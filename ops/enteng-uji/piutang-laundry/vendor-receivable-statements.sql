do $vendor_precheck$
begin
 if to_regnamespace('cp7_vendor_receivable') is not null then raise exception 'Vendor AR already installed';end if;
end $vendor_precheck$;
do $vendor_routine_check$
 begin
  if exists(select from (values ('erp.bd_apply_vendor_credit_v1(text,uuid,text,uuid,numeric,date,text,uuid)','3384d2e6fe13955f9d5f25507a35d7ef5a618c2760302e231c1f63c86ea5f9e6'),('erp.bd_claim_credit_applied_v1(text,uuid)','98979a9e8902b591c09ad1a95990ee5195d34f293fec5679ce324f710d7fa30c'),('erp.bd_claim_credit_opening_lines_v1(uuid)','25d977da554119636f591f77cdc1a43e9ceac0e5b89cc58962f1375c79773ffa'),('erp.bd_post_invoice_v1(jsonb,uuid)','a3b7375eb5d3a5e94199ce72a9342496f2a571f4b441f1c72018e193bf0cb6e1'),('erp.bd_vendor_payables_v1(uuid)','7a137db5d6d33bc9e70a9306a30b0f310ec0899fbcae27c707c14201086cc7f4'),('erp.get_laundry_bd_workspace_v1(jsonb)','93cc0c00d971eea4d05b4f48602e90d9488e31cc005586d9084b9e8749640a0e'),('erp.save_laundry_bd_action_v1(text,jsonb,uuid)','087bb966c9689f4efe14f79a6b092afd3f4eb37f463f0ad81166b6c3396c9e46')) expected(sig,sha)
     left join pg_proc p on p.oid=to_regprocedure(expected.sig)
     where p.oid is null or p.proowner<>'postgres'::regrole or encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex')<>expected.sha)
     then raise exception 'Vendor AR business function differs';end if;
 end $vendor_routine_check$;
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
  where (l.vendor_id=p_vendor or not exists(
    select 1 from cp7_vendor_receivable.sources_v1 owner_source
    where owner_source.account_id=l.account_id and owner_source.vendor_id=l.vendor_id))
   and j.status in('POSTED','REVERSED')
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

CREATE OR REPLACE FUNCTION erp.bd_apply_vendor_credit_v1(p_kind text, p_source uuid, p_target_kind text, p_target uuid, p_amount numeric, p_date date, p_reason text, p_request uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare src jsonb;v_applied numeric;v_available numeric;v_remaining numeric;h erp.vendor_invoices%rowtype;b erp.opening_subledger_balances%rowtype;ctx jsonb;
  v_vendor uuid;v_at timestamptz;v_journal uuid;v_paid numeric;v_doc_date date;v_label text;v_method text;v_prefix text;
begin
  if p_kind='DAILY_CLAIM' then perform 1 from erp.laundry_claims where id=p_source for update;
  elsif p_kind='OPENING_CLAIM' then perform 1 from erp.bd_opening_laundry_claim_events_v1 where id=p_source for update;
  elsif p_kind='INVOICE_CORRECTION' then perform 1 from erp.bd_laundry_invoices_v1 where id=p_source for update;
  else raise exception 'BD_FIELD_INVALID: source_kind DAILY_CLAIM, OPENING_CLAIM atau INVOICE_CORRECTION';end if;
  v_label:=case when p_kind='INVOICE_CORRECTION' then 'kredit koreksi' else 'kredit klaim' end;
  v_method:=case when p_kind='INVOICE_CORRECTION' then 'CORRECTION_CREDIT' else 'CLAIM_CREDIT' end;
  v_prefix:=case when p_kind='INVOICE_CORRECTION' then 'KR' else 'KK' end;
  src:=erp.bd_claim_credit_source_v1(p_kind,p_source);
  if src is null then raise exception 'BD_CLAIM_CREDIT_NOT_FOUND: % tidak ditemukan',v_label;end if;
  if not (src->>'active')::boolean then raise exception 'BD_CLAIM_CREDIT_NOT_ACTIVE: % % belum disetujui/diposting atau sudah dibatalkan',v_label,src->>'number';end if;
  v_vendor:=(src->>'vendor_id')::uuid;
  if p_date<(src->>'approved_date')::date then
    raise exception 'BD_CLAIM_CREDIT_BEFORE_APPROVAL: % % baru ada sejak %; tidak dapat dipakai pada %',v_label,src->>'number',src->>'approved_date',p_date;end if;
  if p_date>erp.bb_business_today_v1() then raise exception 'BD_DATE_FUTURE: tanggal pemakaian kredit di masa depan';end if;
  v_applied:=erp.bd_claim_credit_applied_v1(p_kind,p_source);
  v_available:=(src->>'amount')::numeric-v_applied;
  if p_amount>v_available then
    raise exception 'BD_CLAIM_CREDIT_EXCEEDS_AVAILABLE: % % tersisa %, sudah terpakai %, diminta %',v_label,src->>'number',v_available,v_applied,p_amount;end if;
  v_at:=erp.bb_physical_at_v1(p_date);
  if p_target_kind='VENDOR_INVOICE' then
    select * into h from erp.vendor_invoices where id=p_target for update;
    if h.id is null then raise exception 'BD_DOCUMENT_NOT_FOUND: invoice vendor tidak ditemukan';end if;
    if h.vendor_id<>v_vendor then raise exception 'BD_CLAIM_CREDIT_OTHER_VENDOR: % hanya untuk tagihan vendor yang sama',v_label;end if;
    if h.status not in('POSTED','PARTIAL_PAID') then raise exception 'BD_DOCUMENT_NOT_OPEN: invoice % sudah lunas atau tidak aktif',h.invoice_number;end if;
    v_doc_date:=h.invoice_date;
    v_remaining:=h.total_amount-erp.bd_vendor_invoice_paid_v1(h.id,null);
    if p_amount>v_remaining then raise exception 'BD_CLAIM_CREDIT_EXCEEDS_REMAINING: sisa invoice % adalah %, diminta %',h.invoice_number,v_remaining,p_amount;end if;
    if p_date<v_doc_date then raise exception 'BD_DATE_BEFORE_DOCUMENT: pelunasan tidak boleh sebelum tanggal invoice %',v_doc_date;end if;
    insert into erp.vendor_payments(id,vendor_invoice_id,payment_number,payment_date,amount,cash_account_id,payment_method,reference_number,status,notes,created_by)
    values(p_request,h.id,v_prefix||'-'||upper(substr(replace(p_request::text,'-',''),1,16)),v_at,p_amount,null,v_method,left(src->>'number',100),'DRAFT',
      p_reason,erp.current_app_user_id());
    insert into erp.bd_claim_credit_applications_v1(id,vendor_id,source_kind,laundry_claim_id,opening_claim_event_id,correction_invoice_id,target_kind,
      vendor_payment_id,amount,applied_date,reason,created_by)
    values(p_request,v_vendor,p_kind,case when p_kind='DAILY_CLAIM' then p_source end,case when p_kind='OPENING_CLAIM' then p_source end,
      case when p_kind='INVOICE_CORRECTION' then p_source end,p_target_kind,p_request,p_amount,p_date,p_reason,erp.current_app_user_id());
    v_journal:=erp.post_journal('VENDOR_PAYMENT',p_request,erp._cp3_business_date(v_at),
      case when p_kind='INVOICE_CORRECTION' then 'Kredit koreksi laundry ' else 'Kredit klaim laundry ' end||(src->>'number')||' untuk '||h.invoice_number,
      cp7_vendor_receivable.application_lines_v1(p_kind,p_source,v_vendor,p_amount));
    update erp.vendor_payments set status='POSTED' where id=p_request;
    v_paid:=erp.bd_vendor_invoice_paid_v1(h.id,null);
    update erp.vendor_invoices set status=case when v_paid=total_amount then 'PAID' else 'PARTIAL_PAID' end,updated_at=statement_timestamp() where id=h.id;
  perform cp7_vendor_receivable.check_dates_v1(v_vendor);
    return jsonb_build_object('application_id',p_request,'target_kind',p_target_kind,'target_id',h.id,'document_number',h.invoice_number,
      'amount',p_amount::text,'remaining',(h.total_amount-v_paid)::numeric(18,2)::text,'credit_left',(v_available-p_amount)::numeric(18,2)::text);
  elsif p_target_kind<>'OPENING_PAYABLE' then raise exception 'BD_FIELD_INVALID: target_kind VENDOR_INVOICE atau OPENING_PAYABLE';
  end if;
  select * into b from erp.opening_subledger_balances where id=p_target for update;
  if b.id is null or b.party_type<>'VENDOR' or b.direction<>'PAYABLE' then raise exception 'BD_DOCUMENT_NOT_FOUND: hutang vendor saldo awal tidak ditemukan';end if;
  if b.vendor_id<>v_vendor then raise exception 'BD_CLAIM_CREDIT_OTHER_VENDOR: % hanya untuk tagihan vendor yang sama',v_label;end if;
  ctx:=erp.bb_opening_balance_context_v1(b.id);
  v_remaining:=b.original_amount-b.settled_amount-erp.bb_opening_balance_reserved_v1(b.id);
  if p_amount>v_remaining then raise exception 'BD_CLAIM_CREDIT_EXCEEDS_REMAINING: sisa hutang saldo awal % adalah %, diminta %',ctx->>'document_number',v_remaining,p_amount;end if;
  insert into erp.opening_subledger_settlements(id,balance_id,settlement_number,physical_at,amount,cash_account_id,status,notes,created_by)
  values(p_request,b.id,'OSS-'||v_prefix||'-'||upper(substr(replace(p_request::text,'-',''),1,12)),v_at,p_amount,null,'DRAFT',p_reason,erp.current_app_user_id());
  insert into erp.bb_opening_credits_v1(settlement_id,credit_kind,credit_note_number,reason)
  values(p_request,case when p_kind='INVOICE_CORRECTION' then 'VENDOR_CORRECTION_APPLY' else 'VENDOR_CLAIM_APPLY' end,
    left((src->>'number')||' #'||upper(substr(replace(p_request::text,'-',''),1,8)),120),p_reason);
  insert into erp.bd_claim_credit_applications_v1(id,vendor_id,source_kind,laundry_claim_id,opening_claim_event_id,correction_invoice_id,target_kind,
    opening_settlement_id,amount,applied_date,reason,created_by)
  values(p_request,v_vendor,p_kind,case when p_kind='DAILY_CLAIM' then p_source end,case when p_kind='OPENING_CLAIM' then p_source end,
    case when p_kind='INVOICE_CORRECTION' then p_source end,p_target_kind,p_request,p_amount,p_date,p_reason,erp.current_app_user_id());
  perform erp.post_opening_subledger_settlement(p_request);
  select * into b from erp.opening_subledger_balances where id=b.id;
  perform cp7_vendor_receivable.check_dates_v1(v_vendor);
  return jsonb_build_object('application_id',p_request,'target_kind',p_target_kind,'target_id',b.id,'document_number',ctx->>'document_number',
    'amount',p_amount::text,'remaining',(b.original_amount-b.settled_amount)::numeric(18,2)::text,'credit_left',(v_available-p_amount)::numeric(18,2)::text);
end;$function$;
CREATE OR REPLACE FUNCTION erp.bd_claim_credit_applied_v1(p_kind text, p_id uuid)
 RETURNS numeric
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select (coalesce(sum(a.amount),0)+cp7_vendor_receivable.refunded_v1(p_kind,p_id))::numeric(18,2) from erp.bd_claim_credit_applications_v1 a
  left join erp.vendor_payments p on p.id=a.vendor_payment_id
  left join erp.opening_subledger_settlements s on s.id=a.opening_settlement_id
  where a.source_kind=p_kind and (case p_kind when 'DAILY_CLAIM' then a.laundry_claim_id when 'OPENING_CLAIM' then a.opening_claim_event_id
      else a.correction_invoice_id end)=p_id
    and coalesce(p.status,s.status)='POSTED'
$function$;
CREATE OR REPLACE FUNCTION erp.bd_claim_credit_opening_lines_v1(p_settlement_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare s erp.opening_subledger_settlements%rowtype;b erp.opening_subledger_balances%rowtype;
begin
  select * into s from erp.opening_subledger_settlements where id=p_settlement_id;
  select * into b from erp.opening_subledger_balances where id=s.balance_id;
  if b.party_type<>'VENDOR' or b.direction<>'PAYABLE' then
    raise exception 'BB_CREDIT_KIND_MISMATCH: kredit klaim/koreksi laundry hanya untuk hutang vendor laundry';end if;
  if not exists(select 1 from erp.bd_claim_credit_applications_v1 a where a.opening_settlement_id=s.id and a.vendor_id=b.vendor_id) then
    raise exception 'BD_CLAIM_CREDIT_SOURCE_MISSING: pemakaian kredit klaim tanpa klaim sumber';end if;
  return cp7_vendor_receivable.opening_lines_v1(p_settlement_id,jsonb_build_array(
    jsonb_build_object('mapping_key','AP_VENDOR','debit',s.amount,'credit',0,'vendor_id',b.vendor_id),
    jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',s.amount,'vendor_id',b.vendor_id)));
end;$function$;
CREATE OR REPLACE FUNCTION erp.bd_post_invoice_v1(p_payload jsonb, p_request uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare i erp.bd_laundry_invoices_v1%rowtype;l record;v_dec02 jsonb;v_dec03 jsonb;v_dec06 jsonb;v_versions jsonb:='{}'::jsonb;v_billable jsonb;
  v_gross numeric:=0;v_positive numeric:=0;v_payable numeric;v_weights numeric[]:='{}';v_ids uuid[]:='{}';v_split numeric[];k integer;v_last uuid;
  v_pool numeric;v_pieces integer;v_prior numeric;v_released numeric;v_complete boolean;v_cap integer;v_billed integer;v_paid boolean;
  v_lines jsonb:='[]'::jsonb;v_po record;v_journal uuid;v_group uuid;v_line_ids uuid[];v_net numeric;v_open_rel numeric;v_open_var numeric;
  o erp.bd_laundry_invoices_v1%rowtype;v_source_net numeric;v_ap numeric;v_origin_left numeric;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['invoice_id','expected_version'],array['invoice_id','expected_version','vendor_receivable_account_id'],'post invoice');
  select * into i from erp.bd_laundry_invoices_v1 where id=erp.bd_uuid_v1(p_payload,'invoice_id',true) for update;
  if i.id is null or i.status<>'DRAFT' then raise exception 'BD_INVOICE_NOT_DRAFT: hanya draf invoice yang dapat diposting';end if;
  if p_payload->>'expected_version' is distinct from i.row_version::text then raise exception 'STALE_VERSION: draf invoice berubah; muat ulang';end if;
  if i.invoice_date>(statement_timestamp() at time zone 'Asia/Jakarta')::date then
    raise exception 'BD_INVOICE_FUTURE_DATE: tanggal invoice vendor laundry berada di masa depan';end if;
  if exists(select 1 from erp.bd_laundry_invoices_v1 x where x.vendor_id=i.vendor_id and lower(btrim(x.invoice_number))=lower(btrim(i.invoice_number))
      and x.status='POSTED') or exists(select 1 from erp.vendor_invoices v where v.vendor_id=i.vendor_id
      and lower(btrim(v.invoice_number))=lower(btrim(i.invoice_number)) and v.status in('POSTED','PARTIAL_PAID','PAID')) then
    raise exception 'BD_INVOICE_DUPLICATE_NUMBER: nomor invoice vendor ini sudah diposting';end if;
  -- Owner settings (fail closed): billable categories, variance treatment, and discount/tax/rounding when used.
  v_dec02:=erp.bd_require_policy_v1('LAU_DEC02','dasar qty yang ditagih vendor laundry');v_billable:=v_dec02->'billable';
  v_dec06:=erp.bd_require_policy_v1('LAU_DEC06','perlakuan selisih invoice laundry');
  v_versions:=jsonb_build_object('LAU_DEC02',erp.bd_policy_version_v1('LAU_DEC02'),'LAU_DEC06',erp.bd_policy_version_v1('LAU_DEC06'));
  if i.discount_amount>0 or i.tax_amount>0 or i.rounding_amount<>0 then
    v_dec03:=erp.bd_require_policy_v1('LAU_DEC03','diskon, pajak atau pembulatan invoice laundry');
    v_versions:=v_versions||jsonb_build_object('LAU_DEC03',erp.bd_policy_version_v1('LAU_DEC03'));
    if i.discount_amount>0 and v_dec03->>'discount'<>'ALLOWED' then raise exception 'BD_DISCOUNT_REFUSED: LAU-DEC03 tidak mengizinkan diskon invoice laundry';end if;
    if i.rounding_amount<>0 and v_dec03->>'rounding'<>'LAST_LINE' then raise exception 'BD_ROUNDING_REFUSED: LAU-DEC03 tidak mengizinkan baris pembulatan';end if;
    if i.tax_amount>0 and v_dec03->>'tax_account_id' is null then raise exception 'BD_TAX_ACCOUNT_REQUIRED: LAU-DEC03 belum menetapkan akun pajak masukan';end if;
  end if;
  if not exists(select 1 from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id) then raise exception 'BD_INVOICE_LINES: invoice tanpa baris';end if;
  -- A correction document (owner decision no. 13) corrects one posted invoice of the same vendor, on or after its date, only in
  -- the sources that invoice billed; the origin row is locked so it cannot be reversed meanwhile.
  if i.corrects_invoice_id is null then
    if exists(select 1 from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id and line_kind='CORRECTION') then
      raise exception 'BD_CORRECTION_SEPARATE_DOCUMENT: koreksi dibuat sebagai dokumen koreksi tersendiri yang tertaut ke invoice asal';end if;
  else
    select * into o from erp.bd_laundry_invoices_v1 where id=i.corrects_invoice_id for update;
    if o.status<>'POSTED' or o.corrects_invoice_id is not null or o.vendor_id<>i.vendor_id then
      raise exception 'BD_CORRECTION_ORIGIN_INVALID: invoice asal harus invoice vendor laundry POSTED milik vendor yang sama';end if;
    if i.invoice_date<o.invoice_date then
      raise exception 'BD_CORRECTION_BEFORE_ORIGIN: tanggal dokumen koreksi % sebelum tanggal invoice asal %',i.invoice_date,o.invoice_date;end if;
    perform erp.bd_check_correction_sources_v1(i.id);
    if exists(select 1 from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id and sign(amount)<>sign(i.header_total)) then
      raise exception 'BD_CORRECTION_MIXED_SIGN: satu dokumen koreksi hanya menaikkan atau hanya menurunkan tagihan';end if;
  end if;
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform 1 from erp.be_redye_services_v1 where id in(select rework_service_id from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id) order by id for update;
  -- Lock the sources in a fixed order (with the baseline's per-cutting-group flow lock) before reading capacity and estimates.
  for v_group in select distinct dl.cutting_group_id from erp.bd_laundry_invoice_lines_v1 x join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id where x.invoice_id=i.id order by 1 loop
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group::text,0));
  end loop;
  select array_agg(distinct x.receipt_line_id order by x.receipt_line_id) into v_line_ids from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id;
  perform 1 from erp.laundry_receipt_lines where id=any(v_line_ids) order by id for update;
  if exists(select 1 from erp.bd_laundry_invoice_lines_v1 x
    join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
    where x.invoice_id=i.id and x.line_kind='BILL' and x.category in('GOOD','BS')
      and x.actual_wash_process_id is null and rl.actual_wash_process_id is null) then
    raise exception 'LAUNDRY_INVOICE_WASH_REQUIRED: isi jenis cucian aktual pada baris kontra bon';
  end if;
  perform 1 from erp.bd_opening_laundry_uninvoiced_v1 where id in(select x.opening_uninvoiced_id from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id)
    order by id for update;
  -- Discount spread over the billed amounts (largest remainder on cents); rounding on the last billing line.
  for l in select * from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id order by line_no loop
    v_gross:=v_gross+l.amount;
    if l.line_kind='BILL' then v_ids:=v_ids||l.id;v_weights:=v_weights||round(l.amount*100);v_positive:=v_positive+l.amount;v_last:=l.id;end if;
  end loop;
  if i.discount_amount>v_positive then raise exception 'BD_DISCOUNT_EXCEEDS_LINES: diskon melebihi nilai baris tagih';end if;
  update erp.bd_laundry_invoice_lines_v1 set discount_share=0,rounding_share=0 where invoice_id=i.id;
  if i.discount_amount>0 then
    if v_positive<=0 then raise exception 'BD_DISCOUNT_EXCEEDS_LINES: diskon tanpa baris tagih bernilai';end if;
    v_split:=erp.bd_split_money_v1(i.discount_amount,v_weights);
    for k in 1..array_length(v_ids,1) loop update erp.bd_laundry_invoice_lines_v1 set discount_share=v_split[k] where id=v_ids[k];end loop;
  end if;
  if i.rounding_amount<>0 then
    if v_last is null then raise exception 'BD_ROUNDING_REFUSED: pembulatan memerlukan baris tagih';end if;
    update erp.bd_laundry_invoice_lines_v1 set rounding_share=i.rounding_amount where id=v_last;
  end if;
  v_payable:=v_gross-i.discount_amount+i.rounding_amount+i.tax_amount;
  if v_payable<>i.header_total then
    raise exception 'BD_INVOICE_TOTAL_MISMATCH: total invoice % tidak sama dengan baris - diskon + pembulatan + pajak = %',i.header_total,v_payable;end if;
  if (i.corrects_invoice_id is null and i.header_total<=0) or i.header_total=0 then
    raise exception 'BD_INVOICE_TOTAL_MISMATCH: total invoice harus lebih dari 0 (dokumen koreksi: tidak nol)';end if;
  -- Each line in order: category billable, capacity, released estimate, variance.
  for l in select x.*,rl.actual_cost,rl.actual_cost_status,rl.delivery_line_id,u.accrued_amount opening_pool,u.qty opening_qty
      from erp.bd_laundry_invoice_lines_v1 x left join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
      left join erp.bd_opening_laundry_uninvoiced_v1 u on u.id=x.opening_uninvoiced_id where x.invoice_id=i.id order by x.line_no loop
    if l.rework_service_id is not null then perform erp.be_invoice_redye_line_v1(l.id,v_billable,v_dec06);continue;end if;
    -- ALL-W05: an opening record of work returned before cutover releases its opening accrual (none while its estimate is
    -- unknown); the difference is not a PO's product cost, so it needs the owner's LAU-DEC06 variance account.
    if l.opening_uninvoiced_id is not null then
      if not v_billable @> to_jsonb(l.category) then
        raise exception 'BD_CATEGORY_NOT_BILLABLE: LAU-DEC02 tidak menetapkan % sebagai qty yang ditagih',l.category;end if;
      v_pool:=l.opening_pool;
      v_prior:=erp.bd_opening_released_v1(l.opening_uninvoiced_id)+coalesce((select sum(x.released_estimate) from erp.bd_laundry_invoice_lines_v1 x
        where x.invoice_id=i.id and x.opening_uninvoiced_id=l.opening_uninvoiced_id and x.line_no<l.line_no),0);
      if l.line_kind='BILL' then
        v_billed:=erp.bd_opening_billed_v1(l.opening_uninvoiced_id)+coalesce((select sum(x.qty) from erp.bd_laundry_invoice_lines_v1 x
          where x.invoice_id=i.id and x.opening_uninvoiced_id=l.opening_uninvoiced_id and x.line_kind='BILL' and x.line_no<l.line_no),0);
        if v_billed+l.qty>l.opening_qty then
          raise exception 'BD_INVOICE_CAPACITY: % % sudah ditagih dari % yang tersedia pada penerimaan saldo awal ini; diminta %',v_billed,l.category,l.opening_qty,l.qty;end if;
        v_complete:=v_billed+l.qty>=l.opening_qty;
        if v_complete then v_released:=v_pool-v_prior;
        else v_released:=least(round(v_pool*l.qty/l.opening_qty,2),v_pool-v_prior);end if;
      else
        if not exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
            where x.opening_uninvoiced_id=l.opening_uninvoiced_id and x.line_kind='BILL' and (y.status='POSTED' or (y.id=i.id and x.line_no<l.line_no))) then
          raise exception 'BD_CORRECTION_WITHOUT_BILL: koreksi hanya untuk sumber yang sudah ditagih';end if;
        select exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
            join erp.vendor_payments p on p.vendor_invoice_id=y.id and p.status='POSTED'
            where x.opening_uninvoiced_id=l.opening_uninvoiced_id and y.status='POSTED') into v_paid;
        if v_paid and v_dec06->>'after_payment'<>'CORRECTION_DOCUMENT' then
          raise exception 'BD_PAID_CORRECTION_REFUSED: invoice sumber sudah dibayar dan LAU-DEC06 tidak mengizinkan dokumen koreksi';end if;
        select coalesce(sum(x.net_amount),0) into v_source_net from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
          where y.status='POSTED' and x.opening_uninvoiced_id=l.opening_uninvoiced_id;
        v_source_net:=v_source_net+(select coalesce(sum(x.amount),0) from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id
          and x.opening_uninvoiced_id=l.opening_uninvoiced_id and x.line_no<=l.line_no);
        if v_source_net<0 then raise exception 'BD_CORRECTION_BELOW_ZERO: koreksi membuat biaya tertagih sumber ini negatif (%)',v_source_net;end if;
        v_released:=0;v_complete:=false;
      end if;
      if v_released<0 then raise exception 'BD_INTERNAL: estimasi yang dilepas negatif';end if;
      v_net:=l.amount-l.discount_share+l.rounding_share;
      if v_net-v_released<>0 and v_dec06->>'variance_mode'<>'VARIANCE_ACCOUNT' then
        raise exception 'BD_OPENING_VARIANCE_NEEDS_ACCOUNT: selisih % pada penerimaan laundry saldo awal bukan biaya produk PO; LAU-DEC06 harus memakai akun selisih (VARIANCE_ACCOUNT)',v_net-v_released;end if;
      update erp.bd_laundry_invoice_lines_v1 x set net_amount=v_net,released_estimate=v_released,variance=v_net-v_released,product_variance=0,
        completes_source=v_complete where x.id=l.id;
      continue;
    end if;
    if not ((l.actual_cost_status='ESTIMATED' and l.actual_cost is not null)
        or (l.actual_cost_status='PENDING' and l.actual_cost is null and l.category in('GOOD','BS')
          and exists(select 1 from erp.bf_laundry_delivery_sources_v1 bf
            where bf.delivery_line_id=l.delivery_line_id and bf.details_pending))) then
      raise exception 'BD_INVOICE_SOURCE_NOT_ESTIMATED: baris penerimaan belum berbiaya estimasi atau sudah final (status %)',l.actual_cost_status;end if;
    -- Unknown estimates are billed directly; actual cost follows the goods.
    if not erp.bd_line_complete_v1(l.delivery_line_id) and v_dec06->>'variance_mode'<>'PRODUCT_COST' then
      raise exception 'BF_UNKNOWN_INVOICE_PRODUCT_COST: biaya yang belum diketahui harus mengikuti biaya produk';end if;
    if not v_billable @> to_jsonb(l.category) then
      raise exception 'BD_CATEGORY_NOT_BILLABLE: LAU-DEC02 tidak menetapkan % sebagai qty yang ditagih',l.category;end if;
    -- Posted invoices plus the earlier lines of this invoice (the invoice is still DRAFT here).
    -- There is no estimated accrual to release for a registered deferred receipt.
    v_pool:=coalesce(l.actual_cost,0);v_pieces:=erp.bd_invoice_pieces_v1(l.receipt_line_id);
    v_prior:=erp.bd_released_estimate_v1(l.receipt_line_id)+coalesce((select sum(x.released_estimate) from erp.bd_laundry_invoice_lines_v1 x
      where x.invoice_id=i.id and x.receipt_line_id=l.receipt_line_id and x.line_no<l.line_no),0);
    if l.line_kind='BILL' then
      v_cap:=erp.bd_invoice_capacity_v1(l.receipt_line_id,l.category);
      v_billed:=erp.bd_invoice_billed_v1(l.receipt_line_id,l.category)+coalesce((select sum(x.qty) from erp.bd_laundry_invoice_lines_v1 x
        where x.invoice_id=i.id and x.receipt_line_id=l.receipt_line_id and x.category=l.category and x.line_kind='BILL' and x.line_no<l.line_no),0);
      if v_billed+l.qty>v_cap then
        raise exception 'BD_INVOICE_CAPACITY: % % sudah ditagih dari % yang tersedia pada baris penerimaan ini; diminta %',v_billed,l.category,v_cap,l.qty;end if;
      -- Complete when every billable category of the source is billed up to its capacity with this line.
      select bool_and(erp.bd_invoice_billed_v1(l.receipt_line_id,c)+coalesce((select sum(x.qty) from erp.bd_laundry_invoice_lines_v1 x
          where x.invoice_id=i.id and x.receipt_line_id=l.receipt_line_id and x.category=c and x.line_kind='BILL' and x.line_no<=l.line_no),0)
          >=erp.bd_invoice_capacity_v1(l.receipt_line_id,c))
        into v_complete from jsonb_array_elements_text(v_billable) c;
      if v_complete then v_released:=v_pool-v_prior;
      else v_released:=least(round(v_pool*l.qty/nullif(v_pieces,0),2),v_pool-v_prior);end if;
    else
      if not exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
          where x.receipt_line_id=l.receipt_line_id and x.line_kind='BILL' and (y.status='POSTED' or (y.id=i.id and x.line_no<l.line_no))) then
        raise exception 'BD_CORRECTION_WITHOUT_BILL: koreksi hanya untuk baris penerimaan yang sudah ditagih';end if;
      select exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
          join erp.vendor_payments p on p.vendor_invoice_id=y.id and p.status='POSTED'
          where x.receipt_line_id=l.receipt_line_id and y.status='POSTED') into v_paid;
      if v_paid and v_dec06->>'after_payment'<>'CORRECTION_DOCUMENT' then
        raise exception 'BD_PAID_CORRECTION_REFUSED: invoice sumber sudah dibayar dan LAU-DEC06 tidak mengizinkan dokumen koreksi';end if;
      select coalesce(sum(x.net_amount),0) into v_source_net from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
        where y.status='POSTED' and x.receipt_line_id=l.receipt_line_id;
      v_source_net:=v_source_net+(select coalesce(sum(x.amount),0) from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id
        and x.receipt_line_id=l.receipt_line_id and x.line_no<=l.line_no);
      if v_source_net<0 then raise exception 'BD_CORRECTION_BELOW_ZERO: koreksi membuat biaya tertagih sumber ini negatif (%)',v_source_net;end if;
      v_released:=0;v_complete:=false;
    end if;
    if v_released<0 then raise exception 'BD_INTERNAL: estimasi yang dilepas negatif';end if;
    update erp.bd_laundry_invoice_lines_v1 x set net_amount=x.amount-x.discount_share+x.rounding_share,released_estimate=v_released,
      variance=x.amount-x.discount_share+x.rounding_share-v_released,
      product_variance=case when v_dec06->>'variance_mode'='PRODUCT_COST' then x.amount-x.discount_share+x.rounding_share-v_released else 0 end,
      completes_source=coalesce(v_complete,false)
    where x.id=l.id;
  end loop;
  if exists(select 1 from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id and net_amount<0 and line_kind='BILL') then
    raise exception 'BD_INVOICE_LINE: nilai bersih baris tagih negatif';end if;
  -- Journal: cost per PO (WIP), variance account when chosen, input tax, payable to the vendor.
  for v_po in select po_id,sum(net_amount) net,sum(released_estimate) rel,sum(variance) var from erp.bd_laundry_invoice_lines_v1
      where invoice_id=i.id and opening_uninvoiced_id is null group by po_id order by po_id loop
    if v_dec06->>'variance_mode'='PRODUCT_COST' then
      if v_po.net<>0 then v_lines:=v_lines||jsonb_build_object('mapping_key','WIP','debit',greatest(v_po.net,0),'credit',greatest(-v_po.net,0),'po_id',v_po.po_id,'vendor_id',i.vendor_id);end if;
    else
      if v_po.rel<>0 then v_lines:=v_lines||jsonb_build_object('mapping_key','WIP','debit',v_po.rel,'credit',0,'po_id',v_po.po_id,'vendor_id',i.vendor_id);end if;
      if v_po.var<>0 then v_lines:=v_lines||jsonb_build_object('account_id',v_dec06->>'variance_account_id','debit',greatest(v_po.var,0),
        'credit',greatest(-v_po.var,0),'po_id',v_po.po_id,'vendor_id',i.vendor_id,'description','Selisih invoice laundry');end if;
    end if;
  end loop;
  -- ALL-W05: opening records release the opening accrual; their difference goes to the owner's variance account.
  select coalesce(sum(released_estimate),0),coalesce(sum(variance),0) into v_open_rel,v_open_var from erp.bd_laundry_invoice_lines_v1
    where invoice_id=i.id and opening_uninvoiced_id is not null;
  if v_open_rel<>0 then v_lines:=v_lines||jsonb_build_object('mapping_key','ACCRUED_MANUFACTURING','debit',v_open_rel,'credit',0,'vendor_id',i.vendor_id,
    'description','Akrual laundry saldo awal');end if;
  if v_open_var<>0 then v_lines:=v_lines||jsonb_build_object('account_id',v_dec06->>'variance_account_id','debit',greatest(v_open_var,0),
    'credit',greatest(-v_open_var,0),'vendor_id',i.vendor_id,'description','Selisih invoice laundry saldo awal');end if;
  if i.tax_amount>0 then v_lines:=v_lines||jsonb_build_object('account_id',v_dec03->>'tax_account_id','debit',i.tax_amount,'credit',0,'vendor_id',i.vendor_id,'description','Pajak masukan invoice laundry');end if;
  if p_payload ? 'vendor_receivable_account_id' and i.header_total>=0 then raise exception 'CP7_VENDOR_RECEIVABLE_CORRECTION_REQUIRED';end if;
  if i.header_total>0 then
    v_lines:=v_lines||jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',i.header_total,'vendor_id',i.vendor_id);
    -- The payable as an ordinary laundry vendor invoice (payments and AP checks read it); an upward correction document too.
    -- Created as DRAFT and posted by a status change, so the vendor invoice post-date guard and the receipt guard run on it.
    insert into erp.vendor_invoices(id,invoice_number,vendor_id,invoice_date,due_date,status,total_amount,notes,created_by)
    values(i.id,i.invoice_number,i.vendor_id,i.invoice_date,i.due_date,'DRAFT',i.header_total,
      case when i.corrects_invoice_id is null then 'BD invoice laundry (LAU-05b)' else 'BD koreksi naik atas invoice laundry '||o.invoice_number end,
      erp.current_app_user_id());
    update erp.vendor_invoices set status='POSTED' where id=i.id;
    v_journal:=erp.post_journal('VENDOR_INVOICE',i.id,i.invoice_date,
      case when i.corrects_invoice_id is null then 'Invoice vendor laundry ' else 'Koreksi naik invoice laundry '||o.invoice_number||': ' end||i.invoice_number,v_lines);
  else
    -- Downward correction: the vendor's payable falls on the correction date. It must be covered by what the vendor is still
    -- owed (a vendor receivable is not silently created).
    if p_payload ? 'vendor_receivable_account_id' then
      v_lines:=v_lines||cp7_vendor_receivable.register_v1(i.id,erp.bd_uuid_v1(p_payload,'vendor_receivable_account_id',true));
    else
    select coalesce(sum(jl.credit-jl.debit),0) into v_ap from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
      where je.status in('POSTED','REVERSED') and jl.account_id=erp.account_id('AP_VENDOR') and jl.vendor_id=i.vendor_id;
    if -i.header_total>v_ap then
      raise exception 'BD_CORRECTION_EXCEEDS_PAYABLE: koreksi turun % melebihi utang ke vendor ini saat ini %; kelebihan bayar ke vendor perlu alur piutang vendor tersendiri',
        -i.header_total,v_ap;end if;
    v_lines:=v_lines||jsonb_build_object('mapping_key','AP_VENDOR','debit',-i.header_total,'credit',0,'vendor_id',i.vendor_id);
    end if;
    v_journal:=erp.post_journal('BD_LAUNDRY_CORRECTION_CREDIT',i.id,i.invoice_date,'Koreksi turun invoice laundry '||o.invoice_number||': '||i.invoice_number,v_lines);
  end if;
  update erp.bd_laundry_invoices_v1 set status='POSTED',policy_versions=v_versions,variance_mode=v_dec06->>'variance_mode',
    variance_account_id=(v_dec06->>'variance_account_id')::uuid,tax_account_id=(v_dec03->>'tax_account_id')::uuid,journal_id=v_journal,
    posted_by=erp.current_app_user_id(),posted_at=statement_timestamp(),row_version=row_version+1 where id=i.id;
  -- A downward correction first settles what its origin still owes (same date); the rest stays a vendor credit.
  if i.header_total<0 then
    select v.total_amount-erp.bd_vendor_invoice_paid_v1(v.id,null) into v_origin_left from erp.vendor_invoices v where v.id=o.id;
    if coalesce(v_origin_left,0)>0 then
      perform erp.bd_apply_vendor_credit_v1('INVOICE_CORRECTION',i.id,'VENDOR_INVOICE',o.id,least(-i.header_total,v_origin_left),i.invoice_date,
        'Koreksi turun '||i.invoice_number||' atas invoice asal',gen_random_uuid());
    end if;
  end if;
  perform erp.bd_invoice_resync_v1(i.id,i.invoice_date);
  perform cp7_vendor_receivable.check_dates_v1(i.vendor_id);
  return erp.bd_invoice_json_v1(i.id);
