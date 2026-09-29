# P09 — procurement/materials connected (in progress)

Family F03 is active. The receipt increment is **writer-verified in a disposable database and real connected browser**, not full P09 or family acceptance. No hosted writes; `production_go=false`.

## Contract and authorization

Explicit modules in `scripts/cp7-src/procurement`, bundled after the qualified P02–P04 modules. Separate NOLOGIN read and command principals; analysis compute never receives business writers. Public RPCs expose live receipt list/detail, paged active master options, and SAVE_DRAFT/POST through accepted CP6 writers. Commands preserve request identity, exact bigint version strings, existing locking/idempotency and current authorization after writer waits/replay. PostgreSQL remains authoritative for stock, cost and journals.

Existing permission mapping: `warehouse.procurement.view/create/post` for receipt actions and `finance.ap.view` for purchase valuation/manual price and invoice metadata. This is a conservative mapping to the existing financial scope, not a new commercial rule. Operations-only reads omit money fields at the server. Operations can create/post fabric benchmark receipts without receiving the benchmark amount; editing an existing priced draft currently requires valuation access so hidden prices cannot be overwritten blindly. These mapping/boundary choices need independent review alongside the owner/frontend contract.

Numbers cross the boundary as exact decimal strings; no JS arithmetic or silent zero. A draft's registered rolls are **receipt quantities, not stock**. List search/status/pagination runs on the server. Detail is an explicitly bounded complete document (100 lines/2,000 rolls); overflow refuses rather than returns a partial document. Current receipt value is labeled receipt basis, never current payable/HPP. Warehouse on-hand uses its own ledger integration in the next increment.

Material receipts retain accepted CP6 behavior: absent fabric price uses its effective benchmark as ESTIMATED, then invoice finalizes it. This is not the laundry UNKNOWN-price contract. FINAL requires supplier invoice; migration belongs to the import workflow. Existing roll sum, active raw-material warehouse, period and stock prefix guards remain in the accepted writer.

## Declared writer proof

`cp7_procurement_cases.py`: public draft has zero stock; post 10 × 10 produces stock10, GRNI100/AP0; exact 1.123456 × 3.000001 preserves stock and receipt3.370369/AP3.37; request replay versus changed payload, stale revision, redaction/current grants/revocations, operations benchmark, paged 105 rows, inactive options, invalid roll/transport and atomic rejection. Three committed races: same request, competing posts, and permission revocation during a real row lock wait. Real Auth/PostgREST draft/post/replay/ops-redaction/revocation. Fixture smoke is counted separately.

Workflow `cp7-p09-procurement.yml` rebuilds the accepted 30-file CP6 package in disposable clones, installs the explicit development bundle, verifies principal ownership/ACLs, runs cases and restores CP6. The source-bound receipt result is PASS, recorded below; this does not close full P09.

## Remaining P09/F03 work

- Receipt connected browser is qualified below; material/transfer/issue/invoice journeys remain open.
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

The first follow-up stopped in the installation verifier, which combined function definitions and ACLs: four explicitly authored execution grants were incorrectly treated as undeclared body replacements. The corrected verifier requires exactly two body deltas, unchanged predecessor owners, and exactly the old ACL union the six declared function grant sets (including `auth.uid/jwt`). It does not allow arbitrary ACL drift. Receipt: `VERIFIER_FAILURE_2.json`.

Source `922c2226ff7c014c45a26fa17e4145904d7d9922`, run `36518111631`: eight native + three races + one HTTP PASS, plus smoke; one new zone regression fixture INCOMPLETE. Custom role admission and real-wait revocation now pass. The failing fixture tried fabric in an accessory-only zone; the existing guard correctly refused. Keep that refusal, then use ordinary accessory fill to test the nonempty-zone guard. Receipt: `ZONE_FIXTURE_FAILURE_3.json`. CP6 restored; advisor gate passed.

## Connected receipt UI increment (verification in progress)

The connected runtime routes to `ConnectedProcurementPage`; demo retains its original fixture. Server list/detail/options, explicit draft review/post, exact decimals and versions, shared cross-tab recovery and current-identity remount are implemented. No optimistic stock or locally invented posting result. DOM tests exercise exact revision above JavaScript safe integer, post/reload, lost response and remount, committed-but-refetch-failed, invalid success body, financial redaction, partial-page refusal and edit metadata preservation. Full unit/build gates ran before the last small metadata increment; source-bound CI will qualify the final candidate.

The next native workflow adds two real Auth/browser → RPC → database cases: desktop receipt, and mobile lost committed response followed by reload/reconcile with the identical UUID/payload. Native read-back asserts stock10 in one movement, GRNI100/AP0 and exact WIB physical time even when the mobile browser uses America/Los_Angeles. No connected browser result is claimed until it passes.

This receipt increment accepts quantities in the material's base UOM; it does not convert Yard/Metre. Existing alternative purchase-UOM snapshots can be read, but their drafts are not offered for editing in this bounded form. Full UOM selection and accessory conversions remain required before P09 acceptance. Invoice/due/line/roll metadata and original physical timestamp are preserved when editing supported drafts. P09 still includes the warehouse/transfer/issue/reversal/late-invoice/source-return work listed above.

## Receipt qualification — 29 September 2026

