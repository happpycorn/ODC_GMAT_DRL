"""初始幾何產生器：回傳雙方六根數（SMA km, ECC, INC/RAAN/AOP/TA 度）。

官方決賽初始軌道未知，所以準備幾個家族並可混合抽樣：
  * default          —— 舊 final_env 的佔位軌道（固定，回歸測試用）
  * official_sample  —— 初賽官方範例題目（外星人 = 躲者、地球人 = 追者；兩軌道面夾 94°）
  * near_coplanar    —— 近圓、近共面、相位差 0.5–15°、高度差 ±150 km（典型交會問題）
  * inclined         —— 平面差到 ~20°、相位差到 ±40°
  * wild             —— 雙方獨立亂數 LEO（含逆行），類似官方範例那種刁鑽幾何
  * flyby            —— 排位賽型：躲者雙曲線飛掠（近地點高度 300–2000 km、v∞ 1–4 km/s）、追者近圓 LEO。
                        先選交會再倒推：躲者軌道上近地點附近、高度 ≤ 2000 km 的一點，開賽後 900–5400 s 經過；
                        追者圓軌道過這點附近（軌道面繞交會點徑向轉 ±60°、到達時間差 ±60 s、高度差 ±30 km、
                        軌道面側傾 ±0.3°）→ 二體倒推回 t=0。純滑行最近距離幾十～幾百 km，追者一發幾十～
                        兩百 m/s 就攔得到不動的躲者（有得打）。躲者開賽時在 FLYBY_BOUNDARY_KM 的 95% 以內，
                        配 `Rules(t_max_boundary_km=FLYBY_BOUNDARY_KM)` 時 T_max 約 2–3.5 小時。
  * flyby_pursuer    —— 同 flyby、角色對調（追者雙曲線、躲者 LEO）。
（mixed 只抽前三種 LEO 家族，flyby 家族要明指。）
"""
import math
from dataclasses import dataclass

import numpy as np

from physics import EARTH_MU, RE_VAL

MIN_PERIGEE_ALT_KM = 250.0

DEFAULT_ORBIT_PURSUER = {"sma": 7000.0, "ecc": 0.0, "inc": 0.0, "raan": 0.0, "aop": 0.0, "ta": 0.0}
DEFAULT_ORBIT_EVADER = {"sma": 7100.0, "ecc": 0.01, "inc": 0.5, "raan": 0.0, "aop": 0.0, "ta": 8.0}

# 官方 2026-08-28 參賽選手注意事項第八節範例題目（原文六根數）
OFFICIAL_SAMPLE_ALIEN = {"sma": 6978.0, "ecc": 0.0, "inc": 45.0, "raan": 0.0, "aop": 0.0, "ta": 0.0}
OFFICIAL_SAMPLE_HUMAN = {"sma": 6878.0, "ecc": 0.0, "inc": 135.0, "raan": 30.0, "aop": 0.0, "ta": 60.0}


@dataclass(frozen=True)
class Scenario:
    orbit_pursuer: dict
    orbit_evader: dict
    family: str


def _perigee_ok(o):
    return o["sma"] * (1.0 - o["ecc"]) - RE_VAL >= MIN_PERIGEE_ALT_KM


def _leo(rng, alt=(300.0, 1500.0), ecc_max=0.02, inc=None):
    sma = RE_VAL + rng.uniform(*alt)
    return {
        "sma": float(sma),
        "ecc": float(rng.uniform(0.0, ecc_max)),
        "inc": float(rng.uniform(0.0, 180.0) if inc is None else inc),
        "raan": float(rng.uniform(0.0, 360.0)),
        "aop": float(rng.uniform(0.0, 360.0)),
        "ta": float(rng.uniform(0.0, 360.0)),
    }


def _near(rng, base, d_alt, d_plane_deg, d_phase_deg, ecc_max):
    o = dict(base)
    o["sma"] = float(base["sma"] + rng.uniform(-d_alt, d_alt))
    o["ecc"] = float(rng.uniform(0.0, ecc_max))
    o["inc"] = float(np.clip(base["inc"] + rng.uniform(-d_plane_deg, d_plane_deg), 0.0, 180.0))
    o["raan"] = float((base["raan"] + rng.uniform(-d_plane_deg, d_plane_deg)) % 360.0)
    sign = 1.0 if rng.random() < 0.5 else -1.0
    o["ta"] = float((base["ta"] + sign * rng.uniform(*d_phase_deg)) % 360.0)
    return o


