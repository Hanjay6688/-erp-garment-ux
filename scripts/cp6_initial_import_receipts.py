"""Opening GRNI references an existing opening layer; it never receives stock again.

This contract admits wholly unbilled quantities still on hand at cutover. Earlier
consumption needs the physical WIP/cost-origin contract and is refused explicitly.
"""
import json
from pathlib import Path

PREDECESSOR = json.loads(Path('docs/evidence/cp6-initial-import-receipt-predecessor.json').read_text())['functions']

SCHEMA = r"""
create table erp.initial_import_opening_stock_sources(
 source_row_id uuid primary key references erp.migration_staging_rows(id) on delete cascade,
 batch_id uuid not null references erp.migration_batches(id),
 source_key text not null,
 opening_item_id uuid not null unique references erp.opening_balance_items(id) on delete cascade,
 unique(batch_id,source_key)
);
create table erp.initial_import_receipt_headers(
 purchase_id uuid primary key references erp.material_purchase_headers(id),
 batch_id uuid not null references erp.migration_batches(id),
 supplier_id uuid not null references erp.suppliers(id),
 receipt_number text not null check(length(btrim(receipt_number)) between 1 and 120),
 receipt_date date not null,cutover_date date not null,
 check(receipt_date<=cutover_date)
);
create unique index initial_import_receipt_identity on erp.initial_import_receipt_headers(supplier_id,lower(btrim(receipt_number)));
create index initial_import_receipt_batch on erp.initial_import_receipt_headers(batch_id);
create table erp.initial_import_receipt_lines(
 purchase_item_id uuid primary key references erp.material_purchase_items(id),
 purchase_id uuid not null references erp.initial_import_receipt_headers(purchase_id),
 source_row_id uuid not null unique references erp.migration_staging_rows(id),
 opening_item_id uuid not null unique references erp.opening_balance_items(id),
 receipt_line_number text not null check(length(btrim(receipt_line_number)) between 1 and 60)
);
create unique index initial_import_receipt_line_identity on erp.initial_import_receipt_lines(purchase_id,lower(btrim(receipt_line_number)));
alter table erp.initial_import_opening_stock_sources enable row level security;
alter table erp.initial_import_receipt_headers enable row level security;
alter table erp.initial_import_receipt_lines enable row level security;
revoke all on erp.initial_import_opening_stock_sources,erp.initial_import_receipt_headers,erp.initial_import_receipt_lines from public,anon,authenticated,service_role;
"""

