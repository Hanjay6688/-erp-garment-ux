-- MANUAL UAT ONLY — NOT A SUPABASE CLI MIGRATION
-- ERP Enteng phase-0 pre-connect closure for runtime v2.6.11.
--
-- External target allowlist (must be verified by the operator/tool before SQL):
--   siimvrusnzxexizpyoib  ERP Enteng / UAT
-- Forbidden target:
--   vlxdhpkjeevubjxexnfo  ERP-Garment / canonical
--
-- The SQL guard below proves the verified UAT migration lineage. PostgreSQL
-- cannot safely discover the Supabase project ref, so lineage is defense in
-- depth and is NOT a substitute for the external project-ref allowlist.
--
-- Phase-0 Data API contract:
--   * keep exposed schemas unchanged: public and graphql_public only;
--   * never expose the broad erp schema;
--   * expose only public.v_erp_my_profile for Auth profile bootstrap;
--   * grant no phase-0 product/business reads or writes;
--   * close two authenticated legacy RPC entry points as defense in depth.

begin;
set local application_name = 'erp_enteng_v2_6_11a_preconnect';
set local lock_timeout = '8s';
set local statement_timeout = '60s';

do $execution_guard$
begin
  if not pg_try_advisory_xact_lock(2611, 20260830) then
    raise exception 'PRECONNECT_EXECUTION_GUARD: another v2.6.11a execution or acceptance check is still active';
  end if;
end;
$execution_guard$;

do $preflight$
declare
  v_history_count bigint;
  v_marker_count bigint;
  v_is_applied boolean;
  v_expected_legacy_exec boolean;
  v_description text;
  v_installed_at timestamptz;
  v_release_version text;
  v_release_installed_at timestamptz;
  v_release_notes text;
  v_columns text[];
  v_types text[];
  v_outer_owner text;
  v_outer_security_definer boolean;
  v_outer_config text[];
  v_outer_hash text;
  v_outer_definition text;
