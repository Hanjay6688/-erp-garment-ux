-- ================================================================ BD import: ALL-W05 physical (laundry away at cutover)
-- Auditor oracle ALL-W05 (r9): vendor custody 10 PCS, 2 already returned before cutover, 1 documented missing/claim PCS. Import
-- only the pieces physically unreturned at the vendor (the 2 returned are not opening WIP); a claimed piece is held apart from
-- the WIP that can still come back (residual custody 7, claim 1); import alone posts no laundry, payment or claim journal and
-- does not infer a receipt, damage, vendor charge or billable claim from "away". Later actual return/QC adjusts only the
-- returned quantity; an approved claim posts once. Unknown value stays pending and blocks financial finalization (close).
--
-- The pieces at the vendor stay the BB opening WIP row (OPENING_BALANCE_ITEM WIP, stage LAUNDRY, vendor_code). New files:
--   OPENING_LAUNDRY_CLAIM       a documented claim (MISSING, STUCK, DAMAGE) on pieces of such a row (source_key = its
--                               opening_source_key, same vendor; claims of a row never more than its pieces; claim_date on or
--                               before cutover). The claimed pieces are held: they cannot be completed as goods (WIP_OUTPUT
--                               COMPLETE/SPLIT_BS take only the unheld remaining) until recovered.
--   OPENING_LAUNDRY_UNINVOICED  laundry work returned before cutover and not yet billed by the vendor (receipt document,
--                               category GOOD, BS or FAILED_ATTEMPT, quantity, optional evidenced estimate). With an estimate
--                               the opening accrual is Dr OPENING_EQUITY / Cr ACCRUED_MANUFACTURING at cutover (as the supplier
--                               GRNI opening); without one nothing is journaled and close stays blocked until the owner sets
--                               the estimate or the invoice bills it. The later vendor invoice bills it through the BD invoice
--                               facade (an invoice line with opening_uninvoiced_id), releasing the accrual; a difference needs
--                               the owner's LAU-DEC06 variance account (the goods are opening stock, not a PO's product cost).
-- Continuations of a claim (WIP_OUTPUT on the import page, same locks and remaining check as a completion):
--   OPEN_CLAIM          a claim after cutover on unheld pieces (dated; never more than the pieces left on that day and after)
--   RECOVER_CLAIM       claimed pieces came back: they return to the remaining WIP (then COMPLETE/SPLIT_BS as usual)
--   RESOLVE_CLAIM       SETTLED or WRITTEN_OFF the rest: the pieces are finally lost (the PO can then finish; their opening
--                       value stays in WIP and the baseline residual close at PO finish expenses it, as a native lost piece).
--                       A SETTLED compensation posts once, AP_VENDOR Dr / OTHER_EXPENSE Cr, capped by the vendor's payable
--                       (the baseline laundry claim rule).
--   CANCEL_CLAIM        a claim opened after cutover by mistake, before any event (an imported claim is recovered instead)
--   REVERSE_CLAIM_EVENT a recovery (its pieces must still be unused) or a resolution (its journal is reversed)

create table erp.bd_opening_laundry_claims_v1(
  id uuid primary key default gen_random_uuid(),
  claim_number text not null check(length(btrim(claim_number)) between 1 and 60),
  opening_item_id uuid not null references erp.opening_balance_items(id),
  po_id uuid not null references erp.production_orders(id),
  vendor_id uuid not null references erp.laundry_vendors(id),
  claim_type text not null check(claim_type in('MISSING','STUCK','DAMAGE')),
  qty_claimed integer not null check(qty_claimed>0),
  claim_date date not null,
  origin text not null check(origin in('IMPORT','CONTINUATION')),
  batch_id uuid not null references erp.migration_batches(id),
  source_row_id uuid references erp.migration_staging_rows(id),
  dispatch_number text,
  notes text,
  row_version bigint not null default 1,
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  cancelled_at timestamptz,
  cancelled_by uuid,
  cancel_reason text,
  check((origin='IMPORT')=(source_row_id is not null)),
  check(cancelled_at is null or origin='CONTINUATION')
);
create unique index bd_opening_laundry_claims_v1_number on erp.bd_opening_laundry_claims_v1(lower(btrim(claim_number)));
create index bd_opening_laundry_claims_v1_item on erp.bd_opening_laundry_claims_v1(opening_item_id);

create table erp.bd_opening_laundry_claim_events_v1(
  id uuid primary key default gen_random_uuid(),
  claim_id uuid not null references erp.bd_opening_laundry_claims_v1(id),
  event_kind text not null check(event_kind in('RECOVER','RESOLVE')),
  qty integer not null check(qty>0),
  resolution text check(resolution in('SETTLED','WRITTEN_OFF')),
  compensation_amount numeric(18,2) not null default 0 check(compensation_amount>=0),
  event_date date not null,
  journal_id uuid,
  reason text not null check(length(btrim(reason))>0),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  reversed_at timestamptz,
  reversed_by uuid,
  reverse_reason text,
  reversal_journal_id uuid,
  check((event_kind='RESOLVE')=(resolution is not null)),
  check(event_kind='RESOLVE' or compensation_amount=0),
  check(resolution is distinct from 'WRITTEN_OFF' or compensation_amount=0)
);
create unique index bd_opening_laundry_claim_events_v1_resolve on erp.bd_opening_laundry_claim_events_v1(claim_id)
  where event_kind='RESOLVE' and reversed_at is null;
