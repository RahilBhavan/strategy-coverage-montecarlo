"""Write the README headline from results/*.json so its numbers match the figure and are never hand-typed.

    python scripts/readme_headline.py          # rewrite the marked README block
    python scripts/readme_headline.py --check  # fail if the README block is stale
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / 'README.md'
START, END = '<!-- headline:start -->', '<!-- headline:end -->'


def render():
    main = json.loads((ROOT / 'results/main.json').read_text())
    dist = json.loads((ROOT / 'results/coverage_distribution.json').read_text())
    gbm = main['results']['gbm|with_principal']['prob']['b']['5']
    boot = main['results']['bootstrap|with_principal']['prob']['b']['5']
    survivors = dist['results']['gbm']['c']['censored_share_20y']
    seed = main['params']['seed']
    return '\n'.join([
        START,
        f"- **Headline: {gbm['p']:.2%} of {main['n_paths']:,} simulated paths exhaust tier-b funding (reserve + "
        f"common ATM) within five years** under the base GBM assumptions, including note principal. Monte Carlo "
        f"standard error: {100 * gbm['se']:.3f} percentage points. The block-bootstrap case gives {boot['p']:.2%}. "
        f"Funding exhaustion means the modeled sources cannot pay charges when due; **it is not legal default**, and "
        f"unpaid amounts accumulate while the path continues. Source: `results/main.json`, seed {seed}, as of "
        f"{main['as_of']}.",
        f"- The figure plots the same {gbm['p']:.2%} at year 5 on the 20-year curves. Reserve only (tier a) "
        f"exhausts in every path; adding BTC sales (tier c) leaves {survivors:.2%} of paths funded at 20 years "
        f"(`results/coverage_distribution.json`). Funded at 20 years means censored, not funded forever.",
        END])


def updated(text, block):
    head, sep, rest = text.partition(START)
    _, sep2, tail = rest.partition(END)
    if not (sep and sep2):
        raise SystemExit(f'README.md is missing the {START} ... {END} markers')
    return head + block + tail


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='fail if the README headline differs from results')
    args = parser.parse_args()
    text = README.read_text()
    new = updated(text, render())
    if args.check:
        if new != text:
            raise SystemExit('README headline is stale; run python scripts/readme_headline.py')
        print('README headline matches results/main.json and results/coverage_distribution.json')
    elif new != text:
        README.write_text(new)
        print('Updated README headline from results/')
    else:
        print('README headline already matches results/')


if __name__ == '__main__':
    main()
