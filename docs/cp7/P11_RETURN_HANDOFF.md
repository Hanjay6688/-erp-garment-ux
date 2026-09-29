# P11 physical return and full invoice inverse — writer candidate

## Qualified64 on final declared source

Source `e808453079f44876d576cecbc5fce9a7aba389ee`, tree `83d276edcd21ffd2c9ea81ca0d023eb8d7d0b9a0`; [run36632964965](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36632964965): **64 PASS /0 FAIL /0 INCOMPLETE /0 NOT_RUN**. All10 browser cases include real desktop Grade A and mobile Grade B sale→return→cash→full inverse, with identical lost-response replay. Exact source bundle hash recomputed; CP6 restoration, advisor, Auth/database cleanup, primary unchanged and backup/restore pass. The corrected first native over-allocation refusal now passes without changing the business oracle or product. Earlier failed runs remain retained.

[Receipt and original report](evidence/p11-sales/RETURN_VERIFICATION.json). Both R10 screenshots from this exact source were inspected and retained: horizontal fit is intact, but mobile return/recovery screens remain vertically long. This closes the declared writer64 checkpoint, not independent R10 acceptance or all ERP release gates. The old47 cash/source cases are contained in64, not added to it.

## Run3:63 PASS, single native refusal-message mismatch

Source `f8bc18ae2bacd00c2a6dd12f487bb4790f19ba57`, tree `57507be0e9b041e256efd58bf040f291a491c57d`; [run36631707785](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36631707785): **63 PASS /0 FAIL /1 INCOMPLETE /0 NOT_RUN**. All10 browser cases, all races, HTTP, cash and other return cases pass. CP6 restoration, advisor, Auth/database cleanup, primary-unchanged and backup/restore pass. [Retained original result](evidence/p11-sales/RETURN_RUN3_RECEIPT.json).

One direct over-allocation test expected the later posting guard but the accepted item normalizer already refused qty3 against allocation2 (`Return qty 3 exceeds qty 2 sold from this lot allocation`). The test is corrected to that exact first guard; the atomic-boundary assertion, separate prior-document aggregate cap and remaining independent allocation checks stay unchanged. No product change or new visual-review claim. Final64 rerun still required; writer acceptance remains pending.

## Run2: validator alias and failed-browser cleanup repair

Source `4dc25d5701ea2c24e50b332fc0f10c4fea8efe06`, tree `10b213074ca7e13ae89da4fc593f8d0a19f346c6`; [run36630711725](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36630711725): **47 PASS /0 FAIL /16 INCOMPLETE /1 NOT_RUN** of64, reconstructed from recorded outcomes and the predeclared browser list. The raw report's54 count omits browser outcomes because its host exited before finalization. [Original report and receipt](evidence/p11-sales/RETURN_RUN2_RECEIPT.json) preserve this discrepancy.

The new duplicate-line guard used SQL alias `x`, which conflicts with the function's existing PL/pgSQL variable. Candidate repair explicitly qualifies `return_line.value`. The failed return also exposed a browser harness problem: asserting inside an asynchronous route callback terminated the host before cleanup. The callback now forwards a refused RPC normally; lost-response simulation happens only after HTTP200. Product success assertions remain unchanged. The run's Auth cleanup and primary-unchanged gates failed; CP6 schema restoration, disposable test database removal, advisor and backup/restore passed. No new visual review or acceptance is claimed. Full64 native/Auth/browser rerun, including cleanup, remains required.

## Run1 result and source-contract correction

Source `8bbd467cee5207b8bd2e741a28539782dd266754`, tree `e68259227a8be616ea967e3f7d37408dcf42acac`; [run36629457186](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36629457186): **61 PASS /0 FAIL /3 INCOMPLETE /0 NOT_RUN** of64. All10 browser cases passed, including both complete real source CREATE → POST → Grade A/B RETURN to another warehouse → cash60 → full inverse journeys and mobile lost-RETURN recovery. All47 prior cash/source cases now pass on this exact source (included in64, not additional). CP6 restoration, advisor, Auth/database cleanup and backup/restore pass; the overall writer gate correctly stays false. Four current cash/return screenshots were inspected and retained; long mobile invoice lists after recovery remain a layout limitation. [Receipt and original diagnostics](evidence/p11-sales/RETURN_RUN1_RECEIPT.json).

The adapter/UI incorrectly allowed repeated allocation lines within one return, despite the existing native `uq_sales_return_item_allocation` constraint. The earlier reading of AH split_destination was wrong: it creates separate return documents. No accepted schema constraint is removed. Candidate repair adds early duplicate refusal and disables repeat selection; multiple different allocations may still carry different grades/destinations. The revised split fixture proves A/B on two allocations in one document, then HOLD from the first allocation in another document. Quantity cap has its own direct single-line counterexample and prior-return check. The consumed-stock inverse correctly refused; only its expected error text needed the native first guard. **Same64-case rerun required; product repair not yet qualified.**

