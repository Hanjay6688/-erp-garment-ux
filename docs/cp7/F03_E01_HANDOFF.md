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

Every execution has its own source. Report differences are checked against the exact worksheet and UI amounts against the same native report. A final source HPP does not make open payroll obligations disappear or close the books. Customer-owned E03/refund and independent R10 remain separate obligations. Selected pocket/transitive-cost proof is now retained in [its handoff](F03_COST_CONTINUATION_HANDOFF.md); it does not close E04/E07 in full.

## Retained first result and correction

Source `698480b2567967d8f21cdb9268b9db835f08acae`, tree `1b1c261ef34b99b54e6aa7de34bec435c3951304`, [run36653759262](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36653759262), job109693480199:0 PASS,1 INCOMPLETE. Receipt100/value1000 and cutting remainder40/value400 passed before source preparation stopped at a private work-snapshot function. No sales/HPP success is inferred from these checkpoints. CP6 restoration, advisors, installation/backup restoration, primary database and Auth cleanup passed; writer-runtime gate correctly failed.

[Original compressed reports](evidence/f03-e01/NATIVE_FIRST.json.gz) and [artifact/source receipt](evidence/f03-e01/NATIVE_FIRST_RECEIPT.json) retain the failure and hashes. The correction uses admitted native `ensure_po_work_component_snapshots_v2` with request UUID. The disposable legacy work-DRAFT schema grant is restored before HTTP calls. No function permission was widened and no product formula was changed.

Connected candidate `01739294afa774f309c9d65d28d4e2dcd01175f1`, [run36653998973](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36653998973), job109694216142:0 PASS/4 INCOMPLETE on the same private-call setup defect. [Receipt](evidence/f03-e01/CONNECTED_FIRST_RECEIPT.json). Follow-up `9aad2a21de0c3e4ff81d6ebdb0ce2b93193671c3`, [run36654159977](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36654159977), job109694704358:0 PASS/4 INCOMPLETE. It correctly uses the admitted work API and reaches sewing30+30/cost120, laundry30+30 and QC20+40=60 GOOD, then the undeclared disposable LAU_DEC02 policy blocks invoice posting. [Receipt](evidence/f03-e01/ADMITTED_SOURCE_RECEIPT.json). Both keep CP6 restoration, advisors, installation/backup restoration and Auth/database cleanup green; no financial finish/browser PASS is inferred.

## First connected qualification and remaining readiness limit

Source `9f040b8bb0352ee2a94c473e1b9cca6fe41beec7`, tree `07bce31ddec2cd800b4d5c4fe063496f8e73b963`, [run36654365874](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36654365874), job109695336002: **4 PASS /0 FAIL /0 INCOMPLETE /0 NOT_RUN** (one native, one real Auth/HTTP, desktop and mobile). [Reports](evidence/f03-e01/POLICY_QUALIFIED.json.gz), [source/artifact receipt](evidence/f03-e01/POLICY_QUALIFIED_RECEIPT.json).

All source, sale, payment, original-allocation return and exact money assertions pass, including mobile committed-response loss/reload/exact-UUID replay. CP6 restoration, advisors, package installation/backup restoration, unchanged primary database and Auth/database cleanup pass. The four original sale/return/report screenshots were inspected: desktop/mobile sale detail shows net375, payment200, AR175 and five returned PCS. The report truthfully shows BLOCKED and a long, scrollable list of obligations. Browser source-production entry remains outside this proof.

**This first qualification does not prove READY:** the report includes the fixture's own unallocated sewing60/value120, plus foundation attendance/payroll obligations. Own HPP is final and own WIP0; global seeded WIP is not asserted to be zero. These limits do not erase the four bounded PASS results or imply a monetary defect.

## READY source qualification

Candidate `d828c2e1337a7f9f7b20d811b5be2baa17ac2b09`, tree `aa9e7548ebedae5b09f06e172cde9afa71bc9048`, [run36655185497](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36655185497), job109697895093: **4 PASS /0 FAIL /0 INCOMPLETE /0 NOT_RUN**. [Original reports](evidence/f03-e01/READY_QUALIFIED.json.gz), [complete source/artifact/hash receipt](evidence/f03-e01/READY_QUALIFIED_RECEIPT.json).

The native, real Auth/HTTP, desktop and mobile executions all require and obtain **READY** before and after the sale/payment/return journey. Current HPP components are exactly MATERIAL600/LABOR120/ACCESSORY60/LAUNDRY120. Actual earned-source cards pass CP7 Nota SAVE/POST and CP7 payroll PREPARE/APPROVE: labor120 plus accessory reimbursement60 equals approved-unpaid180. Approval replay is exact; stock/HPP/journals remain unchanged and no wages are paid. This resolves the own-source readiness limit of the first connected qualification.

The disposable foundation's other obligations are completed using existing native attendance/payroll writers, never hidden/deleted/disabled. The seeded foundation still has unrelated WIP; the qualified own source has WIP0. CP6 restoration, advisors, exact26-role admission, package installation/backup restoration, unchanged primary database, real Auth cleanup and database cleanup all pass. This is four overlapping executions of one worksheet, not four independent business requirements or proof that every production-entry form was used.

All four original screenshots were inspected. Retained images are lossless and pixel-identical to their originals, with hashes in the receipt: [desktop sale/return](evidence/f03-e01/READY_E01_SALE_RETURN_DESKTOP.webp), [mobile sale/return](evidence/f03-e01/READY_E01_SALE_RETURN_MOBILE.webp), [desktop READY report](evidence/f03-e01/READY_E01_REPORT_DESKTOP.webp), [mobile READY report](evidence/f03-e01/READY_E01_REPORT_MOBILE.webp). Mobile report includes both browser fixtures: revenue750/COGS450/gross300; the test checks the second source's exact375/225/150 delta. READY does not mean the period was closed; no closing/archive action is claimed.

No product source paths (`src`, `scripts/cp7-src`, `supabase`) have changed since55cb59d. E03 customer service, remaining packet exits and independent acceptance continue separately; F03 remains OPEN. [Active E03 work](F03_E03_HANDOFF.md).


## E12 second-tab continuation — execution pending

The existing mobile E01 journey now also opens a second real tab in the same authenticated browser context on the same partially paid invoice before the return. The first tab commits its return and loses the response. The second tab must observe recovery, disable another return/payment, permit a read showingAR175 without clearing the pending envelope, and retain the original return UUID and document. Reload/reconciliation in the first tab must return that same outcome. A fresh read then restores the second tab's controls, with zero write RPCs from the second tab and still exactly one return/FG45/value675.

This extends the existing mobile case; it does not add invented case counts. The four-case E01 native/HTTP/desktop/mobile suite must qualify the updated source. Earlier four-PASS proof remains valid in its earlier scope. No two-tab result is claimed until the new run is inspected. Other-device/localStorage-isolated clients still rely on server source/version/capacity controls and are not covered by this browser-context assertion.
