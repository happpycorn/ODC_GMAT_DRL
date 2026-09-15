# ODC_GMAT_DRL —— 軌道設計競賽「決賽」追逃戰

第一屆軌道設計競賽（TASA / 淡江）**決賽（四強賽）** 的物理、解析策略、DRL 訓練與當天作戰工具。初賽 9/5 已晉級（57 隊取前 8）；決賽 **2026-11-09 @ 大臺南會展中心**。

- **怎麼用** → 這份
- **問題本質、理論、為什麼這樣做、實測教訓** → [METHODOLOGY.md](METHODOLOGY.md)
- **當天流程** → [CONTEST_DAY_FINAL.md](CONTEST_DAY_FINAL.md)
- **做到哪、接下來做什麼** → [ROADMAP.md](ROADMAP.md)（進度也同步在 Linear 專案 `ODC_GMAT_DRL`）
- **每個實驗量到什麼** → [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)

---

## 決賽賽制（一段話）

兩艘太空船在地球重力場下**追逐 vs 躲避**，當天**抽籤**決定我方角色，**回合交替**下機動指令。追者在時間+燃料限制內追上即勝；躲者撐到時限即勝。電競模式、會場公用電腦下指令、GMAT 模擬。**詳細規則數字官方尚未公告**——所有數字集中在 `game/rules.py`，並用規則分布訓練/評測。

---

## 安裝

```bash
pip install uv
uv sync            # 每次 git pull 後跑一次
uv run pytest      # 43 項；有裝 GMAT 的機器會多跑 GMAT 重播一致性測試
```

GMAT（只用於驗證，不在訓練迴圈裡）預設路徑 `~/software/GMAT/GMAT/R2026a/bin/GmatConsole`，可用環境變數 `GMAT_CONSOLE` 覆寫。

---

## 常用指令

```bash
# 對打評測：追者 × 躲者 × 同一批隨機（規則, 幾何），輸出 reports/<name>.md
uv run python evaluate.py --pursuers lambert_pursuer,minimax_pursuer \
    --evaders coast,random,dv_evader,minimax_evader_fast --games 60 --rules default --scenario mixed

# 當天 copilot：局勢檔 → 戰況 + 建議脈衝（ECI/VNB/RSW）+ 推演 + GMAT 驗證腳本
uv run python copilot.py init state.json
uv run python copilot.py advise state.json --gmat burn.script --verify
uv run python copilot.py drill --role evader --opponent lambert_pursuer     # 整場演練

# GMAT 一致性：整局機動丟進 GMAT 重播、逐回合比位置
uv run python tools/gmat_verify.py --pursuer lambert_pursuer --evader dv_evader

# Self-play 訓練（BC 暖啟動 → curriculum → league），產物在 runs/<name>/
uv run python train_selfplay.py --name sp1 --envs 12 --iters 12
# 挑最好的快照確認評測後部署到 models/
uv run python tools/promote_model.py --run sp1 --games 60

# 規則平衡掃描（規則網格上的追者勝率地圖）
uv run python tools/balance_sweep.py --axis max_dv_evader_mps=150,375,750,1500 --axis fuel_evader_mps=750,1500,3000
```

Agent 規格字串：`coast`、`random`、`lambert_pursuer`、`lambert_pursuer_fast`、`dv_evader`、`dv_evader_fast`、`minimax_pursuer`、`minimax_evader`、`minimax_evader_fast`、`rollout_pursuer`、`rollout_evader`、`sb3:<模型.zip>`，或 JSON（例 `{"name":"lambert_pursuer","time_weight_mps":60}`、`{"name":"pool","specs":[...]}`）。

---

## Repo 佈局

```
physics/           軌道物理
  propagator.py      get_r0_v0、propagate（DOP853）         ← vendored 自 Planner（PROVENANCE.md）
  core_math.py       動力學、J2/J3/J4、VNB、近地點檢查       ← vendored
  scorer.py          初賽官方計分公式                         ← vendored
  lambert.py         numba Izzo Lambert（多圈），與 poliastro 比對到機器精度
  intercept.py       追擊所需 Δv 掃描（TOF × 圈數 × 分支 + J2 打靶）
  coast.py           雙船滑行 + 窗口內連續偵測捕獲/撞地/最近接近
  frames.py          RSW(LVLH)、VNB、rv2coe
game/              純遊戲核心（與 gym 解耦；搜尋、評測、copilot 共用）
  rules.py           Rules（佔位規則）+ RuleRanges（規則分布）
  scenarios.py       初始幾何家族（near_coplanar / inclined / wild / official_sample / default）
  core.py            Game：回合推進、Δv 裁切、燃料帳、勝負、歷程、中途快照
  obs.py             RL 觀測（LVLH、正規化、規則參數、最近接近、追擊所需 Δv）
  actions.py         RL action ↔ Δv
agents/            策略
  base.py            Agent 介面、coast、random、PoolAgent（對手池）
  analytic.py        LambertPursuer、DvEvader、存活檢查/救命推力、追擊所需 Δv
  search.py          2-ply 極小極大（實驗性）
  rollout.py         Rollout 規劃器：候選脈衝 × 對手模型推演到終局，挑最壞情況最好
  rl.py              SB3Agent（訓練好的模型當 agent）
envs/final_env.py  gym 包裝：單 agent + 可插拔對手、role 可隨機、勢能型塑形
evaluation/        對打評測系統
tools/             gmat_verify.py（GMAT 重播）、compare_lambert_poliastro.py
configs/           rules_template.json（當天填 rules_final.json）
reports/           評測報表（.md 進 git）
evaluate.py  copilot.py  train_selfplay.py
tests/             pytest
```

---

## 現況（2026-09-15）

- ✅ 物理：vendored DOP853 + 自寫 Lambert / 攔截掃描 / 連續事件偵測；**GMAT 重播位置差 < 10 m**（degree 0/2/4）
- ✅ 遊戲核心重構 + env 正確性修復（HAP-101）、物理工具箱（HAP-102）
- ✅ 解析 agent + 對打評測系統（HAP-103）；預設規則下 LambertPursuer 對被動目標 92% 捕獲
- ✅ copilot CLI（HAP-104）、當天手冊初版（HAP-55）
- ⏳ self-play 訓練（HAP-54）進行中；決賽規則待官方公告（HAP-50）
