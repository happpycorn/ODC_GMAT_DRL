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


SAFETY_MARGIN_KM = 50.0


def safe_radius(game, margin_km=SAFETY_MARGIN_KM):
    return game.crash_radius + margin_km


def orbit_survives(game, side, dv_eci_mps, horizon=None, margin_km=SAFETY_MARGIN_KM):
    """施加 dv 之後純滑行 horizon 秒（預設到 T_max）會不會掉到「撞地高度 + 安全裕度」以下。

    密切軌道近地點在門檻之上 → 安全；否則看剩餘時間內會不會真的飛過近地點
    （同 Planner 的 reaches_perigee 分拆法，二體近似）。

    ⚠️ 安全裕度是 2026-09-15 對打評測抓到的：零裕度時追者把近地點壓在 101–110 km 高度
    （撞地線 100 km），二體判斷說安全，但 J2 讓近地點在幾圈內緩慢下沉，最後真的再入。
    """
    r = game.r(side)
    v = game.v(side) + np.asarray(dv_eci_mps, dtype=np.float64) / 1000.0
    h = game.time_left if horizon is None else horizon
    if check_constraints(r, v, game.mu, game.crash_radius + margin_km):
        return True
    return not reaches_perigee(r, v, game.mu, h)


def rescue_burn(game, side):
    """目前軌道撐不到比賽結束時，找最小的一發讓它恢復安全（沒有就回傳 None）。"""
    cap = game.burn_cap(side)
    if cap <= 0.0:
        return None
    for frac in (0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0):
        for d in _direction_set("full"):
            dv = rsw_to_eci_dv(game, side, d * frac * cap)
            if orbit_survives(game, side, dv):
                return dv
    return None


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

    def __init__(self, time_weight_mps=10.0, pts_per_period=24, max_revs=2, j2_shoot=True,
                 coast_if_captures=True, max_pts=240, horizon_frac=1.0):
        self.time_weight_mps = time_weight_mps   # 每晚一個窗口抓到，願意多付多少 m/s
        self.horizon_frac = horizon_frac         # 只考慮 TOF <= 剩餘時間 × frac 的攔截（至少一個窗口）
        self.pts_per_period = pts_per_period     # TOF 網格密度跟軌道週期走（固定點數會漏極小值）
        self.max_pts = max_pts
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
            if R.capture_mode == "endpoint":
                rp_w, _ = propagate(mu, rp, vp, game.next_window(), gd)
                re_w, _ = propagate(mu, re, ve, game.next_window(), gd)
                d_ca = float(np.linalg.norm(rp_w - re_w))
            else:
                d_ca, _, _ = closest_approach(rp, vp, re, ve, game.next_window(), 60.0, mu, gd)
            if d_ca <= 0.8 * R.capture_radius_km:
                return np.zeros(3)

        horizon = game.time_left
        if self.horizon_frac < 1.0:
            horizon = min(horizon, max(self.horizon_frac * horizon, game.next_window() + 120.0))
        if horizon <= 60.0:
            return np.zeros(3)
        endpoint = R.capture_mode == "endpoint"
        if endpoint:
            # 只在回合結束瞬間判定捕獲 → 攔截時刻必須落在回合邊界（本窗口末、之後每個窗口末）
            w = R.window_sec
            first = game.next_window()
            k_max = int((horizon - first) // w)
            if k_max < 0:
                return np.zeros(3)
            tof_lo, tof_hi, n_tof = first, first + k_max * w, k_max + 1
        else:
            n_tof = int(np.clip(math.ceil(horizon / game.period("pursuer") * self.pts_per_period), 8, self.max_pts))
            tof_lo, tof_hi = 60.0, horizon
        tofs, dvs, v1s, re_at, ve_at = intercept_scan(mu, gd, rp, vp, re, ve, tof_lo, tof_hi, n_tof,
                                                      self.max_revs, safe_radius(game))
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

        # 在選中的 TOF 鄰域精修最小 Δv（endpoint 模式 TOF 被綁在回合邊界，不能精修）
        tof, v1 = tofs[i], v1s[i]
        if not endpoint:
            lo, hi = max(i - 1, 0), min(i + 1, len(tofs) - 1)
            d, tof_r, v1_r = _refine_tof(mu, gd, rp, vp, re_at[lo], ve_at[lo], tofs[lo], tofs[hi],
                                         self.max_revs, safe_radius(game), 12)
            if math.isfinite(d) and d * 1000.0 <= dvs_mps[i]:
                tof, v1 = tof_r, v1_r
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
        # 完整解且在這個窗口內抓到 → 躲者來不及反應，弧已檢查過安全，直接推。
        # 其他情況（部分推力、或躲者還有機會閃開）推完的軌道必須撐到比賽結束：
        # 不行就減半重試；連不推都會再入的話改做救命推力。
        if full and tof <= game.next_window():
            # 只有「真的會命中」才免檢查：J2 打靶沒收斂時 Lambert 二體解會偏幾公里，
            # 沒抓到就會留在一條可能撞地的轉移軌道上（copilot 演練抓到過）
            rp_t, _ = propagate(mu, rp, vp + dv / 1000.0, tof, gd)
            re_t, _ = propagate(mu, re, ve, tof, gd)
            if np.linalg.norm(rp_t - re_t) <= 0.5 * R.capture_radius_km or orbit_survives(game, side, dv):
                return dv
        if orbit_survives(game, side, dv):
            return dv
        for _ in range(8):
            dv *= 0.5
            if orbit_survives(game, side, dv):
                return dv
        rb = rescue_burn(game, side)
        return rb if rb is not None else np.zeros(3)


def _direction_set(kind):
    if kind == "axes":
        dirs = [np.array(d, dtype=float) for d in
                [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]]
    elif kind == "full":
        dirs = [np.array(d, dtype=float) for d in product((-1, 0, 1), repeat=3) if any(d)]
    else:
        raise ValueError(kind)
    return [d / np.linalg.norm(d) for d in dirs]


class EscapeEvader(Agent):
    """開局高能量逃逸：前 `n_escape` 個躲者回合沿 (徑向+沿軌道) 推滿，之後交給 DvEvader。

    來源（HAP-108 exploitability 重播）：針對 rollout 追者的反制躲者，機動類型跟一般躲者一樣
    （1061/1061 m/s 徑向+沿軌道），差別只在**第二發緊接著推**——兩三個回合內就把遠地點拉到
    追者追不到的高度，rollout 追者判斷所有候選都輸、乾脆不追。把它做成顯式對手模型，
    追者的 rollout 才會把「開局就逃」納入最壞情況。
    """
    name = "escape_evader"

    def __init__(self, n_escape=2, direction=(1.0, 1.0, 0.0), then="dv_evader_fast"):
        d = np.asarray(direction, dtype=float)
        self.dir = d / np.linalg.norm(d)
        self.n_escape = n_escape
        self.then_spec = then
        self._then = None
        self._done = 0

    def reset(self, seed=None):
        self._done = 0
        if self._then is not None:
            self._then.reset(seed)

    def act(self, game, side):
        assert side == "evader"
        if self._done < self.n_escape and game.burn_cap(side) > 0:
            dv = rsw_to_eci_dv(game, side, self.dir * game.burn_cap(side))
            for _ in range(6):
                if orbit_survives(game, side, dv):
                    self._done += 1
                    return dv
                dv = dv * 0.5
            self._done = self.n_escape
        if self._then is None:
            from agents import make_agent
            self._then = make_agent(self.then_spec)
        return self._then.act(game, side)


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
        doomed = not orbit_survives(game, side, np.zeros(3))
        for k, dv_rsw in enumerate(cands):
            dv = rsw_to_eci_dv(game, side, dv_rsw)
            if (k > 0 or doomed) and not orbit_survives(game, side, dv):
                continue                      # 推完會在比賽結束前再入：直接淘汰
            g = game.clone()
            g.play_turn(dv)
            s = self._score(g, float(np.linalg.norm(dv_rsw)))
            if s > best[0]:
                best = (s, dv)
        if best[0] == -math.inf and doomed:
            rb = rescue_burn(game, side)
            return rb if rb is not None else np.zeros(3)
        return best[1]
