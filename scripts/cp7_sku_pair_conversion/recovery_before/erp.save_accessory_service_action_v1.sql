CREATE OR REPLACE FUNCTION erp.save_accessory_service_action_v1(p_action text, p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
 SET "DateStyle" TO 'ISO, YMD'
AS $function$
declare v_action text:=upper(btrim(coalesce(p_action,'')));v_cached jsonb;v_result jsonb;v_doc uuid;
begin
  perform erp.require_permission('warehouse.accessory.view');
  if v_action not in('SET_POLICY','REGISTER_ZONE','FILL_POST','RETURN_TO_WAREHOUSE','INTERNAL_USE','RECEIVE_RETURN','INSPECT','VALUE_CUSTODY',
      'CREDIT_NOTE_RETURN','ALLOCATE_CARRY','DISPOSE_STOCK','CLOSE_CUSTODY','CUSTOMER_GARMENT_IN','CUSTOMER_GARMENT_OUT','COUNT_POST',
      'RESOLVE_VARIANCE','ROUND_NOTE','REVERSE') then
    raise exception 'BC_ACTION_UNKNOWN: tindakan aksesori tidak dikenal';end if;
  if v_action in('FILL_POST','RETURN_TO_WAREHOUSE','INTERNAL_USE','RECEIVE_RETURN','INSPECT','CLOSE_CUSTODY','DISPOSE_STOCK','CUSTOMER_GARMENT_IN',
      'CUSTOMER_GARMENT_OUT','COUNT_POST','RESOLVE_VARIANCE','REVERSE') then
    perform erp.require_permission('warehouse.stock.adjust');
  end if;
  if v_action='REVERSE' then
    begin perform erp.require_owner_admin();
    exception when others then raise exception 'BC_APPROVAL_REQUIRED: pembatalan memerlukan owner/admin';end;
  end if;
  perform erp.require_internal();
  if p_client_request_id is null then raise exception 'BC_REQUEST_ID_REQUIRED: request id wajib';end if;
  if jsonb_typeof(p_payload) is distinct from 'object' or octet_length(p_payload::text)>20000 then raise exception 'BC_PAYLOAD_INVALID: data tidak valid';end if;
  v_cached:=erp._idempotency_begin('save_accessory_service_action_v1',p_client_request_id,
    erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));
  if v_cached is not null then return v_cached;end if;
  if exists(select 1 from erp.bc_documents_v1 where id=p_client_request_id) then raise exception 'BC_REQUEST_REUSED: request id sudah dipakai';end if;
  perform set_config('app.change_reason',coalesce(nullif(btrim(p_payload->>'reason'),''),v_action),true);
  perform erp.bc_enter_context_v1();
  v_result:=case v_action
    when 'SET_POLICY' then erp.bc_set_policy_v1(p_payload,p_client_request_id)
    when 'REGISTER_ZONE' then erp.bc_register_zone_v1(p_payload,p_client_request_id)
    when 'FILL_POST' then erp.bc_move_post_v1(v_action,p_payload,p_client_request_id)
    when 'RETURN_TO_WAREHOUSE' then erp.bc_move_post_v1(v_action,p_payload,p_client_request_id)
    when 'INTERNAL_USE' then erp.bc_internal_use_v1(p_payload,p_client_request_id)
    when 'RECEIVE_RETURN' then erp.bc_receive_return_v1(p_payload,p_client_request_id)
    when 'INSPECT' then erp.bc_inspect_v1(p_payload,p_client_request_id)
    when 'VALUE_CUSTODY' then erp.bc_value_custody_v1(p_payload,p_client_request_id)
    when 'CREDIT_NOTE_RETURN' then erp.bc_credit_note_return_v1(p_payload,p_client_request_id)
    when 'ALLOCATE_CARRY' then erp.bc_allocate_carry_v1(p_payload,p_client_request_id)
    when 'DISPOSE_STOCK' then erp.bc_dispose_stock_v1(p_payload,p_client_request_id)
    when 'CLOSE_CUSTODY' then erp.bc_close_custody_v1(p_payload,p_client_request_id)
    when 'CUSTOMER_GARMENT_IN' then erp.bc_customer_garment_v1(v_action,p_payload,p_client_request_id)
    when 'CUSTOMER_GARMENT_OUT' then erp.bc_customer_garment_v1(v_action,p_payload,p_client_request_id)
    when 'COUNT_POST' then erp.bc_count_post_v1(p_payload,p_client_request_id)
    when 'RESOLVE_VARIANCE' then erp.bc_resolve_variance_v1(p_payload,p_client_request_id)
    when 'ROUND_NOTE' then erp.bc_round_note_v1(p_payload,p_client_request_id)
    else erp.bc_reverse_v1(p_payload,p_client_request_id) end;
  perform erp.bc_leave_context_v1();
  v_doc:=case when v_action='REVERSE' then (v_result->>'reversed_document_id')::uuid
    when v_action in('SET_POLICY','REGISTER_ZONE') then null else p_client_request_id end;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values(case when v_action='SET_POLICY' then 'bc_policy_settings_v1' when v_action='REGISTER_ZONE' then 'bc_accessory_zones_v1' else 'bc_documents_v1' end,
    coalesce(v_doc,p_client_request_id),case when v_action='REVERSE' then 'REVERSE' else 'INSERT' end,
    jsonb_build_object('action',v_action,'result',v_result),erp.current_app_user_id(),coalesce(nullif(btrim(p_payload->>'reason'),''),v_action));
  v_result:=v_result||jsonb_build_object('request_id',p_client_request_id,'action',v_action,'document_id',v_doc,
    'status',case when v_action='REVERSE' then 'REVERSED' when v_action in('SET_POLICY','REGISTER_ZONE') then 'SAVED' else 'POSTED' end,
    'row_version',case when v_action='REVERSE' then v_result->>'row_version' when v_doc is not null then
      (select row_version::text from erp.bc_documents_v1 where id=v_doc) end);
  return erp._idempotency_complete('save_accessory_service_action_v1',p_client_request_id,v_result);
end;$function$
