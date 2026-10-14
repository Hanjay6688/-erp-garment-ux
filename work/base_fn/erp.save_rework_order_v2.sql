-- bootstrap lines 22992-23122
CREATE OR REPLACE FUNCTION erp.save_rework_order_v2(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
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
  v_order erp.rework_orders%rowtype;
  v_component jsonb;v_total_return integer;
begin
  perform erp.require_internal();
  if v_action not in('SAVE','CANCEL') then raise exception 'Rework action must be SAVE or CANCEL'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_rework_order_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_id is null then
    if v_action='CANCEL' then raise exception 'Rework id is required for CANCEL'; end if;
    if p_expected_version is not null then raise exception 'expected_version must be null when creating rework'; end if;
    v_total_return:=coalesce(nullif(p_payload->>'qty_good_returned','')::integer,0)
      +coalesce(nullif(p_payload->>'qty_bs_returned','')::integer,0);
    if v_total_return>=coalesce(nullif(p_payload->>'qty_sent','')::integer,0) then
      raise exception 'Fully reconciled return must use complete_rework_order_v2 after creating the active order';
    end if;
    insert into erp.rework_orders(
      rework_number,bs_case_id,destination_type,contractor_id,vendor_id,
      qty_sent,qty_good_returned,qty_bs_returned,physical_sent_at,status,
      return_fg_location_id,notes
    ) values(
      btrim(p_payload->>'rework_number'),(p_payload->>'bs_case_id')::uuid,
      upper(p_payload->>'destination_type'),nullif(p_payload->>'contractor_id','')::uuid,
      nullif(p_payload->>'vendor_id','')::uuid,(p_payload->>'qty_sent')::integer,
      coalesce(nullif(p_payload->>'qty_good_returned','')::integer,0),
      coalesce(nullif(p_payload->>'qty_bs_returned','')::integer,0),
      (p_payload->>'physical_sent_at')::timestamptz,
      case when v_total_return>0 then 'PARTIAL'
           when upper(coalesce(nullif(p_payload->>'status',''),'OPEN'))='IN_PROGRESS' then 'IN_PROGRESS'
           else 'OPEN' end,
      nullif(p_payload->>'return_fg_location_id','')::uuid,nullif(btrim(p_payload->>'notes'),'')
    ) returning * into v_order;
    v_id:=v_order.id;
  else
    if p_expected_version is null then raise exception 'expected_version is required'; end if;
    select * into v_order from erp.rework_orders where id=v_id for update;
    if v_order.id is null then raise exception 'Rework order not found'; end if;
    if v_order.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_order.row_version;
    end if;
    if v_order.cost_posted or v_order.status in('COMPLETED','CANCELLED') then
      raise exception 'Completed/cancelled rework is locked; use reversal/correction';
    end if;
    if v_action='CANCEL' then
      if v_order.qty_good_returned+v_order.qty_bs_returned>0 then
        raise exception 'Partially returned rework must be fully reconciled before cancellation';
      end if;
      update erp.rework_orders set status='CANCELLED',notes=concat_ws(E'\n',notes,'CANCELLED: '||v_reason),updated_at=now()
      where id=v_id returning * into v_order;
      perform erp.refresh_bs_case_status(v_order.bs_case_id);
      v_response:=jsonb_build_object(
        'rework_order_id',v_order.id,'status',v_order.status,'row_version',v_order.row_version
      );
      return erp._idempotency_complete('save_rework_order_v2',p_client_request_id,v_response);
    end if;
    v_total_return:=coalesce(nullif(p_payload->>'qty_good_returned','')::integer,v_order.qty_good_returned)
      +coalesce(nullif(p_payload->>'qty_bs_returned','')::integer,v_order.qty_bs_returned);
    if v_total_return>=coalesce(nullif(p_payload->>'qty_sent','')::integer,v_order.qty_sent) then
      raise exception 'Fully reconciled return must use complete_rework_order_v2';
    end if;
    update erp.rework_orders
    set rework_number=coalesce(nullif(btrim(p_payload->>'rework_number'),''),v_order.rework_number),
        bs_case_id=case when p_payload?'bs_case_id' then (p_payload->>'bs_case_id')::uuid else v_order.bs_case_id end,
        destination_type=upper(coalesce(nullif(p_payload->>'destination_type',''),v_order.destination_type)),
        contractor_id=case when p_payload?'contractor_id' then nullif(p_payload->>'contractor_id','')::uuid else v_order.contractor_id end,
        vendor_id=case when p_payload?'vendor_id' then nullif(p_payload->>'vendor_id','')::uuid else v_order.vendor_id end,
        qty_sent=coalesce(nullif(p_payload->>'qty_sent','')::integer,v_order.qty_sent),
        qty_good_returned=coalesce(nullif(p_payload->>'qty_good_returned','')::integer,v_order.qty_good_returned),
        qty_bs_returned=coalesce(nullif(p_payload->>'qty_bs_returned','')::integer,v_order.qty_bs_returned),
        physical_sent_at=coalesce(nullif(p_payload->>'physical_sent_at','')::timestamptz,v_order.physical_sent_at),
        status=case when v_total_return>0 then 'PARTIAL'
                    when upper(coalesce(nullif(p_payload->>'status',''),'OPEN'))='IN_PROGRESS' then 'IN_PROGRESS'
                    else 'OPEN' end,
        return_fg_location_id=case when p_payload?'return_fg_location_id' then nullif(p_payload->>'return_fg_location_id','')::uuid else v_order.return_fg_location_id end,
        notes=case when p_payload?'notes' then nullif(btrim(p_payload->>'notes'),'') else v_order.notes end,
        updated_at=now()
    where id=v_id returning * into v_order;
  end if;

  if p_payload?'components' then
    if jsonb_typeof(p_payload->'components')<>'array' then raise exception 'components must be an array'; end if;
    delete from erp.rework_component_lines where rework_order_id=v_id;
    for v_component in select value from jsonb_array_elements(p_payload->'components') loop
      insert into erp.rework_component_lines(
        rework_order_id,bs_case_component_id,qty_performed,qty_newly_payable,
        rate_snapshot,notes
      ) values(
        v_id,(v_component->>'bs_case_component_id')::uuid,
        (v_component->>'qty_performed')::integer,0,0,
        nullif(btrim(v_component->>'notes'),'')
      );
    end loop;
    update erp.rework_orders set updated_at=now() where id=v_id returning * into v_order;
  end if;
  if v_order.destination_type='CONTRACTOR' and not exists(
    select 1 from erp.rework_component_lines where rework_order_id=v_order.id
  ) then raise exception 'Contractor rework requires at least one component line'; end if;
  perform erp.refresh_bs_case_status(v_order.bs_case_id);
  select * into v_order from erp.rework_orders where id=v_order.id;
  v_response:=jsonb_build_object(
    'rework_order_id',v_order.id,'status',v_order.status,'row_version',v_order.row_version,
    'bs_case_id',v_order.bs_case_id,'components',coalesce((
      select jsonb_agg(jsonb_build_object(
        'rework_component_line_id',l.id,'bs_case_component_id',l.bs_case_component_id,
        'qty_performed',l.qty_performed,'qty_newly_payable',l.qty_newly_payable,
        'rate_snapshot',l.rate_snapshot,'rate_basis',l.rate_basis,
        'source_contractor_rate_id',l.source_contractor_rate_id,
        'source_po_component_snapshot_id',l.source_po_component_snapshot_id
      ) order by l.id) from erp.rework_component_lines l where l.rework_order_id=v_order.id
    ),'[]'::jsonb)
  );
  return erp._idempotency_complete('save_rework_order_v2',p_client_request_id,v_response);
end;
$function$;

alter function "erp"."save_rework_order_v2"(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint) owner to "postgres";
