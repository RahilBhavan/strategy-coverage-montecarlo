"""Market histories reproduce the static model's market inputs; calibration is internally consistent."""
import datetime as dt

import numpy as np
import pytest

from mc import history


def test_market_closes_match_static_inputs():
    bd, bc = history.btc_daily()
    assert round(history.close_on(bd, bc, dt.date(2026, 10, 15))) == 82131
    md, mc_, _ = history.mstr_daily()
    assert history.close_on(md, mc_, dt.date(2026, 10, 15)) == pytest.approx(151.29, abs=0.005)
    fd, fx = history.eurusd_daily()
    assert history.close_on(fd, fx, dt.date(2026, 10, 16)) == 1.1253
    assert history.adv20(dt.date(2026, 10, 15)) == pytest.approx(22.0, abs=0.01)


def test_btc_daily_has_no_gaps_and_weekly_returns_end_on_window_end():
    bd, bc = history.btc_daily()
    assert (np.diff(bd).astype("timedelta64[D]").astype(int) == 1).all() if bd.dtype.kind == "M" else \
        all((b - a).days == 1 for a, b in zip(bd, bd[1:]))
    r = history.btc_weekly_log_returns("2016-01-01", "2026-10-20")
    sel = bc[(bd >= dt.date(2016, 1, 1)) & (bd <= dt.date(2026, 10, 20))]
    assert r.sum() == pytest.approx(np.log(sel[-1] / sel[(len(sel) - 1) % 7]))


def test_dat_accretion_mnav_matches_the_cited_value():
    w = history.dat_weekly_mstr()
    last = [x for x in w if x["week_end"] == dt.date(2026, 10, 11)][0]
    assert last["m"] == pytest.approx(1.190726)  # Rahil's notes: dat-accretion 1.191x, week ending Oct 11


def test_ou_fit_recovers_known_parameters():
    rng = np.random.default_rng(0)
    b, mu, sd = 0.8, 0.1, 0.05
    x = [mu]
    for _ in range(20000):
        x.append(mu + b * (x[-1] - mu) + sd * rng.standard_normal())
    fit = history._ar1(np.array(x), history.WEEK)
    assert fit["b"] == pytest.approx(b, abs=0.01)
    assert fit["mean"] == pytest.approx(mu, abs=0.005)
    assert fit["half_life_years"] == pytest.approx(np.log(2) / (-np.log(b) / history.WEEK), rel=0.05)
