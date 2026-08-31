-- ERP Garment v2.6.13b
-- Forward-only source tracking for the v2.6.11a UAT Auth self-profile facade.
--
-- The original v2.6.11a closure was applied manually and is immutable evidence.
-- This focused delta adopts an already-exact facade or creates it when wholly
-- absent. Any partial or drifted object fails before DDL. The operator must
-- externally verify project ref siimvrusnzxexizpyoib; PostgreSQL cannot prove a
-- Supabase project ref or the Data API exposed-schema allowlist. The latter must
-- remain public + graphql_public; erp must stay unexposed. Canonical project
-- vlxdhpkjeevubjxexnfo is forbidden.

set local application_name = 'erp_v2_6_13b_auth_profile_facade_tracking';
set local lock_timeout = '10s';
set local statement_timeout = '120s';
set local search_path = pg_catalog, public, pg_temp;

do $migration_guard$
declare
  v_view regclass := to_regclass('public.v_erp_my_profile');
  v_columns text[];
  v_types text[];
  v_not_null boolean[];
begin
  if current_user <> 'postgres' then
    raise exception 'AUTH_PROFILE_TARGET_GUARD: migration must run as postgres';
  end if;

  if not pg_try_advisory_xact_lock(2613, 20260830) then
    raise exception 'AUTH_PROFILE_EXECUTION_GUARD: another facade migration or acceptance test is active';
  end if;

  if current_setting('server_version_num')::integer < 150000 then
    raise exception 'AUTH_PROFILE_TARGET_GUARD: SECURITY INVOKER views require PostgreSQL 15 or newer';
  end if;

  if to_regrole('anon') is null
     or to_regrole('authenticated') is null
     or to_regrole('service_role') is null
     or to_regrole('postgres') is null then
    raise exception 'AUTH_PROFILE_TARGET_GUARD: required Supabase API roles are missing';
  end if;

  if to_regnamespace('public') is null
     or to_regnamespace('erp') is null
     or to_regnamespace('auth') is null
     or to_regnamespace('extensions') is null
     or to_regclass('supabase_migrations.schema_migrations') is null
     or to_regclass('erp.schema_migrations') is null
     or to_regclass('erp.system_release_info') is null
     or to_regclass('erp.app_users') is null
     or to_regprocedure('auth.uid()') is null then
    raise exception 'AUTH_PROFILE_TARGET_GUARD: required UAT schemas, history, table, or auth.uid() are missing';
  end if;

  -- This is a UAT lineage guard, not a substitute for the external project-ref
  -- allowlist. Avoid total migration counts because later forward deltas are valid.
  if not exists (
       select 1
       from supabase_migrations.schema_migrations
       where version = '20260826112217' and name = 'compact_replay_001'
     )
     or not exists (
       select 1
       from supabase_migrations.schema_migrations
       where version = '20260830140645'
         and name = 'erp_v2_6_12_attendance_and_stock_explainability'
     )
     or not exists (
       select 1
       from supabase_migrations.schema_migrations
       where version = '20260830190955'
         and name = 'erp_v2_6_13_manual_reminders_v1'
     )
     or (select count(*)
         from erp.schema_migrations
         where version = 'v2.6.11a'
           and description = 'UAT phase-0 public self-profile facade and direct legacy RPC closure'
           and installed_at is not null) <> 1
     or not exists (
       select 1
       from erp.system_release_info
       where singleton_id = 1
         and position('[v2.6.11a/UAT_PRECONNECT]' in coalesce(notes, '')) > 0
     ) then
    raise exception 'AUTH_PROFILE_TARGET_GUARD: expected the verified ERP Enteng UAT lineage; externally verify siimvrusnzxexizpyoib';
  end if;

  if exists (
       select 1
       from (values ('anon'),('authenticated'),('service_role')) r(role_name)
       cross join (values ('erp'),('public'),('auth'),('extensions')) s(schema_name)
       where has_schema_privilege(r.role_name, s.schema_name, 'CREATE')
     )
     or exists (
       select 1
       from pg_namespace n
       cross join lateral aclexplode(
         coalesce(n.nspacl, acldefault('n', n.nspowner))
       ) a
       where n.nspname in ('erp','public','auth','extensions')
         and a.grantee = 0
         and a.privilege_type = 'CREATE'
     ) then
    raise exception 'AUTH_PROFILE_BASELINE_DRIFT: untrusted API roles may CREATE in a trusted schema';
  end if;

  if not has_schema_privilege('authenticated', 'public', 'USAGE')
     or not has_schema_privilege('authenticated', 'auth', 'USAGE')
     or not has_function_privilege('authenticated', 'auth.uid()', 'EXECUTE')
     or has_schema_privilege('anon', 'erp', 'USAGE') then
    raise exception 'AUTH_PROFILE_BASELINE_DRIFT: public/auth helper or private ERP schema boundary differs';
  end if;

  select
    array_agg(a.attname::text order by a.attnum),
    array_agg(format_type(a.atttypid, a.atttypmod) order by a.attnum),
    array_agg(a.attnotnull order by a.attnum)
  into v_columns, v_types, v_not_null
  from pg_attribute a
  where a.attrelid = 'erp.app_users'::regclass
    and a.attnum > 0
    and not a.attisdropped;

  if v_columns is distinct from array[
       'id','auth_user_id','full_name','role','is_active',
       'created_at','updated_at','row_version'
     ]::text[]
     or v_types is distinct from array[
       'uuid','uuid','character varying(150)','character varying(20)','boolean',
       'timestamp with time zone','timestamp with time zone','bigint'
     ]::text[]
     or v_not_null is distinct from array[
       true,false,true,true,true,true,true,true
     ]::boolean[] then
    raise exception 'AUTH_PROFILE_BASELINE_DRIFT: erp.app_users column contract differs';
  end if;

  if not exists (
       select 1
       from pg_class c
       where c.oid = 'erp.app_users'::regclass
         and c.relkind = 'r'
         and c.relowner = to_regrole('postgres')::oid
         and c.relrowsecurity
         and not c.relforcerowsecurity
     )
     or not exists (
       select 1
       from pg_constraint c
       where c.conrelid = 'erp.app_users'::regclass
         and c.contype = 'u'
         and pg_get_constraintdef(c.oid, true) = 'UNIQUE (auth_user_id)'
     )
     or (select count(*) from pg_policy
         where polrelid = 'erp.app_users'::regclass) <> 1
     or not exists (
       select 1
       from pg_policy p
       where p.polrelid = 'erp.app_users'::regclass
         and p.polname = 'app_users_select_v262'
         and p.polcmd = 'r'
         and p.polpermissive
         and p.polroles = array[to_regrole('authenticated')::oid]
         and p.polwithcheck is null
         and md5(pg_get_expr(p.polqual, p.polrelid)) =
             'ce7c898347068ed07331b3af7c67e94f'
     ) then
    raise exception 'AUTH_PROFILE_BASELINE_DRIFT: erp.app_users owner, RLS, uniqueness, or policy differs';
  end if;

  -- Missing authenticated SELECT/ERP USAGE is an allowed all-or-none grant
  -- state and is normalized below. Any broader or foreign grant is drift.
  if exists (
       select 1
       from pg_class c
       cross join lateral aclexplode(
         coalesce(c.relacl, acldefault('r', c.relowner))
       ) a
       where c.oid = 'erp.app_users'::regclass
         and (
           a.is_grantable
           or a.grantee = 0
           or a.grantee = to_regrole('anon')::oid
           or (a.grantee = to_regrole('authenticated')::oid
               and a.privilege_type <> 'SELECT')
           or a.grantee not in (
             c.relowner,
             to_regrole('authenticated')::oid,
             to_regrole('service_role')::oid
           )
         )
     )
     or exists (
       select 1
       from pg_attribute a
       where a.attrelid = 'erp.app_users'::regclass
         and a.attnum > 0
         and not a.attisdropped
         and a.attacl is not null
     ) then
    raise exception 'AUTH_PROFILE_BASELINE_DRIFT: erp.app_users direct or column ACL differs';
  end if;

  if v_view is null then
    if to_regtype('public.v_erp_my_profile') is not null then
      raise exception 'AUTH_PROFILE_PARTIAL_INSTALL: profile relation is absent but its type name is occupied';
    end if;
  else
    select
      array_agg(a.attname::text order by a.attnum),
      array_agg(format_type(a.atttypid, a.atttypmod) order by a.attnum)
    into v_columns, v_types
    from pg_attribute a
    where a.attrelid = v_view
      and a.attnum > 0
      and not a.attisdropped;

    if not exists (
         select 1
         from pg_class c
         where c.oid = v_view
           and c.relkind = 'v'
           and c.relowner = to_regrole('postgres')::oid
           and coalesce(cardinality(c.reloptions), 0) = 3
           and c.reloptions @> array[
             'security_invoker=true',
             'security_barrier=true',
             'check_option=local'
           ]::text[]
       )
       or v_columns is distinct from array[
         'id','auth_user_id','full_name','role','is_active','row_version'
       ]::text[]
       or v_types is distinct from array[
         'uuid','uuid','character varying(150)','character varying(20)',
         'boolean','bigint'
       ]::text[]
       or not exists (
         select 1
         from information_schema.views v
         where v.table_schema = 'public'
           and v.table_name = 'v_erp_my_profile'
           and v.check_option = 'LOCAL'
       )
       or md5(pg_get_viewdef(v_view, true)) is distinct from
          'efd4feeaf2b1dac307638394d33c60c1'
       or obj_description(v_view, 'pg_class') is distinct from
          'Phase-0 Auth bootstrap facade. Returns only the authenticated user own ERP profile columns through explicit auth.uid filtering, SECURITY INVOKER, and SECURITY BARRIER. The erp schema must remain unexposed.'
       or not exists (
         select 1
         from pg_class c
         cross join lateral aclexplode(
           coalesce(c.relacl, acldefault('r', c.relowner))
         ) a
         where c.oid = v_view
           and a.grantee = to_regrole('authenticated')::oid
           and a.privilege_type = 'SELECT'
           and not a.is_grantable
       )
       or exists (
         select 1
         from pg_class c
         cross join lateral aclexplode(
           coalesce(c.relacl, acldefault('r', c.relowner))
         ) a
         where c.oid = v_view
           and (
             a.is_grantable
             or a.grantee not in (c.relowner, to_regrole('authenticated')::oid)
             or (a.grantee = to_regrole('authenticated')::oid
                 and a.privilege_type <> 'SELECT')
           )
       )
       or exists (
         select 1
         from pg_attribute a
         where a.attrelid = v_view
           and a.attnum > 0
           and not a.attisdropped
           and a.attacl is not null
       )
       or has_table_privilege('anon', v_view, 'SELECT')
       or has_table_privilege('service_role', v_view, 'SELECT')
       or has_table_privilege('authenticated', v_view, 'INSERT')
       or has_table_privilege('authenticated', v_view, 'UPDATE')
       or has_table_privilege('authenticated', v_view, 'DELETE') then
      raise exception 'AUTH_PROFILE_REPLAY_DRIFT: existing profile facade is not the exact audited v2.6.11a object';
    end if;
  end if;
