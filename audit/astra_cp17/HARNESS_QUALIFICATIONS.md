# Qualification notes — every first result retained

## Q01 — own-contract workflow configuration, no cases executed

Run 38525347545 at d91a31570aabc365c60413e242d9737ec1ad7e7f failed during
workflow evaluation. The copied job still referenced `matrix.timeout`, while
the new three-entry matrix omitted that field. No job/case execution occurred.
Correction: fixed `timeout-minutes: 180`, matching the predeclared maximum used
by the baseline wave. No case, fixture, input, expected value or status changed.
The replacement commit/run will be recorded; the failed run is not erased.

## Q02 — baseline phase restoration expectation

Temporal first run 38523724159, job 115719087438, attempt 1: all AT16, AU15,
four temporal races and six master races returned PASS. The two sequential
groups restored their full boundary, public catalog, functions/owners/ACLs,
and had no missing cases. The final FULL uninstall comparison failed because
the original temporal phase commits `api.seed` and temporal-race fixtures in
the disposable clone. These retained fixture rows were compared with the
empty pre-phase state by Astra's new outer wrapper. Public catalog and complete
function definition/owner/ACL components matched; ERP data did not.

This is an auditor orchestration limitation, not a proven product restore
defect. Original raw ZIP 11875343186 is retained with SHA-256
abd3f982560546db6485f915e91104143c198885c5c10266eeeaa4ae80104181.
The run remains red/INCOMPLETE at the outer gate; no post-case rerun is requested.
Any later tool qualification must use a separate declared isolation probe and
preserve the full before/after data difference and all first case results.
