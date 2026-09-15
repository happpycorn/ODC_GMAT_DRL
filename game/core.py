"""決賽追逃賽局的純遊戲核心（與 gym 解耦）。

一個 **turn** = 輪到的一方（mover）下一發脈衝 → 雙方滑行 `window_sec`（最後一回合截到
T_max）→ 換另一方。滑行期間用 `physics.coast.coast_pair` 連續偵測捕獲 / 撞地，事件
發生就停在那個時刻結束比賽。

勝負（官方）：追者在時間+燃料內靠近到捕獲半徑 → 追者勝；躲者撐到 T_max → 躲者勝。
撞地（軌跡低於 crash_altitude）→ 撞的那方輸（佔位判定，待 HAP-50）。

Agent 直接吃 Game（完整狀態：雙方 r/v、燃料、時間、規則），不必經過 RL 觀測；RL 的
觀測由 game/obs.py 從 Game 組出來。
"""
import copy
import math

import numpy as np

from game.rules import SIDES, Rules, other
from physics import EARTH_MU, RE_VAL, get_r0_v0, orbital_period
from physics.coast import EV_CAPTURE, EV_CRASH_E, EV_CRASH_P, coast_pair
from physics.frames import rsw_basis

OUTCOME_WINNER = {
    "capture": "pursuer",
    "crash_evader": "pursuer",
    "timeout": "evader",
    "crash_pursuer": "evader",
}


def sma_from_rv(r, v, mu=EARTH_MU):
    energy = float(v @ v) / 2.0 - mu / float(np.linalg.norm(r))
    return -mu / (2.0 * energy) if energy < 0 else math.inf


