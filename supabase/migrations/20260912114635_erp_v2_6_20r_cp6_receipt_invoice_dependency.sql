-- CP6 R: preserve posted supplier invoice dependencies during receipt reversal.
-- Forward-only successor; published Q migration and rollback remain immutable.
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
  erp.cp6_v2620o_rollback_capsule,erp.cp6_v2620p_rollback_capsule,erp.cp6_v2620q_rollback_capsule
in share row exclusive mode;

do $predecessor_v2620r$
declare r record;c record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20q')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20r')
     or to_regclass('erp.cp6_v2620r_rollback_capsule') is not null then
    raise exception 'R_REQUIRES_EXACT_Q_WITHOUT_R_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20q_cp6_supplier_invoice_exact_quantity')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260912084719'
         and name='erp_v2_6_20q_cp6_supplier_invoice_exact_quantity'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('26faa6601494521d46813ecef194eb1c33ea7c9f71b98c3ef13ee90f869b5188',
              'ed1b5f684e9f5a58eca2b1312fb7239d0d64bf92612a0c6178b589d7c2518f95'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'20260912084719')
     or (select count(*) from erp.cp6_v2620q_rollback_capsule)<>4 then
    raise exception 'R_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH';
  end if;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()',
      '17a07e10665756088f2faa0570c055efae4513abf1c5985afacf86bf8467e056',
      'edefb0fa134200d5d541bfdb6ab1b4b81e28b8cd912eff0a7c1ef59106744917',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_supplier_invoice(uuid)',
      'da4ce12c6f41625933511e6fd59246c2410b80ce02ddf865c489803070f7b8b0',
      '727382a2c3b8464526bb5a8a66c68813be439fb931ca94d993898fecc1e41faf',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.refresh_material_purchase_item_match_state(uuid)',
      '7ff2434fb46099077d3891359a161cfcf5fac8f4f8ca80f549b4d2e7ef6f8658',
      '351dc9ea86baa9cda11047468f58db5f69044c9860ce5ca7315dcc9ec6e1acd5',
      array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()',
      '2c546026b1325e265c62828c13f2eea63aaff302c9a359d5f49c18d5fb7a492e',
      '04115f87a2dd4777a56ed3667b461f71fb972887eccd1c9b5281878660a3acc3',
      array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620q_rollback_capsule
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
      raise exception 'R_TRUSTED_Q_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  -- R also pins the receipt reversal outside Q's replaced identities.
  for r in select * from(values
    ('erp.reverse_material_purchase(uuid,text)',
      '9b637facd36bcf810e11350fc97a1e0da68cbb77b67aec54697b3ae52cd820b3',
      array['authenticated=X/postgres','postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(
        to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.sha256
       or (select pg_get_userbyid(proowner) from pg_proc
         where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
         from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'R_TRUSTED_Q_INPUT_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if not exists(select 1 from pg_class
      where oid='erp.supplier_cent_posting_facts'::regclass
        and relrowsecurity and relowner='postgres'::regrole)
     or exists(select 1 from information_schema.role_table_grants
       where table_schema='erp' and table_name='supplier_cent_posting_facts'
         and grantee in('PUBLIC','anon','authenticated','service_role')) then
    raise exception 'R_INHERITED_Q_SECURITY_MISMATCH';
  end if;
  if exists(
    select 1 from erp.material_supplier_invoices ih
    where ih.status='POSTED' and exists(
      select 1 from erp.material_supplier_invoice_lines il
      join erp.material_purchase_items pi on pi.id=il.purchase_item_id
      join erp.material_purchase_headers ph on ph.id=pi.purchase_id
      where il.invoice_id=ih.id and ph.status<>'POSTED'
    )
  ) then
    raise exception 'R_PREEXISTING_INVOICE_SOURCE_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620r$;

create table erp.cp6_v2620r_rollback_capsule(
  like erp.cp6_v2620q_rollback_capsule including all
);
alter table erp.cp6_v2620r_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620r_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620r_rollback_capsule(
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
  'erp.reverse_material_purchase(uuid,text)'::regprocedure,
  'erp.run_v267_financial_truth_checks()'::regprocedure
);

do $patch_v2620r_1$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp._v268_financial_report_checks_pre_scope()'::regprocedure) into d;
  anchor:=$a$or r.check_name like 'V2620P_%'$a$;
  replacement:=$r$or r.check_name like 'V2620P_%' or r.check_name like 'V2620R_%'$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'R_RECEIPT_DEPENDENCY_ANCHOR_1_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_v2620r_1$;

do $patch_v2620r_2$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.reverse_material_purchase(uuid,text)'::regprocedure) into d;
  anchor:=$a$  if exists(select 1 from erp.supplier_payments where purchase_id=h.id and status='POSTED') then$a$;
  replacement:=$r$
  -- The receipt row is already locked. Invoice posting takes the same row lock
  -- and rechecks source state, so either serialization order preserves the link.
  -- Do not lock invoice headers here: invoice writers acquire those first.
  if exists(
    select 1 from erp.material_supplier_invoice_lines il
    join erp.material_supplier_invoices ih on ih.id=il.invoice_id
    join erp.material_purchase_items pi on pi.id=il.purchase_item_id
    where pi.purchase_id=h.id and ih.status='POSTED'
  ) then
    raise exception 'Reverse posted supplier invoices before reversing this receipt';
  end if;

  if exists(select 1 from erp.supplier_payments where purchase_id=h.id and status='POSTED') then$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'R_RECEIPT_DEPENDENCY_ANCHOR_2_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_v2620r_2$;

do $patch_v2620r_3$
declare d text;anchor text;replacement text;
begin
  select pg_get_functiondef('erp.run_v267_financial_truth_checks()'::regprocedure) into d;
  anchor:=$a$  union all
  select 'V2620N_SUPPLIER_CENT_FACT_LEDGER'$a$;
  replacement:=$r$  union all
  select 'V2620R_SUPPLIER_INVOICE_SOURCE_STATE','CRITICAL',count(*)::bigint,
    'Every posted supplier invoice must reference only posted material receipts'
  from erp.material_supplier_invoices ih
  where ih.status='POSTED' and exists(
    select 1 from erp.material_supplier_invoice_lines il
    join erp.material_purchase_items pi on pi.id=il.purchase_item_id
    join erp.material_purchase_headers ph on ph.id=pi.purchase_id
    where il.invoice_id=ih.id and ph.status<>'POSTED'
  )

  union all
  select 'V2620N_SUPPLIER_CENT_FACT_LEDGER'$r$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'R_RECEIPT_DEPENDENCY_ANCHOR_3_MISMATCH';
  end if;
  execute replace(d,anchor,replacement);
end
$patch_v2620r_3$;

do $installed_v2620r$
declare r record;c record;v_count bigint;
begin
  if (select count(*) from erp.cp6_v2620r_rollback_capsule)<>3 then
    raise exception 'R_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620r_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
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
      raise exception 'R_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  select issue_count into v_count from erp.run_v267_financial_truth_checks()
  where check_name='V2620R_SUPPLIER_INVOICE_SOURCE_STATE';
  if v_count is distinct from 0 then
    raise exception 'R_INSTALLED_INVOICE_SOURCE_RECONCILIATION_FAILED: %',v_count;
  end if;
  if not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620P_SUPPLIER_RETURN_MATCH_STATE' and issue_count=0)
     or not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620R_SUPPLIER_INVOICE_SOURCE_STATE' and issue_count=0)
     or not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620O_SUPPLIER_RETURN_ALLOCATION' and issue_count=0)
     or not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V267_INVOICE_MATCH_OVER_RECEIPT' and issue_count=0)
     or not exists(select 1 from erp.run_v268_financial_report_checks()
      where check_name='V2620N_SUPPLIER_CENT_FACT_LEDGER' and issue_count=0) then
    raise exception 'R_FINANCIAL_REPORT_SCOPE_NOT_CONNECTED';
  end if;
end
$installed_v2620r$;

do $boundary_v2620r$
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
    'cp6_v2620o_rollback_capsule','cp6_v2620p_rollback_capsule','cp6_v2620q_rollback_capsule'
  ]::text[] loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620r_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620r$;

insert into erp.schema_migrations(version,description)
values('v2.6.20r','Prevent receipt reversal with posted invoices and connect invoice source-state financial checks');
commit;
