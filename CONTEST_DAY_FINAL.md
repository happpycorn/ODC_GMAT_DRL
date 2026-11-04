# 金／銅牌賽當天作戰手冊（2026-11-09 @ 大臺南會展中心）

> 照 2026/10/29 正式規則初版寫（2026-11-01 更新，F1–F5 工具定案）。舊版（回合交替＋燃料上限的假設）在 git 歷史
> `ef6ea44:CONTEST_DAY_FINAL.md`，**已不適用**。
>
> **比賽中禁止網路與生成式 AI。** 這份手冊要讓隊員自己照著做完，不能問 Claude／Codex。所有工具都在 Mac 上離線跑。
> 所有指令都在 repo 根目錄（`cd ~/Documents/Program/ODC_GMAT_DRL`）執行。指令裡的 `<...>` 換成實際檔名。

---

## 一、規則重點（只記會影響操作的）

| 項目 | 規則 | 我們的對應 |
|---|---|---|
| 出手 | 雙方**同時**在回合起點各推一發，互相看不到 | 每回合只決定一個 Δv |
| 回合 | **6 回合**，每回合滑行 T_round（當場公告） | 規則檔 `window_sec` = T_round、`rounds` = 6 |
| 單發上限 | ΔV_lim（當場公告）；超過不違規，等比例縮到上限照常執行 | 規則檔 `max_dv_pursuer_mps`、`max_dv_evader_mps`；工具一律交 ΔV_lim − 0.05 以內 |
| 總 Δv | **不設上限** | 規則檔燃料填 `null` |
| 攔截 | 任一時刻距離 ≤ R_cap，比賽立即結束、追方贏 | 規則檔 `capture_radius_km` |
| 撞地 | 球形地球，軌跡高度 < 0 的一方判輸 | `crash_altitude_km` = 0；工具推完近地點至少留 30 km |
| 逃方勝利 | 6 回合撐完、沒被攔截，**而且**最後逃方半長軸 a = (2/r − v²/μ)⁻¹ 落在安全空域 [lo, hi] | 規則檔 `safe_sma_km` = [lo, hi]（km） |
| 力學 | 純二體（地球點質量） | `gravity_degree` = 0 |
| 初始狀態 | 雙方 r0、v0（EarthMJ2000Eq，km、km/s），含 epoch；兩艘 epoch 可以不同 | 工具把早出發的那艘先傳播到較晚的 epoch |
| 提交 | 一行 `角色, 回合, ΔvX, ΔvY, ΔvZ`（m/s、EarthMJ2000Eq、至少兩位小數） | 工具最後一行印 `提交：...`，照抄 |
| 角色 | 公告題目後 **10 分鐘**分析，排位較優的一方選角色 | 角色選擇器（第三節） |

---

## 二、開賽前要問工作人員的清單

| # | 問題 | 影響 |
|---|---|---|
| 1 | 狀態檔（USB）是什麼格式？笛卡兒還是六根數？EarthMJ2000Eq 嗎？有沒有經緯高（EarthFixed）？ | 第四節步驟 1 用哪個指令 |
| 2 | 兩艘的 epoch 不同時，是不是早出發的那艘先單獨傳播到晚出發的時刻、第 1 回合從那裡開始？ | 工具照這個假設對齊 |
| 3 | 撞地判定用的地球半徑？（GMAT 預設 6378.1363 km，我們引擎 6378.137 km，差 0.7 m） | 近地點不要貼著地表 |
| 4 | 每回合公告的內容：雙方實際 Δv、最近距離、雙方新狀態？公告用什麼格式？ | `announce` 要輸入什麼 |
| 5 | 提交的 Δv 是在回合起點瞬間施加嗎？主辦用幾位小數計算？ | 工具已用印出的數字重驗 |
| 6 | 每回合 10 分鐘從什麼時候開始算？超時沒交算不推嗎？ | 時間分配（第四節） |
| 7 | 安全空域是閉區間嗎？a 用最後一回合結束當下的二體狀態算？ | 逃方最後一回合的落點 |
| 8 | 提交行的角色要寫什麼字（追方／逃方？中文或英文？）、回合從 1 還是 0 算？ | 改 `configs/final_format.json`（第六節） |

