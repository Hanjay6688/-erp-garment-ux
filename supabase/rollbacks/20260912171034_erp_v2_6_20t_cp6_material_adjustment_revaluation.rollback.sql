-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20t -> exact S.
-- Execute only through scripts/cp6_preuse_rollback_maintenance.py after its
-- independently pinned trust checks, admission closure and session drain.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $platform_guard_v2620t$
begin
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20t_cp6_material_adjustment_revaluation')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260912171034'
         and name='erp_v2_6_20t_cp6_material_adjustment_revaluation'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('e888fa66bd40abda0ba1152662df9d0855193325dcf1c8491d47b522cdd00add','564538094fb948dded4ff26223595227222166030ac8b8c7c77495245ebe3890'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260912171034') then
    raise exception 'T_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620t$;

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
  erp.cp6_v2620n_rollback_capsule,erp.cp6_v2620o_rollback_capsule,erp.cp6_v2620p_rollback_capsule,erp.cp6_v2620q_rollback_capsule,erp.cp6_v2620r_rollback_capsule,erp.cp6_v2620s_rollback_capsule,
  erp.material_adjustments,erp.material_adjustment_items,erp.material_adjustment_revaluation_facts
in share row exclusive mode;
lock table erp.cp6_v2620t_rollback_capsule in access exclusive mode;

do $t_extra_objects$
declare r record;
begin
  for r in select * from(values
    ('erp._cp6_material_adjustment_revaluation_state(uuid)','47a2c15955a682040d2c0c6b72f2941eaae8467e2b16fa5c4bbc10dff27a3c2e',array['postgres=X/postgres']::text[]),
    ('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)','355246b52dc88e5d91643485fe796f24e7975d0629824c5b28c31074469ed7ba',array['postgres=X/postgres']::text[]),
    ('erp.guard_material_adjustment_revaluation_fact_v2620t()','c2cc7ddb076f557d0f71df9170b9d02425fc17c2f33e471bd1af48e61729829e',array['postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
        is distinct from r.sha256
       or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'T_EXTRA_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if not exists(select 1 from pg_class where oid=to_regclass('erp.material_adjustment_revaluation_facts')
       and relrowsecurity and relowner='postgres'::regrole)
     or exists(select 1 from information_schema.role_table_grants where table_schema='erp'
       and table_name='material_adjustment_revaluation_facts' and grantee in('PUBLIC','anon','authenticated','service_role'))
     or (select count(*) from pg_trigger where tgrelid=to_regclass('erp.material_adjustment_revaluation_facts')
       and not tgisinternal and tgenabled='O'
       and tgfoid=to_regprocedure('erp.guard_material_adjustment_revaluation_fact_v2620t()')
       and tgname in('trg_material_adjustment_revaluation_fact_append_only','trg_material_adjustment_revaluation_fact_no_truncate'))<>2 then
    raise exception 'T_ADJUSTMENT_FACT_SECURITY_MISMATCH';
  end if;
end
$t_extra_objects$;

do $restore_guard_v2620t$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20s')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20t')
     or exists(select 1 from erp.schema_migrations
       where version not in('v2.6.20s','v2.6.20t')
         and installed_at>(select installed_at from erp.schema_migrations
           where version='v2.6.20t'))
     or (select count(*) from erp.cp6_v2620t_rollback_capsule)<>6 then
    raise exception 'T_ROLLBACK_MARKER_CAPSULE_OR_SUCCESSOR';
  end if;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','2eb47603dcfefe58ea89e8f3cf832aca187f397d66b99bd7a4ab3bb5d6c428ad','8e0e303066c23476223089e2705b8ad0861b34faa2efb12c58663677f454b196',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.resolve_accounting_transaction_date(date)','13fa7b70e1b723bb5d0f0f112f19ff9f7f928c587aef75b9ad4737e135b0a769','92e6c30c60bce3406178bd661ca5df2e5d12e17380fad2a8730be0c91d86bf48',array['postgres=X/postgres']::text[]),
    ('erp.reverse_journal(uuid,text)','3ff7dec1176c79b58a981e5fdc68a3ce47908cfd5347cbd192d40022c9d7aee1','a6f635cd2319a68a1afa522fa4682921a6f7b80afd0e31fbdc4271cf53fcfef4',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_adjustment(uuid,text)','38800321130b33af3b127928b724f4e2b7b02342c62087a25536580c1eba8043','c90fd34d4045a060ae4d36413d6520068281066d0de52dc766583c5f6e7d7288',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','e5f4d8749851824e11bb7b76bb3614963aa26feca7034962f47cc198a7962e89','acd6f623c83f1ce74323a11b9224955ea922b10788ed631b9973aa9345698af8',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.sync_material_cost_revaluation(uuid)','57b213f5b7adb8abc78eafd8639cbc1907fd49319027534166a10365cfb69b83','3334800b5888000a4388dda4362ebd0db4c5f0dcdc0bbf3e41acfcf629d720f0',array['postgres=X/postgres']::text[])
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
    from erp.cp6_v2620t_rollback_capsule cap
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
      raise exception 'T_TRUSTED_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;

  select boundary_snapshot into v_expected
  from erp.cp6_v2620t_rollback_capsule limit 1;
  if v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>73
     or exists(select 1 from erp.cp6_v2620t_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'T_BOUNDARY_SNAPSHOT_MISMATCH';
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
    'cp6_v2620n_rollback_capsule','cp6_v2620o_rollback_capsule','cp6_v2620p_rollback_capsule','cp6_v2620q_rollback_capsule','cp6_v2620r_rollback_capsule','cp6_v2620s_rollback_capsule','material_adjustments','material_adjustment_items','material_adjustment_revaluation_facts'
  ]::text[]
  loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'T_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;

  for c in select * from erp.cp6_v2620t_rollback_capsule
    order by object_regidentity
  loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','2eb47603dcfefe58ea89e8f3cf832aca187f397d66b99bd7a4ab3bb5d6c428ad'),
    ('erp.resolve_accounting_transaction_date(date)','13fa7b70e1b723bb5d0f0f112f19ff9f7f928c587aef75b9ad4737e135b0a769'),
    ('erp.reverse_journal(uuid,text)','3ff7dec1176c79b58a981e5fdc68a3ce47908cfd5347cbd192d40022c9d7aee1'),
    ('erp.reverse_material_adjustment(uuid,text)','38800321130b33af3b127928b724f4e2b7b02342c62087a25536580c1eba8043'),
    ('erp.run_v267_financial_truth_checks()','e5f4d8749851824e11bb7b76bb3614963aa26feca7034962f47cc198a7962e89'),
    ('erp.sync_material_cost_revaluation(uuid)','57b213f5b7adb8abc78eafd8639cbc1907fd49319027534166a10365cfb69b83')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
    into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'T_ROLLBACK_RESTORE_HASH_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_guard_v2620t$;

drop function erp._cp6_sync_material_adjustment_revaluation(uuid,uuid);
drop function erp._cp6_material_adjustment_revaluation_state(uuid);
drop table erp.material_adjustment_revaluation_facts;
drop function erp.guard_material_adjustment_revaluation_fact_v2620t();
drop table erp.cp6_v2620t_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20t';
delete from supabase_migrations.schema_migrations
where version='20260912171034'
  and name='erp_v2_6_20t_cp6_material_adjustment_revaluation'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
    in('e888fa66bd40abda0ba1152662df9d0855193325dcf1c8491d47b522cdd00add','564538094fb948dded4ff26223595227222166030ac8b8c7c77495245ebe3890');

do $postcheck_v2620t$
declare r record;v_actual text;
begin
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','2eb47603dcfefe58ea89e8f3cf832aca187f397d66b99bd7a4ab3bb5d6c428ad',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.resolve_accounting_transaction_date(date)','13fa7b70e1b723bb5d0f0f112f19ff9f7f928c587aef75b9ad4737e135b0a769',array['postgres=X/postgres']::text[]),
    ('erp.reverse_journal(uuid,text)','3ff7dec1176c79b58a981e5fdc68a3ce47908cfd5347cbd192d40022c9d7aee1',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_adjustment(uuid,text)','38800321130b33af3b127928b724f4e2b7b02342c62087a25536580c1eba8043',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','e5f4d8749851824e11bb7b76bb3614963aa26feca7034962f47cc198a7962e89',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.sync_material_cost_revaluation(uuid)','57b213f5b7adb8abc78eafd8639cbc1907fd49319027534166a10365cfb69b83',array['postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl)
  loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'T_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20t')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20t_cp6_material_adjustment_revaluation')
     or to_regclass('erp.cp6_v2620t_rollback_capsule') is not null
     or to_regclass('erp.material_adjustment_revaluation_facts') is not null
     or to_regprocedure('erp._cp6_material_adjustment_revaluation_state(uuid)') is not null
     or to_regprocedure('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)') is not null
     or to_regprocedure('erp.guard_material_adjustment_revaluation_fact_v2620t()') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20s')
     or to_regclass('erp.cp6_v2620s_rollback_capsule') is null
     or to_regclass('erp.supplier_cent_posting_facts') is null then
    raise exception 'T_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620t$;
commit;
