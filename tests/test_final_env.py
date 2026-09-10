"""GmatFinalEnv 煙霧測試（HAP-53 驗收）。

不需要 pytest，直接跑就會印結果：
    uv run python tests/test_final_env.py
守的是：check_env 合規（兩種角色）、回合交替、勝負分支（捕獲/超時/撞地）。
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from envs.final_env import GmatFinalEnv
from stable_baselines3.common.env_checker import check_env


def test_check_env_both_roles():
    for role in ("pursuer", "evader"):
        check_env(GmatFinalEnv(config={"role": role}), warn=True)
    print("[OK] check_env 兩種角色皆通過")


def test_capture_branch():
    env = GmatFinalEnv(config={"role": "pursuer"})
    env.reset(seed=0)
    env.re = env.rp + np.array([3.0, 0.0, 0.0])          # 相距 3km < 5km 捕獲半徑
    assert env._check_terminal() == "capture"
    assert env._agent_won() is True
    print("[OK] 捕獲分支：追者判贏")


def test_timeout_branch():
    env_p = GmatFinalEnv(config={"role": "pursuer"}); env_p.reset(seed=0)
    env_p.re = env_p.rp + np.array([1000.0, 0.0, 0.0]); env_p.elapsed = env_p.t_max + 1.0
    assert env_p._check_terminal() == "timeout" and env_p._agent_won() is False

    env_e = GmatFinalEnv(config={"role": "evader"}); env_e.reset(seed=0)
    env_e.re = env_e.rp + np.array([1000.0, 0.0, 0.0]); env_e.elapsed = env_e.t_max + 1.0
    env_e._check_terminal()
    assert env_e._agent_won() is True
    print("[OK] 超時分支：追者輸 / 躲者贏")


def test_crash_branch():
    env = GmatFinalEnv(config={"role": "pursuer"})
    env.reset(seed=0)
    env.rp = env.rp / np.linalg.norm(env.rp) * 6000.0     # 拉到地表以下（RE≈6378）
    env._coast(1.0)
    assert env._check_terminal() == "crash_pursuer"
    print("[OK] 撞地分支")


def test_alternation():
    env = GmatFinalEnv(config={"role": "pursuer", "opponent_policy": "naive_evader"})
    env.reset(seed=1)
    used_e_before = env.used_e
    env.step(np.zeros(3))                                  # 我方不動
    assert env.used_e > used_e_before, "對手窗口沒被執行——交替失效"
    print("[OK] 回合交替：對手窗口確實被執行")


def test_random_episode_runs():
    rng = np.random.default_rng(0)
    for role in ("pursuer", "evader"):
        env = GmatFinalEnv(config={"role": role,
                                   "opponent_policy": lambda o: rng.uniform(-1, 1, 3).astype(np.float32)})
        obs, _ = env.reset(seed=0)
        done = False
        while not done:
            obs, r, term, trunc, info = env.step(env.action_space.sample())
            assert env.observation_space.contains(obs) and np.isfinite(r)
            done = term or trunc
        assert info["outcome"] is not None
    print("[OK] 隨機對打：兩種角色都能跑完整 episode 並判定結局")


if __name__ == "__main__":
    test_check_env_both_roles()
    test_capture_branch()
    test_timeout_branch()
    test_crash_branch()
    test_alternation()
    test_random_episode_runs()
    print("\nALL TESTS PASSED")
