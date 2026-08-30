# ERP Enteng UAT v2.6.11a pre-connect runbook

Status: **DRAFT / NOT APPLIED**  
Last read-only verification: 2026-08-30 UTC

This runbook is for one manual UAT operational patch. It is not a portable
Supabase CLI migration and must never be deployed with `supabase db push`.

## Reviewed artifacts

| Artifact | SHA-256 |
|---|---|
| `ops/supabase/uat/manual_uat_only__erp_enteng__v2_6_11a_preconnect.sql` | `d8b42725eb3299989b682a8f3932f480cf5e1c10344c224235fad6154d404a91` |
| `ops/supabase/uat/manual_uat_only__erp_enteng__v2_6_11a_preconnect.acceptance.sql` | `2e2f7a53b499b1f4ccd05ce1b398fc49f706a00b1ccf9f230b118405a6f39597` |

Recalculate both hashes immediately before an approved execution. Any change
requires another review and new recorded hashes.

## Target boundary

Allowed target only:

- Project: ERP Enteng / UAT
- Project ref: `siimvrusnzxexizpyoib`

Forbidden target:

- Project: ERP-Garment / canonical
- Project ref: `vlxdhpkjeevubjxexnfo`

The SQL verifies an exact UAT database lineage:

- 50 platform migration rows;
- `20260826112217 / compact_replay_001`;
- `20260829185830 / erp_v2_6_10_fg_partial_completion`;
- `20260829204632 / erp_v2_6_11_operational_reservations_and_completion_scope`.

This is defense in depth only. PostgreSQL cannot safely discover a Supabase
project ref. The operator or tool must independently verify the exact external
project ref before sending any SQL.

## Phase-0 security decision

Do **not** expose the `erp` schema.

The current authenticated ERP ACL inventory is broad:

| ACL inventory | Before patch | After patch |
|---|---:|---:|
| ERP relations with authenticated `SELECT` | 176 | 176 |
| ERP tables with any authenticated direct write ACL | 64 | 64 |
| ERP functions executable by authenticated | 179 | 177 |

The two-function reduction closes `run_v260_integrity_checks()` and legacy
`post_sale(uuid)`. The remaining broad ACLs are not approved phase-0 APIs.
They stay unreachable because the Data API must not expose `erp`. A frontend
allowlist is not a database security boundary.

Phase 0 adds exactly one relation to the already-exposed `public` schema:

`public.v_erp_my_profile`

The view:

- is `security_invoker=true` and `security_barrier=true`;
- explicitly filters `auth_user_id = (select auth.uid())`;
- has `WITH LOCAL CHECK OPTION` as defense in depth;
- is owned by `postgres`;
- returns only `id`, `auth_user_id`, `full_name`, `role`, `is_active`, and
  `row_version`;
- grants only `SELECT` to `authenticated`;
- grants no access to `anon`;
- explicitly revokes all facade privileges from `service_role` so broad default
  privileges cannot create a Data API DML path;
- grants no insert, update, or delete path to any API role;
- still relies on RLS on `erp.app_users` as defense in depth.

No product view or business mutation is exposed in phase 0. Product reads must
wait for a separately audited `public` read facade.

## Why this file is outside `supabase/migrations`

Supabase CLI compares timestamp IDs between local files and
`supabase_migrations.schema_migrations`. Existing timestamps already differ:

| Logical change | Local filename | UAT remote | Canonical remote |
|---|---|---|---|
| v2.6.10 | `20260829013000` | `20260829185830` | `20260829190125` |
| v2.6.11 | `20260829210000` | `20260829204632` | `20260829204756` |

The repository also has no complete baseline migration or `supabase/config.toml`;
the two standard migration files are deltas that require an existing ERP
schema. A clean `supabase db reset` is not currently reproducible.

Therefore:

- do not put this UAT guard under `supabase/migrations`;
- do not call MCP `apply_migration` because it creates another remote timestamp;
- do not run `supabase db push`, `db reset`, or `migration repair` from this
  repository;
- do not use `migration repair` merely to hide timestamp disagreement.

## Release metadata semantics

`erp.system_release_info` is the current runtime pointer:

- `release_version = 2.6.11`;
- `installed_at = 2026-08-29 20:46:32+00`, the verified UAT installation time
  of runtime v2.6.11.

`v2.6.11a` is an operational UAT closure, not a new runtime schema version. Its
actual execution time is stored separately in
`erp.schema_migrations.installed_at`. The old release note is preserved and one
stable `[v2.6.11a/UAT_PRECONNECT]` marker is appended.

## Preflight state

The manual SQL validates all preconditions before its first write. The verified
pre-apply state is:

- platform migration history: 50 rows;
- application migration history: 38 rows;
- current release pointer: 2.6.1;
- `v2.6.10`, `v2.6.11`, and `v2.6.11a` application markers: absent;
- `public` application relations: 0;
- `public` functions: 0;
- phase-0 product view grants: 0;
- `erp.app_users`: RLS enabled, authenticated self-read available, anon denied;
- Auth users and ERP app users: 0;
- legacy authenticated RPC grants: still present until the patch is approved.

The exact preflight block has been executed read-only against UAT and passed.
No database mutation was made.

## Approved execution route

Execution requires explicit user approval after this runbook and both hashes
have been reviewed.

1. Select MCP `execute_sql`, never `apply_migration`.
2. Set the tool `project_id` explicitly to `siimvrusnzxexizpyoib`.
3. Send the exact contents of
   `manual_uat_only__erp_enteng__v2_6_11a_preconnect.sql` in one call.
4. Do not prepend, append, or edit SQL in transit.
5. The file contains an explicit transaction. Any preflight or self-check
   exception must roll back all changes.
