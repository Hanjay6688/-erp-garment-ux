# P09 material physical counts — candidate for qualification

29 September 2026. F03/P09 remains open. This increment is a writer candidate; native and connected-browser results are pending. It does not close P09, F03, independent acceptance, R10, or production (`production_go=false`). The prior procurement and all-material transfer source `b81a5f607404075929fe74e0dac5608f5fbfe9e4` passed93 cases plus three smokes; its receipt is `UNROLLED_VERIFICATION.json`. This physical-count candidate is source `4003d16f6375bcaaff70d7c403578b00ef83ecd3` and remains outside that qualification.

## Existing rule and authority

The inventory-control shell requires **physical quantity input, locked system quantity, and a computed difference**. The connected material screen follows that rule. It calls a PostgreSQL preview for the posted quantity at the actual count time, then sends the physical count and the returned source token. The client never submits a signed adjustment or an invented system balance.

Accepted `save_material_adjustment_draft_v2`, `post_material_adjustment_v2`, and `reverse_material_adjustment_v2` remain the only business writers. Native material movement, chronological negative-stock, moving-average recost, journal, business-date, closed-period, and inverse guards remain intact. No second JS/Python stock or accounting engine is added. Only the already-declared CP7 `require_internal` delta gains private count actions; its accepted original hash and restoration proof remain mandatory.

## Transaction and access contract

- `warehouse.material.view` authorizes reads; `warehouse.stock.adjust` authorizes SAVE, POST and draft DELETE. REVERSE retains OWNER/ADMIN. Explicit positive-count cost input additionally requires current `finance.hpp.view`; negative counts obtain cost from the accepted engine. Operational DTOs contain no valuation.
- The count uses exact decimal strings and a dated ledger prefix; null roll is valid only for non-fabric. Fabric needs a real matching roll. Active ordinary raw-material locations are required. Service zones retain their native service workflow.
- A private actor/request cache binds action, payload and exact version. Current permission is checked before cached outcomes and after waits. A committed old outcome is metadata, followed by a fresh document/stock read. If the draft was subsequently deleted, the client refreshes the current list instead of treating the old outcome as a live draft.
- The server derives each delta, saves the accepted adjustment, and privately records the physical input and native document signature. SAVE of an existing count and POST/DELETE/REVERSE use the same private-document/header lock order.
- POST checks the prefix token and actual native document signature before invoking the accepted writer, then checks them again in a fresh statement after the native material-row locks. Its own newly posted movements are excluded from the comparison. A concurrently committed movement or external draft edit therefore requires another review; all tentative effects roll back together. Recost alone does not fabricate a physical change.
- Private read-owned validators and source-signature helpers have no public EXECUTE. The write principal receives no ERP business-table SELECT or DML. Its private count records and request records use RLS. All function owners, definitions, ACLs and predecessor deltas are pinned during proof.
- Browser recovery uses its own `MATERIAL_COUNT` domain within the shared actor/tab fence, persistent UUID and read-generation protocol. Exact bigint versions remain strings inside the recovery document. Confirmations reset on refresh; committed actions retire before reload.

## Declared proof and remaining limits

Local **45/45 targeted DOM/recovery cases**, TypeScript, source/access/CSS gates and script syntax pass. These do not prove PostgreSQL transactions.

The candidate adds **11 native, two concurrent, one real Auth/HTTP, and two desktop/mobile browser cases**. Combined with the previous93 planned procurement/material cases, the target is109 plus three separate smokes. Required examples include count10→8, late invoice at12.5 yielding inventory100 and adjustment expense25, invoice inverse, then count inverse restoring all account balances; positive10→12 at10; dated count before a later transfer; changed stock/native draft rejection; forged client delta rejection; duplicate/zero/cost/zone/lineage refusal; exact replay/draft delete; two competing counts; revocation at a real material-row wait; money redaction; and lost committed response recovery on mobile.

Current UI creates one counted existing material/roll/location per document and shows complete bounded native document detail. The server supports up to100 unique count positions and omits zero-difference lines from the native adjustment. Draft editing UI and selecting a material with no prior movement at a location remain follow-up. Legacy/service adjustments can be read but are corrected through their source workflow. FG adjustments remain P10. Mixed-receipt invoice/return writes and other P09/F03 obligations remain open. No completion claim is based on the target case count.

## First native result and corrections

Run36537511255 on4003d16 produced **97 PASS /12 INCOMPLETE plus three smokes**, including all93 previously qualified cases. Both app workflows, CP6 restoration, advisor gate and exact Auth cleanup passed. `COUNT_RUN_1` retains the complete report and hashes. The new count read had a PL/pgSQL alias collision; its signature used a timezone-dependent timestamp string; and positive-count fixture/UI used FOUND, which is not a native material-adjustment enum.

Corrections rename the SQL alias, compare an absolute epoch in the private document signature, and post the human “Barang ditemukan” choice as accepted COUNT_CORRECTION with that reason preserved in notes. Native reason constraints and writers are unchanged. The lifecycle probe now deliberately switches to America/Los_Angeles between SAVE and POST. Local45 targeted cases still pass; native/browser retest is pending. These corrections do not close the count increment yet.
