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

### E3b 長時間漂移（2026-09-16）
- **設定**：純滑行 20,000 s（約 3.5 圈），LEO 圓軌道與高遠地點橢圓（e = 0.35），GMAT 重播逐窗口比位置。
- **結果**：

| 重力 | LEO 圓 | 高遠地點 e=0.35 |
|---|---|---|
| 點質量（degree 0） | 0.23 m | 0.31 m |
| J2（degree 2） | 9–14 m | 9 m |

- 當天流程彩排（追者 vs DvEvader，含多發大脈衝）在 16,000 s 時匯入差約 37 m。
- **結論**：積分器與 μ 對得非常好（點質量 0.2 m / 5.5 h）；**J2 模型與 GMAT JGM2 有約 0.5–2 m / 1000 s 的線性漂移**（係數/正規化的微小差異）。遠小於 5 km 捕獲半徑，而且**當天每回合都從官方 GMAT 狀態重新匯入**，漂移只累積一個窗口（300 s → < 1 m），不影響決策。若官方回合很長或要在自家引擎推演整場，才需要再追 J2 係數。

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
- **反過來的收穫**：我們自己的 rollout 躲者（候選 = DvEvader 系）**沒有**立刻逃逸，所以不是最強的躲者。
- **躲者驗證**（16 局，`reports/hap108_escape_evader_{symmetric,pursuer_fuel_2x}.md`；數字為躲者平均存活，對 Lambert + rollout 追者）：

| 躲者 | 對稱燃料 | 追者燃料 2× |
|---|---|---|
| rollout 躲者 | 72% | **31%** |
| EscapeEvader | **88%** | 12% |
| rollout 躲者 + escape 候選 | 72% | 31% |

- **結論**：(1) 逃逸打法**強烈依賴規則**——燃料對稱時最強、追者燃料多時最差；(2) 把 escape 塞進 rollout 候選**沒效**：rollout 躲者的對手模型是較弱的 Lambert 系追者，推演裡「省油也能贏」，分數偏好保留燃料，永遠不選燒光燃料的逃逸（**對手模型太弱 → 規劃過度樂觀**）。→ 改做 `AdaptiveEvader`：開局看「躲者燃料 / 追者燃料」，≥ 門檻整場逃逸、否則 rollout。
- **隨機規則分布驗證**（40 局，`reports/hap108_adaptive_ranges.md`；躲者平均存活，對 Lambert + rollout 追者）：

| 躲者 | 存活 |
|---|---|
| rollout 躲者 | **60%** |
| EscapeEvader | 38% |
| Adaptive（燃料比門檻 0.5 / 0.75 / 1.0） | 44% / 46% / 49% |

- **負結果**：只看燃料比的切換**全部輸給 rollout 躲者**。原因：隨機規則裡躲者單發上限只有追者的 0.3–1.0 倍，**逃逸需要大推力**，單發小時無效——對稱規則那組（E12 表）單發也對稱，所以沒暴露這個條件。
- **修正**：AdaptiveEvader 改成燃料比 ≥ 0.75 **且**單發上限比 ≥ 0.9 才逃逸（只在已驗證的近對稱區域切換），其餘一律 rollout；確認評測見下一條。
- **教訓**：一條規則在一個測試點成立，不代表在規則分布上成立——**每個「策略切換條件」都要在隨機規則分布上再驗一次**。
- **雙條件確認**（`reports/hap108_adaptive2_{ranges,symmetric}.md`）：

| 躲者 | 隨機規則 40 局 | 對稱規則 16 局 |
|---|---|---|
| rollout 躲者 | **60%** | 72% |
| Adaptive（燃料比 ≥ 0.75 且單發比 ≥ 0.9） | 50% | **88%** |

- 逐局比對隨機規則：雙條件在 6 局觸發逃逸，**rollout 躲者在這 6 局全部存活**，逃逸對 Lambert 追者輸 3 局、對 rollout 追者輸 5 局。差別在**絕對推力**：對稱規則集雙方單發 1500 m/s，隨機規則的單發上限可低到 50 m/s，比例對稱也逃不掉。
- **最終決定**：不採用 AdaptiveEvader 當預設（再加第三個條件就是在 6 局上過擬合）。copilot 預設躲者維持 rollout；`escape_evader` 列為參考大腦，並把 rollout 追者加進躲者推演的對手模型，避免推演過度樂觀。當天手冊只保留一條窄結論：**正式規則若雙方單發上限都大（≥ ~1000 m/s）且燃料對稱，逃逸值得優先考慮**。

