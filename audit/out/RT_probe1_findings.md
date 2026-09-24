# Runtime probe 1 — findings (INDEPENDENT_NATIVE_RERUN)

Run 36039753521 · job 107768697263 · head_sha 9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc · phase after
Scenario scen/rt_probe_1.py sha256 13b3b800900e55d5ae60d67baafffec6aa07216da76bf6b7a95534f42da0c33a (8775 bytes; runner printed the same hash first)
Job conclusion: success · run report status RUN_COMPLETE · auditor_cases status COUNTEREXAMPLE, counts {PASS:5, COUNTEREXAMPLE:1, OK:1} · primary_unchanged true · clone_remaining 0

## What the runtime proved about itself
- RT:IDENTITY PASS: auditor checkout head 9add57e, tree 5d5f833, no tracked file modified (only untracked cp6-proof/). Writer cwd head ca7f095 (baseline). sys.path[0..2] = writer/scripts (baseline scripts shadow auditor scripts of the same name). DB: cp6_rollback as supabase_admin, TimeZone UTC, today (Asia/Jakarta) = 2026-09-25 at 18:16 UTC, closed_through 2026-08-31, supabase_migrations tail ends 20260923110000 (AV); AW..AZ dev installs leave no supabase_migrations row (marker rows in erp.schema_migrations only). erp+public functions 673.
- RT:INSTALLED_BODIES_VERBATIM PASS: every CREATE OR REPLACE FUNCTION body in supabase/dev/cp6_a{w,x,y,z}_t1_family.sql (13+11+4+12 = 40) equals pg_proc.prosrc in the clone. This is an independent check that also covers AX, whose writer verifier (ax_verified) checks only a marker and the coverage assertion.

## Tooling findings
- RT-T1 (P3, TOOLING): a session-level advisory lock taken inside a case survives `rollback to savepoint` (RT:LEAK_CHECK COUNTEREXAMPLE: advisory_locks=1 after rollback; session GUC and temp table did not survive). A case (auditor's or writer's) that uses pg_advisory_lock can influence later cases in the same group; boundary.snapshot does not see it.
- RT-T2 (P2, TOOLING): duplicate case ids overwrite silently. Two cases with id RT:DUP_ID (first COUNTEREXAMPLE, second PASS): both JSON lines are printed, but report['cases'] and counts keep only the last (counts total 7 for 8 planned cases; the COUNTEREXAMPLE of the first occurrence is absent from counts). planned_case_ids is not compared with the case dict.
- RT-T3 (P3, TOOLING): an arbitrary status string ('OK') is accepted and counted as its own bucket; it neither fails nor completes the run. Only INCOMPLETE and FAIL make a run INCOMPLETE; COUNTEREXAMPLE keeps the job green. A reader must count statuses per case, never trust group PASS or job colour.
- RT-T4 (P2, TOOLING): a commit through a SECOND connection to the clone (create table public.cp6_audit_leak_marker + insert, autocommit) was not detected: the case still shows full_boundary_restored=true, the run ended RUN_COMPLETE and the job stayed green. boundary.snapshot does not cover objects outside its enumerated set. Whether it covers erp business tables is tested by probe 2.

## Limits
- Probe 1 did not test erp-table leakage or sequences; it did not test the T2/T3 runners (different scripts, same group() helper for T2).
