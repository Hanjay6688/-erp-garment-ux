-- bootstrap lines 13079-13123
CREATE OR REPLACE FUNCTION erp.post_fg_partial_completion_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
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

alter function "erp"."post_fg_partial_completion_v2"(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint) owner to "postgres";
