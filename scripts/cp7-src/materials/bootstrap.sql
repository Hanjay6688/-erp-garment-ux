-- P09 live material/roll bridge; no cached draft quantities are stock.
create role cp7_material_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create role cp7_material_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_material authorization cp7_material_read;
revoke all on schema cp7_material from public,anon,authenticated,service_role;
grant usage,create on schema cp7_material to cp7_material_write;
grant usage on schema erp,auth to cp7_material_read,cp7_material_write;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_material_read,cp7_material_write;
grant select on erp.materials,erp.material_rolls,erp.material_stock_movements,erp.locations,
 erp.bc_accessory_zones_v1,erp.material_purchase_headers,erp.material_purchase_items,erp.material_transfers,erp.material_transfer_items to cp7_material_read;
grant execute on function erp.save_material_transfer_draft_v2(jsonb,uuid,bigint),erp.post_material_transfer_v2(uuid,uuid,bigint,text),
 erp.reverse_material_transfer_v2(uuid,text,uuid,bigint) to cp7_material_write;
create table cp7_material.execution_context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 action text not null check(action in('SAVE_TRANSFER','POST_TRANSFER','REVERSE_TRANSFER')),
 permission_key text not null check(permission_key='warehouse.stock.adjust'),primary key(backend_pid,transaction_id)
);
alter table cp7_material.execution_context owner to cp7_material_write;
alter table cp7_material.execution_context enable row level security;
revoke all on cp7_material.execution_context from public,anon,authenticated,service_role,cp7_capture,cp7_material_read;

create function cp7_material.access_now() returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;adjust boolean;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_MATERIAL_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if (a->>'allowed')::boolean is distinct from true or not erp.has_permission('warehouse.material.view') then
  raise exception using errcode='42501',message='CP7_MATERIAL_ACCESS_DENIED';end if;
 adjust:=erp.has_permission('warehouse.stock.adjust');
 return jsonb_build_object('actor',auth.uid(),'profile',a->'profile','permissions',a->'permissions',
  'can_value',erp.has_permission('finance.hpp.view'),'can_adjust',adjust,
  'can_reverse',adjust and a->'profile'->>'role_code' in('OWNER','ADMIN'));
end $$;

create function cp7_material.validate_lines(p_lines jsonb) returns void
language plpgsql stable security definer set search_path='' as $$
declare line jsonb;
begin
 -- Narrow read authority, not a BYPASSRLS writer. Only the private command
 -- principal can execute this validator; recheck the caller's view grant.
 perform cp7_material.access_now();
 if jsonb_typeof(p_lines) is distinct from 'array' or jsonb_array_length(p_lines) not between 1 and 100 then raise exception 'CP7_MATERIAL_LINES';end if;
 for line in select value from jsonb_array_elements(p_lines) loop
  if jsonb_typeof(line) is distinct from 'object' or not line ?& array['material_id','roll_id','qty']
   or exists(select 1 from jsonb_each(line) e where e.key not in('material_id','roll_id','qty','notes') or jsonb_typeof(e.value) not in('string','null'))
   or line->>'qty' is null or line->>'qty'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$' or (line->>'qty')::numeric<=0 then raise exception 'CP7_MATERIAL_EXACT_LINE';end if;
  if not exists(select 1 from erp.materials m join erp.material_rolls r on r.material_id=m.id
   where m.id=(line->>'material_id')::uuid and r.id=(line->>'roll_id')::uuid and m.material_type='FABRIC') then raise exception 'CP7_MATERIAL_FABRIC_ROLL_REQUIRED';end if;
 end loop;
end $$;
