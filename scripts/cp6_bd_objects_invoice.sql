-- ================================================================ BD laundry vendor invoices (LAU-05b, LAU-T16..T19, T21..T23)
-- A vendor invoice bills returned work after the fact. Each line bills a quantity of one category (GOOD, BS or FAILED_ATTEMPT,
-- the categories the owner makes billable in LAU-DEC02) of one posted receipt line of the same vendor, never more than that
-- line holds in the category (LAU-T19: a new request key does not reset the capacity). One invoice may bill many deliveries and
-- one receipt may be billed by many invoices (LAU-T17/T18). A line releases the estimate it replaces: its share of the receipt
-- line's estimate, and the whole rest once the billable categories of that line are fully billed (a category that is not
-- billable costs nothing). The difference between the invoice and the released estimate goes to product cost or to the owner's
-- variance account (LAU-DEC06, LAU-T16/T22). Discount, tax and a rounding line need the owner's LAU-DEC03 (LAU-T21); the header
-- total must equal the recomputed payable to the cent. A correction line (quantity 0, signed amount) changes the cost of an
-- already billed receipt line; after a payment it needs LAU-DEC06 after_payment CORRECTION_DOCUMENT. An unpaid invoice can be
-- reversed; a paid one cannot (reverse the payment first, or correct with a correction line). The payable is an ordinary
-- erp.vendor_invoices row (total >= 0), so vendor payments, AP checks and aging see it; the journal is VENDOR_INVOICE on it.
-- The receipt lines stay ESTIMATED: the released estimate and the product variance are read by accrual and HPP.

create table erp.bd_laundry_invoices_v1(
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references erp.laundry_vendors(id),
  invoice_number text not null check(length(btrim(invoice_number)) between 1 and 80),
  invoice_date date not null,
  due_date date,
  status text not null check(status in('DRAFT','POSTED','REVERSED','CANCELLED')),
  header_total numeric(18,2) not null check(header_total>=0),
  discount_amount numeric(18,2) not null default 0 check(discount_amount>=0),
  tax_amount numeric(18,2) not null default 0 check(tax_amount>=0),
  rounding_amount numeric(18,2) not null default 0 check(abs(rounding_amount)<1000),
  notes text,
  row_version bigint not null default 1,
  policy_versions jsonb,
  variance_mode text check(variance_mode in('PRODUCT_COST','VARIANCE_ACCOUNT')),
  variance_account_id uuid,
  tax_account_id uuid,
  journal_id uuid,
  reversal_journal_id uuid,
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  posted_by uuid,
  posted_at timestamptz,
  reversed_by uuid,
  reversed_at timestamptz,
  reverse_reason text
);
create unique index bd_laundry_invoices_v1_number on erp.bd_laundry_invoices_v1(vendor_id,lower(btrim(invoice_number))) where status in('DRAFT','POSTED');

create table erp.bd_laundry_invoice_lines_v1(
  id uuid primary key default gen_random_uuid(),
  invoice_id uuid not null references erp.bd_laundry_invoices_v1(id),
  line_no integer not null,
  line_kind text not null check(line_kind in('BILL','CORRECTION')),
  receipt_line_id uuid not null references erp.laundry_receipt_lines(id),
  category text not null check(category in('GOOD','BS','FAILED_ATTEMPT')),
  qty integer not null check(qty>=0),
  amount numeric(18,2) not null,
  note text,
  po_id uuid,
  discount_share numeric(18,2),
  rounding_share numeric(18,2),
  net_amount numeric(18,2),
  released_estimate numeric(18,2),
  variance numeric(18,2),
  product_variance numeric(18,2),
  completes_source boolean not null default false,
  unique(invoice_id,line_no),
  check((line_kind='BILL' and qty>0 and amount>=0) or (line_kind='CORRECTION' and qty=0 and amount<>0))
);
create index bd_laundry_invoice_lines_v1_source on erp.bd_laundry_invoice_lines_v1(receipt_line_id);

