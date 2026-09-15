# ODC_GMAT_DRL —— 軌道設計競賽「決賽」追逃戰的 DRL 專案

第一屆軌道設計競賽（TASA / 淡江）**決賽（四強賽）** 的深度強化學習專案。初賽 9/5 已晉級（57 隊取前 8）；決賽 **2026-11-09 @ 大臺南會展中心**。

**這份講怎麼用（裝/跑/佈局）。想知道問題本質、有沒有理論優解、我們為什麼這樣訓練 → 看 [METHODOLOGY.md](METHODOLOGY.md)。** 決賽賽制的官方情報與架構決策在 Linear 專案 `ODC_GMAT_DRL` 的文件裡。

---

## 決賽賽制（一段話）

兩艘太空船在地球重力場下**追逐 vs 躲避**，當天**抽籤**決定我方是追者還是躲者，**回合交替**下機動指令（一段時間一方動、交替）。追者在時間+燃料限制內追上即勝；躲者全程沒被追上即勝。電競模式、會場公用電腦下指令、GMAT 模擬。詳細計分規則官方尚未公告。

---

## 為什麼是 RL

對手會反應、不是被動目標，這是**零和微分賽局**：理論上有最優（賽局值 + 鞍點策略），但完整問題沒有封閉解，用 self-play 數值逼近。細節見 [METHODOLOGY.md](METHODOLOGY.md)。

---

## Repo 佈局

```
physics/         軌道物理
  propagator.py    get_r0_v0、propagate（DOP853）          ← vendored 自 Planner（PROVENANCE.md）
  core_math.py     動力學、J2/J3/J4、VNB、近地點檢查        ← vendored
  scorer.py        初賽官方計分公式                          ← vendored
  lambert.py       numba Izzo Lambert（多圈），與 poliastro 比對到機器精度
  intercept.py     追擊所需 Δv 掃描（TOF × 圈數 × 分支 + J2 打靶）
  coast.py         雙船滑行 + 窗口內連續偵測捕獲/撞地/最近接近
  frames.py        RSW(LVLH)、VNB、rv2coe
game/            純遊戲核心（與 gym 解耦，搜尋/評測/copilot 共用）
  rules.py         Rules（佔位規則數字）+ RuleRanges（規則分布）
  scenarios.py     初始幾何家族（near_coplanar / inclined / wild / official_sample…）
  core.py          Game：回合推進、Δv 裁切、燃料帳、勝負判定、歷程紀錄
  obs.py           RL 觀測（LVLH、正規化、規則參數、最近接近、追擊所需 Δv）
agents/          策略：coast / random / LambertPursuer / DvEvader（+ RL 包裝）
envs/final_env.py  gym 包裝：單 agent + 可插拔對手、role 可隨機、勢能型塑形
tests/           pytest（uv run python -m pytest tests）
tools/           離線驗證腳本（例：Lambert vs poliastro）
METHODOLOGY.md   理論與訓練方法論
```

> 規則數字全是**佔位**（`game/rules.py`），官方公告（HAP-50）後填 `Rules(...)` 即可；在那之前訓練用 `RuleRanges` 隨機抽規則並把規則放進觀測。

---

## 安裝與執行

本專案用 [`uv`](https://github.com/astral-sh/uv) 管理環境（Python 3.10）。

```bash
pip install uv
uv sync          # 每次 git pull 後跑一次，讓環境精確等於 lockfile
```

跑測試：

```bash
uv run pytest
```

**GMAT 不在訓練迴圈裡**——訓練用 `physics/` 的純 numba 引擎（快、且與 GMAT 交叉驗證到公尺級）；GMAT 只在最終驗證階段用（尚未接，Linear HAP-56）。

---

## 現況（2026-09）

- ✅ 物理引擎接好（`physics/`），env 用真實軌道傳播、`check_env` 通過、SAC 端到端可訓練（HAP-51 / HAP-52）。
- ✅ 決賽環境 `final_env.py`（回合交替追逃、單 agent + 可插拔對手、勝負判定）骨架完成（HAP-53）。
- ✅ 遊戲核心重構 + 正確性修復：窗口內連續事件偵測、Δv 裁切、超時=terminated、規則/幾何隨機化、LVLH 觀測（HAP-101）。
- ✅ 物理工具箱：numba Lambert、追擊所需 Δv、最近接近、座標系；解析 LambertPursuer / DvEvader（HAP-102）。
- ⏳ 對打評測系統 + 極小極大搜尋（HAP-103）、self-play 訓練管線（HAP-54）。
- ⏳ 決賽計分/規則細節待官方公告（HAP-50）。

進度與待辦以 Linear 專案 `ODC_GMAT_DRL`（team Happpycorn / HAP）為準。
