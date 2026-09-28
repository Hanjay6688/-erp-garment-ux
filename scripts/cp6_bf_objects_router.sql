CREATE OR REPLACE FUNCTION erp.save_sku_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare a text:=upper(btrim(p_action)); prior erp.bf_requests_v1%rowtype; result jsonb;
begin
 if erp.current_app_user_id() is null then raise exception 'BF_AUTH_REQUIRED';end if;
 if p_client_request_id is null then raise exception 'BF_REQUEST_REQUIRED';end if;
 if a not in('SAVE_GROUPS','BIND_WAVE') then raise exception 'BF_ACTION';end if;
 perform pg_advisory_xact_lock(hashtextextended('BFREQ:'||p_client_request_id::text,0));
 -- Permissions before cache, including replay following a live role change.
 if a='SAVE_GROUPS' then
   perform erp.require_owner_admin();perform erp.require_permission('master.product.manage');perform erp.require_permission('finance.hpp.manage');
 else perform erp.require_permission('production.cutting.edit_draft');end if;
 select * into prior from erp.bf_requests_v1 where request_id=p_client_request_id;
 if prior.request_id is not null then
   if prior.actor is distinct from erp.current_app_user_id() or prior.action<>a or prior.payload<>p_payload then raise exception 'BF_REQUEST_REUSED';end if;
   return prior.response||jsonb_build_object('replayed',true);
 end if;
 result:=case a when 'SAVE_GROUPS' then erp.bf_save_groups_v1(p_payload,p_client_request_id) else erp.bf_bind_wave_v1(p_payload,p_client_request_id) end;
 result:=result||jsonb_build_object('action',a,'request_id',p_client_request_id,'status','SAVED');
 insert into erp.bf_requests_v1 values(p_client_request_id,erp.current_app_user_id(),a,p_payload,result);
 return result;
end;$function$;

