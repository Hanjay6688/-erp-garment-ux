-- BB (ALL-S02): a sales draft open at cutover with its official stock reservation. Oracles: auditor r9 ALL-S02
-- (out/r9_all_oracle.md: "preserve original draft/reservation identity and explain its cutover provenance ... availability =
-- 10-3 = 7; edit 3->2 releases exactly 1 ... cancel releases reservation only; posting removes actual fulfilled qty exactly
-- once ... reject reservation > physical eligible FG, duplicate reserve ... competing reservations whose aggregate exceeds 10")
-- and Fable's (out/fable_all22_oracles_pre_code.md S02: M:3821 "reserve resmi sekali; POST tidak stock-out kedua"; refused:
-- inventing the old draft as a new document with a false physical date, reserving the same pieces twice). The more fail-closed
-- reading is kept: the reservation is carried (the promised pieces are never offered again), through the native draft only.
--
-- New file OPEN_SALES_DRAFT (one row per draft line). At FINALIZE, after the opening stock, each draft becomes ONE native
-- DRAFT sale through erp.save_sale_draft_v2 (the native reservation, SALE_RESERVE, once), numbered with the old draft number,
-- dated at cutover (the reservation held at cutover; no date before it is invented) and carrying its provenance (old draft
-- date) in erp.bb_open_sales_drafts_v1. No revenue, receivable, cost or shipment exists until the native POST. A trigger keeps
-- the draft's identity (number, customer) and refuses any sale date before cutover; editing, cancelling and posting are the
-- native sales commands.

create table erp.bb_open_sales_drafts_v1(
  sale_id uuid primary key references erp.sales_headers(id),
  batch_id uuid not null references erp.migration_batches(id),
  draft_number text not null check(length(btrim(draft_number)) between 1 and 60),
  draft_date date not null,
  customer_id uuid not null references erp.customers(id),
  cutover_at timestamptz not null,
  created_at timestamptz not null default statement_timestamp(),
  check(draft_date<=(cutover_at at time zone 'Asia/Jakarta')::date)
);
create unique index bb_open_sales_drafts_v1_number on erp.bb_open_sales_drafts_v1(lower(btrim(draft_number)));
create table erp.bb_open_sales_draft_lines_v1(
  source_row_id uuid primary key references erp.migration_staging_rows(id),
  sale_id uuid not null references erp.bb_open_sales_drafts_v1(sale_id),
  line_number text not null check(length(btrim(line_number)) between 1 and 60),
  product_id uuid not null references erp.products(id),
  qty_pcs integer not null check(qty_pcs>0),
  unit_price numeric(18,2) not null check(unit_price>=0),
  discount_amount numeric(18,2) not null check(discount_amount>=0),
  check(discount_amount<=qty_pcs*unit_price)
);
create unique index bb_open_sales_draft_lines_v1_number on erp.bb_open_sales_draft_lines_v1(sale_id,lower(btrim(line_number)));
comment on table erp.bb_open_sales_drafts_v1 is 'BB (ALL-S02): a sales draft open at cutover, continued as the native DRAFT sale sale_id (reservation made once by erp.save_sale_draft_v2 at import); draft_date is the old draft''s date, provenance only.';
do $rls$
declare t text;
begin
  foreach t in array array['bb_open_sales_drafts_v1','bb_open_sales_draft_lines_v1'] loop
    execute format('alter table erp.%I enable row level security',t);
    execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
  end loop;
end $rls$;

