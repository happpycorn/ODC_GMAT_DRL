"""Agent 介面：`act(game, side) -> Δv (ECI, m/s)`。

Agent 拿到的是完整遊戲狀態（game.core.Game），可以自己決定要看什麼；Game 會把回傳的
Δv 裁到合法（單次上限、剩餘燃料），所以 agent 不必自己保證合法。
"""
import numpy as np

from physics.frames import rsw_basis


class Agent:
    name = "agent"

    def reset(self, seed=None):
        """每局開始前呼叫。"""

    def act(self, game, side) -> np.ndarray:
        raise NotImplementedError

    def __repr__(self):
        return f"<{type(self).__name__} {self.name}>"


def rsw_to_eci_dv(game, side, dv_rsw_mps):
    return rsw_basis(game.r(side), game.v(side)).T @ np.asarray(dv_rsw_mps, dtype=np.float64)


class CoastAgent(Agent):
    """完全不推（純漂移）。追者對它 = 初賽問題。"""
    name = "coast"

    def act(self, game, side):
        return np.zeros(3)


class RandomAgent(Agent):
    """每回合以機率 p_burn 朝 RSW 隨機方向推 [0, frac_max] × burn_cap。"""
    name = "random"

    def __init__(self, p_burn=0.5, frac_max=1.0, seed=None):
        self.p_burn = p_burn
        self.frac_max = frac_max
        self.rng = np.random.default_rng(seed)

    def reset(self, seed=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)

    def act(self, game, side):
        if self.rng.random() > self.p_burn:
            return np.zeros(3)
        d = self.rng.normal(size=3)
        d /= np.linalg.norm(d)
        mag = self.rng.uniform(0.0, self.frac_max) * game.burn_cap(side)
        return rsw_to_eci_dv(game, side, d * mag)


class CallableAgent(Agent):
    """把 `fn(game, side) -> dv` 包成 Agent。"""

    def __init__(self, fn, name="callable"):
        self.fn = fn
        self.name = name

    def act(self, game, side):
        return np.asarray(self.fn(game, side), dtype=np.float64)
