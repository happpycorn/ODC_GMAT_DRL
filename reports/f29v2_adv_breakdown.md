# 決賽評測分桶報表

來源：reports/f29v2_adv_close.jsonl、reports/f29v2_adv_cover.jsonl、reports/f29v2_adv_cross.jsonl、reports/f29v2_adv_far.jsonl、reports/f29v2_adv_narrow.jsonl、reports/f29v2_adv_taiwan.jsonl

共 960 局、4 個配對。

## 配對總覽

| 追方 | 躲方 | 局數 | 躲方勝率 | Wilson 95% 區間 | 結局分布 |
|---|---|---:|---:|---:|---|
| capture_pursuer | heuristic_evader | 240 | 53% (128/240) | 47.0–59.5% | capture: 56、escape: 128、sma_out: 56 |
| capture_pursuer | safe_evader | 240 | 100% (240/240) | 98.4–100.0% | escape: 240 |
| lambert_pursuer | heuristic_evader | 240 | 65% (156/240) | 58.8–70.8% | capture: 14、escape: 156、sma_out: 70 |
| lambert_pursuer | safe_evader | 240 | 100% (239/240) | 97.7–99.9% | escape: 239、sma_out: 1 |

## 躲方勝率分桶

τ* = 1000 × R_cap（km）/ ΔV_lim（m/s）；初始距離比例 = 1000 × 初始距離（km） / [ΔV_lim（m/s）× T_round（秒）]。每桶顯示勝率（勝局數/局數）。

### ΔV_lim（m/s）

| 追方 | 躲方 | 100–200 | 200–350 | 350–500 |
|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 53% (54/102) | 54% (52/96) | 52% (22/42) |
| capture_pursuer | safe_evader | 100% (102/102) | 100% (96/96) | 100% (42/42) |
| lambert_pursuer | heuristic_evader | 63% (64/102) | 69% (66/96) | 62% (26/42) |
| lambert_pursuer | safe_evader | 100% (102/102) | 100% (96/96) | 98% (41/42) |

### R_cap（km）

| 追方 | 躲方 | 1–3 | 3–8 | 8–20 |
|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 56% (60/108) | 53% (38/72) | 50% (30/60) |
| capture_pursuer | safe_evader | 100% (108/108) | 100% (72/72) | 100% (60/60) |
| lambert_pursuer | heuristic_evader | 72% (78/108) | 57% (41/72) | 62% (37/60) |
| lambert_pursuer | safe_evader | 100% (108/108) | 100% (72/72) | 98% (59/60) |

### T_round（秒）

| 追方 | 躲方 | 600–1200 | 1200–2400 | 2400–3600 |
|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 56% (57/102) | 53% (51/96) | 48% (20/42) |
| capture_pursuer | safe_evader | 100% (102/102) | 100% (96/96) | 100% (42/42) |
| lambert_pursuer | heuristic_evader | 62% (63/102) | 65% (62/96) | 74% (31/42) |
| lambert_pursuer | safe_evader | 100% (102/102) | 99% (95/96) | 100% (42/42) |

### τ* = R_cap/ΔV_lim（秒）

| 追方 | 躲方 | 0–10 | 10–30 | 30 以上 |
|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 54% (45/84) | 53% (41/78) | 54% (42/78) |
| capture_pursuer | safe_evader | 100% (84/84) | 100% (78/78) | 100% (78/78) |
| lambert_pursuer | heuristic_evader | 70% (59/84) | 63% (49/78) | 62% (48/78) |
| lambert_pursuer | safe_evader | 100% (84/84) | 99% (77/78) | 100% (78/78) |

### 初始距離比例：初始距離 / (ΔV_lim·T_round)

| 追方 | 躲方 | 0–0.5 | 0.5–2 | 2 以上 |
|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 32% (13/41) | 54% (22/41) | 59% (93/158) |
| capture_pursuer | safe_evader | 100% (41/41) | 100% (41/41) | 100% (158/158) |
| lambert_pursuer | heuristic_evader | 63% (26/41) | 66% (27/41) | 65% (103/158) |
| lambert_pursuer | safe_evader | 98% (40/41) | 100% (41/41) | 100% (158/158) |

### 安全空域偏移：|區間中心 − 初始 a| / 一發容量

