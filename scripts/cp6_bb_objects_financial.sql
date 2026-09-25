-- CP6 BB financial part (ALL-P02/S01/S03/A03/Y01 and the opening settlement facade). New objects only; the functions this
-- part changes are rebuilt by scripts/cp6_bb_build.py from their current definitions with checked substitutions.
-- Nothing here reconstructs a pre-cutover sale, purchase, payment or wage (M:369-379, M:930-938): old documents stay
-- provenance, every new fact is dated on or after cutover and posts through the canonical journal.

-- ---------------------------------------------------------------- tables
create table erp.bb_legacy_documents_v1(
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references erp.migration_batches(id),
  source_row_id uuid not null unique references erp.migration_staging_rows(id),
  balance_type text not null check(balance_type in('CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE')),
  party_id uuid not null,
  document_number text not null check(length(btrim(document_number)) between 1 and 120),
  document_date date not null,
  cutover_date date not null,
  original_amount numeric(20,2) not null check(original_amount>0),
  settled_before_cutover numeric(20,2) not null,
  notes text,
  created_at timestamptz not null default statement_timestamp(),
  check(settled_before_cutover=original_amount),
  check(document_date<=cutover_date)
);
create unique index bb_legacy_documents_v1_identity on erp.bb_legacy_documents_v1(balance_type,party_id,lower(btrim(document_number)));
comment on table erp.bb_legacy_documents_v1 is 'BB (ALL-A03): a document fully settled before cutover, kept only as provenance so a later return can name it and its number cannot be imported again as an open balance. No opening item, balance, journal or cash event.';

create table erp.bb_customer_credits_v1(
  id uuid primary key default gen_random_uuid(),
  origin text not null check(origin in('IMPORTED','RETURN')),
  batch_id uuid not null references erp.migration_batches(id),
  source_row_id uuid unique references erp.migration_staging_rows(id),
  return_receipt_id uuid unique,
  customer_id uuid not null references erp.customers(id),
  coa_account_id uuid not null references erp.chart_accounts(id),
  document_number text not null check(length(btrim(document_number)) between 1 and 160),
  document_date date not null,
  original_amount numeric(20,2) not null check(original_amount>0),
  settled_before_cutover numeric(20,2) not null default 0 check(settled_before_cutover>=0),
  amount numeric(20,2) not null check(amount>0),
  effective_date date not null,
  journal_entry_id uuid references erp.journal_entries(id),
  voided_at timestamptz,
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  check(original_amount-settled_before_cutover=amount),
  check(voided_at is null or origin='RETURN'),
  check((origin='IMPORTED')=(source_row_id is not null)),
  check((origin='RETURN')=(return_receipt_id is not null))
);
create unique index bb_customer_credits_v1_document on erp.bb_customer_credits_v1(customer_id,lower(btrim(document_number)));
comment on table erp.bb_customer_credits_v1 is 'BB (ALL-S03): money owed to a customer for a return. IMPORTED: a return already received before cutover whose refund was still open (Dr OPENING_EQUITY / Cr the credit account). RETURN: the credit of a return of an old sale received after cutover (Dr SALES_REVENUE / Cr the credit account). Used only by refund or by applying it to an open opening receivable of the same customer.';

create table erp.bb_customer_credit_events_v1(
  id uuid primary key,
  credit_id uuid not null references erp.bb_customer_credits_v1(id),
  event_type text not null check(event_type in('REFUND','APPLY_OPENING_AR')),
  amount numeric(20,2) not null check(amount>0),
  effective_date date not null,
  cash_account_id uuid references erp.cash_accounts(id),
  settlement_id uuid unique references erp.opening_subledger_settlements(id),
  journal_entry_id uuid references erp.journal_entries(id),
  reason text not null check(length(btrim(reason))>0),
  reversed_at timestamptz,
  reversal_reason text,
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  check((event_type='REFUND')=(cash_account_id is not null and journal_entry_id is not null)),
  check((event_type='APPLY_OPENING_AR')=(settlement_id is not null)),
  check((reversed_at is null)=(reversal_reason is null))
);
create index bb_customer_credit_events_v1_credit on erp.bb_customer_credit_events_v1(credit_id);

create table erp.bb_opening_sale_return_rights_v1(
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references erp.migration_batches(id),
  source_row_id uuid not null unique references erp.migration_staging_rows(id),
  customer_id uuid not null references erp.customers(id),
  return_number text not null check(length(btrim(return_number)) between 1 and 120),
  invoice_document_number text not null,
  invoice_source_id uuid references erp.initial_import_financial_sources(id),
  legacy_document_id uuid references erp.bb_legacy_documents_v1(id),
  product_id uuid not null references erp.products(id),
  qty_pcs integer not null check(qty_pcs>0),
  credit_unit_price numeric(18,2) not null check(credit_unit_price>=0),
  unit_cost numeric(18,2) not null check(unit_cost>=0),
  credit_coa_account_id uuid not null references erp.chart_accounts(id),
  cutover_date date not null,
  created_at timestamptz not null default statement_timestamp(),
  check(num_nonnulls(invoice_source_id,legacy_document_id)=1)
);
create unique index bb_opening_sale_return_rights_v1_number on erp.bb_opening_sale_return_rights_v1(customer_id,lower(btrim(return_number)));
comment on table erp.bb_opening_sale_return_rights_v1 is 'BB (ALL-S03): the right, agreed before cutover, of a customer to return pieces of an old invoice (open receivable or fully settled legacy document) at a stated credit price and cost. Nothing posts at import; each physical receipt after cutover posts once.';

create table erp.bb_opening_sale_return_receipts_v1(
  id uuid primary key,
  right_id uuid not null references erp.bb_opening_sale_return_rights_v1(id),
  qty_pcs integer not null check(qty_pcs>0),
  location_id uuid not null references erp.locations(id),
  product_id uuid not null references erp.products(id),
  physical_at timestamptz not null,
  lot_id uuid not null unique references erp.fg_lots(id),
  movement_id uuid not null,
  value_journal_id uuid references erp.journal_entries(id),
  credit_id uuid unique references erp.bb_customer_credits_v1(id),
  reason text not null check(length(btrim(reason))>0),
  status text not null default 'POSTED' check(status in('POSTED','REVERSED')),
  reversed_at timestamptz,
  reversal_reason text,
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  check((status='REVERSED')=(reversed_at is not null))
);
alter table erp.bb_customer_credits_v1 add constraint bb_customer_credits_v1_return_receipt_fkey
  foreign key(return_receipt_id) references erp.bb_opening_sale_return_receipts_v1(id) deferrable initially deferred;

create table erp.bb_opening_credits_v1(
  settlement_id uuid primary key references erp.opening_subledger_settlements(id),
  credit_kind text not null check(credit_kind in('CUSTOMER_ALLOWANCE','SUPPLIER_ALLOWANCE','VENDOR_ALLOWANCE','CUSTOMER_CREDIT_APPLY')),
  credit_note_number text not null check(length(btrim(credit_note_number)) between 1 and 120),
  customer_credit_id uuid references erp.bb_customer_credits_v1(id),
  reason text not null check(length(btrim(reason))>0),
  created_at timestamptz not null default statement_timestamp(),
  check((credit_kind='CUSTOMER_CREDIT_APPLY')=(customer_credit_id is not null))
);
create unique index bb_opening_credits_v1_note on erp.bb_opening_credits_v1(credit_kind,lower(btrim(credit_note_number)))
  where credit_kind<>'CUSTOMER_CREDIT_APPLY';
comment on table erp.bb_opening_credits_v1 is 'BB (ALL-P02/S01): a non-cash settlement of an imported opening document (a credit note or allowance issued after cutover, or a customer credit applied to it). It rides on an opening_subledger_settlements row without a cash account, so settled amounts and the subledger checks stay canonical.';

do $rls$
declare t text;
begin
  foreach t in array array['bb_legacy_documents_v1','bb_customer_credits_v1','bb_customer_credit_events_v1',
    'bb_opening_sale_return_rights_v1','bb_opening_sale_return_receipts_v1','bb_opening_credits_v1'] loop
    execute format('alter table erp.%I enable row level security',t);
    execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
  end loop;
end $rls$;

-- Y01: an imported CONTRACTOR_PAYABLE paid inside payroll, like a cash advance deducted inside payroll (AP).
alter table erp.payroll_reimbursements add column opening_payable_balance_id uuid references erp.opening_subledger_balances(id);
alter table erp.payroll_reimbursements drop constraint payroll_reimbursements_source_type_check;
alter table erp.payroll_reimbursements add constraint payroll_reimbursements_source_type_check
  check(source_type::text=any(array['MANUAL','ACCESSORY_BOM','OPENING_PAYABLE']));
alter table erp.payroll_reimbursements add constraint payroll_reimbursements_opening_payable_check
  check((source_type::text='OPENING_PAYABLE')=(opening_payable_balance_id is not null));
create unique index payroll_reimbursements_opening_payable_unique on erp.payroll_reimbursements(payroll_id,opening_payable_balance_id)
  where opening_payable_balance_id is not null;

-- ---------------------------------------------------------------- shared helpers
CREATE OR REPLACE FUNCTION erp.bb_business_today_v1()
 RETURNS date LANGUAGE sql STABLE SET search_path TO ''
AS $function$ select (statement_timestamp() at time zone 'Asia/Jakarta')::date $function$;

CREATE OR REPLACE FUNCTION erp.bb_physical_at_v1(p_date date)
 RETURNS timestamptz LANGUAGE sql STABLE SET search_path TO ''
AS $function$
  -- A business date entered by the user as the instant it happened: noon Jakarta, or now for today (never in the future).
  -- A future date stays in the future so the date guards refuse it.
  select case when p_date=erp.bb_business_today_v1() then statement_timestamp()
    else (p_date::timestamp+interval '12 hours') at time zone 'Asia/Jakarta' end
$function$;

CREATE OR REPLACE FUNCTION erp.bb_parse_amount_v1(p_value text,p_field text,p_allow_zero boolean DEFAULT false)
 RETURNS numeric LANGUAGE plpgsql IMMUTABLE SET search_path TO ''
AS $function$
declare v numeric;
begin
  if p_value is null or btrim(p_value) !~ '^[0-9]+([.,][0-9]{1,2})?$' then
    raise exception 'BB_AMOUNT_INVALID: % harus nominal tepat dua desimal',p_field;
  end if;
  v:=replace(btrim(p_value),',','.')::numeric;
  if v>=1000000000000000000::numeric or (v=0 and not p_allow_zero) then
    raise exception 'BB_AMOUNT_INVALID: % harus lebih dari nol dan dalam batas penyimpanan',p_field;
  end if;
  return v;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_parse_date_v1(p_value text,p_field text)
 RETURNS date LANGUAGE plpgsql IMMUTABLE SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
