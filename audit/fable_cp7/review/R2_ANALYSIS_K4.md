# R2 — Staged analysis 5,000 / Snapshot v2 / K4 runner — source review of d0b9e9c2 (read-only)

Paths relative to the candidate checkout. S = scripts/cp7-src/planning/analysis-stages.sql,
SN = scripts/cp7-src/planning/analysis-stage-snapshot.sql, HS = scripts/cp7-src/planning/history-source.sql,
OPS = scripts/cp7-src/ops/schedule.sql.

## 1. 5,000 cap
- Declared once: `bounds()` S:1385-1391 (`job_targets` 5000, `job_matching_products` 10000, `page_utf8_bytes`/`header_utf8_bytes` 8000000).
- `request()` S:2045-2077: ONE statement `cp7_analysis_native.source_within(5000,10000)` (S:2064); chain analysis.sql:5-7 → netting.sql:9-11
  `cp7_schedule_native.source_within(p_products)` → baseline-source.sql:20 `cp7_planning.history_source_within(p_products)` (HS:6-108), which reads
  `limit p_products+1` (HS:30) and sets `status` INCOMPLETE when products > p_products (HS:103) — facts are still returned.
- `create_job` S:1449-1460 stores the reference unconditionally (targets_total null when > cap); `capture_marks` S:2075.
- Refusal only at unit 0: `history_prep` S:129 `CP7_PLANNING_CAPTURE_INCOMPLETE` (status check precedes S:130 `CP7_ANALYSIS_STAGED_TARGET_LIMIT`, which is
  unreachable from request(): COMPLETE implies products ≤ p_targets). `step()` S:2020-2022 → FAILED, failure_code = SQLERRM.
- Cap applies to the operational product universe (one product per size = one target), not to the query. Same cap on every entry: only one request RPC
  (`erp_cp7_request_staged_analysis_v1` S:2456); AI/report/plan readers consume DONE runs (no second cap path found; `job_targets` referenced only in S).
- Same-UUID semantics: S:2056-2060 (same query → same job status; different query → CP7_ANALYSIS_REQUEST_CHANGED; UUID owned by single capture/analysis job →
  REQUEST_CHANGED S:2061-2063). UI keeps the UUID in localStorage (src/nativeStagedJob.ts:72-96) and resumes with get() (driveStagedJob :137-150).

## 2. 8 s / unit
- Page path: the statement limit is the role's existing `statement_timeout` (P19_STAGED.json statement_timeout: "existing 8s authenticated limit"); nothing in S sets it.
- K4: `run_next` S:2401-2406 reads `pg_settings.statement_timeout` (ms) and refuses unless 1..8000 → 55000 `CP7_RUNNER_STATEMENT_LIMIT_REQUIRED`.
  Set by the pg_cron command string `set statement_timeout to '8s'; begin; select cp7_ops.analysis_tick(); commit; ×60` (OPS:51-53).
- Breach: `step()` S:2004-2023: run_unit + outputs insert + progress update inside a BEGIN/EXCEPTION block (subtransaction) → `when query_canceled`
  rolls the unit's rows back, `unit_attempts+1`, 3 → FAILED `CP7_ANALYSIS_STAGE_STOPPED` (failure_sqlstate 57014). `when others` → FAILED immediately
  (CP7_* message kept as code, else CP7_ANALYSIS_STAGE_ERROR). Partial unit never stored (same block).

## 3. 8,000,000 B / page
- Cut: `page_cuts` S:1507-1522 over stored fragment sizes (`utf8_bytes+2` per target, budget = 8,000,000 − 4096 envelope reserve); a single target over
  budget → `CP7_ANALYSIS_PAGE_BODY_LIMIT`.
- Measured: `octet_length(page::text)` of the finished page body S:1671 (→ CP7_ANALYSIS_PAGE_BODY_LIMIT, job FAILED via when-others), stored with sha256 S:1672-1673;
  table check `utf8_bytes between 1 and 8000000` S:1327 (pages), S:1321 (headers); header S:1933 `CP7_ANALYSIS_PAGE_HEADER_LIMIT`.
- Client re-measures: nativeAnalysisPages.ts:83,105 (byteLength == utf8_bytes, sha256 == hash).

## 4. identity_hash
- `PAGE_INDEX` S:1700-1705: sha256(header_sha256 || '\n' || page sha256s joined '\n' by idx), after layout checks S:1685-1699; written last (page_sets).
- Served: `page_set` S:2128, `page` S:2153 (also header_sha256); `access_epoch` = sha256(access json) S:2128; `page()` refuses other epoch S:2141 (42501
  CP7_ANALYSIS_ACCESS_CHANGED). Not recomputed on read (trusted stored value); recomputed by `verify_final` S:2299-2301 and `clean_done` S:2336-2339.
- Client: stagedIdentityHash nativeAnalysisPages.ts:60, page check :147, freshness bound to identity_hash :224.

## 5. Unit exclusivity
- `step()` S:1995 `select … for update skip locked`; locked → status + worker_active true, nothing run (S:1996-1999). `run_next` S:2419 oldest RUNNING
  `for update skip locked` (LIMIT after LockRows → skips a page-held job and takes the next). Both hold the job row to commit; `outputs` PK (job_id,idx)
  S:1304; units_done read after the lock. No window for two drivers on one unit. Page UI polls get() every 2 s while worker_active (nativeStagedJob.ts:146).