begin
  -- Exact UAT-lineage fingerprint. This intentionally fails on canonical,
  -- preview branches, local reset, and any future unknown database state.
  if (select count(*) from supabase_migrations.schema_migrations) <> 50
     or not exists (
       select 1 from supabase_migrations.schema_migrations
       where version = '20260826112217' and name = 'compact_replay_001'
     )
     or not exists (
       select 1 from supabase_migrations.schema_migrations
       where version = '20260829185830'
         and name = 'erp_v2_6_10_fg_partial_completion'
     )
     or not exists (
       select 1 from supabase_migrations.schema_migrations
       where version = '20260829204632'
         and name = 'erp_v2_6_11_operational_reservations_and_completion_scope'
     ) then
    raise exception
      'UAT_LINEAGE_GUARD: expected the exact 50-migration ERP Enteng lineage; externally verify project ref siimvrusnzxexizpyoib';
  end if;

  if to_regrole('authenticated') is null
     or to_regrole('anon') is null
     or to_regrole('service_role') is null then
    raise exception 'PRECONNECT_PREFLIGHT: required Supabase API roles are missing';
  end if;

  if to_regclass('erp.system_release_info') is null
     or to_regclass('erp.schema_migrations') is null
     or to_regclass('erp.app_users') is null then
    raise exception 'PRECONNECT_PREFLIGHT: required ERP contract tables are missing';
  end if;

  select count(*) into v_history_count from erp.schema_migrations;
  select exists (
    select 1 from erp.schema_migrations where version = 'v2.6.11a'
  ) into v_is_applied;
  v_expected_legacy_exec := not v_is_applied;

  if (not v_is_applied and v_history_count <> 38)
     or (v_is_applied and v_history_count <> 41) then
    raise exception
      'PRECONNECT_PREFLIGHT: unexpected application history count %, applied marker %',
      v_history_count, v_is_applied;
  end if;

  select count(*) into v_marker_count
  from erp.schema_migrations
  where version in ('v2.6.10', 'v2.6.11', 'v2.6.11a');
  if (not v_is_applied and v_marker_count <> 0)
     or (v_is_applied and v_marker_count <> 3) then
    raise exception 'PRECONNECT_PREFLIGHT: partial release-marker state is not allowed';
  end if;

  -- If an idempotent retry finds markers, they must already be exact. History
  -- is never overwritten to conceal a conflicting prior record.
  select description, installed_at into v_description, v_installed_at
  from erp.schema_migrations where version = 'v2.6.10';
  if found and (
    v_description is distinct from
      'Partial Finished Goods completion through immutable QC postings'
    or v_installed_at is distinct from timestamptz '2026-08-29 18:58:30+00'
  ) then
    raise exception 'PRECONNECT_PREFLIGHT: existing v2.6.10 marker differs';
  end if;

  select description, installed_at into v_description, v_installed_at
  from erp.schema_migrations where version = 'v2.6.11';
  if found and (
    v_description is distinct from
      'Operational truth for partial FG, Laundry outstanding, and all-day sales drafts'
    or v_installed_at is distinct from timestamptz '2026-08-29 20:46:32+00'
  ) then
    raise exception 'PRECONNECT_PREFLIGHT: existing v2.6.11 marker differs';
  end if;

  select description, installed_at into v_description, v_installed_at
  from erp.schema_migrations where version = 'v2.6.11a';
  if found and (
    v_description is distinct from
      'UAT phase-0 public self-profile facade and direct legacy RPC closure'
    or v_installed_at is null
  ) then
    raise exception 'PRECONNECT_PREFLIGHT: existing v2.6.11a marker differs';
  end if;

  if (select count(*) from erp.system_release_info where singleton_id = 1) <> 1 then
    raise exception 'PRECONNECT_PREFLIGHT: release singleton is missing or duplicated';
  end if;
  select release_version, installed_at, notes
    into v_release_version, v_release_installed_at, v_release_notes
  from erp.system_release_info where singleton_id = 1;

  if not v_is_applied and v_release_version is distinct from '2.6.1' then
    raise exception 'PRECONNECT_PREFLIGHT: expected pre-closure release pointer 2.6.1';
  end if;
  if v_is_applied and (
    v_release_version is distinct from '2.6.11'
    or v_release_installed_at is distinct from timestamptz '2026-08-29 20:46:32+00'
    or position('[v2.6.11a/UAT_PRECONNECT]' in coalesce(v_release_notes, '')) = 0
  ) then
    raise exception 'PRECONNECT_PREFLIGHT: existing release pointer differs';
  end if;

  -- public is the only phase-0 facade schema. authenticated keeps ERP USAGE
  -- solely because the security-invoker view must reach app_users; anon does not.
  if has_schema_privilege('authenticated', 'public', 'USAGE') is distinct from true
     or has_schema_privilege('anon', 'public', 'USAGE') is distinct from true
     or has_schema_privilege('authenticated', 'erp', 'USAGE') is distinct from true
     or has_schema_privilege('anon', 'erp', 'USAGE') is distinct from false then
    raise exception 'PRECONNECT_PREFLIGHT: schema USAGE contract differs';
  end if;

  select array_agg(a.attname::text order by a.attnum),
         array_agg(format_type(a.atttypid, a.atttypmod) order by a.attnum)
    into v_columns, v_types
  from pg_attribute a
  where a.attrelid = 'erp.app_users'::regclass
    and a.attnum > 0 and not a.attisdropped;
  if v_columns is distinct from array[
       'id','auth_user_id','full_name','role','is_active',
       'created_at','updated_at','row_version'
     ]::text[]
     or v_types is distinct from array[
       'uuid','uuid','character varying(150)','character varying(20)','boolean',
       'timestamp with time zone','timestamp with time zone','bigint'
     ]::text[] then
    raise exception 'PRECONNECT_PREFLIGHT: app_users column contract differs';
  end if;

  if not exists (
       select 1 from pg_class c
       where c.oid = 'erp.app_users'::regclass and c.relrowsecurity
     )
     or has_table_privilege('authenticated', 'erp.app_users', 'SELECT') is distinct from true
     or has_table_privilege('anon', 'erp.app_users', 'SELECT') is distinct from false
     or not exists (
       select 1 from pg_policy p
       where p.polrelid = 'erp.app_users'::regclass
         and p.polname = 'app_users_select_v262'
         and p.polcmd = 'r'
         and position('auth_user_id' in pg_get_expr(p.polqual, p.polrelid)) > 0
         and position('auth.uid()' in pg_get_expr(p.polqual, p.polrelid)) > 0
     ) then
    raise exception 'PRECONNECT_PREFLIGHT: app_users RLS/self-read contract differs';
  end if;

  if (not v_is_applied and (
        select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relkind in ('r','p','v','m','f')
      ) <> 0)
     or (v_is_applied and (
        select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relkind in ('r','p','v','m','f')
      ) <> 1) then
    raise exception 'PRECONNECT_PREFLIGHT: unexpected public relation surface';
  end if;
  if (select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
      where n.nspname = 'public') <> 0 then
    raise exception 'PRECONNECT_PREFLIGHT: public function surface must remain empty';
  end if;

  if v_is_applied and to_regclass('public.v_erp_my_profile') is null then
    raise exception 'PRECONNECT_PREFLIGHT: applied marker exists without profile facade';
  end if;
  if not v_is_applied and to_regclass('public.v_erp_my_profile') is not null then
    raise exception 'PRECONNECT_PREFLIGHT: profile facade exists without release marker';
  end if;

  -- Broad ERP ACLs remain deliberately hidden, not made safe by a client-side
  -- allowlist. These counts are an inventory and a fail-closed drift signal.
  if (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'erp' and c.relkind in ('r','p','v','m','f')
        and has_table_privilege('authenticated', c.oid, 'SELECT')) <> 176
     or (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
         where n.nspname = 'erp' and c.relkind in ('r','p') and (
           has_table_privilege('authenticated', c.oid, 'INSERT')
           or has_table_privilege('authenticated', c.oid, 'UPDATE')
           or has_table_privilege('authenticated', c.oid, 'DELETE')
           or has_table_privilege('authenticated', c.oid, 'TRUNCATE')
         )) <> 64
     or (select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'erp'
           and has_function_privilege('authenticated', p.oid, 'EXECUTE'))
        <> (case when v_is_applied then 177 else 179 end) then
    raise exception 'PRECONNECT_PREFLIGHT: broad ERP ACL inventory differs';
  end if;

  if (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'erp'
        and c.relname in (
          'v_product_identity_history','v_product_price_current',
          'v_products_current','v_products_sellable'
        ) and has_table_privilege('authenticated', c.oid, 'SELECT')) <> 0 then
    raise exception 'PRECONNECT_PREFLIGHT: phase-0 product-view grants must remain absent';
  end if;

  if to_regprocedure('erp.run_v260_integrity_checks()') is null
     or to_regprocedure('erp.post_sale(uuid)') is null
     or to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)') is null then
    raise exception 'PRECONNECT_PREFLIGHT: required exact RPC signature is missing';
  end if;

  if md5(pg_get_functiondef(to_regprocedure('erp.run_v260_integrity_checks()')))
       <> '73978086376e3c4d3e606ae8939544fd'
     or md5(pg_get_functiondef(to_regprocedure('erp.post_sale(uuid)')))
       <> '195c2bfb86256c630f1400511ed15eb7' then
    raise exception 'PRECONNECT_PREFLIGHT: legacy RPC definition hash differs';
  end if;

  select pg_get_userbyid(p.proowner), p.prosecdef, p.proconfig,
         md5(pg_get_functiondef(p.oid)), pg_get_functiondef(p.oid)
    into v_outer_owner, v_outer_security_definer, v_outer_config,
         v_outer_hash, v_outer_definition
  from pg_proc p
  where p.oid = to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)');

  if v_outer_owner is distinct from 'postgres'
     or v_outer_security_definer is distinct from true
     or v_outer_config is distinct from
       array['search_path=erp, public, auth, extensions, pg_temp']::text[]
     or v_outer_hash is distinct from '980ad66e98cae68c61309ca2ad79eefb'
     or pg_get_function_identity_arguments(
       to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)')
     ) is distinct from
       'p_sale_id uuid, p_client_request_id uuid, p_expected_version bigint'
     or pg_get_function_result(
       to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)')
     ) is distinct from 'jsonb'
     or position('perform erp.require_internal();' in v_outer_definition) = 0
     or position('perform erp.post_sale(h.id);' in v_outer_definition) = 0
     or has_function_privilege(
       v_outer_owner, 'erp.post_sale(uuid)', 'EXECUTE'
     ) is distinct from true then
    raise exception 'PRECONNECT_PREFLIGHT: post_sale_v2 verified contract differs';
  end if;

  if has_function_privilege(
       'authenticated', 'erp.run_v260_integrity_checks()', 'EXECUTE'
     ) is distinct from v_expected_legacy_exec
     or has_function_privilege(
       'authenticated', 'erp.post_sale(uuid)', 'EXECUTE'
     ) is distinct from v_expected_legacy_exec
     or has_function_privilege(
       'authenticated', 'erp.post_sale_v2(uuid,uuid,bigint)', 'EXECUTE'
     ) is distinct from true
     or has_function_privilege(
       'service_role', 'erp.run_v260_integrity_checks()', 'EXECUTE'
     ) is distinct from true then
    raise exception 'PRECONNECT_PREFLIGHT: RPC ACL contract differs';
  end if;