end;$function$;
CREATE OR REPLACE FUNCTION erp.bd_vendor_payables_v1(p_vendor uuid)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  with docs as (
    select 'VENDOR_INVOICE'::text kind,h.id,h.invoice_number::text number,h.invoice_date date,h.total_amount::numeric(18,2) total,
      erp.bd_vendor_invoice_paid_v1(h.id,'CASH') cash,erp.bd_vendor_invoice_paid_v1(h.id,'CLAIM_CREDIT') credit,
      erp.bd_vendor_invoice_paid_v1(h.id,'CORRECTION_CREDIT') correction,h.status::text status,
      (select o.invoice_number from erp.bd_laundry_invoices_v1 c join erp.bd_laundry_invoices_v1 o on o.id=c.corrects_invoice_id where c.id=h.id)::text corrects
    from erp.vendor_invoices h where h.vendor_id=p_vendor and h.status in('POSTED','PARTIAL_PAID','PAID')
    union all
    select 'OPENING_PAYABLE',b.id,coalesce(ctx->>'document_number','Saldo awal'),coalesce((ctx->>'document_date')::date,(ctx->>'cutover_date')::date),
      b.original_amount::numeric(18,2),
      coalesce((select sum(s.amount) from erp.opening_subledger_settlements s left join erp.bb_opening_credits_v1 c on c.settlement_id=s.id
        where s.balance_id=b.id and s.status='POSTED' and c.credit_kind is distinct from 'VENDOR_CLAIM_APPLY'
          and c.credit_kind is distinct from 'VENDOR_CORRECTION_APPLY'),0)::numeric(18,2),
      coalesce((select sum(s.amount) from erp.opening_subledger_settlements s join erp.bb_opening_credits_v1 c on c.settlement_id=s.id
        where s.balance_id=b.id and s.status='POSTED' and c.credit_kind='VENDOR_CLAIM_APPLY'),0)::numeric(18,2),
      coalesce((select sum(s.amount) from erp.opening_subledger_settlements s join erp.bb_opening_credits_v1 c on c.settlement_id=s.id
        where s.balance_id=b.id and s.status='POSTED' and c.credit_kind='VENDOR_CORRECTION_APPLY'),0)::numeric(18,2),b.status::text,null::text
    from erp.opening_subledger_balances b cross join lateral(select erp.bb_opening_balance_context_v1(b.id) ctx) x
    where b.vendor_id=p_vendor and b.party_type='VENDOR' and b.direction='PAYABLE'),
  credits as (
    select x.src,(x.src->>'amount')::numeric(18,2) amount,erp.bd_claim_credit_applied_v1(x.src->>'kind',(x.src->>'id')::uuid) applied
    from (select erp.bd_claim_credit_source_v1('DAILY_CLAIM',c.id) src from erp.laundry_claims c
            where c.vendor_id=p_vendor and c.status='SETTLED' and c.compensation_amount>0
          union all
          select erp.bd_claim_credit_source_v1('OPENING_CLAIM',e.id) from erp.bd_opening_laundry_claim_events_v1 e
            join erp.bd_opening_laundry_claims_v1 oc on oc.id=e.claim_id
            where oc.vendor_id=p_vendor and e.event_kind='RESOLVE' and e.reversed_at is null and e.compensation_amount>0
          union all
          select erp.bd_claim_credit_source_v1('INVOICE_CORRECTION',i.id) from erp.bd_laundry_invoices_v1 i
            where i.vendor_id=p_vendor and i.status='POSTED' and i.header_total<0) x
    where (x.src->>'active')::boolean),
  ledger as (
    select coalesce(sum(l.credit-l.debit),0)::numeric(18,2) ap from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
    where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id('AP_VENDOR') and l.vendor_id=p_vendor)
  select cp7_vendor_receivable.augment_v1(p_vendor,jsonb_build_object('vendor_id',p_vendor,
    'documents',coalesce((select jsonb_agg(jsonb_build_object('kind',d.kind,'id',d.id,'number',d.number,'date',d.date,'total',d.total::text,
        'paid_cash',d.cash::text,'claim_credit',d.credit::text,'correction_credit',d.correction::text,'corrects',d.corrects,
        'remaining',(d.total-d.cash-d.credit-d.correction)::numeric(18,2)::text,'status',d.status,
        'settlements',case d.kind when 'VENDOR_INVOICE' then coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'number',p.payment_number,
            'date',erp._cp3_business_date(p.payment_date),'amount',p.amount::numeric(18,2)::text,
            'method',case when p.payment_method in('CLAIM_CREDIT','CORRECTION_CREDIT') then p.payment_method else 'CASH' end,
            'reference',p.reference_number,'status',p.status) order by p.payment_date,p.id)
          from erp.vendor_payments p where p.vendor_invoice_id=d.id and p.status in('POSTED','REVERSED')),'[]'::jsonb)
          else coalesce((select jsonb_agg(jsonb_build_object('id',s.id,'number',s.settlement_number,'date',erp._cp3_business_date(s.physical_at),
            'amount',s.amount::numeric(18,2)::text,'method',case when c.credit_kind='VENDOR_CLAIM_APPLY' then 'CLAIM_CREDIT'
              when c.credit_kind='VENDOR_CORRECTION_APPLY' then 'CORRECTION_CREDIT' when c.settlement_id is not null then 'CREDIT' else 'CASH' end,
            'reference',c.credit_note_number,'status',s.status) order by s.physical_at,s.id)
          from erp.opening_subledger_settlements s left join erp.bb_opening_credits_v1 c on c.settlement_id=s.id
          where s.balance_id=d.id and s.status in('POSTED','REVERSED')),'[]'::jsonb) end)
      order by d.date,d.number,d.id) from docs d),'[]'::jsonb),
    'credits',coalesce((select jsonb_agg(c.src||jsonb_build_object('applied',c.applied::text,'available',(c.amount-c.applied)::numeric(18,2)::text)
      order by c.src->>'approved_date',c.src->>'number') from credits c),'[]'::jsonb),
    'cash_accounts',coalesce((select jsonb_agg(jsonb_build_object('id',a.id,'code',a.cash_account_code,'name',a.cash_account_name) order by a.cash_account_name,a.id)
      from erp.cash_accounts a where a.is_active),'[]'::jsonb),
    'ledger',(select jsonb_build_object('ap_balance',l.ap::text,
        'documents_remaining',coalesce((select sum(d.total-d.cash-d.credit-d.correction) from docs d),0)::numeric(18,2)::text,
        'credit_available',coalesce((select sum(c.amount-c.applied) from credits c),0)::numeric(18,2)::text,
        'matches',l.ap=coalesce((select sum(d.total-d.cash-d.credit-d.correction) from docs d),0)-coalesce((select sum(c.amount-c.applied) from credits c),0))
      from ledger l)))
