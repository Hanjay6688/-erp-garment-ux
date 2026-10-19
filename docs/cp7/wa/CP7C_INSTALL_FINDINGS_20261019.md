# CP7C install findings from the WA stack check (19 Oct 2026)

Found while building the WhatsApp forwarding (WA-3a, `scripts/cp7_wa_stack_smoke.py`, workflow "CP7 WA Forward"). The
check installs SQL as `postgres` on a bare Supabase CLI 2.116.0 stack (Postgres 17.6, image 17.6.1.165), the role the
hosted install will use. `postgres` is not a superuser there (`rolsuper=false`). The Native test harness installs every
CP7 bundle as `supabase_admin` (a superuser, `ADMIN=postgresql://supabase_admin:...`), so none of this showed up in
the existing suites. Nothing hosted was read or changed.

## F1. Handing objects to a new role needs SET ROLE (all bundles)

- Fact (runs 39271239303 / 39272579014): as `postgres`, `create role x; create schema s authorization x` fails with
  `must be able to SET ROLE "x"` (PostgreSQL 16+ rule). With the session setting
  `createrole_self_grant = 'set, inherit'` the same statements succeed.
- Effect: every CP7 bundle creates its own roles and hands schemas, tables and functions to them (39 SQL files with
  `create role`). Installed as `postgres` without that setting, the first hand-over stops the install.
- Fix options for CP7C (no decision needed now; CP7C is held, D13-9a):
  1. The install session runs `set createrole_self_grant = 'set, inherit'` before the bundle SQL (no SQL file changes;
     proved on the stack). Each new role is then a member of `postgres`; it goes away with the role on uninstall.
  2. Each file grants its new role to `current_user` (what the restore drill does, and what `alerts.sql` now does).
- To prove at CP7C: the full composition installed as `postgres` on a disposable stack (not only as `supabase_admin`).

## F2. `postgres` cannot pass on USAGE of schema `auth`

- Fact (run 39272579014): `has_schema_privilege('postgres','auth','USAGE WITH GRANT OPTION')` is false (it is true for
  `vault` and `extensions`). `grant usage on schema auth to <role>` by `postgres` is skipped with a warning, not an
  error. A SECURITY DEFINER function owned by that role then fails at run time with
  `permission denied for schema auth` as soon as it calls `auth.uid()` or `auth.jwt()` (seen in run 39271994388 for
  the WA RPCs before the fix).
- Effect: 27 CP7 roles receive `usage on schema auth` this way (31 receive EXECUTE on `auth.uid()`/`auth.jwt()`), e.g.
  `cp7_sales_read`, `cp7_material_write`, `cp7_payable_read`, `cp7_reminder`, `cp7_capture`, `cp7_policy`. Installed
  as `postgres`, their facades would refuse every call.
- Fix options for CP7C:
  1. A small reader owned by `postgres` (which can use `auth`), e.g. `cp7_identity.uid()/jwt()`, executable by the CP7
     roles; the CP7 functions call it instead of `auth.uid()/auth.jwt()`.
  2. Read the request identity from the same settings `auth.uid()/jwt()` read (`request.jwt.claim.sub`,
     `request.jwt.claims`, `request.jwt.claim`), as `cp7_alert_native.uid()/jwt()` now does.
  3. Ask whether the hosted project differs (read-only preflight: the `has_schema_privilege` query above). Not run on
     Enteng; Enteng is not touched before the first backup is verified (D13-8f).
- To prove at CP7C: the Native suites run with the bundles installed as `postgres`, or at least one facade per role
  called through real Auth after a `postgres` install.

## F3. pg_net and pg_cron are available but not created

- Fact (WA-0 run 39266618659 and run 39272579014): `pg_net` 0.20.4 and `pg_cron` 1.6.4 are preloaded but have no
  extension in the database until `create extension` (as `postgres`, allowed). The WA module needs both on Enteng;
  the K3/K4/K6 schedules need `pg_cron`.

## What WA already does

`scripts/cp7-src/alerts/alerts.sql` grants `cp7_alert` to the installing role (F1 option 2), reads the request identity
without `auth` (F2 option 2) and keeps every Vault and pg_net call in four functions owned by `postgres`. Its stack
check installs and uninstalls it as `postgres`.
