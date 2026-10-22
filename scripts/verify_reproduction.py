"""Run the full offline demo and require byte agreement with all committed results.

Use in a clean checkout: this deliberately regenerates results/*.json.
"""
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = sorted((ROOT / 'results').glob('*.json'))
    if len(paths) != 7:
        raise SystemExit('expected seven result JSON files')
    paths.append(ROOT / 'results/funding_exhaustion.svg')
    expected = {p: p.read_bytes() for p in paths}
    subprocess.run([sys.executable, '-m', 'mc.run'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, 'scripts/render_figure.py'], cwd=ROOT, check=True)
    changed = [p.name for p, data in expected.items() if p.read_bytes() != data]
    if changed:
        raise SystemExit('result byte mismatch: ' + ', '.join(changed))
    for path in paths:
        print(hashlib.sha256(path.read_bytes()).hexdigest(), path.name)
    print('All seven full-run JSON results and the figure reproduced byte-for-byte.')


if __name__ == '__main__':
    main()