## E13 當天流程彩排（GMAT 當真實世界，HAP-55）
- **方法**：`tools/dress_rehearsal.py`。每回合 GMAT 重播全部歷程 → 帶表頭報表 → `copilot import` → 我方 `copilot advise`（推演全開，採用推演表 ★ 推薦）/ 對手 agent，兩邊都只看 GMAT 匯入的狀態。預設規則（對稱 1500/3000）、near_coplanar、seed 0。
- **產物**：`reports/rehearsal_pursuer_vs_dv_evader.md`、`reports/rehearsal_evader_vs_rollout.md`

| 場次 | 結局 | 回合 | 我方決策 平均 / 最長 | GMAT 每回合 | 匯入差最大 | 整場 |
|---|---|---|---|---|---|---|
| 我方追者 vs DvEvader | **捕獲（勝）** t=18,551 s | 62 | 1.5 s / 11.6 s | 0.5 s | 47 m | 79 s |
| 我方躲者 vs rollout 追者 | **撐到時限（勝）**，最近 26.6 km | 78 | 3.9 s / 14.0 s | 0.6 s | 84 m | 208 s |

- **亮點**：躲者那場的 ★ 推薦**自己選出了逃逸打法**——第 1 回合選 `escape_evader`（1500 m/s）、第 3 回合選 RL 躲者（又一發 1500 m/s，等於第二發逃逸），燃料用完後才交給 rollout 躲者。這正是 E12 發現「燃料與推力都對稱時開局逃逸最強」的打法，而 copilot 的推演排序（對 rollout 追者做推演）不需要任何手寫切換條件就找到了。
- **邊界細節**：追者那場引擎在距離 5.0000 km 判定捕獲，同時刻 GMAT 為 5.0057 km（差 5.7 m）；該次交會最近到 30 m，GMAT 下同樣會捕獲。捕獲發生在邊界上時，要以官方 GMAT 判定為準。
- **結論**：當天工具鏈（GMAT 報表 → 匯入 → 推演排序 → 脈衝 → GMAT）完整可用；決策最長 ~14 s，只要官方回合時限 ≥ 30 s 就能每回合跑完整推演。

## E10 用 rollout 大腦確認平衡結論
- **產物**：`reports/rollout_rules_{symmetric,pursuer_fuel_2x,evader_small_burn_big_fuel}.md`（24 局，mixed 幾何）

| 規則集 | Lambert 追者 vs DvEvader / rollout 躲者 | rollout 追者 vs DvEvader / rollout 躲者 |
|---|---|---|
| 對稱（1500/3000 對 1500/3000） | 21% / 4% | **54% / 54%** |
| 追者燃料 2× | 88% / 58% | **88% / 83%** |
| 躲者小單發（150）+ 多燃料 | 8% / 8% | **42% / 33%** |

- **結論**：(1) 燃料比主導勝負的結論在強大腦下仍成立（2× 燃料 → 83–88%；小單發多燃料躲者仍最難）；(2) rollout 追者在每種規則下都顯著強於 Lambert，差距最大在對稱規則（+33～50 個百分點）；(3) rollout 躲者也比 DvEvader 難抓。

## E14 排位賽版規則：結論有沒有翻（2026-10-20）
- **問題**：排位賽規則（2026-10-06 初版，10-19 收到）是單發 250 m/s、總 Δv 3 km/s。四強賽如果沿用這組數字，燃料等於 12 發小推力，落在之前所有評測都沒涵蓋的區域（`RuleRanges` 燃料最多 8 發、對稱規則集是 2 發 × 1500）。E8–E12 的結論還成立嗎？
- **設定**：新規則集 `configs/rulesets/ranking_like.json`（雙方 250/3000，其餘同預設，連 `gravity_degree=2` 都不動，只改燃料結構），跟 `symmetric.json` 各跑 20 局，mixed 幾何、seed 0，兩邊同 game_id 是同一個初始幾何，可以逐局比對。4 worker、`nice 10`（另一個 session 同時在跑 Planner）；兩組共 ~5 分鐘。
  ```bash
  NUMBA_NUM_THREADS=1 uv run python evaluate.py --rules configs/rulesets/{symmetric,ranking_like}.json --scenario mixed --games 20 --seed 0 --workers 4 \
      --pursuers "lambert_pursuer;rollout_pursuer" --evaders "dv_evader;rollout_evader;escape_evader" --name ranking_like_check_{symmetric,ranking_like}
  ```
