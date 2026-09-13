-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20x -> exact W.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py after its
-- independently pinned trust checks, admission closure and session drain.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $platform_guard_v2620x$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20x_cp6_internal_role_fail_closed')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260913202948'
         and name='erp_v2_6_20x_cp6_internal_role_fail_closed'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('53af147202671e5919a49080ed135ab9896399867bbb71065ef2da57f6543117',
              'ae81dc594310794596a32d5719aa76068eb2b47f3898bc2780c48cc2419dccac'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260913202948') then
    raise exception 'X_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620x$;

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
lock table erp.cp6_v2620x_rollback_capsule in access exclusive mode;

do $lock_all_erp_v2620x$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620x_rollback_capsule') order by c.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620x$;

do $restore_guard_v2620x$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20w')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20x')
     or exists(select 1 from erp.schema_migrations
       where version not in('v2.6.20w','v2.6.20x')
         and installed_at>(select installed_at from erp.schema_migrations
           where version='v2.6.20x'))
     or (select count(*) from erp.cp6_v2620x_rollback_capsule)<>1 then
    raise exception 'X_ROLLBACK_MARKER_CAPSULE_OR_SUCCESSOR';
  end if;
  for r in select * from(values
    ('erp.require_internal()','da4bc536f6a9b4f882c6985ee981bd4f1ea63cf3575390389d8798e3654fa91f','5dffcd53c0a5de609ae41482ca246d2afc806b9d92241253d680cf5c7fe1612e',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c
    from erp.cp6_v2620x_rollback_capsule cap
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
      raise exception 'X_TRUSTED_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;

  select boundary_snapshot into v_expected
  from erp.cp6_v2620x_rollback_capsule limit 1;
  if (select count(*) from (select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620x_rollback_capsule') order by c.relname) all_erp_tables)<>209
     or v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>209
     or exists(select 1 from erp.cp6_v2620x_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'X_BOUNDARY_SNAPSHOT_MISMATCH';
  end if;
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620x_rollback_capsule') order by c.relname loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'X_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;

  for c in select * from erp.cp6_v2620x_rollback_capsule
    order by object_regidentity
  loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp.require_internal()','da4bc536f6a9b4f882c6985ee981bd4f1ea63cf3575390389d8798e3654fa91f')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'X_ROLLBACK_RESTORE_HASH_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_guard_v2620x$;

drop table erp.cp6_v2620x_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20x';
delete from supabase_migrations.schema_migrations
where version='20260913202948'
  and name='erp_v2_6_20x_cp6_internal_role_fail_closed'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('53af147202671e5919a49080ed135ab9896399867bbb71065ef2da57f6543117',
       'ae81dc594310794596a32d5719aa76068eb2b47f3898bc2780c48cc2419dccac');

do $postcheck_v2620x$
declare r record;v_actual text;
begin
  for r in select * from(values
    ('erp.require_internal()','da4bc536f6a9b4f882c6985ee981bd4f1ea63cf3575390389d8798e3654fa91f',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'X_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20x')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20x_cp6_internal_role_fail_closed')
     or to_regclass('erp.cp6_v2620x_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20w')
     or to_regclass('erp.cp6_v2620u_rollback_capsule') is null
     or to_regclass('erp.cp6_v2620v_rollback_capsule') is null
     or to_regclass('erp.cp6_v2620w_rollback_capsule') is null
     or to_regclass('erp.material_adjustment_revaluation_facts') is null
     or to_regprocedure('erp._cp6_material_adjustment_revaluation_state(uuid)') is null
     or to_regprocedure('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)') is null
     or to_regprocedure('erp.guard_material_adjustment_revaluation_fact_v2620t()') is null then
    raise exception 'X_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620x$;
commit;
