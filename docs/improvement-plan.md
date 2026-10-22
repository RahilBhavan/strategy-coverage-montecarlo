# Assumption sensitivity and analytic validation

Scope authorized October 22, 2026. Baseline: clean `606f22f`, 55 passing tests.
No glossary or domain-decision files exist in this repository; `docs/spec.md`,
`docs/methodology.md` and `docs/review.md` define its terms and accounting.

Deliver a separate offline, seeded tier-b five-year sensitivity report. Keep the
seven existing result JSON schemas/counts and principal settlement engine intact.
Vary funding policies and calibration-transfer assumptions one at a time with
common random numbers. Rank maximum absolute changes over explicitly selected
endpoints; retain individual changes, counts, paired simulation standard errors
and Wilson intervals. Scenario spread is not parameter uncertainty coverage.

Done conditions:

- A standalone CLI writes a reproducible JSON report with full base settings,
  exact scenario overrides, frozen-input hashes, calibration sample dates/counts,
  exact failure/discordance counts, probabilities and a deterministic ranking.
- Known indicator vectors independently validate paired SE and Wilson endpoints;
  synthetic constant-charge cases validate cash, capped ATM, sale-cost accounting,
  and zero-charge survival against closed-form answers.
- Invalid report CLI settings fail without writing output; repeat runs reproduce
  bytes. Strict default / portable 1e-12 CI reproduction includes the new report
  without relaxing any existing artifact/schema/count check.
- Existing tests and full byte reproduction pass, a five-minute example and
  measured runtime/limits are documented, and scoped changes are committed/pushed.

Non-goals: new data, refitting the 20-week mNAV sample, joint parameter/posterior
uncertainty, a global variance decomposition, default forecasts, engine changes,
visuals, dependencies, licenses or changes to sibling repositories.
