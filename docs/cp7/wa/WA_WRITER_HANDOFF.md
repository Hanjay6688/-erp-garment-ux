# WhatsApp forwarding writer handoff (living checkpoint)

Owner decisions D17-3..D17-6 (`docs/cp7/OWNER_DECISIONS_20261008.md`): every reminder forwarded to the owner's WhatsApp
through CallMeBot, a twice-daily summary, built now and tested against a fake CallMeBot; no real message, no real number or
key, no installation (CP7C held, D13-9a). Design: `docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md` (v2: separate module
`cp7_alert_native`). Work on `claude/new-session-deapao`, one piece per commit; the last commit touching this file is the
checkpoint.

## Rules that stay in force

- Owner reports in plain everyday Indonesian (CLAUDE.md); follow `docs/ERP_BEST_PRACTICES.md`.
- Never mutate main, Cloudflare, hosted Enteng, legacy ERP-Garment, production. Never ask for or store a real phone number
  or CallMeBot key; tests use `+620000000000` and `FAKEKEY*` against the fake server only.
- Do not change the reminder module's behaviour or loosen its verifiers; the WA module is separate.

## Plan

| Step | Content | State |
|---|---|---|
| WA-0 | CI stack facts: pg_net, Vault, pg_cron, fake CallMeBot on the stack network, pg_net serving a second database, rollback sends nothing | done (run 39266618659) |
| WA-1 | Map install/test path (done: see below) | done |
| WA-2a | `scripts/cp7-src/alerts/alerts.sql` + `scripts/cp7_alert_bundle.py`: schema `cp7_alert_native` (role `cp7_alert`), settings, alerts, outbox, dispatches, Vault key, ticks, public RPCs; sources: owner's manual reminders, fabric below minimum, AR/AP due | done (local PG16 smoke, see below); CI in WA-3 |
| WA-2b | Analysis-based kinds (PRODUCTION_GAP, FABRIC_NEED; ACCESSORY_NEED not forwarded: no live recheck exists) from the owner's latest DONE staged run + automatic owner analysis; job `erp-wa-analysis` | built; local PG16 smoke with stubs PASS; CI with WA-3b |
| WA-3 | Bundle `scripts/cp7_alert_bundle.py` (previous = reminder v2), reachability, cases (Native/race/HTTP), declaration JSON, suite in the probe, fake server in CI | WA-3a PASS; WA-3b 21 cases, CI running |
| WA-4 | Reminder menu: Pengingat sistem + tab Sambungan WhatsApp (owner); browser cases desktop + phone | todo |
| WA-5 | Docs, best practices, owner report; then the r6 candidate for Fable/Astra/Sol (with Sol's five test-hardening points) | todo |

## Facts found (WA-1 mapping, 19 Oct)

- Reminder SQL loads through `cp7_reminder_bundle` → `cp7_rule_source_bundle` → `cp7_other_obligation_bundle` →
  `cp7_obligation_report_bundle` → `cp7_reminder_v2_bundle` (top). Probes install `candidate.extension()` in one statement
  (`cp7_f05_analysis_probe.py:280`); uninstall = originals replay + `drop owned by` each ROLE + catalog/advisor equality.
- `cp7_bundle_reachability.py` fails on any cp7-src SQL file the composition does not read.
- The reminder verifiers pin: function list of `cp7_reminder_native`, one trigger per staged/rule table, `cp7_reminder` reads
  only `erp.manual_reminders`, `staged_claims.environment='LOCAL_TEST_SINK'` only. Hence the separate module.
- Reminders are computed on demand (every path requires `auth.uid()` + authenticated JWT role); server-side work uses the K4
  pattern (`request.jwt.claims` with the actor, access re-checked, claims restored: `analysis-stages.sql:2434-2479`).
- `receivable_source()` / `payable_source()` need no analysis run; staged conditions need the actor's own DONE retained run.
- Warehouse summary computes "fabric below minimum" inside one statement (`summary.sql:183-189`); not a separate function.
- pg_cron jobs named `cp7-*` are installed/uninstalled together by `scripts/cp7_schedule.py` from `cp7_ops.schedules()`;
  K3/K4/K6 cases pin that list.
- WA-0 first run (39261328722): pg_net 0.20.4 and pg_cron preloaded; `pg_net.database_name=postgres`; supabase_vault 0.3.1
  installed; `http` 1.6 available. The run hung in `createdb` (password prompt); fixed.
- WA-0 third run (39266618659, job 118107749879, a638d592), all as printed by `scripts/cp7_wa_spike.sh`:
  - Vault as `postgres`: `vault.create_secret` works and `vault.decrypted_secrets` returns the value; `authenticated` has
    no SELECT on `vault.secrets` or `vault.decrypted_secrets`.
  - `postgres` cannot set `pg_net.database_name` (permission denied). `supabase_admin` inside the db container can
    (`alter system` + `pg_reload_conf()`), and after `net.worker_restart()` the worker serves the second database: fake
    CallMeBot answered 200 "Message queued" and 500 for a FAIL text, both read back from `net._http_response`.
  - A rolled-back `net.http_get` never reached the fake server (2 requests seen, rollback text 0 times).
  - `net.http_request_queue` columns: id, method, url, headers, body, timeout_milliseconds (the query string, key
    included, sits in `url` until the worker takes the row). Responses are kept 6 hours (`pg_net.ttl`).
  - Back on `postgres` after `alter system reset`: 200 again. pg_cron exists only in `postgres` (its own database), so
    cases call the tick functions directly; schedules are checked as rows, as K3 does.
  - `vault_clone` printed nothing: probe bug (volatile `create_secret` in the WHERE of the read; the subquery returned
    NULL). Not a fact either way; WA-3 cases check Vault in the harness clone itself.

## WA-2a build notes (19 Oct)

- Tables: `settings` (append-only revisions, `request_hash` for replay), `key_events` (never the key), `transport`
  (postgres-owned single row; CHECK allows only CallMeBot or `http://fake-callmebot:8080/whatsapp.php`), `alerts`,
  `outbox`, `dispatches`, `dispatch_items`, `source_state`, `ticks`. RLS on with a false policy; no client grants.
- Key path: `vault_key_present/vault_key_write/wa_post/wa_response` owned by postgres, EXECUTE only for `cp7_alert`;
  `wa_response` masks the key in provider text. No ACL delta on vault/net objects.
- Declared ACL delta on pre-existing functions: `cp7_alert` EXECUTE on `auth.uid()`, `auth.jwt()`,
  `erp.get_my_access_v1()`, `erp.has_permission(text)` (GRANTS). SELECT on five erp tables (TABLE_GRANTS). EXECUTE on
  `receivable_source()`, `payable_source()`, `public.erp_cp7_get_sales_v1(jsonb)` (created in the same install).
- `scripts/cp7_bundle_reachability.py` now composes `cp7_alert_bundle` as the top (PASS 183/184 + 1 diagnostic).
- Local PG16 smoke with stubs (scratchpad `wa2/`): WA off -> DISABLED; enable needs phone+key; SENT with
  `apikey/phone/text`; 1 message/min; 200 -> ACCEPTED with key masked; resolved before send (stock back, reminder DONE);
  500 -> PENDING + 5 min rest; 10 min silence -> UNKNOWN, owner NOT_DELIVERED -> PENDING; staff denied on owner RPCs and
  sees only kinds of its permissions; 3 tests/hour; rollback leaves no outbox row; no key text in any table; same
  request id with other content refused; digest (slot after enabling) covers pending items, once per slot; DETAILED shows
  party names, SUMMARY aggregates AR/AP; 40+40 items cut to 862 chars with "dan 35 lainnya"; KIND_OFF; quiet -> HELD_QUIET
  then sent; repeat after 24 h ("Masih terbuka"); owner inactive -> both ticks hold; tick without 8 s limit refused.
  `verify_alert` passed and caught 7/7 injected mistakes.
- For WA-3: the CI stack has pg_net available but NOT created (`pg_net=-/0.20.4`); the WA suite must create it in the
  stack database before the baseline snapshot (and point the worker at the clone as supabase_admin, as WA-0 did).
  Uninstall must also delete the Vault secret `cp7_callmebot_apikey` if a committed mode wrote one.

## WA-3a stack check (19 Oct)

`scripts/cp7_wa_stack_smoke.py` (job `wa3a-stack-smoke` in `.github/workflows/claude-wa-forward.yml`) installs
`alerts.sql` as `postgres` (not a superuser) over `scripts/cp7_wa_smoke_stubs.sql` on a bare stack with the fake
CallMeBot (`scripts/cp7_wa_fake_callmebot.py`). Run 39273065727 (job 118130172052, `65789737`): PASS, all steps:
install + verifier; NOT_CONFIGURED before settings; owner settings and key, staff 42501 x3; enable; alert sent and
delivered to the fake server (phone, text, `apikey=FAKEKEY-SMOKE`), stored answer `Message queued apikey=***`; test
message delivered; pg_cron ran both ticks from `schedules()` (22 runs succeeded) and delivered the owner's reminder,
never the staff one; a FAIL text got 500 -> PROVIDER_REFUSED, item PENDING; rollback sent nothing; key in none of 17
tables nor the settings answer; uninstall left nothing (schema, RPCs, role, Vault secret, cron jobs).
Earlier runs, logs kept in CI: 39271239303 (`must be able to SET ROLE "cp7_alert"`), 39271994388 (`permission denied
for schema auth`), 39272579014 (`schema "cron" does not exist`; pg_cron not created). Fixes: role granted to the
installer; identity read without schema auth; pg_cron created by the check. CP7C install facts from these runs:
`docs/cp7/wa/CP7C_INSTALL_FINDINGS_20261019.md` (best practice E25j).

## WA-3b and WA-2b (19 Oct)

- WA-3b first Native run 39275715784 (job 118139520134, `97cd1386`): INCOMPLETE before any case, verifier
  `('transport', 'supabase_admin', True)`: the harness installs as supabase_admin and the table was left with its
  installer. Fix: `alter table cp7_alert_native.transport owner to postgres` (reproduced locally with a non-postgres
  superuser installer: same assertion before, PASS after). Best practice E25l. Log kept: writer scratchpad
  `cand-logs/wa3b/run39275715784_job118139520134.log`.
- CodeQL run 39273065854 (`65789737`): the fake server printed `apikey` (py/clear-text-logging-sensitive-data). Fixed in
  `97cd1386`: it prints `key_ok` against `FAKE_CALLMEBOT_ACCEPTS`; CodeQL 39275715248 success. Best practice E25k.
- WA-2b in `alerts.sql`: kinds PRODUCTION_GAP and FABRIC_NEED; tables `analysis_runs`, `analysis_requests`;
  `analysis_tick()` (one unit per call: condition-set step, or up to 3 s of condition rechecks ten a page, or an automatic
  request in its own unit, or the due decision); `analysis_recheck()` before every send (5 s budget, at most 20 items or
  max_items per kind for a digest; the rest waits or is counted "belum dicek ulang"). cp7_alert calls only the public
  functions the screens call (CALLS in the bundle) and reads six columns of `cp7_analysis_stage.jobs`.
- Cases: 21 (15 Native, 4 races, 2 HTTP). New: WAF_ANALYSIS_GAP_FORWARDED_AND_RECHECKED (real staged run of the owner,
  owner's rule on, set built by the tick, alerts equal the reminders' own read + recheck, sent with need now, resolved
  before the repeat, no reminder claim written) and WAF_ANALYSIS_AUTOMATIC_RUN (due query oracle, request in the owner's
  name, job driven, new run checked, NOT_DUE, outside hours, off). The pg_cron race now also proves the analysis command.
- WA Forward run 39279865016 (job 118151914129, `4c36f1a2`, 22.41-22.48 WIB): 18 PASS, 3 INCOMPLETE. Log kept: writer
  scratchpad `cand-logs/wa2b/run39279865016_job118151914129.log`.
  - WAF_ANALYSIS_GAP_FORWARDED_AND_RECHECKED and WAF_RACE_PG_CRON_RUNS_TICKS: the first analysis tick answered
    OUTSIDE_ANALYSIS_HOURS (default hours 07:00-20:00) where NO_OWNER_ANALYSIS_YET was expected. Root cause in
    `analysis_unit`: the switch and the hours were checked before the owner's own state. Fixed: running job, then no
    finished run, then switch, then hours (the hours gate only a new automatic request; the owner's run is read and checked
    at any hour, as before). The gap case now runs with hours that exclude the current WIB time and asserts the run is
    still worked through, then OUTSIDE_ANALYSIS_HOURS. The automatic case waits past WIB midnight when within 3 minutes of
    it (00:00-23:59 leaves the last minute out), so the business-day control reruns it. Best practice E25m. Local smoke
    `wa2/smoke8.sql`: outside hours gives NO_OWNER_ANALYSIS_YET, ANALYSIS_RUNNING, ANALYSIS_CHECKED, OUTSIDE_ANALYSIS_HOURS.
  - WAF_OWNER_REMINDERS_ONLY_WHEN_DUE: the "other user's reminder" fixture used a GUDANG user; the reminders module accepts
    only OWNER/ADMIN/STAFF ("Internal ERP access required"). Fixture now ADMIN (as `cp7_r3_reminders_cases.py`); the
    assertion (another user's reminder never queued or read) is unchanged. Best practice E25n.
  - `writer_runtime: False` in the package gate follows from the INCOMPLETE suite.

## Checkpoint log

| Commit subject | State after it |
|---|---|
| test(wa): WA-0 stack facts ... / passes the local password ... / prints values without command tags | WA-0 probe in `.github/workflows/claude-wa-forward.yml` + `scripts/cp7_wa_spike.sh`; rerun pending |
| docs(wa): WA-0 facts from the third probe run | WA-0 done |
| feat(wa): WA-2a system reminders and WhatsApp forwarding (database part) | WA-2a done locally; next WA-3 (CI cases + workflow) |
| test(wa)/fix(wa): WA-3a stack check + SET ROLE + auth-free identity + pg_cron | WA-3a PASS (run 39273065727); next WA-3b full Native suite |
