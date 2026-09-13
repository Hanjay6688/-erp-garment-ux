-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20u -> exact T.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py after its
-- independently pinned trust checks, admission closure and session drain.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $platform_guard_v2620u$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20u_cp6_canonical_business_date')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260913070000'
         and name='erp_v2_6_20u_cp6_canonical_business_date'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('972b5189a065e078590c0742f67722684eb14a1d0df21f5fb1ebd42bf7f3bbaa',
              'ca2759018e86597da6ebdc4d5e2c577095a44ecbffe0bbd549a75ceb02f7ceac'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260913070000') then
    raise exception 'U_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620u$;

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
  erp.cp6_v2620t_rollback_capsule
in share row exclusive mode;
lock table erp.cp6_v2620u_rollback_capsule in access exclusive mode;

do $restore_guard_v2620u$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20t')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20u')
     or exists(select 1 from erp.schema_migrations
       where version not in('v2.6.20t','v2.6.20u')
         and installed_at>(select installed_at from erp.schema_migrations
           where version='v2.6.20u'))
     or (select count(*) from erp.cp6_v2620u_rollback_capsule)<>7 then
    raise exception 'U_ROLLBACK_MARKER_CAPSULE_OR_SUCCESSOR';
  end if;
  for r in select * from(values
    ('erp._cp3_r4_reverse_journal_internal(uuid,text)','9b60fcd88852337ad0956d471e54c1c04bcccd35f5e85a8e5093469cc1c37249','2d54bfdf9bf0912e6b13e558ddbc4cb419020f191c3ce626a26f2c27b814b20c',array['postgres=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','8e0e303066c23476223089e2705b8ad0861b34faa2efb12c58663677f454b196','3a8af1f92f85ddbebf697b681e16f42b9c48b2cdb543b6ab2daa2a928a5bc775',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.get_owner_financial_snapshot_v2(date,date,date)','e51dbe224d112f523e51bddc609ee0f0036ecae2ef5d328b865326781aa8780c','0afb94d932b1c7488c1a787de7f734133c1674e0a43100d366c6f3f129ffb9bb',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_adjustment(uuid)','be5a163932f0678667d94095f3db519abb7e5df4ea2c4c95204e42620ee27d83','b32962d12adde0ca4ae659f2dd83a02a0a3111c3a9060d845ed2e82025696201',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_purchase(uuid)','83f51a14eef3b2942b7158e81c2db1ee1e7ec401368fd8abb6bc013bf1be95de','17547ee019fca617bf67100d9b3b899b96781a2fa62cc47c57bb2dbafe358082',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','acd6f623c83f1ce74323a11b9224955ea922b10788ed631b9973aa9345698af8','f32dcd6d6be2ef1f2762bce1dac463aeeed8965f4ef94f8e7a31f8da4451e6ce',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.sync_material_purchase_grni_on_status()','7537c077a003924fce425c9db9769824fc5ffdd0e761e7b292508b1e248ad870','e39d7cc4b457a58b929894f4fd5a9c7f47aa0da678853a3ddbee65f9630d676c',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c
    from erp.cp6_v2620u_rollback_capsule cap
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
      raise exception 'U_TRUSTED_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;

  select boundary_snapshot into v_expected
  from erp.cp6_v2620u_rollback_capsule limit 1;
  if v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>74
     or exists(select 1 from erp.cp6_v2620u_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'U_BOUNDARY_SNAPSHOT_MISMATCH';
  end if;
  foreach v_table in array array[
    'app_users','idempotency_requests','products','audit_logs','journal_entries',
    'journal_lines','account_daily_balances','sales_headers','sales_items',
    'sale_stock_allocations','sales_returns','sales_return_items','sales_payments',
    'fg_lots','fg_stock_movements','fg_inventory_balances','hpp_versions',
    'product_conversions','product_conversion_allocations','laundry_deliveries',
    'laundry_delivery_lines','laundry_receipts','laundry_failed_wash_attempts',
    'wip_stage_events','cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule',
    'cp6_v2620i_rollback_capsule','sales_payment_posting_facts',
    'sales_payment_reversal_facts','cp6_v2620j_rollback_capsule',
    'cp6_v2620k_rollback_capsule','accounting_period_control',
    'accounting_account_mappings','cash_accounts','chart_accounts','laundry_claims',
    'laundry_vendors','cp6_v2620l_rollback_capsule','opening_balance_headers',
    'opening_balance_items','opening_subledger_balances','opening_subledger_settlements',
    'opening_financial_corrections','supplier_payments','material_purchase_headers',
    'material_purchase_items','material_supplier_invoices',
    'material_supplier_invoice_lines','material_supplier_returns',
    'material_supplier_return_items','material_purchase_cost_corrections',
    'material_purchase_cost_correction_items','material_stock_movements','material_rolls',
    'cost_recalc_queue','cost_adjustments','suppliers','materials',
    'cp6_v2620m_rollback_capsule','supplier_cent_posting_facts','material_cost_history',
    'material_cost_revaluation_state','material_cost_revaluation_events',
    'material_cost_checkpoints','cp6_v2620n_rollback_capsule',
    'cp6_v2620o_rollback_capsule','cp6_v2620p_rollback_capsule',
    'cp6_v2620q_rollback_capsule','cp6_v2620r_rollback_capsule',
    'cp6_v2620s_rollback_capsule','material_adjustments','material_adjustment_items',
    'material_adjustment_revaluation_facts','cp6_v2620t_rollback_capsule'
  ]::text[] loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'U_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;

  for c in select * from erp.cp6_v2620u_rollback_capsule
    order by object_regidentity
  loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp._cp3_r4_reverse_journal_internal(uuid,text)','9b60fcd88852337ad0956d471e54c1c04bcccd35f5e85a8e5093469cc1c37249'),
    ('erp._v268_financial_report_checks_pre_scope()','8e0e303066c23476223089e2705b8ad0861b34faa2efb12c58663677f454b196'),
    ('erp.get_owner_financial_snapshot_v2(date,date,date)','e51dbe224d112f523e51bddc609ee0f0036ecae2ef5d328b865326781aa8780c'),
    ('erp.post_material_adjustment(uuid)','be5a163932f0678667d94095f3db519abb7e5df4ea2c4c95204e42620ee27d83'),
    ('erp.post_material_purchase(uuid)','83f51a14eef3b2942b7158e81c2db1ee1e7ec401368fd8abb6bc013bf1be95de'),
    ('erp.run_v267_financial_truth_checks()','acd6f623c83f1ce74323a11b9224955ea922b10788ed631b9973aa9345698af8'),
    ('erp.sync_material_purchase_grni_on_status()','7537c077a003924fce425c9db9769824fc5ffdd0e761e7b292508b1e248ad870')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'U_ROLLBACK_RESTORE_HASH_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_guard_v2620u$;

drop table erp.cp6_v2620u_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20u';
delete from supabase_migrations.schema_migrations
where version='20260913070000'
  and name='erp_v2_6_20u_cp6_canonical_business_date'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('972b5189a065e078590c0742f67722684eb14a1d0df21f5fb1ebd42bf7f3bbaa',
       'ca2759018e86597da6ebdc4d5e2c577095a44ecbffe0bbd549a75ceb02f7ceac');

do $postcheck_v2620u$
declare r record;v_actual text;
begin
  for r in select * from(values
    ('erp._cp3_r4_reverse_journal_internal(uuid,text)','9b60fcd88852337ad0956d471e54c1c04bcccd35f5e85a8e5093469cc1c37249',array['postgres=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','8e0e303066c23476223089e2705b8ad0861b34faa2efb12c58663677f454b196',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.get_owner_financial_snapshot_v2(date,date,date)','e51dbe224d112f523e51bddc609ee0f0036ecae2ef5d328b865326781aa8780c',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_adjustment(uuid)','be5a163932f0678667d94095f3db519abb7e5df4ea2c4c95204e42620ee27d83',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_purchase(uuid)','83f51a14eef3b2942b7158e81c2db1ee1e7ec401368fd8abb6bc013bf1be95de',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','acd6f623c83f1ce74323a11b9224955ea922b10788ed631b9973aa9345698af8',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.sync_material_purchase_grni_on_status()','7537c077a003924fce425c9db9769824fc5ffdd0e761e7b292508b1e248ad870',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'U_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20u')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20u_cp6_canonical_business_date')
     or to_regclass('erp.cp6_v2620u_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20t')
     or to_regclass('erp.cp6_v2620t_rollback_capsule') is null
     or to_regclass('erp.material_adjustment_revaluation_facts') is null
     or to_regprocedure('erp._cp6_material_adjustment_revaluation_state(uuid)') is null
     or to_regprocedure('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)') is null
     or to_regprocedure('erp.guard_material_adjustment_revaluation_fact_v2620t()') is null then
    raise exception 'U_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620u$;
commit;