create index bd_opening_laundry_claim_events_v1_claim on erp.bd_opening_laundry_claim_events_v1(claim_id);

create table erp.bd_opening_laundry_uninvoiced_v1(
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references erp.migration_batches(id),
  source_row_id uuid not null references erp.migration_staging_rows(id),
  vendor_id uuid not null references erp.laundry_vendors(id),
  document_number text not null check(length(btrim(document_number)) between 1 and 80),
  receipt_date date not null,
  category text not null check(category in('GOOD','BS','FAILED_ATTEMPT')),
  qty integer not null check(qty>0),
  estimated_amount numeric(18,2) check(estimated_amount>0),
  accrued_amount numeric(18,2) not null default 0,
  po_id uuid references erp.production_orders(id),
  dispatch_number text,
  notes text,
  accrual_journal_id uuid,
  estimate_set_by uuid,
  estimate_set_at timestamptz,
  estimate_reason text,
  row_version bigint not null default 1,
  check((estimated_amount is null and accrued_amount=0 and accrual_journal_id is null)
    or (accrued_amount=estimated_amount and accrual_journal_id is not null))
);
create unique index bd_opening_laundry_uninvoiced_v1_document on erp.bd_opening_laundry_uninvoiced_v1(vendor_id,lower(btrim(document_number)),category);

-- ---------------------------------------------------------------- held pieces
-- Pieces a claim holds now: claimed less recovered (a resolved claim keeps its lost pieces held for good).
CREATE OR REPLACE FUNCTION erp.bd_opening_claim_recovered_v1(p_claim uuid)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(qty),0)::integer from erp.bd_opening_laundry_claim_events_v1 where claim_id=p_claim and event_kind='RECOVER' and reversed_at is null
$function$;

CREATE OR REPLACE FUNCTION erp.bd_opening_claim_held_qty_v1(p_item uuid)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(c.qty_claimed-erp.bd_opening_claim_recovered_v1(c.id)),0)::integer
  from erp.bd_opening_laundry_claims_v1 c where c.opening_item_id=p_item and c.cancelled_at is null
$function$;

-- Pieces finally lost by an active resolution (counted as done when the PO finishes).
CREATE OR REPLACE FUNCTION erp.bd_opening_claim_lost_qty_v1(p_item uuid)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(e.qty),0)::integer from erp.bd_opening_laundry_claim_events_v1 e join erp.bd_opening_laundry_claims_v1 c on c.id=e.claim_id
  where c.opening_item_id=p_item and e.event_kind='RESOLVE' and e.reversed_at is null
$function$;

-- Held on a day: claims dated on or before it (less those cancelled on or before it), less recoveries dated on or before it
-- (less those reversed on or before it). The dated remaining check of BA A3 subtracts it on every day.
CREATE OR REPLACE FUNCTION erp.bd_opening_claim_held_asof_v1(p_item uuid,p_day date)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select (coalesce((select sum(c.qty_claimed) filter(where c.claim_date<=p_day)
      -coalesce(sum(c.qty_claimed) filter(where c.cancelled_at is not null and erp._cp3_business_date(c.cancelled_at)<=p_day),0)
    from erp.bd_opening_laundry_claims_v1 c where c.opening_item_id=p_item),0)
    -coalesce((select sum(e.qty) filter(where e.event_date<=p_day)
      -coalesce(sum(e.qty) filter(where e.reversed_at is not null and erp._cp3_business_date(e.reversed_at)<=p_day),0)
    from erp.bd_opening_laundry_claim_events_v1 e join erp.bd_opening_laundry_claims_v1 c on c.id=e.claim_id
    where c.opening_item_id=p_item and e.event_kind='RECOVER'),0))::integer
$function$;

CREATE OR REPLACE FUNCTION erp.bd_opening_claim_days_v1(p_item uuid)
 RETURNS SETOF date LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select c.claim_date from erp.bd_opening_laundry_claims_v1 c where c.opening_item_id=p_item
  union select erp._cp3_business_date(c.cancelled_at) from erp.bd_opening_laundry_claims_v1 c where c.opening_item_id=p_item and c.cancelled_at is not null
  union select e.event_date from erp.bd_opening_laundry_claim_events_v1 e join erp.bd_opening_laundry_claims_v1 c on c.id=e.claim_id
    where c.opening_item_id=p_item and e.event_kind='RECOVER'
  union select erp._cp3_business_date(e.reversed_at) from erp.bd_opening_laundry_claim_events_v1 e join erp.bd_opening_laundry_claims_v1 c on c.id=e.claim_id
    where c.opening_item_id=p_item and e.event_kind='RECOVER' and e.reversed_at is not null
$function$;

