-- OW08b 2.19: owner authorizes both next-invoice application and cash/bank refund.
-- These are source links, not a second general ledger. All money uses Native journals.
create schema cp7_vendor_receivable authorization postgres;
revoke all on schema cp7_vendor_receivable from public,anon,authenticated,service_role;

create table cp7_vendor_receivable.sources_v1(
 correction_id uuid primary key,vendor_id uuid not null,account_id uuid not null,
 amount numeric(18,2)not null check(amount>0),economic_date date not null,
 actor uuid not null,recorded_at timestamptz not null default statement_timestamp()
);
create index sources_v1_vendor on cp7_vendor_receivable.sources_v1(vendor_id,account_id);
create table cp7_vendor_receivable.refunds_v1(
 id uuid primary key,correction_id uuid not null references cp7_vendor_receivable.sources_v1,
 amount numeric(18,2)not null check(amount>0),cash_account_id uuid not null,
 economic_date date not null,reason text not null check(length(btrim(reason))between 4 and 500),
 journal_id uuid not null unique,actor uuid not null,
 recorded_at timestamptz not null default statement_timestamp()
);
create index refunds_v1_source on cp7_vendor_receivable.refunds_v1(correction_id);
create table cp7_vendor_receivable.reversals_v1(
 refund_id uuid primary key references cp7_vendor_receivable.refunds_v1,
 request_id uuid not null unique,journal_id uuid not null unique,
 reason text not null check(length(btrim(reason))between 4 and 500),actor uuid not null,
 recorded_at timestamptz not null default statement_timestamp()
);
alter table cp7_vendor_receivable.sources_v1 enable row level security;
alter table cp7_vendor_receivable.refunds_v1 enable row level security;
alter table cp7_vendor_receivable.reversals_v1 enable row level security;
create policy deny_sources on cp7_vendor_receivable.sources_v1 for all using(false)with check(false);
create policy deny_refunds on cp7_vendor_receivable.refunds_v1 for all using(false)with check(false);
create policy deny_reversals on cp7_vendor_receivable.reversals_v1 for all using(false)with check(false);

create function cp7_vendor_receivable.immutable_v1()returns trigger
language plpgsql volatile security invoker set search_path=''as $$
begin raise exception 'CP7_VENDOR_RECEIVABLE_APPEND_ONLY';end $$;
create trigger source_immutable before update or delete on cp7_vendor_receivable.sources_v1
 for each row execute function cp7_vendor_receivable.immutable_v1();
create trigger refund_immutable before update or delete on cp7_vendor_receivable.refunds_v1
 for each row execute function cp7_vendor_receivable.immutable_v1();
create trigger reversal_immutable before update or delete on cp7_vendor_receivable.reversals_v1
 for each row execute function cp7_vendor_receivable.immutable_v1();

create function cp7_vendor_receivable.eligible_v1(p_account uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from erp.chart_accounts a where a.id=p_account
  and a.is_active and a.is_postable and a.account_type='ASSET'and a.normal_balance='DEBIT'
  and not exists(select 1 from erp.cash_accounts c where c.coa_account_id=a.id)
  and not exists(select 1 from erp.accounting_account_mappings m where m.account_id=a.id)
  and not exists(select 1 from erp.initial_import_prepayments x where x.coa_account_id=a.id)
  and not exists(select 1 from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
   where l.account_id=a.id and not(
    exists(select 1 from cp7_vendor_receivable.sources_v1 s where s.correction_id=j.source_id and s.account_id=a.id)
    or exists(select 1 from cp7_vendor_receivable.refunds_v1 r join cp7_vendor_receivable.sources_v1 s on s.correction_id=r.correction_id
      where r.id=j.source_id and s.account_id=a.id)
    or exists(select 1 from erp.bd_claim_credit_applications_v1 x join cp7_vendor_receivable.sources_v1 s on s.correction_id=x.correction_invoice_id
      where coalesce(x.vendor_payment_id,x.opening_settlement_id)=j.source_id and s.account_id=a.id)
    or j.reversal_of_id is not null)))
$$;

create function cp7_vendor_receivable.accounts_v1()returns jsonb
language sql stable security definer set search_path=''as $$
 select coalesce(jsonb_agg(jsonb_build_object('id',a.id,'code',a.account_code,'name',a.account_name)order by a.account_code),'[]'::jsonb)
 from erp.chart_accounts a where cp7_vendor_receivable.eligible_v1(a.id)