begin
  if p_value is null or p_value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' or p_value::date::text<>p_value then
    raise exception 'BB_DATE_INVALID: % memakai YYYY-MM-DD',p_field;
  end if;
  return p_value::date;
end;$function$;

-- The context of one opening subledger balance: its cutover (opening date), document date and import source if any.
CREATE OR REPLACE FUNCTION erp.bb_opening_balance_context_v1(p_balance uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('balance_id',b.id,'opening_item_id',b.opening_item_id,'party_type',b.party_type,'direction',b.direction,
    'party_id',coalesce(b.customer_id,b.supplier_id,b.vendor_id,b.contractor_id),'balance_type',i.balance_type,
    'opening_date',h.opening_date,'cutover_date',coalesce(s.cutover_date,h.opening_date),'document_date',s.document_date,
    'document_number',s.document_number,'batch_id',s.batch_id,'source_kind',s.source_kind,'source_mode',s.source_mode,
    'min_date',greatest(coalesce(s.cutover_date,h.opening_date),coalesce(s.document_date,coalesce(s.cutover_date,h.opening_date))))
  from erp.opening_subledger_balances b
  join erp.opening_balance_items i on i.id=b.opening_item_id
  join erp.opening_balance_headers h on h.id=i.opening_id
  left join erp.initial_import_financial_sources s on s.opening_item_id=b.opening_item_id
  where b.id=p_balance
$function$;

-- Money of one opening balance already promised to a payroll that is not paid yet (Y01 lines and AP cash advance lines).
CREATE OR REPLACE FUNCTION erp.bb_opening_balance_reserved_v1(p_balance uuid,p_except_payroll uuid DEFAULT NULL)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce((select sum(r.amount) from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
      where r.opening_payable_balance_id=p_balance and p.status not in('PAID','REVERSED')
        and p.id is distinct from p_except_payroll),0)
    +coalesce((select sum(d.amount) from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
      where d.opening_cash_advance_balance_id=p_balance and p.status not in('PAID','REVERSED')
        and p.id is distinct from p_except_payroll),0)
$function$;

-- BB (D02 applied to opening balances, like BA A9 for advances): the lowest outstanding amount of one opening balance on
-- p_from and every later day. Opening amount at cutover; corrections on their effective date and their reversals on the
-- reversal date; settlements (cash, advance, credit) and payroll lines on their economic date, reversals on theirs.
CREATE OR REPLACE FUNCTION erp.bb_opening_balance_dated_floor_v1(p_balance uuid,p_from date)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
with b as (
  select b.id,b.original_amount-coalesce((select sum(c.delta_amount) from erp.opening_financial_corrections c
      where c.opening_item_id=b.opening_item_id and c.status='POSTED'),0) as initial_amount,b.opening_item_id
  from erp.opening_subledger_balances b where b.id=p_balance),
payroll_lines as (
  select x.payroll_id,x.amount from (
    select r.payroll_id,r.amount from erp.payroll_reimbursements r where r.opening_payable_balance_id=p_balance
    union all select d.payroll_id,d.amount from erp.payroll_deductions d where d.opening_cash_advance_balance_id=p_balance) x),
ev as (
  select c.effective_date as day,c.delta_amount as delta
  from erp.opening_financial_corrections c join b on b.opening_item_id=c.opening_item_id
  union all
  select coalesce((select min(r.economic_date) from erp.journal_entries j join erp.journal_entries r on r.reversal_of_id=j.id
      where j.source_type='OPENING_FINANCIAL_CORRECTION' and j.source_id=c.id),(c.reversed_at at time zone 'Asia/Jakarta')::date),
    -c.delta_amount
  from erp.opening_financial_corrections c join b on b.opening_item_id=c.opening_item_id where c.status='REVERSED'
  union all
  select coalesce((select j.economic_date from erp.journal_entries j where j.source_type='OPENING_SUBLEDGER_SETTLEMENT'
      and j.source_id=s.id and j.reversal_of_id is null order by j.posting_at,j.id limit 1),erp._cp3_business_date(s.physical_at)),-s.amount
  from erp.opening_subledger_settlements s where s.balance_id=p_balance and s.status in('POSTED','REVERSED')
  union all
  select coalesce((select min(r.economic_date) from erp.journal_entries j join erp.journal_entries r on r.reversal_of_id=j.id
      where j.source_type='OPENING_SUBLEDGER_SETTLEMENT' and j.source_id=s.id),(s.updated_at at time zone 'Asia/Jakarta')::date),s.amount
  from erp.opening_subledger_settlements s where s.balance_id=p_balance and s.status='REVERSED'
  union all
  select p.payment_date,-l.amount from payroll_lines l join erp.payroll_settlements p on p.id=l.payroll_id
  where p.status='PAID' or (p.status='REVERSED' and p.settled_at is null and exists(select 1 from erp.journal_entries j
    where j.source_id=p.id and j.source_type in('PAYROLL_PAYMENT','PAYROLL_CASH_ADVANCE_DEDUCTION','PAYROLL_MATERIAL_DEDUCTION','PAYROLL_OTHER_DEDUCTION') and j.status='REVERSED'))
  union all
  select coalesce((select min(r.economic_date) from erp.journal_entries j join erp.journal_entries r on r.reversal_of_id=j.id
      where j.source_id=p.id and j.source_type in('PAYROLL_PAYMENT','PAYROLL_CASH_ADVANCE_DEDUCTION','PAYROLL_MATERIAL_DEDUCTION','PAYROLL_OTHER_DEDUCTION')),(p.updated_at at time zone 'Asia/Jakarta')::date),
    l.amount
  from payroll_lines l join erp.payroll_settlements p on p.id=l.payroll_id
  where p.status='REVERSED' and exists(select 1 from erp.journal_entries j
    where j.source_id=p.id and j.source_type in('PAYROLL_PAYMENT','PAYROLL_CASH_ADVANCE_DEDUCTION','PAYROLL_MATERIAL_DEDUCTION','PAYROLL_OTHER_DEDUCTION') and j.status='REVERSED'))
select min(b.initial_amount+coalesce((select sum(e.delta) from ev e where e.day<=d.day),0))
from b cross join (select p_from as day union select e.day from ev e where e.day>p_from) d
$function$;

CREATE OR REPLACE FUNCTION erp.bb_assert_opening_balance_floor_v1(p_balance uuid,p_from date)
 RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v numeric;
begin
  v:=erp.bb_opening_balance_dated_floor_v1(p_balance,p_from);
  if v<0 then
    raise exception 'BB_OSS_DATED_CAPACITY: sisa saldo awal pada % atau sesudahnya menjadi % ; pelunasan tidak boleh memakai saldo yang baru ada di tanggal lebih akhir',p_from,v;
  end if;
end;$function$;

-- The journal lines of a non-cash opening settlement (credit note, allowance, customer credit applied).
CREATE OR REPLACE FUNCTION erp.bb_opening_credit_lines_v1(p_settlement_id uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare c erp.bb_opening_credits_v1%rowtype;s erp.opening_subledger_settlements%rowtype;b erp.opening_subledger_balances%rowtype;
  v_credit erp.bb_customer_credits_v1%rowtype;
begin
  select * into c from erp.bb_opening_credits_v1 where settlement_id=p_settlement_id;
  select * into s from erp.opening_subledger_settlements where id=p_settlement_id;
  select * into b from erp.opening_subledger_balances where id=s.balance_id;
  if c.credit_kind in('CUSTOMER_ALLOWANCE','CUSTOMER_CREDIT_APPLY') then
    if b.party_type<>'CUSTOMER' or b.direction<>'RECEIVABLE' then raise exception 'BB_CREDIT_KIND_MISMATCH: kredit pelanggan hanya untuk piutang pelanggan';end if;
    if c.credit_kind='CUSTOMER_CREDIT_APPLY' then
      select * into v_credit from erp.bb_customer_credits_v1 where id=c.customer_credit_id;
      if v_credit.customer_id is distinct from b.customer_id then raise exception 'BB_CREDIT_PARTY_MISMATCH: kredit dan piutang harus milik pelanggan yang sama';end if;
      return jsonb_build_array(
        jsonb_build_object('account_id',v_credit.coa_account_id,'debit',s.amount,'credit',0,'customer_id',b.customer_id),
        jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',s.amount,'customer_id',b.customer_id));
    end if;
    return jsonb_build_array(
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',s.amount,'credit',0,'customer_id',b.customer_id),
      jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',s.amount,'customer_id',b.customer_id));
  elsif c.credit_kind='SUPPLIER_ALLOWANCE' then
    if b.party_type<>'SUPPLIER' or b.direction<>'PAYABLE' then raise exception 'BB_CREDIT_KIND_MISMATCH: potongan supplier hanya untuk hutang supplier';end if;
    return jsonb_build_array(
      jsonb_build_object('mapping_key','AP_SUPPLIER','debit',s.amount,'credit',0),
      jsonb_build_object('mapping_key','MATERIAL_PURCHASE_VARIANCE','debit',0,'credit',s.amount));
  elsif c.credit_kind='VENDOR_ALLOWANCE' then
    if b.party_type<>'VENDOR' or b.direction<>'PAYABLE' then raise exception 'BB_CREDIT_KIND_MISMATCH: potongan laundry hanya untuk hutang vendor laundry';end if;
    return jsonb_build_array(
      jsonb_build_object('mapping_key','AP_VENDOR','debit',s.amount,'credit',0,'vendor_id',b.vendor_id),
      jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',s.amount,'vendor_id',b.vendor_id));
  end if;
  raise exception 'BB_CREDIT_KIND_MISMATCH';
end;$function$;

-- The account a non-cash opening settlement credits or debits against the party account (the counterpart of the cash
-- account of a cash settlement), used by the V2620M payment/journal detector.
CREATE OR REPLACE FUNCTION erp.bb_opening_credit_account_v1(p_settlement_id uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select case c.credit_kind when 'CUSTOMER_ALLOWANCE' then erp.account_id('SALES_REVENUE')
    when 'SUPPLIER_ALLOWANCE' then erp.account_id('MATERIAL_PURCHASE_VARIANCE') when 'VENDOR_ALLOWANCE' then erp.account_id('OTHER_INCOME')
    else (select k.coa_account_id from erp.bb_customer_credits_v1 k where k.id=c.customer_credit_id) end
  from erp.bb_opening_credits_v1 c where c.settlement_id=p_settlement_id
$function$;

-- ---------------------------------------------------------------- customer credits (S03)
CREATE OR REPLACE FUNCTION erp.bb_customer_credit_state_v1(p_credit_id uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('credit_id',c.id,'origin',c.origin,'customer_id',c.customer_id,'document_number',c.document_number,
    'document_date',c.document_date,'effective_date',c.effective_date,'original_amount',c.original_amount::text,
    'settled_before_cutover',c.settled_before_cutover::text,'amount',c.amount::text,
    'used_amount',u.used::text,'voided',c.voided_at is not null,
    'remaining_amount',(case when c.voided_at is null then c.amount-u.used else 0 end)::numeric(20,2)::text)
  from erp.bb_customer_credits_v1 c
  cross join lateral (select coalesce(sum(e.amount),0)::numeric(20,2) used from erp.bb_customer_credit_events_v1 e
    left join erp.opening_subledger_settlements s on s.id=e.settlement_id
    where e.credit_id=c.id and ((e.event_type='REFUND' and e.reversed_at is null) or (e.event_type='APPLY_OPENING_AR' and s.status='POSTED'))) u
  where c.id=p_credit_id
$function$;

-- The lowest remaining credit on p_from and every later day, from the lines on the credit account of the credit's own
-- journals (its creation, refunds, applications and their reversals), by economic date.
CREATE OR REPLACE FUNCTION erp.bb_customer_credit_dated_floor_v1(p_credit_id uuid,p_from date)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
with c as (select * from erp.bb_customer_credits_v1 where id=p_credit_id),
js as (
  select c.journal_entry_id id from c
  union select e.journal_entry_id from erp.bb_customer_credit_events_v1 e where e.credit_id=p_credit_id and e.journal_entry_id is not null
  union select j.id from erp.journal_entries j join erp.bb_customer_credit_events_v1 e on e.settlement_id=j.source_id
    where e.credit_id=p_credit_id and j.source_type='OPENING_SUBLEDGER_SETTLEMENT'
  union select r.id from erp.journal_entries r join erp.journal_entries j on j.id=r.reversal_of_id
    join erp.bb_customer_credit_events_v1 e on e.journal_entry_id=j.id or (j.source_type='OPENING_SUBLEDGER_SETTLEMENT' and j.source_id=e.settlement_id)
    where e.credit_id=p_credit_id),
moves as (
  select je.economic_date as day,jl.credit-jl.debit as amount
  from js join erp.journal_entries je on je.id=js.id and je.status in('POSTED','REVERSED')
  join erp.journal_lines jl on jl.journal_entry_id=je.id
  cross join c where jl.account_id=c.coa_account_id and jl.customer_id is not distinct from c.customer_id)
select min(coalesce((select sum(m.amount) from moves m where m.day<=d.day),0))
from (select p_from as day union select m.day from moves m where m.day>p_from) d
$function$;

CREATE OR REPLACE FUNCTION erp.bb_check_credit_account_v1(p_account uuid,p_account_payload jsonb DEFAULT NULL)
 RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare a jsonb;
begin
  select to_jsonb(x) into a from erp.chart_accounts x where x.id=p_account;
  a:=coalesce(a,p_account_payload);
  if a is null or a->>'account_type' is distinct from 'LIABILITY' or a->>'normal_balance' is distinct from 'CREDIT'
    or not coalesce(nullif(a->>'is_active','')::boolean,true) or not coalesce(nullif(a->>'is_postable','')::boolean,true)
    or (p_account is not null and (exists(select 1 from erp.cash_accounts where coa_account_id=p_account)
      or exists(select 1 from erp.accounting_account_mappings where account_id=p_account)
      or exists(select 1 from erp.initial_import_prepayments where coa_account_id=p_account))) then
    raise exception 'BB_CREDIT_ACCOUNT_INVALID: gunakan akun kewajiban khusus kredit pelanggan yang aktif, bukan kas, akun mapping, atau akun uang muka';
  end if;
  if p_account is not null and not exists(select 1 from erp.bb_customer_credits_v1 where coa_account_id=p_account)
    and exists(select 1 from erp.journal_lines where account_id=p_account) then
    raise exception 'BB_CREDIT_ACCOUNT_INVALID: akun ini sudah memiliki saldo tanpa sumber kredit pelanggan; rekonsiliasi dahulu';
  end if;
end;$function$;

-- ---------------------------------------------------------------- import rows: validation and apply
CREATE OR REPLACE FUNCTION erp.bb_party_of_v1(p_batch uuid,p_balance_type text,p_code text)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
-- The party of a balance type by code: an active master, or a valid master row of the same batch (applied at FINALIZE).
declare v_table text;v_code text;v_entity text;v_id uuid;
begin
  v_table:=case p_balance_type when 'CUSTOMER_RECEIVABLE' then 'customers' when 'SUPPLIER_PAYABLE' then 'suppliers'
    when 'VENDOR_PAYABLE' then 'laundry_vendors' when 'CONTRACTOR_RECEIVABLE' then 'contractors' when 'CONTRACTOR_PAYABLE' then 'contractors' end;
  if v_table is null then raise exception 'balance_type: gunakan CUSTOMER_RECEIVABLE, SUPPLIER_PAYABLE, VENDOR_PAYABLE, CONTRACTOR_RECEIVABLE, atau CONTRACTOR_PAYABLE';end if;
  v_code:=case v_table when 'customers' then 'customer_code' when 'suppliers' then 'supplier_code' when 'laundry_vendors' then 'vendor_code' else 'contractor_code' end;
  v_entity:=case v_table when 'customers' then 'CUSTOMER' when 'suppliers' then 'SUPPLIER' when 'laundry_vendors' then 'LAUNDRY_VENDOR' else 'CONTRACTOR' end;
  execute format('select id from erp.%I where %I=$1 and is_active',v_table,v_code) into v_id using p_code;
  if v_id is null and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type=v_entity
      and validation_status='VALID' and normalized_payload->>v_code=p_code
      and coalesce(nullif(normalized_payload->>'is_active','')::boolean,true)) then
    raise exception 'party_code: pihak aktif % tidak ditemukan',p_code;
  end if;
  return jsonb_build_object('party_id',v_id,'party_code',p_code,'code_field',v_code,'table',v_table);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_check_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_cutover date;v_party jsonb;v_date date;v_doc text;
  v_original numeric;v_settled numeric;v_amount numeric;v_account uuid;a jsonb;v_qty numeric;v_price numeric;v_cost numeric;
  v_invoice jsonb;v_product jsonb;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch;
  if r.id is null then raise exception 'Baris impor tidak ditemukan';end if;
  j:=r.normalized_payload;
  select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch;
  if r.entity_type='LEGACY_DOCUMENT' then
    foreach k in array array['balance_type','party_code','document_number','document_date','original_amount','settled_before_cutover'] loop
      if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk dokumen lama yang sudah lunas',k;end if;
    end loop;
    v_party:=erp.bb_party_of_v1(p_batch,j->>'balance_type',j->>'party_code');
    v_doc:=btrim(j->>'document_number');
    if length(v_doc)>120 then raise exception 'document_number: maksimal 120 karakter';end if;
    v_date:=erp.bb_parse_date_v1(j->>'document_date','document_date');
    if v_date>v_cutover then raise exception 'document_date: dokumen lama tidak boleh sesudah tanggal saldo awal';end if;
    v_original:=erp.bb_parse_amount_v1(j->>'original_amount','original_amount');
    v_settled:=erp.bb_parse_amount_v1(j->>'settled_before_cutover','settled_before_cutover',true);
    if v_settled<>v_original then
      raise exception 'BB_LEGACY_DOCUMENT_NOT_SETTLED: dokumen lama hanya dicatat bila sudah lunas penuh; sisa terbuka diimpor sebagai saldo awal dokumen';
    end if;
    if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.id<>r.id
        and ((s.entity_type='LEGACY_DOCUMENT' and s.normalized_payload->>'balance_type'=j->>'balance_type'
              and s.normalized_payload->>'party_code'=j->>'party_code')
          or (s.entity_type='OPENING_BALANCE_ITEM' and s.normalized_payload->>'balance_type'=j->>'balance_type'
              and s.normalized_payload->>(v_party->>'code_field')=j->>'party_code'))
        and lower(btrim(s.normalized_payload->>'document_number'))=lower(v_doc))
      or (v_party->>'party_id' is not null and (exists(select 1 from erp.bb_legacy_documents_v1 d where d.balance_type=j->>'balance_type'
          and d.party_id=(v_party->>'party_id')::uuid and lower(btrim(d.document_number))=lower(v_doc) and d.source_row_id<>r.id)
        or exists(select 1 from erp.initial_import_financial_sources f where f.balance_type=j->>'balance_type'
          and f.party_id=(v_party->>'party_id')::uuid and lower(btrim(f.document_number))=lower(v_doc)))) then
      raise exception 'BB_LEGACY_DOCUMENT_DUPLICATE: nomor dokumen ini sudah tercatat untuk pihak yang sama';
    end if;
    return jsonb_build_object('party_id',v_party->>'party_id','cutover_date',v_cutover,'document_date',v_date);
  elsif r.entity_type='OPENING_CUSTOMER_CREDIT' then
    foreach k in array array['customer_code','coa_account_code','document_number','document_date','original_amount','settled_before_cutover','amount'] loop
      if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk kredit pelanggan',k;end if;
    end loop;
    v_party:=erp.bb_party_of_v1(p_batch,'CUSTOMER_RECEIVABLE',j->>'customer_code');
    v_doc:=btrim(j->>'document_number');
    if length(v_doc)>120 then raise exception 'document_number: maksimal 120 karakter';end if;
    v_date:=erp.bb_parse_date_v1(j->>'document_date','document_date');
    if v_date>v_cutover then raise exception 'document_date: retur yang kreditnya dibawa harus sudah terjadi sebelum saldo awal';end if;
    v_original:=erp.bb_parse_amount_v1(j->>'original_amount','original_amount');
    v_settled:=erp.bb_parse_amount_v1(j->>'settled_before_cutover','settled_before_cutover',true);
    v_amount:=erp.bb_parse_amount_v1(j->>'amount','amount');
    if v_original-v_settled<>v_amount then raise exception 'amount: sisa kredit harus sama dengan kredit asal dikurangi yang sudah dibayar sebelum saldo awal';end if;
    select id into v_account from erp.chart_accounts where account_code=j->>'coa_account_code';
    if v_account is null then
      select normalized_payload into a from erp.migration_staging_rows where batch_id=p_batch and entity_type='CHART_ACCOUNT'
        and validation_status='VALID' and normalized_payload->>'account_code'=j->>'coa_account_code';
      if a is null then raise exception 'coa_account_code: akun tidak ditemukan';end if;
    end if;
    perform erp.bb_check_credit_account_v1(v_account,a);
    if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.id<>r.id
        and s.entity_type='OPENING_CUSTOMER_CREDIT' and s.normalized_payload->>'customer_code'=j->>'customer_code'
        and lower(btrim(s.normalized_payload->>'document_number'))=lower(v_doc))
      or (v_party->>'party_id' is not null and exists(select 1 from erp.bb_customer_credits_v1 c
        where c.customer_id=(v_party->>'party_id')::uuid and lower(btrim(c.document_number))=lower(v_doc)
          and c.source_row_id is distinct from r.id)) then
      raise exception 'BB_CUSTOMER_CREDIT_DUPLICATE: kredit dengan nomor ini sudah tercatat untuk pelanggan yang sama';
    end if;
    return jsonb_build_object('customer_id',v_party->>'party_id','coa_account_id',v_account,'cutover_date',v_cutover,'document_date',v_date);
  elsif r.entity_type='OPENING_SALE_RETURN' then
    foreach k in array array['customer_code','return_number','invoice_document_number','product_sku','qty','credit_unit_price','unit_cost','credit_coa_account_code'] loop
      if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk hak retur penjualan lama',k;end if;
    end loop;
    v_party:=erp.bb_party_of_v1(p_batch,'CUSTOMER_RECEIVABLE',j->>'customer_code');
    if length(btrim(j->>'return_number'))>120 then raise exception 'return_number: maksimal 120 karakter';end if;
    if j->>'qty' !~ '^[1-9][0-9]{0,8}$' then raise exception 'qty: jumlah pcs bilangan bulat positif';end if;
    v_price:=erp.bb_parse_amount_v1(j->>'credit_unit_price','credit_unit_price',true);
    v_cost:=erp.bb_parse_amount_v1(j->>'unit_cost','unit_cost',true);
    -- The invoice: an open receivable document or a fully settled legacy document of the same customer.
    if not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.validation_status<>'ERROR'
        and ((s.entity_type='OPENING_BALANCE_ITEM' and s.normalized_payload->>'balance_type'='CUSTOMER_RECEIVABLE'
              and s.normalized_payload->>'customer_code'=j->>'customer_code')
          or (s.entity_type='LEGACY_DOCUMENT' and s.normalized_payload->>'balance_type'='CUSTOMER_RECEIVABLE'
              and s.normalized_payload->>'party_code'=j->>'customer_code'))
        and lower(btrim(s.normalized_payload->>'document_number'))=lower(btrim(j->>'invoice_document_number')))
      and not (v_party->>'party_id' is not null and (exists(select 1 from erp.initial_import_financial_sources f
          where f.balance_type='CUSTOMER_RECEIVABLE' and f.party_id=(v_party->>'party_id')::uuid and f.source_mode='DOCUMENT'
            and lower(btrim(f.document_number))=lower(btrim(j->>'invoice_document_number')))
        or exists(select 1 from erp.bb_legacy_documents_v1 d where d.balance_type='CUSTOMER_RECEIVABLE'
          and d.party_id=(v_party->>'party_id')::uuid and lower(btrim(d.document_number))=lower(btrim(j->>'invoice_document_number'))))) then
      raise exception 'BB_RETURN_INVOICE_REQUIRED: invoice asal harus diimpor sebagai piutang dokumen atau dokumen lama lunas milik pelanggan yang sama';
    end if;
    if not exists(select 1 from erp.products p where lower(btrim(p.sku))=lower(btrim(j->>'product_sku')))
      and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='PRODUCT'
        and s.validation_status='VALID' and lower(btrim(s.normalized_payload->>'sku'))=lower(btrim(j->>'product_sku'))) then
      raise exception 'product_sku: produk tidak ditemukan';
    end if;
    select id into v_account from erp.chart_accounts where account_code=j->>'credit_coa_account_code';
    if v_account is null then
      select normalized_payload into a from erp.migration_staging_rows where batch_id=p_batch and entity_type='CHART_ACCOUNT'
        and validation_status='VALID' and normalized_payload->>'account_code'=j->>'credit_coa_account_code';
      if a is null then raise exception 'credit_coa_account_code: akun tidak ditemukan';end if;
    end if;
    perform erp.bb_check_credit_account_v1(v_account,a);
    if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.id<>r.id
        and s.entity_type='OPENING_SALE_RETURN' and s.normalized_payload->>'customer_code'=j->>'customer_code'
        and lower(btrim(s.normalized_payload->>'return_number'))=lower(btrim(j->>'return_number')))
      or (v_party->>'party_id' is not null and exists(select 1 from erp.bb_opening_sale_return_rights_v1 x
        where x.customer_id=(v_party->>'party_id')::uuid and lower(btrim(x.return_number))=lower(btrim(j->>'return_number'))
          and x.source_row_id<>r.id)) then
      raise exception 'BB_RETURN_RIGHT_DUPLICATE: hak retur dengan nomor ini sudah tercatat';
    end if;
    return jsonb_build_object('customer_id',v_party->>'party_id','coa_account_id',v_account,'cutover_date',v_cutover);
  end if;
  raise exception 'BB: jenis baris % tidak ditangani bagian keuangan',r.entity_type;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_validate_financial_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;
begin
  perform erp.require_owner_admin();
  -- Legacy documents first: return rights name them.
  for r in select id from erp.migration_staging_rows where batch_id=p_batch
      and entity_type in('LEGACY_DOCUMENT','OPENING_CUSTOMER_CREDIT','OPENING_SALE_RETURN')
      order by case entity_type when 'LEGACY_DOCUMENT' then 1 when 'OPENING_CUSTOMER_CREDIT' then 2 else 3 end,source_row_no loop
    begin
      perform erp.bb_check_import_row_v1(p_batch,r.id);
      update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
    exception when others then
      update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;
    end;
  end loop;
  -- An open receivable document may not also be a fully settled legacy document (checked from the document side too).
  update erp.migration_staging_rows s set validation_status='ERROR',
    validation_errors=s.validation_errors||jsonb_build_array('BB_LEGACY_DOCUMENT_DUPLICATE: dokumen ini juga dicatat sebagai dokumen lama lunas')
  where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM' and nullif(btrim(s.normalized_payload->>'document_number'),'') is not null
    and exists(select 1 from erp.migration_staging_rows d where d.batch_id=p_batch and d.entity_type='LEGACY_DOCUMENT'
      and d.normalized_payload->>'balance_type'=s.normalized_payload->>'balance_type'
      and d.normalized_payload->>'party_code'=s.normalized_payload->>(case s.normalized_payload->>'balance_type'
        when 'CUSTOMER_RECEIVABLE' then 'customer_code' when 'SUPPLIER_PAYABLE' then 'supplier_code'
        when 'VENDOR_PAYABLE' then 'vendor_code' else 'contractor_code' end)
      and lower(btrim(d.normalized_payload->>'document_number'))=lower(btrim(s.normalized_payload->>'document_number')));
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_apply_financial_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;j jsonb;c jsonb;v_id uuid;v_journal uuid;v_party uuid;v_invoice uuid;v_legacy uuid;v_product uuid;
  v_cutover_at timestamptz;v_account uuid;
begin
  perform erp.require_owner_admin();
  select cutover_at into v_cutover_at from erp.migration_batches where id=p_batch;
  for r in select * from erp.migration_staging_rows where batch_id=p_batch
      and entity_type in('LEGACY_DOCUMENT','OPENING_CUSTOMER_CREDIT','OPENING_SALE_RETURN') and posted_entity_id is null
      order by case entity_type when 'LEGACY_DOCUMENT' then 1 when 'OPENING_CUSTOMER_CREDIT' then 2 else 3 end,source_row_no loop
    if r.validation_status<>'VALID' then raise exception 'Baris % belum lolos pemeriksaan',r.entity_type;end if;
    j:=r.normalized_payload;
    perform pg_advisory_xact_lock(hashtextextended('BB_IMPORT_DOC:'||r.entity_type||':'||coalesce(j->>'party_code',j->>'customer_code','')
      ||':'||lower(btrim(coalesce(j->>'document_number',j->>'return_number',''))),0));
    c:=erp.bb_check_import_row_v1(p_batch,r.id);
    if r.entity_type='LEGACY_DOCUMENT' then
      v_party:=(erp.bb_party_of_v1(p_batch,j->>'balance_type',j->>'party_code')->>'party_id')::uuid;
      if v_party is null then raise exception 'Master pihak dokumen lama belum tersedia';end if;
      insert into erp.bb_legacy_documents_v1(batch_id,source_row_id,balance_type,party_id,document_number,document_date,cutover_date,
        original_amount,settled_before_cutover,notes)
      values(p_batch,r.id,j->>'balance_type',v_party,btrim(j->>'document_number'),(c->>'document_date')::date,(c->>'cutover_date')::date,
        replace(j->>'original_amount',',','.')::numeric,replace(j->>'settled_before_cutover',',','.')::numeric,nullif(btrim(j->>'notes'),''))
      returning id into v_id;
    elsif r.entity_type='OPENING_CUSTOMER_CREDIT' then
      v_party:=(c->>'customer_id')::uuid;
      v_account:=coalesce((c->>'coa_account_id')::uuid,(select id from erp.chart_accounts where account_code=j->>'coa_account_code'));
      if v_party is null or v_account is null then raise exception 'Master kredit pelanggan belum tersedia';end if;
      perform erp.bb_check_credit_account_v1(v_account);
      v_id:=gen_random_uuid();
      v_journal:=erp.post_journal('BB_CUSTOMER_CREDIT',v_id,(c->>'cutover_date')::date,'Kredit retur pelanggan sebelum ERP',jsonb_build_array(
        jsonb_build_object('mapping_key','OPENING_EQUITY','debit',replace(j->>'amount',',','.')::numeric,'credit',0,'customer_id',v_party),
        jsonb_build_object('account_id',v_account,'debit',0,'credit',replace(j->>'amount',',','.')::numeric,'customer_id',v_party)));
      insert into erp.bb_customer_credits_v1(id,origin,batch_id,source_row_id,customer_id,coa_account_id,document_number,document_date,
        original_amount,settled_before_cutover,amount,effective_date,journal_entry_id,created_by)
      values(v_id,'IMPORTED',p_batch,r.id,v_party,v_account,btrim(j->>'document_number'),(c->>'document_date')::date,
        replace(j->>'original_amount',',','.')::numeric,replace(j->>'settled_before_cutover',',','.')::numeric,
        replace(j->>'amount',',','.')::numeric,(c->>'cutover_date')::date,v_journal,erp.current_app_user_id());
    else
      v_party:=(c->>'customer_id')::uuid;
      v_account:=coalesce((c->>'coa_account_id')::uuid,(select id from erp.chart_accounts where account_code=j->>'credit_coa_account_code'));
      if v_party is null or v_account is null then raise exception 'Master hak retur belum tersedia';end if;
      perform erp.bb_check_credit_account_v1(v_account);
      select f.id into v_invoice from erp.initial_import_financial_sources f where f.balance_type='CUSTOMER_RECEIVABLE'
        and f.party_id=v_party and f.source_mode='DOCUMENT' and lower(btrim(f.document_number))=lower(btrim(j->>'invoice_document_number'));
      if v_invoice is null then
        select d.id into v_legacy from erp.bb_legacy_documents_v1 d where d.balance_type='CUSTOMER_RECEIVABLE' and d.party_id=v_party
          and lower(btrim(d.document_number))=lower(btrim(j->>'invoice_document_number'));
      end if;
      if v_invoice is null and v_legacy is null then raise exception 'BB_RETURN_INVOICE_REQUIRED: invoice asal tidak ditemukan';end if;
      v_product:=erp.resolve_opening_product_identity(j->>'product_sku',v_cutover_at,j->>'color_name',j->>'size_code',
        j->>'model_code',j->>'brand_code');
      if v_product is null then raise exception 'product_sku: produk hak retur tidak ditemukan pada tanggal saldo awal';end if;
      insert into erp.bb_opening_sale_return_rights_v1(batch_id,source_row_id,customer_id,return_number,invoice_document_number,
        invoice_source_id,legacy_document_id,product_id,qty_pcs,credit_unit_price,unit_cost,credit_coa_account_id,cutover_date)
      values(p_batch,r.id,v_party,btrim(j->>'return_number'),btrim(j->>'invoice_document_number'),v_invoice,v_legacy,v_product,
        (j->>'qty')::integer,replace(j->>'credit_unit_price',',','.')::numeric,replace(j->>'unit_cost',',','.')::numeric,v_account,
        (c->>'cutover_date')::date)
      returning id into v_id;
      v_invoice:=null;v_legacy:=null;
    end if;
    update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type=r.entity_type,posted_at=statement_timestamp(),
      updated_at=statement_timestamp() where id=r.id;
  end loop;
end;$function$;

-- One identity for an old document: an open imported document and a fully settled legacy document never share it.
CREATE OR REPLACE FUNCTION erp.bb_guard_legacy_document_identity_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if TG_TABLE_NAME='bb_legacy_documents_v1' then
    if TG_OP<>'INSERT' then raise exception 'BB_LEGACY_DOCUMENT_IMMUTABLE: dokumen lama hanya provenance dan tidak diubah';end if;
    perform pg_advisory_xact_lock(hashtextextended('BB_DOC_IDENTITY:'||new.balance_type||':'||new.party_id||':'||lower(btrim(new.document_number)),0));
    if exists(select 1 from erp.initial_import_financial_sources f where f.balance_type=new.balance_type and f.party_id=new.party_id
        and lower(btrim(f.document_number))=lower(btrim(new.document_number))) then
      raise exception 'BB_LEGACY_DOCUMENT_DUPLICATE: dokumen ini sudah diimpor sebagai saldo terbuka';
    end if;
  elsif new.document_number is not null then
    perform pg_advisory_xact_lock(hashtextextended('BB_DOC_IDENTITY:'||new.balance_type||':'||new.party_id||':'||lower(btrim(new.document_number)),0));
    if exists(select 1 from erp.bb_legacy_documents_v1 d where d.balance_type=new.balance_type and d.party_id=new.party_id
        and lower(btrim(d.document_number))=lower(btrim(new.document_number))) then
      raise exception 'BB_LEGACY_DOCUMENT_DUPLICATE: dokumen ini sudah dicatat sebagai dokumen lama lunas';
    end if;
  end if;
  return new;
end;$function$;
create trigger trg_bb_legacy_document_identity before insert or update or delete on erp.bb_legacy_documents_v1
  for each row execute function erp.bb_guard_legacy_document_identity_v1();
create trigger trg_bb_financial_source_legacy_identity before insert on erp.initial_import_financial_sources
  for each row execute function erp.bb_guard_legacy_document_identity_v1();

-- ---------------------------------------------------------------- Y01: opening payable lines in payroll
CREATE OR REPLACE FUNCTION erp.bb_guard_opening_payable_reimbursement_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path TO ''
AS $function$
declare p erp.payroll_settlements%rowtype;b erp.opening_subledger_balances%rowtype;ctx jsonb;v_id uuid;v_reserved numeric;
begin
  if TG_OP='DELETE' then
    if old.opening_payable_balance_id is null then return old;end if;
    v_id:=old.payroll_id;
  else
    if new.opening_payable_balance_id is null and new.source_type::text<>'OPENING_PAYABLE'
      and (TG_OP='INSERT' or old.opening_payable_balance_id is null) then return new;end if;
    v_id:=new.payroll_id;
  end if;
  -- Only the controlled writer reaches these lines (same rule as the cash advance deduction of AP).
  if current_user<>'postgres' then raise exception 'BB_OPENING_PAYABLE_WRITER: hutang saldo awal masuk payroll hanya lewat command resmi';end if;
  perform erp.require_internal();
  if TG_OP='UPDATE' and (new.payroll_id<>old.payroll_id or new.opening_payable_balance_id is distinct from old.opening_payable_balance_id
      or new.source_type is distinct from old.source_type) then
    raise exception 'BB_OPENING_PAYABLE_WRITER: sumber hutang payroll tidak dapat dipindah; lepaskan lalu pilih ulang';
  end if;
  select * into p from erp.payroll_settlements where id=v_id for update;
  if p.id is null or p.status not in('DRAFT','CALCULATED','REVIEW') then
    raise exception 'BB_OPENING_PAYABLE_DRAFT_ONLY: hutang saldo awal hanya dapat diatur pada payroll draft';
  end if;
  if TG_OP='DELETE' then
    perform 1 from erp.opening_subledger_balances where id=old.opening_payable_balance_id for update;
    return old;
  end if;
  if new.source_type::text<>'OPENING_PAYABLE' or new.opening_payable_balance_id is null or new.amount is null
    or new.amount::text in('NaN','Infinity','-Infinity') or new.amount<=0 or new.amount<>round(new.amount,2) then
    raise exception 'BB_OPENING_PAYABLE_AMOUNT: hutang saldo awal memerlukan sumber dan nominal positif tepat dua desimal';
  end if;
  select * into b from erp.opening_subledger_balances where id=new.opening_payable_balance_id for update;
  ctx:=erp.bb_opening_balance_context_v1(b.id);
  if b.id is null or ctx->>'batch_id' is null or b.party_type<>'CONTRACTOR' or b.direction<>'PAYABLE'
    or b.contractor_id is distinct from p.contractor_id then
    raise exception 'BB_OPENING_PAYABLE_WRONG_CONTRACTOR: hutang harus saldo awal impor milik mandor payroll ini';
  end if;
  v_reserved:=erp.bb_opening_balance_reserved_v1(b.id)-coalesce((select r.amount from erp.payroll_reimbursements r where r.id=new.id
    and TG_OP='UPDATE'),0);
  if new.amount>b.original_amount-b.settled_amount-v_reserved then
    raise exception 'BB_OPENING_PAYABLE_EXCEEDS_AVAILABLE: melebihi sisa hutang saldo awal yang belum dilunasi atau dipakai payroll lain';
  end if;
  return new;
end;$function$;
create trigger trg_bb_opening_payable_reimbursement before insert or update or delete on erp.payroll_reimbursements
  for each row execute function erp.bb_guard_opening_payable_reimbursement_v1();

-- A balance never promises more than it has: settled plus payroll lines not yet paid stay within the opening amount.
CREATE OR REPLACE FUNCTION erp.bb_guard_opening_balance_reserved_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_reserved numeric;
begin
  select coalesce(sum(r.amount),0) into v_reserved from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
    where r.opening_payable_balance_id=new.id and p.status not in('PAID','REVERSED');
  if v_reserved>0 and new.original_amount<new.settled_amount+v_reserved then
    raise exception 'BB_OSS_EXCEEDS_AVAILABLE: saldo awal tidak cukup setelah pelunasan dan hutang yang sudah masuk payroll; lepaskan dari payroll dahulu';
  end if;
  return new;
end;$function$;
create trigger trg_bb_opening_balance_reserved before update on erp.opening_subledger_balances
  for each row execute function erp.bb_guard_opening_balance_reserved_v1();

CREATE OR REPLACE FUNCTION erp.bb_check_opening_payable_payroll_v1(p_payroll_id uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare p erp.payroll_settlements%rowtype;r record;
begin
  perform erp.require_internal();
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null then raise exception 'Payroll tidak ditemukan';end if;
  for r in select b.*,x.amount line_amount,(erp.bb_opening_balance_context_v1(b.id)->>'cutover_date')::date cutover_date
      from erp.opening_subledger_balances b
      join (select opening_payable_balance_id id,sum(amount) amount from erp.payroll_reimbursements
        where payroll_id=p.id and source_type='OPENING_PAYABLE' group by 1) x on x.id=b.id
      order by b.id for update of b loop
    if r.party_type<>'CONTRACTOR' or r.direction<>'PAYABLE' or r.contractor_id is distinct from p.contractor_id then
      raise exception 'BB_OPENING_PAYABLE_WRONG_CONTRACTOR: hutang saldo awal bukan milik mandor payroll ini';
    end if;
    if p.payment_date<r.cutover_date then
      raise exception 'BB_OPENING_PAYABLE_DATE: tanggal pembayaran payroll sebelum saldo awal %',r.cutover_date;
    end if;
    if r.line_amount>r.original_amount-r.settled_amount-erp.bb_opening_balance_reserved_v1(r.id,p.id) then
      raise exception 'BB_OPENING_PAYABLE_EXCEEDS_AVAILABLE: saldo hutang berubah atau sudah dipakai pelunasan/payroll lain';
    end if;
  end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_set_opening_payable_payroll_v1(p_balance_id uuid,p_payroll_id uuid,p_amount numeric,p_expected_version bigint)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare p erp.payroll_settlements%rowtype;v_id uuid;ctx jsonb;
begin
  perform erp.require_owner_admin();
  if p_amount is null or p_amount::text in('NaN','Infinity','-Infinity') or p_amount<0 or p_amount<>round(p_amount,2) then
    raise exception 'BB_OPENING_PAYABLE_AMOUNT: nominal tepat dua desimal; nol untuk melepaskan';
  end if;
  select * into p from erp.payroll_settlements where id=p_payroll_id for update;
  if p.id is null or p.status not in('DRAFT','CALCULATED','REVIEW') then raise exception 'BB_OPENING_PAYABLE_DRAFT_ONLY: payroll harus draft';end if;
  if p_expected_version is null or p.row_version<>p_expected_version then raise exception 'STALE_VERSION: payroll berubah';end if;
  ctx:=erp.bb_opening_balance_context_v1(p_balance_id);
  if ctx is null or ctx->>'batch_id' is null then raise exception 'BB_OSS_NOT_IN_BATCH: saldo hutang impor tidak ditemukan';end if;
  select id into v_id from erp.payroll_reimbursements where payroll_id=p.id and opening_payable_balance_id=p_balance_id;
  if p_amount=0 then
    if v_id is null then raise exception 'Alokasi yang akan dilepas tidak ditemukan';end if;
    delete from erp.payroll_reimbursements where id=v_id;
  elsif v_id is null then
    insert into erp.payroll_reimbursements(payroll_id,amount,description,source_type,opening_payable_balance_id)
    values(p.id,p_amount,'Hutang upah/reimburse saldo awal '||coalesce(ctx->>'document_number','ringkasan'),'OPENING_PAYABLE',p_balance_id)
    returning id into v_id;
  else
    update erp.payroll_reimbursements set amount=p_amount where id=v_id;
  end if;
  perform erp.recalculate_payroll(p.id);
  return v_id;
end;$function$;

-- ---------------------------------------------------------------- facade: settle, credit and pay opening balances
CREATE OR REPLACE FUNCTION erp.bb_manage_opening_settlement_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_op text:=upper(coalesce(nullif(btrim(p_payload->>'operation'),''),''));v_batch uuid:=(p_payload->>'batch_id')::uuid;
  b erp.opening_subledger_balances%rowtype;s erp.opening_subledger_settlements%rowtype;ctx jsonb;v_amount numeric;v_date date;
  v_reason text:=nullif(btrim(p_payload->>'reason'),'');v_kind text;v_note text;v_cash uuid;v_id uuid;v_available numeric;
  v_customer_credit erp.bb_customer_credits_v1%rowtype;v_payroll uuid;
begin
  if v_op not in('SETTLE','REVERSE','CREDIT','ALLOCATE_PAYROLL') then raise exception 'BB_OSS_OPERATION: operasi tidak dikenal';end if;
  if v_op in('SETTLE','CREDIT','ALLOCATE_PAYROLL') then
    select * into b from erp.opening_subledger_balances where id=(p_payload->>'balance_id')::uuid for update;
    ctx:=erp.bb_opening_balance_context_v1(b.id);
    if b.id is null or ctx->>'batch_id' is distinct from v_batch::text then raise exception 'BB_OSS_NOT_IN_BATCH: saldo bukan milik impor ini';end if;
  end if;
  if v_op='ALLOCATE_PAYROLL' then
    if b.party_type<>'CONTRACTOR' or b.direction<>'PAYABLE' then
      raise exception 'BB_OPENING_PAYABLE_WRONG_CONTRACTOR: hanya hutang upah/reimburse mandor yang dibayar lewat payroll';
    end if;
    v_payroll:=(p_payload->>'payroll_id')::uuid;
    perform 1 from erp.payroll_settlements where id=v_payroll for update;
    v_amount:=erp.bb_parse_amount_v1(p_payload->>'amount','amount',true);
    v_id:=erp.bb_set_opening_payable_payroll_v1(b.id,v_payroll,v_amount,(p_payload->>'expected_payroll_version')::bigint);
    return jsonb_build_object('operation',v_op,'balance_id',b.id,'payroll_id',v_payroll,'reimbursement_id',v_id,'amount',v_amount::text);
  end if;
  if v_reason is null then raise exception 'BB_OSS_REASON_REQUIRED: alasan wajib diisi';end if;
  if v_op='REVERSE' then
    select * into s from erp.opening_subledger_settlements where id=(p_payload->>'settlement_id')::uuid for update;
    select * into b from erp.opening_subledger_balances where id=s.balance_id for update;
    ctx:=erp.bb_opening_balance_context_v1(b.id);
    if s.id is null or ctx->>'batch_id' is distinct from v_batch::text then raise exception 'BB_OSS_NOT_IN_BATCH: pelunasan bukan milik impor ini';end if;
    if s.status<>'POSTED' then raise exception 'BB_OSS_NOT_POSTED: hanya pelunasan yang sudah dibukukan yang dapat dibalik';end if;
    if erp.initial_prepayment_account_v1(s.id) is not null then
      raise exception 'BB_OSS_USE_SOURCE_REVERSAL: pelunasan dari uang muka dibalik lewat uang muka asalnya';
    end if;
    if exists(select 1 from erp.bb_customer_credit_events_v1 e where e.settlement_id=s.id) then
      raise exception 'BB_OSS_USE_SOURCE_REVERSAL: pemakaian kredit pelanggan dibalik lewat kredit pelanggan asalnya';
    end if;
    perform erp.reverse_opening_subledger_settlement(s.id,v_reason);
    return jsonb_build_object('operation',v_op,'settlement_id',s.id,'status','REVERSED');
  end if;
  v_amount:=erp.bb_parse_amount_v1(p_payload->>'amount','amount');
  v_date:=erp.bb_parse_date_v1(p_payload->>'effective_date','effective_date');
  v_available:=b.original_amount-b.settled_amount-erp.bb_opening_balance_reserved_v1(b.id);
  if erp.opening_cash_advance_state_v1(b.id) is not null then
    v_available:=(erp.opening_cash_advance_state_v1(b.id)->>'available_amount')::numeric;
  end if;
  if v_amount>v_available then
    raise exception 'BB_OSS_EXCEEDS_AVAILABLE: sisa yang bebas % , diminta % (termasuk yang sudah masuk payroll)',v_available,v_amount;
  end if;
  if v_op='SETTLE' then
    select id into v_cash from erp.cash_accounts where id=(p_payload->>'cash_account_id')::uuid and is_active;
    if v_cash is null then raise exception 'BB_OSS_CASH_ACCOUNT_REQUIRED: pilih rekening kas/bank aktif';end if;
  else
    v_kind:=upper(nullif(btrim(p_payload->>'credit_kind'),''));
    v_note:=nullif(btrim(p_payload->>'credit_note_number'),'');
    if v_kind is null or v_kind not in('CUSTOMER_ALLOWANCE','SUPPLIER_ALLOWANCE','VENDOR_ALLOWANCE') then
      raise exception 'BB_CREDIT_KIND_MISMATCH: gunakan CUSTOMER_ALLOWANCE, SUPPLIER_ALLOWANCE, atau VENDOR_ALLOWANCE';
    end if;
    if v_note is null or length(v_note)>120 then raise exception 'BB_CREDIT_NOTE_REQUIRED: nomor nota kredit wajib (maksimal 120 karakter)';end if;
    if exists(select 1 from erp.bb_opening_credits_v1 c join erp.opening_subledger_settlements x on x.id=c.settlement_id
        where c.credit_kind=v_kind and lower(btrim(c.credit_note_number))=lower(v_note) and x.status<>'REVERSED') then
      raise exception 'BB_CREDIT_NOTE_DUPLICATE: nomor nota kredit sudah dipakai';
    end if;
  end if;
  insert into erp.opening_subledger_settlements(id,balance_id,settlement_number,physical_at,amount,cash_account_id,status,notes,created_by)
  values(p_request,b.id,'OSS-'||upper(substr(replace(p_request::text,'-',''),1,16)),erp.bb_physical_at_v1(v_date),v_amount,v_cash,'DRAFT',
    v_reason,erp.current_app_user_id());
  if v_op='CREDIT' then
    insert into erp.bb_opening_credits_v1(settlement_id,credit_kind,credit_note_number,reason) values(p_request,v_kind,v_note,v_reason);
  end if;
  perform erp.post_opening_subledger_settlement(p_request);
  return jsonb_build_object('operation',v_op,'settlement_id',p_request,'balance_id',b.id,'amount',v_amount::text,'effective_date',v_date,
    'remaining',(select (original_amount-settled_amount)::text from erp.opening_subledger_balances where id=b.id));
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_manage_customer_credit_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_op text:=upper(coalesce(nullif(btrim(p_payload->>'operation'),''),''));v_batch uuid:=(p_payload->>'batch_id')::uuid;
  c erp.bb_customer_credits_v1%rowtype;e erp.bb_customer_credit_events_v1%rowtype;b erp.opening_subledger_balances%rowtype;
  v_amount numeric;v_date date;v_reason text:=nullif(btrim(p_payload->>'reason'),'');v_cash uuid;v_cash_coa uuid;v_journal uuid;
  v_remaining numeric;v_floor numeric;v_available numeric;v_right_batch uuid;
begin
  if v_op not in('REFUND','APPLY_OPENING_AR','REVERSE_EVENT') then raise exception 'BB_CREDIT_OPERATION: operasi tidak dikenal';end if;
  if v_reason is null then raise exception 'BB_OSS_REASON_REQUIRED: alasan wajib diisi';end if;
  if v_op='REVERSE_EVENT' then
    select * into e from erp.bb_customer_credit_events_v1 where id=(p_payload->>'event_id')::uuid for update;
    select * into c from erp.bb_customer_credits_v1 where id=e.credit_id for update;
  else
    select * into c from erp.bb_customer_credits_v1 where id=(p_payload->>'credit_id')::uuid for update;
  end if;
  if c.id is null or c.batch_id is distinct from v_batch then raise exception 'BB_CREDIT_NOT_IN_BATCH: kredit bukan milik impor ini';end if;
  if v_op='REVERSE_EVENT' then
    if e.reversed_at is not null then raise exception 'BB_CREDIT_EVENT_REVERSED: kejadian ini sudah dibalik';end if;
    if e.event_type='REFUND' then
      perform erp._cp3_r4_reverse_journal_internal(e.journal_entry_id,v_reason);
    else
      if (select status from erp.opening_subledger_settlements where id=e.settlement_id)<>'POSTED' then
        raise exception 'BB_CREDIT_EVENT_REVERSED: pemakaian ini sudah dibalik';
      end if;
      perform erp.reverse_opening_subledger_settlement(e.settlement_id,v_reason);
    end if;
    update erp.bb_customer_credit_events_v1 set reversed_at=clock_timestamp(),reversal_reason=v_reason where id=e.id;
    return jsonb_build_object('operation',v_op,'event_id',e.id,'credit',erp.bb_customer_credit_state_v1(c.id));
  end if;
  v_amount:=erp.bb_parse_amount_v1(p_payload->>'amount','amount');
  v_date:=erp.bb_parse_date_v1(p_payload->>'effective_date','effective_date');
  if v_date<c.effective_date or v_date>erp.bb_business_today_v1() then
    raise exception 'BB_OSS_DATE_OUT_OF_RANGE: tanggal harus antara % dan hari ini',c.effective_date;
  end if;
  v_remaining:=(erp.bb_customer_credit_state_v1(c.id)->>'remaining_amount')::numeric;
  if v_amount>v_remaining then
    raise exception 'BB_RETURN_CREDIT_EXCEEDS_REMAINING: sisa kredit %, diminta %',v_remaining,v_amount;
  end if;
  if v_op='REFUND' then
    select id,coa_account_id into v_cash,v_cash_coa from erp.cash_accounts where id=(p_payload->>'cash_account_id')::uuid and is_active;
    if v_cash is null then raise exception 'BB_OSS_CASH_ACCOUNT_REQUIRED: pilih rekening kas/bank aktif';end if;
    v_journal:=erp.post_journal('BB_CUSTOMER_CREDIT_REFUND',p_request,v_date,'Pengembalian kredit retur pelanggan '||c.document_number,jsonb_build_array(
      jsonb_build_object('account_id',c.coa_account_id,'debit',v_amount,'credit',0,'customer_id',c.customer_id),
      jsonb_build_object('account_id',v_cash_coa,'debit',0,'credit',v_amount,'customer_id',c.customer_id)));
    insert into erp.bb_customer_credit_events_v1(id,credit_id,event_type,amount,effective_date,cash_account_id,journal_entry_id,reason,created_by)
    values(p_request,c.id,'REFUND',v_amount,v_date,v_cash,v_journal,v_reason,erp.current_app_user_id());
  else
    select * into b from erp.opening_subledger_balances where id=(p_payload->>'balance_id')::uuid for update;
    if b.id is null or b.party_type<>'CUSTOMER' or b.direction<>'RECEIVABLE' or b.customer_id is distinct from c.customer_id
      or erp.bb_opening_balance_context_v1(b.id)->>'batch_id' is null then
      raise exception 'BB_CREDIT_PARTY_MISMATCH: kredit hanya dipakai untuk piutang saldo awal impor milik pelanggan yang sama';
    end if;
    v_available:=b.original_amount-b.settled_amount;
    if v_amount>v_available then raise exception 'BB_OSS_EXCEEDS_AVAILABLE: sisa piutang %, diminta %',v_available,v_amount;end if;
    insert into erp.opening_subledger_settlements(id,balance_id,settlement_number,physical_at,amount,cash_account_id,status,notes,created_by)
    values(p_request,b.id,'OSS-'||upper(substr(replace(p_request::text,'-',''),1,16)),erp.bb_physical_at_v1(v_date),v_amount,null,'DRAFT',
      v_reason,erp.current_app_user_id());
    insert into erp.bb_opening_credits_v1(settlement_id,credit_kind,credit_note_number,customer_credit_id,reason)
    values(p_request,'CUSTOMER_CREDIT_APPLY',c.document_number,c.id,v_reason);
    insert into erp.bb_customer_credit_events_v1(id,credit_id,event_type,amount,effective_date,settlement_id,reason,created_by)
    values(p_request,c.id,'APPLY_OPENING_AR',v_amount,v_date,p_request,v_reason,erp.current_app_user_id());
    perform erp.post_opening_subledger_settlement(p_request);
  end if;
  v_floor:=erp.bb_customer_credit_dated_floor_v1(c.id,v_date);
  if v_floor<0 then
    raise exception 'BB_RETURN_CREDIT_DATED_CAPACITY: kredit pada % atau sesudahnya menjadi %; pemakaian tidak boleh mendahului kredit yang tersedia',v_date,v_floor;
  end if;
  return jsonb_build_object('operation',v_op,'event_id',p_request,'credit',erp.bb_customer_credit_state_v1(c.id));
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_manage_opening_sale_return_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_op text:=upper(coalesce(nullif(btrim(p_payload->>'operation'),''),''));v_batch uuid:=(p_payload->>'batch_id')::uuid;
  r erp.bb_opening_sale_return_rights_v1%rowtype;x erp.bb_opening_sale_return_receipts_v1%rowtype;
  v_reason text:=nullif(btrim(p_payload->>'reason'),'');v_qty integer;v_date date;v_at timestamptz;v_location uuid;v_root uuid;
  v_product uuid;v_received integer;v_lot uuid;v_movement uuid;v_value numeric(20,2);v_credit numeric(20,2);v_journal uuid;
  v_credit_id uuid;v_credit_journal uuid;v_used numeric;
begin
  if v_op not in('RECEIVE','REVERSE_RECEIPT') then raise exception 'BB_RETURN_OPERATION: operasi tidak dikenal';end if;
  if v_reason is null then raise exception 'BB_OSS_REASON_REQUIRED: alasan wajib diisi';end if;
  if v_op='REVERSE_RECEIPT' then
    select * into x from erp.bb_opening_sale_return_receipts_v1 where id=(p_payload->>'receipt_id')::uuid for update;
    select * into r from erp.bb_opening_sale_return_rights_v1 where id=x.right_id;
    if x.id is null or r.batch_id is distinct from v_batch then raise exception 'BB_RETURN_NOT_IN_BATCH: penerimaan retur bukan milik impor ini';end if;
    if x.status<>'POSTED' then raise exception 'BB_RETURN_ALREADY_REVERSED: penerimaan retur sudah dibatalkan';end if;
    if x.credit_id is not null then
      select coalesce(sum(e.amount),0) into v_used from erp.bb_customer_credit_events_v1 e
        left join erp.opening_subledger_settlements s on s.id=e.settlement_id
        where e.credit_id=x.credit_id and ((e.event_type='REFUND' and e.reversed_at is null) or (e.event_type='APPLY_OPENING_AR' and s.status='POSTED'));
      if v_used>0 then raise exception 'BB_RETURN_CREDIT_USED: kredit retur sudah dipakai atau dikembalikan; batalkan pemakaiannya dahulu';end if;
    end if;
    if erp.fg_lot_has_active_downstream(x.lot_id,'ADJUSTMENT','BB_OPENING_SALE_RETURN',x.id) then
      raise exception 'BB_RETURN_STOCK_CONSUMED: barang retur sudah dipakai transaksi lain; batalkan transaksi itu lebih dulu';
    end if;
    perform erp.reverse_fg_movement(x.movement_id,v_reason);
    update erp.fg_lots set lot_origin='VOIDED_PRODUCTION',is_open=false where id=x.lot_id;
    if x.value_journal_id is not null then perform erp.reverse_journal(x.value_journal_id,v_reason);end if;
    if x.credit_id is not null then
      select journal_entry_id into v_credit_journal from erp.bb_customer_credits_v1 where id=x.credit_id;
      perform erp.reverse_journal(v_credit_journal,v_reason);
      update erp.bb_customer_credits_v1 set voided_at=clock_timestamp() where id=x.credit_id;
    end if;
    update erp.bb_opening_sale_return_receipts_v1 set status='REVERSED',reversed_at=clock_timestamp(),reversal_reason=v_reason where id=x.id;
    perform erp.assert_non_po_product_hpp_target_book_v2620f(x.product_id);
    return jsonb_build_object('operation',v_op,'receipt_id',x.id,'status','REVERSED');
  end if;
  select * into r from erp.bb_opening_sale_return_rights_v1 where id=(p_payload->>'right_id')::uuid for update;
  if r.id is null or r.batch_id is distinct from v_batch then raise exception 'BB_RETURN_NOT_IN_BATCH: hak retur bukan milik impor ini';end if;
  if coalesce(p_payload->>'qty','') !~ '^[1-9][0-9]{0,8}$' then raise exception 'BB_RETURN_QTY_INVALID: jumlah pcs bilangan bulat positif';end if;
  v_qty:=(p_payload->>'qty')::integer;
  select coalesce(sum(qty_pcs),0) into v_received from erp.bb_opening_sale_return_receipts_v1 where right_id=r.id and status='POSTED';
  if v_qty>r.qty_pcs-v_received then
    raise exception 'BB_RETURN_EXCEEDS_RIGHT: hak retur tersisa % pcs, diterima %',r.qty_pcs-v_received,v_qty;
  end if;
  v_date:=erp.bb_parse_date_v1(p_payload->>'effective_date','effective_date');
  if v_date<r.cutover_date or v_date>erp.bb_business_today_v1() then
    raise exception 'BB_OSS_DATE_OUT_OF_RANGE: penerimaan retur antara % dan hari ini',r.cutover_date;
  end if;
  v_at:=erp.bb_physical_at_v1(v_date);
  select id into v_location from erp.locations where id=(p_payload->>'location_id')::uuid and is_active and location_type='FG_WAREHOUSE';
  if v_location is null then raise exception 'BB_RETURN_LOCATION_REQUIRED: pilih gudang barang jadi aktif';end if;
  -- The pieces take the version of the right's product identity in force at the receipt instant (NEW_STOCK, decision 1C).
  select coalesce(p.identity_root_id,p.id) into v_root from erp.products p where p.id=r.product_id;
  select p.id into v_product from erp.products p where coalesce(p.identity_root_id,p.id)=v_root and p.effective_from<=v_at
    and (p.effective_to is null or v_at<p.effective_to) order by p.effective_from desc,p.id limit 1;
  v_product:=coalesce(v_product,r.product_id);
  perform erp.assert_product_identity_time(v_product,v_at,'NEW_STOCK');
  perform erp.assert_non_po_product_hpp_target_book_v2620f(v_product);
  v_value:=round(r.unit_cost*v_qty,2);v_credit:=round(r.credit_unit_price*v_qty,2);
  insert into erp.fg_lots(lot_number,po_id,qc_item_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin)
  values('BBR-'||to_char(v_at at time zone 'Asia/Jakarta','YYYYMMDD')||'-'||substr(p_request::text,1,8),null,null,v_product,v_qty,0,v_at,true,'RETURN')
  returning id into v_lot;
  insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,calculation_reason,created_by)
  values(v_lot,1,'ADJUSTED',v_qty,v_value,true,'Retur penjualan lama '||r.return_number||' pada biaya hak retur',erp.current_app_user_id());
  v_movement:=erp.post_fg_movement(v_product,v_lot,v_location,'GRADE_A','ADJUSTMENT',v_qty,r.unit_cost,null,
    'BB_OPENING_SALE_RETURN',p_request,v_at,'Retur penjualan lama '||r.return_number,false);
  if v_value>0 then
    v_journal:=erp.post_journal('BB_OPENING_SALE_RETURN',p_request,v_date,'Barang retur penjualan lama '||r.return_number,jsonb_build_array(
      jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_value,'credit',0,'product_id',v_product),
      jsonb_build_object('mapping_key','COGS','debit',0,'credit',v_value)));
  end if;
  insert into erp.bb_opening_sale_return_receipts_v1(id,right_id,qty_pcs,location_id,product_id,physical_at,lot_id,movement_id,value_journal_id,
    reason,created_by)
  values(p_request,r.id,v_qty,v_location,v_product,v_at,v_lot,v_movement,v_journal,v_reason,erp.current_app_user_id());
  if v_credit>0 then
    v_credit_id:=gen_random_uuid();
    v_credit_journal:=erp.post_journal('BB_CUSTOMER_CREDIT',v_credit_id,v_date,'Kredit retur penjualan lama '||r.return_number,jsonb_build_array(
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',v_credit,'credit',0,'customer_id',r.customer_id),
      jsonb_build_object('account_id',r.credit_coa_account_id,'debit',0,'credit',v_credit,'customer_id',r.customer_id)));
    insert into erp.bb_customer_credits_v1(id,origin,batch_id,return_receipt_id,customer_id,coa_account_id,document_number,document_date,
      original_amount,settled_before_cutover,amount,effective_date,journal_entry_id,created_by)
    values(v_credit_id,'RETURN',r.batch_id,p_request,r.customer_id,r.credit_coa_account_id,r.return_number||'/'||substr(p_request::text,1,8),
      v_date,v_credit,0,v_credit,v_date,v_credit_journal,erp.current_app_user_id());
    update erp.bb_opening_sale_return_receipts_v1 set credit_id=v_credit_id where id=p_request;
  end if;
  perform erp.assert_non_po_product_hpp_target_book_v2620f(v_product);
  return jsonb_build_object('operation',v_op,'receipt_id',p_request,'lot_id',v_lot,'product_id',v_product,'qty',v_qty,
    'value',v_value::text,'credit_id',v_credit_id,'credit',v_credit::text);
