-- bootstrap lines 16196-16339
CREATE OR REPLACE FUNCTION erp.record_sewing_terminal_v1(p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_operation constant text := 'record_sewing_terminal_v1';
  v_hash text;
  v_cached jsonb;
  v_work_completion_id uuid;
  v_qty integer;
  v_reason text;
  v_work erp.work_completion_events%rowtype;
  v_max_line_qty integer;
  v_cutting_qty bigint;
  v_existing_terminal_qty bigint;
  v_event erp.sewing_terminal_events%rowtype;
  v_response jsonb;
begin
  perform erp.require_internal();
  perform erp._cp3_assert_closed_json_object(
    p_payload,
    array['work_completion_id','qty_pcs','reason'],
    array['work_completion_id','qty_pcs','reason'],
    'SELESAI_DIJAHIT payload'
  );

  if jsonb_typeof(p_payload->'work_completion_id') is distinct from 'string'
     or jsonb_typeof(p_payload->'qty_pcs') is distinct from 'number'
     or jsonb_typeof(p_payload->'reason') is distinct from 'string' then
    raise exception 'SELESAI_DIJAHIT payload has invalid field types';
  end if;

  v_work_completion_id := (p_payload->>'work_completion_id')::uuid;
  v_qty := (p_payload->>'qty_pcs')::integer;
  v_reason := nullif(btrim(p_payload->>'reason'), '');

  if v_qty <= 0 then raise exception 'SELESAI_DIJAHIT qty must be positive'; end if;
  if v_reason is null then raise exception 'SELESAI_DIJAHIT reason is required'; end if;

  v_hash := erp._request_hash(jsonb_build_object('payload', p_payload));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_work
  from erp.work_completion_events
  where id = v_work_completion_id
  for update;

  if v_work.id is null then raise exception 'Work completion not found'; end if;
  if v_work.status <> 'POSTED' then
    raise exception 'SELESAI_DIJAHIT can only reference a POSTED production work completion';
  end if;

  perform erp._cp3_lock_business_date(erp._cp3_business_date(v_work.physical_at));
  if exists (
    select 1 from erp.attendance_hpp_pools p
    where p.status = 'ACTIVE'
      and erp._cp3_business_date(v_work.physical_at) between p.period_start and p.period_end
  ) then
    raise exception 'ACTIVE_ATTENDANCE_HPP_PERIOD_LOCKED: cancel the active pool before recording late/backdated SELESAI_DIJAHIT';
  end if;
  if v_work.cutting_group_id is null then
    raise exception 'SELESAI_DIJAHIT requires cutting-group lineage';
  end if;
  if not exists (
    select 1 from erp.contractors c
    where c.id = v_work.contractor_id and c.contractor_type = 'MANDOR'
  ) then
    raise exception 'SELESAI_DIJAHIT source contractor must have explicit role MANDOR';
  end if;
  if exists (
    select 1 from erp.sewing_terminal_events e
    where e.source_work_completion_id = v_work.id
      and e.event_kind = 'SELESAI_DIJAHIT'
  ) then
    raise exception 'This work completion already has an authoritative SELESAI_DIJAHIT event';
  end if;

  select max(l.qty_completed)::integer into v_max_line_qty
  from erp.work_completion_lines l
  where l.completion_id = v_work.id;

  if coalesce(v_max_line_qty, 0) <= 0 or v_qty > v_max_line_qty then
    raise exception 'SELESAI_DIJAHIT qty % exceeds the maximum completed qty % recorded by the owning work completion',
      v_qty, coalesce(v_max_line_qty, 0);
  end if;

  perform 1 from erp.cutting_groups where id = v_work.cutting_group_id for update;
  select coalesce(v.total_pcs, 0)::bigint into v_cutting_qty
  from erp.v_cutting_group_totals v
  where v.cutting_group_id = v_work.cutting_group_id;

  select coalesce(sum(e.qty_signed), 0)::bigint into v_existing_terminal_qty
  from erp.sewing_terminal_events e
  where e.cutting_group_id = v_work.cutting_group_id;

  if v_existing_terminal_qty + v_qty > coalesce(v_cutting_qty, 0) then
    raise exception 'Cumulative SELESAI_DIJAHIT qty would exceed cutting-group physical qty. Current %, new %, maximum %',
      v_existing_terminal_qty, v_qty, coalesce(v_cutting_qty, 0);
  end if;

  insert into erp.sewing_terminal_events(
    event_number, event_kind, source_work_completion_id,
    contractor_id, po_id, cutting_group_id, physical_at,
    qty_signed, reason, created_by
  ) values (
    'SEW-' || to_char(v_work.physical_at at time zone 'UTC', 'YYYYMMDDHH24MISSUS') || '-' || substr(gen_random_uuid()::text, 1, 8),
    'SELESAI_DIJAHIT', v_work.id,
    v_work.contractor_id, v_work.po_id, v_work.cutting_group_id, v_work.physical_at,
    v_qty, v_reason, erp.current_app_user_id()
  ) returning * into v_event;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'sewing_terminal_events', v_event.id, 'POST',
    jsonb_build_object(
      'event_kind', v_event.event_kind,
      'source_work_completion_id', v_event.source_work_completion_id,
      'contractor_id', v_event.contractor_id,
      'po_id', v_event.po_id,
      'cutting_group_id', v_event.cutting_group_id,
      'physical_at_epoch_us', erp._cp3_epoch_microseconds(v_event.physical_at),
      'qty_signed', v_event.qty_signed
    ),
    erp.current_app_user_id(), v_reason
  );

  v_response := jsonb_build_object(
    'sewing_terminal_event_id', v_event.id,
    'event_number', v_event.event_number,
    'event_kind', v_event.event_kind,
    'source_work_completion_id', v_event.source_work_completion_id,
    'physical_at_epoch_us', erp._cp3_epoch_microseconds(v_event.physical_at),
    'qty_pcs', v_event.qty_signed,
    'row_version', v_event.row_version
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

alter function "erp"."record_sewing_terminal_v1"(p_payload jsonb, p_client_request_id uuid) owner to "postgres";