- **產物**：`reports/ranking_like_check_{symmetric,ranking_like}.md`

追者勝率（20 局，括號是 95% 區間）：

| 追者 \ 躲者 | dv_evader | rollout_evader | escape_evader |
|---|---|---|---|
| Lambert（對稱 → 排位版） | 25% → 40% | 5% → 20% | 5% → 45% |
| rollout（對稱 → 排位版） | 55% → 80% | 45% → 20% [8–42] | 50% → **100%** [84–100] |

逐局配對（rollout 追者；「只 X 抓到」= 同一幾何只在 X 規則下捕獲）：

| 躲者 | 兩邊都抓到 | 只對稱抓到 | 只排位版抓到 | 都沒抓到 |
|---|---|---|---|---|
| dv_evader | 10 | 1 | 6 | 3 |
| rollout_evader | 1 | 8 | 3 | 8 |
| escape_evader | 10 | 0 | **10** | 0 |

- **結論**：
  1. **開局逃逸在排位版規則下翻盤，從最強變最弱**：rollout 追者 20/20 全抓到，連 Lambert 追者都抓到 45%。逐局 10 局只有排位版抓到、0 局反向（符號檢定 p ≈ 0.002），不是雜訊。原因和 E12 的雙條件修正一致：逃逸靠一發大推力把遠地點拉走，250 m/s 一發做不到，連推 12 發又給追者 12 個回合修正。E12 手冊那條窄結論（「雙方單發都 ≥ ~1000 m/s 且燃料對稱才優先考慮逃逸」）**在這裡被證實**；「燃料對稱時開局逃逸近乎支配策略」只在大推力下成立。
  2. **最強躲者是 rollout 躲者**，排位版下存活 80%（對 Lambert 80%、對 rollout 追者 80%）。rollout 追者對它從 45% 掉到 20%，但配對只有 8 對 3 局，統計上還不能說變難抓（p ≈ 0.23）。
  3. **對弱躲者，追者變強**：DvEvader 和逃逸躲者都更好抓（小推力閃避躲不掉多回合修正）。所以「燃料比主導勝負」在這組規則下不足以描述局勢——燃料對稱時，**勝負改由躲者打法決定**。
  4. **對 copilot 的影響**：E13 躲者彩排的 ★ 推薦是開局逃逸（1500 m/s 規則）。排位版規則下照理推演排序會自己避開逃逸，但**還沒用 drill/彩排實測**。
- **附帶發現**：對稱規則下 rollout 追者對 escape_evader 這次是 50%，E12 是 19%（16 局、不同幾何批次）。兩次的 95% 區間有重疊（約 7–43% 對 30–70%），差距可能只是幾何批次不同；引用這類數字要附上局數 n 和區間。
- **限制**：20 局/配對（區間 ±20 個百分點）、只用 J2、窗口 300 s、捕獲半徑 5 km 都是佔位；沒有測一回合多發（HAP-107）——排位賽有 100 s 機動間隔，四強賽可能允許一回合多發，這會讓小推力的劣勢縮小。

### E14b 排位賽版規則下的躲者 drill：★ 推薦會不會選逃逸（2026-10-20）
- **設定**：`copilot.py drill --role evader --opponent rollout_pursuer --scenario near_coplanar --seed 0`，大腦 `rollout_evader,dv_evader,escape_evader,sb3:models/evader.zip`（跟 E13 彩排同一組大腦、同一個幾何），對手模型用 copilot 預設。每回合照 ★ 推薦下。`ranking_like` 和 `symmetric` 各一場當對照（無 GMAT，單行程）。
  ```bash
  NUMBA_NUM_THREADS=1 uv run python copilot.py drill --role evader --opponent rollout_pursuer --rules configs/rulesets/{ranking_like,symmetric}.json \
      --scenario near_coplanar --seed 0 --brains "rollout_evader,dv_evader,escape_evader,sb3:models/evader.zip"
  ```

