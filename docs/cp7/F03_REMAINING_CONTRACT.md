# F03 continuation boundary — current implementation and remaining contracts

This ledger replaces obsolete “next” wording in historical packet narratives; it does not change any frozen framework file or mark a family accepted. CP6 is CLOSED_CONTRACT_SCOPE. F03 is OPEN, independent_acceptance=false and production_go=false. F04 takeover follows completion of this family's agreed boundary.

**Keuangan (termasuk laporan), stok dan HPP adalah raja. Reliable data adalah dewa.**

## Bounded results available to the next auditor

| Packet | Implemented and source-bound writer proof | Remaining acceptance work |
|---|---|---|
| P09 | Receipt, transfer, combined invoices, original-source return/portable supplier credit, receipt inverse, UOM, physical multi-input and registered zero-history counts:132 PASS plus3 separate smokes on `09efc955`. [Receipt](evidence/p09-procurement/UNMOVED_QUALIFIED_RECEIPT.json). | Remaining material-issue continuations, mixed-receipt return writes, paid-source return carry and complete E01/E24/E12/E14 integration. Zero-history and multi-input counts are no longer implementation gaps. |
| P10 | Exact FG summary/ledger/adjustment/book proof34 on `7ddeca84`; [regression receipt](evidence/p09-procurement/UNMOVED_P10_REGRESSION_RECEIPT.json). P12 already supplies native source entitlement/card/Nota and opening→payroll continuations. | Audit exact-size/ownership and source handoff across the complete packet, including O07 and E01/E04/E13/E14/E20. A working Nota card does not create FG or prove the planner's size-gap result. |
| P11 | Native draft/post/cancel, partial/full customer payments, original-allocation Grade A/B/HOLD returns and full invoice inverse:64 PASS on `e8084530`, including two actual R10 browser journeys. [Receipt](evidence/p11-sales/RETURN_VERIFICATION.json). | Independent R10 review and E03 customer-owned service/return/refund chain. Existing paid-return refusal must not be relabeled a cash-refund or customer-credit carry workflow. |
| P12 | Selected-card Nota/attendance→payroll80, and separate opening→payroll10; [source handoff](P12_SOURCE_HANDOFF.md). Latest opening10 regression on `f7bddaf` passes; combined stack repeats selected continuations. | Resolve E05's precise partial-settlement meaning against the owner contract, then test the missing mechanism. [Boundary](P12_E05_CONTRACT_BOUNDARY.md). Finish E07/E12/E14 integrations; a full 6060 payment is not installment proof. |
| P13 | Dated native financial report and immutable archive12 PASS on `d1a8a84`; [receipt](evidence/p13-finance/PERIOD_REPORT_REPAIRED_RECEIPT.json). Period control25 PASS on `9861692`; [receipt](evidence/p13-finance/PERIOD_QUALIFIED_RECEIPT.json). | Complete the current comparison/cash24 candidate; period25 is qualified. Qualify the [native recost candidate](P13_RECOST_HANDOFF.md) and connect remaining financial controls where required, with current permission/replay/date proofs. Complete O18, E04/E05/E06/E07/E13/E14/X04. Existing HPP-per-SKU reader is present; do not rebuild it as a second costing engine. |
| Combined F03 | Explicit P09→P10/P12→P11→P13 install/restore with24 private roles after period extension. Selected22 integration cases PASS on `d1a8a84`; [receipt](evidence/p13-finance/PERIOD_COMBINED_REPAIRED_RECEIPT.json). | Full E01 numerical source-to-cash journey and all required packet exits. Selected22 is neither the sum of historical suites nor full-family acceptance. |

Counts overlap and belong to their exact source SHA/tree/bundle receipt. Do not add them into a single “total tests on current candidate.” Retained first failures are evidence, not current reopened defects when a later source qualified the repair. The original framework's case status fields remain frozen historical contracts, not this execution ledger.

## Next work order

1. Keep the qualified period25 receipt and finish comparison/cash24, preserving every failed or missing case and restoration/cleanup outcome. Inspect actual responsive screenshots before visual acceptance. Reconcile their source against the combined installer.
2. Complete the remaining unambiguous financial/stock continuations and native recost control, using existing domain writers. An RPC success is not “all costs final”: pending/failed queue state and per-date readiness remain authoritative.
3. Exercise E01 from lawful opening/material receipt through production, FG, sale, customer payment and report. The frozen oracle is60 GOOD PCS/value900/HPP15; sale20×25 and cash200 leaves FG40/value600, COGS300, revenue500, AR300. No direct final-HPP/stock inserts or new factory defaults are allowed. E03 branches from an isolated copy of that exact source state.
4. Finish transitive cost/late-date/pocket/import and recovery/access cases listed above, without treating earlier bounded source coverage as whole-charter acceptance.
5. Freeze the actual integrated source and hand the family to an independent auditor. Resolve confirmed findings before F04 dependencies proceed. P18–P21 still own final lifecycle, scale/resilience, independent candidate audit and release installation/recovery.

## Business decisions that cannot be silently supplied by code

The native payroll writer settles the full net payroll, while the framework requires partial/full settlement without identifying cash installments versus partial earned-source selection. Advance/opening-payable reservation and reversal timing must follow an explicit recovered decision; do not invent it from a test target. Likewise, a refusal of a paid invoice return is not a refund policy. Continue unaffected work while keeping these concrete boundaries visible.

The existing vendor rules remain binding: laundry can proceed with UNKNOWN price until the kontra bon, checkbox components and named combinations derive price from vendor tariff, SKU history is a selection aid, and same-counterparty credit can move between eligible invoices while retaining original settlement ability and exact accounting. These rules are not rewritten by CP7 reporting or checkpoint labels.
