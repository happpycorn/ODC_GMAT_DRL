"""把訓練好的 stable-baselines3 策略包成 Agent（評測 / self-play 對手 / copilot 共用）。

模型存成 `xxx.zip`，旁邊放 `xxx.json` 描述觀測與 action 設定：
    {"algo": "PPO", "role": "pursuer", "action_power": 1.0, "use_intercept_obs": true}
"""
import json
import os

import numpy as np

from agents.base import Agent
from game.actions import action_to_dv
from game.obs import build_obs

_MODEL_CACHE = {}


def _load_model(path, algo, device):
    key = (os.path.abspath(path), algo, device)
    if key not in _MODEL_CACHE:
        import torch
        torch.set_num_threads(1)
        from stable_baselines3 import PPO, SAC
        cls = {"PPO": PPO, "SAC": SAC}[algo]
        _MODEL_CACHE[key] = cls.load(path, device=device)
    return _MODEL_CACHE[key]


def read_meta(path):
    meta_path = os.path.splitext(path)[0] + ".json"
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            return json.load(f)
    return {}


def write_meta(path, meta):
    with open(os.path.splitext(path)[0] + ".json", "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


class SB3Agent(Agent):
    def __init__(self, model, action_power=1.0, use_intercept_obs=True, deterministic=True, name="sb3"):
        self.model = model
        self.action_power = action_power
        self.use_intercept_obs = use_intercept_obs
        self.deterministic = deterministic
        self.name = name

    @classmethod
    def load(cls, path, device="cpu", deterministic=True):
        meta = read_meta(path)
        model = _load_model(path, meta.get("algo", "PPO"), device)
        name = "sb3:" + os.path.relpath(path)
        return cls(model, meta.get("action_power", 1.0), meta.get("use_intercept_obs", True),
                   deterministic, name)

    def act(self, game, side):
        obs = build_obs(game, side, use_intercept=self.use_intercept_obs)
        a, _ = self.model.predict(obs, deterministic=self.deterministic)
        return action_to_dv(game, side, np.asarray(a).reshape(3), self.action_power)
