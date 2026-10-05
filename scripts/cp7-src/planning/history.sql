create function cp7_planning.history_availability(c jsonb,q jsonb)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC' as $$
-- Parse the whole immutable Native stock collection once. Build each WIB day's
-- ordered movement prefix once, then carry its total into the following days.
-- The opening balance, intraday minimum, grade basis and knowledge boundary
-- remain the same; no source row, clock, root, day or decimal is truncated.
with products as materialized(select value p from jsonb_array_elements(c->'facts'->'products')),
roots as materialized(select distinct p->>'root_id'root_id from products),
stock as materialized(select m->>'root_id'root_id,(m->>'physical_at')::timestamptz physical_at,
 (m->>'book_order')::numeric book_order,m->>'id'id,(m->>'qty_signed')::numeric qty
 from jsonb_array_elements(c->'facts'->'stock')m where m->>'quality_grade'in('GRADE_A','GRADE_B')),
days as(select (q->>'from_date')::date+i d from generate_series(0,(q->>'through_date')::date-(q->>'from_date')::date)i),
opening as materialized(select root_id,sum(qty)qty from stock
 where physical_at<(q->>'from_date')::date::timestamp at time zone 'Asia/Jakarta' group by root_id),
movements as materialized(select *, (physical_at at time zone 'Asia/Jakarta')::date d from stock
 where physical_at>=(q->>'from_date')::date::timestamp at time zone 'Asia/Jakarta'
  and physical_at<((q->>'through_date')::date+1)::timestamp at time zone 'Asia/Jakarta'),
running as(select *,sum(qty)over(partition by root_id,d order by physical_at,book_order,id rows unbounded preceding)intraday
 from movements),
