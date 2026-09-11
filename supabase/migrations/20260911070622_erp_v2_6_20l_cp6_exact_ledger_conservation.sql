-- ERP CP6 v2.6.20l. Forward-only closure of COMP-K-01/02/03.
begin;
set local lock_timeout='10s';
set local statement_timeout='240s';
set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,erp.cp6_v2620j_rollback_capsule in share row exclusive mode;
lock table erp.audit_logs,erp.journal_lines,erp.account_daily_balances,
  erp.sales_headers,erp.sales_items,erp.sale_stock_allocations,
  erp.sales_returns,erp.sales_return_items,erp.sales_payments,
  erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,
  erp.hpp_versions,erp.product_conversions,erp.product_conversion_allocations,
  erp.laundry_deliveries,erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events
in share row exclusive mode;

lock table erp.sales_payment_posting_facts,erp.sales_payment_reversal_facts
in share row exclusive mode;

lock table erp.cp6_v2620k_rollback_capsule,erp.accounting_period_control,erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts,erp.laundry_claims,erp.laundry_vendors in share row exclusive mode;
do $guard_v2620l$
declare r record; c record; actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20k')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20l')
     or to_regclass('erp.cp6_v2620l_rollback_capsule') is not null then
    raise exception 'L_REQUIRES_EXACT_K_WITHOUT_L_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
      where name='erp_v2_6_20k_cp6_payment_date_conservation')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260911023222' and name='erp_v2_6_20k_cp6_payment_date_conservation'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
           in('567ede242847e7f0a428e673f896d61886f4cbb23e8bb55becf06c34a358b880','ef8b8d4f5e3d1e723cadd0c3c5257fbeadb7c79c238295982172861ee462f614'))
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260911023222')
     or (select count(*) from erp.cp6_v2620k_rollback_capsule)<>4
     or exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'L_PREDECESSOR_PLATFORM_OR_CONTEXT_MISMATCH';
  end if;
  for r in select * from(values
    ('erp.post_sales_payment(uuid)','5634d6fa8fa613e455b9de57b2bd186ac6424815ea2a0aa33866c7c235918e5a','362e4266718275af5af6efcded3c85cd7a7a7f1faba7241979114fe6e57ffd6c',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.reverse_sales_payment(uuid,text)','00d2c2e0dea82508840c06a9aa7ddade503df9a552a29b664beeb32cd081e5b6','e5f48784389148a40b2f71fbe9a3e133ff9a7bc95ec969da74e27163b0c5b069',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','3ab1c4e42616eadac12dd0d37811703fdd0436690a57ebe962c651af56e3588f','2bffd2d8f33ad2d918d1fb2f767676dc403ac777ad9a8ff69d4f32bf74067eff',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.guard_sales_payment_posted_identity_v2620j()','3849af0c4d17fa6fba90d87ff923dd82bf942f922d792ab5c2901f069b42a5d0','bc2f8539173958e7c8c8dd8287e193131598ee71286146e7d76d258d700e1617',array['postgres=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
    select * into c from erp.cp6_v2620k_rollback_capsule where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex') is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'L_PREDECESSOR_K_CAPSULE_SOURCE_PIN_MISMATCH';
    end if;
  end loop;
  for r in select * from(values
    ('erp.post_journal(text,uuid,date,text,jsonb)','c9bfb4804246a2c7b2352ef0a67db5e035939e29f292f2dff34e0b2b590d4e76',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','4eb19d881f47dbbf57bc69f4f49ffdbb5c3071b4b126d2398d26dd2e980b2bf7',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.resolve_laundry_claim(uuid,text,text)','51ebcf8c01d7d47279112808424d7c18e2ea637d9fa7a41472a21de15b17b54b',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.sha256
       or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'L_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH';
    end if;
  end loop;
end
$guard_v2620l$;
create table erp.cp6_v2620l_rollback_capsule(
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
alter table erp.cp6_v2620l_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620l_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.cp6_v2620l_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a order by a::text) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp.post_journal(text,uuid,date,text,jsonb)'::regprocedure,
  'erp._v268_financial_report_checks_pre_scope()'::regprocedure,
  'erp.resolve_laundry_claim(uuid,text,text)'::regprocedure
);


CREATE OR REPLACE FUNCTION erp.post_journal(p_source_type text, p_source_id uuid, p_transaction_date date, p_description text, p_lines jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_entry_id uuid;
  v_input_debit numeric;
  v_input_credit numeric;
  v_cent_lines jsonb := '[]'::jsonb;
  v_number text;
  v_debit numeric(20,2);
  v_credit numeric(20,2);
  r jsonb;
  v_account_id uuid;
  v_gl_date date;
  v_ap_vendor_account uuid;
  v_vendor_id uuid;
  v_vendor_balance numeric(24,6);
  v_vendor_delta numeric(24,6);
begin
  perform erp.require_internal();
  if jsonb_typeof(p_lines) is distinct from 'array' then
    raise exception 'JOURNAL_LINES_ARRAY_REQUIRED';
  end if;
  if jsonb_array_length(p_lines)<2 then
    raise exception 'Journal requires at least two lines';
  end if;
  -- Canonicalize each monetary line exactly as it will be stored. All balance
  -- and vendor-admission checks below consume these same cent amounts.
  for r in select * from jsonb_array_elements(p_lines) loop
    if jsonb_typeof(r) is distinct from 'object' then
      raise exception 'JOURNAL_LINE_OBJECT_REQUIRED';
    end if;
    v_input_debit:=coalesce((r->>'debit')::numeric,0);
    v_input_credit:=coalesce((r->>'credit')::numeric,0);
    if v_input_debit::text in('NaN','Infinity','-Infinity')
       or v_input_credit::text in('NaN','Infinity','-Infinity')
       or v_input_debit<0 or v_input_credit<0 then
      raise exception 'JOURNAL_FINITE_NONNEGATIVE_MONEY_REQUIRED';
    end if;
    v_cent_lines:=v_cent_lines||jsonb_build_array(r||jsonb_build_object(
      'debit',round(v_input_debit,2),'credit',round(v_input_credit,2)));
  end loop;
  p_lines:=v_cent_lines;
  select coalesce(sum(coalesce((x->>'debit')::numeric,0)),0),coalesce(sum(coalesce((x->>'credit')::numeric,0)),0)
  into v_debit,v_credit from jsonb_array_elements(p_lines) x;
  if v_debit<>v_credit or v_debit<=0 then raise exception 'Journal is not balanced. Debit %, Credit %',v_debit,v_credit; end if;
  if exists(select 1 from erp.journal_entries where source_type=p_source_type and source_id=p_source_id and status='POSTED') then
    raise exception 'A posted journal already exists for this source';
  end if;

  -- Serialize journal posting with accounting close/reopen. A close that starts
  -- first blocks this journal until the new closed-through date is visible; a
  -- journal that starts first keeps the close waiting until this posting commits.
  perform 1 from erp.accounting_period_control where singleton_id=1 for share;

  -- Vendor AP is allowed to reach zero, but not become negative. Negative AP
  -- means the company has a receivable/advance from the vendor and requires a
  -- separate explicit workflow instead of silently crossing the account sign.
  v_ap_vendor_account:=erp.account_id('AP_VENDOR');
  for v_vendor_id in
    select distinct nullif(x->>'vendor_id','')::uuid
    from jsonb_array_elements(p_lines) x
    where nullif(x->>'vendor_id','') is not null
      and coalesce((x->>'debit')::numeric,0)>coalesce((x->>'credit')::numeric,0)
      and (
        (x ? 'mapping_key' and x->>'mapping_key'='AP_VENDOR')
        or (x ? 'account_id' and nullif(x->>'account_id','')::uuid=v_ap_vendor_account)
      )
    order by 1
  loop
    perform pg_advisory_xact_lock(hashtextextended('VENDOR_AP|'||v_vendor_id::text,0));

    select coalesce(sum(jl.credit-jl.debit),0)
      into v_vendor_balance
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
    where je.status in ('POSTED','REVERSED')
      and jl.account_id=v_ap_vendor_account
      and jl.vendor_id=v_vendor_id;

    select coalesce(sum(
      coalesce((x->>'credit')::numeric,0)-coalesce((x->>'debit')::numeric,0)
    ),0)
      into v_vendor_delta
    from jsonb_array_elements(p_lines) x
    where nullif(x->>'vendor_id','')::uuid=v_vendor_id
      and (
        (x ? 'mapping_key' and x->>'mapping_key'='AP_VENDOR')
        or (x ? 'account_id' and nullif(x->>'account_id','')::uuid=v_ap_vendor_account)
      );

    if v_vendor_balance::text in('NaN','Infinity','-Infinity') or v_vendor_balance+v_vendor_delta < 0 then
      raise exception 'Transaksi ini membuat hutang vendor menjadi negatif. Hutang saat ini %, perubahan %, hasil %. Reverse/koreksi pembayaran, claim, atau invoice terkait dulu; kelebihan bayar/claim vendor harus masuk workflow piutang vendor terpisah.',
        round(v_vendor_balance,2),round(v_vendor_delta,2),round(v_vendor_balance+v_vendor_delta,2);
    end if;
  end loop;

  v_gl_date:=erp.resolve_accounting_transaction_date(p_transaction_date);
  v_number:='JRN-'||to_char(clock_timestamp(),'YYYYMMDDHH24MISSMS')||'-'||substr(gen_random_uuid()::text,1,8);
  insert into erp.journal_entries(journal_number,economic_date,transaction_date,posting_at,source_type,source_id,description,status,created_by)
  values(v_number,p_transaction_date,v_gl_date,now(),p_source_type,p_source_id,p_description,'POSTED',erp.current_app_user_id()) returning id into v_entry_id;

  for r in select * from jsonb_array_elements(p_lines) loop
    if r?'account_id' then v_account_id:=(r->>'account_id')::uuid; else v_account_id:=erp.account_id(r->>'mapping_key'); end if;
    insert into erp.journal_lines(journal_entry_id,account_id,description,debit,credit,customer_id,vendor_id,contractor_id,po_id,product_id)
    values(v_entry_id,v_account_id,r->>'description',coalesce((r->>'debit')::numeric,0),coalesce((r->>'credit')::numeric,0),nullif(r->>'customer_id','')::uuid,nullif(r->>'vendor_id','')::uuid,nullif(r->>'contractor_id','')::uuid,nullif(r->>'po_id','')::uuid,nullif(r->>'product_id','')::uuid);
  end loop;

  insert into erp.account_daily_balances(balance_date,account_id,debit_total,credit_total)
  select v_gl_date,jl.account_id,sum(jl.debit),sum(jl.credit) from erp.journal_lines jl where jl.journal_entry_id=v_entry_id group by jl.account_id
  on conflict(balance_date,account_id) do update set debit_total=erp.account_daily_balances.debit_total+excluded.debit_total,credit_total=erp.account_daily_balances.credit_total+excluded.credit_total,updated_at=now();

  if v_gl_date<>p_transaction_date then
    insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
    values('journal_entries',v_entry_id,'POST',jsonb_build_object('economic_date',p_transaction_date,'transaction_date',v_gl_date,'period_shifted',true,'source_type',p_source_type,'source_id',p_source_id),erp.current_app_user_id(),'Late/backdated posting moved to open accounting period');
  end if;
  return v_entry_id;
end;
$function$;

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
          where h.status in('POSTED','PARTIAL_PAID','PAID')),0)::numeric subledger_amount
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
  where r.check_name in('V267_GRNI_GL_SUBLEDGER_MISMATCH','V267_AP_GL_SUBLEDGER_MISMATCH')

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

CREATE OR REPLACE FUNCTION erp.resolve_laundry_claim(p_claim_id uuid, p_resolution text, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare c erp.laundry_claims%rowtype;v_ap_account uuid;v_ap_balance numeric(24,6):=0;v_effective_date date;
begin
  perform erp.require_owner_admin();
  if p_resolution not in ('SETTLED','WRITTEN_OFF') then raise exception 'Claim resolution must be SETTLED or WRITTEN_OFF'; end if;
  if nullif(trim(p_reason),'') is null then raise exception 'Claim resolution reason is required'; end if;
  select * into c from erp.laundry_claims where id=p_claim_id for update;
  if c.id is null then raise exception 'Laundry claim not found'; end if;
  if c.status in ('SETTLED','WRITTEN_OFF') then return; end if;
  if c.status='REJECTED' then raise exception 'Rejected laundry claim cannot be settled/write-off without reopening'; end if;
  if p_resolution='WRITTEN_OFF' and c.compensation_amount>0 then raise exception 'WRITTEN_OFF claim must have zero compensation; set compensation to zero or use SETTLED'; end if;
  v_effective_date:=coalesce(c.resolution_date,current_date);
  if v_effective_date>current_date then raise exception 'Tanggal penyelesaian claim laundry berada di masa depan'; end if;
  if p_resolution='SETTLED' and c.compensation_amount>0 then
    v_ap_account:=erp.account_id('AP_VENDOR');
    select coalesce(sum(jl.credit-jl.debit),0) into v_ap_balance from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
    where je.status in ('POSTED','REVERSED') and jl.vendor_id=c.vendor_id and jl.account_id=v_ap_account;
    if v_ap_balance<c.compensation_amount then raise exception 'Claim compensation % exceeds current laundry vendor payable %. Cash/receivable settlement needs a separate receivable workflow',c.compensation_amount,round(v_ap_balance,2); end if;
    perform erp.post_journal('LAUNDRY_CLAIM_SETTLEMENT',c.id,v_effective_date,'Laundry claim compensation offset',jsonb_build_array(
      jsonb_build_object('mapping_key','AP_VENDOR','debit',round(c.compensation_amount,2),'credit',0,'vendor_id',c.vendor_id),
      jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',0,'credit',round(c.compensation_amount,2),'vendor_id',c.vendor_id)));
  end if;
  update erp.laundry_claims set status=p_resolution,resolution_date=v_effective_date,resolved_at=now(),notes=concat_ws(E'\n',notes,'Resolution: '||p_reason) where id=c.id;
end$function$;
do $capture_boundary_v2620l$
declare v_table text; v_hash text; v_snapshot jsonb:='{}';
begin
  foreach v_table in array array[
    'app_users','idempotency_requests','products','audit_logs',
    'journal_entries','journal_lines','account_daily_balances',
    'sales_headers','sales_items','sale_stock_allocations',
    'sales_returns','sales_return_items','sales_payments',
    'fg_lots','fg_stock_movements','fg_inventory_balances','hpp_versions',
    'product_conversions','product_conversion_allocations',
    'laundry_deliveries','laundry_delivery_lines','laundry_receipts',
    'laundry_failed_wash_attempts','wip_stage_events',
    'cp6_v2620g_rollback_capsule','cp6_v2620h_rollback_capsule','cp6_v2620i_rollback_capsule',
    'sales_payment_posting_facts','sales_payment_reversal_facts','cp6_v2620j_rollback_capsule',
    'cp6_v2620k_rollback_capsule','accounting_period_control','accounting_account_mappings','cash_accounts','chart_accounts','laundry_claims','laundry_vendors'
  ]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620l_rollback_capsule set boundary_snapshot=v_snapshot;
end
$capture_boundary_v2620l$;

do $installed_guard_v2620l$
declare r record;
begin
  if (select count(*) from erp.cp6_v2620l_rollback_capsule)<>3 then
    raise exception 'L_INCOMPLETE_CAPSULE';
  end if;
  for r in select * from(values
    ('erp.post_journal(text,uuid,date,text,jsonb)','c9bfb4804246a2c7b2352ef0a67db5e035939e29f292f2dff34e0b2b590d4e76','1ae479c9c32b9489e659d83d99a9829ef88876643f3e8f8aa276fee6d96a9cdf',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','4eb19d881f47dbbf57bc69f4f49ffdbb5c3071b4b126d2398d26dd2e980b2bf7','dc4ed2384dda4b34a30093cad8cb13fa80db26201371569a88dbaee790a24108',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.resolve_laundry_claim(uuid,text,text)','51ebcf8c01d7d47279112808424d7c18e2ea637d9fa7a41472a21de15b17b54b','20eba16640912f04220437c21df018a6799dc48b06d8147abfbd2454e2d60425',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text) from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'L_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH';
    end if;
  end loop;
  -- Reject incompatible existing posted history; never rewrite it during DDL.
  if exists(select 1 from erp.run_v268_financial_report_checks() where issue_count<>0
    and check_name in('V268_DAILY_BALANCE_LEDGER_MISMATCH','V268_UNBALANCED_POSTED_JOURNAL',
      'V268_BALANCE_SHEET_EQUATION','V2620L_NONFINITE_LEDGER_MONEY','V2620L_NEGATIVE_VENDOR_AP')) then
    raise exception 'L_PREEXISTING_LEDGER_REVIEW_REQUIRED';
  end if;
  update erp.cp6_v2620l_rollback_capsule c set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'),'sha256'),'hex');
end
$installed_guard_v2620l$;
insert into erp.schema_migrations(version,description) values(
  'v2.6.20l','CP6 competition: exact stored ledger money, per-cent reconciliation and nonnegative vendor claim settlement'
);
commit;
