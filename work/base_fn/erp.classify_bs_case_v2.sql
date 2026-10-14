-- bootstrap lines 7414-7491
CREATE OR REPLACE FUNCTION erp.classify_bs_case_v2(p_bs_case_id uuid, p_payload jsonb, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_case erp.bs_cases%rowtype;
  v_cause text;v_contractor uuid;v_vendor uuid;
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_component jsonb;v_snapshot uuid;
begin
  perform erp.require_internal();
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'bs_case_id',p_bs_case_id,'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin('classify_bs_case_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  select * into v_case from erp.bs_cases where id=p_bs_case_id for update;
  if v_case.id is null then raise exception 'BS case not found'; end if;
  if v_case.status not in('OPEN','PARTIAL','IN_REWORK') then raise exception 'Closed/cancelled BS case cannot be classified'; end if;
  if v_case.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_case.row_version;
  end if;
  v_cause:=upper(coalesce(nullif(p_payload->>'cause_source',''),v_case.cause_source));
  v_contractor:=case when p_payload?'responsible_contractor_id'
    then nullif(p_payload->>'responsible_contractor_id','')::uuid else v_case.responsible_contractor_id end;
  v_vendor:=case when p_payload?'responsible_vendor_id'
    then nullif(p_payload->>'responsible_vendor_id','')::uuid else v_case.responsible_vendor_id end;
  if v_cause='SEWING' and v_contractor is null then raise exception 'SEWING cause requires responsible contractor'; end if;
  if v_cause='LAUNDRY' and v_vendor is null then raise exception 'LAUNDRY cause requires responsible vendor'; end if;
  if v_cause not in('SEWING','LAUNDRY','UNKNOWN') then raise exception 'Invalid cause_source'; end if;
  perform set_config('app.change_reason',v_reason,true);
  update erp.bs_cases
  set cause_source=v_cause,responsible_contractor_id=v_contractor,
      responsible_vendor_id=v_vendor,
      notes=case when p_payload?'notes' then nullif(btrim(p_payload->>'notes'),'') else notes end,
      legacy_reference=case when p_payload?'legacy_reference' then nullif(btrim(p_payload->>'legacy_reference'),'') else legacy_reference end,
      updated_at=now()
  where id=v_case.id returning * into v_case;

  if p_payload?'components' then
    if exists(
      select 1 from erp.rework_component_lines rcl
      join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
      where bcc.bs_case_id=v_case.id
    ) then raise exception 'BS components are frozen after rework lines exist'; end if;
    if jsonb_typeof(p_payload->'components')<>'array' then raise exception 'components must be an array'; end if;
    delete from erp.bs_case_components where bs_case_id=v_case.id;
    for v_component in select value from jsonb_array_elements(p_payload->'components') loop
      select id into v_snapshot from erp.po_work_component_snapshots
      where po_id=v_case.po_id and work_component_id=(v_component->>'work_component_id')::uuid
      order by committed_at desc,id desc limit 1;
      insert into erp.bs_case_components(
        bs_case_id,po_component_snapshot_id,work_component_id,completed_before_bs_qty,notes
      ) values(
        v_case.id,v_snapshot,(v_component->>'work_component_id')::uuid,
        coalesce(nullif(v_component->>'completed_before_bs_qty','')::integer,0),
        nullif(btrim(v_component->>'notes'),'')
      );
    end loop;
    update erp.bs_cases set updated_at=now() where id=v_case.id returning * into v_case;
  end if;
  v_response:=jsonb_build_object(
    'bs_case_id',v_case.id,'status',v_case.status,'cause_source',v_case.cause_source,
    'row_version',v_case.row_version,'component_count',(
      select count(*) from erp.bs_case_components where bs_case_id=v_case.id
    )
  );
  return erp._idempotency_complete('classify_bs_case_v2',p_client_request_id,v_response);
end;
$function$;

alter function "erp"."classify_bs_case_v2"(p_bs_case_id uuid, p_payload jsonb, p_client_request_id uuid, p_expected_version bigint) owner to "postgres";
