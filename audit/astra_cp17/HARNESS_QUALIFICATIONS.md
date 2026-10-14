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

## Q03 — regression logging collision after 76 completed cases

First regression job 115719087495, run 38523724159, recorded 76 PASS rows
before Python logging collided with a case result's existing `case` field.
The case itself, CROSS:SUPPLIER_CENT:CORRECTION_ROUND_DELTA, was already saved.
Correction changes the log envelope to `case_id` and preserves the result's
original `case`. Continuation carries the byte-exact first BUSINESS.json,
explicitly marks all 76 as not executed again, and executes only the missing
284 baseline cases plus originally planned supplements. Expected maps and
case operations remain unchanged. First raw artifact: 11874823769, SHA-256
00e182422829867b0a15050e1016f4c1b52ca0f86a715196281edfcd3fc0ee14.

## Q04 — AR installation verifier predates CP7

First AR job 115719087397 recorded sequential146 (145 PASS, one historical
INCOMPLETE for ACCESSORY_CONNECTED_ZERO) and its one PASS replacement
ACCESSORY_CONNECTED_ZERO_REFUSED_BC_FREE_POLICY. The latter is the existing
ERP-DEC02 expected-change disposition; the old raw result remains INCOMPLETE.
Before any of the 28 race operations, the old BA verifier rejected the intended
CP7 replacement of get_owner_financial_snapshot_v2. No AR race executed.

Continuation uses candidate P21 FULL verification, executes each unchanged
race operation in a fresh child clone, proves parent boundary equality and
OID-bound disposal. Sequential147 are not repeated. First raw artifact:
11874359808, SHA-256
a3c61eec1d07d850e41e0ec7c32cfeb19ba78466ab3aa919fb25152d24b270ae.

## Q05 — C0 admission uses obsolete BA reader definition

Run38526619037 completes all original326+AS34, AO12, approved supplements but rejects `erp.get_owner_financial_snapshot_v2(date,date,date)` before C0 case execution. Zero C0 cases ran. A separate c0-oracles-only phase changes only T2 admission to the candidate FULL verifier, retaining the exact pinned25-case oracle and adjustment transport adapter. No earlier case is rerun and all earlier raw statuses remain unchanged.
