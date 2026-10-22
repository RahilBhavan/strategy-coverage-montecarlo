# Sources, observation dates and estimated bridges

Purpose: distinguish observed corporate facts, historical calibration and assumed financing policy.

Cutoff: October 21, 2026 America/Detroit. Retrieval timestamps may be October 22 UTC, the same local evening. Primary SEC pages were reopened during this continuation; real-source tests re-parse the frozen filings and check source-byte SHA-256. Direct EDGAR fetching previously returned HTTP 403, so those original responses were copied byte-for-byte from sibling caches. Sidecars retain original URL, sibling path and available retrieval time. No claim of a fresh successful Python EDGAR download is made.

## Corporate filings

- [June 30, 2026 10-Q](https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm): six outstanding note principals, coupons, puts, maturities and split-adjusted conversion prices; five preferred issues, shares, liquidation preferences and seniority. Coupon cash-flow calculation retains the precise note schedule, differing from the workbook's rounded aggregate by $0.005484 million/year.
- [October 12 weekly exhibit](https://www.sec.gov/Archives/edgar/data/1050446/000119312526419726/mstr-ex99_1.htm): October 11 holdings/reserve/cash/common ATM and weekly STRC repurchases. This anchors the static base, not today's fully reconciled balance sheet.
- [October 15 rate notice](https://www.sec.gov/Archives/edgar/data/1050446/000119312526423400/mstr-20261015.htm): STRC 12% rate for the October 16–November 15 period and, conditionally, November calendar month if the proposal passes. Code holds 12% constant as an assumption. It does not model a passed vote.
- [October 19 weekly 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312526424688/mstr-20261019.htm): October 18 roll-forward (848,517 BTC and $4,830 million reserve). The refreshed run still mixes these observations with earlier share/award estimates and Friday market closes.
- [October 5 special-meeting proxy](https://www.sec.gov/Archives/edgar/data/1050446/000119312526413159/d503578ddef14a.htm): meeting October 28; proposed first daily-payment dates are conditional future intentions. Annual/weekly accrual here does not assume those amendments enacted.

## Static model and local derived history

`data/reference/` contains read-only copies of `model/calculator.mjs` and `docs/formula-verification.json` from strategy-preferred-coverage-model commit `096efc4c17c5df4f62f920a45b8a71aed9a546e9`. `provenance.json` gives SHA-256. The source repo was not edited. The workbook's LibreOffice execution is prior evidence; this continuation independently runs the snapshot equations and compares against that saved execution, without claiming a new Excel run.

Base common shares (421.761 million), awards (3.950554 million), STRC shares (87.921436 million), $2 million other-debt annual interest, and 22 million-share ADV are static-model inputs/estimates. STRC counts bridge the Q2 count less cumulative weekly repurchases; the refresh subtracts one further week's repurchases. This is an estimate, not a newly reported share count. `Inputs.sources` names the origin/date per field.

Twenty dat-accretion weekly `m` values (May 31–October 11, 2026) are a **derived** Strategy-definition mNAV series rebuilt from filings, not direct market observations. The series and its own provenance sidecar are frozen here. This definition differs from the reconstructed net mNAV used to initialize the static case. Reusing its dispersion/mean-reversion calibration is a model assumption with a definition mismatch, not an assertion of interchangeability. No changes were made to dat-accretion.

## Market histories

- [Coinbase Exchange BTC-USD candles](https://api.exchange.coinbase.com/products/BTC-USD/candles): daily UTC OHLCV, January 2016–October 20, 2026; sidecar records individual paginated request URLs. This is one venue's observed data. Weekly returns are sampled from its closes.
- [ECB EUR/USD daily references](https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A): January 2016 onward, filtered by the analysis dates. FX calibration uses Friday observations in the frozen file, ending October 16, 2026. An optional source refresh changes the available sample.
- [Yahoo MSTR historical market data](https://finance.yahoo.com/quote/MSTR/history/): secondary split-adjusted close/volume history. ADV calibration starts after the August 2024 split. Yahoo's adjustment conventions and any historical revisions remain a data limitation; no primary exchange volume audit is claimed.

`data/derived/calibration.json` records the exact samples, fitted estimates and source paths. Re-running `mc.history.calibrate()` matches it exactly in the tested environment. Primary financial terms are sourced to SEC; secondary market history and local derived mNAV are explicitly separated.

## Frozen reproducibility

Eighteen raw files, including provenance sidecars, restore offline from `data/frozen/`. Its index supplies original paths, byte lengths and SHA-256. Compressed pieces are <=16 KB so no staged file exceeds 5,000 tokens. The restoration script rejects changed existing sources rather than silently replacing them. Analysis requires no reads from sibling repos once restored. New fetching is optional, not part of the reported run.
