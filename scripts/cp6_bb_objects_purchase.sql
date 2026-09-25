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
