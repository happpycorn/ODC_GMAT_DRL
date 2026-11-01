# Tournament f29_adv_cross

- **rules**: final_ranges
- **scenario**: final_adv_cross
- **games per pairing**: 40
- **seed**: 0

## 追者勝率（捕獲 + 躲者撞地；同時出手賽制另含 sma_out），列 = 追者、欄 = 躲者

| 追者 \ 躲者 | safe_evader | heuristic_evader | 平均 |
|---|---|---|---|
| capture_pursuer | 0% [-0–9] | 42% [29–58] | 21% |
| lambert_pursuer | 0% [-0–9] | 22% [12–38] | 11% |
| **躲者平均存活** | 100% | 68% | |

## 細節

| 追者 | 躲者 | n | 結局 | 最近距離中位數 km | 燃料 P / E (m/s) | 決策 ms P / E |
|---|---|---|---|---|---|---|
| capture_pursuer | safe_evader | 40 | escape:40 | 220.2 | 1354 / 1158 | 268.2 / 612.2 |
| capture_pursuer | heuristic_evader | 40 | capture:7, escape:23, sma_out:10 | 205.1 | 1278 / 1145 | 269.7 / 0.3 |
| lambert_pursuer | safe_evader | 40 | escape:40 | 401.1 | 1211 / 1164 | 102.7 / 620.8 |
| lambert_pursuer | heuristic_evader | 40 | escape:31, sma_out:9 | 414.4 | 1101 / 1196 | 235.8 / 0.5 |
