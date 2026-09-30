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
