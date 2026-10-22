"""Weekly funding waterfall for three source tiers on the same market paths.

Tier a: USD Reserve only. Tier b: Reserve + common ATM (gate, ADV participation cap, remaining ATM).
Tier c: tier b + BTC sales. Each tier keeps its own cash, ATM, share count and BTC, because issuance and sales change
the share price that the next week's volume cap uses. A tier fails the first week its sources cannot pay that week's
fixed charges (and principal, when included). After a failure the shortfall is accumulated as unmet funding and the
simulation continues; it is a required-financing record, not a solvency forecast.
"""
from __future__ import annotations

import datetime as dt
import math

import numpy as np

from .inputs import Inputs
from .params import Params
from .paths import DT, Market

TIERS = ("a", "b", "c")
HORIZONS = (1, 3, 5)


def run(inp: Inputs, p: Params, record_years: tuple = HORIZONS) -> dict:
    from .validation import validate
    validate(inp, p)
    rng = np.random.default_rng(p.seed)
    n = p.n_paths
    m0 = inp.net_mnav() if p.mnav_start is None else p.mnav_start
    mkt = Market(p, inp.btc_price, m0, inp.adv_m, inp.eurusd, rng, n)
    steps = int(math.ceil(p.horizon_years / DT - 1e-12))
    T = len(TIERS)
    allow_common = np.array([0.0, 1.0, 1.0])[:, None]
    allow_btc = np.array([False, False, True])[:, None]

    R = np.full((T, n), inp.reserve + (inp.usd_cash if p.include_usd_cash else 0.0), dtype=float)
    usd_cash_nv = 0.0 if p.include_usd_cash else inp.usd_cash
    A = np.full((T, n), inp.atm_remaining if p.atm_binding else np.inf, dtype=float)
    S = np.full((T, n), inp.basic_shares_m, dtype=float)
    B = np.full((T, n), inp.btc_held, dtype=float)
    notes = inp.notes
    J = len(notes)
    out = np.ones((T, n, J), dtype=bool)
    prin = np.array([x.principal for x in notes])
    conv = np.array([x.conversion_price for x in notes])
    coup = np.array([x.coupon for x in notes])
    nv0, fd0 = inp.net_value()  # moneyness at the observed MSTR price; equals the observed price at base inputs
    prev_price = np.full((T, n), max(0.0, m0 * nv0 / fd0))
    fail = np.full((T, n), np.inf)
    unmet = np.zeros((T, n))
    issued = np.zeros((T, n))
    btc_sold = np.zeros((T, n))
    principal_due = np.zeros((T, n))
    gate_closed_weeks = np.zeros(n)

    rates = dict(inp.rates)
    if p.strc_rate is not None:
        rates["STRC"] = p.strc_rate
    usd_pref_div = sum(v * rates[k] for k, v in inp.pref_usd.items())
    usd_pref_claims = sum(inp.pref_usd.values())
    snaps = {}
    record_steps = {int(math.ceil(y / DT - 1e-12)): y for y in record_years}

    for k in range(steps):
        d0 = inp.start + dt.timedelta(days=7 * k)
        d1 = d0 + dt.timedelta(days=7)
        mk = mkt.step()
        P, m, adv, fx = mk["btc"], mk["mnav"], mk["adv"], mk["fx"]
        gate_closed_weeks += m < p.gate

        # charges accrued this week (accrual basis, as in the static model)
        pref = (usd_pref_div + inp.stre_eur * fx * rates["STRE"]) * DT
        interest = (out * (prin * coup)).sum(axis=2) * DT + inp.other_debt_interest * DT
        need = pref[None, :] + interest
        cash_principal = np.zeros((T, n))

        # principal events; moneyness uses the prior week's share price
        if p.principal:
            for j, note in enumerate(notes):
                otm = prev_price < conv[j]
                if d0 < note.put <= d1:
                    put = out[:, :, j] & (otm if p.put_rule == "rational" else True)
                    need = need + put * prin[j]
                    cash_principal += put * prin[j]
                    principal_due += put * prin[j]
                    out[:, :, j] &= ~put
                if d0 < note.maturity <= d1:
                    live = out[:, :, j]
                    cash = live & otm
                    need = need + cash * prin[j]
                    cash_principal += cash * prin[j]
                    principal_due += cash * prin[j]
                    S += (live & ~otm) * (prin[j] / conv[j])
                    out[:, :, j] = False

        # share price from net value per fully diluted share (static Net NAV definition)
        itm = out & (prev_price[:, :, None] >= conv)
        otm_claims = (out & ~itm) * prin
        strk_itm = prev_price >= inp.strk_conversion_price
        pref_claims = usd_pref_claims + inp.stre_eur * fx[None, :] - strk_itm * inp.pref_usd["STRK"]
        # A removed cash-settled note still consumes cash in this waterfall step.
        nv = B * P[None, :] / 1e6 + R + usd_cash_nv - otm_claims.sum(axis=2) - pref_claims - cash_principal
        fd = S + inp.awards_m + (itm * (prin / conv)).sum(axis=2) + strk_itm * (inp.pref_usd["STRK"] /
                                                                              inp.strk_conversion_price)
        price = np.maximum(0.0, m[None, :] * nv / fd)

        # tier b/c: common issuance
        cap = adv[None, :] * price * p.participation * p.trading_days * DT
        cap = np.minimum(cap, A) * allow_common * ((m >= p.gate)[None, :]) * (price > 0)
        # cash target: floor_months of current charges plus principal expected within lookahead_months
        target = (pref[None, :] + interest) / DT * p.floor_months / 12
        if p.principal and p.lookahead_months > 0:
            horizon = d1 + dt.timedelta(days=round(p.lookahead_months * 365.25 / 12))
            for j, note in enumerate(notes):
                expect = out[:, :, j] & ((prev_price < conv[j]) if p.put_rule == "rational" else True)
                if d1 < note.put <= horizon or (d1 < note.maturity <= horizon and p.put_rule == "rational"):
                    target = target + expect * prin[j]
        if p.policy == "common_first":  # sell common for this week's need first, then top up to the target
            want = (need + np.maximum(0.0, target - R)) / (1 - p.fee)
        elif p.policy == "reserve_first":  # static quarterly path: spend the Reserve down to the target first
            want = np.maximum(0.0, need + target - R) / (1 - p.fee)
        else:
            raise ValueError(p.policy)
        G = np.minimum(cap, want)
        R += G * (1 - p.fee)
        A -= G
        S += np.where(price > 0, G / np.where(price > 0, price, 1.0), 0.0)
        issued += G

        # pay from cash
        paid = np.minimum(R, need)
        R -= paid
        short = need - paid

        # tier c: BTC sales
        proceeds_per_btc = P[None, :] * (1 - p.btc_sale_cost) / 1e6
        sell = np.where(allow_btc & (short > 0), np.minimum(B, short / proceeds_per_btc), 0.0)
        B -= sell
        btc_sold += sell
        short = np.maximum(0.0, short - sell * proceeds_per_btc)

        newly = (short > 1e-9) & np.isinf(fail)
        frac = np.where(need > 0, 1 - short / np.where(need > 0, need, 1.0), 0.0)
        fail = np.where(newly, k * DT + frac * DT, fail)
        unmet += short
        prev_price = price

        if k + 1 in record_steps:
            y = record_steps[k + 1]
            snaps[y] = {"reserve": R.copy(), "atm": A.copy(), "shares": S.copy(), "btc": B.copy(),
                        "issued": issued.copy(), "btc_sold": btc_sold.copy(), "unmet": unmet.copy(),
                        "principal_due": principal_due.copy(), "btc_price": P.copy(), "mnav": m.copy(),
                        "gate_closed_share": gate_closed_weeks / (k + 1)}

    return {"fail_years": fail, "snapshots": snaps, "steps": steps, "params": p, "inputs": inp.label}


def summarize(res: dict, horizons=HORIZONS) -> dict:
    """P(first failure within each horizon) with binomial standard errors, per tier."""
    if any(h <= 0 or h > res["steps"] * DT + 1e-12 for h in horizons):
        raise ValueError("summary horizons must be within the simulated horizon")
    f = res["fail_years"]
    n = f.shape[1]
    out = {}
    for i, t in enumerate(TIERS):
        out[t] = {}
        for h in horizons:
            p = float((f[i] <= h + 1e-12).mean())
            out[t][h] = {"p": p, "se": math.sqrt(p * (1 - p) / n)}
    return out
