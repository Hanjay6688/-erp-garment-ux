-- CP6 P: keep derived invoice-match and price states synchronized when a
-- supplier return removes the last remaining GRNI-backed quantity.
-- Forward-only successor; the published O migration and rollback stay intact.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
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
  erp.cp6_v2620o_rollback_capsule
in share row exclusive mode;

do $predecessor_v2620p$
declare r record;c record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20o')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20p')
     or to_regclass('erp.cp6_v2620p_rollback_capsule') is not null then
    raise exception 'P_REQUIRES_EXACT_O_WITHOUT_P_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20o_cp6_supplier_return_document_allocation')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260911165255'
         and name='erp_v2_6_20o_cp6_supplier_return_document_allocation'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('9399b7b8d397165d76e0a87dfcb2bf5efeae82f7930bd8ce3449a004c7ed734b',
              '72653dc66bd04ebecef31aa860c211e06a7289aea2124e8a0d446efcf60d3b8d'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260911165255')
     or (select count(*) from erp.cp6_v2620o_rollback_capsule)<>2 then
    raise exception 'P_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH';
  end if;
  for r in select * from(values
    ('erp.post_material_supplier_return(uuid)',
      'b4ac34b5df0e35f0cf1afe85d4a92e0b369922f91d0ce9eb4e2589a71367d607',
      'eff9b9a2a19eca7f51d51ac0fc73983d53f7fa5e4c699407813580dac91bbace',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()',
      'f50decac0d38f9ddc2cfc5a28af53607fb8c1cf38cde5a65f13b38ec748a6fda',
      'fc3edcc094fb4843886206466801f96441907d83efeed01c92c5604f658a96d0',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620o_rollback_capsule
    where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(
            pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex')
            is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'P_TRUSTED_O_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  select encode(extensions.digest(convert_to(pg_get_functiondef(
      'erp._v268_financial_report_checks_pre_scope()'::regprocedure),'UTF8'),'sha256'),'hex')
  into v_actual;
  select * into c from erp.cp6_v2620m_rollback_capsule
  where object_regidentity='erp._v268_financial_report_checks_pre_scope()';
  if v_actual is distinct from '98fac1a865982d5c60fc5e6a5caae9033755ff915b7e53d22213c0d1d1765ca1'
     or c.object_regidentity is null
     or c.installed_definition_sha256 is distinct from v_actual
     or c.owner_snapshot is distinct from 'postgres'
     or c.acl_snapshot is distinct from array['postgres=X/postgres','service_role=X/postgres']::text[]
     or (select pg_get_userbyid(proowner) from pg_proc
          where oid='erp._v268_financial_report_checks_pre_scope()'::regprocedure)
          is distinct from 'postgres'
     or (select array(select a::text from unnest(proacl) a order by a::text)
          from pg_proc where oid='erp._v268_financial_report_checks_pre_scope()'::regprocedure)
          is distinct from array['postgres=X/postgres','service_role=X/postgres']::text[] then
    raise exception 'P_TRUSTED_O_REPORT_SCOPE_OWNER_ACL_MISMATCH';
  end if;
  if not exists(select 1 from pg_class
      where oid='erp.supplier_cent_posting_facts'::regclass
        and relrowsecurity and relowner='postgres'::regrole)
     or exists(select 1 from information_schema.role_table_grants
       where table_schema='erp' and table_name='supplier_cent_posting_facts'
         and grantee in('PUBLIC','anon','authenticated','service_role')) then
    raise exception 'P_INHERITED_O_SECURITY_MISMATCH';
  end if;
  if exists(
    select 1 from erp.material_purchase_items i
    cross join lateral(select erp.material_purchase_invoice_capacity(i.id) capacity,
      erp.material_purchase_posted_invoice_qty(i.id) matched) x
    where i.invoice_match_state<>'DIRECT_FINAL' and(
      i.invoice_match_state is distinct from case when x.matched<=0 then 'UNMATCHED'
        when x.matched<x.capacity-0.000001 then 'PARTIAL' else 'MATCHED' end
      or i.price_state is distinct from case when x.matched<=0 then 'ESTIMATED'
        when x.matched<x.capacity-0.000001 then 'PARTIAL' else 'FINAL' end)
  ) then
    raise exception 'P_PREEXISTING_RETURN_MATCH_STATE_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620p$;

