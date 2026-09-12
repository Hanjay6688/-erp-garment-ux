-- CP6 S: canonical supplier-payment business dates, independent of session timezone.
-- Forward-only successor; published R migration and rollback remain immutable.
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
  erp.cp6_v2620o_rollback_capsule,erp.cp6_v2620p_rollback_capsule,erp.cp6_v2620q_rollback_capsule,erp.cp6_v2620r_rollback_capsule
in share row exclusive mode;

do $predecessor_v2620s$
declare r record;c record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20r')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20s')
     or to_regclass('erp.cp6_v2620s_rollback_capsule') is not null then
    raise exception 'S_REQUIRES_EXACT_R_WITHOUT_S_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20r_cp6_receipt_invoice_dependency')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260912114635'
         and name='erp_v2_6_20r_cp6_receipt_invoice_dependency'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('0c5551ef49da417310e0bcf8c8aa9d655f551ff66ca6e7ca79679ffd331f788b',
              'e3f43f0ba23a958cd7748dc8a851e001cd6be381bb3d7958053da10d9885d066'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260912114635')
     or (select count(*) from erp.cp6_v2620r_rollback_capsule)<>3 then
    raise exception 'S_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH';
  end if;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()',
      'edefb0fa134200d5d541bfdb6ab1b4b81e28b8cd912eff0a7c1ef59106744917',
      '8b3617725cd9061137dc55d6e2b5af75a87453929c93918b9e0acddea34f3cb2',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_purchase(uuid,text)',
      '9b637facd36bcf810e11350fc97a1e0da68cbb77b67aec54697b3ae52cd820b3',
      '5ed3d75116f42f558829e1707f58c28fd1c81a2c66004ae54cf52069b147d4e1',
      array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()',
      '04115f87a2dd4777a56ed3667b461f71fb972887eccd1c9b5281878660a3acc3',
      'ce489ade327609230a40a0e804b1b67a9cecb11bb08a42bb470b9ba556183066',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620r_rollback_capsule
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
      raise exception 'S_TRUSTED_R_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  -- S also pins its payment entrypoint and unchanged canonical date helper.
  for r in select * from(values
    ('erp.post_supplier_payment(uuid)',
      '231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._cp3_business_date(timestamp with time zone)',
      'adf1fb87dd9f0b6a856bcb109b5118f9c4aac5da0ac32554ecbbc009f6d88248',
      array['postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(
        to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.sha256
       or (select pg_get_userbyid(proowner) from pg_proc
         where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
         from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'S_TRUSTED_R_INPUT_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if not exists(select 1 from pg_class
      where oid='erp.supplier_cent_posting_facts'::regclass
        and relrowsecurity and relowner='postgres'::regrole)
     or exists(select 1 from information_schema.role_table_grants
       where table_schema='erp' and table_name='supplier_cent_posting_facts'
         and grantee in('PUBLIC','anon','authenticated','service_role')) then
    raise exception 'S_INHERITED_R_SECURITY_MISMATCH';
  end if;
  if exists(
    select 1 from erp.supplier_payments p
    join erp.journal_entries j on j.source_type='SUPPLIER_PAYMENT' and j.source_id=p.id
      and j.status in('POSTED','REVERSED')
    where p.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(p.payment_date)
  ) then
    raise exception 'S_PREEXISTING_PAYMENT_DATE_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620s$;

create table erp.cp6_v2620s_rollback_capsule(
  like erp.cp6_v2620r_rollback_capsule including all
);
alter table erp.cp6_v2620s_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620s_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620s_rollback_capsule(
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
  'erp.post_supplier_payment(uuid)'::regprocedure,
  'erp.run_v267_financial_truth_checks()'::regprocedure
);

do $patch_v2620s_1$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp._v268_financial_report_checks_pre_scope()'::regprocedure) into d;
  anchor:=$a$or r.check_name like 'V2620R_%'$a$;
  replacement:=$r$or r.check_name like 'V2620R_%' or r.check_name like 'V2620S_%'$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'S_PAYMENT_DATE_ANCHOR_1_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_v2620s_1$;

do $patch_v2620s_2$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.post_supplier_payment(uuid)'::regprocedure) into d;
  anchor:=$a$erp.post_journal('SUPPLIER_PAYMENT',p.id,p.payment_date::date,$a$;
  replacement:=$r$erp.post_journal('SUPPLIER_PAYMENT',p.id,erp._cp3_business_date(p.payment_date),$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'S_PAYMENT_DATE_ANCHOR_2_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_v2620s_2$;

do $patch_v2620s_3$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.run_v267_financial_truth_checks()'::regprocedure) into d;
  anchor:=$a$  union all
  select 'V2620N_SUPPLIER_CENT_FACT_LEDGER'$a$;
  replacement:=$r$  union all
  select 'V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Supplier payment original journals must retain the canonical Jakarta business date in every lifecycle state'
  from erp.supplier_payments p
  join erp.journal_entries j on j.source_type='SUPPLIER_PAYMENT' and j.source_id=p.id
    and j.status in('POSTED','REVERSED')
  where p.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(p.payment_date)

  union all
  select 'V2620N_SUPPLIER_CENT_FACT_LEDGER'$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'S_PAYMENT_DATE_ANCHOR_3_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_v2620s_3$;

do $installed_v2620s$
declare r record;c record;v_count bigint;
begin
  if (select count(*) from erp.cp6_v2620s_rollback_capsule)<>3 then
    raise exception 'S_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620s_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
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
    select * into c from erp.cp6_v2620s_rollback_capsule
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
      raise exception 'S_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  select issue_count into v_count from erp.run_v267_financial_truth_checks()
  where check_name='V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE';
  if v_count is distinct from 0 then
    raise exception 'S_INSTALLED_PAYMENT_DATE_RECONCILIATION_FAILED: %',v_count;
  end if;
  if not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620P_SUPPLIER_RETURN_MATCH_STATE' and issue_count=0)
     or not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE' and issue_count=0)
     or not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620R_SUPPLIER_INVOICE_SOURCE_STATE' and issue_count=0)
     or not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620O_SUPPLIER_RETURN_ALLOCATION' and issue_count=0)
     or not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V267_INVOICE_MATCH_OVER_RECEIPT' and issue_count=0)
     or not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620N_SUPPLIER_CENT_FACT_LEDGER' and issue_count=0) then
    raise exception 'S_FINANCIAL_REPORT_SCOPE_NOT_CONNECTED';
  end if;
end
$installed_v2620s$;

do $boundary_v2620s$
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
    'cp6_v2620o_rollback_capsule','cp6_v2620p_rollback_capsule','cp6_v2620q_rollback_capsule','cp6_v2620r_rollback_capsule'
  ]::text[] loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620s_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620s$;

insert into erp.schema_migrations(version,description)
values('v2.6.20s','Canonical supplier-payment business dates and connected original-journal date checks');
commit;
