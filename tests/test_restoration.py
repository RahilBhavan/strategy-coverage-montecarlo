"""Offline persistence, retry and integrity checks of the portable source bundle."""
import hashlib
import json

import pytest

from mc.fetch import ROOT
from scripts import restore_data


def test_restore_is_idempotent_and_rejects_modified_sources(tmp_path):
    assert restore_data.restore(tmp_path) == 18
    index = json.loads((restore_data.FROZEN / 'index.json').read_text())
    before = {item['path']: (tmp_path / item['path']).read_bytes() for item in index}
    assert restore_data.restore(tmp_path) == 18
    assert all((tmp_path / path).read_bytes() == data for path, data in before.items())
    path = tmp_path / index[0]['path']
    path.write_bytes(b'changed source')
    with pytest.raises(ValueError, match='refusing to overwrite'):
        restore_data.restore(tmp_path)
    assert path.read_bytes() == b'changed source'


def test_corrupted_bundle_is_rejected_before_source_write(tmp_path, monkeypatch):
    frozen = tmp_path / 'bundle'
    frozen.mkdir()
    (frozen / 'part').write_bytes(__import__('gzip').compress(b'corrupted'))
    (frozen / 'index.json').write_text(json.dumps([
        {'path': 'restored/source', 'parts': ['part'], 'bytes': 8, 'sha256': '0' * 64}]))
    monkeypatch.setattr(restore_data, 'FROZEN', frozen)
    with pytest.raises(ValueError, match='hash mismatch'):
        restore_data.restore(tmp_path)
    assert not (tmp_path / 'restored/source').exists()


def test_reference_copies_still_match_original_provenance():
    folder = ROOT / 'data/reference'
    provenance = json.loads((folder / 'provenance.json').read_text())
    for name, digest in provenance['files'].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest


def test_frozen_calibration_is_reproducible():
    from mc import history
    expected = json.loads((ROOT / 'data/derived/calibration.json').read_text())
    actual = history.calibrate()
    assert actual.keys() == expected.keys()
    for group, fields in expected.items():
        assert actual[group].keys() == fields.keys()
        for name, value in fields.items():
            # OLS/correlation reductions vary by a few ulps across BLAS/CPU builds.
            if isinstance(value, float):
                assert actual[group][name] == pytest.approx(value, rel=1e-12, abs=1e-14)
            else:
                assert actual[group][name] == value
