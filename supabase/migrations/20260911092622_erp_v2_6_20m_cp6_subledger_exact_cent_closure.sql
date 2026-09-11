-- ERP CP6 v2.6.20m: exact supplier and opening subledger conservation.
-- Forward-only closure of independently reproduced COMP-L-01/02/03.
begin;
set local lock_timeout='10s';
set local statement_timeout='240s';
set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.audit_logs,
  erp.journal_lines,
  erp.account_daily_balances,
  erp.sales_headers,
  erp.sales_items,
  erp.sale_stock_allocations,
  erp.sales_returns,
  erp.sales_return_items,
  erp.sales_payments,
  erp.fg_lots,
  erp.fg_stock_movements,
  erp.fg_inventory_balances,
  erp.hpp_versions,
  erp.product_conversions,
  erp.product_conversion_allocations,
  erp.laundry_deliveries,
  erp.laundry_delivery_lines,
  erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,
  erp.wip_stage_events,
  erp.cp6_v2620g_rollback_capsule,
  erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,
  erp.sales_payment_posting_facts,
  erp.sales_payment_reversal_facts,
  erp.cp6_v2620j_rollback_capsule,
  erp.cp6_v2620k_rollback_capsule,
  erp.accounting_period_control,
  erp.accounting_account_mappings,
  erp.cash_accounts,
  erp.chart_accounts,
  erp.laundry_claims,
  erp.laundry_vendors,
  erp.cp6_v2620l_rollback_capsule,
  erp.opening_balance_headers,
  erp.opening_balance_items,
  erp.opening_subledger_balances,
  erp.opening_subledger_settlements,
  erp.opening_financial_corrections,
  erp.supplier_payments,
  erp.material_purchase_headers,
  erp.material_purchase_items,
  erp.material_supplier_invoices,
  erp.material_supplier_invoice_lines,
  erp.material_supplier_returns,
  erp.material_supplier_return_items,
  erp.material_purchase_cost_corrections,
  erp.material_purchase_cost_correction_items,
  erp.material_stock_movements,
  erp.material_rolls,
  erp.cost_recalc_queue,
  erp.cost_adjustments,
  erp.suppliers,
  erp.materials
in share row exclusive mode;

do $guard_v2620m$
declare r record; c record;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20l')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20m')
     or to_regclass('erp.cp6_v2620m_rollback_capsule') is not null then
    raise exception 'M_REQUIRES_EXACT_L_WITHOUT_M_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20l_cp6_exact_ledger_conservation')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260911070622' and name='erp_v2_6_20l_cp6_exact_ledger_conservation'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex') in('f46e70911e9e582fa9b7dd742c9a94d455662fa52eac256afd86f590f4d4b815','8ba7ed8baf7fb97bca277b66e4901a5b9cff773cfec7d91bb7e9402fb28d9a04'))
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260911070622')
     or (select count(*) from erp.cp6_v2620l_rollback_capsule)<>3
     or exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'M_PREDECESSOR_PLATFORM_OR_CONTEXT_MISMATCH';
  end if;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','4eb19d881f47dbbf57bc69f4f49ffdbb5c3071b4b126d2398d26dd2e980b2bf7','dc4ed2384dda4b34a30093cad8cb13fa80db26201371569a88dbaee790a24108',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_journal(text,uuid,date,text,jsonb)','c9bfb4804246a2c7b2352ef0a67db5e035939e29f292f2dff34e0b2b590d4e76','1ae479c9c32b9489e659d83d99a9829ef88876643f3e8f8aa276fee6d96a9cdf',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.resolve_laundry_claim(uuid,text,text)','51ebcf8c01d7d47279112808424d7c18e2ea637d9fa7a41472a21de15b17b54b','20eba16640912f04220437c21df018a6799dc48b06d8147abfbd2454e2d60425',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
    select * into c from erp.cp6_v2620l_rollback_capsule where object_regidentity=r.identity;
    if c.object_regidentity is null or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres' or c.acl_snapshot is distinct from r.acl
       or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'M_PREDECESSOR_L_CAPSULE_SOURCE_PIN_MISMATCH';
    end if;
  end loop;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','dc4ed2384dda4b34a30093cad8cb13fa80db26201371569a88dbaee790a24108','98fac1a865982d5c60fc5e6a5caae9033755ff915b7e53d22213c0d1d1765ca1',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_purchase_cost_correction(uuid)','d80d5d357acddd562412ada1a27fced5ac979c0ab1aa1dc0a9cbefa81aee0ad8','9542acde669945e633d5929cb5b441a2119b8f3bf9a69919ae46725d598e8ba9',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_material_supplier_invoice(uuid)','ec73a81f2bae980039edde861f01157337814a3bb9a0554f9d0275716c1f19d5','65ae76bce50952c2ced64ad7ec25c1039a1e3086048e5ea39eae71ec4c8b7d69',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_supplier_return(uuid)','562140bee0171cb892501ca4499e93e8b6d661772d1d03c95271283e6cea8714','f5f6603b258eeda0b34a10f06a301b94c488525dfddfe0863e5ded8f56244ad1',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_opening_financial_correction(uuid,numeric,text,date)','41ef3e9b7e9be5432cd09db2e4cba4d303c6c7205c2dcf92cb052293dc4062a7','95ad1f5db523bdc19d7b21d1f1b9e1baa49a499fb791f937fe43b0291d4bd7f1',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_opening_subledger_settlement(uuid)','95eb1e84cd0dabd02b3f11dc8745f72997b56fea47c04a9f56a9e18e9a9ebdf2','c56b387a8593b19cd3b92e6dc20ac95459d2aedeb2b616b6fb1e4d812e729393',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_supplier_payment(uuid)','3d77b3cc0339606aa7eb456b9b341af33f8251a7a0415229a2d7c08cfe54ef60','231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_purchase_cost_correction(uuid,text)','2cbfb722a7b644d47886e23555ef8dcffb2ea2060525c6251afa43e52689389b','dc17e41110f001f6f16d18d065745dc8e85bb9e58ef28e162522976da45c4a6f',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.reverse_material_supplier_invoice(uuid,text)','c269a2cb171184f49be2720e195bd24292f76d0127cb752ffc158a894768d1cb','76ee31ad50c747b5a9f5730a5a3e81ba79c1685f57f716ac211197f11aa7080e',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_supplier_return(uuid,text)','570bb23aeebdf5f309e34a84071a247ff201855b6c283f8a6264b7389816eaa6','ac2504b1f04d5eaf8bf63b13ce945adf17fda0104ac6e4f6c44ac831c255706b',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_opening_financial_correction(uuid,text)','5d794a5d6d4d63b2bc5e4b6407523488d1b87ba5c47ab557056fd566442ec50c','1ce99785ee8dc682b1b0f2aa9171f2110614baf4c9a99ecf4880b547496947fe',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.reverse_opening_subledger_settlement(uuid,text)','d5c1e4b368a13de3738d458c89584ec181149f6f070cc697111c61e56bfba07e','c01292aebb98ea09d0fb440215f9c4cdbd9ece3b98caa641b9b308faec542e1a',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.reverse_supplier_payment(uuid,text)','b6518df0cc3941554eca06016e483e8e020112778db67dad69202d4c032d40be','9733b0e39d82732fb4b2ec7be17c66bcff2a088a81cccd25892eb440d4923102',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','368c7f97b895ce7d08aa6b5fa5a77b50957191465a44e26ef9268b6424c93aea','efde954275e89f01793f405e2b000c6c599bae0be731869802f288994dd154fa',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','2bffd2d8f33ad2d918d1fb2f767676dc403ac777ad9a8ff69d4f32bf74067eff','48d60613970b015d1afb30a2f8a7cec0e5d56d1f692c6a1acfa0ffd48684fda1',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.predecessor_sha256
       or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'M_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH';
    end if;
  end loop;
end
$guard_v2620m$;
create table erp.cp6_v2620m_rollback_capsule(
  object_identity text primary key,
  object_regidentity text not null unique,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp(),
  boundary_snapshot jsonb
);
alter table erp.cp6_v2620m_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620m_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.cp6_v2620m_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a order by a::text) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp._v268_financial_report_checks_pre_scope()'::regprocedure,
  'erp.post_material_purchase_cost_correction(uuid)'::regprocedure,
  'erp.post_material_supplier_invoice(uuid)'::regprocedure,
  'erp.post_material_supplier_return(uuid)'::regprocedure,
  'erp.post_opening_financial_correction(uuid,numeric,text,date)'::regprocedure,
  'erp.post_opening_subledger_settlement(uuid)'::regprocedure,
  'erp.post_supplier_payment(uuid)'::regprocedure,
  'erp.reverse_material_purchase_cost_correction(uuid,text)'::regprocedure,
  'erp.reverse_material_supplier_invoice(uuid,text)'::regprocedure,
  'erp.reverse_material_supplier_return(uuid,text)'::regprocedure,
  'erp.reverse_opening_financial_correction(uuid,text)'::regprocedure,
  'erp.reverse_opening_subledger_settlement(uuid,text)'::regprocedure,
  'erp.reverse_supplier_payment(uuid,text)'::regprocedure,
  'erp.run_v267_financial_truth_checks()'::regprocedure,
  'erp.run_v268_financial_report_checks()'::regprocedure
);


