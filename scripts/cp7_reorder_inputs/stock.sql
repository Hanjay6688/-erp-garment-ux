-- The Native availability source as SQL aggregates, without collecting or
-- truncating raw movements into a 50,000-row JSON array. Every visible row
-- contributes. The availability states/ordering/knowledge boundary below
-- are the existing Native history_availability rules, tested against it.
-- This reader does not make an incomplete Native capture complete by itself.
create function cp7_reorder_inputs.stock_summary(products jsonb,p_at timestamptz,q jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare first_day date;last_day date;day_count integer;answer jsonb;
begin
 perform cp7_wip.fields(q,array['from_date','through_date','group_mode']);
 perform cp7_demand.items(products,5000);
 first_day:=cp7_demand.day(q->'from_date');last_day:=cp7_demand.day(q->'through_date');day_count:=last_day-first_day+1;
 if p_at is null or day_count<1 or last_day>=(p_at at time zone'Asia/Jakarta')::date
  or jsonb_array_length(products)*day_count>(cp7_analysis_stage.bounds()->>'job_history_cells')::bigint
  or q->>'group_mode'is null or q->>'group_mode'not in('AS_SOLD','RESTATED')then raise exception 'CP7_REORDER_STOCK_SCOPE_BOUND';end if;
 with product_rows as materialized(select value p,(value->>'established_at')::timestamptz established,
  jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',value->>'id','revision','1'))refs
  from jsonb_array_elements(products)),
 capture_clock as materialized(select cp7_planning.utc(p_at)known_at),
 roots as materialized(select distinct p->>'root_id'root_id from product_rows),
 all_moves as materialized(
  select m.id,coalesce(p.identity_root_id,p.id)::text root_id,m.physical_at,m.book_order,m.qty_signed qty,
   m.quality_grade,m.movement_type,m.reversal_of_id
  from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
  where coalesce(p.identity_root_id,p.id)::text in(select root_id from roots)
   and m.physical_at<=p_at and m.system_created_at<=p_at),
 stock as materialized(select *from all_moves where quality_grade in('GRADE_A','GRADE_B')),
 reserves as materialized(select id from all_moves where movement_type='SALE_RESERVE'),
 totals as materialized(select s.root_id,sum(s.qty)free,
  sum(s.qty)filter(where s.physical_at<first_day::timestamp at time zone'Asia/Jakarta')opening_qty,
  coalesce(sum(s.qty)filter(where s.movement_type<>'SALE_RESERVE'and r.id is null),0)physical
  from stock s left join reserves r on r.id=s.reversal_of_id group by s.root_id),
 opening as materialized(select root_id,opening_qty qty from totals),
 movements as materialized(select *,(physical_at at time zone'Asia/Jakarta')::date d from stock
  where physical_at>=first_day::timestamp at time zone'Asia/Jakarta'
   and physical_at<(last_day+1)::timestamp at time zone'Asia/Jakarta'),
 running as(select *,sum(qty)over(partition by root_id,d order by physical_at,book_order,id rows unbounded preceding)intraday from movements),
 daily as materialized(select root_id,d,sum(qty)qty,min(intraday)day_min from running group by root_id,d),
 days as(select first_day+i d from generate_series(0,day_count-1)i),
 root_grid as(select root_id,d from roots cross join days),
 balances as(
  select grid.root_id,grid.d,grid.d::timestamp at time zone'Asia/Jakarta'lo,
   coalesce(op.qty,0)+coalesce(sum(coalesce(dt.qty,0))over(partition by grid.root_id order by grid.d
    rows between unbounded preceding and 1 preceding),0)start_pcs,dt.day_min
  from root_grid grid left join opening op on op.root_id=grid.root_id left join daily dt on dt.root_id=grid.root_id and dt.d=grid.d),
 availability as materialized(select coalesce(jsonb_agg(jsonb_build_object('target_key',(p->>'root_id')||':'||(p->>'size_id'),
  'date',d::text,'revision','1','known_at',capture_clock.known_at,
  'state',case when established>lo or start_pcs+least(coalesce(day_min,0),0)<0 then'UNKNOWN'
   when start_pcs>0 and start_pcs+least(coalesce(day_min,0),0)>0 then'AVAILABLE'else'STOCKOUT'end,
  'refs',product_rows.refs)
  order by p->>'root_id',d),'[]')rows from balances join product_rows on p->>'root_id'=root_id cross join capture_clock),
 normalized_availability as materialized(select coalesce(jsonb_agg(x-'known_at'
  order by x->>'target_key',x->>'date'),'[]')rows from availability,jsonb_array_elements(availability.rows)x),
 current_rows as materialized(select coalesce(jsonb_agg(jsonb_build_object('target_key',(p->>'root_id')||':'||(p->>'size_id'),
  'root_id',p->>'root_id','size_id',p->>'size_id','free_pcs',coalesce(t.free,0)::text,'physical_pcs',coalesce(t.physical,0)::text)
  order by p->>'root_id'),'[]')rows from product_rows left join totals t on t.root_id=p->>'root_id')
 select jsonb_build_object('contract_version','cp7.reorder-stock-summary.v1','captured_at',cp7_planning.utc(p_at),'query',q,
  'raw_rows_read',(select count(*)from all_moves),'products',jsonb_array_length(products),'days',day_count,
  'availability',availability.rows,'current_stock',current_rows.rows,
  'history_data_hash',encode(extensions.digest(convert_to(jsonb_build_object('products',products,'query',q,
   'availability',normalized_availability.rows)::text,'UTF8'),'sha256'),'hex'),
  'data_hash',encode(extensions.digest(convert_to(jsonb_build_object('products',products,'query',q,
   'availability',normalized_availability.rows,
   'current_stock',current_rows.rows)::text,'UTF8'),'sha256'),'hex'),
  'raw_rows_truncated',false,'Native_capture_status_overridden',false,'apply_enabled',false,'production_go',false)
 into answer from availability cross join current_rows cross join normalized_availability;
 return answer;
end $$;
alter function cp7_reorder_inputs.stock_summary(jsonb,timestamptz,jsonb)owner to cp7_capture;
revoke all on function cp7_reorder_inputs.stock_summary(jsonb,timestamptz,jsonb)from public,anon,authenticated,service_role;
