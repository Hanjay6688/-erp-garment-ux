-- bootstrap lines 21924-22008
CREATE OR REPLACE FUNCTION erp.save_laundry_claim_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_action text:=upper(coalesce(nullif(p_payload->>'action',''),'SAVE'));
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_claim erp.laundry_claims%rowtype;
  v_target_status text;
begin
  perform erp.require_internal();
  if v_action not in('SAVE','REJECT','REOPEN') then
    raise exception 'Claim action must be SAVE, REJECT, or REOPEN';
  end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_laundry_claim_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_id is null then
    if v_action<>'SAVE' then raise exception 'Create a claim with SAVE first'; end if;
    if p_expected_version is not null then raise exception 'expected_version must be null when creating a claim'; end if;
    if coalesce(btrim(p_payload->>'claim_number'),'')='' then raise exception 'claim_number is required'; end if;
    if nullif(p_payload->>'opened_at','')::timestamptz>clock_timestamp()+interval '5 minutes' then
      raise exception 'Claim opened_at cannot be in the future';
    end if;
    insert into erp.laundry_claims(
      claim_number,vendor_id,delivery_id,receipt_line_id,qty_claimed,claim_type,
      compensation_amount,status,opened_at,resolution_date,notes
    ) values(
      btrim(p_payload->>'claim_number'),(p_payload->>'vendor_id')::uuid,
      nullif(p_payload->>'delivery_id','')::uuid,nullif(p_payload->>'receipt_line_id','')::uuid,
      (p_payload->>'qty_claimed')::integer,upper(p_payload->>'claim_type'),
      coalesce(nullif(p_payload->>'compensation_amount','')::numeric,0),'OPEN',
      coalesce(nullif(p_payload->>'opened_at','')::timestamptz,now()),
      nullif(p_payload->>'resolution_date','')::date,nullif(btrim(p_payload->>'notes'),'')
    ) returning * into v_claim;
  else
    if p_expected_version is null then raise exception 'expected_version is required'; end if;
    select * into v_claim from erp.laundry_claims where id=v_id for update;
    if v_claim.id is null then raise exception 'Laundry claim not found'; end if;
    if v_claim.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_claim.row_version;
    end if;
    if v_claim.status in('SETTLED','WRITTEN_OFF') then
      raise exception 'Final claim is locked; use reverse_laundry_claim_resolution first';
    end if;
    if v_action='REOPEN' then
      perform erp.require_owner_admin();v_target_status:='OPEN';
    elsif v_action='REJECT' then v_target_status:='REJECTED';
    else
      if v_claim.status='REJECTED' then raise exception 'Rejected claim requires REOPEN by OWNER/ADMIN'; end if;
      v_target_status:=case when upper(coalesce(nullif(p_payload->>'status',''),v_claim.status))='ACCEPTED'
        then 'ACCEPTED' else 'OPEN' end;
    end if;
    update erp.laundry_claims
    set claim_number=coalesce(nullif(btrim(p_payload->>'claim_number'),''),v_claim.claim_number),
        vendor_id=case when p_payload?'vendor_id' then (p_payload->>'vendor_id')::uuid else v_claim.vendor_id end,
        delivery_id=case when p_payload?'delivery_id' then nullif(p_payload->>'delivery_id','')::uuid else v_claim.delivery_id end,
        receipt_line_id=case when p_payload?'receipt_line_id' then nullif(p_payload->>'receipt_line_id','')::uuid else v_claim.receipt_line_id end,
        qty_claimed=coalesce(nullif(p_payload->>'qty_claimed','')::integer,v_claim.qty_claimed),
        claim_type=upper(coalesce(nullif(p_payload->>'claim_type',''),v_claim.claim_type)),
        compensation_amount=coalesce(nullif(p_payload->>'compensation_amount','')::numeric,v_claim.compensation_amount),
        status=v_target_status,
        opened_at=coalesce(nullif(p_payload->>'opened_at','')::timestamptz,v_claim.opened_at),
        resolution_date=case when p_payload?'resolution_date' then nullif(p_payload->>'resolution_date','')::date else v_claim.resolution_date end,
        notes=case when p_payload?'notes' then nullif(btrim(p_payload->>'notes'),'') else v_claim.notes end
    where id=v_claim.id returning * into v_claim;
  end if;
  v_response:=jsonb_build_object(
    'laundry_claim_id',v_claim.id,'claim_number',v_claim.claim_number,
    'status',v_claim.status,'row_version',v_claim.row_version,
    'qty_claimed',v_claim.qty_claimed,'compensation_amount',v_claim.compensation_amount
  );
  return erp._idempotency_complete('save_laundry_claim_v2',p_client_request_id,v_response);
end;
$function$;

alter function "erp"."save_laundry_claim_v2"(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint) owner to "postgres";
