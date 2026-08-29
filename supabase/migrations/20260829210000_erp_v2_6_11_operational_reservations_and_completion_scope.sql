-- ERP Garment v2.6.11
-- Operational truth for partial FG, Laundry outstanding, and all-day sales drafts.
--
-- Business contract:
--   * PARTIAL_SELECTION means the operator intentionally posts only part of the
--     physical quantity that is already eligible for QC/FG.
--   * WAITING_LAUNDRY means physical pieces are still outside at Laundry; it is
--     never presented as a partial FG choice.
--   * a DRAFT sale immediately reduces sellable FG through SALE_RESERVE.
--   * editing/cancelling a DRAFT releases the old reservation first.
--   * posting a sale converts SALE_RESERVE to SALE without a second qty movement.

alter table erp.qc_inspections
  add column if not exists completion_mode varchar(30);

alter table erp.qc_inspections
  drop constraint if exists qc_inspections_completion_mode_check;
alter table erp.qc_inspections
  add constraint qc_inspections_completion_mode_check
  check (completion_mode is null or completion_mode in ('ALL_READY','PARTIAL_SELECTION'));

comment on column erp.qc_inspections.completion_mode is
  'Operator intent for an FG completion. PARTIAL_SELECTION is only valid when already-returned eligible pieces are deliberately left for a later completion.';