end;
$preflight$;

-- Backfill application-owned history from the exact UAT platform timestamps.
-- Conflicting existing rows were rejected above and are never rewritten.
insert into erp.schema_migrations(version, description, installed_at)
values
  (
    'v2.6.10',
    'Partial Finished Goods completion through immutable QC postings',
    timestamptz '2026-08-29 18:58:30+00'
  ),
  (
    'v2.6.11',
    'Operational truth for partial FG, Laundry outstanding, and all-day sales drafts',
    timestamptz '2026-08-29 20:46:32+00'
  )
on conflict (version) do nothing;

insert into erp.schema_migrations(version, description, installed_at)
values (
  'v2.6.11a',
  'UAT phase-0 public self-profile facade and direct legacy RPC closure',
  clock_timestamp()
)
on conflict (version) do nothing;

-- Release semantics:
--   release_version/installed_at identify the installed runtime v2.6.11.
--   v2.6.11a is an operational UAT closure with its own history timestamp.
update erp.system_release_info
set
  release_version = '2.6.11',
  installed_at = timestamptz '2026-08-29 20:46:32+00',
  notes = case
    when position('[v2.6.11a/UAT_PRECONNECT]' in coalesce(notes, '')) > 0 then notes
    else concat_ws(
      E'\n',
      nullif(notes, ''),
      '[v2.6.11a/UAT_PRECONNECT] Public self-profile Auth facade created; broad ERP schema remains unexposed; unguarded v2.6.0 diagnostics and direct legacy sale posting removed from authenticated execution.'
    )
  end
