"""Known-answer simulation statistics and synthetic cash-resource limits."""
import dataclasses
import json
import math
import subprocess
import sys

import numpy as np
import pytest

from mc import engine, inputs, params, sensitivity
from mc.paths import DT


def test_paired_change_known_discordance():
    base = np.array([0, 0, 1, 1], dtype=bool)
    case = np.array([1, 1, 0, 1], dtype=bool)
    out = sensitivity.paired_change(base, case)
    # D=[1,1,-1,0], mean=1/4, sample variance=11/12.
    assert out == {"delta_p": 0.25, "paired_mc_se": math.sqrt(11 / 48),
                   "new_failures": 2, "avoided_failures": 1}
    assert sensitivity.paired_change(base, base)["paired_mc_se"] == 0


def test_wilson_known_endpoints_and_midpoint():
    for count in (0, 5, 10):
        out = sensitivity.probability_summary(np.arange(10) < count)
        assert out["failures"] == count and out["survivors"] == 10 - count
        lo, hi = out["mc_wilson_95"]
        if count == 0:
            assert lo == pytest.approx(0, abs=1e-15)
            assert hi == pytest.approx(sensitivity.Z95 ** 2 / (10 + sensitivity.Z95 ** 2))
        elif count == 10:
            assert lo == pytest.approx(10 / (10 + sensitivity.Z95 ** 2))
            assert hi == pytest.approx(1)
        else:
            assert (lo, hi) == pytest.approx((0.236593090512564, 0.763406909487436))


@pytest.mark.parametrize('fee,sale_cost', [(0.0, 0.0), (0.03, 0.1)])
def test_constant_charge_resource_budget_known_answer(fee, sale_cost):
    base = inputs.base()
    # $100m annual charges; no notes, FX charges, price changes or stock conversion.
    inp = dataclasses.replace(base, reserve=25.0, atm_remaining=10.0, usd_cash=0.0,
                              btc_held=100.0, btc_price=1e6, notes=(),
                              pref_usd={k: 0.0 for k in base.pref_usd}, stre_eur=0.0,
                              other_debt_interest=100.0)
    p = params.deterministic(inp, horizon_years=2, participation=1e6, gate=0,
                             fee=fee, btc_sale_cost=sale_cost, mnav_start=1, mnav_level=1)
    result = engine.run(inp, p, record_years=(2,))
    expected = np.array([25, 25 + 10 * (1 - fee),
                         25 + 10 * (1 - fee) + 100 * (1 - sale_cost)]) / 100
    assert result['fail_years'] == pytest.approx(np.repeat(expected[:, None], 4, axis=1), abs=1e-12)
    s = result['snapshots'][2]
    assert s['issued'][1:, :] == pytest.approx(10)
    assert s['principal_due'] == pytest.approx(0)
    # Rounding up to weekly boundary: total charges = 100 * steps * DT.
    assert s['unmet'] == pytest.approx(np.repeat((100 * result['steps'] * DT - 100 * expected)[:, None],
                                               4, axis=1), abs=1e-10)


def test_zero_charges_survive_without_resources():
    base = inputs.base()
    inp = dataclasses.replace(base, reserve=0., atm_remaining=0., btc_held=0., notes=(),
                              pref_usd={k: 0. for k in base.pref_usd}, stre_eur=0., other_debt_interest=0.)
    p = params.deterministic(inp, horizon_years=1, mnav_start=1., mnav_level=1.)
    result = engine.run(inp, p, record_years=(1,))
    assert np.isinf(result['fail_years']).all()
    assert not result['snapshots'][1]['unmet'].any()


def test_report_reproducible_counts_ranking_and_overrides():
    a = sensitivity.build_report(24, 7)
    assert json.dumps(a) == json.dumps(sensitivity.build_report(24, 7))
    assert len(a['drivers']) == 13
    assert sum(len(d['cases']) for d in a['drivers']) == 23
    assert a['provenance']['mnav']['weeks'] == 20
    assert a['provenance']['mnav']['n'] == 19
    ranks = [d['max_abs_delta_p'] for d in a['drivers']]
    assert ranks == sorted(ranks, reverse=True)
    base = a['base']['failures']
    for row in a['drivers']:
        for c in row['cases']:
            assert c['failures'] + c['survivors'] == 24
            assert c['failures'] - base == c['new_failures'] - c['avoided_failures']
            settings = dataclasses.replace(params.default(n_paths=24, seed=7), **c['overrides'])
            f = engine.run(inputs.base(), settings, record_years=())['fail_years'][1]
            assert c['failures'] == int((f <= 5 + 1e-12).sum())


@pytest.mark.parametrize('n,seed', [(1, 0), (True, 0), (2, -1)])
def test_invalid_settings(n, seed):
    with pytest.raises(ValueError):
        sensitivity.build_report(n, seed)


def test_cli_rejects_before_writing(tmp_path):
    output = tmp_path / 'report.json'
    run = subprocess.run([sys.executable, '-m', 'mc.sensitivity', '--paths', '1', '--output', str(output)],
                         capture_output=True, text=True)
    assert run.returncode == 2
    assert 'integer >= 2' in run.stderr
    assert not output.exists()
