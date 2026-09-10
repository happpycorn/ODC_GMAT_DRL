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
envs/            Gym 環境
  base_env.py      共用底座：初始化雙方軌道、施加脈衝、傳播、組觀測、燃料/違規/時間帳
  preliminary_env.py  初賽語意（B 攔截被動 A）——驗證物理與底座接得起來的場景
  final_env.py     ★ 決賽核心：回合交替追逃、單 agent + 可插拔對手、勝負判定
  baselines.py     解析/啟發式基準對手（coast / naive_pursuer / naive_evader）
physics/         軌道物理引擎（vendored 自 ODC_GMAT_Planner，見 PROVENANCE.md）
  propagator.py    get_r0_v0（六根數→r,v）、propagate（DOP853）
  core_math.py     動力學、J2/J3/J4、VNB、撞地檢查（逐字複製）
  scorer.py        官方計分公式（逐字複製）
tests/           煙霧測試（uv run python tests/test_final_env.py）
train.py         SAC + Optuna 超參搜尋（骨架，目前針對 preliminary_env）
METHODOLOGY.md   理論與訓練方法論
```

> `final_env.py` 用**佔位參數**搭好了「結構對」的骨架（回合交替、雙方觀測、勝負判定都可跑、check_env 通過）。規則數字（窗口長度、Δv/燃料上限、捕獲半徑、初始軌道、計分）待官方公告（HAP-50）後填入；self-play 訓練管線是 HAP-54。

---

## 安裝與執行

本專案用 [`uv`](https://github.com/astral-sh/uv) 管理環境（Python 3.10）。

```bash
pip install uv
uv sync          # 每次 git pull 後跑一次，讓環境精確等於 lockfile
```

跑超參搜尋（目前針對 `preliminary_env`）：

```bash
uv run train.py
```

**GMAT 不在訓練迴圈裡**——訓練用 `physics/` 的純 numba 引擎（快、且與 GMAT 交叉驗證到公尺級）；GMAT 只在最終驗證階段用（尚未接，Linear HAP-56）。

---

## 現況（2026-09）

- ✅ 物理引擎接好（`physics/`），env 用真實軌道傳播、`check_env` 通過、SAC 端到端可訓練（HAP-51 / HAP-52）。
- ✅ 決賽環境 `final_env.py`（回合交替追逃、單 agent + 可插拔對手、勝負判定）骨架完成、測試通過（HAP-53）。
- ⏳ self-play 訓練管線（curriculum + 凍結自我對打）建置中（HAP-54）。
- ⏳ 決賽計分/規則細節待官方公告（HAP-50）。

進度與待辦以 Linear 專案 `ODC_GMAT_DRL`（team Happpycorn / HAP）為準。
