# F03 E01 — one lawful source through sale, cash, return and report

F03 OPEN; CP6 CLOSED_CONTRACT_SCOPE; independent_acceptance=false; production_go=false. This is writer work, not independent acceptance. F04 has not started.

The frozen worksheet remains `framework-v2/04_BUKTI_DAN_ORACLE.md`, E01/E03. No frozen requirement or expected amount is changed.

## Source and exact oracle

- Public P09 receipt:100 raw units×10, final supplier AP1000; native cutting consumes60, leaving raw40/value400 and producing60 PCS of one brand/size.
- Isolated model and contractor masters supply one native committed work-BOM/rate:two posted sewing legs30+30 at2, total120. `ensure_po_work_component_snapshots_v2` commits the master basis; there is no direct HPP/result snapshot seed.
- Two vendor-priced laundry legs30+30 at2. GOOD receipts and QC20+40 retain each original receipt-size source. One counterpart invoice120 replaces the estimate through the accepted laundry writer.
- Accessory cost60 uses the existing contractor-supplied `BOM_STANDARD` path:one per GOOD, HPP1 and reimbursement1. It creates native FG accessory snapshots and contractor entitlements. It does not claim a company accessory-stock issue. Disposable LAU_DEC02=GOOD and LAU_DEC06=PRODUCT_COST/REFUSE are declared via the accepted owner policy command; no variance/refund policy is exercised or deployed.
- All production FG60/value900/HPP15, physical own WIP0. No company FG/stock/HPP outcome is inserted directly.
- Draft20 reserves exactly20; posting at25 gives revenue500, COGS300, FG40/value600. Cash200 gives AR300. GOOD return5 at original125 gives FG45/value675, COGS225, revenue375, AR175, cash200, gross profit150. Same UUID cannot return another5.

## Execution boundary

The dedicated `cp7-f03-e01.yml` installs the same explicit26-role F03 stack, verifies exact guard/ACL changes, then runs one native execution, one Auth/HTTP execution, and desktop/mobile browser executions. These overlap the same journey; they are not four separate business requirements. Mobile loses a committed return response and replays the identical envelope after reload. Browser writes cover invoice creation/post, payment and return; upstream receipt/production is qualified through the native source fixture. Production-browser entry is not claimed.

Every execution has its own source. Report differences are checked against the exact worksheet and UI amounts against the same native report. Global report confidence is retained as returned; a final source HPP does not make unrelated seed obligations disappear or close the books. Customer-owned E03/refund, pocket/transitive-cost continuations and independent R10 remain separate obligations.

## Retained first result and correction

Source `698480b2567967d8f21cdb9268b9db835f08acae`, tree `1b1c261ef34b99b54e6aa7de34bec435c3951304`, [run36653759262](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36653759262), job109693480199:0 PASS,1 INCOMPLETE. Receipt100/value1000 and cutting remainder40/value400 passed before source preparation stopped at a private work-snapshot function. No sales/HPP success is inferred from these checkpoints. CP6 restoration, advisors, installation/backup restoration, primary database and Auth cleanup passed; writer-runtime gate correctly failed.

[Original compressed reports](evidence/f03-e01/NATIVE_FIRST.json.gz) and [artifact/source receipt](evidence/f03-e01/NATIVE_FIRST_RECEIPT.json) retain the failure and hashes. The correction uses admitted native `ensure_po_work_component_snapshots_v2` with request UUID. The disposable legacy work-DRAFT schema grant is restored before HTTP calls. No function permission was widened and no product formula was changed.

Connected candidate `01739294afa774f309c9d65d28d4e2dcd01175f1` started before that correction and still contains the same private-call setup defect. Follow-up `9aad2a21de0c3e4ff81d6ebdb0ce2b93193671c3` corrects that call and restores the HTTP fixture ACL. Latest local continuation also declares the required disposable laundry-invoice policy. Results remain PENDING until their actual report and cleanup evidence are read. No screenshot review is claimed yet.
