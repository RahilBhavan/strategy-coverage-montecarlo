# Verification record

Purpose: record actual source, deterministic, stochastic and reproducibility checks, October 21, 2026 local time. Commands use a repository-local `.venv` built from `requirements.txt`; the historical records below ran in an equivalent venv under the author's scratch directory.

## Commands exercised

```bash
python3 scripts/restore_data.py
.venv/bin/python -m pytest -q
.venv/bin/python -m mc.run --quick
.venv/bin/python -m mc.run
```

**44 tests pass**, on Python 3.14.7, NumPy 2.5.4 and pytest 9.1.1. Quick and full runs completed; committed main results use 20,000 paths, seed 20261021. Sensitivities use 10,000 paths, the BTC/mNAV grid uses 2,000 per cell, and convergence uses eight seeds through 50,000 paths. Full analysis took about two minutes on this host. README dependency setup was exercised under scratch.

The full analysis was run twice and all seven JSON outputs compared equal after removing the subsequently deleted, unused `strk_in_stock=false` metadata field from the earlier main result. A later histogram serialization correction was tested independently and regenerated with the same 20,000-path settings. Numeric probabilities did not change. A clean staged-file copy then restored all sources, passed 44 tests, reran the complete full analysis and reproduced all seven current result JSON files byte-for-byte. Exact repeatability is conditional on the pinned NumPy version and inputs; changing calibration or process rules changes results.

Source tests check all cached raw hashes and parse Q2 note/preferred terms plus October filings/proxy. Market tests check actual date-selected closes, volume and historical return calculations. Recalibrating from frozen raw inputs exactly reproduced `data/derived/calibration.json` in this environment.

Zero-volatility paths reproduce static reserve-only and reserve/common coverage using note-derived annual charges to floating-point precision. The independent saved workbook reference differs by about $0.005484 million annual debt interest due to rounding; reserve/common years differ by about 0.0000534 years. The quarterly/weekly path comparison checks ending cash within $0.000001 million and gross common/unmet funding within 0.5%, including $6,713.659 million put principal. The copied prior LibreOffice verification is not a fresh Excel execution.

Behavior checks include empty reserves/ATM/BTC (immediate failure), exhausted common capacity, BTC sales, nonnegative balances, no issuance with nonpositive equity, gate closure, principal timing and put moneyness, same/different seeds, observed shock correlation, OU stationarity, historical bootstrap blocks, binomial simulation variability, invalid settings and reporting beyond the simulated horizon. First-passage histogram edges/counts are tested to partition observed failures and explicit censoring.

## Corrections to partial work

Fixed deterministic override collisions, integer-initialized money/BTC arrays, a deterministic test's `inf-inf` comparison, and histogram bins/censoring. Added run-boundary validation, explicit conditional-probability labels, strict CLI arguments and frozen standalone source restoration. Removed an unused stock-dividend election setting whose dilution was not implemented. The existing engine, calibration and research artifacts were reused.

No corporate forecast validation, default-probability calibration, legal solvency model, independent venue-volume audit or live market integration is claimed. The short derived mNAV series uses a different definition from starting net mNAV; its parameter transfer is explicitly an assumption.

## Publication review verification

After the original v1 record above, the review repaired principal valuation, integer share handling, horizon coverage and principal-due naming. **54 tests now pass** in a newly created scratch venv installed only from `requirements.txt`, with Python 3.14.7 / NumPy 2.5.4 / pytest 9.1.1. No configured static type checker applies to this Python repository.

A tracked-source scratch copy restored 18 files without sibling repositories, passed the then-current 53-test suite, and ran the full analysis in 144 seconds. All seven regenerated JSON files matched byte-for-byte. A subsequent cap-binding regression brought the suite to 54; it changes no numerical code. The remote-clone and CI evidence is recorded in [publication.md](publication.md).

`python scripts/verify_reproduction.py` reruns the full analysis and figure generator, then compares all seven JSON files and the SVG with their starting bytes. CI uses this behavioral check after restoration and tests; it requires no source-network access, credentials or paid services. Only dependency installation and GitHub runner setup need the network. Actions are pinned to immutable commits, Python and direct dependencies to exact versions, the runner to Ubuntu 24.04, with `contents: read` permission and no schedule.

The figure is generated from the GBM first-passage histogram in `results/coverage_distribution.json`, with shared linear axes and explicit 20-year censoring. Its brief passed the present-data checker; the two warnings are a 30px headline below social-card guidance and an agent-only reader test. The 900px SVG is a zoomable documentation artifact, not a social card. Browser inspection covered full width and 400px; labels use IBM Plex Sans when available with Arial/sans-serif fallback. The figure is not a confidence band or parameter-uncertainty estimate.