## 6. Rights per unit without login
- `run_next` S:2421-2424: `set_config('request.jwt.claims', {"sub":actor,"role":"authenticated"}, true)`, claim.sub/claim cleared; `cp7_schedule_native.access_now(false)`
  (schedule.sql:26-34 → cp7_private.access_now snapshot/bootstrap.sql:37-56: auth.uid()/auth.jwt() role, erp.get_my_access_v1 allowed, 4 view permissions;
  all refusals 42501 CP7_ACCESS_DENIED). insufficient_privilege → a={"denied":…} (S:2425-2426) → step(j,a) → differs from access_at_capture → FAILED
  CP7_ANALYSIS_ACCESS_CHANGED (S:2001-2004). Re-read after the unit (S:2429-2431): changed → raise → subtransaction rollback discards the unit; prior identity restored S:2434-2435.
- Actor row deleted/inactive: erp.get_my_access_v1 returns allowed=false (supabase/migrations/20260902104937…:663-679) → CP7_ACCESS_DENIED 42501 → FAILED. Covered.
- Residual: any NON-42501 error from access_now propagates out of run_next (only insufficient_privilege is caught); the tick aborts without changing the job,
  which stays the oldest RUNNING → every later tick reselects it → other jobs starve. Not observed in the reviewed code paths; hardening note (D3).

## 7. Blocking paths
- Heartbeat SOL-K4-01 fix: S:2414-2418 `pg_try_advisory_xact_lock(hashtextextended('CP7:K4_RUNNER_HEARTBEAT',0))` guards the single-row
  `insert … on conflict do update … where older than 10 s`; the lock is held to transaction end so only one writer per instant; others skip. Cold two ticks: fine.
- Remaining waits: (a) `request()` S:2054 `pg_advisory_xact_lock` per actor+request (double submit of the same UUID waits; by design).
  (b) `clean_done` S:2325-2331 and `purge_expired` S:2235-2248 run `ALTER TABLE … DISABLE/ENABLE TRIGGER` on outputs/target_rows/pair_rows/pair_lists/fragments
  (and pages) — SHARE ROW EXCLUSIVE held until the surrounding transaction commits: `clean_pending` S:2353-2372 (up to 5 jobs, one transaction, lock_timeout 2 s
  only for the cleaner's own waits), `purge_expired` (up to 200 jobs, one transaction, NO lock_timeout, NO busy guard). A concurrent unit's INSERT (page step or
  tick) waits on these → consumes the 8 s → query_canceled → unit_attempts++ (3 consecutive minutes → FAILED). clean_pending defers while any RUNNING job
  progressed in the last 10 min (S:2357-2360), purge_expired (retention_tick 19:30 UTC daily) has no guard. (D2)
- Denied job: FAILED in the same tick (S:2001-2004) → leaves the RUNNING set → never reselected. OK.

## 8. DONE reopen
- step after DONE/FAILED returns status only S:1999; get() never runs a unit S:2092-2103; page_set/page read stored rows only S:2111-2155 (no erp.* read;
  source check is separate S:2159-2175). Retention gate `require_kept` S:1412-1420 (7 days, CP7_ANALYSIS_RESULT_EXPIRED). No recompute path found.

## 9. Snapshot v2 freshness
- Not category hashes: `changes_since` SN:85-130 counts rows per tracked table (SN:38-72 list) whose recording-time column > captured_at OR whose xmin is not
  visible in the capture's `pg_snapshot` (capture_marks S:1336, written S:2069-2075), plus audit_logs DELETE entries; `freshness` SN:138-166 states
  STALE_VERIFIED / VERIFIED_SAME (last check UNCHANGED and 0 rows after check) / CHANGES_RECORDED / NO_RECORDED_CHANGE; `data_as_of` = captured_at.
  `check_and_record` SN:172-182 persists each full check with its snapshot.
- UI texts (src/NativeStagedAnalysisView.tsx): :40 "Data per <t>; …", :26-31 stagedFreshnessText — VERIFIED_SAME "Sama dengan data per <check t> (Cek sumber).
  Belum ada perubahan tercatat sesudahnya."; STALE_VERIFIED "Data sudah berubah (Cek sumber <t>); hasil ini tetap analisis per <data_as_of>."; CHANGES_RECORDED
  "… ada N perubahan tercatat; hasil ini tetap analisis per …"; NO_RECORDED_CHANGE "Belum ada perubahan tercatat sejak data diambil. Belum dicek penuh; tekan Cek sumber
  untuk memastikan."; fallback :46 "Cek sumber <t>: sama dengan data saat itu / data sudah berubah." Per-category list :43. The word "terkini" does not occur in
  NativeStagedAnalysisView.tsx / nativeAnalysisPages.ts / nativeStagedJob.ts (grep); CSS class `native-demand-current` (green colour only, native-demand-history.css:8)
  is applied for VERIFIED_SAME — a class name, no visible wording. Client re-derives the state and fails on mismatch (nativeAnalysisPages.ts:240-241).
- "boleh ditutup": only in STAGED_SERVER_TEXT nativeStagedJob.ts:117, appended only when `serverRunner?.active` (:116; paused text :119-121; label :122);
  `active` = heartbeat within 2 minutes (S:1438-1439). Other "boleh ditutup" hits (FinancePages/ConnectedFinanceReportPage) are unrelated finance wording.

## 10. K7a
- One implementation: `history_source_within(p)` HS:6-108 (K7 comments HS:9-10, HS:84); `history_source()` = within(1000) HS:110-113; staged passes 5000.
  `check_source` S:2169 uses the same `source_within(5000,10000)` + `fingerprint` as request S:2064 → same output by construction. No slow path remains in product
  and no in-product equivalence check; equality rests on tests (P19G_STAGED_EQUALS_SINGLE / same_as_single).

## Not determined from source
- Real value of `authenticated` statement_timeout; pg_cron per-statement timeout behaviour on the real instance (installed=false in K4_RUNNER.json).
- Whether `erp.has_permission` can raise a non-42501 error for an unknown user (only its head read); whether cp7_capture holds EXECUTE on it (migration grants service_role only).
- Runtime equality of staged vs single output (tests only).
