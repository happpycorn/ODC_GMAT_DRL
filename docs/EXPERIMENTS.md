# 實驗紀錄（EXPERIMENTS）

每個實驗：問題 → 設定 → 結果 → 結論 → 產物。數字都能用產物路徑的指令重跑（同 seed 可重現）。
原理與設計理由在 [METHODOLOGY.md](../METHODOLOGY.md)，這份只記「量到什麼」。

---

## E1 舊 final_env 盤點（2026-09-15）
- **問題**：HAP-53 的 env 能不能直接拿去訓練？
- **設定**：隨機動作 31 局；`naive_pursuer` 對 coast 3 局；coast vs coast 密集取樣。
- **結果**：隨機動作 22 局追者撞地、7 局躲者撞地；naive 追者 3/3 自己撞地（最近 865 km）；只看窗口端點高估最近距離。
- **結論**：Δv 映射、事件偵測、超時標記、reset 隨機化都要重做 → HAP-101。

## E2 Lambert 求解器驗證
- **設定**：1000 組隨機 (r1, r2, tof, M, 順逆行, 分支)，本 repo numba 版 vs Planner venv 的 poliastro 0.17 izzo。
- **結果**：可解/不可解判定 1000/1000 一致；速度差最大 1.4e-14 km/s。純二體 DOP853 實飛：單圈命中 < 1 m、M 圈 < 10 m × M。
- **產物**：`tools/compare_lambert_poliastro.py`、`tests/test_lambert.py`。

## E3 GMAT 重播一致性
- **設定**：4000 s、雙方多次脈衝的局，gravity degree 0/2/4，整局丟 GmatConsole（RK89、JGM2、Order=0）。
- **結果**：逐回合位置差 < 10 m（三個 degree 皆是）；copilot 單發驗證腳本 0.03 m。
- **坑**：GMAT 停止條件 `ElapsedSecs` 從該 Propagate 起算。
- **產物**：`tools/gmat_verify.py`、`tests/test_gmat_verify.py`。

## E4 追擊所需 Δv 的解析度與 horizon
- **結果**：固定 24 點 TOF 網格掃 26,000 s → 96 m/s；每週期 24 點 → 5 m/s。整個 T_max 當 horizon 時量值飽和到個位數 m/s。
- **結論**：網格跟週期走、局勢評估用短 horizon（4 窗口、至少半週期）。

## E5 解析 agent 第一輪對打 → 抓到兩個 bug
- **產物**：`reports/diag_default_lambert.md` → `reports/diag2_default.md`、`reports/diag2_ranges.md`
- **Bug 1**：逆行高速交會時捕獲球落在取樣點之間（最近 0.0 km 卻判超時）→ coast.py 回頭二分。
- **Bug 2**：追者近地點壓在撞地線上方幾公里，J2 讓它下沉再入（預設規則 25/60 局）→ 50 km 裕度 + 救命推力 → 0/60。
- **修正後（預設規則，60 局）**：LambertPursuer 對 coast 92%、random 93%、DvEvader 22%、minimax_evader_fast 28%；MinimaxPursuer 全面較弱（對 coast 只 27%）。
- **隨機規則**：near_coplanar 74%、inclined 38%、wild 15%（所有配對平均）。
- **結論**：能力對稱時躲者結構性有利；初始幾何比策略更決定勝負；2-ply 極小極大葉值太悲觀。

## E6 RL 追者的 action 表示（sp1 → sp2 → sp3）
- **sp1（direct Δv）**：BC 模仿 LambertPursuer 後 action MSE 0.026（≈240 m/s RMS）→ 對 coast 捕獲 **4%**（專家 92%）。中止。
- **sp2（guided）**：RL 輸出（時間偏好、推力比例、horizon 比例）→ BC 後對 coast/dv_evader_fast/dv_evader = 75/42/38%。但 NLL 把 log_std 壓到接近 0（nll −4.4），PPO 不探索。中止。
- **sp3（guided + BC 後 log_std 重設 −1.0）**：curriculum 30 萬步後 79/42/38%（587 sps）；躲者 curriculum 30 萬步後對 Lambert 存活 50%（1007 sps）。league 進行中。
- **結論**：攔截的 m/s 級精度留給 Lambert，RL 只做策略層決策。
- **產物**：`runs/sp3/metrics.jsonl`（不進 git）、`train_selfplay.py`。

## E7 Rollout 規劃器
- **產物**：`reports/rollout_eval_default.md`、`reports/rollout_eval_ranges.md`、`reports/rollout_eval_official_geom.md`

| 條件 | 追者 | 對 coast | 對 DvEvader | 對 rollout 躲者 |
|---|---|---|---|---|
| 預設規則（30 局） | Lambert | 93% | 17% | 7% |
| | **rollout** | 97% | **50%** | **57%** |
| 隨機規則（40 局） | Lambert | 72% | 38% | 25% |
| | **rollout** | 82% | **57%** | **35%** |
| 官方範例幾何 + 隨機規則（30 局） | Lambert | 27% | 7% | 7% |
| | **rollout** | 50% | 23% | 17% |

- 躲者：rollout 對 Lambert 追者存活 93%（預設規則）。決策 ~140 ms。
- **結論**：直接下完整場推演 > 短視啟發式葉值；copilot 預設大腦改 rollout。

## E8 規則平衡地圖
- **躲者單發上限 × 躲者燃料**（追者 1500/3000，Lambert vs DvEvader，24 局/格）：`reports/balance_evader_dv_fuel.md`

| 躲者上限 \ 燃料 | 750 | 1500 | 3000 |
|---|---|---|---|
| 150 | 67% | 46% | **8%** |
| 375 | 75% | 79% | 38% |
| 750 | 83% | 67% | 38% |
| 1500 | 83% | 62% | 21% |

- **結論**：躲者總燃料是主因；小單發 + 多燃料（持續小閃避）最難抓。

- **捕獲半徑 × 窗口**（其餘預設規則）：`reports/balance_capture_window.md`

| 捕獲半徑 \ 窗口 | 120 s | 300 s | 900 s |
|---|---|---|---|
| 1 km | 25% | 17% | 17% |
| 5 km | 25% | 21% | 17% |
| 20 km | 29% | 21% | 17% |

- **結論**：幾乎是平的——對稱規則下追者的瓶頸是**燃料**，不是瞄準精度或回合節奏。捕獲半徑從 1 → 20 km 只多 ~4 個百分點。

- **追者單發上限 × 追者燃料**（躲者 1500/3000）：`reports/balance_pursuer_dv_fuel.md`

| 追者上限 \ 燃料 | 1500 | 3000 | 6000 |
|---|---|---|---|
| 300 | 8% | 29% | 33% |
| 750 | 0% | 12% | 62% |
| 1500 | 0% | 21% | **88%** |

- **結論**：追者燃料要**明顯多於躲者**（2×）才有利；燃料少時單發上限大反而更糟（大推力快速燒光油）；燃料多時則需要大單發才能一次收掉。
- 先手 × 窗口、capture_mode × 捕獲半徑：執行中（HAP-106）。

## E9 sp3 league 進度
- it1 追者（250k 步）：coast 83%、dv_evader_fast 29%、dv_evader 46%（curriculum 後 79/42/38）。混合訊號，待更多輪。