CHECK = r"""CREATE OR REPLACE FUNCTION erp.check_initial_import_receipt_v1(p_batch_id uuid,p_row_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD' AS $function$
declare r erp.migration_staging_rows%rowtype;s erp.migration_staging_rows%rowtype;
 j jsonb;v_cutover date;v_party uuid;v_key text;v_number text;v_line text;v_date date;v_qty numeric;v_cost numeric;k text;
begin
 perform erp.require_owner_admin();
 select * into r from erp.migration_staging_rows where id=p_row_id and batch_id=p_batch_id and entity_type='UNINVOICED_RECEIPT';
 if r.id is null then raise exception 'Baris penerimaan tidak ditemukan'; end if;
 j:=r.normalized_payload;
 foreach k in array array['receipt_number','receipt_line_number','receipt_date','supplier_code','material_sku','location_code','qty','unit_cost','opening_source_key','control_key'] loop
   if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi',k;end if;
 end loop;
 v_number:=btrim(j->>'receipt_number');v_line:=btrim(j->>'receipt_line_number');v_key:=btrim(j->>'opening_source_key');
 if length(v_number)>120 or length(v_line)>60 or length(v_key)>120 then raise exception 'receipt_number: identitas sumber terlalu panjang';end if;
 if j->>'receipt_date' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' or (j->>'receipt_date')::date::text<>j->>'receipt_date' then
   raise exception 'receipt_date: gunakan YYYY-MM-DD';end if;
 v_date:=(j->>'receipt_date')::date;
 select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch_id;
 if v_date>v_cutover then raise exception 'receipt_date: penerimaan melewati cutover';end if;
 v_qty:=(j->>'qty')::numeric;v_cost:=(j->>'unit_cost')::numeric;
 if v_qty::text in('NaN','Infinity','-Infinity') or v_cost::text in('NaN','Infinity','-Infinity')
   or v_qty<=0 or v_cost<0 or v_qty<>round(v_qty,6) or v_cost<>round(v_cost,6) then
   raise exception 'qty: jumlah positif dan biaya nonnegatif harus tepat, maksimal enam desimal';end if;
 perform v_qty::numeric(18,6);perform v_cost::numeric(18,6);
 if (select count(*) from erp.migration_staging_rows where batch_id=p_batch_id
   and entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM') and normalized_payload->>'opening_source_key'=v_key)<>1 then
   raise exception 'opening_source_key: harus menunjuk tepat satu rincian stok dalam batch ini';end if;
 select * into s from erp.migration_staging_rows where batch_id=p_batch_id
   and entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM') and normalized_payload->>'opening_source_key'=v_key;
 if s.validation_status<>'VALID' or (s.entity_type='OPENING_BALANCE_ITEM' and upper(s.normalized_payload->>'balance_type')<>'MATERIAL') then
   raise exception 'opening_source_key: sumber harus rincian stok bahan yang valid';end if;
 if s.normalized_payload->>'material_sku' is distinct from j->>'material_sku'
   or s.normalized_payload->>'location_code' is distinct from j->>'location_code'
   or (s.normalized_payload->>'unit_cost')::numeric is distinct from v_cost
   or (s.normalized_payload->>case when s.entity_type='MATERIAL_ROLL' then 'opening_qty' else 'qty' end)::numeric is distinct from v_qty then
   raise exception 'opening_source_key: jumlah belum ditagih, bahan, gudang, dan biaya harus sama dengan stok awal; konsumsi sebelum cutover memerlukan asal WIP/HPP';end if;
 if nullif(s.normalized_payload->>'supplier_code','') is not null and s.normalized_payload->>'supplier_code'<>j->>'supplier_code' then
   raise exception 'supplier_code: supplier berbeda dengan stok asal';end if;
 select id into v_party from erp.suppliers where supplier_code=j->>'supplier_code' and is_active;
 if v_party is null and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='SUPPLIER'
   and validation_status='VALID' and normalized_payload->>'supplier_code'=j->>'supplier_code'
   and coalesce(nullif(normalized_payload->>'is_active','')::boolean,true)) then raise exception 'supplier_code: supplier aktif tidak ditemukan';end if;
 if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch_id and x.entity_type='UNINVOICED_RECEIPT' and x.id<>r.id
   and (x.normalized_payload->>'opening_source_key'=v_key or (
     x.normalized_payload->>'supplier_code'=j->>'supplier_code' and lower(btrim(x.normalized_payload->>'receipt_number'))=lower(v_number)
     and (lower(btrim(x.normalized_payload->>'receipt_line_number'))=lower(v_line)
       or x.normalized_payload->>'receipt_date'<>j->>'receipt_date' or x.normalized_payload->>'location_code'<>j->>'location_code'
       or x.normalized_payload->>'control_key'<>j->>'control_key')))) then
   raise exception 'receipt_number: sumber ganda atau rincian dokumen tidak konsisten';end if;
 if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch_id and x.entity_type='OPENING_BALANCE_ITEM'
   and upper(x.normalized_payload->>'balance_type')='SUPPLIER_PAYABLE' and x.normalized_payload->>'supplier_code'=j->>'supplier_code'
   and (nullif(btrim(x.normalized_payload->>'document_number'),'') is null or lower(btrim(x.normalized_payload->>'document_number'))=lower(v_number))) then
   raise exception 'receipt_number: jangan campur kewajiban belum ditagih dengan ringkasan utang atau dokumen asal yang sama';end if;
 if v_party is not null then
   if exists(select 1 from erp.initial_import_receipt_headers where supplier_id=v_party and lower(btrim(receipt_number))=lower(v_number))
      or exists(select 1 from erp.material_purchase_headers where supplier_id=v_party and lower(btrim(purchase_number))=lower(v_number)) then
     raise exception 'receipt_number: penerimaan sudah tercatat, termasuk pada jalur pembelian';end if;
   if exists(select 1 from erp.initial_import_financial_sources where balance_type='SUPPLIER_PAYABLE' and party_id=v_party
     and (source_mode='SUMMARY' or lower(btrim(document_number))=lower(v_number)))
     or exists(select 1 from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
       where i.balance_type='SUPPLIER_PAYABLE' and i.supplier_id=v_party and h.status='POSTED'
       and not exists(select 1 from erp.initial_import_financial_sources f where f.opening_item_id=i.id)) then
     raise exception 'receipt_number: kewajiban supplier sudah memiliki opening yang tumpang tindih atau belum terurai';end if;
 end if;
end;$function$;
"""

