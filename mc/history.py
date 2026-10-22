"""Load cached market histories and estimate the path-model parameters. Every estimate records its window and source."""
from __future__ import annotations

import csv
import datetime as dt
import json
from functools import lru_cache

import numpy as np

from . import fetch

RAW = fetch.RAW
WEEK = 7 / 365.25  # years per simulation step (BTC trades every day)


def _utc(ts: int) -> dt.date:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).date()


@lru_cache(maxsize=None)
def btc_daily() -> tuple[np.ndarray, np.ndarray]:
    d = json.loads((RAW / "coinbase" / "btc-usd-daily.json").read_text())
    dates = np.array([_utc(r[0]) for r in d["rows"]])
    close = np.array([r[4] for r in d["rows"]], dtype=float)
    return dates, close


@lru_cache(maxsize=None)
def mstr_daily() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y = json.loads((RAW / "yahoo" / "mstr-daily.json").read_text())["chart"]["result"][0]
    q = y["indicators"]["quote"][0]
    keep = [i for i, (c, v) in enumerate(zip(q["close"], q["volume"])) if c is not None and v]
    dates = np.array([_utc(y["timestamp"][i]) for i in keep])
    return dates, np.array([q["close"][i] for i in keep]), np.array([q["volume"][i] for i in keep], dtype=float)


@lru_cache(maxsize=None)
def eurusd_daily() -> tuple[np.ndarray, np.ndarray]:
    with open(RAW / "ecb" / "eurusd-daily.csv", newline="") as f:
        rows = [(dt.date.fromisoformat(r["TIME_PERIOD"]), float(r["OBS_VALUE"])) for r in csv.DictReader(f)
                if r["OBS_VALUE"]]
    return np.array([r[0] for r in rows]), np.array([r[1] for r in rows])


@lru_cache(maxsize=None)
def dat_weekly_mstr() -> list[dict]:
    with open(RAW / "dat-accretion" / "weekly.csv", newline="") as f:
        return [dict(week_end=dt.date.fromisoformat(r["week_end"]), price_date=dt.date.fromisoformat(r["price_date"]),
                     btc=float(r["p"]), m=float(r["m"])) for r in csv.DictReader(f) if r["firm"] == "MSTR"]


def close_on(dates: np.ndarray, values: np.ndarray, day: dt.date) -> float:
    i = np.searchsorted(dates, day, side="right") - 1
    if i < 0 or dates[i] != day:
        raise KeyError(day)
    return float(values[i])


def btc_weekly_log_returns(start="2016-01-01", end="2026-10-20") -> np.ndarray:
    """Non-overlapping 7-day log returns of the Coinbase daily close, oldest first, ending on `end`."""
    dates, close = btc_daily()
    lo, hi = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    sel = close[(dates >= lo) & (dates <= hi)]
    sel = sel[(len(sel) - 1) % 7:][::7]  # align so the last point is `end`
    return np.diff(np.log(sel))


def adv20(day: dt.date) -> float:
    """Mean daily MSTR volume (millions of shares) over the 20 trading days ending on `day`."""
    dates, _, vol = mstr_daily()
    i = np.searchsorted(dates, day, side="right")
    return float(vol[i - 20:i].mean() / 1e6)


def _ar1(x: np.ndarray, dt_years: float) -> dict:
    """OU fit by OLS on x[t+1] = a + b x[t] + e. Returns kappa, long-run mean, sigma, half-life."""
    a, b = np.polyfit(x[:-1], x[1:], 1)[::-1]
    resid = x[1:] - (a + b * x[:-1])
    b = min(b, 0.9999)
    kappa = -np.log(b) / dt_years
    sd = resid.std(ddof=2)
    sigma = sd * np.sqrt(2 * kappa / (1 - b * b))
    return {"kappa": float(kappa), "mean": float(a / (1 - b)), "sigma": float(sigma), "b": float(b),
            "half_life_years": float(np.log(2) / kappa), "n": int(len(x) - 1), "resid_sd": float(sd)}