end;
$migration_guard$;

-- Normalize only the privileges required by a SECURITY INVOKER facade. Keep
-- service_role's existing operational access to the private table unchanged.
revoke create on schema public, erp
  from public, anon, authenticated, service_role;
revoke all on schema erp from public, anon;
grant usage on schema public, erp to authenticated;

revoke all on table erp.app_users from public, anon, authenticated;
grant select on table erp.app_users to authenticated;

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

alter view public.v_erp_my_profile owner to postgres;

revoke all on public.v_erp_my_profile
  from public, anon, authenticated, service_role;
grant select on public.v_erp_my_profile to authenticated;

comment on view public.v_erp_my_profile is
  'Phase-0 Auth bootstrap facade. Returns only the authenticated user own ERP profile columns through explicit auth.uid filtering, SECURITY INVOKER, and SECURITY BARRIER. The erp schema must remain unexposed.';

do $self_check$
declare
  v_view regclass := to_regclass('public.v_erp_my_profile');
  v_columns text[];
  v_types text[];
begin
  if v_view is null then
    raise exception 'AUTH_PROFILE_SELF_CHECK: profile facade was not created';
  end if;

  select
    array_agg(a.attname::text order by a.attnum),
    array_agg(format_type(a.atttypid, a.atttypmod) order by a.attnum)
  into v_columns, v_types
  from pg_attribute a
  where a.attrelid = v_view
    and a.attnum > 0
    and not a.attisdropped;

  if not exists (
       select 1
       from pg_class c
       where c.oid = v_view
         and c.relkind = 'v'
         and c.relowner = to_regrole('postgres')::oid
         and coalesce(cardinality(c.reloptions), 0) = 3
         and c.reloptions @> array[
           'security_invoker=true',
           'security_barrier=true',
           'check_option=local'
         ]::text[]
     )
     or v_columns is distinct from array[
       'id','auth_user_id','full_name','role','is_active','row_version'
     ]::text[]
     or v_types is distinct from array[
       'uuid','uuid','character varying(150)','character varying(20)',
       'boolean','bigint'
     ]::text[]
     or md5(pg_get_viewdef(v_view, true)) is distinct from
        'efd4feeaf2b1dac307638394d33c60c1'
     or obj_description(v_view, 'pg_class') is distinct from
        'Phase-0 Auth bootstrap facade. Returns only the authenticated user own ERP profile columns through explicit auth.uid filtering, SECURITY INVOKER, and SECURITY BARRIER. The erp schema must remain unexposed.'
     or not exists (
       select 1
       from information_schema.views v
       where v.table_schema = 'public'
         and v.table_name = 'v_erp_my_profile'
         and v.check_option = 'LOCAL'
     )
     or not has_schema_privilege('authenticated', 'erp', 'USAGE')
     or has_schema_privilege('anon', 'erp', 'USAGE')
     or not has_table_privilege('authenticated', 'erp.app_users', 'SELECT')
     or has_table_privilege('authenticated', 'erp.app_users', 'INSERT')
     or has_table_privilege('authenticated', 'erp.app_users', 'UPDATE')
     or has_table_privilege('authenticated', 'erp.app_users', 'DELETE')
     or has_table_privilege('authenticated', 'erp.app_users', 'TRUNCATE')
     or has_table_privilege('anon', 'erp.app_users', 'SELECT')
     or not has_table_privilege('authenticated', v_view, 'SELECT')
     or has_table_privilege('anon', v_view, 'SELECT')
     or has_table_privilege('service_role', v_view, 'SELECT')
     or has_table_privilege('authenticated', v_view, 'INSERT')
     or has_table_privilege('authenticated', v_view, 'UPDATE')
     or has_table_privilege('authenticated', v_view, 'DELETE')
     or exists (
       select 1
       from pg_attribute a
       where a.attrelid = v_view
         and a.attnum > 0
         and not a.attisdropped
         and a.attacl is not null
     )
     or exists (
       select 1
       from pg_class c
       cross join lateral aclexplode(
         coalesce(c.relacl, acldefault('r', c.relowner))
       ) a
       where c.oid = v_view
         and (
           a.is_grantable
           or a.grantee not in (c.relowner, to_regrole('authenticated')::oid)
           or (a.grantee = to_regrole('authenticated')::oid
               and a.privilege_type <> 'SELECT')
         )
     ) then
    raise exception 'AUTH_PROFILE_SELF_CHECK: facade shape, filter, RLS reachability, or ACL differs';
  end if;
end;
$self_check$;

notify pgrst, 'reload schema';