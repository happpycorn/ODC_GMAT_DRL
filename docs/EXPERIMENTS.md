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
- **先手 × 窗口**：`reports/balance_firstmover_window.md`

| 先手 \ 窗口 | 120 s | 300 s | 900 s |
|---|---|---|---|
| 追者先 | 25% | 21% | 17% |
| 躲者先 | 25% | 17% | 33% |

- **結論**：先手影響在統計雜訊內（24 局的 95% 區間約 ±20 個百分點）。

- **捕獲判定模式 × 捕獲半徑**：`reports/balance_capturemode_radius.md`

| 模式 \ 半徑 | 1 km | 5 km | 20 km |
|---|---|---|---|
| continuous | 17% | 21% | 21% |
| endpoint | 12% | 12% | 12% |

- **結論**：「只看回合結束」讓追者勝率降 ~5–9 個百分點（躲者多了窗口中途不算數的空間）；endpoint 模式下半徑完全無影響（LambertPursuer 精準瞄準回合邊界，命中就是直接命中）。

## E9 sp3 league self-play（完成，2026-09-16 00:31）
- **設定**：10 envs、隨機規則、mixed 幾何；BC → curriculum 30 萬步/角色 → 12 輪 × 25 萬步/角色（總 ~6.6M 步，約 3.5 小時；追者 ~470 sps、躲者 ~680 sps）。每輪 24 局評測。

| 階段 | 追者 vs coast / dv_evader_fast / dv_evader | 躲者存活 vs lambert / lambert(w=60) |
|---|---|---|
| BC | 75 / 42 / 38 | 50 / 50 |
| curriculum | 79 / 42 / 38 | 50 / 50 |
| it1–it12 範圍 | 71–83 / 29–54 / 33–46 | 42–54 / 42–54 |
| it12 | 75 / 46 / 38 | 54 / 54 |

- **結論**：RL 在 BC 暖啟動的水準附近震盪，**12 輪 league 沒有明顯超越專家**（24 局評測的 95% 區間 ±20 個百分點，看不出趨勢）。guided 追者的策略參數空間（時間偏好/推力比例/horizon）本身的上限就接近 LambertPursuer；躲者直接 Δv 也沒學出比 DvEvader 更好的閃避。對照 E7：**rollout 規劃器（不需訓練）明顯更強**。
- **下一步**：RL 不當主腦；改評估它當 rollout 的候選產生器或對手模型（HAP-105）。

## E11 RL × rollout 整合（HAP-105）
- **設定**：對稱規則（configs/rulesets/symmetric.json）、mixed 幾何、24 局；已部署 models/pursuer.zip（sp3 it4）、models/evader.zip（sp3 it8，含撞地防呆）。
- **產物**：`reports/hap105_pursuer.md`、`reports/hap105_evader.md`

| 追者大腦 | vs DvEvader | vs rollout 躲者 | vs RL 躲者 | 平均 | 決策 ms |
|---|---|---|---|---|---|
| rollout | 54% | 54% | 62% | **57%** | ~137 |
| rollout + RL 當對手模型 | 50% | 46% | 71% | 56% | ~320 |
| rollout + RL 當候選 | 58% | 50% | 67% | 58% | ~165 |
| RL 單獨 | 8% | 0% | 12% | 7% | ~19 |

| 躲者大腦 | 平均存活（vs Lambert / rollout / RL 追者） | 決策 ms |
|---|---|---|
| rollout | **81%** | ~120 |
| rollout + RL 當候選 | 78% | ~150 |
| rollout + RL 當對手模型 | 76% | ~280 |
| RL 單獨 | 69% | ~4 |

- **結論**：RL 不論當候選或對手模型都**沒有統計上可見的增益**，還讓決策變慢 1.2–2.3 倍；單獨使用在對稱規則下是最弱的大腦。**當天主腦 = 純 rollout 規劃器**；RL 模型保留為 copilot 的參考意見與極快速（4 ms）的訓練/推演對手。
- **細節觀察**：rollout 追者把 RL 躲者當對手模型時，對 RL 躲者勝率升到 71%（對手模型對上真實對手時確實有用），但對其他躲者掉——**「猜中對手」有利、「猜錯」有害**，這正是 exploitability 測試（E12）要量的東西。

## E12 Exploitability（HAP-108）
- **方法**：`tools/exploitability.py`。反制者 = 對面角色的 RolloutPlanner，對手模型設成我方大腦（rollout 大腦用輕量版近似）；exploitability = 我方對一般強對手的勝率 − 對反制者的勝率。16 局、mixed 幾何。

| 我方大腦 | 規則 | vs 一般強對手 | vs 反制者 | exploitability |
|---|---|---|---|---|
| **rollout 追者** | 對稱 | 56% | **12%** | **+44** 🔴 |
| rollout 躲者 | 對稱 | 44% | 50% | −6 |
| Lambert 追者 | 對稱 | 0% | 0% | 地板效應 |
| Lambert 追者 | 追者燃料 2× | 50% | 56% | −6 |
| rollout 追者 | 追者燃料 2× | 88% | 88% | 0 |

- **重播診斷**（4 局）：反制躲者的機動**類型**跟一般 rollout 躲者一模一樣（徑向+沿軌道 1061/1061 m/s 高能量逃逸），差別只在**時機**——第二發緊接著推（一般躲者隔 3000–3600 s）。兩三回合內遠地點就拉到追不到的高度，rollout 追者判斷所有候選都輸、乾脆不追（贏的反制局追者只用了 ~400 m/s）。
- **初步解讀**：對手模型集缺了「開局連續逃逸」這種躲者 → 新增 `EscapeEvader`。
- **驗證**（對稱規則、16 局，`reports/hap108_robust_pursuer.md`）：

| 追者 | vs rollout 躲者 | vs EscapeEvader | vs 反制者 |
|---|---|---|---|
| rollout 追者 | 56% | **19%** | 12% |
| rollout 追者 + EscapeEvader 對手模型 | 56% | 19% | 19% |

- **修正後的結論**：加對手模型**沒用**，因為**單純的 EscapeEvader 本身就把 rollout 追者壓到 19%**——這不是「被讀心」，而是**燃料對稱時「開局立刻逃逸」近乎躲者的支配策略**，追者的候選集（任何 Lambert 解）都追不上（呼應 E8：燃料比主導勝負）。追者燃料 2× 時同一招就無效（E12 表中 88% / 88%）。
- **反過來的收穫**：我們自己的 rollout 躲者（候選 = DvEvader 系）**沒有**立刻逃逸，所以不是最強的躲者 → 把 EscapeEvader 加進 rollout 躲者的候選集驗證中（`reports/hap108_escape_evader_*.md`）。

## E10 用 rollout 大腦確認平衡結論
- **產物**：`reports/rollout_rules_{symmetric,pursuer_fuel_2x,evader_small_burn_big_fuel}.md`（24 局，mixed 幾何）

| 規則集 | Lambert 追者 vs DvEvader / rollout 躲者 | rollout 追者 vs DvEvader / rollout 躲者 |
|---|---|---|
| 對稱（1500/3000 對 1500/3000） | 21% / 4% | **54% / 54%** |
| 追者燃料 2× | 88% / 58% | **88% / 83%** |
| 躲者小單發（150）+ 多燃料 | 8% / 8% | **42% / 33%** |

- **結論**：(1) 燃料比主導勝負的結論在強大腦下仍成立（2× 燃料 → 83–88%；小單發多燃料躲者仍最難）；(2) rollout 追者在每種規則下都顯著強於 Lambert，差距最大在對稱規則（+33～50 個百分點）；(3) rollout 躲者也比 DvEvader 難抓。
