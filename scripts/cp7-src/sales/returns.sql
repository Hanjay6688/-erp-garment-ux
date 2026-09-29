-- Physical returns choose an original sale allocation. HPP/product/lot identity
-- comes from the native allocation normalizer; callers cannot supply its cost.
grant select on erp.fg_lots to cp7_sales_read;
create function cp7_sales.validate_return(p jsonb,p_reverse boolean) returns void
language plpgsql immutable security invoker set search_path='' as $$
declare allowed text[];x jsonb;k text;
begin
 allowed:=array['sale_id','review_token','change_reason']||case when p_reverse then array['return_id'] else array['return_number','physical_at','notes','items'] end;
 if jsonb_typeof(p) is distinct from 'object' or not p ?& allowed or exists(select 1 from jsonb_object_keys(p) key_name where not key_name=any(allowed)) then raise exception 'CP7_SALES_RETURN_FIELDS';end if;
 foreach k in array allowed loop
  if k='items' then continue;
  elsif k='notes' then
   if jsonb_typeof(p->k) not in('string','null') or length(p->>k)>2000 then raise exception 'CP7_SALES_RETURN_FIELDS';end if;
  elsif jsonb_typeof(p->k) is distinct from 'string' then raise exception 'CP7_SALES_RETURN_FIELDS';end if;
 end loop;
 if (p->>'sale_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or(p->>'review_token')!~'^[a-f0-9]{32}$' or length(btrim(p->>'change_reason')) not between 5 and 1000 then raise exception 'CP7_SALES_RETURN_FIELDS';end if;
 if p_reverse then
  if(p->>'return_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then raise exception 'CP7_SALES_RETURN_FIELDS';end if;
  return;
 end if;
 if length(btrim(p->>'return_number')) not between 1 and 60 or length(p->>'physical_at') not between 20 and 40 or(p->>'physical_at')!~'(Z|[+-][0-9]{2}:[0-9]{2})$'
  or jsonb_typeof(p->'items') is distinct from 'array' then raise exception 'CP7_SALES_RETURN_FIELDS';end if;
 if jsonb_array_length(p->'items') not between 1 and 100 then raise exception 'CP7_SALES_RETURN_LINES';end if;
 for x in select value from jsonb_array_elements(p->'items') loop
  if jsonb_typeof(x) is distinct from 'object' or not x ?& array['allocation_id','location_id','qty_pcs','quality_grade','refund_amount','notes']
   or exists(select 1 from jsonb_each(x) e where e.key not in('allocation_id','location_id','qty_pcs','quality_grade','refund_amount','notes') or(e.key<>'notes' and jsonb_typeof(e.value)<>'string'))
   or jsonb_typeof(x->'notes') not in('string','null') or length(x->>'notes')>2000
   or(x->>'allocation_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or(x->>'location_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or(x->>'qty_pcs')!~'^[1-9][0-9]{0,8}$' or(x->>'quality_grade') not in('GRADE_A','GRADE_B','HOLD')
   or(x->>'refund_amount')!~'^(0|[1-9][0-9]{0,17})(\.[0-9]{1,2})?$' then raise exception 'CP7_SALES_RETURN_LINES';end if;
 end loop;
 -- One allocation may be split across destination/grade lines. The native
 -- poster sums every line for that allocation before enforcing its capacity.
end $$;

create function cp7_sales.return_workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare h erp.sales_headers;ident uuid;kind text;q text;off integer;n integer;total bigint;rows jsonb;
begin
 if not cp7_sales.access_now() or not erp.has_permission('sales.return.view') then raise exception using errcode='42501',message='CP7_SALES_RETURN_DENIED';end if;
 if jsonb_typeof(p_query) is distinct from 'object' or not p_query ?& array['sale_id','kind']
  or exists(select 1 from jsonb_object_keys(p_query) k where k not in('sale_id','kind','q','offset','limit'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('sale_id','kind','q') and jsonb_typeof(e.value)<>'string')
  or exists(select 1 from jsonb_each(p_query) e where e.key in('offset','limit') and(jsonb_typeof(e.value)<>'number' or e.value::text!~'^[0-9]{1,7}$')) then raise exception 'CP7_SALES_RETURN_QUERY';end if;
 ident:=(p_query->>'sale_id')::uuid;kind:=p_query->>'kind';q:=btrim(coalesce(p_query->>'q',''));off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);
 if ident is null or kind is null or kind not in('ALLOCATIONS','RETURNS','LOCATIONS') or off not between 0 and 1000000 or n not between 1 and 100 or length(q)>120 then raise exception 'CP7_SALES_RETURN_QUERY';end if;
 select * into h from erp.sales_headers where id=ident;if h.id is null then raise exception 'CP7_SALES_NOT_FOUND';end if;
 if kind='ALLOCATIONS' then
  with sources as materialized(
   select a.id,a.sale_item_id,a.lot_id,fl.lot_number,p.id product_id,p.sku product_sku,erp.bf_commercial_sku_at_v1(p.id,h.sale_date) commercial_sku,p.product_name,s.size_code,l.location_name source_location_name,
    a.qty_pcs allocated_qty,coalesce((select sum(ri.qty_pcs) from erp.sales_return_items ri join erp.sales_returns rh on rh.id=ri.return_id where ri.sale_stock_allocation_id=a.id and rh.sale_id=ident and rh.status='POSTED'),0) returned_qty,
    i.qty_pcs sale_item_qty,i.line_total sale_item_net
   from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id join erp.products p on p.id=i.product_id join erp.sizes s on s.id=p.size_id join erp.fg_lots fl on fl.id=a.lot_id join erp.locations l on l.id=a.location_id
   where i.sale_id=ident and h.status in('POSTED','PARTIAL_PAID','PAID')),
  eligible as materialized(select * from sources where allocated_qty>returned_qty and(q='' or strpos(lower(concat_ws(' ',product_sku,commercial_sku,product_name,size_code,lot_number)),lower(q))>0)),
  sliced as(select * from eligible order by sale_item_id,lot_id,id limit n offset off)
  select(select count(*) from eligible),coalesce((select jsonb_agg(jsonb_build_object('allocation_id',id,'sale_item_id',sale_item_id,'product_id',product_id,'product_sku',product_sku,'commercial_sku',commercial_sku,'product_name',product_name,'size_code',size_code,'lot_id',lot_id,'lot_number',lot_number,'source_location_name',source_location_name,'allocated_qty',allocated_qty::text,'returned_qty',returned_qty::text,'remaining_qty',(allocated_qty-returned_qty)::text,'sale_item_qty',sale_item_qty::text,'sale_item_net',round(sale_item_net,2)::text) order by sale_item_id,lot_id,id) from sliced),'[]') into total,rows;
 elsif kind='LOCATIONS' then
  with eligible as materialized(select id,location_name from erp.locations where is_active and location_type='FG_WAREHOUSE' and(q='' or strpos(lower(location_name),lower(q))>0)),
  sliced as(select * from eligible order by location_name,id limit n offset off)
  select(select count(*) from eligible),coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',location_name) order by location_name,id) from sliced),'[]') into total,rows;
 else
  if exists(select 1 from(select id from erp.sales_returns where sale_id=ident and(q='' or strpos(lower(return_number),lower(q))>0) order by physical_at desc,id limit n offset off)x where(select count(*) from erp.sales_return_items i where i.return_id=x.id)>100) then raise exception 'CP7_SALES_RETURN_DOCUMENT_TOO_LARGE';end if;
  select count(*) into total from erp.sales_returns where sale_id=ident and(q='' or strpos(lower(return_number),lower(q))>0);
  select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'number',x.return_number,'physical_at',x.physical_at,'status',x.status,'notes',x.notes,'line_count',(select count(*)::text from erp.sales_return_items i where i.return_id=x.id),'items',
   (select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'allocation_id',i.sale_stock_allocation_id,'product_sku',p.sku,'lot_number',fl.lot_number,'location_id',i.location_id,'location_name',l.location_name,'qty_pcs',i.qty_pcs::text,'quality_grade',i.quality_grade,'refund_amount',i.refund_amount::text,'notes',i.notes) order by i.id),'[]') from erp.sales_return_items i join erp.products p on p.id=i.product_id join erp.fg_lots fl on fl.id=i.lot_id join erp.locations l on l.id=i.location_id where i.return_id=x.id)) order by x.physical_at desc,x.id),'[]') into rows
  from(select * from erp.sales_returns where sale_id=ident and(q='' or strpos(lower(return_number),lower(q))>0) order by physical_at desc,id limit n offset off)x;
 end if;
 return jsonb_build_object('contract_version','cp7.sales-returns.v1','kind',kind,'sale_id',ident,'row_version',h.row_version::text,'review_token',cp7_sales.review_token(ident),'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));
end $$;
create function public.erp_cp7_get_sales_returns_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_sales.return_workspace(p_query)$$;
alter function cp7_sales.validate_return(jsonb,boolean) owner to cp7_sales_read;
alter function cp7_sales.return_workspace(jsonb) owner to cp7_sales_read;
grant create on schema public to cp7_sales_read;
alter function public.erp_cp7_get_sales_returns_v1(jsonb) owner to cp7_sales_read;
revoke create on schema public from cp7_sales_read;
revoke all on function cp7_sales.validate_return(jsonb,boolean),cp7_sales.return_workspace(jsonb),public.erp_cp7_get_sales_returns_v1(jsonb) from public,anon,authenticated,service_role,cp7_capture,cp7_sales_write;
grant execute on function cp7_sales.validate_return(jsonb,boolean) to cp7_sales_write;
grant execute on function public.erp_cp7_get_sales_returns_v1(jsonb) to authenticated;
