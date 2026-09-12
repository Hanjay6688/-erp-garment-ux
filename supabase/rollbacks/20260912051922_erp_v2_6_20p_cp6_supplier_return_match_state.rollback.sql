-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20p -> exact O.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py after its
-- independently pinned trust checks, admission closure and session drain.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $platform_guard_v2620p$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20p_cp6_supplier_return_match_state')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260912051922'
         and name='erp_v2_6_20p_cp6_supplier_return_match_state'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('109a991d12643ff1c056fd984cea3b3a26bc9fe9d9d716f62c84c4bcb053c138','b805e85e1c01136cfa299f697ec57d7746b4c1d88c36b3a27cb81f9c0faa2b80'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260912051922') then
    raise exception 'P_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620p$;

lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table   erp.app_users,erp.idempotency_requests,erp.products,erp.audit_logs,
  erp.journal_entries,erp.journal_lines,erp.account_daily_balances,erp.sales_headers,
  erp.sales_items,erp.sale_stock_allocations,erp.sales_returns,erp.sales_return_items,
  erp.sales_payments,erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,
  erp.hpp_versions,erp.product_conversions,erp.product_conversion_allocations,erp.laundry_deliveries,
  erp.laundry_delivery_lines,erp.laundry_receipts,erp.laundry_failed_wash_attempts,erp.wip_stage_events,
  erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,erp.cp6_v2620i_rollback_capsule,erp.sales_payment_posting_facts,
  erp.sales_payment_reversal_facts,erp.cp6_v2620j_rollback_capsule,erp.cp6_v2620k_rollback_capsule,erp.accounting_period_control,
  erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts,erp.laundry_claims,
  erp.laundry_vendors,erp.cp6_v2620l_rollback_capsule,erp.opening_balance_headers,erp.opening_balance_items,
  erp.opening_subledger_balances,erp.opening_subledger_settlements,erp.opening_financial_corrections,erp.supplier_payments,
  erp.material_purchase_headers,erp.material_purchase_items,erp.material_supplier_invoices,erp.material_supplier_invoice_lines,
  erp.material_supplier_returns,erp.material_supplier_return_items,erp.material_purchase_cost_corrections,erp.material_purchase_cost_correction_items,
  erp.material_stock_movements,erp.material_rolls,erp.cost_recalc_queue,erp.cost_adjustments,
  erp.suppliers,erp.materials,erp.cp6_v2620m_rollback_capsule,erp.supplier_cent_posting_facts,
  erp.material_cost_history,erp.material_cost_revaluation_state,erp.material_cost_revaluation_events,erp.material_cost_checkpoints,
  erp.cp6_v2620n_rollback_capsule,erp.cp6_v2620o_rollback_capsule
in share row exclusive mode;
lock table erp.cp6_v2620p_rollback_capsule in access exclusive mode;

do $restore_guard_v2620p$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20o')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20p')
     or exists(select 1 from erp.schema_migrations
       where version not in('v2.6.20o','v2.6.20p')
         and installed_at>(select installed_at from erp.schema_migrations
           where version='v2.6.20p'))
     or (select count(*) from erp.cp6_v2620p_rollback_capsule)<>3 then
    raise exception 'P_ROLLBACK_MARKER_CAPSULE_OR_SUCCESSOR';
  end if;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()',
      '98fac1a865982d5c60fc5e6a5caae9033755ff915b7e53d22213c0d1d1765ca1',
      '17a07e10665756088f2faa0570c055efae4513abf1c5985afacf86bf8467e056',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_supplier_return(uuid)',
      'eff9b9a2a19eca7f51d51ac0fc73983d53f7fa5e4c699407813580dac91bbace',
      '541ce87729dd47bffd536847e71271c1e0b968d199e2fe24fd671a025cee027a',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()',
      'fc3edcc094fb4843886206466801f96441907d83efeed01c92c5604f658a96d0',
      '2c546026b1325e265c62828c13f2eea63aaff302c9a359d5f49c18d5fb7a492e',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex')
        definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
        installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c
    from erp.cp6_v2620p_rollback_capsule cap
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
      raise exception 'P_TRUSTED_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;

  select boundary_snapshot into v_expected
  from erp.cp6_v2620p_rollback_capsule limit 1;
  if v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>66
     or exists(select 1 from erp.cp6_v2620p_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'P_BOUNDARY_SNAPSHOT_MISMATCH';
  end if;
  foreach v_table in array array[
    'app_users','idempotency_requests','products','audit_logs',
    'journal_entries','journal_lines','account_daily_balances','sales_headers',
    'sales_items','sale_stock_allocations','sales_returns','sales_return_items',
    'sales_payments','fg_lots','fg_stock_movements','fg_inventory_balances',
    'hpp_versions','product_conversions','product_conversion_allocations','laundry_deliveries',
    'laundry_delivery_lines','laundry_receipts','laundry_failed_wash_attempts','wip_stage_events',
    'cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule','cp6_v2620i_rollback_capsule','sales_payment_posting_facts',
    'sales_payment_reversal_facts','cp6_v2620j_rollback_capsule','cp6_v2620k_rollback_capsule','accounting_period_control',
    'accounting_account_mappings','cash_accounts','chart_accounts','laundry_claims',
    'laundry_vendors','cp6_v2620l_rollback_capsule','opening_balance_headers','opening_balance_items',
    'opening_subledger_balances','opening_subledger_settlements','opening_financial_corrections','supplier_payments',
    'material_purchase_headers','material_purchase_items','material_supplier_invoices','material_supplier_invoice_lines',
    'material_supplier_returns','material_supplier_return_items','material_purchase_cost_corrections','material_purchase_cost_correction_items',
    'material_stock_movements','material_rolls','cost_recalc_queue','cost_adjustments',
    'suppliers','materials','cp6_v2620m_rollback_capsule','supplier_cent_posting_facts',
    'material_cost_history','material_cost_revaluation_state','material_cost_revaluation_events','material_cost_checkpoints',
    'cp6_v2620n_rollback_capsule','cp6_v2620o_rollback_capsule'
  ]::text[]
  loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'P_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;

  for c in select * from erp.cp6_v2620p_rollback_capsule
    order by object_regidentity
  loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()',
      '98fac1a865982d5c60fc5e6a5caae9033755ff915b7e53d22213c0d1d1765ca1'),
    ('erp.post_material_supplier_return(uuid)',
      'eff9b9a2a19eca7f51d51ac0fc73983d53f7fa5e4c699407813580dac91bbace'),
    ('erp.run_v267_financial_truth_checks()',
      'fc3edcc094fb4843886206466801f96441907d83efeed01c92c5604f658a96d0')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'P_ROLLBACK_RESTORE_HASH_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_guard_v2620p$;

drop table erp.cp6_v2620p_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20p';
delete from supabase_migrations.schema_migrations
where version='20260912051922'
  and name='erp_v2_6_20p_cp6_supplier_return_match_state'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('109a991d12643ff1c056fd984cea3b3a26bc9fe9d9d716f62c84c4bcb053c138','b805e85e1c01136cfa299f697ec57d7746b4c1d88c36b3a27cb81f9c0faa2b80');

do $postcheck_v2620p$
declare r record;v_actual text;
begin
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()',
      '98fac1a865982d5c60fc5e6a5caae9033755ff915b7e53d22213c0d1d1765ca1',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_supplier_return(uuid)',
      'eff9b9a2a19eca7f51d51ac0fc73983d53f7fa5e4c699407813580dac91bbace',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()',
      'fc3edcc094fb4843886206466801f96441907d83efeed01c92c5604f658a96d0',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'P_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20p')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20p_cp6_supplier_return_match_state')
     or to_regclass('erp.cp6_v2620p_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20o')
     or to_regclass('erp.cp6_v2620o_rollback_capsule') is null
     or to_regclass('erp.supplier_cent_posting_facts') is null then
    raise exception 'P_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620p$;
commit;
