"""Opening balances retain real document provenance without historical posting.

The outstanding amount is posted once through the existing opening subledger.
Original totals and settlements before cutover are evidence, not new cash flows.
"""

SCHEMA = r"""
create table erp.initial_import_financial_sources(
 id uuid primary key default gen_random_uuid(),
 batch_id uuid not null references erp.migration_batches(id),
 source_row_id uuid not null unique references erp.migration_staging_rows(id) on delete cascade,
 opening_item_id uuid not null unique references erp.opening_balance_items(id) on delete cascade,
 balance_type text not null check(balance_type in('CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE')),
 party_id uuid not null,cutover_date date not null,
 source_mode text not null check(source_mode in('SUMMARY','DOCUMENT')),
 document_number text,document_date date,due_date date,
 original_amount numeric(20,2) not null,settled_before_cutover numeric(20,2) not null,
 outstanding_amount numeric(20,2) not null,
 created_at timestamptz not null default statement_timestamp(),
 check(original_amount>0 and settled_before_cutover>=0 and outstanding_amount>0
   and original_amount-settled_before_cutover=outstanding_amount),
 check((source_mode='SUMMARY' and document_number is null and document_date is null and due_date is null and settled_before_cutover=0)
   or (source_mode='DOCUMENT' and nullif(btrim(document_number),'') is not null and document_date is not null
     and document_date<=cutover_date and (due_date is null or due_date>=document_date)))
);
create unique index initial_import_financial_document_key on erp.initial_import_financial_sources
 (balance_type,party_id,lower(btrim(document_number))) where source_mode='DOCUMENT';
create unique index initial_import_financial_summary_key on erp.initial_import_financial_sources
 (balance_type,party_id) where source_mode='SUMMARY';
create index initial_import_financial_party on erp.initial_import_financial_sources(balance_type,party_id);
alter table erp.initial_import_financial_sources enable row level security;
revoke all on erp.initial_import_financial_sources from public,anon,authenticated,service_role;
"""

