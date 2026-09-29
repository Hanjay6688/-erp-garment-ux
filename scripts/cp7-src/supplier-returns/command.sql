create function cp7_supplier_return.command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;z jsonb;r jsonb;pid uuid;expected bigint;permission_key text;capability text;cached cp7_supplier_return.requests;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_supplier_return.access_now();
 if p_action is null or p_action not in('SAVE','POST','REVERSE') or p_request is null then raise exception 'CP7_RETURN_ACTION';end if;
 if jsonb_typeof(p_payload) is distinct from 'object' or jsonb_typeof(p_payload->'purchase_id') is distinct from 'string' then raise exception 'CP7_RETURN_FIELDS';end if;
 pid:=(p_payload->>'purchase_id')::uuid;
 if p_expected is not null and p_expected!~'^[1-9][0-9]{0,18}$' then raise exception 'CP7_RETURN_VERSION';end if;expected:=p_expected::bigint;
 capability:=case p_action when 'SAVE' then 'create' when 'POST' then 'post' else 'reverse' end;
 permission_key:=case p_action when 'SAVE' then 'warehouse.procurement.create' else 'warehouse.procurement.reverse' end;
 if a->capability is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_RETURN_ACTION_DENIED';end if;
 insert into cp7_supplier_return.requests(actor,request_id,action,payload,expected_version) values(auth.uid(),p_request,p_action,p_payload,p_expected) on conflict do nothing;
 select * into cached from cp7_supplier_return.requests where actor=auth.uid() and request_id=p_request for update;
 if cached.action<>p_action or cached.payload<>p_payload or cached.expected_version is distinct from p_expected then raise exception 'CP7_RETURN_REQUEST_PAYLOAD_CHANGED';end if;
 z:=cp7_supplier_return.access_now();if z<>a then raise exception using errcode='42501',message='CP7_RETURN_ACCESS_CHANGED';end if;
 if cached.response is not null then return cached.response;end if;
 if p_action='SAVE' then
  if not p_payload ?& array['purchase_id','return_number','supplier_id','location_id','physical_at','change_reason','items'] or exists(select 1 from jsonb_each(p_payload) e where e.key not in('purchase_id','id','return_number','supplier_id','location_id','physical_at','change_reason','reason','items') or (e.key<>'items' and jsonb_typeof(e.value) not in('string','null'))) then raise exception 'CP7_RETURN_FIELDS';end if;
  if exists(select 1 from unnest(array['purchase_id','return_number','supplier_id','location_id','physical_at','change_reason']) k where jsonb_typeof(p_payload->k) is distinct from 'string' or nullif(btrim(p_payload->>k),'') is null) then raise exception 'CP7_RETURN_FIELDS';end if;
  if p_payload->>'id' is not null then perform cp7_supplier_return.assert_document(pid,(p_payload->>'id')::uuid);end if;
  perform cp7_supplier_return.validate_source(pid,p_payload);
 else
  if p_expected is null or not p_payload ?& array['purchase_id','return_id','change_reason'] or exists(select 1 from jsonb_each(p_payload) e where e.key not in('purchase_id','return_id','change_reason') or jsonb_typeof(e.value)<>'string') then raise exception 'CP7_RETURN_FIELDS';end if;
  perform cp7_supplier_return.assert_document(pid,(p_payload->>'return_id')::uuid);
  if p_action='POST' then perform cp7_supplier_return.validate_post(pid,(p_payload->>'return_id')::uuid);end if;
 end if;
 insert into cp7_supplier_return.execution_context values(pg_backend_pid(),txid_current(),auth.uid(),p_action,permission_key);
 if p_action='SAVE' then r:=erp.save_material_supplier_return_draft_v2(p_payload-'purchase_id',p_request,expected);
 elsif p_action='POST' then r:=erp.post_material_supplier_return_v2((p_payload->>'return_id')::uuid,p_request,expected,p_payload->>'change_reason');
 else r:=erp.reverse_material_supplier_return_v2((p_payload->>'return_id')::uuid,p_payload->>'change_reason',p_request,expected);end if;
 z:=cp7_supplier_return.access_now();if z<>a then raise exception using errcode='42501',message='CP7_RETURN_ACCESS_CHANGED';end if;
 if p_action='POST' then perform cp7_supplier_return.validate_post(pid,(p_payload->>'return_id')::uuid);end if;
 delete from cp7_supplier_return.execution_context where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 r:=jsonb_build_object('contract_version','cp7.supplier-return-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'purchase_id',pid,
  'return_id',r->'material_supplier_return_id','row_version',r->>'row_version','status',r->>'status');
 update cp7_supplier_return.requests set response=r where actor=auth.uid() and request_id=p_request;
 return r;
end $$;
create function public.erp_cp7_save_supplier_return_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_supplier_return.command(p_action,p_payload,p_request,p_expected)$$;