| 規則 | 結局 | 最近距離 | 躲者實際推的次數 / 用油 | 39 個我方回合的 ★ |
|---|---|---|---|---|
| symmetric（1500/3000） | 撐到時限（勝） | 26.9 km | 2 發 / 3000 m/s | 第 1 回合 `escape_evader`、第 3 回合 RL 躲者（同為 1500 m/s 逃逸），其餘 rollout |
| **ranking_like（250/3000）** | 撐到時限（勝） | 60.5 km | 11 發 / 2651 m/s | rollout 37、dv_evader 1、RL 1，**`escape_evader` 0 次** |

- **對照組重現 E13**：對稱規則下 ★ 一開局就選逃逸，跟 GMAT 彩排一致。
- **排位版規則下 ★ 從沒選 `escape_evader` 大腦**：它的推演幾乎每回合都輸給 3 個追者模型（Lambert、Lambert w=60、rollout）。
- **但要注意，最後的打法裡仍有逃逸方向的推力**：rollout 躲者 11 發裡有 5 發的方向跟逃逸大腦一樣（RSW 徑向 + 沿軌道各 177 m/s，cos = 1.00），其餘是純徑向或純沿軌道。差別在**時機**：中間夾著不推的回合，大約 3 小時把油分批用完，不是每回合連續推滿。所以結論是「不要用連續推滿的逃逸**大腦**」，不是「不要往逃逸方向推」。
- **前半場比對稱規則危險**：t ≤ 6900 s 的 9 個回合，★ 推薦只贏 1–3 個對手模型（大多輸給 Lambert 系追者模型，實際對手 rollout 追者反而推演會贏），要到 t ≥ 8700 s 才每回合 4/4 全贏。對稱規則下逃逸推完後每回合都是 4/4。
- **限制**：只有一場、一個幾何；對手是 rollout 追者；沒有經過 GMAT。

## E15 排位版規則：大批評測與 exploitability（2026-10-20）
- **問題**：E14 只有 20 局、一批幾何。換一批幾何、加上所有大腦（含 RL、AdaptiveEvader）後結論還在嗎？我們推薦的大腦被針對時會掉多少？
- **設定**：`ranking_like.json`、mixed 幾何、**seed 1**（跟 E14 不同批）、48 局/配對；exploitability 24 局（工具固定 seed 777）。
- **產物**：`reports/e15_ranking_like_wide.md`、`reports/e15_exploit_{rollout_evader,rollout_pursuer,pool_evader}_ranking_like.md`

追者勝率（48 局）：

| 追者 \ 躲者 | dv_evader | rollout_evader | escape_evader | adaptive_evader | RL 躲者 |
|---|---|---|---|---|---|
| Lambert | 52% | 35% | 62% | 62% | 44% |
| **rollout** | 81% | **40%** [27–54] | 94% | 94% | 75% |
| RL 追者 | 60% | 48% | 67% | 67% | 48% |

- **E14 的方向成立**：rollout 追者最強（平均 77%）；rollout 躲者最強（存活 59%），逃逸最弱。E14 的「rollout 追者對 rollout 躲者 20%」這批是 40%，兩批的區間有重疊，取 30–40% 當量級。
- **AdaptiveEvader 在這組規則下會觸發逃逸**，結果跟 escape_evader 逐局相同（94% 被抓）：它的切換條件只看燃料比與單發「比例」都 ≥ 門檻，沒看單發絕對大小（E12 就提醒過）。不要用。

Exploitability（我方勝率）：

| 我方大腦 | vs 一般強對手 | vs 量身反制者 | exploitability |
|---|---|---|---|
| rollout 躲者 | 71% | 42% | **+29** 🔴 |
| rollout 追者 | 29% | 50% | −21 |
| 混合躲者（70% rollout + 30% RL，每局抽） | 58% | 25% | +33 |

