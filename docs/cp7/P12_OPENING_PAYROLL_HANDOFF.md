# P12 opening sources → payroll — writer checkpoint

Run2 on `a2643533457925213f90d56ab9646ccd0fae8a5c`: **9 PASS /0 FAIL /1 INCOMPLETE /0 NOT_RUN** for the10 opening additions. [Diagnostic receipt](evidence/p12-attendance/OPENING_RUN2_RECEIPT.json). Native5, races2, Auth1 and desktop1 pass; desktop completes CSV import, allocations,6060 payment and full inverse. Mobile commits carry allocation, then its test navigation runs before the authorized shell is ready after reload. The closed-menu screenshot and original error are preserved. The navigation helper now waits for the shell exactly as the previously qualified Nota helper does; rerun remains required. No product financial behavior changed. CP6 restoration, advisor and Auth/database cleanup pass. Prior80 remain separately bound to run1.

30 September 2026 WIB. **Candidate: five new native cases PASS; browser/Auth/race increment is not yet qualified.** The previously qualified 80-case source remains `5082fbec159095c3452c14c6ad500839f28a166b`. This increment adds 10 cases, making an explicitly gated 90-case run. No product SQL, product UI or accepted CP6 function changes are proposed: the connected initial import already supplies the opening allocations; this checkpoint proves their connection to CP7 payroll.

## Fixed financial oracle

The browser imports three old documents through CSV → save → validate → finalize. Recognized wages 90 less 25 paid before cutover leaves 65 payable; old reimbursement adds 20; old cash advance leaves 30 receivable. A sewing entitlement has 40 earned, 10 previously paid and 4 carry at 2.50. Its recognized amount is 65; only 2 carry units are allocated to this payroll, adding 5 when approved. Two ordinary current FG work cards contribute 6000.

PREPARE must preserve the selected work and all reviewed opening allocations: `6000 + 65 + 20 + 5 - 30 = 6060`. Repeated PREPARE creates no GL or stock/HPP effect. APPROVE adds only `Dr LABOR_COST 5 / Cr CONTRACTOR_PAYABLE 5`; the old 85 is not accrued again. PAY settles all three opening documents, disburses 6060 and leaves two carry units. Exact replay creates no second payment. REVERSE restores payable 65 + 20, advance 30 and carry 4, with GL neutral against the post-import baseline. Original opening journals and physical/HPP facts remain intact. Unpaid cancellation also reverses the carry expense and releases reservations.

## Predeclared additions

| Cases | Scope |
| --- | --- |
| P12_OPENING_LIFECYCLE | Import, allocations, repeat prepare, approval, exact payment replay and inverse |
| P12_OPENING_EDIT_RELEASE | Change allocations, exact decimal carry and zero release |
| P12_OPENING_STALE_REVIEW | Old CP7 review and stale payroll version denied after opening edit |
| P12_OPENING_GUARDS | Carry limit, wrong mandor and approved payroll refusal |
| P12_OPENING_CANCEL | Approved unpaid cancellation restores opening sources and GL |
| P12_OPENING_RACE_REPLAY | Concurrent identical opening request produces one allocation |
| P12_OPENING_RACE_RESERVATION | Concurrent competing payroll requests share one finite carry source |
| P12_OPENING_HTTP | Real Auth allocation/replay and deactivation denial |
| P12_OPENING_BROWSER_DESKTOP_CYCLE | CSV source entry, Nota, opening allocation and full payroll cycle |
| P12_OPENING_BROWSER_MOBILE_RECOVERY | Same connected cycle; committed carry response lost, reload, identical retry |

The initial `--opening-payroll` workflow executed the retained80 and opening additions. First result: **85 PASS /0 FAIL /3 INCOMPLETE /2 NOT_RUN**, with CP6 restoration, advisor and Auth/database cleanup intact. [Run1 receipt](evidence/p12-attendance/OPENING_RUN1_RECEIPT.json) and compressed full report retain that outcome. Five new native cases prove the6060 payment and inverse oracle. The next workflow uses `--opening-delta` to rerun only the10 affected additions, with the same restoration/advisor/cleanup gates and exact10-case count. Its report remains `CP7_P12_OPENING_PAYROLL.json`, explicitly labelled `CP7_P12_OPENING_DELTA`. The retained80 are bound to run1, not claimed as executed on the delta SHA. The full90 mode remains available. A green workflow alone is not evidence of 90 PASS. Screenshots require actual inspection before visual review is claimed.

First candidate is `74ae3a1b39b39d878d92bab4604b01cb3a639d16`, tree `50291e7b17326e5ce1fe933cd8926d0d6ec7f64a`, [run36617726767](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36617726767). During review, the new race module's entry point was found to be named `race_cases`, while the inherited runner calls `races`. The next checkpoint corrects that harness name without changing the business oracle; first-run outcomes are retained separately. The HTTP expectation is also corrected to the accepted native P0001/HTTP400 owner/admin denial, with an exact message and no-effect assertion. Both browser diagnostics originally failed while inspecting an unposted source, masking the UI failure; rerun now preserves the original exception and screenshot. The browser cause remains unresolved. Existing initial-import local tests pass81 cases. This is not native execution or independent acceptance.

**P12/F03 OPEN.** E05 partial settlement remains separate and open; its exact mechanism is unresolved in the [contract boundary](P12_E05_CONTRACT_BOUNDARY.md). Capped kasbon and this full payment do not close E05. P11/R10, P13, the remaining P09 scope, combined release/install/recovery and independent family acceptance remain open. CP6 stays CLOSED_CONTRACT_SCOPE; `production_go=false`, `independent_acceptance=false`. The owner permits F04 takeover after F03 is complete, subject to rereading its handoff and current writer heads before editing.