-- The fewest pieces left in the source stage on a day and every later day (outputs, output reversals, BS splits and held claims,
-- the same terms as the BA A3 check of a completion).
CREATE OR REPLACE FUNCTION erp.bd_opening_wip_floor_v1(p_item uuid,p_from date)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select min(s.qty_pcs
      -coalesce((select sum(o.qty_pcs) from erp.initial_import_wip_outputs o where o.opening_item_id=p_item and erp._cp3_business_date(o.physical_at)<=d.day),0)
      +coalesce((select sum(o.qty_pcs) from erp.initial_import_wip_output_reversals rv join erp.initial_import_wip_outputs o on o.id=rv.output_id
          where o.opening_item_id=p_item and erp._cp3_business_date(rv.physical_at)<=d.day),0)
      -erp.bb_wip_split_net_asof_v1(p_item,d.day)-erp.bd_opening_claim_held_asof_v1(p_item,d.day))::integer
  from erp.initial_import_production_sources s,
    (select p_from as day
     union select erp._cp3_business_date(o.physical_at) from erp.initial_import_wip_outputs o where o.opening_item_id=p_item
     union select erp._cp3_business_date(rv.physical_at) from erp.initial_import_wip_output_reversals rv
       join erp.initial_import_wip_outputs o on o.id=rv.output_id where o.opening_item_id=p_item
     union select x.day from erp.bb_wip_split_days_v1(p_item) x(day)
     union select x.day from erp.bd_opening_claim_days_v1(p_item) x(day)) d
  where s.opening_item_id=p_item and d.day>=p_from
$function$;

