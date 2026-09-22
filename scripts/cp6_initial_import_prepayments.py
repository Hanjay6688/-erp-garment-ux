"""Opening prepayments use real payment lifecycles without historical cash.

Proposal installed only in the rolled-back AO/AP native trial. Native payment
rows/facts keep their original shape; a private immutable link records funding.
"""
import json
from pathlib import Path

PREDECESSOR = json.loads(Path('docs/evidence/cp6-initial-import-prepayment-predecessor.json').read_text())['functions']

SCHEMA = r"""
create table erp.initial_import_prepayments(
 id uuid primary key default gen_random_uuid(),batch_id uuid not null references erp.migration_batches(id),
 source_row_id uuid not null unique references erp.migration_staging_rows(id),
 party_type text not null check(party_type in('SUPPLIER','CUSTOMER','VENDOR')),party_id uuid not null,
 supplier_id uuid references erp.suppliers(id),customer_id uuid references erp.customers(id),vendor_id uuid references erp.laundry_vendors(id),
 coa_account_id uuid not null references erp.chart_accounts(id),
 document_number text not null check(length(btrim(document_number)) between 1 and 120),
 document_date date not null,cutover_date date not null check(document_date<=cutover_date),
 original_amount numeric(20,2) not null,settled_before_cutover numeric(20,2) not null,amount numeric(20,2) not null,
 created_at timestamptz not null default statement_timestamp(),
 check(original_amount>0 and settled_before_cutover>=0 and amount>0 and original_amount-settled_before_cutover=amount),
 check(num_nonnulls(supplier_id,customer_id,vendor_id)=1 and party_id=coalesce(supplier_id,customer_id,vendor_id)
   and ((party_type='SUPPLIER' and supplier_id is not null) or (party_type='CUSTOMER' and customer_id is not null) or (party_type='VENDOR' and vendor_id is not null)))
);
create unique index initial_import_prepayment_document on erp.initial_import_prepayments(party_type,party_id,lower(btrim(document_number)));
create index initial_import_prepayment_batch on erp.initial_import_prepayments(batch_id);
create index initial_import_prepayment_account on erp.initial_import_prepayments(coa_account_id);
create table erp.initial_import_prepayment_payments(
 payment_id uuid primary key,advance_id uuid not null references erp.initial_import_prepayments(id),
 supplier_payment_id uuid unique references erp.supplier_payments(id),
 sales_payment_id uuid unique references erp.sales_payments(id),
 vendor_payment_id uuid unique references erp.vendor_payments(id),
 opening_settlement_id uuid unique references erp.opening_subledger_settlements(id),
 payment_snapshot jsonb not null,created_at timestamptz not null default statement_timestamp(),
 check(num_nonnulls(supplier_payment_id,sales_payment_id,vendor_payment_id,opening_settlement_id)=1
   and payment_id=coalesce(supplier_payment_id,sales_payment_id,vendor_payment_id,opening_settlement_id))
);
create index initial_import_prepayment_payment_source on erp.initial_import_prepayment_payments(advance_id);
create table erp.initial_import_prepayment_events(
 id uuid primary key default gen_random_uuid(),advance_id uuid not null references erp.initial_import_prepayments(id),
 event_type text not null check(event_type in('CORRECTION','REFUND','REVERSAL')),
 component text not null check(component in('CORRECTION','REFUND')),delta numeric(20,2) not null check(delta<>0),
 effective_date date not null,reason text not null check(length(btrim(reason))>0),
 cash_account_id uuid references erp.cash_accounts(id),
 reverses_event_id uuid unique references erp.initial_import_prepayment_events(id),
 journal_entry_id uuid not null unique references erp.journal_entries(id),
 created_by uuid not null references erp.app_users(id),created_at timestamptz not null default statement_timestamp(),
 check((event_type='REVERSAL' and reverses_event_id is not null) or
   (event_type=component and reverses_event_id is null and (component<>'REFUND' or delta<0))),
 check((component='REFUND' and cash_account_id is not null) or (component='CORRECTION' and cash_account_id is null))
);
create index initial_import_prepayment_event_source on erp.initial_import_prepayment_events(advance_id);
alter table erp.initial_import_prepayments enable row level security;
alter table erp.initial_import_prepayment_payments enable row level security;
alter table erp.initial_import_prepayment_events enable row level security;
revoke all on erp.initial_import_prepayments,erp.initial_import_prepayment_payments,erp.initial_import_prepayment_events from public,anon,authenticated,service_role;
alter table erp.supplier_payments alter column cash_account_id drop not null;
alter table erp.opening_subledger_settlements alter column cash_account_id drop not null;
alter table erp.supplier_payments add constraint supplier_prepayment_funding_check
 check(cash_account_id is not null or payment_method is not distinct from 'OPENING_ADVANCE');
alter table erp.sales_payment_posting_facts alter column cash_account_id drop not null;
alter table erp.sales_payment_posting_facts add constraint sales_prepayment_fact_funding_check
 check(cash_account_id is not null or payment_snapshot->>'payment_method' is not distinct from 'OPENING_ADVANCE');
"""

PAYMENTS = r"""CREATE OR REPLACE FUNCTION erp.initial_prepayment_payments_v1(p_advance_id uuid)
RETURNS TABLE(payment_id uuid,target_id uuid,party_id uuid,party_type text,number text,status text,amount numeric,
 payment_date timestamptz,cash_account_id uuid,source_type text,payment_snapshot jsonb)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' SET TimeZone TO 'UTC' AS $function$
 select p.id,p.purchase_id,h.supplier_id,'SUPPLIER'::text,p.payment_number::text,p.status::text,p.amount,p.payment_date,p.cash_account_id,'SUPPLIER_PAYMENT'::text,to_jsonb(p)-'status'
 from erp.initial_import_prepayment_payments l join erp.supplier_payments p on p.id=l.supplier_payment_id
 join erp.material_purchase_headers h on h.id=p.purchase_id where l.advance_id=p_advance_id
 union all
 select p.id,p.sale_id,h.customer_id,'CUSTOMER',p.payment_number::text,p.status::text,p.amount,p.payment_date,p.cash_account_id,'SALES_PAYMENT',to_jsonb(p)-'status'
 from erp.initial_import_prepayment_payments l join erp.sales_payments p on p.id=l.sales_payment_id
 join erp.sales_headers h on h.id=p.sale_id where l.advance_id=p_advance_id
 union all
 select p.id,p.vendor_invoice_id,h.vendor_id,'VENDOR',p.payment_number::text,p.status::text,p.amount,p.payment_date,p.cash_account_id,'VENDOR_PAYMENT',to_jsonb(p)-'status'
 from erp.initial_import_prepayment_payments l join erp.vendor_payments p on p.id=l.vendor_payment_id
 join erp.vendor_invoices h on h.id=p.vendor_invoice_id where l.advance_id=p_advance_id
 union all
 select p.id,p.balance_id,coalesce(h.supplier_id,h.customer_id,h.vendor_id),h.party_type::text,p.settlement_number::text,p.status::text,p.amount,p.physical_at,p.cash_account_id,
   'OPENING_SUBLEDGER_SETTLEMENT',(to_jsonb(p)-'status'-'updated_at')||jsonb_build_object('payment_method','OPENING_ADVANCE')
 from erp.initial_import_prepayment_payments l join erp.opening_subledger_settlements p on p.id=l.opening_settlement_id
 join erp.opening_subledger_balances h on h.id=p.balance_id where l.advance_id=p_advance_id;
$function$;
"""