-- ---------------------------------------------------------------- source facts
-- Pieces and capacity of a receipt line per category (a failed-wash attempt line holds only FAILED_ATTEMPT).
CREATE OR REPLACE FUNCTION erp.bd_invoice_capacity_v1(p_receipt_line uuid,p_category text)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select case
    when a.id is not null then case when p_category='FAILED_ATTEMPT' then a.qty_attempted_pcs else 0 end
    when p_category='GOOD' then rl.qty_good_received
    when p_category='BS' then rl.qty_bs_laundry
    else 0 end
  from erp.laundry_receipt_lines rl left join erp.laundry_failed_wash_attempts a on a.receipt_line_id=rl.id
  where rl.id=p_receipt_line
$function$;

CREATE OR REPLACE FUNCTION erp.bd_invoice_pieces_v1(p_receipt_line uuid)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(a.qty_attempted_pcs,rl.qty_good_received+rl.qty_bs_laundry)
  from erp.laundry_receipt_lines rl left join erp.laundry_failed_wash_attempts a on a.receipt_line_id=rl.id
  where rl.id=p_receipt_line
$function$;

CREATE OR REPLACE FUNCTION erp.bd_invoice_billed_v1(p_receipt_line uuid,p_category text)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(l.qty),0)::integer from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id
  where l.receipt_line_id=p_receipt_line and l.category=p_category and l.line_kind='BILL' and i.status='POSTED'
$function$;

-- Estimate released by posted invoice lines (read by the accrual), product variance (read by HPP), and whether the source is
-- fully billed (HPP no longer pending on it).
CREATE OR REPLACE FUNCTION erp.bd_released_estimate_v1(p_receipt_line uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(l.released_estimate),0) from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id
  where l.receipt_line_id=p_receipt_line and i.status='POSTED'
$function$;

CREATE OR REPLACE FUNCTION erp.bd_product_variance_v1(p_receipt_line uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(l.product_variance),0) from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id
  where l.receipt_line_id=p_receipt_line and i.status='POSTED'
$function$;

