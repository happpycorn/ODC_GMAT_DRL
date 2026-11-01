# Tournament f29_e28_regress

- **rules**: final_ranges
- **scenario**: final
- **games per pairing**: 120
- **seed**: 0

## 追者勝率（捕獲 + 躲者撞地；同時出手賽制另含 sma_out），列 = 追者、欄 = 躲者

| 追者 \ 躲者 | safe_evader | dv_evader | heuristic_evader | 平均 |
|---|---|---|---|---|
| capture_pursuer | 0% [-0–3] | 99% [95–100] | 44% [36–53] | 48% |
| lambert_pursuer | 0% [-0–3] | 100% [97–100] | 30% [23–39] | 43% |
| **躲者平均存活** | 100% | 0% | 63% | |

## 細節

| 追者 | 躲者 | n | 結局 | 最近距離中位數 km | 燃料 P / E (m/s) | 決策 ms P / E |
|---|---|---|---|---|---|---|
| capture_pursuer | safe_evader | 120 | escape:120 | 187.3 | 1329 / 1110 | 290.1 / 721.2 |
| capture_pursuer | dv_evader | 120 | capture:104, escape:1, sma_out:15 | 0.1 | 525 / 13 | 293.8 / 95.3 |
| capture_pursuer | heuristic_evader | 120 | capture:34, escape:67, sma_out:19 | 97.5 | 1086 / 972 | 284.0 / 0.3 |
| lambert_pursuer | safe_evader | 120 | escape:120 | 256.4 | 1118 / 1105 | 84.5 / 724.1 |
| lambert_pursuer | dv_evader | 120 | capture:97, sma_out:23 | 5.1 | 46 / 78 | 76.8 / 71.6 |
| lambert_pursuer | heuristic_evader | 120 | capture:4, escape:84, sma_out:32 | 177.2 | 907 / 1168 | 73.8 / 0.3 |