VALIDATE = r"""CREATE OR REPLACE FUNCTION erp.validate_initial_import_receipts_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare r record;
begin
 perform erp.require_owner_admin();
 for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM')
   and nullif(btrim(normalized_payload->>'opening_source_key'),'') is not null loop
   if length(r.normalized_payload->>'opening_source_key')>120
     or (r.entity_type='OPENING_BALANCE_ITEM' and upper(r.normalized_payload->>'balance_type')<>'MATERIAL')
     or exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.id<>r.id
       and s.entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM')
       and s.normalized_payload->>'opening_source_key'=r.normalized_payload->>'opening_source_key') then
     update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array('opening_source_key: kode unik maksimal 120 karakter hanya untuk stok bahan') where id=r.id;
   end if;
 end loop;
 for r in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='UNINVOICED_RECEIPT' order by source_row_no loop
   begin perform erp.check_initial_import_receipt_v1(p_batch_id,r.id);
   exception when others then update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=r.id;
   end;
 end loop;
end;$function$;
"""

LINK = r"""CREATE OR REPLACE FUNCTION erp.link_initial_import_stock_source_v1(p_batch_id uuid,p_row_id uuid,p_item_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare v_key text;
begin
 perform erp.require_owner_admin();
 select nullif(btrim(normalized_payload->>'opening_source_key'),'') into v_key from erp.migration_staging_rows where id=p_row_id and batch_id=p_batch_id;
 if v_key is null then return;end if;
 if not exists(select 1 from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
   where i.id=p_item_id and i.balance_type='MATERIAL' and h.status='DRAFT' and h.migration_batch_id=p_batch_id) then
   raise exception 'opening_source_key hanya untuk rincian stok bahan';end if;
 insert into erp.initial_import_opening_stock_sources(source_row_id,batch_id,source_key,opening_item_id) values(p_row_id,p_batch_id,v_key,p_item_id);
end;$function$;
"""