---

## 三、題目公告後的 10 分鐘（分析、選角色）

| 時間 | 誰 | 做什麼 |
|---|---|---|
| 0–2 分 | 記錄 | USB 狀態檔複製到 `day/`；複製規則範本並填公告的四個數字（見下） |
| 2–3 分 | 主控 | 解析初始狀態、看數字合不合理 |
| 3–6 分 | 主控 | 跑角色選擇器（Corn 實測 90 s、Mac 實測 126 s（11-04）；趕時間加 `--fast`，Mac 實測 39 s） |
| 6–9 分 | 全隊 | 看「題目特徵」與最後一行建議 |
| 9–10 分 | 主控 | 決定角色、告知工作人員；建 session |

**1. 規則檔**（記錄負責，改四個數字，其餘不要動）
```bash
mkdir -p day && cp configs/rulesets/final_official.json day/announced.json
open -e day/announced.json
```
- `max_dv_pursuer_mps`、`max_dv_evader_mps` ← ΔV_lim（m/s；**不是 km/s**）
- `capture_radius_km` ← R_cap（km）
- `window_sec` ← T_round（**秒**；公告給分鐘要乘 60）
- `safe_sma_km` ← `[lo, hi]`（km，半長軸，不是高度；公告給高度要加 6378.137）

**2. 初始狀態**
```bash
uv run python copilot.py final parse day/<USB檔>
```
看印出來的 |r|（要像 6700–8000 km）、|v|（要像 7–8 km/s）、高度、格式判斷。檔案裡的船名認不出來時加
`--names pursuer=<追方船名>,evader=<逃方船名>` 或 `--order pursuer,evader`。
- 狀態是**經緯高**（EarthFixed／SphericalAZFPA 等 GMAT 欄位）：先轉成 EarthMJ2000Eq，再 parse 轉出來的檔
  ```bash
  uv run python tools/gmat_state_convert.py day/<經緯高.json> --out day/initial.json
  ```
  輸入 JSON 每艘寫 GMAT 欄位：`{"pursuer": {"DateFormat": "UTCGregorian", "Epoch": "09 Nov 2026 00:00:00.000",
  "CoordinateSystem": "EarthFixed", "DisplayStateType": "SphericalAZFPA", "RMAG": ..., "RA": 經度, "DEC": 緯度,
  "VMAG": ..., "AZI": ..., "FPA": ...}, "evader": {...}}`（FPA 水平 = 90°）。
- 什麼格式都讀不了：`uv run python copilot.py final manual --out day/initial.json`，照提示逐項輸入 12 個數字。

**3. 角色選擇器**
```bash
uv run python tools/role_select.py day/<初始狀態檔> --rules day/announced.json --workers 4 --budget-sec 150
```
（`<初始狀態檔>` 要是 JSON：`day/initial.json`，或 parse 確認過的 JSON 檔。）
看三樣：
1. **題目特徵**（安全空域對抗）：出現「6 發都沿速度方向推滿也到不了安全空域」→ **直接選追方**（躲方必輸）。
2. **最後一行建議**（`建議選：…`）。
3. 我方躲方的**安全證書比例**：每回合都接近 100% 才算穩。

**選角色原則**（E28、E29 評測）：預設選**躲方**。我們的躲方每回合算「追方怎麼推都碰不到」的推力，在 ΔV_lim 100–500、
R_cap 1–20 km、T_round 600–3600 s 全範圍，加上安全空域蓋住追方 a、很窄（0.02 發寬）、要穿過追方軌道、很遠（5 發）、
初始距離很近、台灣上空入軌（epoch 差 0–24 h）等對抗題，對任何追方都沒被抓過。只有三種情況改選追方：
1. 選擇器說安全空域到不了；
2. 選擇器我方躲方對 capture_pursuer 勝率明顯低於 100%；
3. 安全證書比例 < 90%。