STATE = r"""CREATE OR REPLACE FUNCTION erp.initial_prepayment_state_v1(p_advance_id uuid)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select jsonb_build_object('id',a.id,'party_type',a.party_type,'party_id',a.party_id,'document_number',a.document_number,
   'document_date',a.document_date,'cutover_date',a.cutover_date,'original_amount',a.original_amount::text,
   'settled_before_cutover',a.settled_before_cutover::text,'opening_amount',(a.amount+e.corrected)::numeric(20,2)::text,
   'applied_amount',p.applied::numeric(20,2)::text,'refunded_amount',(-e.refunded)::numeric(20,2)::text,
   'remaining_amount',(a.amount+e.corrected+e.refunded-p.applied)::numeric(20,2)::text)
 from erp.initial_import_prepayments a
 cross join lateral(select coalesce(sum(delta) filter(where component='CORRECTION'),0) corrected,
   coalesce(sum(delta) filter(where component='REFUND'),0) refunded from erp.initial_import_prepayment_events where advance_id=a.id) e
 cross join lateral(select coalesce(sum(amount),0) applied from erp.initial_prepayment_payments_v1(a.id) where status='POSTED') p
 where a.id=p_advance_id;
$function$;
"""

FUNDING = r"""CREATE OR REPLACE FUNCTION erp.initial_prepayment_funding_v1(
 p_payment_id uuid,p_kind text,p_party uuid,p_amount numeric,p_date date,p_target_date date)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare a erp.initial_import_prepayments%rowtype;l erp.initial_import_prepayment_payments%rowtype;c erp.chart_accounts%rowtype;p record;
begin
 perform erp.require_internal();
 select * into l from erp.initial_import_prepayment_payments where payment_id=p_payment_id;
 if l.payment_id is null then return null;end if;
 select * into a from erp.initial_import_prepayments where id=l.advance_id for update;
 select * into p from erp.initial_prepayment_payments_v1(a.id) where payment_id=p_payment_id;
 if a.id is null or a.party_type<>p_kind or a.party_id<>p_party or p.party_type<>a.party_type or p.party_id<>a.party_id
   or p.amount<>p_amount or p.status<>'DRAFT' or p.cash_account_id is not null
   or p.payment_snapshot is distinct from l.payment_snapshot or p.payment_snapshot->>'payment_method' is distinct from 'OPENING_ADVANCE'
   or not exists(select 1 from erp.migration_batches where id=a.batch_id and status='POSTED') then
   raise exception 'Sumber uang muka tidak cocok dengan pihak dan pembayaran tagihan';end if;
 if p_date is null or p_target_date is null or p_date<greatest(a.cutover_date,p_target_date)
   or p_date>erp._cp3_business_date(statement_timestamp()) then raise exception 'Tanggal pemakaian uang muka harus sejak saldo awal dan tagihan, sampai hari ini';end if;
 if p_amount<=0 or p_amount>(erp.initial_prepayment_state_v1(a.id)->>'remaining_amount')::numeric then
   raise exception 'Pemakaian melebihi sisa uang muka';end if;
 select * into c from erp.chart_accounts where id=a.coa_account_id;
 if not(c.is_active and c.is_postable) or c.account_type<>case when a.party_type='CUSTOMER' then 'LIABILITY' else 'ASSET' end
   or c.normal_balance<>case when a.party_type='CUSTOMER' then 'CREDIT' else 'DEBIT' end
   or exists(select 1 from erp.cash_accounts where coa_account_id=c.id)
   or exists(select 1 from erp.accounting_account_mappings where account_id=c.id) then raise exception 'Akun uang muka harus akun khusus aktif sesuai jenis pihak';end if;
 return a.coa_account_id;
end;$function$;
"""

IMMUTABLE = r"""CREATE OR REPLACE FUNCTION erp.guard_initial_prepayment_immutable_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $function$
begin raise exception 'Riwayat uang muka tetap; gunakan koreksi atau pembatalan tertaut';end;$function$;
"""

PAYMENT_GUARD = r"""CREATE OR REPLACE FUNCTION erp.guard_initial_prepayment_payment_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $function$
begin
 if TG_TABLE_NAME='opening_subledger_settlements' then
   if TG_OP='DELETE' then
     if old.cash_account_id is null then raise exception 'Pemakaian uang muka tetap; gunakan pembatalan tertaut';end if;return old;
   end if;
   if new.cash_account_id is not null and (TG_OP='INSERT' or old.cash_account_id is not null) then return new;end if;
   if current_user<>'postgres' or new.cash_account_id is not null or
     (TG_OP='UPDATE' and to_jsonb(new)-'status'-'updated_at' is distinct from to_jsonb(old)-'status'-'updated_at') then
     raise exception 'Pelunasan saldo awal dari uang muka harus melalui command resmi dan identitasnya tetap';end if;
   return new;
 end if;
 if TG_OP='DELETE' then
   if old.payment_method='OPENING_ADVANCE' then raise exception 'Riwayat pemakaian uang muka tidak dapat dihapus';end if;return old;
 end if;
 if new.payment_method is distinct from 'OPENING_ADVANCE' and (TG_OP='INSERT' or old.payment_method is distinct from 'OPENING_ADVANCE') then return new;end if;
 if current_user<>'postgres' then raise exception 'Uang muka harus melalui command resmi';end if;
 if new.payment_method is distinct from 'OPENING_ADVANCE' or new.cash_account_id is not null
   or (TG_OP='UPDATE' and to_jsonb(new)-'status' is distinct from to_jsonb(old)-'status') then
   raise exception 'Identitas pembayaran uang muka bersifat tetap';end if;
 if TG_OP='INSERT' and new.status<>'DRAFT' then raise exception 'Pembayaran uang muka dibuat draft sebelum diposting';end if;
 if TG_OP='UPDATE' and not((old.status='DRAFT' and new.status='POSTED') or (old.status='POSTED' and new.status='REVERSED') or old.status=new.status) then
   raise exception 'Status pembayaran uang muka tidak sah';end if;
 return new;
end;$function$;
"""

TRIGGERS = '\n'.join(
 f'create trigger initial_prepayment_immutable before update or delete on erp.{table} for each row execute function erp.guard_initial_prepayment_immutable_v1();'
 for table in ['initial_import_prepayments','initial_import_prepayment_payments','initial_import_prepayment_events'])+'\n'+ '\n'.join(
 f'create trigger initial_prepayment_payment_guard before insert or update or delete on erp.{table} for each row execute function erp.guard_initial_prepayment_payment_v1();'
 for table in ['supplier_payments','sales_payments','vendor_payments','opening_subledger_settlements'])

