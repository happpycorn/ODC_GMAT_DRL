"""當天流程彩排（HAP-55）：GMAT 當「真實世界」，每回合走一遍完整的當天 SOP。

每回合：
  1. 把到目前為止的所有機動丟給 GmatConsole 重播 → GMAT 報表（WriteHeaders=true 格式，模擬官方給的狀態）
  2. `copilot import` 讀報表更新 state.json（走真正的匯入/防呆路徑）
  3. 輪到我方：`copilot advise`（可選推演）→ 採用推演表排序第一的大腦；輪到對手：對手 agent 決策
     兩者都只看**從 GMAT 匯入的狀態**，不看我們引擎的內部狀態
  4. 把這發脈衝記進歷程，下一回合 GMAT 重播時一起施加

驗的是：匯入沒抄錯（GMAT 狀態 vs 引擎狀態差距）、每回合決策耗時、整條流程能不能在時限內跑完、
勝負判定在 GMAT 真實軌跡下是否一致。

例：
    uv run python tools/dress_rehearsal.py --role evader --opponent rollout_pursuer --max-turns 12
    uv run python tools/dress_rehearsal.py --role pursuer --opponent dv_evader --no-rollout
"""
import argparse
import json
import os
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HEADER = ("ShipP.ElapsedSecs ShipP.EarthMJ2000Eq.X ShipP.EarthMJ2000Eq.Y ShipP.EarthMJ2000Eq.Z "
          "ShipP.EarthMJ2000Eq.VX ShipP.EarthMJ2000Eq.VY ShipP.EarthMJ2000Eq.VZ "
          "ShipE.EarthMJ2000Eq.X ShipE.EarthMJ2000Eq.Y ShipE.EarthMJ2000Eq.Z "
          "ShipE.EarthMJ2000Eq.VX ShipE.EarthMJ2000Eq.VY ShipE.EarthMJ2000Eq.VZ")


def gmat_report_now(game, workdir):
    """GMAT 重播目前歷程，把最後一列寫成帶表頭的報表檔，回傳路徑。沒有歷程時直接寫初始狀態。"""
    from tools.gmat_verify import game_to_script, run_gmat
    if game.history:
        rows = run_gmat(game_to_script(game, "__REPORT__"))
        last = rows[-1]
    else:
        (rp, vp), (re, ve) = game.initial["pursuer"], game.initial["evader"]
        last = np.concatenate([[0.0], rp, vp, re, ve])
    path = os.path.join(workdir, f"gmat_turn{len(game.history):03d}.txt")
    with open(path, "w") as f:
        f.write(HEADER + "\n" + " ".join(f"{x:.12f}" for x in last) + "\n")
    return path


