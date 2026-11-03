# Four-day canvas validation

- Seven tests pass, including a real PostgreSQL integration test using `cleanviet_test`.
- Coverage: example parsing, unknown dishes, aggregation, covered quantities, unpriced items, unit mismatches, accented lookup, recent-review filtering and missing-provider behavior.
- Integration checks: persistence, revision conflicts, shopping check persistence, meal history and cross-origin write rejection.
- React production build succeeds; frontend production dependency audit reports zero vulnerabilities.
- Additive migration applied; legacy records preserved. Docker seed exits 0; API and PostgreSQL healthy.
- Browser checks: four favorite additions, editable ingredients and toddler notes, confirmation, three shopping groups, item lookup and dark/light modes.
- Mobile: document width equals viewport width at 390 px. Desktop breakpoint checked at 1440 px.
- An editable example week was saved for demonstration; there are no rotation constraints.
- Live Google Places responses are unverified without an API key. Missing-key behavior is tested and labeled. Reviews cannot confirm stock.
- Parsing uses local aliases and dish patterns. Unknown dishes accept manual ingredients; no general-purpose LLM is configured or claimed.