CHECK = r"""CREATE OR REPLACE FUNCTION erp.check_initial_prepayment_v1(p_batch_id uuid,p_row_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD' AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;c jsonb;v_cutover date;v_party uuid;v_account uuid;
 v_table text;v_code text;v_entity text;k text;v_number text;v_value numeric;
begin
 perform erp.require_owner_admin();
 select * into r from erp.migration_staging_rows where id=p_row_id and batch_id=p_batch_id and entity_type='OPENING_ADVANCE';
 if r.id is null then raise exception 'Baris uang muka tidak ditemukan';end if;j:=r.normalized_payload;
 foreach k in array array['party_type','party_code','coa_account_code','document_number','document_date','original_amount','settled_before_cutover','amount','control_key'] loop
   if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk uang muka',k;end if;
 end loop;
 if j->>'party_type' not in('SUPPLIER','CUSTOMER','VENDOR') then raise exception 'party_type: gunakan SUPPLIER, CUSTOMER, atau VENDOR';end if;
 v_number:=btrim(j->>'document_number');if length(v_number)>120 then raise exception 'document_number: maksimal 120 karakter';end if;
 select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch_id;
 if j->>'document_date' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' or (j->>'document_date')::date::text<>j->>'document_date'
   or (j->>'document_date')::date>v_cutover then raise exception 'document_date: tanggal valid tidak boleh melewati saldo awal';end if;
 foreach k in array array['original_amount','settled_before_cutover','amount'] loop
   v_value:=(j->>k)::numeric;
   if v_value::text in('NaN','Infinity','-Infinity') or v_value<0 or v_value<>round(v_value,2) then raise exception '%: nominal harus tepat dua desimal dan nonnegatif',k;end if;
   perform v_value::numeric(20,2);
 end loop;
 if (j->>'amount')::numeric<=0 or (j->>'original_amount')::numeric-(j->>'settled_before_cutover')::numeric<>(j->>'amount')::numeric then
   raise exception 'amount: sisa positif harus sama dengan uang muka asal dikurangi pemakaian/pengembalian lama';end if;
 v_table:=case j->>'party_type' when 'SUPPLIER' then 'suppliers' when 'CUSTOMER' then 'customers' else 'laundry_vendors' end;
 v_code:=case j->>'party_type' when 'SUPPLIER' then 'supplier_code' when 'CUSTOMER' then 'customer_code' else 'vendor_code' end;
 v_entity:=case j->>'party_type' when 'VENDOR' then 'LAUNDRY_VENDOR' else j->>'party_type' end;
 execute format('select id from erp.%I where %I=$1 and is_active',v_table,v_code) into v_party using j->>'party_code';
 if v_party is null and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type=v_entity
   and validation_status='VALID' and normalized_payload->>v_code=j->>'party_code'
   and coalesce(nullif(normalized_payload->>'is_active','')::boolean,true)) then raise exception 'party_code: pihak aktif tidak ditemukan';end if;
 select id,to_jsonb(a) into v_account,c from erp.chart_accounts a where account_code=j->>'coa_account_code';
 if v_account is null then
   select normalized_payload into c from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='CHART_ACCOUNT'
     and validation_status='VALID' and normalized_payload->>'account_code'=j->>'coa_account_code';
 end if;
 if c is null or c->>'account_type' is distinct from case when j->>'party_type'='CUSTOMER' then 'LIABILITY' else 'ASSET' end
   or c->>'normal_balance' is distinct from case when j->>'party_type'='CUSTOMER' then 'CREDIT' else 'DEBIT' end
   or not coalesce(nullif(c->>'is_active','')::boolean,true) or not coalesce(nullif(c->>'is_postable','')::boolean,true)
   or exists(select 1 from erp.cash_accounts where coa_account_id=v_account)
   or exists(select 1 from erp.accounting_account_mappings where account_id=v_account)
   or exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='CASH_ACCOUNT'
     and normalized_payload->>'coa_account_code'=j->>'coa_account_code') then
   raise exception 'coa_account_code: gunakan akun khusus uang muka aktif, aset untuk supplier/vendor atau kewajiban untuk pelanggan';end if;
 if v_account is not null and not exists(select 1 from erp.initial_import_prepayments where coa_account_id=v_account)
   and exists(select 1 from erp.journal_lines where account_id=v_account) then
   raise exception 'coa_account_code: akun ini sudah memiliki saldo tanpa sumber uang muka; rekonsiliasi dahulu';end if;
 if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='OPENING_ADVANCE' and s.id<>r.id
   and s.normalized_payload->>'party_type'=j->>'party_type' and s.normalized_payload->>'party_code'=j->>'party_code'
   and lower(btrim(s.normalized_payload->>'document_number'))=lower(v_number))
   or exists(select 1 from erp.initial_import_prepayments where party_type=j->>'party_type' and party_id=v_party
     and lower(btrim(document_number))=lower(v_number) and source_row_id<>r.id) then raise exception 'document_number: uang muka sudah dicatat';end if;
 return jsonb_build_object('party_id',v_party,'coa_account_id',v_account,'cutover_date',v_cutover);
end;$function$;
"""

VALIDATE = r"""CREATE OR REPLACE FUNCTION erp.validate_initial_prepayments_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare r record;
begin
 perform erp.require_owner_admin();
 for r in select id from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_ADVANCE' order by source_row_no loop
   begin
     perform erp.check_initial_prepayment_v1(p_batch_id,r.id);
     update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
   exception when others then
     update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;
   end;
 end loop;
end;$function$;
"""

