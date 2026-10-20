"""agents/evader_lab.py 的測試（小規模、決定性）。"""
import math

import numpy as np

from agents import make_agent
from agents.evader_lab import LazyEvader, ReserveRolloutEvader, fuelwar_score, inwindow_need
from game.core import Game
from game.rules import Rules

RANKING = Rules(max_dv_pursuer_mps=250.0, max_dv_evader_mps=250.0, fuel_pursuer_mps=3000.0,
                fuel_evader_mps=3000.0, t_max_sec=3600.0)
NEAR_P = {"sma": 6978.0, "ecc": 0.0, "inc": 51.6, "raan": 10.0, "aop": 0.0, "ta": 0.0}
FAR_E = {"sma": 7010.0, "ecc": 0.001, "inc": 51.8, "raan": 10.3, "aop": 0.0, "ta": 4.0}      # ~500 km
CLOSE_E = {"sma": 6980.0, "ecc": 0.0, "inc": 51.6, "raan": 10.0, "aop": 0.0, "ta": 0.25}     # ~30 km


def _evader_turn(rules, p, e):
    g = Game.from_elements(rules, p, e)
    g.play_turn(np.zeros(3))              # 追者先手：不推，輪到躲者
    return g


def test_inwindow_need_close_vs_far():
    assert inwindow_need(_evader_turn(RANKING, NEAR_P, CLOSE_E)) < 250.0
    assert inwindow_need(_evader_turn(RANKING, NEAR_P, FAR_E)) > 1000.0


def test_lazy_evader_coasts_when_safe_and_dodges_when_threatened():
    lazy = LazyEvader()
    g_far = _evader_turn(RANKING, NEAR_P, FAR_E)
    assert not lazy.threatened(g_far)
    assert np.allclose(lazy.act(g_far, "evader"), 0.0)
    g_close = _evader_turn(RANKING, NEAR_P, CLOSE_E)
    assert lazy.threatened(g_close)
    dv = lazy.act(g_close, "evader")
    assert 0.0 < np.linalg.norm(dv) <= 250.0 + 1e-6


def test_fuelwar_score_prefers_win_fuel_and_margin():
    g = Game.from_elements(RANKING, NEAR_P, FAR_E)
    win = g.clone()
    win.outcome = "timeout"
    win.min_dist = 50.0
    rich = win.clone()
    rich.used = {"pursuer": 2000.0, "evader": 0.0}
    poor = win.clone()
    poor.used = {"pursuer": 2000.0, "evader": 2000.0}
    lose = g.clone()
    lose.outcome = "capture"
    assert fuelwar_score(rich, "evader") > fuelwar_score(poor, "evader") > fuelwar_score(lose, "evader")
    near = rich.clone()
    near.min_dist = 6.0
    assert fuelwar_score(rich, "evader") > fuelwar_score(near, "evader")


def test_reserve_rollout_evader_legal_and_registered():
    a = make_agent("py:agents.evader_lab:ReserveRolloutEvader")
    assert isinstance(a, ReserveRolloutEvader)
    g = _evader_turn(RANKING.with_(t_max_sec=1800.0), NEAR_P, CLOSE_E)
    cands = a._candidates(g)
    assert np.allclose(cands[0], 0.0) and len(cands) >= 3
    dv = a.act(g, "evader")
    assert np.all(np.isfinite(dv)) and np.linalg.norm(dv) <= 250.0 + 1e-6
    # 整局推演到結束（短 T_max），燃料帳合法
    P = make_agent("lambert_pursuer_fast")
    while not g.done:
        g.play_turn((P if g.mover == "pursuer" else a).act(g, g.mover))
    assert g.used["evader"] <= 3000.0 + 1e-6 and math.isfinite(g.min_dist)
