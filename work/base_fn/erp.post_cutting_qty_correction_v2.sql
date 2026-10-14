-- bootstrap lines 12770-12872
CREATE OR REPLACE FUNCTION erp.post_cutting_qty_correction_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_batch erp.cutting_batches%rowtype;
  v_batch_id uuid := nullif(p_payload->>'cutting_batch_id', '')::uuid;
  v_type text := upper(nullif(btrim(p_payload->>'correction_type'), ''));
  v_reason_code text := upper(nullif(btrim(p_payload->>'reason_code'), ''));
  v_reason text := nullif(btrim(p_payload->>'reason'), '');
  v_lines jsonb := p_payload->'lines';
  v_physical_at timestamptz;
  v_correction_id uuid;
  v_correction_number text;
  v_net_delta bigint;
  v_totals record;
begin
  perform erp.require_internal();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if v_batch_id is null then raise exception 'cutting_batch_id is required'; end if;
  if v_type is null then raise exception 'correction_type is required'; end if;
  if v_reason_code is null then raise exception 'reason_code is required'; end if;
  if v_reason is null then raise exception 'Correction reason is required'; end if;
  if jsonb_typeof(v_lines) <> 'array' or jsonb_array_length(v_lines) = 0 then
    raise exception 'Correction requires at least one line';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(
    'post_cutting_qty_correction_v2', p_client_request_id, v_hash
  );
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason', v_reason, true);

  select * into v_batch
  from erp.cutting_batches
  where id = v_batch_id
  for update;
  if v_batch.id is null then raise exception 'Cutting batch not found'; end if;
  if v_batch.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',
      p_expected_version, v_batch.row_version;
  end if;

  v_physical_at := coalesce(
    nullif(p_payload->>'physical_at', '')::timestamptz,
    clock_timestamp()
  );
  if v_physical_at > clock_timestamp() + interval '5 minutes' then
    raise exception 'Tanggal/jam Koreksi Potongan berada di masa depan';
  end if;
  v_correction_id := erp._post_cutting_qty_correction(
    v_batch_id, v_type, v_reason_code, v_reason,
    v_lines, v_physical_at, null
  );

  -- Touching the aggregate root makes every successful correction invalidate
  -- stale browser drafts through the existing row-version trigger.
  update erp.cutting_batches
  set updated_at = clock_timestamp()
  where id = v_batch_id
  returning * into v_batch;

  select c.correction_number, coalesce(sum(l.qty_delta_pcs), 0)::bigint
  into v_correction_number, v_net_delta
  from erp.cutting_qty_corrections c
  join erp.cutting_qty_correction_lines l on l.correction_id = c.id
  where c.id = v_correction_id
  group by c.correction_number;

  select original_pcs, adjustment_pcs, effective_pcs
  into v_totals
  from erp.v_cutting_batch_totals
  where cutting_batch_id = v_batch_id;

  v_response := jsonb_build_object(
    'correction_id', v_correction_id,
    'correction_number', v_correction_number,
    'cutting_batch_id', v_batch_id,
    'correction_type', v_type,
    'net_delta_pcs', v_net_delta,
    'original_pcs', coalesce(v_totals.original_pcs, 0),
    'adjustment_pcs', coalesce(v_totals.adjustment_pcs, 0),
    'effective_pcs', coalesce(v_totals.effective_pcs, 0),
    'row_version', v_batch.row_version,
    'status', 'POSTED'
  );
  return erp._idempotency_complete(
    'post_cutting_qty_correction_v2', p_client_request_id, v_response
  );
end;
$function$;

alter function "erp"."post_cutting_qty_correction_v2"(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint) owner to "postgres";