end;$function$;

-- ---------------------------------------------------------------- workspace and revision parts
CREATE OR REPLACE FUNCTION erp.bb_financial_workspace_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object(
    'opening_balances',coalesce((select jsonb_agg(jsonb_build_object(
        'balance_id',b.id,'balance_type',f.balance_type,'source_kind',f.source_kind,'source_mode',f.source_mode,
        'party_type',b.party_type,'party_id',f.party_id,'party_code',coalesce(cu.customer_code,su.supplier_code,ve.vendor_code,co.contractor_code),
        'party_name',coalesce(cu.customer_name,su.supplier_name,ve.vendor_name,co.contractor_name),
        'document_number',f.document_number,'document_date',f.document_date,'due_date',f.due_date,'cutover_date',f.cutover_date,
        'original_amount',f.original_amount::text,'settled_before_cutover',f.settled_before_cutover::text,
        'opening_amount',b.original_amount::text,'settled_amount',b.settled_amount::text,
        'reserved_amount',erp.bb_opening_balance_reserved_v1(b.id)::numeric(20,2)::text,
        'remaining_amount',(b.original_amount-b.settled_amount)::text,
        'available_amount',(b.original_amount-b.settled_amount-erp.bb_opening_balance_reserved_v1(b.id))::text,'status',b.status,
        'settlements',coalesce((select jsonb_agg(jsonb_build_object('id',s.id,'number',s.settlement_number,
            'date',erp._cp3_business_date(s.physical_at),'amount',s.amount::text,'status',s.status,
            'method',case when c.settlement_id is not null then 'CREDIT' when s.cash_account_id is null then 'ADVANCE' else 'CASH' end,
            'credit_kind',c.credit_kind,'credit_note_number',c.credit_note_number,
            'reversible',s.status='POSTED' and c.credit_kind is distinct from 'CUSTOMER_CREDIT_APPLY' and s.cash_account_id is not null or
              (s.status='POSTED' and c.credit_kind in('CUSTOMER_ALLOWANCE','SUPPLIER_ALLOWANCE','VENDOR_ALLOWANCE')))
            order by s.physical_at,s.id)
          from erp.opening_subledger_settlements s left join erp.bb_opening_credits_v1 c on c.settlement_id=s.id
          where s.balance_id=b.id),'[]'::jsonb),
        'payroll_lines',coalesce((select jsonb_agg(jsonb_build_object('payroll_id',p.id,'payroll_number',p.payroll_number,'status',p.status,
            'row_version',p.row_version::text,'amount',r.amount::text) order by p.period_end,p.id)
          from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
          where r.opening_payable_balance_id=b.id and p.status<>'REVERSED'),'[]'::jsonb))
        order by f.balance_type,f.document_number,b.id)
      from erp.initial_import_financial_sources f join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id
      left join erp.customers cu on cu.id=b.customer_id left join erp.suppliers su on su.id=b.supplier_id
      left join erp.laundry_vendors ve on ve.id=b.vendor_id left join erp.contractors co on co.id=b.contractor_id
      where f.batch_id=p_batch and f.source_kind<>'CONTRACTOR_CASH_ADVANCE'),'[]'::jsonb),
    'opening_payable_payrolls',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'payroll_number',p.payroll_number,
        'contractor_id',p.contractor_id,'period_end',p.period_end,'row_version',p.row_version::text,'net_payable',p.net_payable::text)
        order by p.period_end,p.id)
      from erp.payroll_settlements p where p.status in('DRAFT','CALCULATED','REVIEW') and exists(select 1 from erp.initial_import_financial_sources f
        where f.batch_id=p_batch and f.balance_type='CONTRACTOR_PAYABLE' and f.party_id=p.contractor_id)),'[]'::jsonb),
    'legacy_documents',coalesce((select jsonb_agg(jsonb_build_object('id',d.id,'balance_type',d.balance_type,'party_id',d.party_id,
        'document_number',d.document_number,'document_date',d.document_date,'original_amount',d.original_amount::text) order by d.document_number,d.id)
      from erp.bb_legacy_documents_v1 d where d.batch_id=p_batch),'[]'::jsonb),
    'customer_credits',coalesce((select jsonb_agg(erp.bb_customer_credit_state_v1(c.id)||jsonb_build_object(
        'customer_code',cu.customer_code,'customer_name',cu.customer_name,
        'open_receivables',coalesce((select jsonb_agg(jsonb_build_object('balance_id',b.id,'document_number',f.document_number,
            'remaining_amount',(b.original_amount-b.settled_amount)::text) order by f.document_number,b.id)
          from erp.initial_import_financial_sources f join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id
          where f.balance_type='CUSTOMER_RECEIVABLE' and f.party_id=c.customer_id and b.original_amount>b.settled_amount),'[]'::jsonb),
        'events',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'kind',e.event_type,'amount',e.amount::text,'date',e.effective_date,
            'reason',e.reason,'reversed',e.reversed_at is not null or (e.event_type='APPLY_OPENING_AR'
              and (select status from erp.opening_subledger_settlements where id=e.settlement_id)<>'POSTED')) order by e.created_at,e.id)
          from erp.bb_customer_credit_events_v1 e where e.credit_id=c.id),'[]'::jsonb)) order by c.document_number,c.id)
      from erp.bb_customer_credits_v1 c join erp.customers cu on cu.id=c.customer_id where c.batch_id=p_batch),'[]'::jsonb),
    'sale_return_rights',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'return_number',r.return_number,
        'customer_code',cu.customer_code,'invoice_document_number',r.invoice_document_number,
        'invoice_state',case when r.invoice_source_id is not null then 'OPEN' else 'SETTLED_BEFORE_CUTOVER' end,
        'product_sku',p.sku,'qty_pcs',r.qty_pcs,'credit_unit_price',r.credit_unit_price::text,'unit_cost',r.unit_cost::text,
        'received_pcs',coalesce((select sum(x.qty_pcs) from erp.bb_opening_sale_return_receipts_v1 x where x.right_id=r.id and x.status='POSTED'),0),
        'receipts',coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'qty_pcs',x.qty_pcs,'date',erp._cp3_business_date(x.physical_at),
            'status',x.status,'credit_id',x.credit_id) order by x.physical_at,x.id)
          from erp.bb_opening_sale_return_receipts_v1 x where x.right_id=r.id),'[]'::jsonb)) order by r.return_number,r.id)
      from erp.bb_opening_sale_return_rights_v1 r join erp.customers cu on cu.id=r.customer_id join erp.products p on p.id=r.product_id
      where r.batch_id=p_batch),'[]'::jsonb),
    'fg_locations',coalesce((select jsonb_agg(jsonb_build_object('id',l.id,'code',l.location_code,'name',l.location_name) order by l.location_code)
      from erp.locations l where l.is_active and l.location_type='FG_WAREHOUSE'),'[]'::jsonb))