CREATE OR REPLACE FUNCTION erp._v268_financial_report_checks_pre_scope()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
AS $function$
begin
  perform erp.require_owner_admin();

  return query
  with expected_daily as(
    select je.transaction_date balance_date,jl.account_id,
           sum(jl.debit)::numeric debit_total,sum(jl.credit)::numeric credit_total
    from erp.journal_entries je
    join erp.journal_lines jl on jl.journal_entry_id=je.id
    where je.status in('POSTED','REVERSED')
    group by je.transaction_date,jl.account_id
  ), daily_mismatch as(
    select 1
    from expected_daily e
    full join erp.account_daily_balances a
      on a.balance_date=e.balance_date and a.account_id=e.account_id
    where abs(coalesce(e.debit_total,0)-coalesce(a.debit_total,0))<>0
       or abs(coalesce(e.credit_total,0)-coalesce(a.credit_total,0))<>0
  ), bs as(
    select
      coalesce(sum(case when ca.account_type='ASSET' then adb.debit_total-adb.credit_total else 0 end),0)::numeric assets,
      coalesce(sum(case when ca.account_type='LIABILITY' then adb.credit_total-adb.debit_total else 0 end),0)::numeric liabilities,
      coalesce(sum(case when ca.account_type='EQUITY' then adb.credit_total-adb.debit_total else 0 end),0)::numeric equity,
      coalesce(sum(case when ca.account_type in('REVENUE','EXPENSE') then adb.credit_total-adb.debit_total else 0 end),0)::numeric current_earnings
    from erp.account_daily_balances adb
    join erp.chart_accounts ca on ca.id=adb.account_id
  ), ar as(
    select
      coalesce((select sum(a.debit_total-a.credit_total) from erp.account_daily_balances a
                where a.account_id=erp.account_id('AR_CUSTOMER')),0)::numeric gl_amount,
      coalesce((select sum(
        round(erp.sale_net_total(h.id),2)-coalesce((select sum(round(p.amount,2))
          from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'),0)
      ) from erp.sales_headers h
          where h.status in('POSTED','PARTIAL_PAID','PAID')),0)::numeric
      +coalesce((select sum(b.original_amount-b.settled_amount)
        from erp.opening_subledger_balances b
        join erp.opening_balance_items i on i.id=b.opening_item_id
        join erp.opening_balance_headers oh on oh.id=i.opening_id and oh.status='POSTED'
        where b.party_type='CUSTOMER' and b.direction='RECEIVABLE'),0) as subledger_amount
  )
  select 'V268_DAILY_BALANCE_LEDGER_MISMATCH','CRITICAL',count(*)::bigint,
         'account_daily_balances must exactly equal posted/reversed journal lines by GL date and account'
  from daily_mismatch

  union all
  select 'V268_UNBALANCED_POSTED_JOURNAL','CRITICAL',count(*)::bigint,
         'Every posted/reversed journal entry must remain debit-equals-credit'
  from(
    select je.id from erp.journal_entries je
    left join erp.journal_lines jl on jl.journal_entry_id=je.id
    where je.status in('POSTED','REVERSED')
    group by je.id having count(jl.id)<2
      or sum(jl.debit) is distinct from sum(jl.credit)
      or sum(jl.debit)::text in('NaN','Infinity','-Infinity')
      or sum(jl.credit)::text in('NaN','Infinity','-Infinity')
  ) q

  union all
  select 'V268_BALANCE_SHEET_EQUATION','CRITICAL',
         case when abs(assets-liabilities-equity-current_earnings)<>0 then 1 else 0 end::bigint,
         'Assets must equal liabilities plus recorded equity plus current earnings'
  from bs

  union all
  select 'V2620L_NONFINITE_LEDGER_MONEY','CRITICAL',count(*)::bigint,
         'Posted money and daily balances must be finite cent amounts'
  from(
    select 1 from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
    where j.status in('POSTED','REVERSED') and(
      l.debit::text in('NaN','Infinity','-Infinity')
      or l.credit::text in('NaN','Infinity','-Infinity'))
    union all
    select 1 from erp.account_daily_balances a where
      a.debit_total::text in('NaN','Infinity','-Infinity')
      or a.credit_total::text in('NaN','Infinity','-Infinity')
  ) invalid_money

  union all
  select 'V2620L_NEGATIVE_VENDOR_AP','CRITICAL',count(*)::bigint,
         'Each laundry vendor payable must remain finite and nonnegative; advances need a separate workflow'
  from(
    select l.vendor_id from erp.journal_lines l
    join erp.journal_entries j on j.id=l.journal_entry_id
    where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id('AP_VENDOR')
    group by l.vendor_id having sum(l.credit-l.debit)<0
      or sum(l.credit-l.debit)::text in('NaN','Infinity','-Infinity')
  ) negative_vendor

  union all
  select 'V268_AR_GL_SUBLEDGER_MISMATCH' ,'CRITICAL',
         case when round(gl_amount,2) is distinct from round(subledger_amount,2) then 1 else 0 end::bigint,
         'Customer AR general ledger must equal active sales net of posted returns and customer payments'
  from ar

  union all
  select r.check_name,r.severity,r.issue_count,r.details
  from erp.run_v267_financial_truth_checks() r
  where r.check_name in('V267_GRNI_GL_SUBLEDGER_MISMATCH','V267_AP_GL_SUBLEDGER_MISMATCH',
    'V267_PAYMENT_EXCEEDS_FINAL_AP') or r.check_name like 'V2620M_%'

  union all
  select 'V268_ACTIVE_SALE_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
         'Every non-zero active sale requires its SALE journal'
  from erp.sales_headers h
  where h.status in('POSTED','PARTIAL_PAID','PAID')
    and(
      coalesce((select sum(i.line_total) from erp.sales_items i where i.sale_id=h.id),0)>0.005
      or coalesce((select sum(a.qty_pcs*a.unit_hpp_snapshot)
                   from erp.sale_stock_allocations a
                   join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=h.id),0)>0.005
    )
    and not exists(select 1 from erp.journal_entries j
                   where j.source_type='SALE' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V268_POSTED_SALES_RETURN_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
         'Every non-zero posted sales return requires its SALES_RETURN journal'
  from erp.sales_returns h
  where h.status='POSTED'
    and coalesce((select sum(i.refund_amount+i.qty_pcs*i.unit_hpp_snapshot)
                  from erp.sales_return_items i where i.return_id=h.id),0)>0.005
    and not exists(select 1 from erp.journal_entries j
                   where j.source_type='SALES_RETURN' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V268_POSTED_CUSTOMER_PAYMENT_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
         'Every posted non-zero customer payment requires its SALES_PAYMENT journal'
  from erp.sales_payments p
  where p.status='POSTED' and p.amount>0.005
    and not exists(select 1 from erp.journal_entries j
                   where j.source_type='SALES_PAYMENT' and j.source_id=p.id and j.status='POSTED')

  union all
  select 'V268_PRODUCTION_FG_WITHOUT_CURRENT_HPP','CRITICAL',count(*)::bigint,
         'Every active production FG lot must have exactly one current HPP version'
  from erp.fg_lots l
  where l.lot_origin='PRODUCTION' and l.initial_qty_pcs>0
    and (select count(*) from erp.hpp_versions h where h.lot_id=l.id and h.is_current)<>1

  union all
  select 'V268_COST_RECALC_EXHAUSTED','CRITICAL',count(*)::bigint,
         'A permanently failed HPP recalc means owner profitability is not reliable'
  from erp.cost_recalc_queue q where q.status='FAILED' and q.attempt_count>=3

  union all
  select 'V268_COST_RECALC_PENDING','WARNING',count(*)::bigint,
         'Pending/running/retryable HPP recalc means profitability is provisional until the queue clears'
  from erp.cost_recalc_queue q
  where q.status in('PENDING','RUNNING') or(q.status='FAILED' and q.attempt_count<3)

  union all
  select 'V268_LIABILITY_VIEW_HELPER_PRIVILEGE','CRITICAL',count(*)::bigint,
         'Authenticated browser role needs EXECUTE on pure read helpers used by security-invoker liability views'
  from(values
    ('erp.material_purchase_grni_total(uuid)'),
    ('erp.material_purchase_final_ap_total(uuid)'),
    ('erp.material_purchase_total_liability(uuid)')
  ) f(signature)
  where not has_function_privilege('authenticated',f.signature,'EXECUTE')

  union all
  select 'V268_BROWSER_DIRECT_FINANCIAL_WRITE','CRITICAL',count(*)::bigint,
         'Browser roles must not directly mutate posted-source financial tables'
  from information_schema.role_table_grants g
  where g.table_schema='erp'
    and g.table_name in(
      'journal_entries','journal_lines','account_daily_balances',
      'material_supplier_invoices','material_supplier_invoice_lines',
      'sales_headers','sales_items','sales_returns','sales_return_items',
      'sales_payments','supplier_payments'
    )
    and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE');
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_material_purchase_cost_correction(p_correction_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.material_purchase_cost_corrections%rowtype;
  p erp.material_purchase_headers%rowtype;
  m record;
  r record;
  v_delta_payable numeric(24,6);
  v_old_cost numeric(18,6);
  v_material_delta numeric(24,6);
  v_current_payable numeric(24,6);
  v_proposed_payable numeric(24,6);
  v_paid numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
  v_post_seq bigint;
begin
  perform erp.require_owner_admin();
  select * into h from erp.material_purchase_cost_corrections where id=p_correction_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Material purchase cost correction must be DRAFT'; end if;
  select * into p from erp.material_purchase_headers where id=h.purchase_id for update;
  if p.id is null or p.status<>'POSTED' then raise exception 'Source material purchase must be POSTED'; end if;
  if not exists(select 1 from erp.material_purchase_cost_correction_items where correction_id=h.id) then raise exception 'Cost correction has no lines'; end if;

  select coalesce(max(c.post_seq),0)+1 into v_post_seq
  from erp.material_purchase_cost_corrections c
  where c.purchase_id=p.id and c.post_seq is not null;

  select erp.material_purchase_payable_total(p.id) into v_current_payable;
  select coalesce(sum(mpi.qty*(ci.new_unit_price-erp.material_purchase_current_unit_cost(mpi.id))),0)
  into v_delta_payable
  from erp.material_purchase_cost_correction_items ci
  join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
  where ci.correction_id=h.id;
  v_proposed_payable:=v_current_payable+v_delta_payable;
  select coalesce(sum(sp.amount),0) into v_paid from erp.supplier_payments sp where sp.purchase_id=p.id and sp.status='POSTED';
  if round(v_proposed_payable,2)<0 then raise exception 'Corrected purchase payable cannot become negative'; end if;
  if v_paid>round(v_proposed_payable,2) then raise exception 'Cost correction would make supplier payments exceed corrected payable. Use supplier credit/receivable correction flow'; end if;

  for m in
    select distinct mpi.material_id
    from erp.material_purchase_cost_correction_items ci join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
    where ci.correction_id=h.id
  loop
    v_material_delta:=0;
    for r in
      select ci.id as correction_item_id,ci.purchase_item_id,ci.new_unit_price,mpi.qty,mpi.material_id
      from erp.material_purchase_cost_correction_items ci
      join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
      where ci.correction_id=h.id and mpi.material_id=m.material_id
      order by ci.id
    loop
      v_old_cost:=erp.material_purchase_current_unit_cost(r.purchase_item_id);
      update erp.material_purchase_cost_correction_items
      set old_unit_cost_snapshot=v_old_cost,qty_basis=r.qty,delta_amount=r.qty*(r.new_unit_price-v_old_cost)
      where id=r.correction_item_id;
      v_material_delta:=v_material_delta+(r.qty*(r.new_unit_price-v_old_cost));
      update erp.material_stock_movements msm
      set input_unit_cost=r.new_unit_price
      where msm.movement_type='PURCHASE' and msm.qty_signed>0 and (
        (msm.source_type='MATERIAL_PURCHASE_ITEM' and msm.source_id=r.purchase_item_id)
        or (msm.source_type='MATERIAL_PURCHASE_ROLL' and msm.source_id in(select mr.id from erp.material_rolls mr where mr.purchase_item_id=r.purchase_item_id))
      );
      if not found then raise exception 'Original purchase stock movement not found for purchase item %',r.purchase_item_id; end if;
    end loop;

    perform erp.recalculate_material_cost(m.material_id,p.physical_at);

    if abs(v_material_delta)>0.005 then
      if v_material_delta>0 then
        v_lines:=v_lines||jsonb_build_array(
          jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',round(v_material_delta,2),'credit',0),
          jsonb_build_object('mapping_key','AP_SUPPLIER','debit',0,'credit',round(v_material_delta,2))
        );
      else
        v_lines:=v_lines||jsonb_build_array(
          jsonb_build_object('mapping_key','AP_SUPPLIER','debit',round(abs(v_material_delta),2),'credit',0),
          jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',0,'credit',round(abs(v_material_delta),2))
        );
      end if;
    end if;
  end loop;

  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('MATERIAL_PURCHASE_COST_CORRECTION',h.id,h.invoice_date,'Late/final fabric supplier invoice cost correction',v_lines);
  end if;
  update erp.material_purchase_cost_corrections
  set status='POSTED',posted_at=clock_timestamp(),post_seq=v_post_seq
  where id=h.id;
  select erp.material_purchase_payable_total(p.id) into v_proposed_payable;
  select coalesce(sum(sp.amount),0) into v_paid from erp.supplier_payments sp where sp.purchase_id=p.id and sp.status='POSTED';
  update erp.material_purchase_headers set payment_status=case when v_paid=round(v_proposed_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end where id=p.id;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_material_supplier_invoice(p_invoice_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  h erp.material_supplier_invoices%rowtype;
  r record;
  v_capacity numeric;
  v_matched numeric;
  v_old_cost numeric;
  v_new_cost numeric;
  v_basis_qty numeric;
  v_delta_before numeric;
  v_delta_after numeric;
  v_inventory_delta numeric;
  v_liability_delta numeric;
  v_bridge numeric;
  v_grni_total numeric(24,6):=0;
  v_ap_total numeric(24,6):=0;
  v_inventory_total numeric(24,6):=0;
  v_bridge_total numeric(24,6):=0;
  v_lines jsonb:='[]'::jsonb;
  v_purchase uuid;
  v_paid numeric;
  v_payable numeric;
begin
  perform erp.require_owner_admin();
  select * into h from erp.material_supplier_invoices where id=p_invoice_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Material supplier invoice must be DRAFT'; end if;
  if h.invoice_date>current_date then raise exception 'Supplier invoice date cannot be in the future'; end if;
  if h.received_at::date>current_date then raise exception 'Supplier invoice received_at cannot be in the future'; end if;
  if not exists(select 1 from erp.material_supplier_invoice_lines where invoice_id=h.id) then
    raise exception 'Material supplier invoice has no lines';
  end if;

  -- Deterministic lock order protects concurrent invoice/payment/return clicks.
  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    perform 1 from erp.material_purchase_headers where id=v_purchase for update;
  end loop;
  for r in
    select distinct i.id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.id
  loop
    perform 1 from erp.material_purchase_items where id=r.id for update;
  end loop;

  for r in
    select l.*,i.qty as receipt_qty,i.unit_price as estimate_unit_cost,
           i.material_id,i.purchase_id,i.invoice_match_state,
           ph.supplier_id,ph.physical_at
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    join erp.material_purchase_headers ph on ph.id=i.purchase_id
    where l.invoice_id=h.id order by i.id
  loop
    if r.supplier_id is distinct from h.supplier_id then
      raise exception 'Invoice supplier does not match receipt supplier for item %',r.purchase_item_id;
    end if;
    if r.invoice_match_state='DIRECT_FINAL' then
      raise exception 'Receipt item % was already final-invoiced at physical receipt',r.purchase_item_id;
    end if;
    v_capacity:=erp.material_purchase_invoice_capacity(r.purchase_item_id);
    v_matched:=erp.material_purchase_posted_invoice_qty(r.purchase_item_id);
    if v_matched+r.qty_invoiced>v_capacity+0.000001 then
      raise exception 'Invoice quantity exceeds unmatched receipt quantity for item %. Capacity %, already matched %, requested %',
        r.purchase_item_id,v_capacity,v_matched,r.qty_invoiced;
    end if;

    v_old_cost:=erp.material_purchase_current_unit_cost(r.purchase_item_id);
    v_basis_qty:=v_capacity;
    select coalesce(sum(x.net_amount-(x.qty_invoiced*r.estimate_unit_cost)),0)
    into v_delta_before
    from erp.material_supplier_invoice_lines x
    join erp.material_supplier_invoices xh on xh.id=x.invoice_id
    where x.purchase_item_id=r.purchase_item_id and xh.status='POSTED';
    v_delta_after:=v_delta_before+(r.net_amount-(r.qty_invoiced*r.estimate_unit_cost));
    v_new_cost:=greatest(((v_basis_qty*r.estimate_unit_cost)+v_delta_after)/v_basis_qty,0);
    v_inventory_delta:=r.receipt_qty*(v_new_cost-v_old_cost);
    v_liability_delta:=r.net_amount-(r.qty_invoiced*r.estimate_unit_cost);
    v_bridge:=v_inventory_delta-v_liability_delta;

    update erp.material_supplier_invoice_lines
    set receipt_estimate_unit_cost_snapshot=r.estimate_unit_cost,
        prior_blended_unit_cost_snapshot=v_old_cost,
        posted_blended_unit_cost_snapshot=v_new_cost,
        grni_clear_amount_snapshot=r.qty_invoiced*r.estimate_unit_cost,
        ap_create_amount_snapshot=r.net_amount,
        inventory_revaluation_snapshot=v_inventory_delta,
        bridge_variance_snapshot=v_bridge
    where id=r.id;

    v_grni_total:=v_grni_total+(r.qty_invoiced*r.estimate_unit_cost);
    v_ap_total:=v_ap_total+r.net_amount;
    v_inventory_total:=v_inventory_total+v_inventory_delta;
    v_bridge_total:=v_bridge_total+v_bridge;
  end loop;

  update erp.material_supplier_invoices
  set status='POSTED',posted_at=clock_timestamp(),posting_reason=coalesce(posting_reason,'Supplier invoice posted')
  where id=h.id;

  if v_grni_total>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','GRNI_MATERIAL','debit',round(v_grni_total,2),'credit',0));
  end if;
  if v_inventory_total>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','MATERIAL_INVENTORY','debit',round(v_inventory_total,2),'credit',0));
  elsif v_inventory_total< -0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','MATERIAL_INVENTORY','debit',0,'credit',round(abs(v_inventory_total),2)));
  end if;
  if v_bridge_total>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','MATERIAL_PURCHASE_VARIANCE','debit',0,'credit',round(v_bridge_total,2)));
  elsif v_bridge_total< -0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','MATERIAL_PURCHASE_VARIANCE','debit',round(abs(v_bridge_total),2),'credit',0));
  end if;
  if v_ap_total>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','AP_SUPPLIER','debit',0,'credit',round(v_ap_total,2)));
  end if;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal(
      'MATERIAL_SUPPLIER_INVOICE',h.id,h.invoice_date,
      'Final supplier invoice / GRNI matching '||h.invoice_number,v_lines
    );
  end if;

  for r in
    select distinct l.purchase_item_id
    from erp.material_supplier_invoice_lines l
    where l.invoice_id=h.id order by l.purchase_item_id
  loop
    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_payable,v_paid;
    update erp.material_purchase_headers
    set supplier_invoice_number=h.invoice_number,
        due_date=coalesce(h.due_date,due_date),
        payment_status=case when v_paid=round(v_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_material_supplier_return(p_return_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  h erp.material_supplier_returns%rowtype;
  r record;
  v_purchase uuid;
  v_invoiced_qty numeric;
  v_prior_ap_qty numeric;
  v_ap_qty numeric;
  v_grni_qty numeric;
  v_paid numeric;
  v_payable numeric;
  v_proposed_relief numeric;
  v_carry numeric(24,6):=0;
  v_ap_relief numeric(24,6):=0;
  v_grni_relief numeric(24,6):=0;
  v_line_carry numeric(24,6);
  v_variance numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  select * into h from erp.material_supplier_returns where id=p_return_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Supplier return must be DRAFT'; end if;
  if h.location_id is null then raise exception 'Supplier return location is required'; end if;
  if not exists(select 1 from erp.material_supplier_return_items where return_id=h.id) then
    raise exception 'Supplier return has no lines';
  end if;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    perform 1 from erp.material_purchase_headers where id=v_purchase for update;
  end loop;

  -- Allocate each physical return against already-final AP first; any remaining
  -- quantity cancels the receipt estimate in GRNI. These snapshots are immutable
  -- once the document posts and make reversal deterministic.
  for r in
    select ri.*,i.qty as receipt_qty,i.unit_price as estimate_unit_cost,
           i.invoice_match_state,i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.id,ri.id
  loop
    perform 1 from erp.material_purchase_items where id=r.purchase_item_id for update;
    v_invoiced_qty:=case when r.invoice_match_state='DIRECT_FINAL'
      then r.receipt_qty else erp.material_purchase_posted_invoice_qty(r.purchase_item_id) end;
    select coalesce(sum(coalesce(x.ap_relief_qty_snapshot,0)),0)
    into v_prior_ap_qty
    from erp.material_supplier_return_items x
    join erp.material_supplier_returns xh on xh.id=x.return_id
    where x.purchase_item_id=r.purchase_item_id and xh.status='POSTED';
    v_ap_qty:=least(r.qty,greatest(v_invoiced_qty-v_prior_ap_qty,0));
    v_grni_qty:=r.qty-v_ap_qty;
    update erp.material_supplier_return_items
    set ap_relief_qty_snapshot=v_ap_qty,
        grni_relief_qty_snapshot=v_grni_qty,
        ap_relief_amount_snapshot=v_ap_qty*r.supplier_credit_unit_price,
        grni_relief_amount_snapshot=v_grni_qty*r.estimate_unit_cost
    where id=r.id;
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0),
           coalesce(sum(ri.ap_relief_amount_snapshot),0)
    into v_payable,v_paid,v_proposed_relief
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id and i.purchase_id=v_purchase;
    if v_paid>round(v_payable-v_proposed_relief,2) then
      raise exception 'Supplier return would make payment % exceed projected final AP %. Reverse/correct supplier payment first.',
        v_paid,v_payable-v_proposed_relief;
    end if;
  end loop;

  update erp.material_supplier_returns set status='POSTED' where id=h.id;

  for r in
    select ri.*
    from erp.material_supplier_return_items ri
    where ri.return_id=h.id order by ri.material_id,ri.id
  loop
    insert into erp.material_stock_movements(
      material_id,roll_id,location_id,movement_type,qty_signed,
      source_type,source_id,physical_at,created_by,note
    ) values(
      r.material_id,r.roll_id,h.location_id,'SUPPLIER_RETURN',-r.qty,
      'MATERIAL_SUPPLIER_RETURN_ITEM',r.id,h.physical_at,erp.current_app_user_id(),h.reason
    );

    -- GRNI-backed returns reduce the cost-basis quantity. Recompute the source
    -- purchase layer before replaying chronological MA.
    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    select r.qty*coalesce(msm.unit_cost_snapshot,0)
    into v_line_carry
    from erp.material_stock_movements msm
    where msm.source_type='MATERIAL_SUPPLIER_RETURN_ITEM' and msm.source_id=r.id
    order by msm.system_created_at desc,msm.id desc limit 1;
    v_carry:=v_carry+coalesce(v_line_carry,0);
    v_ap_relief:=v_ap_relief+coalesce(r.ap_relief_amount_snapshot,0);
    v_grni_relief:=v_grni_relief+coalesce(r.grni_relief_amount_snapshot,0);
    if r.roll_id is not null then
      update erp.material_rolls
      set status=case when cached_qty=0 then 'RETURNED_SUPPLIER' else status end,updated_at=now()
      where id=r.roll_id;
    end if;
  end loop;

  v_variance:=v_carry-v_ap_relief-v_grni_relief;
  if v_ap_relief>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','AP_SUPPLIER','debit',round(v_ap_relief,2),'credit',0));
  end if;
  if v_grni_relief>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','GRNI_MATERIAL','debit',round(v_grni_relief,2),'credit',0));
  end if;
  if v_variance>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','MATERIAL_PURCHASE_VARIANCE','debit',round(v_variance,2),'credit',0));
  elsif v_variance< -0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','MATERIAL_PURCHASE_VARIANCE','debit',0,'credit',round(abs(v_variance),2)));
  end if;
  if v_carry>0.005 then
    v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','MATERIAL_INVENTORY','debit',0,'credit',round(v_carry,2)));
  end if;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal(
      'MATERIAL_SUPPLIER_RETURN',h.id,h.physical_at::date,
      'Material returned to supplier; AP/GRNI relief split',v_lines
    );
  end if;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_payable,v_paid;
    update erp.material_purchase_headers
    set payment_status=case when v_paid=round(v_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_opening_financial_correction(p_opening_item_id uuid, p_corrected_amount numeric, p_reason text, p_effective_date date DEFAULT CURRENT_DATE)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  i erp.opening_balance_items%rowtype;
  h_status text;
  b erp.opening_subledger_balances%rowtype;
  v_old numeric(20,2);
  v_new numeric(20,2);
  v_delta numeric(20,2);
  v_id uuid;
  v_no text;
  v_lines jsonb:='[]'::jsonb;
  v_cash uuid;
  v_abs numeric(20,2);
  v_seq bigint;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan koreksi saldo awal wajib diisi'; end if;
  if p_corrected_amount is null or p_corrected_amount<0 then raise exception 'Saldo awal hasil koreksi tidak boleh negatif'; end if;
  if p_effective_date is null then raise exception 'Tanggal koreksi saldo awal wajib diisi'; end if;

  select * into i from erp.opening_balance_items where id=p_opening_item_id for update;
  if i.id is null then raise exception 'Item saldo awal tidak ditemukan'; end if;
  select status into h_status from erp.opening_balance_headers where id=i.opening_id for update;
  if h_status<>'POSTED' then raise exception 'Saldo awal harus sudah POSTED sebelum dikoreksi'; end if;
  if i.balance_type not in ('WIP','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE','CUSTOMER_RECEIVABLE','CASH_BANK') then
    raise exception 'Jenis saldo awal % tidak dikoreksi lewat jalur finansial ini. Stok MATERIAL/FG gunakan stock adjustment agar lineage tetap aman.',i.balance_type;
  end if;

  select coalesce(max(c.correction_seq),0)+1
    into v_seq
  from erp.opening_financial_corrections c
  where c.opening_item_id=i.id;

  if i.balance_type in ('CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE','CUSTOMER_RECEIVABLE') then
    select * into b from erp.opening_subledger_balances where opening_item_id=i.id for update;
    if b.id is null then raise exception 'Opening subledger untuk item ini tidak ditemukan'; end if;
    v_old:=b.original_amount;
    if round(p_corrected_amount,2) < b.settled_amount then
      raise exception 'Saldo awal tidak boleh dikoreksi menjadi % karena sudah disettle %. Reverse settlement terkait terlebih dahulu.',p_corrected_amount,b.settled_amount;
    end if;
  else
    select coalesce((select c.corrected_amount from erp.opening_financial_corrections c where c.opening_item_id=i.id and c.status='POSTED' order by c.correction_seq desc limit 1),
                    case when i.balance_type='WIP' then coalesce(i.amount,coalesce(i.qty,0)*coalesce(i.unit_cost_snapshot,0)) else coalesce(i.amount,0) end)::numeric(20,2)
    into v_old;
  end if;

  v_new:=round(p_corrected_amount::numeric,2);
  v_delta:=v_new-v_old;
  if abs(v_delta)<=0.005 then raise exception 'Nilai koreksi sama dengan saldo awal efektif saat ini (%)',v_old; end if;
  v_no:='OFC-'||to_char(clock_timestamp(),'YYYYMMDDHH24MISSMS')||'-'||substr(gen_random_uuid()::text,1,6);
  insert into erp.opening_financial_corrections(correction_number,opening_item_id,previous_amount_snapshot,corrected_amount,delta_amount,effective_date,reason,created_by,created_at,correction_seq)
  values(v_no,i.id,v_old,v_new,v_delta,p_effective_date,p_reason,erp.current_app_user_id(),clock_timestamp(),v_seq) returning id into v_id;

  v_abs:=round(abs(v_delta),2);
  if i.balance_type='CASH_BANK' then
    select coa_account_id into v_cash from erp.cash_accounts where id=i.cash_account_id;
    if v_cash is null then raise exception 'Cash/bank account saldo awal tidak ditemukan'; end if;
    if v_delta>0 then v_lines:=jsonb_build_array(
      jsonb_build_object('account_id',v_cash,'debit',v_abs,'credit',0),
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',0,'credit',v_abs));
    else v_lines:=jsonb_build_array(
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',v_abs,'credit',0),
      jsonb_build_object('account_id',v_cash,'debit',0,'credit',v_abs)); end if;
  elsif i.balance_type in ('WIP','CUSTOMER_RECEIVABLE','CONTRACTOR_RECEIVABLE') then
    if v_delta>0 then v_lines:=jsonb_build_array(
      case when i.balance_type='WIP' then jsonb_build_object('mapping_key','WIP','debit',v_abs,'credit',0)
           when i.balance_type='CUSTOMER_RECEIVABLE' then jsonb_build_object('mapping_key','AR_CUSTOMER','debit',v_abs,'credit',0,'customer_id',i.customer_id)
           else jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',v_abs,'credit',0,'contractor_id',i.contractor_id) end,
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',0,'credit',v_abs));
    else v_lines:=jsonb_build_array(
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',v_abs,'credit',0),
      case when i.balance_type='WIP' then jsonb_build_object('mapping_key','WIP','debit',0,'credit',v_abs)
           when i.balance_type='CUSTOMER_RECEIVABLE' then jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',v_abs,'customer_id',i.customer_id)
           else jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',v_abs,'contractor_id',i.contractor_id) end); end if;
  else
    if v_delta>0 then v_lines:=jsonb_build_array(
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',v_abs,'credit',0),
      case when i.balance_type='SUPPLIER_PAYABLE' then jsonb_build_object('mapping_key','AP_SUPPLIER','debit',0,'credit',v_abs)
           when i.balance_type='VENDOR_PAYABLE' then jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',v_abs,'vendor_id',i.vendor_id)
           else jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_abs,'contractor_id',i.contractor_id) end);
    else v_lines:=jsonb_build_array(
      case when i.balance_type='SUPPLIER_PAYABLE' then jsonb_build_object('mapping_key','AP_SUPPLIER','debit',v_abs,'credit',0)
           when i.balance_type='VENDOR_PAYABLE' then jsonb_build_object('mapping_key','AP_VENDOR','debit',v_abs,'credit',0,'vendor_id',i.vendor_id)
           else jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_abs,'credit',0,'contractor_id',i.contractor_id) end,
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',0,'credit',v_abs)); end if;
  end if;

  perform erp.post_journal('OPENING_FINANCIAL_CORRECTION',v_id,p_effective_date,'Correction saldo awal: '||p_reason,v_lines);
  if b.id is not null then
    update erp.opening_subledger_balances
    set original_amount=v_new,
        status=case when settled_amount=v_new then 'SETTLED' when settled_amount>0 then 'PARTIAL' else 'OPEN' end,
        updated_at=now()
    where id=b.id;
  end if;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('opening_balance_items',i.id,'UPDATE',jsonb_build_object('correction_id',v_id,'previous_amount',v_old,'corrected_amount',v_new,'delta',v_delta,'correction_type','OPENING_FINANCIAL_CORRECTION'),erp.current_app_user_id(),p_reason);
  return v_id;
end;
$function$;

CREATE OR REPLACE FUNCTION erp.post_opening_subledger_settlement(p_settlement_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
DECLARE s erp.opening_subledger_settlements%ROWTYPE;b erp.opening_subledger_balances%ROWTYPE;v_cash uuid;v_remaining numeric(20,2);v_lines jsonb;
BEGIN PERFORM erp.require_owner_admin();SELECT * INTO s FROM erp.opening_subledger_settlements WHERE id=p_settlement_id FOR UPDATE;IF s.id IS NULL OR s.status<>'DRAFT' THEN RAISE EXCEPTION 'Opening subledger settlement must be DRAFT';END IF;SELECT * INTO b FROM erp.opening_subledger_balances WHERE id=s.balance_id FOR UPDATE;IF b.id IS NULL OR b.status='SETTLED' THEN RAISE EXCEPTION 'Opening subledger balance is not open';END IF;v_remaining:=b.original_amount-b.settled_amount;IF s.amount>v_remaining THEN RAISE EXCEPTION 'Settlement exceeds opening outstanding. Remaining %, requested %',v_remaining,s.amount;END IF;SELECT coa_account_id INTO v_cash FROM erp.cash_accounts WHERE id=s.cash_account_id AND is_active=true;IF v_cash IS NULL THEN RAISE EXCEPTION 'Active cash/bank account is required';END IF;
IF b.direction='RECEIVABLE' AND b.party_type='CUSTOMER' THEN v_lines:=jsonb_build_array(jsonb_build_object('account_id',v_cash,'debit',s.amount,'credit',0,'customer_id',b.customer_id),jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',s.amount,'customer_id',b.customer_id));ELSIF b.direction='RECEIVABLE' AND b.party_type='CONTRACTOR' THEN v_lines:=jsonb_build_array(jsonb_build_object('account_id',v_cash,'debit',s.amount,'credit',0,'contractor_id',b.contractor_id),jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',s.amount,'contractor_id',b.contractor_id));ELSIF b.direction='PAYABLE' AND b.party_type='SUPPLIER' THEN v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','AP_SUPPLIER','debit',s.amount,'credit',0),jsonb_build_object('account_id',v_cash,'debit',0,'credit',s.amount));ELSIF b.direction='PAYABLE' AND b.party_type='VENDOR' THEN v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','AP_VENDOR','debit',s.amount,'credit',0,'vendor_id',b.vendor_id),jsonb_build_object('account_id',v_cash,'debit',0,'credit',s.amount,'vendor_id',b.vendor_id));ELSIF b.direction='PAYABLE' AND b.party_type='CONTRACTOR' THEN v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',s.amount,'credit',0,'contractor_id',b.contractor_id),jsonb_build_object('account_id',v_cash,'debit',0,'credit',s.amount,'contractor_id',b.contractor_id));ELSE RAISE EXCEPTION 'Unsupported opening subledger direction/party combination';END IF;
PERFORM erp.post_journal('OPENING_SUBLEDGER_SETTLEMENT',s.id,s.physical_at::date,'Opening subledger settlement '||s.settlement_number,v_lines);UPDATE erp.opening_subledger_settlements SET status='POSTED',updated_at=now() WHERE id=s.id;UPDATE erp.opening_subledger_balances SET settled_amount=settled_amount+s.amount,status=CASE WHEN settled_amount+s.amount=original_amount THEN 'SETTLED' ELSE 'PARTIAL' END,updated_at=now() WHERE id=b.id;END;$function$;

CREATE OR REPLACE FUNCTION erp.post_supplier_payment(p_payment_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare p erp.supplier_payments%rowtype;h erp.material_purchase_headers%rowtype;v_cash uuid;v_paid numeric(20,2);v_total numeric(20,2);
begin
  perform erp.require_internal();select * into p from erp.supplier_payments where id=p_payment_id for update;
  if p.id is null or p.status<>'DRAFT' then raise exception 'Supplier payment must be DRAFT'; end if;
  select * into h from erp.material_purchase_headers where id=p.purchase_id for update;
  if h.id is null or h.status<>'POSTED' then raise exception 'Material purchase must be POSTED before payment'; end if;
  select erp.material_purchase_payable_total(h.id)::numeric(20,2) into v_total;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid from erp.supplier_payments where purchase_id=h.id and status='POSTED';
  if v_paid+p.amount>v_total then raise exception 'Supplier payment exceeds remaining payable. Net payable %, already paid %, requested %',v_total,v_paid,p.amount; end if;
  select coa_account_id into v_cash from erp.cash_accounts where id=p.cash_account_id and is_active=true;
  if v_cash is null then raise exception 'Active cash/bank account is required'; end if;
  perform erp.post_journal('SUPPLIER_PAYMENT',p.id,p.payment_date::date,'Material supplier payment',jsonb_build_array(
    jsonb_build_object('mapping_key','AP_SUPPLIER','debit',p.amount,'credit',0),jsonb_build_object('account_id',v_cash,'debit',0,'credit',p.amount)));
  update erp.supplier_payments set status='POSTED' where id=p.id;v_paid:=v_paid+p.amount;
  update erp.material_purchase_headers set payment_status=case when v_paid=round(v_total,2) then 'PAID' else 'PARTIAL' end where id=h.id;
end;$function$;

CREATE OR REPLACE FUNCTION erp.reverse_material_purchase_cost_correction(p_correction_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.material_purchase_cost_corrections%rowtype;
  p erp.material_purchase_headers%rowtype;
  r record;
  m uuid;
  v_journal uuid;
  v_current_payable numeric(24,6);
  v_delta numeric(24,6);
  v_projected numeric(24,6);
  v_paid numeric(24,6);
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal koreksi harga pembelian wajib diisi'; end if;
  select * into h from erp.material_purchase_cost_corrections where id=p_correction_id for update;
  if h.id is null then raise exception 'Koreksi harga pembelian tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya koreksi harga pembelian POSTED yang dapat direverse'; end if;
  if h.post_seq is null then raise exception 'Urutan posting koreksi harga pembelian tidak ditemukan; reversal dibatalkan'; end if;
  select * into p from erp.material_purchase_headers where id=h.purchase_id for update;
  if p.id is null or p.status<>'POSTED' then raise exception 'Pembelian sumber harus masih POSTED'; end if;

  if exists(
    select 1
    from erp.material_purchase_cost_correction_items ci
    join erp.material_purchase_cost_correction_items ci2 on ci2.purchase_item_id=ci.purchase_item_id
    join erp.material_purchase_cost_corrections c2 on c2.id=ci2.correction_id
    where ci.correction_id=h.id and c2.status='POSTED' and c2.id<>h.id
      and c2.post_seq>h.post_seq
  ) then
    raise exception 'Ada koreksi harga yang lebih baru pada item pembelian ini. Reverse koreksi terbaru terlebih dahulu.';
  end if;

  select erp.material_purchase_payable_total(p.id) into v_current_payable;
  select coalesce(sum(delta_amount),0) into v_delta
  from erp.material_purchase_cost_correction_items where correction_id=h.id;
  v_projected:=v_current_payable-v_delta;
  select coalesce(sum(amount),0) into v_paid from erp.supplier_payments where purchase_id=p.id and status='POSTED';
  if v_paid>round(v_projected,2) then
    raise exception 'Reversal koreksi harga membuat pembayaran supplier melebihi hutang tersisa. Reverse/koreksi pembayaran supplier terlebih dahulu.';
  end if;

  for r in
    select ci.*,mpi.material_id
    from erp.material_purchase_cost_correction_items ci
    join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id
    where ci.correction_id=h.id order by ci.id
  loop
    if r.old_unit_cost_snapshot is null then
      raise exception 'Snapshot harga sebelum koreksi tidak ditemukan untuk item %; reversal dibatalkan',r.purchase_item_id;
    end if;
    update erp.material_stock_movements msm
    set input_unit_cost=r.old_unit_cost_snapshot
    where msm.movement_type='PURCHASE' and msm.qty_signed>0 and (
      (msm.source_type='MATERIAL_PURCHASE_ITEM' and msm.source_id=r.purchase_item_id)
      or (msm.source_type='MATERIAL_PURCHASE_ROLL' and msm.source_id in (select mr.id from erp.material_rolls mr where mr.purchase_item_id=r.purchase_item_id))
    );
  end loop;

  update erp.material_purchase_cost_corrections set status='REVERSED' where id=h.id;
  for m in
    select distinct mpi.material_id from erp.material_purchase_cost_correction_items ci
    join erp.material_purchase_items mpi on mpi.id=ci.purchase_item_id where ci.correction_id=h.id
  loop
    perform erp.recalculate_material_cost(m,p.physical_at);
  end loop;

  select id into v_journal from erp.journal_entries
  where source_type='MATERIAL_PURCHASE_COST_CORRECTION' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if abs(v_delta)>0.005 and v_journal is null then
    raise exception 'Jurnal koreksi harga pembelian tidak ditemukan; reversal dibatalkan agar inventory/AP tidak rusak';
  end if;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;

  select erp.material_purchase_payable_total(p.id) into v_projected;
  select coalesce(sum(amount),0) into v_paid from erp.supplier_payments where purchase_id=p.id and status='POSTED';
  update erp.material_purchase_headers set payment_status=case when v_paid=round(v_projected,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end where id=p.id;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('material_purchase_cost_corrections',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_material_supplier_invoice(p_invoice_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  h erp.material_supplier_invoices%rowtype;
  r record;
  v_purchase uuid;
  v_current_ap numeric;
  v_invoice_ap numeric;
  v_paid numeric;
  v_journal uuid;
  v_latest record;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null then raise exception 'Supplier invoice reversal reason is required'; end if;
  select * into h from erp.material_supplier_invoices where id=p_invoice_id for update;
  if h.id is null then raise exception 'Material supplier invoice not found'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Only a POSTED supplier invoice may be reversed'; end if;

  if exists(
    select 1
    from erp.material_supplier_invoice_lines l
    join erp.material_supplier_return_items ri on ri.purchase_item_id=l.purchase_item_id
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    where l.invoice_id=h.id and rh.status='POSTED'
      and coalesce(ri.ap_relief_qty_snapshot,0)>0
  ) then
    raise exception 'Reverse AP-backed supplier returns before reversing this invoice';
  end if;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    perform 1 from erp.material_purchase_headers where id=v_purchase for update;
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce(sum(l.net_amount),0),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_current_ap,v_invoice_ap,v_paid
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id and i.purchase_id=v_purchase;
    if v_paid>round(v_current_ap-v_invoice_ap,2) then
      raise exception 'Reverse supplier payments first: payment % would exceed projected final AP %',
        v_paid,v_current_ap-v_invoice_ap;
    end if;
  end loop;

  select id into v_journal from erp.journal_entries
  where source_type='MATERIAL_SUPPLIER_INVOICE' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if exists(
    select 1 from erp.material_supplier_invoice_lines
    where invoice_id=h.id and(
      coalesce(grni_clear_amount_snapshot,0)<>0
      or coalesce(ap_create_amount_snapshot,0)<>0
      or coalesce(inventory_revaluation_snapshot,0)<>0
    )
  ) and v_journal is null then
    raise exception 'Supplier invoice journal is missing; reversal aborted to protect AP/GRNI/HPP';
  end if;

  update erp.material_supplier_invoices
  set status='REVERSED',reversed_at=clock_timestamp(),reversal_reason=btrim(p_reason)
  where id=h.id;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;

  for r in
    select distinct l.purchase_item_id
    from erp.material_supplier_invoice_lines l
    where l.invoice_id=h.id order by l.purchase_item_id
  loop
    perform erp.refresh_material_purchase_item_cost(r.purchase_item_id);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
  end loop;

  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_invoice_lines l
    join erp.material_purchase_items i on i.id=l.purchase_item_id
    where l.invoice_id=h.id order by i.purchase_id
  loop
    select ih.invoice_number,ih.due_date into v_latest
    from erp.material_supplier_invoices ih
    join erp.material_supplier_invoice_lines il on il.invoice_id=ih.id
    join erp.material_purchase_items pi on pi.id=il.purchase_item_id
    where pi.purchase_id=v_purchase and ih.status='POSTED'
    order by ih.posted_at desc,ih.id desc limit 1;
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_current_ap,v_paid;
    update erp.material_purchase_headers
    set supplier_invoice_number=v_latest.invoice_number,
        due_date=v_latest.due_date,
        payment_status=case when v_paid=round(v_current_ap,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('material_supplier_invoices',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_material_supplier_return(p_return_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  h erp.material_supplier_returns%rowtype;
  r record;
  v_journal uuid;
  v_purchase uuid;
  v_payable numeric;
  v_paid numeric;
  v_roll_qty numeric;
  v_cost numeric;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null then raise exception 'Alasan reversal retur supplier wajib diisi'; end if;
  select * into h from erp.material_supplier_returns where id=p_return_id for update;
  if h.id is null then raise exception 'Retur supplier tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya retur supplier POSTED yang dapat direverse'; end if;

  perform erp.lock_supplier_return_source_purchases(h.id);
  select id into v_journal from erp.journal_entries
  where source_type='MATERIAL_SUPPLIER_RETURN' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if exists(
    select 1 from erp.material_supplier_return_items
    where return_id=h.id and(
      coalesce(ap_relief_amount_snapshot,0)<>0
      or coalesce(grni_relief_amount_snapshot,0)<>0
    )
  ) and v_journal is null then
    raise exception 'Jurnal retur supplier tidak ditemukan; reversal dibatalkan agar stok/AP/GRNI tidak rusak';
  end if;

  update erp.material_supplier_returns set status='REVERSED',updated_at=now() where id=h.id;

  -- Recalculate the purchase source input before reverse_material_movement runs,
  -- so its single chronological replay sees the restored GRNI cost-basis.
  for r in
    select distinct ri.purchase_item_id,i.material_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by ri.purchase_item_id
  loop
    v_cost:=erp.material_purchase_current_unit_cost(r.purchase_item_id);
    update erp.material_stock_movements msm
    set input_unit_cost=v_cost
    where msm.movement_type='PURCHASE' and msm.qty_signed>0 and(
      (msm.source_type='MATERIAL_PURCHASE_ITEM' and msm.source_id=r.purchase_item_id)
      or
      (msm.source_type='MATERIAL_PURCHASE_ROLL' and msm.source_id in(
        select mr.id from erp.material_rolls mr where mr.purchase_item_id=r.purchase_item_id
      ))
    );
  end loop;

  for r in
    select msm.id,ri.roll_id,ri.purchase_item_id
    from erp.material_stock_movements msm
    join erp.material_supplier_return_items ri on ri.id=msm.source_id
    where ri.return_id=h.id
      and msm.source_type='MATERIAL_SUPPLIER_RETURN_ITEM'
      and msm.movement_type='SUPPLIER_RETURN'
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
    order by msm.physical_at desc,msm.id desc
  loop
    perform erp.reverse_material_movement(r.id,p_reason);
    perform erp.refresh_material_purchase_item_match_state(r.purchase_item_id);
    if r.roll_id is not null then
      select coalesce(sum(qty_signed),0) into v_roll_qty
      from erp.material_stock_movements where roll_id=r.roll_id;
      update erp.material_rolls
      set cached_qty=v_roll_qty,
          status=case when v_roll_qty<=0 then 'EXHAUSTED'
                      when v_roll_qty<original_qty then 'HALF_USED' else 'AVAILABLE' end,
          updated_at=now()
      where id=r.roll_id;
    end if;
  end loop;

  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  for v_purchase in
    select distinct i.purchase_id
    from erp.material_supplier_return_items ri
    join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where ri.return_id=h.id order by i.purchase_id
  loop
    select erp.material_purchase_final_ap_total(v_purchase),
           coalesce((select sum(amount) from erp.supplier_payments where purchase_id=v_purchase and status='POSTED'),0)
    into v_payable,v_paid;
    update erp.material_purchase_headers
    set payment_status=case when v_paid=round(v_payable,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end
    where id=v_purchase;
  end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('material_supplier_returns',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_opening_financial_correction(p_correction_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare c erp.opening_financial_corrections%rowtype;i erp.opening_balance_items%rowtype;b erp.opening_subledger_balances%rowtype;v_journal uuid;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal koreksi saldo awal wajib diisi'; end if;
  select * into c from erp.opening_financial_corrections where id=p_correction_id for update;
  if c.id is null then raise exception 'Koreksi saldo awal tidak ditemukan'; end if;
  if c.status='REVERSED' then return; end if;
  if exists(select 1 from erp.opening_financial_corrections x where x.opening_item_id=c.opening_item_id and x.status='POSTED' and x.id<>c.id and x.correction_seq>c.correction_seq) then
    raise exception 'Ada koreksi saldo awal yang lebih baru. Reverse koreksi terbaru terlebih dahulu.';
  end if;
  select * into i from erp.opening_balance_items where id=c.opening_item_id for update;
  if i.balance_type in ('CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE','CUSTOMER_RECEIVABLE') then
    select * into b from erp.opening_subledger_balances where opening_item_id=i.id for update;
    if b.settled_amount>c.previous_amount_snapshot then
      raise exception 'Reversal koreksi akan menurunkan saldo awal ke %, tetapi sudah disettle %. Reverse settlement terkait terlebih dahulu.',c.previous_amount_snapshot,b.settled_amount;
    end if;
  end if;
  select id into v_journal from erp.journal_entries where source_type='OPENING_FINANCIAL_CORRECTION' and source_id=c.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if v_journal is null then raise exception 'Jurnal koreksi saldo awal tidak ditemukan'; end if;
  perform erp.reverse_journal(v_journal,p_reason);
  if b.id is not null then
    update erp.opening_subledger_balances set original_amount=c.previous_amount_snapshot,
      status=case when settled_amount=c.previous_amount_snapshot then 'SETTLED' when settled_amount>0 then 'PARTIAL' else 'OPEN' end,
      updated_at=now() where id=b.id;
  end if;
  update erp.opening_financial_corrections set status='REVERSED',reversed_at=clock_timestamp(),reversal_reason=p_reason where id=c.id;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('opening_balance_items',i.id,'REVERSE',jsonb_build_object('correction_id',c.id,'restored_amount',c.previous_amount_snapshot,'correction_type','OPENING_FINANCIAL_CORRECTION'),erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.reverse_opening_subledger_settlement(p_settlement_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
DECLARE s erp.opening_subledger_settlements%ROWTYPE;b erp.opening_subledger_balances%ROWTYPE;v_journal uuid;
BEGIN PERFORM erp.require_owner_admin();SELECT * INTO s FROM erp.opening_subledger_settlements WHERE id=p_settlement_id FOR UPDATE;IF s.id IS NULL OR s.status<>'POSTED' THEN RAISE EXCEPTION 'Only POSTED opening settlement can be reversed';END IF;SELECT * INTO b FROM erp.opening_subledger_balances WHERE id=s.balance_id FOR UPDATE;SELECT id INTO v_journal FROM erp.journal_entries WHERE source_type='OPENING_SUBLEDGER_SETTLEMENT' AND source_id=s.id AND status='POSTED' ORDER BY posting_at DESC LIMIT 1;IF v_journal IS NULL THEN RAISE EXCEPTION 'Opening settlement journal not found';END IF;PERFORM erp.reverse_journal(v_journal,COALESCE(NULLIF(trim(p_reason),''),'Opening settlement reversal'));UPDATE erp.opening_subledger_settlements SET status='REVERSED',updated_at=now() WHERE id=s.id;UPDATE erp.opening_subledger_balances SET settled_amount=GREATEST(settled_amount-s.amount,0),status=CASE WHEN GREATEST(settled_amount-s.amount,0)=0 THEN 'OPEN' WHEN GREATEST(settled_amount-s.amount,0)=original_amount THEN 'SETTLED' ELSE 'PARTIAL' END,updated_at=now() WHERE id=b.id;END;$function$;

CREATE OR REPLACE FUNCTION erp.reverse_supplier_payment(p_payment_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  p erp.supplier_payments%rowtype;
  h erp.material_purchase_headers%rowtype;
  v_journal uuid;
  v_paid numeric(20,2);
  v_total numeric(20,2);
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal pembayaran supplier wajib diisi'; end if;
  select * into p from erp.supplier_payments where id=p_payment_id for update;
  if p.id is null then raise exception 'Pembayaran supplier tidak ditemukan'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status<>'POSTED' then raise exception 'Hanya pembayaran supplier yang sudah POSTED yang dapat direverse'; end if;
  select * into h from erp.material_purchase_headers where id=p.purchase_id for update;
  if h.id is null then raise exception 'Pembelian sumber pembayaran tidak ditemukan'; end if;

  select id into v_journal from erp.journal_entries
  where source_type='SUPPLIER_PAYMENT' and source_id=p.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_journal is null then raise exception 'Jurnal pembayaran supplier tidak ditemukan; reversal dibatalkan agar kas/hutang tidak rusak'; end if;

  perform erp.reverse_journal(v_journal,p_reason);
  update erp.supplier_payments set status='REVERSED' where id=p.id;

  select erp.material_purchase_payable_total(h.id)::numeric(20,2) into v_total;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid from erp.supplier_payments where purchase_id=h.id and status='POSTED';
  update erp.material_purchase_headers set payment_status=case when v_paid=round(v_total,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end where id=h.id;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('supplier_payments',p.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

CREATE OR REPLACE FUNCTION erp.run_v267_financial_truth_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
AS $function$
  select 'V267_GRNI_MAPPING_INVALID','CRITICAL',count(*)::bigint,
         'GRNI_MATERIAL must map to an active CREDIT liability account'
  from erp.accounting_account_mappings m
  join erp.chart_accounts a on a.id=m.account_id
  where m.mapping_key='GRNI_MATERIAL'
    and not(a.account_type='LIABILITY' and a.normal_balance='CREDIT' and a.is_active and a.is_postable)

  union all
  select 'V267_MISSING_GRNI_MAPPING','CRITICAL',case when exists(
    select 1 from erp.accounting_account_mappings where mapping_key='GRNI_MATERIAL'
  ) then 0 else 1 end::bigint,'GRNI mapping is required'

  union all
  select 'V267_ESTIMATED_RECEIPT_MISSING_GRNI_RECLASS','CRITICAL',count(*)::bigint,
         'Posted estimated receipts require an AP-to-GRNI reclassification journal'
  from erp.material_purchase_headers h
  where h.status='POSTED' and erp.material_purchase_grni_total(h.id)>0.005
    and not exists(
      select 1 from erp.journal_entries j
      where j.source_type='MATERIAL_PURCHASE_GRNI_RECLASS' and j.source_id=h.id
        and j.status in('POSTED','REVERSED')
    )

  union all
  select 'V267_POSTED_INVOICE_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
         'Every non-zero posted supplier invoice requires an AP/GRNI journal'
  from erp.material_supplier_invoices h
  where h.status='POSTED'
    and exists(select 1 from erp.material_supplier_invoice_lines l where l.invoice_id=h.id and(l.net_amount<>0 or l.grni_clear_amount_snapshot<>0))
    and not exists(
      select 1 from erp.journal_entries j
      where j.source_type='MATERIAL_SUPPLIER_INVOICE' and j.source_id=h.id and j.status='POSTED'
    )

  union all
  select 'V267_INVOICE_MATCH_OVER_RECEIPT','CRITICAL',count(*)::bigint,
         'Posted supplier-invoice quantity exceeds receipt quantity net of GRNI-backed returns'
  from erp.material_purchase_items i
  where erp.material_purchase_posted_invoice_qty(i.id)>erp.material_purchase_invoice_capacity(i.id)+0.000001

  union all
  select 'V267_PAYMENT_EXCEEDS_FINAL_AP','CRITICAL',count(*)::bigint,
         'Supplier payment must never consume GRNI or exceed final AP'
  from erp.material_purchase_headers h
  where coalesce((select sum(p.amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0)
        >round(erp.material_purchase_final_ap_total(h.id),2)

  union all
  select 'V267_LEGACY_CORRECTION_ON_GRNI','CRITICAL',count(*)::bigint,
         'Legacy price corrections may only touch DIRECT_FINAL receipt items'
  from erp.material_purchase_cost_correction_items ci
  join erp.material_purchase_cost_corrections c on c.id=ci.correction_id
  join erp.material_purchase_items i on i.id=ci.purchase_item_id
  where c.status='POSTED' and i.invoice_match_state<>'DIRECT_FINAL'

  union all
  select 'V267_POSTED_RETURN_MISSING_LIABILITY_SNAPSHOT','CRITICAL',count(*)::bigint,
         'Posted supplier returns require AP/GRNI quantity and amount snapshots'
  from erp.material_supplier_return_items ri
  join erp.material_supplier_returns rh on rh.id=ri.return_id
  where rh.status='POSTED' and(
    ri.ap_relief_qty_snapshot is null or ri.grni_relief_qty_snapshot is null
    or ri.ap_relief_amount_snapshot is null or ri.grni_relief_amount_snapshot is null
  )

  union all
  select 'V267_GRNI_GL_SUBLEDGER_MISMATCH','CRITICAL',case when abs(
    coalesce((select sum(a.credit_total-a.debit_total)
      from erp.account_daily_balances a
      where a.account_id=erp.account_id('GRNI_MATERIAL')),0)
    -coalesce((select sum(round(erp.material_purchase_grni_total(h.id),2))
      from erp.material_purchase_headers h where h.status='POSTED'),0)
  )<>0 then 1 else 0 end::bigint,
  'GRNI general ledger must equal estimated unmatched receipt liability'

  union all
  select 'V267_AP_GL_SUBLEDGER_MISMATCH','CRITICAL',case when abs(
    coalesce((select sum(a.credit_total-a.debit_total)
      from erp.account_daily_balances a
      where a.account_id=erp.account_id('AP_SUPPLIER')),0)
    -coalesce((select sum(greatest(
      round(erp.material_purchase_final_ap_total(h.id),2)
      -coalesce((select sum(p.amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0),0
    )) from erp.material_purchase_headers h where h.status='POSTED'),0)
    -coalesce((select sum(b.original_amount-b.settled_amount)
      from erp.opening_subledger_balances b
      join erp.opening_balance_items i on i.id=b.opening_item_id
      join erp.opening_balance_headers oh on oh.id=i.opening_id and oh.status='POSTED'
      where b.party_type='SUPPLIER' and b.direction='PAYABLE'),0)
  )<>0 then 1 else 0 end::bigint,
  'Supplier AP general ledger must equal final-invoice subledger net of payment/returns'

  union all
  select 'V267_BROWSER_ROLE_DIRECT_INVOICE_WRITE','CRITICAL',count(*)::bigint,
         'Supplier invoice aggregate must be writable only through v2 RPCs'
  from information_schema.role_table_grants g
  where g.table_schema='erp' and g.table_name in('material_supplier_invoices','material_supplier_invoice_lines')
    and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE')
  union all
  select 'V2620M_SUPPLIER_PAYMENT_EXACT_STATUS','CRITICAL',count(*)::bigint,
    'Supplier payment status and capacity must equal the rounded final liability of each purchase'
  from erp.material_purchase_headers h
  cross join lateral(select round(erp.material_purchase_final_ap_total(h.id),2) payable,
    coalesce((select sum(p.amount) from erp.supplier_payments p
      where p.purchase_id=h.id and p.status='POSTED'),0) paid) x
  where h.status='POSTED' and(
    x.paid<0 or x.paid>x.payable
    or x.paid::text in('NaN','Infinity','-Infinity')
    or x.payable::text in('NaN','Infinity','-Infinity')
    or(h.payment_status='PAID' and x.paid<>x.payable)
    or(h.payment_status='PARTIAL' and not(x.paid>0 and x.paid<x.payable))
    or(h.payment_status='UNPAID' and x.paid<>0))

  union all
  select 'V2620M_OPENING_SUBLEDGER_STATE','CRITICAL',count(*)::bigint,
    'Every posted financial opening requires one source-matched balance, exact settlements, and exact status'
  from erp.opening_balance_items i
  join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
  left join erp.opening_subledger_balances b on b.opening_item_id=i.id
  cross join lateral(select coalesce((select c.corrected_amount
      from erp.opening_financial_corrections c where c.opening_item_id=i.id and c.status='POSTED'
      order by c.correction_seq desc limit 1),i.amount) original,
    coalesce((select sum(s.amount) from erp.opening_subledger_settlements s
      where s.balance_id=b.id and s.status='POSTED'),0) paid) x
  where i.balance_type in('CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE',
    'CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE') and(
    b.id is null or (select count(*) from erp.opening_subledger_balances bx where bx.opening_item_id=i.id)<>1
    or b.original_amount is distinct from x.original
    or b.settled_amount is distinct from x.paid
    or b.original_amount::text in('NaN','Infinity','-Infinity')
    or b.settled_amount::text in('NaN','Infinity','-Infinity')
    or b.original_amount<0 or b.settled_amount<0 or b.settled_amount>b.original_amount
    or b.status is distinct from case when x.paid=x.original then 'SETTLED'
      when x.paid>0 then 'PARTIAL' else 'OPEN' end
    or b.party_type is distinct from split_part(i.balance_type,'_',1)
    or b.direction is distinct from split_part(i.balance_type,'_',2)
    or b.customer_id is distinct from i.customer_id
    or b.supplier_id is distinct from i.supplier_id
    or b.vendor_id is distinct from i.vendor_id
    or b.contractor_id is distinct from i.contractor_id)

  union all
  select 'V2620M_PAYMENT_SOURCE_JOURNAL_MISMATCH','CRITICAL',count(*)::bigint,
    'Each supplier or opening settlement must match its own original and inverse money, accounts, party, and lifecycle'
  from(
    select p.id,p.status,p.amount,p.cash_account_id,'SUPPLIER_PAYMENT'::text source_type,
      erp.account_id('AP_SUPPLIER') balance_account,false incoming,
      null::uuid customer_id,null::uuid vendor_id,null::uuid contractor_id
    from erp.supplier_payments p
    union all
    select s.id,s.status,s.amount,s.cash_account_id,'OPENING_SUBLEDGER_SETTLEMENT',
      erp.account_id(case when b.party_type='CUSTOMER' then 'AR_CUSTOMER'
        when b.party_type='SUPPLIER' then 'AP_SUPPLIER'
        when b.party_type='VENDOR' then 'AP_VENDOR'
        when b.direction='RECEIVABLE' then 'CONTRACTOR_RECEIVABLE' else 'CONTRACTOR_PAYABLE' end),
      b.direction='RECEIVABLE',b.customer_id,b.vendor_id,b.contractor_id
    from erp.opening_subledger_settlements s
    join erp.opening_subledger_balances b on b.id=s.balance_id
  ) x
  left join erp.cash_accounts ca on ca.id=x.cash_account_id
  where x.amount<=0 or x.amount::text in('NaN','Infinity','-Infinity') or ca.id is null
    or (select count(*) from erp.journal_entries j
      where j.source_type=x.source_type and j.source_id=x.id and j.status in('POSTED','REVERSED'))
      <>case when x.status='DRAFT' then 0 else 1 end
    or exists(
      select 1 from erp.journal_entries j
      where j.source_type=x.source_type and j.source_id=x.id and j.status in('POSTED','REVERSED') and(
        j.status is distinct from x.status
        or (select count(*) from erp.journal_lines l where l.journal_entry_id=j.id)<>2
        or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and(
          l.customer_id is distinct from x.customer_id or l.vendor_id is distinct from x.vendor_id
          or l.contractor_id is distinct from x.contractor_id
          or not((l.account_id=ca.coa_account_id and
                l.debit=case when x.incoming then x.amount else 0 end and
                l.credit=case when x.incoming then 0 else x.amount end)
            or (l.account_id=x.balance_account and
                l.debit=case when x.incoming then 0 else x.amount end and
                l.credit=case when x.incoming then x.amount else 0 end))))
        or (select count(*) from erp.journal_entries inv where inv.reversal_of_id=j.id)
          <>case when x.status='REVERSED' then 1 else 0 end
        or exists(select 1 from erp.journal_entries inv where inv.reversal_of_id=j.id and(
          inv.source_type<>'JOURNAL_REVERSAL' or inv.status<>'POSTED'
          or (select count(*) from erp.journal_lines l where l.journal_entry_id=inv.id)<>2
          or exists(select 1 from erp.journal_lines l where l.journal_entry_id=inv.id and(
            l.customer_id is distinct from x.customer_id or l.vendor_id is distinct from x.vendor_id
            or l.contractor_id is distinct from x.contractor_id
            or not((l.account_id=ca.coa_account_id and
                  l.credit=case when x.incoming then x.amount else 0 end and
                  l.debit=case when x.incoming then 0 else x.amount end)
              or (l.account_id=x.balance_account and
                  l.credit=case when x.incoming then 0 else x.amount end and
                  l.debit=case when x.incoming then x.amount else 0 end))))))
      ))

  union all
  select 'V2620M_ORPHAN_PAYMENT_JOURNAL','CRITICAL',count(*)::bigint,
    'A supplier payment or opening settlement journal must retain its business source'
  from erp.journal_entries j
  where j.status in('POSTED','REVERSED') and(
    (j.source_type='SUPPLIER_PAYMENT' and not exists(select 1 from erp.supplier_payments p where p.id=j.source_id))
    or(j.source_type='OPENING_SUBLEDGER_SETTLEMENT' and not exists(
      select 1 from erp.opening_subledger_settlements s where s.id=j.source_id)));

$function$;

CREATE OR REPLACE FUNCTION erp.run_v268_financial_report_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
 SET "TimeZone" TO 'UTC'
AS $function$
begin
  perform erp.require_owner_admin();
  return query
  select r.check_name,r.severity,r.issue_count,r.details
  from erp._v268_financial_report_checks_pre_scope() r
  where r.check_name not in(
    'V268_BROWSER_DIRECT_FINANCIAL_WRITE',
    'V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE',
    'V268_ACTIVE_SALE_MISSING_JOURNAL',
    'V268_POSTED_SALES_RETURN_MISSING_JOURNAL'
  )

  union all
  select 'V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE','CRITICAL',count(*)::bigint,
    'Browser roles must not directly mutate ledger or supplier-invoice aggregates'
  from information_schema.role_table_grants g
  where g.table_schema='erp'
    and g.table_name in('journal_entries','journal_lines','account_daily_balances',
      'material_supplier_invoices','material_supplier_invoice_lines')
    and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE')

  union all
  select 'V2620C_PO_HPP_TARGET_STATE_MISMATCH','CRITICAL',count(*)::bigint,
    'Saved PO HPP/FG/COGS/other state must equal independently recomputed current minor-unit targets'
  from erp.po_hpp_gl_state s
  cross join lateral erp.compute_po_hpp_gl_targets_v2620d(s.po_id) t
  where s.base_output_qty is distinct from coalesce(t.base_output_qty,0)
     or s.hpp_total_cost is distinct from round(coalesce(t.hpp_total_cost,0),2)
     or s.fg_value is distinct from round(coalesce(t.fg_value,0),2)
     or s.cogs_value is distinct from round(coalesce(t.cogs_value,0),2)
     or s.other_out_value is distinct from(
       round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2))

  union all
  select 'V2620C_HPP_COMPONENT_SUM_MISMATCH','CRITICAL',count(*)::bigint,
    'Every current production HPP version must equal the exact sum of its traceable production components'
  from erp.hpp_versions h
  join erp.fg_lots fl on fl.id=h.lot_id and fl.lot_origin='PRODUCTION'
  where h.is_current and abs(h.total_cost-coalesce((
    select sum(c.total_cost) from erp.hpp_version_components c where c.hpp_version_id=h.id
  ),0))>0.000001

  union all
  select 'V2620C_PO_HPP_BOOK_MISMATCH','CRITICAL',count(*)::bigint,
    'Per-PO FG, COGS, and HPP-disposition books must equal the saved minor-unit state after every post, recost, cancellation, return, and reversal'
  from erp.po_hpp_gl_state s
  cross join lateral erp.compute_po_hpp_gl_book_v2620e(s.po_id) b
  where abs(b.fg_value-s.fg_value)>0.005
     or abs(b.cogs_value-s.cogs_value)>0.005
     or abs(b.other_out_value-s.other_out_value)>0.005

  union all
  select 'V2620C_WIP_SOURCE_CONSERVATION_MISMATCH','CRITICAL',count(*)::bigint,
    'Per-PO WIP book must equal independently sourced manufacturing cost not yet transferred into current HPP, net of an active final residual close'
  from erp.po_hpp_gl_state s
  cross join lateral(
    select (
      coalesce((
        select sum(-m.qty_signed*m.unit_cost_snapshot)
        from erp.material_stock_movements m
        where (m.source_type='CUTTING_GROUP' and m.source_id in(
          select g.id from erp.cutting_groups g where g.po_id=s.po_id
        )) or (m.source_type='CUTTING_GROUP_RETURN' and m.source_id in(
          select g.id from erp.cutting_groups g where g.po_id=s.po_id
        ))
      ),0)
      +coalesce((
        select sum(i.qty*i.unit_cost_snapshot)
        from erp.contractor_material_issue_items i
        join erp.contractor_material_issues h on h.id=i.issue_id and h.status='POSTED'
        join erp.materials m on m.id=i.material_id and m.material_type<>'ACCESSORY'
        where h.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(l.amount_payable)
        from erp.work_completion_lines l
        join erp.work_completion_events h on h.id=l.completion_id and h.status='POSTED'
        where h.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(a.allocated_amount)
        from erp.attendance_hpp_pool_allocations a
        join erp.attendance_hpp_pools h on h.id=a.pool_id and h.status='ACTIVE'
        where a.po_id=s.po_id
      ),0)
      +coalesce((
        with delivery_cost as(
          select dl.id,dl.qty_sent_pcs,dl.estimated_rate_snapshot,
            coalesce(sum(case when rh.status='POSTED'
              and rl.actual_cost_status in('ESTIMATED','FINAL')
              then rl.qty_good_received+rl.qty_bs_laundry else 0 end),0) qty_costed,
            coalesce(sum(case when rh.status='POSTED'
              and rl.actual_cost_status in('ESTIMATED','FINAL')
              then coalesce(rl.actual_cost,0) else 0 end),0) actual_cost
          from erp.laundry_delivery_lines dl
          join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
          left join erp.laundry_receipt_lines rl on rl.delivery_line_id=dl.id
          left join erp.laundry_receipts rh on rh.id=rl.receipt_id
          where d.po_id=s.po_id
          group by dl.id,dl.qty_sent_pcs,dl.estimated_rate_snapshot
        )
        select sum(actual_cost+greatest(qty_sent_pcs-qty_costed,0)
          *coalesce(estimated_rate_snapshot,0)) from delivery_cost
      ),0)
      +coalesce((
        select sum(rl.actual_cost)
        from erp.laundry_failed_wash_attempts a
        join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
          and rl.actual_cost_status in('ESTIMATED','FINAL')
        join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
        join erp.laundry_deliveries d on d.id=a.delivery_id and d.status='REVERSED'
        where d.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(l.amount_payable)
        from erp.rework_component_lines l
        join erp.rework_orders r on r.id=l.rework_order_id
          and r.status<>'CANCELLED' and r.cost_posted=true
        join erp.bs_cases b on b.id=r.bs_case_id
        where b.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(a.adjustment_amount) from erp.cost_adjustments a
        where a.po_id=s.po_id and a.component_type='OTHER'
      ),0)
      +coalesce((
        select sum(a.total_hpp_cost)
        from erp.fg_accessory_cost_snapshots a
        join erp.fg_lots fl on fl.id=a.lot_id
          and fl.lot_origin='PRODUCTION'
        where fl.po_id=s.po_id
      ),0)
    )::numeric source_cost
  ) truth
  cross join lateral(
    select coalesce(sum(jl.debit-jl.credit),0)::numeric wip_book
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
      and je.status in('POSTED','REVERSED')
    where jl.po_id=s.po_id and jl.account_id=erp.account_id('WIP')
  ) w
  cross join lateral(
    select coalesce(sum(e.residual_amount),0)::numeric active_wip_close
    from erp.po_wip_close_events e
    join erp.journal_entries je on je.id=e.journal_entry_id
      and je.source_type='PO_WIP_RESIDUAL_CLOSE' and je.status='POSTED'
    where e.po_id=s.po_id
  ) c
  where abs(w.wip_book-(round(truth.source_cost,2)-s.hpp_total_cost-c.active_wip_close))>0.005

  union all
  select 'V2620C_SALE_REVENUE_REPORT_INPUT_MISMATCH','CRITICAL',count(*)::bigint,
    'Each sale lifecycle must contribute its exact line total to SALES_REVENUE while active and zero after cancellation/reversal'
  from(
    select h.id,h.status,
      case when h.status in('POSTED','PARTIAL_PAID','PAID')
        then coalesce((select sum(i.line_total) from erp.sales_items i where i.sale_id=h.id),0)
        else 0 end::numeric expected_revenue,
      coalesce(sum(jl.credit-jl.debit),0)::numeric booked_revenue
    from erp.sales_headers h
    left join erp.journal_entries origin on origin.source_type='SALE' and origin.source_id=h.id
      and origin.status in('POSTED','REVERSED')
    left join erp.journal_entries je on je.id=origin.id
      or (je.source_type='JOURNAL_REVERSAL' and je.reversal_of_id=origin.id
          and je.status in('POSTED','REVERSED'))
    left join erp.journal_lines jl on jl.journal_entry_id=je.id
      and jl.account_id=erp.account_id('SALES_REVENUE')
    group by h.id,h.status
  ) x
  where abs(x.booked_revenue-x.expected_revenue)>0.005

  union all
  select 'V2620C_SALES_RETURN_REPORT_INPUT_MISMATCH','CRITICAL',count(*)::bigint,
    'Each sales-return lifecycle must reduce SALES_REVENUE by its exact refund while active and contribute zero after reversal'
  from(
    select h.id,h.status,
      case when h.status='POSTED'
        then -coalesce((select sum(i.refund_amount) from erp.sales_return_items i where i.return_id=h.id),0)
        else 0 end::numeric expected_revenue,
      coalesce(sum(jl.credit-jl.debit),0)::numeric booked_revenue
    from erp.sales_returns h
    left join erp.journal_entries origin on origin.source_type='SALES_RETURN' and origin.source_id=h.id
      and origin.status in('POSTED','REVERSED')
    left join erp.journal_entries je on je.id=origin.id
      or (je.source_type='JOURNAL_REVERSAL' and je.reversal_of_id=origin.id
          and je.status in('POSTED','REVERSED'))
    left join erp.journal_lines jl on jl.journal_entry_id=je.id
      and jl.account_id=erp.account_id('SALES_REVENUE')
    group by h.id,h.status
  ) x
  where abs(x.booked_revenue-x.expected_revenue)>0.005

  union all
  select 'V2620C_DRAFT_SALE_VALUE_LEAK','CRITICAL',count(*)::bigint,
    'An active Draft reservation may reduce sellable quantity but may not classify current HPP as COGS/other expense'
  from(
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.sales_headers h on h.id=i.sale_id and h.status='DRAFT'
    join erp.fg_lots fl on fl.id=a.lot_id and fl.po_id is not null
  ) d
  cross join lateral erp.compute_po_hpp_gl_targets_v2620d(d.po_id) t
  where abs(coalesce(t.other_out_value,0))>0.005

  union all
  select 'V2620C_VENDOR_PAYMENT_EXACT_STATUS_MISMATCH','CRITICAL',count(*)::bigint,
    'Vendor invoice PAID/PARTIAL status must match the exact two-decimal payment subledger'
  from erp.vendor_invoices h
  cross join lateral(
    select coalesce(sum(p.amount),0)::numeric(20,2) paid
    from erp.vendor_payments p where p.vendor_invoice_id=h.id and p.status='POSTED'
  ) x
  where (h.status='PAID' and x.paid<>h.total_amount)
     or (h.status='PARTIAL_PAID' and not(x.paid>0 and x.paid<h.total_amount))
     or (h.status='POSTED' and x.paid<>0)

  union all
  select 'V2620C_HPP_STATE_HAS_SUBCENT','CRITICAL',count(*)::bigint,
    'Cumulative PO HPP GL state must contain exactly the minor-unit amounts that were journaled'
  from erp.po_hpp_gl_state s
  where s.hpp_total_cost<>round(s.hpp_total_cost,2)
     or s.fg_value<>round(s.fg_value,2)
     or s.cogs_value<>round(s.cogs_value,2)
     or s.other_out_value<>round(s.other_out_value,2)

  union all
  select 'V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Every carried participant interval must be contiguous, bounded, acyclic, same-source, and descend from a prior immutable full return'
  from(
    select a.id issue_id
    from erp.laundry_redispatch_participant_allocations a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.source_delivery_batch_size_line_id
    join erp.laundry_delivery_lines sdl on sdl.id=sx.delivery_line_id
    join erp.laundry_deliveries sd on sd.id=sdl.delivery_id
    join erp.laundry_delivery_batch_size_lines dx
      on dx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines ddl on ddl.id=dx.delivery_line_id
    join erp.laundry_deliveries dd on dd.id=ddl.delivery_id
    where sx.distribution_batch_id<>dx.distribution_batch_id
       or sx.size_id<>dx.size_id or sdl.cutting_group_id<>ddl.cutting_group_id
       or sd.status<>'REVERSED'
       or (sd.physical_at,sd.created_at,sd.id)>=(dd.physical_at,dd.created_at,dd.id)
       or a.source_offset_pcs+a.qty_pcs>sx.qty_sent_pcs
       or a.successor_offset_pcs+a.qty_pcs>dx.qty_sent_pcs
       or not exists(
         select 1 from erp.laundry_failed_wash_attempts f
         join erp.laundry_failed_wash_batch_size_lines fx
           on fx.attempt_id=f.id and fx.delivery_batch_size_line_id=sx.id
          and fx.qty_attempted_pcs=sx.qty_sent_pcs
         join erp.laundry_receipts fr on fr.id=f.receipt_id
           and fr.status in('POSTED','REVERSED')
         join erp.wip_stage_events rv on rv.id=f.return_wip_event_id
           and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
           and rv.stage_from='LAUNDRY' and rv.stage_to='SEWING'
           and rv.qty_pcs=f.qty_attempted_pcs
         join erp.wip_stage_events src on src.id=rv.source_id
           and src.source_type='LAUNDRY_DELIVERY_LINE'
           and src.source_id=sx.delivery_line_id
         join erp.laundry_delivery_lines fdl on fdl.id=src.source_id
           and fdl.delivery_id=f.delivery_id
           and rv.po_id=sd.po_id
           and rv.cutting_group_id=fdl.cutting_group_id
         where f.delivery_id=sd.id and f.custody_outcome='RETURN_UNPROCESSED'
           and fr.physical_at<=dd.physical_at and rv.physical_at<=dd.physical_at
       )
    union all
    select min(a.id::text)::uuid
    from erp.laundry_redispatch_participant_allocations a
    group by a.source_delivery_batch_size_line_id
    having min(a.source_offset_pcs)<>0
       or max(a.source_offset_pcs+a.qty_pcs)<>sum(a.qty_pcs)
    union all
    select min(a.id::text)::uuid
    from erp.laundry_redispatch_participant_allocations a
    group by a.successor_delivery_batch_size_line_id
    having min(a.successor_offset_pcs)<>0
       or max(a.successor_offset_pcs+a.qty_pcs)<>sum(a.qty_pcs)
  ) bad_lineage

  union all
  select 'V268_ACTIVE_SALE_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
    'Every active Sale with a monetary or rounded non-PO HPP effect requires its SALE journal'
  from erp.sales_headers h
  where h.status in('POSTED','PARTIAL_PAID','PAID')
    and round(coalesce((select sum(i.line_total) from erp.sales_items i
          where i.sale_id=h.id),0),2)>0.005
    and not exists(select 1 from erp.journal_entries j
      where j.source_type='SALE' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V268_POSTED_SALES_RETURN_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
    'Every posted return with a monetary or rounded non-PO HPP effect requires its SALES_RETURN journal'
  from erp.sales_returns h
  where h.status='POSTED'
    and round(coalesce((select sum(i.refund_amount)
          from erp.sales_return_items i where i.return_id=h.id),0),2)>0.005
    and not exists(select 1 from erp.journal_entries j
      where j.source_type='SALES_RETURN' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH','CRITICAL',count(*)::bigint,
    'Each non-PO product book must equal cumulative per-lot minor-unit HPP targets across every active Sale, return, correction, and reversal'
  from(
    select distinct fl.product_id
    from erp.fg_lots fl
    where fl.po_id is null
      and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
  ) p
  cross join lateral erp.compute_non_po_product_hpp_targets_v2620f(p.product_id) t
  cross join lateral erp.compute_non_po_product_hpp_book_v2620f(p.product_id) b
  where abs(t.hpp_total_cost-b.hpp_total_cost)>0.005
     or abs(t.fg_value-b.fg_value)>0.005
     or abs(t.cogs_value-b.cogs_value)>0.005
     or abs(t.other_out_value-b.other_out_value)>0.005

  union all
  select 'V2620E_SALES_RETURN_VALUE_EXCEEDS_SALE','CRITICAL',count(*)::bigint,
    'Posted cumulative product refund may never exceed the exact original product sale value'
  from(
    select sr.sale_id,i.product_id,sum(i.refund_amount)::numeric refund,
      coalesce((select sum(si.line_total) from erp.sales_items si
        where si.sale_id=sr.sale_id and si.product_id=i.product_id),0)::numeric sold
    from erp.sales_returns sr join erp.sales_return_items i on i.return_id=sr.id
    where sr.status='POSTED'
    group by sr.sale_id,i.product_id
  ) refund where refund.refund>refund.sold

  union all
  select 'V2620E_OPENING_HPP_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Opening FG HPP must follow its opening source or latest active correction and must not pretend to have production components'
  from erp.fg_lots fl
  left join lateral(
    select count(*)::integer movement_count,min(m.id::text)::uuid movement_id,
      min(m.source_id::text)::uuid source_id,min(m.qty_signed)::integer qty_signed,
      min(m.unit_hpp_snapshot)::numeric unit_hpp
    from erp.fg_stock_movements m
    where m.lot_id=fl.id and m.movement_type='OPENING'
  ) om on true
  left join erp.opening_balance_items oi on oi.id=om.source_id
  left join erp.opening_balance_headers oh on oh.id=oi.opening_id
  left join lateral(
    select count(*)::integer current_count,min(h.id::text)::uuid current_id,
      min(h.qty_basis_pcs)::integer qty_basis,min(h.total_cost)::numeric total_cost
    from erp.hpp_versions h where h.lot_id=fl.id and h.is_current
  ) ch on true
  left join lateral(
    select h.total_cost,h.qty_basis_pcs
    from erp.hpp_versions h where h.lot_id=fl.id
    order by h.version_no,h.id limit 1
  ) first_hpp on true
  left join lateral(
    select c.corrected_hpp
    from erp.opening_hpp_corrections c
    join erp.hpp_versions h on h.id=c.hpp_version_id
    where c.lot_id=fl.id and c.status='POSTED'
    order by h.version_no desc,h.id desc limit 1
  ) correction on true
  where fl.lot_origin='OPENING' and(
    om.movement_count<>1 or ch.current_count<>1
    or oi.id is null or oi.balance_type<>'FINISHED_GOODS'
    or oh.status<>'POSTED' or oi.product_id is distinct from fl.product_id
    or om.qty_signed is distinct from fl.initial_qty_pcs
    or ch.qty_basis is distinct from fl.initial_qty_pcs
    or abs(first_hpp.total_cost-fl.initial_qty_pcs*om.unit_hpp)>0.000001
    or abs(om.unit_hpp-erp.resolve_opening_fg_unit_hpp(oi.id,oh.opening_date))>0.000001
    or abs(ch.total_cost-fl.initial_qty_pcs
      *coalesce(correction.corrected_hpp,om.unit_hpp))>0.000001
    or fl.cached_qty_pcs is distinct from coalesce((
      select sum(m.qty_signed)::integer from erp.fg_stock_movements m
      where m.lot_id=fl.id
    ),0)
    or exists(select 1 from erp.hpp_version_components c
      join erp.hpp_versions h on h.id=c.hpp_version_id where h.lot_id=fl.id)
  )

  union all
  select 'V2620E_OPENING_FG_GL_MISMATCH','CRITICAL',count(*)::bigint,
    'Each posted opening document FG journal must equal its immutable opening FG movement value'
  from erp.opening_balance_headers h
  cross join lateral(
    select coalesce(sum(round(m.qty_signed*m.unit_hpp_snapshot,2)),0)::numeric expected_fg
    from erp.opening_balance_items i
    join erp.fg_stock_movements m
      on m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id
     and m.movement_type='OPENING'
    where i.opening_id=h.id and i.balance_type='FINISHED_GOODS'
  ) expected
  cross join lateral(
    select coalesce(sum(l.debit-l.credit),0)::numeric actual_fg
    from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
    where j.source_type='OPENING_BALANCE' and j.source_id=h.id
      and j.status='POSTED' and l.account_id=erp.account_id('FG_INVENTORY')
  ) actual
  where h.status='POSTED' and abs(expected.expected_fg-actual.actual_fg)>0.005

  union all
  select 'V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Each customer payment must own exactly one exact cash/AR journal and, when reversed, exactly one exact inverse'
  from(
    select p.id
    from erp.sales_payments p
    join erp.sales_headers h on h.id=p.sale_id
    where
      (p.status='DRAFT' and exists(
        select 1 from erp.journal_entries o
        where o.source_type='SALES_PAYMENT' and o.source_id=p.id
      ))
      or
      (p.status in('POSTED','REVERSED') and(
        (select count(*) from erp.journal_entries o
         where o.source_type='SALES_PAYMENT' and o.source_id=p.id)<>1
        or not exists(
          select 1
          from erp.journal_entries o
          where o.source_type='SALES_PAYMENT' and o.source_id=p.id
            and o.status=case when p.status='POSTED' then 'POSTED' else 'REVERSED' end
            and o.economic_date=case when p.replaces_payment_id is null
          then p.payment_date::date else (select pr.reversal_economic_date
            from erp.sales_payment_reversal_facts pr
            where pr.payment_id=p.replaces_payment_id) end
            and (select count(*) from erp.journal_lines l where l.journal_entry_id=o.id)=2
            and (select coalesce(sum(l.debit),0) from erp.journal_lines l where l.journal_entry_id=o.id)=p.amount
            and (select coalesce(sum(l.credit),0) from erp.journal_lines l where l.journal_entry_id=o.id)=p.amount
            and (select count(*) from erp.journal_lines l
                 join erp.cash_accounts ca on ca.id=p.cash_account_id and ca.coa_account_id=l.account_id
                 where l.journal_entry_id=o.id and l.debit=p.amount and l.credit=0
                   and l.customer_id=h.customer_id and l.vendor_id is null
                   and l.contractor_id is null and l.po_id is null and l.product_id is null)=1
            and (select count(*) from erp.journal_lines l
                 where l.journal_entry_id=o.id and l.account_id=erp.account_id('AR_CUSTOMER')
                   and l.debit=0 and l.credit=p.amount and l.customer_id=h.customer_id
                   and l.vendor_id is null and l.contractor_id is null
                   and l.po_id is null and l.product_id is null)=1
            and (
              (p.status='POSTED' and not exists(
                select 1 from erp.journal_entries r
                where r.source_type='JOURNAL_REVERSAL'
                  and (r.source_id=o.id or r.reversal_of_id=o.id)
              ))
              or
              (p.status='REVERSED'
                and (select count(*) from erp.journal_entries r
                     where r.source_type='JOURNAL_REVERSAL'
                       and (r.source_id=o.id or r.reversal_of_id=o.id))=1
                and exists(
                  select 1 from erp.journal_entries r
                  where r.source_type='JOURNAL_REVERSAL' and r.source_id=o.id
                    and r.reversal_of_id=o.id and r.status='POSTED'
                    and (select count(*) from erp.journal_lines x where x.journal_entry_id=r.id)=2
                    and not exists(
                      select 1 from erp.journal_lines ol
                      where ol.journal_entry_id=o.id and not exists(
                        select 1 from erp.journal_lines rl
                        where rl.journal_entry_id=r.id
                          and rl.account_id=ol.account_id
                          and rl.debit=ol.credit and rl.credit=ol.debit
                          and rl.customer_id is not distinct from ol.customer_id
                          and rl.vendor_id is not distinct from ol.vendor_id
                          and rl.contractor_id is not distinct from ol.contractor_id
                          and rl.po_id is not distinct from ol.po_id
                          and rl.product_id is not distinct from ol.product_id
                      )
                    )
                    and not exists(
                      select 1 from erp.journal_lines rl
                      where rl.journal_entry_id=r.id and not exists(
                        select 1 from erp.journal_lines ol
                        where ol.journal_entry_id=o.id
                          and ol.account_id=rl.account_id
                          and ol.debit=rl.credit and ol.credit=rl.debit
                          and ol.customer_id is not distinct from rl.customer_id
                          and ol.vendor_id is not distinct from rl.vendor_id
                          and ol.contractor_id is not distinct from rl.contractor_id
                          and ol.po_id is not distinct from rl.po_id
                          and ol.product_id is not distinct from rl.product_id
                      )
                    )
                )
              )
            )
        )
      ))
    union all
    select o.id
    from erp.journal_entries o
    where o.source_type='SALES_PAYMENT'
      and not exists(select 1 from erp.sales_payments p where p.id=o.source_id)
  ) payment_lineage_faults

  union all
  select 'V2620K_PAYMENT_ALLOCATION_DATE_MISMATCH','CRITICAL',count(*)::bigint,
    'Allocation replacement must conserve cash and customer AR on each economic and GL date'
  from erp.sales_payment_posting_facts f
  left join erp.sales_payment_reversal_facts pr on pr.payment_id=f.replaces_payment_id
  where f.replaces_payment_id is not null and(
    pr.payment_id is null
    or f.journal_economic_date is distinct from pr.reversal_economic_date
    or f.journal_transaction_date is distinct from pr.reversal_transaction_date
    or f.journal_posting_at<pr.reversal_posting_at)

  union all
  select 'V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH','CRITICAL',count(*)::bigint,
    'Posted payment invoice/cash identity and reversal dates must match append-only facts; correction requires one linked replacement'
  from(
    select p.id
    from erp.sales_payments p
    left join erp.sales_headers h on h.id=p.sale_id
    left join erp.sales_payment_posting_facts f on f.payment_id=p.id
    left join erp.journal_entries o on o.id=f.original_journal_entry_id
    left join erp.sales_payment_reversal_facts rf on rf.payment_id=p.id
    left join erp.journal_entries r on r.id=rf.reversal_journal_entry_id
    left join erp.sales_payment_posting_facts pf on pf.payment_id=f.replaces_payment_id
    left join erp.sales_payment_reversal_facts prf on prf.payment_id=f.replaces_payment_id
    where
      (p.status='DRAFT' and(f.payment_id is not null or rf.payment_id is not null))
      or
      (p.status in('POSTED','REVERSED') and(
        f.payment_id is null or h.id is null
        or f.sale_id is distinct from p.sale_id
        or f.customer_id is distinct from h.customer_id
        or f.payment_number is distinct from p.payment_number
        or f.payment_date is distinct from p.payment_date
        or f.amount is distinct from p.amount
        or f.cash_account_id is distinct from p.cash_account_id
        or f.replaces_payment_id is distinct from p.replaces_payment_id
        or f.payment_snapshot is distinct from to_jsonb(p)-'status'
        or f.lineage_sha256 is distinct from encode(extensions.digest(convert_to(jsonb_build_array(
          f.payment_id,f.sale_id,f.customer_id,f.payment_number,f.payment_date,f.amount,
          f.cash_account_id,f.original_journal_entry_id,f.journal_economic_date,
          f.journal_transaction_date,f.journal_posting_at,f.replaces_payment_id,
          f.predecessor_reversal_journal_id,f.payment_snapshot
        )::text,'UTF8'),'sha256'),'hex')
        or o.id is null or o.source_type<>'SALES_PAYMENT' or o.source_id is distinct from p.id
        or o.status is distinct from case when p.status='POSTED' then 'POSTED' else 'REVERSED' end
        or o.economic_date is distinct from f.journal_economic_date
        or o.transaction_date is distinct from f.journal_transaction_date
        or o.posting_at is distinct from f.journal_posting_at
        or ((f.replaces_payment_id is null)<>(f.predecessor_reversal_journal_id is null))
        or (f.replaces_payment_id is not null and(
          pf.payment_id is null or prf.payment_id is null
          or f.predecessor_reversal_journal_id is distinct from prf.reversal_journal_entry_id
          or pf.sale_id=f.sale_id or pf.customer_id is distinct from f.customer_id
          or pf.amount is distinct from f.amount
          or pf.cash_account_id is distinct from f.cash_account_id
          or pf.payment_date is distinct from f.payment_date
        ))
        or (p.status='POSTED' and(
          rf.payment_id is not null or exists(
            select 1 from erp.journal_entries x where x.source_type='JOURNAL_REVERSAL'
              and(x.source_id=o.id or x.reversal_of_id=o.id)
          )
        ))
        or (p.status='REVERSED' and(
          rf.payment_id is null or r.id is null
          or rf.original_journal_entry_id is distinct from o.id
          or r.source_type<>'JOURNAL_REVERSAL' or r.source_id is distinct from o.id
          or r.reversal_of_id is distinct from o.id or r.status<>'POSTED'
          or r.economic_date is distinct from rf.reversal_economic_date
          or r.transaction_date is distinct from rf.reversal_transaction_date
          or r.posting_at is distinct from rf.reversal_posting_at
          or rf.reversal_economic_date<f.journal_economic_date
          or rf.reversal_posting_at<f.journal_posting_at
          or rf.lineage_sha256 is distinct from encode(extensions.digest(convert_to(jsonb_build_array(
            rf.payment_id,rf.original_journal_entry_id,rf.reversal_journal_entry_id,
            rf.reversal_economic_date,rf.reversal_transaction_date,rf.reversal_posting_at
          )::text,'UTF8'),'sha256'),'hex')
        ))
      ))
    union all
    select f.payment_id from erp.sales_payment_posting_facts f
    left join erp.sales_payments p on p.id=f.payment_id where p.id is null
    union all
    select r.payment_id from erp.sales_payment_reversal_facts r
    left join erp.sales_payments p on p.id=r.payment_id
    left join erp.sales_payment_posting_facts f on f.payment_id=r.payment_id
    where p.id is null or f.payment_id is null or p.status<>'REVERSED'
  ) payment_fact_faults

  union all
  select 'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH','CRITICAL',count(*)::bigint,
    'RETURN_UNPROCESSED inverse WIP time must equal its authoritative physical receipt time'
  from erp.laundry_failed_wash_attempts a
  left join erp.laundry_receipts rh on rh.id=a.receipt_id
  left join erp.wip_stage_events rv on rv.id=a.return_wip_event_id
  where a.custody_outcome='RETURN_UNPROCESSED' and(
    rh.id is null or rv.id is null
    or rv.source_type<>'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
    or rv.physical_at is distinct from rh.physical_at
  )

  union all
  select 'V2620H_CUSTOMER_AR_STATUS_MISMATCH','CRITICAL',count(*)::bigint,
    'Sale PAID/PARTIAL/POSTED status must equal the exact two-decimal payment subledger and overpayment is unsupported'
  from erp.sales_headers h
  cross join lateral(
    select round(erp.sale_net_total(h.id),2)::numeric(20,2) total,
      round(coalesce(sum(round(p.amount,2)),0),2)::numeric(20,2) paid
    from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'
  ) x
  where h.status in('POSTED','PARTIAL_PAID','PAID') and(
    x.paid>x.total
    or (h.status='PAID' and x.paid<>x.total)
    or (h.status='PARTIAL_PAID' and not(x.paid>0 and x.paid<x.total))
    or (h.status='POSTED' and x.paid<>0)
  )

  union all
  select 'V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH','CRITICAL',count(*)::bigint,
    'Each customer signed AR general-ledger balance must equal active net sales less posted payments'
  from(
    select coalesce(g.customer_id,s.customer_id) customer_id,
      coalesce(g.amount,0)::numeric gl_amount,coalesce(s.amount,0)::numeric subledger_amount
    from(
      select jl.customer_id,sum(jl.debit-jl.credit)::numeric amount
      from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
      where je.status in('POSTED','REVERSED') and jl.account_id=erp.account_id('AR_CUSTOMER')
        and jl.customer_id is not null
      group by jl.customer_id
    ) g
    full join(
      select x.customer_id,sum(x.amount)::numeric amount from(
        select h.customer_id,round(erp.sale_net_total(h.id),2)-coalesce((
          select sum(round(p.amount,2)) from erp.sales_payments p
          where p.sale_id=h.id and p.status='POSTED'),0) amount
        from erp.sales_headers h where h.status in('POSTED','PARTIAL_PAID','PAID')
        union all
        select ob.customer_id,ob.original_amount-ob.settled_amount
        from erp.opening_subledger_balances ob
        join erp.opening_balance_items oi on oi.id=ob.opening_item_id
        join erp.opening_balance_headers oh on oh.id=oi.opening_id and oh.status='POSTED'
        where ob.party_type='CUSTOMER' and ob.direction='RECEIVABLE'
      ) x group by x.customer_id
    ) s on s.customer_id=g.customer_id
  ) ar where round(ar.gl_amount,2) is distinct from round(ar.subledger_amount,2)

  union all
  select 'V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH','CRITICAL',count(*)::bigint,
    'Laundry source and inverse events must match authoritative delivery quantity, dimensions, direction, chronology and net physical custody'
  from(
    select dl.id
    from erp.laundry_delivery_lines dl
    join erp.laundry_deliveries d on d.id=dl.delivery_id
    join erp.production_orders po on po.id=d.po_id
    left join lateral(
      select count(*) total_sources,
        count(*) filter(where s.po_id=d.po_id
          and s.cutting_group_id is not distinct from dl.cutting_group_id
          and s.contractor_id is not distinct from po.contractor_id
          and s.stage_from='SEWING' and s.stage_to='LAUNDRY'
          and s.qty_pcs=dl.qty_sent_pcs and s.physical_at=d.physical_at) valid_sources,
        coalesce(sum(s.qty_pcs),0) source_qty
      from erp.wip_stage_events s
      where s.source_type='LAUNDRY_DELIVERY_LINE' and s.source_id=dl.id
    ) source on true
    left join lateral(
      select count(*) total_inverses,
        count(*) filter(where r.po_id=s.po_id
          and r.cutting_group_id is not distinct from s.cutting_group_id
          and r.contractor_id is not distinct from s.contractor_id
          and r.stage_from='LAUNDRY' and r.stage_to='SEWING'
          and r.qty_pcs=dl.qty_sent_pcs and r.qty_pcs=s.qty_pcs
          and r.physical_at>=s.physical_at) valid_inverses,
        coalesce(sum(r.qty_pcs),0) inverse_qty
      from erp.wip_stage_events s
      join erp.wip_stage_events r on r.source_id=s.id
        and r.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
      where s.source_type='LAUNDRY_DELIVERY_LINE' and s.source_id=dl.id
    ) inverse on true
    where d.status<>'DRAFT' and(
      source.total_sources<>1 or source.valid_sources<>1
      or inverse.total_inverses<>case when d.status='REVERSED' then 1 else 0 end
      or inverse.valid_inverses<>inverse.total_inverses
      or source.source_qty-inverse.inverse_qty<>
        case when d.status='REVERSED' then 0 else dl.qty_sent_pcs end
    )
    union all
    select s.id from erp.wip_stage_events s
    left join erp.laundry_delivery_lines dl on dl.id=s.source_id
    left join erp.laundry_deliveries d on d.id=dl.delivery_id
    where s.source_type='LAUNDRY_DELIVERY_LINE'
      and(dl.id is null or d.id is null or d.status='DRAFT')
    union all
    select r.id from erp.wip_stage_events r
    left join erp.wip_stage_events s on s.id=r.source_id
      and s.source_type='LAUNDRY_DELIVERY_LINE'
    where r.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL' and s.id is null
  ) bad_custody

  union all
  select 'V2620E_REDISPATCH_EVENT_MISMATCH','CRITICAL',count(*)::bigint,
    'Effective redispatch allocation/release events must be bounded, non-overlapping, chronological, and backed by exact custody facts'
  from(
    select a.id
    from erp.laundry_redispatch_participant_events a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.source_delivery_batch_size_line_id
    join erp.laundry_delivery_lines sl on sl.id=sx.delivery_line_id
    join erp.laundry_deliveries sd on sd.id=sl.delivery_id
    join erp.laundry_delivery_batch_size_lines dx
      on dx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines dl on dl.id=dx.delivery_line_id
    join erp.laundry_deliveries dd on dd.id=dl.delivery_id
    where a.event_type='ALLOCATE' and(
      sx.distribution_batch_id<>dx.distribution_batch_id or sx.size_id<>dx.size_id
      or sl.cutting_group_id<>dl.cutting_group_id or sd.status<>'REVERSED'
      or (sd.physical_at,sd.created_at,sd.id)>=(dd.physical_at,dd.created_at,dd.id)
      or a.source_offset_pcs+a.qty_pcs>sx.qty_sent_pcs
      or a.successor_offset_pcs+a.qty_pcs>dx.qty_sent_pcs
      or not exists(
        select 1 from erp.laundry_failed_wash_attempts f
        join erp.laundry_failed_wash_batch_size_lines fx
          on fx.attempt_id=f.id and fx.delivery_batch_size_line_id=sx.id
         and fx.qty_attempted_pcs=sx.qty_sent_pcs
        join erp.laundry_receipts fr on fr.id=f.receipt_id
           and fr.status in('POSTED','REVERSED')
         join erp.wip_stage_events rv on rv.id=f.return_wip_event_id
           and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
           and rv.stage_from='LAUNDRY' and rv.stage_to='SEWING'
           and rv.qty_pcs=f.qty_attempted_pcs
         join erp.wip_stage_events src on src.id=rv.source_id
           and src.source_type='LAUNDRY_DELIVERY_LINE'
           and src.source_id=sx.delivery_line_id
         join erp.laundry_delivery_lines fdl on fdl.id=src.source_id
           and fdl.delivery_id=f.delivery_id
           and rv.po_id=sd.po_id
           and rv.cutting_group_id=fdl.cutting_group_id
        where f.delivery_id=sd.id and f.custody_outcome='RETURN_UNPROCESSED'
          and fr.physical_at<=dd.physical_at and rv.physical_at<=dd.physical_at)
      or (not exists(select 1 from erp.laundry_redispatch_participant_events x
            where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
          and dd.status='REVERSED'
          and not exists(select 1 from erp.laundry_receipts r where r.delivery_id=dd.id))
    )
    union all
    select a.id
    from erp.laundry_redispatch_participant_events a
    where a.event_type='ALLOCATE'
      and not exists(select 1 from erp.laundry_redispatch_participant_events x
        where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
      and exists(
        select 1 from erp.laundry_redispatch_participant_events b
        where b.event_type='ALLOCATE' and b.id>a.id
          and not exists(select 1 from erp.laundry_redispatch_participant_events x
            where x.event_type='RELEASE' and x.releases_allocation_event_id=b.id)
          and ((b.source_delivery_batch_size_line_id=a.source_delivery_batch_size_line_id
              and int4range(b.source_offset_pcs,b.source_offset_pcs+b.qty_pcs,'[)')
                && int4range(a.source_offset_pcs,a.source_offset_pcs+a.qty_pcs,'[)'))
            or (b.successor_delivery_batch_size_line_id=a.successor_delivery_batch_size_line_id
              and int4range(b.successor_offset_pcs,b.successor_offset_pcs+b.qty_pcs,'[)')
                && int4range(a.successor_offset_pcs,a.successor_offset_pcs+a.qty_pcs,'[)')))
      )
    union all
    select x.id
    from erp.laundry_redispatch_participant_events x
    join erp.laundry_redispatch_participant_events a
      on a.id=x.releases_allocation_event_id and a.event_type='ALLOCATE'
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
    join erp.laundry_deliveries d on d.id=dl.delivery_id
    where x.event_type='RELEASE' and(
      x.released_delivery_id<>d.id or d.status<>'REVERSED'
      or exists(select 1 from erp.laundry_receipts r where r.delivery_id=d.id)
    )
  ) bad_events

  union all
  select 'V2620F_CONVERSION_VALUE_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Every posted conversion must be PO-sourced, value-preserving, rooted, and represented by exact OUT/IN facts with current descendant HPP'
  from erp.product_conversion_allocations a
  join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
  join erp.fg_lots s on s.id=a.source_lot_id
  left join erp.fg_lots d on d.id=a.destination_lot_id
  left join erp.v_current_hpp sh on sh.lot_id=s.id
  left join erp.v_current_hpp dh on dh.lot_id=d.id
  where s.po_id is null or d.id is null or d.po_id is distinct from s.po_id
     or d.lot_origin<>'CONVERSION' or d.source_lot_id is distinct from s.id
     or d.initial_qty_pcs is distinct from a.qty_pcs or a.qty_pcs<=0
     or sh.hpp_per_pcs is null or dh.hpp_per_pcs is null
     or abs(dh.hpp_per_pcs-(sh.hpp_per_pcs
       +a.conversion_cost_allocated/nullif(a.qty_pcs,0)))>0.000001
     or (select count(*) from erp.fg_stock_movements m
         where m.source_type='PRODUCT_CONVERSION' and m.source_id=c.id
           and m.lot_id=s.id and m.movement_type='REBRAND_OUT'
           and m.qty_signed=-a.qty_pcs)<>1
     or (select count(*) from erp.fg_stock_movements m
         where m.source_type='PRODUCT_CONVERSION' and m.source_id=c.id
           and m.lot_id=d.id and m.movement_type='REBRAND_IN'
           and m.qty_signed=a.qty_pcs)<>1

  union all
  select 'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH','CRITICAL',count(*)::bigint,
    'Every Sale lifecycle journal must conserve FG/COGS/disposition independently inside each PO or non-PO dimension'
  from erp.journal_entries e
  left join erp.journal_entries o on o.id=e.reversal_of_id
  cross join lateral(
    select coalesce(sum(l.debit-l.credit) filter(where l.account_id in(
      erp.account_id('COGS'),erp.account_id('FG_INVENTORY'),
      erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
    )),0) hpp_net
    from erp.journal_lines l where l.journal_entry_id=e.id
  ) b
  where e.status in('POSTED','REVERSED') and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  ) and(
    abs(b.hpp_net)>0.005
    or exists(
      select 1 from erp.journal_lines l
      where l.journal_entry_id=e.id
        and l.account_id in(
          erp.account_id('COGS'),erp.account_id('FG_INVENTORY'),
          erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
        )
      group by l.po_id
      having abs(sum(l.debit-l.credit))>0.005
    )
  );
end
$function$;
do $capture_boundary_v2620m$
declare v_table text; v_hash text; v_snapshot jsonb:='{}';
begin
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
    'suppliers','materials'
  ]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620m_rollback_capsule set boundary_snapshot=v_snapshot;
end
$capture_boundary_v2620m$;

do $installed_guard_v2620m$
declare r record;
begin
  if (select count(*) from erp.cp6_v2620m_rollback_capsule)<>15 then
    raise exception 'M_INCOMPLETE_CAPSULE';
  end if;
  for r in select * from(values
    ('erp._v268_financial_report_checks_pre_scope()','dc4ed2384dda4b34a30093cad8cb13fa80db26201371569a88dbaee790a24108','98fac1a865982d5c60fc5e6a5caae9033755ff915b7e53d22213c0d1d1765ca1',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_purchase_cost_correction(uuid)','d80d5d357acddd562412ada1a27fced5ac979c0ab1aa1dc0a9cbefa81aee0ad8','9542acde669945e633d5929cb5b441a2119b8f3bf9a69919ae46725d598e8ba9',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_material_supplier_invoice(uuid)','ec73a81f2bae980039edde861f01157337814a3bb9a0554f9d0275716c1f19d5','65ae76bce50952c2ced64ad7ec25c1039a1e3086048e5ea39eae71ec4c8b7d69',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_material_supplier_return(uuid)','562140bee0171cb892501ca4499e93e8b6d661772d1d03c95271283e6cea8714','f5f6603b258eeda0b34a10f06a301b94c488525dfddfe0863e5ded8f56244ad1',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_opening_financial_correction(uuid,numeric,text,date)','41ef3e9b7e9be5432cd09db2e4cba4d303c6c7205c2dcf92cb052293dc4062a7','95ad1f5db523bdc19d7b21d1f1b9e1baa49a499fb791f937fe43b0291d4bd7f1',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_opening_subledger_settlement(uuid)','95eb1e84cd0dabd02b3f11dc8745f72997b56fea47c04a9f56a9e18e9a9ebdf2','c56b387a8593b19cd3b92e6dc20ac95459d2aedeb2b616b6fb1e4d812e729393',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_supplier_payment(uuid)','3d77b3cc0339606aa7eb456b9b341af33f8251a7a0415229a2d7c08cfe54ef60','231d2e8132d966e3b539015e3e9fc463e758c2e0bcfe4ecdb89414fc5c0b97f8',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_purchase_cost_correction(uuid,text)','2cbfb722a7b644d47886e23555ef8dcffb2ea2060525c6251afa43e52689389b','dc17e41110f001f6f16d18d065745dc8e85bb9e58ef28e162522976da45c4a6f',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.reverse_material_supplier_invoice(uuid,text)','c269a2cb171184f49be2720e195bd24292f76d0127cb752ffc158a894768d1cb','76ee31ad50c747b5a9f5730a5a3e81ba79c1685f57f716ac211197f11aa7080e',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_material_supplier_return(uuid,text)','570bb23aeebdf5f309e34a84071a247ff201855b6c283f8a6264b7389816eaa6','ac2504b1f04d5eaf8bf63b13ce945adf17fda0104ac6e4f6c44ac831c255706b',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_opening_financial_correction(uuid,text)','5d794a5d6d4d63b2bc5e4b6407523488d1b87ba5c47ab557056fd566442ec50c','1ce99785ee8dc682b1b0f2aa9171f2110614baf4c9a99ecf4880b547496947fe',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.reverse_opening_subledger_settlement(uuid,text)','d5c1e4b368a13de3738d458c89584ec181149f6f070cc697111c61e56bfba07e','c01292aebb98ea09d0fb440215f9c4cdbd9ece3b98caa641b9b308faec542e1a',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.reverse_supplier_payment(uuid,text)','b6518df0cc3941554eca06016e483e8e020112778db67dad69202d4c032d40be','9733b0e39d82732fb4b2ec7be17c66bcff2a088a81cccd25892eb440d4923102',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','368c7f97b895ce7d08aa6b5fa5a77b50957191465a44e26ef9268b6424c93aea','efde954275e89f01793f405e2b000c6c599bae0be731869802f288994dd154fa',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','2bffd2d8f33ad2d918d1fb2f767676dc403ac777ad9a8ff69d4f32bf74067eff','48d60613970b015d1afb30a2f8a7cec0e5d56d1f692c6a1acfa0ffd48684fda1',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'M_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH';
    end if;
  end loop;
  -- Reject incompatible existing posted history; never rewrite it during DDL.
  if exists(select 1 from erp.run_v268_financial_report_checks() where issue_count<>0
    and (check_name like 'V2620M_%' or check_name in('V268_AR_GL_SUBLEDGER_MISMATCH',
      'V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH','V267_GRNI_GL_SUBLEDGER_MISMATCH','V267_AP_GL_SUBLEDGER_MISMATCH',
      'V267_PAYMENT_EXCEEDS_FINAL_AP'))) then
    raise exception 'M_PREEXISTING_SUBLEDGER_REVIEW_REQUIRED';
  end if;
  update erp.cp6_v2620m_rollback_capsule c set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'),'sha256'),'hex');
end
$installed_guard_v2620m$;
insert into erp.schema_migrations(version,description) values(
  'v2.6.20m','CP6 competition: exact supplier/opening settlement capacity, source journals, and opening AR/AP reconciliation'
);
commit;
