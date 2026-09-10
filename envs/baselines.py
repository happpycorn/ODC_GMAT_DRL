"""決賽環境用的解析/啟發式基準策略（curriculum 第一階的對手，也是 self-play 前的 sanity 對照）。

每個策略都是 `policy(obs) -> action`，action ∈ [-1,1]^3；obs 是 `GmatFinalEnv` 從
**該策略所控制那一方的視角**組出來的 12 維向量（見 GmatFinalEnv._obs_for 的欄位說明）：
    obs[0:3]  = r_rel  (對手位置 − 自己位置, km)
    obs[3:6]  = v_rel  (對手速度 − 自己速度, km/s)
    obs[6]    = 自己剩餘燃料比例
    obs[7]    = 對手剩餘燃料比例
    obs[8]    = 剩餘時間比例
    obs[9:12] = ZEM 預測相對位置（自由漂移外推, km）

這些是 obs-only 的樸素基準（示範用）。真正的解析 ZEM/Lambert 追者、徑向逃者（需要
絕對狀態與 Planner 的 Lambert 求解器）留待 HAP-54 的訓練管線再補，見 METHODOLOGY §6。
"""
import numpy as np


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else np.zeros(3, dtype=np.float64)


def coast_policy(obs):
    """完全不推進（純漂移）。curriculum 第一階：追者對被動目標 = 初賽問題。"""
    return np.zeros(3, dtype=np.float32)


def naive_pursuer_policy(obs, gain: float = 0.1):
    """樸素追者：沿 ZEM 方向（打向對手的預測位置）全力推。

    比「沿當前視線追」好一點，因為 ZEM 已含自由漂移外推；但仍不是最優（沒解 Lambert、
    沒考慮燃料經濟）。當強一點的基準對手用。
    """
    aim = obs[9:12]
    if np.linalg.norm(aim) < 1e-9:
        aim = obs[0:3]  # 退回當前相對位置
    return np.clip(gain * _unit(aim), -1.0, 1.0).astype(np.float32)


def naive_evader_policy(obs, gain: float = 0.1):
    """樸素逃者：沿遠離追者方向推，加一個垂直分量做 juke（逼追者多花 Δv 修正）。"""
    r_rel = obs[0:3]
    away = -_unit(r_rel)
    # 垂直於視線的一個方向（與世界 z 軸叉積；視線接近 z 時退用 x 軸）
    ref = np.array([0.0, 0.0, 1.0]) if abs(away[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    perp = _unit(np.cross(away, ref))
    a = 0.7 * away + 0.7 * perp
    return np.clip(gain * a, -1.0, 1.0).astype(np.float32)


# 名稱 → 策略，方便從 config 以字串指定對手
BASELINES = {
    "coast": coast_policy,
    "naive_pursuer": naive_pursuer_policy,
    "naive_evader": naive_evader_policy,
}
