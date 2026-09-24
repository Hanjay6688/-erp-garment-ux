# Runtime probe 2 — findings (INDEPENDENT_NATIVE_RERUN)

Run 36040954954 · job 107772716244 · head_sha 9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc · phase after
Scenario scen/rt_probe_2.py sha256 cd6df40c868afefa9023c84d6c4f284f3b79d4abaa63907d66101b8395d82789 (5010 bytes)
Job conclusion: failure (by design: the last case issues COMMIT). Run report: status INCOMPLETE, error `savepoint "r1_case" does not exist`, auditor_cases null, primary_unchanged true, clone_remaining 0.

## Results per case
- RT2:MODULE_ORIGINS PASS (informational): with cwd=writer (baseline ca7f095) first on sys.path, these helper modules are imported from the BASELINE checkout, not from the candidate 9add57e: cp6_ao_ap_installed, cp6_successor_regression, cp6_au_runtime, cp6_au_trial, cp6_au_browser_fixture, cp6_v2620al_import_review, cp6_ac_independent_audit, cp6_successor_specs, cp6_as_cases, cp6_at_cases, cp6_au_cases. The probe modules (cp6_aw/ax/ay/az_probe, cp6_au_r1_probe, cp6_av_runtime) come from the candidate. `cp6_au_browser_fixture.py` differs between baseline (blob 6534e20f) and candidate (blob f8bc9676): whichever CI job imports it with writer cwd runs the BASELINE version (to check: T3 browser job, cp6_t3_browser.py).
- RT2:SEQ_ARM / RT2:SEQ_CHECK PASS (informational): erp.audit_logs_id_seq advanced 222→223 across the rolled-back case (PostgreSQL never rolls sequences back); boundary.snapshot did not flag it (full_boundary_restored=true). Sequence values are a leak channel the harness ignores (harmless for business assertions unless a case asserts sequence values).
- RT2:ERP_LEAK_SECOND_CONNECTION INCOMPLETE with full_boundary_restored=false: a committed erp.contractors row through a second connection IS detected by boundary.snapshot (the case is forced INCOMPLETE). So the snapshot covers erp business tables; probe 1 showed it does not cover new objects in `public`.
- RT2:ERP_LEAK_VISIBLE_NEXT COUNTEREXAMPLE: the leaked row is visible to the next case (rows_visible=1); the runtime flags but keeps running, so every case after a leak runs on polluted data (their results must be discounted).
- RT2:COMMIT_ON_CASE_CONNECTION_LAST: a plain COMMIT on the case connection destroyed the group savepoint; the runner's `rollback to savepoint r1_case` failed and the whole run ended INCOMPLETE (job red). Fail-closed: a case cannot commit and still look PASS.

## Refined tooling findings (supersede RT-T4 of probe 1)
- RT-T4a (P3, TOOLING): boundary.snapshot covers erp tables (detected) but not objects created in `public` (undetected in probe 1). An auditor/writer case that writes outside the enumerated set can look PASS.
- RT-T4b (P3, TOOLING): after a detected leak the group continues; later cases inherit the leak.
- RT-T5 (P2, TOOLING/PROTOCOL): 11 helper modules are taken from the baseline checkout because writer/scripts precedes auditor/scripts on sys.path; for modules that changed in the candidate (cp6_au_browser_fixture.py) CI may test the baseline helper instead of the candidate's. Impact on T3 browser evidence to be checked (F-REL / F-T2 readers).
