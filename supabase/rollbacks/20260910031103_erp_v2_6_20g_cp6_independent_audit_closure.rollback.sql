-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20g -> exact F.
-- Never delete business history. Refuse any post-boundary content change,
-- forward-reconciliation output, successor, ledger ambiguity, or object drift.
begin;
set local lock_timeout='10s';
set local statement_timeout='240s';
lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;

do $platform_guard_v2620g$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20g_cp6_independent_audit_closure')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
      where name='erp_v2_6_20g_cp6_independent_audit_closure'
        and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
          in('645623b047e6c762cf078507450d260d712427ccd0b2c314113de856c4aff726','e9bc2d59dbd1da0facfaa01d2b955630710258e6b761e3ef114b95fc8c783724')) then
    raise exception 'v2.6.20g rollback refused: exact platform ledger identity is ambiguous';
  end if;
end
$platform_guard_v2620g$;

-- Same leading fence as authenticated/backend business entry points.
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.cp6_v2620g_rollback_capsule in access exclusive mode;
lock table erp.audit_logs,erp.journal_lines,
  erp.fg_adjustments,erp.fg_adjustment_items,
  erp.opening_balance_headers,erp.opening_balance_items,
  erp.opening_hpp_corrections,erp.material_stock_movements,
  erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,
  erp.hpp_versions,erp.opening_lot_hpp_gl_state,
  erp.non_po_hpp_gl_sync_events_v2620f,
  erp.sales_headers,erp.sales_items,erp.sale_stock_allocations,
  erp.sales_returns,erp.sales_return_items,
  erp.laundry_deliveries,erp.laundry_delivery_lines,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events
in share row exclusive mode;

do $guard_restore_v2620g$
declare r record; v_table text; v_hash text; v_expected jsonb; v_platform text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20g')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20f')
     or (select count(*) from erp.cp6_v2620g_rollback_capsule)<>7 then
    raise exception 'v2.6.20g rollback refused: required application markers/capsule absent';
  end if;
  select version into strict v_platform from supabase_migrations.schema_migrations
  where name='erp_v2_6_20g_cp6_independent_audit_closure';
  if exists(select 1 from supabase_migrations.schema_migrations where version>v_platform)
     or exists(select 1 from erp.schema_migrations where version<>'v2.6.20g'
       and installed_at>(select installed_at from erp.schema_migrations where version='v2.6.20g')) then
    raise exception 'v2.6.20g rollback refused: successor installed';
  end if;
  for r in select c.*,p.proowner,p.proacl from erp.cp6_v2620g_rollback_capsule c
    left join pg_proc p on p.oid=to_regprocedure(c.object_regidentity)
  loop
    if r.definition_sha256 is distinct from encode(extensions.digest(convert_to(r.object_definition,'UTF8'),'sha256'),'hex')
       or r.installed_definition_sha256 is null
       or r.installed_definition_sha256 is distinct from encode(extensions.digest(convert_to(
         pg_get_functiondef(to_regprocedure(r.object_regidentity)),'UTF8'),'sha256'),'hex')
       or pg_get_userbyid(r.proowner) is distinct from r.owner_snapshot
       or (case when r.proacl is null then null else array(select a::text from unnest(r.proacl) a order by a::text) end)
          is distinct from r.acl_snapshot then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20g object/capsule/ACL %',r.object_regidentity;
    end if;
  end loop;
  if exists(select 1 from erp.cp6_v2620g_rollback_capsule where boundary_snapshot is null)
     or (select count(distinct boundary_snapshot) from erp.cp6_v2620g_rollback_capsule)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20g boundary snapshot';
  end if;
  select boundary_snapshot into v_expected from erp.cp6_v2620g_rollback_capsule limit 1;
  if (select count(*) from jsonb_object_keys(v_expected))<>27 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20g incomplete business boundary';
  end if;
  foreach v_table in array array['app_users','idempotency_requests','products','audit_logs','journal_entries','journal_lines','fg_adjustments','fg_adjustment_items','opening_balance_headers','opening_balance_items','opening_hpp_corrections','material_stock_movements','fg_lots','fg_stock_movements','fg_inventory_balances','hpp_versions','opening_lot_hpp_gl_state','non_po_hpp_gl_sync_events_v2620f','sales_headers','sales_items','sale_stock_allocations','sales_returns','sales_return_items','laundry_deliveries','laundry_delivery_lines','laundry_failed_wash_attempts','wip_stage_events']
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'v2.6.20g rollback refused: post-install reconciliation or business history exists (%)',v_table;
    end if;
  end loop;
  for r in select * from erp.cp6_v2620g_rollback_capsule order by object_identity
  loop
    -- CREATE OR REPLACE preserves the exact owner/ACL already checked above.
    execute r.object_definition;
    if encode(extensions.digest(convert_to(pg_get_functiondef(
        to_regprocedure(r.object_regidentity)),'UTF8'),'sha256'),'hex') is distinct from r.definition_sha256 then
      raise exception 'v2.6.20g rollback restore hash mismatch: %',r.object_regidentity;
    end if;
  end loop;
end
$guard_restore_v2620g$;

drop table erp.cp6_v2620g_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20g';
delete from supabase_migrations.schema_migrations
where name='erp_v2_6_20g_cp6_independent_audit_closure'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('645623b047e6c762cf078507450d260d712427ccd0b2c314113de856c4aff726','e9bc2d59dbd1da0facfaa01d2b955630710258e6b761e3ef114b95fc8c783724');

do $postcheck_v2620g$
begin
  if exists(select 1 from erp.schema_migrations where version='v2.6.20g')
     or exists(select 1 from supabase_migrations.schema_migrations where name='erp_v2_6_20g_cp6_independent_audit_closure')
     or to_regclass('erp.cp6_v2620g_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20f') then
    raise exception 'v2.6.20g rollback postcondition failed';
  end if;
end
$postcheck_v2620g$;
commit;
