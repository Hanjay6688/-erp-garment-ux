# P09 — procurement/materials connected (in progress)

Family F03 is active. This first increment is a **receipt bridge under native verification**, not full P09 or family acceptance. No hosted writes; `production_go=false`.

## Contract and authorization

Explicit modules in `scripts/cp7-src/procurement`, bundled after the qualified P02–P04 modules. Separate NOLOGIN read and command principals; analysis compute never receives business writers. Public RPCs expose live receipt list/detail, paged active master options, and SAVE_DRAFT/POST through accepted CP6 writers. Commands preserve request identity, exact bigint version strings, existing locking/idempotency and current authorization after writer waits/replay. PostgreSQL remains authoritative for stock, cost and journals.

Existing permission mapping: `warehouse.procurement.view/create/post` for receipt actions and `finance.ap.view` for purchase valuation/manual price and invoice metadata. This is a conservative mapping to the existing financial scope, not a new commercial rule. Operations-only reads omit money fields at the server. Operations can create/post fabric benchmark receipts without receiving the benchmark amount; editing an existing priced draft currently requires valuation access so hidden prices cannot be overwritten blindly. These mapping/boundary choices need independent review alongside the owner/frontend contract.

Numbers cross the boundary as exact decimal strings; no JS arithmetic or silent zero. A draft's registered rolls are **receipt quantities, not stock**. List search/status/pagination runs on the server. Detail is an explicitly bounded complete document (100 lines/2,000 rolls); overflow refuses rather than returns a partial document. Current receipt value is labeled receipt basis, never current payable/HPP. Warehouse on-hand uses its own ledger integration in the next increment.

Material receipts retain accepted CP6 behavior: absent fabric price uses its effective benchmark as ESTIMATED, then invoice finalizes it. This is not the laundry UNKNOWN-price contract. FINAL requires supplier invoice; migration belongs to the import workflow. Existing roll sum, active raw-material warehouse, period and stock prefix guards remain in the accepted writer.

## Declared writer proof

`cp7_procurement_cases.py`: public draft has zero stock; post 10 × 10 produces stock10, GRNI100/AP0; exact 1.123456 × 3.000001 preserves stock and receipt3.370369/AP3.37; request replay versus changed payload, stale revision, redaction/current grants/revocations, operations benchmark, paged 105 rows, inactive options, invalid roll/transport and atomic rejection. Three committed races: same request, competing posts, and permission revocation during a real row lock wait. Real Auth/PostgREST draft/post/replay/ops-redaction/revocation. Fixture smoke is counted separately.

Workflow `cp7-p09-procurement.yml` rebuilds the accepted 30-file CP6 package in disposable clones, installs the explicit development bundle, verifies principal ownership/ACLs, runs cases and restores CP6. Results are pending, not inferred from local Python syntax checks.

## Remaining P09/F03 work

- Connected receipt browser with authoritative reload and persisted uncertain-request recovery.
- Warehouse/material/roll drilldown, transfer/issue/adjustment, reversals, location and historical-prefix cases; server search must cover complete sources.
- Late invoice, source return, valuation propagation and same-counterparty supplier credit integration with P13.
- P10 FG ledger, P11 sale/return/payment including R10, P12 attendance/payroll/Nota, P13 finance/HPP/close.
- Full E01/E24/E14/E12, family independent audit and P18–P21 remain open.

F02 carry: review failed-wash with unknown vendor pricing separately; ordinary deferred laundry UNKNOWN was qualified. Do not introduce SKU-specific laundry prices.

## First native run: two concrete findings

Source `a10c3154b3d9a454dc5deb852a795b090cddd724`, run `36516767000`: smoke, four native, two race and one real HTTP PASS; four native and one race INCOMPLETE. Full original report and adjudication are in `evidence/p09-procurement/BEFORE_GUARDS*`. Restore/advisors passed.

1. **P09 integration defect:** custom permission roles pass the new facade but fail the accepted internal role-code guard. The revoke race consequently never reached its row lock. The fix adds a private transaction/actor-bound execution context for SAVE_DRAFT/POST; the common guard recognizes only its exact permission/action pair. No caller-controlled setting grants admission. Context disappears before success or rolls back with a failure.
2. **Predecessor product defect exposed by P09:** the existing location trigger refers to `OLD.location_id` on `erp.locations`, where the column is `id`. Ordinary updates fail. An explicit CP7 delta corrects this reference and qualifies zone type/delete/nonempty-stock negative controls. This finding does not revoke the already accepted CP6 contract milestone; its affected continuation must pass before P09 closes.

`accepted-deltas.sql` refuses unless both predecessor definitions match their accepted SHA256. Original CP6 files are unchanged. The runner verifies accepted CP6/F02 before extension, checks that exactly the two declared predecessor functions changed, pins every installed function/ACL for all cases, and restores the two originals before the final CP6 boundary comparison. This is a product extension plus rollback proof, not a patched test oracle. The next native result remains pending.