create or replace view erp.v_fg_partial_completion_progress
with (security_invoker = true)
as
with qc as (
  select
    i.cutting_group_id,
    coalesce(sum(i.qty_good_pcs), 0)::bigint as qc_good_qty_pcs,
    coalesce(sum(i.qty_bs_pcs), 0)::bigint as qc_bs_qty_pcs,
    coalesce(sum(i.qty_good_pcs + i.qty_bs_pcs), 0)::bigint as qc_accounted_qty_pcs,
    coalesce(sum(i.qty_good_pcs + i.qty_bs_pcs)
      filter (where i.source_laundry_receipt_line_id is not null), 0)::bigint as laundry_qc_accounted_qty_pcs,
    coalesce(sum(i.qty_good_pcs + i.qty_bs_pcs)
      filter (where i.source_laundry_receipt_line_id is null), 0)::bigint as direct_qc_accounted_qty_pcs,
    count(distinct q.id)::bigint as completion_count,
    max(q.physical_at) as last_completion_at
  from erp.qc_inspection_items i
  join erp.qc_inspections q on q.id = i.inspection_id
  where q.status = 'POSTED'
  group by i.cutting_group_id
), latest_completion as (
  select distinct on (i.cutting_group_id)
    i.cutting_group_id,
    q.completion_mode
  from erp.qc_inspection_items i
  join erp.qc_inspections q on q.id = i.inspection_id
  where q.status = 'POSTED'
    and q.completion_mode is not null
  order by i.cutting_group_id, q.physical_at desc, q.id desc
), laundry as (
  select
    l.cutting_group_id,
    coalesce(sum(l.qty_sent_pcs), 0)::bigint as laundry_sent_qty_pcs
  from erp.laundry_delivery_lines l
  join erp.laundry_deliveries d on d.id = l.delivery_id
  where d.status not in ('DRAFT', 'REVERSED')
  group by l.cutting_group_id
), laundry_returned as (
  select
    dl.cutting_group_id,
    coalesce(sum(rl.qty_good_received), 0)::bigint as laundry_good_returned_qty_pcs,
    coalesce(sum(rl.qty_bs_laundry), 0)::bigint as laundry_bs_returned_qty_pcs,
    coalesce(sum(rl.qty_good_received + rl.qty_bs_laundry), 0)::bigint as laundry_returned_qty_pcs
  from erp.laundry_receipt_lines rl
  join erp.laundry_receipts r on r.id = rl.receipt_id
  join erp.laundry_delivery_lines dl on dl.id = rl.delivery_line_id
  join erp.laundry_deliveries d on d.id = dl.delivery_id
  where r.status = 'POSTED'
    and d.status <> 'REVERSED'
  group by dl.cutting_group_id
), resolved_claim as (
  select
    dl.cutting_group_id,
    coalesce(sum(c.qty_claimed), 0)::bigint as resolved_claim_qty_pcs
  from erp.laundry_claims c
  join erp.laundry_receipt_lines rl on rl.id = c.receipt_line_id
  join erp.laundry_delivery_lines dl on dl.id = rl.delivery_line_id
  where c.claim_type in ('MISSING','STUCK')
    and c.status in ('SETTLED','WRITTEN_OFF')
  group by dl.cutting_group_id
), progress as (
  select
    g.id as cutting_group_id,
    g.po_id,
    g.group_number,
    g.row_version,
    po.status as po_status,
    coalesce(t.total_pcs, 0)::bigint as effective_qty_pcs,
    coalesce(q.qc_good_qty_pcs, 0)::bigint as qc_good_qty_pcs,
    coalesce(q.qc_bs_qty_pcs, 0)::bigint as qc_bs_qty_pcs,
    coalesce(q.qc_accounted_qty_pcs, 0)::bigint as qc_accounted_qty_pcs,
    greatest(coalesce(t.total_pcs, 0) - coalesce(q.qc_accounted_qty_pcs, 0), 0)::bigint as remaining_qc_qty_pcs,
    coalesce(q.direct_qc_accounted_qty_pcs, 0)::bigint as direct_qc_accounted_qty_pcs,
    coalesce(q.laundry_qc_accounted_qty_pcs, 0)::bigint as laundry_qc_accounted_qty_pcs,
    coalesce(l.laundry_sent_qty_pcs, 0)::bigint as laundry_sent_qty_pcs,
    coalesce(lr.laundry_good_returned_qty_pcs, 0)::bigint as laundry_good_returned_qty_pcs,
    coalesce(lr.laundry_bs_returned_qty_pcs, 0)::bigint as laundry_bs_returned_qty_pcs,
    coalesce(lr.laundry_returned_qty_pcs, 0)::bigint as laundry_returned_qty_pcs,
    coalesce(rc.resolved_claim_qty_pcs, 0)::bigint as resolved_claim_qty_pcs,
    greatest(
      coalesce(lr.laundry_returned_qty_pcs, 0)
        - coalesce(q.laundry_qc_accounted_qty_pcs, 0),
      0
    )::bigint as ready_for_qc_qty_pcs,
    greatest(
      coalesce(l.laundry_sent_qty_pcs, 0)
        - coalesce(lr.laundry_returned_qty_pcs, 0)
        - coalesce(rc.resolved_claim_qty_pcs, 0),
      0
    )::bigint as laundry_outstanding_qty_pcs,
    (coalesce(q.direct_qc_accounted_qty_pcs, 0) + coalesce(l.laundry_sent_qty_pcs, 0))::bigint as source_accounted_qty_pcs,
    greatest(
      coalesce(t.total_pcs, 0)
        - coalesce(q.direct_qc_accounted_qty_pcs, 0)
        - coalesce(l.laundry_sent_qty_pcs, 0),
      0
    )::bigint as remaining_source_qty_pcs,
    coalesce(q.completion_count, 0)::bigint as completion_count,
    q.last_completion_at,
    lc.completion_mode as last_completion_mode
  from erp.cutting_groups g
  join erp.production_orders po on po.id = g.po_id
  left join erp.v_cutting_group_totals t on t.cutting_group_id = g.id
  left join qc q on q.cutting_group_id = g.id
  left join latest_completion lc on lc.cutting_group_id = g.id
  left join laundry l on l.cutting_group_id = g.id
  left join laundry_returned lr on lr.cutting_group_id = g.id
  left join resolved_claim rc on rc.cutting_group_id = g.id
)
select
  p.cutting_group_id,
  p.po_id,
  p.group_number,
  p.row_version,
  p.po_status,
  p.effective_qty_pcs,
  p.qc_good_qty_pcs,
  p.qc_bs_qty_pcs,
  p.qc_accounted_qty_pcs,
  p.remaining_qc_qty_pcs,
  p.direct_qc_accounted_qty_pcs,
  p.laundry_sent_qty_pcs,
  p.source_accounted_qty_pcs,
  p.remaining_source_qty_pcs,
  p.completion_count,
  p.last_completion_at,
  case
    when p.po_status = 'FINISHED' then 'FINISHED'
    when p.qc_accounted_qty_pcs = 0 then 'OPEN'
    when p.ready_for_qc_qty_pcs > 0 and p.last_completion_mode = 'PARTIAL_SELECTION' then 'PARTIAL_SELECTION'
    when p.ready_for_qc_qty_pcs > 0 then 'READY_FOR_QC'
    when p.laundry_outstanding_qty_pcs > 0 then 'WAITING_LAUNDRY'
    when p.remaining_qc_qty_pcs > 0 and p.last_completion_mode = 'PARTIAL_SELECTION' then 'PARTIAL_SELECTION'
    when p.remaining_qc_qty_pcs > 0 then 'OPEN_SOURCE'
    else 'QC_COMPLETE'
  end::text as completion_status,
  p.laundry_qc_accounted_qty_pcs,
  p.laundry_good_returned_qty_pcs,
  p.laundry_bs_returned_qty_pcs,
  p.laundry_returned_qty_pcs,
  p.resolved_claim_qty_pcs,
  p.ready_for_qc_qty_pcs,
  p.laundry_outstanding_qty_pcs,
  p.last_completion_mode
