-- Correction presentation only. Every Native movement remains immutable.
-- Filter the physical lot BEFORE grouping: an allocation changing lots must
-- restore the old lot and debit the new lot on their separate cards.
create function cp7_fg.corrected_ledger_rows(p_product uuid,p_lot uuid,p_location uuid,p_grade text)returns setof jsonb
language sql stable security invoker set search_path=''as $$
 with members as materialized(
  select m.*,coalesce(link.origin_id,m.id)origin_id,link.correction_id,link.recorded_at correction_recorded_at,
   case when m.movement_type='SALE_RESERVE'or original.movement_type='SALE_RESERVE'then-m.qty_signed else 0 end reservation_delta
  from erp.fg_stock_movements m left join cp7_fg.correction_movements link on link.member_id=m.id
   left join erp.fg_stock_movements original on original.id=m.reversal_of_id
  where m.product_id=p_product and m.lot_id is not distinct from p_lot
   and m.location_id=p_location and m.quality_grade=p_grade and m.physical_at<=statement_timestamp()
 ),effective as materialized(
  select origin_id,sum(qty_signed)available_delta,sum(reservation_delta)reservation_delta,
   count(distinct correction_id)correction_count,max(correction_recorded_at)correction_recorded_at,
   jsonb_agg(jsonb_build_object('id',id,'physical_at',physical_at,'recorded_at',system_created_at,
    'lot_id',lot_id,'source_type',source_type,'source_id',source_id,'reversal_of_id',reversal_of_id,
    'available_delta',qty_signed::text,'reservation_delta',reservation_delta::text)
    order by system_created_at,id)audit_movements
  from members group by origin_id
 ),sources as materialized(
  select original.*,e.available_delta,e.reservation_delta,e.correction_count,e.correction_recorded_at,e.audit_movements,
   case when original.lot_id is not distinct from p_lot then original.qty_signed else 0 end original_available_delta,
   case when original.lot_id is not distinct from p_lot and(original.movement_type='SALE_RESERVE'or reversed.movement_type='SALE_RESERVE')
    then-original.qty_signed else 0 end original_reserved_delta
  from effective e join erp.fg_stock_movements original on original.id=e.origin_id
   left join erp.fg_stock_movements reversed on reversed.id=original.reversal_of_id
 ),prefix as(
  select s.*,sum(available_delta)over chronology available_balance,sum(reservation_delta)over chronology reserved_balance
  from sources s window chronology as(order by physical_at,system_created_at,id rows unbounded preceding)
 )
 select jsonb_build_object('id',p.id,'physical_at',p.physical_at,'recorded_at',p.system_created_at,
  'movement_type',p.movement_type,'source_type',p.source_type,'source_id',p.source_id,'reversal_of_id',p.reversal_of_id,
  'customer_name',c.customer_name,'notes',p.notes,'book_order',p.book_order::text,
  'commercial_sku_at_transaction',erp.bf_commercial_sku_at_v1(p.product_id,p.physical_at),
  'qty_signed',p.available_delta::text,'reservation_delta',p.reservation_delta::text,
  'physical_delta',(p.available_delta+p.reservation_delta)::text,'available_balance',p.available_balance::text,
  'reserved_balance',p.reserved_balance::text,'physical_balance',(p.available_balance+p.reserved_balance)::text,
  'original_physical_delta',(p.original_available_delta+p.original_reserved_delta)::text,
  'correction_count',p.correction_count::text,'correction_recorded_at',p.correction_recorded_at,
  'audit_movements',p.audit_movements)
 from prefix p left join erp.customers c on c.id=p.customer_id
$$;

