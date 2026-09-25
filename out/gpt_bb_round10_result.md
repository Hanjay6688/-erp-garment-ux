# Independent BB round 10 — native run 36154846659 rev1

Audit commit [7199cadb](https://github.com/Hanjay6688/-erp-garment-ux/commit/7199cadb468c0c372118280b98b15c6aabd8efbf), writer tool head `4c61acad2270e11a2aca762237790a68cf36278a`, installed product ref `797fadd8b0b4aa033d3c807f0f806270fa1cf87b`. [Actions run 36154846659](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36154846659), job `108136764090` SUCCESS; scenario sha256 `18dc5075eabb27302b80d7c9919164d1ed371342f6c6c78839d7614f523f8d7c`, phase after, `RUN_COMPLETE`, both boundaries restored, no session leaks.

| Case | Raw native runner | Auditor disposition |
|---|---|---|
| `G10:BB_TWO_DRAFT_SHARED_RESERVE` | PASS, all five checks true | Local S02 **ACCEPT** for this specific two-draft cycle: free 5→4→6→6; cancel no journal; native POST single AR +40, revenue −40, COGS +24, FG −24; one source/reserve for each draft. Master Pulih M:3821, M:6631. This does not accept the full ALL/CP6 gate. |
| `G10:BA_TEN_DOCUMENT_CENT_POOL` | COUNTEREXAMPLE because `no_remaining_stock_qty_or_value=false` | **INCOMPLETE as product oracle.** Auditor's rev1 fixture captured the inventory baseline *after* the ten receipts; it therefore computed −100.10 instead of zero when all units were used. This is an auditor error. Independent observed values are still useful: ten distinct docs, physical qty zero, aggregate WIP 100.10 (ten × 10.01), per PO [10.05,10.01,10.00,10.01,10.00,10.01,10.00,10.01,10.00,10.01]. Largest PO deviation from its document's rounded value = +0.04, but pooled moving average does not guarantee per-PO invoice allocation. |

Writer's question in `docs/cp6-t3-cent-per-po-and-t5-advisor-note.md:65–72` permits at most **one cent per contributing document** into the next consumption, not an unconditional one cent *per PO*. Rev1 field `writer_claim_1_cent_per_po_holds=false` misphrases that question and MUST NOT be used to claim a defect. Rev2 renames the observation and measures the one-cent-per-document aggregate bound separately. Contract M:835/M:3820/M:6632 governs total, dated value, stock exhaustion and trace.

Next: rev2 scenario sha256 `4655575482e90e333f753bd65d7f788c2f04f55e8c47e05ae31d275a80393b86` moves the inventory baseline to before the receipts and corrects the writer-claim wording; native rerun pending. CP6 HOLD, `audit_complete=false`, `production_go=false`.