from progress p;

comment on view erp.v_fg_partial_completion_progress is
  'FG progress with separate ready-for-QC and Laundry-outstanding quantities. PARTIAL_SELECTION represents an explicit operator choice, never a Stuck Laundry balance.';

create or replace view erp.v_laundry_po_operational_progress
with (security_invoker = true)
as
with sent as (
  select d.po_id, sum(l.qty_sent_pcs)::bigint as sent_qty_pcs
  from erp.laundry_deliveries d
  join erp.laundry_delivery_lines l on l.delivery_id = d.id
  where d.status not in ('DRAFT','REVERSED')
  group by d.po_id
), returned as (
  select d.po_id,
    sum(rl.qty_good_received)::bigint as good_returned_qty_pcs,
    sum(rl.qty_bs_laundry)::bigint as bs_returned_qty_pcs,
    sum(rl.qty_good_received + rl.qty_bs_laundry)::bigint as returned_qty_pcs
  from erp.laundry_deliveries d
  join erp.laundry_receipts r on r.delivery_id = d.id and r.status = 'POSTED'
  join erp.laundry_receipt_lines rl on rl.receipt_id = r.id
  where d.status <> 'REVERSED'
  group by d.po_id
), resolved as (
  select d.po_id, sum(c.qty_claimed)::bigint as resolved_claim_qty_pcs
  from erp.laundry_claims c
  join erp.laundry_deliveries d on d.id = c.delivery_id
  where c.claim_type in ('MISSING','STUCK')
    and c.status in ('SETTLED','WRITTEN_OFF')
    and d.status <> 'REVERSED'
  group by d.po_id
)
select
  po.id as po_id,
  po.po_number,
  po.status as po_status,
  coalesce(s.sent_qty_pcs,0)::bigint as sent_qty_pcs,
  coalesce(r.good_returned_qty_pcs,0)::bigint as good_returned_qty_pcs,
  coalesce(r.bs_returned_qty_pcs,0)::bigint as bs_returned_qty_pcs,
  coalesce(r.returned_qty_pcs,0)::bigint as returned_qty_pcs,
  coalesce(x.resolved_claim_qty_pcs,0)::bigint as resolved_claim_qty_pcs,
  greatest(
    coalesce(s.sent_qty_pcs,0)
      - coalesce(r.returned_qty_pcs,0)
      - coalesce(x.resolved_claim_qty_pcs,0),
    0
  )::bigint as laundry_outstanding_qty_pcs
from erp.production_orders po
join sent s on s.po_id = po.id
left join returned r on r.po_id = po.id
left join resolved x on x.po_id = po.id;

comment on view erp.v_laundry_po_operational_progress is
  'PO-level Laundry balance. Posted physical returns and settled/written-off Stuck or Missing claims automatically reduce operational Laundry outstanding.';

do $migration$
begin
  if to_regprocedure('erp.post_fg_partial_completion_v2_legacy_v2610(jsonb,uuid,bigint)') is null
     and to_regprocedure('erp.post_fg_partial_completion_v2(jsonb,uuid,bigint)') is not null then
    alter function erp.post_fg_partial_completion_v2(jsonb, uuid, bigint)
      rename to post_fg_partial_completion_v2_legacy_v2610;
  end if;
end;
$migration$;

