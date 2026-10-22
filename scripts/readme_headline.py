"""Write the README's method summary from results/*.json and keep result probabilities out of the README and docs.

    python scripts/readme_headline.py          # rewrite the marked README block
    python scripts/readme_headline.py --check  # fail if the block is stale or a result probability appears

The README is a methods piece: it states what is simulated and how, never the estimated probabilities.
Those stay in results/*.json. The check renders every probability strictly between 0 and 1 from the
main run, the first-passage distribution and the tornado, and fails if any appears in README.md or docs/.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / 'README.md'
START, END = '<!-- headline:start -->', '<!-- headline:end -->'


def load(name):
    return json.loads((ROOT / 'results' / name).read_text())


def render(main, dist, convergence):
    p = main['params']
    cases = sorted({key.split('|')[0] for key in main['results']})
    if cases != ['bootstrap', 'gbm']:
        raise SystemExit(f'results/main.json cases changed: {cases}; update the README method block')
    horizon = dist['results']['gbm']['b']['hist_edges'][-1]
    sizes = [row['n'] for row in convergence['rows']]
    *early, last = sorted(main['results']['gbm|with_principal']['prob']['b'], key=float)
    return '\n'.join([
        START,
        f"- **Paths:** {main['n_paths']:,} weekly paths per case, seed {p['seed']}, frozen snapshot {main['as_of']}. "
        f"Each path moves BTC price, mNAV, MSTR trading volume and EUR/USD together.",
        f"- **Two BTC processes:** lognormal (GBM) with assumed zero log drift and {p['btc_vol']:.1%} annual volatility "
        f"estimated from {p['btc_window'][0]} to {p['btc_window'][1]}, and a circular block bootstrap of historical "
        f"weekly returns in {p['block_weeks']}-week blocks, rescaled to the same drift and volatility. Both run with and "
        f"without note principal.",
        f"- **What is counted:** the share of paths whose funding tier first cannot pay modeled charges within "
        f"{', '.join(early)} and {last} years, with its binomial standard error. Survival is tracked to {horizon:g} "
        f"years; paths still funded then are censored.",
        f"- **Convergence:** the five-year tier-b estimate is rerun across {convergence['seeds']} seeds at "
        f"{sizes[0]:,} to {sizes[-1]:,} paths to compare seed spread with the binomial standard error.",
        END])


def embargoed(main, dist, tornado):
    values = [cell['p'] for case in main['results'].values() for tier in case['prob'].values() for cell in tier.values()]
    values += [tier['censored_share_20y'] for case in dist['results'].values() for tier in case.values()]
    values += [tornado['base']] + [row[k] for row in tornado['rows'] for k in ('low', 'high') if row[k] is not None]
    return sorted({f'{v:.2%}' for v in values if 0 < v < 1})


def published_files():
    return [README, *sorted((ROOT / 'docs').glob('*.md')), *sorted((ROOT / 'docs').glob('*.json'))]


def leaks(figures, files):
    return [f'{path.name}: {fig}' for path in files for fig in figures if fig in path.read_text()]


def updated(text, block):
    head, sep, rest = text.partition(START)
    _, sep2, tail = rest.partition(END)
    if not (sep and sep2):
        raise SystemExit(f'README.md is missing the {START} ... {END} markers')
    return head + block + tail


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='fail if the method block is stale or a result leaks')
    args = parser.parse_args()
    main_run, dist = load('main.json'), load('coverage_distribution.json')
    text = README.read_text()
    new = updated(text, render(main_run, dist, load('convergence.json')))
    if args.check:
        if new != text:
            raise SystemExit('README method block is stale; run python scripts/readme_headline.py')
        found = leaks(embargoed(main_run, dist, load('tornado.json')), published_files())
        if found:
            raise SystemExit('Result probabilities appear in the README or docs:\n' + '\n'.join(found))
        print('README method block matches results/; no result probability appears in README.md or docs/')
    elif new != text:
        README.write_text(new)
        print('Updated README method block from results/')
    else:
        print('README method block already matches results/')


if __name__ == '__main__':
    main()
