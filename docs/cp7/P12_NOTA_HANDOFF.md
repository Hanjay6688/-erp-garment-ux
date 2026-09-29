# P10 Nota → P12 payroll — bounded writer checkpoint, 29 September 2026

**Selected-card Nota transaction scope: 20/20 PASS. Independent acceptance pending. F03 and full P12 remain OPEN. production_go=false.**

Qualified source: `3d7ef09cc67426fda5c333ee6b963a587fc31c7e` (tree `db90eb5b83186ad632dab654dd35d200b0cce78c`). [Run 36579321113](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36579321113), job 109443017719, artifact 11039022192. Archive SHA256 `9329b2cc91d8a9a57a7b39d84f99c5a2443461e00104c7c0537c6d4c37bca48a`. Native Nota bundle SHA256 `f4cc89bc15d5d4231bd13f7791be90a4dd74b4197c397932018678172faaceee`. Receipt and full report: [NOTA_VERIFICATION.json](evidence/p12-nota/NOTA_VERIFICATION.json), [CP7_P12_NOTA.json.gz](evidence/p12-nota/CP7_P12_NOTA.json.gz).

## What works in this bounded scope

- Standalone Susun Nota FG: whole remaining component cards from Regular, completed contractor REWORK and unsourced BS repair. Combine cards for one mandor, save draft, review and post only the selected sources to a new or explicitly chosen editable payroll. Native historical source rates remain the authority.
- Two actual repair receipt cards: 3 component PCS at2000 =6000, one native CALCULATED payroll and two work items. Posting is not payment and creates no second FG/HPP/journal effect.
- Ordinary contractor rework: no eligible card before completed; after BS resolution/completion only two newly payable components at30 =60. Native work not selected in the Nota is not automatically populated.
- Draft exact-version edits and void release private claims; native payroll allocation alone reserves payable quantities. Same-card draft race, same-UUID post race and current permission after actual row-lock wait pass.
- Explicit append to existing payroll; changed payroll version or native partial source allocation requires a new review. Failure rolls back both new header and allocation.
- Current Auth/permission is checked before cached replay and after waits. Operational source/Nota DTOs omit every money field. Private command principal has no ERP business table DML; header principal has only identity/period insertion and row lock.
- Real desktop HTML drag and mobile add-button flow; mobile POST commits while its HTTP response is lost, then reload/reconcile reuses the exact original payload/version/UUID. One allocation, no payment or duplicate cost. Failed refresh retires displayed source facts.
- Native cancellation is an explicit test control: source cards return, old Nota stays POSTED, native payroll reads REVERSED and note snapshots remain. This does **not** claim connected payroll cancellation/payment UI.

## Evidence

| Group | PASS |
|---|---:|
| Native source | 5 |
| Source real Auth/HTTP | 1 |
| Native Nota | 7 |
| Concurrent transactions | 3 |
| Nota real Auth/HTTP | 1 |
| Existing P09 HTTP admission regression | 1 |
| Actual browser | 2 |
| Total | 20 |

Separate local DOM/contract:5 PASS. Shell build, tests and both CodeQL analyses passed [run36579336948](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36579336948). Separate P09 regression [run36577500114](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36577500114):121 PASS plus3 smoke cases, full archive read and digest verified. Exact predecessor restoration, advisor gate, Auth cleanup, disposable copy cleanup and backup/restore drill passed. These are writer-run proofs, not independent acceptance or a CP7 release install/rollback certification.

## Failures retained and corrections

SOURCE_RUN_1 and NOTA_RUN_1..3 reports remain in evidence/p12-nota. Missing nested-view SELECT closure, custom-role native admission, cross-timezone source tokens/snapshots, test scope errors and harness hash-vs-SQL mismatch were corrected openly. Run3 HTTP mismatch was timestamp serialization: the unchanged full stock/HPP/journal rows yield different raw JSON hashes by connection timezone; canonical UTC comparison now passes and reproduces that prior false difference. Existing legacy component UUID `a4000000-0000-0000-0000-000000000001` is accepted as a PostgreSQL UUID, rather than inventing a new RFC-version constraint for old masters.

The sole native definition delta is hash-bound admission in require_internal through a private transaction/actor/action/permission context. Native wage, allocation, cost, stock and journal writers are unchanged. The probe verifies the exact complete definition delta and restores the accepted predecessor afterwards.

## Visual follow-up and next P12 work

The qualified run's desktop/mobile screenshots were inspected. Posted cards had low-contrast text in the dark theme; a subsequent candidate fixes the surface colors, labels posted quantities as historical "PCS dalam nota", and uses plain recovery wording. Its browser rerun must prove contrast as well as the existing transaction flow. Transaction PASS is not used to claim this visual correction already verified.

A separate candidate finance reader exposes native payroll headers and fully paged work, attendance, reimbursement, deduction and source-note history. Finance permission is independent of operational handoff permission. Review token binds header and all child revisions; a changed child without recalculation must visibly invalidate review and flag inconsistent stored totals. Five new native/HTTP cases are predeclared. This candidate is not yet qualified and has no connected payroll writer/UI.

Next: preserve selected work when attaching attendance/accessory/advance sources; native APPROVED cost once; payment and inverse lifecycle; opening/carry balances; connected finance/attendance browser and E05. Native post_payroll_payment currently settles the full net amount; E05 partial payment remains a real integration obligation, not a silently claimed feature. P11/R10 and P13 remain open. P09 larger return/count/issue cases and full-family combined release gates also remain open.

The Nota page is connected only in DISPOSABLE_TEST. Hosted CP6 boundary and production data remain untouched. Acceptance belongs to the auditor and owner.
