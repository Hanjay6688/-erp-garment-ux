-- P09 development bridge. Reads and commands use separate principals; analysis
-- roles never acquire access to purchase/stock writers.
create role cp7_procure_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create role cp7_procure_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_procurement authorization cp7_procure_read;
revoke all on schema cp7_procurement from public,anon,authenticated,service_role;
grant usage on schema cp7_procurement to cp7_procure_write;
grant usage on schema erp,auth to cp7_procure_read,cp7_procure_write;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_procure_read,cp7_procure_write;
grant select on erp.material_purchase_headers,erp.material_purchase_items,erp.material_rolls,
 erp.materials,erp.suppliers,erp.locations,erp.material_stock_movements to cp7_procure_read;
grant execute on function erp.save_material_purchase_draft_v2(jsonb,uuid,bigint),
 erp.post_material_purchase_v2(uuid,uuid,bigint,text) to cp7_procure_write;

create function cp7_procurement.access_now() returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then
  raise exception using errcode='42501',message='CP7_PROCUREMENT_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if (a->>'allowed')::boolean is distinct from true or not erp.has_permission('warehouse.procurement.view') then
  raise exception using errcode='42501',message='CP7_PROCUREMENT_ACCESS_DENIED';end if;
 return jsonb_build_object('actor',auth.uid(),'profile',a->'profile','permissions',a->'permissions',
  'can_value',erp.has_permission('finance.ap.view'),'can_create',erp.has_permission('warehouse.procurement.create'),
  'can_post',erp.has_permission('warehouse.procurement.post'),'can_reverse',erp.has_permission('warehouse.procurement.reverse'));
end $$;
create function cp7_procurement.fields(v jsonb,allowed text[],required text[]) returns void
language plpgsql immutable security invoker set search_path='' as $$
begin
 if jsonb_typeof(v) is distinct from 'object' or not v ?& required or exists(select 1 from jsonb_object_keys(v) k where not k=any(allowed)) then
  raise exception using errcode='22023',message='CP7_PROCUREMENT_FIELDS';end if;
end $$;
create function cp7_procurement.decimal(v jsonb,positive boolean) returns text
language plpgsql immutable security invoker set search_path='' as $$
begin
 if jsonb_typeof(v) is distinct from 'string' or (v#>>'{}') !~ '^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$'
  or (positive and (v#>>'{}')::numeric<=0) then raise exception 'CP7_PROCUREMENT_EXACT_DECIMAL';end if;
 return v#>>'{}';
end $$;
