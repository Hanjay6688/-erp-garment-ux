# CP6 T — document cents, accounting day and lawful stock inverse

Audited predecessor: S `99fd487bece1c76a189b302f4e79e46920821aa8`.
Single writer; competition branch only. `production_go:false`. DO NOT MERGE.

## Three reproduced P2 findings

1. **COMP-S-T01:** material adjustment recost rounded movement deltas independently
   of the original document journal. Two half-yard rolls at 10000.01 consumed in
   one adjustment, then corrected to 10000.02, produced expense 10000.03 and
   inventory -0.01 with zero physical stock; report remained READY. The correct
   document amounts are expense 10000.02 and inventory zero. Single endpoint,
   decrease, partial consumption and two-material documents reproduce the same
   root cause. These variants are not counted as separate defects.
2. **COMP-S-T02:** S canonicalized the supplier payment date, but the shared
   accounting resolver still compared it with session `current_date`. At
   2026-09-12 17:12 UTC, a legitimate payment for September 13 WIB was refused
   in UTC/New York and accepted in Jakarta/Tokyo. Closed-period redirection used
   the same inconsistent session day. The shared oracle selects real UTC-12 or
   UTC+14 sessions at runtime; it never changes the clock.
3. **COMP-S-T03:** a lawful mixed stock adjustment with original aggregate value
   zero posts no original journal. S refused its linked stock inverse because
   the missing-journal guard examined individual current-value lines. T uses
   the rounded aggregate original valuation and still refuses an absent
   nonzero original journal atomically.

These new counterexamples are backend SQL proofs. HTTP/UI reachability is not
established by those probes. Existing native Auth95 and browser contract suites
are separate evidence and must not be presented as proof of these new routes.

## Repair and consumers

T adds a private append-only `material_adjustment_revaluation_facts` table.
`sync_material_cost_revaluation` routes adjustment movements to a document state
and synchronization pair; its obsolete per-movement adjustment branch is removed.
The target ledger is the difference between rounded original and current document
endpoints, including expense/income classification for mixed-sign documents.
Actual book includes historical per-movement revaluation journals, new facts and
linked reversals. Historical facts are retained; no old movement, journal or
published migration is rewritten.

The material writer owns its normal material locks. A document advisory lock
serializes shared adjustment recost without acquiring another material's row
locks. The native race suite observes actual PostgreSQL blockers for both material
orders and an abort. It records the observed lock kind, uses no manual prelock
and performs no retry. Two immutable-fact triggers, table permissions and
runtime source pins protect the new objects; generic reversal of a protected
revaluation journal is refused in favor of the source correction workflow.

The accounting resolver uses `_cp3_business_date(current_timestamp)`, consistent
with the existing journal `posting_at=now()` transaction instant. It preserves
future-day rejection and resolves closed-period postings to the canonical day.
Three T truth checks are connected to the financial report: future economic
dates, document revaluation balance, and fact/original-journal agreement.

## Upgrade and rollback boundary

The forward migration pins S's platform bytes, three-function capsule and every
additional replaced input with owner/ACL. It records six predecessor functions,
installs three private helpers and rejects pre-existing inconsistent adjustment
or future-day journal history atomically. It does not silently repair history.

T's pre-use boundary hashes 73 tables, including both adjustment tables, the
new fact table and S's capsule. Rollback requires the established maintenance
admission closure and session drain. It verifies independent predecessor and
installed pins, refuses post-use history, restores all six definitions/ACLs,
and removes every T helper/table/capsule. The native workflow compares the entire
S function catalog before T and after rollback, then runs the unchanged S-to-base
ladder. No compatibility helper or newly created fact object is left behind.

## Required proof, not a publication claim

The shared SQL oracle has 21 cases: 15 affected S paths and six controls. Both
phases roll back to READY; unsafe-history upgrade refusal follows each case's
actual persisted state. Final T must pass all 21, three shared-document native
races, Auth95, the existing 34 native races and three abort qualifications,
M's three money races, R's two receipt/invoice races, 300 maintenance schedules
(75 real backend body entries), 134 fixture-orchestration unit cases, rollback,
cleanup, build, frontend tests and exact-SHA CodeQL. Fixture-orchestration units
are mocked; PGlite is local SQL evidence; neither substitutes for native proof.

The final artifact manifest binds every payload and changed source to the exact
Git head/tree/run attempt. Writer verification never grants independent audit
acceptance, merge authority or production GO. CP7 rev3, CP7.5 and CP8 remain in
the preserved master context.
