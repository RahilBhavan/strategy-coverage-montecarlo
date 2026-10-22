"""Parse the cached primary filings into dated facts. Every fact carries its source URL and as-of date."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from functools import lru_cache

from . import fetch
from .htmltable import num, rows, text

RAW = fetch.RAW / "edgar"


@dataclass(frozen=True)
class Fact:
    value: object
    unit: str
    as_of: str
    url: str


def _doc(name: str) -> tuple[str, str]:
    p = RAW / name
    return p.read_text(encoding="utf-8", errors="replace"), fetch.meta(p)["url"]


def _date(s: str) -> str:
    return dt.datetime.strptime(s.strip(), "%B %d, %Y").date().isoformat()


def _row(table: list[list[str]], label: str, start: int = 0) -> list[str]:
    for r in table[start:]:
        if r[0].startswith(label):
            return r
    raise KeyError(label)


@lru_cache(maxsize=None)
def ten_q() -> dict:
    """Q2 2026 10-Q: convertible notes and preferred stock at June 30, 2026."""
    doc, url = _doc("10q-2026q2.htm")
    t = rows(doc)
    asof = "2026-06-30"
    names = ["2028", "2029", "2030A", "2030B", "2031", "2032"]
    rate = _row(t, "Stated Interest Rate")[1:7]
    conv = _row(t, "Initial Conversion Price")[1:7]
    head = next(i for i, r in enumerate(t) if r[0] == "Convertible Notes" and "Put Option Date (1)" in r)
    notes = []
    for i, n in enumerate(names):
        r = t[head + 1 + i]
        assert r[0] == f"{n} Convertible Notes", r
        notes.append({"name": n, "principal_musd": num(r[1]) / 1000, "maturity": _date(r[2]), "put": _date(r[3]),
                      "coupon": float(rate[i].rstrip("%")) / 100, "conversion_price": num(conv[i])})
    shares = [num(x) for x in _row(t, "Shares Issued as of June 30, 2026")[1:6]]
    liq = [num(x) / 1000 for x in _row(t, "Aggregate Liquidation Preference as of June 30, 2026")[1:6]]
    tickers = ["STRF", "STRC", "STRE", "STRK", "STRD"]
    body = text(doc)
    seg = re.search(r"rank, from highest to lowest, as follows: (.{0,120}?Stock), and (STR[A-Z]) Stock", body)
    order = re.findall(r"STR[A-Z]", seg.group(1)) + [seg.group(2)]
    return {
        "notes": Fact(notes, "$m / dates", asof, url),
        "pref_shares": Fact(dict(zip(tickers, shares)), "shares", asof, url),
        "pref_liq_usd_m": Fact(dict(zip(tickers, liq)), "$m (STRE translated at Jun 30 FX)", asof, url),
        "seniority": Fact(order, "highest to lowest", asof, url),
    }


def _weekly(name: str, asof_label: str) -> dict:
    doc, url = _doc(name)
    t, body = rows(doc), text(doc)
    asof = _date(re.search(r"As of (\w+ \d+, \d{4}), the balances of the USD Reserve", body).group(1))
    m = re.search(r"USD Reserve and USD Cash were \$([\d.]+) billion and \$([\d.]+) million", body)
    mstr = _row(t, "MSTR Stock")
    btc_row = next(r for r in t if len(r) == 6 and re.fullmatch(r"[\d,]+", r[3]) and num(r[3]) > 500_000)
    strc_rep = next(r for r in t if r[0].startswith("STRC Stock (1)"))
    return {
        "as_of": asof,
        "btc_held": Fact(num(btc_row[3]), "BTC", asof, url),
        "usd_reserve_m": Fact(float(m.group(1)) * 1000, "$m", asof, url),
        "usd_cash_m": Fact(float(m.group(2)), "$m", asof, url),
        "mstr_atm_remaining_m": Fact(num(mstr[-1]), "$m", asof, url),
        "mstr_shares_sold_week": Fact(num(mstr[1]), "shares", asof, url),
        "strc_repurchased_week": Fact(num(strc_rep[1]) if strc_rep[1] != "-" else 0.0, "shares", asof, url),
    }


@lru_cache(maxsize=None)
def weekly_2026_10_11() -> dict:
    return _weekly("8k-2026-10-12-ex99_1.htm", "October 11")


@lru_cache(maxsize=None)
def weekly_2026_10_18() -> dict:
    return _weekly("8k-2026-10-19.htm", "October 18")


@lru_cache(maxsize=None)
def strc_rate() -> Fact:
    doc, url = _doc("8k-2026-10-15-strc-rate.htm")
    body = text(doc)
    m = re.search(r"record dates from (\w+ \d+, \d{4}) through (\w+ \d+, \d{4}) will be ([\d.]+)%", body)
    return Fact(float(m.group(3)) / 100, "per annum", _date(m.group(1)), url)


@lru_cache(maxsize=None)
def special_meeting() -> dict:
    doc, url = _doc("def14a-2026-10-05.htm")
    body = text(doc)
    meet = re.search(r"Special Meeting of Stockholders to be held on \w+, (\w+ \d+, \d{4})", body).group(1)
    strc = re.search(r"STRC Stock — Daily Schedule ?\. Pay the first dividend under the daily schedule on (\w+ \d+, \d{4})",
                     body).group(1)
    other = re.search(r"STRF Stock, STRK Stock and STRD Stock — Daily Schedule ?\. Pay the first dividends under the "
                      r"daily schedule on (\w+ \d+, \d{4})", body).group(1)
    return {"meeting": Fact(_date(meet), "date", "2026-10-05", url),
            "strc_daily_first_payment": Fact(_date(strc), "date", "2026-10-05", url),
            "others_daily_first_payment": Fact(_date(other), "date", "2026-10-05", url)}