IMPORT = r"""CREATE OR REPLACE FUNCTION erp.apply_initial_prepayments_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare r record;j jsonb;c jsonb;v_id uuid;v_amount numeric;v_customer uuid;v_vendor uuid;
begin
 perform erp.require_owner_admin();
 for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_ADVANCE'
   and posted_entity_id is null order by source_row_no loop
   if r.validation_status<>'VALID' then raise exception 'Uang muka belum lolos pemeriksaan';end if;j:=r.normalized_payload;
   -- Lock normalized source identity before revalidation, including other batches.
   perform pg_advisory_xact_lock(hashtextextended('INITIAL_PREPAYMENT:'||(j->>'party_type')||':'||(j->>'party_code')||':'||lower(btrim(j->>'document_number')),0));
   c:=erp.check_initial_prepayment_v1(p_batch_id,r.id);
   if c->>'party_id' is null or c->>'coa_account_id' is null then raise exception 'Master uang muka belum tersedia';end if;
   insert into erp.initial_import_prepayments(batch_id,source_row_id,party_type,party_id,supplier_id,customer_id,vendor_id,coa_account_id,document_number,document_date,cutover_date,original_amount,settled_before_cutover,amount)
   values(p_batch_id,r.id,j->>'party_type',(c->>'party_id')::uuid,
     case when j->>'party_type'='SUPPLIER' then (c->>'party_id')::uuid end,
     case when j->>'party_type'='CUSTOMER' then (c->>'party_id')::uuid end,
     case when j->>'party_type'='VENDOR' then (c->>'party_id')::uuid end,
     (c->>'coa_account_id')::uuid,btrim(j->>'document_number'),
     (j->>'document_date')::date,(c->>'cutover_date')::date,(j->>'original_amount')::numeric,(j->>'settled_before_cutover')::numeric,(j->>'amount')::numeric)
   returning id into v_id;
   v_amount:=(j->>'amount')::numeric;
   v_customer:=case when j->>'party_type'='CUSTOMER' then (c->>'party_id')::uuid end;
   v_vendor:=case when j->>'party_type'='VENDOR' then (c->>'party_id')::uuid end;
   perform erp.post_journal('OPENING_PREPAYMENT',v_id,(c->>'cutover_date')::date,'Uang muka tersisa sebelum ERP',jsonb_build_array(
     jsonb_build_object('account_id',c->>'coa_account_id','debit',case when v_customer is null then v_amount else 0 end,
       'credit',case when v_customer is null then 0 else v_amount end,'customer_id',v_customer,'vendor_id',v_vendor),
     jsonb_build_object('mapping_key','OPENING_EQUITY','debit',case when v_customer is null then 0 else v_amount end,
       'credit',case when v_customer is null then v_amount else 0 end,'customer_id',v_customer,'vendor_id',v_vendor)));
   update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type='OPENING_ADVANCE' where id=r.id;
 end loop;
end;$function$;
"""

TARGETS = r"""CREATE OR REPLACE FUNCTION erp.initial_prepayment_targets_v1(p_advance_id uuid)
RETURNS TABLE(id uuid,number text,party_id uuid,party_type text,remaining_amount text,target_date date,target_kind text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select h.id,h.purchase_number::text,h.supplier_id,'SUPPLIER'::text,
   (erp.material_purchase_payable_total(h.id)-coalesce((select sum(amount) from erp.supplier_payments where purchase_id=h.id and status='POSTED'),0))::numeric(20,2)::text,
   greatest(erp._cp3_business_date(h.physical_at),(select max(i.invoice_date) from erp.material_supplier_invoices i
     join erp.material_supplier_invoice_lines l on l.invoice_id=i.id join erp.material_purchase_items pi on pi.id=l.purchase_item_id where pi.purchase_id=h.id and i.status='POSTED')),'DOCUMENT'::text
 from erp.material_purchase_headers h join erp.initial_import_prepayments a on a.id=p_advance_id and a.party_type='SUPPLIER' and a.party_id=h.supplier_id
 where h.status='POSTED'
 union all
 select h.id,h.sale_number::text,h.customer_id,'CUSTOMER',
   (round(erp.sale_net_total(h.id),2)-coalesce((select sum(amount) from erp.sales_payments where sale_id=h.id and status='POSTED'),0))::numeric(20,2)::text,
   erp._cp3_business_date(h.sale_date),'DOCUMENT'
 from erp.sales_headers h join erp.initial_import_prepayments a on a.id=p_advance_id and a.party_type='CUSTOMER' and a.party_id=h.customer_id
 where h.status in('POSTED','PARTIAL_PAID','PAID')
 union all
 select h.id,h.invoice_number::text,h.vendor_id,'VENDOR',
   (h.total_amount-coalesce((select sum(amount) from erp.vendor_payments where vendor_invoice_id=h.id and status='POSTED'),0))::numeric(20,2)::text,h.invoice_date,'DOCUMENT'
 from erp.vendor_invoices h join erp.initial_import_prepayments a on a.id=p_advance_id and a.party_type='VENDOR' and a.party_id=h.vendor_id
 where h.status in('POSTED','PARTIAL_PAID','PAID')
 union all
 select b.id,coalesce(s.document_number,h.opening_number)||' · saldo awal',a.party_id,a.party_type,
   (b.original_amount-b.settled_amount)::numeric(20,2)::text,h.opening_date,'OPENING'
 from erp.initial_import_prepayments a join erp.opening_subledger_balances b on b.party_type=a.party_type
   and coalesce(b.supplier_id,b.customer_id,b.vendor_id)=a.party_id
 join erp.opening_balance_items oi on oi.id=b.opening_item_id
 join erp.opening_balance_headers h on h.id=oi.opening_id and h.status='POSTED'
 left join erp.initial_import_financial_sources s on s.opening_item_id=b.opening_item_id
 where a.id=p_advance_id and b.direction=case when a.party_type='CUSTOMER' then 'RECEIVABLE' else 'PAYABLE' end;
$function$;
"""

