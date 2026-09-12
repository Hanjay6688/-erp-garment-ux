-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20s -> exact R.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py after its
-- independently pinned trust checks, admission closure and session drain.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $platform_guard_v2620s$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20s_cp6_supplier_payment_business_date')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260912132445'
         and name='erp_v2_6_20s_cp6_supplier_payment_business_date'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('c9e35612100f0e387a7fdb80fda382ea1212df0cf5200ebceeaf67df9f77cf1f','e0516a4533c76c416f6385cb07c33ab9ea9a7a50386fa818ac6c232fd5e21b7d'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260912132445') then
    raise exception 'S_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620s$;

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
  erp.cp6_v2620n_rollback_capsule,erp.cp6_v2620o_rollback_capsule,erp.cp6_v2620p_rollback_capsule,erp.cp6_v2620q_rollback_capsule,erp.cp6_v2620r_rollback_capsule
in share row exclusive mode;
lock table erp.cp6_v2620s_rollback_capsule in access exclusive mode;

do $restore_guard_v2620s$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20r')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20s')
     or exists(select 1 from erp.schema_migrations
       where version not in('v2.6.20r','v2.6.20s')
         and installed_at>(select installed_at from erp.schema_migrations
           where version='v2.6.20s'))
     or (select count(*) from erp.cp6_v2620s_rollback_capsule)<>3 then
    raise exception 'S_ROLLBACK_MARKER_CAPSULE_OR_SUCCESSOR';
  end if;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()',
      '8b3617725cd9061137dc55d6e2b5af75a87453929c93918b9e0acddea34f3cb2',
      '2eb47603dcfefe58ea89e8f3cf832aca187f397d66b99bd7a4ab3bb5d6c428ad',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_supplier_payment(uuid)',
      '231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8',
      'ad780c4b00261b6ee1890391cac1c459c23d06b041859399e6ccc2f73d67f421',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()',
      'ce489ade327609230a40a0e804b1b67a9cecb11bb08a42bb470b9ba556183066',
      'e5f4d8749851824e11bb7b76bb3614963aa26feca7034962f47cc198a7962e89',
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
    from erp.cp6_v2620s_rollback_capsule cap
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
      raise exception 'S_TRUSTED_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;

  select boundary_snapshot into v_expected
  from erp.cp6_v2620s_rollback_capsule limit 1;
  if v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>69
     or exists(select 1 from erp.cp6_v2620s_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'S_BOUNDARY_SNAPSHOT_MISMATCH';
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
    'cp6_v2620n_rollback_capsule','cp6_v2620o_rollback_capsule','cp6_v2620p_rollback_capsule','cp6_v2620q_rollback_capsule','cp6_v2620r_rollback_capsule'
  ]::text[]
  loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'S_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;

  for c in select * from erp.cp6_v2620s_rollback_capsule
    order by object_regidentity
  loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()',
      '8b3617725cd9061137dc55d6e2b5af75a87453929c93918b9e0acddea34f3cb2'),
    ('erp.post_supplier_payment(uuid)',
      '231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8'),
    ('erp.run_v267_financial_truth_checks()',
      'ce489ade327609230a40a0e804b1b67a9cecb11bb08a42bb470b9ba556183066')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'S_ROLLBACK_RESTORE_HASH_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_guard_v2620s$;

drop table erp.cp6_v2620s_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20s';
delete from supabase_migrations.schema_migrations
where version='20260912132445'
  and name='erp_v2_6_20s_cp6_supplier_payment_business_date'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('c9e35612100f0e387a7fdb80fda382ea1212df0cf5200ebceeaf67df9f77cf1f','e0516a4533c76c416f6385cb07c33ab9ea9a7a50386fa818ac6c232fd5e21b7d');

do $postcheck_v2620s$
declare r record;v_actual text;
begin
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()',
      '8b3617725cd9061137dc55d6e2b5af75a87453929c93918b9e0acddea34f3cb2',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_supplier_payment(uuid)',
      '231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()',
      'ce489ade327609230a40a0e804b1b67a9cecb11bb08a42bb470b9ba556183066',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'S_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20s')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20s_cp6_supplier_payment_business_date')
     or to_regclass('erp.cp6_v2620s_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20r')
     or to_regclass('erp.cp6_v2620r_rollback_capsule') is null
     or to_regclass('erp.supplier_cent_posting_facts') is null then
    raise exception 'S_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620s$;
commit;