-- The claims of one opening WIP row (production row part: the import page and the WIP status page, which a production viewer
-- reads; quantities and states only, no amounts).
CREATE OR REPLACE FUNCTION erp.bd_wip_row_part_v1(p_item uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('held_qty_pcs',erp.bd_opening_claim_held_qty_v1(p_item),'lost_qty_pcs',erp.bd_opening_claim_lost_qty_v1(p_item),
    'claims',coalesce((select jsonb_agg(jsonb_build_object('claim_id',c.id,'claim_number',c.claim_number,'claim_type',c.claim_type,'origin',c.origin,
        'qty_claimed',c.qty_claimed,'recovered',erp.bd_opening_claim_recovered_v1(c.id),
        'lost',coalesce((select e.qty from erp.bd_opening_laundry_claim_events_v1 e where e.claim_id=c.id and e.event_kind='RESOLVE' and e.reversed_at is null),0),
        'state',case when c.cancelled_at is not null then 'CANCELLED'
          when exists(select 1 from erp.bd_opening_laundry_claim_events_v1 e where e.claim_id=c.id and e.event_kind='RESOLVE' and e.reversed_at is null)
            then (select e.resolution from erp.bd_opening_laundry_claim_events_v1 e where e.claim_id=c.id and e.event_kind='RESOLVE' and e.reversed_at is null)
          when erp.bd_opening_claim_recovered_v1(c.id)=c.qty_claimed then 'RECOVERED' else 'OPEN' end,
        'claim_date',c.claim_date,'dispatch_number',c.dispatch_number,'vendor_code',v.vendor_code,'row_version',c.row_version::text,
        'events',coalesce((select jsonb_agg(jsonb_build_object('event_id',e.id,'kind',e.event_kind,'qty',e.qty,'date',e.event_date,'resolution',e.resolution,
            'reversed',e.reversed_at is not null) order by e.created_at,e.id)
          from erp.bd_opening_laundry_claim_events_v1 e where e.claim_id=c.id),'[]'::jsonb)) order by c.claim_date,c.claim_number)
      from erp.bd_opening_laundry_claims_v1 c join erp.laundry_vendors v on v.id=c.vendor_id where c.opening_item_id=p_item),'[]'::jsonb))
$function$;

-- ---------------------------------------------------------------- import rows
CREATE OR REPLACE FUNCTION erp.bd_check_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_src record;v_cutover date;v_date date;v_qty integer;v_total bigint;v_amount numeric;
  v_vendor boolean;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch
    and entity_type in('OPENING_LAUNDRY_CLAIM','OPENING_LAUNDRY_UNINVOICED');
  if r.id is null then raise exception 'Baris laundry saldo awal tidak ditemukan';end if;
  j:=r.normalized_payload;
  select erp._cp3_business_date(cutover_at) into strict v_cutover from erp.migration_batches where id=p_batch;
  if r.entity_type='OPENING_LAUNDRY_CLAIM' then
    foreach k in array array['claim_number','source_key','vendor_code','claim_type','qty','claim_date'] loop
      if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk klaim laundry saldo awal',k;end if;
    end loop;
    if length(btrim(j->>'claim_number'))>60 then raise exception 'claim_number: maksimal 60 karakter';end if;
    if upper(j->>'claim_type') not in('MISSING','STUCK','DAMAGE') then raise exception 'claim_type: MISSING, STUCK atau DAMAGE';end if;
    if j->>'qty'!~'^[1-9][0-9]{0,8}$' then raise exception 'qty: PCS utuh positif';end if;
    v_qty:=(j->>'qty')::integer;
    if j->>'claim_date'!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'claim_date: gunakan YYYY-MM-DD';end if;
    v_date:=(j->>'claim_date')::date;
    if v_date::text<>j->>'claim_date' or v_date>v_cutover then raise exception 'BD_W05_CLAIM_AFTER_CUTOVER: klaim yang diimpor adalah klaim sebelum atau pada tanggal saldo awal; klaim sesudahnya dicatat lewat lanjutan WIP';end if;
    -- The opening WIP row at the laundry vendor this claim holds pieces of (same batch, same vendor).
    select s.id,s.normalized_payload p into v_src from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
      and s.validation_status='VALID' and s.normalized_payload->>'opening_source_key'=j->>'source_key';
    if v_src.id is null or upper(v_src.p->>'balance_type')<>'WIP' or v_src.p->>'stage'<>'LAUNDRY' then
      raise exception 'BD_W05_SOURCE_REQUIRED: source_key harus menunjuk WIP saldo awal tahap LAUNDRY yang valid di impor ini';end if;
    if v_src.p->>'vendor_code' is distinct from j->>'vendor_code' then
      raise exception 'BD_W05_VENDOR_MISMATCH: vendor klaim berbeda dengan vendor pemegang WIP';end if;
    if exists(select 1 from erp.migration_staging_rows x where x.entity_type='OPENING_LAUNDRY_CLAIM' and x.id<>r.id
        and lower(btrim(x.normalized_payload->>'claim_number'))=lower(btrim(j->>'claim_number')) and (x.batch_id=p_batch or x.posted_entity_id is not null))
      or exists(select 1 from erp.bd_opening_laundry_claims_v1 c where lower(btrim(c.claim_number))=lower(btrim(j->>'claim_number')))
      or exists(select 1 from erp.laundry_claims c where lower(btrim(c.claim_number))=lower(btrim(j->>'claim_number'))) then
      raise exception 'BD_W05_DUPLICATE_CLAIM: nomor klaim sudah dipakai';end if;
    select sum((x.normalized_payload->>'qty')::bigint) into v_total from erp.migration_staging_rows x where x.batch_id=p_batch
      and x.entity_type='OPENING_LAUNDRY_CLAIM' and x.normalized_payload->>'source_key'=j->>'source_key' and x.normalized_payload->>'qty'~'^[1-9][0-9]{0,8}$';
    if v_total>(v_src.p->>'qty')::numeric then
      raise exception 'BD_W05_CLAIM_EXCEEDS_SOURCE: klaim % PCS melebihi % PCS WIP di vendor',v_total,v_src.p->>'qty';end if;
    return jsonb_build_object('qty',v_qty,'claim_date',v_date,'source_row_id',v_src.id);
  end if;
  -- OPENING_LAUNDRY_UNINVOICED
  foreach k in array array['document_number','vendor_code','receipt_date','category','qty'] loop
    if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk penerimaan laundry belum ditagih',k;end if;
  end loop;
  if length(btrim(j->>'document_number'))>80 then raise exception 'document_number: maksimal 80 karakter';end if;
  if upper(j->>'category') not in('GOOD','BS','FAILED_ATTEMPT') then raise exception 'category: GOOD, BS atau FAILED_ATTEMPT';end if;
  if j->>'qty'!~'^[1-9][0-9]{0,8}$' then raise exception 'qty: PCS utuh positif';end if;
  if j->>'receipt_date'!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'receipt_date: gunakan YYYY-MM-DD';end if;
  v_date:=(j->>'receipt_date')::date;
  if v_date::text<>j->>'receipt_date' or v_date>v_cutover then raise exception 'receipt_date: penerimaan belum ditagih terjadi sebelum atau pada tanggal saldo awal';end if;
  v_vendor:=exists(select 1 from erp.laundry_vendors where vendor_code=j->>'vendor_code' and is_active)
    or exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='LAUNDRY_VENDOR' and s.validation_status='VALID'
      and s.normalized_payload->>'vendor_code'=j->>'vendor_code');
  if not v_vendor then raise exception 'vendor_code: vendor laundry aktif tidak ditemukan';end if;
  if nullif(btrim(j->>'estimated_amount'),'') is not null then
    -- An evidenced estimate is positive; no estimate means unknown (never a zero journal).
    v_amount:=erp.bb_parse_amount_v1(j->>'estimated_amount','estimated_amount',false);
  end if;
  if nullif(btrim(j->>'po_number'),'') is not null and not exists(select 1 from erp.production_orders where po_number=j->>'po_number')
    and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPEN_PO' and s.validation_status='VALID'
      and s.normalized_payload->>'po_number'=j->>'po_number') then raise exception 'po_number: PO tidak ditemukan';end if;
  if exists(select 1 from erp.migration_staging_rows x where x.entity_type='OPENING_LAUNDRY_UNINVOICED' and x.id<>r.id
      and x.normalized_payload->>'vendor_code'=j->>'vendor_code' and lower(btrim(x.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))
      and upper(x.normalized_payload->>'category')=upper(j->>'category') and (x.batch_id=p_batch or x.posted_entity_id is not null)) then
    raise exception 'BD_W05_DUPLICATE_RECEIPT: dokumen penerimaan dan kategori ini sudah diimpor';end if;
  return jsonb_build_object('qty',(j->>'qty')::integer,'receipt_date',v_date,'estimated_amount',v_amount);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bd_validate_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;
begin
  perform erp.require_owner_admin();
  for r in select id from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_LAUNDRY_CLAIM','OPENING_LAUNDRY_UNINVOICED')
      order by entity_type,source_row_no loop
    begin
      perform erp.bd_check_import_row_v1(p_batch,r.id);
      update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
    exception when others then
      update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;
    end;
  end loop;
end;$function$;

-- After the opening stock (the WIP rows and their production sources) is posted.
CREATE OR REPLACE FUNCTION erp.bd_apply_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;j jsonb;c jsonb;b erp.migration_batches%rowtype;v_item uuid;s erp.initial_import_production_sources%rowtype;v_vendor uuid;v_id uuid;
  v_journal uuid;v_amount numeric;v_cutover date;
