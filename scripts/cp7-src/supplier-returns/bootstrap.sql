-- P09 source-linked physical supplier returns. Price/AP/GRNI stay in the
-- accepted return writers; the browser may never supply a credit valuation.
create role cp7_return_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create role cp7_return_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_supplier_return authorization cp7_return_read;
revoke all on schema cp7_supplier_return from public,anon,authenticated,service_role;
grant usage,create on schema cp7_supplier_return to cp7_return_write;
grant usage on schema erp,auth to cp7_return_read,cp7_return_write;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_return_read,cp7_return_write;
grant select on erp.material_purchase_headers,erp.material_purchase_items,erp.material_rolls,erp.materials,erp.locations,
 erp.bc_accessory_zones_v1,erp.material_stock_movements,erp.material_supplier_returns,erp.material_supplier_return_items,erp.suppliers to cp7_return_read;
grant execute on function erp.save_material_supplier_return_draft_v2(jsonb,uuid,bigint),erp.post_material_supplier_return_v2(uuid,uuid,bigint,text),
 erp.reverse_material_supplier_return_v2(uuid,text,uuid,bigint) to cp7_return_write;
create table cp7_supplier_return.execution_context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 action text not null check(action in('SAVE','POST','REVERSE')),
 permission_key text not null check(permission_key in('warehouse.procurement.create','warehouse.procurement.reverse')),
 primary key(backend_pid,transaction_id)
);
alter table cp7_supplier_return.execution_context owner to cp7_return_write;
alter table cp7_supplier_return.execution_context enable row level security;
revoke all on cp7_supplier_return.execution_context from public,anon,authenticated,service_role,cp7_capture,cp7_return_read;
-- Bind the complete outer intent before inspecting mutable receipt/draft
-- membership. Replaying a known SAVE after later correction returns its original
-- outcome, then the caller separately reloads current business state.
create table cp7_supplier_return.requests(
 actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,
 expected_version text,response jsonb,primary key(actor,request_id)
);
alter table cp7_supplier_return.requests owner to cp7_return_write;
alter table cp7_supplier_return.requests enable row level security;
revoke all on cp7_supplier_return.requests from public,anon,authenticated,service_role,cp7_capture,cp7_return_read;
create function cp7_supplier_return.access_now() returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_RETURN_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if (a->>'allowed')::boolean is distinct from true or not erp.has_permission('warehouse.procurement.view') then raise exception using errcode='42501',message='CP7_RETURN_ACCESS_DENIED';end if;
 return jsonb_build_object('actor',auth.uid(),'profile',a->'profile','permissions',a->'permissions','view_value',erp.has_permission('finance.ap.view'),
  'create',erp.has_permission('warehouse.procurement.create'),'post',erp.has_permission('warehouse.procurement.reverse'),
  'reverse',erp.has_permission('warehouse.procurement.reverse') and a->'profile'->>'role_code' in('OWNER','ADMIN'));
end $$;

create function cp7_supplier_return.validate_source(p_purchase uuid,p_payload jsonb) returns void
language plpgsql stable security definer set search_path='' as $$
declare l jsonb;
begin
 perform cp7_supplier_return.access_now();
 if not exists(select 1 from erp.material_purchase_headers where id=p_purchase and status='POSTED' and supplier_id=(p_payload->>'supplier_id')::uuid) then raise exception 'CP7_RETURN_POSTED_SOURCE_REQUIRED';end if;
 if jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 100 then raise exception 'CP7_RETURN_LINES';end if;
 for l in select value from jsonb_array_elements(p_payload->'items') loop
  if jsonb_typeof(l) is distinct from 'object' or not l ?& array['purchase_item_id','material_id','roll_id','qty'] or exists(select 1 from jsonb_each(l) e
   where e.key not in('purchase_item_id','material_id','roll_id','qty','notes') or jsonb_typeof(e.value) not in('string','null')) then raise exception 'CP7_RETURN_LINE_FIELDS';end if;
  if l->>'qty' is null or l->>'qty'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$' or (l->>'qty')::numeric<=0 then raise exception 'CP7_RETURN_EXACT_QUANTITY';end if;
  if not exists(select 1 from erp.material_purchase_items i join erp.materials m on m.id=i.material_id where i.id=(l->>'purchase_item_id')::uuid and i.purchase_id=p_purchase and i.material_id=(l->>'material_id')::uuid
    and ((m.material_type='FABRIC' and exists(select 1 from erp.material_rolls r where r.id=(l->>'roll_id')::uuid and r.material_id=i.material_id and r.purchase_item_id=i.id)) or (m.material_type<>'FABRIC' and l->>'roll_id' is null))) then raise exception 'CP7_RETURN_SOURCE_LINEAGE';end if;
 end loop;
end $$;
create function cp7_supplier_return.assert_document(p_purchase uuid,p_return uuid) returns void
language plpgsql stable security definer set search_path='' as $$
begin
 perform cp7_supplier_return.access_now();
 if not exists(select 1 from erp.material_supplier_return_items r join erp.material_purchase_items i on i.id=r.purchase_item_id where r.return_id=p_return and i.purchase_id=p_purchase)
  or exists(select 1 from erp.material_supplier_return_items r left join erp.material_purchase_items i on i.id=r.purchase_item_id where r.return_id=p_return and i.purchase_id is distinct from p_purchase) then raise exception 'CP7_RETURN_COMPLETE_SOURCE_DOCUMENT_REQUIRED';end if;
end $$;
-- Validate the physical source at both sides of the accepted POST's waits.
-- Reversal deliberately remains possible after a master is deactivated.
create function cp7_supplier_return.validate_post(p_purchase uuid,p_return uuid) returns void
language plpgsql stable security definer set search_path='' as $$
begin
 perform cp7_supplier_return.access_now();
 perform cp7_supplier_return.assert_document(p_purchase,p_return);
 if not exists(select 1 from erp.material_supplier_returns h join erp.locations l on l.id=h.location_id where h.id=p_return and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=l.id)) then raise exception 'CP7_RETURN_ACTIVE_WAREHOUSE_REQUIRED';end if;
 if exists(select 1 from erp.material_supplier_return_items r join erp.materials m on m.id=r.material_id where r.return_id=p_return and not m.is_active) then raise exception 'CP7_RETURN_ACTIVE_MATERIAL_REQUIRED';end if;
 if (select count(*) from erp.material_supplier_return_items where return_id=p_return)>100 then raise exception 'CP7_RETURN_COMPLETE_DOCUMENT_REQUIRED';end if;
end $$;