# ------------------------------------------------------------------ 雙曲線飛掠（排位賽型）
FLYBY_BOUNDARY_KM = 40000.0          # flyby 家族假設的任務邊界（地心距離）；configs/rulesets/flyby_*.json 用同一個值
FLYBY_PERIGEE_ALT_KM = (300.0, 2000.0)
FLYBY_VINF_KMS = (1.0, 4.0)
FLYBY_LEO_MAX_ALT_KM = 2000.0        # 交會點（= LEO 方軌道高度）上限
FLYBY_T_ENC_SEC = (900.0, 5400.0)    # 開賽到設計交會的時間
FLYBY_CROSS_DEG = 60.0               # LEO 方軌道面繞交會點徑向相對飛掠方軌道面轉的角度上限
FLYBY_MISS = {"dt_sec": 60.0, "dh_km": 30.0, "tilt_deg": 0.3}   # 讓純滑行差一點撞上的偏差上限


def _hyp_time_from_ta(e, a, nu, mu=EARTH_MU):
    """雙曲線（a < 0）真近點角 nu（弧度）→ 距近地點的時間（秒，近地點前為負）。"""
    F = 2.0 * math.atanh(math.sqrt((e - 1.0) / (e + 1.0)) * math.tan(nu / 2.0))
    return (e * math.sinh(F) - F) / math.sqrt(mu / (-a) ** 3)


def _hyp_ta_from_time(e, a, t, mu=EARTH_MU):
    """雙曲線距近地點 t 秒時的真近點角（弧度）：解 e·sinh F − F = M（Newton）。"""
    M = t * math.sqrt(mu / (-a) ** 3)
    F = math.asinh(M / e)
    for _ in range(100):
        dF = (e * math.sinh(F) - F - M) / (e * math.cosh(F) - 1.0)
        F -= dF
        if abs(dF) < 1e-14:
            break
    return 2.0 * math.atan(math.sqrt((e + 1.0) / (e - 1.0)) * math.tanh(F / 2.0))


def _rotate(axis, ang, x):
    """x 繞單位向量 axis 轉 ang 弧度（Rodrigues）。"""
    k = axis / np.linalg.norm(axis)
    return x * math.cos(ang) + np.cross(k, x) * math.sin(ang) + k * float(k @ x) * (1.0 - math.cos(ang))


def _pqw(inc, raan, aop):
    """六根數角度（度）→ 近焦點座標軸 P、Q、W（ECI），同 physics.get_r0_v0 的 Rz(raan)·Rx(inc)·Rz(aop)。"""
    i, O, w = (math.radians(x) for x in (inc, raan, aop))
    cO, sO, ci, si, cw, sw = math.cos(O), math.sin(O), math.cos(i), math.sin(i), math.cos(w), math.sin(w)
    P = np.array([cO * cw - sO * sw * ci, sO * cw + cO * sw * ci, sw * si])
    Q = np.array([-cO * sw - sO * cw * ci, -sO * sw + cO * cw * ci, cw * si])
    W = np.array([sO * si, -cO * si, ci])
    return P, Q, W


def _circular_through(u_hat, w_hat, radius, t_arrive, mu=EARTH_MU):
    """軌道面法向 w_hat、半徑 radius 的圓軌道，t_arrive 秒後經過方向 u_hat（須在軌道面內）→ 六根數。"""
    w = w_hat / np.linalg.norm(w_hat)
    node = np.cross([0.0, 0.0, 1.0], w)
    if np.linalg.norm(node) < 1e-9:
        node, raan = np.array([1.0, 0.0, 0.0]), 0.0
    else:
        node = node / np.linalg.norm(node)
        raan = math.degrees(math.atan2(node[1], node[0])) % 360.0
    u_tgt = math.atan2(float(u_hat @ np.cross(w, node)), float(u_hat @ node))
    u0 = u_tgt - t_arrive * math.sqrt(mu / radius ** 3)
    return {"sma": float(radius), "ecc": 0.0, "inc": math.degrees(math.acos(float(np.clip(w[2], -1.0, 1.0)))),
            "raan": raan, "aop": 0.0, "ta": math.degrees(u0) % 360.0}


