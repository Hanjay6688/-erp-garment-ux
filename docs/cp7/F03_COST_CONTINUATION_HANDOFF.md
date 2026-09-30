# F03 required cost continuations — writer checkpoint

F03 OPEN; CP6 CLOSED_CONTRACT_SCOPE; independent_acceptance=false; production_go=false. This checkpoint does not authorize F04 or production.

Source `f7c91bf382c74f385217070673397d2947b3c6a9`, tree `907d5b477b3757596329e8543a87240860812a25`, [run36654590107](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36654590107), job109696065667: **4 PASS /0 FAIL /0 INCOMPLETE /0 NOT_RUN**. [Compressed original reports](evidence/f03-cost-continuation/QUALIFIED.json.gz), [artifact/source/hash receipt](evidence/f03-cost-continuation/QUALIFIED_RECEIPT.json). Workflow success was checked against all four case results.

| Case | Exact evidence |
|---|---|
| O18 pocket allocation and P13 report | Historical lawful source11.25 split across denominator10: WIP5=5.62, FG3=3.38, sold2=COGS2.25; expense reclass−11.25. Source correction to15 gives7.50/4.50/3.00. Cancellation restores those three allocations to0, leaving expense+3.75 and opening-equity−3.75 from the retained source correction. Native journals and CP7 report agree; same UUID posts once. |
| E07 receipt-pocket certainty/reprice | Equal estimate/invoice changes ESTIMATED→ADJUSTED without money delta; inverse restores certainty. Later receipt repricing yields pool15, allocation delta WIP1.88/FG1.12/COGS0.75. Quantity stays15, stock is not drawn twice, inverse restores deltas0. |
| E07 sale/return/conversion | Same allocation delta reaches source/child costs34.50/11.50. Quantity, original source, history and exact correction/allocation inverses pass. |
| E04 sold conversion child | Actual accessory source reaches sold parent and conversion child: late invoice FG+4/COGS+2; actual recovery FG−2/COGS−1. Original sale snapshots remain immutable, no extra income, dependency/capacity/policy refusals and inverse pass. |

All four execute against the explicit26-role F03 installed stack on disposable native PostgreSQL17. Exact guard/ACL verification, CP6 restoration, advisor gate, unchanged primary database, install/backup restoration and cleanup pass. Source bundleSHA256=`d999ab45ebe40001e7a30ba46e0e10a18b950cc19531555716060d62cdd1759e`.

These are selected financial branches, not full E04/E07 or family acceptance. No browser execution, visual review, service refund, partial cash payroll, new independent CP6 acceptance or production change is claimed. Current product paths match55cb59d. The wrapper now preserves a delegated FAIL/COUNTEREXAMPLE result instead of converting a non-PASS business result into an assertion/setup INCOMPLETE; that reporting-only change does not alter the retained run.