create table erp.cp6_v2620p_rollback_capsule(
  like erp.cp6_v2620o_rollback_capsule including all
);
alter table erp.cp6_v2620p_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620p_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620p_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,
    pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  array(select a::text from unnest(p.proacl) a order by a::text),
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp._v268_financial_report_checks_pre_scope()'::regprocedure,
  'erp.post_material_supplier_return(uuid)'::regprocedure,
  'erp.run_v267_financial_truth_checks()'::regprocedure
);

do $patch_return_v2620p$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.post_material_supplier_return(uuid)'::regprocedure) into d;
  anchor:=$a$    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    if r.roll_id is not null then$a$;
  replacement:=$r$    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
    if r.roll_id is not null then$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'P_RETURN_MATCH_REFRESH_ANCHOR_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_return_v2620p$;

do $patch_report_v2620p$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.run_v267_financial_truth_checks()'::regprocedure) into d;
  anchor:=$a$  union all
  select 'V2620O_SUPPLIER_RETURN_ALLOCATION','CRITICAL',count(*)::bigint,$a$;
  replacement:=$r$  union all
  select 'V2620P_SUPPLIER_RETURN_MATCH_STATE','CRITICAL',count(*)::bigint,
    'Supplier invoice match and price states must equal posted invoice quantity against current return-adjusted capacity'
  from erp.material_purchase_items i
  cross join lateral(select erp.material_purchase_invoice_capacity(i.id) capacity,
    erp.material_purchase_posted_invoice_qty(i.id) matched) x
  where i.invoice_match_state<>'DIRECT_FINAL' and(
    i.invoice_match_state is distinct from case when x.matched<=0 then 'UNMATCHED'
      when x.matched<x.capacity-0.000001 then 'PARTIAL' else 'MATCHED' end
    or i.price_state is distinct from case when x.matched<=0 then 'ESTIMATED'
      when x.matched<x.capacity-0.000001 then 'PARTIAL' else 'FINAL' end)

  union all
  select 'V2620O_SUPPLIER_RETURN_ALLOCATION','CRITICAL',count(*)::bigint,$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'P_REPORT_MATCH_STATE_ANCHOR_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_report_v2620p$;

do $patch_report_scope_v2620p$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef(
    'erp._v268_financial_report_checks_pre_scope()'::regprocedure) into d;
  anchor:=$a$  where r.check_name in('V267_GRNI_GL_SUBLEDGER_MISMATCH','V267_AP_GL_SUBLEDGER_MISMATCH',
    'V267_PAYMENT_EXCEEDS_FINAL_AP') or r.check_name like 'V2620M_%'$a$;
  replacement:=$r$  where r.check_name in('V267_GRNI_GL_SUBLEDGER_MISMATCH','V267_AP_GL_SUBLEDGER_MISMATCH',
    'V267_PAYMENT_EXCEEDS_FINAL_AP') or r.check_name like 'V2620M_%'
    or r.check_name like 'V2620N_%' or r.check_name like 'V2620O_%'
    or r.check_name like 'V2620P_%'$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'P_REPORT_SCOPE_ANCHOR_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_report_scope_v2620p$;

do $installed_v2620p$
declare r record;c record;v_count bigint;
begin
  if (select count(*) from erp.cp6_v2620p_rollback_capsule)<>3 then
    raise exception 'P_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620p_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
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
    select * into c from erp.cp6_v2620p_rollback_capsule
    where object_regidentity=r.identity;
    if c.object_regidentity is null or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres' or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'P_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  select issue_count into v_count from erp.run_v267_financial_truth_checks()
  where check_name='V2620P_SUPPLIER_RETURN_MATCH_STATE';
  if v_count is distinct from 0 then
    raise exception 'P_INSTALLED_RETURN_MATCH_STATE_RECONCILIATION_FAILED: %',v_count;
  end if;
  if not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620P_SUPPLIER_RETURN_MATCH_STATE' and issue_count=0)
     or not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620O_SUPPLIER_RETURN_ALLOCATION' and issue_count=0)
     or not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620N_SUPPLIER_CENT_FACT_LEDGER' and issue_count=0) then
    raise exception 'P_FINANCIAL_REPORT_SCOPE_NOT_CONNECTED';
  end if;
end
$installed_v2620p$;

do $boundary_v2620p$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
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
    'cp6_v2620o_rollback_capsule'
  ]::text[] loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620p_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620p$;

insert into erp.schema_migrations(version,description)
values('v2.6.20p','Synchronize return-adjusted supplier invoice match and price states');
commit;
