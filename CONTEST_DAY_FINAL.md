# 決賽（四強賽）當天作戰手冊（2026-11-09 @ 大臺南會展中心）

> 對應 Linear HAP-55 / HAP-104。規則細節官方尚未公告（HAP-50）——**本手冊的流程設計成「規則當天才知道也跑得動」**。規則一公告就更新第一節與 `configs/rules_final.json`。

---

## 一、已知 / 未知

**已知（官方 0510 簡報 + 口頭情報）**
- 追逐 vs 躲避即時對戰，**當天抽籤**決定角色；追者在時間+燃料內靠近 → 追者勝，否則躲者勝。
- **回合交替**：一段時間一方下指令、下一段換另一方。
- 電競模式、會場公用電腦下指令；**兩側有測試電腦可先期模擬**；可自備電腦先期運算。用 GMAT 模擬。
- 簡報 p.10 提到 AIAA Capture the Satellite Challenge（MIT LL KSPDG），賽制設計可能參考它（評分看完成時間、燃料、相對距離）。

**未知（開賽前一定要問到，見第二節）**：窗口長度、單次 Δv 上限、燃料、捕獲半徑、T_max、雙方是否對稱、先手、力模型、指令輸入格式、看得到對手什麼。

---

## 二、開賽前要問工作人員的清單（隊友 A 負責，拿到答案立刻填 `configs/rules_final.json`）

| # | 問題 | 對應 `Rules` 欄位 / 影響 |
|---|---|---|
| 1 | 一個回合（一方）有多久？一回合能下幾發？ | `window_sec`（若可多發 → 告訴主控，copilot 目前假設一發/回合） |
| 2 | 單次機動 Δv 上限？追/躲一樣嗎？ | `max_dv_pursuer_mps` / `max_dv_evader_mps` |
| 3 | 總燃料（總 Δv）？追/躲一樣嗎？ | `fuel_pursuer_mps` / `fuel_evader_mps` |
| 4 | 「靠近」的判定距離？是任何時刻還是只看回合結束？ | `capture_radius_km`（我們的引擎是**連續**偵測；若官方只看端點，策略要瞄準窗口末） |
| 5 | 比賽總時限？ | `t_max_sec` |
| 6 | 誰先動？ | `first_mover` |
| 7 | 力模型（J2？JGM2？階數？大氣？） | `gravity_degree`；有大氣要回報（我們沒模擬） |
| 8 | 撞地/低於多少高度算輸？ | `crash_altitude_km` |
| 9 | 指令怎麼輸入？座標系（EarthMJ2000Eq / VNB / LVLH）？單位（km/s？） | copilot 輸出 ECI km/s、VNB km/s、RSW m/s 三種，照官方選 |
| 10 | 狀態怎麼給？（六根數 / 笛卡兒 / GMAT 報表）看得到對手的燃料嗎？ | 局勢檔 `elements` 或 `r_km/v_kms`；對手燃料看不到就填估計值 |
| 11 | 每回合下指令有沒有時間限制？ | 決定能不能跑 rollout（`--no-rollout` 約 1 s，完整約 5–20 s） |
| 12 | 計分細節（只看勝負？還是距離/燃料/時間也算分？） | 影響燃料權重；copilot 的 rollout 會列燃料與時間 |

---

## 三、規則公布後 30 分鐘內

```bash
# 1. 填規則（照 game/rules.py 的欄位名）
cp configs/rules_template.json configs/rules_final.json   # 然後編輯
# 2. 平衡評估：這個規則下誰有利、哪個大腦最好（約 5 分鐘，12 核）
uv run python evaluate.py --rules configs/rules_final.json --scenario mixed --games 30 \
    --pursuers "lambert_pursuer;{\"name\":\"lambert_pursuer\",\"time_weight_mps\":60};sb3:models/pursuer.zip" \
    --evaders "coast;dv_evader;minimax_evader_fast;sb3:models/evader.zip" --name final_rules
# 3. 看 reports/final_rules.md：兩個角色各選勝率最高的大腦，寫在白板上
```

- 如果初始軌道也公布了：`--scenario` 換成對應家族，或直接用 `copilot.py drill` 以正式軌道演練一場。
- **追者勝率 < 20% 的規則**（雙方對稱、躲者油多）：抽到追者時目標改成「最小化最近距離」（若計分看距離）；抽到躲者就穩穩打燃料消耗戰。

