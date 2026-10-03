-- "Benerin nama bahan": a typo in a material's name or code (SKU) is fixed on
-- the same material. Only material_name/material_sku change; type, unit,
-- accessory category, active state, stock, cost and every roll/movement keep
-- their identity and history. A receipt recorded under a different material is not a typo: it is
-- corrected with "Benerin penerimaan" (wrong material A -> B).
create table cp7_receipt_fix.name_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,expected_version text not null,
 response jsonb,primary key(actor,request_id)
);
create table cp7_receipt_fix.material_names(
 id uuid primary key default gen_random_uuid(),
 material_id uuid not null references erp.materials,
 previous_name text not null,corrected_name text not null,previous_sku text not null,corrected_sku text not null,reason text not null,
 actor uuid not null,request_id uuid not null,recorded_at timestamptz not null default clock_timestamp(),
 unique(actor,request_id)
);
create index receipt_fix_material_names on cp7_receipt_fix.material_names(material_id,recorded_at);
do $own$
declare t text;
begin
 foreach t in array array['name_requests','material_names']loop
  execute format('alter table cp7_receipt_fix.%I owner to postgres',t);
  execute format('alter table cp7_receipt_fix.%I enable row level security',t);
  execute format('create policy private_%s on cp7_receipt_fix.%I for all using(false)with check(false)',t,t);
 end loop;
end $own$;
revoke all on cp7_receipt_fix.name_requests,cp7_receipt_fix.material_names from public,anon,authenticated,service_role,cp7_capture;
create trigger immutable_material_name before update or delete on cp7_receipt_fix.material_names for each row execute function cp7_receipt_fix.immutable();

