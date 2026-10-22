"""Fetch and cache raw source data under data/raw/ with a .meta.json sidecar (URL, fetch time, sha256).

Run: python -m mc.fetch
Later runs read the cache. EDGAR returned HTTP 403 to the project User-Agent on 2026-10-21 (SEC wants a contact
email), so EDGAR documents are copied byte-for-byte from sibling repositories' caches; the sidecar records the
original EDGAR URL, the sibling path and the sibling's own fetch time.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import shutil
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UA = "RahilBhavan-research (github.com/RahilBhavan)"
PROJECTS = pathlib.Path.home() / "projects"
EDGAR = "https://www.sec.gov/Archives/edgar/data/1050446/"

# (local name, EDGAR URL, sibling cache path, sibling meta path or None)
EDGAR_COPIES = [
    ("10q-2026q2.htm", EDGAR + "000105044626000044/mstr-20260630.htm",
     "strc-rate-controller/data/raw/edgar/000105044626000044-mstr-20260630.htm"),
    ("8k-2026-10-12-ex99_1.htm", EDGAR + "000119312526419726/mstr-ex99_1.htm",
     "dat-accretion/data/raw/000119312526419726/mstr-ex99_1.htm"),
    ("8k-2026-10-15-strc-rate.htm", EDGAR + "000119312526423400/mstr-20261015.htm",
     "strc-rate-controller/data/raw/edgar/000119312526423400-mstr-20261015.htm"),
    ("8k-2026-10-19.htm", EDGAR + "000119312526424688/mstr-20261019.htm",
     "strc-rate-controller/data/raw/edgar/000119312526424688-mstr-20261019.htm"),
    ("def14a-2026-10-05.htm", EDGAR + "000119312526413159/d503578ddef14a.htm",
     "strc-rate-controller/data/raw/edgar/000119312526413159-d503578ddef14a.htm"),
]
DAT_WEEKLY = "dat-accretion/data/weekly.csv"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _write(path: pathlib.Path, body: bytes, meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    meta = {**meta, "bytes": len(body), "sha256": _sha(body)}
    path.with_name(path.name + ".meta.json").write_text(json.dumps(meta, indent=1) + "\n")


def meta(path: pathlib.Path) -> dict:
    return json.loads(path.with_name(path.name + ".meta.json").read_text())


_last = [0.0]


def get(url: str) -> bytes:
    wait = 0.35 - (time.time() - _last[0])  # well under 10 req/s
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    _last[0] = time.time()
    return body


def copy_edgar(refresh: bool = False) -> None:
    for name, url, rel in EDGAR_COPIES:
        dst = RAW / "edgar" / name
        if dst.exists() and not refresh:
            continue
        src = PROJECTS / rel
        sib_meta = src.with_name(src.name + ".meta.json")
        sib = json.loads(sib_meta.read_text()) if sib_meta.exists() else None
        body = src.read_bytes()
        _write(dst, body, {"url": url, "copied_utc": _now(), "via": str(src),
                           "sibling_fetch": sib.get("fetched_utc") if sib else "sibling git-tracked file, no sidecar"})
    src = PROJECTS / DAT_WEEKLY
    dst = RAW / "dat-accretion" / "weekly.csv"
    if refresh or not dst.exists():
        _write(dst, src.read_bytes(), {"url": "https://github.com/RahilBhavan/dat-accretion/blob/main/data/weekly.csv",
                                       "copied_utc": _now(), "via": str(src),
                                       "note": "column m = Strategy-definition mNAV rebuilt from weekly 8-Ks; "
                                               "each row's filing URL is in dat-accretion data/stated.csv"})


def fetch_btc(refresh: bool = False, start="2016-01-01", end="2026-10-20") -> None:
    """Coinbase Exchange BTC-USD daily candles, 300 days per request."""
    out = RAW / "coinbase" / "btc-usd-daily.json"
    if out.exists() and not refresh:
        return
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    rows, urls = {}, []
    while d0 <= d1:
        e = min(d0 + dt.timedelta(days=299), d1)
        url = (f"https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400"
               f"&start={d0.isoformat()}T00:00:00Z&end={e.isoformat()}T00:00:00Z")
        for t, lo, hi, op, cl, vol in json.loads(get(url)):
            rows[t] = [t, lo, hi, op, cl, vol]
        urls.append(url)
        d0 = e + dt.timedelta(days=1)
    body = json.dumps({"columns": ["time", "low", "high", "open", "close", "volume"],
                       "rows": [rows[k] for k in sorted(rows)]}).encode()
    _write(out, body, {"url": "https://api.exchange.coinbase.com/products/BTC-USD/candles (granularity=86400)",
                       "requests": urls, "fetched_utc": _now(), "range": [start, end],
                       "note": "secondary market data; daily candles in UTC"})


def fetch_mstr(refresh: bool = False, start="2020-01-01", end="2026-10-21") -> None:
    out = RAW / "yahoo" / "mstr-daily.json"
    if out.exists() and not refresh:
        return
    p1 = int(dt.datetime.fromisoformat(start).replace(tzinfo=dt.timezone.utc).timestamp())
    p2 = int(dt.datetime.fromisoformat(end).replace(tzinfo=dt.timezone.utc).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/MSTR?period1={p1}&period2={p2}&interval=1d&events=split"
    _write(out, get(url), {"url": url, "fetched_utc": _now(),
                           "note": "secondary market data; Yahoo split-adjusts close and volume"})


def fetch_eurusd(refresh: bool = False, start="2016-01-01") -> None:
    out = RAW / "ecb" / "eurusd-daily.csv"
    if out.exists() and not refresh:
        return
    url = f"https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata&startPeriod={start}"
    _write(out, get(url), {"url": url, "fetched_utc": _now(), "note": "ECB euro foreign exchange reference rate"})


def main(refresh: bool = False) -> None:
    copy_edgar(refresh)
    fetch_btc(refresh)
    fetch_mstr(refresh)
    fetch_eurusd(refresh)
    for p in sorted(RAW.rglob("*")):
        if p.is_file() and not p.name.endswith(".meta.json"):
            print(f"{p.relative_to(ROOT)}  {p.stat().st_size:>9} bytes")


if __name__ == "__main__":
    import sys
    main(refresh="--refresh" in sys.argv)
