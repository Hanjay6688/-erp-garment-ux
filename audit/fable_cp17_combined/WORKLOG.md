# Fable cp17c work log (candidate dfab13bf, tree 886f8331)

Working notes per checkpoint; the locked reports are RETEST_FABLE_dfab13bf.md and FINAL_FABLE.md.
Status read per case from JSON log lines (SP/wf/case_summary.py), never from job colour.

## Runs dispatched 15 Oct 18:17–18:20Z on claude/new-session-deapao head 65628336 (product tree = dfab13bf; only docs differ)

| Run | Workflow | Per-case result | Label |
|---|---|---|---|
| 38784255332 | CP7 CP17 Fixes | 41 native + 4 races + 6 HTTP + 10 browser = 61 PASS, 0 other | INDEPENDENT_NATIVE_RERUN |
| 38784311913 | CP6 T3 Rollback | 148 checks PASS, 0 FAIL | INDEPENDENT_NATIVE_RERUN |
| 38784330868 | P18 Full Cycle | 2 PASS | INDEPENDENT_NATIVE_RERUN |
| 38784350980 | P12 Payroll (3 jobs) | PASS lines: roster 103, attendance-write 121, review 80; no FAIL/COUNTEREXAMPLE/INCOMPLETE | INDEPENDENT_NATIVE_RERUN |
| 38784369800 | P12 Nota | opening payroll 5+2+1+2 PASS | INDEPENDENT_NATIVE_RERUN |
| 38784388068 | F03 E05 installments | 20+3+1+2 PASS | INDEPENDENT_NATIVE_RERUN |
| 38784446800 | Supplier payment correction | 14+4+3+2 PASS | INDEPENDENT_NATIVE_RERUN |
| 38784464552 | Supplier payment create | 4+3+1+2 PASS | INDEPENDENT_NATIVE_RERUN |
| 38784483635 | P13 Period | report 8+1+1+2, period 8+2+1+2 PASS | INDEPENDENT_NATIVE_RERUN |
| 38784501713 | Cutting correction | 10+4+3+2 PASS | INDEPENDENT_NATIVE_RERUN |
| 38784274269 | CP6 T2 Combined Regression | all 3 jobs died before any case: `gh: Artifact has expired (HTTP 410)` | NOT_APPLICABLE (see below) |
| 38784292945 | CP6 T3 Release Package (3 jobs) | PASS lines: pins 32, browser 64, writer runtime 173; 0 other | INDEPENDENT_NATIVE_RERUN |
| 38784428651 | Owning receipt correction | 77 PASS, 0 other | INDEPENDENT_NATIVE_RERUN |
| 38784519618 | Native payment correction | 57 PASS, 0 other | INDEPENDENT_NATIVE_RERUN |
| 38784537309 | F03 connected cash reader | 56 PASS, 0 other | INDEPENDENT_NATIVE_RERUN |
| 38784556107 | Pre-freeze UI regression | 64 PASS; 2 INCOMPLETE only in group `AUDITOR_BROWSER_CP7_PREFREEZE_LEGACY_RUNTIME_GAP` (finance readiness screen on the legacy runtime: `erp_cp7_get_recost_queue_v1` PGRST202 404); the same two cases PASS on the full stack | INDEPENDENT_NATIVE_RERUN; gap = LEGACY_RUNTIME_OBSERVATION_ONLY |
| 38784408935 | Note correction | in progress at the time of this note | — |

Install consequence of the legacy gap: the CP7 UI must not reach Enteng before the CP7 database layer it calls
(the finance readiness screen breaks with a 404 on a legacy database). Goes to the "before Enteng" list as an order rule.

D14-17 pre-U inventory: every rebuilt chain read above logs `PRE_U_CAPTURED_IN_THIS_REBUILD` with names_sha256
`eb7f121d…` = the pinned value (cp17fixes, t3-rollback, p18, p12-nota, cutting). No business-day retry in these logs.

Supabase security advisors (T3_SECURITY_ADVISORS, REVIEW_REQUIRED, every chain): 73 → 216 lints; all 143 added are
`rls_enabled_no_policy` INFO (RLS on, no policy = closed to API roles), none WARN/ERROR, none removed. Consistent with A3.

T2: cp6-t2-regression.yml checks out pinned CP6 refs (ca7f0955 / c6b0e4fb / 25fa4736 / 1bdca376), not the
candidate, and is one of the 37 old CP6 workflows the writer lists as no longer runnable (GAPS_D14_14 §3a "Batas").
Confirmed: run 38784274269 stops at the archive download in all 3 jobs. T2 therefore says nothing about dfab13bf and
is not counted as candidate evidence either way. Historical T2 evidence on 0b7049d9 stays as recorded in v1.0.

## Fable own runs

| Run | Head | Scenario | Result |
|---|---|---|---|
| 38784599005 | 99b43ba5 | fable_cp17_chain | AUDITOR_TOOL: died before any case, HTTP 410 on the expired AC archive (my workflow still had the hard download line) |
| 38784617586, 38784635065, 38784653182, 38784671018 | 99b43ba5 | chain2, chain4, rbac, smoke | same workflow defect; logs kept, not evidence |
| 38785788908, (rbac2) | 7181d3c4 | cash_basis, rbac2 | same workflow defect; logs kept, not evidence |
| 38786127478 … 38786227211 | 844017982 | chain, chain2, chain4, rbac, rbac2, smoke, cp17c_cash_basis | rerun after the one-line workflow fix (writer's D14-17 fallback line, verbatim); the only rerun allowed (job died before cases) |
