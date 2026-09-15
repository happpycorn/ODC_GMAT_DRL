"""初始幾何產生器：回傳雙方六根數（SMA km, ECC, INC/RAAN/AOP/TA 度）。

官方決賽初始軌道未知，所以準備幾個家族並可混合抽樣：
  * default          —— 舊 final_env 的佔位軌道（固定，回歸測試用）
  * official_sample  —— 初賽官方範例題目（外星人 = 躲者、地球人 = 追者；兩軌道面夾 94°）
  * near_coplanar    —— 近圓、近共面、相位差 0.5–15°、高度差 ±150 km（典型交會問題）
  * inclined         —— 平面差到 ~20°、相位差到 ±40°
  * wild             —— 雙方獨立亂數 LEO（含逆行），類似官方範例那種刁鑽幾何
"""
from dataclasses import dataclass

import numpy as np

from physics import RE_VAL

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


def sample_scenario(rng: np.random.Generator, family: str = "mixed") -> Scenario:
    if family == "mixed":
        family = str(rng.choice(["near_coplanar", "inclined", "wild"], p=[0.5, 0.3, 0.2]))
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


FAMILIES = ("default", "official_sample", "near_coplanar", "inclined", "wild", "mixed")
