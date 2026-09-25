-- CP6 BB purchase part (ALL-P03). New objects only; changed functions are rebuilt by scripts/cp6_bb_build.py.
-- P03: one supplier receipt part invoiced before cutover and part still unbilled. The receipt stays one purchase item of
-- its full quantity; the invoiced part counts as already matched quantity at its invoiced price (so the item cost is the
-- blend of both parts and GRNI covers only the unbilled part), while the invoiced money stays the imported SUPPLIER_PAYABLE
-- document of that invoice, settled by the opening settlement route (P02). No supplier invoice, payment or cash row of the
-- old invoice is created (M:938).

create table erp.bb_receipt_invoiced_parts_v1(
  purchase_item_id uuid primary key references erp.material_purchase_items(id),
  source_row_id uuid not null unique references erp.migration_staging_rows(id),
  financial_source_id uuid not null unique references erp.initial_import_financial_sources(id),
  invoiced_qty numeric(18,6) not null check(invoiced_qty>0),
  invoiced_amount numeric(20,2) not null check(invoiced_amount>0),
  created_at timestamptz not null default statement_timestamp()
);
comment on table erp.bb_receipt_invoiced_parts_v1 is 'BB (ALL-P03): the part of an imported receipt line already invoiced before cutover: its quantity counts as matched and its invoiced amount enters the item cost; the money is the linked imported SUPPLIER_PAYABLE document.';
alter table erp.bb_receipt_invoiced_parts_v1 enable row level security;
revoke all on erp.bb_receipt_invoiced_parts_v1 from public,anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION erp.bb_guard_receipt_invoiced_part_v1()
 RETURNS trigger LANGUAGE plpgsql SET search_path TO ''
AS $function$
begin
  raise exception 'BB_RECEIPT_INVOICED_PART_IMMUTABLE: bagian penerimaan yang sudah ditagih sebelum saldo awal tidak diubah atau dihapus';
end;$function$;
create trigger trg_bb_receipt_invoiced_part_immutable before update or delete on erp.bb_receipt_invoiced_parts_v1
  for each row execute function erp.bb_guard_receipt_invoiced_part_v1();