- 對稱規則下（E12）rollout 躲者不怕被針對（−6），排位版規則下變成 +29：反制追者（rollout 追者，對手模型換成 rollout 躲者輕量版）把捕獲率從 29% 拉到 58%。
- 每局隨機混一個 RL 躲者**沒有幫助**（更差）。這暗示反制追者不是「讀懂我們」，而是**本身就是更強的追者**：它腦中的躲者模型比預設的 `[coast, dv_evader_fast]` 更像真正的強躲者。→ E16 直接驗證。

## E17 一回合多發（HAP-107）：誰得利（2026-10-20）
- **問題**：主辦方口頭說「一段時間一組動作」，排位賽規則有「機動間隔 ≥ 100 s」——四強賽很可能一個窗口能下好幾發。引擎原本假設一回合一發。
- **實作**（`game/core.py`）：`Rules.burns_per_turn`（預設 1）、`min_burn_gap_sec`（預設 100）。`take_turn(game, agent)` 在副本上推一發、滑行 100 s 後再問 agent 下一發——**自己的窗口裡對手不動**，所以副本的未來就是真實的未來，任何單發 agent 都能直接多發。rollout 推演、copilot（顯示整個窗口的多發計畫）、GMAT 重播都支援。`burns_per_turn=1` 逐位元不變（同 worktree 同 numba 快取，120/120 局相同）。
- **設定**：`configs/rulesets/ranking_like{,_2burn,_3burn}.json`（250/3000，窗口 300 s → 最多 3 發），seed 1、24 局/配對、同一批幾何。
- **產物**：`reports/hap107_ranking_like{,_2burn,_3burn}.md`

追者勝率：

| 追者 \ 躲者 | dv_evader | rollout_evader | escape_evader |
|---|---|---|---|
| Lambert 1 / 2 / 3 發 | 58 / 50 / 46% | 46 / 50 / 33% | 67 / 71 / 50% |
| **rollout 1 / 2 / 3 發** | 79 / 83 / 96% | **29 / 83 / 75%** | 100 / 100 / 96% |

逐局配對（rollout 追者 vs rollout 躲者）：2 發時 14 局「只有多發抓到」對 1 局反向（符號檢定 p ≈ 0.001）；3 發 12 對 1（p ≈ 0.003）。

- **結論**：
  1. **一回合多發讓 rollout 追者大幅變強**，最強躲者（rollout）的存活從 71% 掉到 17–25%。機制：窗口內對手不動，第二發等於拿完美資訊做中途修正；推演到終局的 rollout 會利用這點，Lambert 追者（每發只重解一次）不會，所以 Lambert 沒有變強。
  2. 躲者也能多發，但沒有對稱的好處：閃避靠的是讓對方下一回合要重新攔截，自己窗口內多推幾發的價值小得多。
  3. **規則若允許一回合多發：抽到追者是大優勢**；抽到躲者時存活率掉到 1/4 左右，要以「拖延時間、逼對方耗油」為主。
  4. 每回合決策時間：2 發約 0.5 s、3 發約 1 s（rollout 追者，單行程），現場跑得完。
- **限制**：rollout 推演裡「候選 = 本窗口第一發，剩下的發交給 continuation agent」，候選集沒有直接列舉雙脈衝組合；躲者的多發沒有特別設計（只是重複問 agent）。
- **另一個限制**：解析 agent 的存活檢查要求「推完這一發後的軌道撐到比賽結束」，所以不會用初賽官方範例解那招（兩發同向、中間軌道近地點在地表下、100 s 後第二發救回來）。多發時存活其實只需要撐過間隔，放寬後追者可能更強。

## E16 rollout 追者換更強的對手模型（2026-10-20）
- **問題**：E15 的反制追者（rollout 追者、對手模型 = rollout 躲者輕量版）把 rollout 躲者打到 58%，混合策略也擋不住。它是「讀懂我們」還是「本身就比較強」？
- **設定**：`ranking_like.json`、seed 1、24 局/配對。比較預設 rollout 追者（對手模型 `[coast, dv_evader_fast]`）、只用 rollout 躲者輕量版當對手模型、三個一起（`[coast, dv_evader_fast, rollout 躲者輕量版]`）。
- **產物**：`reports/e16_pursuer_opp_model.md`

