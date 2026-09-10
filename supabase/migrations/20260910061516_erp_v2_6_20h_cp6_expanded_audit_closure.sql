-- ERP Garment v2.6.20h / independent CP6 R02-R03 data closure.
-- VENI. VIDI. VICI. ERP. -- I CONQUERED ERP.
-- Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.
--
-- R01 is an operational DDL rollback boundary, not a business-data rewrite.
-- Exact F/G/H rollback files stay immutable and are admitted only through the
-- database-level maintenance controller that closes new connections and drains
-- old invocations before executing their bytes.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';

lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.audit_logs,erp.journal_lines,erp.account_daily_balances,
  erp.sales_headers,erp.sales_items,erp.sale_stock_allocations,
  erp.sales_returns,erp.sales_return_items,erp.sales_payments,
  erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,
  erp.hpp_versions,erp.product_conversions,erp.product_conversion_allocations,
  erp.laundry_deliveries,erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events
in share row exclusive mode;

do $guard_v2620h$
declare r record; v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20g') then
    raise exception 'ERP v2.6.20h requires exact v2.6.20g first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20h')
     or to_regclass('erp.cp6_v2620h_rollback_capsule') is not null then
    raise exception 'ERP v2.6.20h already recorded or prior repair residue exists; never replay';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations m
      where m.name='erp_v2_6_20g_cp6_independent_audit_closure'
        and encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex')
          in('645623b047e6c762cf078507450d260d712427ccd0b2c314113de856c4aff726',
             'e9bc2d59dbd1da0facfaa01d2b955630710258e6b761e3ef114b95fc8c783724'))<>1 then
    raise exception 'ERP v2.6.20h requires one exact G platform-ledger row';
  end if;
  if exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'ERP v2.6.20h refuses an active CP6 execution context';
  end if;
  for r in select * from(values
    ('erp.post_sales_payment(uuid)','83214f0812d151b5d03cb8669f48fb5c72b4480d0c609df84d244559f3e4d988'),
    ('erp.reverse_sales_payment(uuid,text)','33219c5509a43470f87d3b0fe4af472bec3f87b4808bbdba7d2eed69ea88354d'),
    ('erp.post_sales_return(uuid)','217788d5f72bcfb87a387b82360c0f4a1ac191913beb0cf1a2ec5e31926a09a0'),
    ('erp.reverse_sales_return(uuid,text)','68e4ed3a1940e3853bcdadaf2d607ed60a78a350460efcaf4fa052a90c902bce'),
    ('erp._v268_financial_report_checks_pre_scope()','436a77b32c953e92fc8e43f953335392c4137b61bf632780d26b9b942d94e8b0'),
    ('erp.run_v268_financial_report_checks()','fd48bcf94868dbcf7087af2c34b12c82333ae861d44c6bf79cbb41b1350a8962')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: H predecessor % (%)',r.identity,v_actual;
    end if;
  end loop;
end
$guard_v2620h$;

create table erp.cp6_v2620h_rollback_capsule(
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
alter table erp.cp6_v2620h_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620h_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.cp6_v2620h_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a order by a::text) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp.post_sales_payment(uuid)'::regprocedure,
  'erp.reverse_sales_payment(uuid,text)'::regprocedure,
  'erp.post_sales_return(uuid)'::regprocedure,
  'erp.reverse_sales_return(uuid,text)'::regprocedure,
  'erp._v268_financial_report_checks_pre_scope()'::regprocedure,
  'erp.run_v268_financial_report_checks()'::regprocedure
);

do $capture_boundary_v2620h$
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
    'laundry_failed_wash_attempts','wip_stage_events'
  ]
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620h_rollback_capsule set boundary_snapshot=v_snapshot;
end
$capture_boundary_v2620h$;

-- R03: currency decisions are exact after one normalization to book precision.
-- There is no customer-credit ledger in this version, so overpayment is an
-- atomic refusal instead of an invisible negative receivable.
create or replace function erp.post_sales_payment(p_payment_id uuid)
returns void language plpgsql security definer set search_path='erp','public'
as $function$
declare
  p erp.sales_payments%rowtype;
  h erp.sales_headers%rowtype;
  v_cash uuid;
  v_paid numeric(20,2);
  v_total numeric(20,2);
  v_amount numeric(20,2);
