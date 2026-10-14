-- bootstrap lines 17819-17922
CREATE OR REPLACE FUNCTION erp.reverse_cutting_qty_correction_v2(p_correction_id uuid, p_reason text, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_reason text := nullif(btrim(p_reason), '');
  v_source erp.cutting_qty_corrections%rowtype;
  v_batch erp.cutting_batches%rowtype;
  v_reversal_id uuid;
  v_reversal_number text;
  v_net_delta bigint;
  v_totals record;
begin
  perform erp.require_owner_admin();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if p_correction_id is null then raise exception 'correction_id is required'; end if;
  if v_reason is null then raise exception 'Reversal reason is required'; end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'correction_id', p_correction_id,
    'reason', v_reason,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(
    'reverse_cutting_qty_correction_v2', p_client_request_id, v_hash
  );
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason', v_reason, true);

  select * into v_source
  from erp.cutting_qty_corrections
  where id = p_correction_id;
  if v_source.id is null then raise exception 'Correction not found'; end if;
  if v_source.correction_type = 'REVERSAL' then
    raise exception 'A REVERSAL cannot be reversed; post a new reasoned correction instead';
  end if;

  select * into v_batch
  from erp.cutting_batches
  where id = v_source.cutting_batch_id
  for update;
  if v_batch.id is null then raise exception 'Cutting batch not found'; end if;
  if v_batch.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',
      p_expected_version, v_batch.row_version;
  end if;

  select * into v_source
  from erp.cutting_qty_corrections
  where id = p_correction_id
  for update;
  if exists (
    select 1 from erp.cutting_qty_corrections
    where reversal_of_id = p_correction_id
  ) then
    raise exception 'Correction has already been reversed';
  end if;

  v_reversal_id := erp.reverse_cutting_qty_correction(
    p_correction_id, v_reason
  );

  update erp.cutting_batches
  set updated_at = clock_timestamp()
  where id = v_source.cutting_batch_id
  returning * into v_batch;

  select c.correction_number, coalesce(sum(l.qty_delta_pcs), 0)::bigint
  into v_reversal_number, v_net_delta
  from erp.cutting_qty_corrections c
  join erp.cutting_qty_correction_lines l on l.correction_id = c.id
  where c.id = v_reversal_id
  group by c.correction_number;

  select original_pcs, adjustment_pcs, effective_pcs
  into v_totals
  from erp.v_cutting_batch_totals
  where cutting_batch_id = v_source.cutting_batch_id;

  v_response := jsonb_build_object(
    'correction_id', p_correction_id,
    'reversal_id', v_reversal_id,
    'reversal_number', v_reversal_number,
    'cutting_batch_id', v_source.cutting_batch_id,
    'net_delta_pcs', v_net_delta,
    'original_pcs', coalesce(v_totals.original_pcs, 0),
    'adjustment_pcs', coalesce(v_totals.adjustment_pcs, 0),
    'effective_pcs', coalesce(v_totals.effective_pcs, 0),
    'row_version', v_batch.row_version,
    'status', 'REVERSED'
  );
  return erp._idempotency_complete(
    'reverse_cutting_qty_correction_v2', p_client_request_id, v_response
  );
end;
$function$;

alter function "erp"."reverse_cutting_qty_correction_v2"(p_correction_id uuid, p_reason text, p_client_request_id uuid, p_expected_version bigint) owner to "postgres";
