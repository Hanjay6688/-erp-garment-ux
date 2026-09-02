-- ERP Garment v2.6.10
-- Partial Finished Goods completion through immutable QC postings.
--
-- Contract:
--   * every partial completion is its own POSTED QC document;
--   * GOOD creates its own FG lot, stock movement, HPP version, and reimbursement snapshot;
--   * retrying the same client_request_id returns the original response;
--   * stale browser drafts fail through cutting_groups.row_version;
--   * cumulative GOOD + BS cannot exceed effective Potongan quantity;
--   * a PO cannot become FINISHED while any Potongan source remains unaccounted.

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
      filter (where i.source_laundry_receipt_line_id is null), 0)::bigint as direct_qc_accounted_qty_pcs,
    count(distinct q.id)::bigint as completion_count,
    max(q.physical_at) as last_completion_at
  from erp.qc_inspection_items i
  join erp.qc_inspections q on q.id = i.inspection_id
  where q.status = 'POSTED'
  group by i.cutting_group_id
), laundry as (
  select
    l.cutting_group_id,
    coalesce(sum(l.qty_sent_pcs), 0)::bigint as laundry_sent_qty_pcs
  from erp.laundry_delivery_lines l
  join erp.laundry_deliveries d on d.id = l.delivery_id
  where d.status not in ('DRAFT', 'REVERSED')
  group by l.cutting_group_id
)
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
  coalesce(l.laundry_sent_qty_pcs, 0)::bigint as laundry_sent_qty_pcs,
  (coalesce(q.direct_qc_accounted_qty_pcs, 0) + coalesce(l.laundry_sent_qty_pcs, 0))::bigint as source_accounted_qty_pcs,
  greatest(
    coalesce(t.total_pcs, 0)
      - coalesce(q.direct_qc_accounted_qty_pcs, 0)
      - coalesce(l.laundry_sent_qty_pcs, 0),
    0
  )::bigint as remaining_source_qty_pcs,
  coalesce(q.completion_count, 0)::bigint as completion_count,
  q.last_completion_at,
  case
    when po.status = 'FINISHED' then 'FINISHED'
    when coalesce(q.qc_accounted_qty_pcs, 0) = 0 then 'OPEN'
    when coalesce(q.qc_accounted_qty_pcs, 0) < coalesce(t.total_pcs, 0) then 'PARTIAL'
    else 'QC_COMPLETE'
  end::text as completion_status
from erp.cutting_groups g
join erp.production_orders po on po.id = g.po_id
left join erp.v_cutting_group_totals t on t.cutting_group_id = g.id
left join qc q on q.cutting_group_id = g.id
left join laundry l on l.cutting_group_id = g.id;

comment on view erp.v_fg_partial_completion_progress is
  'Authoritative cumulative Finished Goods/QC progress per Potongan. PARTIAL is a posted fact, not an editable document status.';

create or replace function erp.guard_qc_laundry_source_matches_group()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
declare
  v_source_group_id uuid;
begin
  if new.source_laundry_receipt_line_id is null then
    return new;
  end if;

  select dl.cutting_group_id
  into v_source_group_id
  from erp.laundry_receipt_lines rl
  join erp.laundry_delivery_lines dl on dl.id = rl.delivery_line_id
  where rl.id = new.source_laundry_receipt_line_id;

  if v_source_group_id is null then
    raise exception 'QC laundry receipt source was not found';
  end if;
  if new.cutting_group_id is null or v_source_group_id is distinct from new.cutting_group_id then
    raise exception 'QC laundry source belongs to a different Potongan';
  end if;
  return new;
end;
$function$;

drop trigger if exists trg_qc_laundry_source_matches_group on erp.qc_inspection_items;
create trigger trg_qc_laundry_source_matches_group
before insert or update of cutting_group_id, source_laundry_receipt_line_id
on erp.qc_inspection_items
for each row execute function erp.guard_qc_laundry_source_matches_group();

create or replace function erp.guard_finished_po_source_accounting()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
declare
  r record;
begin
  if new.status = 'FINISHED' and old.status is distinct from 'FINISHED' then
    select
      p.cutting_group_id,
      p.group_number,
      p.effective_qty_pcs,
      p.source_accounted_qty_pcs,
      p.remaining_source_qty_pcs
    into r
    from erp.v_fg_partial_completion_progress p
    where p.po_id = new.id
      and p.effective_qty_pcs > 0
      and p.source_accounted_qty_pcs is distinct from p.effective_qty_pcs
    order by p.group_number, p.cutting_group_id
    limit 1;

    if found then
      raise exception
        'PO belum boleh FINISHED. Potongan % baru terjelaskan % dari % pcs; sisa sumber % pcs.',
        r.group_number,
        r.source_accounted_qty_pcs,
        r.effective_qty_pcs,
        r.remaining_source_qty_pcs;
    end if;
  end if;
  return new;