CREATE OR REPLACE FUNCTION erp.bb_receipt_invoiced_qty_v1(p_purchase_item_id uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce((select invoiced_qty from erp.bb_receipt_invoiced_parts_v1 where purchase_item_id=p_purchase_item_id),0)::numeric $function$;

-- The unit cost an imported receipt line brings into opening stock: its estimate, or with an invoiced part the blend of
-- the unbilled quantity at the estimate and the invoiced amount, over the full quantity (six decimals, the stock column).
CREATE OR REPLACE FUNCTION erp.bb_receipt_opening_unit_cost_v1(p_purchase_item_id uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select case when p.purchase_item_id is null then i.unit_price
    else round(((i.qty-p.invoiced_qty)*i.unit_price+p.invoiced_amount)/i.qty,6) end::numeric
  from erp.material_purchase_items i left join erp.bb_receipt_invoiced_parts_v1 p on p.purchase_item_id=i.id
  where i.id=p_purchase_item_id
$function$;

-- The invoiced part an UNINVOICED_RECEIPT row declares (invoice_document_number + invoiced_qty), read from the batch:
-- the linked SUPPLIER_PAYABLE document row of the same supplier and its original (gross) amount. Null without a part.
CREATE OR REPLACE FUNCTION erp.bb_receipt_row_invoiced_part_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare j jsonb;v_qty numeric;v_doc erp.migration_staging_rows%rowtype;v_amount numeric;v_count integer;
begin
  select normalized_payload into j from erp.migration_staging_rows where id=p_row and batch_id=p_batch and entity_type='UNINVOICED_RECEIPT';
  if nullif(btrim(j->>'invoice_document_number'),'') is null and nullif(btrim(j->>'invoiced_qty'),'') is null then return null;end if;
  if nullif(btrim(j->>'invoice_document_number'),'') is null or nullif(btrim(j->>'invoiced_qty'),'') is null then
    raise exception 'P03_INVOICED_PART_INCOMPLETE: isi nomor invoice asal dan jumlah yang sudah ditagih bersama-sama';
  end if;
  begin v_qty:=(j->>'invoiced_qty')::numeric;exception when others then v_qty:=null;end;
  if v_qty is null or v_qty::text in('NaN','Infinity','-Infinity') or v_qty<=0 or v_qty<>round(v_qty,6) then
    raise exception 'P03_INVOICED_QTY_INVALID: jumlah yang sudah ditagih harus positif, maksimal enam desimal';
  end if;
  if lower(btrim(j->>'invoice_document_number'))=lower(btrim(j->>'receipt_number')) then
    raise exception 'P03_INVOICE_DOC_DUPLICATE: nomor invoice harus berbeda dari nomor penerimaan';
  end if;
  select count(*) into v_count from erp.migration_staging_rows d where d.batch_id=p_batch and d.entity_type='OPENING_BALANCE_ITEM'
    and upper(d.normalized_payload->>'balance_type')='SUPPLIER_PAYABLE' and d.normalized_payload->>'supplier_code'=j->>'supplier_code'
    and lower(btrim(d.normalized_payload->>'document_number'))=lower(btrim(j->>'invoice_document_number'));
  if v_count<>1 then
    raise exception 'P03_INVOICE_DOC_REQUIRED: invoice asal harus tepat satu dokumen hutang supplier yang sama dalam batch ini';
  end if;
  select * into v_doc from erp.migration_staging_rows d where d.batch_id=p_batch and d.entity_type='OPENING_BALANCE_ITEM'
    and upper(d.normalized_payload->>'balance_type')='SUPPLIER_PAYABLE' and d.normalized_payload->>'supplier_code'=j->>'supplier_code'
    and lower(btrim(d.normalized_payload->>'document_number'))=lower(btrim(j->>'invoice_document_number'));
  begin v_amount:=replace(v_doc.normalized_payload->>'original_amount',',','.')::numeric;exception when others then v_amount:=null;end;
  if v_amount is null or v_amount<=0 then
    raise exception 'P03_INVOICE_DOC_REQUIRED: dokumen invoice asal memerlukan nominal dokumen awal';
  end if;
  if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='UNINVOICED_RECEIPT' and x.id<>p_row
      and x.normalized_payload->>'supplier_code'=j->>'supplier_code'
      and lower(btrim(x.normalized_payload->>'invoice_document_number'))=lower(btrim(j->>'invoice_document_number'))) then
    raise exception 'P03_INVOICE_DOC_DUPLICATE: satu invoice asal hanya untuk satu baris penerimaan';
  end if;
  return jsonb_build_object('invoiced_qty',v_qty,'invoiced_amount',v_amount,'document_row_id',v_doc.id,
    'document_number',btrim(v_doc.normalized_payload->>'document_number'));
end;$function$;

do $grants$
declare f text;
begin
  for f in select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='erp' and p.proname in('bb_guard_receipt_invoiced_part_v1','bb_receipt_invoiced_qty_v1',
        'bb_receipt_opening_unit_cost_v1','bb_receipt_row_invoiced_part_v1') loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
  end loop;
end $grants$;

-- ---------------------------------------------------------------- P04: purchase orders not (fully) received at cutover
-- An open purchase commitment is imported as its remaining quantity: a registry of the old order (ordered, received and
-- cancelled before cutover, remaining) and one native DRAFT receipt per order for the remaining quantity. Nothing is
-- received, costed or journaled at import. The ordinary purchase page edits the draft to what really arrives and posts it;
-- the draft may not be posted before cutover, for a material the order does not have, or over the order's remaining
-- quantity (cancellations and earlier posted receipts of the order counted, reversed receipts not). The remainder is
-- cancelled or reopened as a new draft through the import action PURCHASE_COMMITMENT.
create table erp.bb_purchase_commitments_v1(
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references erp.migration_batches(id),
  supplier_id uuid not null references erp.suppliers(id),
  po_number text not null check(length(btrim(po_number)) between 1 and 60),
  po_date date not null,
  location_id uuid not null references erp.locations(id),
  expected_date date,
  cutover_date date not null,
  created_at timestamptz not null default statement_timestamp(),
  check(po_date<=cutover_date)
);
create unique index bb_purchase_commitments_v1_number on erp.bb_purchase_commitments_v1(supplier_id,lower(btrim(po_number)));
create table erp.bb_purchase_commitment_lines_v1(
  id uuid primary key default gen_random_uuid(),
  commitment_id uuid not null references erp.bb_purchase_commitments_v1(id),
  source_row_id uuid not null unique references erp.migration_staging_rows(id),
  line_number text not null,
  material_id uuid not null references erp.materials(id),
  ordered_qty numeric(18,6) not null check(ordered_qty>0),
  received_before_cutover_qty numeric(18,6) not null check(received_before_cutover_qty>=0),
  cancelled_before_cutover_qty numeric(18,6) not null check(cancelled_before_cutover_qty>=0),
  remaining_at_cutover numeric(18,6) not null check(remaining_at_cutover>0),
  unit_price numeric(18,6) not null check(unit_price>=0),
  check(ordered_qty-received_before_cutover_qty-cancelled_before_cutover_qty=remaining_at_cutover),
  unique(commitment_id,material_id)
);
create unique index bb_purchase_commitment_lines_v1_number on erp.bb_purchase_commitment_lines_v1(commitment_id,lower(btrim(line_number)));
create table erp.bb_purchase_commitment_drafts_v1(
  purchase_id uuid primary key references erp.material_purchase_headers(id),
  commitment_id uuid not null references erp.bb_purchase_commitments_v1(id),
  sequence_no integer not null check(sequence_no>=1),
  created_at timestamptz not null default statement_timestamp(),
  unique(commitment_id,sequence_no)
);
create table erp.bb_purchase_commitment_cancellations_v1(
  id uuid primary key,
  line_id uuid not null references erp.bb_purchase_commitment_lines_v1(id),
  qty numeric(18,6) not null check(qty>0),
  effective_date date not null,
  reason text not null check(length(btrim(reason))>0),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp()
);
comment on table erp.bb_purchase_commitments_v1 is 'BB (ALL-P04): a purchase order still open at cutover (remaining quantity only); its receipts are native DRAFT purchases in erp.bb_purchase_commitment_drafts_v1.';
do $rls$
declare t text;
begin
  foreach t in array array['bb_purchase_commitments_v1','bb_purchase_commitment_lines_v1','bb_purchase_commitment_drafts_v1',
    'bb_purchase_commitment_cancellations_v1'] loop
    execute format('alter table erp.%I enable row level security',t);
    execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
  end loop;
end $rls$;

-- What an order line still expects: remaining at cutover less cancellations and less the posted receipts of the order.
CREATE OR REPLACE FUNCTION erp.bb_commitment_line_remaining_v1(p_line uuid,p_except_purchase uuid DEFAULT NULL)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select l.remaining_at_cutover
    -coalesce((select sum(c.qty) from erp.bb_purchase_commitment_cancellations_v1 c where c.line_id=l.id),0)
    -coalesce((select sum(i.qty) from erp.bb_purchase_commitment_drafts_v1 d join erp.material_purchase_headers h on h.id=d.purchase_id
        join erp.material_purchase_items i on i.purchase_id=h.id
        where d.commitment_id=l.commitment_id and h.status='POSTED' and i.material_id=l.material_id
          and h.id is distinct from p_except_purchase),0)
  from erp.bb_purchase_commitment_lines_v1 l where l.id=p_line
$function$;

CREATE OR REPLACE FUNCTION erp.bb_guard_commitment_draft_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare c erp.bb_purchase_commitments_v1%rowtype;r record;v_line erp.bb_purchase_commitment_lines_v1%rowtype;v_remaining numeric;
begin
  select k.* into c from erp.bb_purchase_commitment_drafts_v1 d join erp.bb_purchase_commitments_v1 k on k.id=d.commitment_id
    where d.purchase_id=coalesce(new.id,old.id);
  if c.id is null then return coalesce(new,old);end if;
  if TG_OP='DELETE' then
    raise exception 'P04_DELETE_USE_CANCEL: draf penerimaan dari PO lama tidak dihapus; batalkan sisa PO lewat impor';
  end if;
  if new.supplier_id is distinct from old.supplier_id then
    raise exception 'P04_SUPPLIER_CHANGED: supplier draf penerimaan PO lama tidak dapat diganti';
  end if;
  if old.status='DRAFT' and new.status='POSTED' then
    perform pg_advisory_xact_lock(hashtextextended('BB_P04_COMMITMENT:'||c.id::text,0));
    if erp._cp3_business_date(new.physical_at)<c.cutover_date then
      raise exception 'P04_BEFORE_CUTOVER: penerimaan PO lama harus bertanggal sejak saldo awal %',c.cutover_date;
    end if;
    for r in select i.material_id,sum(i.qty) qty from erp.material_purchase_items i where i.purchase_id=new.id group by i.material_id loop
      select * into v_line from erp.bb_purchase_commitment_lines_v1 where commitment_id=c.id and material_id=r.material_id;
      if v_line.id is null then
        raise exception 'P04_MATERIAL_NOT_ORDERED: bahan ini tidak ada pada PO %',c.po_number;
      end if;
      v_remaining:=erp.bb_commitment_line_remaining_v1(v_line.id,new.id);
      if r.qty>v_remaining then
        raise exception 'P04_EXCEEDS_REMAINING: sisa PO % untuk bahan ini %, diterima %',c.po_number,v_remaining,r.qty;
      end if;
    end loop;
  end if;
  return new;
end;$function$;
create trigger trg_bb_commitment_draft before update or delete on erp.material_purchase_headers
  for each row execute function erp.bb_guard_commitment_draft_v1();

CREATE OR REPLACE FUNCTION erp.bb_check_purchase_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_cutover date;v_supplier uuid;v_material uuid;v_location uuid;
  v_ordered numeric;v_received numeric;v_cancelled numeric;v_remaining numeric;v_price numeric;v_date date;v_expected date;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch and entity_type='OPEN_PURCHASE_ORDER';
  if r.id is null then raise exception 'Baris PO pembelian tidak ditemukan';end if;
  j:=r.normalized_payload;
  foreach k in array array['po_number','po_line_number','po_date','supplier_code','location_code','material_sku','ordered_qty',
      'received_before_cutover_qty','cancelled_before_cutover_qty','remaining_qty','unit_price'] loop
    if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk PO pembelian terbuka',k;end if;
  end loop;
  if length(btrim(j->>'po_number'))>60 or length(btrim(j->>'po_line_number'))>60 then raise exception 'po_number: maksimal 60 karakter';end if;
  select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch;
  v_date:=erp.bb_parse_date_v1(j->>'po_date','po_date');
  if v_date>v_cutover then raise exception 'po_date: PO harus dibuat sebelum saldo awal';end if;
  if nullif(btrim(j->>'expected_date'),'') is not null then v_expected:=erp.bb_parse_date_v1(j->>'expected_date','expected_date');end if;
  foreach k in array array['ordered_qty','received_before_cutover_qty','cancelled_before_cutover_qty','remaining_qty','unit_price'] loop
    if j->>k !~ '^[0-9]+([.][0-9]{1,6})?$' then raise exception '%: angka nonnegatif maksimal enam desimal',k;end if;
  end loop;
  v_ordered:=(j->>'ordered_qty')::numeric;v_received:=(j->>'received_before_cutover_qty')::numeric;
  v_cancelled:=(j->>'cancelled_before_cutover_qty')::numeric;v_remaining:=(j->>'remaining_qty')::numeric;v_price:=(j->>'unit_price')::numeric;
  if v_ordered<=0 or v_remaining<=0 or v_ordered-v_received-v_cancelled<>v_remaining then
    raise exception 'P04_REMAINING_EQUATION: sisa PO harus positif dan sama dengan dipesan dikurangi diterima dan dibatalkan sebelum saldo awal';
  end if;
  select id into v_supplier from erp.suppliers where supplier_code=j->>'supplier_code' and is_active;
  if v_supplier is null and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='SUPPLIER'
      and validation_status='VALID' and normalized_payload->>'supplier_code'=j->>'supplier_code') then
    raise exception 'supplier_code: supplier aktif tidak ditemukan';
  end if;
  if not exists(select 1 from erp.materials where material_sku=j->>'material_sku' and is_active)
    and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='MATERIAL' and validation_status='VALID'
      and normalized_payload->>'material_sku'=j->>'material_sku') then
    raise exception 'material_sku: bahan aktif tidak ditemukan';
  end if;
  if not exists(select 1 from erp.locations where location_code=j->>'location_code' and is_active and location_type='RAW_MATERIAL_WAREHOUSE')
    and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='LOCATION' and validation_status='VALID'
      and normalized_payload->>'location_code'=j->>'location_code' and normalized_payload->>'location_type'='RAW_MATERIAL_WAREHOUSE') then
    raise exception 'location_code: gudang bahan aktif tidak ditemukan';
  end if;
  if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPEN_PURCHASE_ORDER' and x.id<>r.id
      and x.normalized_payload->>'supplier_code'=j->>'supplier_code' and lower(btrim(x.normalized_payload->>'po_number'))=lower(btrim(j->>'po_number'))
      and (lower(btrim(x.normalized_payload->>'po_line_number'))=lower(btrim(j->>'po_line_number'))
        or x.normalized_payload->>'material_sku'=j->>'material_sku'
        or x.normalized_payload->>'po_date'<>j->>'po_date' or x.normalized_payload->>'location_code'<>j->>'location_code'
        or coalesce(x.normalized_payload->>'expected_date','')<>coalesce(j->>'expected_date',''))) then
    raise exception 'P04_DUPLICATE_PO: baris PO ganda atau rincian kepala PO tidak konsisten';
  end if;
  if v_supplier is not null and exists(select 1 from erp.bb_purchase_commitments_v1 c where c.supplier_id=v_supplier
      and lower(btrim(c.po_number))=lower(btrim(j->>'po_number'))) then
    raise exception 'P04_DUPLICATE_PO: PO ini sudah diimpor';
  end if;
  if exists(select 1 from erp.material_purchase_headers where lower(btrim(purchase_number))=lower(btrim(j->>'po_number')))
    or exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='UNINVOICED_RECEIPT'
      and x.normalized_payload->>'supplier_code'=j->>'supplier_code' and lower(btrim(x.normalized_payload->>'receipt_number'))=lower(btrim(j->>'po_number')))
    or (v_supplier is not null and exists(select 1 from erp.initial_import_receipt_headers h where h.supplier_id=v_supplier
      and lower(btrim(h.receipt_number))=lower(btrim(j->>'po_number')))) then
    raise exception 'P04_PO_NUMBER_IS_RECEIPT: nomor PO sudah dipakai sebagai nomor penerimaan';
  end if;
  return jsonb_build_object('supplier_id',v_supplier,'cutover_date',v_cutover,'po_date',v_date,'expected_date',v_expected);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_validate_purchase_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;
