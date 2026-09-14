-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20aa -> exact Z.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py after its
-- independently pinned trust checks, admission closure and session drain.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $platform_guard_v2620aa$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20aa_cp6_material_cost_business_day')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260914163608'
         and name='erp_v2_6_20aa_cp6_material_cost_business_day'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('2ada33f0d04da6589b92646652a482290ef614e500c6abb026011823f6ebcfc7',
              '63c1b52a4e1ab8c329135ba0c4502c303be0cde0bb28bbc9f34413f191eb13fc'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260914163608') then
    raise exception 'AA_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620aa$;

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
lock table erp.cp6_v2620aa_rollback_capsule in access exclusive mode;

do $lock_all_erp_v2620aa$
declare v_table text;
begin
  for v_table in select relation.relname from pg_class relation join pg_namespace namespace on namespace.oid=relation.relnamespace where namespace.nspname='erp' and relation.relkind in('r','p') and relation.relname not in('schema_migrations','cp6_v2620aa_rollback_capsule') order by relation.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620aa$;

do $restore_guard_v2620aa$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20z')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20aa')
     or exists(select 1 from erp.schema_migrations
       where version not in('v2.6.20z','v2.6.20aa')
         and installed_at>(select installed_at from erp.schema_migrations
           where version='v2.6.20aa'))
     or (select count(*) from erp.cp6_v2620aa_rollback_capsule)<>2 then
    raise exception 'AA_ROLLBACK_MARKER_CAPSULE_OR_SUCCESSOR';
  end if;
  for r in select * from(values
    ('erp.refresh_material_cost_checkpoint(uuid,date)','cbb3d27608c720380b099a020a2f54b639ffc9626d3a09fd258402eb15511978','7eea402dec46b03d5425ef9c1c052ca409de7fafa72000b7abef5fda6849b30a',array['postgres=X/postgres']::text[]),
    ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','e70bce5bc64114ac0dad5c0ccbc374a63590089d9f481007d6c609f82f323399','c1f74ab9e855bf354d62f0e9053883c7cc0efdfeb329de8f2e081e46852f50b6',array['postgres=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c
    from erp.cp6_v2620aa_rollback_capsule cap
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
      raise exception 'AA_TRUSTED_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;

  select boundary_snapshot into v_expected
  from erp.cp6_v2620aa_rollback_capsule limit 1;
  if (select count(*) from (select relation.relname from pg_class relation join pg_namespace namespace on namespace.oid=relation.relnamespace where namespace.nspname='erp' and relation.relkind in('r','p') and relation.relname not in('schema_migrations','cp6_v2620aa_rollback_capsule') order by relation.relname) all_erp_tables)<>212
     or v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>212
     or exists(select 1 from erp.cp6_v2620aa_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'AA_BOUNDARY_SNAPSHOT_MISMATCH';
  end if;
  for v_table in select relation.relname from pg_class relation join pg_namespace namespace on namespace.oid=relation.relnamespace where namespace.nspname='erp' and relation.relkind in('r','p') and relation.relname not in('schema_migrations','cp6_v2620aa_rollback_capsule') order by relation.relname loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'AA_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;

  for c in select * from erp.cp6_v2620aa_rollback_capsule
    order by object_regidentity
  loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp.refresh_material_cost_checkpoint(uuid,date)','cbb3d27608c720380b099a020a2f54b639ffc9626d3a09fd258402eb15511978'),
    ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','e70bce5bc64114ac0dad5c0ccbc374a63590089d9f481007d6c609f82f323399')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'AA_ROLLBACK_RESTORE_HASH_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_guard_v2620aa$;

drop table erp.cp6_v2620aa_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20aa';
delete from supabase_migrations.schema_migrations
where version='20260914163608'
  and name='erp_v2_6_20aa_cp6_material_cost_business_day'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('2ada33f0d04da6589b92646652a482290ef614e500c6abb026011823f6ebcfc7',
       '63c1b52a4e1ab8c329135ba0c4502c303be0cde0bb28bbc9f34413f191eb13fc');

do $postcheck_v2620aa$
declare r record;v_actual text;
begin
  for r in select * from(values
    ('erp.refresh_material_cost_checkpoint(uuid,date)','cbb3d27608c720380b099a020a2f54b639ffc9626d3a09fd258402eb15511978',array['postgres=X/postgres']::text[]),
    ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','e70bce5bc64114ac0dad5c0ccbc374a63590089d9f481007d6c609f82f323399',array['postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'AA_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20aa')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20aa_cp6_material_cost_business_day')
     or to_regclass('erp.cp6_v2620aa_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20z')
     or to_regclass('erp.cp6_v2620u_rollback_capsule') is null
     or to_regclass('erp.cp6_v2620v_rollback_capsule') is null
     or to_regclass('erp.cp6_v2620w_rollback_capsule') is null
     or to_regclass('erp.cp6_v2620z_rollback_capsule') is null
     or to_regclass('erp.material_adjustment_revaluation_facts') is null
     or to_regprocedure('erp._cp6_material_adjustment_revaluation_state(uuid)') is null
     or to_regprocedure('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)') is null
     or to_regprocedure('erp.guard_material_adjustment_revaluation_fact_v2620t()') is null then
    raise exception 'AA_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620aa$;
commit;
