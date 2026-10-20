# OW04: preserved SQL name-resolution failures

`de3d5c6d23e788481f4d30957cf46615add5f3d6`, run `39478852590`, job `118821836221`: 11/32 PASS, 21 INCOMPLETE, restoration and advisor gate true. All twelve new cases reached the quote builder but stopped on ambiguous `amount`; no new settlement passed. Original case results, representative trace and complete hashed raw log remain in `CI_DE3D_FIRST_FAILURE.json` and `CI_DE3D_FIRST_RUNTIME.log.gz`.

The payment total now explicitly selects `pay.amount`. The same review found six further resolution hazards: local HPP `value` against JSON `value`, HPP local `x`/`b` against query aliases, materialization local `x`, consumer row `ce`, provenance local `id`, and deferred closure local `id`. Query aliases/local names are separated. The provenance query also receives an explicit table alias `fm`; `f` is the destination row variable, not a FROM alias. Selected columns, predicates, order, lock modes, amounts and closure guards remain intact.

`name-clash-fix/RESULT.json` records 14 isolated actual-fragment controls: seven old queries refuse with PostgreSQL `42702`, and the seven changed queries return the expected payment total, JSON row, selected objects, consumer, marker and closure parent. This is name-resolution evidence, not complete ERP Native money/authority proof. Two initial control-harness errors (a missing separator after LOOP and capturing an earlier SQL-language function) are retained separately; no expected assertion was changed to accept them. The control script subsequently limits extraction to the named owning function.

The existing `cp7_plpgsql_clash_check.py` is only a heuristic: it does not check bare column/local collisions and can span an intervening SQL-language function or inspect dynamic SQL literals. It is not used to excuse a runtime error or to claim complete SQL validation. No existing checker or financial expected value is modified.

Reproduce from the repository root with Node, Git history at the pinned predecessor, and PGlite installed:

```sh
PGLITE_MODULE=/absolute/path/to/@electric-sql/pglite/dist/index.js node docs/cp7/d17-14/ow04/name-clash-fix/check.mjs
```

The next real ERP run retains all 32 declared case IDs, monetary/date oracles, immutable-original comparisons, replay assertions, deferred constraints, restoration and advisor gate. OW04 remains incomplete; no product default installation or production authorization changes.

Internal source counter: `name-clash-fix/COUNTER_INITIAL.json` (SHA256 d18c1471832b5048238142adf824bf797b1e05d95123983ab726f74fcd066050) independently records no concrete additional defect in the bounded coordinator/reader scan and no changed predicate, money formula, ORDER, lock mode or closure/refusal branch. It did not execute Native and is not independent external audit.
