"""Reproduction of the static Excel model's snapshot coverage (Coverage sheet and model/calculator.mjs).

Snapshot rules: charges are constant, principal is excluded, common stock is sold first up to
min(ADV x price x participation x 252, remaining ATM), the Reserve pays the rest, and no common is sold when net
mNAV is below the gate. Observed convertible moneyness is held fixed when the BTC price or mNAV changes.
"""
from __future__ import annotations

from .inputs import Inputs


def snapshot(inp: Inputs, btc_price: float | None = None, mnav: float | None = None, strc_rate: float | None = None,
             participation: float = 0.02, trading_days: int = 252, gate: float = 1.0, display_cap: float = 50.0) -> dict:
    p = inp.btc_price if btc_price is None else btc_price
    m = inp.net_mnav() if mnav is None else mnav
    charges = inp.annual_charges() + inp.pref_usd["STRC"] * ((strc_rate if strc_rate is not None else inp.rates["STRC"])
                                                            - inp.rates["STRC"])
    net0, fd = inp.net_value()
    net = net0 + inp.btc_held * (p - inp.btc_price) / 1e6
    share_price = max(0.0, m * net) / fd
    common = 0.0 if m < gate else inp.adv_m * share_price * participation * trading_days
    reserve, atm = inp.reserve, inp.atm_remaining
    if common < charges and common * reserve / (charges - common) <= atm:
        years = reserve / (charges - common)
    else:
        years = (reserve + atm) / charges
    return {"charges": charges, "reserve_months": reserve / charges * 12, "years_reserve_plus_common": min(display_cap, years),
            "annual_common": common, "share_price": share_price, "net_value": net, "mnav": m}


def by_seniority(inp: Inputs, participation: float = 0.02, trading_days: int = 252, display_cap: float = 50.0) -> list:
    """Coverage sheet rows: cumulative charges down the stack (debt interest first), Reserve months and years."""
    s = snapshot(inp, participation=participation, trading_days=trading_days)
    common = s["annual_common"]
    order = ["STRF", "STRC", "STRE", "STRK", "STRD"]
    div = inp.pref_dividends()
    rows, cum = [], inp.debt_interest()
    for name in ["Debt interest"] + order:
        if name != "Debt interest":
            cum += div[name]
        r = inp.reserve
        if common < cum and common * r / (cum - common) <= inp.atm_remaining:
            y = r / (cum - common)
        else:
            y = (r + inp.atm_remaining) / cum
        rows.append({"claim": name, "cumulative_charges": cum, "reserve_months": min(display_cap * 12, r / cum * 12),
                     "reserve_plus_common_years": min(display_cap, y)})
    return rows