| 追者（rollout，對手模型） | dv_evader | rollout_evader | escape_evader | RL 躲者 | 平均 | 決策 |
|---|---|---|---|---|---|---|
| 預設 `[coast, dv_evader_fast]` | 79% | 29% | 100% | 83% | 73% | ~0.2 s |
| `[rollout 躲者輕量版]` | 88% | 71% | 92% | 83% | 83% | ~2.3 s |
| **`[coast, dv_evader_fast, rollout 躲者輕量版]`** | 83% | **71%** | 100% | 88% | **85%** | ~2.4 s |

逐局配對（三模型版 vs 預設）：對 rollout 躲者 11 局只有新版抓到、1 局反向（p ≈ 0.006）；其他躲者差異都在 ±3 局內。

- **結論**：反制追者不是讀心，而是**對手模型更像真正的強躲者，推演就更準**。三模型版對每種躲者都不輸預設，對最強躲者從 29% → 71%。這也解釋了 E15 的「rollout 躲者 exploitability +29」：那其實是「更強的追者」，不是針對。
- **代價**：每回合決策 ~2.4 s（單行程；copilot 會平行跑推演）。
- **對稱規則（1500/3000）確認**（`reports/e16_pursuer_opp_model_symmetric.md`，seed 1、24 局）：三模型版**略弱**——平均 41% → 34%，逐局合計 7 局「只有預設抓到」對 1 局反向（p ≈ 0.07，個別配對都不顯著）。效果規則相依。
- **決定**：不改 `rollout_pursuer` 的全域預設。copilot 追者大腦多一個 `STRONG_ROLLOUT_PURSUER`（三模型版），由推演表排序在當下局面決定用不用；推演表裡它只決定第一發，後續交給預設 rollout 追者（不然一次推演要幾分鐘）。整次 advise ~29 s（8 worker，含暖機）。
- **限制**：「copilot ★ 推薦」這個整體策略本身沒有拿去大批對打（太慢），只驗過單一大腦。

## E18 全攝動 GMAT 彩排：官方模型當真實世界（2026-10-20）
- **問題**：排位賽驗證用完整攝動（EGM96 20×20、潮汐、NRLMSISE00 阻力、日月、SRP、相對論），四強賽很可能一樣；引擎只有 J2–J4。copilot 的預測在官方模型下還準嗎？勝負判定會不會不同？
- **工具**：`tools/gmat_verify.py --force-model ranking_full`（ForceModel 逐字搬自 Planner，太空船參數用佔位值 850 kg / Cd 2.2 / Cr 1.8 / 6 m² / 8 m²）；`tools/dress_rehearsal.py --force-model ranking_full`：GMAT 逐回合推進（曆元跟著走）、每回合把引擎帳本重設成 GMAT 狀態、賽後用 GMAT 密集報表（Hermite 內插）重算真實最近距離與捕獲時刻。逐回合推進 vs 整局重播 < 1 m（pytest）。
- **開環落差**（同一組脈衝不重設狀態，`gmat_verify.py --rules ranking_like.json --force-model ranking_full`，Lambert vs DvEvader 一整局）：位置差 1 個窗口 ~3 m、10 個窗口 ~0.2 km、73 個窗口（6 h）**4.4 km**——跟 5 km 捕獲半徑同量級，所以**每回合一定要用官方給的狀態重新規劃**（copilot 的 import 流程本來就是這樣）。
- **彩排**（near_coplanar、seed 0、推演全開）：

| 場次 | 規則 | 結局（引擎 / GMAT 真實判定） | 單窗口預測誤差 中位 / 最大 | 我方決策 平均 / 最長 |
|---|---|---|---|---|
| 我方躲者 vs rollout 追者 | ranking_like | 撐到時限 / 全程沒進捕獲球，最近 60.5 km（一致） | 1.7 m / 27 m | 15.9 s / 58.7 s（機器滿載、3 worker） |
| 我方追者（2 發/回合）vs rollout 躲者 | ranking_like_2burn | t=15130 s 捕獲 / t=15131 s 進捕獲球，最近 0.51 km（一致） | — / 14 m | 3.9 s / 20.1 s |