def main():
    import copilot
    from agents import make_agent
    from game.core import Game
    from game.rules import RuleRanges, Rules
    from game.scenarios import sample_scenario

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--role", default="pursuer", choices=["pursuer", "evader"])
    ap.add_argument("--opponent", default=None)
    ap.add_argument("--rules", default="default", help="default / ranges / 規則 JSON")
    ap.add_argument("--scenario", default="near_coplanar")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-rollout", action="store_true")
    ap.add_argument("--opponents", default=None, help="copilot 推演用的對手模型（逗號分隔）")
    ap.add_argument("--max-turns", type=int, default=0, help="> 0 時只彩排前 N 回合")
    ap.add_argument("--name", default=None)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    if args.rules == "ranges":
        R = RuleRanges().sample(rng)
    elif args.rules == "default":
        R = Rules()
    else:
        R = Rules.from_dict(json.load(open(args.rules)))
    sc = sample_scenario(rng, args.scenario)
    g = Game.from_elements(R, sc.orbit_pursuer, sc.orbit_evader)       # 帳本：歷程 + 燃料 + 勝負
    side = args.role
    opp_side = "evader" if side == "pursuer" else "pursuer"
    opp = make_agent(args.opponent or ("dv_evader" if side == "pursuer" else "rollout_pursuer"))
    opp.reset(seed=args.seed)
    opp_models = copilot._parse_specs(args.opponents)

    log = []
    t_start = time.time()
    with tempfile.TemporaryDirectory(prefix="rehearsal_") as wd:
        state_path = os.path.join(wd, "state.json")
        copilot.main(["init", state_path])
        while not g.done and (args.max_turns <= 0 or g.turn < args.max_turns):
            t0 = time.perf_counter()
            rep = gmat_report_now(g, wd)
            t_gmat = time.perf_counter() - t0
            copilot.main(["import", state_path, rep, "--pursuer-ship", "ShipP", "--evader-ship", "ShipE",
                          "--mover", g.mover, "--fuel-used", str(g.used["pursuer"]), str(g.used["evader"])])
            st = json.load(open(state_path))
            st["rules"] = R.with_(t_max_sec=g.t_max).to_dict()
            st["t_max_sec"] = g.t_max
            st["role"] = side
            truth = copilot.game_from_state(st)                         # 從 GMAT 匯入的「真實」狀態
            d_import = max(float(np.linalg.norm(truth.r(s) - g.r(s))) for s in ("pursuer", "evader"))

            t1 = time.perf_counter()
            if g.mover == side:
                out = copilot.advise(st, opp_models=opp_models, rollouts=not args.no_rollout, log=lambda *a: None)
                pick = out["advice"][0]
                if out.get("ranking"):
                    top = out["ranking"][0]["brain"]
                    pick = next(a for a in out["advice"] if a["brain"] == top)
                dv = np.asarray(pick["burn"]["eci_mps"])
                who = f"我方 {pick['brain']}"
            else:
                dv = truth.clip_dv(opp_side, opp.act(truth, opp_side))
                who = f"對手 {opp.name}"
            t_decide = time.perf_counter() - t1
            rec = g.play_turn(dv)
            log.append({"turn": rec["turn"], "side": rec["side"], "who": who, "dv_mps": rec["dv_mps"],
                        "gmat_sec": t_gmat, "decide_sec": t_decide, "import_vs_engine_m": 1000 * d_import,
                        "distance_km": rec["distance_after_km"], "outcome": rec["outcome"]})
            print(f"turn {rec['turn']:3d} {rec['side']:<8} {who:<45} |Δv|={rec['dv_mps']:7.1f}  "
                  f"GMAT {t_gmat:4.1f}s  決策 {t_decide:5.1f}s  匯入差 {1000 * d_import:6.2f} m  "
                  f"距離 {rec['distance_after_km']:9.2f} km  {rec['outcome'] or ''}", flush=True)

        final = gmat_report_now(g, wd) if g.history else None
        if final:
            vals = np.loadtxt(final, skiprows=1)
            d_gmat = float(np.linalg.norm(vals[1:4] - vals[7:10]))
        else:
            d_gmat = g.distance()

    s = g.summary()
    name = args.name or f"rehearsal_{side}_{args.seed}"
    lines = [f"# 當天流程彩排 {name}", "",
             f"- 我方 {side}、對手 `{opp.name}`、規則 `{args.rules}`、幾何 `{sc.family}`、seed {args.seed}、"
             f"推演 {'關' if args.no_rollout else '開'}",
             f"- 結局：**{s['outcome'] or '（彩排截斷）'}**（我方{'勝' if g.winner == side else ('敗' if g.winner else '—')}），"
             f"{s['turns']} 回合，t = {s['t_end']:.0f} s，最近距離 {s['min_dist_km']:.2f} km",
             f"- 最終距離：引擎 {g.distance():.4f} km / GMAT {d_gmat:.4f} km",
             f"- 匯入狀態 vs 引擎最大差：{max((r['import_vs_engine_m'] for r in log), default=0):.2f} m",
             f"- 我方決策耗時：平均 {np.mean([r['decide_sec'] for r in log if r['side'] == side] or [0]):.1f} s、"
             f"最長 {max([r['decide_sec'] for r in log if r['side'] == side] or [0]):.1f} s；"
             f"GMAT 重播每回合平均 {np.mean([r['gmat_sec'] for r in log] or [0]):.1f} s",
             f"- 總耗時 {time.time() - t_start:.0f} s", "",
             "| 回合 | 方 | 決策者 | |Δv| m/s | GMAT s | 決策 s | 匯入差 m | 距離 km | 事件 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in log:
        lines.append(f"| {r['turn']} | {r['side']} | {r['who']} | {r['dv_mps']:.1f} | {r['gmat_sec']:.1f} | "
                     f"{r['decide_sec']:.1f} | {r['import_vs_engine_m']:.2f} | {r['distance_km']:.2f} | {r['outcome'] or ''} |")
    os.makedirs("reports", exist_ok=True)
    with open(f"reports/{name}.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines[:9]))
    print(f"→ reports/{name}.md")


if __name__ == "__main__":
    main()
