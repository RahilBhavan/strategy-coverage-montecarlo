# Publication receipt

Purpose: record public source publication and the observed verification evidence.

- Public repository: [RahilBhavan/strategy-coverage-montecarlo](https://github.com/RahilBhavan/strategy-coverage-montecarlo).
- Default branch: `main`. Original history begins at `43d12b7`; no force push or unrelated-history rewrite was used.
- Reviewed numerical repairs: `b0b6bad`. Publication/CI additions: `fc07497`. Tested implementation with portable diagnostics: `5e9735c2a2efe8f73c8bfaa7336f3e7bb3dcda44`.
- Verified [GitHub Actions run 39719280761](https://github.com/RahilBhavan/strategy-coverage-montecarlo/actions/runs/39719280761): **success**, 55 tests, full analysis in 230 seconds. All seven JSON results and the SVG matched their committed hashes; the run emitted no difference diagnostics.
- Verification date: October 21, 2026 America/Detroit (October 22 UTC). Financial corpus remains frozen as of October 21, independently of later runtime dates. October 28 daily-dividend proposal remains pending in that corpus.

## Fresh-clone evidence

A fresh clone from GitHub under `~/scratch/strategy-coverage-montecarlo/` restored 18 SHA-256-checked raw source files without siblings or source-network access. A newly created venv installed `requirements.txt` (Python 3.14.7, NumPy 2.5.4, pytest 9.1.1). After updating the clone to `5e9735c`, these commands passed:

```bash
python scripts/restore_data.py
python -m pytest -q
python scripts/verify_reproduction.py
```

The suite passed **55 tests**. The full analysis took 155 seconds and all seven JSON files plus `results/funding_exhaustion.svg` reproduced **byte-for-byte**. The clone remained clean. [Exact artifact hashes and CI difference evidence](ci-differences.md) distinguish this from the earlier failed runner: that runner reported a byte mismatch only in `coverage_distribution.json`, without preserving the exact numeric/structural diff. Its cause remains unproven. CI permits relative/absolute `1e-12` JSON floating differences but requires exact schema/types/counts/text and SVG; default reproduction stays byte-strict. The successful diagnostic run did not exercise that allowance.

## Review and publication boundaries

Four demonstrated issues were repaired: principal settlement valuation, integer share-array casting, truncated reporting horizons and principal-due naming. See [review.md](review.md) for failing inputs and regression evidence. Source/static-reference copies and frozen calibration were preserved. GitHub About/topics describe conditional funding exhaustion, without default estimates or calibration claims.

Before the initial push, current tracked/new files and all reachable Git-history blobs were inspected, including decoding all 18 compressed snapshot entries. The final scan then covered 119 reachable blobs, largest 16,000 bytes; no credential-pattern match or private account/hub artifact was found. Subsequent commits contain only reviewed source/tests/docs. Public filing contact details and public author/provenance metadata are retained. Hooks ran; no staged file exceeded 20,000 bytes. This was a bounded review, not a security certification.

Remaining limits include weak and definition-mismatched mNAV calibration, retrospective mixed observation dates, weekly timing approximations and unmeasured model/parameter error. Probabilities describe conditional funding exhaustion, not default. No license file yet; third-party material retains its rights. No website deployment, trades, messages or recurring services were created.
