-- The accepted sale lifecycle changes SALE_RESERVE to SALE at POST without
-- another stock deduction. Keep physical, reserved and available explicit.
create function cp7_fg.positions(p_q text,p_zero boolean) returns table(
 product_id uuid,product_sku text,commercial_sku text,product_name text,size_code text,brand_name text,lot_id uuid,lot_number text,
 location_id uuid,location_name text,quality_grade text,available_qty numeric,reserved_qty numeric,physical_qty numeric,last_at timestamptz,lineage_valid boolean
) language sql stable security invoker set search_path='' as $$
 with ledger as(
  select m.product_id,m.lot_id,m.location_id,m.quality_grade,sum(m.qty_signed)::numeric available_qty,
   coalesce(sum(abs(m.qty_signed)) filter(where m.movement_type='SALE_RESERVE' and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id and rv.physical_at<=statement_timestamp())),0)::numeric reserved_qty,
   max(m.physical_at) last_at
  from erp.fg_stock_movements m where m.physical_at<=statement_timestamp() group by m.product_id,m.lot_id,m.location_id,m.quality_grade
 ), source as(
  select p.id,p.sku::text,erp.bf_commercial_sku_at_v1(p.id,statement_timestamp()) commercial_sku,p.product_name::text,s.size_code::text,b.brand_name::text,
   x.lot_id,l.lot_number::text,loc.id location_id,loc.location_name::text,x.quality_grade::text,x.available_qty,x.reserved_qty,x.available_qty+x.reserved_qty physical_qty,x.last_at,
   coalesce(l.id is not null and l.product_id=p.id,false) lineage_valid
  from ledger x join erp.products p on p.id=x.product_id join erp.sizes s on s.id=p.size_id join erp.brands b on b.id=p.brand_id
  join erp.locations loc on loc.id=x.location_id left join erp.fg_lots l on l.id=x.lot_id
 )
 select * from source x where (p_zero or x.physical_qty<>0 or x.available_qty<>0 or x.reserved_qty<>0)
  and(p_q='' or strpos(lower(concat_ws(' ',x.sku,x.commercial_sku,x.product_name,x.size_code,x.brand_name,x.lot_number,x.location_name)),lower(p_q))>0)
$$;

create function cp7_fg.workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;purpose text;q text;off integer;n integer;zero boolean;rows jsonb;total bigint;totals jsonb;
begin
 if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('purpose','q','show_zero','offset','limit'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('purpose','q') and jsonb_typeof(e.value) not in('string','null'))
  or(p_query ? 'show_zero' and jsonb_typeof(p_query->'show_zero')<>'boolean')
  or(p_query ? 'offset' and (jsonb_typeof(p_query->'offset')<>'number' or (p_query->>'offset')!~'^[0-9]{1,7}$'))
  or(p_query ? 'limit' and (jsonb_typeof(p_query->'limit')<>'number' or (p_query->>'limit')!~'^[0-9]{1,3}$')) then raise exception 'CP7_FG_QUERY';end if;
 purpose:=coalesce(p_query->>'purpose','SUMMARY');a:=cp7_fg.access_now(purpose);q:=btrim(coalesce(p_query->>'q',''));off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);zero:=coalesce((p_query->>'show_zero')::boolean,false);
 if length(q)>120 or off not between 0 and 1000000 or n not between 1 and 100 then raise exception 'CP7_FG_QUERY';end if;
 select count(*) into total from cp7_fg.positions(q,zero);
 select coalesce(jsonb_agg(jsonb_build_object('product_id',x.product_id,'product_sku',x.product_sku,'commercial_sku',x.commercial_sku,'product_name',x.product_name,'size_code',x.size_code,'brand_name',x.brand_name,
  'lot_id',x.lot_id,'lot_number',x.lot_number,'location_id',x.location_id,'location_name',x.location_name,'quality_grade',x.quality_grade,
  'available_qty',x.available_qty::text,'reserved_qty',x.reserved_qty::text,'physical_qty',x.physical_qty::text,'last_movement_at',x.last_at,
  'quality',case when x.available_qty<0 or x.physical_qty<0 or not x.lineage_valid then 'CONFLICT' else 'KNOWN' end)
  ||case when a->'can_value'='true'::jsonb then jsonb_build_object('valuation',cp7_fg.lot_value(x.lot_id,x.physical_qty)) else '{}'::jsonb end
  order by x.commercial_sku,x.size_code,x.product_id,x.lot_id nulls first,x.location_id,x.quality_grade),'[]') into rows
 from(select * from cp7_fg.positions(q,zero) order by commercial_sku,size_code,product_id,lot_id nulls first,location_id,quality_grade limit n offset off)x;
 select jsonb_build_object('available_qty',coalesce(sum(available_qty),0)::text,'reserved_qty',coalesce(sum(reserved_qty),0)::text,'physical_qty',coalesce(sum(physical_qty),0)::text,
  'quality',case when bool_or(available_qty<0 or physical_qty<0 or not lineage_valid) then 'CONFLICT' else 'KNOWN' end) into totals from cp7_fg.positions(q,zero);
 return jsonb_build_object('contract_version','cp7.fg-workspace.v1','purpose',purpose,'read_at',statement_timestamp(),'knowledge','CURRENT','quantity_basis','PHYSICAL_EQUALS_AVAILABLE_PLUS_ACTIVE_RESERVATION',
  'financial_captured',a->'can_value','capabilities',jsonb_build_object('card',a->'can_card'),'unit_code','PCS','totals',totals,
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));
end $$;
create function public.erp_cp7_get_fg_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_fg.workspace(p_query)$$;
