-- P11 bounded invoice reader. It has no business writer capability. Financial
-- fields require AR authority; historical SKU is resolved at the invoice time.
create role cp7_sales_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_sales authorization cp7_sales_read;
revoke all on schema cp7_sales from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema erp,auth to cp7_sales_read;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text),erp.bf_commercial_sku_at_v1(uuid,timestamptz) to cp7_sales_read;
grant select on erp.sales_headers,erp.sales_items,erp.customers,erp.locations,erp.products,erp.sizes,erp.brands,
 erp.sales_returns,erp.sales_return_items,erp.sales_payments,erp.fg_stock_movements,erp.sale_stock_allocations to cp7_sales_read;

create function cp7_sales.access_now() returns boolean
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('sales.invoice.view') then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 return erp.has_permission('finance.ar.view');
end $$;

create function cp7_sales.review_token(p_id uuid) returns text
language sql stable security invoker set search_path='' as $$
 select md5(jsonb_build_object('header',to_jsonb(h),
  'items',(select coalesce(jsonb_agg(to_jsonb(i) order by i.id),'[]') from erp.sales_items i where i.sale_id=h.id),
  'allocations',(select coalesce(jsonb_agg(to_jsonb(a) order by a.id),'[]') from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=h.id),
  'reservations',(select coalesce(jsonb_agg(to_jsonb(m) order by m.id),'[]') from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id and m.source_type='SALE_ITEM' where i.sale_id=h.id))::text)
 from erp.sales_headers h where h.id=p_id
$$;

create function cp7_sales.header(h erp.sales_headers,p_financial boolean) returns jsonb
language sql stable security invoker set search_path='' as $$
 with amounts as(
  select coalesce((select sum(line_total) from erp.sales_items where sale_id=h.id),0)::numeric gross,
   coalesce((select sum(i.refund_amount) from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=h.id and r.status='POSTED'),0)::numeric returned,
   coalesce((select sum(round(amount,2)) from erp.sales_payments where sale_id=h.id and status='POSTED'),0)::numeric paid
 )
 select jsonb_build_object('id',h.id,'number',h.sale_number,'customer_id',h.customer_id,
  'customer_name',(select customer_name from erp.customers where id=h.customer_id),'location_id',h.source_location_id,
  'location_name',(select location_name from erp.locations where id=h.source_location_id),'physical_at',h.sale_date,
  'due_date',h.due_date,'status',h.status,'row_version',h.row_version::text,'notes',h.notes,
  'line_count',(select count(*)::text from erp.sales_items where sale_id=h.id),
  'qty_pcs',(select coalesce(sum(qty_pcs),0)::text from erp.sales_items where sale_id=h.id),
  'reserved_qty',(select coalesce(sum(-m.qty_signed),0)::text from erp.fg_stock_movements m join erp.sales_items i on m.source_id=i.id and m.source_type='SALE_ITEM'
   where i.sale_id=h.id and m.movement_type='SALE_RESERVE' and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)),
  'returned_qty',(select coalesce(sum(i.qty_pcs),0)::text from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=h.id and r.status='POSTED'))
 ||case when p_financial then (select jsonb_build_object('financial',jsonb_build_object(
   'basis','CURRENT_NATIVE_DOCUMENT','state',case when h.status='DRAFT' then 'DRAFT_PREVIEW' when h.status in('POSTED','PARTIAL_PAID','PAID') then 'ACTIVE_RECEIVABLE' else 'INACTIVE_DOCUMENT' end,
   'gross_total',round(gross,2)::text,'return_total',round(returned,2)::text,'net_total',round(greatest(gross-returned,0),2)::text,
   'paid_total',round(paid,2)::text,'open_balance',case when h.status in('POSTED','PARTIAL_PAID','PAID') then round(greatest(gross-returned,0)-paid,2)::text else null end)) from amounts) else '{}'::jsonb end
$$;

