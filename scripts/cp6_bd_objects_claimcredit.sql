-- ================================================================ D12 (owner 26 Sep 2026): a laundry claim credit settles unpaid
-- documents of the same vendor, older ones included. Example: invoice January 10,000,000; reject February; claim approved April
-- 2,000,000; cash April 8,000,000: the January invoice is paid by 8,000,000 cash plus 2,000,000 claim credit, with no phantom
-- remaining and no credit used twice, and nothing dated January changes.
-- Accounting: the claim approval keeps its own journal on its own date (daily claim: baseline LAUNDRY_CLAIM_SETTLEMENT; opening
-- claim: BD_OPENING_LAUNDRY_CLAIM; both AP_VENDOR Dr / OTHER_EXPENSE Cr), so the vendor's payable falls on the approval date.
-- Applying the credit to a document is the document's settlement on the application date:
--   * a daily vendor invoice: a vendor payment with method CLAIM_CREDIT (no cash account) whose journal is AP_VENDOR Dr / AP_VENDOR
--     Cr for the vendor (the payable already fell at approval), so the invoice's paid amount, remaining and PAID status follow the
--     same rules as a cash payment (V2620C status check, business date check V2620Y, reverse_vendor_payment);
--   * an opening vendor payable: an opening subledger settlement with a VENDOR_CLAIM_APPLY credit (AP_VENDOR Dr / AP_VENDOR Cr), so
--     the settled amount and status follow the BB rules (V2620M, dated floor).
-- The credit left to use is the compensation less the applications whose payment/settlement is still POSTED. A claim whose
-- credit is in use cannot be reversed; reversing the application (its payment or settlement) frees the credit again.
-- Per vendor: AP_VENDOR on the ledger = remaining of the open documents - credit not yet applied (bd_vendor_payables_v1).
-- Owner decision no. 13 (26 Sep 2026): a downward invoice correction document (scripts/cp6_bd_objects_invoice.sql) is a vendor
-- credit of the same kind (source INVOICE_CORRECTION; vendor payment method CORRECTION_CREDIT; opening credit kind
-- VENDOR_CORRECTION_APPLY); it first settles its origin invoice, the rest is applied like a claim credit.

alter table erp.bb_opening_credits_v1 drop constraint bb_opening_credits_v1_credit_kind_check;
alter table erp.bb_opening_credits_v1 add constraint bb_opening_credits_v1_credit_kind_check
  check(credit_kind in('CUSTOMER_ALLOWANCE','SUPPLIER_ALLOWANCE','VENDOR_ALLOWANCE','CUSTOMER_CREDIT_APPLY','ACCESSORY_NOTE_RETURN','VENDOR_CLAIM_APPLY',
    'VENDOR_CORRECTION_APPLY'));

create table erp.bd_claim_credit_applications_v1(
  id uuid primary key,
  vendor_id uuid not null references erp.laundry_vendors(id),
  source_kind text not null check(source_kind in('DAILY_CLAIM','OPENING_CLAIM','INVOICE_CORRECTION')),
  laundry_claim_id uuid references erp.laundry_claims(id),
  opening_claim_event_id uuid references erp.bd_opening_laundry_claim_events_v1(id),
  correction_invoice_id uuid references erp.bd_laundry_invoices_v1(id),
  target_kind text not null check(target_kind in('VENDOR_INVOICE','OPENING_PAYABLE')),
  vendor_payment_id uuid unique references erp.vendor_payments(id),
  opening_settlement_id uuid unique references erp.opening_subledger_settlements(id),
  amount numeric(18,2) not null check(amount>0),
  applied_date date not null,
  reason text not null check(length(btrim(reason))>0),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  check((source_kind='DAILY_CLAIM')=(laundry_claim_id is not null) and (source_kind='OPENING_CLAIM')=(opening_claim_event_id is not null)
    and (source_kind='INVOICE_CORRECTION')=(correction_invoice_id is not null)),
  check((target_kind='VENDOR_INVOICE')=(vendor_payment_id is not null) and (target_kind='OPENING_PAYABLE')=(opening_settlement_id is not null))
);
create index bd_claim_credit_applications_v1_daily on erp.bd_claim_credit_applications_v1(laundry_claim_id);
create index bd_claim_credit_applications_v1_opening on erp.bd_claim_credit_applications_v1(opening_claim_event_id);
create index bd_claim_credit_applications_v1_correction on erp.bd_claim_credit_applications_v1(correction_invoice_id);
create index bd_claim_credit_applications_v1_vendor on erp.bd_claim_credit_applications_v1(vendor_id);
comment on table erp.bd_claim_credit_applications_v1 is 'D12: a laundry claim credit (or a downward invoice correction credit, decision no. 13) applied to one unpaid document of the same vendor; active while its vendor payment or opening settlement is POSTED.';

