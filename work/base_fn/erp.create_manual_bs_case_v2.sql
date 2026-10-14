-- bootstrap lines 7833-7900
CREATE OR REPLACE FUNCTION erp.create_manual_bs_case_v2(p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_id uuid:=gen_random_uuid();
  v_type text:=upper(coalesce(p_payload->>'untracked_type',''));
  v_ref text:=nullif(btrim(p_payload->>'legacy_reference'),'');
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_physical timestamptz:=nullif(p_payload->>'physical_at','')::timestamptz;
  v_component jsonb;
  v_case erp.bs_cases%rowtype;
begin
  perform erp.require_internal();
  if v_type not in('LEGACY','OUT_OF_NOWHERE') then
    raise exception 'Manual BS is allowed only for LEGACY or OUT_OF_NOWHERE';
  end if;
  if v_ref is null then raise exception 'legacy_reference is required for manual BS traceability'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if v_physical is null or v_physical>clock_timestamp()+interval '5 minutes' then
    raise exception 'Valid non-future physical_at is required';
  end if;
  if coalesce(nullif(p_payload->>'qty_pcs','')::integer,0)<=0 then raise exception 'qty_pcs must be positive'; end if;
  v_hash:=erp._request_hash(p_payload);
  v_cached:=erp._idempotency_begin('create_manual_bs_case_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);
  insert into erp.bs_cases(
    id,bs_number,po_id,cutting_group_id,qc_item_id,product_id,
    detected_at_stage,cause_source,untracked_type,
    responsible_contractor_id,responsible_vendor_id,qty_pcs,status,
    physical_at,legacy_reference,notes
  ) values(
    v_id,coalesce(nullif(btrim(p_payload->>'bs_number'),''),
      'BS-MAN-'||to_char(v_physical,'YYYYMMDD')||'-'||substr(v_id::text,1,8)),
    null,null,null,nullif(p_payload->>'product_id','')::uuid,
    'UNKNOWN','UNKNOWN',v_type,
    nullif(p_payload->>'responsible_contractor_id','')::uuid,
    nullif(p_payload->>'responsible_vendor_id','')::uuid,
    (p_payload->>'qty_pcs')::integer,'OPEN',v_physical,v_ref,
    nullif(btrim(p_payload->>'notes'),'')
  ) returning * into v_case;
  if p_payload?'components' then
    if jsonb_typeof(p_payload->'components')<>'array' then raise exception 'components must be an array'; end if;
    for v_component in select value from jsonb_array_elements(p_payload->'components') loop
      insert into erp.bs_case_components(
        bs_case_id,po_component_snapshot_id,work_component_id,completed_before_bs_qty,notes
      ) values(
        v_case.id,null,(v_component->>'work_component_id')::uuid,
        coalesce(nullif(v_component->>'completed_before_bs_qty','')::integer,0),
        nullif(btrim(v_component->>'notes'),'')
      );
    end loop;
  end if;
  select * into v_case from erp.bs_cases where id=v_case.id;
  v_response:=jsonb_build_object(
    'bs_case_id',v_case.id,'bs_number',v_case.bs_number,'status',v_case.status,
    'row_version',v_case.row_version,'untracked_type',v_case.untracked_type
  );
  return erp._idempotency_complete('create_manual_bs_case_v2',p_client_request_id,v_response);
end;
$function$;

alter function "erp"."create_manual_bs_case_v2"(p_payload jsonb, p_client_request_id uuid) owner to "postgres";
