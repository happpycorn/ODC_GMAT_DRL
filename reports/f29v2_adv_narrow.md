# Tournament f29v2_adv_narrow

- **rules**: final_ranges
- **scenario**: final_adv_narrow
- **games per pairing**: 40
- **seed**: 0

## 追者勝率（捕獲 + 躲者撞地；同時出手賽制另含 sma_out），列 = 追者、欄 = 躲者

| 追者 \ 躲者 | safe_evader | heuristic_evader | 平均 |
|---|---|---|---|
| capture_pursuer | 0% [-0–9] | 52% [37–67] | 26% |
| lambert_pursuer | 0% [-0–9] | 32% [20–48] | 16% |
| **躲者平均存活** | 100% | 57% | |

## 細節

| 追者 | 躲者 | n | 結局 | 最近距離中位數 km | 燃料 P / E (m/s) | 決策 ms P / E |
|---|---|---|---|---|---|---|
| capture_pursuer | safe_evader | 40 | escape:40 | 276.7 | 1345 / 965 | 292.6 / 697.1 |
| capture_pursuer | heuristic_evader | 40 | capture:10, escape:19, sma_out:11 | 118.1 | 1182 / 1009 | 285.9 / 0.4 |
| lambert_pursuer | safe_evader | 40 | escape:40 | 254.6 | 1151 / 997 | 383.5 / 701.5 |
| lambert_pursuer | heuristic_evader | 40 | escape:27, sma_out:13 | 300.8 | 1011 / 1160 | 44.6 / 0.6 |