$$;

create function cp7_vendor_receivable.register_v1(p_correction uuid,p_account uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare i erp.bd_laundry_invoices_v1%rowtype;
begin
 select *into strict i from erp.bd_laundry_invoices_v1 where id=p_correction for update;
 if i.status<>'DRAFT'or i.header_total>=0 or i.corrects_invoice_id is null then raise exception 'CP7_VENDOR_RECEIVABLE_CORRECTION_REQUIRED';end if;
 perform 1 from erp.chart_accounts where id=p_account for share;
 if not cp7_vendor_receivable.eligible_v1(p_account)then
  raise exception 'CP7_VENDOR_RECEIVABLE_ACCOUNT_REQUIRED: pilih akun aset debit aktif khusus piutang vendor, bukan akun kas, pemetaan resmi, atau uang muka saldo awal';end if;
 insert into cp7_vendor_receivable.sources_v1(correction_id,vendor_id,account_id,amount,economic_date,actor)
 values(i.id,i.vendor_id,p_account,-i.header_total,i.invoice_date,erp.current_app_user_id());
 return jsonb_build_object('account_id',p_account,'debit',-i.header_total,'credit',0,'vendor_id',i.vendor_id);
end $$;

create function cp7_vendor_receivable.refunded_v1(p_kind text,p_source uuid)returns numeric
language sql stable security definer set search_path=''as $$
 select coalesce(sum(r.amount),0)::numeric(18,2)from cp7_vendor_receivable.refunds_v1 r
 where p_kind='INVOICE_CORRECTION'and r.correction_id=p_source
 and not exists(select 1 from cp7_vendor_receivable.reversals_v1 x where x.refund_id=r.id)
$$;

create function cp7_vendor_receivable.application_lines_v1(p_kind text,p_source uuid,p_vendor uuid,p_amount numeric)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare s cp7_vendor_receivable.sources_v1%rowtype;
begin
 if p_kind='INVOICE_CORRECTION'then select *into s from cp7_vendor_receivable.sources_v1 where correction_id=p_source;end if;
 if s.correction_id is not null and s.vendor_id<>p_vendor then raise exception 'CP7_VENDOR_RECEIVABLE_SOURCE_CHANGED';end if;
 return jsonb_build_array(jsonb_build_object('mapping_key','AP_VENDOR','debit',p_amount,'credit',0,'vendor_id',p_vendor),
  case when s.correction_id is null then jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',p_amount,'vendor_id',p_vendor)
   else jsonb_build_object('account_id',s.account_id,'debit',0,'credit',p_amount,'vendor_id',p_vendor)end);
end $$;

create function cp7_vendor_receivable.opening_lines_v1(p_settlement uuid,p_original jsonb)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare a erp.bd_claim_credit_applications_v1%rowtype;
begin
 select *into a from erp.bd_claim_credit_applications_v1 where opening_settlement_id=p_settlement;
 if a.source_kind='INVOICE_CORRECTION'and exists(select 1 from cp7_vendor_receivable.sources_v1 where correction_id=a.correction_invoice_id)then
  return cp7_vendor_receivable.application_lines_v1(a.source_kind,a.correction_invoice_id,a.vendor_id,a.amount);end if;
 return p_original;
end $$;

create function cp7_vendor_receivable.prove_v1(p_vendor uuid)returns void
language plpgsql stable security definer set search_path=''as $$
begin
 if exists(select 1 from cp7_vendor_receivable.sources_v1 s
  left join erp.bd_laundry_invoices_v1 i on i.id=s.correction_id left join erp.journal_entries j on j.id=i.journal_id
  where s.vendor_id=p_vendor and(i.id is null or i.vendor_id<>s.vendor_id or i.header_total<>-s.amount
   or i.invoice_date<>s.economic_date or i.corrects_invoice_id is null or i.status not in('POSTED','REVERSED')
   or j.id is null or j.source_id<>i.id or j.source_type<>'BD_LAUNDRY_CORRECTION_CREDIT'or j.status<>i.status))then
  raise exception 'CP7_VENDOR_RECEIVABLE_SOURCE_CHANGED';end if;
 if exists(select 1 from cp7_vendor_receivable.refunds_v1 r join cp7_vendor_receivable.sources_v1 s on s.correction_id=r.correction_id
  left join cp7_vendor_receivable.reversals_v1 x on x.refund_id=r.id left join erp.journal_entries j on j.id=r.journal_id
  left join erp.journal_entries rev on rev.id=x.journal_id
  left join erp.cash_accounts ca on ca.id=r.cash_account_id
  where s.vendor_id=p_vendor and(j.id is null or j.source_type<>'CP7_VENDOR_RECEIVABLE_REFUND'or j.source_id<>r.id
   or j.economic_date<>r.economic_date or j.status is distinct from(case when x.refund_id is null then 'POSTED'else 'REVERSED'end)
   or ca.id is null or(select count(*)from erp.journal_lines l where l.journal_entry_id=j.id)<>2
   or(select count(*)from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=ca.coa_account_id
      and l.vendor_id=s.vendor_id and l.debit=r.amount and l.credit=0)<>1
   or(x.refund_id is not null and(rev.id is null or rev.reversal_of_id is distinct from j.id or rev.status<>'POSTED'))))then
  raise exception 'CP7_VENDOR_REFUND_JOURNAL_CHANGED';end if;
 -- Every AR posting must trace to its correction, existing BD application,
 -- refund or the Native inverse of one of those. Equal totals alone are not proof.
 if exists(with expected as(
  select s.account_id,s.vendor_id,i.journal_id,s.amount delta from cp7_vendor_receivable.sources_v1 s
   join erp.bd_laundry_invoices_v1 i on i.id=s.correction_id where s.vendor_id=p_vendor
  union all
  select s.account_id,s.vendor_id,j.id,-a.amount from cp7_vendor_receivable.sources_v1 s
   join erp.bd_claim_credit_applications_v1 a on a.correction_invoice_id=s.correction_id and a.source_kind='INVOICE_CORRECTION'
   left join erp.journal_entries j on j.source_id=coalesce(a.vendor_payment_id,a.opening_settlement_id)and j.reversal_of_id is null
   where s.vendor_id=p_vendor
  union all
  select s.account_id,s.vendor_id,r.journal_id,-r.amount from cp7_vendor_receivable.sources_v1 s
   join cp7_vendor_receivable.refunds_v1 r on r.correction_id=s.correction_id where s.vendor_id=p_vendor),
 expanded as(select *from expected union all
  select e.account_id,e.vendor_id,j.id,-e.delta from expected e join erp.journal_entries j on j.reversal_of_id=e.journal_id),
 observed as(select l.account_id,l.vendor_id,l.journal_entry_id,sum(l.debit-l.credit)delta,count(*)n
  from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
  where l.vendor_id=p_vendor and j.status in('POSTED','REVERSED')
   and l.account_id in(select account_id from cp7_vendor_receivable.sources_v1 where vendor_id=p_vendor)
  group by l.account_id,l.vendor_id,l.journal_entry_id)
 select 1 from expanded e full join observed o on o.account_id=e.account_id and o.vendor_id=e.vendor_id and o.journal_entry_id=e.journal_id
 where e.journal_id is null or o.journal_entry_id is null or o.delta<>e.delta or o.n<>1)then
  raise exception 'CP7_VENDOR_RECEIVABLE_MATERIALIZATION_UNPROVEN';end if;
end $$;

create function cp7_vendor_receivable.check_dates_v1(p_vendor uuid)returns void
language plpgsql stable security definer set search_path=''as $$
begin
 perform cp7_vendor_receivable.prove_v1(p_vendor);
 -- Include both original REVERSED journals and their posted inverse, on each date basis.
 if exists(with deltas as(
  select l.account_id,j.economic_date on_day,'ECONOMIC'axis,sum(l.debit-l.credit)delta
   from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
   where l.vendor_id=p_vendor and j.status in('POSTED','REVERSED')
    and l.account_id in(select account_id from cp7_vendor_receivable.sources_v1 where vendor_id=p_vendor)
   group by l.account_id,j.economic_date
  union all
  select l.account_id,j.transaction_date,'BOOK',sum(l.debit-l.credit)
   from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
   where l.vendor_id=p_vendor and j.status in('POSTED','REVERSED')
    and l.account_id in(select account_id from cp7_vendor_receivable.sources_v1 where vendor_id=p_vendor)
   group by l.account_id,j.transaction_date),running as(
  select sum(delta)over(partition by account_id,axis order by on_day)balance from deltas)
  select 1 from running where balance<0)then raise exception 'CP7_VENDOR_RECEIVABLE_NEGATIVE_DATED: saldo piutang vendor tidak cukup pada tanggal ekonomi atau tanggal buku';end if;
end $$;

create function cp7_vendor_receivable.refund_v1(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare s cp7_vendor_receivable.sources_v1%rowtype;i erp.bd_laundry_invoices_v1%rowtype;
 a numeric;d date;c uuid;coa uuid;why text;j uuid;left_amount numeric;
begin
 perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
 perform erp._cp3_assert_closed_json_object(p_payload,array['source_id','amount','date','cash_account_id','reason'],
  array['source_id','amount','date','cash_account_id','reason'],'vendor refund');
 select *into i from erp.bd_laundry_invoices_v1 where id=erp.bd_uuid_v1(p_payload,'source_id',true)for update;
 select *into s from cp7_vendor_receivable.sources_v1 where correction_id=i.id;
 if s.correction_id is null or i.status<>'POSTED'then raise exception 'CP7_VENDOR_RECEIVABLE_SOURCE_NOT_ACTIVE';end if;
 a:=erp.bd_amount_v1(p_payload->'amount','amount',true);d:=erp.bb_parse_date_v1(p_payload->>'date','date');
 why:=btrim(p_payload->>'reason');
 if why is null or length(why)not between 4 and 500 then raise exception 'BD_REASON_REQUIRED: alasan 4–500 karakter';end if;
 if d<s.economic_date then raise exception 'BD_CLAIM_CREDIT_BEFORE_APPROVAL';end if;
 if d>erp.bb_business_today_v1()then raise exception 'BD_DATE_FUTURE';end if;
 left_amount:=s.amount-erp.bd_claim_credit_applied_v1('INVOICE_CORRECTION',s.correction_id);
 if a<=0 or a>left_amount then raise exception 'BD_CLAIM_CREDIT_EXCEEDS_AVAILABLE: sisa piutang %, diminta %',left_amount,a;end if;
 c:=erp.bd_uuid_v1(p_payload,'cash_account_id',true);
 select ca.coa_account_id into coa from erp.cash_accounts ca join erp.chart_accounts ac on ac.id=ca.coa_account_id
  where ca.id=c and ca.is_active and ac.is_active and ac.is_postable and ac.account_type='ASSET'and ac.normal_balance='DEBIT'for share of ca,ac;
 if coa is null then raise exception 'BD_CASH_ACCOUNT_REQUIRED: pilih rekening kas/bank aktif';end if;
 j:=erp.post_journal('CP7_VENDOR_RECEIVABLE_REFUND',p_request,d,'Pengembalian vendor untuk '||i.invoice_number||': '||why,
  jsonb_build_array(jsonb_build_object('account_id',coa,'debit',a,'credit',0,'vendor_id',s.vendor_id),
   jsonb_build_object('account_id',s.account_id,'debit',0,'credit',a,'vendor_id',s.vendor_id)));
 insert into cp7_vendor_receivable.refunds_v1(id,correction_id,amount,cash_account_id,economic_date,reason,journal_id,actor)
 values(p_request,s.correction_id,a,c,d,why,j,erp.current_app_user_id());
 perform cp7_vendor_receivable.check_dates_v1(s.vendor_id);
 return jsonb_build_object('refund_id',p_request,'source_id',s.correction_id,'journal_id',j,'amount',a::numeric(18,2)::text,
  'remaining',(left_amount-a)::numeric(18,2)::text);
end $$;

create function cp7_vendor_receivable.reverse_refund_v1(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare r cp7_vendor_receivable.refunds_v1%rowtype;s cp7_vendor_receivable.sources_v1%rowtype;why text;j uuid;
begin
 perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
 perform erp._cp3_assert_closed_json_object(p_payload,array['refund_id','reason'],array['refund_id','reason'],'reverse vendor refund');
 select *into r from cp7_vendor_receivable.refunds_v1 where id=erp.bd_uuid_v1(p_payload,'refund_id',true);
 if r.id is null then raise exception 'CP7_VENDOR_REFUND_NOT_FOUND';end if;
 perform 1 from erp.bd_laundry_invoices_v1 where id=r.correction_id for update;
 if exists(select 1 from cp7_vendor_receivable.reversals_v1 where refund_id=r.id)then raise exception 'CP7_VENDOR_REFUND_ALREADY_REVERSED';end if;
 why:=btrim(p_payload->>'reason');
 if why is null or length(why)not between 4 and 500 then raise exception 'BD_REASON_REQUIRED: alasan 4–500 karakter';end if;
 j:=erp.reverse_journal(r.journal_id,why);
 insert into cp7_vendor_receivable.reversals_v1(refund_id,request_id,journal_id,reason,actor)
 values(r.id,p_request,j,why,erp.current_app_user_id());
 select *into strict s from cp7_vendor_receivable.sources_v1 where correction_id=r.correction_id;
 perform cp7_vendor_receivable.check_dates_v1(s.vendor_id);
 return jsonb_build_object('refund_id',r.id,'reversal_journal_id',j,'source_id',s.correction_id);
end $$;

create function cp7_vendor_receivable.augment_v1(p_vendor uuid,p_base jsonb)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare remaining numeric;gl numeric;credits jsonb;refunds jsonb;l jsonb;expected_ap numeric;
begin
 select coalesce(sum(s.amount-erp.bd_claim_credit_applied_v1('INVOICE_CORRECTION',s.correction_id)),0)into remaining
  from cp7_vendor_receivable.sources_v1 s join erp.bd_laundry_invoices_v1 i on i.id=s.correction_id
  where s.vendor_id=p_vendor and i.status='POSTED';
 if remaining<0 then raise exception 'CP7_VENDOR_RECEIVABLE_SOURCE_OVERUSED';end if;
 select coalesce(sum(jl.debit-jl.credit),0)into gl from erp.journal_lines jl join erp.journal_entries j on j.id=jl.journal_entry_id
  where jl.vendor_id=p_vendor and j.status in('POSTED','REVERSED')
  and jl.account_id in(select account_id from cp7_vendor_receivable.sources_v1 where vendor_id=p_vendor);
 if gl<>remaining then raise exception 'CP7_VENDOR_RECEIVABLE_LEDGER_MISMATCH';end if;
 if exists(select 1 from cp7_vendor_receivable.refunds_v1 r join cp7_vendor_receivable.sources_v1 s on s.correction_id=r.correction_id
  left join cp7_vendor_receivable.reversals_v1 x on x.refund_id=r.id
  left join erp.journal_entries j on j.id=r.journal_id
  where s.vendor_id=p_vendor and(j.id is null or j.status is distinct from(case when x.refund_id is null then 'POSTED'else 'REVERSED'end)))then
  raise exception 'CP7_VENDOR_REFUND_JOURNAL_CHANGED';end if;
 perform cp7_vendor_receivable.check_dates_v1(p_vendor);
 select coalesce(jsonb_agg(c||jsonb_build_object('receivable',case when s.correction_id is null then '0.00'else c->>'available'end,
  'refunded',cp7_vendor_receivable.refunded_v1(c->>'kind',(c->>'id')::uuid)::numeric(18,2)::text)),'[]'::jsonb)into credits
  from jsonb_array_elements(p_base->'credits')c left join cp7_vendor_receivable.sources_v1 s on s.correction_id=(c->>'id')::uuid;
 select coalesce(jsonb_agg(jsonb_build_object('id',r.id,'source_id',r.correction_id,'source_number',i.invoice_number,
  'date',r.economic_date,'amount',r.amount::text,'cash_account_id',r.cash_account_id,'journal_id',r.journal_id,
  'recorded_at',r.recorded_at,'status',case when x.refund_id is null then 'POSTED'else 'REVERSED'end)order by r.recorded_at,r.id),'[]'::jsonb)into refunds
  from cp7_vendor_receivable.refunds_v1 r join cp7_vendor_receivable.sources_v1 s on s.correction_id=r.correction_id
  join erp.bd_laundry_invoices_v1 i on i.id=s.correction_id left join cp7_vendor_receivable.reversals_v1 x on x.refund_id=r.id
  where s.vendor_id=p_vendor;
 l:=p_base->'ledger';expected_ap:=(l->>'documents_remaining')::numeric-(l->>'credit_available')::numeric+remaining;
 return p_base||jsonb_build_object('vendor_receivable_contract','cp7.vendor-receivable.v1','credits',credits,'refunds',refunds,
  'ledger',l||jsonb_build_object('receivable_balance',remaining::numeric(18,2)::text,'receivable_gl',gl::numeric(18,2)::text,
   'matches',(l->>'ap_balance')::numeric=expected_ap and gl=remaining));
end $$;

revoke all on all tables in schema cp7_vendor_receivable from public,anon,authenticated,service_role;
revoke all on all functions in schema cp7_vendor_receivable from public,anon,authenticated,service_role;
