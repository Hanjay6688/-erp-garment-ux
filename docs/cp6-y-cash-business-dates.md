# CP6 Y: canonical cash dates after independent X failure

Status: writer candidate, not yet admitted or independently passed. `production_go:false`.

The independent audit on commit `81b23247f4673d5d01d57ee81543d1b5b9886ea4`
kept all X business SQL byte-identical to `fa3f76c74b169d4869721a203650be60cd866160`.
Native [#173](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34805891046)
completed 35 isolated cases: 16 cash-date counterexamples, 19 controls, zero fixture errors.
Its failure remains authoritative. X writer #171 success did not constitute independent PASS.

The three P2 findings are silent per-date cash/report misposting. Opening settlement
in all five AR/AP party categories and vendor payment use session-dependent timestamp
casts. Sales payment forces UTC, making a Jakarta 00:30 original payment enter the
previous day's journal and immutable fact in every caller timezone. In the minimum
reproductions, 0.03 enters cash one day early while owner reports remain READY.
Whole-lifecycle cents still balance; these findings do not establish a stock or HPP loss.

Y adds a new migration and its maintenance-only rollback. It preserves admitted
U/V/W/X source, the original X rollback, and its separate R2 correction. It replaces
six functions: the three affected posting functions, financial-truth checks, report
check propagation, and the report's original-payment-date comparison. The canonical
helper converts timestamps to Jakarta business dates. Sales payment retains its UTC
serialization setting and immutable fact format; linked allocation replacements
continue to use the predecessor reversal's economic date.

Three CRITICAL date detectors propagate to owner reports. Existing mismatches refuse
Y admission atomically and require a reviewed append-only correction; the migration
does not rewrite posted history or restate filed snapshots. Exact predecessor hashes,
owner and ACLs authenticate six private capsule entries. A full 210-table ERP boundary
supports pre-use Y-to-X rollback under closed admission and drained sessions.

The same independent Python zoneinfo oracle runs before Y and after Y. Before Y,
exactly 16 reproduced failures plus 19 controls and zero incomplete cases are mandatory.
After Y, all 35 must pass with READY reports; ten additional writer cases cover replay,
linked inverses, prior-date report preservation, three explicitly privileged detector
corruption probes and four caller-zone future-date refusals. Ten installation refusals
qualify predecessor drift, coherent X capsule tampering, and existing wrong-date facts.

New scripts are invoked and source-pinned by the full-schema workflow. Historical
runtime adapters follow independently pinned Y edges without relaxing rollback
admission. The matrix expands from F–X 380 schedules to F–Y 400 schedules, including
100 demonstrated backend body entries. The complete 533-function catalog must restore
exactly to X before the existing X-to-W and older rollback ladder executes.

Signed JWT/HTTP/UI coverage from existing Auth suites is distinct from the new
cash-date SQL cases: those use real authenticated database sessions with synthetic
JWT claims. New HTTP/UI route reachability remains unproved. No hosted environment,
main, deployment, PR state, or CP7 work is authorized by this change.