daily as materialized(select root_id,d,sum(qty)qty,min(intraday)day_min from running group by root_id,d),
root_grid as(select root_id,d from roots cross join days),
balances as(
 select g.root_id,g.d,g.d::timestamp at time zone 'Asia/Jakarta'lo,
  coalesce(o.qty,0)+coalesce(sum(coalesce(v.qty,0))over(partition by g.root_id order by g.d
   rows between unbounded preceding and 1 preceding),0)start_pcs,v.day_min
 from root_grid g left join opening o on o.root_id=g.root_id left join daily v on v.root_id=g.root_id and v.d=g.d
)
select coalesce(jsonb_agg(jsonb_build_object('target_key',(p->>'root_id')||':'||(p->>'size_id'),
 'date',d::text,'revision','1','known_at',c->>'captured_at',
 'state',case when(p->>'established_at')::timestamptz>lo or start_pcs+least(coalesce(day_min,0),0)<0 then 'UNKNOWN'
  when start_pcs>0 and start_pcs+least(coalesce(day_min,0),0)>0 then 'AVAILABLE'else 'STOCKOUT'end,
 'refs',jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',p->>'id','revision','1')))
 order by p->>'root_id',d),'[]')from balances join products on p->>'root_id'=root_id
$$;

create function cp7_planning.history_build(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC' as $$
declare input jsonb;result jsonb;p jsonb;stock jsonb;target text;refs jsonb;drafts jsonb;
 current_physical numeric;native_available numeric;availability jsonb;current_rows jsonb:='[]';hash text;
begin
 if c->>'status'is distinct from 'COMPLETE'then raise exception 'CP7_PLANNING_CAPTURE_INCOMPLETE';end if;
 if jsonb_array_length(c->'facts'->'products')*((q->>'through_date')::date-(q->>'from_date')::date+1)>100000 then raise exception 'CP7_PLANNING_HISTORY_GRID_LIMIT';end if;
 hash:=encode(extensions.digest(convert_to((c->'facts')::text,'UTF8'),'sha256'),'hex');
 input:=jsonb_build_object('contract_version','cp7.demand-input.v1','snapshot_id',hash,
  'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','known_as_of',c->>'captured_at','effective_as_of',c->>'captured_at',
  'from_date',q->'from_date','through_date',q->'through_date','history_complete',true,'group_mode',q->'group_mode',
  'targets',(select coalesce(jsonb_agg(jsonb_build_object('key',(value->>'root_id')||':'||(value->>'size_id'),
   'size_id',value->>'size_id','current_group_key',coalesce(value->'commercial'->0->>'sku_id',value->>'root_id'),
   'refs',jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',value->>'id','revision','1')))order by value->>'root_id'),'[]')from jsonb_array_elements(c->'facts'->'products')),
  'events',cp7_planning.history_events(c),'availability',cp7_planning.history_availability(c,q));
 result:=cp7_demand.history(input);
 for p in select value from jsonb_array_elements(c->'facts'->'products')order by value->>'root_id'loop
  target:=(p->>'root_id')||':'||(p->>'size_id');
  refs:=jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',p->>'id','revision','1'));
  select coalesce(sum((value->>'qty_signed')::numeric),0)into native_available from jsonb_array_elements(c->'facts'->'stock')
   where value->>'root_id'=p->>'root_id'and value->>'quality_grade'in('GRADE_A','GRADE_B');
  -- Native draft reservation movements already reduce sellable stock. Remove
  -- those movements AND their linked releases before the single kernel draft
  -- subtraction. Posted SALE movements remain in FG; never subtract twice.
  select coalesce(sum((m.value->>'qty_signed')::numeric),0)into current_physical from jsonb_array_elements(c->'facts'->'stock')m
   where m.value->>'root_id'=p->>'root_id'and m.value->>'quality_grade'in('GRADE_A','GRADE_B')
    and m.value->>'movement_type'<>'SALE_RESERVE'
    and not exists(select 1 from jsonb_array_elements(c->'facts'->'stock')orig
     where orig.value->>'id'=m.value->>'reversal_of_id'and orig.value->>'movement_type'='SALE_RESERVE');
  select coalesce(jsonb_agg(jsonb_build_object('lineage_key',value->>'id','qty_pcs',value->>'qty_pcs',
   'refs',jsonb_build_array(jsonb_build_object('kind','SALE_ITEM','id',value->>'id','revision',value->>'revision')))order by value->>'id'),'[]')into drafts
   from jsonb_array_elements(c->'facts'->'sales')where value->>'root_id'=p->>'root_id'and value->>'status'='DRAFT';
  availability:=cp7_demand.availability(jsonb_build_object('contract_version','cp7.available-input.v1',
   'snapshot_id',hash,'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','target_key',target,'size_id',p->>'size_id',
   'fg_basis','ON_HAND_AFTER_POSTED','fg_pcs',current_physical::text,'open_drafts',drafts,
   'residual_future_pcs','0','refs',refs));
  if(availability->>'available_fg_pcs')::numeric<>native_available or native_available<0 then raise exception 'CP7_PLANNING_NATIVE_RESERVATION_MISMATCH';end if;
  current_rows:=current_rows||jsonb_build_array(jsonb_build_object('target_key',target,'root_id',p->>'root_id',
   'size_id',p->>'size_id','sku',p->>'sku','product_name',p->>'product_name',
   'is_active',(p->>'is_active')::boolean,'grade_basis','NATIVE_SELLABLE_GRADE_A_AND_B','availability',availability,
   'projection_basis','CURRENT_STOCK_ONLY_NO_FORECAST','native_available_pcs',native_available::text,'refs',refs));
 end loop;
 return jsonb_build_object('contract_version','cp7.native-demand-history.v1','scope','GLOBAL_CURRENT_PHYSICAL_ROOTS',
  'capture_complete',true,'captured_at',c->'captured_at','source_hash',hash,'history',result,
  'current_stock',current_rows,'availability_knowledge_basis','CURRENT_CAPTURE_RESTATED_LEDGER',
  'training_known_at',c->'captured_at','model_eligibility','HISTORICAL_AVAILABILITY_KNOWLEDGE_NOT_BACKFILLED',
  'versions',jsonb_build_object('producer','native-demand-1','history','demand-1','availability','availability-1'),
  'production_go',false);
end $$;

create function cp7_planning.serve_history(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC' as $$
declare a jsonb;r cp7_planning.history_runs%rowtype;live jsonb;hash text;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();
 select * into r from cp7_planning.history_runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_PLANNING_RUN_UNAVAILABLE';end if;
 live:=cp7_planning.history_source();hash:=encode(extensions.digest(convert_to((live->'facts')::text,'UTF8'),'sha256'),'hex');
 outcome:=r.result||jsonb_build_object('run_id',r.id,'request_id',r.request_id,
  'source_state',case when live->>'status'='COMPLETE'and hash=r.dependency_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end);
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PLANNING_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function cp7_planning.capture_history(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC' as $$
declare a jsonb;q jsonb;r cp7_planning.history_runs%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();q:=cp7_planning.history_query(p_query);
 if p_request is null then raise exception 'CP7_PLANNING_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:HISTORY:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PLANNING_ACCESS_CHANGED';end if;
 select * into r from cp7_planning.history_runs where actor=(a->>'actor')::uuid and request_id=p_request;
 if r.id is not null then
  if r.query<>q then raise exception 'CP7_PLANNING_REQUEST_CHANGED';end if;
  return cp7_planning.serve_history(r.id);
 end if;
 with source as materialized(select cp7_planning.history_source()c),
 calculated as materialized(select c,cp7_planning.history_build(c,q)result from source)
 insert into cp7_planning.history_runs(actor,request_id,query,captured_at,access_at_capture,facts,result,dependency_hash)
 select(a->>'actor')::uuid,p_request,q,(c->>'captured_at')::timestamptz,a,c->'facts',result,
  encode(extensions.digest(convert_to((c->'facts')::text,'UTF8'),'sha256'),'hex')from calculated returning * into r;
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PLANNING_ACCESS_CHANGED';end if;
 return cp7_planning.serve_history(r.id);
end $$;

create function public.erp_cp7_capture_demand_history_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_planning.capture_history(p_query,p_request)$$;
create function public.erp_cp7_read_demand_history_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_planning.serve_history(p_run)$$;
