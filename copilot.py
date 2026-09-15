"""決賽當天 copilot（HAP-104）：輸入當前局勢 → 建議機動 + 對多種對手模型的後續推演 + GMAT 驗證腳本。

當天流程（見 CONTEST_DAY_FINAL.md）：
  1. `copilot.py init state.json`             產生局勢檔範本，照官方畫面/報表填數字
  2. `copilot.py advise state.json`           看戰況、各大腦的建議脈衝、推演到比賽結束的結果
  3. `copilot.py advise state.json --gmat out.script [--verify]`
                                              產生「從現在狀態施加建議脈衝並滑行一窗口」的 GMAT 腳本，
                                              拿去會場測試電腦先跑（--verify 在本機 GMAT 比對）
  4. 對手動完、官方更新狀態後，改 state.json 再 advise

演練模式（不需要真比賽）：
  `copilot.py drill --role pursuer --opponent dv_evader --rules default`
  每回合印出建議並自動採用第一個大腦的建議，模擬整場；可 `--interactive` 手動選。

局勢檔（JSON）欄位：
  rules        規則（game/rules.py 的欄位；官方公告後填正式值）
  role         我方角色 pursuer / evader
  mover        現在輪到誰
  t_elapsed_sec, t_max_sec  比賽已經過 / 總時限（秒，從開賽起算）
  fuel_used_mps {"pursuer": .., "evader": ..}
  pursuer / evader: {"elements": {sma,ecc,inc,raan,aop,ta}} 或 {"r_km": [..], "v_kms": [..]}
                   （EarthMJ2000Eq；六根數的角度單位是度）
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

from agents import make_agent
from agents.analytic import need_horizon, orbit_survives, pursuer_need
from game.core import Game
from game.rules import Rules, other
from game.scenarios import DEFAULT_ORBIT_EVADER, DEFAULT_ORBIT_PURSUER, sample_scenario
from physics import EARTH_MU, RE_VAL, get_r0_v0
from physics.coast import closest_approach
from physics.frames import rsw_basis, rv2coe, vnb_basis

# 第一個是預設採用的大腦。rollout 規劃器是目前評測最強（reports/rollout_eval_default.md）：
# 追者對 DvEvader 50%（LambertPursuer 17%）、躲者對 LambertPursuer 存活 93%，決策 ~140 ms
DEFAULT_BRAINS = {"pursuer": ["rollout_pursuer", "lambert_pursuer",
                              {"name": "lambert_pursuer", "time_weight_mps": 60.0}],
                  "evader": ["rollout_evader", "dv_evader"]}
DEFAULT_OPP_MODELS = {"pursuer": ["coast", "dv_evader_fast", "dv_evader"],
                      "evader": ["coast", "lambert_pursuer", {"name": "lambert_pursuer", "time_weight_mps": 60.0}]}


# ------------------------------------------------------------------ 局勢檔
def template_state():
    rules = Rules()
    g = Game.from_elements(rules, DEFAULT_ORBIT_PURSUER, DEFAULT_ORBIT_EVADER)
    return {
        "_comment": "照官方畫面填。rules 欄位見 game/rules.py；位置可給 elements（度）或 r_km/v_kms（EarthMJ2000Eq）",
        "rules": rules.to_dict(),
        "role": "pursuer",
        "mover": "pursuer",
        "t_elapsed_sec": 0.0,
        "t_max_sec": g.t_max,
        "fuel_used_mps": {"pursuer": 0.0, "evader": 0.0},
        "pursuer": {"elements": dict(DEFAULT_ORBIT_PURSUER)},
        "evader": {"elements": dict(DEFAULT_ORBIT_EVADER)},
    }


def _rv(entry):
    if "elements" in entry:
        return get_r0_v0(**entry["elements"])
    return np.asarray(entry["r_km"], dtype=float), np.asarray(entry["v_kms"], dtype=float)


def game_from_state(st):
    rules = Rules.from_dict(st["rules"])
    rp, vp = _rv(st["pursuer"])
    re, ve = _rv(st["evader"])
    return Game.from_snapshot(rules, rp, vp, re, ve, t=st.get("t_elapsed_sec", 0.0), t_max=st["t_max_sec"],
                              used=st.get("fuel_used_mps"), mover=st.get("mover"))


def state_from_game(g, role):
    return {
        "rules": g.rules.to_dict(), "role": role, "mover": g.mover, "t_elapsed_sec": g.t, "t_max_sec": g.t_max,
        "fuel_used_mps": dict(g.used),
        "pursuer": {"r_km": g.r("pursuer").tolist(), "v_kms": g.v("pursuer").tolist()},
        "evader": {"r_km": g.r("evader").tolist(), "v_kms": g.v("evader").tolist()},
    }


# ------------------------------------------------------------------ 分析
def _perigee_alt(r, v, mu=EARTH_MU):
    c = rv2coe(r, v, mu)
    return c["sma"] * (1 - c["ecc"]) - RE_VAL if math.isfinite(c["sma"]) and c["sma"] > 0 else float("nan")


def situation(g):
    R = g.rules
    horizon = min(g.time_left, 2 * g.period("pursuer"))
    ca_d, ca_t, _ = closest_approach(g.r("pursuer"), g.v("pursuer"), g.r("evader"), g.v("evader"), horizon,
                                     60.0, g.mu, R.gravity_degree)
    need_s, tof_s = pursuer_need(g, horizon=need_horizon(g))
    need_f, tof_f = pursuer_need(g)
    B = rsw_basis(g.r("pursuer"), g.v("pursuer"))
    return {
        "t": g.t, "time_left": g.time_left, "mover": g.mover,
        "distance_km": g.distance(),
        "rel_pos_rsw_km (evader wrt pursuer)": (B @ (g.r("evader") - g.r("pursuer"))).round(3).tolist(),
        "coast_closest_approach_km": ca_d, "coast_closest_approach_in_sec": ca_t,
        "capture_radius_km": R.capture_radius_km,
        "pursuer_need_short_mps": need_s, "pursuer_need_short_tof": tof_s,
        "pursuer_need_full_mps": need_f, "pursuer_need_full_tof": tof_f,
        "fuel_left": {s: g.fuel_left(s) for s in ("pursuer", "evader")},
        "burn_cap": {s: g.burn_cap(s) for s in ("pursuer", "evader")},
        "perigee_alt_km": {s: _perigee_alt(g.r(s), g.v(s)) for s in ("pursuer", "evader")},
        "coast_is_safe": {s: orbit_survives(g, s, np.zeros(3)) for s in ("pursuer", "evader")},
    }


def rollout(g, side, first_dv, my_agent, opp_agent):
    """我方先推 first_dv，之後我方交給 my_agent、對手交給 opp_agent 下到比賽結束。"""
    h = g.clone()
    h.play_turn(first_dv)
    while not h.done:
        a = my_agent if h.mover == side else opp_agent
        h.play_turn(a.act(h, h.mover))
    s = h.summary()
    s["we_win"] = h.winner == side
    return s


def burn_formats(g, side, dv_eci_mps):
    r, v = g.r(side), g.v(side)
    return {
        "eci_mps": np.asarray(dv_eci_mps).round(4).tolist(),
        "eci_kms (EarthMJ2000Eq, like official Burn Table)": (np.asarray(dv_eci_mps) / 1000).round(7).tolist(),
        "vnb_kms (GMAT ImpulsiveBurn Axes=VNB)": (vnb_basis(r, v) @ dv_eci_mps / 1000).round(7).tolist(),
        "rsw_mps (radial, along-track, cross-track)": (rsw_basis(r, v) @ dv_eci_mps).round(3).tolist(),
        "magnitude_mps": float(np.linalg.norm(dv_eci_mps)),
    }


def advise(st, brains=None, opp_models=None, rollouts=True, log=print):
    g = game_from_state(st)
    side = st["role"]
    brains = brains or DEFAULT_BRAINS[side]
    opp_models = opp_models or DEFAULT_OPP_MODELS[side]
    out = {"situation": situation(g), "advice": []}
    if g.done:
        out["note"] = f"比賽已結束：{g.outcome}"
        return out
    if g.mover != side:
        out["note"] = f"現在輪到 {g.mover}，不是我方（{side}）——以下建議是假設我方現在行動"
        g.mover = side
    opps = [(o, make_agent(o)) for o in opp_models]
    for b in brains:
        agent = make_agent(b)
        t0 = time.perf_counter()
        dv = g.clip_dv(side, agent.act(g, side))
        entry = {"brain": b, "decide_sec": time.perf_counter() - t0, "burn": burn_formats(g, side, dv),
                 "safe_after_burn": orbit_survives(g, side, dv), "rollouts": []}
        if rollouts:
            for name, oa in opps:
                oa.reset(seed=0)
                entry["rollouts"].append({"opponent": name, **rollout(g, side, dv, agent, oa)})
        out["advice"].append(entry)
    return out


def print_advice(out, side):
    s = out["situation"]
    print("=" * 78)
    print(f"戰況  t={s['t']:.0f}s  剩 {s['time_left']:.0f}s  輪到 {s['mover']}  我方={side}")
    print(f"  距離 {s['distance_km']:.2f} km   純滑行最近接近 {s['coast_closest_approach_km']:.2f} km "
          f"@ +{s['coast_closest_approach_in_sec']:.0f}s（捕獲半徑 {s['capture_radius_km']} km）")
    print(f"  追者攔截所需 Δv：短程 {s['pursuer_need_short_mps']:.1f} m/s (tof {s['pursuer_need_short_tof']:.0f}s)"
          f"   全程 {s['pursuer_need_full_mps']:.1f} m/s (tof {s['pursuer_need_full_tof']:.0f}s)")
    print(f"  剩餘燃料 P {s['fuel_left']['pursuer']:.0f} / E {s['fuel_left']['evader']:.0f} m/s   "
          f"單發上限 P {s['burn_cap']['pursuer']:.0f} / E {s['burn_cap']['evader']:.0f}")
    print(f"  近地點高度 P {s['perigee_alt_km']['pursuer']:.0f} / E {s['perigee_alt_km']['evader']:.0f} km   "
          f"不推也安全 P={s['coast_is_safe']['pursuer']} E={s['coast_is_safe']['evader']}")
    if out.get("note"):
        print("  ⚠️ " + out["note"])
    for a in out["advice"]:
        b = a["burn"]
        print("-" * 78)
        print(f"大腦 {a['brain']}（{a['decide_sec']:.2f}s）  |Δv| = {b['magnitude_mps']:.2f} m/s  推完安全={a['safe_after_burn']}")
        print(f"  ECI  km/s : {b['eci_kms (EarthMJ2000Eq, like official Burn Table)']}")
        print(f"  VNB  km/s : {b['vnb_kms (GMAT ImpulsiveBurn Axes=VNB)']}")
        print(f"  RSW  m/s  : {b['rsw_mps (radial, along-track, cross-track)']}")
        for r in a["rollouts"]:
            print(f"    vs {str(r['opponent']):<40} → {r['outcome']:<14} {'WIN ' if r['we_win'] else 'LOSE'} "
                  f"t={r['t_end']:.0f}s  最近 {r['min_dist_km']:.1f} km  燃料用 P {r['used_pursuer_mps']:.0f} / E {r['used_evader_mps']:.0f}")


def _parse_specs(s):
    if not s:
        return None
    return [json.loads(t) if t.strip().startswith("{") else t.strip() for t in s.split(";" if ";" in s else ",")]


# ------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="產生局勢檔範本")
    p.add_argument("path")

    p = sub.add_parser("advise", help="讀局勢檔，給建議")
    p.add_argument("path")
    p.add_argument("--brains", default=None, help="逗號分隔 agent 規格（可含 sb3:path）")
    p.add_argument("--opponents", default=None, help="推演用的對手模型")
    p.add_argument("--no-rollout", action="store_true")
    p.add_argument("--gmat", default=None, help="把第一個大腦的建議輸出成 GMAT 腳本")
    p.add_argument("--verify", action="store_true", help="用本機 GmatConsole 跑腳本並比對")
    p.add_argument("--json", default=None, help="完整結果另存 JSON")

    p = sub.add_parser("drill", help="模擬整場演練")
    p.add_argument("--role", default="pursuer")
    p.add_argument("--opponent", default=None)
    p.add_argument("--rules", default="default", help="default / ranges / 規則 JSON 檔")
    p.add_argument("--scenario", default="near_coplanar")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--brains", default=None)
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--no-rollout", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd == "init":
        with open(args.path, "w") as f:
            json.dump(template_state(), f, indent=2, ensure_ascii=False)
        print(f"→ {args.path}")
        return 0

    if args.cmd == "advise":
        with open(args.path) as f:
            st = json.load(f)
        out = advise(st, _parse_specs(args.brains), _parse_specs(args.opponents), not args.no_rollout)
        print_advice(out, st["role"])
        if args.json:
            with open(args.json, "w") as f:
                json.dump(out, f, indent=2, default=float, ensure_ascii=False)
        if args.gmat and out["advice"]:
            from tools.gmat_verify import game_to_script, verify_game
            g = game_from_state(st)
            g.mover = st["role"]
            fresh = Game(g.rules.with_(t_max_sec=g.t + g.next_window() + 1.0), g.r("pursuer"), g.v("pursuer"),
                         g.r("evader"), g.v("evader"))
            fresh.mover = st["role"]
            fresh.used = dict(g.used)
            dv = np.asarray(out["advice"][0]["burn"]["eci_mps"])
            fresh.play_turn(dv)
            with open(args.gmat, "w") as f:
                f.write(game_to_script(fresh, os.path.abspath(os.path.splitext(args.gmat)[0] + "_report.txt")))
            print(f"→ GMAT 腳本 {args.gmat}（施加建議脈衝並滑行 {fresh.history[0]['coast_sec']:.0f}s）")
            if args.verify:
                v = verify_game(fresh)
                print(f"  GMAT 比對：位置差 {1000 * v['max_dpos_km']:.2f} m、窗口末距離 ours/GMAT = "
                      f"{v['final_dist_ours_km']:.4f} / {v['final_dist_gmat_km']:.4f} km")
        return 0

    if args.cmd == "drill":
        rng = np.random.default_rng(args.seed)
        from game.rules import RuleRanges
        if args.rules == "ranges":
            R = RuleRanges().sample(rng)
        elif args.rules == "default":
            R = Rules()
        else:
            R = Rules.from_dict(json.load(open(args.rules)))
        sc = sample_scenario(rng, args.scenario)
        g = Game.from_elements(R, sc.orbit_pursuer, sc.orbit_evader)
        side = args.role
        opp = make_agent(args.opponent or ("dv_evader" if side == "pursuer" else "lambert_pursuer"))
        brains = _parse_specs(args.brains) or DEFAULT_BRAINS[side]
        while not g.done:
            if g.mover != side:
                g.play_turn(opp.act(g, g.mover))
                continue
            st = state_from_game(g, side)
            out = advise(st, brains, None, not args.no_rollout)
            print_advice(out, side)
            k = 0
            if args.interactive:
                ans = input(f"採用第幾個大腦的建議？[0-{len(out['advice']) - 1}，或輸入 eci m/s 三個數字] ").strip()
                parts = ans.split()
                if len(parts) == 3:
                    g.play_turn(np.array([float(x) for x in parts]))
                    continue
                k = int(ans or 0)
            g.play_turn(np.asarray(out["advice"][k]["burn"]["eci_mps"]))
        print("=" * 78)
        print("比賽結束：", g.summary(), "我方", "勝" if g.winner == side else "敗")
        return 0


if __name__ == "__main__":
    sys.exit(main())
