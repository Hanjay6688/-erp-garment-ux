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
| WA-0 | CI stack facts: pg_net, Vault, pg_cron, fake CallMeBot on the stack network, pg_net serving a second database, rollback sends nothing | running |
| WA-1 | Map install/test path (done: see below) | done |
| WA-2a | `scripts/cp7-src/alerts/alerts.sql`: schema `cp7_alert_native` (role `cp7_alert`), `alerts`, `alert_settings`, Vault key, `wa_outbox`, `wa_dispatches`, trigger on `alerts`, sender + reconcile (pg_net), public RPCs; sources: owner's manual reminders, fabric below minimum, AR/AP due | todo |
| WA-2b | Analysis-based kinds (FABRIC_NEED, ACCESSORY_NEED, PRODUCTION_GAP) from the latest DONE staged set + scheduled owner analysis; schedules in `cp7_ops.schedules()` with K3/K4/K6 schedule lists updated by declaration | todo |
| WA-3 | Bundle `scripts/cp7_alert_bundle.py` (previous = reminder v2), reachability, cases (Native/race/HTTP), declaration JSON, suite in the probe, fake server in CI | todo |
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

## Checkpoint log

| Commit subject | State after it |
|---|---|
| test(wa): WA-0 stack facts ... / passes the local password ... / prints values without command tags | WA-0 probe in `.github/workflows/claude-wa-forward.yml` + `scripts/cp7_wa_spike.sh`; rerun pending |