def calibrate() -> dict:
    """All path-model estimates, each with its window and source file."""
    out = {}
    r = btc_weekly_log_returns()
    ann = np.sqrt(365.25 / 7)
    k = ((r - r.mean()) ** 4).mean() / r.var() ** 2
    out["btc"] = {"window": ["2016-01-01", "2026-10-20"], "weeks": int(len(r)), "source": "data/raw/coinbase/btc-usd-daily.json",
                  "mean_log_return_annual": float(r.mean() * 365.25 / 7), "vol_annual": float(r.std(ddof=1) * ann),
                  "kurtosis_weekly": float(k), "worst_week": float(r.min()), "best_week": float(r.max())}
    r3 = btc_weekly_log_returns(start="2023-10-20")
    out["btc"]["vol_annual_last3y"] = float(r3.std(ddof=1) * ann)

    # mNAV dynamics: dat-accretion Strategy-definition mNAV (22 source rows including quarter ends, May 31 - Oct 11 2026)
    w = dat_weekly_mstr()
    # drop the extra quarter-end rows (Jun 30, Sep 30) so points are about 7 days apart; Sep 7 is a Monday week end
    w = [x for x in w if x["week_end"].weekday() == 6 or (x["week_end"].month, x["week_end"].day) not in
         ((3, 31), (6, 30), (9, 30), (12, 31))]
    lm = np.log([x["m"] for x in w])
    lb = np.log([x["btc"] for x in w])
    fit = _ar1(lm, WEEK)
    dlm, dlb = np.diff(lm), np.diff(lb)
    resid = lm[1:] - (fit["mean"] * (1 - fit["b"]) + fit["b"] * lm[:-1])
    rho = float(np.corrcoef(resid, dlb)[0, 1])
    out["mnav"] = {"window": [w[0]["week_end"].isoformat(), w[-1]["week_end"].isoformat()], "weeks": len(w),
                   "source": "data/raw/dat-accretion/weekly.csv (column m)", **fit,
                   "long_run_level": float(np.exp(fit["mean"])), "rho_with_btc": rho,
                   "corr_dlogm_dlogbtc": float(np.corrcoef(dlm, dlb)[0, 1]),
                   "beta_dlogm_on_dlogbtc": float(np.polyfit(dlb, dlm, 1)[0]),
                   "geo_mean_level": float(np.exp(lm.mean())), "sd_log": float(lm.std(ddof=1)),
                   "min": float(np.exp(lm.min())), "max": float(np.exp(lm.max())), "mean_level": float(np.exp(lm).mean()),
                   "weeks_below_1x": int((np.exp(lm) < 1).sum())}

    # MSTR ADV: weekly mean volume, post-split window (split 2024-08-08)
    d, _, v = mstr_daily()
    sel = d >= dt.date(2024, 8, 12)
    dd, vv = d[sel], v[sel]
    iso = np.array([x.isocalendar()[:2] for x in dd])
    keys = sorted(set(map(tuple, iso)))
    wk = np.array([vv[(iso[:, 0] == a) & (iso[:, 1] == b)].mean() for a, b in keys]) / 1e6
    fit = _ar1(np.log(wk), WEEK)
    # pair weekly ADV changes with BTC weekly returns over the same ISO weeks
    bd, bc = btc_daily()
    wk_end = [max(x for x, k2 in zip(dd, map(tuple, iso)) if k2 == k) for k in keys]
    bw = np.log([close_on(bd, bc, x) for x in wk_end])
    rho_adv = float(np.corrcoef(np.diff(np.log(wk)), np.diff(bw))[0, 1])
    out["adv"] = {"window": [dd[0].isoformat(), dd[-1].isoformat()], "weeks": len(wk), "source": "data/raw/yahoo/mstr-daily.json",
                  **fit, "long_run_m_shares": float(np.exp(fit["mean"])),
                  "stationary_sd_log": float(fit["resid_sd"] / np.sqrt(1 - fit["b"] ** 2)), "rho_with_btc": rho_adv,
                  "adv20_2026_10_15": adv20(dt.date(2026, 10, 15))}

    # EUR/USD: ECB reference rate, weekly (Friday) log returns
    fd, fx = eurusd_daily()
    fri = np.array([x.weekday() == 4 for x in fd])
    fdf, fxf = fd[fri], fx[fri]
    rf = np.diff(np.log(fxf))
    bwk = np.log([close_on(bd, bc, x) for x in fdf])
    out["eurusd"] = {"window": [fdf[0].isoformat(), fdf[-1].isoformat()], "weeks": int(len(rf)),
                     "source": "data/raw/ecb/eurusd-daily.csv", "vol_annual": float(rf.std(ddof=1) * ann),
                     "rho_with_btc": float(np.corrcoef(rf, np.diff(bwk))[0, 1])}
    peak_i = int(np.argmax(bc))
    out["btc"]["all_time_high"] = {"date": bd[peak_i].isoformat(), "close": float(bc[peak_i])}
    return out


if __name__ == "__main__":
    print(json.dumps(calibrate(), indent=1))
