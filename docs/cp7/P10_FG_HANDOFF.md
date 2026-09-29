# P10 FG summary and stock card — candidate

29 September 2026. Native/connected-browser qualification pending. This is an increment within F03, not full P10 or family acceptance. `production_go=false`. The qualified F02 repair checkpoint remains `e3ddcec`; its tested product is `ee86998`.

## Read contract and source authority

The connected FG summary and stock-card routes read actual posted `fg_stock_movements`, grouped by exact physical product/size, lot, location and grade. They do not use mutable cached stock as authority or combine different sizes into one availability figure. Current commercial labels follow the accepted BF identity reader; ledger labels use each transaction's physical date. Current knowledge is explicit; no historical AS_KNOWN claim is made.

Physical stock, active sale reservation and available stock are separate values. Accepted sale drafts create SALE_RESERVE; accepted posting changes that movement to SALE and must not deduct again. Cancellation releases the reservation without physical outflow. The ledger computes the complete chronological prefix before search/date/paging; presentation `book_order` cannot change it. The ordinary native stock/sale functions remain the only writers.

`cp7_fg_read` is NOLOGIN/NOINHERIT with narrowly enumerated SELECT and read-only EXECUTE grants. Public read facades enforce the existing `warehouse.fg.view`, `warehouse.stock.view` or `warehouse.movement.view` permission appropriate to purpose and current active identity. `finance.hpp.view` is separately required for any HPP/valuation fields. Pending laundry/HPP stays UNKNOWN with null amount, including the ledger; an internal zero is not presented as a known cost. The role has no ERP business DML or operational-writer grants.

The current list is paged server-side (maximum100 rows). Totals cover all matching stock positions, not just the visible page. Each card binds product/lot/location/grade; mismatched or partial DTOs fail closed. Exact quantities and versions use strings. The browser clears obsolete results on failed/revoked reads, respects the existing global read fence, and remounts on identity/permission changes. No posting controls or new client stock engine are added.

## Predeclared proof

Seven native cases: actual10 PCS at unit10/value100; draft4 gives physical10/reserved4/available6, cancellation restores10/0/10 and post gives6/0/6 once; ordinary reversal/zero positions; deferred laundry15 PCS with UNKNOWN valuation; separate purpose permissions/redaction/revocation/private grants;26 real lots spanning a25-row page with full26 totals; complete ledger prefix before date/search/page and independent display order.

One real Auth/HTTP case and two connected desktop/mobile browser cases are planned (10 total). Browsers display native reserve/cancel/post fixtures, bind the selected position and render the authoritative ledger; mobile operations has no money fields and clears stale stock after a failed read. **The source sale commands in these tests are fixture operations, not the P11 connected sale UI or R10.** Any fixture-only ERP schema usage grant is revoked before commit; the browser never receives it. Five local DOM/contract cases currently pass; they are not native proof.

The P10 runner installs the current CP7 stack using the same P09 install verifier (factored without changing its checks), then requires no predecessor definition/owner changes and only the seven declared FG read-function grants. It checks exact installed functions/ACLs throughout and restores CP6 afterward. The shared installer refactor also triggers the existing P09 qualification. No hosted database is involved.

## Remaining scope

Full P10 still needs its Nota handoff, FG adjustments, movement-book interactions and wider family acceptance oracles. P11 owns connected sale/return/payment and R10. P12 owns mandor payroll and draggable Nota cards; P13 owns full financial/HPP/close integration. Remaining P09 multi-receipt returns, multi-input/zero-history counts and issue workflows remain in the family ledger. F02 independent acceptance remains HOLD pending auditor retest and its public planner composition obligation.
