# P09 complete supplier invoice documents — candidate

29 September 2026. Qualified P09 source remains `4fae1a0067f7058fb7eaf2b4eaf527028716e8d9` (109 cases plus three smokes), with proof checkpoint `32a21db5dc47356c2e73f2966a17d5c49f3f188f`. This continuation is a candidate, not a passed native qualification. P09/F03 and independent acceptance remain open; `production_go=false`.

## Behavior and native authority

One supplier invoice can contain lines from several posted receipts of the same supplier. The browser selects complete paged receipt sources, enters explicit quantities/prices/discounts, saves or edits a draft, reviews every included receipt, posts the complete invoice, and can reverse that complete invoice. A draft does not change stock, AP, GRNI, or HPP. The prior single-receipt FINALIZE/REVERSE request protocol remains compatible.

Accepted `save_material_supplier_invoice_draft_v2`, `post_material_supplier_invoice_v2` and `reverse_material_supplier_invoice_v2` remain the business writers. Their exact invoice version, deterministic receipt/item locks, current remaining capacity, direct-final exclusion, invoice cents, recost, historical/closed-period guards and inverse rules remain authoritative. No new invoice, stock or money calculation engine is introduced.

New SAVE_DOCUMENT / POST_DOCUMENT / DELETE_DOCUMENT / REVERSE_DOCUMENT actions use a private actor/request cache before mutable document checks. Current access is checked before cached responses and after waits. Invoice versions and decimals travel as exact strings; CREATE expects a null version and DELETE returns null. A cached deleted draft is an outcome, followed by a current list read.

A read-owned validator requires complete source IDs, the anchor receipt, and one supplier. POST/DELETE/REVERSE bind the complete reviewed receipt set and exact invoice version; partial or duplicate review is refused. The accepted native POST rechecks source capacity under its locks. All source validation, native effects and final authorization checks share one transaction. The write role receives EXECUTE only on the accepted writers, with no ERP table SELECT/DML. Its private requests table has RLS; private validators have no public EXECUTE. Reads require procurement.view and finance.ap.view; writes also retain OWNER/ADMIN plus procurement.post or procurement.reverse. No new predecessor function body is replaced.

The connected editor preserves every original line and line note, invoice identity, exact version and full received timestamp when its displayed minute is unchanged. Confirmation resets after edits and refreshes. Each complete document is bounded to100 lines; receipt choices are paged by supplier. The shared PURCHASE_INVOICE recovery fence binds actor, tab, original UUID, exact payload and version. Committed controls retire before current receipt/invoice reload.

## Qualification to run

Six native cases cover the two-receipt lifecycle and inverse, draft edit/replay/delete, wrong supplier/numeric/duplicate/partial review refusal, complete paged sources, access before cached outcomes and private-principal isolation, and direct-final/overcapacity atomicity. Three races cover same UUID, competing capacity, and revocation while blocked on a real receipt row. One real Auth/HTTP case and desktop/mobile connected browsers complete the12 additional cases. The combined target is121 plus three separate smokes; a target is not a pass claim.

The fixed money oracle is4 units at12.5 on receipt A and6 at7.5 on receipt B: AP50/45, GRNI60/40, stock value110/85, quantity10 each. A second invoice closes the remaining6/4 units at10. Reversing both must restore every account and both receipts. Browsers edit the draft first; mobile deliberately loses a committed POST response and must recover the identical UUID/payload without duplication.

Remaining scope: mixed-receipt supplier returns, physical-count multi-input/zero-history selection, the other P09 issue workflows and F03 P10–P13. Supplier payments and portable credits keep their accepted boundary. Paid-source return rules and R10 are not changed by this increment.
