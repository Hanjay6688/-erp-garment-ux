# R1 — Akses dan pemulihan (candidate d0b9e9c2, static review)

Scope: all 197 `public.erp_cp7_*` facades in scripts/cp7-src (static, from `_inv.json` + source), the
correction/reversal command chain, locks vs. rights re-check, dynamic SQL. Work products:
`_r1_facades.json` (per-facade analysis), `_r1_table.txt` (facade | owner | secdef | callee | first rights check |
#checks | #writes | rc-before-write | locks | rc-after-lock | exc | dyn), `_r1_cmd_skeletons.txt` (command skeletons),
tool `tools/r1_analyze.py`.

Oracles used: 01_KONTRAK §16 "Apply memeriksa actor terbaru ... dan request payload setelah lock"; §17 "Reuse request
ID+payload"; 04_BUKTI L37 "repeat command key/payload sama satu effect; key sama payload beda atomically rejected";
04_BUKTI E12 (tab lain, same replay, no new UUID); 01_KONTRAK L77 "JWT sah tidak otomatis berarti izin".

## 1. Facade table (summary; full rows in _r1_table.txt)

Shape: every facade is a thin SECURITY DEFINER `language sql` wrapper (owner = a cp7_* principal: cp7_capture 66,
cp7_reminder 26, cp7_plan_writer 11, cp7_sales_read/write 7+7, ...; never postgres, never authenticated) calling one
internal `cp7_<x>.command/workspace/...`. Rights check is therefore in the callee, never in the facade body.

Static results over all 197:
- 197/197 callee paths begin with an access function (`cp7_<x>.access_now` / `*_access` / `recheck`) before any write
  (rcBeforeWrite=Y for all 60 writer callees; 0 rows with RC=-).
- 58/60 writer callees take a lock (`for update` on the request row, business rows and/or `pg_advisory_xact_lock`) and
  every one re-runs the access function after the lock (rcAfterLk=Y for all; 0 N). Two writers lock nothing:
  `cp7_analysis_stage.check_and_record` (analysis-stage-snapshot.sql:160, appends a source_checks row) and
  `cp7_procurement.command` SAVE_DRAFT/POST path (procurement/command.sql:2; locks and idempotency are delegated to Native
  `erp.save_material_purchase_draft_v2`/`erp.post_material_purchase_v2`, and `access_now` is re-run after they return,
  command.sql:58-59; REVERSE path locks in `reverse_receipt_locked`, reversal.sql:21-27).
- Grants: multi-line parse of every `grant/revoke` statement containing `erp_cp7_` plus the loop-style block in
  staged-reminders.sql:1062-1070: all 197 facades are `revoke all ... from public,anon,authenticated,service_role` then
  `grant execute ... to authenticated` only. Exceptions: 3 facades additionally granted to `postgres`
  (sales/chain-reversal.sql:209 save_sale_v1, sales/correction.sql:387 get_sales_v1, transactions/source.sql:319
  resolve_transaction_source_v1) so postgres-owned secdef commands can call them — harmless (superuser).
- Access roots (functions that do not delegate to another cp7 access fn), 30 of them: 26 check
  `auth.jwt()->>'role'='authenticated'` AND `erp.get_my_access_v1()` AND `erp.has_permission(<key>)` (permission keys,
  not just role names). Role_code (OWNER/ADMIN[/STAFF]) is checked IN ADDITION to permission keys, never instead.
  Exception: `cp7_reminder_native.other_access` (reminders/other-obligation-source.sql:20) = jwt role + get_my_access +
  role_code in (OWNER,ADMIN,STAFF) and NO permission key; but its only callers `other_obligation_source` (:285) and
  `condition_source` (rule-condition-source.sql:155 via `recheck` first) gate every data domain with has_permission
  (finance.ar.view / finance.ap.view / ...) at :288-290, so it is a coarse pre-filter, not the authorizer. Secondary
  roots `report_finance_access`, `condition_domain_access`, `other_accessory`, `staged_recheck_json` are only called after
  a full access_now in the same path (e.g. report-staged.sql:509→513).
- `erp.has_permission` (migrations/20260902104937:589) returns TRUE unconditionally for jwt role `service_role`. Every
  cp7 access root rejects jwt role != 'authenticated' first, so this shortcut is unreachable through the facade. Noted
  because any future access function that skips the jwt-role check would grant service_role everything.
- `erp.has_permission`/`get_my_access_v1` read erp.app_users/app_roles/app_role_permissions live (STABLE but called from
  VOLATILE plpgsql statements → fresh snapshot per statement under read committed), so re-checks after locks see
  revocations. This is why the writers add `if current_setting('transaction_isolation')<>'read committed' then raise
  'CP7_FRESH_ACCESS_REQUIRED'`.

## 2. Correction / reversal commands

All ten are one plpgsql function = one transaction (no COMMIT, no dblink, no autonomous call). Common skeleton:
isolation guard → `a:=access_now()` → field/version regex guard → `insert into <schema>.requests ... on conflict do
nothing` → `select ... for update` on that request row → payload/expected_version compare (→ *_REQUEST_CHANGED) →
`access_now() is distinct from a` (→ 42501 *_ACCESS_CHANGED) → `if old.response is not null then return old.response`
→ advisory lock / business `for update` → access re-check → business writes → access re-check → `update requests set
response`. Response is written in the same transaction, so a failure anywhere rolls back request row and business
rows together; a successful replay returns `old.response` before any lock/write.

| command | file:lines (req insert / replay return / business lock / rc after lock / rc after writes) | notes |
|---|---|---|
| cp7_note.command (correct_note_v1) | sales/correction.sql:215 / 219 / 220-226 / 222 / 364 | secdef owner postgres; nested Native `erp.save_sale_draft_v2` with derived UUID md5(actor:NOTE:request) :269-271; per-step `cp7_sales.command_access('PAYMENT_REVERSE'/...)` :263,266,276,309 |
| cp7_payment_correction.command | sales/payment-correction.sql:215 / 219 / in `apply` (:144; 2 for update + 1 advisory) / inside apply + :223 / :223 | request-row lock :216 then rc :217 |
| cp7_sales_return_correction.command | sales/return-correction.sql:308 / 312 / 316-326 / 330 / 385 | expected_version regex :307 |
| cp7_sales_chain.command | sales/chain-reversal.sql:125 / 129 / 131-137 / 144 / 176 | children via `public.erp_cp7_save_sale_v1` with derived child UUIDs :158,165,171; CP7_SALES_CHAIN_INCOMPLETE guard :175 |
| cp7_supplier_payment_correction.command | invoices/payment-correction.sql:207 / 211 / in `apply` (:139) / :215 / :215 | no expected_version column; review token inside payload validated by `validate` |
| cp7_invoice.reverse_payment_request | invoices/payments.sql:141 / 146 / `reverse_payment_locked` :107-113 / :114 / :120 | locked fn owner postgres, checks `payment_access()->reverse_payment` before+after lock |
| cp7_receipt_fix.command (correct_receipt_v1) | procurement/correction.sql:504 / 508 / 520-521,581,746,759 / 507 (req row), business rc at :1021 | 24 writes; two EXCEPTION blocks :533 (cast → re-raise 22023) and :996-1002 (translate two Native messages, else `raise;`) — nothing swallowed |
| cp7_procurement.reverse_request | procurement/reversal.sql:38 / 42 / `reverse_receipt_locked` :21 / :25 / :28 | isolation guard lives in caller `cp7_procurement.command` :5 |
| cp7_misc_correction.command | finance/misc-correction.sql:156 / 160 / in `apply` (:81; 3 for update) / :164 / :164 | shares `cp7_misc.requests` with save; `saved.action<>'CORRECT'` guard :159 |
| cp7_cutting_correction.command (reopen_cutting_v1) | cutting-correction/reopen.sql:98 / 102 / 103-104 / 106 / 116 | Native `erp.reverse_cutting_material_flow_before_sewing_v2(..., p_request, row_version)` :113; completeness check :119 |
| fg/corrected-book.sql, fg/corrected-ledger.sql | read-only (get_fg_book_v2 / get_fg_ledger_v2); access `book_access`/`access_now` first; no writes | |

Request key is `(actor, request_id)` everywhere: the same UUID from a *different* actor is a new request, not a replay.
Same actor, same UUID, different payload → `*_REQUEST_CHANGED` raised before any lock/write (04_BUKTI L37 satisfied).
Two tabs racing the same UUID: second blocks on the request-row `for update`, then sees `response` and returns it.

Capture/plan writers without a `requests` table (25, e.g. cp7_plan_native.apply, cp7_*_native.capture) use the request
UUID as the run/row key with an early "existing → return" branch (earlyReturn=True for 21/25); `check_and_record`,
`cp7_analysis_stage.request`, `staged_set_step`, `cp7_procurement.command` delegate or append-only. Not correction
paths; not probed further.

EXCEPTION blocks in facade-reachable writers (all re-raise or map to a declared state, none continue after a partial
business write): receipt_fix :533,:996; `cp7_reminder_native.obligation_evaluate` obligation-episodes.sql:83 (catches
only two named *_SOURCE_INCOMPLETE and records status INCOMPLETE — intended state, no business write precedes it);
`cp7_analysis_jobs.run`, `cp7_reminder_native.staged_set_step` catch `query_canceled` only (job-state bookkeeping);
`cp7_journal.workspace`:40, `cp7_misc.workspace`:84 cast guards in read paths.

## 3. Locks vs. rights re-check

Every `pg_advisory_xact_lock` / `for update` in a facade-reachable writer is followed by an `access_now()/payment_access()`
compare against the pre-lock value (`is distinct from a` → 42501 *_ACCESS_CHANGED). Verified by regex on all 60 writers
(rcAfterLk=Y, 0 N) and by reading the ten correction commands above plus `reverse_receipt_locked`/`reverse_payment_locked`.
The re-check compares the whole access JSON (actor, profile incl. row_version/role_row_version, permissions list), so a
role/permission change mid-transaction is detected, not only a revocation.

Isolation guard (`CP7_FRESH_ACCESS_REQUIRED`) — present in 50/60 writer callees or their access function. Absent in:
`cp7_period.command` (finance/period.sql:58), `cp7_recost.command` (finance/recost.sql:51),
`cp7_analysis_native.report_command` (planning/report-publication.sql:138), `cp7_reminder_native.obligation_evaluate`
(obligation-episodes.sql:56), `obligation_report_command` (obligation-report.sql:183), `rule_episode_evaluate`
(rule-episodes.sql:34), and `cp7_schedule_native.access_now` / `cp7_reminder_native.recheck` roots. Under REPEATABLE
READ the "re-check after lock" of these would read the transaction-start snapshot of app_role_permissions and miss a
revocation. PostgREST runs read committed and does not let the client raise isolation, so this is a defence-in-depth
inconsistency, not a reachable bypass over HTTP. Severity: low.

## 4. Dynamic SQL

`execute`/`execute format` inside cp7_* bodies: `cp7_analysis_stage.changes_since` (analysis-stage-snapshot.sql:78;
schema/table/columns come from the constant `cp7_analysis_stage.change_sources()`, `%I`-quoted, caller values bound via
USING; numbers derived from pg_snapshot args), `purge_intermediates`/`purge_expired`/`clean_done` (analysis-stages.sql
:2183,:2219,:2311; table names from a literal array, `%I`, job id via USING), and DDL loops in install blocks. No
facade-reachable function interpolates caller text into SQL. No injection surface found.

## 5. Native paths outside the facade touched by CP7

- `erp.require_internal()` is re-created in procurement/accepted-deltas.sql:9 (guarded by sha256 of predecessor
  functions). Normalised diff vs migrations/20260904111157: keeps the pre-existing early-returns for
  `session_user in (postgres,supabase_admin)` and jwt role `service_role`; adds three bypass clauses keyed on
  `cp7_procurement/cp7_material/cp7_supplier_return.execution_context` rows that must match (backend_pid, txid,
  actor=auth.uid(), jwt role 'authenticated', action→permission_key) AND live `erp.has_permission` — the context rows are
  only insertable by the cp7 command principals (schemas not reachable by authenticated, verified by auditor) and are
  deleted at end of command. The service_role early-return is Native/pre-existing, not introduced here.
- `public.erp_save_supplier_credit_v1` / `erp.bf_supplier_credit_allocate_v1` (procurement/supplier-credit-authority.sql
  :11,:37): CREATE OR REPLACE of a CP6 public RPC (sha256-pinned predecessor). Body: isolation guard, `erp.require_owner_admin`
  + `erp.require_permission('finance.ap.pay')` before the advisory lock, after it, after `for update`, and after all
  writes; idempotent via `erp.bf_requests_v1` (replay → `replayed:true`, payload mismatch → CLIENT_REQUEST_ID_CONFLICT).
  No grant/revoke statement for either function exists in supabase/migrations or scripts → ACL is whatever the CP6
  release left (CREATE OR REPLACE preserves it). Cannot be determined statically; probe P9.

## 6. Runtime probes (psycopg, style of scripts/cp7_snapshot_cases.py `actor()`)

Setup: `admin(cur)`; `actor(cur, subject, role)` = set request.jwt.claims + `set local session authorization <role>`.
Pick one facade pair per family; suggested: `public.erp_cp7_correct_sales_payment_v1(p jsonb,p_request uuid,p_expected text)`
and `public.erp_cp7_reverse_supplier_payment_v1`.

P1 service_role EXECUTE revoked: `actor(cur, OPERATOR, 'service_role'); select public.erp_cp7_get_sales_v1('{}')`
   → SQLSTATE 42501 "permission denied for function erp_cp7_get_sales_v1". Repeat with role 'anon' → 42501.
P2 service_role via a role that CAN execute (defeat P1 by `set local session authorization authenticated` but claims
   role=service_role, sub=OPERATOR): → 42501 message CP7_ACCESS_DENIED / CP7_SALES_ACCESS_DENIED (jwt-role check in
   access root, has_permission's service_role shortcut never reached).
P3 Fresh-access guard: `begin isolation level repeatable read; actor(...); select public.erp_cp7_correct_sales_payment_v1(...)`
   → P0001 CP7_FRESH_ACCESS_REQUIRED. Same under repeatable read for `erp_cp7_save_period_control_v1('CLOSE',...)` →
   EXPECTED TO NOT REFUSE on isolation (confirms §3 gap; it will fail later on payload/version instead).
P4 Replay: valid correction with UUID u, payload p, expected v → r1 (kind COMMITTED_OUTCOME). Call again identical
   → r2 = r1 byte-identical; `select count(*) from erp.sales_payments where sale_id=...` and from
   `cp7_payment_correction.requests`/`links` unchanged between calls; no new audit_logs row.
P5 Same u, payload p' ≠ p → P0001 CP7_SALES_REQUEST_CHANGED; requests row still holds p; no business row added.
P6 Same u, different actor → executes as a new request (expected by design, (actor,request_id) key) — document, not defect.
P7 Revocation between tabs: as admin `delete from erp.app_role_permissions where role_id=<ADMIN role> and permission_key='sales.payment.create'`
   (or the key the family's access_now lists), then `actor(cur, ADMIN_SUBJECT); select ...correct_sales_payment_v1(...)`
   → 42501 CP7_*_DENIED. Restore permission afterwards.
P8 Role-only root: STAFF user with no finance.* permissions → `erp_cp7_get_rule_conditions_v1(...)`: returns without
   42501 but AR/AP/payroll rows empty and coverage flags false (has_permission gates per domain at
   other-obligation-source.sql:288-290). A non-empty obligation row for that user = defect.
P9 Supplier credit ACL: `actor(cur, STAFF); select public.erp_save_supplier_credit_v1('{}', gen_random_uuid())` →
   42501 (either "permission denied for function" or PERMISSION_DENIED: finance.ap.pay). `select
   erp.bf_supplier_credit_allocate_v1('{}',gen_random_uuid())` as authenticated → 42501 permission denied for function
   (schema erp has no USAGE for authenticated). Also `select has_function_privilege('authenticated','public.erp_save_supplier_credit_v1(jsonb,uuid)','execute')`.
P10 Concurrency: two sessions, same actor, same u, same payload; session A `begin; select correct...` (hold), session B
   same call → B blocks on `requests` row lock; after A commits B returns A's response and writes nothing.
P11 Partial-failure atomicity: inject failure after business writes (e.g. make `cp7_note.revisions` insert fail via a
   temporary unique violation) → whole call rolls back; `cp7_note.requests` has no row for u; replay later executes fresh.

## 7. Could not determine statically
- ACL of `public.erp_save_supplier_credit_v1` / `erp.bf_supplier_credit_allocate_v1` (no grant text in repo).
- Whether UI reuses the same request UUID after a lost reply across tabs (E12) — frontend out of scope here.
- Owner of `cp7_receipt_fix.command` not captured in _inv.json (set by loop at procurement/correction.sql:1057 → postgres);
  confirm with `select proowner::regrole from pg_proc where proname='command' and pronamespace='cp7_receipt_fix'::regnamespace`.
- Latest Native `erp.require_internal` version (20260915031500 adds laundry reverse actions) vs CP7 copy: diff shown is
  against 20260904111157; re-diff against the latest before judging the laundry clauses.
