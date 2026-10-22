# Funding and market methodology

Purpose: explain the assumptions behind the conditional probabilities.

## Static baseline

Base observations follow the original workbook (October 11–15, 2026). The snapshot excludes principal, holds charges constant, and lets common proceeds meet charges subject to the mNAV gate, ADV participation and remaining ATM cap. The reserve funds residual charges. Zero-volatility engine tests reproduce the same reserve/common coverage to floating-point precision using the engine's note-by-note charges. The workbook uses rounded aggregate debt interest: the difference is about $0.005484 million per year. This gives a small, disclosed difference from its reported static result.

The deterministic quarterly-path comparison enables all note puts in cash, 1% issuance fees, reserve-first funding, a 12-month cash floor and no principal lookahead. Weekly discretization reproduces ending cash within $0.000001 million; common proceeds and unmet reserve-only funding are checked within 0.5%. The copied LibreOffice results are external reference evidence, not a fresh Excel execution.

## Market paths

Time steps are seven calendar days / 365.25. BTC follows `d log P = assumed_log_drift*dt + vol*sqrt(dt)*z`. Thus the zero-drift default has a flat **median**, not flat expected price. The bootstrap samples circular eight-week blocks from standardized historical weekly BTC log returns, then rescales to the same drift/volatility. It preserves some empirical tails/clustering but is not a forward forecast or a joint historical bootstrap of all variables.

Log mNAV uses an exact OU step toward `log(level) + gamma*log(P/P_ref)`. The default reference is the starting BTC price (symmetric response); the alternative running-peak reference compresses mNAV during drawdowns. ADV follows log OU. FX is driftless in log terms. Each variable's standardized shock equals `rho*z_BTC + sqrt(1-rho²)*independent_normal`. The full shock structure is positive semidefinite by construction; other correlations arise through the shared BTC factor. Correlations are scenario settings or historical estimates, not guaranteed future relationships.

Calibration is reproduced from the cached histories. BTC: 563 weekly returns from January 2016 to October 20, 2026. mNAV: 20 observations (19 transitions), May 31–October 11, 2026. Its fitted half-life is especially fragile. Base mNAV innovation correlation is deliberately assumed zero; the sample residual estimate is about -0.194. ADV and FX correlations use their historical estimates. See `data/derived/calibration.json` for exact ranges and values.

## Waterfall and first passage

Each tier has independent cash, ATM remaining, shares and BTC balances. Annual charges include preferred dividends converted at scenario FX and note coupon accrual. Put principal is paid if the prior-week common price is below conversion price under the default rule; an all-cash-put scenario is available. At maturity, out-of-the-money principal is paid in cash and in-the-money notes convert into shares. These are policy approximations, not holder-behavior estimates.

Common price is nonnegative mNAV × net BTC value / diluted shares. Prior-week prices determine current conversion moneyness, avoiding an implicit circular solve. Common issuance is capped by ADV × participation × trading days × weekly fraction, remaining ATM, a positive price and the mNAV gate. The common-first policy pays current charges and fills the reserve floor/lookahead target; reserve-first spends cash toward its target before issuing. Issuance reduces ATM capacity and dilutes shares. BTC sales fund only residual need in tier c, after a modeled cost. No new financing programs are introduced in the default scenario.

First failure is the first weekly shortfall, fractionally interpolated within the week. For lump principal events this interpolation is only a numerical approximation; there is no intraday/actual payment-date cash ledger. Failure is absorbing for the first-passage metric, although the ledger continues and records cumulative unmet funding. Twenty-year quantiles are null when the requested quantile is right-censored. JSON null is not a zero or a measured infinite lifetime.

`p` is the fraction of paths with a first failure within a horizon. `se=sqrt(p*(1-p)/N)` is the conditional Monte Carlo standard error. Identical seeds support reproducibility and common random numbers for sensitivity comparisons; the reported scenarios are one-at-a-time changes, not confidence bounds. A finite simulation with p=0 has zero plug-in SE but still uncertainty (roughly 3/N as a simple 95% upper rule of thumb).

## Important exclusions

No corporate operating cash flow, BTC purchase program, issuance-demand curve, tax treatment, new preferreds, new debt, new ATM registration, insolvency process or legal payment-priority model. The seniority snapshot cumulates charges as a comparison; the stochastic engine does not distribute recoveries. Optional non-reserve cash funding is a sensitivity. STRK cash dividends are retained; a stock-dividend election model is not implemented. STRD is accrued in modeled charges even though its noncumulative dividends may be omitted under its terms. The daily-dividend proposal is not a modeled enacted change.