create or replace function erp.post_fg_partial_completion_v2(
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_mode text := upper(coalesce(nullif(btrim(p_payload->>'completion_mode'),''),'ALL_READY'));
  v_result jsonb;
  v_qc_id uuid;
  v_progress erp.v_fg_partial_completion_progress%rowtype;
begin
  perform erp.require_internal();
  if v_mode not in ('ALL_READY','PARTIAL_SELECTION') then
    raise exception 'completion_mode must be ALL_READY or PARTIAL_SELECTION';
  end if;

  v_result := erp.post_fg_partial_completion_v2_legacy_v2610(
    p_payload,
    p_client_request_id,
    p_expected_version
  );
  v_qc_id := nullif(v_result->>'qc_inspection_id','')::uuid;

  update erp.qc_inspections
  set completion_mode = v_mode
  where id = v_qc_id
    and completion_mode is distinct from v_mode;

  select * into v_progress
  from erp.v_fg_partial_completion_progress
  where cutting_group_id = nullif(v_result->>'cutting_group_id','')::uuid;

  return v_result || jsonb_build_object(
    'completion_mode', v_mode,
    'completion_status', v_progress.completion_status,
    'ready_for_qc_qty_pcs', v_progress.ready_for_qc_qty_pcs,
    'laundry_outstanding_qty_pcs', v_progress.laundry_outstanding_qty_pcs,
    'remaining_qc_qty_pcs', v_progress.remaining_qc_qty_pcs
  );
end;
$function$;

comment on function erp.post_fg_partial_completion_v2(jsonb, uuid, bigint) is
  'Posts one immutable FG completion and persists explicit ALL_READY versus PARTIAL_SELECTION intent. Stuck Laundry is reported separately.';

-- ---------------------------------------------------------------------------
-- Sales Draft reservation ledger
-- ---------------------------------------------------------------------------

alter table erp.sales_headers
  add column if not exists row_version bigint not null default 1;
alter table erp.sales_headers
  drop constraint if exists sales_headers_row_version_check;
alter table erp.sales_headers
  add constraint sales_headers_row_version_check check (row_version > 0);

drop trigger if exists trg_sales_row_version on erp.sales_headers;
create trigger trg_sales_row_version
before update on erp.sales_headers
for each row execute function erp.bump_row_version();

alter table erp.fg_stock_movements
  drop constraint if exists fg_stock_movements_movement_type_check;
alter table erp.fg_stock_movements
  add constraint fg_stock_movements_movement_type_check
  check (movement_type in (
    'OPENING','QC_GOOD','SALE_RESERVE','SALE','SALE_RETURN',
    'REBRAND_OUT','REBRAND_IN','BS_OUT','REWORK_IN','ADJUSTMENT','REVERSAL'
  ));

create or replace function erp._release_sale_draft_reservations(
  p_sale_id uuid,
  p_reason text
)
returns bigint
language plpgsql
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  r record;
  v_reversal_id uuid;
  v_released bigint := 0;
begin
  perform erp.require_internal();
  for r in
    select m.*
    from erp.fg_stock_movements m
    join erp.sales_items i on i.id = m.source_id
    where i.sale_id = p_sale_id
      and m.source_type = 'SALE_ITEM'
      and m.movement_type = 'SALE_RESERVE'
      and not exists (
        select 1 from erp.fg_stock_movements rv where rv.reversal_of_id = m.id
      )
    order by m.physical_at, m.book_order, m.id
    for update of m
  loop
    v_reversal_id := erp.post_fg_movement(
      r.product_id,r.lot_id,r.location_id,r.quality_grade,
      'REVERSAL',-r.qty_signed,r.unit_hpp_snapshot,r.customer_id,
      'FG_MOVEMENT_REVERSAL',r.id,r.physical_at,
      coalesce(nullif(btrim(p_reason),''),'Release sales Draft reservation'),false
    );
    update erp.fg_stock_movements
    set reversal_of_id = r.id
    where id = v_reversal_id;
    v_released := v_released + abs(r.qty_signed);
  end loop;

  delete from erp.sale_stock_allocations a
  using erp.sales_items i
  where a.sale_item_id = i.id
    and i.sale_id = p_sale_id;
  return v_released;
end;
$function$;

create or replace function erp._reserve_sale_draft(p_sale_id uuid)
returns bigint
language plpgsql
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  h erp.sales_headers%rowtype;
  item record;
  lotrow record;
  v_need integer;
  v_take integer;
  v_hpp numeric(18,6);
  v_reserved bigint := 0;
begin
  perform erp.require_internal();
  select * into h from erp.sales_headers where id = p_sale_id for update;
  if h.id is null or h.status <> 'DRAFT' then
    raise exception 'Sale must be DRAFT before reservation';
  end if;
  if h.source_location_id is null then
    raise exception 'Sale source FG location is required';
  end if;
  if not exists (select 1 from erp.sales_items where sale_id = h.id) then
    raise exception 'Sale has no items';
  end if;
  if exists (
    select 1
    from erp.fg_stock_movements m
    join erp.sales_items i on i.id = m.source_id
    where i.sale_id = h.id
      and m.movement_type = 'SALE_RESERVE'
      and not exists (select 1 from erp.fg_stock_movements rv where rv.reversal_of_id = m.id)
  ) then
    raise exception 'Active Draft reservation already exists; release it before rebuilding';
  end if;

  for item in
    select * from erp.sales_items where sale_id = h.id order by product_id,id
  loop
    insert into erp.fg_inventory_balances(product_id,location_id,quality_grade,cached_qty_pcs)
    values(item.product_id,h.source_location_id,'GRADE_A',0)
    on conflict(product_id,location_id,quality_grade) do nothing;
    perform 1
    from erp.fg_inventory_balances
    where product_id = item.product_id
      and location_id = h.source_location_id
      and quality_grade = 'GRADE_A'
    for update;

    v_need := item.qty_pcs;
    for lotrow in
      select fl.id,sum(fm.qty_signed)::integer as location_qty,fl.produced_at
      from erp.fg_lots fl
      join erp.fg_stock_movements fm on fm.lot_id = fl.id
      where fl.product_id = item.product_id
        and fm.location_id = h.source_location_id
        and fm.quality_grade = 'GRADE_A'
      group by fl.id,fl.produced_at
      having sum(fm.qty_signed) > 0
      order by fl.produced_at,fl.id
    loop
      exit when v_need <= 0;
      perform 1 from erp.fg_lots where id = lotrow.id for update;
      v_take := least(v_need,lotrow.location_qty);
      v_hpp := coalesce(erp.lock_current_hpp_per_pcs(lotrow.id),0);
      insert into erp.sale_stock_allocations(
        sale_item_id,lot_id,location_id,qty_pcs,unit_hpp_snapshot
      ) values (
        item.id,lotrow.id,h.source_location_id,v_take,v_hpp
      );
      perform erp.post_fg_movement(
        item.product_id,lotrow.id,h.source_location_id,'GRADE_A',
        'SALE_RESERVE',-v_take,v_hpp,h.customer_id,'SALE_ITEM',item.id,
        h.sale_date,'Draft invoice reserve · reduces sellable stock',false
      );
      v_need := v_need - v_take;
      v_reserved := v_reserved + v_take;
    end loop;
    if v_need > 0 then
      raise exception 'Insufficient FG stock for product %; short % pcs',item.product_id,v_need;
    end if;
  end loop;
  return v_reserved;
end;
$function$;

create or replace function erp.save_sale_draft_v2(
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_version bigint default null
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'save_sale_draft_v2';
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_sale_id uuid := nullif(p_payload->>'sale_id','')::uuid;
  v_sale_number text := nullif(btrim(p_payload->>'sale_number'),'');
  v_customer_id uuid := nullif(p_payload->>'customer_id','')::uuid;
  v_location_id uuid := nullif(p_payload->>'source_location_id','')::uuid;
  v_sale_date timestamptz := nullif(p_payload->>'sale_date','')::timestamptz;
  v_due_date date := nullif(p_payload->>'due_date','')::date;
  v_payment_terms text := nullif(btrim(p_payload->>'payment_terms'),'');
  v_notes text := nullif(btrim(p_payload->>'notes'),'');
  v_reason text := nullif(btrim(p_payload->>'reason'),'');
  v_items jsonb := p_payload->'items';
  h erp.sales_headers%rowtype;
  v_reserved bigint;
  v_released bigint := 0;
  v_total numeric(24,6);
begin
  perform erp.require_internal();
  if v_sale_number is null or v_customer_id is null or v_location_id is null or v_sale_date is null then
    raise exception 'sale_number, customer_id, source_location_id, and sale_date are required';
  end if;
  if v_reason is null then raise exception 'Draft save reason is required'; end if;
  if v_sale_date > clock_timestamp() + interval '5 minutes' then
    raise exception 'Tanggal/jam invoice berada di masa depan';
  end if;
  if jsonb_typeof(v_items) <> 'array' or jsonb_array_length(v_items) = 0 then
    raise exception 'Sale Draft requires at least one item';
  end if;
  if not exists (select 1 from erp.customers where id=v_customer_id and is_active=true) then
    raise exception 'Active customer is required';
  end if;
  if not exists (
    select 1 from erp.locations
    where id=v_location_id and is_active=true and location_type='FG_WAREHOUSE'
  ) then raise exception 'Active FG warehouse is required'; end if;
  if exists (
    select 1 from jsonb_to_recordset(v_items) as x(
      product_id uuid,qty_pcs integer,unit_price_snapshot numeric,discount_amount numeric,notes text
    )
    where x.product_id is null or coalesce(x.qty_pcs,0)<=0
      or coalesce(x.unit_price_snapshot,0)<0 or coalesce(x.discount_amount,0)<0
      or coalesce(x.discount_amount,0)>coalesce(x.qty_pcs,0)*coalesce(x.unit_price_snapshot,0)
  ) then raise exception 'Every sale line requires valid product, qty, price, and discount'; end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_sale_id is null then
    if p_expected_version is not null then
      raise exception 'expected_version must be null when creating a Sale Draft';
    end if;
    insert into erp.sales_headers(
      sale_number,customer_id,sale_date,due_date,status,payment_terms,notes,created_by,source_location_id
    ) values (
      v_sale_number,v_customer_id,v_sale_date,v_due_date,'DRAFT',v_payment_terms,v_notes,
      erp.current_app_user_id(),v_location_id
    ) returning * into h;
    v_sale_id := h.id;
  else
    if p_expected_version is null then raise exception 'expected_version is required when editing a Sale Draft'; end if;
    select * into h from erp.sales_headers where id=v_sale_id for update;
    if h.id is null then raise exception 'Sale Draft not found'; end if;
    if h.status <> 'DRAFT' then raise exception 'Only a DRAFT sale can be edited'; end if;
    if h.row_version <> p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,h.row_version;
    end if;
    v_released := erp._release_sale_draft_reservations(v_sale_id,'Edit Draft · release previous reservation');
    delete from erp.sales_items where sale_id=v_sale_id;
    update erp.sales_headers set
      sale_number=v_sale_number,customer_id=v_customer_id,sale_date=v_sale_date,
      due_date=v_due_date,payment_terms=v_payment_terms,notes=v_notes,
      source_location_id=v_location_id
    where id=v_sale_id
    returning * into h;
  end if;

  insert into erp.sales_items(
    sale_id,product_id,qty_pcs,unit_price_snapshot,discount_amount,notes
  )
  select v_sale_id,x.product_id,x.qty_pcs,x.unit_price_snapshot,
    coalesce(x.discount_amount,0),nullif(btrim(x.notes),'')
  from jsonb_to_recordset(v_items) as x(
    product_id uuid,qty_pcs integer,unit_price_snapshot numeric,discount_amount numeric,notes text
  );

  v_reserved := erp._reserve_sale_draft(v_sale_id);
  select * into h from erp.sales_headers where id=v_sale_id;
  select coalesce(sum(line_total),0) into v_total from erp.sales_items where sale_id=v_sale_id;
  v_response := jsonb_build_object(
    'sale_id',v_sale_id,'sale_number',h.sale_number,'status',h.status,
    'reserved_qty_pcs',v_reserved,'released_previous_qty_pcs',v_released,
    'sellable_stock_delta_pcs',-v_reserved,'invoice_total',v_total,
    'row_version',h.row_version
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

create or replace function erp.cancel_sale_draft_v2(
  p_sale_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  h erp.sales_headers%rowtype;
  v_released bigint;
begin
  perform erp.require_internal();
  if nullif(btrim(p_reason),'') is null then raise exception 'Cancellation reason is required'; end if;
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  v_hash := erp._request_hash(jsonb_build_object(
    'sale_id',p_sale_id,'reason',btrim(p_reason),'expected_version',p_expected_version
  ));
  v_cached := erp._idempotency_begin('cancel_sale_draft_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into h from erp.sales_headers where id=p_sale_id for update;
  if h.id is null then raise exception 'Sale Draft not found'; end if;
  if h.status <> 'DRAFT' then raise exception 'Only a DRAFT sale can be cancelled'; end if;
  if h.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,h.row_version;
  end if;
  perform set_config('app.change_reason',btrim(p_reason),true);
  v_released := erp._release_sale_draft_reservations(h.id,btrim(p_reason));
  update erp.sales_headers set status='CANCELLED' where id=h.id returning * into h;
  v_response := jsonb_build_object(
    'sale_id',h.id,'sale_number',h.sale_number,'status',h.status,
    'released_qty_pcs',v_released,'sellable_stock_delta_pcs',v_released,
    'row_version',h.row_version
  );
  return erp._idempotency_complete('cancel_sale_draft_v2',p_client_request_id,v_response);
end;
$function$;

create or replace function erp.post_sale(p_sale_id uuid)
returns void
language plpgsql
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  h erp.sales_headers%rowtype;
  v_sales numeric(24,6) := 0;
  v_cogs numeric(24,6) := 0;
  v_item_qty bigint;
  v_reserved_qty bigint;
  v_lines jsonb := '[]'::jsonb;
begin
  perform erp.require_internal();
  select * into h from erp.sales_headers where id=p_sale_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Sale must be DRAFT'; end if;
  if h.source_location_id is null then raise exception 'Sale source FG location is required'; end if;
  if not exists(select 1 from erp.sales_items where sale_id=p_sale_id) then raise exception 'Sale has no items'; end if;

  select coalesce(sum(qty_pcs),0),coalesce(sum(line_total),0)
  into v_item_qty,v_sales
  from erp.sales_items where sale_id=h.id;
  select coalesce(sum(abs(m.qty_signed)),0)
  into v_reserved_qty
  from erp.fg_stock_movements m
  join erp.sales_items i on i.id=m.source_id
  where i.sale_id=h.id and m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);

  if v_reserved_qty=0 then
    v_reserved_qty:=erp._reserve_sale_draft(h.id);
  end if;
  if v_reserved_qty<>v_item_qty then
    raise exception 'Sale Draft reservation mismatch. Items %, active reservation %',v_item_qty,v_reserved_qty;
  end if;
  if exists (
    select 1 from erp.sales_items i
    left join (
      select sale_item_id,sum(qty_pcs)::bigint qty_pcs
      from erp.sale_stock_allocations group by sale_item_id
    ) a on a.sale_item_id=i.id
    where i.sale_id=h.id and coalesce(a.qty_pcs,0)<>i.qty_pcs
  ) then raise exception 'Sale allocation does not match Draft line quantity'; end if;

  select coalesce(sum(a.qty_pcs*a.unit_hpp_snapshot),0)
  into v_cogs
  from erp.sale_stock_allocations a
  join erp.sales_items i on i.id=a.sale_item_id
  where i.sale_id=h.id;

  -- This is the key invariant: posting changes classification only. Quantity was
  -- already deducted at Draft time and must not be deducted a second time.
  update erp.fg_stock_movements m
  set movement_type='SALE', notes='Sale posted · quantity already reserved in Draft'
  from erp.sales_items i
  where i.id=m.source_id and i.sale_id=h.id
    and m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);

  update erp.sales_headers set status='POSTED' where id=h.id;
  if abs(v_sales)>0.005 then
    v_lines:=v_lines||jsonb_build_array(
      jsonb_build_object('mapping_key','AR_CUSTOMER','debit',round(v_sales,2),'credit',0,'customer_id',h.customer_id),
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',0,'credit',round(v_sales,2),'customer_id',h.customer_id));
  end if;
  if abs(v_cogs)>0.005 then
    v_lines:=v_lines||jsonb_build_array(
      jsonb_build_object('mapping_key','COGS','debit',round(v_cogs,2),'credit',0,'customer_id',h.customer_id),
      jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',round(v_cogs,2),'customer_id',h.customer_id));
  end if;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALE',h.id,h.sale_date::date,'Sales to customer/toko',v_lines);
  end if;
end;
$function$;

create or replace function erp.post_sale_v2(
  p_sale_id uuid,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  h erp.sales_headers%rowtype;
  v_before bigint;
  v_after bigint;
  v_qty bigint;
begin
  perform erp.require_internal();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'sale_id',p_sale_id,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('post_sale_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into h from erp.sales_headers where id=p_sale_id for update;
  if h.id is null then raise exception 'Sale not found'; end if;
  if h.status<>'DRAFT' then raise exception 'Sale must be DRAFT'; end if;
  if h.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,h.row_version;
  end if;
  select coalesce(sum(b.cached_qty_pcs),0) into v_before
  from erp.fg_inventory_balances b
  where b.location_id=h.source_location_id and b.quality_grade='GRADE_A'
    and b.product_id in (select product_id from erp.sales_items where sale_id=h.id);
  select coalesce(sum(qty_pcs),0) into v_qty from erp.sales_items where sale_id=h.id;
  perform erp.post_sale(h.id);
  select * into h from erp.sales_headers where id=h.id;
  select coalesce(sum(b.cached_qty_pcs),0) into v_after
  from erp.fg_inventory_balances b
  where b.location_id=h.source_location_id and b.quality_grade='GRADE_A'
    and b.product_id in (select product_id from erp.sales_items where sale_id=h.id);
  if v_before is distinct from v_after then
    raise exception 'Invariant violation: posting changed FG balance after Draft reservation';
  end if;
  v_response:=jsonb_build_object(
    'sale_id',h.id,'sale_number',h.sale_number,'status',h.status,
    'posted_qty_pcs',v_qty,'post_stock_delta_pcs',0,'row_version',h.row_version
  );
  return erp._idempotency_complete('post_sale_v2',p_client_request_id,v_response);
end;
$function$;

create or replace view erp.v_sale_reservation_progress
with (security_invoker = true)
as
with items as (
  select sale_id,sum(qty_pcs)::bigint as item_qty_pcs
  from erp.sales_items group by sale_id
), allocations as (
  select i.sale_id,sum(a.qty_pcs)::bigint as allocated_qty_pcs
  from erp.sales_items i
  join erp.sale_stock_allocations a on a.sale_item_id=i.id
  group by i.sale_id
), reservations as (
  select i.sale_id,sum(abs(m.qty_signed))::bigint as active_reserved_qty_pcs
  from erp.sales_items i
  join erp.fg_stock_movements m on m.source_id=i.id
  where m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)
  group by i.sale_id
)
select
  h.id as sale_id,h.sale_number,h.customer_id,h.source_location_id,h.sale_date,
  h.status,h.row_version,
  coalesce(i.item_qty_pcs,0)::bigint as item_qty_pcs,
  coalesce(a.allocated_qty_pcs,0)::bigint as allocated_qty_pcs,
  coalesce(r.active_reserved_qty_pcs,0)::bigint as active_reserved_qty_pcs,
  case
    when h.status='DRAFT'
      and coalesce(i.item_qty_pcs,0)=coalesce(a.allocated_qty_pcs,0)
      and coalesce(i.item_qty_pcs,0)=coalesce(r.active_reserved_qty_pcs,0)
      and coalesce(i.item_qty_pcs,0)>0 then 'RESERVED'
    when h.status='DRAFT' then 'RESERVATION_MISMATCH'
    else h.status
  end::text as reservation_status
from erp.sales_headers h
left join items i on i.sale_id=h.id
left join allocations a on a.sale_id=h.id
left join reservations r on r.sale_id=h.id;

comment on view erp.v_sale_reservation_progress is
  'Draft invoice reservation truth. A valid Draft has item qty = FIFO allocation qty = active SALE_RESERVE qty; Post creates no second stock delta.';

revoke all on function erp._release_sale_draft_reservations(uuid,text) from public,anon,authenticated;
revoke all on function erp._reserve_sale_draft(uuid) from public,anon,authenticated;
revoke all on function erp.post_fg_partial_completion_v2_legacy_v2610(jsonb,uuid,bigint) from public,anon,authenticated;
revoke all on function erp.save_sale_draft_v2(jsonb,uuid,bigint) from public,anon;
revoke all on function erp.cancel_sale_draft_v2(uuid,text,uuid,bigint) from public,anon;
revoke all on function erp.post_sale_v2(uuid,uuid,bigint) from public,anon;
revoke all on function erp.post_fg_partial_completion_v2(jsonb,uuid,bigint) from public,anon;

grant execute on function erp.save_sale_draft_v2(jsonb,uuid,bigint) to authenticated,service_role;
grant execute on function erp.cancel_sale_draft_v2(uuid,text,uuid,bigint) to authenticated,service_role;
grant execute on function erp.post_sale_v2(uuid,uuid,bigint) to authenticated,service_role;
grant execute on function erp.post_fg_partial_completion_v2(jsonb,uuid,bigint) to authenticated,service_role;
grant select on erp.v_fg_partial_completion_progress to authenticated,service_role;
grant select on erp.v_laundry_po_operational_progress to authenticated,service_role;
grant select on erp.v_sale_reservation_progress to authenticated,service_role;

notify pgrst, 'reload schema';
