# BB T1 auditor exact-head rerun — 25 cases before and after

- [Audit run 36127700002](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36127700002), trigger `0edaebe73e8f3205c2c4582a25c0147beab6f299`, BB writer product/tool head `72bf53f8d808e18fd3e2866491f28667c1b6193d`; development SQL SHA256 `d863144bcbf83e5d445024525d3ee0a07653aa4fb695922e658b91d2d41bc6f3`.
- Auditor script `audit/scenarios/r9_bb_independent.py` SHA256 `4c8557200a281516b1e1eab7a067324b5dafecf98c43441f5fbf4f6b2ca08766`, workflow SHA256 `6ff7827170a36b78f70c1f2b9c7d92476a614d855c3c2a75b40326380f380a0d`. Original writer 24 business operations unchanged. Script drops duplicate display field `case` before reporter appends the canonical ID; adds `AUD:ALL_S01_OPENING_AR_SIGN`. No product SQL edited by auditor.
- Before job `108047512931`, artifact `10860333224`: SUCCESS / REVIEW_COMPLETE; 20 NO_ROUTE +2 COUNTEREXAMPLE +3 PASS; expected before state, no mismatches. Direct settlement before cutover incorrectly posted and dated prefix capacity could go negative before BB.
- After job `108047512581`, artifact `10861050563`: SUCCESS / REVIEW_COMPLETE; 25/25 PASS, no expectation mismatches; primary unchanged=true, clone_remaining=0, all savepoint boundaries restored. `release_evidence=false`, `independent_acceptance=false`, production_go=false.

| Case ID | Before BB | After BB |
|---|---|---|
| `F:P02_SETTLE_AND_REVERSE` | `NO_ROUTE` | `PASS` |
| `F:S01_SETTLE_AND_REVERSE` | `NO_ROUTE` | `PASS` |
| `F:W05_VENDOR_PAYABLE_SETTLE_AND_REVERSE` | `NO_ROUTE` | `PASS` |
| `F:OSS_OVER_REMAINING_REFUSED` | `NO_ROUTE` | `PASS` |
| `F:OSS_BEFORE_CUTOVER_REFUSED` | `NO_ROUTE` | `PASS` |
| `F:OSS_FUTURE_REFUSED` | `NO_ROUTE` | `PASS` |
| `F:OSS_DIRECT_BEFORE_CUTOVER` | `COUNTEREXAMPLE` | `PASS` |
| `F:OSS_DIRECT_FUTURE_CONTROL` | `PASS` | `PASS` |
| `F:OSS_DATED_CAPACITY` | `COUNTEREXAMPLE` | `PASS` |
| `F:OSS_DATED_CAPACITY_ORDERED_CONTROL` | `PASS` | `PASS` |
| `F:S01_CUSTOMER_ALLOWANCE` | `NO_ROUTE` | `PASS` |
| `F:P02_SUPPLIER_ALLOWANCE` | `NO_ROUTE` | `PASS` |
| `F:W05_VENDOR_ALLOWANCE` | `NO_ROUTE` | `PASS` |
| `F:A03_LEGACY_DOCUMENT_NO_LEDGER` | `NO_ROUTE` | `PASS` |
| `F:A03_LEGACY_THEN_OPEN_LATER_BATCH_REFUSED` | `NO_ROUTE` | `PASS` |
| `F:A03_LEGACY_AND_OPEN_SAME_BATCH_REFUSED` | `NO_ROUTE` | `PASS` |
| `F:A03_LEGACY_NOT_SETTLED_REFUSED` | `NO_ROUTE` | `PASS` |
| `F:S03_IMPORTED_CREDIT_REFUND_CYCLE` | `NO_ROUTE` | `PASS` |
| `F:S03_CREDIT_APPLIED_TO_OPENING_AR` | `NO_ROUTE` | `PASS` |
| `F:S03_RETURN_RIGHT_OPEN_INVOICE` | `NO_ROUTE` | `PASS` |
| `F:S03_RETURN_RIGHT_LEGACY_INVOICE` | `NO_ROUTE` | `PASS` |
| `F:S03_RETURN_WITHOUT_INVOICE_REFUSED` | `NO_ROUTE` | `PASS` |
| `F:Y01_OPENING_PAYABLE_THROUGH_PAYROLL` | `NO_ROUTE` | `PASS` |
| `F:Y01_OVER_AVAILABLE_REFUSED` | `NO_ROUTE` | `PASS` |
| `AUD:ALL_S01_OPENING_AR_SIGN` | `PASS` | `PASS` |

**Independent ALL-S01 oracle correction:** on both candidates opening invoice 100 less historical receipts 30 yields debit `AR_CUSTOMER=70.00`, bank debit 100 and aggregate credit `OPENING_EQUITY=170.00`, no extra GL accounts, no synthetic sale/receipt journal, subledger70, six checks true; this is a controlled fixture. Correction recorded after BB published, so do not claim pre-code independence for journal-sign criterion. Frozen original and errata are unchanged.

**Risk / status:** two BA counterexamples targeted by BB T1, but release parity/rollback for BB, two live sessions, real Auth/browser, full ALL22 and C6 75 remain unverified. Writer red run `36126427534` remains red historically. CP6 HOLD, audit_complete=false, production_go=false.

Per-case original status and savepoint flags: `out/gpt_r9_bb_t1_cases.json`.