- **結論**：每回合重設狀態後，引擎在一個窗口內的預測誤差是公尺級（最大 27 m），遠小於捕獲半徑；兩場的勝負判定 GMAT 與引擎一致，捕獲時刻差 1 s。**全攝動不會讓 copilot 的建議失準**，前提是每回合都匯入官方狀態。
- **踩到的坑**：引擎在剛進捕獲球的瞬間結束比賽，GMAT 判定重播如果也停在那一刻，只會看到「剛好 5.000 km」而判成沒抓到。`gmat_truth` 現在會把最後一個窗口滑完再判定（有 pytest）。現場若官方 GMAT 也只看端點或離散時刻，捕獲要留裕度。
- **限制**：太空船參數是佔位值；兩場、一個幾何；決策時間在滿載機器上量的。

## E19 rollout 躲者換更強的對手模型（2026-10-20）
- **問題**：E16 裡追者換強的對手模型就變強。躲者照做（對手模型多一個 rollout 追者輕量版）也會變強嗎？
- **設定**：`ranking_like.json`、seed 1、24 局。躲者：預設 rollout 躲者（對手模型 Lambert 系兩個）vs 多一個 rollout 追者輕量版。
- **產物**：`reports/e19_evader_opp_model.md`

| 追者 | 預設 rollout 躲者被抓 | 強化對手模型版被抓 |
|---|---|---|
| Lambert | 46% | 46% |
| rollout（預設） | 29% | **62%** |
| 強化版 rollout 追者（E16） | 71% | 67% |

- 逐局配對（對預設 rollout 追者）：11 局只有預設版存活、3 局反向（p ≈ 0.057）。
- **結論**：**不對稱——躲者換強對手模型反而變差**，對其他追者則沒差。可能的原因是推演過度悲觀：假想的追者夠強時，幾乎每個候選都推演成「輸」，排序就只剩「撐多久」這個很粗的差別，選不出真正好的閃避。躲者維持預設；copilot 躲者的推演表（★ 排序）本來就有 rollout 追者當對手模型，那是拿來排序，不是拿來產生候選，所以不受影響。
- **整體結論（E14–E19）**：照排位賽數字的規則下，**追者比躲者好打**——追者有強化版大腦（對最強躲者 71%），一回合多發時更強（E17）；躲者最強的打法（rollout 躲者）被強追者抓到約 70%。

## E20 多發規則下放寬中間軌道存活檢查（HAP-118，2026-10-21 夜間）
- **問題**：`burns_per_turn > 1` 時窗口內兩發之間的中間軌道只需撐過間隔（初賽官方範例解：兩發同向、中間近地點在地表下），
  `orbit_survives` 卻要求撐到比賽結束、把部分解減半。放寬後追者會不會更強（E17 的限制）？
- **實作**：`agents/analytic.py` 的 `next_burn_gap`／`gap_burn_survives`，`LambertPursuer(gap_survival=0|1|2)`，環境變數 `ODC_GAP_SURVIVAL`。
  level 1 = 間隔內不撞地且之後救得回來；level 2 再加「間隔後一發補得完同一個攔截」。**預設 0（舊行為）**；新增 `configs/rulesets/symmetric_{2,3}burn.json`。
- **觸發率**（窗口第一發、嚴格不過但放寬過）：ranking_like_2burn Lambert 6/1690、rollout 候選 4/6140；symmetric_2burn Lambert 8%、rollout 候選 32%。
- **結果**（追者勝率，關 → level 1，逐局配對）：ranking_like_2burn rollout vs rollout 83% → 79%（2/1，p=1）、其他配對逐局相同；
  symmetric_2burn seed 1 rollout vs rollout 71% → 62%（3/1，p=0.62）、seed 2 42% → 46%（1/2，p=1）；全部合計只有關抓到 8 局 vs 只有開抓到 6 局（p=0.79）。level 2 幾乎不觸發。
- **結論**：**看不出增益，預設維持關。** LambertPursuer 瞄的是單發最省轉移，放寬只是讓第一發更大、第二發多半只能救命；
  level 1 配 rollout 還有風險（全輸時 rollout 平手取第一個候選＝零向量，停在撞地軌道上撞毀 1 局）。要用官方範例那招需要真的「兩發規劃」（候選列舉 (第一發, 第二發)）。
