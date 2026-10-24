"""`python -m mc.run --set key=value`: validated overrides, paired base comparison, nothing written."""
import subprocess
import sys
from pathlib import Path

import pytest

from mc import whatif

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run([sys.executable, '-m', 'mc.run', *args], cwd=ROOT, capture_output=True, text=True,
                          timeout=300)


def test_parse_coerces_to_field_types():
    got = whatif.parse(['participation=0.05', 'n_paths=500', 'principal=false', 'model=bootstrap',
                        'strc_rate=none', 'btc_window=2018-01-01,2026-10-20'])
    assert got == {'participation': 0.05, 'n_paths': 500, 'principal': False, 'model': 'bootstrap',
                   'strc_rate': None, 'btc_window': ('2018-01-01', '2026-10-20')}


@pytest.mark.parametrize('pair, message', [
    ('nope=1', 'Valid keys: model, horizon_years'),
    ('participation', 'expects key=value'),
    ('participation=lots', 'must be a number'),
    ('participation=nan', 'must be finite'),
    ('participation=-0.1', 'participation must be nonnegative'),
    ('n_paths=2.5', 'must be an integer'),
    ('principal=maybe', 'true or false'),
    ('fee=1', 'fees must lie in [0,1)'),
    ('model=heston', 'unknown model'),
])
def test_parse_rejects_bad_values_with_reason(pair, message):
    with pytest.raises(ValueError, match=message.replace('[', r'\[').replace(')', r'\)')):
        whatif.parse([pair])


def test_duplicate_key_rejected():
    with pytest.raises(ValueError, match='more than once'):
        whatif.parse(['gate=1.2', 'gate=0'])


def test_compare_is_paired_and_reproduces_base_when_nothing_changes():
    same = whatif.compare({'n_paths': 400, 'participation': 0.02})
    assert all(r['p'] == r['base_p'] and r['change_pp'] == 0 for r in same['rows'])
    more = whatif.compare({'n_paths': 400, 'participation': 0.05})
    b5 = next(r for r in more['rows'] if r['tier'] == 'b' and r['years'] == 5)
    assert b5['p'] < b5['base_p'] and b5['change_se_pp'] > 0
    assert {r['years'] for r in whatif.compare({'n_paths': 50, 'horizon_years': 2})['rows']} == {1}


def test_cli_prints_headline_and_writes_nothing(tmp_path):
    results = ROOT / 'results/main.json'
    before = results.read_bytes()
    done = run_cli('--quick', '--set', 'participation=0.05')
    assert done.returncode == 0, done.stderr
    assert 'participation 0.02 -> 0.05' in done.stdout
    assert '2,000 GBM paths' in done.stdout
    b5 = next(line.split() for line in done.stdout.splitlines() if line.startswith('b ') and line.split()[1] == '5')
    assert b5[2].endswith('%') and b5[4].endswith('%')
    assert 'not legal default' in done.stdout
    assert results.read_bytes() == before


def test_cli_unknown_key_exits_2_listing_valid_keys():
    done = run_cli('--set', 'participaton=0.05')
    assert done.returncode == 2
    assert "unknown setting 'participaton'" in done.stderr and 'participation' in done.stderr.split('Valid keys:')[1]
    assert done.stdout == ''


def test_readme_example_is_real_output():
    readme = (ROOT / 'README.md').read_text()
    command = 'python -m mc.run --set participation=0.05'
    assert command in readme
    sample = readme.split(command, 1)[1].split('```text\n', 1)[1].split('```', 1)[0]
    done = run_cli('--set', 'participation=0.05')
    assert done.returncode == 0, done.stderr
    assert sample.count('\n') >= 4 and done.stdout.startswith(sample)
