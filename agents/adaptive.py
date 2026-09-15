"""依規則選打法的躲者（HAP-108 收穫）。

實測（reports/hap108_escape_evader_*.md，16 局）：
  * 燃料對稱（躲者/追者燃料比 = 1）：純 EscapeEvader 存活 88%，rollout 躲者只有 72%
  * 追者燃料 2×（比 = 0.5）：EscapeEvader 只剩 12%，rollout 躲者 31%
  * 把 escape 加進 rollout 躲者的候選集沒用——它的對手模型是較弱的 Lambert 系追者，
    推演裡「省油也能贏」，於是永遠不選燒光燃料的逃逸

所以開局看一次規則：躲者燃料 / 追者燃料 >= threshold → 整場用逃逸打法；否則用 rollout 躲者。
threshold 預設 0.75（兩個實測點中間），在隨機規則分布上驗證（reports/hap108_adaptive_*.md）。
"""
from agents.base import Agent


class AdaptiveEvader(Agent):
    name = "adaptive_evader"

    def __init__(self, threshold=0.75, escape="escape_evader", default="rollout_evader"):
        from agents import make_agent
        self.threshold = float(threshold)
        self.escape = make_agent(escape)
        self.default = make_agent(default)
        self._pick = None
        self._pick_key = None

    def reset(self, seed=None):
        self._pick = None
        self._pick_key = None
        self.escape.reset(seed)
        self.default.reset(seed)

    def choose(self, rules):
        ratio = rules.fuel_evader_mps / max(rules.fuel_pursuer_mps, 1e-9)
        return self.escape if ratio >= self.threshold else self.default

    def act(self, game, side):
        assert side == "evader"
        key = id(game.rules)
        if self._pick is None or self._pick_key != key:     # 每局（每組規則）決定一次
            self._pick = self.choose(game.rules)
            self._pick_key = key
        return self._pick.act(game, side)
