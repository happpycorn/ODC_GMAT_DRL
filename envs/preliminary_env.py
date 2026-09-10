"""初賽語意的追逐環境：B（我方）攔截被動的 A，兼顧時間與燃料。

**改動說明（HAP-52）**：
* 修好 `compute_reward` 的簽名——base 現在統一以 `(obs, action, terminated, truncated)`
  呼叫，不再與 base 的 `compute_reward(obs)` 打架、也拿掉了對抽象 `super()` 的無效呼叫。
* Δv / 違規累計搬到 base 統一處理，這裡不再自己 override `step()`（原本會與 base
  重複累計）。
* 終局分數改用 vendored 的官方計分函式 `physics.calculate_score`，不再內嵌一份會與
  官方公式漂移的 sigmoid。
"""
import numpy as np

from envs.base_env import GmatBaseEnv
from physics import calculate_score

# 命中門檻：相對距離 ≤ 5 km 視為攔截成功（初賽規則）
INTERCEPT_RADIUS_KM = 5.0


class GmatPreliminaryEnv(GmatBaseEnv):
    def __init__(self, config=None):
        super().__init__(config or {})

        # 官方計分參數（規則第 5 節，賽前公告；這裡先給初賽量級的佔位值）
        rules = self.config
        self.k_t = float(rules.get("k_t", 0.001))
        self.C_t = float(rules.get("C_t", 10000.0))
        self.k_v = float(rules.get("k_v", 0.005))
        self.C_v = float(rules.get("C_v", 3000.0))

        self.previous_distance = float("inf")

    def reset(self, seed=None, options=None):
        obs, info = super().reset(seed=seed, options=options)
        self.previous_distance = float(np.linalg.norm(obs[0:3]))
        return obs, info

    def check_done(self, obs):
        """相對距離 ≤ 5 km → 攔截成功終止；超過時間上限 → 超時截斷。"""
        distance = float(np.linalg.norm(obs[0:3]))
        terminated = distance <= INTERCEPT_RADIUS_KM
        truncated = self._get_elapsed_time() >= self.t_max
        return terminated, truncated

    def _compute_reward(self, obs, action, terminated, truncated):
        distance = float(np.linalg.norm(obs[0:3]))

        # 稠密塑形：拉近距離給正回饋、消耗 Δv 給小懲罰
        step_reward = (self.previous_distance - distance) * 0.1
        self.previous_distance = distance
        step_dv = float(np.linalg.norm(action) * self.max_dv)  # 與 base 的映射一致
        step_reward -= step_dv * 0.001

        # 撞地球：直接大幅懲罰並收場
        if self.crashed:
            return step_reward - 100.0

        # 終局：加上官方計分（距離/時間/燃料 三段 + 違規懲罰）
        if terminated or truncated:
            final_score = calculate_score(
                min_distance_km=distance,
                total_time_sec=self._get_elapsed_time(),
                total_dv_mps=self.total_delta_v,
                penalty_count=self.violation_count,
                k_t=self.k_t, C_t=self.C_t, k_v=self.k_v, C_v=self.C_v,
            )
            step_reward += final_score * 10.0

        return step_reward
