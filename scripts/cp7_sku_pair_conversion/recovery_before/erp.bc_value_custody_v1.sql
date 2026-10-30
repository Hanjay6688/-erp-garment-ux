CREATE OR REPLACE FUNCTION erp.bc_value_custody_v1(p_payload jsonb, p_request uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare l erp.bc_return_lots_v1%rowtype;s jsonb;v_policy jsonb;v_cond text:=upper(coalesce(p_payload->>'condition',''));v_qty numeric;v_unit numeric;
  v_to uuid;v_at timestamptz;v_adj uuid;v_event uuid;v_avg numeric;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['lot_id','condition','qty','unit_value','location_id','physical_at','reason'],
    array['lot_id','condition','qty','unit_value','location_id','physical_at','reason','responsible','reference'],'valuation payload');
  v_policy:=erp.bc_require_policy_v1('ACC_DEC03','nilai pemulihan barang bekas');
  l:=erp.bc_lock_lot_v1(erp.bc_uuid_v1(p_payload,'lot_id',true));
  if l.value_mode<>'PENDING' then raise exception 'BC_NOT_PENDING_VALUE: hanya barang perusahaan bernilai pending yang dapat dinilai';end if;
  if v_cond not in('USABLE','DAMAGED') then raise exception 'BC_CONDITION_INVALID: nilai hanya untuk barang yang sudah diperiksa (USABLE atau DAMAGED)';end if;
  v_qty:=erp.bc_parse_qty_v1(l.material_id,p_payload->'qty','qty');
  s:=erp.bc_lot_state_v1(l.id);
  if v_qty>(s->>lower(v_cond))::numeric then
    raise exception 'BC_QTY_EXCEEDS_BUCKET: % yang tersedia % , diminta %',v_cond,((s->>lower(v_cond))::numeric)::numeric(18,6),v_qty;end if;
  if jsonb_typeof(p_payload->'unit_value') is distinct from 'string' then raise exception 'BB_AMOUNT_INVALID: unit_value harus nominal tepat dua desimal';end if;
  v_unit:=erp.bb_parse_amount_v1(p_payload->>'unit_value','unit_value');
  if v_policy->>'unit_value_cap'='MOVING_AVERAGE' then
    select moving_average_cost into v_avg from erp.materials where id=l.material_id for update;
    if v_avg is null or v_avg<=0 or v_unit>v_avg then
      raise exception 'BC_VALUE_ABOVE_CAP: nilai pemulihan % melebihi rata-rata biaya barang baru %',v_unit,coalesce(v_avg,0)::numeric(18,6);end if;
  end if;
  v_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),case when v_cond='USABLE' then array['MAIN'] else array['DAMAGED'] end,
    case when v_cond='USABLE' then 'gudang untuk barang layak' else 'area rusak' end);
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if v_at<l.received_at then raise exception 'BC_DATE_BEFORE_SOURCE: penilaian tidak boleh sebelum barang diterima';end if;
  perform erp.bc_new_document_v1(p_request,'VALUE_CUSTODY',v_at,p_payload,jsonb_build_object('ACC_DEC03',erp.bc_policy_version_v1('ACC_DEC03')));
  insert into erp.bc_lot_events_v1(document_id,lot_id,event_kind,condition,qty,event_at,target_location_id,unit_value,amount)
  values(p_request,l.id,'VALUE',v_cond,v_qty,v_at,v_to,v_unit,round(v_qty*v_unit,2)) returning id into v_event;
  v_adj:=erp.bc_post_adjustment_v1(p_request,v_to,v_at,'OTHER',jsonb_build_array(jsonb_build_object('material_id',l.material_id,
    'qty_signed',v_qty::text,'input_unit_cost',v_unit::text)),btrim(p_payload->>'reason'),'RECOVERY_VALUATION',(v_policy->>'credit_account_id')::uuid,'ACC_DEC03');
  perform erp.be_link_recovery_v1(p_request,l.id,erp._cp3_business_date(v_at));
  return jsonb_build_object('event_id',v_event,'adjustment_id',v_adj,'value',round(v_qty*v_unit,2)::text,'lot',erp.bc_lot_state_v1(l.id));
end;$function$
