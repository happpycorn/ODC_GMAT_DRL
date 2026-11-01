# Tournament f29_adv_close

- **rules**: final_ranges
- **scenario**: final_adv_close
- **games per pairing**: 40
- **seed**: 0

## 追者勝率（捕獲 + 躲者撞地；同時出手賽制另含 sma_out），列 = 追者、欄 = 躲者

| 追者 \ 躲者 | safe_evader | heuristic_evader | 平均 |
|---|---|---|---|
| capture_pursuer | 0% [-0–9] | 62% [47–76] | 31% |
| lambert_pursuer | 0% [-0–9] | 38% [24–53] | 19% |
| **躲者平均存活** | 100% | 50% | |

## 細節

| 追者 | 躲者 | n | 結局 | 最近距離中位數 km | 燃料 P / E (m/s) | 決策 ms P / E |
|---|---|---|---|---|---|---|
| capture_pursuer | safe_evader | 40 | escape:40 | 46.5 | 1206 / 1167 | 252.7 / 590.0 |
| capture_pursuer | heuristic_evader | 40 | capture:20, escape:15, sma_out:5 | 14.7 | 686 / 686 | 261.6 / 0.2 |
| lambert_pursuer | safe_evader | 40 | escape:40 | 49.0 | 930 / 1170 | 260.4 / 591.7 |
| lambert_pursuer | heuristic_evader | 40 | capture:9, escape:25, sma_out:6 | 32.9 | 601 / 1015 | 260.6 / 0.4 |