Source `6b7148c6510c3321a65300984d8bdcdfd09e28fe`, [run 36518831592](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36518831592): **9 native + 3 committed races + 1 real HTTP + 2 real browser = 15 PASS**, plus one repeated smoke. CP6 restore and advisor gate PASS. Full report/hash receipt: `evidence/p09-procurement/CP7_P09_RECEIPT.json.gz` and `RECEIPT_VERIFICATION.json`. Earlier pending statements above describe run history and are superseded for this receipt scope only.

Both desktop and mobile prove real UI/Auth/RPC/database posting. Mobile deliberately loses a committed response, reloads and reconciles the same UUID/payload; stock remains 10 in exactly one movement, GRNI100/AP0. Physical WIB time is preserved even in a Los Angeles browser timezone. The final application gate passed 645 tests in 61 files, build/security ownership, CodeQL and 6 shell browser cases. Screenshots are preserved; visual inspection found dark-theme contrast issues for controls, selected cards and totals, which are being fixed in the next increment.

This is writer evidence, not independent acceptance, and not a family checkpoint. **F03 and P09 remain open**, `production_go=false`.

## Material/roll continuation — native qualification started

New `scripts/cp7-src/materials` reads posted physical movements, never `material_rolls.cached_qty` (drafts already have that cache). Fabric roll/location pages are complete server pages, quantities and versions stay exact strings, units have separate totals, and ledger running balances include the entire chronological prefix before pagination. Value requires `finance.hpp.view`; current material moving average and restated movement snapshots are labeled separately. It is not AS_KNOWN history.

Transfer SAVE/POST/REVERSE call accepted writers. Admission uses a separate private transaction/actor context and `warehouse.material.view` + existing sensitive `warehouse.stock.adjust`; the original OWNER/ADMIN restriction for transfer reversal remains. This conservative existing permission mapping must be independently reviewed. The write principal has no business DML, only the three accepted writers and a private read-owned material/roll identity validator. Current access is checked again after waits/replay.

Declared next proof: draft-roll cache is not stock; 10 at source becomes 6+4 with total value100 and transfer value net0; paged running prefix; inverse pairs; invalid backdate, inactive locations/materials, wrong roll, consumed destination reversal, exact payload, complete 105 roll pages, separate unit totals, money redaction, custom-role/current permission checks; concurrent 7+7 claims against10; revoke during actual row wait; real Auth HTTP. These material results are **pending**. The receipt browser suite is rerun because the shared guard now recognizes the additional private transfer context. Material connected browser/UI is the following increment.

### Material first run and connected follow-up

Source `d11713592fc73e616aa1247a00e00718625b2530`, run36520512754: the 13 receipt native/race/HTTP cases and smoke remain PASS; first material smoke INCOMPLETE because its invoker validator reached predecessor table RLS without `current_app_role` privilege. Receipt browser was not reached. No material qualification was claimed. CP6 restored and advisor gate passed; diagnostic receipt `MATERIAL_BEFORE_VALIDATOR.json`. The fix makes only the private identity validator a read-owned definer, checks current view access inside it, and removes all material/roll SELECT grants from the command principal. The verifier admits exactly this single private definer and keeps every other private material helper invoker.

`ConnectedMaterialsPage` now replaces the demo material page only in connected runtime. Reads, server search/pagination, per-unit totals, complete roll ledger and transfer documents are strict validated DTOs with current money projection. New transfer drafts originate from a selected roll; post/reverse use exact string revisions and the shared MATERIALS recovery domain. Lost/malformed outcomes retain the persisted request; forms retire before read-back; stale reads and other tabs share the existing fence. Browser fixtures post receipt stock through the accepted public receipt boundary, then test the actual material UI. Planned two additional real desktop/mobile cases prove draft0, posted6+4/value100/net0, then reversal10+0; mobile loses a committed transfer reply and replays exactly the same request after reload. These new results are pending.

### Material second run and financial continuation

Source `a4707a4e19549ac29cde2576489266f6605c0071`, run36521391129: **28 cases PASS**, two repeated smoke PASS, one historical-prefix case INCOMPLETE due solely to a case-sensitive expected error substring (`negative` versus the actual `AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY`). Backend correctly refused the invalid backdate. The corrected case now requires the exact error identifier and still checks zero partial movement/document effects after refusal. No SQL guard is loosened. Material custom-role admission/current-revoke race, 105 complete rows with separate unit totals, HTTP money projection, both real transfer browsers and lost-response recovery passed. Both desktop/mobile went draft0 → 6+4/value100 → inverse10+0/value100 with four transfer/inverse movements. Receipt browser regression passed; CP6 restoration/advisors passed. Full run remains INCOMPLETE until the corrected case executes.

The next run also covers two required E24/P13 native integrations: CP7 receipt → CP7 full-roll transfer → ordinary cutting/sewing/laundry/partial FG/sale → staged late supplier invoices. The existing independent arithmetic oracle in `cp6_final_crossflow_review.py` remains unchanged; only its receipt fixture is replaced by public CP7 receipt/transfer calls. Open-period invoices 4×12.50 +6×7.50 result in material value95; closed-receipt-day invoices 7×12.50 +3×7.50 result in value110, while the closed historical report stays unchanged. Actual wages12.70 and laundry70, WIP/FG/COGS/AP/GRNI and idempotent invoice replay remain the established oracle. These new cases are pending and do not claim a connected invoice/sale UI.
