# F03 E20/E14 — complete FG pages to invoice capacity

**Five executions declared; runtime qualification pending.** F03 OPEN, CP6 CLOSED_CONTRACT_SCOPE, independent_acceptance=false, production_go=false. This scoped seam joins the existing P10 FG readers and P11 public invoice writer on the installed26-role combined stack. It does not close either full scenario or supply a future planner's size-gap calculation.

## Independent worksheet

Thirty distinct real FOUND_AT_OPNAME receipts each supply one piece at owner value10. Initial physical30, reserved0, available30 and stock value300. FG pages contain25 and5 distinct lots, while both retain complete totals30. P11's stock candidate must expose30 available in one product/location candidate.

Creating an invoice27 at price20 reserves27 across27 original lots: physical30, reserved27, available3; no journal. Posting that reviewed invoice changes the original reservation source into sale, leaving physical3/reserved0/available3, FG value30, COGS270, AR540 and revenue540. Exact POST replay leaves the same allocations and quantities. Public invoice inverse restores physical30/value300 and all original accounts and report amounts. A request31 must refuse atomically.

Operations actors may read both complete stock pages and the last-page lot's actual card. Neither response may contain valuation, unit cost, HPP, unit price or financial objects. Such reading confers no right to create/post an invoice. Current permission revocation must deny both readers and writes before an effect or cached mutation outcome.

## Declared executions and boundaries

| Execution | Scope |
|---|---|
| Native E20 | Complete30-lot pages → stock option30 → refused31 → public draft27 → POST/replay → public inverse; fixed lot/account/report conservation |
| Native E14 | Both pages/card redacted before/after real reservation27; operational POST denied; current stock/card permissions revoked; no stock/GL effect |
| Auth/HTTP | Actual owner/operations sessions, complete pages/card, public CREATE27/exact replay, anonymous/operations write denial; owner deactivation precedes cached outcome, operations revocation denies current reads |
| Desktop owner browser | Actual FG pages25+5 → real P11 form/source option30 → CREATE27 → POST → refreshed physical3/0/3;27 native allocation lots, exact fixed money/report read-back |
| Mobile operations browser | Actual pages25+5 and card without money; real permission revocation and server403 clear previously displayed positions/card while underlying stock/accounts remain |

The browser fixture creates the30 real source receipts through native commands before UI interaction. Desktop invoice creation/posting is in the actual browser through public RPCs. Mobile proves operations reads/revocation, not invoice writing. No cash, refund, installment payroll, SKU tariff or new cost engine is introduced.

The qualification keeps PostgreSQL17, accepted30-file package installation, exact combined predecessor definitions/owners/ACL admission, advisor, CP6 restoration, backup restoration, unchanged primary and Auth/database cleanup. The temporary legacy fixture schema grant is restored before HTTP/browser. Five source/invoice/stock/revocation screenshots are requested; visual review is pending until genuine captures are inspected.

Files: `scripts/cp7_f03_capacity_cases.py`, `scripts/cp7_f03_capacity_probe.py`, `scripts/cp7_f03_capacity_browser_fixture.py`, `scripts/cp7_f03_capacity_browser.mjs`, `.github/workflows/cp7-f03-capacity.yml`. Existing22-case combined regression remains a separate overlapping suite. No result is claimed from syntax checks or a workflow badge.

## First execution —4 PASS and early authorization refusal

Source `c76a7a5279f4f9e3aafcbfa629d8f760acb2f1a2`, tree `cce2893eb2b460f40c646097ee15134b218e5b06`, [run36686209312](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36686209312), job109792557270: **4 PASS /0 FAIL /1 INCOMPLETE /0 NOT_RUN**. [Complete receipt](evidence/f03-capacity/FIRST_RECEIPT.json) retains all original JSON reports and original file hashes; ZIP SHA256 `8387fe525a48d78fc10b13437c6eafa01b160bfb306b6ab47d7eee10bcdb1351`. All restoration/installation/advisor/cleanup gates pass except whole writer-runtime qualification.

Native E20, real Auth/HTTP, desktop actual invoice creation/posting and mobile actual operation pages/card/revocation pass the fixed30/27/3,270/540 worksheet. The remaining native E14 test asks a stock-only actor to POST. Existing `cp7_sales.access_now()` correctly refuses at invoice/finance admission as `CP7_SALES_ACCESS_DENIED` before the test's incorrectly expected later `CP7_SALES_WRITE_DENIED`. The corrected case checks that earlier denial, then temporarily grants only invoice read/AR read and verifies that POST still refuses at its separate write permission; it removes those added read rights before current stock/card revocation. No authorization predicate, money, stock or product source changes. Full five-case qualification and source-bound visual review remain pending.
