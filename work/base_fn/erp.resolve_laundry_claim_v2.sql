-- bootstrap lines 17215-17252
CREATE OR REPLACE FUNCTION erp.resolve_laundry_claim_v2(p_claim_id uuid, p_resolution text, p_reason text, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_claim erp.laundry_claims%rowtype;
begin
  perform erp.require_owner_admin();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if nullif(btrim(p_reason),'') is null then raise exception 'Claim resolution reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'claim_id',p_claim_id,'resolution',upper(p_resolution),'reason',btrim(p_reason),
    'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('resolve_laundry_claim_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_claim from erp.laundry_claims where id=p_claim_id for update;
  if v_claim.id is null then raise exception 'Laundry claim not found'; end if;
  if v_claim.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_claim.row_version;
  end if;
  perform set_config('app.change_reason',btrim(p_reason),true);
  perform erp.resolve_laundry_claim(v_claim.id,upper(p_resolution),btrim(p_reason));
  select * into v_claim from erp.laundry_claims where id=v_claim.id;
  v_response:=jsonb_build_object(
    'laundry_claim_id',v_claim.id,'status',v_claim.status,
    'row_version',v_claim.row_version,'resolved_at',v_claim.resolved_at,
    'resolution_date',v_claim.resolution_date
  );
  return erp._idempotency_complete('resolve_laundry_claim_v2',p_client_request_id,v_response);
end;
$function$;

alter function "erp"."resolve_laundry_claim_v2"(p_claim_id uuid, p_resolution text, p_reason text, p_client_request_id uuid, p_expected_version bigint) owner to "postgres";
