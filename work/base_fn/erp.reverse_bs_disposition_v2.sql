-- bootstrap lines 17504-17547
CREATE OR REPLACE FUNCTION erp.reverse_bs_disposition_v2(p_resolution_id uuid, p_reason text, p_client_request_id uuid, p_expected_bs_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_resolution erp.bs_resolutions%rowtype;v_case erp.bs_cases%rowtype;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null then raise exception 'Reversal reason is required'; end if;
  if p_expected_bs_version is null then raise exception 'expected_bs_version is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'resolution_id',p_resolution_id,'reason',btrim(p_reason),'expected_version',p_expected_bs_version
  ));
  v_cached:=erp._idempotency_begin('reverse_bs_disposition_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_resolution from erp.bs_resolutions where id=p_resolution_id for update;
  if v_resolution.id is null then raise exception 'BS disposition not found'; end if;
  if v_resolution.source_rework_order_id is not null
     or v_resolution.resolution_type in('REWORK_SEWING','REWORK_LAUNDRY') then
    raise exception 'Rework resolution must be reversed through reverse_rework_completion';
  end if;
  select * into v_case from erp.bs_cases where id=v_resolution.bs_case_id for update;
  if v_case.row_version<>p_expected_bs_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_bs_version,v_case.row_version;
  end if;
  perform set_config('app.change_reason',btrim(p_reason),true);
  delete from erp.bs_resolutions where id=v_resolution.id;
  perform erp.refresh_bs_case_status(v_case.id);
  insert into erp.audit_logs(entity_type,entity_id,action,old_data,changed_by,change_reason)
  values('bs_resolutions',v_resolution.id,'REVERSE',to_jsonb(v_resolution),erp.current_app_user_id(),btrim(p_reason));
  select * into v_case from erp.bs_cases where id=v_case.id;
  v_response:=jsonb_build_object(
    'bs_resolution_id',v_resolution.id,'status','REVERSED',
    'bs_case_id',v_case.id,'bs_case_status',v_case.status,'row_version',v_case.row_version
  );
  return erp._idempotency_complete('reverse_bs_disposition_v2',p_client_request_id,v_response);
end;
$function$;

alter function "erp"."reverse_bs_disposition_v2"(p_resolution_id uuid, p_reason text, p_client_request_id uuid, p_expected_bs_version bigint) owner to "postgres";
