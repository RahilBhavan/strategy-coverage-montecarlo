"""Minimal HTML table reader for EDGAR filings (stdlib only)."""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser


def clean(s: str) -> str:
    s = html.unescape(s).replace("\xa0", " ").replace("​", "")
    return re.sub(r"\s+", " ", s).strip()


class _Rows(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell, self.depth = [], None, None, 0

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(clean("".join(self.cell)))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            cells = [c for c in self.row if c and c not in ("$", "€", "%", ")")]
            if cells:
                self.rows.append(cells)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def rows(doc: str) -> list[list[str]]:
    p = _Rows()
    p.feed(doc)
    return p.rows


def text(doc: str) -> str:
    doc = re.sub(r"(?is)<(script|style).*?</\1>", " ", doc)
    doc = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|li|h\d)>", "\n", doc)
    return clean(re.sub(r"<[^>]+>", " ", doc))


def num(s: str) -> float:
    s = s.replace(",", "").replace("$", "").replace("€", "").strip()
    neg = s.startswith("(") and s.endswith(")")
    v = float(s.strip("()"))
    return -v if neg else v