COMMAND = r"""CREATE OR REPLACE FUNCTION erp.manage_initial_prepayment_v1(p_payload jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD' SET TimeZone TO 'UTC' AS $function$
declare a erp.initial_import_prepayments%rowtype;e erp.initial_import_prepayment_events%rowtype;
 v_op text:=p_payload->>'operation';v_table text;v_parent text;v_fk text;v_link text;v_rpc text;
 v_payment uuid;v_target uuid;v_id uuid;v_journal uuid;v_cash uuid;v_cash_coa uuid;v_locked uuid;
 v_amount numeric;v_delta numeric;v_debit numeric;v_date date;v_reason text;v_customer uuid;v_vendor uuid;
 v_snapshot jsonb;v_state jsonb;v_target_state record;v_payment_at timestamptz;
begin
 perform erp.require_owner_admin();
 if v_op is null or v_op not in('APPLY','REVERSE_PAYMENT','REFUND','CORRECT','REVERSE_EVENT') then raise exception 'Operasi uang muka tidak dikenal';end if;
 v_reason:=nullif(btrim(p_payload->>'reason'),'');if v_reason is null then raise exception 'Alasan pemakaian/perubahan uang muka wajib diisi';end if;
 select * into a from erp.initial_import_prepayments where id=(p_payload->>'advance_id')::uuid and batch_id=(p_payload->>'batch_id')::uuid;
 if a.id is null then raise exception 'Uang muka bukan milik batch ini';end if;
 v_table:=case a.party_type when 'SUPPLIER' then 'supplier_payments' when 'CUSTOMER' then 'sales_payments' else 'vendor_payments' end;
 v_parent:=case a.party_type when 'SUPPLIER' then 'material_purchase_headers' when 'CUSTOMER' then 'sales_headers' else 'vendor_invoices' end;
 v_fk:=case a.party_type when 'SUPPLIER' then 'purchase_id' when 'CUSTOMER' then 'sale_id' else 'vendor_invoice_id' end;
 v_link:=case a.party_type when 'SUPPLIER' then 'supplier_payment_id' when 'CUSTOMER' then 'sales_payment_id' else 'vendor_payment_id' end;
 v_rpc:=case a.party_type when 'SUPPLIER' then 'supplier_payment' when 'CUSTOMER' then 'sales_payment' else 'vendor_payment' end;
 -- Match native lock order: payment (when existing), document, then funding.
 if v_op='REVERSE_PAYMENT' then
   v_payment:=(p_payload->>'payment_id')::uuid;
   if not exists(select 1 from erp.initial_import_prepayment_payments where payment_id=v_payment and advance_id=a.id) then raise exception 'Pembayaran bukan pemakaian uang muka ini';end if;
   if exists(select 1 from erp.initial_import_prepayment_payments where payment_id=v_payment and opening_settlement_id is not null) then
     v_table:='opening_subledger_settlements';v_parent:='opening_subledger_balances';v_fk:='balance_id';v_link:='opening_settlement_id';v_rpc:='opening_subledger_settlement';end if;
   execute format('select to_jsonb(p) from erp.%I p where id=$1 for update',v_table) into v_snapshot using v_payment;
   v_target:=(v_snapshot->>v_fk)::uuid;
 elsif v_op='APPLY' then
   v_target:=(p_payload->>'target_id')::uuid;
   select * into v_target_state from erp.initial_prepayment_targets_v1(a.id) where id=v_target;
   if v_target_state.id is null then raise exception 'Tagihan pihak ini tidak ditemukan';end if;
   if v_target_state.target_kind='OPENING' then
     v_table:='opening_subledger_settlements';v_parent:='opening_subledger_balances';v_fk:='balance_id';v_link:='opening_settlement_id';v_rpc:='opening_subledger_settlement';end if;
 end if;
 if v_target is not null then execute format('select id from erp.%I where id=$1 for update',v_parent) into v_locked using v_target;
   if v_locked is null then raise exception 'Tagihan tujuan tidak ditemukan';end if;
 end if;
 select * into a from erp.initial_import_prepayments where id=a.id for update;
 if p_payload->>'expected_revision' is distinct from erp.initial_import_revision_v1(a.batch_id) then raise exception 'STALE_VERSION: saldo atau tagihan berubah; muat ulang';end if;
 v_state:=erp.initial_prepayment_state_v1(a.id);
 if v_op in('APPLY','REFUND','CORRECT') then
   if coalesce(p_payload->>'amount','') !~ '^[0-9]+([.,][0-9]{1,2})?$' then raise exception 'amount: isi nominal tepat dua desimal tanpa pemisah ribuan';end if;
   v_amount:=replace(p_payload->>'amount',',','.')::numeric;perform v_amount::numeric(20,2);
   if v_amount<=0 and v_op<>'CORRECT' then raise exception 'Nominal harus positif';end if;
   if coalesce(p_payload->>'effective_date','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'Tanggal wajib YYYY-MM-DD';end if;
   v_date:=(p_payload->>'effective_date')::date;
   if v_date::text<>p_payload->>'effective_date' or v_date<a.cutover_date or v_date>erp._cp3_business_date(statement_timestamp()) then raise exception 'Tanggal harus sejak saldo awal sampai hari ini';end if;
 end if;
 if v_op='APPLY' then
   select * into v_target_state from erp.initial_prepayment_targets_v1(a.id) where id=v_target;
   if v_target_state.id is null or v_amount>(v_target_state.remaining_amount)::numeric then raise exception 'Tagihan pihak yang sama harus memiliki sisa mencukupi';end if;
   if v_date<v_target_state.target_date then raise exception 'Pemakaian uang muka tidak boleh mendahului tagihan';end if;
   if v_amount>(v_state->>'remaining_amount')::numeric then raise exception 'Pemakaian melebihi sisa uang muka';end if;
   v_payment:=gen_random_uuid();v_payment_at:=(v_date::timestamp+interval '12 hours') at time zone 'Asia/Jakarta';
   if v_link='opening_settlement_id' then
     insert into erp.opening_subledger_settlements(id,balance_id,settlement_number,physical_at,amount,cash_account_id,notes,created_by)
     values(v_payment,v_target,'ADV-'||v_payment::text,v_payment_at,v_amount,null,v_reason,erp.current_app_user_id())
     returning (to_jsonb(opening_subledger_settlements)-'status'-'updated_at')||jsonb_build_object('payment_method','OPENING_ADVANCE') into v_snapshot;
   else
     execute format('insert into erp.%I(id,%I,payment_number,payment_date,amount,cash_account_id,payment_method,notes,created_by) values($1,$2,$3,$4,$5,null,''OPENING_ADVANCE'',$6,erp.current_app_user_id()) returning to_jsonb(%I)-''status''',v_table,v_fk,v_table)
       into v_snapshot using v_payment,v_target,'ADV-'||v_payment::text,v_payment_at,v_amount,v_reason;
   end if;
   execute format('insert into erp.initial_import_prepayment_payments(payment_id,advance_id,%I,payment_snapshot) values($1,$2,$1,$3)',v_link)
     using v_payment,a.id,v_snapshot;
   execute format('select erp.%I($1)','post_'||v_rpc) using v_payment;
 elsif v_op='REVERSE_PAYMENT' then
   execute format('select erp.%I($1,$2)','reverse_'||v_rpc) using v_payment,v_reason;
 else
   v_id:=gen_random_uuid();
   v_customer:=case when a.party_type='CUSTOMER' then a.party_id end;v_vendor:=case when a.party_type='VENDOR' then a.party_id end;
   if v_op='REVERSE_EVENT' then
     select * into e from erp.initial_import_prepayment_events where id=(p_payload->>'event_id')::uuid and advance_id=a.id;
     if e.id is null or e.event_type='REVERSAL' or exists(select 1 from erp.initial_import_prepayment_events where reverses_event_id=e.id) then raise exception 'Perubahan tidak ditemukan atau sudah dibatalkan';end if;
     v_delta:=-e.delta;
     if (v_state->>'remaining_amount')::numeric+v_delta<0 then raise exception 'Pembatalan mengurangi uang muka di bawah pemakaian; batalkan pemakaiannya dahulu';end if;
     v_journal:=erp._cp3_r4_reverse_journal_internal(e.journal_entry_id,v_reason);
     select economic_date into v_date from erp.journal_entries where id=v_journal;
     insert into erp.initial_import_prepayment_events(id,advance_id,event_type,component,delta,effective_date,reason,cash_account_id,reverses_event_id,journal_entry_id,created_by)
       values(v_id,a.id,'REVERSAL',e.component,v_delta,v_date,v_reason,e.cash_account_id,e.id,v_journal,erp.current_app_user_id());
   else
     v_delta:=case when v_op='CORRECT' then v_amount-(v_state->>'opening_amount')::numeric else -v_amount end;
     if v_delta=0 then raise exception 'Nilai koreksi sama dengan saldo awal saat ini';end if;
     if (v_state->>'remaining_amount')::numeric+v_delta<0 then raise exception 'Perubahan melebihi sisa uang muka; batalkan pemakaian dahulu';end if;
     if v_op='REFUND' then
       v_cash:=(p_payload->>'cash_account_id')::uuid;
       select coa_account_id into v_cash_coa from erp.cash_accounts where id=v_cash and is_active;
       if v_cash_coa is null then raise exception 'Pilih rekening kas/bank aktif';end if;
     else v_cash_coa:=erp.account_id('OPENING_EQUITY');end if;
     v_debit:=case when a.party_type='CUSTOMER' then -v_delta else v_delta end;
     v_journal:=erp.post_journal('PREPAYMENT_EVENT',v_id,v_date,v_reason,jsonb_build_array(
       jsonb_build_object('account_id',a.coa_account_id,'debit',greatest(v_debit,0),'credit',greatest(-v_debit,0),'customer_id',v_customer,'vendor_id',v_vendor),
       jsonb_build_object('account_id',v_cash_coa,'debit',greatest(-v_debit,0),'credit',greatest(v_debit,0),'customer_id',v_customer,'vendor_id',v_vendor)));
     insert into erp.initial_import_prepayment_events(id,advance_id,event_type,component,delta,effective_date,reason,cash_account_id,journal_entry_id,created_by)
       values(v_id,a.id,case when v_op='CORRECT' then 'CORRECTION' else 'REFUND' end,
         case when v_op='CORRECT' then 'CORRECTION' else 'REFUND' end,v_delta,v_date,v_reason,v_cash,v_journal,erp.current_app_user_id());
   end if;
 end if;
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
   values('initial_import_prepayments',a.id,'UPDATE',jsonb_build_object('operation',v_op,'payment_id',v_payment,'event_id',v_id),erp.current_app_user_id(),v_reason);
end;$function$;
"""

