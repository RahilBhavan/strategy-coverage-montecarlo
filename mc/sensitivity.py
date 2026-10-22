"""Offline paired assumption sensitivity; separate from the seven legacy analyses.

    python -m mc.sensitivity --output reports/assumption_sensitivity.json
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from . import engine, inputs, params
from .fetch import ROOT

Z95 = 1.959963984540054


def probability_summary(failed: np.ndarray) -> dict:
    """Conditional binomial simulation error, including nonzero endpoint intervals."""
    n, count = failed.size, int(failed.sum())
    p = count / n
    den = 1 + Z95 ** 2 / n
    center = (p + Z95 ** 2 / (2 * n)) / den
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95 ** 2 / (4 * n * n)) / den
    return {"failures": count, "survivors": n - count, "p": p,
            "mc_se": math.sqrt(p * (1 - p) / n),
            "mc_wilson_95": [max(0.0, center - half), min(1.0, center + half)]}


def paired_change(base: np.ndarray, case: np.ndarray) -> dict:
    """SE(mean D) from D=case-base, using sample variance of paired indicators."""
    increased = int((case & ~base).sum())
    decreased = int((base & ~case).sum())
    n = base.size
    delta = (increased - decreased) / n
    variance = max(0.0, (increased + decreased - n * delta ** 2) / (n - 1))
    return {"delta_p": delta, "paired_mc_se": math.sqrt(variance / n),
            "new_failures": increased, "avoided_failures": decreased}


def assumptions() -> tuple:
    """Endpoint grids are scenarios, not fitted parameter confidence limits."""
    return (
        ("BTC volatility", "calibration transfer", ({"btc_vol": params.calibration()["btc"]["vol_annual_last3y"]},
                                                    {"btc_vol": 0.8})),
        ("mNAV level", "calibration transfer", ({"mnav_level": 1.0}, {"mnav_level": 1.4})),
        ("mNAV half-life", "calibration transfer", ({"mnav_half_life": 0.25}, {"mnav_half_life": 1.0})),
        ("mNAV dispersion", "calibration transfer", ({"mnav_sd": 0.06}, {"mnav_sd": 0.20})),
        ("mNAV BTC linkage", "model assumption", ({"mnav_dd_beta": 0.0}, {"mnav_dd_beta": 1.0})),
        ("mNAV link form", "model assumption", ({"mnav_link": "peak"},)),
        ("Issuance gate", "funding policy", ({"gate": 0.0}, {"gate": 1.2})),
        ("ADV participation", "funding policy", ({"participation": 0.01}, {"participation": 0.05})),
        ("Reserve floor months", "funding policy", ({"floor_months": 0.0}, {"floor_months": 24.0})),
        ("Principal lookahead months", "funding policy", ({"lookahead_months": 0.0}, {"lookahead_months": 24.0})),
        ("Issuance fee", "funding policy", ({"fee": 0.0}, {"fee": 0.03})),
        ("Put election", "funding policy", ({"put_rule": "all"},)),
        ("ATM capacity", "funding policy", ({"atm_binding": False},)),
    )


def build_report(n_paths: int = 4000, seed: int = 20261021) -> dict:
    if isinstance(n_paths, bool) or not isinstance(n_paths, int) or n_paths < 2:
        raise ValueError("n_paths must be an integer >= 2 for paired sample variance")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    inp = inputs.base()
    p = params.default(n_paths=n_paths, seed=seed)

    def failures(settings):
        result = engine.run(inp, settings, record_years=())
        return result["fail_years"][1] <= p.horizon_years + 1e-12

    base = failures(p)
    rows = []
    for name, category, variants in assumptions():
        cases = []
        for overrides in variants:
            failed = failures(dataclasses.replace(p, **overrides))
            cases.append({"overrides": overrides, **probability_summary(failed), **paired_change(base, failed)})
        rows.append({"assumption": name, "category": category,
                     "max_abs_delta_p": max(abs(c["delta_p"]) for c in cases), "cases": cases})
    rows.sort(key=lambda row: (-row["max_abs_delta_p"], row["assumption"]))
    calibration = params.calibration()
    return {
        "schema_version": 1, "as_of": "2026-10-21",
        "metric": "Tier b first funding exhaustion within 5 years; conditional, not default probability",
        "uncertainty": {
            "simulation": "mc_se and mc_wilson_95 condition on each scenario; paired_mc_se uses common GBM draws",
            "parameter": "Not estimated. Endpoint spread is assumption sensitivity, not a confidence or credible interval",
            "ranking": "Maximum absolute change over selected endpoints; one-at-a-time, no interactions or global attribution",
        },
        "provenance": {
            "sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                       ("data/derived/calibration.json", "data/frozen/index.json")},
            "inputs": inp.label,
            "mnav": {k: calibration["mnav"][k] for k in ("source", "window", "weeks", "n")},
            "mnav_limit": "20 derived weekly observations, 19 transitions; definition differs from starting net mNAV",
            "scenario_source": "mc.sensitivity.assumptions; illustrative endpoints, existing tornado except reserve floor",
        },
        "base_params": dataclasses.asdict(p), "base": probability_summary(base), "drivers": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build_report(args.paths, args.seed)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1, allow_nan=False) + "\n")
    print(f"Wrote {args.output}: {args.paths} paired paths, {len(report['drivers'])} assumptions")


if __name__ == "__main__":
    main()
