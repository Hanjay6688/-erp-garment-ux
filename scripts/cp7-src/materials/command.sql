-- Existing stock-adjust authority is conservative for transfers. Reversal also
-- retains the accepted OWNER/ADMIN guard. No new default permission is created.
create function cp7_material.command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;z jsonb;r jsonb;expected bigint;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_material.access_now();
 if a->'can_adjust'<>'true'::jsonb then raise exception using errcode='42501',message='CP7_MATERIAL_ADJUST_DENIED';end if;
 if p_request is null or p_action is null or p_action not in('SAVE_TRANSFER','POST_TRANSFER','REVERSE_TRANSFER') then raise exception 'CP7_MATERIAL_ACTION';end if;
 if p_expected is not null and p_expected!~'^[1-9][0-9]{0,18}$' then raise exception 'CP7_MATERIAL_VERSION';end if;
 expected:=p_expected::bigint;
 if jsonb_typeof(p_payload) is distinct from 'object' then raise exception 'CP7_MATERIAL_FIELDS';end if;
 if p_action='SAVE_TRANSFER' then
  if not p_payload ?& array['transfer_number','from_location_id','to_location_id','physical_at','change_reason','items']
   or exists(select 1 from jsonb_each(p_payload) e where e.key not in('id','transfer_number','from_location_id','to_location_id','physical_at','change_reason','items','notes')
    or(e.key<>'items' and jsonb_typeof(e.value) not in('string','null'))) then raise exception 'CP7_MATERIAL_FIELDS';end if;
  if nullif(p_payload->>'from_location_id','') is null or nullif(p_payload->>'to_location_id','') is null
   or p_payload->>'from_location_id'=p_payload->>'to_location_id' then raise exception 'CP7_MATERIAL_DIFFERENT_LOCATIONS_REQUIRED';end if;
  perform cp7_material.validate_lines(p_payload->'items');
  insert into cp7_material.execution_context values(pg_backend_pid(),txid_current(),auth.uid(),p_action,'warehouse.stock.adjust');
  r:=erp.save_material_transfer_draft_v2(p_payload,p_request,expected);
 else
  if expected is null then raise exception 'CP7_MATERIAL_VERSION';end if;
  if not p_payload ?& array['transfer_id','change_reason'] or exists(select 1 from jsonb_each(p_payload) e
   where e.key not in('transfer_id','change_reason') or jsonb_typeof(e.value)<>'string') then raise exception 'CP7_MATERIAL_FIELDS';end if;
  insert into cp7_material.execution_context values(pg_backend_pid(),txid_current(),auth.uid(),p_action,'warehouse.stock.adjust');
  if p_action='POST_TRANSFER' then r:=erp.post_material_transfer_v2((p_payload->>'transfer_id')::uuid,p_request,expected,p_payload->>'change_reason');
  else
   if a->'can_reverse' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_MATERIAL_REVERSE_DENIED';end if;
   r:=erp.reverse_material_transfer_v2((p_payload->>'transfer_id')::uuid,p_payload->>'change_reason',p_request,expected);
  end if;
 end if;
 z:=cp7_material.access_now();
 if z<>a then raise exception using errcode='42501',message='CP7_MATERIAL_ACCESS_CHANGED';end if;
 delete from cp7_material.execution_context where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 return jsonb_build_object('contract_version','cp7.material-outcome.v1','kind','COMMITTED_OUTCOME',
  'action',p_action,'request_id',p_request,'transfer_id',r->'material_transfer_id','status',r->'status','row_version',r->>'row_version');
end $$;

create function public.erp_cp7_save_materials_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_material.command(p_action,p_payload,p_request,p_expected)$$;
