"""解析 / 啟發式 agent：不用訓練、規則一公布就能用的保底大腦，也是 RL 的對手與基準。

* LambertPursuer —— 每回合對「躲者從現在起純滑行」的預測星曆解最省 Δv 的攔截
  （TOF × 圈數 × 分支掃描 + J2 打靶），超過這一發的上限就先推一部分、下回合重規劃
  （receding horizon）。`time_weight_mps` 決定「早點抓到」值多少 Δv。
* DvEvader —— 候選脈衝（RSW 方向 × 大小）逐一模擬自己這個窗口，挑讓
  「追者攔截所需 Δv − 追者剩餘燃料」最大者（燃料消耗戰，見 METHODOLOGY §5）。
"""
import math
from itertools import product

import numpy as np

from agents.base import Agent, rsw_to_eci_dv
from physics.coast import closest_approach
from physics.core_math import check_constraints, reaches_perigee
from physics.intercept import _refine_tof, intercept_scan, min_intercept, shoot_j2
from physics.propagator import propagate


def orbit_survives(game, side, dv_eci_mps, horizon=None):
    """施加 dv 之後純滑行 horizon 秒（預設到 T_max）會不會掉到撞地高度以下。

    密切軌道近地點在撞地半徑之上 → 安全；否則看剩餘時間內會不會真的飛過近地點
    （同 Planner 的 reaches_perigee 分拆法，二體近似，J2 在這個判斷上的影響可忽略）。
    """
    r = game.r(side)
    v = game.v(side) + np.asarray(dv_eci_mps, dtype=np.float64) / 1000.0
    h = game.time_left if horizon is None else horizon
    if check_constraints(r, v, game.mu, game.crash_radius):
        return True
    return not reaches_perigee(r, v, game.mu, h)


def pursuer_need(game, horizon=None, max_revs=2, pts_per_period=24, n_refine=2, refine_iters=10,
                 max_pts=160):
    """追者此刻一發攔截（假設躲者之後純滑行）、在 horizon 秒內抓到所需的最小 Δv（m/s）與 TOF。

    ⚠️ 2026-09-15 實測教訓：TOF 網格要跟軌道週期走（每週期 pts_per_period 點），固定點數在
    長 horizon 下會漏掉尖銳的極小值（24 點掃 26,000 s 回報 96 m/s，高解析是 5 m/s）。
    另外 horizon 拉到整個 T_max 時，多圈調相幾乎免費，這個量會飽和到個位數 m/s 失去
    鑑別力——所以局勢評估 / 塑形 / 躲者啟發式用「接下來幾個窗口內」的短 horizon 版本。
    """
    R = game.rules
    H = game.time_left if horizon is None else min(horizon, game.time_left)
    if H <= 60.0:
        return math.inf, 0.0
    T = game.period("pursuer")
    n = int(np.clip(math.ceil(H / T * pts_per_period), 8, max_pts))
    dv, tof, _ = min_intercept(game.mu, R.gravity_degree, game.r("pursuer"), game.v("pursuer"),
                               game.r("evader"), game.v("evader"), 60.0, H, n, max_revs,
                               game.crash_radius, n_refine, refine_iters)
    return float(dv) * 1000.0, float(tof)


def need_horizon(game, windows=4.0):
    """短 horizon：接下來 `windows` 個窗口，至少半個週期（太短會找不到任何可行轉移）。"""
    return max(windows * game.rules.window_sec, 0.5 * game.period("pursuer"))