create function cp7_sales.workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare financial boolean;q text;state text;chosen uuid;n integer;off integer;total bigint;rows jsonb;detail jsonb:=null;h erp.sales_headers;items jsonb;
begin
 financial:=cp7_sales.access_now();
 if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','status','sale_id','offset','limit'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','status','sale_id') and jsonb_typeof(e.value) not in('string','null'))
  or(p_query ? 'limit' and (jsonb_typeof(p_query->'limit')<>'number' or (p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query ? 'offset' and (jsonb_typeof(p_query->'offset')<>'number' or (p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_SALES_QUERY';end if;
 q:=btrim(coalesce(p_query->>'q',''));state:=nullif(p_query->>'status','');chosen:=(p_query->>'sale_id')::uuid;n:=coalesce((p_query->>'limit')::integer,25);off:=coalesce((p_query->>'offset')::integer,0);
 if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 or state is not null and state not in('DRAFT','POSTED','PARTIAL_PAID','PAID','CANCELLED','REVERSED') then raise exception 'CP7_SALES_QUERY';end if;
 select count(*) into total from erp.sales_headers x join erp.customers c on c.id=x.customer_id
 where (state is null or x.status=state) and(q='' or strpos(lower(concat_ws(' ',x.sale_number,c.customer_code,c.customer_name)),lower(q))>0);
 select coalesce(jsonb_agg(cp7_sales.header(x,financial) order by x.sale_date desc,x.id),'[]') into rows from(
  select x.* from erp.sales_headers x join erp.customers c on c.id=x.customer_id
  where (state is null or x.status=state) and(q='' or strpos(lower(concat_ws(' ',x.sale_number,c.customer_code,c.customer_name)),lower(q))>0)
  order by x.sale_date desc,x.id limit n offset off)x;
 if chosen is not null then
  select * into h from erp.sales_headers where id=chosen;
  if h.id is null then raise exception 'CP7_SALES_NOT_FOUND';end if;
  if (select count(*) from erp.sales_items where sale_id=h.id)>100 then raise exception 'CP7_SALES_DOCUMENT_TOO_LARGE';end if;
  select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'product_id',i.product_id,'product_sku',p.sku,
   'commercial_sku',erp.bf_commercial_sku_at_v1(p.id,h.sale_date),'product_name',p.product_name,'size_code',s.size_code,'brand_name',b.brand_name,
   'qty_pcs',i.qty_pcs::text,'notes',i.notes)
   ||case when financial then jsonb_build_object('financial',jsonb_build_object('unit_price',i.unit_price_snapshot::text,'discount',i.discount_amount::text,'line_total',i.line_total::text)) else '{}'::jsonb end order by i.id),'[]')
  into items from erp.sales_items i join erp.products p on p.id=i.product_id join erp.sizes s on s.id=p.size_id join erp.brands b on b.id=p.brand_id where i.sale_id=h.id;
  if jsonb_array_length(items)<>(select count(*) from erp.sales_items where sale_id=h.id) then raise exception 'CP7_SALES_INCOMPLETE_ITEMS';end if;
  detail:=cp7_sales.header(h,financial)||jsonb_build_object('items',items)||case when financial then jsonb_build_object('review_token',cp7_sales.review_token(h.id)) else '{}'::jsonb end;
 end if;
 return jsonb_build_object('contract_version','cp7.sales-workspace.v1','read_at',statement_timestamp(),'financial_captured',financial,'read_only',true,
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end),'detail',detail);
end $$;
create function public.erp_cp7_get_sales_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_sales.workspace(p_query)$$;
alter function cp7_sales.access_now() owner to cp7_sales_read;
alter function cp7_sales.review_token(uuid) owner to cp7_sales_read;
alter function cp7_sales.header(erp.sales_headers,boolean) owner to cp7_sales_read;
alter function cp7_sales.workspace(jsonb) owner to cp7_sales_read;
grant create on schema public to cp7_sales_read;
alter function public.erp_cp7_get_sales_v1(jsonb) owner to cp7_sales_read;
revoke create on schema public from cp7_sales_read;
revoke all on all functions in schema cp7_sales from public,anon,authenticated,service_role,cp7_capture;
revoke all on function public.erp_cp7_get_sales_v1(jsonb) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_sales_v1(jsonb) to authenticated;
