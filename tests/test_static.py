"""The static Excel model's snapshot figures (docs/formula-verification.json, LibreOffice) reproduce from inputs."""
import pytest

from mc import inputs, static


@pytest.fixture(scope="module")
def base():
    return inputs.base()


def test_charges_and_net_mnav(base):
    assert sum(base.pref_dividends().values()) == pytest.approx(1523.073002, abs=1e-6)
    # workbook uses the filed $17.3m semi-annual coupon; the note schedule gives $0.005m/yr less
    assert base.annual_charges() == pytest.approx(1559.673002, abs=0.01)
    assert base.net_mnav() == pytest.approx(1.17456717826807, rel=1e-10)
    net, fd = base.net_value()
    assert net == pytest.approx(55521.74565) and fd == pytest.approx(431.0530776696268)


def test_snapshot_coverage(base):
    s = static.snapshot(base)
    assert s["share_price"] == pytest.approx(151.29)
    assert s["reserve_months"] == pytest.approx(37.546331779102, rel=1e-5)
    assert s["years_reserve_plus_common"] == pytest.approx(15.1875424974497, rel=1e-5)
    assert static.snapshot(base, mnav=0.8)["years_reserve_plus_common"] == pytest.approx(3.12886098159183, rel=1e-5)


def test_calculator_behaviour_checks(base):
    """The seven checks in the static repo's model/check-calculator.mjs."""
    s0 = static.snapshot(base)
    assert static.snapshot(base, mnav=0.8)["years_reserve_plus_common"] == pytest.approx(base.reserve / s0["charges"])
    assert static.snapshot(base, strc_rate=0.15)["reserve_months"] < s0["reserve_months"]
    assert static.snapshot(base, btc_price=30000)["share_price"] < s0["share_price"]
    assert static.snapshot(base, mnav=1.0)["annual_common"] > 0
    assert static.snapshot(base, mnav=0.9999)["annual_common"] == 0


def test_coverage_by_seniority_matches_workbook(base):
    rows = {r["claim"]: r for r in static.by_seniority(base)}
    assert rows["STRC"]["reserve_months"] == pytest.approx(47.9978703108888, rel=1e-4)
    assert rows["STRC"]["reserve_plus_common_years"] == pytest.approx(19.415204111615598, rel=1e-4)
    assert rows["STRD"]["reserve_plus_common_years"] == pytest.approx(15.187542497449734, rel=1e-4)
    assert rows["STRF"]["reserve_plus_common_years"] == 50.0  # display cap


def test_refreshed_inputs_roll_forward_one_week(base):
    r = inputs.refreshed()
    assert r.reserve == 4830 and r.btc_held == 848_517
    assert r.pref_usd["STRC"] == pytest.approx(base.pref_usd["STRC"] - 193.878)
    assert r.annual_charges() < base.annual_charges()


def test_frozen_workbook_reference_agrees(base):
    import json
    from mc.fetch import ROOT
    ref = json.loads((ROOT / "data/reference/formula-verification.json").read_text())["cases"]["Base"]
    s = static.snapshot(base)
    assert s["reserve_months"] == pytest.approx(ref["snapshotMonths"], rel=1e-5)
    assert s["years_reserve_plus_common"] == pytest.approx(ref["snapshotYears"], rel=1e-5)
