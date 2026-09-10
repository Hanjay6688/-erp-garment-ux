-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20i -> exact H.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py. The
-- controller verifies independently pinned source/capsule/function trust roots,
-- closes database admission, and drains old invocations before these bytes run.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';
lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;

do $platform_guard_v2620i$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20i_cp6_h2_audit_closure')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
      where name='erp_v2_6_20i_cp6_h2_audit_closure'
        and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
          in('01db1c8f2d59485c1c42567ec2d1318de156397483b1d0afd30a16b27450b683',
             '60fa613e31d13f7db3efff7f1e0daee956886afe2676c61ee05661bb55211a1c')) then
    raise exception 'v2.6.20i rollback refused: exact platform ledger identity is ambiguous';
  end if;
end
$platform_guard_v2620i$;

lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule
in share row exclusive mode;
lock table erp.cp6_v2620i_rollback_capsule in access exclusive mode;
lock table erp.audit_logs,erp.journal_lines,erp.account_daily_balances,
  erp.sales_headers,erp.sales_items,erp.sale_stock_allocations,
  erp.sales_returns,erp.sales_return_items,erp.sales_payments,
  erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,
  erp.hpp_versions,erp.product_conversions,erp.product_conversion_allocations,
  erp.laundry_deliveries,erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events
in share row exclusive mode;

do $guard_restore_v2620i$
declare
  c record;
  v_table text;
  v_hash text;
  v_expected jsonb;
  v_platform text;
  v_actual text;
  v_acl text[];
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20i')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20h')
     or (select count(*) from erp.cp6_v2620i_rollback_capsule)<>1 then
    raise exception 'v2.6.20i rollback refused: required application markers/capsule absent';
  end if;
  select version into strict v_platform from supabase_migrations.schema_migrations
  where name='erp_v2_6_20i_cp6_h2_audit_closure';
  if exists(select 1 from supabase_migrations.schema_migrations where version>v_platform)
     or exists(select 1 from erp.schema_migrations where version<>'v2.6.20i'
       and installed_at>(select installed_at from erp.schema_migrations where version='v2.6.20i')) then
    raise exception 'v2.6.20i rollback refused: successor installed';
  end if;

  select i.*,
    encode(extensions.digest(convert_to(i.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
    encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
    pg_get_userbyid(p.proowner) installed_owner,
    case when p.proacl is null then null else
      array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
  into c
  from erp.cp6_v2620i_rollback_capsule i
  left join pg_proc p on p.oid=to_regprocedure(i.object_regidentity);
  v_acl:=array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[];
  if c.object_regidentity is distinct from 'erp.run_v268_financial_report_checks()'
     or c.definition_sha256 is distinct from '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f'
     or c.definition_actual is distinct from '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f'
     or c.installed_definition_sha256 is distinct from 'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1'
     or c.installed_actual is distinct from 'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1'
     or c.owner_snapshot is distinct from 'postgres'
     or c.installed_owner is distinct from 'postgres'
     or c.acl_snapshot is distinct from v_acl
     or c.installed_acl is distinct from v_acl then
    raise exception 'TRUSTED_PREDECESSOR_PIN_MISMATCH: v2.6.20i report capsule/function';
  end if;

  if c.boundary_snapshot is null
     or (select count(*) from jsonb_object_keys(c.boundary_snapshot))<>26 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20i incomplete business boundary';
  end if;
  v_expected:=c.boundary_snapshot;
  foreach v_table in array array[
    'app_users','idempotency_requests','products','audit_logs',
    'journal_entries','journal_lines','account_daily_balances',
    'sales_headers','sales_items','sale_stock_allocations',
    'sales_returns','sales_return_items','sales_payments',
    'fg_lots','fg_stock_movements','fg_inventory_balances','hpp_versions',
    'product_conversions','product_conversion_allocations',
    'laundry_deliveries','laundry_delivery_lines','laundry_receipts',
    'laundry_failed_wash_attempts','wip_stage_events',
    'cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule'
  ]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'v2.6.20i rollback refused: post-install business history exists (%)',v_table;
    end if;
  end loop;

  execute c.object_definition;
  select encode(extensions.digest(convert_to(pg_get_functiondef(
    'erp.run_v268_financial_report_checks()'::regprocedure),'UTF8'),'sha256'),'hex') into v_actual;
  if v_actual<>'3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f' then
    raise exception 'v2.6.20i rollback restore hash mismatch: %',v_actual;
  end if;
end
$guard_restore_v2620i$;

drop table erp.cp6_v2620i_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20i';
delete from supabase_migrations.schema_migrations
where name='erp_v2_6_20i_cp6_h2_audit_closure'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('01db1c8f2d59485c1c42567ec2d1318de156397483b1d0afd30a16b27450b683',
       '60fa613e31d13f7db3efff7f1e0daee956886afe2676c61ee05661bb55211a1c');

do $postcheck_v2620i$
declare v_actual text;
begin
  select encode(extensions.digest(convert_to(pg_get_functiondef(
    'erp.run_v268_financial_report_checks()'::regprocedure),'UTF8'),'sha256'),'hex') into v_actual;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20i')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20i_cp6_h2_audit_closure')
     or to_regclass('erp.cp6_v2620i_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20h')
     or to_regclass('erp.cp6_v2620h_rollback_capsule') is null
     or v_actual<>'3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f' then
    raise exception 'v2.6.20i rollback postcondition failed';
  end if;
end
$postcheck_v2620i$;
commit;
