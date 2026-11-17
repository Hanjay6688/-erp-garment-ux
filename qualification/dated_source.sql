create function cp7_vendor_receivable.source_journal_deltas_v1(p_vendor uuid,p_correction uuid)
returns table(correction_id uuid,account_id uuid,vendor_id uuid,journal_id uuid,delta numeric)
language sql stable security definer set search_path=''as $$
 with selected as materialized (
  select s.correction_id,s.account_id,s.vendor_id,s.amount from cp7_vendor_receivable.sources_v1 s
   where s.vendor_id=p_vendor and (p_correction is null or s.correction_id=p_correction)),
 expected as(
  select s.correction_id,s.account_id,s.vendor_id,i.journal_id,s.amount delta from selected s
   join erp.bd_laundry_invoices_v1 i on i.id=s.correction_id
  union all
  select s.correction_id,s.account_id,s.vendor_id,j.id,-a.amount from selected s
   join erp.bd_claim_credit_applications_v1 a on a.correction_invoice_id=s.correction_id and a.source_kind='INVOICE_CORRECTION'
   left join erp.journal_entries j on j.source_id=coalesce(a.vendor_payment_id,a.opening_settlement_id)and j.reversal_of_id is null
    and (p_correction is null or j.source_type=case a.target_kind when 'VENDOR_INVOICE' then 'VENDOR_PAYMENT'
                                                       when 'OPENING_PAYABLE' then 'OPENING_SUBLEDGER_SETTLEMENT' end)
  union all
  select s.correction_id,s.account_id,s.vendor_id,r.journal_id,-r.amount from selected s
   join cp7_vendor_receivable.refunds_v1 r on r.correction_id=s.correction_id)
 select * from expected
 union all
 select e.correction_id,e.account_id,e.vendor_id,j.id,-e.delta from expected e
  join erp.journal_entries j on j.reversal_of_id=e.journal_id
$$;

create or replace function cp7_vendor_receivable.prove_v1(p_vendor uuid)returns void
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
 if exists(with observed as(select l.account_id,l.vendor_id,l.journal_entry_id,sum(l.debit-l.credit)delta,count(*)n
  from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
  where (l.vendor_id=p_vendor or not exists(
    select 1 from cp7_vendor_receivable.sources_v1 owner_source
    where owner_source.account_id=l.account_id and owner_source.vendor_id=l.vendor_id))
   and j.status in('POSTED','REVERSED')
   and l.account_id in(select account_id from cp7_vendor_receivable.sources_v1 where vendor_id=p_vendor)
  group by l.account_id,l.vendor_id,l.journal_entry_id)
 select 1 from cp7_vendor_receivable.source_journal_deltas_v1(p_vendor,null) e
  full join observed o on o.account_id=e.account_id and o.vendor_id=e.vendor_id and o.journal_entry_id=e.journal_id
 where e.journal_id is null or o.journal_entry_id is null or o.delta<>e.delta or o.n<>1)then
  raise exception 'CP7_VENDOR_RECEIVABLE_MATERIALIZATION_UNPROVEN';end if;
end $$;

create function cp7_vendor_receivable.assert_source_debit_v1(p_kind text,p_source uuid,p_date date,p_amount numeric)
returns void language plpgsql volatile security definer set search_path=''as $$
declare s cp7_vendor_receivable.sources_v1%rowtype;v_book date;
begin
 if p_kind is distinct from 'INVOICE_CORRECTION'then return;end if;
 select * into s from cp7_vendor_receivable.sources_v1 where correction_id=p_source;
 if not found then return;end if;
 -- The caller has locked the correction and its target. Hold the same period
 -- lock as Native posting before resolving the book date or allocating audit rows.
 perform 1 from erp.accounting_period_control where singleton_id=1 for share;
 perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
 v_book:=erp.resolve_accounting_transaction_date(p_date);
 if not exists(select 1 from erp.bd_laundry_invoices_v1 i
  join erp.journal_entries j on j.id=i.journal_id
  join erp.journal_lines l on l.journal_entry_id=j.id
  where i.id=s.correction_id and i.vendor_id=s.vendor_id and i.status='POSTED'
   and i.corrects_invoice_id is not null and i.invoice_date=s.economic_date and i.header_total=-s.amount
   and j.source_type='BD_LAUNDRY_CORRECTION_CREDIT' and j.source_id=i.id and j.status='POSTED'
   and j.economic_date=s.economic_date and l.account_id=s.account_id and l.vendor_id=s.vendor_id
   and l.debit=s.amount and l.credit=0)then
  raise exception 'CP7_VENDOR_RECEIVABLE_SOURCE_CHANGED';
 end if;
 -- Keep the original REVERSED entry and its linked inverse on their own dates.
 -- A debit must fit the selected source at its day and all later cutoffs.
 if exists(with dated as(
  select d.axis,d.on_day,e.delta from cp7_vendor_receivable.source_journal_deltas_v1(s.vendor_id,p_source) e
   join erp.journal_entries j on j.id=e.journal_id and j.status in('POSTED','REVERSED')
   cross join lateral (values ('ECONOMIC',j.economic_date),('BOOK',j.transaction_date)) d(axis,on_day)
  union all select 'ECONOMIC',p_date,-p_amount
  union all select 'BOOK',v_book,-p_amount),
 daily as(select axis,on_day,sum(delta) delta from dated group by axis,on_day),
 running as(select axis,on_day,sum(delta)over(partition by axis order by on_day)balance from daily)
 select 1 from running where balance<0 and on_day>=case axis when 'ECONOMIC' then p_date else v_book end)then
  raise exception 'CP7_VENDOR_RECEIVABLE_NEGATIVE_DATED: saldo piutang vendor tidak cukup pada tanggal ekonomi atau tanggal buku';
 end if;
end $$;

create or replace function cp7_vendor_receivable.refund_v1(p_payload jsonb,p_request uuid)returns jsonb
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
 perform cp7_vendor_receivable.assert_source_debit_v1('INVOICE_CORRECTION',s.correction_id,d,a);
 j:=erp.post_journal('CP7_VENDOR_RECEIVABLE_REFUND',p_request,d,'Pengembalian vendor untuk '||i.invoice_number||': '||why,
  jsonb_build_array(jsonb_build_object('account_id',coa,'debit',a,'credit',0,'vendor_id',s.vendor_id),
   jsonb_build_object('account_id',s.account_id,'debit',0,'credit',a,'vendor_id',s.vendor_id)));
 insert into cp7_vendor_receivable.refunds_v1(id,correction_id,amount,cash_account_id,economic_date,reason,journal_id,actor)
 values(p_request,s.correction_id,a,c,d,why,j,erp.current_app_user_id());
 perform cp7_vendor_receivable.check_dates_v1(s.vendor_id);
 return jsonb_build_object('refund_id',p_request,'source_id',s.correction_id,'journal_id',j,'amount',a::numeric(18,2)::text,
  'remaining',(left_amount-a)::numeric(18,2)::text);
end $$;
