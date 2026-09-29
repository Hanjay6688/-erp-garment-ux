# P10 FG source, stock card and corrections — qualified increment

**Current writer checkpoint: 23/23 PASS**, source `fa75d47de5b8fa010071b35d551018b064d64d60`, [run36564816759](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36564816759). This supersedes the two incomplete correction runs retained below. Full P10, F03, independent acceptance and production GO remain open. Receipt: `evidence/p10-fg/ADJUSTMENT_VERIFICATION.json`.

15 native + 2 native races + 2 real Auth/HTTP + 4 connected browser cases. Nine DOM cases and both app gates pass. Stock/value/account reversal, current-access refusal after native lock, same-request replay, complete two-lot browser edit, operational money redaction and mobile committed-response recovery are all executed. CP6 restore, advisors and Auth/database cleanup pass. P09 dependent regression remains121 PASS +3 separate smokes on `7e2aedd` (run36563203850); its backend and materials/invoice/return consumers are unchanged by the later FG-only fixture/parser delta.

Images were visually checked. A presentation follow-up remains: inventory-type switcher needs the existing cproc style namespace for readable buttons; the fix is prepared with the next UI increment. No stock/money behavior depends on that styling.

## Earlier read-only qualification (retained)


29 September 2026. Writer qualification: **10/10 PASS** (7 native, 1 real Auth/HTTP, 2 connected desktop/mobile browser), plus 5 local DOM cases. Source `f41e6eb1dd7fc44d8cd60a1b02ff3998e14f499a`, [run 36560773493](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36560773493). Both screenshots visually reviewed; CP6 restoration and advisor gate pass. Shared-installer P09 regression **121/121 PASS + 3 separate smoke checks**, [run36560773198](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36560773198); CP6 restore and advisor gate pass. This is an increment within F03, not full P10 or family acceptance. `production_go=false`. The qualified F02 repair checkpoint remains `e3ddcec`; its tested product is `ee86998`.

## Read contract and source authority

The connected FG summary and stock-card routes read actual posted `fg_stock_movements`, grouped by exact physical product/size, lot, location and grade. They do not use mutable cached stock as authority or combine different sizes into one availability figure. Current commercial labels follow the accepted BF identity reader; ledger labels use each transaction's physical date. Current knowledge is explicit; no historical AS_KNOWN claim is made.

Physical stock, active sale reservation and available stock are separate values. Accepted sale drafts create SALE_RESERVE; accepted posting changes that movement to SALE and must not deduct again. Cancellation releases the reservation without physical outflow. The ledger computes the complete chronological prefix before search/date/paging; presentation `book_order` cannot change it. The ordinary native stock/sale functions remain the only writers.

`cp7_fg_read` is NOLOGIN/NOINHERIT with narrowly enumerated SELECT and read-only EXECUTE grants. Public read facades enforce the existing `warehouse.fg.view`, `warehouse.stock.view` or `warehouse.movement.view` permission appropriate to purpose and current active identity. `finance.hpp.view` is separately required for any HPP/valuation fields. Pending laundry/HPP stays UNKNOWN with null amount, including the ledger; an internal zero is not presented as a known cost. The role has no ERP business DML or operational-writer grants.

The current list is paged server-side (maximum100 rows). Totals cover all matching stock positions, not just the visible page. Each card binds product/lot/location/grade; mismatched or partial DTOs fail closed. Exact quantities and versions use strings. The browser clears obsolete results on failed/revoked reads, respects the existing global read fence, and remounts on identity/permission changes. No posting controls or new client stock engine are added.

## Executed predeclared proof

Seven native cases: actual10 PCS at unit10/value100; draft4 gives physical10/reserved4/available6, cancellation restores10/0/10 and post gives6/0/6 once; ordinary reversal/zero positions; deferred laundry15 PCS with UNKNOWN valuation; separate purpose permissions/redaction/revocation/private grants;26 real lots spanning a25-row page with full26 totals; complete ledger prefix before date/search/page and independent display order.