-- Credit of one claim already applied (applications whose payment or settlement is still POSTED).
CREATE OR REPLACE FUNCTION erp.bd_claim_credit_applied_v1(p_kind text,p_id uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(a.amount),0)::numeric(18,2) from erp.bd_claim_credit_applications_v1 a
  left join erp.vendor_payments p on p.id=a.vendor_payment_id
  left join erp.opening_subledger_settlements s on s.id=a.opening_settlement_id
  where a.source_kind=p_kind and (case p_kind when 'DAILY_CLAIM' then a.laundry_claim_id when 'OPENING_CLAIM' then a.opening_claim_event_id
      else a.correction_invoice_id end)=p_id
    and coalesce(p.status,s.status)='POSTED'
$function$;

-- One claim credit: vendor, compensation, approval date, claim number and whether it can be used (approved, not reversed).
CREATE OR REPLACE FUNCTION erp.bd_claim_credit_source_v1(p_kind text,p_id uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select case p_kind
    when 'DAILY_CLAIM' then (select jsonb_build_object('kind',p_kind,'id',c.id,'vendor_id',c.vendor_id,'number',c.claim_number,
        'amount',c.compensation_amount::numeric(18,2)::text,'approved_date',c.resolution_date,
        'active',c.status='SETTLED' and c.compensation_amount>0 and exists(select 1 from erp.journal_entries j
          where j.source_type='LAUNDRY_CLAIM_SETTLEMENT' and j.source_id=c.id and j.status='POSTED'))
      from erp.laundry_claims c where c.id=p_id)
    when 'OPENING_CLAIM' then (select jsonb_build_object('kind',p_kind,'id',e.id,'vendor_id',oc.vendor_id,'number',oc.claim_number,
        'amount',e.compensation_amount::numeric(18,2)::text,'approved_date',e.event_date,
        'active',e.event_kind='RESOLVE' and e.reversed_at is null and e.compensation_amount>0 and e.journal_id is not null)
      from erp.bd_opening_laundry_claim_events_v1 e join erp.bd_opening_laundry_claims_v1 oc on oc.id=e.claim_id where e.id=p_id)
    when 'INVOICE_CORRECTION' then (select jsonb_build_object('kind',p_kind,'id',i.id,'vendor_id',i.vendor_id,'number',i.invoice_number,
        'amount',(-i.header_total)::numeric(18,2)::text,'approved_date',i.invoice_date,'corrects',o.invoice_number,
        'active',i.status='POSTED' and i.header_total<0 and i.corrects_invoice_id is not null)
      from erp.bd_laundry_invoices_v1 i join erp.bd_laundry_invoices_v1 o on o.id=i.corrects_invoice_id where i.id=p_id)
  end
$function$;

-- The journal lines of an opening settlement that applies a claim credit: the vendor's payable already fell when the claim was
-- approved, so the settlement moves nothing on the ledger (AP_VENDOR Dr and Cr for the same vendor) and only settles the document.
CREATE OR REPLACE FUNCTION erp.bd_claim_credit_opening_lines_v1(p_settlement_id uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare s erp.opening_subledger_settlements%rowtype;b erp.opening_subledger_balances%rowtype;
begin
  select * into s from erp.opening_subledger_settlements where id=p_settlement_id;
  select * into b from erp.opening_subledger_balances where id=s.balance_id;
  if b.party_type<>'VENDOR' or b.direction<>'PAYABLE' then
    raise exception 'BB_CREDIT_KIND_MISMATCH: kredit klaim/koreksi laundry hanya untuk hutang vendor laundry';end if;
  if not exists(select 1 from erp.bd_claim_credit_applications_v1 a where a.opening_settlement_id=s.id and a.vendor_id=b.vendor_id) then
    raise exception 'BD_CLAIM_CREDIT_SOURCE_MISSING: pemakaian kredit klaim tanpa klaim sumber';end if;
  return jsonb_build_array(
    jsonb_build_object('mapping_key','AP_VENDOR','debit',s.amount,'credit',0,'vendor_id',b.vendor_id),
    jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',s.amount,'vendor_id',b.vendor_id));
end;$function$;

-- Paid amount of one daily vendor invoice: all (null), cash (CASH: every other method), claim credit or correction credit.
CREATE OR REPLACE FUNCTION erp.bd_vendor_invoice_paid_v1(p_invoice uuid,p_method text)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(p.amount),0)::numeric(18,2) from erp.vendor_payments p
  where p.vendor_invoice_id=p_invoice and p.status='POSTED'
    and (p_method is null or p_method=case when p.payment_method in('CLAIM_CREDIT','CORRECTION_CREDIT') then p.payment_method else 'CASH' end)
$function$;

-- The payment screen's credit application: owner/admin with finance rights; a claim credit or a downward correction credit.
CREATE OR REPLACE FUNCTION erp.bd_apply_claim_credit_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_kind text;v_target_kind text;v_reason text;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['source_kind','source_id','target_kind','target_id','amount','date','reason'],
    array['source_kind','source_id','target_kind','target_id','amount','date','reason'],'claim credit payload');
  v_kind:=p_payload->>'source_kind';v_target_kind:=p_payload->>'target_kind';
  if v_kind is null or v_kind not in('DAILY_CLAIM','OPENING_CLAIM','INVOICE_CORRECTION') then
    raise exception 'BD_FIELD_INVALID: source_kind DAILY_CLAIM, OPENING_CLAIM atau INVOICE_CORRECTION';end if;
  if v_target_kind is null or v_target_kind not in('VENDOR_INVOICE','OPENING_PAYABLE') then raise exception 'BD_FIELD_INVALID: target_kind VENDOR_INVOICE atau OPENING_PAYABLE';end if;
  v_reason:=nullif(btrim(p_payload->>'reason'),'');
  if v_reason is null or length(v_reason)<4 then raise exception 'BD_REASON_REQUIRED: alasan minimal 4 karakter';end if;
  return erp.bd_apply_vendor_credit_v1(v_kind,erp.bd_uuid_v1(p_payload,'source_id',true),v_target_kind,erp.bd_uuid_v1(p_payload,'target_id',true),
    erp.bb_parse_amount_v1(p_payload->>'amount','amount'),erp.bb_parse_date_v1(p_payload->>'date','date'),v_reason,p_request);
end;$function$;

-- One application of a vendor credit (claim or downward correction) to one unpaid document of the same vendor. Callers check
-- the actor; the correction poster uses it to settle the origin invoice at once. The credit's own row is the lock: two uses of
-- one credit wait for each other and the second sees the first.
CREATE OR REPLACE FUNCTION erp.bd_apply_vendor_credit_v1(p_kind text,p_source uuid,p_target_kind text,p_target uuid,p_amount numeric,p_date date,
  p_reason text,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
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
      jsonb_build_array(jsonb_build_object('mapping_key','AP_VENDOR','debit',p_amount,'credit',0,'vendor_id',v_vendor),
        jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',p_amount,'vendor_id',v_vendor)));
    update erp.vendor_payments set status='POSTED' where id=p_request;
    v_paid:=erp.bd_vendor_invoice_paid_v1(h.id,null);
    update erp.vendor_invoices set status=case when v_paid=total_amount then 'PAID' else 'PARTIAL_PAID' end,updated_at=statement_timestamp() where id=h.id;
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
  return jsonb_build_object('application_id',p_request,'target_kind',p_target_kind,'target_id',b.id,'document_number',ctx->>'document_number',
    'amount',p_amount::text,'remaining',(b.original_amount-b.settled_amount)::numeric(18,2)::text,'credit_left',(v_available-p_amount)::numeric(18,2)::text);
end;$function$;

-- Cash payment of one vendor document from the payment screen: a daily invoice through the baseline vendor payment poster, an
-- opening payable through the BB opening settlement (same checks as the import page).
CREATE OR REPLACE FUNCTION erp.bd_pay_vendor_document_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_kind text;v_target uuid;v_amount numeric;v_date date;v_reason text;v_cash uuid;h erp.vendor_invoices%rowtype;ctx jsonb;v_paid numeric;v_result jsonb;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['target_kind','target_id','amount','date','cash_account_id','reason'],
    array['target_kind','target_id','amount','date','cash_account_id','reason'],'vendor payment payload');
  v_kind:=p_payload->>'target_kind';v_target:=erp.bd_uuid_v1(p_payload,'target_id',true);
  v_amount:=erp.bb_parse_amount_v1(p_payload->>'amount','amount');v_date:=erp.bb_parse_date_v1(p_payload->>'date','date');
  v_reason:=nullif(btrim(p_payload->>'reason'),'');
  if v_reason is null or length(v_reason)<4 then raise exception 'BD_REASON_REQUIRED: alasan minimal 4 karakter';end if;
  select id into v_cash from erp.cash_accounts where id=erp.bd_uuid_v1(p_payload,'cash_account_id',true) and is_active;
  if v_cash is null then raise exception 'BD_CASH_ACCOUNT_REQUIRED: pilih rekening kas/bank aktif';end if;
  if v_date>erp.bb_business_today_v1() then raise exception 'BD_DATE_FUTURE: tanggal pembayaran di masa depan';end if;
  if v_kind='VENDOR_INVOICE' then
    select * into h from erp.vendor_invoices where id=v_target for update;
    if h.id is null then raise exception 'BD_DOCUMENT_NOT_FOUND: invoice vendor tidak ditemukan';end if;
    if not exists(select 1 from erp.laundry_vendors where id=h.vendor_id) then raise exception 'BD_DOCUMENT_NOT_FOUND: bukan invoice vendor laundry';end if;
    if v_date<h.invoice_date then raise exception 'BD_DATE_BEFORE_DOCUMENT: pembayaran tidak boleh sebelum tanggal invoice %',h.invoice_date;end if;
    insert into erp.vendor_payments(id,vendor_invoice_id,payment_number,payment_date,amount,cash_account_id,payment_method,status,notes,created_by)
    values(p_request,h.id,'VP-'||upper(substr(replace(p_request::text,'-',''),1,16)),erp.bb_physical_at_v1(v_date),v_amount,v_cash,'CASH','DRAFT',v_reason,
      erp.current_app_user_id());
    perform erp.post_vendor_payment(p_request);
    v_paid:=erp.bd_vendor_invoice_paid_v1(h.id,null);
    return jsonb_build_object('payment_id',p_request,'target_kind',v_kind,'target_id',h.id,'document_number',h.invoice_number,'amount',v_amount::text,
      'remaining',(h.total_amount-v_paid)::numeric(18,2)::text);
  elsif v_kind='OPENING_PAYABLE' then
    if not exists(select 1 from erp.opening_subledger_balances where id=v_target and party_type='VENDOR' and direction='PAYABLE') then
      raise exception 'BD_DOCUMENT_NOT_FOUND: hutang vendor saldo awal tidak ditemukan';end if;
    ctx:=erp.bb_opening_balance_context_v1(v_target);
    v_result:=erp.bb_manage_opening_settlement_v1(jsonb_build_object('operation','SETTLE','batch_id',ctx->>'batch_id','balance_id',v_target,
      'amount',v_amount::text,'effective_date',v_date::text,'cash_account_id',v_cash,'reason',v_reason),p_request);
    return jsonb_build_object('payment_id',p_request,'target_kind',v_kind,'target_id',v_target,'document_number',ctx->>'document_number',
      'amount',v_amount::text,'remaining',v_result->>'remaining');
  end if;
  raise exception 'BD_FIELD_INVALID: target_kind VENDOR_INVOICE atau OPENING_PAYABLE';
end;$function$;

-- Reverses a cash payment or a claim credit application of a laundry vendor document (the credit is free again).
CREATE OR REPLACE FUNCTION erp.bd_reverse_vendor_settlement_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_kind text;v_id uuid;v_reason text;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['target_kind','settlement_id','reason'],array['target_kind','settlement_id','reason'],
    'vendor settlement reversal payload');
  v_kind:=p_payload->>'target_kind';v_id:=erp.bd_uuid_v1(p_payload,'settlement_id',true);v_reason:=nullif(btrim(p_payload->>'reason'),'');
  if v_reason is null or length(v_reason)<4 then raise exception 'BD_REASON_REQUIRED: alasan minimal 4 karakter';end if;
  if v_kind='VENDOR_INVOICE' then
    if not exists(select 1 from erp.vendor_payments p join erp.vendor_invoices h on h.id=p.vendor_invoice_id
        join erp.laundry_vendors v on v.id=h.vendor_id where p.id=v_id) then raise exception 'BD_DOCUMENT_NOT_FOUND: pembayaran vendor laundry tidak ditemukan';end if;
    perform erp.reverse_vendor_payment(v_id,v_reason);
  elsif v_kind='OPENING_PAYABLE' then
    if not exists(select 1 from erp.opening_subledger_settlements s join erp.opening_subledger_balances b on b.id=s.balance_id
        where s.id=v_id and b.party_type='VENDOR' and b.direction='PAYABLE') then
      raise exception 'BD_DOCUMENT_NOT_FOUND: pelunasan hutang vendor saldo awal tidak ditemukan';end if;
    perform erp.reverse_opening_subledger_settlement(v_id,v_reason);
  else raise exception 'BD_FIELD_INVALID: target_kind VENDOR_INVOICE atau OPENING_PAYABLE';end if;
  return jsonb_build_object('settlement_id',v_id,'target_kind',v_kind,'status','REVERSED');
end;$function$;

-- The payment screen of one laundry vendor: documents with cash, claim credit and remaining; claim credits with what is left;
-- and the ledger check (AP_VENDOR on the ledger = remaining of the open documents - credit not yet applied).
CREATE OR REPLACE FUNCTION erp.bd_vendor_payables_v1(p_vendor uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
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
  select jsonb_build_object('vendor_id',p_vendor,
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
      from ledger l))
$function$;

-- A claim whose credit is in use cannot lose its approval (daily claim reversal or opening claim event reversal).
CREATE OR REPLACE FUNCTION erp.bd_guard_claim_credit_in_use_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if tg_table_name='laundry_claims' then
    if old.status='SETTLED' and (new.status is distinct from 'SETTLED' or new.compensation_amount is distinct from old.compensation_amount)
      and erp.bd_claim_credit_applied_v1('DAILY_CLAIM',old.id)>0 then
      raise exception 'BD_CLAIM_CREDIT_IN_USE: kredit klaim % sudah dipakai untuk melunasi tagihan; batalkan pemakaiannya dulu',old.claim_number;end if;
  elsif old.reversed_at is null and new.reversed_at is not null and erp.bd_claim_credit_applied_v1('OPENING_CLAIM',old.id)>0 then
    raise exception 'BD_CLAIM_CREDIT_IN_USE: kredit klaim ini sudah dipakai untuk melunasi tagihan; batalkan pemakaiannya dulu';
  end if;
  return new;
end;$function$;
create trigger trg_bd_claim_credit_in_use_daily before update on erp.laundry_claims
  for each row execute function erp.bd_guard_claim_credit_in_use_v1();
create trigger trg_bd_claim_credit_in_use_opening before update on erp.bd_opening_laundry_claim_events_v1
  for each row execute function erp.bd_guard_claim_credit_in_use_v1();
