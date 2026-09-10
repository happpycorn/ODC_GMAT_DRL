"""決賽核心環境：回合交替的追逃微分賽局（HAP-53）。

理論背景與設計理由見 METHODOLOGY.md。重點：

* **回合交替**：一段時間一方動作、下一段時間換另一方，交替（官方口頭情報）。這裡把
  「一個回合 = 我方下一發脈衝並滑行一個窗口，接著對手下一發脈衝並滑行一個窗口」當成
  一次 `env.step()`。
* **單 agent + 可插拔對手**：本環境對 stable-baselines3 呈現成標準單 agent 環境——
  對手那一半由 `opponent_policy(obs) -> action` 在 env 內部推進。這讓它 (1) 直接吃
  sb3 SAC、(2) curriculum 可把對手設成 coast / 解析基準、(3) self-play 時把對手換成
  凍結的自己（HAP-54）。用 `set_opponent()` 或 config 指定。
* **角色**：`role="pursuer"`（預設）或 `"evader"`，決定學習中的 agent 控制哪一方。
* **勝負**（官方）：追者在時間+燃料限制內把相對距離壓進捕獲半徑 → 追者勝；躲者撐到
  時間上限沒被追上 → 躲者勝。

⚠️ 所有規則數字（窗口長度、Δv/燃料/時間上限、捕獲半徑、雙方初始軌道、計分公式）
都還沒官方公告（Linear HAP-50），以下皆為**佔位參數**，集中在 DEFAULT_* / config，
公告一到只改數字，不動結構。
"""
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from physics import propagate, get_r0_v0, orbital_period, EARTH_MU, RE_VAL
from envs.baselines import BASELINES, coast_policy

# ---- 佔位參數（HAP-50 公告後覆寫）----
DEFAULT_WINDOW_SEC = 300.0           # 一個控制窗口（滑行）長度
DEFAULT_MAX_DV_MPS = 1500.0          # 單次機動 Δv 上限
DEFAULT_FUEL_BUDGET_MPS = 3000.0     # 每方總 Δv 預算
DEFAULT_CAPTURE_RADIUS_KM = 5.0      # 捕獲判定半徑
DEFAULT_TMAX_PERIOD_MULT = 4.0       # 時間上限 = 追者軌道週期的幾倍
DEFAULT_GRAVITY_DEGREE = 2
ZEM_HORIZON_CAP_MULT = 2.0           # ZEM 外推最長取幾倍追者週期（限制成本）

# 佔位初始軌道（六根數：SMA km, ECC, INC/RAAN/AOP/TA 度）——追者在後、躲者在前
DEFAULT_ORBIT_PURSUER = {"sma": 7000.0, "ecc": 0.0, "inc": 0.0, "raan": 0.0, "aop": 0.0, "ta": 0.0}
DEFAULT_ORBIT_EVADER = {"sma": 7100.0, "ecc": 0.01, "inc": 0.5, "raan": 0.0, "aop": 0.0, "ta": 8.0}

# 獎勵權重（佔位）
W_SHAPE = 0.1          # 距離塑形（燃料成本塑形待 HAP-54 調參再加）
CAPTURE_BONUS = 500.0  # 追者捕獲 / 躲者被捕的終局值（零和）
TIMEOUT_VALUE = 500.0  # 躲者存活 / 追者超時的終局值（零和）
CRASH_PENALTY = 500.0  # 自己撞地球的懲罰


class GmatFinalEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}

        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)
        # obs：r_rel(3)+v_rel(3)+own_fuel(1)+opp_fuel(1)+t_remain(1)+zem(3) = 12
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(12,), dtype=np.float32)

        self.role = self.config.get("role", "pursuer")
        assert self.role in ("pursuer", "evader"), "role 必須是 'pursuer' 或 'evader'"

        self.mu = float(self.config.get("mu", EARTH_MU))
        self.gravity_degree = int(self.config.get("gravity_degree", DEFAULT_GRAVITY_DEGREE))
        self.window_sec = float(self.config.get("window_sec", DEFAULT_WINDOW_SEC))
        self.max_dv = float(self.config.get("max_dv_mps", DEFAULT_MAX_DV_MPS))
        self.fuel_budget = float(self.config.get("fuel_budget_mps", DEFAULT_FUEL_BUDGET_MPS))
        self.capture_radius = float(self.config.get("capture_radius_km", DEFAULT_CAPTURE_RADIUS_KM))
        self.orbit_p = dict(self.config.get("orbit_pursuer", DEFAULT_ORBIT_PURSUER))
        self.orbit_e = dict(self.config.get("orbit_evader", DEFAULT_ORBIT_EVADER))

        self.T_p = orbital_period(self.orbit_p["sma"], self.mu)
        tmax_mult = float(self.config.get("t_max_period_multiple", DEFAULT_TMAX_PERIOD_MULT))
        t_max = self.config.get("t_max_sec", None)
        self.t_max = float(t_max) if t_max is not None else tmax_mult * self.T_p
        self.zem_horizon_cap = ZEM_HORIZON_CAP_MULT * self.T_p

        # 對手策略：config 可給字串（查 BASELINES）或 callable；預設 coast
        opp = self.config.get("opponent_policy", "coast")
        self.opponent_policy = BASELINES.get(opp, coast_policy) if isinstance(opp, str) else opp

        self._init_state()

    # ------------------------------------------------------------------ #
    def set_opponent(self, policy):
        """換對手（curriculum / self-play 用）。接受字串或 callable(obs)->action。"""
        self.opponent_policy = BASELINES.get(policy, coast_policy) if isinstance(policy, str) else policy

    def _init_state(self):
        self.rp = self.vp = self.re = self.ve = None
        self.used_p = 0.0
        self.used_e = 0.0
        self.viol_p = 0
        self.viol_e = 0
        self.elapsed = 0.0
        self.outcome = None            # None / "capture" / "timeout" / "crash_pursuer" / "crash_evader"
        self.crashed_side = None

    # ------------------------------------------------------------------ #
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.rp, self.vp = get_r0_v0(**self.orbit_p, mu=self.mu)
        self.re, self.ve = get_r0_v0(**self.orbit_e, mu=self.mu)
        self.used_p = self.used_e = 0.0
        self.viol_p = self.viol_e = 0
        self.elapsed = 0.0
        self.outcome = None
        self.crashed_side = None
        return self._obs_for(self.role), {}

    def step(self, action):
        action = np.asarray(action, dtype=np.float64).reshape(3)
        opp_role = "evader" if self.role == "pursuer" else "pursuer"

        dist_before = self._distance()

        # 一個回合 = 我方一發 + 滑行；接著對手一發 + 滑行（交替）
        self._apply_impulse(self.role, action)
        self._coast(self.window_sec)

        if self._check_terminal() is None:
            opp_action = np.asarray(self.opponent_policy(self._obs_for(opp_role)),
                                    dtype=np.float64).reshape(3)
            self._apply_impulse(opp_role, opp_action)
            self._coast(self.window_sec)
            self._check_terminal()

        obs = self._obs_for(self.role)
        terminated = self.outcome in ("capture", "crash_pursuer", "crash_evader")
        truncated = self.outcome == "timeout"
        reward = self._reward(dist_before)

        info = {
            "distance_km": self._distance(),
            "outcome": self.outcome,
            "used_dv_pursuer": self.used_p,
            "used_dv_evader": self.used_e,
            "elapsed_sec": self.elapsed,
            "agent_won": self._agent_won(),
        }
        return obs, float(reward), bool(terminated), bool(truncated), info

    # ------------------------------------------------------------------ #
    def _own_opp(self, perspective):
        if perspective == "pursuer":
            return (self.rp, self.vp, self.used_p), (self.re, self.ve, self.used_e)
        return (self.re, self.ve, self.used_e), (self.rp, self.vp, self.used_p)

    def _apply_impulse(self, side, action):
        """action ∈ [-1,1]^3 → ECI Δv 向量 (m/s)，脈衝加到該方速度；燃料不足則夾成 0。"""
        remaining = self.fuel_budget - (self.used_p if side == "pursuer" else self.used_e)
        dv_mps = action * self.max_dv
        mag = float(np.linalg.norm(dv_mps))
        if remaining <= 0.0:
            return 0.0                      # 沒油了，動不了
        if mag > remaining:                 # 只剩一點油：等比例縮到剩餘量
            dv_mps = dv_mps * (remaining / mag)
            mag = remaining
        if side == "pursuer":
            self.vp = self.vp + dv_mps / 1000.0
            self.used_p += mag
            if mag > self.max_dv:
                self.viol_p += 1
        else:
            self.ve = self.ve + dv_mps / 1000.0
            self.used_e += mag
            if mag > self.max_dv:
                self.viol_e += 1
        return mag

    def _coast(self, dt):
        self.rp, self.vp = propagate(self.mu, self.rp, self.vp, dt, self.gravity_degree)
        self.re, self.ve = propagate(self.mu, self.re, self.ve, dt, self.gravity_degree)
        self.elapsed += dt
        if not (np.all(np.isfinite(self.rp)) and np.all(np.isfinite(self.re))):
            self.crashed_side = "pursuer" if not np.all(np.isfinite(self.rp)) else "evader"
        elif np.linalg.norm(self.rp) < RE_VAL:
            self.crashed_side = "pursuer"
        elif np.linalg.norm(self.re) < RE_VAL:
            self.crashed_side = "evader"

    def _distance(self):
        return float(np.linalg.norm(self.rp - self.re))

    def _check_terminal(self):
        """設定並回傳 self.outcome（None 表示尚未結束）。優先序：撞地 > 捕獲 > 超時。"""
        if self.crashed_side is not None:
            self.outcome = f"crash_{self.crashed_side}"
        elif self._distance() <= self.capture_radius:
            self.outcome = "capture"
        elif self.elapsed >= self.t_max:
            self.outcome = "timeout"
        return self.outcome

    def _zem(self, perspective):
        """自由漂移外推的預測相對位置向量 (km)：把雙方從當前狀態往前滑行 horizon 秒。"""
        horizon = min(self.t_max - self.elapsed, self.zem_horizon_cap)
        if horizon <= 0.0:
            (ro, _, _), (rp, _, _) = self._own_opp(perspective)
            return rp - ro
        rp_p, _ = propagate(self.mu, self.rp, self.vp, horizon, self.gravity_degree)
        re_p, _ = propagate(self.mu, self.re, self.ve, horizon, self.gravity_degree)
        if perspective == "pursuer":
            return re_p - rp_p
        return rp_p - re_p

    def _obs_for(self, perspective):
        (r_own, v_own, used_own), (r_opp, v_opp, used_opp) = self._own_opp(perspective)
        r_rel = r_opp - r_own
        v_rel = v_opp - v_own
        own_fuel = max(0.0, 1.0 - used_own / self.fuel_budget)
        opp_fuel = max(0.0, 1.0 - used_opp / self.fuel_budget)
        t_remain = max(0.0, 1.0 - self.elapsed / self.t_max)
        zem = self._zem(perspective)
        obs = np.concatenate([r_rel, v_rel, [own_fuel, opp_fuel, t_remain], zem]).astype(np.float64)
        obs = np.nan_to_num(obs, nan=0.0, posinf=1e12, neginf=-1e12)
        return obs.astype(np.float32)

    def _agent_won(self):
        if self.outcome is None:
            return None
        if self.role == "pursuer":
            return self.outcome == "capture"
        return self.outcome == "timeout"          # 躲者：存活到時間上限即勝

    def _reward(self, dist_before):
        """從 agent（self.role）視角的近似零和獎勵：距離塑形 + 燃料成本 + 終局值。

        佔位版（HAP-50 公告計分後再對齊）：追者要縮短距離、躲者要拉開/存活。
        """
        dist_after = self._distance()
        closing = dist_before - dist_after        # >0 表示距離縮短

        if self.role == "pursuer":
            r = W_SHAPE * closing
        else:
            r = W_SHAPE * (-closing)               # 躲者：距離拉開才是好事

        # 終局值（零和）
        if self.outcome == "capture":
            r += CAPTURE_BONUS if self.role == "pursuer" else -CAPTURE_BONUS
        elif self.outcome == "timeout":
            r += TIMEOUT_VALUE if self.role == "evader" else -TIMEOUT_VALUE
        elif self.outcome == f"crash_{self.role}":
            r -= CRASH_PENALTY
        elif self.outcome in ("crash_pursuer", "crash_evader"):
            r += CAPTURE_BONUS                     # 對手自爆，等同我方獲勝

        return r