One real Auth/HTTP case and two connected desktop/mobile browser cases passed (10 total). Browsers display native reserve/cancel/post fixtures, bind the selected position and render the authoritative ledger; mobile operations has no money fields and clears stale stock after a failed read. **The source sale commands in these tests are fixture operations, not the P11 connected sale UI or R10.** Any fixture-only ERP schema usage grant is revoked before commit; the browser never receives it. Five local DOM/contract cases pass; they are not native proof.

The P10 runner installs the current CP7 stack using the same P09 install verifier (factored without changing its checks), then requires no predecessor definition/owner changes and only the seven declared FG read-function grants. It checks exact installed functions/ACLs throughout and restores CP6 afterward. The shared installer refactor also triggers the existing P09 qualification. No hosted database is involved.

## Remaining scope

Full P10 still needs its Nota handoff, FG adjustments, movement-book interactions and wider family acceptance oracles. P11 owns connected sale/return/payment and R10. P12 owns mandor payroll and draggable Nota cards; P13 owns full financial/HPP/close integration. Remaining P09 multi-receipt returns, multi-input/zero-history counts and issue workflows remain in the family ledger. F02 independent acceptance remains HOLD pending auditor retest and its public planner composition obligation.


## FG correction scope (now qualified)

The Stock Adjustment route now offers materials and FG. FG corrections retain accepted OWNER/ADMIN plus `warehouse.stock.adjust` and FG-view requirements. The command principal is NOLOGIN without business SELECT/DML; exact reviewed integer corrections use the three accepted native draft/post/inverse writers, without a predecessor definition change or a new HPP engine. It does not adopt AX/other source documents. Private actor/request records fence idempotent retries; current access is checked before cached replay and after native waits. A private complete document signature prevents a different native draft from being posted under the earlier review.

The browser can create and edit all 1–100 selected product/lot/grade lines in one FG warehouse, with exact version strings, WIB physical time, explicit action review and the existing persistent recovery lock. HPP and signed valuation are server-projected only for financial users; UNKNOWN stays null. This increment accepts signed physical corrections on existing lots; unknown-source new lots retain their accepted receipt workflow.

Predeclared qualification adds eight native cases (positive and negative quantity/value/inverse, complete multi-line edit/version, UUID/delete replay, exact-input atomicity, external native edit, deferred laundry UNKNOWN, current authority/private grants), two native races, one real Auth/HTTP lifecycle and two connected browser correction lifecycles. Mobile loses a committed POST response and must reuse the same request after reload; desktop edits a complete two-lot document. Prior ten FG source-read cases remain in the same run. Four new local contract/DOM cases and five prior FG DOM cases pass. All thirteen added correction cases now pass on the current checkpoint; the ten earlier FG source cases also pass.


First correction candidate `7e2aedd`, run36563203792: **17 PASS, 6 INCOMPLETE**. See `evidence/p10-fg/ADJUST_RUN_1.json` for every original failure and unchanged expected oracle. The new mobile connected write/recovery/inverse passed. Six incomplete checks arise from test setup/source identification: two inverse-source queries, the unrelated AA RPC whitelist, last-active-owner protection, missing ADMIN adjust permission, and positional browser line selection after native item order changed. These are corrected for rerun without changing stock/value oracles or native safeguards. Separately, the FG DTO now admits negative exact `book_order`, which the accepted presentation reorder writer can legitimately create; a native source control and DOM case cover it. That incomplete candidate was not promoted; see the current qualified checkpoint above.


Second candidate `bb84dd4`, run36564028231: **18 PASS, 1 INCOMPLETE, 4 browser cases NOT_RUN**. Native quantity/value/multi-line/inverse and real Auth/HTTP now pass. The remaining race correctly refused after revocation (`Internal ERP access required`) but its assertion expected uppercase `ACCESS`; post-refusal stock/draft oracles remain required on rerun. The browser never started because the new signed-rank DOM fixture mutation caused TS2571; the explicit fixture cast is fixed and TypeScript plus all nine DOM tests are rerun before the next push. The SQL product bundle remains `4860f9b97c8bf9a185beaa16dffe423acc56ce6b6124ba0dafecc62d46335a70`; no native guard is relaxed. Both failed reports stay available.