ACCOUNT = r"""CREATE OR REPLACE FUNCTION erp.initial_prepayment_account_v1(p_payment_id uuid)
RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select a.coa_account_id from erp.initial_import_prepayment_payments l join erp.initial_import_prepayments a on a.id=l.advance_id where l.payment_id=p_payment_id;
$function$;
"""

TRUTH = r"""CREATE OR REPLACE FUNCTION erp.initial_prepayment_checks_v1()
RETURNS TABLE(check_name text,severity text,issue_count bigint,details text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select 'AP_PREPAYMENT_CAPACITY','CRITICAL',count(*)::bigint,'Current opening minus refunds and native posted applications must remain nonnegative'
 from erp.initial_import_prepayments a cross join lateral(select erp.initial_prepayment_state_v1(a.id) s) v
 where (s->>'remaining_amount')::numeric<0 or (s->>'opening_amount')::numeric<0 or (s->>'refunded_amount')::numeric<0
 union all
 select 'AP_PREPAYMENT_PAYMENT_SOURCE','CRITICAL',count(*)::bigint,'Every application retains its source, exact payment snapshot, and party; cash is absent'
 from erp.initial_import_prepayments a cross join lateral erp.initial_prepayment_payments_v1(a.id) p
 join erp.initial_import_prepayment_payments l on l.payment_id=p.payment_id
 where p.party_id<>a.party_id or p.party_type<>a.party_type or p.amount<=0 or p.cash_account_id is not null
   or p.payment_snapshot is distinct from l.payment_snapshot or p.payment_snapshot->>'payment_method' is distinct from 'OPENING_ADVANCE'
   or erp._cp3_business_date(p.payment_date)<a.cutover_date
 union all
 select 'AP_PREPAYMENT_PAYMENT_JOURNAL','CRITICAL',count(*)::bigint,'Applied advances retain exact native liability/receivable journals and their linked inverses'
 from erp.initial_import_prepayments a cross join lateral erp.initial_prepayment_payments_v1(a.id) p
 cross join lateral(select case a.party_type when 'SUPPLIER' then erp.account_id('AP_SUPPLIER') when 'CUSTOMER' then erp.account_id('AR_CUSTOMER') else erp.account_id('AP_VENDOR') end account_id,
   case when a.party_type='CUSTOMER' then 1 else -1 end sign) k
 where (p.status='DRAFT' and exists(select 1 from erp.journal_entries where source_type=p.source_type and source_id=p.payment_id))
   or(p.status in('POSTED','REVERSED') and (
     (select count(*) from erp.journal_entries where source_type=p.source_type and source_id=p.payment_id)<>1
     or not exists(select 1 from erp.journal_entries j where j.source_type=p.source_type and j.source_id=p.payment_id
       and j.status=p.status and j.economic_date=erp._cp3_business_date(p.payment_date)
       and (select count(*) from erp.journal_lines where journal_entry_id=j.id)=2
       and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(a.coa_account_id::text,p.amount*k.sign,k.account_id::text,-p.amount*k.sign)
       and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and
         (l.customer_id is distinct from a.customer_id or l.vendor_id is distinct from a.vendor_id or l.contractor_id is not null))
       and (select count(*) from erp.journal_entries where reversal_of_id=j.id)=case when p.status='REVERSED' then 1 else 0 end
       and (p.status<>'REVERSED' or exists(select 1 from erp.journal_entries x where x.reversal_of_id=j.id and x.status='POSTED'
         and erp._cp6_supplier_cent_ledger(array[j.id,x.id])='{}'::jsonb)))))
 union all
 select 'AP_PREPAYMENT_OPENING_JOURNAL','CRITICAL',count(*)::bigint,'Opening prepayment posts only the carried balance once at cutover, without historical cash'
 from erp.initial_import_prepayments a
 where (select count(*) from erp.journal_entries where source_type='OPENING_PREPAYMENT' and source_id=a.id)<>1
   or not exists(select 1 from erp.journal_entries j where j.source_type='OPENING_PREPAYMENT' and j.source_id=a.id
     and j.status='POSTED' and j.economic_date=a.cutover_date
     and (select count(*) from erp.journal_lines where journal_entry_id=j.id)=2
     and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(
       a.coa_account_id::text,case when a.party_type='CUSTOMER' then -a.amount else a.amount end,
       erp.account_id('OPENING_EQUITY')::text,case when a.party_type='CUSTOMER' then a.amount else -a.amount end)
     and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id
       and (l.customer_id is distinct from a.customer_id or l.vendor_id is distinct from a.vendor_id or l.contractor_id is not null)))
 union all
 select 'AP_PREPAYMENT_EVENT_JOURNAL','CRITICAL',count(*)::bigint,'Corrections, cash refunds, and append-only reversals retain exact money and economic dates'
 from erp.initial_import_prepayment_events e join erp.initial_import_prepayments a on a.id=e.advance_id
 left join erp.initial_import_prepayment_events prior on prior.id=e.reverses_event_id
 left join erp.journal_entries j on j.id=e.journal_entry_id
 cross join lateral(select case when a.party_type='CUSTOMER' then -e.delta else e.delta end amount,
   case when e.component='CORRECTION' then erp.account_id('OPENING_EQUITY') else (select coa_account_id from erp.cash_accounts where id=e.cash_account_id) end account_id) k
 where j.id is null or j.economic_date<>e.effective_date or e.effective_date<a.cutover_date
   or j.source_type<>case when e.event_type='REVERSAL' then 'JOURNAL_REVERSAL' else 'PREPAYMENT_EVENT' end
   or (e.event_type<>'REVERSAL' and j.source_id<>e.id)
   or (e.event_type='REVERSAL' and (prior.advance_id is distinct from e.advance_id or prior.event_type='REVERSAL'
     or e.delta<>-prior.delta or e.component<>prior.component or j.reversal_of_id is distinct from prior.journal_entry_id))
   or j.status<>case when exists(select 1 from erp.initial_import_prepayment_events x where x.reverses_event_id=e.id) then 'REVERSED' else 'POSTED' end
   or (select count(*) from erp.journal_lines where journal_entry_id=j.id)<>2
   or erp._cp6_supplier_cent_ledger(array[j.id]) is distinct from jsonb_build_object(a.coa_account_id::text,k.amount,k.account_id::text,-k.amount)
   or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id
     and (l.customer_id is distinct from a.customer_id or l.vendor_id is distinct from a.vendor_id or l.contractor_id is not null))
 union all
 select 'AP_PREPAYMENT_GL_SUBLEDGER','CRITICAL',count(*)::bigint,'Each dedicated advance account equals current remaining balances across all sources'
 from (select a.coa_account_id,sum((erp.initial_prepayment_state_v1(a.id)->>'remaining_amount')::numeric
   *case when a.party_type='CUSTOMER' then -1 else 1 end) expected from erp.initial_import_prepayments a group by a.coa_account_id) x
 where x.expected is distinct from (select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
   join erp.journal_entries j on j.id=l.journal_entry_id where l.account_id=x.coa_account_id and j.status in('POSTED','REVERSED'));
$function$;
"""


