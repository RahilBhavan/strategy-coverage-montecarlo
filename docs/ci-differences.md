# CI numeric difference record

Purpose: preserve the actual observed CI evidence without inferring unrecorded numeric differences.

- Run [39718711960](https://github.com/RahilBhavan/strategy-coverage-montecarlo/actions/runs/39718711960), `fc07497`: 53 tests passed, one failed. Actual ADV kappa was `19.535832566239154` versus frozen `19.535832566239165`; mNAV mean was `0.10562308661402076` versus `0.1056230866140207`. Those observed BLAS reductions justify the narrow recalibration test tolerance (`rel=1e-12`, `abs=1e-14`) with exact dates/counts/schema.
- Run [39718803909](https://github.com/RahilBhavan/strategy-coverage-montecarlo/actions/runs/39718803909), `e6baafa`: 54 tests passed; full run completed in 207 seconds, then failed byte comparison only for `coverage_distribution.json`. No actual numeric/structural diff was retained, so its cause is **unproven**.
- Diagnostic run [39719280761](https://github.com/RahilBhavan/strategy-coverage-montecarlo/actions/runs/39719280761), `5e9735c`: 55 tests passed; full run took 230 seconds. It reported **zero differing files and zero numerical differences**. Its final success message mentioned a numerical tolerance, but no tolerance was exercised: all eight generated artifact hashes below equal the committed hashes.

The initial mismatch’s exact cause remains unproven. CI’s portable policy permits JSON float differences with relative/absolute tolerance `1e-12`, while schema, types, counts, text and SVG bytes stay exact. This threshold is an explicit engineering acceptance policy; no particular tolerated full-result delta was observed in the successful run. Default reproduction remains byte-strict. All source bytes and static reference copies remain unchanged.

Exact diagnostic-run artifact SHA-256 values:

```text
aa7dfed82f7a422ebdd104d7865db25639b25340292aec0a961856c05baab0b0 convergence.json
fb5e1a3649cd1097e6c0419387559cc6658cb90cd964b67457dd8be2ffe92dce coverage_distribution.json
69ed5e2bc44b803154107b038adecd43e52963aa49ba0c33093fb356f1e219e4 heatmap.json
557edee9f615f4ade096db7d007694959c5063ae7a038093a37120ce300a8569 main.json
84dc5379e276c6436e6aa2a80469ce1393915b6f45f89d4480b22a3697016e38 refresh_compare.json
be44da82f25fabea18de1537b76d9a134eb7b15502b650f5b81b726ae107c5da static_check.json
8f9941948b0312a4dd7f07f153ebe5707d50ca0a9a8f5194802851c9ebb7b47b tornado.json
5b0b84cbedad77b1a271fdc3de254e9db711b69a6097fbd6e9a68b40b61f9717 funding_exhaustion.svg
```