| 追方 | 躲方 | 0（在區間內） | 0–2 | 2–4 | 4 以上 |
|---|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 37% (16/43) | 65% (55/85) | 52% (29/56) | 50% (28/56) |
| capture_pursuer | safe_evader | 100% (43/43) | 100% (85/85) | 100% (56/56) | 100% (56/56) |
| lambert_pursuer | heuristic_evader | 58% (25/43) | 71% (60/85) | 71% (40/56) | 55% (31/56) |
| lambert_pursuer | safe_evader | 98% (42/43) | 100% (85/85) | 100% (56/56) | 100% (56/56) |

## 安全證書成立比例

有 2880 個躲方決策回合含 certificate 紀錄。

### 依回合

| 追方 | 躲方 | 第 1 回合 | 第 2 回合 | 第 3 回合 | 第 4 回合 | 第 5 回合 | 第 6 回合 |
|---|---|---|---|---|---|---|---|
| capture_pursuer | heuristic_evader | — | — | — | — | — | — |
| capture_pursuer | safe_evader | 100% (239/240) | 100% (240/240) | 100% (240/240) | 100% (240/240) | 100% (240/240) | 100% (240/240) |
| lambert_pursuer | heuristic_evader | — | — | — | — | — | — |
| lambert_pursuer | safe_evader | 100% (239/240) | 100% (240/240) | 100% (240/240) | 100% (240/240) | 100% (239/240) | 98% (236/240) |

### 依規則與題目分桶

#### ΔV_lim（m/s）

| 追方 | 躲方 | 100–200 | 200–350 | 350–500 |
|---|---|---|---|---|
| capture_pursuer | heuristic_evader | — | — | — |
| capture_pursuer | safe_evader | 100% (611/612) | 100% (576/576) | 100% (252/252) |
| lambert_pursuer | heuristic_evader | — | — | — |
| lambert_pursuer | safe_evader | 100% (610/612) | 99% (572/576) | 100% (252/252) |

#### R_cap（km）

| 追方 | 躲方 | 1–3 | 3–8 | 8–20 |
|---|---|---|---|---|
| capture_pursuer | heuristic_evader | — | — | — |
| capture_pursuer | safe_evader | 100% (648/648) | 100% (432/432) | 100% (359/360) |
| lambert_pursuer | heuristic_evader | — | — | — |
| lambert_pursuer | safe_evader | 100% (645/648) | 100% (432/432) | 99% (357/360) |

#### T_round（秒）

| 追方 | 躲方 | 600–1200 | 1200–2400 | 2400–3600 |
|---|---|---|---|---|
| capture_pursuer | heuristic_evader | — | — | — |
| capture_pursuer | safe_evader | 100% (612/612) | 100% (576/576) | 100% (251/252) |
| lambert_pursuer | heuristic_evader | — | — | — |
| lambert_pursuer | safe_evader | 99% (608/612) | 100% (576/576) | 99% (250/252) |

#### τ* = R_cap/ΔV_lim（秒）

| 追方 | 躲方 | 0–10 | 10–30 | 30 以上 |
|---|---|---|---|---|
| capture_pursuer | heuristic_evader | — | — | — |
| capture_pursuer | safe_evader | 100% (504/504) | 100% (468/468) | 100% (467/468) |
| lambert_pursuer | heuristic_evader | — | — | — |
| lambert_pursuer | safe_evader | 100% (502/504) | 100% (467/468) | 99% (465/468) |

#### 初始距離比例：初始距離 / (ΔV_lim·T_round)

| 追方 | 躲方 | 0–0.5 | 0.5–2 | 2 以上 |
|---|---|---|---|---|
| capture_pursuer | heuristic_evader | — | — | — |
| capture_pursuer | safe_evader | 100% (245/246) | 100% (246/246) | 100% (948/948) |
| lambert_pursuer | heuristic_evader | — | — | — |
| lambert_pursuer | safe_evader | 99% (244/246) | 100% (246/246) | 100% (944/948) |

#### 安全空域偏移：|區間中心 − 初始 a| / 一發容量

| 追方 | 躲方 | 0（在區間內） | 0–2 | 2–4 | 4 以上 |
|---|---|---|---|---|---|
| capture_pursuer | heuristic_evader | — | — | — | — |
| capture_pursuer | safe_evader | 100% (257/258) | 100% (510/510) | 100% (336/336) | 100% (336/336) |
| lambert_pursuer | heuristic_evader | — | — | — | — |
| lambert_pursuer | safe_evader | 99% (256/258) | 99% (506/510) | 100% (336/336) | 100% (336/336) |