begin
  perform erp.require_owner_admin();
  for r in select id from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPEN_PURCHASE_ORDER' order by source_row_no loop
    begin
      perform erp.bb_check_purchase_import_row_v1(p_batch,r.id);
      update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
    exception when others then
      update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;
    end;
  end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_open_commitment_draft_v1(p_commitment uuid,p_physical_at timestamptz,p_note text)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare c erp.bb_purchase_commitments_v1%rowtype;v_purchase uuid:=gen_random_uuid();v_seq integer;l record;v_any boolean:=false;
begin
  select * into c from erp.bb_purchase_commitments_v1 where id=p_commitment for update;
  select coalesce(max(sequence_no),0)+1 into v_seq from erp.bb_purchase_commitment_drafts_v1 where commitment_id=c.id;
  insert into erp.material_purchase_headers(id,purchase_number,supplier_id,physical_at,status,location_id,notes,created_by)
  values(v_purchase,case when v_seq=1 then c.po_number else c.po_number||'/R'||(v_seq-1) end,c.supplier_id,p_physical_at,'DRAFT',
    c.location_id,p_note,erp.current_app_user_id());
  insert into erp.bb_purchase_commitment_drafts_v1(purchase_id,commitment_id,sequence_no) values(v_purchase,c.id,v_seq);
  for l in select * from erp.bb_purchase_commitment_lines_v1 where commitment_id=c.id order by line_number,id loop
    if erp.bb_commitment_line_remaining_v1(l.id)>0 then
      insert into erp.material_purchase_items(purchase_id,material_id,qty,unit_price,price_state,price_source,notes)
      values(v_purchase,l.material_id,erp.bb_commitment_line_remaining_v1(l.id),l.unit_price,'ESTIMATED','MANUAL_ESTIMATE','Sisa PO '||c.po_number||' baris '||l.line_number);
      v_any:=true;
    end if;
  end loop;
  if not v_any then raise exception 'P04_NOTHING_REMAINING: PO % tidak memiliki sisa',c.po_number;end if;
  return v_purchase;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_apply_purchase_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;j jsonb;c jsonb;v_commitment uuid;v_supplier uuid;v_material uuid;v_location uuid;v_line uuid;b erp.migration_batches%rowtype;