SOURCE = r"""CREATE OR REPLACE FUNCTION erp.check_initial_import_financial_source_v1(
 p_batch_id uuid,p_row_id uuid,p_opening_item_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD' AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;v_cutover date;v_type text;v_mode text;
 v_code_field text;v_id_field text;v_table text;v_party uuid;v_number text;v_date date;v_due date;
 v_original numeric;v_paid numeric;v_amount numeric;v_field text;v_value numeric;v_result jsonb;
begin
 perform erp.require_owner_admin();
 select * into r from erp.migration_staging_rows where id=p_row_id and batch_id=p_batch_id;
 if r.id is null or r.entity_type<>'OPENING_BALANCE_ITEM' then raise exception 'Baris saldo awal tidak ditemukan'; end if;
 j:=r.normalized_payload;v_type:=upper(j->>'balance_type');
 if v_type not in('CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE') then
   if exists(select 1 from unnest(array['document_number','document_date','due_date','original_amount','settled_before_cutover']) f
       where nullif(btrim(j->>f),'') is not null) then
     raise exception 'document_number: metadata dokumen ini hanya untuk piutang/utang awal'; end if;
   return null;
 end if;
 select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch_id;
 v_code_field:=case when v_type like 'CONTRACTOR_%' then 'contractor_code'
   when v_type='CUSTOMER_RECEIVABLE' then 'customer_code' when v_type='SUPPLIER_PAYABLE' then 'supplier_code' else 'vendor_code' end;
 v_id_field:=replace(v_code_field,'_code','_id');
 v_table:=case when v_type like 'CONTRACTOR_%' then 'contractors'
   when v_type='CUSTOMER_RECEIVABLE' then 'customers' when v_type='SUPPLIER_PAYABLE' then 'suppliers' else 'laundry_vendors' end;
 execute format('select id from erp.%I where %I=$1',v_table,v_code_field) into v_party using j->>v_code_field;
 v_number:=nullif(btrim(j->>'document_number'),'');v_mode:=case when v_number is null then 'SUMMARY' else 'DOCUMENT' end;
 v_amount:=nullif(j->>'amount','')::numeric;
 if v_amount is null or v_amount::text in('NaN','Infinity','-Infinity') or v_amount<=0 or v_amount<>round(v_amount,2) then
   raise exception 'amount: saldo tersisa harus uang positif dengan paling banyak dua desimal'; end if;
 if v_mode='SUMMARY' then
   if exists(select 1 from unnest(array['document_date','due_date','original_amount','settled_before_cutover']) f
       where nullif(btrim(j->>f),'') is not null) then
     raise exception 'document_number: isi nomor dokumen untuk rincian nilai awal dan pembayaran lama'; end if;
   v_original:=v_amount;v_paid:=0;
 else
   if length(v_number)>120 then raise exception 'document_number: maksimal 120 karakter'; end if;
   foreach v_field in array array['original_amount','settled_before_cutover'] loop
     v_value:=nullif(j->>v_field,'')::numeric;
     if v_value is null or v_value::text in('NaN','Infinity','-Infinity') or v_value<0 or v_value<>round(v_value,2) then
       raise exception '%: wajib nominal valid dengan paling banyak dua desimal',v_field; end if;
     perform v_value::numeric(20,2);
   end loop;
   v_original:=(j->>'original_amount')::numeric;v_paid:=(j->>'settled_before_cutover')::numeric;
   if v_original-v_paid<>v_amount then raise exception 'amount: nominal awal dikurangi pembayaran lama harus sama dengan saldo tersisa'; end if;
   foreach v_field in array array['document_date','due_date'] loop
     if v_field='due_date' and nullif(j->>v_field,'') is null then continue; end if;
     if coalesce(j->>v_field,'') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
       or (j->>v_field)::date::text<>j->>v_field then raise exception '%: gunakan tanggal YYYY-MM-DD yang valid',v_field; end if;
   end loop;
   v_date:=(j->>'document_date')::date;v_due:=nullif(j->>'due_date','')::date;
   if v_date>v_cutover then raise exception 'document_date: dokumen melewati tanggal saldo awal'; end if;
   if v_due<v_date then raise exception 'due_date: jatuh tempo mendahului tanggal dokumen'; end if;
 end if;
 -- The same party/balance may be represented by one summary or by documents.
 -- Even a mathematically matching control must not admit both representations.
 if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.id<>r.id
   and s.entity_type='OPENING_BALANCE_ITEM' and upper(s.normalized_payload->>'balance_type')=v_type
   and s.normalized_payload->>v_code_field=j->>v_code_field
   and (v_mode='SUMMARY' or nullif(btrim(s.normalized_payload->>'document_number'),'') is null)) then
   raise exception 'document_number: jangan campur ringkasan saldo dan rincian dokumen pihak yang sama, atau ulangi ringkasannya'; end if;
 if v_mode='DOCUMENT' and exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.id<>r.id
   and s.entity_type='OPENING_BALANCE_ITEM' and upper(s.normalized_payload->>'balance_type')=v_type
   and s.normalized_payload->>v_code_field=j->>v_code_field
   and lower(btrim(s.normalized_payload->>'document_number'))=lower(v_number)) then
   raise exception 'document_number: dokumen yang sama muncul dua kali dalam batch'; end if;
 if p_opening_item_id is not null then
   if v_party is null or not exists(select 1 from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
     where i.id=p_opening_item_id and h.migration_batch_id=p_batch_id and h.status='DRAFT'
       and i.balance_type=v_type and (to_jsonb(i)->>v_id_field)::uuid=v_party and i.amount=v_amount) then
     raise exception 'Dokumen asal tidak cocok dengan rincian saldo yang akan dibukukan'; end if;
   perform pg_advisory_xact_lock(hashtextextended('INITIAL_OPENING_FINANCIAL:'||v_type||':'||v_party::text,0));
 end if;
 if v_party is not null then
   if exists(select 1 from erp.initial_import_financial_sources s where s.balance_type=v_type and s.party_id=v_party
     and s.source_row_id<>r.id and (s.source_mode='SUMMARY' or v_mode='SUMMARY')) then
     raise exception 'document_number: saldo pihak ini sudah diimpor; ringkasan dan rincian tidak boleh dibukukan ulang lintas batch'; end if;
   if v_mode='DOCUMENT' and exists(select 1 from erp.initial_import_financial_sources s where s.balance_type=v_type and s.party_id=v_party
     and s.source_row_id<>r.id and lower(btrim(s.document_number))=lower(v_number)) then
     raise exception 'document_number: dokumen ini sudah diimpor pada batch lain'; end if;
   if exists(select 1 from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
     where h.status='POSTED' and i.balance_type=v_type and (to_jsonb(i)->>v_id_field)::uuid=v_party
       and not exists(select 1 from erp.initial_import_financial_sources s where s.opening_item_id=i.id)) then
     raise exception 'document_number: saldo pihak ini sudah dibukukan melalui jalur lama; rekonsiliasi sumbernya sebelum impor tambahan'; end if;
 end if;
 v_result:=jsonb_build_object('source_mode',v_mode,'document_number',v_number,'document_date',v_date,'due_date',v_due,
   'original_amount',v_original,'settled_before_cutover',v_paid,'outstanding_amount',v_amount);
 if p_opening_item_id is not null then
   insert into erp.initial_import_financial_sources(batch_id,source_row_id,opening_item_id,balance_type,party_id,cutover_date,
     source_mode,document_number,document_date,due_date,original_amount,settled_before_cutover,outstanding_amount)
   values(p_batch_id,r.id,p_opening_item_id,v_type,v_party,v_cutover,v_mode,v_number,v_date,v_due,v_original,v_paid,v_amount);
 end if;
 return v_result;
end;$function$;
"""

VALIDATE = r"""CREATE OR REPLACE FUNCTION erp.validate_initial_import_financial_sources_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare r record;
begin
 perform erp.require_owner_admin();
 for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_BALANCE_ITEM'
   and validation_status='VALID' order by source_row_no loop
   begin
     perform erp.check_initial_import_financial_source_v1(p_batch_id,r.id,null);
   exception when others then
     update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=r.id;
   end;
 end loop;
end;$function$;
"""


def extend_financial_contract(functions):
    identity='erp.prepare_migration_opening_balance(uuid,text)'
    old='v_hpp_pct numeric;'
    assert functions[identity].count(old)==1
    functions[identity]=functions[identity].replace(old,old+'v_opening_item uuid;')
    old="case when v_type='FINISHED_GOODS' and v_hpp_method='PRICE_PERCENT' then v_hpp_pct else null end);"
    assert functions[identity].count(old)==1
    functions[identity]=functions[identity].replace(old,old[:-2]+') returning id into v_opening_item;\n    perform erp.check_initial_import_financial_source_v1(b.id,r.id,v_opening_item);')
    identity='erp.save_initial_import_action_v1(text,jsonb,uuid)'
    old='     perform erp.validate_initial_import_totals_v1(b.id);'
    assert functions[identity].count(old)==1
    functions[identity]=functions[identity].replace(old,'     perform erp.validate_initial_import_financial_sources_v1(b.id);\n'+old)
    functions['erp.check_initial_import_financial_source_v1(uuid,uuid,uuid)']=SOURCE
    functions['erp.validate_initial_import_financial_sources_v1(uuid)']=VALIDATE