證書成立的回合被捕獲：0 次。

## 追方命中機率校準

平均 hit_prob 與實際捕獲率均以有 hit_prob 的決策回合為分母；實際捕獲指該回合結束時 outcome 為 capture。

| 追方 | 躲方 | 決策回合 | 平均 hit_prob | 實際捕獲率 |
|---|---|---:|---:|---:|
| capture_pursuer | heuristic_evader | 1273 | 3.7% | 4% (56/1273) |
| capture_pursuer | safe_evader | 1440 | 2.3% | 0% (0/1440) |

## 對抗題目分桶

有 960 局含 scenario_meta。每格依序顯示躲方勝率 / 安全證書成立比例；勝率以局數、證書以有紀錄的躲方決策回合數為分母。

### family（題目家族）

| 追方 | 躲方 | final_adv_close | final_adv_cover | final_adv_cross | final_adv_far | final_adv_narrow | final_adv_taiwan |
|---|---|---|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 38% (15/40) / — | 62% (25/40) / — | 60% (24/40) / — | 42% (17/40) / — | 48% (19/40) / — | 70% (28/40) / — |
| capture_pursuer | safe_evader | 100% (40/40) / 100% (239/240) | 100% (40/40) / 100% (240/240) | 100% (40/40) / 100% (240/240) | 100% (40/40) / 100% (240/240) | 100% (40/40) / 100% (240/240) | 100% (40/40) / 100% (240/240) |
| lambert_pursuer | heuristic_evader | 62% (25/40) / — | 68% (27/40) / — | 78% (31/40) / — | 50% (20/40) / — | 68% (27/40) / — | 65% (26/40) / — |
| lambert_pursuer | safe_evader | 98% (39/40) / 99% (238/240) | 100% (40/40) / 100% (239/240) | 100% (40/40) / 100% (240/240) | 100% (40/40) / 100% (240/240) | 100% (40/40) / 99% (237/240) | 100% (40/40) / 100% (240/240) |

### sub（題目子類）

| 追方 | 躲方 | close_frac | close_km | cover | cross | far | narrow | w002 | w05_10 | 缺資料 |
|---|---|---|---|---|---|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 27% (6/22) / — | 50% (9/18) / — | 20% (1/5) / — | 90% (9/10) / — | 69% (11/16) / — | 78% (7/9) / — | 47% (8/17) / — | 48% (11/23) / — | 55% (66/120) / — |
| capture_pursuer | safe_evader | 100% (22/22) / 100% (132/132) | 100% (18/18) / 99% (107/108) | 100% (5/5) / 100% (30/30) | 100% (10/10) / 100% (60/60) | 100% (16/16) / 100% (96/96) | 100% (9/9) / 100% (54/54) | 100% (17/17) / 100% (102/102) | 100% (23/23) / 100% (138/138) | 100% (120/120) / 100% (720/720) |
| lambert_pursuer | heuristic_evader | 82% (18/22) / — | 39% (7/18) / — | 20% (1/5) / — | 70% (7/10) / — | 69% (11/16) / — | 78% (7/9) / — | 59% (10/17) / — | 74% (17/23) / — | 65% (78/120) / — |
| lambert_pursuer | safe_evader | 95% (21/22) / 100% (132/132) | 100% (18/18) / 98% (106/108) | 100% (5/5) / 100% (30/30) | 100% (10/10) / 100% (60/60) | 100% (16/16) / 100% (96/96) | 100% (9/9) / 100% (54/54) | 100% (17/17) / 98% (100/102) | 100% (23/23) / 99% (137/138) | 100% (120/120) / 100% (719/720) |

### zone_width_da（安全空域寬 / 一發容量）

| 追方 | 躲方 | <0.05 | 0.05–0.1 | 0.1–0.3 | ≥0.3 |
|---|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 47% (8/17) / — | 56% (18/32) / — | — | 53% (102/191) / — |
| capture_pursuer | safe_evader | 100% (17/17) / 100% (102/102) | 100% (32/32) / 100% (192/192) | — | 100% (191/191) / 100% (1145/1146) |
| lambert_pursuer | heuristic_evader | 59% (10/17) / — | 75% (24/32) / — | — | 64% (122/191) / — |
| lambert_pursuer | safe_evader | 100% (17/17) / 98% (100/102) | 100% (32/32) / 99% (191/192) | — | 99% (190/191) / 100% (1143/1146) |

