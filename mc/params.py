"""Simulation settings. Defaults marked (estimate) come from data/derived/calibration.json; everything else is a
model assumption and is varied in the tornado (mc/sensitivity.py)."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace

from . import fetch

CAL_PATH = fetch.ROOT / "data" / "derived" / "calibration.json"


def calibration() -> dict:
    if not CAL_PATH.exists():
        from . import history
        CAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        CAL_PATH.write_text(json.dumps(history.calibrate(), indent=1) + "\n")
    return json.loads(CAL_PATH.read_text())


@dataclass(frozen=True)
class Params:
    model: str = "gbm"  # "gbm" or "bootstrap"
    horizon_years: float = 5.0
    n_paths: int = 20_000
    seed: int = 20261021
    # BTC
    btc_log_drift: float = 0.0  # assumption: median path flat; historical mean is not projected
    btc_vol: float = float("nan")  # (estimate) annualized weekly vol, 2016-01-01..2026-10-20
    btc_window: tuple = ("2016-01-01", "2026-10-20")
    block_weeks: int = 8  # bootstrap block length (assumption)
    # net mNAV: OU on log mNAV, long-run level shifted by gamma x log drawdown from the path's running peak
    mnav_level: float = float("nan")  # (estimate) geometric mean of dat-accretion weekly mNAV
    mnav_sd: float = float("nan")  # (estimate) stationary sd of log mNAV
    mnav_half_life: float = float("nan")  # (estimate, weak) years
    mnav_rho: float = 0.0  # assumption: sample estimate is indistinguishable from zero
    mnav_dd_beta: float = 0.5  # assumption carried from the static path (0.6 level sensitivity / 1.17)
    mnav_link: str = "start"  # "start": log(P/P0) as in the static path; "peak": drawdown from running peak
    mnav_start: float | None = None  # None = reconstructed net mNAV from inputs
    # MSTR average daily volume (millions of shares), OU on log ADV
    adv_level: float = float("nan")  # (estimate)
    adv_sd: float = float("nan")  # (estimate)
    adv_half_life: float = float("nan")  # (estimate)
    adv_rho: float = float("nan")  # (estimate)
    # EUR/USD
    fx_vol: float = float("nan")  # (estimate)
    fx_rho: float = float("nan")  # (estimate)
    # Funding rules
    gate: float = 1.0  # assumption: no common below this net mNAV (no filed 1x policy)
    participation: float = 0.02  # assumption: share of ADV the ATM can take
    trading_days: int = 252
    fee: float = 0.01  # assumption: issuance cost (static path)
    atm_binding: bool = True  # cap issuance at the remaining registered MSTR ATM
    principal: bool = True  # include convertible put/maturity principal
    put_rule: str = "rational"  # "rational": put/maturity paid in cash only if MSTR < conversion price; "all"
    policy: str = "common_first"  # or "reserve_first": spend the Reserve down to the target, then issue (static path)
    floor_months: float = 12.0  # cash target: months of charges (Strategy's stated 12-month Reserve minimum)
    lookahead_months: float = 12.0  # assumption: also pre-fund principal expected within this window
    include_usd_cash: bool = False
    btc_sale_cost: float = 0.005  # assumption: slippage and fees on BTC sales (tier c)
    strc_rate: float | None = None  # None = input rate (12%)


def default(**kw) -> Params:
    c = calibration()
    m, a = c["mnav"], c["adv"]
    base = Params(
        btc_vol=c["btc"]["vol_annual"],
        mnav_level=m["geo_mean_level"], mnav_sd=m["sd_log"], mnav_half_life=m["half_life_years"],
        adv_level=a["long_run_m_shares"], adv_sd=a["stationary_sd_log"], adv_half_life=a["half_life_years"],
        adv_rho=a["rho_with_btc"], fx_vol=c["eurusd"]["vol_annual"], fx_rho=c["eurusd"]["rho_with_btc"])
    return replace(base, **kw)


def deterministic(inp, **kw) -> Params:
    """Zero-volatility limit: every process stays at its starting value."""
    kw = {"floor_months": 0.0, "lookahead_months": 0.0, "fee": 0.0, "principal": False, **kw}
    return default(**{
        "btc_vol": 0.0, "mnav_sd": 0.0, "adv_sd": 0.0, "fx_vol": 0.0,
        "mnav_level": inp.net_mnav(), "adv_level": inp.adv_m, "n_paths": 4, **kw})


def half_life_to_b(h: float, dt: float) -> float:
    return math.exp(-math.log(2) / h * dt) if h > 0 else 0.0