begin
  perform erp.require_owner_admin();
  select * into b from erp.migration_batches where id=p_batch;
  for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPEN_PURCHASE_ORDER' and posted_entity_id is null
      order by normalized_payload->>'supplier_code',lower(btrim(normalized_payload->>'po_number')),source_row_no loop
    if r.validation_status<>'VALID' then raise exception 'PO pembelian belum lolos pemeriksaan';end if;
    j:=r.normalized_payload;
    perform pg_advisory_xact_lock(hashtextextended('BB_P04_PO:'||(j->>'supplier_code')||':'||lower(btrim(j->>'po_number')),0));
    c:=erp.bb_check_purchase_import_row_v1(p_batch,r.id);
    select id into strict v_supplier from erp.suppliers where supplier_code=j->>'supplier_code' and is_active;
    select id into strict v_material from erp.materials where material_sku=j->>'material_sku' and is_active;
    select id into strict v_location from erp.locations where location_code=j->>'location_code' and is_active and location_type='RAW_MATERIAL_WAREHOUSE';
    select id into v_commitment from erp.bb_purchase_commitments_v1 where batch_id=p_batch and supplier_id=v_supplier
      and lower(btrim(po_number))=lower(btrim(j->>'po_number'));
    if v_commitment is null then
      insert into erp.bb_purchase_commitments_v1(batch_id,supplier_id,po_number,po_date,location_id,expected_date,cutover_date)
      values(p_batch,v_supplier,btrim(j->>'po_number'),(c->>'po_date')::date,v_location,(c->>'expected_date')::date,(c->>'cutover_date')::date)
      returning id into v_commitment;
    end if;
    insert into erp.bb_purchase_commitment_lines_v1(commitment_id,source_row_id,line_number,material_id,ordered_qty,received_before_cutover_qty,
      cancelled_before_cutover_qty,remaining_at_cutover,unit_price)
    values(v_commitment,r.id,btrim(j->>'po_line_number'),v_material,(j->>'ordered_qty')::numeric,(j->>'received_before_cutover_qty')::numeric,
      (j->>'cancelled_before_cutover_qty')::numeric,(j->>'remaining_qty')::numeric,(j->>'unit_price')::numeric)
    returning id into v_line;
    update erp.migration_staging_rows set posted_entity_id=v_line,posted_entity_type='OPEN_PURCHASE_ORDER',posted_at=statement_timestamp(),
      updated_at=statement_timestamp() where id=r.id;
  end loop;
  -- One native DRAFT receipt per imported order, for its remaining quantity, dated at cutover (the user dates the real receipt).
  for r in select id,po_number from erp.bb_purchase_commitments_v1 where batch_id=p_batch order by id loop
    perform erp.bb_open_commitment_draft_v1(r.id,b.cutover_at,'Sisa PO '||r.po_number||' saat saldo awal; ubah ke penerimaan nyata sebelum posting');
  end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_manage_purchase_commitment_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_op text:=upper(coalesce(nullif(btrim(p_payload->>'operation'),''),''));v_batch uuid:=(p_payload->>'batch_id')::uuid;
  c erp.bb_purchase_commitments_v1%rowtype;l erp.bb_purchase_commitment_lines_v1%rowtype;v_reason text:=nullif(btrim(p_payload->>'reason'),'');
  v_qty numeric;v_date date;v_remaining numeric;v_purchase uuid;
