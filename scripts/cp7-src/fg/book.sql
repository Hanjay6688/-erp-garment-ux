-- Global FG presentation book. Quantity prefixes precede all display filters.
-- Reordering is presentation-only; the private request records actor/intent/result.
create function cp7_fg.book_access() returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;
begin
 a:=cp7_fg.access_now('MOVEMENTS');
 return a||jsonb_build_object('can_order',erp.has_permission('warehouse.stock.adjust') and a->'profile'->>'role_code' in('OWNER','ADMIN'));
end $$;

create function cp7_fg.book_signature() returns text
language sql stable security definer set search_path='' as $$
 select md5(coalesce(string_agg(jsonb_build_array(id,book_order,qty_signed,movement_type,reversal_of_id,extract(epoch from physical_at))::text,',' order by id),'')) from erp.fg_stock_movements
$$;

create function cp7_fg.book_rows() returns table(
 id uuid,book_order text,physical_at timestamptz,recorded_at timestamptz,product_id uuid,brand_id uuid,brand_name text,commercial_sku text,product_name text,size_code text,
 lot_id uuid,lot_number text,location_id uuid,location_name text,quality_grade text,customer_id uuid,customer_name text,movement_type text,source_type text,source_id uuid,reversal_of_id uuid,notes text,
 physical_delta text,reservation_delta text,available_delta text,book_physical_before text,book_physical_after text,book_available_after text,book_reserved_after text,official_physical_after text,official_available_after text,official_reserved_after text
) language sql stable security invoker set search_path='' as $$
 with source as(
  select m.*,case when m.movement_type='SALE_RESERVE' or exists(select 1 from erp.fg_stock_movements o where o.id=m.reversal_of_id and o.movement_type='SALE_RESERVE') then -m.qty_signed else 0 end reservation_delta
  from erp.fg_stock_movements m where m.physical_at<=statement_timestamp()
 ), prefix as(
  select m.*,sum(qty_signed+reservation_delta) over book book_physical_after,sum(qty_signed) over book book_available_after,sum(reservation_delta) over book book_reserved_after,
   sum(qty_signed+reservation_delta) over official official_physical_after,sum(qty_signed) over official official_available_after,sum(reservation_delta) over official official_reserved_after
  from source m
  window book as(partition by product_id,location_id,quality_grade order by book_order,id rows between unbounded preceding and current row),
   official as(partition by product_id,location_id,quality_grade order by physical_at,system_created_at,id rows between unbounded preceding and current row)
 )
 select m.id,m.book_order::text,m.physical_at,m.system_created_at,m.product_id,b.id,b.brand_name::text,erp.bf_commercial_sku_at_v1(p.id,m.physical_at),p.product_name::text,s.size_code::text,
  m.lot_id,l.lot_number::text,m.location_id,loc.location_name::text,m.quality_grade::text,m.customer_id,c.customer_name::text,m.movement_type::text,m.source_type::text,m.source_id,m.reversal_of_id,m.notes,
  (m.qty_signed+m.reservation_delta)::text,m.reservation_delta::text,m.qty_signed::text,(m.book_physical_after-m.qty_signed-m.reservation_delta)::text,m.book_physical_after::text,m.book_available_after::text,m.book_reserved_after::text,
  m.official_physical_after::text,m.official_available_after::text,m.official_reserved_after::text
 from prefix m join erp.products p on p.id=m.product_id join erp.brands b on b.id=p.brand_id join erp.sizes s on s.id=p.size_id
 join erp.locations loc on loc.id=m.location_id left join erp.fg_lots l on l.id=m.lot_id left join erp.customers c on c.id=m.customer_id
$$;