-- Current authority for one material: OWNER/ADMIN with the master permission
-- of the material's own kind.
create function cp7_receipt_fix.name_access(p_type text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'
  then raise exception using errcode='42501',message='CP7_MATERIAL_NAME_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or erp.has_permission('warehouse.material.view')is distinct from true then
  raise exception using errcode='42501',message='CP7_MATERIAL_NAME_ACCESS_DENIED';end if;
 if coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')then
  raise exception using errcode='42501',message='CP7_MATERIAL_NAME_OWNER_ADMIN_REQUIRED';end if;
 if erp.has_permission(case when p_type='ACCESSORY'then 'master.accessory.manage'else 'master.fabric.manage'end)is distinct from true then
  raise exception using errcode='42501',message='CP7_MATERIAL_NAME_ACCESS_DENIED';end if;
 return a;
end $$;

create function cp7_receipt_fix.identity(p_material uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select jsonb_build_object('sku',m.material_sku,'type',m.material_type,'unit',m.unit_code,'category',m.accessory_category_id,'active',m.is_active,
  'cost',m.moving_average_cost::text,'stock',m.cached_stock_qty::text,
  'profile',(select to_jsonb(p)-array['updated_at','updated_by']from erp.fabric_master_profiles p where p.material_id=m.id),
  'rolls',(select count(*)from erp.material_rolls r where r.material_id=m.id),'movements',(select count(*)from erp.material_stock_movements s where s.material_id=m.id))
 from erp.materials m where m.id=p_material$$;

create function cp7_receipt_fix.name_workspace(p_material uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare m erp.materials%rowtype;a jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 select*into m from erp.materials where id=p_material;
 if m.id is null then raise exception 'CP7_MATERIAL_NAME_NOT_FOUND';end if;
 a:=cp7_receipt_fix.name_access(m.material_type);
 return jsonb_build_object('contract_version','cp7.material-name-workspace.v1','read_at',clock_timestamp(),
  'material_id',m.id,'material_sku',m.material_sku,'material_name',m.material_name,'material_type',m.material_type,'unit_code',m.unit_code,
  'row_version',m.row_version::text,
  'history',(select coalesce(jsonb_agg(jsonb_build_object('id',h.id,'previous_name',h.previous_name,'corrected_name',h.corrected_name,
    'previous_sku',h.previous_sku,'corrected_sku',h.corrected_sku,'reason',h.reason,
    'recorded_at',h.recorded_at,'actor_id',h.actor,
    'actor_display_name',(select nullif(btrim(u.full_name),'')from erp.app_users u where u.auth_user_id=h.actor),'actor_name_basis','CURRENT_PROFILE')order by h.recorded_at,h.id),'[]')
   from cp7_receipt_fix.material_names h where h.material_id=m.id),
  'production_go',false);
end $$;

create function cp7_receipt_fix.rename(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;old cp7_receipt_fix.name_requests%rowtype;m erp.materials%rowtype;before jsonb;name text;sku text;why text;result jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if jsonb_typeof(p_payload)is distinct from'object'or not p_payload?&array['material_id','material_name','change_reason']
  or exists(select 1 from jsonb_object_keys(p_payload)k where k not in('material_id','material_name','material_sku','change_reason'))
  or exists(select 1 from jsonb_each(p_payload)e where jsonb_typeof(e.value)<>'string')
  or p_payload->>'material_id'!~'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
 then raise exception using errcode='22023',message='CP7_MATERIAL_NAME_FIELDS';end if;
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_MATERIAL_NAME_REQUEST_REQUIRED';end if;
 name:=regexp_replace(btrim(p_payload->>'material_name'),'\s+',' ','g');why:=btrim(p_payload->>'change_reason');
 if length(name)not between 1 and 150 then raise exception using errcode='22023',message='CP7_MATERIAL_NAME_LENGTH';end if;
 if length(why)not between 5 and 500 then raise exception using errcode='22023',message='CP7_MATERIAL_NAME_REASON_REQUIRED';end if;
 if p_payload?'material_sku'and length(btrim(p_payload->>'material_sku'))not between 1 and 60 then raise exception using errcode='22023',message='CP7_MATERIAL_NAME_SKU_LENGTH';end if;
 select*into m from erp.materials where id=(p_payload->>'material_id')::uuid for update;
 if m.id is null then raise exception 'CP7_MATERIAL_NAME_NOT_FOUND';end if;
 a:=cp7_receipt_fix.name_access(m.material_type);
 insert into cp7_receipt_fix.name_requests values(auth.uid(),p_request,p_payload,p_expected,null)on conflict do nothing;
 select*into strict old from cp7_receipt_fix.name_requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_MATERIAL_NAME_REQUEST_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 if m.row_version::text<>p_expected then raise exception 'CP7_MATERIAL_NAME_REVIEW_CHANGED';end if;
 sku:=coalesce(btrim(p_payload->>'material_sku'),m.material_sku);
 if name=m.material_name and sku=m.material_sku then raise exception 'CP7_MATERIAL_NAME_UNCHANGED';end if;
 -- The same name or code on another material means two records of one
 -- material (identity), not a typo; it is never merged here.
 if name<>m.material_name and exists(select 1 from erp.materials x where x.id<>m.id and lower(x.material_name)=lower(name))then
  raise exception 'CP7_MATERIAL_NAME_TAKEN';end if;
 if sku<>m.material_sku and exists(select 1 from erp.materials x where x.id<>m.id and lower(x.material_sku)=lower(sku))then
  raise exception 'CP7_MATERIAL_NAME_SKU_TAKEN';end if;
 before:=cp7_receipt_fix.identity(m.id)-'sku';
 perform set_config('app.change_reason','Benerin nama bahan: '||why,true);
 update erp.materials set material_name=name,material_sku=sku where id=m.id;
 if cp7_receipt_fix.identity(m.id)-'sku'is distinct from before or cp7_receipt_fix.identity(m.id)->>'sku'is distinct from sku then
  raise exception 'CP7_MATERIAL_NAME_IDENTITY_CHANGED';end if;
 insert into cp7_receipt_fix.material_names(material_id,previous_name,corrected_name,previous_sku,corrected_sku,reason,actor,request_id)
 values(m.id,m.material_name,name,m.material_sku,sku,why,auth.uid(),p_request);
 if cp7_receipt_fix.name_access(m.material_type)is distinct from a then raise exception using errcode='42501',message='CP7_MATERIAL_NAME_ACCESS_CHANGED';end if;
 result:=jsonb_build_object('contract_version','cp7.material-name-outcome.v1','kind','COMMITTED_OUTCOME','action','RENAME','request_id',p_request,
  'material_id',m.id,'previous_name',m.material_name,'material_name',name,'previous_sku',m.material_sku,'material_sku',sku,'row_version',(select row_version::text from erp.materials where id=m.id));
 update cp7_receipt_fix.name_requests set response=result where actor=auth.uid()and request_id=p_request;
 return result;
end $$;

do $own$
declare f text;
begin
 foreach f in array array['name_access(text)','identity(uuid)','name_workspace(uuid)','rename(jsonb,uuid,text)']loop
  execute 'alter function cp7_receipt_fix.'||f||' owner to postgres';
 end loop;
end $own$;
revoke all on function cp7_receipt_fix.name_access(text),cp7_receipt_fix.identity(uuid),cp7_receipt_fix.name_workspace(uuid),cp7_receipt_fix.rename(jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_procure_read,cp7_procure_write;
grant execute on function cp7_receipt_fix.name_workspace(uuid),cp7_receipt_fix.rename(jsonb,uuid,text)to cp7_procure_write;
create function public.erp_cp7_get_material_name_v1(p_material uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_receipt_fix.name_workspace(p_material)$$;
create function public.erp_cp7_rename_material_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_receipt_fix.rename(p_payload,p_request,p_expected)$$;
grant create on schema public to cp7_procure_write;
alter function public.erp_cp7_get_material_name_v1(uuid)owner to cp7_procure_write;
alter function public.erp_cp7_rename_material_v1(jsonb,uuid,text)owner to cp7_procure_write;
revoke create on schema public from cp7_procure_write;
revoke all on function public.erp_cp7_get_material_name_v1(uuid),public.erp_cp7_rename_material_v1(jsonb,uuid,text)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_material_name_v1(uuid),public.erp_cp7_rename_material_v1(jsonb,uuid,text)to authenticated;
