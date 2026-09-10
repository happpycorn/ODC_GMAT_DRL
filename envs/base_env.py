"""追逐/攔截任務的 Gym 基礎環境。

**改動說明（HAP-51 / HAP-52）**：原本這個檔把 GMAT 當每步的模擬器（且 `_get_obs`
回傳全 0 的 stub）。DRL 要跑幾百萬步，GMAT 一步都嫌慢，所以改用 vendored 進來、與
GMAT 交叉驗證到公尺級的純 numba 物理（`physics/`）當引擎；GMAT 只在最終驗證用。

本基礎環境提供共用機制（初始化雙方軌道、施加脈衝、傳播、組觀測、燃料/違規/時間帳），
`compute_reward` 與 `check_done` 由子類別實作。決賽的回合交替追逃環境（HAP-53）會在此
之上另建，不改這個檔的單邊語意。
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np

from physics import propagate, get_r0_v0, orbital_period, EARTH_MU, RE_VAL

# 初賽規則的預設數字（晉級賽若不同，從 config 覆寫即可）
DEFAULT_MAX_DV_MPS = 1500.0            # 單次機動 Δv 上限
DEFAULT_FUEL_BUDGET_MPS = 3000.0       # 總 Δv 預算（僅用於觀測正規化，非硬性規則）
DEFAULT_DT_SEC = 100.0                 # 每步時間 = 機動間隔下限
DEFAULT_TMAX_PERIOD_MULT = 4.0         # 任務時間上限 = T_A 的幾倍

# 佔位初始軌道（六根數：SMA km, ECC, INC/RAAN/AOP/TA 度）。等 HAP-50 公告正式測資再換。
DEFAULT_ORBIT_A = {"sma": 7000.0, "ecc": 0.0, "inc": 0.0, "raan": 0.0, "aop": 0.0, "ta": 40.0}
DEFAULT_ORBIT_B = {"sma": 7000.0, "ecc": 0.0, "inc": 0.0, "raan": 0.0, "aop": 0.0, "ta": 0.0}


class GmatBaseEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}

        # 1. 動作空間：3 維連續推力方向 [-1,1]，於 _apply_action 映射成 Δv 向量 (m/s)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)

        # 2. 觀測空間：[相對位置(3) km, 相對速度(3) km/s, 剩餘燃料比例(1)]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(7,), dtype=np.float32)

        # 3. 物理 / 規則參數
        self.mu = float(self.config.get("mu", EARTH_MU))
        self.gravity_degree = int(self.config.get("gravity_degree", 2))
        self.dt = float(self.config.get("dt_sec", DEFAULT_DT_SEC))
        self.max_dv = float(self.config.get("max_dv_mps", DEFAULT_MAX_DV_MPS))
        self.fuel_budget = float(self.config.get("fuel_budget_mps", DEFAULT_FUEL_BUDGET_MPS))
        self.orbit_A = dict(self.config.get("orbit_A", DEFAULT_ORBIT_A))
        self.orbit_B = dict(self.config.get("orbit_B", DEFAULT_ORBIT_B))

        # T_A 由 A 的 SMA 算出（不再寫死 5400）；t_max = 倍數 × T_A
        self.T_A = orbital_period(self.orbit_A["sma"], self.mu)
        tmax_mult = float(self.config.get("t_max_period_multiple", DEFAULT_TMAX_PERIOD_MULT))
        self.t_max = self.config.get("t_max_sec", None)
        self.t_max = float(self.t_max) if self.t_max is not None else tmax_mult * self.T_A

        # 執行期狀態（reset 時初始化）
        self.rA = self.vA = self.rB = self.vB = None
        self.total_delta_v = 0.0
        self.violation_count = 0
        self.elapsed_time = 0.0
        self.crashed = False

    # ------------------------------------------------------------------ #
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.rA, self.vA = get_r0_v0(**self.orbit_A, mu=self.mu)
        self.rB, self.vB = get_r0_v0(**self.orbit_B, mu=self.mu)
        self.total_delta_v = 0.0
        self.violation_count = 0
        self.elapsed_time = 0.0
        self.crashed = False

        return self._get_obs(), {}

    def step(self, action):
        action = np.asarray(action, dtype=np.float64).reshape(3)

        # 1. 施加動作（脈衝 Δv 加到 B 的速度上），回傳這一棒的 Δv 大小 (m/s)
        step_dv = self._apply_action(action)
        self.total_delta_v += step_dv
        if step_dv > self.max_dv:
            self.violation_count += 1

        # 2. 物理傳播：A 被動只受重力，B 施加脈衝後同樣只受重力，各往前 dt 秒
        self._propagate(self.dt)
        self.elapsed_time += self.dt

        # 3. 組觀測（並偵測數值爆炸 / 撞地球）
        obs = self._get_obs()

        # 4. 結束判定與獎勵（由子類別實作；base 統一補上「撞地球」這個硬終止）
        term_sub, trunc_sub = self.check_done(obs)
        terminated = bool(term_sub or self.crashed)
        truncated = bool(trunc_sub)

        reward = self._compute_reward(obs, action, terminated, truncated)
        info = {
            "distance_km": float(np.linalg.norm(self.rA - self.rB)),
            "total_delta_v_mps": self.total_delta_v,
            "violation_count": self.violation_count,
            "elapsed_time_sec": self.elapsed_time,
            "crashed": self.crashed,
        }
        return obs, float(reward), terminated, truncated, info

    # ------------------------------------------------------------------ #
    def _apply_action(self, action):
        """action ∈ [-1,1]^3 → ECI 慣性系的 Δv 向量 (m/s)，脈衝加到 B 的速度。

        映射（佔位，HAP-52）：`dv_mps = action * max_dv`。步 Δv 大小以向量模長計，
        對角方向可能超過 max_dv → 記一次違規（與規則「單次機動 Δv 上限」一致）。
        速度單位是 km/s，Δv 是 m/s，施加時除以 1000。
        """
        dv_mps = action * self.max_dv
        self.vB = self.vB + dv_mps / 1000.0
        return float(np.linalg.norm(dv_mps))

    def _propagate(self, dt):
        rA, vA = propagate(self.mu, self.rA, self.vA, dt, self.gravity_degree)
        rB, vB = propagate(self.mu, self.rB, self.vB, dt, self.gravity_degree)
        self.rA, self.vA, self.rB, self.vB = rA, vA, rB, vB

        # 撞地球 / 數值爆炸偵測
        finite = np.all(np.isfinite(rB)) and np.all(np.isfinite(rA))
        if (not finite) or np.linalg.norm(rB) < RE_VAL:
            self.crashed = True

    def _get_obs(self):
        r_rel = self.rA - self.rB
        v_rel = self.vA - self.vB
        fuel_frac = max(0.0, 1.0 - self.total_delta_v / self.fuel_budget)
        obs = np.concatenate([r_rel, v_rel, [fuel_frac]]).astype(np.float64)
        # 防呆：Box.contains 不接受 nan/inf，數值爆炸時夾成有限值
        obs = np.nan_to_num(obs, nan=0.0, posinf=1e12, neginf=-1e12)
        return obs.astype(np.float32)

    def _get_elapsed_time(self) -> float:
        return self.elapsed_time

    # ------------------------------------------------------------------ #
    def _compute_reward(self, obs, action, terminated, truncated):
        # 命名刻意加底線：`compute_reward` 是 gym GoalEnv 的保留方法名，用它會讓
        # stable-baselines3 的 check_env 把本環境誤判成 GoalEnv。
        raise NotImplementedError

    def check_done(self, obs):
        raise NotImplementedError