CREATE OR REPLACE FUNCTION erp.get_sku_workspace_v1(p_filters jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare page_no integer:=greatest(1,coalesce((p_filters->>'page')::integer,1)); q text:=coalesce(p_filters->>'query','');
 at_time timestamptz:=coalesce((p_filters->>'at')::timestamptz,statement_timestamp()); roots uuid[]; result jsonb; money boolean;
begin
 perform erp.require_permission('master.product.view');
 money:=erp.has_permission('finance.hpp.view') or erp.has_permission('finance.hpp.manage');
 select coalesce(array_agg(x::uuid),'{}') into roots from jsonb_array_elements_text(coalesce(p_filters->'roots','[]')) x;
 if cardinality(roots)>500 then raise exception 'BF_MEMBER_LIMIT';end if;
 if cardinality(roots)>0 and not money then raise exception 'BF_PRICE_PERMISSION';end if;
 with g as materialized(
   select s.*,v.id version_id,v.revision selected_revision,v.effective_from,v.effective_to,v.settings,b.brand_name,m.model_name,
     coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'size_id',p.size_id,'size',z.size_code) order by z.sort_order,z.size_code,p.id)
       from erp.bf_sku_members_v1 sm join erp.products p on p.id=sm.product_root join erp.sizes z on z.id=p.size_id
       where sm.version_id=v.id),'[]') members
   from erp.bf_skus_v1 s join erp.brands b on b.id=s.brand_id join erp.product_models m on m.id=s.model_id
   join lateral(select x.* from erp.bf_sku_versions_v1 x where x.sku_id=s.id
     and x.effective_from<=at_time and (x.effective_to is null or x.effective_to>at_time)
     order by x.revision desc limit 1) v on true
   where s.sku ilike '%'||q||'%' or b.brand_name ilike '%'||q||'%' or exists(select 1 from erp.bf_sku_members_v1 sm where sm.version_id=v.id and sm.product_root=any(roots))
 ), products as materialized(
   select p.id,p.sku,p.brand_id,b.brand_name,p.model_id,m.model_name,p.color_name,p.size_id,z.size_code size,
     (select v.sku_id from erp.bf_sku_members_v1 sm join erp.bf_sku_versions_v1 v on v.id=sm.version_id
       where sm.product_root=p.id and v.effective_from<=at_time and(v.effective_to is null or v.effective_to>at_time)) group_id
   from erp.products p join erp.brands b on b.id=p.brand_id join erp.product_models m on m.id=p.model_id join erp.sizes z on z.id=p.size_id
   where p.id=p.identity_root_id and p.is_active and (p.sku ilike '%'||q||'%' or b.brand_name ilike '%'||q||'%' or p.id=any(roots))
 ) select jsonb_build_object('at',at_time,'page',page_no,'page_size',50,'groups_total',(select count(*) from g),
   'groups',coalesce((select jsonb_agg(to_jsonb(x)) from(select id,sku,brand_id,brand_name,model_id,model_name,color_name,revision::text,selected_revision::text,version_id,
      effective_from,effective_to,members,case when money then settings end settings from g order by brand_name,sku,id limit 50 offset (page_no-1)*50)x),'[]'),
   'products_total',(select count(*) from products),'products',coalesce((select jsonb_agg(to_jsonb(x)) from(select * from products order by brand_name,sku,size,id limit 50 offset (page_no-1)*50)x),'[]'),
   'related_groups',coalesce((select jsonb_agg(to_jsonb(x)) from(select id,sku,brand_id,brand_name,model_id,model_name,color_name,revision::text,selected_revision::text,version_id,effective_from,effective_to,members,case when money then settings end settings from g
     where exists(select 1 from jsonb_array_elements(members) mem where (mem->>'id')::uuid=any(roots)))x),'[]'),
   'wave',case when nullif(p_filters->>'wave_id','') is not null then (select jsonb_build_object('id',cg.id,'number',cg.group_number,
     'revision',erp.bf_wave_revision_v1(cg.id),'can_bind',erp.has_permission('production.cutting.edit_draft'),
     'sizes',coalesce((select jsonb_agg(jsonb_build_object('id',z.id,'name',z.size_code,'sku_id',w.sku_id,'sku',s.sku) order by z.sort_order,z.size_code)
       from (select distinct size_id from erp.cutting_group_size_slots where cutting_group_id=cg.id) sl
       join erp.sizes z on z.id=sl.size_id
       left join erp.bf_wave_skus_v1 w on w.cutting_group_id=cg.id and w.size_id=z.id left join erp.bf_skus_v1 s on s.id=w.sku_id
       ),'[]')) from erp.cutting_groups cg where cg.id=(p_filters->>'wave_id')::uuid) end,
   'selected_products',coalesce((select jsonb_agg(to_jsonb(x)) from products x where id=any(roots)),'[]'),
   'lookups',case when money then jsonb_build_object(
     'accessories',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',category_name,'unit',base_uom_code) order by category_name,id) from erp.accessory_categories where is_active),'[]'),
     'work',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',component_name,'category',component_category) order by sequence_default,id) from erp.work_components where is_active),'[]'),
     'contractors',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',contractor_name) order by contractor_name,id) from erp.contractors where is_active),'[]'),
     'vendors',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',vendor_name) order by vendor_name,id) from erp.laundry_vendors where is_active),'[]'),
     'laundry',coalesce((select jsonb_agg(to_jsonb(x)) from(
       select id,process_name name,'PROCESS' kind,null::uuid vendor_id from erp.wash_processes where is_active
       union all select id,component_name,'COMPONENT',vendor_id from erp.bd_laundry_components_v1 where is_active
       union all select id,package_name,'PACKAGE',vendor_id from erp.bd_laundry_packages_v1 where is_active)x),'[]')) end,
   'legacy_basis',case when money then erp.bf_legacy_basis_v1(roots,at_time) end,'can_edit',erp.has_permission('master.product.manage') and erp.has_permission('finance.hpp.manage') and erp.current_app_role() in('OWNER','ADMIN')) into result;
 return result;
end;$function$;