end;
$function$;

drop trigger if exists trg_guard_finished_po_source_accounting on erp.production_orders;
create trigger trg_guard_finished_po_source_accounting
before update of status on erp.production_orders
for each row execute function erp.guard_finished_po_source_accounting();

create or replace function erp.get_fg_partial_completion_context(p_cutting_group_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
declare
  v_group erp.cutting_groups%rowtype;
  v_progress jsonb;
  v_sizes jsonb;
  v_unassigned_adjustment bigint;
begin
  perform erp.require_internal();

  select * into v_group
  from erp.cutting_groups
  where id = p_cutting_group_id;
  if v_group.id is null then
    raise exception 'Potongan not found';
  end if;

  select to_jsonb(p) into v_progress
  from erp.v_fg_partial_completion_progress p
  where p.cutting_group_id = v_group.id;

  with original as (
    select s.size_id, sum(y.qty_pcs)::bigint as qty_pcs
    from erp.cutting_group_size_slots s
    left join erp.cutting_roll_yields y on y.size_slot_id = s.id
    where s.cutting_group_id = v_group.id
    group by s.size_id
  ), adjustment as (
    select s.size_id, sum(l.qty_delta_pcs)::bigint as qty_pcs
    from erp.cutting_qty_correction_lines l
    join erp.cutting_group_size_slots s on s.id = l.size_slot_id
    where l.cutting_group_id = v_group.id
    group by s.size_id
  ), posted as (
    select pr.size_id,
      sum(i.qty_good_pcs)::bigint as good_qty_pcs,
      sum(i.qty_bs_pcs)::bigint as bs_qty_pcs
    from erp.qc_inspection_items i
    join erp.qc_inspections q on q.id = i.inspection_id and q.status = 'POSTED'
    join erp.products pr on pr.id = i.final_product_id
    where i.cutting_group_id = v_group.id
    group by pr.size_id
  ), size_ids as (
    select size_id from original
    union select size_id from adjustment
    union select size_id from posted
  )
  select coalesce(jsonb_agg(jsonb_build_object(
    'size_id', z.size_id,
    'size_code', sz.size_code,
    'target_qty_pcs', coalesce(o.qty_pcs, 0) + coalesce(a.qty_pcs, 0),
    'good_qty_pcs', coalesce(p.good_qty_pcs, 0),
    'bs_qty_pcs', coalesce(p.bs_qty_pcs, 0),
    'remaining_qty_pcs', greatest(
      coalesce(o.qty_pcs, 0) + coalesce(a.qty_pcs, 0)
        - coalesce(p.good_qty_pcs, 0) - coalesce(p.bs_qty_pcs, 0),
      0
    ),
    'suggested_product_id', (
      select pr.id
      from erp.products pr
      join erp.production_orders po on po.model_id = pr.model_id
      where po.id = v_group.po_id
        and pr.size_id = z.size_id
        and pr.is_active = true
        and pr.effective_from <= clock_timestamp()
        and (pr.effective_to is null or pr.effective_to > clock_timestamp())
      order by pr.effective_from desc, pr.created_at desc, pr.id desc
      limit 1
    )
  ) order by sz.sort_order, sz.size_code), '[]'::jsonb)
  into v_sizes
  from size_ids z
  join erp.sizes sz on sz.id = z.size_id
  left join original o on o.size_id = z.size_id
  left join adjustment a on a.size_id = z.size_id
  left join posted p on p.size_id = z.size_id;

  select coalesce(sum(l.qty_delta_pcs), 0)::bigint
  into v_unassigned_adjustment
  from erp.cutting_qty_correction_lines l
  where l.cutting_group_id = v_group.id
    and l.size_slot_id is null;

  return jsonb_build_object(
    'cutting_group_id', v_group.id,
    'po_id', v_group.po_id,
    'group_number', v_group.group_number,
    'row_version', v_group.row_version,
    'progress', coalesce(v_progress, '{}'::jsonb),
    'sizes', coalesce(v_sizes, '[]'::jsonb),
    'unassigned_adjustment_qty_pcs', v_unassigned_adjustment
  );
end;
$function$;

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
  v_operation constant text := 'post_fg_partial_completion_v2';
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_group erp.cutting_groups%rowtype;
  v_po_status text;
  v_group_id uuid := nullif(p_payload->>'cutting_group_id', '')::uuid;
  v_destination_location_id uuid := nullif(p_payload->>'destination_location_id', '')::uuid;
  v_physical_at timestamptz := coalesce(
    nullif(p_payload->>'physical_at', '')::timestamptz,
    clock_timestamp()
  );
  v_reason text := nullif(btrim(p_payload->>'reason'), '');
  v_lines jsonb := p_payload->'lines';
  v_qc_id uuid := gen_random_uuid();
  v_inspection_number text;
  v_total_qty bigint;
  v_good_qty bigint;
  v_bs_qty bigint;
  v_effective_qty bigint;
  v_prior_qty bigint;
  v_stock_qty bigint;
  v_stock_event_count bigint;
  v_progress erp.v_fg_partial_completion_progress%rowtype;
begin
  perform erp.require_internal();
  if p_expected_version is null then
    raise exception 'expected_version is required';
  end if;
  if v_group_id is null then
    raise exception 'cutting_group_id is required';
  end if;
  if v_destination_location_id is null then
    raise exception 'destination_location_id is required';
  end if;
  if v_reason is null then
    raise exception 'Completion reason is required';
  end if;
  if v_physical_at > clock_timestamp() + interval '5 minutes' then
    raise exception 'Tanggal/jam penyelesaian FG berada di masa depan';
  end if;
  if jsonb_typeof(v_lines) <> 'array' or jsonb_array_length(v_lines) = 0 then
    raise exception 'Partial FG completion requires at least one line';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then
    return v_cached;
  end if;

  perform set_config('app.change_reason', v_reason, true);

  select * into v_group
  from erp.cutting_groups
  where id = v_group_id
  for update;
  if v_group.id is null then
    raise exception 'Potongan not found';
  end if;
  if v_group.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',
      p_expected_version, v_group.row_version;
  end if;

  select status into v_po_status
  from erp.production_orders
  where id = v_group.po_id
  for update;
  if v_po_status in ('FINISHED', 'CANCELLED') then
    raise exception 'PO berstatus % dan tidak menerima penyelesaian FG baru', v_po_status;
  end if;

  if not exists (
    select 1 from erp.locations l
    where l.id = v_destination_location_id
      and l.is_active = true
      and l.location_type = 'FG_WAREHOUSE'
  ) then
    raise exception 'Destination must be an active FG warehouse';
  end if;

  if exists (
    select 1
    from jsonb_to_recordset(v_lines) as x(
      final_product_id uuid,
      qty_good_pcs integer,
      qty_bs_pcs integer,
      source_laundry_receipt_line_id uuid,
      notes text
    )
    where coalesce(x.qty_good_pcs, 0) < 0
       or coalesce(x.qty_bs_pcs, 0) < 0
       or coalesce(x.qty_good_pcs, 0) + coalesce(x.qty_bs_pcs, 0) <= 0
       or x.final_product_id is null
  ) then
    raise exception 'Every completion line requires a SKU and a positive GOOD/BS quantity';
  end if;

  if exists (
    select 1
    from jsonb_to_recordset(v_lines) as x(
      final_product_id uuid,
      qty_good_pcs integer,
      qty_bs_pcs integer,
      source_laundry_receipt_line_id uuid,
      notes text
    )
    group by x.final_product_id, x.source_laundry_receipt_line_id
    having count(*) > 1
  ) then
    raise exception 'Duplicate SKU and laundry source lines are not allowed';
  end if;

  select
    sum(coalesce(x.qty_good_pcs, 0) + coalesce(x.qty_bs_pcs, 0))::bigint,
    sum(coalesce(x.qty_good_pcs, 0))::bigint,
    sum(coalesce(x.qty_bs_pcs, 0))::bigint
  into v_total_qty, v_good_qty, v_bs_qty
  from jsonb_to_recordset(v_lines) as x(
    final_product_id uuid,
    qty_good_pcs integer,
    qty_bs_pcs integer,
    source_laundry_receipt_line_id uuid,
    notes text
  );

  select effective_qty_pcs, qc_accounted_qty_pcs
  into v_effective_qty, v_prior_qty
  from erp.v_fg_partial_completion_progress
  where cutting_group_id = v_group.id;
  if coalesce(v_effective_qty, 0) <= 0 then
    raise exception 'Potongan has no effective quantity available for FG';
  end if;
  if coalesce(v_prior_qty, 0) + coalesce(v_total_qty, 0) > v_effective_qty then
    raise exception
      'Qty penyelesaian melebihi sisa Potongan. Efektif %, sudah diposting %, input %.',
      v_effective_qty, coalesce(v_prior_qty, 0), coalesce(v_total_qty, 0);
  end if;

  v_inspection_number := 'FGP-'
    || to_char(v_physical_at, 'YYMMDD') || '-'
    || upper(substr(replace(p_client_request_id::text, '-', ''), 1, 10));

  insert into erp.qc_inspections(
    id, inspection_number, po_id, physical_at, status,
    notes, created_by, destination_location_id
  ) values (
    v_qc_id, v_inspection_number, v_group.po_id, v_physical_at, 'DRAFT',
    'Partial FG completion: ' || v_reason,
    erp.current_app_user_id(), v_destination_location_id
  );

  insert into erp.qc_inspection_items(
    inspection_id, cutting_group_id, source_laundry_receipt_line_id,
    final_product_id, qty_good_pcs, qty_bs_pcs, notes
  )
  select
    v_qc_id,
    v_group.id,
    x.source_laundry_receipt_line_id,
    x.final_product_id,
    coalesce(x.qty_good_pcs, 0),
    coalesce(x.qty_bs_pcs, 0),
    nullif(btrim(x.notes), '')
  from jsonb_to_recordset(v_lines) as x(
    final_product_id uuid,
    qty_good_pcs integer,
    qty_bs_pcs integer,
    source_laundry_receipt_line_id uuid,
    notes text
  );

  perform erp.post_qc(v_qc_id);

  -- Invalidate stale partial-completion drafts after every successful posting.
  update erp.cutting_groups
  set updated_at = clock_timestamp()
  where id = v_group.id
  returning * into v_group;

  select * into v_progress
  from erp.v_fg_partial_completion_progress
  where cutting_group_id = v_group.id;

  select
    coalesce(sum(m.qty_signed), 0)::bigint,
    count(*)::bigint
  into v_stock_qty, v_stock_event_count
  from erp.fg_stock_movements m
  where m.movement_type = 'QC_GOOD'
    and m.source_type = 'QC_ITEM'
    and m.source_id in (
      select i.id from erp.qc_inspection_items i where i.inspection_id = v_qc_id
    );

  v_response := jsonb_build_object(
    'qc_inspection_id', v_qc_id,
    'inspection_number', v_inspection_number,
    'cutting_group_id', v_group.id,
    'po_id', v_group.po_id,
    'completion_status', v_progress.completion_status,
    'posted_qty_pcs', v_total_qty,
    'good_qty_pcs', v_good_qty,
    'bs_qty_pcs', v_bs_qty,
    'fg_stock_in_qty_pcs', v_stock_qty,
    'fg_stock_event_count', v_stock_event_count,
    'cumulative_qc_qty_pcs', v_progress.qc_accounted_qty_pcs,
    'remaining_qc_qty_pcs', v_progress.remaining_qc_qty_pcs,
    'completion_count', v_progress.completion_count,
    'row_version', v_group.row_version,
    'document_status', 'POSTED'
  );

  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

comment on function erp.post_fg_partial_completion_v2(jsonb, uuid, bigint) is
  'Posts one immutable partial FG/QC completion. Uses UUID idempotency, Potongan optimistic locking, cumulative quantity guards, and existing FG/HPP/reimbursement ledgers.';
comment on function erp.get_fg_partial_completion_context(uuid) is
  'Returns authoritative Potongan progress, row_version, and size-level suggested SKU context for the partial FG writer.';

revoke all on function erp.guard_qc_laundry_source_matches_group() from public, anon, authenticated;
revoke all on function erp.guard_finished_po_source_accounting() from public, anon, authenticated;
revoke all on function erp.post_fg_partial_completion_v2(jsonb, uuid, bigint) from public, anon;
revoke all on function erp.get_fg_partial_completion_context(uuid) from public, anon;

grant execute on function erp.post_fg_partial_completion_v2(jsonb, uuid, bigint) to authenticated, service_role;
grant execute on function erp.get_fg_partial_completion_context(uuid) to authenticated, service_role;
grant select on erp.v_fg_partial_completion_progress to authenticated, service_role;

notify pgrst, 'reload schema';
