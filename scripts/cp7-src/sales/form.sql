-- Complete source selectors for invoice drafts. Availability is a current
-- reference only; native SAVE rechecks real stock and dated transaction rules.
grant select on erp.fg_inventory_balances to cp7_sales_read;
create function cp7_sales.form_options(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare kind text;q text;at_time timestamptz;loc uuid;n integer;off integer;total bigint;rows jsonb;
begin
 if not cp7_sales.access_now() or not(erp.has_permission('sales.invoice.create') or erp.has_permission('sales.invoice.edit_draft')) then raise exception using errcode='42501',message='CP7_SALES_FORM_DENIED';end if;
 if jsonb_typeof(p_query) is distinct from 'object' or not p_query ?& array['kind','physical_at']
  or exists(select 1 from jsonb_object_keys(p_query) k where k not in('kind','q','physical_at','location_id','offset','limit'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('kind','q','physical_at','location_id') and jsonb_typeof(e.value) not in('string','null'))
  or (p_query ? 'limit' and(jsonb_typeof(p_query->'limit')<>'number' or(p_query->>'limit')!~'^[0-9]{1,3}$'))
  or (p_query ? 'offset' and(jsonb_typeof(p_query->'offset')<>'number' or(p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_SALES_FORM_QUERY';end if;
 kind:=p_query->>'kind';q:=btrim(coalesce(p_query->>'q',''));at_time:=(p_query->>'physical_at')::timestamptz;loc:=(p_query->>'location_id')::uuid;n:=coalesce((p_query->>'limit')::integer,25);off:=coalesce((p_query->>'offset')::integer,0);
 if kind is null or kind not in('CUSTOMER','STOCK') or length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 or at_time is null or at_time>statement_timestamp() then raise exception 'CP7_SALES_FORM_QUERY';end if;
 if kind='CUSTOMER' then
  with eligible as materialized(select id,customer_code,customer_name from erp.customers where is_active and(q='' or strpos(lower(concat_ws(' ',customer_code,customer_name)),lower(q))>0)),
  sliced as(select * from eligible order by customer_code,id limit n offset off)
  select (select count(*) from eligible),coalesce((select jsonb_agg(jsonb_build_object('id',id,'code',customer_code,'name',customer_name) order by customer_code,id) from sliced),'[]') into total,rows;
 else
  with positions as materialized(
   select p.id as product_id,p.sku as product_sku,p.product_name,erp.bf_commercial_sku_at_v1(p.id,at_time) as commercial_sku,s.size_code,b.brand_name,l.id as location_id,l.location_name,x.cached_qty_pcs as available_qty
   from erp.fg_inventory_balances x join erp.products p on p.id=x.product_id join erp.sizes s on s.id=p.size_id join erp.brands b on b.id=p.brand_id join erp.locations l on l.id=x.location_id
   where x.quality_grade='GRADE_A' and x.cached_qty_pcs>0 and p.is_active and l.is_active and l.location_type='FG_WAREHOUSE' and(loc is null or l.id=loc)),
  eligible as materialized(select * from positions where q='' or strpos(lower(concat_ws(' ',product_sku,commercial_sku,product_name,size_code,brand_name,location_name)),lower(q))>0),
  sliced as(select * from eligible order by commercial_sku,size_code,product_id,location_id limit n offset off)
  select (select count(*) from eligible),coalesce((select jsonb_agg(jsonb_build_object('product_id',product_id,'product_sku',product_sku,'product_name',product_name,'commercial_sku',commercial_sku,'size_code',size_code,'brand_name',brand_name,'location_id',location_id,'location_name',location_name,'available_qty',available_qty::text) order by commercial_sku,size_code,product_id,location_id) from sliced),'[]') into total,rows;
 end if;
 return jsonb_build_object('contract_version','cp7.sales-form-options.v1','kind',kind,'physical_at',at_time,'location_id',loc,'availability_basis','CURRENT_AVAILABLE_NOT_HISTORICAL_STOCK','rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end);
end $$;
create function public.erp_cp7_get_sales_form_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_sales.form_options(p_query)$$;
alter function cp7_sales.form_options(jsonb) owner to cp7_sales_read;
grant create on schema public to cp7_sales_read;
alter function public.erp_cp7_get_sales_form_v1(jsonb) owner to cp7_sales_read;
revoke create on schema public from cp7_sales_read;
revoke all on function cp7_sales.form_options(jsonb),public.erp_cp7_get_sales_form_v1(jsonb) from public,anon,authenticated,service_role,cp7_capture,cp7_sales_write;
grant execute on function public.erp_cp7_get_sales_form_v1(jsonb) to authenticated;
