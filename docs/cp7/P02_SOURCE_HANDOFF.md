# P02 — single snapshot source probe

Status: diagnostic SELECT and native fixture PASS at `67f3b0f2b2903758d6acc25e2f73786d5b6411a9` on [run 36480942787](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36480942787). This is a source capture spike, not packet P02 acceptance. Production connection: false.

## What the code does

- `scripts/cp7-src/snapshot/capture_probe.sql` captures six bounded source families (physical identity, dated commercial membership, cutting yield candidates, FG movements, sale lines, lot cost) for one physical root/exact size in one PostgreSQL statement. All domain rows share the same MVCC statement snapshot. Cutting candidates are explicitly UNBOUND_CANDIDATE: model/size agreement cannot prove destination. Signed FG movements are kept as facts; no stock arithmetic or reservation is inferred.
- A missing root, overlapping commercial membership, conflicting current HPP or a source page exceeding 500 rows returns INCOMPLETE. The TypeScript parser rejects this result; UNKNOWN cost never becomes Rp0. The snapshot only claims completeness for those six source collections.
- The native harness uses the unchanged accepted CP6 30-file package on `cp6_rollback`, then an isolated rollback fixture with one root, two child cutting groups, one FG movement, one draft sale and missing HPP. SQL has no ledger write. The harness also runs the query in a read-only transaction against an absent root and checks the before/after ERP boundary and package rollback.

## Verified result and limits

The native fixture returned COMPLETE with two distinct cutting groups (6+7 PCS) labeled UNBOUND_CANDIDATE, one signed FG movement of +9 PCS, one DRAFT sale of 2 PCS, and one lot whose cost is UNKNOWN. Collection lengths matched their counts and all three cutoff fields were identical. The missing-root control returned INCOMPLETE in a read-only repeatable-read transaction. The per-case rollback restored the database and public schema; no advisory lock or other session leaked. The 30-file package install, approved advisor gate, primary-unchanged guard and restoration gate passed. See [compact evidence](evidence/p02/VERIFICATION.json) and [original native result](evidence/p02/CP7_P02_SOURCE_CAPTURE.json).

This proof uses an administrative disposable fixture for the FG movement and draft sale. It does not prove normal posting of those records, actor-facing authorization, six-domain completeness under concurrent changes, or a persisted immutable run. The SQL is internal to the native harness; no browser or server endpoint serves its output.

## What remains to implement in P02

- A scoped actor-facing facade with current-role checks before initial response and before cached/replayed response; authorize finance at the server before its facts enter output.
- Persist coherent facts and dependency vector atomically; provide versioned run/cursor and stale tracking including insert/backdate/reversal/recost/status/role changes.
- Reconstruct AS_KNOWN only where source history proves it, otherwise AS_KNOWN_UNAVAILABLE; implement RESTATED labeling separately.
- Follow source lineage across stages and count physical WIP only once (P03/P04). Prove concurrent updates, partial pages, revocation, controls with Auth/HTTP, independent source-oracle cases E09/E14/E15/E20/E22/X09.
- R10 remains OPEN_CP7 in P11. No operator-facing CP7 data should be displayed from this probe.

Do not confuse a single-statement diagnostic or TypeScript type guard with a production-safe analysis run.