class Game:
    def __init__(self, rules: Rules, rp, vp, re, ve, mu: float = EARTH_MU):
        self.rules = rules
        self.mu = float(mu)
        self._r = {"pursuer": np.asarray(rp, dtype=np.float64).copy(),
                   "evader": np.asarray(re, dtype=np.float64).copy()}
        self._v = {"pursuer": np.asarray(vp, dtype=np.float64).copy(),
                   "evader": np.asarray(ve, dtype=np.float64).copy()}
        self.used = {"pursuer": 0.0, "evader": 0.0}
        self.t = 0.0
        if rules.t_max_sec > 0:
            self.t_max = float(rules.t_max_sec)
        else:
            self.t_max = rules.t_max_periods * orbital_period(sma_from_rv(self._r["pursuer"], self._v["pursuer"], mu), mu)
        self.mover = rules.first_mover
        self.turn = 0
        self.outcome = None
        self.min_dist = self.distance()
        self.initial = {s: (self._r[s].copy(), self._v[s].copy()) for s in SIDES}
        self.history = []
        if self.min_dist <= rules.capture_radius_km:
            self.outcome = "capture"

    # ------------------------------------------------------------------ 建構
    @classmethod
    def from_elements(cls, rules: Rules, orbit_pursuer: dict, orbit_evader: dict, mu: float = EARTH_MU):
        rp, vp = get_r0_v0(**orbit_pursuer, mu=mu)
        re, ve = get_r0_v0(**orbit_evader, mu=mu)
        g = cls(rules, rp, vp, re, ve, mu)
        g.initial_elements = {"pursuer": dict(orbit_pursuer), "evader": dict(orbit_evader)}
        return g

    def clone(self) -> "Game":
        g = copy.copy(self)
        g._r = {s: a.copy() for s, a in self._r.items()}
        g._v = {s: a.copy() for s, a in self._v.items()}
        g.used = dict(self.used)
        g.history = list(self.history)
        return g

    # ------------------------------------------------------------------ 查詢
    def r(self, side):
        return self._r[side]

    def v(self, side):
        return self._v[side]

    def distance(self) -> float:
        return float(np.linalg.norm(self._r["pursuer"] - self._r["evader"]))

    def fuel_left(self, side) -> float:
        return max(0.0, self.rules.fuel(side) - self.used[side])

    def burn_cap(self, side) -> float:
        """這一發最多能推多少 m/s（單次上限與剩餘燃料取小）。"""
        return min(self.rules.max_dv(side), self.fuel_left(side))

    @property
    def time_left(self) -> float:
        return max(0.0, self.t_max - self.t)

    @property
    def done(self) -> bool:
        return self.outcome is not None

    @property
    def winner(self):
        return OUTCOME_WINNER.get(self.outcome)

    @property
    def crash_radius(self) -> float:
        return RE_VAL + self.rules.crash_altitude_km

    def period(self, side) -> float:
        """該方當前密切軌道週期（雙曲線時回傳 6000 s 當尺度，避免 inf 傳下去）。"""
        a = sma_from_rv(self._r[side], self._v[side], self.mu)
        return orbital_period(a, self.mu) if math.isfinite(a) else 6000.0

    def next_window(self) -> float:
        return min(self.rules.window_sec, self.time_left)

    # ------------------------------------------------------------------ 推進
    def clip_dv(self, side, dv_eci_mps) -> np.ndarray:
        dv = np.asarray(dv_eci_mps, dtype=np.float64).reshape(3)
        if not np.all(np.isfinite(dv)):
            return np.zeros(3)
        mag = float(np.linalg.norm(dv))
        cap = self.burn_cap(side)
        if mag > cap:
            dv = dv * (cap / mag) if mag > 0 else np.zeros(3)
        return dv

    def play_turn(self, dv_eci_mps) -> dict:
        """輪到的一方施加脈衝（自動裁到合法）並滑行一個窗口。回傳這個 turn 的紀錄。"""
        if self.done:
            raise RuntimeError("比賽已結束")
        side = self.mover
        dv = self.clip_dv(side, dv_eci_mps)
        mag = float(np.linalg.norm(dv))
        r_b, v_b = self._r[side].copy(), self._v[side].copy()
        dv_rsw = rsw_basis(r_b, v_b) @ dv
        self._v[side] = self._v[side] + dv / 1000.0
        self.used[side] += mag

        dt = self.next_window()
        R = self.rules
        rp, vp, re, ve, t_el, ev, dmin, t_dmin = coast_pair(
            self._r["pursuer"], self._v["pursuer"], self._r["evader"], self._v["evader"],
            dt, R.substep_sec, self.mu, R.gravity_degree, R.capture_radius_km, self.crash_radius)
        self._r["pursuer"], self._v["pursuer"] = rp, vp
        self._r["evader"], self._v["evader"] = re, ve
        t0 = self.t
        self.t += float(t_el)
        self.min_dist = min(self.min_dist, float(dmin))

        if ev == EV_CAPTURE:
            self.outcome = "capture"
        elif ev == EV_CRASH_P:
            self.outcome = "crash_pursuer"
        elif ev == EV_CRASH_E:
            self.outcome = "crash_evader"
        elif self.t >= self.t_max - 1e-6:
            self.outcome = "timeout"

        rec = {
            "turn": self.turn, "side": side, "t": t0, "dv_eci_mps": dv, "dv_rsw_mps": dv_rsw,
            "dv_mps": mag, "r_before": r_b, "v_before": v_b, "coast_sec": float(t_el),
            "window_min_dist_km": float(dmin), "t_window_min": t0 + float(t_dmin),
            "distance_after_km": self.distance(), "outcome": self.outcome,
            "rp_after": rp.copy(), "vp_after": vp.copy(), "re_after": re.copy(), "ve_after": ve.copy(),
        }
        self.history.append(rec)
        self.turn += 1
        self.mover = other(side)
        return rec

    def summary(self) -> dict:
        return {
            "outcome": self.outcome, "winner": self.winner, "t_end": self.t, "t_max": self.t_max,
            "turns": self.turn, "min_dist_km": self.min_dist, "final_dist_km": self.distance(),
            "used_pursuer_mps": self.used["pursuer"], "used_evader_mps": self.used["evader"],
        }
