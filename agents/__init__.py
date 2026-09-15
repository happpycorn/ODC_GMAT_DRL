"""Agent 註冊表：用字串 / dict / 物件 / callable 指定 agent。

    make_agent("coast")
    make_agent({"name": "lambert_pursuer", "time_weight_mps": 30})
    make_agent("sb3:runs/xxx/pursuer_final.zip")      # 訓練好的 RL 策略（見 agents/rl.py）
"""
from agents.base import Agent, CallableAgent, CoastAgent, RandomAgent
from agents.analytic import DvEvader, LambertPursuer

REGISTRY = {
    "coast": CoastAgent,
    "random": RandomAgent,
    "lambert_pursuer": LambertPursuer,
    "dv_evader": DvEvader,
    "dv_evader_fast": lambda **kw: DvEvader(directions="axes", mags=(1.0,), **kw),
}


def make_agent(spec) -> Agent:
    if isinstance(spec, Agent):
        return spec
    if isinstance(spec, str):
        if spec.startswith("sb3:"):
            from agents.rl import SB3Agent
            return SB3Agent.load(spec[4:])
        if spec not in REGISTRY:
            raise KeyError(f"未知 agent {spec!r}，可用：{sorted(REGISTRY)} 或 'sb3:<path>'")
        a = REGISTRY[spec]()
        a.name = spec
        return a
    if isinstance(spec, dict):
        kw = dict(spec)
        name = kw.pop("name")
        if name == "sb3":
            from agents.rl import SB3Agent
            return SB3Agent.load(**kw)
        return REGISTRY[name](**kw)
    if callable(spec):
        return CallableAgent(spec)
    raise TypeError(f"無法把 {spec!r} 變成 agent")


__all__ = ["Agent", "CoastAgent", "RandomAgent", "CallableAgent", "LambertPursuer", "DvEvader",
           "make_agent", "REGISTRY"]
