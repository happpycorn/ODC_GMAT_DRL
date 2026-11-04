# 金／銅牌賽賽前準備

當天流程在 [CONTEST_DAY_FINAL](CONTEST_DAY_FINAL.md)。只能在 Mac 上做。

## 賽前 Mac 檢查

- [ ] `git pull && uv sync --python 3.12 && .venv/bin/python -m pytest` 全綠
- [ ] **拔網路**，追方、躲方各彩排一場，每回合計時 10 分鐘：
  ```bash
  .venv/bin/python tools/final_rehearsal.py --role evader --opponent capture_pursuer --workdir day_rehearsal_e
  .venv/bin/python tools/final_rehearsal.py --role pursuer --opponent heuristic_evader --workdir day_rehearsal_p
  ```
- [x] 計時：role_select 126 s（`--fast` 39 s）、advise 1.3–4.9 s（11-04 Mac）
- [ ] 比賽前先跑一次 `final advise` 暖機（numba 編譯）
- [ ] 插電／不插電各跑一次 role_select 看耗電
- [ ] 關自動睡眠、螢幕自動鎖
- [ ] 給主辦的提問（`ODC_Program/docs/ranking/QUESTIONS_FOR_ORGANIZER.md` 第 4、5、7 題）有回覆就照答案改 `configs/final_format.json`；沒回覆的抄在紙上，開賽時問
- [ ] 印出手冊第二、三、七節，帶紙筆
- [ ] 備機也做一次