create function cp7_fg.book_workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;q text;n integer;off integer;at_from timestamptz;at_to timestamptz;brands uuid[];customers uuid[];types text[];rows jsonb;total bigint;key text;
begin
 a:=cp7_fg.book_access();
 if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','limit','offset','from','to','brand_ids','customer_ids','movement_types'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','from','to') and jsonb_typeof(e.value) not in('string','null'))
  or(p_query?'limit' and (jsonb_typeof(p_query->'limit')<>'number' or(p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query?'offset' and (jsonb_typeof(p_query->'offset')<>'number' or(p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_FG_BOOK_QUERY';end if;
 foreach key in array array['brand_ids','customer_ids','movement_types'] loop
  if p_query?key and (jsonb_typeof(p_query->key)<>'array' or jsonb_array_length(p_query->key)>100 or exists(select 1 from jsonb_array_elements(p_query->key) e where jsonb_typeof(e)<>'string')) then raise exception 'CP7_FG_BOOK_FILTER';end if;
 end loop;
 q:=btrim(coalesce(p_query->>'q',''));n:=coalesce((p_query->>'limit')::integer,25);off:=coalesce((p_query->>'offset')::integer,0);at_from:=(p_query->>'from')::timestamptz;at_to:=(p_query->>'to')::timestamptz;
 if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 or at_from>=at_to then raise exception 'CP7_FG_BOOK_QUERY';end if;
 select array_agg(value::uuid) into brands from jsonb_array_elements_text(p_query->'brand_ids');
 select array_agg(value::uuid) into customers from jsonb_array_elements_text(p_query->'customer_ids');
 select array_agg(value) into types from jsonb_array_elements_text(p_query->'movement_types');
 with filtered as materialized(
  select * from cp7_fg.book_rows() m where(at_from is null or m.physical_at>=at_from) and(at_to is null or m.physical_at<at_to)
   and(brands is null or m.brand_id=any(brands)) and(customers is null or m.customer_id=any(customers)) and(types is null or m.movement_type=any(types))
   and(q='' or strpos(lower(concat_ws(' ',m.brand_name,m.commercial_sku,m.product_name,m.size_code,m.lot_number,m.location_name,m.customer_name,m.source_type,m.source_id,m.notes)),lower(q))>0)
 ), page as(select * from filtered order by book_order::bigint,id limit n offset off)
 select(select count(*) from filtered),coalesce(jsonb_agg(to_jsonb(page) order by book_order::bigint,id),'[]') into total,rows from page;
 return jsonb_build_object('contract_version','cp7.fg-book.v1','read_at',statement_timestamp(),'knowledge','CURRENT','book_token',cp7_fg.book_signature(),
  'can_order',a->'can_order','quantity_scope','PHYSICAL_PRODUCT_LOCATION_GRADE','presentation_only',true,
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));
end $$;

create function cp7_fg.book_anchor(p_source uuid,p_target uuid,p_placement text) returns integer
language plpgsql stable security definer set search_path='' as $$
declare source_pos integer;target_pos integer;
begin
 if p_source is null or p_target is null or p_source=p_target or coalesce(p_placement,'') not in('BEFORE','AFTER') then raise exception 'CP7_FG_BOOK_ANCHOR';end if;
 select max(pos) filter(where id=p_source),max(pos) filter(where id=p_target) into source_pos,target_pos
 from(select id,row_number() over(order by book_order,id)::integer pos from erp.fg_stock_movements)x;
 if source_pos is null or target_pos is null then raise exception 'CP7_FG_BOOK_SOURCE_MISSING';end if;
 -- Native target rank is in the final list after removing the dragged row.
 return target_pos-case when source_pos<target_pos then 1 else 0 end+case when p_placement='AFTER' then 1 else 0 end;
end $$;

create function cp7_fg.book_command(p_action text,p_payload jsonb,p_request uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;old cp7_fg.requests;r jsonb;position integer;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_fg.book_access();
 if a->'can_order' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_FG_BOOK_ORDER_DENIED';end if;
 if p_action is null or p_action not in('MOVE','RESET') or p_request is null or jsonb_typeof(p_payload) is distinct from 'object'
  or not (p_payload?'book_token') or coalesce(p_payload->>'book_token','')!~'^[a-f0-9]{32}$'
  or exists(select 1 from jsonb_each(p_payload) e where e.key not in('book_token','source_id','target_id','placement') or jsonb_typeof(e.value)<>'string') then raise exception 'CP7_FG_BOOK_ACTION';end if;
 if p_action='RESET' and (p_payload-array['book_token'])<>'{}'::jsonb then raise exception 'CP7_FG_BOOK_ACTION';end if;
 insert into cp7_fg.requests(actor,request_id,action,payload,expected_version) values(auth.uid(),p_request,'BOOK_'||p_action,p_payload,null) on conflict do nothing;
 select * into old from cp7_fg.requests where actor=auth.uid() and request_id=p_request for update;
 if old.action<>('BOOK_'||p_action) or old.payload is distinct from p_payload or old.expected_version is not null then raise exception 'CP7_FG_BOOK_REQUEST_CHANGED';end if;
 if cp7_fg.book_access()<>a then raise exception using errcode='42501',message='CP7_FG_BOOK_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 perform pg_advisory_xact_lock(hashtextextended('FGBOOK|GLOBAL',0));
 if cp7_fg.book_access()<>a then raise exception using errcode='42501',message='CP7_FG_BOOK_ACCESS_CHANGED';end if;
 if cp7_fg.book_signature()<>p_payload->>'book_token' then raise exception 'CP7_FG_BOOK_STALE_RELOAD';end if;
 if p_action='MOVE' then
  position:=cp7_fg.book_anchor((p_payload->>'source_id')::uuid,(p_payload->>'target_id')::uuid,p_payload->>'placement');
  perform erp.move_fg_stock_card_row_to_position((p_payload->>'source_id')::uuid,position);
 else perform erp.reset_fg_stock_mutation_book_order();
 end if;
 if cp7_fg.book_access()<>a then raise exception using errcode='42501',message='CP7_FG_BOOK_ACCESS_CHANGED';end if;
 r:=jsonb_build_object('contract_version','cp7.fg-book-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'source_id',p_payload->'source_id','book_token',cp7_fg.book_signature(),'presentation_only',true);
 update cp7_fg.requests set response=r where actor=auth.uid() and request_id=p_request;return r;
end $$;
grant execute on function erp.move_fg_stock_card_row_to_position(uuid,integer),erp.reset_fg_stock_mutation_book_order() to cp7_fg_write;
create function public.erp_cp7_get_fg_book_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_fg.book_workspace(p_query)$$;
create function public.erp_cp7_save_fg_book_v1(p_action text,p_payload jsonb,p_request uuid) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_fg.book_command(p_action,p_payload,p_request)$$;

create function cp7_fg.book_options(p_kind text,p_q text,p_offset integer,p_limit integer) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare q text:=btrim(coalesce(p_q,''));rows jsonb;total bigint;
begin
 perform cp7_fg.book_access();
 if p_kind is null or p_kind not in('BRAND','CUSTOMER','TYPE') or length(q)>120 or p_offset is null or p_offset not between 0 and 1000000 or p_limit is null or p_limit not between 1 and 100 then raise exception 'CP7_FG_BOOK_OPTIONS';end if;
 with source as materialized(
  select b.id::text id,b.brand_name::text label,b.brand_code::text code from erp.brands b where p_kind='BRAND'
  union all select c.id::text,c.customer_name::text,c.customer_code::text from erp.customers c where p_kind='CUSTOMER'
  union all select distinct m.movement_type::text,m.movement_type::text,m.movement_type::text from erp.fg_stock_movements m where p_kind='TYPE'
 ), filtered as materialized(select * from source where q='' or strpos(lower(concat_ws(' ',label,code)),lower(q))>0),
 page as(select * from filtered order by label,id limit p_limit offset p_offset)
 select(select count(*) from filtered),coalesce(jsonb_agg(to_jsonb(page) order by label,id),'[]') into total,rows from page;
 return jsonb_build_object('contract_version','cp7.fg-book-options.v1','kind',p_kind,'read_at',statement_timestamp(),'page',
  jsonb_build_object('rows',rows,'total',total::text,'offset',p_offset,'limit',p_limit,'next_offset',case when p_offset+jsonb_array_length(rows)<total then p_offset+jsonb_array_length(rows) else null end));
end $$;
create function public.erp_cp7_get_fg_book_options_v1(p_kind text,p_q text,p_offset integer,p_limit integer) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_fg.book_options(p_kind,p_q,p_offset,p_limit)$$;
