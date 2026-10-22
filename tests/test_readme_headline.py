import subprocess
import sys
from pathlib import Path

from scripts import readme_headline as rh

ROOT = Path(__file__).resolve().parents[1]


def test_check_passes_on_committed_readme_and_docs():
    done = subprocess.run([sys.executable, 'scripts/readme_headline.py', '--check'], cwd=ROOT,
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert 'no result probability appears' in done.stdout


def test_result_probability_in_a_published_file_is_reported(tmp_path):
    main = rh.load('main.json')
    figures = rh.embargoed(main, rh.load('coverage_distribution.json'), rh.load('tornado.json'))
    headline = f"{main['results']['gbm|with_principal']['prob']['b']['5']['p']:.2%}"
    assert headline in figures
    leaked = tmp_path / 'README.md'
    leaked.write_text(f'Headline: {headline} of paths exhaust tier-b funding.\n')
    clean = tmp_path / 'methods.md'
    clean.write_text('20,000 paths, seed 20261021, 0.00% and 100.00% are not embargoed.\n')
    assert rh.leaks(figures, [leaked, clean]) == [f'README.md: {headline}']


def test_method_block_numbers_come_from_results():
    block = rh.render(rh.load('main.json'), rh.load('coverage_distribution.json'), rh.load('convergence.json'))
    readme = (ROOT / 'README.md').read_text()
    assert block in readme
    main = rh.load('main.json')
    assert f"{main['n_paths']:,} weekly paths" in block and str(main['params']['seed']) in block
