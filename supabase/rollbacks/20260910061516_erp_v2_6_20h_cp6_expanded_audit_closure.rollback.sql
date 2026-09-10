-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20h -> exact G.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py. The
-- controller closes database admission and drains old function generations
-- before these exact bytes run. This SQL still refuses any business use,
-- reconciliation, successor, ledger ambiguity, ACL drift, or content drift.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';
lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;

do $platform_guard_v2620h$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20h_cp6_expanded_audit_closure')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
      where name='erp_v2_6_20h_cp6_expanded_audit_closure'
        and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
          in('e16dbb655164595be273c03582d35c9ac33593136bd418fdd87156e592f292b8',
             'bcac43cd1cca5214f8678cd058caf6ff19ce90bdebd1c31f47675c0efd79a36f')) then
    raise exception 'v2.6.20h rollback refused: exact platform ledger identity is ambiguous';
  end if;
end
$platform_guard_v2620h$;

lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.cp6_v2620h_rollback_capsule in access exclusive mode;
lock table erp.audit_logs,erp.journal_lines,erp.account_daily_balances,
  erp.sales_headers,erp.sales_items,erp.sale_stock_allocations,
  erp.sales_returns,erp.sales_return_items,erp.sales_payments,
  erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,
  erp.hpp_versions,erp.product_conversions,erp.product_conversion_allocations,
  erp.laundry_deliveries,erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events
in share row exclusive mode;

do $guard_restore_v2620h$
declare r record; v_table text; v_hash text; v_expected jsonb; v_platform text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20h')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20g')
     or (select count(*) from erp.cp6_v2620h_rollback_capsule)<>6 then
    raise exception 'v2.6.20h rollback refused: required application markers/capsule absent';
  end if;
  select version into strict v_platform from supabase_migrations.schema_migrations
  where name='erp_v2_6_20h_cp6_expanded_audit_closure';
  if exists(select 1 from supabase_migrations.schema_migrations where version>v_platform)
     or exists(select 1 from erp.schema_migrations where version<>'v2.6.20h'
       and installed_at>(select installed_at from erp.schema_migrations where version='v2.6.20h')) then
    raise exception 'v2.6.20h rollback refused: successor installed';
  end if;
  for r in select c.*,p.proowner,p.proacl from erp.cp6_v2620h_rollback_capsule c
    left join pg_proc p on p.oid=to_regprocedure(c.object_regidentity)
  loop
    if r.definition_sha256 is distinct from encode(extensions.digest(convert_to(r.object_definition,'UTF8'),'sha256'),'hex')
       or r.installed_definition_sha256 is null
       or r.installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(
         pg_get_functiondef(to_regprocedure(r.object_regidentity)),'UTF8'),'sha256'),'hex')
       or pg_get_userbyid(r.proowner) is distinct from r.owner_snapshot
       or (case when r.proacl is null then null else array(select a::text from unnest(r.proacl) a order by a::text) end)
          is distinct from r.acl_snapshot then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20h object/capsule/ACL %',r.object_regidentity;
    end if;
  end loop;
  if exists(select 1 from erp.cp6_v2620h_rollback_capsule where boundary_snapshot is null)
     or (select count(distinct boundary_snapshot) from erp.cp6_v2620h_rollback_capsule)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20h boundary snapshot';
  end if;
  select boundary_snapshot into v_expected from erp.cp6_v2620h_rollback_capsule limit 1;
  if (select count(*) from jsonb_object_keys(v_expected))<>24 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20h incomplete business boundary';
  end if;
  foreach v_table in array array[
    'app_users','idempotency_requests','products','audit_logs',
    'journal_entries','journal_lines','account_daily_balances',
    'sales_headers','sales_items','sale_stock_allocations',
    'sales_returns','sales_return_items','sales_payments',
    'fg_lots','fg_stock_movements','fg_inventory_balances','hpp_versions',
    'product_conversions','product_conversion_allocations',
    'laundry_deliveries','laundry_delivery_lines','laundry_receipts',
    'laundry_failed_wash_attempts','wip_stage_events'
  ]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'v2.6.20h rollback refused: post-install business history exists (%)',v_table;
    end if;
  end loop;
  for r in select * from erp.cp6_v2620h_rollback_capsule order by object_identity
  loop
    execute r.object_definition;
    if encode(extensions.digest(convert_to(pg_get_functiondef(
        to_regprocedure(r.object_regidentity)),'UTF8'),'sha256'),'hex') is distinct from r.definition_sha256 then
      raise exception 'v2.6.20h rollback restore hash mismatch: %',r.object_regidentity;
    end if;
  end loop;
end
$guard_restore_v2620h$;

drop table erp.cp6_v2620h_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20h';
delete from supabase_migrations.schema_migrations
where name='erp_v2_6_20h_cp6_expanded_audit_closure'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('e16dbb655164595be273c03582d35c9ac33593136bd418fdd87156e592f292b8',
       'bcac43cd1cca5214f8678cd058caf6ff19ce90bdebd1c31f47675c0efd79a36f');

do $postcheck_v2620h$
begin
  if exists(select 1 from erp.schema_migrations where version='v2.6.20h')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20h_cp6_expanded_audit_closure')
     or to_regclass('erp.cp6_v2620h_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20g') then
    raise exception 'v2.6.20h rollback postcondition failed';
  end if;
end
$postcheck_v2620h$;
commit;
