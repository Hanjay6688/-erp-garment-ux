# P11 physical return and full invoice inverse — writer candidate

CP6 remains CLOSED_CONTRACT_SCOPE. P11/F03 remain OPEN; independent_acceptance=false and production_go=false. This source extends the separately qualified33-case draft flow and the cash run2 diagnostic (44 PASS /3 INCOMPLETE out of47). **Native and connected browser qualification of this new candidate is pending.**

## Accepted rules and implementation

Return lines select an original sale allocation. The accepted normalizer derives product, lot and HPP; the browser cannot submit cost or replace those identities. Real paged selectors expose remaining quantity per allocation, the original invoice line value, and active FG warehouses. One allocation can be split across lines with different warehouses and Grade A/B/HOLD; all lines and prior posted returns share that allocation's capacity. These are existing accepted paths (`cp6_ah_independent_review.py`, `cp6_v2620ah_family.py`), not new grade policy.

Each line requires explicit PCS and refund value. Blank is unknown, never zero. Explicit zero is allowed by the existing native return writer. Manual values are retained and exact cents use integer arithmetic. Native quantity/refund limits, active destinations, chronological stock/HPP/journals, original invoice/customer binding and date restrictions remain authoritative. A return that would put paid cash above the remaining invoice is refused by the existing native rule. The UI explains correcting payment separately; this does not invent cash refunds or customer-credit carryover.

The same reviewed command boundary adds RETURN, RETURN_REVERSE and SALE_REVERSE. Current invoice/AR/action permissions are checked before cached outcomes, after real lock waits and before effects. Native inverse OWNER/ADMIN restrictions are also checked before returning cached inverse results. Requests retain exact actor/UUID/payload/version semantics and a review token covering header, items, allocations, payments and returns. The FG lock and native child-before-header lock order are preserved. Private request/context tables remain inaccessible to browser roles; no public business DML or direct native execute is granted. Only the exact preceding private require_internal admission body receives a hash-guarded transaction/actor/action-bound extension; native business functions remain unchanged.

Actual invoice, allocation, payment and return navigation entries now use the connected sales workspace. The return panel retains edited lines on source failure while preventing writes, shows complete paged return history including reversals, and handles split grades and destinations. Payment, return and invoice reversal use explicit review/reason and native conservation, with shared persistent recovery after a committed response is lost.

## Predeclared64-case qualification

Existing47 cases are rerun unchanged in intent, with two cash harness corrections: a second owner identity fixture preserves LAST_ACTIVE_OWNER_PROTECTED during actor-demotion setup; exact accessible-name locators distinguish the parent payment region from its history. Cash run2 remains retained in `evidence/p11-sales/CASH_RUN2.json.gz` and `CASH_RUN2_RECEIPT.json`; it is not relabeled as green.

Additional17 cases:

| Group | Cases | Required outcome |
|---|---:|---|
| Native returns | 11 | Lifecycle, split A/B/HOLD, selected allocation cap, closed exact fields/refund cap, paid-return refusal, dates/inactive destination, exact replay, stale/reversed source, permissions/private boundary, complete pages, consumed-return inverse refusal |
| Real concurrent transactions | 3 | Competing returns, cash vs return, permission revocation during observed FG wait; one valid winner/no overpayment or stock excess |
| Auth/PostgREST | 1 | Real authorized Grade B return to other warehouse, exact replay/inverse, anonymous refusal |
| Connected browser | 2 | Desktop Grade A and mobile Grade B: source CREATE → POST → RETURN → CASH → payment inverse → return inverse → sale inverse; mobile committed RETURN reply lost and recovered with identical envelope |

Exact browser oracle: original10 PCS at HPP10; invoice4×20=80 reserves6 available without GL, POST retains6 and AR80/revenue−80/FG−40/COGS40; return1 for20 to another warehouse leaves source6 plus returned1 and AR−20/revenue+20/FG+10/COGS−10; cash60 changes cash+60/AR−60 only. Full inverse restores original10 Grade A in the source warehouse and **every** GL account to its baseline, preserving reversed cash/return history. Fixtures create masters/FG stock only; the invoice and all lifecycle commands run through the real browser UI. Separate native split-grade case covers HOLD and multiple destination lines.

Local verification: 7 return DOM/contract tests plus21 existing sales DOM/contract and30 shared recovery tests. Type/build/source/access checks are required before the candidate push. These checks are not PostgreSQL or visual proof.

## Boundaries and next handoff

This bundle installs after the explicit P09/F02 development stack, not yet the complete P10/P12/P13 family combination. Qualification must bind actual source SHA/tree and bundle hash, count all64 outcomes, retain failures, verify CP6 restoration, advisor, Auth/database cleanup and accepted-package backup/restore. Inspect actual current desktop/mobile screenshots before a visual claim. R10 closure remains subject to the observed outcomes and independent auditor acceptance; no full-ERP production certification. P13, E05 settlement contract/proof and combined F03 install/restore remain separate open obligations.
