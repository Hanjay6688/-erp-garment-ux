# P12 E05 — partial settlement boundary

30 September 2026 WIB. **E05 remains OPEN.** This note corrects an overly specific interpretation in earlier writer handoffs; it neither changes the frozen framework nor creates a wage/payment rule.

The frozen `framework-v2/registries/cases.json` requires payroll attendance APPROVED → paid partial/full, accessory deduction/advance and reversal. Its oracle is expense once, immutable denominator and conservation of remaining entitlement/cash. P12 in `work_packets.json` explicitly forbids inventing wage policy.

The original `ERP_V3_2_Master_Pulih_20260923.md`, G05 (lines6310–6331 in the retrieved Library copy), requires attendance approval, allocation, WIP/FG cost, partial payment and reversal. It requires the existing source/contract and explicitly excludes taking financial policy decisions independently. The original master is already pinned by the accepted contract; this review read the named source, not a newly recomputed byte hash.

These clauses establish a partial-settlement obligation. They do **not by themselves distinguish** cash installments against one APPROVED payroll from selecting part of the earned quantity/components for a fully settled payroll and retaining the remainder for a later payroll. No explicit owner choice between those mechanisms was recovered in this review. Earlier handoffs' label “E05 partial cash payment” was a writer interpretation, not a separately recovered owner decision.

Current implemented behavior is concrete: `cp7_payroll` settlement calls the accepted `erp.post_payroll_payment`; that native function pays the full net payable. The selected-card Nota and opening carry allocation can allocate less than the total available entitlement, but that does not prove every E05 clause. The opening-source oracle pays6060 in full and must not be presented as a cash-installment test.

Before any payment-schema change, bind the intended partial-settlement mechanism to an existing explicit owner/native contract and define its accounting, remainder, reservation, date, replay and inverse oracle. Do not synthesize split cash by rewriting an APPROVED document, reversing/reposting cash journals or changing transaction dates. Continue the unambiguous connected P09/P11/P12/P13 work; keep E05 unresolved until its precise mechanism and complete proof are established.

CP6 remains CLOSED_CONTRACT_SCOPE. P12/F03 remain OPEN. `independent_acceptance=false`; `production_go=false`.
