"""Parse the cached primary filings and check them against the figures the static model and Rahil's notes state."""
import hashlib
import json

import pytest

from mc import fetch, sources


def test_raw_files_match_their_recorded_hash_and_url():
    files = [p for p in fetch.RAW.rglob("*") if p.is_file() and not p.name.endswith(".meta.json")]
    assert len(files) >= 9
    for p in files:
        meta = json.loads(p.with_name(p.name + ".meta.json").read_text())
        assert meta["url"].startswith("https://")
        assert hashlib.sha256(p.read_bytes()).hexdigest() == meta["sha256"], p


def test_convertible_notes_from_10q():
    notes = sources.ten_q()["notes"].value
    assert [n["name"] for n in notes] == ["2028", "2029", "2030A", "2030B", "2031", "2032"]
    assert sum(n["principal_musd"] for n in notes) == pytest.approx(6713.659)
    assert {n["name"]: n["put"] for n in notes} == {
        "2028": "2027-09-15", "2029": "2028-06-01", "2030A": "2028-09-15", "2030B": "2028-03-01",
        "2031": "2028-09-15", "2032": "2029-06-15"}
    assert notes[2]["conversion_price"] == 149.77 and notes[5]["coupon"] == 0.0225
    # the 10-Q's own figure: $17.3m of coupon per semi-annual period
    assert sum(n["principal_musd"] * n["coupon"] for n in notes) / 2 == pytest.approx(17.3, abs=0.01)


def test_preferred_stock_from_10q():
    q = sources.ten_q()
    assert q["pref_shares"].value["STRC"] == 104_894_705
    assert q["pref_shares"].value["STRE"] == 7_750_000  # EUR 775m at EUR 100 stated amount
    assert q["pref_liq_usd_m"].value["STRF"] == pytest.approx(1283.969)
    assert q["pref_liq_usd_m"].value["STRD"] == pytest.approx(1402.422)
    assert q["seniority"].value == ["STRF", "STRC", "STRE", "STRK", "STRD"]


def test_weekly_8k_october_11():
    w = sources.weekly_2026_10_11()
    assert w["as_of"] == "2026-10-11"
    assert w["btc_held"].value == 848_250
    assert w["usd_reserve_m"].value == 4880 and w["usd_cash_m"].value == 640.5
    assert w["mstr_atm_remaining_m"].value == 18807.6
    assert w["strc_repurchased_week"].value == 1_932_145


def test_weekly_8k_october_18_is_newer_than_the_static_model():
    w = sources.weekly_2026_10_18()
    assert w["as_of"] == "2026-10-18"
    assert w["btc_held"].value == 848_517
    assert w["usd_reserve_m"].value == 4830 and w["usd_cash_m"].value == 447.3
    assert w["mstr_atm_remaining_m"].value == 18785.6
    assert w["strc_repurchased_week"].value == 1_938_780


def test_strc_rate_and_daily_dividend_vote():
    r = sources.strc_rate()
    assert r.value == 0.12 and r.as_of == "2026-11-01"
    s = sources.special_meeting()
    assert s["meeting"].value == "2026-10-28"
    assert s["strc_daily_first_payment"].value == "2026-11-02"
    assert s["others_daily_first_payment"].value == "2027-01-04"
