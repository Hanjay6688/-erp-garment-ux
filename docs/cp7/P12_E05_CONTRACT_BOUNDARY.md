# P12 E05 — approved payroll cash installments

**Owner decision resolved; implementation and full E05 qualification remain OPEN.** Hansen approved cash installments against the same approved payroll on30 September2026,23:59:57 WIB: “ok setuju, lanjutin sisanya ya cp7 sampe beres”. The immediately preceding explanation was approved wages1000, cash600, remaining400 on that same document, then cash400 to settle. This newer explicit decision supersedes the historical ambiguity note below. It authorizes completing CP7; production deployment and merging the integration branch remain outside this authorization.

The approved native earned quantities, rates, attendance cost and net payable remain immutable. Cost is recognized once at native approval. Each cash installment has its own exact amount, cash account, physical payment date and native journal. Active native payments determine cumulative paid cash and the remaining balance. A partial payment keeps the native payroll APPROVED with a derived partial-payment label; PAID means cumulative cash equals the approved net. No new payroll status enum or reduced approved denominator is invented.

Existing native material, cash-advance, other deduction, opening-payable and reimbursement reservations remain reserved during partial cash payment. Their existing native settlement effects run once when the final cash installment settles the payroll. Cash600 on gross1000 less reserved deductions200 leaves net remaining200, AP400 and reserved AR200. The final cash200 plus deductions200 closes both accounts. This preserves existing native deduction timing and prevents reusing reserved entitlements.

An installment inverse retains its original payment and date and adds a linked native inverse on its own date. It reduces active cumulative cash and reopens the same payroll balance without reversing approved cost. If previously fully settled, the active non-cash settlement effects also reverse and their sources return to the native reserved state. Whole-payroll reversal must honor the native active-HPP-pool/dependency guard, inverse every active installment and invoke the native approval/settlement reversal once.

| Fixed oracle | Native accounting and same-document balance |
|---|---|
| Approved1000, pay600 | Cost1000 once; cash credit600/AP debit600; approved net1000; active paid600; remaining400; APPROVED |
| Pay final400 | Cash credit400/AP debit400; active paid1000; remaining0; PAID; no second cost |
| Inverse first600 after fully paid | Original600 retained; linked inverse600 on its own date; active paid400; remaining600; APPROVED; cost unchanged |
| Pay replacement600 | New dated payment600; active paid1000; remaining0; PAID; original and inverse retained |
| Gross1000, reserved deductions200, pay600 | Approved net800; active paid600; remaining200; AP400; reserved AR200 |
| Final cash200 on net800 | Active paid800; remaining0; native deductions200 settle once; AP0/AR0 |
| Whole-payroll inverse | Active cash and native source effects inversed once; REVERSED; native source reservations released; no false outstanding balance |

Commands require current payroll view/pay authority (whole-payroll reversal also requires approve), exact source/revision review, canonical UUID, closed payload, native locks and current authority rechecks before cached responses. Repeated identical intent returns the same committed outcome. Changed intent, overpayment, changed source/master, revoked access and legacy full-payment/cancellation bypass on a managed partially paid payroll fail atomically. A lost response keeps the original durable UUID/payload and retires related financial facts until reconciliation.

The existing full-payment6060 opening-source proof is not installment proof. New native, observed race, Auth/HTTP and desktop/mobile cases must qualify the exact implementation, including restore/cleanup gates. Writer proof is not independent family acceptance.

## Historical boundary before the owner decision — superseded

30 September 2026 WIB. **E05 remains OPEN.** This note corrects an overly specific interpretation in earlier writer handoffs; it neither changes the frozen framework nor creates a wage/payment rule.

The frozen `framework-v2/registries/cases.json` requires payroll attendance APPROVED → paid partial/full, accessory deduction/advance and reversal. Its oracle is expense once, immutable denominator and conservation of remaining entitlement/cash. P12 in `work_packets.json` explicitly forbids inventing wage policy.

The original `ERP_V3_2_Master_Pulih_20260923.md`, G05 (lines6310–6331 in the retrieved Library copy), requires attendance approval, allocation, WIP/FG cost, partial payment and reversal. It requires the existing source/contract and explicitly excludes taking financial policy decisions independently. The original master is already pinned by the accepted contract; this review read the named source, not a newly recomputed byte hash.

These clauses establish a partial-settlement obligation. They do **not by themselves distinguish** cash installments against one APPROVED payroll from selecting part of the earned quantity/components for a fully settled payroll and retaining the remainder for a later payroll. No explicit owner choice between those mechanisms was recovered in this review. Earlier handoffs' label “E05 partial cash payment” was a writer interpretation, not a separately recovered owner decision.

Current implemented behavior is concrete: `cp7_payroll` settlement calls the accepted `erp.post_payroll_payment`; that native function pays the full net payable. The selected-card Nota and opening carry allocation can allocate less than the total available entitlement, but that does not prove every E05 clause. The opening-source oracle pays6060 in full and must not be presented as a cash-installment test.

Before any payment-schema change, bind the intended partial-settlement mechanism to an existing explicit owner/native contract and define its accounting, remainder, reservation, date, replay and inverse oracle. Do not synthesize split cash by rewriting an APPROVED document, reversing/reposting cash journals or changing transaction dates. Continue the unambiguous connected P09/P11/P12/P13 work; keep E05 unresolved until its precise mechanism and complete proof are established.

## Concrete decision fixture — proposed, not an accepted policy or result

An approved payroll has net1000 and the business wants to hand over cash600 now. The two interpretations produce different records:

| Interpretation | Record after cash600 | Remaining400 |
|---|---|---|
| Cash installments on that approved document | Original approved net1000 stays immutable; cumulative cash600; an unpaid balance400 remains against that same document | Later payment settles that same payroll. Exact timing of advance/deduction consumption, cancellation and inverse must be declared before implementation. |
| Select fewer earned components before approval | A different selected-source payroll of net600 is approved and paid in full; an already-approved1000 is not silently reduced | Unselected entitlements remain available for a later payroll. Existing selected-card support is evidence for this source selection only. |

Both must preserve original earned quantities/rates, recognize each cost once and retain every cash/source allocation. This table makes the unresolved choice reviewable; it does not authorize either new financial mechanism or alter existing payrolls. The independent auditor must receive the selected contract with a fixed money/stock/replay/inverse oracle.

CP6 remains CLOSED_CONTRACT_SCOPE. P12/F03 remain OPEN. `independent_acceptance=false`; `production_go=false`.
