# P12 payroll continuation — writer candidate, 29 September 2026

Finance review is qualified on `5da1fb6106c7c72058ebd73a782a5155f59c258d`: **27/27 PASS**, including desktop/mobile finance-view-only UI, complete native totals and source Nota trace. Full receipt: [PAYROLL_UI_VERIFICATION.json](evidence/p12-nota/PAYROLL_UI_VERIFICATION.json); [run36583328093](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36583328093). This remains writer evidence, independent acceptance pending. Full P12/F03 OPEN; production_go=false.

## Native lifecycle candidate — result pending

The candidate exposes PREPARE, APPROVE, PAY, CANCEL and REVERSE through one public exact-version/review-token/request-UUID command. The command principal has no ERP table DML. A private transaction/actor/document/action context permits a narrowly scoped postgres-owned adapter. Existing finance permissions are applied: view always; approve for preparation/approval/unpaid cancellation; pay for full settlement; both approve and pay for reversing a paid payroll, because native reversal reverses cost approval and payment together.

The accepted populate function deletes/recreates every work allocation and pulls all eligible work. That would defeat selected Nota cards. A new private helper is derived byte-for-byte from the accepted definition with only the work delete/insert removed, plus function name/private admission/empty search path. Attendance, native historical worker rates, BOM reimbursements and FIFO capped material/accessory kasbon formulas remain identical. The accepted populate function itself stays unchanged. PREPARE preserves selected work IDs, quantities and rates. APPROVE reruns preparation and compares complete economic content; changed sources or totals roll back and demand a new preparation/review.

All non-work existing source rows are locked for the reviewed rebuild. A new attendance source committed while approval waits must be observed and refused as unreviewed. Header and all child revisions bind the review token, even when an external child edit did not bump the header version. Current access is checked before cached replay, after waits and after the native action. Private command metadata/context is inaccessible to public, operational and read roles.

APPROVE, full PAY, CANCEL and REVERSE use the accepted native financial functions. Payment accepts date and cash account, with the amount fixed by the approved native net. Attendance cost is recognized at approval once; payment settles. Reversal ends REVERSED and keeps Nota history, releasing native source allocations. No payment-only transition back to APPROVED is invented. Missing/inactive cash, future payment date, stale review and extra amount fields must roll back completely.

Declared native admission deltas are exact/hash-bound changes to require_internal and require_owner_admin, each scoped to the private context and current permissions. The probe verifies complete predecessor definitions/ACLs and derived-helper identity; it restores original functions and removes all candidate roles/schema. No hosted installation or production data write.

## Predeclared qualification

Retain27 qualified Nota/source/finance reader/browser cases, and add12:

- Seven native cases: full6000 payment/replay/inverse, selected6000 work preserved while unselected2000 remains available, ordinary posted attendance100 giving6100 net with approval-only accrual, ordinary accessory note10000 capped to6000 deduction/4000 carry with no cash at zero net, stale child, custom permissions/private boundary, invalid payment plus unpaid cancellation.
- Four real concurrency cases: same payment UUID, competing payment/cancellation, authority revoked during an actual payroll lock wait, and new attendance posted during an approval lock wait.
- One real Auth/HTTP custom-role preparation/approval/payment/replay, anonymous refusal and deactivated replay refusal.

Expected total39. These candidate cases are **not yet claimed PASS**. Native financial controls used by these cases do not imply connected settlement writer UI.

## Remaining P12/family obligations

Connect the qualified settlement command to explicit frontend review/recovery; connect attendance/roster/rate and opening cash advance/payable/carry source editing and their ordinary browser proofs; finish E05 including its partial-payment obligation. Current native payment is full net, not a partial cash payment feature. Keep P11/R10 and P13, broader P09 continuations, independent family acceptance and combined release/install/recovery gates open. Existing business decisions and CP6 closure remain intact.