6. The transaction sets `application_name = erp_enteng_v2_6_11a_preconnect`
   and must acquire advisory transaction lock `(2611, 20260830)`. A second
   execution fails rather than overlapping the first.
7. Do not retry an ambiguous timeout while the original tool call is running or
   lacks a terminal result. Run the read-only acceptance file only after the
   original call has ended; require `00_EXECUTION_QUIESCENT = true` before
   interpreting any other row. If it is false, wait and do not retry.
8. If transport state remains unknown even though the database is quiescent,
   stop for explicit operator review; do not turn an ambiguous request into an
   automatic retry.

MCP `execute_sql` intentionally does not add a platform migration row. The
application-owned `erp.schema_migrations` rows and release note are the audit
record for this manual UAT operation.

## Database acceptance

Immediately after an approved execution:

1. Run the exact contents of
   `manual_uat_only__erp_enteng__v2_6_11a_preconnect.acceptance.sql` through
   read-only `execute_sql` against the same external project ref.
2. Require 18 individual checks, including `00_EXECUTION_QUIESCENT`, and
   `00_ALL_CHECKS_PASS` to return
   `passed = true`.
3. Require platform migration history to remain exactly 50 rows. A count of 51
   means the wrong deployment mechanism was used.
4. Run the Supabase Security Advisor and require zero findings.
5. Repeat the canonical read-only snapshot and require it to remain unchanged:
   release 2.6.1, application history 38, no `public` application relations,
   no product-view grants, and both legacy authenticated grants still present.

The acceptance SQL was executed before apply to validate its syntax. It
correctly returned `00_ALL_CHECKS_PASS = false` with ten expected pending
checks and 18 total checks; execution quiescence, lineage, schema boundary,
app-users RLS, absent product facades, RPC hashes, and the nested
`post_sale_v2` contract already passed.

## Data API acceptance

Keep the Supabase Data API exposed schemas unchanged: `public` and
`graphql_public`. Do not add `erp` in Dashboard and do not override PostgREST
with `ALTER ROLE`.

Use a browser-safe active publishable key only. Never store a service-role or
secret key in the repository, frontend bundle, shell history, or report.

First prove that direct ERP profile selection remains impossible:

```bash
curl -sS -o /tmp/erp-enteng-erp-schema-probe.json -w '%{http_code}\n' \
  -H "apikey: ${ERP_UAT_PUBLISHABLE_KEY}" \
  -H 'Accept-Profile: erp' \
  'https://siimvrusnzxexizpyoib.supabase.co/rest/v1/app_users?select=id&limit=1'
```

Expected: HTTP 406 with PostgREST code `PGRST106`.

Then probe the public facade without a user JWT:

```bash
curl -sS -o /tmp/erp-enteng-anon-profile-probe.json -w '%{http_code}\n' \
  -H "apikey: ${ERP_UAT_PUBLISHABLE_KEY}" \
  'https://siimvrusnzxexizpyoib.supabase.co/rest/v1/v_erp_my_profile?select=id,auth_user_id,full_name,role,is_active,row_version'
```

Expected: non-2xx permission denial because `anon` has no `SELECT` grant.

After the first OWNER is securely created and mapped, repeat the second request
with that user's access token:

```bash
curl -sS -o /tmp/erp-enteng-owner-profile-probe.json -w '%{http_code}\n' \
  -H "apikey: ${ERP_UAT_PUBLISHABLE_KEY}" \
  -H "Authorization: Bearer ${ERP_UAT_OWNER_ACCESS_TOKEN}" \
  'https://siimvrusnzxexizpyoib.supabase.co/rest/v1/v_erp_my_profile?select=id,auth_user_id,full_name,role,is_active,row_version'
```

Expected: HTTP 200 and exactly one row whose `auth_user_id` equals the token
subject. An authenticated but unmapped user must receive an empty array; the
frontend Auth gate must block that state.

The frontend must query the default public schema:

```ts
supabase.from('v_erp_my_profile').select(
  'id,auth_user_id,full_name,role,is_active,row_version',
).maybeSingle()
```

It must not call `.schema('erp')`, `erp.app_users`, any product view, or any
business RPC in phase 0.

## Failure and rollback policy

- A SQL error before commit is a failed attempt; the explicit transaction must
  leave no partial state.
- On timeout, first require the original call to reach a terminal state. Then
  inspect with the acceptance SQL and require `00_EXECUTION_QUIESCENT = true`.
  A false quiescence result is a hard stop, not evidence that the patch is
  unapplied. Never terminate a tagged backend without separate approval.
- After a confirmed commit, never delete or rewrite history to simulate a
  rollback. Use a separately reviewed compensating version with a new marker.
- Do not expose `erp` as a workaround for a facade or permission failure.

## Future promotion path

Before any portable database deployment:

1. Establish a complete canonical baseline in a dedicated migration workflow.
2. Reconcile local and remote migration ledgers deliberately.
3. Generate a portable migration using `supabase migration new`.
4. Remove all UAT-lineage checks and UAT-specific timestamps from the portable
   migration.
5. Verify a clean `supabase db reset` and `supabase db push --dry-run`.
6. Add business read facades one domain at a time with explicit columns, RLS,
   grants, and REST tests.

The manual UAT script remains operational evidence and is never copied into
the portable migrations directory.

## Primary references

- Supabase local workflow and migration behavior:
  https://supabase.com/docs/guides/local-development/cli-workflows
- Migration list compares local and remote timestamp IDs:
  https://supabase.com/docs/reference/cli/supabase-migration-list
- Data API grants and RLS are separate controls:
  https://supabase.com/docs/guides/api/securing-your-api
- PostgreSQL `security_invoker` view behavior:
  https://www.postgresql.org/docs/current/sql-createview.html
