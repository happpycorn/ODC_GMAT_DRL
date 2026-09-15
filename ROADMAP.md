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
- [ ] 監看 sp3 訓練（guided 追者 + BC 後重設探索幅度）；RL 對解析基準的勝率曲線（runs/sp3/metrics.jsonl）→ promote_model
- [x] 規則平衡掃描工具（tools/balance_sweep.py）；第一張地圖：躲者單發上限 × 躲者燃料
- [x] Rollout 規劃器（agents/rollout.py）取代極小極大當 copilot 強腦
- [x] 評測 rollout_pursuer / rollout_evader：追者對 DvEvader 50%（Lambert 17%）、躲者對 Lambert 存活 93% → copilot 預設大腦
- [x] capture_mode（continuous / endpoint）規則變體
- [ ] RL 策略當 rollout 的候選或對手模型（sp3 完成後）
- [ ] rollout 在隨機規則分布與 official_sample 幾何下的評測
- [ ] 追者「最小化最近距離」模式（若官方計分看距離）
- [ ] 回合內多發的規則變體（若官方允許）
- [ ] 規則公告（HAP-50）→ `configs/rules_final.json` → 重跑評測 → 微調 RL → 凍結 `models/`