CREATE OR REPLACE FUNCTION erp.bd_receipt_invoiced_v1(p_receipt_line uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select exists(select 1 from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id
    where l.receipt_line_id=p_receipt_line and l.completes_source and i.status='POSTED')
$function$;

-- A receipt billed by a posted invoice cannot be reversed (the baseline refuses the same for its own invoice items).
CREATE OR REPLACE FUNCTION erp.bd_guard_invoiced_receipt_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if new.status='REVERSED' and old.status is distinct from 'REVERSED' and exists(
    select 1 from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id
    join erp.laundry_receipt_lines rl on rl.id=l.receipt_line_id where rl.receipt_id=new.id and i.status='POSTED') then
    raise exception 'BD_RECEIPT_INVOICED: penerimaan laundry ini sudah ditagih invoice vendor; batalkan invoice dulu';
  end if;
  return new;
end;$function$;
create trigger bd_guard_invoiced_receipt_v1 before update of status on erp.laundry_receipts
  for each row execute function erp.bd_guard_invoiced_receipt_v1();

-- ---------------------------------------------------------------- draft
CREATE OR REPLACE FUNCTION erp.bd_invoice_lines_json_v1(p_invoice uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(jsonb_agg(jsonb_build_object('id',l.id,'line_no',l.line_no,'line_kind',l.line_kind,'receipt_line_id',l.receipt_line_id,
    'category',l.category,'qty',l.qty,'amount',l.amount::text,'note',l.note,'po_id',l.po_id,'discount_share',l.discount_share::text,
    'rounding_share',l.rounding_share::text,'net_amount',l.net_amount::text,'released_estimate',l.released_estimate::text,
    'variance',l.variance::text,'product_variance',l.product_variance::text,'completes_source',l.completes_source) order by l.line_no),'[]'::jsonb)
  from erp.bd_laundry_invoice_lines_v1 l where l.invoice_id=p_invoice
$function$;

CREATE OR REPLACE FUNCTION erp.bd_invoice_json_v1(p_invoice uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('invoice_id',i.id,'vendor_id',i.vendor_id,'invoice_number',i.invoice_number,'invoice_date',i.invoice_date,
    'due_date',i.due_date,'status',i.status,'header_total',i.header_total::text,'discount_amount',i.discount_amount::text,
    'tax_amount',i.tax_amount::text,'rounding_amount',i.rounding_amount::text,'row_version',i.row_version::text,
    'variance_mode',i.variance_mode,'policy_versions',i.policy_versions,'journal_id',i.journal_id,'reversal_journal_id',i.reversal_journal_id,
    'paid',coalesce((select sum(p.amount) from erp.vendor_payments p where p.vendor_invoice_id=i.id and p.status='POSTED'),0)::numeric(18,2)::text,
    'lines',erp.bd_invoice_lines_json_v1(i.id))
  from erp.bd_laundry_invoices_v1 i where i.id=p_invoice
$function$;

-- Create or replace a draft (lines are replaced as a whole); only shape, vendor and source are checked here. Policies and
-- capacity are checked when the invoice is posted (a draft may wait for the owner's settings).
CREATE OR REPLACE FUNCTION erp.bd_save_invoice_draft_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_id uuid;i erp.bd_laundry_invoices_v1%rowtype;v_vendor uuid;v_x jsonb;v_no integer:=0;v_rl record;v_kind text;v_qty integer;v_amount numeric;
  v_rounding numeric;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['vendor_id','invoice_number','invoice_date','header_total','lines'],
    array['invoice_id','expected_version','vendor_id','invoice_number','invoice_date','due_date','header_total','discount_amount','tax_amount',
      'rounding_amount','notes','lines'],'laundry invoice draft');
  v_id:=erp.bd_uuid_v1(p_payload,'invoice_id',false);v_vendor:=erp.bd_uuid_v1(p_payload,'vendor_id',true);
  if not exists(select 1 from erp.laundry_vendors where id=v_vendor) then raise exception 'BD_VENDOR_INACTIVE: vendor laundry tidak dikenal';end if;
  if jsonb_typeof(p_payload->'invoice_date') is distinct from 'string' or p_payload->>'invoice_date'!~'^\d{4}-\d{2}-\d{2}$' then
    raise exception 'BD_FIELD_INVALID: invoice_date wajib tanggal YYYY-MM-DD';end if;
  if p_payload ? 'due_date' and jsonb_typeof(p_payload->'due_date')<>'null' and (jsonb_typeof(p_payload->'due_date')<>'string' or p_payload->>'due_date'!~'^\d{4}-\d{2}-\d{2}$') then
    raise exception 'BD_FIELD_INVALID: due_date wajib tanggal YYYY-MM-DD';end if;
  if jsonb_typeof(p_payload->'lines') is distinct from 'array' or jsonb_array_length(p_payload->'lines') not between 1 and 200 then
    raise exception 'BD_INVOICE_LINES: invoice memuat 1-200 baris';end if;
  v_rounding:=0;
  if p_payload ? 'rounding_amount' and jsonb_typeof(p_payload->'rounding_amount')<>'null' then
    if jsonb_typeof(p_payload->'rounding_amount')<>'string' or p_payload->>'rounding_amount'!~'^-?(0|[1-9][0-9]{0,2})\.[0-9]{2}$' then
      raise exception 'BD_AMOUNT_INVALID: rounding_amount wajib nominal teks bertanda dengan tepat dua desimal, kurang dari 1000';end if;
    v_rounding:=(p_payload->>'rounding_amount')::numeric;
  end if;
  if v_id is null then
    insert into erp.bd_laundry_invoices_v1(vendor_id,invoice_number,invoice_date,due_date,status,header_total,discount_amount,tax_amount,rounding_amount,notes,created_by)
    values(v_vendor,btrim(p_payload->>'invoice_number'),(p_payload->>'invoice_date')::date,(p_payload->>'due_date')::date,'DRAFT',
      erp.bd_amount_v1(p_payload->'header_total','header_total',true),
      case when p_payload ? 'discount_amount' and jsonb_typeof(p_payload->'discount_amount')<>'null' then erp.bd_amount_v1(p_payload->'discount_amount','discount_amount',false) else 0 end,
      case when p_payload ? 'tax_amount' and jsonb_typeof(p_payload->'tax_amount')<>'null' then erp.bd_amount_v1(p_payload->'tax_amount','tax_amount',false) else 0 end,
      v_rounding,nullif(btrim(coalesce(p_payload->>'notes','')),''),erp.current_app_user_id()) returning * into i;
  else
    select * into i from erp.bd_laundry_invoices_v1 where id=v_id for update;
    if i.id is null or i.status<>'DRAFT' then raise exception 'BD_INVOICE_NOT_DRAFT: hanya draf invoice yang dapat diubah';end if;
    if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or p_payload->>'expected_version' is distinct from i.row_version::text then
      raise exception 'STALE_VERSION: draf invoice berubah; muat ulang';end if;
    update erp.bd_laundry_invoices_v1 set vendor_id=v_vendor,invoice_number=btrim(p_payload->>'invoice_number'),invoice_date=(p_payload->>'invoice_date')::date,
      due_date=(p_payload->>'due_date')::date,header_total=erp.bd_amount_v1(p_payload->'header_total','header_total',true),
      discount_amount=case when p_payload ? 'discount_amount' and jsonb_typeof(p_payload->'discount_amount')<>'null' then erp.bd_amount_v1(p_payload->'discount_amount','discount_amount',false) else 0 end,
      tax_amount=case when p_payload ? 'tax_amount' and jsonb_typeof(p_payload->'tax_amount')<>'null' then erp.bd_amount_v1(p_payload->'tax_amount','tax_amount',false) else 0 end,
      rounding_amount=v_rounding,notes=nullif(btrim(coalesce(p_payload->>'notes','')),''),row_version=row_version+1
    where id=i.id returning * into i;
    delete from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id;
  end if;
  for v_x in select value from jsonb_array_elements(p_payload->'lines') loop
    v_no:=v_no+1;
    perform erp._cp3_assert_closed_json_object(v_x,array['line_kind','receipt_line_id','category','qty','amount'],
      array['line_kind','receipt_line_id','category','qty','amount','note'],'invoice line');
    v_kind:=v_x->>'line_kind';
    if v_kind not in('BILL','CORRECTION') then raise exception 'BD_INVOICE_LINE_KIND: BILL atau CORRECTION';end if;
    if v_x->>'category' not in('GOOD','BS','FAILED_ATTEMPT') then raise exception 'BD_INVOICE_CATEGORY: GOOD, BS atau FAILED_ATTEMPT';end if;
    if jsonb_typeof(v_x->'qty') is distinct from 'number' or v_x->>'qty'!~'^(0|[1-9][0-9]{0,8})$' then raise exception 'BD_QTY_INVALID: qty wajib bilangan bulat >= 0';end if;
    v_qty:=(v_x->>'qty')::integer;
    if jsonb_typeof(v_x->'amount') is distinct from 'string' or v_x->>'amount'!~'^-?(0|[1-9][0-9]{0,15})\.[0-9]{2}$' then
      raise exception 'BD_AMOUNT_INVALID: amount wajib nominal teks dengan tepat dua desimal';end if;
    v_amount:=(v_x->>'amount')::numeric;
    if v_kind='BILL' and (v_qty<=0 or v_amount<0) then raise exception 'BD_INVOICE_LINE: baris tagih wajib qty > 0 dan nominal >= 0';end if;
    if v_kind='CORRECTION' and (v_qty<>0 or v_amount=0) then raise exception 'BD_INVOICE_LINE: baris koreksi wajib qty 0 dan nominal tidak nol';end if;
    select rl.id,d.vendor_id,d.po_id,r.status into v_rl from erp.laundry_receipt_lines rl join erp.laundry_receipts r on r.id=rl.receipt_id
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id join erp.laundry_deliveries d on d.id=dl.delivery_id
      where rl.id=erp.bd_uuid_v1(v_x,'receipt_line_id',true);
    if v_rl.id is null or v_rl.status<>'POSTED' then raise exception 'BD_INVOICE_SOURCE: sumber tagihan wajib baris penerimaan laundry POSTED';end if;
    if v_rl.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR: baris penerimaan milik vendor lain';end if;
    insert into erp.bd_laundry_invoice_lines_v1(invoice_id,line_no,line_kind,receipt_line_id,category,qty,amount,note,po_id)
    values(i.id,v_no,v_kind,v_rl.id,v_x->>'category',v_qty,v_amount,nullif(btrim(coalesce(v_x->>'note','')),''),v_rl.po_id);
  end loop;
  return erp.bd_invoice_json_v1(i.id);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bd_cancel_invoice_draft_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare i erp.bd_laundry_invoices_v1%rowtype;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['invoice_id','expected_version'],array['invoice_id','expected_version'],'cancel draft');
  select * into i from erp.bd_laundry_invoices_v1 where id=erp.bd_uuid_v1(p_payload,'invoice_id',true) for update;
  if i.id is null or i.status<>'DRAFT' then raise exception 'BD_INVOICE_NOT_DRAFT: hanya draf invoice yang dapat dibatalkan';end if;
  if p_payload->>'expected_version' is distinct from i.row_version::text then raise exception 'STALE_VERSION: draf invoice berubah; muat ulang';end if;
  update erp.bd_laundry_invoices_v1 set status='CANCELLED',row_version=row_version+1 where id=i.id;
  return erp.bd_invoice_json_v1(i.id);
end;$function$;

-- ---------------------------------------------------------------- post
CREATE OR REPLACE FUNCTION erp.bd_post_invoice_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare i erp.bd_laundry_invoices_v1%rowtype;l record;v_dec02 jsonb;v_dec03 jsonb;v_dec06 jsonb;v_versions jsonb:='{}'::jsonb;v_billable jsonb;
  v_gross numeric:=0;v_positive numeric:=0;v_payable numeric;v_weights integer[]:='{}';v_ids uuid[]:='{}';v_split numeric[];k integer;v_last uuid;
  v_pool numeric;v_pieces integer;v_prior numeric;v_released numeric;v_complete boolean;v_cap integer;v_billed integer;v_paid boolean;
  v_lines jsonb:='[]'::jsonb;v_po record;v_journal uuid;v_group uuid;v_line_ids uuid[];
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['invoice_id','expected_version'],array['invoice_id','expected_version'],'post invoice');
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
  -- Lock the sources in a fixed order (with the baseline's per-cutting-group flow lock) before reading capacity and estimates.
  for v_group in select distinct dl.cutting_group_id from erp.bd_laundry_invoice_lines_v1 x join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id where x.invoice_id=i.id order by 1 loop
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group::text,0));
  end loop;
  select array_agg(distinct x.receipt_line_id order by x.receipt_line_id) into v_line_ids from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id;
  perform 1 from erp.laundry_receipt_lines where id=any(v_line_ids) order by id for update;
  -- Discount spread over the billed amounts (largest remainder on cents); rounding on the last billing line.
  for l in select * from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id order by line_no loop
    v_gross:=v_gross+l.amount;
    if l.line_kind='BILL' then v_ids:=v_ids||l.id;v_weights:=v_weights||round(l.amount*100)::integer;v_positive:=v_positive+l.amount;v_last:=l.id;end if;
  end loop;
  if i.discount_amount>v_positive then raise exception 'BD_DISCOUNT_EXCEEDS_LINES: diskon melebihi nilai baris tagih';end if;
  update erp.bd_laundry_invoice_lines_v1 set discount_share=0,rounding_share=0 where invoice_id=i.id;
  if i.discount_amount>0 then
    if v_positive<=0 then raise exception 'BD_DISCOUNT_EXCEEDS_LINES: diskon tanpa baris tagih bernilai';end if;
    v_split:=erp.bd_split_amount_v1(i.discount_amount,v_weights);
    for k in 1..array_length(v_ids,1) loop update erp.bd_laundry_invoice_lines_v1 set discount_share=v_split[k] where id=v_ids[k];end loop;
  end if;
  if i.rounding_amount<>0 then
    if v_last is null then raise exception 'BD_ROUNDING_REFUSED: pembulatan memerlukan baris tagih';end if;
    update erp.bd_laundry_invoice_lines_v1 set rounding_share=i.rounding_amount where id=v_last;
  end if;
  v_payable:=v_gross-i.discount_amount+i.rounding_amount+i.tax_amount;
  if v_payable<>i.header_total then
    raise exception 'BD_INVOICE_TOTAL_MISMATCH: total invoice % tidak sama dengan baris - diskon + pembulatan + pajak = %',i.header_total,v_payable;end if;
  if i.header_total<=0 then raise exception 'BD_INVOICE_TOTAL_MISMATCH: total invoice harus lebih dari 0';end if;
  -- Each line in order: category billable, capacity, released estimate, variance.
  for l in select x.*,rl.actual_cost,rl.actual_cost_status,rl.delivery_line_id from erp.bd_laundry_invoice_lines_v1 x
      join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id where x.invoice_id=i.id order by x.line_no loop
    if l.actual_cost_status<>'ESTIMATED' or l.actual_cost is null then
      raise exception 'BD_INVOICE_SOURCE_NOT_ESTIMATED: baris penerimaan belum berbiaya estimasi atau sudah final (status %)',l.actual_cost_status;end if;
    if not erp.bd_line_complete_v1(l.delivery_line_id) then
      raise exception 'BD_PRICE_UNKNOWN_SET_FIRST: harga komponen kiriman ini belum diketahui; isi harganya sebelum menagih';end if;
    if not v_billable @> to_jsonb(l.category) then
      raise exception 'BD_CATEGORY_NOT_BILLABLE: LAU-DEC02 tidak menetapkan % sebagai qty yang ditagih',l.category;end if;
    -- Posted invoices plus the earlier lines of this invoice (the invoice is still DRAFT here).
    v_pool:=l.actual_cost;v_pieces:=erp.bd_invoice_pieces_v1(l.receipt_line_id);
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
      where invoice_id=i.id group by po_id order by po_id loop
    if v_dec06->>'variance_mode'='PRODUCT_COST' then
      if v_po.net<>0 then v_lines:=v_lines||jsonb_build_object('mapping_key','WIP','debit',greatest(v_po.net,0),'credit',greatest(-v_po.net,0),'po_id',v_po.po_id,'vendor_id',i.vendor_id);end if;
    else
      if v_po.rel<>0 then v_lines:=v_lines||jsonb_build_object('mapping_key','WIP','debit',v_po.rel,'credit',0,'po_id',v_po.po_id,'vendor_id',i.vendor_id);end if;
      if v_po.var<>0 then v_lines:=v_lines||jsonb_build_object('account_id',v_dec06->>'variance_account_id','debit',greatest(v_po.var,0),
        'credit',greatest(-v_po.var,0),'po_id',v_po.po_id,'vendor_id',i.vendor_id,'description','Selisih invoice laundry');end if;
    end if;
  end loop;
  if i.tax_amount>0 then v_lines:=v_lines||jsonb_build_object('account_id',v_dec03->>'tax_account_id','debit',i.tax_amount,'credit',0,'vendor_id',i.vendor_id,'description','Pajak masukan invoice laundry');end if;
  v_lines:=v_lines||jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',i.header_total,'vendor_id',i.vendor_id);
  -- The payable as an ordinary laundry vendor invoice (payments and AP checks read it).
  -- Created as DRAFT and posted by a status change, so the vendor invoice post-date guard and the receipt guard run on it.
  insert into erp.vendor_invoices(id,invoice_number,vendor_id,invoice_date,due_date,status,total_amount,notes,created_by)
  values(i.id,i.invoice_number,i.vendor_id,i.invoice_date,i.due_date,'DRAFT',i.header_total,'BD invoice laundry (LAU-05b)',erp.current_app_user_id());
  update erp.vendor_invoices set status='POSTED' where id=i.id;
  v_journal:=erp.post_journal('VENDOR_INVOICE',i.id,i.invoice_date,'Invoice vendor laundry '||i.invoice_number,v_lines);
  update erp.bd_laundry_invoices_v1 set status='POSTED',policy_versions=v_versions,variance_mode=v_dec06->>'variance_mode',
    variance_account_id=(v_dec06->>'variance_account_id')::uuid,tax_account_id=(v_dec03->>'tax_account_id')::uuid,journal_id=v_journal,
    posted_by=erp.current_app_user_id(),posted_at=statement_timestamp(),row_version=row_version+1 where id=i.id;
  perform erp.bd_invoice_resync_v1(i.id,i.invoice_date);
  return erp.bd_invoice_json_v1(i.id);