def _flyby_pair(rng, boundary_km=FLYBY_BOUNDARY_KM):
    """(LEO 方六根數, 雙曲線方六根數)：先選交會點與時刻、再二體倒推回 t=0（見模組說明）。"""
    mu = EARTH_MU
    for _ in range(1000):
        rpe = RE_VAL + rng.uniform(*FLYBY_PERIGEE_ALT_KM)
        vinf = rng.uniform(*FLYBY_VINF_KMS)
        a = -mu / vinf ** 2
        e = 1.0 + rpe * vinf ** 2 / mu
        p = a * (1.0 - e * e)
        r_max = RE_VAL + FLYBY_LEO_MAX_ALT_KM
        nu_lim = math.acos(min(1.0, max(-1.0, (p / r_max - 1.0) / e))) if r_max > rpe else 0.0
        nu_enc = rng.uniform(-nu_lim, nu_lim)            # 交會點：近地點前後、高度 ≤ LEO 上限
        t_enc = rng.uniform(*FLYBY_T_ENC_SEC)
        nu0 = _hyp_ta_from_time(e, a, _hyp_time_from_ta(e, a, nu_enc) - t_enc)
        if p / (1.0 + e * math.cos(nu0)) > 0.95 * boundary_km:
            continue                                     # 開賽時要在任務邊界內
        hyp = {"sma": float(a), "ecc": float(e), "inc": math.degrees(math.acos(rng.uniform(-1.0, 1.0))),
               "raan": float(rng.uniform(0.0, 360.0)), "aop": float(rng.uniform(0.0, 360.0)),
               "ta": math.degrees(nu0) % 360.0}
        P, Q, W = _pqw(hyp["inc"], hyp["raan"], hyp["aop"])
        u_enc = math.cos(nu_enc) * P + math.sin(nu_enc) * Q
        r_enc = p / (1.0 + e * math.cos(nu_enc))
        # LEO 方：軌道面繞交會點徑向轉 ψ，再繞自己的沿軌道方向側傾一點（交會點落在軌道面外 → 側向偏差）
        w_leo = _rotate(u_enc, math.radians(rng.uniform(-FLYBY_CROSS_DEG, FLYBY_CROSS_DEG)), W)
        w_leo = _rotate(np.cross(w_leo, u_enc),
                        math.radians(rng.uniform(-FLYBY_MISS["tilt_deg"], FLYBY_MISS["tilt_deg"])), w_leo)
        aim = u_enc - float(u_enc @ w_leo) * w_leo        # 軌道面內最接近交會點的方向
        radius = r_enc + rng.uniform(-FLYBY_MISS["dh_km"], FLYBY_MISS["dh_km"])
        if radius - RE_VAL < MIN_PERIGEE_ALT_KM:
            continue
        leo = _circular_through(aim / np.linalg.norm(aim), w_leo, radius,
                                t_enc + rng.uniform(-FLYBY_MISS["dt_sec"], FLYBY_MISS["dt_sec"]))
        return leo, hyp
    raise RuntimeError("flyby 場景抽樣 1000 次都不合法，檢查參數")


def sample_scenario(rng: np.random.Generator, family: str = "mixed") -> Scenario:
    if family == "mixed":
        family = str(rng.choice(["near_coplanar", "inclined", "wild"], p=[0.5, 0.3, 0.2]))
    if family in ("flyby", "flyby_pursuer"):
        leo, hyp = _flyby_pair(rng)
        return Scenario(leo, hyp, family) if family == "flyby" else Scenario(hyp, leo, family)
    for _ in range(100):
        if family == "default":
            return Scenario(dict(DEFAULT_ORBIT_PURSUER), dict(DEFAULT_ORBIT_EVADER), family)
        if family == "official_sample":
            return Scenario(dict(OFFICIAL_SAMPLE_HUMAN), dict(OFFICIAL_SAMPLE_ALIEN), family)
        if family == "near_coplanar":
            p = _leo(rng, ecc_max=0.01, inc=rng.uniform(0.0, 100.0))
            e = _near(rng, p, 150.0, 2.0, (0.5, 15.0), 0.02)
        elif family == "inclined":
            p = _leo(rng, ecc_max=0.01, inc=rng.uniform(0.0, 100.0))
            e = _near(rng, p, 300.0, 20.0, (0.5, 40.0), 0.03)
        elif family == "wild":
            p = _leo(rng, ecc_max=0.02)
            e = _leo(rng, ecc_max=0.05)
        else:
            raise ValueError(f"未知場景家族：{family!r}")
        if _perigee_ok(p) and _perigee_ok(e):
            return Scenario(p, e, family)
    raise RuntimeError("場景抽樣 100 次都不合法，檢查家族參數")


FAMILIES = ("default", "official_sample", "near_coplanar", "inclined", "wild", "mixed", "flyby", "flyby_pursuer")
