# P02 — single snapshot source probe

Status: diagnostic SELECT and native test prepared. The run result records the exact candidate SHA and must be checked before updating this status. Production connection: false.

## What the code does

- `scripts/cp7-src/snapshot/capture_probe.sql` captures six bounded source families (physical identity, dated commercial membership, cutting yield candidates, FG movements, sale lines, lot cost) for one physical root/exact size in one PostgreSQL statement. All domain rows share the same MVCC statement snapshot. Cutting candidates are explicitly UNBOUND_CANDIDATE: model/size agreement cannot prove destination. Signed FG movements are kept as facts; no stock arithmetic or reservation is inferred.
- A missing root, overlapping commercial membership, conflicting current HPP or a source page exceeding 500 rows returns INCOMPLETE. The TypeScript parser rejects this result; UNKNOWN cost never becomes Rp0. The snapshot only claims completeness for those six source collections.
- The native harness uses the unchanged accepted CP6 30-file package on `cp6_rollback`, then an isolated rollback fixture with one root, two child cutting groups, one FG movement, one draft sale and missing HPP. SQL has no ledger write. The harness also runs the query in a read-only transaction against an absent root and checks the before/after ERP boundary and package rollback.

## What remains to implement in P02

- A scoped actor-facing facade with current-role checks before initial response and before cached/replayed response; authorize finance at the server before its facts enter output.
- Persist coherent facts and dependency vector atomically; provide versioned run/cursor and stale tracking including insert/backdate/reversal/recost/status/role changes.
- Reconstruct AS_KNOWN only where source history proves it, otherwise AS_KNOWN_UNAVAILABLE; implement RESTATED labeling separately.
- Follow source lineage across stages and count physical WIP only once (P03/P04). Prove concurrent updates, partial pages, revocation, controls with Auth/HTTP, independent source-oracle cases E09/E14/E15/E20/E22/X09.
- R10 remains OPEN_CP7 in P11. No operator-facing CP7 data should be displayed from this probe.

Do not confuse a single-statement diagnostic or TypeScript type guard with a production-safe analysis run.
