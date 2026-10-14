# ASTRA-CP17-FIN-01 — Payroll can settle a liability before its accrual

**TERBUKTI / NATIVE_QUALIFIED · S0 under the frozen Pro Max §8 definition.** Candidate `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`. Relevant invariants: INV-P01, INV-U04/U07, INV-L01/L02; the report date is an essential part of the financial claim. This is one root cause with three witnesses, not three findings.

Lead attribution: the owner forwarded Fable's **static suspicion** about early payroll payment. Astra designed and executed the following independent public-RPC probes after that exposure. No blind-discovery credit is claimed.

## Exact reproduction and observed harm

1. Create an ordinary daily worker, post real attendance for **13 October 2026**, and PREPARE/APPROVE the resulting payroll for **1000.00**. The real `PAYROLL_ATTENDANCE_ACCRUAL` posts on 13 October. No source liability exists for this contractor on 12 October.
2. Through `public.erp_cp7_save_payroll_installment_v1`, request a partial ordinary payroll payment of **375.25 dated 12 October**, using the current source/review/version/cash tokens.
3. The command returns `COMMITTED_OUTCOME`, `payment_state:PARTIAL`, native payroll status `APPROVED`. It creates `PAYROLL_INSTALLMENT` on **12 October**. The contractor's payable at that cutoff becomes **−375.25**; there is no cash-advance/credit source accounting for it.
4. The same public financial report at 12 October changes cash **0.00 → −375.25**, assets and liabilities **1759.00 → 1383.75**, while `balance_difference` remains **0.00**. The future attendance cost is still not recognized at that date. This correctly balanced journal therefore silently lowers the dated liability before it exists.
5. `erp.run_integrity_checks()` has **zero nonzero issues before and after** this mutation. All per-case database/public-catalog boundaries restore, with no session/advisory-lock leaks. This evidence does not assert that every separate financial/advisor detector or every UI warning was tested; it proves the command acceptance, dated liability/report effect, and lack of a core-integrity alarm.

Witness **CP17-ASTRA-PAY-06-DATED-PARTIAL**, run **38527771239**, job **115732095969**, attempt 1. Source `audit/astra_cp17/cases_integration.py`; complete Original `ASTRA_CP17_PAYROLL_DATED_PARTIAL_FIRST.json` and `CP17_OWN_CASES_INTEGRATION.json`. Artifact **11876618228**, SHA-256 `e496b632efb97260846eff11b7ac5da79f327c2f4ee3bb154b1e5eb027e2f4b6`. The job is red because the business oracle fails; installation, restoration and advisor gates pass.

Two earlier independent first-execution witnesses corroborate both routes in run **38525930407**, job **115726145641**:

- **PAY-04-EARLY-FULL:** native attendance100 on 14 October plus existing work6000; the public ordinary PAY accepts6100 dated13 October. The original accrued attendance remains14 October.
- **PAY-05-EARLY-INSTALLMENT:** attendance1000 accrued13 October; the installment command accepts final1000 dated12 October.
- **PAY-01-CONTROL:** same-day ordinary payment6100 posts exactly one attendance accrual100 and one cash settlement6100. A legal positive path therefore succeeds.

Artifact **11875608786**, SHA-256 `d35992b0c8d79f186054e30bad7944218640ed8373083e0501b6a44736ff3ba8`. The original responses and raw COUNTEREXAMPLE statuses are retained unchanged. No failed business case was rerun to obtain a green result.

## Source and causal chain

- `scripts/cp7-src/payroll/settlement-write.sql`, PAY branch around lines90–93: copies the user payment date, then invokes the native payment function.
- `scripts/cp7-src/payroll/installments.sql`, PAY branch around lines295–318: validates date syntax and not-future, but does not validate earliest accrual/source date; both partial and final branches post cash against CONTRACTOR_PAYABLE.
- `scripts/cp7_installment_bundle.py`, `derive_payment`: derives both `check_payment` and `final_payment` from the accepted native function, so its date omission is inherited.
- `supabase/migrations/20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql`, approve/payment bodies around lines367–375 and429–447: attendance is recognized at period end, whereas the payment date is checked only against the future plus existence/amount of an accrual, not its temporal availability. The effective candidate body is also retained in the P00 catalogue and verified at runtime through FULL composition.

The original CP3 contract explicitly makes payroll payment **settlement-only**. This witness is not a documented advance entry, timezone rollover, stale response, hypothetical direct SQL corruption, or a late source known only to the auditor. It uses the ordinary public command and its own accepted source tokens. Negative test-bank cash is incidental; the decisive defect is the same contractor's negative dated liability and its reduction of reported liabilities.

## Recommended correction and acceptance

Enforce dated availability of the source liability at the owning native payment boundary, for ordinary full payment, partial installments and final installments. Keep current permission/version/idempotency locks, original economic dates and closed-period rules. A real advance must use an explicitly supported advance source with correct asset classification rather than debit a liability that does not yet exist. Do not edit historical migrations; implement a controlled forward correction.

Add a dated-payable detector and a failing-before/passing-after test for each of the three witnesses, plus positive same-day/later payment, separately declared advance, partial/final replay, reversed payments, reopened liability, and closed-period recognition. Test the exact transaction boundary atomically and confirm no command-context/payment rows survive a refused request. Retest the relevant UI/report flow after the fix. Until corrected and independently accepted, this finding blocks the full CP1–CP7 acceptance gate; it does not reopen the separate, already accepted CP7 A6/F-OPS-05 fixes.