class LambertPursuer(Agent):
    name = "lambert_pursuer"

    def __init__(self, time_weight_mps=10.0, n_tof=40, max_revs=2, j2_shoot=True, coast_if_captures=True):
        self.time_weight_mps = time_weight_mps   # 每晚一個窗口抓到，願意多付多少 m/s
        self.n_tof = n_tof
        self.max_revs = max_revs
        self.j2_shoot = j2_shoot
        self.coast_if_captures = coast_if_captures
        if time_weight_mps != 10.0:
            self.name = f"lambert_pursuer(w={time_weight_mps:g})"

    def act(self, game, side):
        assert side == "pursuer"
        R = game.rules
        cap = game.burn_cap(side)
        if cap <= 0.0:
            return np.zeros(3)
        rp, vp, re, ve = game.r("pursuer"), game.v("pursuer"), game.r("evader"), game.v("evader")
        mu, gd = game.mu, R.gravity_degree

        # 已經在滑行中會進捕獲球（這個窗口內）→ 不動，省油
        if self.coast_if_captures:
            d_ca, _, _ = closest_approach(rp, vp, re, ve, game.next_window(), 60.0, mu, gd)
            if d_ca <= 0.8 * R.capture_radius_km:
                return np.zeros(3)

        horizon = game.time_left
        if horizon <= 60.0:
            return np.zeros(3)
        tofs, dvs, v1s, re_at, ve_at = intercept_scan(mu, gd, rp, vp, re, ve, 60.0, horizon, self.n_tof,
                                                      self.max_revs, game.crash_radius)
        dvs_mps = dvs * 1000.0
        if not np.any(np.isfinite(dvs_mps)):
            return np.zeros(3)
        score = dvs_mps + self.time_weight_mps * tofs / R.window_sec
        # 轉移弧本身已保證不撞地；但若 TOF 超過這個窗口，躲者有機會閃開，追者就會留在轉移
        # 軌道上——那條軌道得撐到比賽結束，否則是在賭命（實測過一局追者因此撞地）
        window = game.next_window()
        for j in range(len(tofs)):
            if np.isfinite(dvs_mps[j]) and tofs[j] > window and \
                    not orbit_survives(game, side, (v1s[j] - vp) * 1000.0):
                score[j] = np.inf
                dvs_mps[j] = np.inf
        if not np.any(np.isfinite(dvs_mps)):
            return np.zeros(3)
        feasible = dvs_mps <= cap
        if np.any(feasible):
            i = int(np.argmin(np.where(feasible, score, np.inf)))
        else:
            i = int(np.argmin(dvs_mps))

        # 在選中的 TOF 鄰域精修最小 Δv
        lo, hi = max(i - 1, 0), min(i + 1, len(tofs) - 1)
        d, tof, v1 = _refine_tof(mu, gd, rp, vp, re_at[lo], ve_at[lo], tofs[lo], tofs[hi],
                                 self.max_revs, game.crash_radius, 12)
        if not math.isfinite(d) or d * 1000.0 > dvs_mps[i]:
            tof, v1 = tofs[i], v1s[i]
        if self.j2_shoot and gd > 0:
            r_t, _ = propagate(mu, re, ve, tof, gd)
            v1_s, miss = shoot_j2(mu, gd, rp, v1, r_t, tof, 6, 1e-3)
            if math.isfinite(miss) and miss < 1.0:
                v1 = v1_s
        dv = (v1 - vp) * 1000.0
        mag = float(np.linalg.norm(dv))
        full = mag <= cap
        if not full:
            dv *= cap / mag
        # 完整攔截解的弧已在掃描時檢查過（捕獲就結束比賽）；部分推力沒有這個保證，
        # 要確認推完之後的軌道撐得到比賽結束，不行就減半重試
        if not full:
            for _ in range(8):
                if orbit_survives(game, side, dv):
                    break
                dv *= 0.5
            else:
                return np.zeros(3)
        return dv


def _direction_set(kind):
    if kind == "axes":
        dirs = [np.array(d, dtype=float) for d in
                [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]]
    elif kind == "full":
        dirs = [np.array(d, dtype=float) for d in product((-1, 0, 1), repeat=3) if any(d)]
    else:
        raise ValueError(kind)
    return [d / np.linalg.norm(d) for d in dirs]


class DvEvader(Agent):
    name = "dv_evader"

    def __init__(self, directions="full", mags=(1.0, 0.4), fuel_weight=0.3, horizon_windows=4.0, max_revs=1):
        self.dirs = _direction_set(directions)
        self.mags = tuple(mags)
        self.fuel_weight = fuel_weight      # 每花 1 m/s 自己的油扣多少分（m/s 等價）
        self.horizon_windows = horizon_windows
        self.max_revs = max_revs
        if directions != "full" or tuple(mags) != (1.0, 0.4):
            self.name = f"dv_evader({directions},{len(self.mags)}mag)"

    def _score(self, g, spent):
        if g.done:
            return 1e9 if g.winner == "evader" else -1e9
        need, _ = pursuer_need(g, horizon=need_horizon(g, self.horizon_windows), max_revs=self.max_revs,
                               pts_per_period=16, n_refine=1)
        if not math.isfinite(need):
            return 1e8 - self.fuel_weight * spent
        return (need - g.fuel_left("pursuer")) - self.fuel_weight * spent

    def act(self, game, side):
        assert side == "evader"
        cap = game.burn_cap(side)
        best = (-math.inf, np.zeros(3))
        cands = [np.zeros(3)]
        if cap > 0.0:
            cands += [d * m * cap for d in self.dirs for m in self.mags]
        for k, dv_rsw in enumerate(cands):
            dv = rsw_to_eci_dv(game, side, dv_rsw)
            if k > 0 and not orbit_survives(game, side, dv):
                continue                      # 推完會在比賽結束前再入：直接淘汰
            g = game.clone()
            g.play_turn(dv)
            s = self._score(g, float(np.linalg.norm(dv_rsw)))
            if s > best[0]:
                best = (s, dv)
        return best[1]
