-- Purchase-unit selection is a dated master read. Native accessory triggers
-- remain the only conversion/price calculation authority.
grant select on erp.accessory_categories,erp.accessory_category_uom_conversions,erp.uom_definitions to cp7_procure_read;
create function cp7_procurement.uom_options(p_material uuid,p_at timestamptz) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;m erp.materials;cat erp.accessory_categories;rows jsonb;
begin
 a:=cp7_procurement.access_now();
 if p_at is null or p_material is null then raise exception 'CP7_PROCUREMENT_UOM_TIME_MATERIAL';end if;
 select * into m from erp.materials where id=p_material and is_active;
 if not found or m.material_type<>'ACCESSORY' then raise exception 'CP7_PROCUREMENT_ACCESSORY_REQUIRED';end if;
 select * into cat from erp.accessory_categories where id=m.accessory_category_id and is_active;
 if not found or cat.base_uom_code<>m.unit_code then raise exception 'CP7_PROCUREMENT_ACCESSORY_CATEGORY';end if;
 if not exists(select 1 from erp.uom_definitions where unit_code=m.unit_code and is_active) then raise exception 'CP7_PROCUREMENT_ACTIVE_BASE_UOM_REQUIRED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('code',upper(x.unit_code),'name',x.unit_name,'factor',x.factor::text,'dimension',x.dimension) order by x.base_first,x.unit_code),'[]'::jsonb) into rows
 from (
  select u.unit_code,u.unit_name,u.dimension,1::numeric factor,0 base_first from erp.uom_definitions u where u.unit_code=m.unit_code and u.is_active
  union all
  select u.unit_code,u.unit_name,u.dimension,c.base_qty_per_uom,1 from erp.accessory_category_uom_conversions c join erp.uom_definitions u on upper(u.unit_code)=upper(c.uom_code)
   where c.category_id=cat.id and u.is_active and upper(c.uom_code)<>upper(m.unit_code) and c.effective_from<=p_at and (c.effective_to is null or c.effective_to>p_at)
 ) x;
 if jsonb_array_length(rows) not between 1 and 100 then raise exception 'CP7_PROCUREMENT_UOM_COMPLETE_REQUIRED';end if;
 return jsonb_build_object('contract_version','cp7.procurement-uom.v1','material_id',m.id,'physical_at',p_at,'base_unit',m.unit_code,'rows',rows);
end $$;

-- Validation occurs only on the first intent. A later master change cannot
-- make a previously committed response unrecoverable.
create function cp7_procurement.validate_uom_lines(p_payload jsonb) returns void
language plpgsql stable security definer set search_path='' as $$
declare line jsonb;m erp.materials;
begin
 perform cp7_procurement.access_now();
 for line in select value from jsonb_array_elements(p_payload->'lines') loop
  if line ? 'purchase_uom_code' then
   select * into m from erp.materials where id=(line->>'material_id')::uuid;
   if not found or m.material_type<>'ACCESSORY' then raise exception 'CP7_PROCUREMENT_ACCESSORY_REQUIRED';end if;
   if not exists(select 1 from erp.uom_definitions where upper(unit_code)=upper(line->>'purchase_uom_code') and is_active) then raise exception 'CP7_PROCUREMENT_ACTIVE_UOM_REQUIRED';end if;
  end if;
 end loop;
end $$;
create table cp7_procurement.draft_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,expected_version text,response jsonb,primary key(actor,request_id)
);
alter table cp7_procurement.draft_requests owner to cp7_procure_write;
alter table cp7_procurement.draft_requests enable row level security;
revoke all on cp7_procurement.draft_requests from public,anon,authenticated,service_role,cp7_capture,cp7_procure_read;
create function cp7_procurement.save_draft_request(p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare old cp7_procurement.draft_requests;r jsonb;
begin
 insert into cp7_procurement.draft_requests(actor,request_id,payload,expected_version) values(auth.uid(),p_request,p_payload,p_expected) on conflict do nothing;
 select * into old from cp7_procurement.draft_requests where actor=auth.uid() and request_id=p_request for update;
 if old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_PROCUREMENT_DRAFT_REQUEST_CHANGED: different payload or version';end if;
 if old.response is not null then return old.response;end if;
 perform cp7_procurement.validate_uom_lines(p_payload);
 r:=erp.save_material_purchase_draft_v2(p_payload,p_request,p_expected::bigint);
 r:=jsonb_build_object('purchase_id',r->'purchase_id','status',r->'status','row_version',r->>'row_version');
 update cp7_procurement.draft_requests set response=r where actor=auth.uid() and request_id=p_request;
 return r;
end $$;
