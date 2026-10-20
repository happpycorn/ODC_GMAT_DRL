# 規則敏感度地圖：250 m/s 級規則、rollout 大腦（清單第 3 項）

## 1. 問題
規則公布當天要在幾分鐘內知道「這組規則誰有利、哪個大腦最好」。E8 的平衡地圖是解析大腦（Lambert vs DvEvader）
在 1500 m/s 級規則量的；E14–E17 顯示 250 m/s 級規則下結論會翻。這裡在 `ranking_like.json`（雙方 250/3000、
窗口 300 s、半徑 5 km、T_max 4 週期、追者先手、1 發/回合、J2）附近逐軸改一個欄位（加幾個兩軸交叉），用 rollout
大腦量追者勝率，跟基底格逐局配對，做成當天查表（`tools/rule_lookup.py`）。

## 2. 改了什麼（沒有改任何既有程式）
- `tools/rule_map.py`（新）：格子 = 相對基底的改動；每局一結束就 append 到 `reports/<name>.jsonl`，中斷後同指令重跑會續跑；
  報表 `reports/<name>.md`（勝率、跟基底逐局配對、大腦選擇、建議）；`export` 合併成 `configs/rule_map.json`。
- `tools/rule_lookup.py`（新）：`uv run python tools/rule_lookup.py configs/rules_final.json` → 最接近的格子、預期勝率、
  建議大腦、各軸單獨效果、**超出地圖範圍的欄位**（數值欄位超出測過的最小～最大、類別值沒測過、燃料發數/燃料比超出）。
- `game/rule_presets.py`（新）：`RankingRuleRanges`（`RuleRanges` 子類別，多抽 `burns_per_turn`）。`game/rules.py` 沒動。
- `tests/test_rule_map.py`（新，12 項）：含 `RuleRanges().sample` 抽樣值與亂數消耗跟改前逐位元相同。

## 3. 設定
- 每格 24 局、mixed 幾何、seed 1（**跟 E15–E17 同一批幾何**；基底格 rollout vs rollout 7/24，跟 E17 完全一樣）、5 worker、nice 10。
- 配對（都是同一批幾何）：**rr** = `rollout_pursuer` vs `rollout_evader`；**strong** = 強化版 rollout 追者（E16 規格）vs
  `rollout_evader`；**escape** = `rollout_pursuer` vs `escape_evader`；**lambert** = `lambert_pursuer` vs `rollout_evader`（對照，見 4.1）。
- 「vs 基底」= 同一局在本格與基底格的結果配對：+只有本格追者贏 / −只有基底追者贏，p = 雙尾精確符號檢定。
  幾十個檢定裡約 5% 會是偽陽性；+0/−7 這種格子 p 最小只到 0.016。
- 跑的 commit：`aa7d605`（第一批）、`4882cb3`（之後）。都**早於**另一個任務對多發存活檢查（agents/analytic.py）的修改，合併後多發格要重跑。
```bash
uv run python tools/rule_map.py run --base configs/rulesets/ranking_like.json --name rmap_ranking \
    --group burns --group fuel --group window --pairs fast --games 24 --seed 1 --workers 5
uv run python tools/rule_map.py run --base configs/rulesets/ranking_like.json --name rmap_ranking --pairs strong --group ...
uv run python tools/rule_map.py export --name rmap_ranking --name rmap_symmetric --name rmap_ranges --out configs/rule_map.json
```

## 4. 結果

### 4.1 關鍵軸（ranking_like 基底，`reports/rmap_ranking.md`）

追者勝率 [95% 區間]，n = 24/格；粗體 = 跟基底逐局配對 p < 0.05。

| 軸 | 值 | rr | rr vs 基底 | escape（逃逸躲者被抓） | escape vs 基底 |
|---|---|---|---|---|---|
| 基底 | 250/3000、300 s、1 發 | 29% [15–49] | — | 100% [86–100] | — |
| 一回合發數 | 2 | 83% [64–93] | **+14/−1 p=0.001** | 100% | +0/−0 |
| | 3 | 75% [55–88] | **+12/−1 p=0.003** | 96% | +0/−1 |
| 燃料 追/躲 | 3000/1500 | 100% [86–100] | **+17/−0 p<0.001** | 100% | +0/−0 |
| | 1500/3000 | 0% [0–14] | **+0/−7 p=0.016** | 75% [55–88] | **+0/−6 p=0.031** |
| | 4500/3000 | 46% [28–65] | +9/−5 p=0.42（看不出） | 100% | +0/−0 |
| | 3000/4500 | 0% [0–14] | **+0/−7 p=0.016** | 17% [7–36] | **+0/−20 p<0.001** |
| 窗口 | 120 s | 83% [64–93] | **+13/−0 p<0.001** | 88% [69–96] | +0/−3 p=0.25 |
| | 600 s | 0% [0–14] | **+0/−7 p=0.016** | 75% [55–88] | **+0/−6 p=0.031** |
| | 900 s | 0% [0–14] | **+0/−7 p=0.016** | 0% [0–14] | **+0/−24 p<0.001** |

- **窗口是 250 m/s 規則下最大的軸之一**（E8 的 1500 m/s 解析地圖窗口幾乎是平的）：120 s → 追者 83%，600/900 s → 0%。
- 多發（2–3 發）大幅利於追者（重現 E17）；**躲者燃料**多一半或追者燃料少一半 → 追者 0%；追者燃料多一半只到 46%，看不出差異。
- 逃逸躲者在基底最弱（100% 被抓），但**窗口 900 s 時 24/24 存活**、躲者燃料 4500 時只被抓 17%——長窗口/躲者油多時逃逸又變好用。
- ⚠ 窗口 600/900 s 的 0% 要小心解讀：rollout 追者平均只用了 405–470 m/s（共 3000），是 E12 那種「推演判斷全輸就不追」。
  所以加了 lambert 對照（Lambert 追者每回合都追）——結果見下面更新。

（其餘軸、交叉、strong、第二組規則、規則分布：跑完後補）