**4. 建 session**（角色定了才做；之後每回合都用這個檔）
```bash
uv run python copilot.py final new --rules day/announced.json --initial day/<初始狀態檔> --role evader --out day/session.json
```
（我方是追方就 `--role pursuer`。兩艘 epoch 不同時會印「傳播了幾秒」，要跟公告對得上。）

---

## 四、每回合流程（10 分鐘 × 6）

每回合：**讀 USB 檔 → advise → 手寫提交行 → 核對 → 交 → 公告後 announce**。

| 時間 | 誰 | 做什麼 |
|---|---|---|
| 0–2 分 | 記錄 | 把主辦的回合起點狀態檔複製到 `day/`（第 1 回合用初始狀態，不用 `--state`） |
| 2–4 分 | 主控 | `advise`（Corn 實測 1–2 s；Mac 更快） |
| 4–6 分 | 主控＋驗證 | 看重驗結果與三件事（下面） |
| 6–8 分 | 記錄 | 照 `提交：` 那行**手寫**；驗證唸數字、記錄核對正負號與小數點 |
| 8–9 分 | 記錄 | 交出；保留抄本 |
| 公告後 | 主控 | `announce`，輸入主辦公告的雙方實際 Δv |

**advise**
```bash
uv run python copilot.py final advise day/session.json --state day/<本回合起點狀態檔>
```
- 第 1 回合不加 `--state`（用建 session 時的初始狀態）。
- 狀態檔讀不了：改 `--manual`（逐項輸入）。
- 很趕：加 `--fast`。

**看三件事再交**
1. `重驗：通過`。沒通過會有 `！！！ 警告` 和替代提交值，照工具給的最後一行交。
2. 我方躲方：`安全證書：成立`；最後一回合看 `提交值推完 a = ...` 在安全空域 [lo, hi] 內。
   我方追方：`估計命中率` 只是參考，照交。
3. `一致性檢查：通過`（第 2 回合起）。出現「疑似錯誤」：照提示核對單位（m／km）、追方逃方有沒有對調、座標系有沒有轉
   （EarthFixed 要先轉）、時間有沒有對。核對後仍以官方狀態為準，繼續 advise。

**提交行**：最後一行 `提交：逃方, 3, 135.3134, -46.4445, -204.9590` → 手寫 `逃方, 3, 135.3134, -46.4445, -204.9590`。
上面一行「手寫核對」把三個數字分開、帶正負號再印一次，抄完逐個對。

**announce**（主辦公告這回合雙方實際 Δv 後）
```bash
uv run python copilot.py final announce day/session.json --opponent-dv <X> <Y> <Z> --our-dv <X> <Y> <Z> --state day/<下一回合起點狀態檔>
```
- `--our-dv` 是主辦公告的「我方實際 Δv」：跟我們提交的不同會警告（抄錯或被縮放）。
- `--state` 有就加（立刻做一致性檢查）；沒有也可以，下回合 advise 時再核對。
- 對手的推法會被分類（不推／背向／法向／徑向／往安全空域推／其他）並累積；我方是追方時下回合會照這個調猜法。

**整場摘要**：`uv run python copilot.py final show day/session.json`

---

## 五、分工（3 人）

| 角色 | 工作 |
|---|---|
| 主控 | 操作 Mac、跑 parse／role_select／advise／announce、決定採用 |
| 記錄 | 複製 USB 檔、填規則檔、手寫提交行、保留每回合抄本 |
| 驗證 | 唸數字核對（單位、正負號、小數點）、看重驗與一致性檢查、計時（每回合第 6 分鐘提醒） |

---

## 六、提交格式要改時

`configs/final_format.json`（建 session 時讀；改了要**重建 session**，或建 session 時加 `--format <檔>`）：
```json
{"role_names": {"pursuer": "追方", "evader": "逃方"}, "round_base": 1, "decimals": 4, "dv_margin_mps": 0.05,
 "template": "{role}, {round}, {dvx}, {dvy}, {dvz}"}
```
- 角色寫英文：`"role_names": {"pursuer": "Pursuer", "evader": "Evader"}`
- 回合從 0 算：`"round_base": 0`
- 只要兩位小數：`"decimals": 2`（工具仍會確認四捨五入後不超過上限、結論不變）
- `template` 只能用 `{role} {round} {dvx} {dvy} {dvz}` 五個欄位。

