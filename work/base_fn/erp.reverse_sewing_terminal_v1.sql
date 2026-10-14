-- bootstrap lines 19650-19740
CREATE OR REPLACE FUNCTION erp.reverse_sewing_terminal_v1(p_event_id uuid, p_reason text, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_operation constant text := 'reverse_sewing_terminal_v1';
  v_hash text;
  v_cached jsonb;
  v_original erp.sewing_terminal_events%rowtype;
  v_reversal erp.sewing_terminal_events%rowtype;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  if p_event_id is null or p_expected_version is null then
    raise exception 'event_id and expected_version are required';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'SELESAI_DIJAHIT reversal reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'event_id', p_event_id,
    'reason', btrim(p_reason),
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_original
  from erp.sewing_terminal_events
  where id = p_event_id
  for update;

  if v_original.id is null or v_original.event_kind <> 'SELESAI_DIJAHIT' then
    raise exception 'Original SELESAI_DIJAHIT event not found';
  end if;
  if v_original.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_original.row_version;
  end if;

  perform erp._cp3_lock_business_date(erp._cp3_business_date(v_original.physical_at));
  if exists (select 1 from erp.sewing_terminal_events where reversal_of_id = v_original.id) then
    raise exception 'SELESAI_DIJAHIT event is already reversed';
  end if;
  if exists (
    select 1
    from erp.attendance_hpp_pool_allocations a
    join erp.attendance_hpp_pools p on p.id = a.pool_id
    where a.sewing_terminal_event_id = v_original.id
      and p.status = 'ACTIVE'
  ) then
    raise exception 'SELESAI_DIJAHIT is consumed by an ACTIVE attendance HPP pool; cancel that pool first';
  end if;

  insert into erp.sewing_terminal_events(
    event_number, event_kind, reversal_of_id,
    contractor_id, po_id, cutting_group_id, physical_at,
    qty_signed, reason, created_by
  ) values (
    'SEW-RV-' || to_char(clock_timestamp() at time zone 'UTC', 'YYYYMMDDHH24MISSUS') || '-' || substr(gen_random_uuid()::text, 1, 8),
    'REVERSAL', v_original.id,
    v_original.contractor_id, v_original.po_id, v_original.cutting_group_id,
    v_original.physical_at, -v_original.qty_signed,
    btrim(p_reason), erp.current_app_user_id()
  ) returning * into v_reversal;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'sewing_terminal_events', v_original.id, 'REVERSE',
    jsonb_build_object(
      'reversal_event_id', v_reversal.id,
      'qty_signed', v_reversal.qty_signed,
      'original_physical_at_epoch_us', erp._cp3_epoch_microseconds(v_original.physical_at)
    ),
    erp.current_app_user_id(), btrim(p_reason)
  );

  v_response := jsonb_build_object(
    'original_event_id', v_original.id,
    'reversal_event_id', v_reversal.id,
    'status', 'REVERSED',
    'qty_reversed', v_original.qty_signed
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

alter function "erp"."reverse_sewing_terminal_v1"(p_event_id uuid, p_reason text, p_client_request_id uuid, p_expected_version bigint) owner to "postgres";