begin
  perform erp.require_owner_admin();
  select * into strict b from erp.migration_batches where id=p_batch;
  v_cutover:=erp._cp3_business_date(b.cutover_at);
  for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_LAUNDRY_CLAIM','OPENING_LAUNDRY_UNINVOICED')
      and posted_entity_id is null order by entity_type,source_row_no loop
    if r.validation_status<>'VALID' then raise exception 'Baris laundry saldo awal belum lolos pemeriksaan';end if;
    j:=r.normalized_payload;c:=erp.bd_check_import_row_v1(p_batch,r.id);v_id:=gen_random_uuid();
    select id into strict v_vendor from erp.laundry_vendors where vendor_code=j->>'vendor_code';
    if r.entity_type='OPENING_LAUNDRY_CLAIM' then
      select k.opening_item_id into v_item from erp.initial_import_opening_stock_sources k where k.batch_id=p_batch and k.source_row_id=(c->>'source_row_id')::uuid;
      select * into s from erp.initial_import_production_sources where opening_item_id=v_item;
      if s.opening_item_id is null or s.stage<>'LAUNDRY' then raise exception 'BD_W05_SOURCE_REQUIRED: WIP laundry % belum terbentuk',j->>'source_key';end if;
      insert into erp.bd_opening_laundry_claims_v1(id,claim_number,opening_item_id,po_id,vendor_id,claim_type,qty_claimed,claim_date,origin,batch_id,
        source_row_id,dispatch_number,notes,created_by)
      values(v_id,btrim(j->>'claim_number'),s.opening_item_id,s.po_id,v_vendor,upper(j->>'claim_type'),(c->>'qty')::integer,(c->>'claim_date')::date,
        'IMPORT',p_batch,r.id,nullif(btrim(j->>'dispatch_number'),''),nullif(btrim(j->>'notes'),''),erp.current_app_user_id());
      if erp.bd_opening_claim_held_qty_v1(s.opening_item_id)>s.qty_pcs then raise exception 'BD_W05_CLAIM_EXCEEDS_SOURCE: klaim melebihi WIP di vendor';end if;
    else
      v_amount:=(c->>'estimated_amount')::numeric;v_journal:=null;
      if v_amount is not null then
        v_journal:=erp.post_journal('BD_OPENING_LAUNDRY_ACCRUAL',v_id,v_cutover,'Saldo awal laundry belum ditagih '||btrim(j->>'document_number'),jsonb_build_array(
          jsonb_build_object('mapping_key','OPENING_EQUITY','debit',v_amount,'credit',0,'vendor_id',v_vendor),
          jsonb_build_object('mapping_key','ACCRUED_MANUFACTURING','debit',0,'credit',v_amount,'vendor_id',v_vendor)));
      end if;
      insert into erp.bd_opening_laundry_uninvoiced_v1(id,batch_id,source_row_id,vendor_id,document_number,receipt_date,category,qty,estimated_amount,
        accrued_amount,po_id,dispatch_number,notes,accrual_journal_id)
      values(v_id,p_batch,r.id,v_vendor,btrim(j->>'document_number'),(c->>'receipt_date')::date,upper(j->>'category'),(c->>'qty')::integer,v_amount,
        coalesce(v_amount,0),(select id from erp.production_orders where po_number=nullif(btrim(j->>'po_number'),'')),nullif(btrim(j->>'dispatch_number'),''),
        nullif(btrim(j->>'notes'),''),v_journal);
    end if;
    update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type=r.entity_type,posted_at=statement_timestamp(),
      updated_at=statement_timestamp() where id=r.id;
  end loop;
end;$function$;

