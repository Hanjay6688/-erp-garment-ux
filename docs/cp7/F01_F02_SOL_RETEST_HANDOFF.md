# CP7 F01/F02 independent retest handoff (Sol)

- Frozen writer source: `ee8699829bc53799e5f840bb5490059e456fa81a`.
- Auditor branch: `audit/cp7-f01-f02-sol-retest-20260929`; probe: `scripts/cp7_f01_f02_sol_retest_probe.py`.
- Native disposable run: https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36562582231 (job 109386719537; artifact 11029983803).
- Result: four independently authored cases PASS; missing cases zero. CP6 boundary and public schema restored after each case. T3 package gates installed, primary unchanged, backup/restore, security advisors, and runtime all true. This is an execution result, not CP7 final acceptance or production GO.

## Independent oracles and results

| Case | Oracle | Observed |
| --- | --- | --- |
| `SOL_F01_FINANCE_REVOCATION_STALE` | Capture with financial permission; revoke; operational read must redact cost and cost read must deny. Mutate sales quantity and check old archive. | PASS: cost denied, count redacted, source `ARCHIVED_STALE`, captured sale remains 2 PCS. |
| `SOL_F02_MATCH_RECOMPUTED` | Compatible RED→RED is feasible; preserve a forged `CANDIDATE_MATCH` edge while target fact becomes BLUE; change label or snapshot; omit matching. | PASS: compatible feasible; contradictory FACT, forged label, old snapshot denied; legacy label-only returns `UNKNOWN/MATCHING_FACTS_REQUIRED`. |
| `SOL_F02_MATCH_REF_INTEGRITY` | Alter source revision refs, target edge revision refs, duplicate source key, or omit target. | PASS: binding, duplicate and missing fact refusals. |
| `SOL_F02_CANCELLED_BS_NEW_SOURCE` | Existing posted QC gives input/WIP/FG/BS 100/80/15/5. Reverse source and cancel BS; inject a new active 7 GOOD + 3 BS; negative control cancelled BS with live source. | PASS: 100/100/0/0 after reversal, then 100/90/7/3, negative control CONFLICT; archived run unchanged. |

The cancellation metamorphosis uses captured ordinary posting facts and exercises the private normalizer with altered JSON facts. It is not an independent public posting of a second QC event. Writer's separate native suite covers its own public route. The matching probes exercise the private kernel, where source/target JSON is an input. They prove the kernel recomputes and binds supplied facts; they do not prove the future P06/P07 public transport obtains current facts on the server under the acting user's authority.

## Writer action

1. Preserve the repaired `match_target` recomputation and snapshot/ref binding in P06/P07. Assemble matching facts server-side from the same immutable capture and enforce actor/role authorization before allocation. Test a real Auth/HTTP request with a forged target fact, a revoked actor, and a changed target revision; reject or return UNKNOWN without publishing a feasible allocation.
2. Keep cancelled BS in captured dependencies for staleness, but suppress its physical slice only when its exact linked QC/receipt source is REVERSED. The unproven cancellation must stay CONFLICT/UNKNOWN.
3. Record this as bounded independent **PASS for four additional F01/F02 seams**. Do not convert to unconditional F02/CP7 acceptance: P06/P07 assembly and integration remain OPEN in the handoff, and no production GO was exercised.
4. Merge only the auditor probe/workflow/handoff after reviewing the draft PR; no writer application source is modified on this branch.

Previous independent X06 reproducer on the old candidate: https://github.com/Hanjay6688/-erp-garment-ux/pull/34 . This retest verifies that exact failure path is closed on the frozen writer repair.
