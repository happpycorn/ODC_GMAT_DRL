# Tournament f29v2_adv_far

- **rules**: final_ranges
- **scenario**: final_adv_far
- **games per pairing**: 40
- **seed**: 0

## 追者勝率（捕獲 + 躲者撞地；同時出手賽制另含 sma_out），列 = 追者、欄 = 躲者

| 追者 \ 躲者 | safe_evader | heuristic_evader | 平均 |
|---|---|---|---|
| capture_pursuer | 0% [-0–9] | 57% [42–71] | 29% |
| lambert_pursuer | 0% [-0–9] | 50% [35–65] | 25% |
| **躲者平均存活** | 100% | 46% | |

## 細節

| 追者 | 躲者 | n | 結局 | 最近距離中位數 km | 燃料 P / E (m/s) | 決策 ms P / E |
|---|---|---|---|---|---|---|
| capture_pursuer | safe_evader | 40 | escape:40 | 322.3 | 1272 / 1247 | 294.6 / 672.3 |
| capture_pursuer | heuristic_evader | 40 | capture:10, escape:17, sma_out:13 | 182.5 | 1158 / 1120 | 283.3 / 0.3 |
| lambert_pursuer | safe_evader | 40 | escape:40 | 718.7 | 1355 / 1229 | 29.5 / 678.7 |
| lambert_pursuer | heuristic_evader | 40 | capture:1, escape:20, sma_out:19 | 575.7 | 1180 / 1235 | 222.6 / 0.5 |