APPLY = r"""CREATE OR REPLACE FUNCTION erp.apply_initial_import_receipts_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare b erp.migration_batches%rowtype;r record;j jsonb;v_supplier uuid;v_purchase uuid;v_item uuid;
 v_opening erp.opening_balance_items%rowtype;v_cutover date;
begin
 perform erp.require_owner_admin();
 select * into b from erp.migration_batches where id=p_batch_id for update;
 if b.status not in('READY','POSTING') or exists(select 1 from erp.migration_staging_rows where batch_id=b.id and validation_status<>'VALID') then
   raise exception 'Penerimaan awal memerlukan batch valid terbaru';end if;
 v_cutover:=(b.cutover_at at time zone 'Asia/Jakarta')::date;
 -- Same lock as financial opening preparation, plus normalized receipt identity.
 for r in select distinct s.id supplier_id from erp.migration_staging_rows x join erp.suppliers s on s.supplier_code=x.normalized_payload->>'supplier_code'
   where x.batch_id=b.id and x.entity_type='UNINVOICED_RECEIPT' order by s.id loop
   perform pg_advisory_xact_lock(hashtextextended('INITIAL_OPENING_FINANCIAL:SUPPLIER_PAYABLE:'||r.supplier_id::text,0));
 end loop;
 for r in select x.*,s.id supplier_id from erp.migration_staging_rows x join erp.suppliers s on s.supplier_code=x.normalized_payload->>'supplier_code'
   where x.batch_id=b.id and x.entity_type='UNINVOICED_RECEIPT' order by s.id,lower(btrim(x.normalized_payload->>'receipt_number')),x.source_row_no loop
   perform pg_advisory_xact_lock(hashtextextended('INITIAL_RECEIPT:'||r.supplier_id::text||':'||lower(btrim(r.normalized_payload->>'receipt_number')),0));
   perform erp.check_initial_import_receipt_v1(b.id,r.id);
 end loop;
 for r in select * from erp.migration_staging_rows where batch_id=b.id and entity_type='UNINVOICED_RECEIPT' order by source_row_no loop
   j:=r.normalized_payload;
   select id into strict v_supplier from erp.suppliers where supplier_code=j->>'supplier_code' and is_active;
   select i.* into strict v_opening from erp.initial_import_opening_stock_sources s
     join erp.opening_balance_items i on i.id=s.opening_item_id join erp.opening_balance_headers h on h.id=i.opening_id
     where s.batch_id=b.id and s.source_key=j->>'opening_source_key' and h.status='POSTED' for update of i;
   if v_opening.qty<>(j->>'qty')::numeric or v_opening.unit_cost_snapshot<>(j->>'unit_cost')::numeric
     or not exists(select 1 from erp.material_stock_movements m where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=v_opening.id
       and m.movement_type='OPENING' and m.qty_signed=v_opening.qty and m.material_id=v_opening.material_id
       and m.location_id=v_opening.location_id and m.roll_id is not distinct from v_opening.roll_id) then
     raise exception 'Asal fisik penerimaan tidak cocok dengan stok awal yang dibukukan';end if;
   select purchase_id into v_purchase from erp.initial_import_receipt_headers where batch_id=b.id and supplier_id=v_supplier
     and lower(btrim(receipt_number))=lower(btrim(j->>'receipt_number'));
   if v_purchase is null then
     v_purchase:=gen_random_uuid();
     insert into erp.material_purchase_headers(id,purchase_number,supplier_id,physical_at,location_id,notes,created_by)
       values(v_purchase,'OPEN-'||v_purchase::text,v_supplier,b.cutover_at,v_opening.location_id,
         'Saldo awal penerimaan '||(j->>'receipt_number')||' tanggal '||(j->>'receipt_date'),erp.current_app_user_id());
     insert into erp.initial_import_receipt_headers(purchase_id,batch_id,supplier_id,receipt_number,receipt_date,cutover_date)
       values(v_purchase,b.id,v_supplier,j->>'receipt_number',(j->>'receipt_date')::date,v_cutover);
   end if;
   insert into erp.material_purchase_items(purchase_id,material_id,qty,unit_price,price_state,price_source,notes)
     values(v_purchase,v_opening.material_id,v_opening.qty,v_opening.unit_cost_snapshot,'ESTIMATED','MANUAL_ESTIMATE',j->>'notes') returning id into v_item;
   insert into erp.initial_import_receipt_lines(purchase_item_id,purchase_id,source_row_id,opening_item_id,receipt_line_number)
     values(v_item,v_purchase,r.id,v_opening.id,j->>'receipt_line_number');
   update erp.migration_staging_rows set posted_entity_type='OPENING_UNINVOICED_RECEIPT_ITEM',posted_entity_id=v_item,
     posted_at=statement_timestamp(),updated_at=statement_timestamp() where id=r.id;
 end loop;
 for r in select purchase_id from erp.initial_import_receipt_headers where batch_id=b.id order by purchase_id loop
   update erp.material_purchase_headers set status='POSTED' where id=r.purchase_id;
 end loop;
end;$function$;
"""

GUARD = r"""CREATE OR REPLACE FUNCTION erp.guard_initial_import_receipt_header_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
begin
 if tg_op<>'INSERT' and exists(select 1 from erp.initial_import_receipt_headers where purchase_id=old.id) then
   if tg_op='DELETE' then raise exception 'Penerimaan saldo awal bersifat tetap; gunakan koreksi tertaut';end if;
   if old.status='POSTED' and (new.status<>old.status or new.supplier_id is distinct from old.supplier_id
     or new.physical_at<>old.physical_at or new.location_id is distinct from old.location_id or new.purchase_number<>old.purchase_number) then
     raise exception 'Penerimaan saldo awal bersifat tetap; gunakan koreksi tertaut';end if;
 elsif tg_op<>'DELETE' and new.supplier_id is not null then
   perform pg_advisory_xact_lock(hashtextextended('INITIAL_RECEIPT:'||new.supplier_id::text||':'||lower(btrim(new.purchase_number)),0));
   if exists(select 1 from erp.initial_import_receipt_headers where supplier_id=new.supplier_id
     and lower(btrim(receipt_number))=lower(btrim(new.purchase_number))) then
     raise exception 'receipt_number: penerimaan ini sudah diimpor sebagai stok awal';end if;
 end if;
 if tg_op='DELETE' then return old;end if;return new;
end;$function$;
"""