- **逐位元**：開關未設時 default／ranking_like／2burn／3burn 共 156 局與改前相同；主 checkout 合併前後另驗一次。
- **產物**：`docs/notes/multi_burn_survival.md`、`reports/gap_survival_ab.md`、`tests/test_gap_survival.py`。

## E21 250 m/s 級規則敏感度地圖（rollout 大腦，HAP-120，2026-10-21 夜間）
- **問題**：E8 的平衡地圖是 1500 m/s 級＋解析大腦；E14–E17 顯示 250 m/s 級下結論會翻。規則公布當天要能直接查「誰有利、用哪個大腦」。
- **設定**：基底 `ranking_like.json`，逐軸改一個欄位（＋多發×窗口、多發×燃料交叉），每格 24 局、mixed、seed 1（與 E15–E17 同一批幾何，基底格與 E17 逐局相同）；
  配對 rr = rollout 追者 vs rollout 躲者、escape = rollout 追者 vs 逃逸躲者、lambert = Lambert 追者 vs rollout 躲者（部分格）；每格跟基底格逐局配對符號檢定。
  強化版 rollout 追者、`RankingRuleRanges` 分布平均**未跑**。
- **工具**：`tools/rule_map.py`（跑格子、可續跑、匯出）、**`tools/rule_lookup.py configs/rules_final.json`**（最接近的格子、預期勝率、建議大腦、超出地圖範圍的欄位）、
  `configs/rule_map.json`（37 格）、`game/rule_presets.py`（`RankingRuleRanges`，排位版規則分布）。

追者勝率 rr（n=24，粗體 = 跟基底逐局配對 p < 0.05）：

| 軸 | 值 → rr |
|---|---|
| 基底（250/3000、300 s、1 發、5 km、T_max 4 週期） | 29% [15–49] |
| 一回合發數 | 2 發 **83%**（+14/−1，p=0.001）、3 發 **75%**（p=0.003） |
| 燃料 追/躲 | 3000/1500 **100%**（p<0.001）、1500/3000 **0%**、3000/4500 **0%**（p=0.016）、4500/3000 46%（p=0.42） |
| 窗口 | 120 s **83%**（p<0.001）、600 s **0%**、900 s **0%**（p=0.016；Lambert 追者也 0/24） |
| T_max | 2 週期 **0%**（p=0.016）、6 週期 **71%**（p=0.013） |
| 看不出差異（p ≥ 0.42） | 捕獲半徑 1／20 km、躲者先手、endpoint 判定、單發 250/150 或 150/250 |
| 交叉 | 多發把「躲者油多」格從 0% 拉回 33–54%；600 s × 3 發 67%（+16/−0）；900 s × 2／3 發 25%／33% |

- **大腦**：逃逸躲者**沒有任何一格**顯著比 rollout 躲者好（900 s 兩者都 24/24 存活）→ 躲者一律 rollout 躲者。
  Lambert 與 rollout 追者只有窗口 120 s 時分得出（83% vs 46%，p=0.004），其他格看不出差異。
- **對稱 1500/3000 確認**（`reports/rmap_symmetric.md`，基底 rr 58%）：燃料方向相同（3000/1500 100%、4500/3000 88%、3000/4500 21%）、
  長窗口方向相同（600 s 21%、900 s 8%）；**不同**的是多發（71%、58%，p ≥ 0.55：燃料只有 2 發滿推）與 120 s 窗口（46%，p=0.38）。
- **結論**：250 m/s 級規則下，除了燃料比，**窗口長度、T_max、一回合發數**都會把勝負整個翻過來（0% ↔ 83%）；E8「窗口、半徑影響很小」只在 1500 m/s 級成立一半（半徑仍然無感、長窗口在兩組規則下都利於躲者）。
  ~70 個檢定約有 5% 偽陽性，單看 p≈0.016（+0/−7）的格子要保守。
- **產物**：`docs/notes/rule_map.md`、`reports/rmap_{ranking,symmetric}.md`、`tests/test_rule_map.py`。
