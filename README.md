# Strategy coverage Monte Carlo: conditional funding exhaustion across three source tiers

[![Offline model verification](https://github.com/RahilBhavan/strategy-coverage-montecarlo/actions/workflows/ci.yml/badge.svg)](https://github.com/RahilBhavan/strategy-coverage-montecarlo/actions/workflows/ci.yml)

![46.24% of GBM paths exhaust tier-b funding (reserve plus common ATM) within 5 years; reserve-only exhausts in every path; adding BTC sales leaves 61.41% funded at 20 years. Funding exhaustion is not legal default.](results/funding_exhaustion.svg)

This Python model asks how long Strategy's funding sources can pay its preferred dividends, debt interest and note principal. It extends the [static preferred-coverage workbook](https://github.com/RahilBhavan/strategy-preferred-coverage-model), an Excel model of one fixed scenario, into weekly BTC, mNAV, trading-volume and EUR/USD paths. It first reproduces the static result, then records the first week each funding tier cannot meet modeled charges. Its probabilities are conditional on chosen processes and financing rules; they are not Strategy default forecasts.

The three funding tiers run on the same simulated paths:

- **Tier a**: the USD cash reserve only.
- **Tier b**: the reserve plus new common stock sold through the at-the-market (ATM) program.
- **Tier c**: tier b plus BTC sales.

## Results

<!-- headline:start -->
- **Headline: 46.24% of 20,000 simulated paths exhaust tier-b funding (reserve + common ATM) within five years** under the base GBM assumptions, including note principal. Monte Carlo standard error: 0.353 percentage points. The block-bootstrap case gives 47.85%. Funding exhaustion means the modeled sources cannot pay charges when due; **it is not legal default**, and unpaid amounts accumulate while the path continues. Source: `results/main.json`, seed 20261021, as of 2026-10-21.
- The figure plots the same 46.24% at year 5 on the 20-year curves. Reserve only (tier a) exhausts in every path; adding BTC sales (tier c) leaves 61.41% of paths funded at 20 years (`results/coverage_distribution.json`). Funded at 20 years means censored, not funded forever.
<!-- headline:end -->
- Static reproduction: $1,559.6675 million annual charges, 37.5465 reserve-only months and 15.1876 reserve-plus-common years. The workbook reports $1,559.6730 million, 37.5463 months and 15.1875 years; the note-interest rounding difference is documented (`results/static_check.json`).
- One-at-a-time assumptions shift five-year tier-b exhaustion from 19.27% (no BTC link in mNAV) to 79.08% (peak-drawdown link), versus 46.21% base in the 10,000-path sensitivity run (`results/tornado.json`). These scenario differences are not confidence bounds.
- A [paired sensitivity report](docs/assumption-sensitivity.md) ranks 13 funding/calibration assumptions, with exact failure counts, Wilson simulation intervals and paired change SEs; parameter uncertainty remains unestimated.
- Results also include principal-on/off comparisons, first-passage distributions and simulation convergence.
- 80 tests cover source hashes, filing parsing, static agreement, source exhaustion, correlation, invalid inputs and reproducibility.

## How it works

`mc/inputs.py` reconstructs dated inputs from read-only source copies and explicit static-model estimates. `history.py` estimates calibration from frozen histories. `paths.py` uses BTC lognormal or block-bootstrap shocks and correlated log-mNAV/ADV mean reversion. `engine.py` maintains separate reserve, ATM capacity, share counts and BTC balances for each tier. `run.py` writes JSON analyses; `whatif.py` handles `--set`.

Terms:

- **mNAV** (net): MSTR's fully diluted market value divided by its net BTC value, which is BTC plus cash minus out-of-the-money convertible notes and preferred claims.
- **1x issuance gate**: no common stock is sold in a week when net mNAV is below 1.0 (`gate`). Strategy has filed no such policy; it is an assumption.
- **ADV participation**: the share of MSTR's average daily trading volume (ADV) that ATM sales may take, 2% by default (`participation`).

## Run it

Tested with Python 3.14.7, NumPy 2.5.4 and pytest 9.1.1. No workbook application or credentials are needed for the frozen run.

```bash
git clone https://github.com/RahilBhavan/strategy-coverage-montecarlo.git
cd strategy-coverage-montecarlo
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
python3 scripts/restore_data.py
.venv/bin/python -m pytest -q
.venv/bin/python -m mc.run
```

For an exact full-run byte comparison, run `.venv/bin/python scripts/verify_reproduction.py`. Regenerate the figure with `python3 scripts/render_figure.py` and the README headline with `python3 scripts/readme_headline.py`.

To change an assumption, pass `--set key=value` (repeatable). Keys are the fields of `mc.params.Params`; a wrong key prints the valid list. It prints base and changed probabilities on the same paths and writes nothing; `--quick` uses 2,000 paths. Raising ADV participation from 2% to 5% took about 5 seconds here:

```bash
.venv/bin/python -m mc.run --set participation=0.05
```

```text
Changed: participation 0.02 -> 0.05
20,000 GBM paths, seed 20261021, principal included, frozen snapshot 2026-10-21.
P(first funding exhaustion within N years), simulation SE in brackets:
tier years              base           changed     change (paired SE)
a        1     0.00% (0.00)     0.00% (0.00)        +0.00 pp (0.00)
a        3    89.96% (0.21)    89.96% (0.21)        +0.00 pp (0.00)
a        5   100.00% (0.00)   100.00% (0.00)        +0.00 pp (0.00)
b        1     0.00% (0.00)     0.00% (0.00)        +0.00 pp (0.00)
b        3    35.45% (0.34)    29.38% (0.32)        -6.07 pp (0.17)
b        5    46.24% (0.35)    40.29% (0.35)        -5.95 pp (0.17)
c        1     0.00% (0.00)     0.00% (0.00)        +0.00 pp (0.00)
c        3     0.47% (0.05)     0.46% (0.05)        -0.01 pp (0.01)
c        5     2.77% (0.12)     2.67% (0.11)        -0.10 pp (0.02)
Tiers: a = reserve only; b = reserve + common ATM; c = reserve + common ATM + BTC sales.
Funding exhaustion is not legal default. SEs cover simulation noise only, not model or parameter error.
```

The full run writes `results/*.json` and took about three minutes on this host. `--quick` uses 2,000 main paths and smaller sensitivity/convergence runs; it also overwrites `results/`. Source refresh (`python -m mc.fetch`) is separate, may depend on sibling caches and changes the snapshot. Restore the committed snapshot for the reported results.

## Repository layout

- `mc/` — input parsers, path processes, validation and funding engine.
- `data/` — compressed raw snapshot, derived calibration and static reference copies.
- `results/` — analysis JSON with settings and estimates.
- `tests/` — real-source, deterministic and stochastic behavior checks.
- `scripts/` — SHA-256-checked snapshot restoration.
- `docs/` — scope, methodology, provenance and verification.

## Documentation

- [Public design system](DESIGN.md): Rahil Design 3.3.0, shared tokens and visual review rules.

- [Scope and acceptance](docs/spec.md) — agreed local v1.
- [Assumption sensitivity](docs/assumption-sensitivity.md) — ranked drivers, analytic checks and a five-minute example.
- [Methodology](docs/methodology.md) — equations, funding policies and probability interpretation.
- [Sources](docs/sources.md) — observed inputs, estimated bridges and frozen provenance.
- [Correctness review](docs/review.md) — proven failures, repairs and remaining evidence limits.
- [Verification](docs/verification.md) — commands and comparison tolerances.

## Sources

[Q2 2026 10-Q](https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm), [October 19 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312526424688/mstr-20261019.htm), earlier October filings and the [special-meeting proxy](https://www.sec.gov/Archives/edgar/data/1050446/000119312526413159/d503578ddef14a.htm) supply dated corporate evidence. Coinbase supplies BTC candles, ECB supplies FX, Yahoo supplies secondary MSTR price/volume data, and the local dat-accretion snapshot supplies 20 weekly mNAV observations. The static reference is copied read-only from commit `096efc4` of strategy-preferred-coverage-model. See [source coverage](docs/sources.md) for ranges and assumptions. Every raw file has a URL/hash sidecar; `data/frozen/index.json` identifies the exact restored bytes.

## Scope and limits

- Independent research, unaffiliated with Strategy. No trades, financing actions or solvency prediction.
- Funding exhaustion is not legal default (see the headline). The 1x issuance gate, ADV participation, financing fee, reserve target and principal pre-funding are policy assumptions. Remaining ATM registration is a cap, not assured demand.
- Annual BTC volatility uses history; the projected log drift is assumed zero. The 20-week mNAV sample is weak evidence. mNAV shock correlation is assumed zero in the base case; the BTC-level link still correlates paths. Sensitivities vary both.
- Weekly accrual is not a dividend/coupon payment calendar. The October 28 daily-dividend vote remains pending on October 21; no amendment is treated as enacted.
- Starting inputs mix observation dates and estimates. No operating cash flow, new preferred issuance, new debt/ATM program, taxes, balance-sheet strategy response or BTC repurchases are modeled. Default runs exclude non-reserve USD cash from funding.
- Note puts use a prior-week moneyness rule; maturity conversion and dilution are scenarios, not observed holder/company decisions. No make-whole adjustments or contractual path-dependent conversion eligibility rules are modeled.
- Calibration uses the October 21 snapshot, including observations after the October 16 static-comparison start. This is retrospective scenario analysis, not an out-of-sample backtest.
- Binomial standard errors describe simulation noise only. They omit parameter, model and data error; zero observed failures does not prove zero risk. Twenty-year survivors are censored, not infinitely funded.

## License

[MIT](LICENSE). The license covers this project's code only. Third-party source material retains its own rights.

Part of [Rahil Bhavan's projects](https://github.com/RahilBhavan).