CREATE OR REPLACE FUNCTION erp.get_sku_hpp_v1(p_filters jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare at_time timestamptz:=coalesce((p_filters->>'at')::timestamptz,statement_timestamp()); result jsonb;
 page_no integer:=greatest(1,coalesce((p_filters->>'page')::integer,1));
begin
 perform erp.require_permission('finance.hpp.view');
 if at_time>statement_timestamp() then raise exception 'BF_REPORT_FUTURE';end if;
 with stock as materialized(
   select m.lot_id,m.product_id,m.location_id,m.quality_grade,sum(m.qty_signed)::bigint qty
   from erp.fg_stock_movements m where m.physical_at<=at_time
     and(nullif(p_filters->>'location_id','') is null or m.location_id=(p_filters->>'location_id')::uuid)
     and(nullif(p_filters->>'grade','') is null or m.quality_grade=p_filters->>'grade')
   group by m.lot_id,m.product_id,m.location_id,m.quality_grade having sum(m.qty_signed)<>0
 ), facts as materialized(
   select coalesce(s.id::text,p.brand_id::text||':'||p.sku) group_key,coalesce(s.sku,p.sku) sku,
     p.brand_id,b.brand_name,z.size_code size,st.*,l.lot_number,h.id hpp_version_id,h.cost_state,
     (st.qty*h.total_cost/nullif(h.qty_basis_pcs,0)) value,
     (h.id is null or h.cost_state='ESTIMATED' or erp.bd_lot_laundry_unknown_v1(l.id) or (l.po_id is not null and exists(select 1 from erp.get_hpp_completeness(l.po_id) c where c.pending_reason_count>0))) provisional
   from stock st join erp.fg_lots l on l.id=st.lot_id join erp.products p on p.id=st.product_id
   join erp.brands b on b.id=p.brand_id join erp.sizes z on z.id=p.size_id
   left join erp.bf_sku_versions_v1 v on v.id=erp.bf_version_at_v1(p.id,at_time)
   left join erp.bf_skus_v1 s on s.id=v.sku_id
   left join lateral(select x.* from erp.hpp_versions x where x.lot_id=l.id and x.calculated_at<=at_time order by x.calculated_at desc,x.version_no desc limit 1) h on true
 ), groups as materialized(
   select group_key,sku,brand_id,brand_name,sum(qty)::bigint qty,
     case when bool_and(value is not null) then sum(value) end value,bool_or(provisional) provisional,
     jsonb_agg(jsonb_build_object('lot_id',lot_id,'lot_number',lot_number,'product_id',product_id,'size',size,'location_id',location_id,
       'grade',quality_grade,'qty',qty::text,'value',value::text,'hpp_version_id',hpp_version_id,'cost_state',cost_state,'provisional',provisional)
       order by size,lot_number,location_id,quality_grade) lots
   from facts group by group_key,sku,brand_id,brand_name
 ), filtered as materialized(
   select * from groups where (nullif(p_filters->>'brand_id','') is null or brand_id=(p_filters->>'brand_id')::uuid)
     and (sku ilike '%'||coalesce(p_filters->>'query','')||'%' or brand_name ilike '%'||coalesce(p_filters->>'query','')||'%')
 ) select jsonb_build_object('at',at_time,'page',page_no,'page_size',50,'total',(select count(*) from filtered),
   'groups',coalesce((select jsonb_agg(to_jsonb(x)) from(select group_key,sku,brand_id,brand_name,qty::text,value::text,
     (value/nullif(qty,0))::text hpp_per_pcs,provisional,lots from filtered order by brand_name,sku,group_key limit 50 offset (page_no-1)*50)x),'[]')) into result;
 return result;
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_save_sku_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.save_sku_action_v1(p_action,p_payload,p_client_request_id) $function$;
CREATE OR REPLACE FUNCTION public.erp_get_sku_workspace_v1(p_filters jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.get_sku_workspace_v1(p_filters) $function$;
CREATE OR REPLACE FUNCTION public.erp_get_sku_hpp_v1(p_filters jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.get_sku_hpp_v1(p_filters) $function$;