---

## 七、戰術原則（E27–E29 評測）

**躲方**（預設角色）
- 每回合挑「追方這回合怎麼推都碰不到」的推力（安全證書），在安全的選項裡把半長軸帶向安全空域，最後一回合精準落在區間
  （工具會列「推完 a 剛好在區間中心」的候選，窄到 0.02 發寬也落得進去）。照工具交就好。
- 工具在接近最優的安全選項間隨機挑，對手猜不到；不要手動改成「每回合都推同一個方向」。

**追方**
- 對會算證書的躲方抓不到（評測 0%）；機會只來自對手犯錯：不懂安全空域（最後 a 不在區間 → sma_out，我方贏）、
  直覺閃法（背向全推、法向、徑向、往安全空域推）被我們的追方抓 30–62%。
- 工具會依對手前幾回合的推法調猜法；照交就好。

---

## 八、故障應變

| 狀況 | 做法 |
|---|---|
| `parse` 讀不了 USB 檔 | 看錯誤訊息（它會說第幾列第幾欄、看到哪些船名）；加 `--names`／`--order`；再不行 `final manual` 手動輸入 |
| 數字看起來是公尺或 m/s | 工具會擋並說明；換單位重填 |
| 經緯高狀態 | `tools/gmat_state_convert.py` 轉（第三節）；GMAT 找不到時加 `--gmat-console "/Users/corn/Documents/GMAT R2026a/bin/GmatConsole"` |
| 一致性檢查「疑似錯誤」 | 照提示核對；以官方狀態為準繼續 |
| 重驗未通過 | 交工具給的替代值（最後一行永遠是可以交的） |
| 工具當掉 | 重開終端機重跑同一個指令（session 檔每步都存）；仍不行換備機（session 檔用 USB 帶過去） |
| 對手 Δv 被縮放 | 正常；`announce` 輸入主辦公告的實際值 |
| 時間不夠 | `advise --fast`；最壞情況照上一回合的提交方向推（躲方）或不推（追方），但一定要交 |

---

## 九、賽前 Mac 檢查（只能在 Mac 上做；Corn 已驗過的不用重做）

- [ ] `git pull && uv sync && uv run pytest`（全綠，含 GMAT 測試；GmatConsole 路徑 `/Users/corn/Documents/GMAT R2026a/bin/GmatConsole`）
- [ ] **拔網路**，照本手冊用彩排工具各跑一場（追方、躲方），每回合計時 10 分鐘：
  ```bash
  uv run python tools/final_rehearsal.py --role evader --opponent capture_pursuer --workdir day_rehearsal_e
  uv run python tools/final_rehearsal.py --role pursuer --opponent heuristic_evader --workdir day_rehearsal_p
  ```
  它用 GMAT 二體當真實世界、每回合寫一個官方格式的狀態檔，我方完整走 `copilot.py final`；`day_rehearsal_*/` 裡的檔案可以
  拿來手動再走一次 advise／announce 練手寫。
- [x] （11-04 Mac 實測：預設 126 s、`--fast` 39 s，200 局）`role_select.py` 在 Mac 的牆鐘時間（預設與 `--fast` 各一次，`--workers 4`），填回第三節：Corn 90 s／6.4 s（40 局×5 組）
- [x] （11-04 Mac 彩排實測 1.3–4.9 s）`advise` 單次時間（Corn 1–2 s），第一次執行會多 numba 編譯時間：比賽前先各跑一次 `final advise` 暖機
- [ ] 電池續航：插電／不插電各跑一次 role_select，看耗電；確認會場插座或帶行動電源
- [ ] 睡眠／省電設定：比賽中不要自動睡眠、螢幕不要自動鎖
- [ ] `configs/final_format.json` 的角色名稱照工作人員答案改好（第二節 #8）
- [ ] 印出本手冊第三、四、八節、紙筆（手寫提交）
- [ ] 備機也做一次上面全部
