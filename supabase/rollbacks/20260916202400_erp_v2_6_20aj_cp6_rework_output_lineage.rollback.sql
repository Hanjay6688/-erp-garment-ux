-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20aj -> exact AI.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py after its
-- independently pinned trust checks, admission closure and session drain.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $platform_guard_v2620aj$
begin
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20aj_cp6_rework_output_lineage')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260916202400' and name='erp_v2_6_20aj_cp6_rework_output_lineage'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('2e6cd4e94b52a27c83d2ba134a996c1db66a6f7ff617a5895f8c14769673f9ea','6764f9aa8af51ff7955fa582bb1a37c3c3c15a0f480194e2e77982dc447a0f11'))
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260916202400') then
    raise exception 'AJ_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620aj$;

lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.audit_logs,erp.journal_entries,erp.journal_lines,
  erp.account_daily_balances,erp.sales_headers,erp.sales_items,
  erp.sale_stock_allocations,erp.sales_returns,erp.sales_return_items,
  erp.sales_payments,erp.fg_lots,erp.fg_stock_movements,
  erp.fg_inventory_balances,erp.hpp_versions,erp.product_conversions,
  erp.product_conversion_allocations,erp.laundry_deliveries,
  erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events,
  erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,erp.sales_payment_posting_facts,
  erp.sales_payment_reversal_facts,erp.cp6_v2620j_rollback_capsule,
  erp.cp6_v2620k_rollback_capsule,erp.accounting_period_control,
  erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts,
  erp.laundry_claims,erp.laundry_vendors,erp.cp6_v2620l_rollback_capsule,
  erp.opening_balance_headers,erp.opening_balance_items,
  erp.opening_subledger_balances,erp.opening_subledger_settlements,
  erp.opening_financial_corrections,erp.supplier_payments,
  erp.material_purchase_headers,erp.material_purchase_items,
  erp.material_supplier_invoices,erp.material_supplier_invoice_lines,
  erp.material_supplier_returns,erp.material_supplier_return_items,
  erp.material_purchase_cost_corrections,
  erp.material_purchase_cost_correction_items,erp.material_stock_movements,
  erp.material_rolls,erp.cost_recalc_queue,erp.cost_adjustments,
  erp.suppliers,erp.materials,erp.cp6_v2620m_rollback_capsule,
  erp.supplier_cent_posting_facts,erp.material_cost_history,
  erp.material_cost_revaluation_state,erp.material_cost_revaluation_events,
  erp.material_cost_checkpoints,erp.cp6_v2620n_rollback_capsule,
  erp.cp6_v2620o_rollback_capsule,erp.cp6_v2620p_rollback_capsule,
  erp.cp6_v2620q_rollback_capsule,erp.cp6_v2620r_rollback_capsule,
  erp.cp6_v2620s_rollback_capsule,erp.material_adjustments,
  erp.material_adjustment_items,erp.material_adjustment_revaluation_facts,
  erp.cp6_v2620t_rollback_capsule,erp.cp6_v2620u_rollback_capsule,
  erp.misc_finance_transactions,erp.misc_finance_categories,
  erp.cp6_v2620v_rollback_capsule,erp.scrap_batches,erp.scrap_sales,
  erp.cp6_v2620w_rollback_capsule,erp.app_roles,erp.app_role_permissions,erp.app_permissions,erp.cutting_bridge_execution_context,erp.bs_resolution_execution_context,erp.cp6_laundry_qc_execution_context
in share row exclusive mode;
lock table erp.cp6_v2620aj_rollback_capsule in access exclusive mode;

do $lock_all_erp_v2620aj$
declare v_table text;
begin
  for v_table in select relation.relname from pg_class relation join pg_namespace namespace on namespace.oid=relation.relnamespace where namespace.nspname='erp' and relation.relkind in('r','p') and relation.relname not in('schema_migrations','cp6_v2620aj_rollback_capsule') order by relation.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620aj$;