$function$;

CREATE OR REPLACE FUNCTION erp.bb_financial_revision_part_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object(
    'balances',coalesce((select jsonb_agg(to_jsonb(b) order by b.id) from erp.opening_subledger_balances b
      join erp.initial_import_financial_sources f on f.opening_item_id=b.opening_item_id where f.batch_id=p_batch),'[]'::jsonb),
    'settlements',coalesce((select jsonb_agg(to_jsonb(s) order by s.id) from erp.opening_subledger_settlements s
      join erp.opening_subledger_balances b on b.id=s.balance_id join erp.initial_import_financial_sources f on f.opening_item_id=b.opening_item_id
      where f.batch_id=p_batch),'[]'::jsonb),
    'payroll_lines',coalesce((select jsonb_agg(to_jsonb(r) order by r.id) from erp.payroll_reimbursements r
      join erp.opening_subledger_balances b on b.id=r.opening_payable_balance_id
      join erp.initial_import_financial_sources f on f.opening_item_id=b.opening_item_id where f.batch_id=p_batch),'[]'::jsonb),
    'credits',coalesce((select jsonb_agg(to_jsonb(c) order by c.id) from erp.bb_customer_credits_v1 c where c.batch_id=p_batch),'[]'::jsonb),
    'credit_events',coalesce((select jsonb_agg(to_jsonb(e) order by e.id) from erp.bb_customer_credit_events_v1 e
      join erp.bb_customer_credits_v1 c on c.id=e.credit_id where c.batch_id=p_batch),'[]'::jsonb),
    'return_receipts',coalesce((select jsonb_agg(to_jsonb(x) order by x.id) from erp.bb_opening_sale_return_receipts_v1 x
      join erp.bb_opening_sale_return_rights_v1 r on r.id=x.right_id where r.batch_id=p_batch),'[]'::jsonb))
$function$;

do $grants$
declare f text;
begin
  for f in select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='erp' and p.proname like 'bb\_%' loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
  end loop;
end $grants$;