$function$;
CREATE OR REPLACE FUNCTION erp.get_laundry_bd_workspace_v1(p_filters jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_vendor uuid;v_now timestamptz:=statement_timestamp();v_money boolean;v_as_of timestamptz:=statement_timestamp();
  v_invoice_page jsonb;v_receipt_page jsonb;v_invoice_after uuid;v_receipt_after uuid;
begin
  perform erp.require_permission('production.laundry.view');
  if jsonb_typeof(coalesce(p_filters,'{}'::jsonb)) is distinct from 'object' then raise exception 'BD_FILTER_INVALID: filter wajib objek';end if;
  v_vendor:=erp.bd_uuid_v1(coalesce(p_filters,'{}'::jsonb),'vendor_id',false);
  v_money:=erp.has_permission('finance.hpp.view') or erp.has_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(coalesce(p_filters,'{}'::jsonb),array[]::text[],
    array['vendor_id','invoice_after','receipt_after','page_as_of'],'BD workspace filter');
  v_invoice_after:=erp.bd_uuid_v1(p_filters,'invoice_after',false);v_receipt_after:=erp.bd_uuid_v1(p_filters,'receipt_after',false);
  if p_filters ? 'page_as_of' then
    if jsonb_typeof(p_filters->'page_as_of') is distinct from 'string' or length(p_filters->>'page_as_of')>40
       or p_filters->>'page_as_of'!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$' then
      raise exception 'BD_PAGE_INVALID: waktu daftar tidak valid';end if;
    v_as_of:=(p_filters->>'page_as_of')::timestamptz;
    if v_as_of>v_now then raise exception 'BD_PAGE_INVALID: waktu daftar di masa depan';end if;
  elsif v_invoice_after is not null or v_receipt_after is not null then
    raise exception 'BD_PAGE_INVALID: kelanjutan memerlukan waktu daftar asal';
  end if;
  if v_money then
    v_invoice_page:=erp.bd_invoice_page_v1(v_vendor,v_invoice_after,v_as_of);
    if v_vendor is not null then v_receipt_page:=erp.bd_receipt_page_v1(v_vendor,v_receipt_after,v_as_of);end if;
  end if;
  return jsonb_build_object(
    'redye_services',erp.be_redye_workspace_v1(v_vendor,v_money),
    'filters',coalesce(p_filters,'{}'::jsonb),'money_visible',v_money,'deferred_details_supported',true,
    'vendor_receivable_contract','cp7.vendor-receivable.v1',
    'vendor_receivable_accounts',case when v_money then cp7_vendor_receivable.accounts_v1()end,
    'can_manage_master',erp.current_app_role() in('OWNER','ADMIN') and erp.has_permission('master.partner.manage'),
    'can_set_price',erp.current_app_role() in('OWNER','ADMIN') and erp.has_permission('finance.hpp.manage'),
    'is_owner',erp.current_app_role()='OWNER',
    'policies',(select jsonb_agg(jsonb_build_object('key',replace(policy_key,'_','-'),'status',status,'value',value,'version',version::text,
        'set_at',to_char(set_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),'reason',reason) order by policy_key) from erp.bd_policy_settings_v1),
    'vendors',coalesce((select jsonb_agg(jsonb_build_object('id',v.id,'code',v.vendor_code,'name',v.vendor_name,
        'pricing_mode',coalesce(t.pricing_mode,'RATE'),'pricing_unit',coalesce(t.pricing_unit,'PCS'),
        'bd_priced',t.pricing_mode is distinct from null and (t.pricing_mode<>'RATE' or t.pricing_unit<>'PCS' or t.minimum_charge is not null)
          or exists(select 1 from erp.bd_laundry_scoped_rates_v1 r where r.vendor_id=v.id),
        'minimum_charge',case when v_money then t.minimum_charge::numeric(18,2)::text end,'terms_version',coalesce(t.row_version,0)::text) order by v.vendor_name,v.id)
      from erp.laundry_vendors v left join erp.bd_laundry_vendor_terms_v1 t on t.vendor_id=v.id where v.is_active),'[]'::jsonb),
    'processes',coalesce((select jsonb_agg(jsonb_build_object('id',w.id,'code',w.process_code,'name',w.process_name) order by w.process_name,w.id)
      from erp.wash_processes w where w.is_active),'[]'::jsonb),
    'components',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'vendor_id',c.vendor_id,'code',c.component_code,'name',c.component_name,
        'is_active',c.is_active,'current',(select jsonb_build_object('status',r.rate_status,'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,
          'reason',r.reason,'version_id',r.id,'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'))
          from erp.bd_laundry_component_rates_v1 r where r.component_id=c.id and r.effective_from<=v_now and (r.effective_to is null or r.effective_to>v_now)))
        order by c.component_name,c.id)
      from erp.bd_laundry_components_v1 c where v_vendor is null or c.vendor_id=v_vendor),'[]'::jsonb),
    'packages',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'vendor_id',p.vendor_id,'code',p.package_code,'name',p.package_name,'is_active',p.is_active,
        'component_ids',(select coalesce(jsonb_agg(pc.component_id order by pc.component_id),'[]'::jsonb) from erp.bd_laundry_package_components_v1 pc where pc.package_id=p.id),
        'current_rate',(select case when v_money then r.rate_per_pcs::numeric(18,2)::text end from erp.bd_laundry_package_rates_v1 r
          where r.package_id=p.id and r.effective_from<=v_now and (r.effective_to is null or r.effective_to>v_now))) order by p.package_name,p.id)
      from erp.bd_laundry_packages_v1 p where v_vendor is null or p.vendor_id=v_vendor),'[]'::jsonb),
    'process_rates',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'vendor_id',r.vendor_id,'wash_process_id',r.wash_process_id,
        'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
        'to',to_char(r.effective_to at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) order by r.vendor_id,r.wash_process_id,r.effective_from)
      from erp.laundry_vendor_rate_versions r where (v_vendor is null or r.vendor_id=v_vendor) and (r.effective_to is null or r.effective_to>v_now - interval '120 days')),'[]'::jsonb),
    'scoped_rates',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'vendor_id',r.vendor_id,'wash_process_id',r.wash_process_id,'scope',r.scope,
        'model_id',r.model_id,'size_id',r.size_id,'color_name',r.color_name,'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,
        'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) order by r.created_at)
      from erp.bd_laundry_scoped_rates_v1 r where v_vendor is null or r.vendor_id=v_vendor),'[]'::jsonb),
    -- Amounts of a priced delivery only for money readers (quantities, labels and price status for everyone).
    'priced_deliveries',coalesce((select jsonb_agg(case when v_money then x.j else (x.j-'total_known')||jsonb_build_object(
        'charges',(select coalesce(jsonb_agg(c-'unit_rate'-'amount' order by (c->>'line_no')::integer),'[]'::jsonb) from jsonb_array_elements(x.j->'charges') c),
        'sizes',(select coalesce(jsonb_agg(s-'known_amount' order by s->>'size_id'),'[]'::jsonb) from jsonb_array_elements(x.j->'sizes') s)) end
      order by x.at desc) from (
        select erp.bd_priced_line_json_v1(p.delivery_line_id)||jsonb_build_object('delivery_number',d.delivery_number,'status',d.status,
          'physical_local',to_char(d.physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) j,d.physical_at at
        from erp.bd_laundry_priced_lines_v1 p join erp.laundry_deliveries d on d.id=p.delivery_id
        where v_vendor is null or p.vendor_id=v_vendor order by d.physical_at desc limit 50) x),'[]'::jsonb),
    -- ALL-W05: laundry work returned before cutover and not yet billed (billed later by an invoice line with opening_uninvoiced_id).
    'opening_uninvoiced',coalesce((select jsonb_agg(jsonb_build_object('id',u.id,'vendor_id',u.vendor_id,'vendor_code',v.vendor_code,
        'document_number',u.document_number,'receipt_date',u.receipt_date,'category',u.category,'qty',u.qty,'billed',erp.bd_opening_billed_v1(u.id),
        'estimate_status',case when u.estimated_amount is null then 'UNKNOWN' else 'KNOWN' end,
        'estimated_amount',case when v_money then u.estimated_amount::text end,'released',case when v_money then erp.bd_opening_released_v1(u.id)::numeric(18,2)::text end,
        'invoiced',erp.bd_opening_invoiced_v1(u.id),'po_number',(select po_number from erp.production_orders where id=u.po_id),
        'dispatch_number',u.dispatch_number,'row_version',u.row_version::text) order by u.receipt_date,u.document_number,u.category)
      from erp.bd_opening_laundry_uninvoiced_v1 u join erp.laundry_vendors v on v.id=u.vendor_id where v_vendor is null or u.vendor_id=v_vendor),'[]'::jsonb),
    -- Money readers only (null otherwise: hidden, never empty): the latest invoices and, for one vendor, the receipt lines it
    -- can still bill (capacity and billed quantity per category), and the accounts the owner may pick in LAU-DEC03/06.
    'invoices',case when v_money then v_invoice_page->'items' end,
    'billable_receipts',case when v_money and v_vendor is not null then v_receipt_page->'items' end,
    'pagination',jsonb_build_object('as_of',to_char(v_as_of at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
      'invoice_next',v_invoice_page->'next_id','receipt_next',v_receipt_page->'next_id'),
    'accounts',case when v_money then coalesce((select jsonb_agg(jsonb_build_object('id',a.id,'code',a.account_code,'name',a.account_name,'type',a.account_type)
        order by a.account_code) from erp.chart_accounts a where a.is_active and a.is_postable and a.account_type in('ASSET','EXPENSE')),'[]'::jsonb) end,
    -- D12: the payment screen of one vendor (money readers only): documents with cash, claim credit and remaining, claim credits,
    -- and the ledger check.
    'payables',case when v_money and v_vendor is not null then erp.bd_vendor_payables_v1(v_vendor) end,
    -- LAU-DEC04 ALLOW_PENDING (owner decision no. 11): goods and sales whose HPP is not final while a laundry price is unknown.
    'pending_cost',erp.bd_pending_cost_json_v1(v_vendor,v_money));
end;$function$;
CREATE OR REPLACE FUNCTION erp.save_laundry_bd_action_v1(p_action text, p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_action text:=upper(btrim(coalesce(p_action,'')));v_prior erp.bd_requests_v1%rowtype;v_result jsonb;
begin
  if erp.current_app_user_id() is null and session_user not in('postgres','supabase_admin') then raise exception 'BD_AUTH_REQUIRED: login ERP diperlukan';end if;
  if p_client_request_id is null then raise exception 'BD_REQUEST_REQUIRED: id permintaan wajib';end if;
  if jsonb_typeof(p_payload) is distinct from 'object' then raise exception 'BD_PAYLOAD_INVALID: payload wajib objek';end if;
  if v_action not in('SET_REDYE_PRICE','SET_POLICY','SAVE_VENDOR_TERMS','SAVE_COMPONENT','SAVE_COMPONENT_RATE','SAVE_PACKAGE','SAVE_PACKAGE_RATE','SAVE_PROCESS_RATE',
    'SAVE_SCOPED_RATE','SAVE_DYEING_TYPE','SET_DYEING_SKU_LINK','POST_PRICED_DELIVERY','SET_CHARGE_PRICE','SAVE_INVOICE_DRAFT','CANCEL_INVOICE_DRAFT','POST_INVOICE','REVERSE_INVOICE','SET_OPENING_ESTIMATE',
    'APPLY_CLAIM_CREDIT','PAY_VENDOR_DOCUMENT','REVERSE_VENDOR_SETTLEMENT','RECEIVE_VENDOR_REFUND','REVERSE_VENDOR_REFUND') then
    raise exception 'BD_ACTION_UNKNOWN: aksi laundry % tidak dikenal',v_action;end if;
  if v_action='SET_REDYE_PRICE' then perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');perform erp.require_permission('warehouse.brand_conversion.post');end if;
  perform pg_advisory_xact_lock(hashtextextended('BDREQ:'||p_client_request_id::text,0));
  -- Recheck live action permissions after waiting for the request lock and BEFORE any cached response.
  -- Inner commands retain their checks. Replays need the same authority as fresh commands.
  if v_action='SET_POLICY' then
    if session_user not in('postgres','supabase_admin') and erp.current_app_role() is distinct from 'OWNER' then
      raise exception 'BD_OWNER_ONLY: pengaturan kebijakan laundry hanya dapat diubah owner';end if;
    perform erp.require_permission('settings.erp.manage');
  elsif v_action='POST_PRICED_DELIVERY' then
    if erp.current_app_user_id() is null then raise exception 'BD_AUTH_REQUIRED: pengguna ERP aktif diperlukan';end if;
    perform erp.require_permission('production.laundry.post');perform erp.require_permission('production.laundry.create');
  elsif v_action in('SAVE_VENDOR_TERMS','SAVE_COMPONENT','SAVE_COMPONENT_RATE','SAVE_PACKAGE','SAVE_PACKAGE_RATE','SAVE_PROCESS_RATE','SAVE_SCOPED_RATE','SAVE_DYEING_TYPE','SET_DYEING_SKU_LINK') then
    perform erp.require_owner_admin();perform erp.require_permission('master.partner.manage');
  else
    perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  end if;
  select * into v_prior from erp.bd_requests_v1 where request_id=p_client_request_id;
  if v_prior.request_id is not null then
    if v_prior.action<>v_action or v_prior.payload<>p_payload or v_prior.actor is distinct from erp.current_app_user_id() then
      raise exception 'BD_REQUEST_REUSED: id permintaan sudah dipakai untuk isi lain';end if;
    return v_prior.response||jsonb_build_object('replayed',true);
  end if;
  v_result:=case v_action
    when 'SET_REDYE_PRICE' then erp.save_product_conversion_action_v1('SET_REDYE_PRICE',p_payload,p_client_request_id)
    when 'SET_POLICY' then erp.bd_set_policy_v1(p_payload,p_client_request_id)
    when 'SAVE_DYEING_TYPE' then erp.cp8_save_laundry_dyeing_master_v1(v_action,p_payload)
    when 'SET_DYEING_SKU_LINK' then erp.cp8_save_laundry_dyeing_master_v1(v_action,p_payload)
    when 'POST_PRICED_DELIVERY' then erp.bd_post_priced_delivery_v1(p_payload,p_client_request_id)
    when 'SET_CHARGE_PRICE' then erp.bd_set_charge_price_v1(p_payload,p_client_request_id)
    when 'SAVE_INVOICE_DRAFT' then erp.bd_save_invoice_draft_v1(p_payload,p_client_request_id)
    when 'CANCEL_INVOICE_DRAFT' then erp.bd_cancel_invoice_draft_v1(p_payload,p_client_request_id)
    when 'POST_INVOICE' then erp.bd_post_invoice_v1(p_payload,p_client_request_id)
    when 'REVERSE_INVOICE' then erp.bd_reverse_invoice_v1(p_payload,p_client_request_id)
    when 'SET_OPENING_ESTIMATE' then erp.bd_set_opening_estimate_v1(p_payload,p_client_request_id)
    when 'APPLY_CLAIM_CREDIT' then erp.bd_apply_claim_credit_v1(p_payload,p_client_request_id)
    when 'RECEIVE_VENDOR_REFUND' then cp7_vendor_receivable.refund_v1(p_payload,p_client_request_id)
    when 'REVERSE_VENDOR_REFUND' then cp7_vendor_receivable.reverse_refund_v1(p_payload,p_client_request_id)
    when 'PAY_VENDOR_DOCUMENT' then erp.bd_pay_vendor_document_v1(p_payload,p_client_request_id)
    when 'REVERSE_VENDOR_SETTLEMENT' then erp.bd_reverse_vendor_settlement_v1(p_payload,p_client_request_id)
    else erp.bd_save_master_v1(v_action,p_payload,p_client_request_id) end;
  v_result:=jsonb_build_object('action',v_action,'request_id',p_client_request_id,'status','SAVED')||v_result;
  insert into erp.bd_requests_v1(request_id,action,actor,payload,response) values(p_client_request_id,v_action,erp.current_app_user_id(),p_payload,v_result);
  return v_result;
end;$function$;
do $vendor_routine_check$
 begin
  if exists(select from (values ('erp.bd_apply_vendor_credit_v1(text,uuid,text,uuid,numeric,date,text,uuid)','490d632af17123df479fa02081595ff3965f613ccbc90d22f5877b43364273e0'),('erp.bd_claim_credit_applied_v1(text,uuid)','6def29d0c2a25e22f87e7ef9ebe338198a00a906e4b44e9c191d1bee89e70f8b'),('erp.bd_claim_credit_opening_lines_v1(uuid)','c47b44f87f089ede1c384f06d85a1cd00cd0645bd689e45c7565fa3d5805ba20'),('erp.bd_post_invoice_v1(jsonb,uuid)','a604ac9fa3bb4122cba5a1649832558eafd1bc726bb787596c181b038fed1daa'),('erp.bd_vendor_payables_v1(uuid)','008fbdefce77699dd7ca2421ee293c524f343b83631559109a267bd35e611f86'),('erp.get_laundry_bd_workspace_v1(jsonb)','1014d385389bdc4104582dded00a2c8ebcc2cf923df48e367d2adf0b089adf59'),('erp.save_laundry_bd_action_v1(text,jsonb,uuid)','b39f17ad726e2059cbebfd9ed321a6840bf39dc9821aa83df852acdb4469bdd6')) expected(sig,sha)
     left join pg_proc p on p.oid=to_regprocedure(expected.sig)
     where p.oid is null or p.proowner<>'postgres'::regrole or encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex')<>expected.sha)
     then raise exception 'Vendor AR business function differs';end if;
 end $vendor_routine_check$;