do $restore_guard_v2620aj$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20ai')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20aj')
     or exists(select 1 from erp.schema_migrations
       where version not in('v2.6.20ai','v2.6.20aj')
         and installed_at>(select installed_at from erp.schema_migrations where version='v2.6.20aj'))
     or (select count(*) from erp.cp6_v2620aj_rollback_capsule)<>6 then
    raise exception 'AJ_ROLLBACK_MARKER_CAPSULE_OR_SUCCESSOR';
  end if;
  for r in select * from(values
    ('erp.post_rework_completion(uuid)','209338cc2b3099b163c0b344d1706a1f42dbdf804307e5fadee08e02f966f34d','63116e419dbbb6e59296416793288d785a348a30cdc46aad7eb44d097444d6c3',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.rebuild_po_hpp(uuid,text)','9bbadaead01d33c7d23cab2172b1cc0b04a9fbe210bfab8a4d2724e936e6ef9b','4e2e96017513d4990c9b2f8da2edf666b992ba016c8d688ea336daba36202d1f',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.cp6_lot_failed_wash_cost_v2620e(uuid)','cc02ece93afca767142d997fc6210c6d0d700633a998262fe95dd5435ea794bb','e8627bc0891322148819e17aca7a98b1177014b6ece6234ec7940e0876e896e1',array['postgres=X/postgres']::text[]),
    ('erp._validate_migration_batch_base(uuid)','78f165c0b42edec0cfa8e3fa295abb64b94cde0df9af9b5611b5f6e4ec3e1fb6','eb6fc2bc6cf419a72be75891d145782dbb1dec06186243834c2a444fc1fa9801',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.validate_migration_opening_stock_costs(uuid)','3b2316af1604ff6bc355ea3b7bb6559e32d41fa4c96b35af7e5f8c3bccb905e7','8223a856b0a0cd66d29a9eba31ebb6644434f934d910f184947a35ae0ffa77a0',array['postgres=X/postgres']::text[]),
    ('erp.validate_migration_batch(uuid)','166aa25ae8bce86daedffc82f5db2cb3266a310b374518672080a08345271b26','88bd4f2283fbdbea3faf2c4694426e87c71883c770243ddb44818797b0f22482',array['authenticated=X/postgres','postgres=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from erp.cp6_v2620aj_rollback_capsule cap
    left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
    where cap.object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or c.definition_actual is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.installed_actual is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or c.installed_owner is distinct from 'postgres'
       or c.installed_acl is distinct from r.acl then
      raise exception 'AJ_TRUSTED_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;
  select boundary_snapshot into v_expected from erp.cp6_v2620aj_rollback_capsule limit 1;
  if (select count(*) from (
       select relation.relname from pg_class relation
       join pg_namespace namespace on namespace.oid=relation.relnamespace
       where namespace.nspname='erp' and relation.relkind in('r','p')
         and relation.relname not in('schema_migrations','cp6_v2620aj_rollback_capsule')
     ) all_erp_tables)<>222
     or v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>222
     or exists(select 1 from erp.cp6_v2620aj_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'AJ_BOUNDARY_SNAPSHOT_MISMATCH';
  end if;
  for v_table in
    select relation.relname from pg_class relation
    join pg_namespace namespace on namespace.oid=relation.relnamespace
    where namespace.nspname='erp' and relation.relkind in('r','p')
      and relation.relname not in('schema_migrations','cp6_v2620aj_rollback_capsule')
    order by relation.relname
  loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'AJ_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;
  for c in select * from erp.cp6_v2620aj_rollback_capsule order by object_regidentity loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp.post_rework_completion(uuid)','209338cc2b3099b163c0b344d1706a1f42dbdf804307e5fadee08e02f966f34d'),
    ('erp.rebuild_po_hpp(uuid,text)','9bbadaead01d33c7d23cab2172b1cc0b04a9fbe210bfab8a4d2724e936e6ef9b'),
    ('erp.cp6_lot_failed_wash_cost_v2620e(uuid)','cc02ece93afca767142d997fc6210c6d0d700633a998262fe95dd5435ea794bb'),
    ('erp._validate_migration_batch_base(uuid)','78f165c0b42edec0cfa8e3fa295abb64b94cde0df9af9b5611b5f6e4ec3e1fb6'),
    ('erp.validate_migration_opening_stock_costs(uuid)','3b2316af1604ff6bc355ea3b7bb6559e32d41fa4c96b35af7e5f8c3bccb905e7'),
    ('erp.validate_migration_batch(uuid)','166aa25ae8bce86daedffc82f5db2cb3266a310b374518672080a08345271b26')
  ) expected(identity,sha256) loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'AJ_ROLLBACK_RESTORE_HASH_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_guard_v2620aj$;

drop table erp.cp6_v2620aj_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20aj';
delete from supabase_migrations.schema_migrations
where version='20260916202400'
  and name='erp_v2_6_20aj_cp6_rework_output_lineage'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('2e6cd4e94b52a27c83d2ba134a996c1db66a6f7ff617a5895f8c14769673f9ea',
       '6764f9aa8af51ff7955fa582bb1a37c3c3c15a0f480194e2e77982dc447a0f11');

do $postcheck_v2620aj$
declare r record;v_actual text;
begin
  for r in select * from(values
    ('erp.post_rework_completion(uuid)','209338cc2b3099b163c0b344d1706a1f42dbdf804307e5fadee08e02f966f34d',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.rebuild_po_hpp(uuid,text)','9bbadaead01d33c7d23cab2172b1cc0b04a9fbe210bfab8a4d2724e936e6ef9b',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.cp6_lot_failed_wash_cost_v2620e(uuid)','cc02ece93afca767142d997fc6210c6d0d700633a998262fe95dd5435ea794bb',array['postgres=X/postgres']::text[]),
    ('erp._validate_migration_batch_base(uuid)','78f165c0b42edec0cfa8e3fa295abb64b94cde0df9af9b5611b5f6e4ec3e1fb6',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.validate_migration_opening_stock_costs(uuid)','3b2316af1604ff6bc355ea3b7bb6559e32d41fa4c96b35af7e5f8c3bccb905e7',array['postgres=X/postgres']::text[]),
    ('erp.validate_migration_batch(uuid)','166aa25ae8bce86daedffc82f5db2cb3266a310b374518672080a08345271b26',array['authenticated=X/postgres','postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'AJ_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20aj')
     or exists(select 1 from supabase_migrations.schema_migrations where name='erp_v2_6_20aj_cp6_rework_output_lineage')
     or to_regclass('erp.cp6_v2620aj_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20ai')
     or to_regclass('erp.cp6_v2620ai_rollback_capsule') is null then
    raise exception 'AJ_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620aj$;
commit;
