"""Change model settings from the command line and print headline tier probabilities against the base case.

Used by `python -m mc.run --set key=value [--set ...]`. Nothing is written to results/.
"""
from __future__ import annotations

import dataclasses
import math

from . import engine, inputs, params

TIER_NAMES = {"a": "reserve only", "b": "reserve + common ATM", "c": "reserve + common ATM + BTC sales"}
# Settings that define the experiment rather than an assumption: the base run shares them so the comparison is paired.
RUN_SETTINGS = ("n_paths", "seed", "horizon_years", "trading_days")


def settable() -> list[str]:
    return [f.name for f in dataclasses.fields(params.Params)]


def _coerce(key: str, text: str, current):
    t = text.strip()
    if key in ("mnav_start", "strc_rate") and t.lower() == "none":
        return None
    if isinstance(current, bool):
        if t.lower() in ("true", "1", "yes"):
            return True
        if t.lower() in ("false", "0", "no"):
            return False
        raise ValueError(f"{key} must be true or false, got {text!r}")
    if isinstance(current, int):
        try:
            return int(t)
        except ValueError:
            raise ValueError(f"{key} must be an integer, got {text!r}") from None
    if isinstance(current, tuple):
        parts = tuple(x.strip() for x in t.split(","))
        if len(parts) != len(current) or not all(parts):
            raise ValueError(f"{key} needs {len(current)} comma-separated values, got {text!r}")
        return parts
    if isinstance(current, str):
        return t
    try:
        value = float(t)
    except ValueError:
        raise ValueError(f"{key} must be a number, got {text!r}") from None
    if not math.isfinite(value):
        raise ValueError(f"{key} must be finite, got {text!r}")
    return value


def parse(pairs: list[str]) -> dict:
    """Turn ['participation=0.05', ...] into validated Params overrides; raise ValueError with the valid keys."""
    base = params.default()
    out = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        key = key.strip()
        if not sep or not key:
            raise ValueError(f"--set expects key=value, got {pair!r}")
        if key not in settable():
            raise ValueError(f"unknown setting {key!r}. Valid keys: {', '.join(settable())}")
        if key in out:
            raise ValueError(f"setting {key!r} given more than once")
        out[key] = _coerce(key, value, getattr(base, key))
    params.default(**out)  # dataclass construction
    from .validation import validate
    validate(inputs.base(), params.default(**out))
    return out


def compare(overrides: dict) -> dict:
    inp = inputs.base()
    shared = {k: v for k, v in overrides.items() if k in RUN_SETTINGS}
    base_p, new_p = params.default(**shared), params.default(**overrides)
    horizons = tuple(h for h in engine.HORIZONS if h <= new_p.horizon_years + 1e-12) or (new_p.horizon_years,)
    base_r = engine.run(inp, base_p, record_years=horizons)
    new_r = engine.run(inp, new_p, record_years=horizons)
    rows = []
    for i, tier in enumerate(engine.TIERS):
        for h in horizons:
            a = base_r["fail_years"][i] <= h + 1e-12
            b = new_r["fail_years"][i] <= h + 1e-12
            d = b.astype(float) - a.astype(float)
            n = len(d)
            rows.append({"tier": tier, "years": h, "base_p": float(a.mean()), "base_se": math.sqrt(a.mean() * (1 - a.mean()) / n),
                         "p": float(b.mean()), "se": math.sqrt(b.mean() * (1 - b.mean()) / n),
                         "change_pp": 100 * float(d.mean()),
                         "change_se_pp": 100 * float(d.std(ddof=1) / math.sqrt(n)) if n > 1 else 0.0})
    return {"overrides": overrides, "n_paths": new_p.n_paths, "seed": new_p.seed, "model": new_p.model,
            "principal": new_p.principal, "rows": rows}


def describe(value) -> str:
    return ",".join(value) if isinstance(value, tuple) else str(value)


def report(result: dict) -> str:
    base = params.default()
    changes = "; ".join(f"{k} {describe(getattr(base, k))} -> {describe(v)}" for k, v in result["overrides"].items())
    lines = [f"Changed: {changes}",
             f"{result['n_paths']:,} {result['model'].upper()} paths, seed {result['seed']}, "
             f"principal {'included' if result['principal'] else 'excluded'}, frozen snapshot 2026-10-21.",
             "P(first funding exhaustion within N years), simulation SE in brackets:",
             f"{'tier':<4} {'years':>5} {'base':>17} {'changed':>17} {'change (paired SE)':>22}"]
    for r in result["rows"]:
        lines.append(f"{r['tier']:<4} {r['years']:>5g} {100 * r['base_p']:>8.2f}% ({100 * r['base_se']:.2f}) "
                     f"{100 * r['p']:>8.2f}% ({100 * r['se']:.2f}) "
                     f"{r['change_pp']:>+12.2f} pp ({r['change_se_pp']:.2f})")
    lines += ["Tiers: " + "; ".join(f"{t} = {name}" for t, name in TIER_NAMES.items()) + ".",
              "Funding exhaustion is not legal default. SEs cover simulation noise only, not model or parameter error."]
    return "\n".join(lines)
