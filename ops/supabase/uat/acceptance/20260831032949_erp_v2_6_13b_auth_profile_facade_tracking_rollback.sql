-- Transactional acceptance for ERP Enteng UAT Auth profile facade tracking v2.6.13b.
-- Run only against externally verified project siimvrusnzxexizpyoib.
-- Every synthetic row and request claim is removed by the final ROLLBACK.

begin;

set local lock_timeout = '10s';
set local statement_timeout = '120s';

do $execution_guard$
begin
  if current_user <> 'postgres' then
    raise exception 'AUTH_PROFILE_TEST_GUARD: acceptance must run as postgres';
  end if;

  if not pg_try_advisory_xact_lock(2613, 20260830) then
    raise exception 'AUTH_PROFILE_TEST_GUARD: migration or another acceptance test is active';
  end if;

  if (
       select count(*)
       from supabase_migrations.schema_migrations
       where version = '20260831032949'
         and name = 'erp_v2_6_13b_auth_profile_facade_tracking'
         and cardinality(statements) = 1
         and octet_length(statements[1]) = 15812
         and md5(statements[1]) = 'cf96eb40ea281d44388283043fc652e6'
     ) <> 1
     or exists (
       select 1
       from supabase_migrations.schema_migrations
       where version = '20260830211000'
          or (name = 'erp_v2_6_13b_auth_profile_facade_tracking'
              and version <> '20260831032949')
     ) then
    raise exception 'AUTH_PROFILE_TEST_GUARD: exact UAT source-tracking ledger row is missing or drifted';
  end if;
end;
$execution_guard$;

create or replace function pg_temp.run_auth_profile_facade_test()
returns jsonb
language plpgsql
security invoker
set search_path = pg_catalog, public, pg_temp
as $test$
declare
  v_owner_app_user uuid := '85d34f21-1001-4f10-8000-000000001001';
  v_owner_auth_user uuid := '85d34f21-1101-4f10-8000-000000001101';
  v_other_app_user uuid := '85d34f21-1002-4f10-8000-000000001002';
  v_other_auth_user uuid := '85d34f21-1102-4f10-8000-000000001102';
  v_unmapped_auth_user uuid := '85d34f21-1103-4f10-8000-000000001103';
  v_seen_app_user uuid;
  v_seen_auth_user uuid;
  v_seen_count bigint;
  v_anon_blocked boolean := false;
  v_service_blocked boolean := false;
  v_insert_blocked boolean := false;
  v_update_blocked boolean := false;
  v_delete_blocked boolean := false;
