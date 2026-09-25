-- ================================================================ BC import: ALL-C02 and ALL-C03
-- ALL-C02 (auditor r9: "old source stock issue is not replayed. Opening note receivable is only its evidenced unpaid residual
-- ... Once the 3 returned PCS are received and an explicit policy gives source credit, credit right is at most 3p ... If no
-- proven credit right, stock custody can be recorded as pending-value but no automatic contractor credit"; Fable C02: the
-- CONTRACTOR_RECEIVABLE opening document keeps 50/20 as provenance, the credit only at the old note's own price/qty).
-- New file OPENING_ACCESSORY_NOTE_LINE: the lines of the old note behind an imported CONTRACTOR_RECEIVABLE document of the same
-- batch (same contractor and document number); the line amounts add up to the document's original amount. Nothing is
-- journaled or moved; a later return uses RECEIVE_RETURN (NOTE_RETURN, opening_note_line_id) and CREDIT_NOTE_RETURN.
--
-- ALL-C03 (auditor r9: "only the evidenced usable 5 are ready stock; 2 remain quarantine ... 1 remains outstanding and is not
-- in available stock. Unknown-value recovery can be recorded physically as pending valuation with no artificial zero-cost
-- financial close"; Fable C03: M:3933 pending value, M:4882 no overlap). Valued company stock at the service post and at the
-- inspection/damaged areas is ordinary opening stock (OPENING_BALANCE_ITEM MATERIAL at the zone's location code: an opening
-- count may enter a zone). New file OPENING_ACCESSORY_CUSTODY carries what is not stock: PENDING_VALUE (company custody with
-- unknown recovery value at an inspection area, condition WAITING/USABLE/DAMAGED, labelled baseline count), UNRETURNED
-- (expected back from a holder, company- or customer-owned, not stock) and CUSTOMER_GARMENT (a customer's garment in
-- service: never company FG, AR or entitlement). Each row has a custody_key used once.

CREATE OR REPLACE FUNCTION erp.bc_check_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_qty numeric;v_amount numeric;v_count boolean;v_type text;v_doc record;v_kind text;
  v_zone text;v_total numeric;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch
    and entity_type in('OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY');
  if r.id is null then raise exception 'Baris aksesori saldo awal tidak ditemukan';end if;
  j:=r.normalized_payload;
  if r.entity_type='OPENING_ACCESSORY_NOTE_LINE' then
    foreach k in array array['document_number','contractor_code','line_number','material_sku','qty','line_amount'] loop
      if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk baris nota aksesori lama',k;end if;
    end loop;
    if j->>'line_number'!~'^[1-9][0-9]{0,2}$' then raise exception 'line_number: nomor baris 1-999';end if;
    select m.material_type,u.dimension='COUNT' into v_type,v_count from erp.materials m join erp.uom_definitions u on u.unit_code=m.unit_code
      where m.material_sku=j->>'material_sku' and m.is_active;
    if v_type is null then
      select upper(s.normalized_payload->>'material_type'),(select u.dimension='COUNT' from erp.uom_definitions u where u.unit_code=s.normalized_payload->>'unit_code')
        into v_type,v_count from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='MATERIAL' and s.validation_status='VALID'
          and s.normalized_payload->>'material_sku'=j->>'material_sku' limit 1;
    end if;
    if v_type is distinct from 'ACCESSORY' then raise exception 'material_sku: nota aksesori hanya untuk aksesori aktif';end if;
    if (v_count and j->>'qty'!~'^[1-9][0-9]{0,11}$') or (not v_count and j->>'qty'!~'^[0-9]{1,12}(\.[0-9]{1,6})?$') then
      raise exception 'qty: % positif',case when v_count then 'PCS utuh' else 'angka maksimal enam desimal' end;end if;
    v_qty:=(j->>'qty')::numeric;
    if v_qty<=0 then raise exception 'qty: harus lebih dari nol';end if;
    v_amount:=erp.bb_parse_amount_v1(j->>'line_amount','line_amount',true);
    -- The note's CONTRACTOR_RECEIVABLE opening document in this batch.
    select s.id,s.normalized_payload into v_doc from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
      and upper(s.normalized_payload->>'balance_type')='CONTRACTOR_RECEIVABLE' and s.normalized_payload->>'contractor_code'=j->>'contractor_code'
      and lower(btrim(s.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'));
    if v_doc.id is null then raise exception 'BC_C02_DOCUMENT_REQUIRED: piutang mandor saldo awal dengan nomor dokumen dan mandor ini tidak ada di impor';end if;
    if nullif(btrim(v_doc.normalized_payload->>'original_amount'),'') is null then
      raise exception 'BC_C02_DOCUMENT_REQUIRED: dokumen piutang mandor wajib membawa nominal dokumen awal';end if;
    if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPENING_ACCESSORY_NOTE_LINE' and x.id<>r.id
        and lower(btrim(x.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))
        and x.normalized_payload->>'contractor_code'=j->>'contractor_code' and x.normalized_payload->>'line_number'=j->>'line_number') then
      raise exception 'BC_C02_DUPLICATE_LINE: nomor baris nota ganda';end if;
    select sum(replace(btrim(x.normalized_payload->>'line_amount'),',','.')::numeric) into v_total from erp.migration_staging_rows x
      where x.batch_id=p_batch and x.entity_type='OPENING_ACCESSORY_NOTE_LINE' and x.normalized_payload->>'contractor_code'=j->>'contractor_code'
        and lower(btrim(x.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))
        and btrim(x.normalized_payload->>'line_amount')~'^[0-9]+([.,][0-9]{1,2})?$';
    if v_total is distinct from replace(btrim(v_doc.normalized_payload->>'original_amount'),',','.')::numeric then
      raise exception 'BC_C02_TOTAL_MISMATCH: jumlah baris nota % tidak sama dengan nominal dokumen awal %',v_total,v_doc.normalized_payload->>'original_amount';end if;
    return jsonb_build_object('qty',v_qty,'line_amount',v_amount,'document_row_id',v_doc.id);
  end if;
  -- OPENING_ACCESSORY_CUSTODY
  v_kind:=upper(coalesce(j->>'custody_kind',''));
  if v_kind not in('PENDING_VALUE','UNRETURNED','CUSTOMER_GARMENT') then
    raise exception 'custody_kind: PENDING_VALUE, UNRETURNED atau CUSTOMER_GARMENT';end if;
  if nullif(btrim(j->>'custody_key'),'') is null or length(btrim(j->>'custody_key'))>80 then raise exception 'custody_key: wajib, maksimal 80 karakter';end if;
  if exists(select 1 from erp.migration_staging_rows x where x.entity_type='OPENING_ACCESSORY_CUSTODY' and x.id<>r.id
      and lower(btrim(x.normalized_payload->>'custody_key'))=lower(btrim(j->>'custody_key'))
      and (x.batch_id=p_batch or x.posted_entity_id is not null)) then
    raise exception 'BC_C03_DUPLICATE: custody_key sudah dipakai; satu barang fisik hanya satu baris';end if;
  if nullif(btrim(j->>'unit_cost'),'') is not null then
    raise exception 'BC_C03_VALUED_ROW: barang bernilai adalah stok saldo awal biasa (OPENING_BALANCE_ITEM MATERIAL di lokasi zona), bukan titipan';end if;
  if j->>'qty'!~'^[1-9][0-9]{0,11}$' then raise exception 'qty: PCS utuh positif';end if;
  if v_kind in('PENDING_VALUE','UNRETURNED') and not (v_kind='UNRETURNED' and nullif(btrim(j->>'material_sku'),'') is null) then
    if not exists(select 1 from erp.materials m join erp.uom_definitions u on u.unit_code=m.unit_code where m.material_sku=j->>'material_sku'
        and m.is_active and m.material_type='ACCESSORY' and u.dimension='COUNT')
      and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='MATERIAL' and s.validation_status='VALID'
        and s.normalized_payload->>'material_sku'=j->>'material_sku' and upper(s.normalized_payload->>'material_type')='ACCESSORY') then
      raise exception 'material_sku: aksesori hitung aktif tidak ditemukan';end if;
  end if;
  if v_kind='PENDING_VALUE' then
    if upper(coalesce(j->>'condition',''))not in('WAITING','USABLE','DAMAGED') then raise exception 'condition: WAITING, USABLE atau DAMAGED';end if;
    select z.zone_kind into v_zone from erp.locations l join erp.bc_accessory_zones_v1 z on z.location_id=l.id
      where l.location_code=j->>'location_code' and l.is_active;
    if v_zone is distinct from 'INSPECTION' then
      raise exception 'location_code: titipan bernilai pending berada di area pemeriksaan terdaftar';end if;
  elsif v_kind='UNRETURNED' then
    if nullif(btrim(j->>'holder'),'') is null or length(btrim(j->>'holder'))>120 then raise exception 'holder: pemegang wajib diisi';end if;
    if upper(coalesce(j->>'owner_kind',''))not in('COMPANY','CUSTOMER') then raise exception 'owner_kind: COMPANY atau CUSTOMER';end if;
    if nullif(btrim(j->>'material_sku'),'') is null and nullif(btrim(j->>'description'),'') is null then
      raise exception 'description: isi aksesori atau keterangan barang';end if;
  else
    if nullif(btrim(j->>'customer_code'),'') is null or nullif(btrim(j->>'description'),'') is null then
      raise exception 'customer_code/description: titipan pelanggan wajib pelanggan dan keterangan';end if;
    if not exists(select 1 from erp.customers where customer_code=j->>'customer_code' and is_active)
      and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='CUSTOMER' and s.validation_status='VALID'
        and s.normalized_payload->>'customer_code'=j->>'customer_code') then raise exception 'customer_code: pelanggan aktif tidak ditemukan';end if;
  end if;
  return jsonb_build_object('kind',v_kind,'qty',(j->>'qty')::numeric);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_validate_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;
begin
  perform erp.require_owner_admin();
  for r in select id from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY')
      order by entity_type,source_row_no loop
    begin
      perform erp.bc_check_import_row_v1(p_batch,r.id);
      update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
    exception when others then
      update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;
    end;
  end loop;
end;$function$;

-- After the opening documents and stock are posted.
CREATE OR REPLACE FUNCTION erp.bc_apply_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;j jsonb;c jsonb;b erp.migration_batches%rowtype;v_balance uuid;v_material uuid;v_location uuid;v_id uuid;v_cond text;
begin
  perform erp.require_owner_admin();
  select * into b from erp.migration_batches where id=p_batch;
  for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_ACCESSORY_NOTE_LINE','OPENING_ACCESSORY_CUSTODY')
      and posted_entity_id is null order by entity_type,source_row_no loop
    if r.validation_status<>'VALID' then raise exception 'Baris aksesori saldo awal belum lolos pemeriksaan';end if;
    j:=r.normalized_payload;c:=erp.bc_check_import_row_v1(p_batch,r.id);v_id:=gen_random_uuid();
    if r.entity_type='OPENING_ACCESSORY_NOTE_LINE' then
      select ob.id into v_balance from erp.initial_import_financial_sources f join erp.opening_subledger_balances ob on ob.opening_item_id=f.opening_item_id
        where f.source_row_id=(c->>'document_row_id')::uuid;
      if v_balance is null then raise exception 'BC_C02_DOCUMENT_REQUIRED: piutang mandor dokumen % belum terbentuk',j->>'document_number';end if;
      select id into strict v_material from erp.materials where material_sku=j->>'material_sku';
      insert into erp.bc_opening_note_lines_v1(id,batch_id,source_row_id,balance_id,document_number,line_number,material_id,qty,line_amount)
      values(v_id,p_batch,r.id,v_balance,btrim(j->>'document_number'),(j->>'line_number')::int,v_material,(c->>'qty')::numeric,(c->>'line_amount')::numeric);
    elsif c->>'kind'='PENDING_VALUE' then
      select id into strict v_material from erp.materials where material_sku=j->>'material_sku';
      select id into strict v_location from erp.locations where location_code=j->>'location_code';
      v_cond:=upper(j->>'condition');
      insert into erp.bc_return_lots_v1(id,source_kind,owner_kind,value_mode,material_id,location_id,qty_received,init_usable,init_damaged,
        received_at,batch_id,source_row_id,reference)
      values(v_id,'OPENING_PENDING_VALUE','COMPANY','PENDING',v_material,v_location,(c->>'qty')::numeric,
        case when v_cond='USABLE' then (c->>'qty')::numeric else 0 end,case when v_cond='DAMAGED' then (c->>'qty')::numeric else 0 end,
        b.cutover_at,p_batch,r.id,'Opname awal '||btrim(j->>'custody_key')||coalesce(' — '||nullif(btrim(j->>'notes'),''),''));
    elsif c->>'kind'='UNRETURNED' then
      insert into erp.bc_outstanding_returns_v1(id,source_kind,owner_kind,material_id,description,qty_expected,holder,reference,batch_id,source_row_id)
      values(v_id,'OPENING_UNRETURNED',upper(j->>'owner_kind'),(select id from erp.materials where material_sku=nullif(btrim(j->>'material_sku'),'')),
        nullif(btrim(j->>'description'),''),(c->>'qty')::numeric,btrim(j->>'holder'),'Opname awal '||btrim(j->>'custody_key'),p_batch,r.id);
    else
      insert into erp.bc_customer_custody_v1(id,customer_id,product_id,description,qty,received_at,batch_id)
      values(v_id,(select id from erp.customers where customer_code=j->>'customer_code'),
        (select id from erp.products where lower(btrim(sku))=lower(btrim(nullif(j->>'product_sku','')))),
        btrim(j->>'description'),(c->>'qty')::numeric,b.cutover_at,p_batch);
    end if;
    update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type=r.entity_type,posted_at=statement_timestamp(),
      updated_at=statement_timestamp() where id=r.id;
  end loop;
  -- Valued opening stock counted at an inspection area (ALL-C03 quarantine, value kept): one ledger lot per opening row so the
  -- inspection can later move it to the warehouse or the damaged area at its value.
  insert into erp.bc_return_lots_v1(source_kind,owner_kind,value_mode,material_id,location_id,qty_received,received_at,batch_id,source_row_id,reference)
  select 'OPENING_QUARANTINE','COMPANY','LEDGER',i.material_id,i.location_id,i.qty,b.cutover_at,p_batch,i.id,'Opname awal area pemeriksaan (saldo awal '||i.id||')'
  from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
  join erp.bc_accessory_zones_v1 z on z.location_id=i.location_id and z.zone_kind='INSPECTION'
  where h.migration_batch_id=p_batch and i.balance_type='MATERIAL' and i.qty>0
    and not exists(select 1 from erp.bc_return_lots_v1 l where l.source_kind='OPENING_QUARANTINE' and l.source_row_id=i.id);
end;$function$;

-- The import workspace part (read only; the continuation is the accessory service workspace).
CREATE OR REPLACE FUNCTION erp.bc_import_workspace_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object(
    'accessory_note_lines',coalesce((select jsonb_agg(jsonb_build_object('line_id',n.id,'document_number',n.document_number,'line_number',n.line_number,
        'material_sku',m.material_sku,'qty',n.qty::text,'line_amount',n.line_amount::text,
        'returned',coalesce((select sum(l.qty_received) from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
          where l.opening_note_line_id=n.id and d.status='POSTED'),0)::text,
        'remaining_receivable',(b.original_amount-b.settled_amount)::text) order by n.document_number,n.line_number)
      from erp.bc_opening_note_lines_v1 n join erp.materials m on m.id=n.material_id join erp.opening_subledger_balances b on b.id=n.balance_id
      where n.batch_id=p_batch),'[]'::jsonb),
    'accessory_custody',coalesce((select jsonb_agg(x order by x->>'kind',x->>'key') from (
        select jsonb_build_object('kind','PENDING_VALUE','key',l.reference,'material_sku',m.material_sku,'qty',l.qty_received::text,
          'value_status','Belum dinilai','state',erp.bc_lot_state_v1(l.id)) x
        from erp.bc_return_lots_v1 l join erp.materials m on m.id=l.material_id where l.batch_id=p_batch
        union all select jsonb_build_object('kind','UNRETURNED','key',o.reference,'material_sku',m.material_sku,'description',o.description,
          'qty',o.qty_expected::text,'owner_kind',o.owner_kind,'holder',o.holder,'value_status','Belum kembali')
        from erp.bc_outstanding_returns_v1 o left join erp.materials m on m.id=o.material_id where o.batch_id=p_batch
        union all select jsonb_build_object('kind','CUSTOMER_GARMENT','key',c.description,'customer_code',k.customer_code,'qty',c.qty::text,
          'value_status','Milik pelanggan')
        from erp.bc_customer_custody_v1 c join erp.customers k on k.id=c.customer_id where c.batch_id=p_batch) s),'[]'::jsonb))
$function$;

CREATE OR REPLACE FUNCTION erp.bc_import_revision_part_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('note_lines',(select count(*) from erp.bc_opening_note_lines_v1 where batch_id=p_batch),
    'returns',(select coalesce(jsonb_agg(jsonb_build_object('id',d.id,'status',d.status,'v',d.row_version) order by d.id),'[]'::jsonb)
      from erp.bc_documents_v1 d where exists(select 1 from erp.bc_return_lots_v1 l join erp.bc_opening_note_lines_v1 n on n.id=l.opening_note_line_id
        where l.document_id=d.id and n.batch_id=p_batch)))
$function$;
