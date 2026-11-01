# Tournament f29_adv_narrow

- **rules**: final_ranges
- **scenario**: final_adv_narrow
- **games per pairing**: 40
- **seed**: 0

## 追者勝率（捕獲 + 躲者撞地；同時出手賽制另含 sma_out），列 = 追者、欄 = 躲者

| 追者 \ 躲者 | safe_evader | heuristic_evader | 平均 |
|---|---|---|---|
| capture_pursuer | 2% [0–13] | 52% [37–67] | 28% |
| lambert_pursuer | 2% [0–13] | 32% [20–48] | 18% |
| **躲者平均存活** | 98% | 57% | |

## 細節

| 追者 | 躲者 | n | 結局 | 最近距離中位數 km | 燃料 P / E (m/s) | 決策 ms P / E |
|---|---|---|---|---|---|---|
| capture_pursuer | safe_evader | 40 | escape:39, sma_out:1 | 297.6 | 1325 / 1147 | 227.7 / 555.8 |
| capture_pursuer | heuristic_evader | 40 | capture:10, escape:19, sma_out:11 | 118.7 | 1183 / 1009 | 232.7 / 0.3 |
| lambert_pursuer | safe_evader | 40 | escape:39, sma_out:1 | 285.7 | 1194 / 1144 | 276.4 / 562.0 |
| lambert_pursuer | heuristic_evader | 40 | escape:27, sma_out:13 | 300.8 | 1011 / 1160 | 24.9 / 0.5 |