-- The carried draft keeps its identity and is never dated before cutover (its reservation and its sale would then precede
-- the opening stock they take).
CREATE OR REPLACE FUNCTION erp.bb_guard_open_sales_draft_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare d erp.bb_open_sales_drafts_v1%rowtype;
begin
  select * into d from erp.bb_open_sales_drafts_v1 where sale_id=old.id;
  if d.sale_id is null then return case when tg_op='DELETE' then old else new end;end if;
  if tg_op='DELETE' then raise exception 'BB_S02_DRAFT_KEPT: draf penjualan dari saldo awal tidak dapat dihapus; batalkan lewat halaman penjualan';end if;
  if new.sale_number is distinct from old.sale_number or new.customer_id is distinct from old.customer_id then
    raise exception 'BB_S02_IDENTITY: nomor dan pelanggan draf penjualan dari saldo awal tidak dapat diubah';
  end if;
  if new.sale_date<d.cutover_at then
    raise exception 'BB_S02_DATE_BEFORE_CUTOVER: tanggal invoice draf dari saldo awal tidak boleh sebelum saldo awal';
  end if;
  return new;
end;$function$;
create trigger trg_bb_open_sales_draft before update or delete on erp.sales_headers
  for each row execute function erp.bb_guard_open_sales_draft_v1();

CREATE OR REPLACE FUNCTION erp.bb_check_sales_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_cutover date;v_date date;v_due date;v_qty integer;v_price numeric;v_discount numeric;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch and entity_type='OPEN_SALES_DRAFT';
  if r.id is null then raise exception 'Baris draf penjualan tidak ditemukan';end if;
  j:=r.normalized_payload;
  foreach k in array array['draft_number','line_number','draft_date','customer_code','location_code','product_sku','qty_pcs','unit_price'] loop
    if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk draf penjualan terbuka',k;end if;
  end loop;
  if length(btrim(j->>'draft_number'))>60 or length(btrim(j->>'line_number'))>60 then raise exception 'draft_number: maksimal 60 karakter';end if;
  select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch;
  v_date:=erp.bb_parse_date_v1(j->>'draft_date','draft_date');
  if v_date>v_cutover then raise exception 'draft_date: draf harus dibuat sebelum saldo awal';end if;
  if nullif(btrim(j->>'due_date'),'') is not null then v_due:=erp.bb_parse_date_v1(j->>'due_date','due_date');end if;
  if j->>'qty_pcs' !~ '^[1-9][0-9]{0,8}$' then raise exception 'qty_pcs: jumlah pcs bilangan bulat positif';end if;
  v_qty:=(j->>'qty_pcs')::integer;
  v_price:=erp.bb_parse_amount_v1(j->>'unit_price','unit_price',true);
  v_discount:=case when nullif(btrim(j->>'discount_amount'),'') is null then 0 else erp.bb_parse_amount_v1(j->>'discount_amount','discount_amount',true) end;
  if v_discount>v_qty*v_price then raise exception 'discount_amount: potongan melebihi nilai baris';end if;
  if not exists(select 1 from erp.customers where customer_code=j->>'customer_code' and is_active)
    and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='CUSTOMER' and validation_status='VALID'
      and normalized_payload->>'customer_code'=j->>'customer_code') then
    raise exception 'customer_code: pelanggan aktif tidak ditemukan';
  end if;
  if not exists(select 1 from erp.locations where location_code=j->>'location_code' and is_active and location_type='FG_WAREHOUSE')
    and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='LOCATION' and validation_status='VALID'
      and normalized_payload->>'location_code'=j->>'location_code' and normalized_payload->>'location_type'='FG_WAREHOUSE') then
    raise exception 'location_code: gudang barang jadi aktif tidak ditemukan';
  end if;
  if not exists(select 1 from erp.products p where lower(btrim(p.sku))=lower(btrim(j->>'product_sku')))
    and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='PRODUCT'
      and s.validation_status='VALID' and lower(btrim(s.normalized_payload->>'sku'))=lower(btrim(j->>'product_sku'))) then
    raise exception 'product_sku: produk tidak ditemukan';
  end if;
  -- One draft: the same customer, warehouse, dates and terms on every line, and each line number once.
  if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type='OPEN_SALES_DRAFT' and x.id<>r.id
      and lower(btrim(x.normalized_payload->>'draft_number'))=lower(btrim(j->>'draft_number'))
      and (lower(btrim(x.normalized_payload->>'line_number'))=lower(btrim(j->>'line_number'))
        or x.normalized_payload->>'customer_code'<>j->>'customer_code' or x.normalized_payload->>'location_code'<>j->>'location_code'
        or x.normalized_payload->>'draft_date'<>j->>'draft_date' or coalesce(x.normalized_payload->>'due_date','')<>coalesce(j->>'due_date','')
        or coalesce(x.normalized_payload->>'payment_terms','')<>coalesce(j->>'payment_terms',''))) then
    raise exception 'BB_S02_DUPLICATE_DRAFT: baris draf ganda atau kepala draf tidak konsisten';
  end if;
  if exists(select 1 from erp.sales_headers where lower(btrim(sale_number))=lower(btrim(j->>'draft_number')))
    or exists(select 1 from erp.bb_open_sales_drafts_v1 where lower(btrim(draft_number))=lower(btrim(j->>'draft_number'))) then
    raise exception 'BB_S02_DUPLICATE_DRAFT: nomor draf sudah dipakai penjualan lain';
  end if;
  return jsonb_build_object('cutover_date',v_cutover,'draft_date',v_date,'due_date',v_due,'qty_pcs',v_qty,'unit_price',v_price,'discount_amount',v_discount);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_validate_sales_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;
