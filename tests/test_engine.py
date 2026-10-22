"""Engine behaviour: deterministic limit equals the static model, path mechanics, reproducibility, convergence."""
import dataclasses
import datetime as dt
import math

import numpy as np
import pytest

from mc import engine, history, inputs, params, paths, static


@pytest.fixture(scope="module")
def base():
    return inputs.base()


def test_zero_vol_limit_reproduces_static_snapshot(base):
    r = engine.run(base, params.deterministic(base, horizon_years=20))
    a, b, c = r["fail_years"][:, 0]
    assert a == pytest.approx(base.reserve / base.annual_charges(), rel=1e-9)
    assert b == pytest.approx(static.snapshot(base)["years_reserve_plus_common"], rel=1e-9)
    assert math.isinf(c)
    assert (r["fail_years"] == r["fail_years"][:, :1]).all()  # every path identical


def test_gate_above_mnav_shuts_common(base):
    r = engine.run(base, params.deterministic(base, horizon_years=20, gate=1.2))
    assert r["fail_years"][1, 0] == pytest.approx(r["fail_years"][0, 0])


def test_zero_vol_limit_reproduces_static_quarterly_path(base):
    """Static Base path (all puts in cash, Reserve spent to 12 months first, 1% fee): ending cash $1,525.073m,
    gross common $11,106.4m; the ATM-zero case leaves $9,470.3m unmet. Weekly vs quarterly steps differ slightly."""
    h = 259 * 7 / 365.25
    r = engine.run(base, params.deterministic(base, principal=True, put_rule="all", fee=0.01, floor_months=12,
                                              lookahead_months=0, policy="reserve_first", horizon_years=h),
                   record_years=(h,))
    s = r["snapshots"][h]
    assert s["reserve"][1, 0] == pytest.approx(1525.073002, abs=1e-6)
    assert s["issued"][1, 0] == pytest.approx(11106.430130151615, rel=0.005)
    assert s["unmet"][0, 0] == pytest.approx(9470.2928268501, rel=0.005)
    assert s["principal_due"][0, 0] == pytest.approx(6713.659)


def test_reserve_only_fails_at_the_march_2028_put(base):
    r = engine.run(base, params.deterministic(base, principal=True, put_rule="all", horizon_years=3))
    t = r["fail_years"][0, 0]
    fail_date = base.start + dt.timedelta(days=t * 365.25)
    assert dt.date(2028, 2, 23) <= fail_date <= dt.date(2028, 3, 8)  # week of the $2.0bn 2030B put


def test_rational_puts_skip_in_the_money_notes(base):
    high = params.deterministic(base, principal=True, horizon_years=1.2, mnav_start=3.0, mnav_level=3.0)
    r = engine.run(base, high, record_years=(1.2,))
    assert r["snapshots"][1.2]["principal_due"][0, 0] == 0  # MSTR above 183.19 on Sep 15 2027: no put
    low = params.deterministic(base, principal=True, horizon_years=1.2)
    r = engine.run(base, low, record_years=(1.2,))
    assert r["snapshots"][1.2]["principal_due"][0, 0] == pytest.approx(1010)


def test_same_seed_same_result_and_different_seed_differs(base):
    p = params.default(n_paths=500, horizon_years=3)
    a, b = engine.run(base, p)["fail_years"], engine.run(base, p)["fail_years"]
    assert np.array_equal(a, b)
    c = engine.run(base, dataclasses.replace(p, seed=p.seed + 1))["fail_years"]
    assert not np.array_equal(a, c)


def test_more_sources_never_fail_sooner_with_fixed_put_rule(base):
    r = engine.run(base, params.default(n_paths=2000, put_rule="all"))
    f = r["fail_years"]
    assert (f[0] <= f[1] + 1e-12).all() and (f[1] <= f[2] + 1e-12).all()


def test_bootstrap_draws_only_historical_weekly_returns_in_blocks(base):
    p = params.default(model="bootstrap", n_paths=50)
    h = history.btc_weekly_log_returns(*p.btc_window)
    p = dataclasses.replace(p, btc_vol=h.std(ddof=1) / math.sqrt(paths.DT), btc_log_drift=h.mean() / paths.DT)
    m = paths.Market(p, 1.0, 1.0, 20.0, 1.1, np.random.default_rng(1))
    prev, steps = m.log_p.copy(), []
    for _ in range(16):
        m.step()
        steps.append(m.log_p - prev)
        prev = m.log_p.copy()
    steps = np.array(steps)
    idx = np.abs(steps[..., None] - h[None, None, :]).argmin(axis=2)
    assert np.allclose(steps, h[idx], atol=1e-12)
    within = (idx[1:8] - idx[:7]) % len(h)  # consecutive weeks inside a block are consecutive history
    assert (within == 1).all()


def test_gbm_volatility_and_fx_correlation(base):
    p = params.default(n_paths=20000, fx_rho=0.5)
    m = paths.Market(p, 80000.0, 1.1, 20.0, 1.1, np.random.default_rng(2))
    lp, lf = m.log_p.copy(), m.log_fx.copy()
    m.step()
    rb, rf = m.log_p - lp, m.log_fx - lf
    assert rb.std() / math.sqrt(paths.DT) == pytest.approx(p.btc_vol, rel=0.02)
    assert np.corrcoef(rb, rf)[0, 1] == pytest.approx(0.5, abs=0.02)


