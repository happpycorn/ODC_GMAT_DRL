# Tournament f29v2_adv_cover

- **rules**: final_ranges
- **scenario**: final_adv_cover
- **games per pairing**: 40
- **seed**: 0

## 追者勝率（捕獲 + 躲者撞地；同時出手賽制另含 sma_out），列 = 追者、欄 = 躲者

| 追者 \ 躲者 | safe_evader | heuristic_evader | 平均 |
|---|---|---|---|
| capture_pursuer | 0% [-0–9] | 38% [24–53] | 19% |
| lambert_pursuer | 0% [-0–9] | 32% [20–48] | 16% |
| **躲者平均存活** | 100% | 65% | |

## 細節

| 追者 | 躲者 | n | 結局 | 最近距離中位數 km | 燃料 P / E (m/s) | 決策 ms P / E |
|---|---|---|---|---|---|---|
| capture_pursuer | safe_evader | 40 | escape:40 | 180.9 | 1342 / 1079 | 301.2 / 690.9 |
| capture_pursuer | heuristic_evader | 40 | capture:8, escape:25, sma_out:7 | 248.3 | 1238 / 1069 | 297.2 / 0.3 |
| lambert_pursuer | safe_evader | 40 | escape:40 | 255.8 | 1180 / 1050 | 157.9 / 700.9 |
| lambert_pursuer | heuristic_evader | 40 | capture:2, escape:27, sma_out:11 | 297.8 | 1093 / 1150 | 217.0 / 0.5 |
