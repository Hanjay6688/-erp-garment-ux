-- READ-ONLY ACCEPTANCE — run only against externally verified project ref:
-- siimvrusnzxexizpyoib (ERP Enteng / UAT).
--
-- This query does not prove the project ref. It proves the expected UAT lineage
-- and the post-closure database contract. Every row, including
-- 00_ALL_CHECKS_PASS, must return passed = true.

with
execution_guard as (
  select
    pg_try_advisory_xact_lock(2611, 20260830) as lock_available,
    (
      select count(*)
      from pg_stat_activity a
      where a.pid <> pg_backend_pid()
        and a.application_name = 'erp_enteng_v2_6_11a_preconnect'
        and a.state <> 'idle'
    )::bigint as active_backend_count
),
profile_view as (
  select
    c.oid,
    c.relkind,
    pg_get_userbyid(c.relowner) as owner_name,
    coalesce(c.reloptions, array[]::text[]) as reloptions,
    pg_get_viewdef(c.oid, true) as definition,
    (
      select v.check_option
      from information_schema.views v
      where v.table_schema = n.nspname and v.table_name = c.relname
    ) as check_option,
    (
      select array_agg(a.attname::text order by a.attnum)
      from pg_attribute a
      where a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
    ) as columns
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public' and c.relname = 'v_erp_my_profile'
),
erp_inventory as (
  select
    (
      select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'erp' and c.relkind in ('r','p','v','m','f')
        and has_table_privilege('authenticated', c.oid, 'SELECT')
    )::bigint as auth_select_relations,
    (
      select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'erp' and c.relkind in ('r','p') and (
        has_table_privilege('authenticated', c.oid, 'INSERT')
        or has_table_privilege('authenticated', c.oid, 'UPDATE')
        or has_table_privilege('authenticated', c.oid, 'DELETE')
        or has_table_privilege('authenticated', c.oid, 'TRUNCATE')
      )
    )::bigint as auth_direct_write_tables,
    (
      select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
      where n.nspname = 'erp'
        and has_function_privilege('authenticated', p.oid, 'EXECUTE')
    )::bigint as auth_execute_functions
),
checks(check_name, passed, observed, expected) as (
  select
    '00_EXECUTION_QUIESCENT',
    lock_available and active_backend_count = 0,
    jsonb_build_object(
      'advisory_lock_available',lock_available,
      'active_tagged_backends',active_backend_count
    ),
    jsonb_build_object(
      'advisory_lock_available',true,
      'active_tagged_backends',0
    )
  from execution_guard

  union all
  select
    '01_external_target_lineage',
    (select count(*) from supabase_migrations.schema_migrations) = 50
      and exists (
        select 1 from supabase_migrations.schema_migrations
        where version = '20260826112217' and name = 'compact_replay_001'
      )
      and exists (
        select 1 from supabase_migrations.schema_migrations
        where version = '20260829185830'
          and name = 'erp_v2_6_10_fg_partial_completion'
      )
      and exists (
        select 1 from supabase_migrations.schema_migrations
        where version = '20260829204632'
          and name = 'erp_v2_6_11_operational_reservations_and_completion_scope'
      ),
    jsonb_build_object(
      'platform_count',(select count(*) from supabase_migrations.schema_migrations),
      'latest',(select jsonb_agg(jsonb_build_object('version',version,'name',name) order by version)
                from (select version,name from supabase_migrations.schema_migrations
                      order by version desc limit 3) x)
    ),
    jsonb_build_object(
      'external_project_ref','siimvrusnzxexizpyoib',
      'platform_count',50,
      'v2_6_10','20260829185830',
      'v2_6_11','20260829204632'
    )

  union all
  select
    '02_application_history_count',
    (select count(*) from erp.schema_migrations) = 41,
    to_jsonb((select count(*) from erp.schema_migrations)),
    '41'::jsonb

  union all
  select
    '03_application_history_exact_markers',
    (select count(*) from erp.schema_migrations
      where (version, description, installed_at) in (
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
      )) = 2
      and exists (
        select 1 from erp.schema_migrations
        where version = 'v2.6.11a'
          and description = 'UAT phase-0 public self-profile facade and direct legacy RPC closure'
          and installed_at is not null
      ),
    (select jsonb_agg(to_jsonb(x) order by version)
     from (select version,description,installed_at from erp.schema_migrations
           where version in ('v2.6.10','v2.6.11','v2.6.11a')) x),
    jsonb_build_object('versions',array['v2.6.10','v2.6.11','v2.6.11a'])

  union all
  select
    '04_release_pointer_semantics',
    exists (
      select 1 from erp.system_release_info
      where singleton_id = 1
        and release_version = '2.6.11'
        and installed_at = timestamptz '2026-08-29 20:46:32+00'
        and position('[v2.6.11a/UAT_PRECONNECT]' in coalesce(notes, '')) > 0
    ),
    (select jsonb_build_object(
       'release_version',release_version,
       'installed_at',installed_at,
       'closure_note',position('[v2.6.11a/UAT_PRECONNECT]' in coalesce(notes,'')) > 0
     ) from erp.system_release_info where singleton_id = 1),
    jsonb_build_object(
      'release_version','2.6.11',
      'installed_at','2026-08-29T20:46:32+00:00',
      'closure_note',true
    )

  union all
  select
    '05_schema_usage_boundary',
    has_schema_privilege('authenticated','public','USAGE')
      and has_schema_privilege('anon','public','USAGE')
      and has_schema_privilege('authenticated','erp','USAGE')
      and not has_schema_privilege('anon','erp','USAGE'),
    jsonb_build_object(
      'auth_public',has_schema_privilege('authenticated','public','USAGE'),
      'anon_public',has_schema_privilege('anon','public','USAGE'),
      'auth_erp',has_schema_privilege('authenticated','erp','USAGE'),
      'anon_erp',has_schema_privilege('anon','erp','USAGE')
    ),
    jsonb_build_object(
      'auth_public',true,'anon_public',true,'auth_erp',true,'anon_erp',false
    )

  union all
  select
    '06_public_relation_surface_exactly_one',
    (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relkind in ('r','p','v','m','f')) = 1
      and to_regclass('public.v_erp_my_profile') is not null,
    (select coalesce(jsonb_agg(jsonb_build_object(
       'name',c.relname,'kind',c.relkind
     ) order by c.relname),'[]'::jsonb)
     from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relkind in ('r','p','v','m','f')),
    '[{"name":"v_erp_my_profile","kind":"v"}]'::jsonb

  union all
  select
    '07_public_function_surface_empty',
    (select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public') = 0,
    to_jsonb((select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
              where n.nspname = 'public')),
    '0'::jsonb

  union all
  select
    '08_profile_view_security_options',
    exists (
      select 1 from profile_view
      where relkind = 'v'
        and owner_name = 'postgres'
        and check_option = 'LOCAL'
        and reloptions @> array['security_invoker=true','security_barrier=true']::text[]
    ),
    (select jsonb_build_object(
       'owner',owner_name,'check_option',check_option,'reloptions',reloptions
     ) from profile_view),
    jsonb_build_object(
      'owner','postgres','check_option','LOCAL',
      'reloptions',array['security_invoker=true','security_barrier=true']
    )

  union all
  select
    '09_profile_view_columns_exact',
    (select columns from profile_view) is not distinct from array[
      'id','auth_user_id','full_name','role','is_active','row_version'
    ]::text[],
    (select to_jsonb(columns) from profile_view),
    '["id","auth_user_id","full_name","role","is_active","row_version"]'::jsonb

  union all
  select
    '10_profile_view_explicit_self_filter',
    coalesce((select position('auth_user_id' in definition) > 0
            and position('auth.uid()' in definition) > 0 from profile_view), false),
    (select to_jsonb(definition) from profile_view),
    jsonb_build_object('requires','auth_user_id = auth.uid()')

  union all
  select
    '11_profile_view_acl_select_only',
    coalesce(has_table_privilege(
      'authenticated',(select oid from profile_view),'SELECT'
    ),false)
      and not coalesce(has_table_privilege(
        'anon',(select oid from profile_view),'SELECT'
      ),false)
      and not coalesce(has_table_privilege(
        'authenticated',(select oid from profile_view),'INSERT'
      ),false)
      and not coalesce(has_table_privilege(
        'authenticated',(select oid from profile_view),'UPDATE'
      ),false)
      and not coalesce(has_table_privilege(
        'authenticated',(select oid from profile_view),'DELETE'
      ),false)
      and not coalesce(has_table_privilege(
        'service_role',(select oid from profile_view),'SELECT'
      ),false)
      and not coalesce(has_table_privilege(
        'service_role',(select oid from profile_view),'INSERT'
      ),false)
      and not coalesce(has_table_privilege(
        'service_role',(select oid from profile_view),'UPDATE'
      ),false)
      and not coalesce(has_table_privilege(
        'service_role',(select oid from profile_view),'DELETE'
      ),false),
    jsonb_build_object(
      'auth_select',has_table_privilege('authenticated',(select oid from profile_view),'SELECT'),
      'anon_select',has_table_privilege('anon',(select oid from profile_view),'SELECT'),
      'auth_insert',has_table_privilege('authenticated',(select oid from profile_view),'INSERT'),
      'auth_update',has_table_privilege('authenticated',(select oid from profile_view),'UPDATE'),
      'auth_delete',has_table_privilege('authenticated',(select oid from profile_view),'DELETE'),
      'service_select',has_table_privilege('service_role',(select oid from profile_view),'SELECT'),
      'service_insert',has_table_privilege('service_role',(select oid from profile_view),'INSERT'),
      'service_update',has_table_privilege('service_role',(select oid from profile_view),'UPDATE'),
      'service_delete',has_table_privilege('service_role',(select oid from profile_view),'DELETE')
    ),
    jsonb_build_object(
      'auth_select',true,'anon_select',false,
      'auth_insert',false,'auth_update',false,'auth_delete',false,
      'service_select',false,'service_insert',false,
      'service_update',false,'service_delete',false
    )

  union all
  select
    '12_underlying_app_users_rls',
    exists (
      select 1 from pg_class c
      where c.oid = 'erp.app_users'::regclass and c.relrowsecurity
    )
      and has_table_privilege('authenticated','erp.app_users','SELECT')
      and not has_table_privilege('anon','erp.app_users','SELECT'),
    (select jsonb_build_object(
       'rls',c.relrowsecurity,
       'auth_select',has_table_privilege('authenticated',c.oid,'SELECT'),
       'anon_select',has_table_privilege('anon',c.oid,'SELECT')
     ) from pg_class c where c.oid = 'erp.app_users'::regclass),
    jsonb_build_object('rls',true,'auth_select',true,'anon_select',false)

  union all
  select
    '13_phase0_product_facades_absent',
    (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'erp'
       and c.relname in (
         'v_product_identity_history','v_product_price_current',
         'v_products_current','v_products_sellable'
       ) and has_table_privilege('authenticated',c.oid,'SELECT')) = 0,
    to_jsonb((select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
              where n.nspname = 'erp'
                and c.relname in (
                  'v_product_identity_history','v_product_price_current',
                  'v_products_current','v_products_sellable'
                ) and has_table_privilege('authenticated',c.oid,'SELECT'))),
    '0'::jsonb

  union all
  select
    '14_hidden_erp_acl_inventory',
    auth_select_relations = 176
      and auth_direct_write_tables = 64
      and auth_execute_functions = 177,
    to_jsonb(erp_inventory),
    jsonb_build_object(
      'auth_select_relations',176,
      'auth_direct_write_tables',64,
      'auth_execute_functions',177,
      'meaning','broad erp ACLs remain hidden; they are not a client allowlist security boundary'
    )
  from erp_inventory

  union all
  select
    '15_legacy_rpc_acl_closure',
    not has_function_privilege('authenticated','erp.run_v260_integrity_checks()','EXECUTE')
      and not has_function_privilege('anon','erp.run_v260_integrity_checks()','EXECUTE')
      and has_function_privilege('service_role','erp.run_v260_integrity_checks()','EXECUTE')
      and not has_function_privilege('authenticated','erp.post_sale(uuid)','EXECUTE')
      and not has_function_privilege('anon','erp.post_sale(uuid)','EXECUTE')
      and has_function_privilege('authenticated','erp.post_sale_v2(uuid,uuid,bigint)','EXECUTE'),
    jsonb_build_object(
      'run_v260_auth',has_function_privilege('authenticated','erp.run_v260_integrity_checks()','EXECUTE'),
      'run_v260_anon',has_function_privilege('anon','erp.run_v260_integrity_checks()','EXECUTE'),
      'run_v260_service',has_function_privilege('service_role','erp.run_v260_integrity_checks()','EXECUTE'),
      'post_sale_auth',has_function_privilege('authenticated','erp.post_sale(uuid)','EXECUTE'),
      'post_sale_anon',has_function_privilege('anon','erp.post_sale(uuid)','EXECUTE'),
      'post_sale_v2_auth',has_function_privilege('authenticated','erp.post_sale_v2(uuid,uuid,bigint)','EXECUTE')
    ),
    jsonb_build_object(
      'run_v260_auth',false,'run_v260_anon',false,'run_v260_service',true,
      'post_sale_auth',false,'post_sale_anon',false,'post_sale_v2_auth',true
    )

  union all
  select
    '16_verified_rpc_definition_hashes',
    md5(pg_get_functiondef(to_regprocedure('erp.run_v260_integrity_checks()')))
      = '73978086376e3c4d3e606ae8939544fd'
      and md5(pg_get_functiondef(to_regprocedure('erp.post_sale(uuid)')))
      = '195c2bfb86256c630f1400511ed15eb7'
      and md5(pg_get_functiondef(to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)')))
      = '980ad66e98cae68c61309ca2ad79eefb',
    jsonb_build_object(
      'run_v260',md5(pg_get_functiondef(to_regprocedure('erp.run_v260_integrity_checks()'))),
      'post_sale',md5(pg_get_functiondef(to_regprocedure('erp.post_sale(uuid)'))),
      'post_sale_v2',md5(pg_get_functiondef(to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)')))
    ),
    jsonb_build_object(
      'run_v260','73978086376e3c4d3e606ae8939544fd',
      'post_sale','195c2bfb86256c630f1400511ed15eb7',
      'post_sale_v2','980ad66e98cae68c61309ca2ad79eefb'
    )

  union all
  select
    '17_post_sale_v2_nested_contract',
    exists (
      select 1 from pg_proc p
      where p.oid = to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)')
        and pg_get_userbyid(p.proowner) = 'postgres'
        and p.prosecdef
        and p.proconfig = array[
          'search_path=erp, public, auth, extensions, pg_temp'
        ]::text[]
        and position('perform erp.require_internal();' in pg_get_functiondef(p.oid)) > 0
        and position('perform erp.post_sale(h.id);' in pg_get_functiondef(p.oid)) > 0
        and has_function_privilege(
          pg_get_userbyid(p.proowner),'erp.post_sale(uuid)','EXECUTE'
        )
    ),
    (select jsonb_build_object(
       'owner',pg_get_userbyid(p.proowner),
       'security_definer',p.prosecdef,
       'config',p.proconfig,
       'inner_call',position('perform erp.post_sale(h.id);' in pg_get_functiondef(p.oid)) > 0,
       'owner_inner_execute',has_function_privilege(
         pg_get_userbyid(p.proowner),'erp.post_sale(uuid)','EXECUTE'
       )
     ) from pg_proc p
     where p.oid = to_regprocedure('erp.post_sale_v2(uuid,uuid,bigint)')),
    jsonb_build_object(
      'owner','postgres','security_definer',true,
      'inner_call',true,'owner_inner_execute',true
    )
)
select check_name, passed, observed, expected
from (
  select
    '00_ALL_CHECKS_PASS'::text as check_name,
    coalesce(bool_and(passed), false) as passed,
    jsonb_build_object(
      'check_count',count(*),
      'failed',coalesce(jsonb_agg(check_name order by check_name)
        filter (where not passed),'[]'::jsonb)
    ) as observed,
    jsonb_build_object('failed','[]'::jsonb) as expected
  from checks

  union all

  select check_name, passed, observed, expected from checks
) result
order by check_name;
