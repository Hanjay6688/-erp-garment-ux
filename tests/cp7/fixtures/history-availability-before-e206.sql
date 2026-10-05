create function cp7_planning.history_availability(c jsonb,q jsonb)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC' as $$
with products as(select value p from jsonb_array_elements(c->'facts'->'products')),
stock as(select value m from jsonb_array_elements(c->'facts'->'stock')),
days as(select (q->>'from_date')::date+i d from generate_series(0,(q->>'through_date')::date-(q->>'from_date')::date)i),
grid as(select p,d,d::timestamp at time zone 'Asia/Jakarta'lo,(d+1)::timestamp at time zone 'Asia/Jakarta'hi from products cross join days),
balances as(
 select p,d,lo,hi,
  coalesce((select sum((m->>'qty_signed')::numeric)from stock where m->>'root_id'=p->>'root_id'
   and m->>'quality_grade'in('GRADE_A','GRADE_B')and(m->>'physical_at')::timestamptz<lo),0)start_pcs,
  (select min(running)from(select sum((m->>'qty_signed')::numeric)over(order by(m->>'physical_at')::timestamptz,(m->>'book_order')::numeric,m->>'id'rows unbounded preceding)running
   from stock where m->>'root_id'=p->>'root_id'and m->>'quality_grade'in('GRADE_A','GRADE_B')
    and(m->>'physical_at')::timestamptz>=lo and(m->>'physical_at')::timestamptz<hi)x)day_min
 from grid
)
select coalesce(jsonb_agg(jsonb_build_object('target_key',(p->>'root_id')||':'||(p->>'size_id'),
 'date',d::text,'revision','1','known_at',c->>'captured_at',
 'state',case when(p->>'established_at')::timestamptz>lo or start_pcs+least(coalesce(day_min,0),0)<0 then 'UNKNOWN'
  when start_pcs>0 and start_pcs+least(coalesce(day_min,0),0)>0 then 'AVAILABLE'else 'STOCKOUT'end,
 'refs',jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',p->>'id','revision','1')))
 order by p->>'root_id',d),'[]')from balances
$$;