create function cp7_fg.corrected_ledger(p_query jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''as $$
declare a jsonb;purpose text;q text;off integer;n integer;pid uuid;lid uuid;location uuid;grade text;
 from_at timestamptz;to_at timestamptz;rows jsonb;total bigint;header jsonb;balances jsonb;cost jsonb;
begin
 if jsonb_typeof(p_query)is distinct from 'object'or exists(select 1 from jsonb_object_keys(p_query)k where k not in('purpose','product_id','lot_id','location_id','quality_grade','q','from','to','offset','limit'))
  or not p_query ?& array['product_id','lot_id','location_id','quality_grade']
  or exists(select 1 from jsonb_each(p_query)e where e.key not in('offset','limit')and jsonb_typeof(e.value)not in('string','null'))
  or(p_query ? 'offset'and(jsonb_typeof(p_query->'offset')<>'number'or(p_query->>'offset')!~'^[0-9]{1,7}$'))
  or(p_query ? 'limit'and(jsonb_typeof(p_query->'limit')<>'number'or(p_query->>'limit')!~'^[0-9]{1,3}$'))then raise exception 'CP7_FG_QUERY';end if;
 purpose:=coalesce(p_query->>'purpose','CARD');if purpose not in('CARD','MOVEMENTS')then raise exception 'CP7_FG_PURPOSE';end if;
 a:=cp7_fg.access_now(purpose);pid:=(p_query->>'product_id')::uuid;lid:=(p_query->>'lot_id')::uuid;location:=(p_query->>'location_id')::uuid;grade:=p_query->>'quality_grade';
 q:=btrim(coalesce(p_query->>'q',''));off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);
 from_at:=(p_query->>'from')::timestamptz;to_at:=(p_query->>'to')::timestamptz;
 if pid is null or location is null or grade is null or length(grade)>40 or length(q)>120 or off not between 0 and 1000000 or n not between 1 and 100
  or(from_at is not null and not isfinite(from_at))or(to_at is not null and(not isfinite(to_at)or to_at>statement_timestamp()))
  or(from_at is not null and to_at is not null and from_at>=to_at)then raise exception 'CP7_FG_QUERY';end if;
 select jsonb_build_object('product_id',x.product_id,'product_sku',x.product_sku,'commercial_sku',x.commercial_sku,'product_name',x.product_name,'size_code',x.size_code,'brand_name',x.brand_name,
  'lot_id',x.lot_id,'lot_number',x.lot_number,'location_id',x.location_id,'location_name',x.location_name,'quality_grade',x.quality_grade)
 into header from cp7_fg.positions('',true)x where x.product_id=pid and x.lot_id is not distinct from lid and x.location_id=location and x.quality_grade=grade;
 if header is null then raise exception using errcode='P0002',message='CP7_FG_POSITION_UNAVAILABLE';end if;
 if a->'can_value'='true'::jsonb then cost:=cp7_fg.lot_value(lid,1);end if;
 with complete as materialized(select value r from cp7_fg.corrected_ledger_rows(pid,lid,location,grade)value),
 filtered as materialized(select r from complete where(from_at is null or(r->>'physical_at')::timestamptz>=from_at)
  and(to_at is null or(r->>'physical_at')::timestamptz<to_at)
  and(q=''or strpos(lower(concat_ws(' ',r->>'source_type',r->>'source_id',r->>'customer_name',r->>'notes',r->>'movement_type',r->>'commercial_sku_at_transaction')),lower(q))>0)),
 page as(select r from filtered order by(r->>'physical_at')::timestamptz,(r->>'recorded_at')::timestamptz,r->>'id'limit n offset off)
 select(select count(*)from filtered),
  coalesce(jsonb_agg(r||case when a->'can_value'='true'::jsonb then jsonb_build_object('valuation',jsonb_build_object('state',cost->'state',
   'unit_cost',case when cost->>'state'='KNOWN'then cost->>'unit_cost'end,'basis','CURRENT_RESTATED_MOVEMENT_SNAPSHOT'))else '{}'::jsonb end
   order by(r->>'physical_at')::timestamptz,(r->>'recorded_at')::timestamptz,r->>'id'),'[]'),
  (select jsonb_build_object('available_qty',coalesce(sum((r->>'qty_signed')::numeric),0)::text,
   'reserved_qty',coalesce(sum((r->>'reservation_delta')::numeric),0)::text,'physical_qty',coalesce(sum((r->>'physical_delta')::numeric),0)::text,
   'quality',case when bool_or((r->>'available_balance')::numeric<0 or(r->>'reserved_balance')::numeric<0 or(r->>'physical_balance')::numeric<0)then 'CONFLICT'else 'KNOWN'end)
   from complete where to_at is null or(r->>'physical_at')::timestamptz<to_at)
 into total,rows,balances from page;
 return jsonb_build_object('contract_version','cp7.fg-ledger.v2','purpose',purpose,'read_at',statement_timestamp(),'knowledge','CURRENT','financial_captured',a->'can_value',
  'position',header,'balances',balances,'balance_basis','COMPLETE_CHRONOLOGICAL_PREFIX_BEFORE_SEARCH_AND_PAGE',
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end));
end $$;
create function public.erp_cp7_get_fg_ledger_v2(p_query jsonb)returns jsonb
language sql stable security definer set search_path=''as $$select cp7_fg.corrected_ledger(p_query)$$;
grant create on schema public to cp7_fg_read;
alter function cp7_fg.corrected_ledger_rows(uuid,uuid,uuid,text)owner to cp7_fg_read;
alter function cp7_fg.corrected_ledger(jsonb)owner to cp7_fg_read;
alter function public.erp_cp7_get_fg_ledger_v2(jsonb)owner to cp7_fg_read;
revoke create on schema public from cp7_fg_read;
revoke all on function cp7_fg.corrected_ledger_rows(uuid,uuid,uuid,text),cp7_fg.corrected_ledger(jsonb)from public,anon,authenticated,service_role,cp7_capture;
revoke all on function public.erp_cp7_get_fg_ledger_v2(jsonb)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_fg_ledger_v2(jsonb)to authenticated;