def extend_prepayment_contract(functions):
    def change(identity,old,new,count=1):
        assert functions[identity].count(old)==count,(identity,old,functions[identity].count(old))
        functions[identity]=functions[identity].replace(old,new)
    for identity,definition,*_ in PREDECESSOR:
        assert identity not in functions,identity
        functions[identity]=definition
    helpers={
      'erp.initial_prepayment_payments_v1(uuid)':PAYMENTS,
      'erp.initial_prepayment_state_v1(uuid)':STATE,
      'erp.initial_prepayment_account_v1(uuid)':ACCOUNT,
      'erp.initial_prepayment_targets_v1(uuid)':TARGETS,
      'erp.initial_prepayment_funding_v1(uuid,text,uuid,numeric,date,date)':FUNDING,
      'erp.guard_initial_prepayment_immutable_v1()':IMMUTABLE,
      'erp.guard_initial_prepayment_payment_v1()':PAYMENT_GUARD,
      'erp.check_initial_prepayment_v1(uuid,uuid)':CHECK,
      'erp.validate_initial_prepayments_v1(uuid)':VALIDATE,
      'erp.apply_initial_prepayments_v1(uuid)':IMPORT,
      'erp.manage_initial_prepayment_v1(jsonb)':COMMAND,
      'erp.initial_prepayment_checks_v1()':TRUTH,
    }
    identity=next(k for k in functions if k.startswith('erp.stage_migration_row('))
    change(identity,"'OPENING_CONTROL','UNINVOICED_RECEIPT'","'OPENING_CONTROL','OPENING_ADVANCE','UNINVOICED_RECEIPT'")
    identity='erp._validate_migration_batch_base(uuid)'
    change(identity,"'OPENING_CONTROL','UNINVOICED_RECEIPT')","'OPENING_CONTROL','UNINVOICED_RECEIPT','OPENING_ADVANCE')")
    identity='erp.finalize_migration_batch(uuid)'
    change(identity,"'CASH_ACCOUNT','UNINVOICED_RECEIPT')","'CASH_ACCOUNT','UNINVOICED_RECEIPT','OPENING_ADVANCE')")
    identity='erp.validate_initial_import_totals_v1(uuid)'
    change(identity,"in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','UNINVOICED_RECEIPT')","in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','UNINVOICED_RECEIPT','OPENING_ADVANCE')")
    change(identity,"then 'GRNI_MATERIAL' else upper(j->>'balance_type')","then 'GRNI_MATERIAL' when r.entity_type='OPENING_ADVANCE' then (j->>'party_type')||'_ADVANCE' else upper(j->>'balance_type')")
    identity='erp.save_initial_import_action_v1(text,jsonb,uuid)'
    change(identity,"'FINALIZE','ALLOCATE_CASH_ADVANCE')","'FINALIZE','ALLOCATE_CASH_ADVANCE','PREPAYMENT')")
    change(identity," elsif v_action='ALLOCATE_CASH_ADVANCE' then", """ elsif v_action='PREPAYMENT' then
   v_batch:=(p_payload->>'batch_id')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null or b.status<>'POSTED' then raise exception 'Uang muka harus berasal dari impor yang sudah disahkan';end if;
   perform erp.manage_initial_prepayment_v1(p_payload);
 elsif v_action='ALLOCATE_CASH_ADVANCE' then""")
    change(identity,'     perform erp.validate_initial_import_totals_v1(b.id);','     perform erp.validate_initial_prepayments_v1(b.id);\n     perform erp.validate_initial_import_totals_v1(b.id);')
    change(identity,'       perform erp.finalize_migration_batch(b.id);','       perform erp.apply_initial_prepayments_v1(b.id);\n       perform erp.finalize_migration_batch(b.id);')
    identity='erp.initial_import_revision_v1(uuid)'
    change(identity,"   'items',coalesce(","""   'prepayments',coalesce((select jsonb_agg(to_jsonb(a)||jsonb_build_object(
     'events',(select jsonb_agg(to_jsonb(e) order by e.id) from erp.initial_import_prepayment_events e where e.advance_id=a.id),
     'payments',(select jsonb_agg(to_jsonb(p) order by p.payment_id) from erp.initial_prepayment_payments_v1(a.id) p),
     'targets',(select jsonb_agg(to_jsonb(t) order by t.id) from erp.initial_prepayment_targets_v1(a.id) t)
   ) order by a.id) from erp.initial_import_prepayments a where a.batch_id=p_batch_id),'[]'::jsonb),
   'items',coalesce(""")
    identity='erp.get_initial_import_workspace_v1(uuid)'
    change(identity,"     'opening_id',(select h.id", """     'prepayments',coalesce((select jsonb_agg(erp.initial_prepayment_state_v1(a.id)||jsonb_build_object(
       'party_name',case a.party_type when 'SUPPLIER' then (select supplier_name from erp.suppliers where id=a.party_id)
         when 'CUSTOMER' then (select customer_name from erp.customers where id=a.party_id) else (select vendor_name from erp.laundry_vendors where id=a.party_id) end,
       'targets',coalesce((select jsonb_agg(to_jsonb(t) order by t.target_date,t.id) from (
         select * from erp.initial_prepayment_targets_v1(a.id) where remaining_amount::numeric>0 order by target_date,id limit 100) t),'[]'::jsonb),
       'payments',coalesce((select jsonb_agg(jsonb_build_object('id',p.payment_id,'number',p.number,'status',p.status,'amount',p.amount::numeric(20,2)::text) order by p.payment_date,p.payment_id)
         from erp.initial_prepayment_payments_v1(a.id) p),'[]'::jsonb),
       'events',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'kind',e.event_type,'delta',e.delta::text,'date',e.effective_date,'reason',e.reason,
         'reversed',exists(select 1 from erp.initial_import_prepayment_events x where x.reverses_event_id=e.id)) order by e.created_at,e.id)
         from erp.initial_import_prepayment_events e where e.advance_id=a.id),'[]'::jsonb)) order by a.document_number,a.id)
       from erp.initial_import_prepayments a where a.batch_id=b.id),'[]'::jsonb),
     'prepayment_cash_accounts',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',cash_account_name) order by cash_account_code)
       from erp.cash_accounts where is_active),'[]'::jsonb),
     'opening_id',(select h.id""")
    for kind,identity,party,date in [
      ('SUPPLIER','erp.post_supplier_payment(uuid)','h.supplier_id',"greatest(erp._cp3_business_date(h.physical_at),(select max(i.invoice_date) from erp.material_supplier_invoices i join erp.material_supplier_invoice_lines l on l.invoice_id=i.id join erp.material_purchase_items pi on pi.id=l.purchase_item_id where pi.purchase_id=h.id and i.status='POSTED'))"),
      ('CUSTOMER','erp.post_sales_payment(uuid)','h.customer_id','erp._cp3_business_date(h.sale_date)'),
      ('VENDOR','erp.post_vendor_payment(uuid)','h.vendor_id','h.invoice_date'),
    ]:
        old='  select coa_account_id into v_cash from erp.cash_accounts'
        start=functions[identity].index(old);end=functions[identity].index(';',start)+1
        old=functions[identity][start:end]
        change(identity,old,f"  v_cash:=erp.initial_prepayment_funding_v1(p.id,'{kind}',{party},p.amount,erp._cp3_business_date(p.payment_date),{date});\n  if v_cash is null then\n"+old+'\n  end if;')
    identity='erp.post_sales_payment(uuid)'
    old="    if prior_fact.customer_id is distinct from h.customer_id"
    change(identity,old,"""    if erp.initial_prepayment_account_v1(p.id) is not null or erp.initial_prepayment_account_v1(prior_payment.id) is not null then
      raise exception 'Uang muka dipindah melalui pembatalan lalu pemakaian baru dari workspace impor';end if;
"""+old)
    for identity in ['erp.reverse_supplier_payment(uuid,text)','erp.reverse_vendor_payment(uuid,text)','erp.reverse_sales_payment(uuid,text)']:
        marker='  select * into h from '
        start=functions[identity].index(marker);end=functions[identity].index(';',start)+1
        old=functions[identity][start:end]
        change(identity,old,old+"\n  perform 1 from erp.initial_import_prepayments a join erp.initial_import_prepayment_payments l on l.advance_id=a.id where l.payment_id=p.id for update of a;")
        if 'reverse_sales' in identity:
            old='  v_reversal_journal:=erp.reverse_journal(v_journal,p_reason);'
            new="  v_reversal_journal:=case when erp.initial_prepayment_account_v1(p.id) is not null then erp._cp3_r4_reverse_journal_internal(v_journal,p_reason) else erp.reverse_journal(v_journal,p_reason) end;"
        else:
            old='  perform erp.reverse_journal(v_journal,p_reason);'
            new="  if erp.initial_prepayment_account_v1(p.id) is not null then perform erp._cp3_r4_reverse_journal_internal(v_journal,p_reason);else perform erp.reverse_journal(v_journal,p_reason);end if;"
        change(identity,old,new)
    identity='erp.post_opening_subledger_settlement(uuid)'
    old='SELECT coa_account_id INTO v_cash FROM erp.cash_accounts WHERE id=s.cash_account_id AND is_active=true;'
    change(identity,old,"""v_cash:=erp.initial_prepayment_funding_v1(s.id,b.party_type,coalesce(b.supplier_id,b.customer_id,b.vendor_id),s.amount,erp._cp3_business_date(s.physical_at),
      (select h.opening_date from erp.opening_balance_items oi join erp.opening_balance_headers h on h.id=oi.opening_id where oi.id=b.opening_item_id));
IF v_cash IS NULL THEN """+old+'END IF;')
    identity='erp.reverse_opening_subledger_settlement(uuid,text)'
    old='SELECT * INTO b FROM erp.opening_subledger_balances WHERE id=s.balance_id FOR UPDATE;'
    change(identity,old,old+'PERFORM 1 FROM erp.initial_import_prepayments a JOIN erp.initial_import_prepayment_payments l ON l.advance_id=a.id WHERE l.payment_id=s.id FOR UPDATE OF a;')
    old="PERFORM erp.reverse_journal(v_journal,COALESCE(NULLIF(trim(p_reason),''),'Opening settlement reversal'));"
    change(identity,old,"IF erp.initial_prepayment_account_v1(s.id) IS NOT NULL THEN PERFORM erp._cp3_r4_reverse_journal_internal(v_journal,p_reason);ELSE "+old+'END IF;')
    identity='erp.reverse_journal(uuid,text)'
    old="  if v_source_type='MATERIAL_ADJUSTMENT_REVALUATION' then"
    change(identity,old,"""  if v_source_type in('OPENING_PREPAYMENT','PREPAYMENT_EVENT') or (v_source_type in('SUPPLIER_PAYMENT','SALES_PAYMENT','VENDOR_PAYMENT','OPENING_SUBLEDGER_SETTLEMENT')
    and exists(select 1 from erp.initial_import_prepayment_payments l join erp.journal_entries j on j.source_id=l.payment_id where j.id=p_journal_entry_id)) then
    raise exception 'Pembatalan uang muka harus melalui sumber pembayaran atau perubahan tertaut';end if;
"""+old)
    identity='erp.run_v267_financial_truth_checks()'
    change(identity,'or ca.id is null','or (ca.id is null and erp.initial_prepayment_account_v1(x.id) is null)')
    change(identity,'l.account_id=ca.coa_account_id','l.account_id=coalesce(erp.initial_prepayment_account_v1(x.id),ca.coa_account_id)',count=2)
    change(identity,';\n\n$function$',"\n union all select * from erp.initial_prepayment_checks_v1();\n\n$function$")
    identity='erp.run_v268_financial_report_checks()'
    old='join erp.cash_accounts ca on ca.id=p.cash_account_id and ca.coa_account_id=l.account_id\n                 where l.journal_entry_id=o.id'
    change(identity,old,'left join erp.cash_accounts ca on ca.id=p.cash_account_id\n                 where l.account_id=coalesce(erp.initial_prepayment_account_v1(p.id),ca.coa_account_id) and l.journal_entry_id=o.id')
    ordered={**helpers,**functions};functions.clear();functions.update(ordered)