CP6 remains CLOSED_CONTRACT_SCOPE. P11/F03 remain OPEN; independent_acceptance=false and production_go=false. This source extends the separately qualified33-case draft flow and the cash run2 diagnostic (44 PASS /3 INCOMPLETE out of47). **Native and connected browser qualification of this new candidate is pending.**

## Accepted rules and implementation

Return lines select an original sale allocation. The accepted normalizer derives product, lot and HPP; the browser cannot submit cost or replace those identities. Real paged selectors expose remaining quantity per allocation, the original invoice line value, and active FG warehouses. Different allocations can use different warehouses and Grade A/B/HOLD within one return. One allocation appears at most once per document (accepted unique constraint); split its grades/destinations across explicit return documents, all sharing the same original capacity. These are existing accepted paths (`cp6_ah_independent_review.py`, `cp6_v2620ah_family.py`), not new grade policy.

Each line requires explicit PCS and refund value. Blank is unknown, never zero. Explicit zero is allowed by the existing native return writer. Manual values are retained and exact cents use integer arithmetic. Native quantity/refund limits, active destinations, chronological stock/HPP/journals, original invoice/customer binding and date restrictions remain authoritative. A return that would put paid cash above the remaining invoice is refused by the existing native rule. The UI explains correcting payment separately; this does not invent cash refunds or customer-credit carryover.

The same reviewed command boundary adds RETURN, RETURN_REVERSE and SALE_REVERSE. Current invoice/AR/action permissions are checked before cached outcomes, after real lock waits and before effects. Native inverse OWNER/ADMIN restrictions are also checked before returning cached inverse results. Requests retain exact actor/UUID/payload/version semantics and a review token covering header, items, allocations, payments and returns. The FG lock and native child-before-header lock order are preserved. Private request/context tables remain inaccessible to browser roles; no public business DML or direct native execute is granted. Only the exact preceding private require_internal admission body receives a hash-guarded transaction/actor/action-bound extension; native business functions remain unchanged.

Actual invoice, allocation, payment and return navigation entries now use the connected sales workspace. The return panel retains edited lines on source failure while preventing writes, shows complete paged return history including reversals, and handles different allocation destinations/grades and separate returns for the same allocation. Payment, return and invoice reversal use explicit review/reason and native conservation, with shared persistent recovery after a committed response is lost.

## Predeclared64-case qualification

Existing47 cases are rerun unchanged in intent, with two cash harness corrections: a second owner identity fixture preserves LAST_ACTIVE_OWNER_PROTECTED during actor-demotion setup; exact accessible-name locators distinguish the parent payment region from its history. Cash run2 remains retained in `evidence/p11-sales/CASH_RUN2.json.gz` and `CASH_RUN2_RECEIPT.json`; it is not relabeled as green.

Additional17 cases:

| Group | Cases | Required outcome |
|---|---:|---|
| Native returns | 11 | Lifecycle, split A/B/HOLD, selected allocation cap, closed exact fields/refund cap, paid-return refusal, dates/inactive destination, exact replay, stale/reversed source, permissions/private boundary, complete pages, consumed-return inverse refusal |
| Real concurrent transactions | 3 | Competing returns, cash vs return, permission revocation during observed FG wait; one valid winner/no overpayment or stock excess |
| Auth/PostgREST | 1 | Real authorized Grade B return to other warehouse, exact replay/inverse, anonymous refusal |
| Connected browser | 2 | Desktop Grade A and mobile Grade B: source CREATE → POST → RETURN → CASH → payment inverse → return inverse → sale inverse; mobile committed RETURN reply lost and recovered with identical envelope |

Exact browser oracle: original10 PCS at HPP10; invoice4×20=80 reserves6 available without GL, POST retains6 and AR80/revenue−80/FG−40/COGS40; return1 for20 to another warehouse leaves source6 plus returned1 and AR−20/revenue+20/FG+10/COGS−10; cash60 changes cash+60/AR−60 only. Full inverse restores original10 Grade A in the source warehouse and **every** GL account to its baseline, preserving reversed cash/return history. Fixtures create masters/FG stock only; the invoice and all lifecycle commands run through the real browser UI. Separate native split-grade case covers two allocations with A/B destinations in one document and HOLD from the first allocation in a subsequent document.

Local verification: 7 return DOM/contract tests plus21 existing sales DOM/contract and30 shared recovery tests. Type/build/source/access checks are required before the candidate push. These checks are not PostgreSQL or visual proof.

## Boundaries and next handoff

This bundle installs after the explicit P09/F02 development stack, not yet the complete P10/P12/P13 family combination. Qualification must bind actual source SHA/tree and bundle hash, count all64 outcomes, retain failures, verify CP6 restoration, advisor, Auth/database cleanup and accepted-package backup/restore. Inspect actual current desktop/mobile screenshots before a visual claim. R10 closure remains subject to the observed outcomes and independent auditor acceptance; no full-ERP production certification. P13, E05 settlement contract/proof and combined F03 install/restore remain separate open obligations.
