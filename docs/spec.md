# Local v1 scope and acceptance

Agreed 2026-10-21: finish existing weekly Monte Carlo code using read-only copies of the static coverage project's inputs. First reproduce its snapshot and deterministic path, explain numerical differences, then simulate correlated BTC/mNAV with reserve-only, reserve/common ATM and reserve/common/BTC-sale funding waterfalls. Record first-passage funding failures, conditional probabilities, path censoring and parameter sensitivities.

Acceptance: cached primary-source parsing and hash checks; deterministic/static agreement; source exhaustion, correlation, negative input and seeded reproducibility tests; exact offline CLI and committed results with run settings. Separate observed inputs, estimated calibration and hypothetical funding policies. The daily dividend vote on Oct 28 remains pending; weekly accrual is not an actual payment calendar. No UI, automation, trading, publishing or license added.

## Authorized publication continuation

The user subsequently authorized correctness repairs, standalone reproduction, CI, portfolio artifacts and a public `RahilBhavan/strategy-coverage-montecarlo` repository. This supersedes the original local-only publishing boundary. The frozen source model copies remain unchanged; no trading, web deployment or license selection is included.