-- ---------------------------------------------------------------- claim continuations (WIP_OUTPUT, source row locked by the caller)
CREATE OR REPLACE FUNCTION erp.bd_manage_opening_claim_v1(p_payload jsonb,p_item uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare v_op text:=p_payload->>'operation';s erp.initial_import_production_sources%rowtype;i erp.opening_balance_items%rowtype;
  c erp.bd_opening_laundry_claims_v1%rowtype;e erp.bd_opening_laundry_claim_events_v1%rowtype;v_reason text:=nullif(btrim(p_payload->>'reason'),'');
  v_qty integer;v_date date;v_cutover date;v_today date:=erp._cp3_business_date(statement_timestamp());v_floor integer;v_lost integer;
  v_comp numeric:=0;v_ap numeric;v_journal uuid;v_id uuid;v_resolution text;
begin
  perform erp.require_owner_admin();
  select * into strict s from erp.initial_import_production_sources where opening_item_id=p_item;
  select * into strict i from erp.opening_balance_items where id=p_item;
  select opening_date into strict v_cutover from erp.opening_balance_headers where id=i.opening_id;
  if s.stage<>'LAUNDRY' or i.vendor_id is null then
    raise exception 'BD_W05_NOT_LAUNDRY: klaim laundry hanya untuk WIP saldo awal yang berada di vendor laundry';end if;
  if v_op in('RECOVER_CLAIM','RESOLVE_CLAIM','CANCEL_CLAIM','REVERSE_CLAIM_EVENT') then
    if v_op='REVERSE_CLAIM_EVENT' then
      select * into e from erp.bd_opening_laundry_claim_events_v1 where id=erp.bd_uuid_v1(p_payload,'event_id',true);
      select * into c from erp.bd_opening_laundry_claims_v1 where id=e.claim_id and opening_item_id=p_item for update;
      select * into e from erp.bd_opening_laundry_claim_events_v1 where id=e.id for update;
    else
      select * into c from erp.bd_opening_laundry_claims_v1 where id=erp.bd_uuid_v1(p_payload,'claim_id',true) and opening_item_id=p_item for update;
    end if;
    if c.id is null then raise exception 'BD_W05_CLAIM_NOT_FOUND: klaim tidak ditemukan pada WIP ini';end if;
    if c.cancelled_at is not null then raise exception 'BD_W05_CLAIM_CANCELLED: klaim sudah dibatalkan';end if;
    if p_payload->>'expected_version' is distinct from c.row_version::text then raise exception 'STALE_VERSION: klaim berubah; muat ulang';end if;
  end if;
  if v_op in('OPEN_CLAIM','RECOVER_CLAIM','RESOLVE_CLAIM') then
    if coalesce(p_payload->>'date','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'date: gunakan YYYY-MM-DD';end if;
    v_date:=(p_payload->>'date')::date;
    if v_date::text<>p_payload->>'date' or v_date<v_cutover or v_date>v_today then raise exception 'date: tanggal harus sejak saldo awal dan tidak di masa depan';end if;
    if v_op<>'OPEN_CLAIM' and v_date<c.claim_date then raise exception 'date: tanggal tidak boleh sebelum tanggal klaim';end if;
  end if;
  if v_op='OPEN_CLAIM' then
    if nullif(btrim(p_payload->>'claim_number'),'') is null or length(btrim(p_payload->>'claim_number'))>60 then
      raise exception 'claim_number: wajib, maksimal 60 karakter';end if;
    if coalesce(p_payload->>'claim_type','') not in('MISSING','STUCK','DAMAGE') then raise exception 'claim_type: MISSING, STUCK atau DAMAGE';end if;
    if coalesce(p_payload->>'qty_pcs','')!~'^[1-9][0-9]{0,8}$' then raise exception 'qty_pcs: PCS utuh positif';end if;
    v_qty:=(p_payload->>'qty_pcs')::integer;
    if exists(select 1 from erp.bd_opening_laundry_claims_v1 x where lower(btrim(x.claim_number))=lower(btrim(p_payload->>'claim_number')))
      or exists(select 1 from erp.laundry_claims x where lower(btrim(x.claim_number))=lower(btrim(p_payload->>'claim_number'))) then
      raise exception 'BD_W05_DUPLICATE_CLAIM: nomor klaim sudah dipakai';end if;
    v_floor:=erp.bd_opening_wip_floor_v1(p_item,v_date);
    if v_qty>v_floor then
      raise exception 'BD_W05_CLAIM_EXCEEDS_REMAINING: pada % atau sesudahnya hanya % pcs tersisa di vendor; potongan yang sudah selesai, dipisah BS, atau diklaim tidak dapat diklaim lagi',v_date,v_floor;end if;
    insert into erp.bd_opening_laundry_claims_v1(claim_number,opening_item_id,po_id,vendor_id,claim_type,qty_claimed,claim_date,origin,batch_id,notes,created_by)
    values(btrim(p_payload->>'claim_number'),p_item,s.po_id,i.vendor_id,p_payload->>'claim_type',v_qty,v_date,'CONTINUATION',s.batch_id,v_reason,
      erp.current_app_user_id()) returning * into c;
    return jsonb_build_object('claim_id',c.id,'operation',v_op);
  elsif v_op='RECOVER_CLAIM' then
    if coalesce(p_payload->>'qty_pcs','')!~'^[1-9][0-9]{0,8}$' then raise exception 'qty_pcs: PCS utuh positif';end if;
    v_qty:=(p_payload->>'qty_pcs')::integer;
    if exists(select 1 from erp.bd_opening_laundry_claim_events_v1 x where x.claim_id=c.id and x.event_kind='RESOLVE' and x.reversed_at is null) then
      raise exception 'BD_W05_CLAIM_RESOLVED: klaim sudah diselesaikan; batalkan penyelesaiannya dulu';end if;
    if v_qty>c.qty_claimed-erp.bd_opening_claim_recovered_v1(c.id) then
      raise exception 'BD_W05_RECOVER_EXCEEDS_CLAIM: yang kembali melebihi sisa klaim %',c.qty_claimed-erp.bd_opening_claim_recovered_v1(c.id);end if;
    insert into erp.bd_opening_laundry_claim_events_v1(claim_id,event_kind,qty,event_date,reason,created_by)
    values(c.id,'RECOVER',v_qty,v_date,v_reason,erp.current_app_user_id()) returning * into e;
  elsif v_op='RESOLVE_CLAIM' then
    v_resolution:=p_payload->>'resolution';
    if v_resolution is null or v_resolution not in('SETTLED','WRITTEN_OFF') then raise exception 'resolution: SETTLED atau WRITTEN_OFF';end if;
    if nullif(p_payload->>'compensation_amount','') is not null then v_comp:=erp.bb_parse_amount_v1(p_payload->>'compensation_amount','compensation_amount',true);end if;
    if v_resolution='WRITTEN_OFF' and v_comp>0 then raise exception 'BD_W05_WRITE_OFF_COMPENSATION: WRITTEN_OFF tanpa kompensasi; gunakan SETTLED';end if;
    if exists(select 1 from erp.bd_opening_laundry_claim_events_v1 x where x.claim_id=c.id and x.event_kind='RESOLVE' and x.reversed_at is null) then
      raise exception 'BD_W05_CLAIM_RESOLVED: klaim sudah diselesaikan';end if;
    if v_date<(select max(x.event_date) from erp.bd_opening_laundry_claim_events_v1 x where x.claim_id=c.id and x.reversed_at is null) then
      raise exception 'date: penyelesaian tidak boleh sebelum pemulihan terakhir klaim ini';end if;
    v_lost:=c.qty_claimed-erp.bd_opening_claim_recovered_v1(c.id);
    if v_lost<=0 then raise exception 'BD_W05_NOTHING_LOST: semua potongan klaim sudah kembali';end if;
    v_id:=gen_random_uuid();
    if v_comp>0 then
      -- Baseline laundry claim rule: the compensation offsets the vendor's payable, never more than it.
      select coalesce(sum(jl.credit-jl.debit),0) into v_ap from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
      where je.status in('POSTED','REVERSED') and jl.vendor_id=c.vendor_id and jl.account_id=erp.account_id('AP_VENDOR');
      if v_ap<v_comp then
        raise exception 'BD_W05_COMPENSATION_EXCEEDS_PAYABLE: kompensasi % melebihi hutang vendor laundry %; penagihan tunai perlu alur piutang terpisah',v_comp,round(v_ap,2);end if;
      v_journal:=erp.post_journal('BD_OPENING_LAUNDRY_CLAIM',v_id,v_date,'Kompensasi klaim laundry '||c.claim_number,jsonb_build_array(
        jsonb_build_object('mapping_key','AP_VENDOR','debit',v_comp,'credit',0,'vendor_id',c.vendor_id),
        jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',0,'credit',v_comp,'vendor_id',c.vendor_id)));
    end if;
    insert into erp.bd_opening_laundry_claim_events_v1(id,claim_id,event_kind,qty,resolution,compensation_amount,event_date,journal_id,reason,created_by)
    values(v_id,c.id,'RESOLVE',v_lost,v_resolution,v_comp,v_date,v_journal,v_reason,erp.current_app_user_id()) returning * into e;
  elsif v_op='CANCEL_CLAIM' then
    if c.origin<>'CONTINUATION' then raise exception 'BD_W05_IMPORTED_CLAIM: klaim dari impor tidak dibatalkan; catat potongan yang kembali (RECOVER_CLAIM)';end if;
    if exists(select 1 from erp.bd_opening_laundry_claim_events_v1 x where x.claim_id=c.id and x.reversed_at is null) then
      raise exception 'BD_W05_CLAIM_HAS_EVENTS: batalkan pemulihan/penyelesaian klaim dulu';end if;
    update erp.bd_opening_laundry_claims_v1 set cancelled_at=statement_timestamp(),cancelled_by=erp.current_app_user_id(),cancel_reason=v_reason,
      row_version=row_version+1 where id=c.id;
    return jsonb_build_object('claim_id',c.id,'operation',v_op);
  elsif v_op='REVERSE_CLAIM_EVENT' then
    if e.id is null or e.reversed_at is not null then raise exception 'BD_W05_EVENT_NOT_ACTIVE: kejadian klaim tidak ditemukan atau sudah dibatalkan';end if;
    if e.event_kind='RECOVER' then
      if exists(select 1 from erp.bd_opening_laundry_claim_events_v1 x where x.claim_id=c.id and x.event_kind='RESOLVE' and x.reversed_at is null) then
        raise exception 'BD_W05_CLAIM_RESOLVED: batalkan penyelesaian klaim dulu';end if;
      v_floor:=erp.bd_opening_wip_floor_v1(p_item,v_today);
      if e.qty>v_floor then
        raise exception 'BD_W05_RECOVERED_IN_USE: potongan yang kembali sudah dipakai (selesai atau dipisah BS); batalkan hasilnya dulu';end if;
    elsif e.journal_id is not null then
      v_journal:=erp.reverse_journal(e.journal_id,'Batal penyelesaian klaim laundry: '||v_reason);
    end if;
    update erp.bd_opening_laundry_claim_events_v1 set reversed_at=statement_timestamp(),reversed_by=erp.current_app_user_id(),reverse_reason=v_reason,
      reversal_journal_id=v_journal where id=e.id;
  else
    raise exception 'Aksi klaim laundry tidak dikenal';
  end if;
  update erp.bd_opening_laundry_claims_v1 set row_version=row_version+1 where id=c.id;
  return jsonb_build_object('claim_id',c.id,'event_id',e.id,'operation',v_op);
end;$function$;

-- ---------------------------------------------------------------- opening uninvoiced: the owner's estimate (BD facade)
-- While a record has no estimate its value is unknown: close stays blocked (BD_OPENING_LAUNDRY_PRICE_UNKNOWN) until the owner
-- sets an evidenced estimate (an opening correction, Dr OPENING_EQUITY / Cr ACCRUED_MANUFACTURING on the day it is set) or an
-- invoice bills it completely.
CREATE OR REPLACE FUNCTION erp.bd_set_opening_estimate_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare u erp.bd_opening_laundry_uninvoiced_v1%rowtype;v_amount numeric;v_reason text:=nullif(btrim(p_payload->>'reason'),'');v_journal uuid;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['opening_uninvoiced_id','expected_version','estimated_amount','reason'],
    array['opening_uninvoiced_id','expected_version','estimated_amount','reason'],'opening estimate');
  if v_reason is null then raise exception 'BD_REASON_REQUIRED: alasan wajib diisi';end if;
  select * into u from erp.bd_opening_laundry_uninvoiced_v1 where id=erp.bd_uuid_v1(p_payload,'opening_uninvoiced_id',true) for update;
  if u.id is null then raise exception 'BD_W05_UNINVOICED_NOT_FOUND: penerimaan laundry belum ditagih tidak ditemukan';end if;
  if p_payload->>'expected_version' is distinct from u.row_version::text then raise exception 'STALE_VERSION: data berubah; muat ulang';end if;
  if u.estimated_amount is not null then raise exception 'BD_W05_ESTIMATE_KNOWN: estimasi sudah ada';end if;
  if exists(select 1 from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id
      where l.opening_uninvoiced_id=u.id and i.status='POSTED') then
    raise exception 'BD_W05_ALREADY_BILLED: sumber ini sudah ditagih invoice; selisihnya ada di invoice';end if;
  v_amount:=erp.bd_amount_v1(p_payload->'estimated_amount','estimated_amount',true);
  v_journal:=erp.post_journal('BD_OPENING_LAUNDRY_ACCRUAL',u.id,erp._cp3_business_date(statement_timestamp()),
    'Estimasi saldo awal laundry belum ditagih '||u.document_number,jsonb_build_array(
      jsonb_build_object('mapping_key','OPENING_EQUITY','debit',v_amount,'credit',0,'vendor_id',u.vendor_id),
      jsonb_build_object('mapping_key','ACCRUED_MANUFACTURING','debit',0,'credit',v_amount,'vendor_id',u.vendor_id)));
  update erp.bd_opening_laundry_uninvoiced_v1 set estimated_amount=v_amount,accrued_amount=v_amount,accrual_journal_id=v_journal,
    estimate_set_by=erp.current_app_user_id(),estimate_set_at=statement_timestamp(),estimate_reason=v_reason,row_version=row_version+1 where id=u.id;
  return jsonb_build_object('opening_uninvoiced_id',u.id,'estimated_amount',v_amount::text,'journal_id',v_journal);
end;$function$;

-- ---------------------------------------------------------------- import workspace and revision parts (read only)
-- plpgsql: they read the invoice helpers of scripts/cp6_bd_objects_invoice.sql, installed after this file.
CREATE OR REPLACE FUNCTION erp.bd_import_workspace_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  return jsonb_build_object(
    'laundry_claims',coalesce((select jsonb_agg(jsonb_build_object('opening_item_id',c.opening_item_id,'source_key',k.source_key,'po_number',p.po_number,
        'claim_id',c.id,'claim_number',c.claim_number,'claim_type',c.claim_type,'origin',c.origin,'vendor_code',v.vendor_code,'qty_claimed',c.qty_claimed,
        'recovered',erp.bd_opening_claim_recovered_v1(c.id),'claim_date',c.claim_date,'dispatch_number',c.dispatch_number,
        'cancelled',c.cancelled_at is not null,'row_version',c.row_version::text,
        'compensation_amount',(select e.compensation_amount::text from erp.bd_opening_laundry_claim_events_v1 e where e.claim_id=c.id
          and e.event_kind='RESOLVE' and e.reversed_at is null)) order by p.po_number,c.claim_date,c.claim_number)
      from erp.bd_opening_laundry_claims_v1 c join erp.laundry_vendors v on v.id=c.vendor_id join erp.production_orders p on p.id=c.po_id
      join erp.initial_import_opening_stock_sources k on k.opening_item_id=c.opening_item_id where c.batch_id=p_batch),'[]'::jsonb),
    'laundry_uninvoiced',coalesce((select jsonb_agg(jsonb_build_object('id',u.id,'vendor_code',v.vendor_code,'document_number',u.document_number,
        'receipt_date',u.receipt_date,'category',u.category,'qty',u.qty,'billed',erp.bd_opening_billed_v1(u.id),
        'estimate_status',case when u.estimated_amount is null then 'UNKNOWN' else 'KNOWN' end,'estimated_amount',u.estimated_amount::text,
        'released',erp.bd_opening_released_v1(u.id)::text,'invoiced',erp.bd_opening_invoiced_v1(u.id),
        'po_number',(select po_number from erp.production_orders where id=u.po_id),'dispatch_number',u.dispatch_number,'row_version',u.row_version::text)
        order by u.receipt_date,u.document_number,u.category)
      from erp.bd_opening_laundry_uninvoiced_v1 u join erp.laundry_vendors v on v.id=u.vendor_id where u.batch_id=p_batch),'[]'::jsonb));
end;$function$;

CREATE OR REPLACE FUNCTION erp.bd_import_revision_part_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  return jsonb_build_object(
    'claims',(select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'v',c.row_version) order by c.id),'[]'::jsonb)
      from erp.bd_opening_laundry_claims_v1 c where c.batch_id=p_batch),
    'uninvoiced',(select coalesce(jsonb_agg(jsonb_build_object('id',u.id,'v',u.row_version,'billed',erp.bd_opening_billed_v1(u.id)) order by u.id),'[]'::jsonb)
      from erp.bd_opening_laundry_uninvoiced_v1 u where u.batch_id=p_batch));
end;$function$;