---

## 四、每回合流程（主控）

1. **更新局勢檔**（`state.json`）：時間、雙方狀態、已用燃料、`mover`。
2. **跑建議**：
   ```bash
   uv run python copilot.py advise state.json                  # 戰況 + 各大腦建議 + 推演
   uv run python copilot.py advise state.json --no-rollout     # 時間很趕時（~1 s）
   ```
3. **看戰況三個數字**：
   - `純滑行最近接近`：< 捕獲半徑 → 追者**不用推**（省油），躲者**必須推**。
   - `追者攔截所需 Δv（短程）` vs `追者剩餘燃料/單發上限`：need < 單發上限 → 追者這回合可能直接收掉。
   - `近地點高度` / `不推也安全`：任何一方 False → 那方不處理就會再入。
4. **選建議**：預設採用推演結果「對最強對手模型仍 WIN」的那個大腦；都 LOSE 就選最近距離最小（追者）/最大（躲者）的。
5. **先驗證再下**（時間允許）：
   ```bash
   uv run python copilot.py advise state.json --no-rollout --gmat burn.script --verify
   ```
   把 `burn.script` 拿到**測試電腦**的 GMAT 跑，確認窗口末距離跟 copilot 預測一致（實測差距 < 10 m）。
6. **照官方要求的座標系輸入**（ECI km/s 或 VNB km/s），隊友 B 唸數字、主控輸入、隊友 C 核對。

---

## 五、分工（3 人）

| 角色 | 工作 |
|---|---|
| 主控 | 操作 copilot、決定採用哪個建議、在公用電腦輸入指令 |
| 記錄 | 抄官方狀態 → state.json；記每回合雙方 Δv 與時間（事後 GMAT 重播用） |
| 驗證 | 測試電腦跑 GMAT 腳本、核對輸入數字（小數點/單位/正負號） |

---

## 六、戰術原則（來自 2026-09-15 起的對打評測，詳見 reports/）

**追者**
- 能在**本窗口內**攔截（躲者來不及反應）→ 直接推滿（copilot 的 LambertPursuer 會優先選這種）。
- 否則推「部分解」、下回合重算（receding horizon）；**不要把近地點壓到撞地線附近**——J2 會讓近地點慢慢下沉（評測中曾因此 25/60 局自己再入，已加 50 km 裕度）。
- 雙方能力對稱時躲者有結構性優勢（預設規則下解析追者對 DvEvader 只有 ~22%），這時追求最近距離/逼對手耗油。

**躲者**
- 燃料消耗戰：挑讓「追者攔截所需 Δv − 追者剩餘燃料」最大的機動（DvEvader）。
- 高能量逃逸（徑向+沿軌道推高遠地點）在對稱規則下非常有效，但**推完要確認近地點安全**。
- 純滑行最近接近 < 捕獲半徑時一定要動。

---

## 七、故障應變

| 狀況 | 做法 |
|---|---|
| 筆電 copilot 當掉 / 環境壞 | 備機（事先 `uv sync` 好）；最壞手動：GMAT 測試電腦跑 Lambert（Planner 的 Target 腳本） |
| copilot 與 GMAT 差很多 | 以 GMAT 為準；檢查力模型（第二節 #7）、單位（m/s vs km/s）、座標系 |
| 官方狀態只給六根數 | 局勢檔用 `elements`（角度是度）；近圓軌道 AOP/TA 退化沒關係，位置速度重建一致 |
| 規則跟我們假設差很多（例如回合內可多發） | 先用 `--no-rollout` 的單發建議；多發時把一發拆成多次、每次重跑 advise |
| 沒有網路 | 全部本地可跑（numba 快取、模型檔都在 repo / models/） |

---

## 八、前一晚準備

- [ ] 兩台筆電 `git pull && uv sync && uv run pytest`（全綠，含 GMAT 重播測試）
- [ ] `uv run python copilot.py drill --role pursuer` 與 `--role evader` 各跑一場（預熱 numba 快取）
- [ ] `models/` 放最新的 pursuer / evader 模型（`evaluate.py` 確認過）
- [ ] 印出本手冊第二、四節
- [ ] 充電器、延長線（官方不保證插座）