where singleton_id = 1;

create or replace view public.v_erp_my_profile
with (security_invoker = true, security_barrier = true)
as
select
  u.id,
  u.auth_user_id,
  u.full_name,
  u.role,
  u.is_active,
  u.row_version
from erp.app_users u
where u.auth_user_id = (select auth.uid())
with local check option;

revoke all on public.v_erp_my_profile from public, anon, authenticated, service_role;
grant select on public.v_erp_my_profile to authenticated;

-- Defense in depth. The erp schema stays unexposed, but these legacy direct
-- authenticated entry points are still closed before later facade expansion.
revoke execute on function erp.run_v260_integrity_checks()
  from public, anon, authenticated;
revoke execute on function erp.post_sale(uuid)
  from public, anon, authenticated;

comment on view public.v_erp_my_profile is
  'Phase-0 Auth bootstrap facade. Returns only the authenticated user own ERP profile columns through explicit auth.uid filtering, SECURITY INVOKER, and SECURITY BARRIER. The erp schema must remain unexposed.';
comment on function erp.run_v260_integrity_checks() is
  'Internal release diagnostic. Direct anon/authenticated execution is revoked; service_role remains the supported operational caller.';
comment on function erp.post_sale(uuid) is
  'Internal legacy sale-posting primitive retained for post_sale_v2. Direct anon/authenticated execution is revoked.';
comment on function erp.post_sale_v2(uuid,uuid,bigint) is
  'Authenticated sale-posting contract retained but unreachable in phase 0 because the erp schema remains unexposed. SECURITY DEFINER calls post_sale(uuid) with role, idempotency, and expected-version guards.';

