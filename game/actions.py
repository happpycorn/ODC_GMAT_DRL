"""RL action ↔ 物理 Δv 的對應（env 與 SB3Agent 共用，避免兩邊各寫一份）。

action ∈ [-1,1]^3 是**自己 RSW(LVLH)** 座標的方向；大小 = 單次上限 × min(|a|,1)^power。
"""
import numpy as np

from physics.frames import rsw_basis


def action_to_dv(game, side, action, power=1.0):
    a = np.nan_to_num(np.asarray(action, dtype=np.float64).reshape(3), nan=0.0)
    n = float(np.linalg.norm(a))
    if n < 1e-6:
        return np.zeros(3)
    mag = game.rules.max_dv(side) * min(n, 1.0) ** power
    return rsw_basis(game.r(side), game.v(side)).T @ (a / n * mag)


def dv_to_action(game, side, dv_eci_mps, power=1.0):
    """action_to_dv 的反函數（行為複製用）。超過單次上限的部分會被夾掉。"""
    dv_rsw = rsw_basis(game.r(side), game.v(side)) @ np.asarray(dv_eci_mps, dtype=np.float64)
    mag = float(np.linalg.norm(dv_rsw))
    if mag < 1e-9:
        return np.zeros(3, dtype=np.float32)
    frac = min(mag / game.rules.max_dv(side), 1.0) ** (1.0 / power)
    return (dv_rsw / mag * frac).astype(np.float32)
