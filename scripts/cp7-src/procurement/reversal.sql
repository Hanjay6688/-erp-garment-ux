-- The predecessor reverse writer has no version/idempotency entrypoint. This
-- private adapter adds only locking/version admission and outcome identity;
-- all reversal dependencies, physical inverses and journals stay in that writer.
-- Its postgres ownership is necessary to lock the receipt without granting any
-- business SELECT/UPDATE privilege to the public command principal.
create table cp7_procurement.reversals(
 actor uuid not null,request_id uuid not null,payload jsonb not null,expected_version text not null,
 response jsonb,primary key(actor,request_id)
);
alter table cp7_procurement.reversals owner to cp7_procure_write;
alter table cp7_procurement.reversals enable row level security;
revoke all on cp7_procurement.reversals from public,anon,authenticated,service_role,cp7_capture,cp7_procure_read;
create function cp7_procurement.reverse_receipt_locked(p_purchase uuid,p_version bigint,p_reason text) returns jsonb
language plpgsql volatile security definer set search_path='' as $$
declare a jsonb;h erp.material_purchase_headers;
begin
 a:=cp7_procurement.access_now();
 if a->'can_reverse' is distinct from 'true'::jsonb or (a->'profile'->>'role_code' in('OWNER','ADMIN')) is distinct from true then raise exception using errcode='42501',message='CP7_PROCUREMENT_REVERSE_DENIED';end if;
 if p_version is null or p_purchase is null or nullif(btrim(p_reason),'') is null then raise exception 'CP7_PROCUREMENT_REVERSE_FIELDS';end if;
 select * into h from erp.material_purchase_headers where id=p_purchase for update;
 if not found then raise exception 'CP7_PROCUREMENT_NOT_FOUND';end if;
 if h.row_version<>p_version then raise exception 'STALE_VERSION expected %, current %',p_version,h.row_version;end if;
 if h.status<>'POSTED' then raise exception 'CP7_PROCUREMENT_POSTED_RECEIPT_REQUIRED';end if;
 if cp7_procurement.access_now()<>a then raise exception using errcode='42501',message='CP7_PROCUREMENT_ACCESS_CHANGED';end if;
 perform erp.reverse_material_purchase(p_purchase,p_reason);
 select * into h from erp.material_purchase_headers where id=p_purchase;
 if cp7_procurement.access_now()<>a then raise exception using errcode='42501',message='CP7_PROCUREMENT_ACCESS_CHANGED';end if;
 return jsonb_build_object('purchase_id',h.id,'status',h.status,'row_version',h.row_version::text);
end $$;
alter function cp7_procurement.reverse_receipt_locked(uuid,bigint,text) owner to postgres;
create function cp7_procurement.reverse_request(p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;old cp7_procurement.reversals;r jsonb;
begin
 a:=cp7_procurement.access_now();
 if a->'can_reverse' is distinct from 'true'::jsonb or (a->'profile'->>'role_code' in('OWNER','ADMIN')) is distinct from true then raise exception using errcode='42501',message='CP7_PROCUREMENT_REVERSE_DENIED';end if;
 perform cp7_procurement.fields(p_payload,array['purchase_id','change_reason'],array['purchase_id','change_reason']);
 if p_expected is null or p_request is null or exists(select 1 from jsonb_each(p_payload) e where jsonb_typeof(e.value)<>'string' or nullif(btrim(e.value#>>'{}'),'') is null) then raise exception 'CP7_PROCUREMENT_REVERSE_FIELDS';end if;
 insert into cp7_procurement.reversals(actor,request_id,payload,expected_version) values(auth.uid(),p_request,p_payload,p_expected) on conflict do nothing;
 select * into old from cp7_procurement.reversals where actor=auth.uid() and request_id=p_request for update;
 if old.payload<>p_payload or old.expected_version<>p_expected then raise exception 'CP7_PROCUREMENT_REVERSE_REQUEST_CHANGED';end if;
 if cp7_procurement.access_now()<>a then raise exception using errcode='42501',message='CP7_PROCUREMENT_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 r:=cp7_procurement.reverse_receipt_locked((p_payload->>'purchase_id')::uuid,p_expected::bigint,p_payload->>'change_reason');
 r:=jsonb_build_object('contract_version','cp7.procurement-outcome.v1','kind','COMMITTED_OUTCOME','action','REVERSE','request_id',p_request,
  'purchase_id',r->'purchase_id','status',r->>'status','row_version',r->>'row_version');
 update cp7_procurement.reversals set response=r where actor=auth.uid() and request_id=p_request;
 return r;
end $$;