### |zone_offset_da|（中心相對躲方初始 a / 一發容量）

| 追方 | 躲方 | 0–1 | 1–2 | 2–4 | ≥4 |
|---|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 45% (25/56) / — | 64% (46/72) / — | 52% (29/56) / — | 50% (28/56) / — |
| capture_pursuer | safe_evader | 100% (56/56) / 100% (335/336) | 100% (72/72) / 100% (432/432) | 100% (56/56) / 100% (336/336) | 100% (56/56) / 100% (336/336) |
| lambert_pursuer | heuristic_evader | 59% (33/56) / — | 72% (52/72) / — | 71% (40/56) / — | 55% (31/56) / — |
| lambert_pursuer | safe_evader | 98% (55/56) / 99% (334/336) | 100% (72/72) / 99% (428/432) | 100% (56/56) / 100% (336/336) | 100% (56/56) / 100% (336/336) |

### ap_in_zone（追方初始 a 在安全空域內）

| 追方 | 躲方 | 否 | 是 |
|---|---|---|---|
| capture_pursuer | heuristic_evader | 56% (87/155) / — | 48% (41/85) / — |
| capture_pursuer | safe_evader | 100% (155/155) / 100% (930/930) | 100% (85/85) / 100% (509/510) |
| lambert_pursuer | heuristic_evader | 66% (103/155) / — | 62% (53/85) / — |
| lambert_pursuer | safe_evader | 100% (155/155) / 100% (927/930) | 99% (84/85) / 99% (507/510) |

### cross（躲方初始 a 與區間中心位於追方兩側）

| 追方 | 躲方 | 否 | 是 |
|---|---|---|---|
| capture_pursuer | heuristic_evader | 58% (30/52) / — | 52% (98/188) / — |
| capture_pursuer | safe_evader | 100% (52/52) / 100% (312/312) | 100% (188/188) / 100% (1127/1128) |
| lambert_pursuer | heuristic_evader | 60% (31/52) / — | 66% (125/188) / — |
| lambert_pursuer | safe_evader | 100% (52/52) / 99% (308/312) | 99% (187/188) / 100% (1126/1128) |

### dist0_over_DT（初始距離 / ΔV_lim·T_round）

| 追方 | 躲方 | <0.2 | 0.2–1 | ≥1 |
|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 29% (9/31) / — | 41% (7/17) / — | 58% (112/192) / — |
| capture_pursuer | safe_evader | 100% (31/31) / 99% (185/186) | 100% (17/17) / 100% (102/102) | 100% (192/192) / 100% (1152/1152) |
| lambert_pursuer | heuristic_evader | 68% (21/31) / — | 53% (9/17) / — | 66% (126/192) / — |
| lambert_pursuer | safe_evader | 97% (30/31) / 99% (184/186) | 100% (17/17) / 100% (102/102) | 100% (192/192) / 100% (1148/1152) |

### epoch_gap_h（兩艘入軌時間差，時）

| 追方 | 躲方 | 0–6 | 6–12 | 12–24 | 缺資料 |
|---|---|---|---|---|---|
| capture_pursuer | heuristic_evader | 86% (6/7) / — | 73% (8/11) / — | 64% (14/22) / — | 50% (100/200) / — |
| capture_pursuer | safe_evader | 100% (7/7) / 100% (42/42) | 100% (11/11) / 100% (66/66) | 100% (22/22) / 100% (132/132) | 100% (200/200) / 100% (1199/1200) |
| lambert_pursuer | heuristic_evader | 86% (6/7) / — | 55% (6/11) / — | 64% (14/22) / — | 65% (130/200) / — |
| lambert_pursuer | safe_evader | 100% (7/7) / 100% (42/42) | 100% (11/11) / 100% (66/66) | 100% (22/22) / 100% (132/132) | 100% (199/200) / 100% (1194/1200) |

## safe_evader 輸掉的局

共 1 局。

| game_id | family | sub | 結局 | ΔV_lim（m/s） | R_cap（km） | T_round（秒） | meta 重點欄位 |
|---:|---|---|---|---:|---:|---:|---|
| 26 | final_adv_close | close_frac | sma_out | 482.718 | 12.3993 | 2354.96 | a_p=7623.81、a_e=7628.39、da=1018.83、zone_width_da=0.628128、zone_offset_da=-0.255742、ap_in_zone=是、cross=是、dist0_km=87.6832、dist0_over_DT=0.077133 |