The first GitHub runner exposed a test-portability error: exact recalibration equality rejected BLAS/CPU differences of a few floating-point ulps (for example ADV kappa `19.535832566239154` versus `19.535832566239165`). Recalibration tests now use relative `1e-12` / absolute `1e-14` tolerance for floating estimates, while dates, counts and schema remain exact. The frozen calibration file and source bytes were not changed. Full result byte reproduction is a separate check.

The next GitHub run passed all 54 tests but differed in bytes only for `coverage_distribution.json`; that failed run did not preserve the actual differing values. A diagnostic run at `5e9735c` then passed 55 tests and reproduced **every artifact byte-for-byte**, emitting no numeric differences. This does **not** establish the earlier mismatch's exact cause.

CI uses `scripts/verify_reproduction.py --portable`: JSON floating values may differ by relative/absolute `1e-12`; schema, types, counts, strings and SVG bytes remain exact. Any tolerated differences are printed. This is an explicit cross-CPU acceptance policy, not a claim that specific floating differences were observed in the successful run. Default CLI reproduction stays byte-strict. A negative test rejects a one-path probability change, count changes, date changes and schema changes; it permits a one-ulp quantile change. The suite has **55 tests**. The separate recalibration tolerance above is supported by its actual recorded BLAS differences.

The fresh GitHub clone on the original host reproduced all seven JSON files **and** the SVG exactly, first in 140 seconds with 54 tests, then in 155 seconds with 55 tests after updating. The [CI difference record](ci-differences.md) includes exact successful-run artifact hashes. Cross-machine byte identity is not guaranteed on every CPU/BLAS build. These checks establish computational reproduction, not parameter or model accuracy.

## October 22 assumption-sensitivity slice

The full suite now passes **65 tests** (4.29 seconds on the original host).
New checks independently verify paired-indicator standard errors, Wilson
boundaries, constant-charge cash/ATM/BTC resource budgets with fees, zero-charge
survival, exact failure counts and reproducible report ranking. The standalone
CLI rejects invalid path counts before writing output. See
[assumption sensitivity](assumption-sensitivity.md) for settings, measured report
runtime, input hashes and the five-minute reproduction command.

The new report is separate from the seven legacy results. It describes conditional
simulation error and selected scenario effects; parameter uncertainty remains
unestimated. No engine, calibration, frozen source or figure changes are included.

A fresh full `python scripts/verify_reproduction.py` run completed the legacy
analysis in 129 seconds and reproduced all seven JSON outputs, the SVG and the
new sensitivity report **byte-for-byte**. A separate CLI report invocation also
matched the committed report exactly. CI retains its existing portable tolerance;
local strict verification did not require it.

## Reader-test follow-up (October 22, 2026)

`python -m mc.run --set key=value` (repeatable) changes any `mc.params.Params` field, validates it with the engine's run-boundary checks, and prints base and changed tier probabilities on the same seed with binomial and paired SEs. It writes nothing. `tests/test_whatif.py` adds 15 tests (80 total): type coercion, unknown keys listing valid keys, invalid values, paired identity when nothing changes, no writes, exit code 2 and the README sample. The figure title was changed to the five-year tier-b value, and `scripts/readme_headline.py --check` (in CI) pinned the README headline to `results/main.json`. Model math and the seven result JSON files are unchanged; only the SVG bytes changed.

## Methods README (October 22, 2026)

The README now describes the method and its checks and states no result probability. It no longer embeds the figure, because the curves encode the result. `scripts/readme_headline.py` writes the README method block (path count, seed, snapshot date, BTC processes, horizons, censoring and convergence settings) from `results/main.json`, `results/coverage_distribution.json` and `results/convergence.json`. Its `--check` mode, still in CI, fails if that block is stale or if any probability strictly between 0 and 1 from the main run, the first-passage distribution or the tornado appears in `README.md` or `docs/`, rounded to two decimal places. The README `--set` sample is now the first four lines of real output; `tests/test_whatif.py` checks that it is a prefix of a fresh run. Result JSON files, the SVG and the model are unchanged.

## Re-check 2026-10-24

This file is a chronological log; earlier test counts describe earlier commits. At `81dcd3e` in a fresh clone, Python 3.14.7, NumPy 2.5.4 and pytest 9.1.1: `pytest -q` passed 83 tests; `scripts/readme_headline.py --check` passed; `scripts/verify_reproduction.py --portable` (2m28s) and the strict `scripts/verify_reproduction.py` both reproduced all seven JSON results, the sensitivity report and the SVG byte-for-byte (strict mode on this host). `pip-audit` found no known vulnerabilities in `requirements.txt`.