def test_mnav_process_is_stationary_around_its_level_without_btc_link(base):
    p = params.default(n_paths=5000, mnav_dd_beta=0.0, mnav_half_life=0.25)
    m = paths.Market(p, 80000.0, 2.0, 20.0, 1.1, np.random.default_rng(3))
    for _ in range(260):
        out = m.step()
    x = np.log(out["mnav"])
    assert x.mean() == pytest.approx(math.log(p.mnav_level), abs=0.01)
    assert x.std() == pytest.approx(p.mnav_sd, rel=0.05)


def test_standard_error_across_seeds_matches_binomial(base):
    est = [engine.summarize(engine.run(base, params.default(n_paths=2000, seed=s), record_years=(5,)))["b"][5]["p"]
           for s in range(8)]
    p = float(np.mean(est))
    se = math.sqrt(p * (1 - p) / 2000)
    assert 0.4 * se < np.std(est, ddof=1) < 2.0 * se


def test_cash_principal_remains_a_claim_until_funded(base):
    """Removing a due note must not create equity before its cash payment."""
    note = inputs.Note('test', 1000.0, 0.0, 10000.0, base.start + dt.timedelta(days=1),
                       base.start + dt.timedelta(days=14))
    inp = dataclasses.replace(base, btc_held=999.0, btc_price=1e6, reserve=0.0, usd_cash=0.0,
                              pref_usd={k: 0.0 for k in base.pref_usd}, stre_eur=0.0,
                              other_debt_interest=0.0, notes=(note,))
    p = params.default(n_paths=1, horizon_years=paths.DT, btc_vol=0.0, mnav_start=1.1, mnav_level=1.1,
                       mnav_sd=0.0, adv_sd=0.0, fx_vol=0.0, floor_months=0.0, lookahead_months=0.0, fee=0.0)
    assert inp.net_value()[0] == -1.0
    s = engine.run(inp, p, record_years=(paths.DT,))['snapshots'][paths.DT]
    assert (s['issued'] == 0).all()
    assert s['unmet'][1, 0] == 1000.0
    assert s['principal_due'][1, 0] == 1000.0  # due remains distinct from payment


@pytest.mark.parametrize('current_mnav', [0.01, 100.0])
def test_put_and_maturity_use_prior_week_moneyness(base, monkeypatch, current_mnav):
    note = inputs.Note('test', 100.0, 0.0, 10.0, base.start + dt.timedelta(days=1),
                       base.start + dt.timedelta(days=2))
    inp = dataclasses.replace(base, notes=(note,))
    p = params.deterministic(inp, principal=True, horizon_years=paths.DT)
    original = paths.Market.step

    def shocked_step(market):
        result = original(market)
        result['mnav'][:] = current_mnav
        return result

    monkeypatch.setattr(paths.Market, 'step', shocked_step)
    s = engine.run(inp, p, record_years=(paths.DT,))['snapshots'][paths.DT]
    # Prior price exceeds $10: skip the put, convert at maturity despite current shock.
    assert (s['principal_due'] == 0).all()
    assert (s['shares'] >= inp.basic_shares_m + 10).all()


def test_one_year_report_observes_exhaustion_after_day_364(base):
    inp = dataclasses.replace(base, reserve=base.annual_charges() * 364.5 / 365.25, atm_remaining=0.0)
    p = params.deterministic(inp, horizon_years=1)
    r = engine.run(inp, p, record_years=())
    assert engine.summarize(r, (1,))['a'][1]['p'] == 1.0
    assert r['fail_years'][0, 0] * 365.25 == pytest.approx(364.5)
    longer = engine.run(inp, dataclasses.replace(p, horizon_years=53 * paths.DT), record_years=())
    assert np.array_equal(r['fail_years'], longer['fail_years'])


def test_principal_valuation_correction_preserves_binding_volume_cap(base):
    note = inputs.Note('test', 1000.0, 0.0, 1000.0, base.start + dt.timedelta(days=7),
                       base.start + dt.timedelta(days=14))
    inp = dataclasses.replace(base, btc_held=2000.0, btc_price=1e6, reserve=0.0, usd_cash=0.0,
                              basic_shares_m=10.0, awards_m=0.0, atm_remaining=10000.0, adv_m=1.1,
                              mstr_price=100.0, pref_usd={k: 0.0 for k in base.pref_usd},
                              stre_eur=0.0, other_debt_interest=0.0, notes=(note,))
    p = params.deterministic(inp, principal=True, horizon_years=paths.DT, mnav_start=1.0,
                             mnav_level=1.0, participation=1.0)
    r = engine.run(inp, p, record_years=(paths.DT,))
    s = r['snapshots'][paths.DT]
    expected_cap = 1.1 * 100.0 * 252 * paths.DT
    assert s['issued'][1, 0] == pytest.approx(expected_cap)
    assert s['unmet'][1, 0] == pytest.approx(1000.0 - expected_cap)
    assert np.isfinite(r['fail_years'][1]).all()