do $self_check$
declare
  v_columns text[];
  v_definition text;
  v_outer_owner text;
begin
  if (select count(*) from supabase_migrations.schema_migrations) <> 50
     or not exists (
       select 1 from supabase_migrations.schema_migrations
       where version = '20260826112217' and name = 'compact_replay_001'
     ) then
    raise exception 'PRECONNECT_SELF_CHECK: platform lineage changed';
  end if;

  if (select count(*) from erp.schema_migrations) <> 41
     or not exists (
       select 1 from erp.schema_migrations
       where version = 'v2.6.10'
         and description = 'Partial Finished Goods completion through immutable QC postings'
         and installed_at = timestamptz '2026-08-29 18:58:30+00'
     )
     or not exists (
       select 1 from erp.schema_migrations
       where version = 'v2.6.11'
         and description = 'Operational truth for partial FG, Laundry outstanding, and all-day sales drafts'
         and installed_at = timestamptz '2026-08-29 20:46:32+00'
     )
     or not exists (
       select 1 from erp.schema_migrations
       where version = 'v2.6.11a'
         and description = 'UAT phase-0 public self-profile facade and direct legacy RPC closure'
         and installed_at is not null
     ) then
    raise exception 'PRECONNECT_SELF_CHECK: application release history differs';
  end if;

  if not exists (
       select 1 from erp.system_release_info
       where singleton_id = 1
         and release_version = '2.6.11'
         and installed_at = timestamptz '2026-08-29 20:46:32+00'
         and position('[v2.6.11a/UAT_PRECONNECT]' in coalesce(notes, '')) > 0
     ) then
    raise exception 'PRECONNECT_SELF_CHECK: release pointer semantics differ';
  end if;

  if has_schema_privilege('authenticated', 'public', 'USAGE') is distinct from true
     or has_schema_privilege('anon', 'public', 'USAGE') is distinct from true
     or has_schema_privilege('authenticated', 'erp', 'USAGE') is distinct from true
     or has_schema_privilege('anon', 'erp', 'USAGE') is distinct from false then
    raise exception 'PRECONNECT_SELF_CHECK: schema USAGE contract differs';
  end if;

  if (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relkind in ('r','p','v','m','f')) <> 1
     or (select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public') <> 0
     or to_regclass('public.v_erp_my_profile') is null then
    raise exception 'PRECONNECT_SELF_CHECK: public surface is not exactly one relation/no functions';
  end if;

  if not exists (
       select 1 from pg_class c
       where c.oid = 'public.v_erp_my_profile'::regclass
         and c.relkind = 'v'
         and pg_get_userbyid(c.relowner) = 'postgres'
         and coalesce(c.reloptions, array[]::text[]) @> array[
           'security_invoker=true','security_barrier=true'
         ]::text[]
     )
     or not exists (
       select 1 from information_schema.views v
       where v.table_schema = 'public'
         and v.table_name = 'v_erp_my_profile'
         and v.check_option = 'LOCAL'
     ) then
    raise exception 'PRECONNECT_SELF_CHECK: profile view security options differ';
  end if;

  select array_agg(a.attname::text order by a.attnum) into v_columns
  from pg_attribute a
  where a.attrelid = 'public.v_erp_my_profile'::regclass
    and a.attnum > 0 and not a.attisdropped;
  select pg_get_viewdef('public.v_erp_my_profile'::regclass, true) into v_definition;
  if v_columns is distinct from array[
       'id','auth_user_id','full_name','role','is_active','row_version'
     ]::text[]
     or position('auth_user_id' in v_definition) = 0
     or position('auth.uid()' in v_definition) = 0
     or has_table_privilege(
       'authenticated', 'public.v_erp_my_profile', 'SELECT'
     ) is distinct from true
     or has_table_privilege(
       'anon', 'public.v_erp_my_profile', 'SELECT'
     ) is distinct from false
     or has_table_privilege(
       'authenticated', 'public.v_erp_my_profile', 'INSERT'
     ) is distinct from false
     or has_table_privilege(
       'authenticated', 'public.v_erp_my_profile', 'UPDATE'
     ) is distinct from false
     or has_table_privilege(
       'authenticated', 'public.v_erp_my_profile', 'DELETE'
     ) is distinct from false
     or has_table_privilege(
       'service_role', 'public.v_erp_my_profile', 'SELECT'
     ) is distinct from false
     or has_table_privilege(
       'service_role', 'public.v_erp_my_profile', 'INSERT'
     ) is distinct from false
     or has_table_privilege(
       'service_role', 'public.v_erp_my_profile', 'UPDATE'
     ) is distinct from false
     or has_table_privilege(
       'service_role', 'public.v_erp_my_profile', 'DELETE'
     ) is distinct from false then
    raise exception 'PRECONNECT_SELF_CHECK: narrow profile facade contract differs';
  end if;

  if not exists (
       select 1 from pg_class c
       where c.oid = 'erp.app_users'::regclass and c.relrowsecurity
     )
     or has_table_privilege('authenticated', 'erp.app_users', 'SELECT') is distinct from true
     or has_table_privilege('anon', 'erp.app_users', 'SELECT') is distinct from false then
    raise exception 'PRECONNECT_SELF_CHECK: underlying app_users protection differs';
  end if;

  if (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'erp' and c.relkind in ('r','p','v','m','f')
        and has_table_privilege('authenticated', c.oid, 'SELECT')) <> 176
     or (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
         where n.nspname = 'erp' and c.relkind in ('r','p') and (
           has_table_privilege('authenticated', c.oid, 'INSERT')
           or has_table_privilege('authenticated', c.oid, 'UPDATE')
           or has_table_privilege('authenticated', c.oid, 'DELETE')
           or has_table_privilege('authenticated', c.oid, 'TRUNCATE')
         )) <> 64
     or (select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'erp'
           and has_function_privilege('authenticated', p.oid, 'EXECUTE')) <> 177 then
    raise exception 'PRECONNECT_SELF_CHECK: hidden broad ERP ACL inventory differs';
  end if;

  if (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'erp'
        and c.relname in (
          'v_product_identity_history','v_product_price_current',
          'v_products_current','v_products_sellable'
        ) and has_table_privilege('authenticated', c.oid, 'SELECT')) <> 0 then
    raise exception 'PRECONNECT_SELF_CHECK: phase-0 product reads were accidentally granted';
  end if;

  if has_function_privilege(
       'authenticated', 'erp.run_v260_integrity_checks()', 'EXECUTE'
     ) is distinct from false
     or has_function_privilege(
       'anon', 'erp.run_v260_integrity_checks()', 'EXECUTE'
     ) is distinct from false
     or has_function_privilege(
       'service_role', 'erp.run_v260_integrity_checks()', 'EXECUTE'
     ) is distinct from true
     or has_function_privilege(
       'authenticated', 'erp.post_sale(uuid)', 'EXECUTE'
     ) is distinct from false
     or has_function_privilege(
       'anon', 'erp.post_sale(uuid)', 'EXECUTE'
     ) is distinct from false
     or has_function_privilege(
       'authenticated', 'erp.post_sale_v2(uuid,uuid,bigint)', 'EXECUTE'
     ) is distinct from true then
    raise exception 'PRECONNECT_SELF_CHECK: RPC ACL closure differs';
  end if;

  select pg_get_userbyid(p.proowner) into v_outer_owner
  from pg_proc p where p.oid = to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)');
  if v_outer_owner is distinct from 'postgres'
     or md5(pg_get_functiondef(
       to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)')
     )) <> '980ad66e98cae68c61309ca2ad79eefb'
     or not exists (
       select 1 from pg_proc p
       where p.oid = to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)')
         and p.prosecdef
         and p.proconfig = array[
           'search_path=erp, public, auth, extensions, pg_temp'
         ]::text[]
     )
     or position(
       'perform erp.post_sale(h.id);'
       in pg_get_functiondef(to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)'))
     ) = 0
     or has_function_privilege(
       v_outer_owner, 'erp.post_sale(uuid)', 'EXECUTE'
     ) is distinct from true then
    raise exception 'PRECONNECT_SELF_CHECK: nested post_sale_v2 contract differs';
  end if;
end;
$self_check$;

notify pgrst, 'reload schema';
commit;
