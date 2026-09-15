# ROADMAP —— 到 2026-11-09 決賽

進度同步在 Linear 專案 `ODC_GMAT_DRL`（team Happpycorn）。

## 策略主軸
1. 規則未公告 → 兩條腿走路：**解析規劃器**（不用訓練、公告即可用，保底）+ **rule-conditioned RL**（訓練時抽規則、規則放進觀測）。
2. 核心物理量是**追擊所需 Δv**：局勢評估、塑形、躲者啟發式、當天戰況指標。
3. 當天真正的交付物是 **copilot**（建議脈衝 + 推演 + GMAT 驗證腳本），RL 只是其中一個大腦。

## 階段

| 階段 | 內容 | 狀態 | Linear |
|---|---|---|---|
| 0 | env 正確性修復 + 遊戲核心重構（連續事件偵測、Δv 裁切、terminated、隨機化、LVLH 觀測） | ✅ 2026-09-15 | HAP-101 |
| 1 | 物理工具箱：numba Lambert（對 poliastro 機器精度）、追擊所需 Δv、座標系 | ✅ 2026-09-15 | HAP-102 |
| 2 | 解析 agent（LambertPursuer / DvEvader / 極小極大）+ 對打評測系統 | ✅ 2026-09-15（極小極大待改進） | HAP-103 |
| 2.5 | GMAT 重播一致性（< 10 m） | ✅ 待官方 ForceModel 確認 | HAP-56 |
| 3 | self-play 訓練管線（BC → curriculum → league）與長時間訓練 | ⏳ 進行中 | HAP-54 |
| 4 | 選上場策略：RL vs 解析 vs 混合；壓力測試（規則偏移、非理性對手） | ☐ | HAP-54 |
| 5 | copilot CLI + 當天手冊 | ✅ 初版 | HAP-104 / HAP-55 |
| 6 | 演練、規則公告後鎖定、凍結 | ☐ | HAP-55 |

## 待辦（依優先序）
- [ ] 監看 sp1 訓練；RL 對解析基準的勝率曲線（runs/sp1/metrics.jsonl）
- [ ] 規則平衡掃描：追/躲單發上限比 × 燃料比 × 捕獲半徑 → 追者勝率地圖（當天查表）
- [ ] 改進極小極大葉值（用全程 need 或 rollout 值）
- [ ] 追者「最小化最近距離」模式（若官方計分看距離）
- [ ] 回合內多發的規則變體（若官方允許）
- [ ] 規則公告（HAP-50）→ `configs/rules_final.json` → 重跑評測 → 微調 RL → 凍結 `models/`
