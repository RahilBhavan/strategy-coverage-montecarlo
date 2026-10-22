"""Run every analysis and write results/*.json.

    python -m mc.run            # full run (about 3 minutes)
    python -m mc.run --quick    # fewer paths, for a smoke test
    python -m mc.run --set participation=0.05   # change settings; print base vs changed, write nothing
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import math
import sys
import time

import numpy as np

from . import engine, inputs, params, static
from .fetch import ROOT

OUT = ROOT / "results"


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(float(x)) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (dt.date,)):
        return x.isoformat()
    return x


def write(name: str, obj) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(_jsonable(obj), indent=1) + "\n")


def static_check(inp) -> dict:
    snap = static.snapshot(inp)
    det = {}
    for name, kw in {"snapshot_gate_open": dict(horizon_years=20),
                     "snapshot_gate_closed_1.2x": dict(horizon_years=20, gate=1.2),
                     "path_principal_prefund": dict(horizon_years=20, principal=True, fee=0.01, floor_months=12,
                                                    lookahead_months=12)}.items():
        r = engine.run(inp, params.deterministic(inp, **kw))
        det[name] = {t: float(r["fail_years"][i, 0]) for i, t in enumerate(engine.TIERS)}
    h = 259 * 7 / 365.25  # nearest week to the static path's Sep 30 2031 end
    r = engine.run(inp, params.deterministic(inp, principal=True, put_rule="all", fee=0.01, floor_months=12,
                                             lookahead_months=0, policy="reserve_first", horizon_years=h),
                   record_years=(h,))
    s = r["snapshots"][h]
    return {"inputs": inp.label, "snapshot": snap, "by_seniority": static.by_seniority(inp),
            "static_workbook": {"charges": 1559.673002, "reserve_months": 37.546331779102,
                                "years_reserve_plus_common": 15.1875424974497, "gate_closed_years": 3.12886098159183,
                                "net_mnav": 1.17456717826807, "path_ending_cash": 1525.073002,
                                "path_gross_common": 11106.430130151615, "atm_zero_unmet": 9470.2928268501,
                                "source": "strategy-preferred-coverage-model docs/formula-verification.json (LibreOffice)"},
            "deterministic_engine_fail_years": det,
            "deterministic_static_path": {"horizon_years": h, "ending_cash_tier_b": float(s["reserve"][1, 0]),
                                          "gross_common_tier_b": float(s["issued"][1, 0]),
                                          "unmet_tier_a": float(s["unmet"][0, 0])},
            "interest_note": "Debt interest uses the 10-Q note schedule ($34.595m + $2m other = $36.595m/yr); the "
                             "workbook uses the filed $17.3m semi-annual coupon (x2 + $2m = $36.6m). Difference "
                             "$0.005m/yr."}


def main_table(inp, n: int) -> dict:
    out = {}
    for model in ("gbm", "bootstrap"):
        for principal in (True, False):
            p = params.default(model=model, principal=principal, n_paths=n)
            r = engine.run(inp, p)
            snap = r["snapshots"][5]
            out[f"{model}|{'with' if principal else 'without'}_principal"] = {
                "prob": engine.summarize(r),
                "tier_c_btc_sold_share_5y": {q: float(np.quantile(snap["btc_sold"][2] / inp.btc_held, q))
                                             for q in (0.5, 0.9, 0.99)},
                "gate_closed_week_share_5y_mean": float(snap["gate_closed_share"].mean()),
                "btc_price_5y_quantiles": {q: float(np.quantile(snap["btc_price"], q)) for q in (0.05, 0.5, 0.95)},
                "tier_b_unmet_5y_given_fail_median": float(np.median(snap["unmet"][1][snap["unmet"][1] > 0]))
                if (snap["unmet"][1] > 0).any() else 0.0}
    return out


def coverage_distribution(inp, n: int) -> dict:
    out = {}
    for model in ("gbm", "bootstrap"):
        p = params.default(model=model, n_paths=n, horizon_years=20)
        r = engine.run(inp, p, record_years=(5, 20))
        f = r["fail_years"]
        out[model] = {t: failure_distribution(f[i], 20.0) for i, t in enumerate(engine.TIERS)}
    return out



def failure_distribution(times, horizon):
    """Explicit censoring: histogram bins contain observed failures only."""
    observed = np.where(times <= horizon, times, np.inf)
    finite = observed[np.isfinite(observed)]
    edges = np.linspace(0, horizon, int(round(horizon * 2)) + 1)
    return {"quantiles": {q: float(np.quantile(observed, q, method="inverted_cdf"))
                           for q in (0.05, 0.1, 0.25, 0.5, 0.75, 0.9)},
            "censored_share_20y": float(np.isinf(observed).mean()),
            "censored_count": int(np.isinf(observed).sum()),
            "hist_edges": edges.tolist(),
            "hist_counts": np.histogram(finite, bins=edges)[0].tolist()}

def convergence(inp, sizes=(500, 1000, 2000, 5000, 10000, 20000, 50000), seeds=8) -> dict:
    rows = []
    for n in sizes:
        est = []
        for s in range(seeds):
            r = engine.run(inp, params.default(n_paths=n, seed=1000 + s), record_years=(5,))
            est.append(engine.summarize(r)["b"][5]["p"])
        est = np.array(est)
        p = est.mean()
        rows.append({"n": n, "mean": float(p), "sd_across_seeds": float(est.std(ddof=1)),
                     "binomial_se": float(math.sqrt(p * (1 - p) / n)), "estimates": est.tolist()})
    return {"metric": "P(tier b fails within 5y), GBM, with principal", "seeds": seeds, "rows": rows}


HEAT_BTC = (30_000, 40_000, 50_000, 60_000, 70_000, 82_131, 100_000, 125_000, 150_000)
HEAT_MNAV = (0.8, 0.9, 1.0, 1.1, 1.175, 1.3, 1.5, 2.0)


def heatmap(inp, n: int, horizon: float = 3.0) -> dict:
    grid = []
    for price in HEAT_BTC:
        row = []
        for m in HEAT_MNAV:
            i2 = dataclasses.replace(inp, btc_price=float(price))
            r = engine.run(i2, params.default(n_paths=n, horizon_years=horizon, mnav_start=m, mnav_level=m),
                           record_years=(horizon,))
            row.append(engine.summarize(r, horizons=(horizon,))["b"][horizon]["p"])
        grid.append(row)
    return {"metric": f"P(tier b fails within {horizon:g}y), GBM, with principal", "n_paths": n,
            "btc": list(HEAT_BTC), "mnav": list(HEAT_MNAV), "p": grid,
            "note": "mNAV axis sets both the starting and long-run net mNAV; BTC axis sets the starting price. "
                    "Convertible moneyness at start uses the observed Oct 15 MSTR price."}


def tornado(inp, n: int) -> dict:
    base_p = params.default(n_paths=n)

    def metric(i, **kw):
        r = engine.run(i, dataclasses.replace(base_p, **kw), record_years=(5,))
        return engine.summarize(r)["b"][5]["p"]

    cal = params.calibration()
    cases = [
        ("BTC volatility", "47% (last 3y) / 80%", dict(btc_vol=cal["btc"]["vol_annual_last3y"]), dict(btc_vol=0.80)),
        ("BTC log drift", "-20% / +20% a year", dict(btc_log_drift=-0.2), dict(btc_log_drift=0.2)),
        ("mNAV long-run level", "1.0x / 1.4x", dict(mnav_level=1.0), dict(mnav_level=1.4)),
        ("mNAV link to BTC (gamma)", "0 / 1.0", dict(mnav_dd_beta=0.0), dict(mnav_dd_beta=1.0)),
        ("mNAV link form", "peak drawdown", dict(mnav_link="peak"), None),
        ("mNAV half-life", "13 weeks / 1 year", dict(mnav_half_life=0.25), dict(mnav_half_life=1.0)),
        ("mNAV dispersion (sd log)", "0.06 / 0.20", dict(mnav_sd=0.06), dict(mnav_sd=0.20)),
        ("mNAV-BTC shock correlation", "-0.2 / +0.5", dict(mnav_rho=-0.2), dict(mnav_rho=0.5)),
        ("Issuance gate", "none (0x) / 1.2x", dict(gate=0.0), dict(gate=1.2)),
        ("ADV participation", "1% / 5%", dict(participation=0.01), dict(participation=0.05)),
        ("ADV long-run level", "12m / 30m shares", dict(adv_level=12.0), dict(adv_level=30.0)),
        ("Issuance fee", "0% / 3%", dict(fee=0.0), dict(fee=0.03)),
        ("ATM capacity", "unlimited (new programs)", dict(atm_binding=False), None),
        ("Put election", "all puts in cash", dict(put_rule="all"), None),
        ("Funding order", "Reserve first (static path)", dict(policy="reserve_first", lookahead_months=0), None),
        ("Pre-fund lookahead", "0 / 24 months", dict(lookahead_months=0), dict(lookahead_months=24)),
        ("STRC rate", "10% / 15%", dict(strc_rate=0.10), dict(strc_rate=0.15)),
        ("Path model", "block bootstrap", dict(model="bootstrap"), None),
        ("USD Cash counted", "yes", dict(include_usd_cash=True), None),
    ]
    base = metric(inp)
    rows = []
    for name, label, lo, hi in cases:
        rows.append({"name": name, "label": label, "low": metric(inp, **lo), "high": metric(inp, **hi) if hi else None})
    for name, fx in (("EUR/USD start", (1.0, 1.35)),):
        rows.append({"name": name, "label": "1.00 / 1.35",
                     "low": metric(dataclasses.replace(inp, eurusd=fx[0])),
                     "high": metric(dataclasses.replace(inp, eurusd=fx[1]))})
    rows.sort(key=lambda r: -max(abs(r["low"] - base), abs((r["high"] if r["high"] is not None else base) - base)))
    return {"metric": "P(tier b fails within 5y), GBM, with principal", "n_paths": n, "base": base, "rows": rows,
            "note": "Common random numbers: every case reuses the base seed."}


def refresh_compare(n: int) -> dict:
    out = {}
    for inp in (inputs.base(), inputs.refreshed()):
        r = engine.run(inp, params.default(n_paths=n))
        out[inp.label] = {"prob": engine.summarize(r), "net_mnav": inp.net_mnav(), "charges": inp.annual_charges(),
                          "reserve_months": inp.reserve / inp.annual_charges() * 12, "start": inp.start}
    return out


def main(quick: bool = False) -> None:
    t0 = time.time()
    inp = inputs.base()
    n = 2000 if quick else 20000
    write("static_check.json", static_check(inp))
    write("main.json", {"as_of": "2026-10-21",
                        "interpretation": "Conditional funding-failure simulations, not estimated real-world default probabilities",
                        "daily_dividend_vote": "pending October 28; weekly accrual is a model convention",
                        "n_paths": n, "params": dataclasses.asdict(params.default(n_paths=n)),
                        "inputs": inp.label, "results": main_table(inp, n)})
    print(f"main {time.time() - t0:.0f}s")
    write("coverage_distribution.json", {"n_paths": n, "results": coverage_distribution(inp, n)})
    print(f"distribution {time.time() - t0:.0f}s")
    write("tornado.json", tornado(inp, 2000 if quick else 10000))
    print(f"tornado {time.time() - t0:.0f}s")
    write("heatmap.json", heatmap(inp, 300 if quick else 2000))
    print(f"heatmap {time.time() - t0:.0f}s")
    write("convergence.json", convergence(inp, sizes=(500, 1000, 2000) if quick else
                                          (500, 1000, 2000, 5000, 10000, 20000, 50000), seeds=4 if quick else 8))
    write("refresh_compare.json", refresh_compare(n))
    print(f"done {time.time() - t0:.0f}s")


if __name__ == "__main__":
    import argparse
    from . import whatif
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="fewer paths; with --set, use 2,000 paths")
    parser.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VALUE",
                        help="change one mc.params.Params setting (repeatable); prints results, writes nothing. "
                             "Valid keys: " + ", ".join(whatif.settable()))
    args = parser.parse_args()
    if args.overrides:
        pairs = (["n_paths=2000"] if args.quick and not any(p.startswith("n_paths=") for p in args.overrides)
                 else []) + args.overrides
        try:
            settings = whatif.parse(pairs)
        except ValueError as exc:
            parser.error(str(exc))
        print(whatif.report(whatif.compare(settings)))
    else:
        main(quick=args.quick)