begin
  if v_op not in('CANCEL','REOPEN_REMAINDER') then raise exception 'P04_OPERATION: operasi tidak dikenal';end if;
  if v_reason is null then raise exception 'BB_OSS_REASON_REQUIRED: alasan wajib diisi';end if;
  select * into c from erp.bb_purchase_commitments_v1 where id=(p_payload->>'commitment_id')::uuid for update;
  if c.id is null or c.batch_id is distinct from v_batch then raise exception 'P04_NOT_IN_BATCH: PO bukan milik impor ini';end if;
  perform pg_advisory_xact_lock(hashtextextended('BB_P04_COMMITMENT:'||c.id::text,0));
  if v_op='CANCEL' then
    select * into l from erp.bb_purchase_commitment_lines_v1 where id=(p_payload->>'line_id')::uuid and commitment_id=c.id;
    if l.id is null then raise exception 'P04_NOT_IN_BATCH: baris PO tidak ditemukan';end if;
    if coalesce(p_payload->>'qty','') !~ '^[0-9]+([.][0-9]{1,6})?$' or (p_payload->>'qty')::numeric<=0 then
      raise exception 'P04_CANCEL_QTY_INVALID: jumlah batal positif maksimal enam desimal';
    end if;
    v_qty:=(p_payload->>'qty')::numeric;
    v_date:=erp.bb_parse_date_v1(p_payload->>'effective_date','effective_date');
    if v_date<c.cutover_date or v_date>erp.bb_business_today_v1() then
      raise exception 'BB_OSS_DATE_OUT_OF_RANGE: tanggal batal antara % dan hari ini',c.cutover_date;
    end if;
    v_remaining:=erp.bb_commitment_line_remaining_v1(l.id);
    if v_qty>v_remaining then raise exception 'P04_CANCEL_EXCEEDS: sisa PO %, dibatalkan %',v_remaining,v_qty;end if;
    insert into erp.bb_purchase_commitment_cancellations_v1(id,line_id,qty,effective_date,reason,created_by)
    values(p_request,l.id,v_qty,v_date,v_reason,erp.current_app_user_id());
    return jsonb_build_object('operation',v_op,'line_id',l.id,'remaining',erp.bb_commitment_line_remaining_v1(l.id)::text);
  end if;
  if exists(select 1 from erp.bb_purchase_commitment_drafts_v1 d join erp.material_purchase_headers h on h.id=d.purchase_id
      where d.commitment_id=c.id and h.status='DRAFT') then
    raise exception 'P04_DRAFT_OPEN: masih ada draf penerimaan PO ini; posting atau gunakan draf itu';
  end if;
  v_purchase:=erp.bb_open_commitment_draft_v1(c.id,statement_timestamp(),'Sisa PO '||c.po_number||': '||v_reason);
  return jsonb_build_object('operation',v_op,'purchase_id',v_purchase);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_purchase_workspace_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object(
    'purchase_commitments',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'po_number',c.po_number,'po_date',c.po_date,
        'supplier_code',s.supplier_code,'supplier_name',s.supplier_name,'expected_date',c.expected_date,
        'lines',(select jsonb_agg(jsonb_build_object('id',l.id,'line_number',l.line_number,'material_sku',m.material_sku,
            'ordered_qty',l.ordered_qty::text,'received_before_cutover_qty',l.received_before_cutover_qty::text,
            'cancelled_before_cutover_qty',l.cancelled_before_cutover_qty::text,'remaining_at_cutover',l.remaining_at_cutover::text,
            'cancelled_after_cutover',coalesce((select sum(x.qty) from erp.bb_purchase_commitment_cancellations_v1 x where x.line_id=l.id),0)::text,
            'remaining_qty',erp.bb_commitment_line_remaining_v1(l.id)::text,'unit_price',l.unit_price::text) order by l.line_number,l.id)
          from erp.bb_purchase_commitment_lines_v1 l join erp.materials m on m.id=l.material_id where l.commitment_id=c.id),
        'drafts',(select jsonb_agg(jsonb_build_object('purchase_id',h.id,'purchase_number',h.purchase_number,'status',h.status,
            'row_version',h.row_version::text,'physical_at',h.physical_at) order by d.sequence_no)
          from erp.bb_purchase_commitment_drafts_v1 d join erp.material_purchase_headers h on h.id=d.purchase_id where d.commitment_id=c.id))
        order by c.po_number,c.id)
      from erp.bb_purchase_commitments_v1 c join erp.suppliers s on s.id=c.supplier_id where c.batch_id=p_batch),'[]'::jsonb))
$function$;

CREATE OR REPLACE FUNCTION erp.bb_purchase_revision_part_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object(
    'commitments',coalesce((select jsonb_agg(to_jsonb(c) order by c.id) from erp.bb_purchase_commitments_v1 c where c.batch_id=p_batch),'[]'::jsonb),
    'cancellations',coalesce((select jsonb_agg(to_jsonb(x) order by x.id) from erp.bb_purchase_commitment_cancellations_v1 x
      join erp.bb_purchase_commitment_lines_v1 l on l.id=x.line_id join erp.bb_purchase_commitments_v1 c on c.id=l.commitment_id
      where c.batch_id=p_batch),'[]'::jsonb),
    'drafts',coalesce((select jsonb_agg(jsonb_build_object('purchase_id',h.id,'status',h.status,'row_version',h.row_version) order by h.id)
      from erp.bb_purchase_commitment_drafts_v1 d join erp.material_purchase_headers h on h.id=d.purchase_id
      join erp.bb_purchase_commitments_v1 c on c.id=d.commitment_id where c.batch_id=p_batch),'[]'::jsonb))
$function$;

do $grants$
declare f text;
begin
  for f in select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='erp' and p.proname like 'bb\_%' loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
  end loop;
end $grants$;
