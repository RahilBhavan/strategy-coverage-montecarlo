"""Model inputs. The base set reuses the static Excel model's inputs (strategy-preferred-coverage-model, Inputs sheet,
observations Oct 11-15 2026) so results are comparable. Filing-derived values are re-parsed from cached filings and
checked against these numbers in tests/test_sources.py. Each value carries (source URL or label, as-of date).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, replace

from . import history, sources

Q2 = "https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm"
W1011 = "https://www.sec.gov/Archives/edgar/data/1050446/000119312526419726/mstr-ex99_1.htm"
W1018 = "https://www.sec.gov/Archives/edgar/data/1050446/000119312526424688/mstr-20261019.htm"
STRC8K = "https://www.sec.gov/Archives/edgar/data/1050446/000119312526423400/mstr-20261015.htm"
COINBASE = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
YAHOO = "https://finance.yahoo.com/quote/MSTR/history"
ECB = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"
STATIC = "strategy-preferred-coverage-model Inputs sheet (estimate)"
ASSUME = "model assumption"


@dataclass(frozen=True)
class Note:
    name: str
    principal: float  # $m
    coupon: float
    conversion_price: float
    put: dt.date
    maturity: dt.date


@dataclass(frozen=True)
class Inputs:
    label: str
    start: dt.date
    btc_held: float
    btc_price: float
    eurusd: float
    mstr_price: float  # observed, used only to reconstruct the starting net mNAV
    basic_shares_m: float
    awards_m: float
    adv_m: float  # millions of shares per day
    reserve: float  # $m
    usd_cash: float  # $m, excluded from fixed-charge funding by default (as in the static model)
    atm_remaining: float  # $m, MSTR common ATM
    pref_usd: dict  # $m notional, USD preferreds
    stre_eur: float  # EUR m notional
    rates: dict
    strk_conversion_price: float
    notes: tuple
    other_debt_interest: float  # $m per year
    sources: dict = field(default_factory=dict, compare=False)

    # --- static-model definitions -------------------------------------------------------------
    def pref_dividends(self, eurusd: float | None = None) -> dict:
        fx = self.eurusd if eurusd is None else eurusd
        d = {k: v * self.rates[k] for k, v in self.pref_usd.items()}
        d["STRE"] = self.stre_eur * fx * self.rates["STRE"]
        return d

    def debt_interest(self) -> float:
        return sum(n.principal * n.coupon for n in self.notes) + self.other_debt_interest

    def annual_charges(self, eurusd: float | None = None) -> float:
        return sum(self.pref_dividends(eurusd).values()) + self.debt_interest()

    def pref_claims(self, eurusd: float | None = None) -> float:
        fx = self.eurusd if eurusd is None else eurusd
        return sum(self.pref_usd.values()) + self.stre_eur * fx

    def net_value(self, btc_price: float | None = None, mstr_price: float | None = None) -> tuple[float, float]:
        """Static 'Net NAV' sheet: (net BTC value $m, fully diluted shares m). Moneyness at the observed MSTR price."""
        p = self.btc_price if btc_price is None else btc_price
        s = self.mstr_price if mstr_price is None else mstr_price
        otm = sum(n.principal for n in self.notes if s < n.conversion_price)
        itm_shares = sum(n.principal / n.conversion_price for n in self.notes if s >= n.conversion_price)
        strk_itm = s >= self.strk_conversion_price
        pref = self.pref_claims() - (self.pref_usd["STRK"] if strk_itm else 0.0)
        fd = self.basic_shares_m + self.awards_m + itm_shares + (self.pref_usd["STRK"] / self.strk_conversion_price
                                                                   if strk_itm else 0.0)
        net = self.btc_held * p / 1e6 + self.reserve + self.usd_cash - otm - pref
        return net, fd

    def net_mnav(self) -> float:
        net, fd = self.net_value()
        return self.mstr_price * fd / net


def _notes() -> tuple:
    out = []
    for n in sources.ten_q()["notes"].value:
        out.append(Note(n["name"], n["principal_musd"], n["coupon"], n["conversion_price"],
                        dt.date.fromisoformat(n["put"]), dt.date.fromisoformat(n["maturity"])))
    return tuple(out)


def base() -> Inputs:
    """Static model base case, observations Oct 11-15 2026."""
    q = sources.ten_q()
    w = sources.weekly_2026_10_11()
    strc_shares = 104.894705 - 16.973269  # static bridge: 10-Q count less 13 weekly 8-K buybacks (estimate)
    return Inputs(
        label="base-2026-10-15", start=dt.date(2026, 10, 16),
        btc_held=w["btc_held"].value, btc_price=82131.0, eurusd=1.1253, mstr_price=151.29,
        basic_shares_m=421.761, awards_m=3.950554, adv_m=22.0,
        reserve=w["usd_reserve_m"].value, usd_cash=w["usd_cash_m"].value, atm_remaining=w["mstr_atm_remaining_m"].value,
        pref_usd={"STRF": q["pref_liq_usd_m"].value["STRF"], "STRC": strc_shares * 100,
                  "STRK": q["pref_liq_usd_m"].value["STRK"], "STRD": q["pref_liq_usd_m"].value["STRD"]},
        stre_eur=q["pref_shares"].value["STRE"] * 100 / 1e6,
        rates={"STRF": 0.10, "STRC": sources.strc_rate().value, "STRE": 0.10, "STRK": 0.08, "STRD": 0.10},
        strk_conversion_price=1000.0, notes=_notes(), other_debt_interest=2.0,
        sources={
            "btc_held": (W1011, "2026-10-11"), "reserve": (W1011, "2026-10-11"), "usd_cash": (W1011, "2026-10-11"),
            "atm_remaining": (W1011, "2026-10-11"), "btc_price": (COINBASE, "2026-10-15 close (UTC)"),
            "eurusd": (ECB, "2026-10-16"), "mstr_price": (YAHOO, "2026-10-15 close"),
            "adv_m": (YAHOO, "20 trading days to 2026-10-15"),
            "basic_shares_m": (STATIC + ": 10-Q cover count + weekly ATM shares", "2026-10-11"),
            "awards_m": (STATIC + ": Q2 10-Q options/RSU/PSU anchor", "2026-06-30"),
            "pref_usd": (Q2, "2026-06-30; STRC rolled to 2026-10-11 with weekly 8-K buybacks (estimate)"),
            "stre_eur": (Q2, "2026-06-30"), "rates": (STRC8K + " (STRC); " + Q2 + " (fixed rates)", "2026-10-15"),
            "notes": (Q2, "2026-06-30"), "other_debt_interest": (STATIC + ": ~$40m secured debt", "2026-06-30"),
            "strk_conversion_price": ("STRK converts into 0.1 MSTR per $100 stated amount (static model)", "2026-06-30"),
        })


def refreshed() -> Inputs:
    """Base rolled to the Oct 18 2026 weekly 8-K, with market closes on Fri Oct 16. Same estimation method."""
    b = base()
    w = sources.weekly_2026_10_18()
    day = dt.date(2026, 10, 16)
    bd, bc = history.btc_daily()
    md, mc_, _ = history.mstr_daily()
    fd, fx = history.eurusd_daily()
    strc = b.pref_usd["STRC"] - w["strc_repurchased_week"].value / 1e6 * 100
    return replace(
        b, label="refresh-2026-10-18", start=dt.date(2026, 10, 19), btc_held=w["btc_held"].value,
        btc_price=history.close_on(bd, bc, day), mstr_price=history.close_on(md, mc_, day),
        eurusd=history.close_on(fd, fx, day), adv_m=history.adv20(day),
        basic_shares_m=b.basic_shares_m + w["mstr_shares_sold_week"].value / 1e6,
        reserve=w["usd_reserve_m"].value, usd_cash=w["usd_cash_m"].value,
        atm_remaining=w["mstr_atm_remaining_m"].value, pref_usd={**b.pref_usd, "STRC": strc},
        sources={**b.sources, "btc_held": (W1018, "2026-10-18"), "reserve": (W1018, "2026-10-18"),
                 "usd_cash": (W1018, "2026-10-18"), "atm_remaining": (W1018, "2026-10-18"),
                 "btc_price": (COINBASE, "2026-10-16 close (UTC)"), "mstr_price": (YAHOO, "2026-10-16 close"),
                 "eurusd": (ECB, "2026-10-16"), "adv_m": (YAHOO, "20 trading days to 2026-10-16")})
