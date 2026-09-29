-- Authoritative chronological prefix first; search/date/page are presentation
-- filters afterwards. A reservation moves availability, not physical custody.
create function cp7_fg.ledger_rows(p_product uuid,p_lot uuid,p_location uuid,p_grade text) returns table(
 id uuid,physical_at timestamptz,recorded_at timestamptz,movement_type text,source_type text,source_id uuid,
 reversal_of_id uuid,customer_name text,notes text,book_order text,commercial_sku text,
 qty_signed numeric,reservation_delta numeric,physical_delta numeric,
 available_balance numeric,reserved_balance numeric,physical_balance numeric,unit_hpp_snapshot numeric
) language sql stable security invoker set search_path='' as $$
 with movements as (
  select m.*,case when m.movement_type='SALE_RESERVE' or original.movement_type='SALE_RESERVE' then -m.qty_signed else 0 end::numeric reserved_delta
  from erp.fg_stock_movements m left join erp.fg_stock_movements original on original.id=m.reversal_of_id
  where m.product_id=p_product and m.lot_id is not distinct from p_lot and m.location_id=p_location and m.quality_grade=p_grade
   and m.physical_at<=statement_timestamp()
 ), prefix as (
  select m.*,sum(m.qty_signed) over w available_balance,sum(m.reserved_delta) over w reserved_balance
  from movements m window w as(order by m.physical_at,m.system_created_at,m.id rows between unbounded preceding and current row)
 )
 select m.id,m.physical_at,m.system_created_at,m.movement_type::text,m.source_type::text,m.source_id,m.reversal_of_id,
  c.customer_name::text,m.notes::text,m.book_order::text,erp.bf_commercial_sku_at_v1(m.product_id,m.physical_at),
  m.qty_signed::numeric,m.reserved_delta,(m.qty_signed+m.reserved_delta)::numeric,m.available_balance::numeric,m.reserved_balance::numeric,
  (m.available_balance+m.reserved_balance)::numeric,m.unit_hpp_snapshot
 from prefix m left join erp.customers c on c.id=m.customer_id
$$;

create function cp7_fg.ledger(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;purpose text;q text;off integer;n integer;pid uuid;lid uuid;location uuid;grade text;
 from_at timestamptz;to_at timestamptz;rows jsonb;total bigint;header jsonb;balances jsonb;cost jsonb;
begin
 if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('purpose','product_id','lot_id','location_id','quality_grade','q','from','to','offset','limit'))
  or not p_query ?& array['product_id','lot_id','location_id','quality_grade']
  or exists(select 1 from jsonb_each(p_query) e where e.key not in('offset','limit') and jsonb_typeof(e.value) not in('string','null'))
  or(p_query ? 'offset' and (jsonb_typeof(p_query->'offset')<>'number' or (p_query->>'offset')!~'^[0-9]{1,7}$'))
  or(p_query ? 'limit' and (jsonb_typeof(p_query->'limit')<>'number' or (p_query->>'limit')!~'^[0-9]{1,3}$')) then raise exception 'CP7_FG_QUERY';end if;
 purpose:=coalesce(p_query->>'purpose','CARD');if purpose not in('CARD','MOVEMENTS') then raise exception 'CP7_FG_PURPOSE';end if;
 a:=cp7_fg.access_now(purpose);pid:=(p_query->>'product_id')::uuid;lid:=(p_query->>'lot_id')::uuid;location:=(p_query->>'location_id')::uuid;grade:=p_query->>'quality_grade';
 q:=btrim(coalesce(p_query->>'q',''));off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);
 from_at:=(p_query->>'from')::timestamptz;to_at:=(p_query->>'to')::timestamptz;
 if pid is null or location is null or grade is null or length(grade)>40 or length(q)>120 or off not between 0 and 1000000 or n not between 1 and 100
  or(from_at is not null and not isfinite(from_at)) or(to_at is not null and(not isfinite(to_at) or to_at>statement_timestamp()))
  or(from_at is not null and to_at is not null and from_at>=to_at) then raise exception 'CP7_FG_QUERY';end if;
 select jsonb_build_object('product_id',x.product_id,'product_sku',x.product_sku,'commercial_sku',x.commercial_sku,'product_name',x.product_name,'size_code',x.size_code,'brand_name',x.brand_name,
  'lot_id',x.lot_id,'lot_number',x.lot_number,'location_id',x.location_id,'location_name',x.location_name,'quality_grade',x.quality_grade)
 into header from cp7_fg.positions('',true) x where x.product_id=pid and x.lot_id is not distinct from lid and x.location_id=location and x.quality_grade=grade;
 if header is null then raise exception using errcode='P0002',message='CP7_FG_POSITION_UNAVAILABLE';end if;
 if a->'can_value'='true'::jsonb then cost:=cp7_fg.lot_value(lid,1);end if;
 select jsonb_build_object('available_qty',coalesce(sum(x.qty_signed),0)::text,'reserved_qty',coalesce(sum(x.reservation_delta),0)::text,'physical_qty',coalesce(sum(x.physical_delta),0)::text,
  'quality',case when bool_or(x.available_balance<0 or x.reserved_balance<0 or x.physical_balance<0) then 'CONFLICT' else 'KNOWN' end)
 into balances from cp7_fg.ledger_rows(pid,lid,location,grade) x where to_at is null or x.physical_at<to_at;
 select count(*) into total from cp7_fg.ledger_rows(pid,lid,location,grade) x
 where(from_at is null or x.physical_at>=from_at) and(to_at is null or x.physical_at<to_at)
  and(q='' or strpos(lower(concat_ws(' ',x.source_type,x.source_id,x.customer_name,x.notes,x.movement_type,x.commercial_sku)),lower(q))>0);
 select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'physical_at',x.physical_at,'recorded_at',x.recorded_at,'movement_type',x.movement_type,
  'source_type',x.source_type,'source_id',x.source_id,'reversal_of_id',x.reversal_of_id,'customer_name',x.customer_name,'notes',x.notes,'book_order',x.book_order,
  'commercial_sku_at_transaction',x.commercial_sku,'qty_signed',x.qty_signed::text,'reservation_delta',x.reservation_delta::text,'physical_delta',x.physical_delta::text,
  'available_balance',x.available_balance::text,'reserved_balance',x.reserved_balance::text,'physical_balance',x.physical_balance::text)
  ||case when a->'can_value'='true'::jsonb then jsonb_build_object('valuation',jsonb_build_object('state',cost->'state',
   'unit_cost',case when cost->>'state'='KNOWN' then x.unit_hpp_snapshot::text end,'basis','CURRENT_RESTATED_MOVEMENT_SNAPSHOT')) else '{}'::jsonb end
  order by x.physical_at,x.recorded_at,x.id),'[]') into rows
 from(select * from cp7_fg.ledger_rows(pid,lid,location,grade) z
  where(from_at is null or z.physical_at>=from_at) and(to_at is null or z.physical_at<to_at)
   and(q='' or strpos(lower(concat_ws(' ',z.source_type,z.source_id,z.customer_name,z.notes,z.movement_type,z.commercial_sku)),lower(q))>0)
  order by z.physical_at,z.recorded_at,z.id limit n offset off)x;
 return jsonb_build_object('contract_version','cp7.fg-ledger.v1','purpose',purpose,'read_at',statement_timestamp(),'knowledge','CURRENT','financial_captured',a->'can_value',
  'position',header,'balances',balances,'balance_basis','COMPLETE_CHRONOLOGICAL_PREFIX_BEFORE_SEARCH_AND_PAGE',
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));
end $$;
create function public.erp_cp7_get_fg_ledger_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_fg.ledger(p_query)$$;
