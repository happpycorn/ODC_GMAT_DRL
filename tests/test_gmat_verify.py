"""GMAT 重播一致性（HAP-56）。沒裝 GmatConsole 的機器自動略過。"""
import os

import numpy as np
import pytest

from tools.gmat_verify import GMAT_CONSOLE, game_to_script, verify_game

pytestmark = pytest.mark.skipif(not os.path.exists(GMAT_CONSOLE), reason="GmatConsole 不在這台機器上")


def _short_game(gravity_degree):
    from agents import make_agent
    from game.core import Game
    from game.rules import Rules
    R = Rules(window_sec=400.0, t_max_sec=4000.0, max_dv_pursuer_mps=300.0, max_dv_evader_mps=150.0,
              fuel_pursuer_mps=1200.0, fuel_evader_mps=600.0, gravity_degree=gravity_degree)
    p = {"sma": 6978.0, "ecc": 0.001, "inc": 51.6, "raan": 10.0, "aop": 30.0, "ta": 0.0}
    e = {"sma": 7030.0, "ecc": 0.002, "inc": 52.0, "raan": 10.5, "aop": 40.0, "ta": 350.0}
    g = Game.from_elements(R, p, e)
    P, E = make_agent("lambert_pursuer"), make_agent({"name": "random", "seed": 3, "p_burn": 1.0})
    while not g.done:
        g.play_turn((P if g.mover == "pursuer" else E).act(g, g.mover))
    return g


def test_script_is_ascii():
    g = _short_game(2)
    game_to_script(g, "/tmp/x.txt").encode("ascii")


@pytest.mark.parametrize("deg", [0, 2, 4])
def test_gmat_replay_matches_physics(deg):
    g = _short_game(deg)
    out = verify_game(g)
    assert out["max_dt_sec"] < 1e-3
    # 4000 s 內多次脈衝：兩邊位置差應在 10 m 以內（捕獲半徑的 1/500）
    assert out["max_dpos_km"] < 0.01, out["per_turn"]
