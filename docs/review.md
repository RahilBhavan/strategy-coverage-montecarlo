# Correctness review

Purpose: record the prove-then-fix audit of local v1 `43d12b7` before publication.

The baseline was clean and passed 44 tests in the pinned scratch venv. Review covered correctness, error handling, security, accessibility, performance, dead code and project conventions. Accessibility is limited to CLI/docs and the generated figure; there is no application UI. No performance change or speculative refactor was justified. No credentials, private account data, database artifacts or oversized blobs were found in the publication scan; this is a bounded review, not security certification.

## Proven and repaired

1. **Principal settlement inflated equity before issuance.** A synthetic $1,000m cash note due this week against $999m BTC assets and no cash had negative net equity, yet the original engine issued $5.106m of common. It removed the debt claim before cash settlement. The valuation now subtracts the cash principal due until the waterfall pays it. `test_cash_principal_remains_a_claim_until_funded` failed before the fix and passes afterward. The independent reviewer also reproduced a solvent-to-failed classification change with a binding volume cap.
2. **Integer share inputs crashed fractional issuance.** `basic_shares_m=422` passed boundary validation but created an integer NumPy array. Float issuance raised a casting error. Share balances now initialize as floats. The regression failed before and passes afterward.
3. **Rounded horizons missed failures.** A reserve lasting 364.5 days was reported as surviving one year because the engine stopped at day 364. Runs/snapshots now round up to a weekly boundary, and summaries cannot extend beyond simulated time. The regression compares one-year and 53-week paths and observes the same exhaustion at day 364.5.
4. **Principal due was labeled paid.** With zero available funding, `principal_paid` could equal the entire cash obligation. The field is now `principal_due`, which preserves the actual metric without inventing a payment-priority policy. Tests assert a $1,000m due amount alongside $1,000m unmet funding. Consumers of raw engine snapshots must adopt the corrected field name; committed analysis JSON does not expose this field.

The final suite has 54 passing tests. Added evidence covers prior-week moneyness despite opposing current-week shocks, maturity dilution, restoration retry/idempotence, refusal to overwrite modified sources, corrupted-bundle rejection, immutable static-reference hashes and exact recalibration. Source model copies were not edited. All full results were regenerated after the numerical repair.

## Independent review

One bounded, read-only T3 Codex review examined committed v1 independently, loading its engine from Git to avoid concurrent fixes. Task ID: `node:delegated-task:command%3Amcp%3Af2c6ccc7-15cf-4cc1-931c-ae406a846bfb%3Adelegate-task%3Astrategy-coverage-audit-1`. It confirmed principal valuation, horizon truncation and misleading principal naming. The root agent reproduced, fixed and verified each finding; no implementation was delegated.

## Unresolved limits

The 20-point derived mNAV calibration and definition mismatch, mixed observation dates, partial ADV week, FX holiday gaps and weekly cash timing remain limitations. October 21 calibration is retrospective relative to ledger starts. Binomial standard errors measure simulation error, not parameter/data/model uncertainty. The one-at-a-time scenarios vary policies and parameters; they are not confidence intervals. Correlation tests cover selected BTC/mNAV and BTC/FX relationships, not every joint bootstrap statistic. No legal-default, insolvency-recovery, holder-behavior or predictive calibration claim is made.

Source hashes establish byte integrity, not independent source authenticity. Primary filings were re-parsed offline against their retained URLs; no fresh source retrieval was used for this publication pass. The October 28 proposal remains pending in the frozen October 21 corpus.
