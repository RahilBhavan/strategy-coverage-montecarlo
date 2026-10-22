# Which assumptions drive conditional exhaustion?

The new [machine-readable report](../reports/assumption_sensitivity.json) measures
**tier-b first funding exhaustion within five years**, with principal included.
It uses 4,000 GBM paths, seed 20261021, the unchanged October 21 frozen snapshot,
and 23 scenarios across 13 assumptions. It does not estimate default probability.

In this run, base exhaustion is 45.475% (1,819/4,000). Its conditional simulation
SE is 0.7873 percentage points and its 95% Wilson interval is 43.9369–47.0217%.
These differ from the larger legacy run because path count changes the draw
layout. The new report does not replace the 20,000-path main analysis.

The largest selected-endpoint changes are:

- Using the peak-drawdown mNAV link: 79.425%, a +33.950 percentage-point change;
  paired simulation SE 0.749 percentage points.
- Removing the mNAV BTC-level link: 18.900%, a −26.575-point change;
  paired SE 0.699 points.
- Removing the issuance gate: 22.900%, a −22.575-point change;
  paired SE 0.661 points.
- Setting the reserve floor to zero months: 58.575%, a +13.100-point change;
  paired SE 0.534 points.

Thus the mNAV response specification and financing gates are consequential in
this selected grid. This ranking depends on the chosen endpoint ranges, horizon,
tier and base settings. It is not a universal ranking of importance. Unlimited
ATM capacity produces no change in these paths; this does not prove it never
binds in other scenarios. All-cash puts can alter earlier pre-funding and share
valuation as well as cash obligations, so its small decrease here is not evidence
that larger obligations always improve coverage.

## Reproduce in five minutes

From the repository root, after the README's pinned environment setup:

```bash
python3 scripts/restore_data.py
"$HOME/scratch/strategy-coverage-montecarlo/venv/bin/python" -m pytest -q tests/test_sensitivity.py
"$HOME/scratch/strategy-coverage-montecarlo/venv/bin/python" -m mc.sensitivity \
  --paths 4000 --seed 20261021 \
  --output "$HOME/scratch/strategy-coverage-montecarlo/sensitivity-example.json"
"$HOME/scratch/strategy-coverage-montecarlo/venv/bin/python" -c \
  'from pathlib import Path; import os; assert Path("reports/assumption_sensitivity.json").read_bytes() == (Path(os.environ["HOME"])/"scratch/strategy-coverage-montecarlo/sensitivity-example.json").read_bytes(); print("Exact report match")'
```

Measured October 22, 2026 on the original Linux host: default report 9.95 seconds,
peak child-process RSS 51,688 KB; Python 3.14.7 / NumPy 2.5.4. Setup/network speed
is excluded. Paths are vectorized; memory and work increase with path count.
`--paths 1000` is a faster exploration, with more simulation noise, and will not
match the committed report. No source fetch, account or sibling repo is needed.

The original seven result JSONs and SVG retain their schemas and exact expected
bytes. `scripts/verify_reproduction.py` now also regenerates this separate report;
default comparison is byte-strict. CI's existing `--portable` policy still permits
only relative/absolute `1e-12` JSON float differences, with exact types, schema,
counts and strings, and exact SVG bytes. No tolerance was broadened.

## How uncertainty is separated

Every case reuses the same GBM draw sequence: only non-random-policy or coefficient
settings change. Each case stores its exact overrides and all base settings are
saved. The report records failures, survivors and 95% Wilson intervals for each
conditional probability. Wilson intervals have a nonzero width even at zero or
all observed failures; the plug-in binomial SE alone does not have this property.
They are approximate simulation intervals, not guarantees of finite-sample coverage.

For paired indicators, let D_i = I(case fails)_i − I(base fails)_i. The reported
change is mean(D), and paired simulation SE is sqrt(sample_variance(D)/N), with
N−1 in the sample variance. Exact new/avoided failure counts make this calculation
auditable. Using independent-binomial error bars would discard the coupling.
No significance flag or multiple-comparison claim is made; a zero paired SE means
no observed discordance, not proof of an exactly zero population effect.

**Parameter uncertainty remains unestimated.** The endpoint spread is a scenario
exercise, not a confidence/credible interval or a probability distribution over
parameters. The mNAV calibration has only 20 derived observations and 19
transitions (May 31–October 11, 2026), and its definition differs from starting
net mNAV. No bootstrap or asymptotic fit interval can cure that definition mismatch.
Joint assumptions, interactions, alternative future data and model error remain
outside this one-at-a-time exercise. BTC bootstrap process comparison remains in
the legacy analysis; it is omitted here to preserve the identical GBM coupling.

## Analytic checks and evidence

`tests/test_sensitivity.py` verifies D=[1,1,−1,0], whose mean is 1/4 and sample
variance is 11/12. Wilson boundaries use known zero/all-event solutions and an
independent midpoint value. Synthetic constant-price runs with no notes and
$100m annual charges exhaust at resource budget / $100m: reserve alone,
reserve + net capped ATM, and those sources + BTC net of sale cost. They also
check gross issuance, unmet balances at the rounded weekly horizon and zero-charge
survival. Existing principal-settlement, prior-week moneyness and static-workbook
checks remain active. No financial source/calibration bytes or engine logic change.

Statistical reference: [NIST/SEMATECH e-Handbook §7.2.4.1](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm),
opened October 22, 2026, supplies the Wilson score formula; it is primary methods
evidence, not support for the financial assumptions. No quoted text or new vendor
data is stored. Financial provenance remains [sources.md](sources.md); the report
records SHA-256 of the frozen index and calibration, exact sample dates/counts,
and the illustrative endpoint source. Existing tornado endpoints are reused,
with a new explicit 0/24-month reserve-floor scenario around the 12-month base.
