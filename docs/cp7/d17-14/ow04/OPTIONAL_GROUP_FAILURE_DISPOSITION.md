# OW04: optional accounts, grouped component order and retained refusal

Candidate `6d350f79dacd41cecb0c0e80d2c62ffb8b723dd8`, run `39481082837`, job `118829518238`: 19/32 Native cases PASS, 13 INCOMPLETE. Restoration and advisor gate true. Ten retained return controls, all eight retained readers, and E01 passed; the allocation-cap control still stopped on a changed refusal code. None of twelve new paid settlements passed. Full first errors and hashed raw runtime log are preserved in `CI_6D350_FIRST_FAILURE.json` and `CI_6D350_FIRST_RUNTIME.log.gz`.

1. CREDIT mode put JSON null in the nullable cash snapshot column. JSON null is not SQL NULL, so the guard tried to load a nonexistent cash account. Only the private typed snapshot fields now normalize JSON null to SQL NULL; selected objects remain byte-identical. Both owning tables reject JSON null/arrays/scalars with object-or-SQL-NULL CHECKs. The quote/source JSON, selected-account eligibility, strict missing-ID refusal, current master comparison and refund-required snapshot checks stay intact.
2. The component loop grouped `z->'component_ordinal'` but ordered a different `z->>'component_ordinal'` expression, which PostgreSQL rejects. Order now casts the grouped JSON numeric expression to integer. Group keys, one component per UUID/JSON/ordinal, all signed parts and numeric ordering remain unchanged.
3. An extra HPP preflight returned its generic quantity code before the retained Native allocation guard. The identical selected-allocation bound is now checked first with `AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION`; the other owned/aggregate HPP checks retain their predicate and generic refusal. No amount/capacity expected or original Native guard is weakened.

`optional-group-fix/RESULT.json`: 15 isolated controls execute the actual cash facts helper and query fragments. Old absent-cash and grouped-order failures are reproduced; new absence is allowed, selected cash survives, deleted cash still refuses, malformed optional shapes refuse, component groups remain unique and ordered 1/2/10, and allocation over-cap refuses while a valid quantity proceeds. These are not full ERP posting or authority proof. The bounded internal counter in `COUNTER_INITIAL.json` found no concrete weakening or semantic counterexample; it did not execute Native or perform external audit.

Reproduce from repo root with Node, Git history and PGlite:

```sh
PGLITE_MODULE=/absolute/path/to/@electric-sql/pglite/dist/index.js node docs/cp7/d17-14/ow04/optional-group-fix/check.mjs
```

The next Native qualification keeps the same 32 IDs and every original financial/date/replay/permission/constraint/restoration assertion. Default product installation, frozen audit candidate and `production_go:false` remain unchanged.
