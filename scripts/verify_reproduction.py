"""Regenerate full offline results; strict bytes by default, tiny numeric tolerance for cross-CPU CI.

Use in a clean checkout: this deliberately regenerates results/*.json and the SVG.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def compare_numeric(expected, actual, location='$'):
    """Require identical schema/counts/text; return only tolerated float-rounding differences."""
    if type(expected) is not type(actual):
        raise ValueError(f'{location}: type mismatch')
    if isinstance(expected, dict):
        if expected.keys() != actual.keys():
            raise ValueError(f'{location}: key mismatch')
        return [row for key in expected for row in compare_numeric(expected[key], actual[key], f'{location}.{key}')]
    if isinstance(expected, list):
        if len(expected) != len(actual):
            raise ValueError(f'{location}: length mismatch')
        return [row for i, (a, b) in enumerate(zip(expected, actual))
                for row in compare_numeric(a, b, f'{location}[{i}]')]
    if expected == actual:
        return []
    if isinstance(expected, float) and math.isclose(expected, actual, rel_tol=1e-12, abs_tol=1e-12):
        return [f'{location}: {expected!r} -> {actual!r} (abs delta {abs(expected-actual):.3g})']
    raise ValueError(f'{location}: value mismatch')


def main(portable=False):
    paths = sorted((ROOT / 'results').glob('*.json'))
    if len(paths) != 7:
        raise SystemExit('expected seven result JSON files')
    paths.append(ROOT / 'results/funding_exhaustion.svg')
    report = ROOT / 'reports/assumption_sensitivity.json'
    paths.append(report)
    expected = {p: p.read_bytes() for p in paths}
    subprocess.run([sys.executable, '-m', 'mc.run'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, 'scripts/render_figure.py'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, '-m', 'mc.sensitivity', '--output', str(report)], cwd=ROOT, check=True)
    changed = [p for p, data in expected.items() if p.read_bytes() != data]
    for path in changed:
        if not portable or path.suffix != '.json':
            raise SystemExit('result byte mismatch: ' + path.name)
        rounding = compare_numeric(json.loads(expected[path]), json.loads(path.read_bytes()), path.name)
        print(f'{path.name}: byte difference; numeric check passed ({len(rounding)} rounding differences)')
        for row in rounding:
            print(' ', row)
    for path in paths:
        print(hashlib.sha256(path.read_bytes()).hexdigest(), path.name)
    print('All seven legacy JSON results, sensitivity report and figure reproduced ' +
          ('within strict numerical tolerance (SVG bytes exact).' if portable else 'byte-for-byte.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--portable', action='store_true', help='allow only floating rounding across CPU builds')
    main(portable=parser.parse_args().portable)