begin
  perform erp.require_internal();
  select * into p from erp.sales_payments where id=p_payment_id for update;
  if p.id is null or p.status<>'DRAFT' then raise exception 'Sales payment must be DRAFT'; end if;
  v_amount:=round(p.amount,2)::numeric(20,2);
  if p.amount is distinct from v_amount or v_amount<=0 then
    raise exception 'Customer payment must be a positive exact two-decimal amount';
  end if;
  select * into h from erp.sales_headers where id=p.sale_id for update;
  if h.status not in('POSTED','PARTIAL_PAID') then
    raise exception 'Sale must be posted and still unpaid before payment';
  end if;
  select round(erp.sale_net_total(h.id),2)::numeric(20,2) into v_total;
  select round(coalesce(sum(round(sp.amount,2)),0),2)::numeric(20,2) into v_paid
  from erp.sales_payments sp where sp.sale_id=h.id and sp.status='POSTED';
  if v_paid>=v_total then
    raise exception 'Sale has no remaining receivable after returns/credits. Net sale %, already paid %',v_total,v_paid;
  end if;
  if v_paid+v_amount>v_total then
    raise exception 'Customer payment exceeds exact remaining receivable. Net sale %, already paid %, requested %',v_total,v_paid,v_amount;
  end if;
  select coa_account_id into v_cash from erp.cash_accounts where id=p.cash_account_id and is_active=true;
  if v_cash is null then raise exception 'Active cash/bank account is required'; end if;
  perform erp.post_journal('SALES_PAYMENT',p_payment_id,p.payment_date::date,'Customer payment',jsonb_build_array(
    jsonb_build_object('account_id',v_cash,'debit',v_amount,'credit',0,'customer_id',h.customer_id),
    jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',v_amount,'customer_id',h.customer_id)));
  update erp.sales_payments set status='POSTED' where id=p_payment_id;
  v_paid:=v_paid+v_amount;
  update erp.sales_headers
  set status=case when v_paid=v_total then 'PAID' else 'PARTIAL_PAID' end
  where id=h.id;
end
$function$;

create or replace function erp.reverse_sales_payment(p_payment_id uuid,p_reason text)
returns void language plpgsql security definer set search_path='erp','public'
as $function$
declare
  p erp.sales_payments%rowtype;
  h erp.sales_headers%rowtype;
  v_journal uuid;
  v_paid numeric(20,2);
  v_total numeric(20,2);
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal pembayaran customer wajib diisi'; end if;
  select * into p from erp.sales_payments where id=p_payment_id for update;
  if p.id is null then raise exception 'Pembayaran customer tidak ditemukan'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status<>'POSTED' then raise exception 'Hanya pembayaran customer yang sudah POSTED yang dapat direverse'; end if;
  select * into h from erp.sales_headers where id=p.sale_id for update;
  if h.id is null then raise exception 'Penjualan sumber pembayaran tidak ditemukan'; end if;

  select id into v_journal from erp.journal_entries
  where source_type='SALES_PAYMENT' and source_id=p.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_journal is null then
    raise exception 'Jurnal pembayaran customer tidak ditemukan; reversal dibatalkan agar kas/piutang tidak rusak';
  end if;
  perform erp.reverse_journal(v_journal,p_reason);
  update erp.sales_payments set status='REVERSED' where id=p.id;

  select round(erp.sale_net_total(h.id),2)::numeric(20,2) into v_total;
  select round(coalesce(sum(round(amount,2)),0),2)::numeric(20,2) into v_paid
  from erp.sales_payments where sale_id=h.id and status='POSTED';
  if v_paid>v_total then
    raise exception 'Payment reversal exposed an unsupported customer overpayment. Net sale %, still paid %',v_total,v_paid;
  end if;
  update erp.sales_headers
  set status=case when v_paid=v_total and v_total>=0 then 'PAID'
    when v_paid>0 and v_paid<v_total then 'PARTIAL_PAID' else 'POSTED' end
  where id=h.id;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('sales_payments',p.id,'REVERSE',erp.current_app_user_id(),p_reason);
end
$function$;

-- Keep F's full return/HPP implementation byte-for-byte except for the three
-- currency decision anchors. Its existing transaction makes a rejected return
-- roll back both physical and financial writes atomically.
do $patch_return_currency_v2620h$
declare v_identity text; v_definition text; v_anchor text; v_replacement text;
begin
  select pg_get_functiondef('erp.post_sales_return(uuid)'::regprocedure) into v_definition;
  v_anchor:='  if v_paid>v_net_total+0.01 then';
  v_replacement:='  if v_paid>v_net_total then';
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: H return overpayment anchor';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);
  v_anchor:=$anchor$  set status=case when v_paid>=v_net_total-0.01 then 'PAID' when v_paid>0 then 'PARTIAL_PAID' else 'POSTED' end$anchor$;
  v_replacement:=$replacement$  set status=case when v_paid=v_net_total then 'PAID' when v_paid>0 and v_paid<v_net_total then 'PARTIAL_PAID' else 'POSTED' end$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: H return exact-status anchor';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);

  select pg_get_functiondef('erp.reverse_sales_return(uuid,text)'::regprocedure) into v_definition;
  v_anchor:=$anchor$  set status=case when v_paid>=v_total-0.01 then 'PAID' when v_paid>0 then 'PARTIAL_PAID' else 'POSTED' end$anchor$;
  v_replacement:=$replacement$  set status=case when v_paid=v_total then 'PAID' when v_paid>0 and v_paid<v_total then 'PARTIAL_PAID' else 'POSTED' end$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: H return-reversal exact-status anchor';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_return_currency_v2620h$;

-- The legacy global AR reconciliation clamped customer credit to zero and
-- tolerated a whole cent. Preserve every other pre-scope check, but make AR
-- signed and exact at two-decimal book precision.
do $patch_pre_scope_ar_v2620h$
declare v_definition text; v_anchor text; v_replacement text;
begin
  select pg_get_functiondef('erp._v268_financial_report_checks_pre_scope()'::regprocedure)
    into v_definition;
  v_anchor:=$anchor$      coalesce((select sum(greatest(
        erp.sale_net_total(h.id)-coalesce((select sum(p.amount) from erp.sales_payments p
                                           where p.sale_id=h.id and p.status='POSTED'),0),0
      )) from erp.sales_headers h
          where h.status in('POSTED','PARTIAL_PAID','PAID')),0)::numeric subledger_amount$anchor$;
  v_replacement:=$replacement$      coalesce((select sum(
        round(erp.sale_net_total(h.id),2)-coalesce((select sum(round(p.amount,2))
          from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'),0)
      ) from erp.sales_headers h
          where h.status in('POSTED','PARTIAL_PAID','PAID')),0)::numeric subledger_amount$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: H signed AR anchor';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);
  v_anchor:='case when abs(gl_amount-subledger_amount)>0.01 then 1 else 0 end::bigint';
  v_replacement:='case when round(gl_amount,2) is distinct from round(subledger_amount,2) then 1 else 0 end::bigint';
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: H exact AR check anchor';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_pre_scope_ar_v2620h$;

-- R02 binds the inverse WIP event to the authoritative physical return clock.
-- R03 adds exact header/subledger and per-customer GL oracles so privileged
-- corruption cannot wash across customers while the owner report stays READY.
do $patch_report_v2620h$
declare v_definition text; v_anchor text; v_replacement text;
begin
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure)
    into v_definition;
  v_anchor:=$anchor$  union all
  select 'V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH','CRITICAL',count(*)::bigint,$anchor$;
  v_replacement:=$replacement$  union all
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
      select h.customer_id,sum(round(erp.sale_net_total(h.id),2)-coalesce((
        select sum(round(p.amount,2)) from erp.sales_payments p
        where p.sale_id=h.id and p.status='POSTED'),0))::numeric amount
      from erp.sales_headers h where h.status in('POSTED','PARTIAL_PAID','PAID')
      group by h.customer_id
    ) s on s.customer_id=g.customer_id
  ) ar where round(ar.gl_amount,2) is distinct from round(ar.subledger_amount,2)

  union all
  select 'V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH','CRITICAL',count(*)::bigint,$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: H report insertion anchor';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_report_v2620h$;

do $installed_guard_v2620h$
declare r record; v_count bigint;
begin
  if (select count(*) from erp.cp6_v2620h_rollback_capsule)<>6 then
    raise exception 'ERP v2.6.20h incomplete rollback capsule';
  end if;
  for r in select c.*,p.proowner,p.proacl
    from erp.cp6_v2620h_rollback_capsule c join pg_proc p on p.oid=to_regprocedure(c.object_regidentity)
  loop
    if pg_get_userbyid(r.proowner) is distinct from r.owner_snapshot
       or (case when r.proacl is null then null else array(select a::text from unnest(r.proacl) a order by a::text) end)
          is distinct from r.acl_snapshot then
      raise exception 'ERP v2.6.20h changed owner/ACL for %',r.object_regidentity;
    end if;
  end loop;
  select coalesce(sum(issue_count),0) into v_count
  from erp.run_v268_financial_report_checks()
  where check_name in(
    'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH',
    'V2620H_CUSTOMER_AR_STATUS_MISMATCH',
    'V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH',
    'V268_AR_GL_SUBLEDGER_MISMATCH'
  );
  if v_count<>0 then
    raise exception 'ERP v2.6.20h targeted reconciliation failed: % issue(s)',v_count;
  end if;
  update erp.cp6_v2620h_rollback_capsule c set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'),'sha256'),'hex');
end
$installed_guard_v2620h$;

insert into erp.schema_migrations(version,description) values(
  'v2.6.20h',
  'CP6 expanded audit R02-R03: authoritative failed-wash return clock and exact signed customer AR lifecycle'
);
commit;
