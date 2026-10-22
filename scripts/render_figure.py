"""Generate the README's cumulative first-passage figure from full-run JSON; no graphics dependencies."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render():
    source = json.loads((ROOT / 'results/coverage_distribution.json').read_text())
    data = source['results']['gbm']
    n = source['n_paths']
    survivors = f"{data['c']['censored_share_20y']:.2%}"
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600" viewBox="0 0 900 600" role="img" aria-labelledby="title desc">',
           f'<title id="title">BTC sales leave {survivors} of paths funded through 20 years</title>',
           f'<desc id="desc">Conditional GBM funding exhaustion, including principal. Reserve-only and reserve plus common reach 100% exhaustion by 20 years. Adding BTC sales leaves {survivors} censored at 20 years. These are scenario simulations, not default estimates.</desc>',
           '<rect width="900" height="600" fill="#F5F5EF"/>',
           '<g font-family="IBM Plex Sans,Arial,sans-serif" fill="#111214">',
           f'<text x="36" y="46" font-size="30" font-weight="bold">BTC sales leave {survivors} funded at 20 years</text>',
           '<text x="36" y="78" font-size="22">Compare three funding tiers on the same simulated paths</text>',
           '<text x="36" y="113" font-size="20" fill="#52545A">Share with first funding exhaustion • GBM, including principal</text>']
    x = lambda year: 92 + year / 20 * 754
    y = lambda p: 430 - p * 260
    for p in (0, .5, 1):
        svg.append(f'<path d="M92 {y(p)}H846" stroke="#C6C7BF" fill="none"/>')
        svg.append(f'<text x="78" y="{y(p)+7}" text-anchor="end" font-size="20">{p:.0%}</text>')
    for year in (0, 5, 10, 15, 20):
        svg.append(f'<text x="{x(year)}" y="461" text-anchor="middle" font-size="20">{year}</text>')
    svg.append('<text x="469" y="492" text-anchor="middle" font-size="20">Years from modeled start • half-year bins</text>')
    for tier, color, dash in [('a', '#52545A', '3 5'), ('b', '#111214', ''), ('c', '#52545A', '9 5')]:
        cumulative = 0
        d = f'M{x(0)} {y(0)}'
        for edge, count in zip(data[tier]['hist_edges'][1:], data[tier]['hist_counts']):
            cumulative += count / n
            d += f'H{x(edge):.2f}V{y(cumulative):.2f}'
        svg.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="4" stroke-dasharray="{dash}"/>')
        if tier == 'c':
            svg.append(f'<path d="{d}" fill="none" stroke="#FFE500" stroke-width="2" stroke-dasharray="9 5"/>')
    for xx, text, dash, color in [(92, 'Reserve only', '3 5', '#52545A'),
                                  (317, '+ common ATM', '', '#111214'),
                                  (603, '+ BTC sales', '9 5', '#52545A')]:
        svg.append(f'<path d="M{xx} 141h38" stroke="{color}" stroke-width="4" stroke-dasharray="{dash}"/>')
        svg.append(f'<text x="{xx+48}" y="148" font-size="20">{text}</text>')
    svg.extend(['<text x="36" y="532" font-size="20">20,000 paths • seed 20261021 • frozen snapshot 2026-10-21</text>',
                '<text x="36" y="559" font-size="20" fill="#52545A">Source: results/coverage_distribution.json • survives ≠ indefinite funding</text>',
                '<text x="36" y="586" font-size="20" fill="#52545A">Conditional scenarios; model and parameter error are not shown.</text>', '</g></svg>'])
    return '\n'.join(svg) + '\n'


if __name__ == '__main__':
    (ROOT / 'results/funding_exhaustion.svg').write_text(render())