begin
  if to_regclass('public.v_erp_my_profile') is null
     or md5(pg_get_viewdef('public.v_erp_my_profile'::regclass, true))
        is distinct from 'efd4feeaf2b1dac307638394d33c60c1'
     or not exists (
       select 1
       from pg_class c
       where c.oid = 'public.v_erp_my_profile'::regclass
         and c.relkind = 'v'
         and c.relowner = to_regrole('postgres')::oid
         and coalesce(cardinality(c.reloptions), 0) = 3
         and c.reloptions @> array[
           'security_invoker=true',
           'security_barrier=true',
           'check_option=local'
         ]::text[]
     )
     or not exists (
       select 1
       from information_schema.views v
       where v.table_schema = 'public'
         and v.table_name = 'v_erp_my_profile'
         and v.check_option = 'LOCAL'
     )
     or not (select c.relrowsecurity
             from pg_class c where c.oid = 'erp.app_users'::regclass)
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
    raise exception 'Auth profile facade pre-test shape or underlying RLS drifted';
  end if;

  if not has_schema_privilege('authenticated', 'erp', 'USAGE')
     or has_schema_privilege('anon', 'erp', 'USAGE')
     or not has_table_privilege('authenticated', 'erp.app_users', 'SELECT')
     or has_table_privilege('authenticated', 'erp.app_users', 'INSERT')
     or has_table_privilege('authenticated', 'erp.app_users', 'UPDATE')
     or has_table_privilege('authenticated', 'erp.app_users', 'DELETE')
     or has_table_privilege('authenticated', 'erp.app_users', 'TRUNCATE')
     or has_table_privilege('anon', 'erp.app_users', 'SELECT')
     or not has_table_privilege(
       'authenticated', 'public.v_erp_my_profile', 'SELECT'
     )
     or has_table_privilege('anon', 'public.v_erp_my_profile', 'SELECT')
     or has_table_privilege('service_role', 'public.v_erp_my_profile', 'SELECT')
     or has_table_privilege(
       'authenticated', 'public.v_erp_my_profile', 'INSERT'
     )
     or has_table_privilege(
       'authenticated', 'public.v_erp_my_profile', 'UPDATE'
     )
     or has_table_privilege(
       'authenticated', 'public.v_erp_my_profile', 'DELETE'
     )
     or exists (
       select 1
       from pg_attribute a
       where a.attrelid = 'public.v_erp_my_profile'::regclass
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
       where c.oid = 'public.v_erp_my_profile'::regclass
         and (
           a.is_grantable
           or a.grantee not in (c.relowner, to_regrole('authenticated')::oid)
           or (a.grantee = to_regrole('authenticated')::oid
               and a.privilege_type <> 'SELECT')
         )
     ) then
    raise exception 'Auth profile facade or underlying-table ACL is not exact';
  end if;

  insert into erp.app_users(id, auth_user_id, full_name, role, is_active)
  values
    (v_owner_app_user, v_owner_auth_user, 'TST Auth Facade Owner', 'OWNER', true),
    (v_other_app_user, v_other_auth_user, 'TST Auth Facade Other', 'STAFF', true);

  -- OWNER can see multiple rows through the underlying RLS policy. The explicit
  -- view predicate must still reduce the facade to the token subject only.
  perform set_config('request.jwt.claims', jsonb_build_object(
    'sub', v_owner_auth_user,
    'role', 'authenticated'
  )::text, true);
  execute 'set local role authenticated';
  select count(*) into v_seen_count from public.v_erp_my_profile;
  select id, auth_user_id
    into v_seen_app_user, v_seen_auth_user
  from public.v_erp_my_profile
  limit 1;
  execute 'reset role';

  if v_seen_count <> 1
     or v_seen_app_user is distinct from v_owner_app_user
     or v_seen_auth_user is distinct from v_owner_auth_user then
    raise exception 'Authenticated self-profile isolation failed: count %, app %, auth %',
      v_seen_count, v_seen_app_user, v_seen_auth_user;
  end if;

  perform set_config('request.jwt.claims', jsonb_build_object(
    'sub', v_unmapped_auth_user,
    'role', 'authenticated'
  )::text, true);
  execute 'set local role authenticated';
  select count(*) into v_seen_count from public.v_erp_my_profile;
  execute 'reset role';

  if v_seen_count <> 0 then
    raise exception 'Unmapped authenticated user received a profile row';
  end if;

  perform set_config('request.jwt.claims', '{}', true);
  execute 'set local role anon';
  begin
    perform 1 from public.v_erp_my_profile limit 1;
  exception when insufficient_privilege then
    v_anon_blocked := true;
  end;
  execute 'reset role';

  execute 'set local role service_role';
  begin
    perform 1 from public.v_erp_my_profile limit 1;
  exception when insufficient_privilege then
    v_service_blocked := true;
  end;
  execute 'reset role';

  perform set_config('request.jwt.claims', jsonb_build_object(
    'sub', v_owner_auth_user,
    'role', 'authenticated'
  )::text, true);
  execute 'set local role authenticated';

  begin
    insert into public.v_erp_my_profile(
      id, auth_user_id, full_name, role, is_active, row_version
    ) values (
      '85d34f21-1004-4f10-8000-000000001004'::uuid,
      '85d34f21-1104-4f10-8000-000000001104'::uuid,
      'FORGED', 'OWNER', true, 1
    );
  exception when insufficient_privilege then
    v_insert_blocked := true;
  end;

  begin
    update public.v_erp_my_profile
    set full_name = 'FORGED'
    where id = v_owner_app_user;
  exception when insufficient_privilege then
    v_update_blocked := true;
  end;

  begin
    delete from public.v_erp_my_profile where id = v_owner_app_user;
  exception when insufficient_privilege then
    v_delete_blocked := true;
  end;

  execute 'reset role';

  if not (
    v_anon_blocked
    and v_service_blocked
    and v_insert_blocked
    and v_update_blocked
    and v_delete_blocked
  ) then
    raise exception 'Auth profile denial matrix failed: anon %, service %, insert %, update %, delete %',
      v_anon_blocked, v_service_blocked, v_insert_blocked,
      v_update_blocked, v_delete_blocked;
  end if;

  return jsonb_build_object(
    'authenticated_self_row_count', 1,
    'unmapped_row_count', 0,
    'anon_select_blocked', v_anon_blocked,
    'service_select_blocked', v_service_blocked,
    'authenticated_insert_blocked', v_insert_blocked,
    'authenticated_update_blocked', v_update_blocked,
    'authenticated_delete_blocked', v_delete_blocked,
    'rollback_required', true
  );
end;
$test$;

select pg_temp.run_auth_profile_facade_test() as result;

rollback;

do $residue$
begin
  perform set_config(
    'search_path', 'pg_catalog, public, pg_temp', true
  );

  if exists (
       select 1
       from erp.app_users
       where id in (
         '85d34f21-1001-4f10-8000-000000001001'::uuid,
         '85d34f21-1002-4f10-8000-000000001002'::uuid
       )
     )
     or exists (
       select 1
       from erp.audit_logs
       where entity_id in (
         '85d34f21-1001-4f10-8000-000000001001'::uuid,
         '85d34f21-1002-4f10-8000-000000001002'::uuid
       )
     ) then
    raise exception 'Auth profile facade rollback left synthetic residue';
  end if;

  if to_regclass('public.v_erp_my_profile') is null
     or md5(pg_get_viewdef('public.v_erp_my_profile'::regclass, true))
        is distinct from 'efd4feeaf2b1dac307638394d33c60c1'
     or (select count(*)
         from supabase_migrations.schema_migrations
         where version = '20260831032949'
           and name = 'erp_v2_6_13b_auth_profile_facade_tracking'
           and cardinality(statements) = 1
           and octet_length(statements[1]) = 15812
           and md5(statements[1]) = 'cf96eb40ea281d44388283043fc652e6') <> 1
     or not has_table_privilege(
       'authenticated', 'public.v_erp_my_profile', 'SELECT'
     )
     or has_table_privilege('anon', 'public.v_erp_my_profile', 'SELECT')
     or has_table_privilege('service_role', 'public.v_erp_my_profile', 'SELECT') then
    raise exception 'Auth profile facade changed across rollback acceptance';
  end if;
end;
$residue$;

select jsonb_build_object(
  'status', 'PASS',
  'post_rollback_residue_rows', 0,
  'facade_definition_md5', 'efd4feeaf2b1dac307638394d33c60c1'
) as rollback_result;