end;$function$;

-- Accrual and HPP of every PO an invoice touches, at the invoice date (a closed date is moved to the open period by the journal).
CREATE OR REPLACE FUNCTION erp.bd_invoice_resync_v1(p_invoice uuid,p_date date)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_po uuid;
begin
  for v_po in select distinct po_id from erp.bd_laundry_invoice_lines_v1 where invoice_id=p_invoice order by 1 loop
    perform erp.sync_laundry_accrual(v_po,p_date);
    if exists(select 1 from erp.fg_lots where po_id=v_po) then
      perform erp.rebuild_po_hpp(v_po,'BD laundry vendor invoice');
      perform erp.propagate_conversion_hpp_for_po(v_po);
      perform erp.sync_po_hpp_to_gl(v_po,p_date);
    end if;
  end loop;
end;$function$;

-- ---------------------------------------------------------------- reverse (unpaid only)
CREATE OR REPLACE FUNCTION erp.bd_reverse_invoice_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare i erp.bd_laundry_invoices_v1%rowtype;v_reason text:=nullif(btrim(p_payload->>'reason'),'');v_rev uuid;v_group uuid;v_line_ids uuid[];
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['invoice_id','expected_version','reason'],array['invoice_id','expected_version','reason'],'reverse invoice');
  if v_reason is null then raise exception 'BD_REASON_REQUIRED: alasan wajib diisi';end if;
  select * into i from erp.bd_laundry_invoices_v1 where id=erp.bd_uuid_v1(p_payload,'invoice_id',true) for update;
  if i.id is null or i.status<>'POSTED' then raise exception 'BD_INVOICE_NOT_POSTED: hanya invoice POSTED yang dapat dibatalkan';end if;
  if p_payload->>'expected_version' is distinct from i.row_version::text then raise exception 'STALE_VERSION: invoice berubah; muat ulang';end if;
  perform 1 from erp.vendor_invoices where id=i.id for update;
  if exists(select 1 from erp.vendor_payments p where p.vendor_invoice_id=i.id and p.status='POSTED') then
    raise exception 'BD_INVOICE_PAID: invoice sudah dibayar; batalkan pembayaran dulu, atau koreksi dengan baris koreksi bila LAU-DEC06 mengizinkan';end if;
  for v_group in select distinct dl.cutting_group_id from erp.bd_laundry_invoice_lines_v1 x join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id where x.invoice_id=i.id order by 1 loop
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group::text,0));
  end loop;
  select array_agg(distinct x.receipt_line_id order by x.receipt_line_id) into v_line_ids from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id;
  perform 1 from erp.laundry_receipt_lines where id=any(v_line_ids) order by id for update;
  -- A later invoice that completed the same source took the residual after this one; reverse that one first.
  if exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
      where y.status='POSTED' and y.id<>i.id and x.receipt_line_id=any(v_line_ids) and y.posted_at>i.posted_at) then
    raise exception 'BD_LATER_INVOICE_EXISTS: invoice lain yang diposting sesudahnya menagih sumber yang sama; batalkan yang terbaru dulu';end if;
  v_rev:=erp.reverse_journal(i.journal_id,'Batal invoice laundry: '||v_reason);
  update erp.vendor_invoices set status='REVERSED' where id=i.id;
  update erp.bd_laundry_invoices_v1 set status='REVERSED',reversal_journal_id=v_rev,reversed_by=erp.current_app_user_id(),reversed_at=statement_timestamp(),
    reverse_reason=v_reason,row_version=row_version+1 where id=i.id;
  perform erp.bd_invoice_resync_v1(i.id,(statement_timestamp() at time zone 'Asia/Jakarta')::date);
  return erp.bd_invoice_json_v1(i.id);
end;$function$;
