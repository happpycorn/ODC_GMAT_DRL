# ROADMAP —— 到 2026-11-09 決賽

進度同步在 Linear 專案 `ODC_GMAT_DRL`（team Happpycorn）。實驗數字見 [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)。

## 策略主軸
1. 規則未公告 → 兩條腿走路：**解析/推演規劃器**（不用訓練、公告即可用，保底）+ **rule-conditioned RL**（訓練時抽規則、規則放進觀測）。
2. 核心物理量是**追擊所需 Δv**；但勝負取決於很久以後的燃料消耗 → 最強大腦是**推演到終局**的 rollout 規劃器。
3. 當天真正的交付物是 **copilot**（建議脈衝 + 推演 + GMAT 驗證腳本），RL 只是其中一個大腦。

## 階段

| 階段 | 內容 | 狀態 | Linear |
|---|---|---|---|
| 0 | env 正確性修復 + 遊戲核心重構 | ✅ 09-15 | HAP-101 |
| 1 | 物理工具箱：numba Lambert、追擊所需 Δv、座標系 | ✅ 09-15 | HAP-102 |
| 2 | 解析 agent + 對打評測 + rollout 規劃器 | ✅ 09-15 | HAP-103 |
| 2.5 | GMAT 重播一致性（< 10 m） | ✅ 待官方 ForceModel | HAP-56 |
| 3 | self-play 訓練（BC → curriculum → league） | ✅ sp3 完成：持平專家、未超越（E9） | HAP-54 |
| 4 | RL × rollout 整合、決定 RL 當天角色 | ✅ 無增益 → 主腦純 rollout（E11） | HAP-105 |
| 4.1 | 規則平衡地圖 → 當天查表 | ✅ 6 張地圖 + rollout 確認（E8、E10） | HAP-106 |
| 4.2 | Exploitability 測試 | ✅ rollout 追者對稱規則 +44（賽局結構）；逃逸躲者不採用當預設（E12） | HAP-108 |
| 5 | copilot CLI + 當天手冊 | ✅ 初版 | HAP-104 / HAP-55 |
| 5.1 | copilot 狀態匯入（GMAT 報表）、推演排序 ★ 推薦、rollout 平行化 | ✅ | HAP-109 / HAP-104 |
| 5.2 | 當天流程彩排（GMAT 當真實世界跑完整 SOP） | ✅ 兩場皆勝、決策最長 ~14 s（E13） | HAP-55 |
| 6 | 規則公告 → 鎖定參數 → 演練 → 凍結 | ☐ 阻塞於 HAP-50 | HAP-50 / HAP-55 |
| — | 規則變體：一回合多發 | ☐ 視 HAP-50 | HAP-107 |

## 近期待辦
- [x] sp3 → `tools/promote_model.py` → RL 當 rollout 候選/對手模型的評測（HAP-105：無增益）
- [ ] 對手風格辨識：從對手前幾回合行為挑對手模型（E11 顯示猜中對手 +9 個百分點）
- [x] 平衡地圖六張 + rollout 確認（HAP-106）
- [x] copilot `import` 讀 GMAT 報表、rollout 平行化（HAP-109）
- [x] Exploitability：rollout 大腦被針對時多弱（HAP-108）
- [ ] 規則公告後：在正式規則上重跑 E7/E11/E12 的關鍵對打（大腦選擇可能隨規則翻轉，例如逃逸躲者）
- [ ] 規則公告（HAP-50）→ `configs/rules_final.json` → 重跑評測/平衡 → 微調 RL → 凍結 `models/`
