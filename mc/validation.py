"""Validate simulation settings and imported observations at the public run boundary."""
import dataclasses
import math


def validate(inp, p):
    for f in dataclasses.fields(p):
        x = getattr(p, f.name)
        if isinstance(x, (int, float)) and not isinstance(x, bool) and not math.isfinite(x):
            raise ValueError(f"{f.name} must be finite")
    for name in ("n_paths", "block_weeks", "trading_days"):
        x = getattr(p, name)
        if not isinstance(x, int) or isinstance(x, bool) or x < 1:
            raise ValueError(f"{name} must be a positive integer")
    if not isinstance(p.seed, int) or isinstance(p.seed, bool) or p.seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if p.horizon_years < 7 / 365.25:
        raise ValueError("horizon must be at least one week")
    for name in ("btc_vol", "mnav_sd", "adv_sd", "fx_vol", "mnav_half_life", "adv_half_life",
                 "participation", "gate", "floor_months", "lookahead_months"):
        if getattr(p, name) < 0:
            raise ValueError(f"{name} must be nonnegative")
    for name in ("mnav_level", "adv_level"):
        if getattr(p, name) <= 0:
            raise ValueError(f"{name} must be positive")
    for name in ("mnav_rho", "adv_rho", "fx_rho"):
        if not -1 <= getattr(p, name) <= 1:
            raise ValueError(f"{name} must lie in [-1,1]")
    if not 0 <= p.fee < 1 or not 0 <= p.btc_sale_cost < 1:
        raise ValueError("fees must lie in [0,1)")
    if p.model not in ("gbm", "bootstrap") or p.put_rule not in ("rational", "all") or p.policy not in ("common_first", "reserve_first") or p.mnav_link not in ("start", "peak"):
        raise ValueError("unknown model, put rule, funding policy or mNAV link")
    if p.strc_rate is not None and p.strc_rate < 0:
        raise ValueError("STRC rate must be nonnegative")
    m0 = inp.net_mnav() if p.mnav_start is None else p.mnav_start
    if not math.isfinite(m0) or m0 <= 0:
        raise ValueError("starting mNAV must be finite and positive")
    for name in ("btc_price", "eurusd", "mstr_price", "basic_shares_m", "adv_m", "strk_conversion_price"):
        x = getattr(inp, name)
        if not math.isfinite(x) or x <= 0:
            raise ValueError(f"input {name} must be finite and positive")
    for name in ("reserve", "atm_remaining", "usd_cash", "btc_held", "awards_m", "stre_eur", "other_debt_interest"):
        x = getattr(inp, name)
        if not math.isfinite(x) or x < 0:
            raise ValueError(f"input {name} must be finite and nonnegative")
    if set(inp.pref_usd) != {"STRF", "STRC", "STRK", "STRD"} or set(inp.rates) != {*inp.pref_usd, "STRE"}:
        raise ValueError("missing or unknown preferred inputs")
    if any(not math.isfinite(x) or x < 0 for x in (*inp.pref_usd.values(), *inp.rates.values())):
        raise ValueError("preferred notionals/rates must be finite and nonnegative")
    for note in inp.notes:
        if not all(math.isfinite(x) for x in (note.principal, note.conversion_price, note.coupon)) or note.principal < 0 or note.conversion_price <= 0 or note.coupon < 0:
            raise ValueError("invalid note terms")
        if not inp.start < note.put <= note.maturity:
            raise ValueError("note schedule must start after simulation start")
