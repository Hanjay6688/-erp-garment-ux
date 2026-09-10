# CP6 G — writer remediation contract

Release state: **HOLD / DRAFT / MERGE BLOCKED / `production_go:false`**.
This document describes writer changes, not an independent PASS or a hosted rollout.

> VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
>
> Reliable data adalah DEWA. Keuangan—termasuk laporan—stok, dan HPP adalah RAJA.

## Input and protected boundaries

- Independent audit: `8ebcd943d93e093f3e9fd99c66c8ba84f13215d9`, tree `387e39e16a746f27ecad0276b1863750d1c7c6d6`.
- ZIP: `CP6_INDEPENDENT_ADVERSARIAL_REAUDIT_8ebcd943_2026-09-10_EVIDENCE.zip`.
- ZIP SHA-256: `aa6e22ced23bc4ffcd5625f0d87d5c4d624d4102a7f5110eea15f08591729f41`; all 386 declared payloads verified before writer work.
- Confirmed findings: P2 N01, N02, N03. G01 is a required native rollback coverage extension; N04 is stale PR evidence metadata.
- Main/base remains `6d4cda118f5d28d1f039cc0ecf318d0866f55c2c`. No merge or hosted UAT/legacy mutation is authorized.
- Existing E/F migrations and the audited F rollback remain byte-identical. The new SQL is a forward G migration with its own exact pre-use rollback.

## Owned closures

| Finding | Writer contract |
| --- | --- |
| N01 — split LOSS cents | Serialize adjustment/reversal with sale/return; assert the starting book, preserve original document journals, then append the cumulative F target residual. Opening 10 × 0.011, five valid losses, sale 5 ends FG 0 / COGS 0.06 / net other-out 0.05; source 0.11 conserved. |
| N02 — multi-line opening | Retain independently rounded source-lot values. Equity sums the exact posted debit/credit amounts: 0.06 + 0.06 = 0.12; two SKUs at 0.006 post 0.01 + 0.01 = 0.02. Raw unit costs and HPP lineage are not flattened. |
| N02 — correction/inverse extension | Price corrections use differences between rounded lot bases, not rounded raw price differences. A 5-pc lot changing 0.011 → 0.0129 remains worth 0.06. The two correction entry points take the shared lifecycle lock and pre-assert the book. Source-equity changes cite the current HPP version; redistribution uses the existing append-only F synchronizer. Draft reservation remains owned stock and is not deducted twice at POST. |
| N03 — WIP detector | Independently reconcile authoritative delivery lines against exactly one source event and the required inverse. Check quantity, PO/group/contractor, stage direction, source timestamp, inverse chronology, orphan/missing rows, and net custody. Financial failed-wash reversal does not erase physical custody. A matching corrupted source/inverse pair must still fail against the delivery. |

The old opening revaluation fields remain raw diagnostic projections/trigger activation state. Monetary authority is the posted journal plus the source/target/book reconciliation, not independently rounded projection differences.

## Fixture boundary, explicitly disclosed

The old first-accrual concurrency fixture directly seeded a SENT delivery without its physical WIP source. G correctly detected that missing fact. The fixture now includes the same physical row emitted by `post_laundry_delivery`; it still has **no accrual-state/event row**, preserving the original first-accrual race precondition. It contributes 10 legitimate outstanding pcs globally. N03's own PO returns to 0; corruption of its source adds one and blocks confidence. The independent audit ZIP and original baseline runs were not rewritten.

Rollback-only multi-RPC tests reset request-local `app.physical_at` before the next RPC to model separate HTTP transactions. They do not disable physical guards for the tested business operations.

## Proof gates (must execute, not just exist)

1. Final G must be installed **before** real Auth/HTTP, all 34 native business races, affected regressions, and the old C01–C06/A01–A03 suites.
2. Shared N regression SQL runs on native PostgreSQL: eight case groups, ten minor-unit price boundaries, twelve WIP corruption variations, lawful mixed sale/return/adjustment/inverse/correction flows, and draft repricing.
3. Native rollback qualification separately covers **F and G × sale/return/conversion/report/FK synchronization × writer-first/rollback-first/writer-abort/rollback-lock-timeout = 40 schedules**. Writers invoke actual backend business functions with the configured operator JWT. This is not an HTTP/Auth claim; the dedicated Auth suite is separate.
4. The FK case really posts a new sale and reverses a linked prior sale, causing an F event-table insertion. No fabricated history marker substitutes for business use. Writers acquire no manual business prelock. The rollback-first gate is a third session on the final WIP relation; the measured writer blocker must be the actual rollback PID.
5. Each schedule binds exact function/owner/ACL observations, actual lock PIDs, physical clone boundaries, business postconditions, source/rollback hashes, and zero remaining clone databases.
6. G pre-use rollback restores seven exact F functions and refuses ambiguous ledger bytes, successor, definition/ACL/capsule drift, and changed business content. Content fingerprints avoid treating transaction-start timestamps as proof of no post-install writes. Installation-generated reconciliation also prevents rollback; history is never deleted to manufacture a pre-use state.
7. The G runtime manifest binds the exact Git SHA/tree/run, source files, payload hashes, real evidence counts, and hosted boundary. Old suite names identify their historical cases; the final installed runtime is E+F+G.

Static/source checks and PGlite sequential tests are useful writer evidence but cannot close native concurrency or HTTP/Auth coverage. No candidate is promoted solely on those results.

## Next gate

After exact-SHA CI evidence is complete, update PR24's body from E to the current G candidate and hand off the frozen SHA and evidence to an independent auditor. Keep the PR draft/unmerged and `production_go:false`. CP7 planning—including pre-SKU WIP coverage and production recommendations—remains preserved, but its implementation does not bypass the CP6 gate.
