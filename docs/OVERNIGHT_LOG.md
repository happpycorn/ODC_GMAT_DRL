# 夜間自主研究日誌（2026-10-20 起）

主 session 在這台主機的 `/home/corn/ODC_GMAT_DRL` 主 checkout 統籌，研究子任務各自在自己的 git worktree／分支上做，
驗收後合併進 master。每合併一項就在這裡追加一段（時間、做了什麼、結論與數字、commit）。
規則數字全是假設：四強賽官方規則尚未公布，決賽 2026-11-09。

## 22:10 開工

- 讀完 README / ROADMAP / CONTEST_DAY_FINAL / EXPERIMENTS（E14–E19）、兩個 repo 的記憶、排位賽規則摘要。
- master `7c9de70` 基準：`uv run pytest` 73 項全綠（含 GMAT）。機器 8 實體核心（16 SMT）、記憶體 11 GB。
- 先在 master 補三樣共用基礎，讓各子任務不用改同一個檔案：
  - `make_agent("py:模組:類別")`：新 agent 寫在自己的新模組，不必改 `agents/__init__.py` 的 REGISTRY。
  - `evaluation/stats.py` + `tools/paired_compare.py`：逐局配對與雙尾精確符號檢定（E16/E17 的 p 值可重現）。
  - `docs/notes/`：子任務的結果筆記，主 session 整合成 E20 之後的編號。
- 研究清單與排程：
  - 第一批（平行）：① 多發時放寬存活檢查（追者）② 躲者改進 ③ 規則敏感度地圖（250 m/s 級）
  - 之後依檔案不重疊排：④ 雙曲線／飛掠幾何 ⑤ copilot 整體策略評測與決策時間 ⑥ 全攝動彩排擴大
    ⑦ 對手風格辨識 ⑧ 排位版規則重訓 RL（sp4）⑨ 各項結論在另一組規則上再驗

## 22:20 第一批子任務開跑

- Linear：母卡 HAP-117；① HAP-118、② HAP-119、③ HAP-120（皆 In Progress）。
- 三個子任務各在自己的 worktree（`.claude/worktrees/agent-*`）。注意：worktree 預設從舊的 `origin/main`（6 月）開，brief 第 0 步改成先 `git merge --ff-only master`。
- master 逐位元基準（`80dc622`，主 checkout）：預設規則、ranking_like、ranking_like_2burn 各 6 局 × 6 配對，之後合併改到 agents/ 的分支時在同一 checkout 前後比對。

## 00:05 用量上限中斷後恢復

- 22:30 左右 5 個 max-effort 代理同時跑，約 30 分鐘用完 5 小時額度，四個子任務全部 429 中斷，空轉到 00:00 重置。
- 恢復：①②③ 用原代理接續（進度在各自 worktree：① 改前基準已跑完、② rollout 躲者基準已跑完、③ 改前基準要重跑）。
  ④ 雙曲線飛掠中斷前沒有改動，worktree 已被自動清掉，等前三項有一項完成再重開。
- 配速改成同時 2–3 個代理；長評測用 run_in_background 丟背景、等完成通知，不輪詢；brief／回報精簡。

## 05:30 合併 ① 多發存活檢查（HAP-118）與 ③ 規則地圖（HAP-120）

- ① `22a083f`、`74eb2e7`：`ODC_GAP_SURVIVAL` 放寬中間軌道存活檢查，**看不出增益、預設關**（E20；合計 8 vs 6 局，p=0.79）。
- ③ `a9b209c`…`b2ba315`：`tools/rule_map.py`、`tools/rule_lookup.py`、`configs/rule_map.json`（37 格）、`game/rule_presets.py`。
  250 m/s 級規則下窗口、T_max、一回合發數、燃料比都能翻盤（E21）；手冊第三、六節已改。
- 驗證順序（註明）：這兩項是**先快轉合併、後在 master 驗證**——子任務各自在 worktree 跑過 pytest（85、88 項），
  合併後主 checkout 再跑：pytest 97 項全綠；逐位元基準（default／ranking_like／ranking_like_2burn 各 36 局）與合併前 `80dc622` 完全相同。
  之後各項改成先在分支 worktree 跑 pytest（＋逐位元）全綠，再快轉 master。
- 也寫了第一版 `docs/OVERNIGHT_SUMMARY.md`（暫定）。
