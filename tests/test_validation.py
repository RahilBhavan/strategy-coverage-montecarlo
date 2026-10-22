"""Invalid settings and resource-exhaustion invariants at the run interface."""
from dataclasses import replace
import numpy as np
import pytest
from mc import engine, inputs, params


@pytest.mark.parametrize('kw', [dict(n_paths=0), dict(n_paths=2.5), dict(fee=1), dict(btc_vol=-1),
    dict(mnav_rho=1.01), dict(mnav_level=0), dict(seed=-1), dict(block_weeks=0),
    dict(btc_vol=float('nan')), dict(horizon_years=0), dict(mnav_link='bad'), dict(put_rule='bad')])
def test_bad_settings(kw):
    with pytest.raises(ValueError):
        engine.run(inputs.base(), params.default(**kw))


def test_empty_funding_sources_fail_immediately_and_never_go_negative():
    inp = replace(inputs.base(), reserve=0, atm_remaining=0, btc_held=0)
    p = params.default(n_paths=8, horizon_years=1, mnav_start=1.1)
    res = engine.run(inp, p, record_years=(1,))
    assert (res['fail_years'] == 0).all()
    s = res['snapshots'][1]
    for key in ('reserve', 'atm', 'btc'):
        assert (s[key] == 0).all()
    assert (s['unmet'] > 0).all()


def test_atm_and_btc_deplete_with_gate_open():
    inp = replace(inputs.base(), reserve=0.01, atm_remaining=0.01)
    p = params.deterministic(inp, horizon_years=1, mnav_start=1.2, mnav_level=1.2, gate=0)
    r = engine.run(inp, p, record_years=(1,))
    s = r['snapshots'][1]
    assert np.isfinite(r['fail_years'][:2]).all()
    assert np.isinf(r['fail_years'][2]).all()
    assert (s['reserve'] >= 0).all() and (s['atm'] >= 0).all() and (s['btc'] >= 0).all()
    assert s['atm'][1, 0] == 0 and s['btc_sold'][2, 0] > 0
    # With negative net equity, common cannot be sold even when the mNAV gate is open.
    poor = replace(inp, btc_held=1)
    s = engine.run(poor, p, record_years=(1,))['snapshots'][1]
    assert s['btc_sold'][2, 0] == 1 and s['atm'][1, 0] == 0.01


def test_btc_mnav_innovation_correlation():
    from mc.paths import Market
    p = params.default(n_paths=20000, mnav_rho=0.6, mnav_dd_beta=0)
    m = Market(p, 80000, p.mnav_level, 20, 1.1, np.random.default_rng(1))
    old_p, old_m = m.log_p.copy(), m.x_m.copy()
    m.step()
    assert np.corrcoef(m.log_p-old_p, m.x_m-old_m)[0,1] == pytest.approx(0.6, abs=0.02)


def test_cannot_report_unobserved_horizon():
    r = engine.run(inputs.base(), params.default(n_paths=4, horizon_years=1))
    with pytest.raises(ValueError):
        engine.summarize(r)


def test_first_passage_histogram_partitions_failures_and_censoring():
    from mc.run import failure_distribution
    d = failure_distribution(np.array([0, 0.25, 19.99, 20, 20.001, np.inf]), 20)
    assert len(d['hist_edges']) == len(d['hist_counts']) + 1
    assert sum(d['hist_counts']) == 4
    assert d['censored_count'] == 2
    assert sum(d['hist_counts']) + d['censored_count'] == 6
    assert d['censored_share_20y'] == pytest.approx(1/3)


def test_integer_share_count_supports_fractional_issuance():
    inp = replace(inputs.base(), basic_shares_m=422)
    p = params.default(n_paths=1, horizon_years=7/365.25)
    s = engine.run(inp, p, record_years=(p.horizon_years,))['snapshots'][p.horizon_years]
    assert s['shares'][1, 0] > 422