TRIGGERS = """
create trigger initial_import_receipt_header_guard before insert or update or delete on erp.material_purchase_headers
 for each row execute function erp.guard_initial_import_receipt_header_v1();
"""

def extend_receipt_contract(functions):
    def change(identity, old, new, count=1):
        assert functions[identity].count(old)==count,(identity,old)
        functions[identity]=functions[identity].replace(old,new)
    functions.update({r[0]:r[1] for r in PREDECESSOR})
    for identity,definition in {
        'erp.check_initial_import_receipt_v1(uuid,uuid)':CHECK,
        'erp.validate_initial_import_receipts_v1(uuid)':VALIDATE,
        'erp.link_initial_import_stock_source_v1(uuid,uuid,uuid)':LINK,
        'erp.apply_initial_import_receipts_v1(uuid)':APPLY,
        'erp.guard_initial_import_receipt_header_v1()':GUARD,
    }.items():functions[identity]=definition
    identity=next(k for k in functions if k.startswith('erp.stage_migration_row('))
    change(identity,"'OPENING_CONTROL','LAUNDRY_VENDOR'","'OPENING_CONTROL','UNINVOICED_RECEIPT','LAUNDRY_VENDOR'")
    identity='erp._validate_migration_batch_base(uuid)'
    change(identity,"not in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPENING_CONTROL')","not in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPENING_CONTROL','UNINVOICED_RECEIPT')")
    identity='erp.prepare_migration_opening_balance(uuid,text)'
    old="coalesce(j->>'notes','Legacy roll opening row '||r.source_row_no));"
    change(identity,old,old[:-2]+') returning id into v_opening_item;\n    perform erp.link_initial_import_stock_source_v1(b.id,r.id,v_opening_item);')
    old='perform erp.check_initial_import_financial_source_v1(b.id,r.id,v_opening_item);'
    change(identity,old,old+'\n    perform erp.link_initial_import_stock_source_v1(b.id,r.id,v_opening_item);')
    identity='erp.save_initial_import_action_v1(text,jsonb,uuid)'
    change(identity,'     perform erp.validate_initial_import_totals_v1(b.id);','     perform erp.validate_initial_import_receipts_v1(b.id);\n     perform erp.validate_initial_import_totals_v1(b.id);')
    change(identity,'       perform erp.finalize_migration_batch(b.id);','       perform erp.apply_initial_import_receipts_v1(b.id);\n       perform erp.finalize_migration_batch(b.id);')
    identity='erp.validate_initial_import_totals_v1(uuid)'
    change(identity,"in('MATERIAL_ROLL','OPENING_BALANCE_ITEM')","in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','UNINVOICED_RECEIPT')")
    change(identity,"then 'MATERIAL' else upper(j->>'balance_type')","then 'MATERIAL' when r.entity_type='UNINVOICED_RECEIPT' then 'GRNI_MATERIAL' else upper(j->>'balance_type')")
    change(identity,"v_type in('MATERIAL','FINISHED_GOODS')","v_type in('MATERIAL','FINISHED_GOODS','GRNI_MATERIAL')")
    old="   if v_amount is null then raise exception 'amount: nilai rincian belum lengkap'; end if;"
    change(identity,old,"""   if r.entity_type='UNINVOICED_RECEIPT' then
     -- GRNI is rounded once per receipt document, exactly as its subledger.
     -- Physical opening value retains its existing per-stock-line rounding.
     if r.source_row_no=(select min(s.source_row_no) from erp.migration_staging_rows s where s.batch_id=p_batch_id
       and s.entity_type='UNINVOICED_RECEIPT' and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
       and lower(btrim(s.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'))) then
       select round(sum((s.normalized_payload->>'qty')::numeric*(s.normalized_payload->>'unit_cost')::numeric),2) into v_amount
       from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='UNINVOICED_RECEIPT'
         and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
         and lower(btrim(s.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'));
     else v_amount:=0;end if;
   end if;
"""+old)
    change(identity,"v_entry->>'type' in('MATERIAL','FINISHED_GOODS','BS')","v_entry->>'type' in('MATERIAL','FINISHED_GOODS','BS','GRNI_MATERIAL')")
    identity='erp.refresh_material_purchase_item_cost(uuid)'
    old='  update erp.material_stock_movements msm\n'
    change(identity,old,"""  if exists(select 1 from erp.initial_import_receipt_lines where purchase_item_id=i.id) then
    update erp.material_stock_movements m set input_unit_cost=v_cost
    from erp.initial_import_receipt_lines l
    where l.purchase_item_id=i.id and m.source_type='OPENING_BALANCE_ITEM' and m.source_id=l.opening_item_id
      and m.movement_type='OPENING' and m.qty_signed=i.qty;
    if not found then raise exception 'Opening source movement missing for imported receipt %',i.id;end if;
    perform erp.recalculate_material_cost(i.material_id,h.physical_at);
    return;
  end if;

"""+old)
    identity='erp.validate_supplier_return_source()'
    old="    if v_roll_purchase_item is null then raise exception 'Returned roll has no source purchase item'; end if;"
    change(identity,old,"""    if v_roll_purchase_item is null then
      select l.purchase_item_id into v_roll_purchase_item from erp.initial_import_receipt_lines l
      join erp.opening_balance_items i on i.id=l.opening_item_id where i.roll_id=new.roll_id;
    end if;
"""+old)
    old="  v_purchase_price:=erp.material_purchase_current_unit_cost(new.purchase_item_id);"
    change(identity,old,"""  if exists(select 1 from erp.initial_import_receipt_lines l join erp.opening_balance_items i on i.id=l.opening_item_id
    where l.purchase_item_id=new.purchase_item_id and i.roll_id is distinct from new.roll_id) then
    raise exception 'Return roll does not match imported opening source';end if;
"""+old)
    identity='erp.validate_material_supplier_invoice_line()'
    old='  return new;'
    change(identity,old,"""  if exists(select 1 from erp.initial_import_receipt_lines l
    join erp.initial_import_receipt_headers r on r.purchase_id=l.purchase_id
    join erp.material_supplier_invoices h on h.id=new.invoice_id
    where l.purchase_item_id=new.purchase_item_id and h.invoice_date<r.cutover_date) then
    raise exception 'Invoice penerimaan awal tidak boleh mendahului cutover; rekonsiliasi dokumen lama terlebih dahulu';end if;
"""+old)
    identity='erp.sync_material_purchase_grni_on_status()'
    old="  if old.status='DRAFT' and new.status='POSTED' then"
    change(identity,old,old+"""
    if exists(select 1 from erp.initial_import_receipt_headers where purchase_id=new.id) then
      select round(sum(qty*unit_price),2) into v_estimated from erp.material_purchase_items where purchase_id=new.id;
      if v_estimated>0 then
        perform erp.post_journal('OPENING_UNINVOICED_RECEIPT',new.id,erp._cp3_business_date(new.physical_at),
          'Opening receipt liability; physical stock already in opening balance',jsonb_build_array(
            jsonb_build_object('mapping_key','OPENING_EQUITY','debit',v_estimated,'credit',0),
            jsonb_build_object('mapping_key','GRNI_MATERIAL','debit',0,'credit',v_estimated)));
      end if;
      return new;
    end if;
""")
    identity='erp.run_v267_financial_truth_checks()'
    old="where j.source_type='MATERIAL_PURCHASE_GRNI_RECLASS' and j.source_id=h.id"
    change(identity,old,"""where (j.source_type='MATERIAL_PURCHASE_GRNI_RECLASS' or (
        j.source_type='OPENING_UNINVOICED_RECEIPT' and exists(select 1 from erp.initial_import_receipt_headers r where r.purchase_id=h.id))) and j.source_id=h.id""")
    old=';\n\n$function$'
    change(identity,old,"""
  union all
  select 'AP_OPENING_RECEIPT_SOURCE_DRIFT','CRITICAL',count(*)::bigint,
    'Imported receipts require an exact posted opening layer and no additional purchase movement'
  from erp.initial_import_receipt_headers rh join erp.material_purchase_headers h on h.id=rh.purchase_id
  where h.status<>'POSTED' or h.supplier_id<>rh.supplier_id or erp._cp3_business_date(h.physical_at)<>rh.cutover_date
    or not exists(select 1 from erp.initial_import_receipt_lines l where l.purchase_id=h.id)
    or exists(select 1 from erp.material_purchase_items pi left join erp.initial_import_receipt_lines l on l.purchase_item_id=pi.id
      left join erp.opening_balance_items oi on oi.id=l.opening_item_id left join erp.opening_balance_headers oh on oh.id=oi.opening_id
      where pi.purchase_id=h.id and (l.purchase_id is distinct from h.id or oh.status is distinct from 'POSTED'
        or oi.balance_type is distinct from 'MATERIAL' or pi.qty is distinct from oi.qty
        or pi.material_id is distinct from oi.material_id or pi.unit_price is distinct from oi.unit_cost_snapshot
        or oi.location_id is distinct from h.location_id
        or (select count(*) from erp.material_stock_movements m where m.source_type='OPENING_BALANCE_ITEM'
          and m.source_id=oi.id and m.movement_type='OPENING' and m.qty_signed=oi.qty)<>1
        or exists(select 1 from erp.material_stock_movements m where m.source_type='MATERIAL_PURCHASE_ITEM' and m.source_id=pi.id)))
  union all
  select 'AP_OPENING_RECEIPT_JOURNAL_DRIFT','CRITICAL',count(*)::bigint,
    'Imported GRNI opening has exact value, opening equity offset, and cutover date'
  from erp.initial_import_receipt_headers rh
  cross join lateral(select round(sum(qty*unit_price),2) value from erp.material_purchase_items where purchase_id=rh.purchase_id) v
  where (v.value>0 and not exists(select 1 from erp.journal_entries j where j.source_type='OPENING_UNINVOICED_RECEIPT'
    and j.source_id=rh.purchase_id and j.status='POSTED' and j.economic_date=rh.cutover_date
    and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(erp.account_id('OPENING_EQUITY')::text,v.value,erp.account_id('GRNI_MATERIAL')::text,-v.value)))
    or exists(select 1 from erp.journal_entries j where j.source_id=rh.purchase_id and j.source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS'))
"""+old)
    identity='erp.check_initial_import_financial_source_v1(uuid,uuid,uuid)'
    old=' v_result:=jsonb_build_object('
    change(identity,old,""" if v_type='SUPPLIER_PAYABLE' and (
   exists(select 1 from erp.initial_import_receipt_headers h where h.supplier_id=v_party
     and (v_mode='SUMMARY' or lower(btrim(h.receipt_number))=lower(v_number)))
   or exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='UNINVOICED_RECEIPT'
     and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and (v_mode='SUMMARY' or lower(btrim(s.normalized_payload->>'receipt_number'))=lower(v_number)))
 ) then raise exception 'document_number: utang awal tumpang tindih dengan penerimaan belum ditagih';end if;
"""+old)
    identity='erp.get_initial_import_workspace_v1(uuid)'
    old="     'opening_id',(select h.id"
    change(identity,old,"""     'uninvoiced_receipts',coalesce((select jsonb_agg(jsonb_build_object(
       'receipt_number',rh.receipt_number,'receipt_line_number',rl.receipt_line_number,'receipt_date',rh.receipt_date,
       'cutover_date',rh.cutover_date,'purchase_id',rh.purchase_id,'purchase_item_id',rl.purchase_item_id,
       'supplier_id',rh.supplier_id,'opening_item_id',rl.opening_item_id,
       'qty',pi.qty,'unmatched_qty',erp.material_purchase_invoice_capacity(pi.id)-erp.material_purchase_posted_invoice_qty(pi.id),
       'invoice_match_state',pi.invoice_match_state) order by rh.receipt_number,rl.receipt_line_number)
       from erp.initial_import_receipt_headers rh join erp.initial_import_receipt_lines rl on rl.purchase_id=rh.purchase_id
       join erp.material_purchase_items pi on pi.id=rl.purchase_item_id where rh.batch_id=b.id),'[]'::jsonb),
"""+old)
