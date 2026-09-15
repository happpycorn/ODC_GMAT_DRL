"""Rollout 規劃器：候選脈衝 × 對手模型集合，逐一推演到比賽結束，挑「最壞情況最好」的一發。

跟 2-ply 極小極大（agents/search.py）的差別：葉節點不用啟發式值（短 horizon 追擊所需 Δv
會飽和/太悲觀，實測比單層 LambertPursuer 還弱），而是**真的下完整場**——對手用多個模型
（解析/RL），我方後續交給 continuation 策略。成本 = 候選數 × 對手模型數 × 一場推演，
適合 copilot 與小規模評測（每步數百 ms ~ 數秒），不適合當訓練對手。

分數（我方視角，越大越好）：
  贏：1000 + 追者早抓到/剩油多、躲者剩油多且距離大 的小獎勵
  輸：追者看最近距離（越近越好）、躲者看撐多久（越久越好）
"""
import math

import numpy as np

from agents.base import Agent, rsw_to_eci_dv


def outcome_score(h, side):
    s = h.summary()
    R = h.rules
    if h.winner == side:
        if side == "pursuer":
            return 1000.0 + 100.0 * (1.0 - s["t_end"] / h.t_max) + 50.0 * h.fuel_left("pursuer") / max(R.fuel_pursuer_mps, 1)
        return 1000.0 + 50.0 * h.fuel_left("evader") / max(R.fuel_evader_mps, 1) + min(s["final_dist_km"], 1e4) / 100.0
    if side == "pursuer":
        return -min(s["min_dist_km"], 1e5) / 10.0
    return 500.0 * s["t_end"] / h.t_max


class RolloutPlanner(Agent):
    def __init__(self, side, candidates=None, opponents=None, continuation=None, aggregate="min",
                 extra_rsw_fracs=(), name=None):
        from agents import make_agent
        self.side = side
        defaults = {
            "pursuer": dict(
                candidates=[{"name": "lambert_pursuer", "time_weight_mps": w} for w in (0.0, 10.0, 60.0, 300.0)],
                opponents=["coast", "dv_evader_fast"], continuation="lambert_pursuer_fast"),
            "evader": dict(
                candidates=["dv_evader", "dv_evader_fast"],
                opponents=["lambert_pursuer_fast", {"name": "lambert_pursuer_fast", "time_weight_mps": 60.0}],
                continuation="dv_evader_fast"),
        }[side]
        self.cand_agents = [make_agent(c) for c in (candidates or defaults["candidates"])]
        self.opp_agents = [make_agent(o) for o in (opponents or defaults["opponents"])]
        self.cont = make_agent(continuation or defaults["continuation"])
        self.aggregate = aggregate
        self.extra_rsw_fracs = tuple(extra_rsw_fracs)   # 額外候選：沿 ±S、+R 推這些比例的上限
        self.name = name or f"rollout_{side}"

    def _candidates(self, game):
        cands = [np.zeros(3)]
        for a in self.cand_agents:
            cands.append(game.clip_dv(self.side, a.act(game, self.side)))
        cap = game.burn_cap(self.side)
        for frac in self.extra_rsw_fracs:
            for d in ((0, 1, 0), (0, -1, 0), (1, 0, 0)):
                cands.append(rsw_to_eci_dv(game, self.side, np.array(d, dtype=float) * frac * cap))
        out = []
        for c in cands:
            if all(np.linalg.norm(c - o) > 0.5 for o in out):
                out.append(c)
        return out

    def act(self, game, side):
        assert side == self.side
        best_s, best_dv = -math.inf, np.zeros(3)
        for dv in self._candidates(game):
            scores = []
            for opp in self.opp_agents:
                opp.reset(seed=0)
                h = game.clone()
                h.play_turn(dv)
                while not h.done:
                    a = self.cont if h.mover == side else opp
                    h.play_turn(a.act(h, h.mover))
                scores.append(outcome_score(h, side))
            s = min(scores) if self.aggregate == "min" else float(np.mean(scores))
            if s > best_s:
                best_s, best_dv = s, dv
        return best_dv