begin
  perform erp.require_owner_admin();
  for r in select id from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPEN_SALES_DRAFT' order by source_row_no loop
    begin
      perform erp.bb_check_sales_import_row_v1(p_batch,r.id);
      update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
    exception when others then
      update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;
    end;
  end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_apply_sales_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare d record;r record;j jsonb;c jsonb;b erp.migration_batches%rowtype;v_customer uuid;v_location uuid;v_items jsonb;v_sale jsonb;
  v_sale_id uuid;v_product uuid;v_lines jsonb;l jsonb;
begin
  perform erp.require_owner_admin();
  select * into b from erp.migration_batches where id=p_batch;
  for d in select lower(btrim(normalized_payload->>'draft_number')) k,min(btrim(normalized_payload->>'draft_number')) draft_number
      from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPEN_SALES_DRAFT' and posted_entity_id is null
      group by 1 order by 1 loop
    perform pg_advisory_xact_lock(hashtextextended('BB_S02_DRAFT:'||d.k,0));
    v_items:='[]'::jsonb;v_lines:='[]'::jsonb;j:=null;
    for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPEN_SALES_DRAFT' and posted_entity_id is null
        and lower(btrim(normalized_payload->>'draft_number'))=d.k order by lower(btrim(normalized_payload->>'line_number')),source_row_no loop
      if r.validation_status<>'VALID' then raise exception 'Draf penjualan belum lolos pemeriksaan';end if;
      j:=r.normalized_payload;c:=erp.bb_check_sales_import_row_v1(p_batch,r.id);
      select id into strict v_product from erp.products where lower(btrim(sku))=lower(btrim(j->>'product_sku'));
      v_items:=v_items||jsonb_build_array(jsonb_build_object('product_id',v_product,'qty_pcs',(c->>'qty_pcs')::integer,
        'unit_price_snapshot',(c->>'unit_price')::numeric,'discount_amount',(c->>'discount_amount')::numeric,
        'notes','Baris '||btrim(j->>'line_number')||' draf lama '||d.draft_number));
      v_lines:=v_lines||jsonb_build_array(c||jsonb_build_object('row_id',r.id,'line_number',btrim(j->>'line_number'),'product_id',v_product));
    end loop;
    select id into strict v_customer from erp.customers where customer_code=j->>'customer_code' and is_active;
    select id into strict v_location from erp.locations where location_code=j->>'location_code' and is_active and location_type='FG_WAREHOUSE';
    -- The native draft and its one reservation. A reservation beyond the free finished goods of the warehouse (the lines of
    -- this draft and every draft before it) is refused by the native check and rolls the whole import back.
    begin
      v_sale:=erp.save_sale_draft_v2(jsonb_build_object('sale_number',d.draft_number,'customer_id',v_customer,'source_location_id',v_location,
        'sale_date',b.cutover_at,'due_date',c->>'due_date','payment_terms',nullif(btrim(j->>'payment_terms'),''),
        'notes','Draf penjualan terbuka saat saldo awal (draf lama '||d.draft_number||' tanggal '||(c->>'draft_date')
          ||'); ubah tanggal invoice ke tanggal nyata sebelum posting',
        'reason','Impor saldo awal: draf penjualan terbuka dengan reservasi resmi','items',v_items),
        md5('BB_S02:'||p_batch::text||':'||d.k)::uuid,null);
    exception when others then
      raise exception 'BB_S02_RESERVATION_REFUSED: draf %: %',d.draft_number,sqlerrm;
    end;
    v_sale_id:=(v_sale->>'sale_id')::uuid;
    insert into erp.bb_open_sales_drafts_v1(sale_id,batch_id,draft_number,draft_date,customer_id,cutover_at)
    values(v_sale_id,p_batch,d.draft_number,(c->>'draft_date')::date,v_customer,b.cutover_at);
    -- The lines as checked before the draft existed (a second check would see the draft's own number as taken).
    for l in select * from jsonb_array_elements(v_lines) loop
      insert into erp.bb_open_sales_draft_lines_v1(source_row_id,sale_id,line_number,product_id,qty_pcs,unit_price,discount_amount)
      values((l->>'row_id')::uuid,v_sale_id,l->>'line_number',(l->>'product_id')::uuid,(l->>'qty_pcs')::integer,(l->>'unit_price')::numeric,
        (l->>'discount_amount')::numeric);
      update erp.migration_staging_rows set posted_entity_id=v_sale_id,posted_entity_type='OPEN_SALES_DRAFT',posted_at=statement_timestamp(),
        updated_at=statement_timestamp() where id=(l->>'row_id')::uuid;
    end loop;
  end loop;
end;$function$;

-- Workspace (read only; the drafts continue on the sales page): status, sale date and the pieces the draft holds now.
CREATE OR REPLACE FUNCTION erp.bb_sales_workspace_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('open_sales_drafts',coalesce((select jsonb_agg(jsonb_build_object('sale_id',d.sale_id,'draft_number',d.draft_number,
      'draft_date',d.draft_date,'customer_code',cu.customer_code,'customer_name',cu.customer_name,'status',h.status,
      'sale_date',erp._cp3_business_date(h.sale_date),
      'reserved_qty_pcs',coalesce((select -sum(m.qty_signed) from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
          where i.sale_id=h.id and m.movement_type='SALE_RESERVE' and m.source_type='SALE_ITEM'
            and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)),0)::integer,
      'lines',coalesce((select jsonb_agg(jsonb_build_object('line_number',l.line_number,'product_sku',p.sku,'qty_pcs',l.qty_pcs,
          'unit_price',l.unit_price::text) order by l.line_number) from erp.bb_open_sales_draft_lines_v1 l join erp.products p on p.id=l.product_id
          where l.sale_id=d.sale_id),'[]'::jsonb))
      order by d.draft_number)
    from erp.bb_open_sales_drafts_v1 d join erp.sales_headers h on h.id=d.sale_id join erp.customers cu on cu.id=d.customer_id
    where d.batch_id=p_batch),'[]'::jsonb))
$function$;

do $grants$
declare f text;
begin
  foreach f in array array['erp.bb_guard_open_sales_draft_v1()','erp.bb_check_sales_import_row_v1(uuid,uuid)',
    'erp.bb_validate_sales_imports_v1(uuid)','erp.bb_apply_sales_imports_v1(uuid)','erp.bb_sales_workspace_v1(uuid)'] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
  end loop;
end $grants$;
