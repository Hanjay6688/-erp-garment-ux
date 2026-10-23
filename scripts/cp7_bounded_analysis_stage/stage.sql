create schema cp7_bounded_analysis_stage authorization cp7_capture;
revoke all on schema cp7_bounded_analysis_stage from public,anon,authenticated,service_role;
create function cp7_bounded_analysis_stage.source_parts(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with source as materialized(select cp7_reorder_inputs.capture_baseline(p_products)c),
 parts as materialized(select c,cp7_supply_native.wip_source_parts((c->>'captured_at')::timestamptz)p from source)
 select jsonb_build_object('c',c||jsonb_build_object('production_sources',p->'source'),'proofs',p->'proofs')from parts
$$;
create function cp7_bounded_analysis_stage.schedule_source(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with source as materialized(select (cp7_bounded_analysis_stage.source_parts(p_products)->'c')c)
 select c||jsonb_build_object('schedule',cp7_schedule_native.source_at((c->>'captured_at')::timestamptz),
  'planning_time_bucket',cp7_planning.utc(date_trunc('minute',(c->>'captured_at')::timestamptz)))from source
$$;
create function cp7_bounded_analysis_stage.netting_source(p_products integer,p_match integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with source as materialized(select cp7_bounded_analysis_stage.schedule_source(p_products)c),
 wanted as materialized(
  select x->>'id'id from source,jsonb_array_elements(c->'facts'->'products')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'other'->'origins')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'other'->'bs')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'cutting'->'bs')x
 ),products as materialized(
  select p.id,coalesce(p.identity_root_id,p.id)root_id,p.model_id,p.size_id,p.brand_id,p.color_name,
   p.effective_from,p.effective_to,p.created_at
  from erp.products p join wanted w on w.id=p.id::text cross join source
  where p.created_at<=(c->>'captured_at')::timestamptz order by p.id limit p_match+1
 )select c||jsonb_build_object('matching_products',coalesce((select jsonb_agg(to_jsonb(p)order by p.id)from products p),'[]'))from source
$$;
create function cp7_bounded_analysis_stage.analysis_source(p_products integer,p_match integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with native as materialized(select cp7_bounded_analysis_stage.netting_source(p_products,p_match)c),
 engine as(select encode(extensions.digest(convert_to(string_agg(
  p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')signature
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname in('cp7_planning','cp7_profile','cp7_supply_native','cp7_schedule_native','cp7_netting_native','cp7_analysis_native','cp7_analysis_stage','cp7_fabric_native','cp7_wip','cp7_demand','cp7_baseline','cp7_models','cp7_finance','cp7_bounded_analysis_stage')
   or p.oid='erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure)
 select c||jsonb_build_object('analysis_engine_signature',signature,
  'material_source',cp7_analysis_native.material_source(c->'facts'->'products',(c->>'captured_at')::timestamptz),
  'fabric_source',cp7_fabric_native.source(c->'facts'->'products',(c->>'captured_at')::timestamptz))from native cross join engine
$$;
create function cp7_bounded_analysis_stage.native_work_fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts',
  'profiles',c->'profiles','production_policies',c->'production_policies'->'rows',
  'production_scope',c->'production_sources'->'scope',
  'production',c->'production_sources'->'facts')::text,'UTF8'),'sha256'),'hex')
$$;


create function cp7_bounded_analysis_stage.producer_hash()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),
  E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname in('cp7_bounded_analysis_stage','cp7_history_bounded','cp7_history_reference')and p.prokind='f'
$$;
create function cp7_bounded_analysis_stage.work_fingerprint(c jsonb)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare stock jsonb:=c->'bounded_stock_reference';producer text:=c->>'bounded_producer_hash';
begin
 if c->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v1'
  or c->>'bounded_reference_contract'is distinct from'cp7.bounded-analysis-reference.v1'
  or producer is null or producer!~'^[0-9a-f]{64}$'
  or stock->>'contract_version'is distinct from'cp7.native-stock-row-digest.v1'
  or stock->>'scope'is distinct from'ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS'
  or stock->'captured_at'is distinct from c->'captured_at'
  or stock->>'rows_sha256'is null or stock->>'rows_sha256'!~'^[0-9a-f]{64}$'
  or stock->>'row_count'is null or stock->>'row_count'!~'^(0|[1-9][0-9]{0,19})$'
  or stock->'raw_rows_truncated'is distinct from'false'::jsonb
  or stock->'raw_native_capture_status_overridden'is distinct from'false'::jsonb then
  raise exception 'CP7_BOUNDED_ANALYSIS_REFERENCE_SHAPE';end if;
 -- No capture clock or selected demand query enters work-calendar identity.
 return encode(extensions.digest(convert_to(jsonb_build_object('contract','cp7.bounded-work-source.v1',
  'native',cp7_bounded_analysis_stage.native_work_fingerprint(c),'full_stock_rows',stock->'rows_sha256',
  'producer',producer)::text,'UTF8'),'sha256'),'hex');
end $$;
create function cp7_bounded_analysis_stage.source(p_query jsonb,p_with_inputs boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare q jsonb;c jsonb;b jsonb:=cp7_analysis_stage.bounds();stock jsonb;summary jsonb;inputs jsonb;
 lo date;hi date;products integer;
begin
 if p_with_inputs is null then raise exception 'CP7_BOUNDED_ANALYSIS_CAPTURE_MODE';end if;
 q:=cp7_planning.history_query(p_query);
 c:=cp7_bounded_analysis_stage.analysis_source((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
   ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');
 products:=jsonb_array_length(c->'facts'->'products');
 if products>(b->>'job_targets')::integer then raise exception 'CP7_ANALYSIS_STAGED_TARGET_LIMIT';end if;
 lo:=cp7_demand.day(q->'from_date');hi:=cp7_demand.day(q->'through_date');
 if hi<lo or hi-lo>3660 or hi>=((c->>'captured_at')::timestamptz at time zone'Asia/Jakarta')::date
  or products::bigint*(hi-lo+1)>(b->>'job_history_cells')::bigint then raise exception 'CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE';end if;
 stock:=cp7_history_reference.stock_digest(c->'facts'->'products',(c->>'captured_at')::timestamptz);
 if p_with_inputs then
  if c->'stock_raw_omitted'='true'::jsonb or jsonb_array_length(c->'facts'->'stock')=50001 then
   summary:=cp7_reorder_inputs.stock_summary(c->'facts'->'products',(c->>'captured_at')::timestamptz,q);
  end if;
  inputs:=cp7_history_bounded.compile(c,q,summary,(b->>'job_targets')::integer);
  if inputs->>'coverage'is distinct from'COMPLETE'or inputs->'raw_native_capture_status'is distinct from c->'status'
   or inputs->'captured_at'is distinct from c->'captured_at'or inputs->'query'is distinct from q then
   raise exception 'CP7_BOUNDED_ANALYSIS_INPUT_BINDING';end if;
 end if;
 return c||jsonb_build_object('bounded_request_contract','cp7.bounded-analysis-request.v1',
  'bounded_reference_contract','cp7.bounded-analysis-reference.v1','bounded_query',q,
  'bounded_producer_hash',cp7_bounded_analysis_stage.producer_hash(),'bounded_stock_reference',stock,
  'bounded_history_inputs',inputs);
end $$;

alter function cp7_bounded_analysis_stage.source_parts(integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.source_parts(integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.schedule_source(integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.schedule_source(integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.netting_source(integer,integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.netting_source(integer,integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.analysis_source(integer,integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.analysis_source(integer,integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.native_work_fingerprint(jsonb) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.native_work_fingerprint(jsonb) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.work_fingerprint(jsonb) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.work_fingerprint(jsonb) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.producer_hash() owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.producer_hash() from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.source(jsonb,boolean) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.source(jsonb,boolean) from public,anon,authenticated,service_role;


create function cp7_bounded_analysis_stage.require_inputs(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare b jsonb:=c->'bounded_history_inputs';i jsonb:=b->'inputs';n integer:=jsonb_array_length(c->'facts'->'products');keys jsonb;
begin
 perform cp7_bounded_analysis_stage.work_fingerprint(c);
 if c->'bounded_query'is distinct from q or b->>'contract_version'is distinct from'cp7.bounded-history-inputs.v1'
  or b->>'coverage'is distinct from'COMPLETE' or b->'captured_at'is distinct from c->'captured_at'
  or b->'query'is distinct from q or b->'raw_native_capture_status'is distinct from c->'status'
  or b->'raw_native_status_overridden'is distinct from'false'::jsonb
  or i->>'contract_version'is distinct from'cp7.reorder-native-inputs.v1'
  or i->'captured_at'is distinct from c->'captured_at' or i->'query'is distinct from q
  or i->'products'is distinct from c->'facts'->'products'
  or i->>'source_hash'is null or i->>'source_hash'!~'^[0-9a-f]{64}$'
  or i->>'history_hash'is null or i->>'history_hash'!~'^[0-9a-f]{64}$'
  or jsonb_typeof(i->'history')is distinct from'array' or jsonb_typeof(i->'current_stock')is distinct from'array'
  or jsonb_typeof(i->'targets')is distinct from'array' then
  raise exception 'CP7_BOUNDED_ANALYSIS_INPUT_BINDING';end if;
 -- One actual Native result per product. Never accept missing or duplicate
 -- rows as zero, or a result for a different target/root/size.
 select coalesce(jsonb_object_agg((p->>'root_id')||':'||(p->>'size_id'),true),'{}')into keys
  from jsonb_array_elements(c->'facts'->'products')p;
 if exists(select 1 from jsonb_each(jsonb_build_object('history',i->'history','stock',i->'current_stock','targets',i->'targets'))a
  where jsonb_array_length(a.value)<>n or n<>(select count(distinct x->>'target_key')from jsonb_array_elements(a.value)x)
   or exists(select 1 from jsonb_array_elements(a.value)x where not(keys?(x->>'target_key'))))then
  raise exception 'CP7_BOUNDED_ANALYSIS_INPUT_TARGETS';end if;
 return i;
end $$;
create function cp7_bounded_analysis_stage.source_for(p_reference jsonb,p_query jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if p_reference?'bounded_request_contract'then
  if p_reference->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v1'
   or p_reference->'bounded_query'is distinct from p_query then raise exception 'CP7_BOUNDED_ANALYSIS_REFERENCE_SHAPE';end if;
  begin
   return cp7_bounded_analysis_stage.source(p_query,false);
  exception when raise_exception then
   if sqlerrm in('CP7_ANALYSIS_STAGED_TARGET_LIMIT','CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE')then
    raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';end if;
   raise;
  end;
 end if;
 return cp7_schedule_staged_review.current_source();
end $$;

create function cp7_bounded_analysis_stage.history_prep(c jsonb,q jsonb,p_targets integer,p_cells bigint,p_sales integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare cells bigint;hash text;targets jsonb;events jsonb;avail jsonb;v jsonb;known timestamptz;effective timestamptz;lo date;hi date;
 p jsonb;stock_order jsonb[]:='{}';events_clean boolean;avail_clean boolean;cuts jsonb;
begin
 perform cp7_bounded_analysis_stage.require_inputs(c,q);
 -- The single call's grid expression (same casts, same errors), its bound per job.
 cells:=jsonb_array_length(c->'facts'->'products')*((q->>'through_date')::date-(q->>'from_date')::date+1);
 if jsonb_array_length(c->'facts'->'products')>p_targets then raise exception 'CP7_ANALYSIS_STAGED_TARGET_LIMIT';end if;
 if cells>p_cells then raise exception 'CP7_PLANNING_HISTORY_GRID_LIMIT';end if;
 hash:=c#>>'{bounded_history_inputs,inputs,history_hash}';
 targets:=(select coalesce(jsonb_agg(jsonb_build_object('key',(value->>'root_id')||':'||(value->>'size_id'),
   'size_id',value->>'size_id','current_group_key',coalesce(value->'commercial'->0->>'sku_id',value->>'root_id'),
   'refs',jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',value->>'id','revision','1')))order by value->>'root_id'),'[]')from jsonb_array_elements(c->'facts'->'products'));
 events_clean:=cp7_analysis_stage.events_clean(c);
 if not events_clean then events:=cp7_planning.history_events(c);end if;
 avail_clean:=true; -- Complete prepared SQL history is sliced below; no raw-prefix availability.
 if not avail_clean then avail:=cp7_planning.history_availability(c,q);end if;
 v:=jsonb_build_object('contract_version','cp7.demand-input.v1','snapshot_id',hash,
  'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','known_as_of',c->>'captured_at','effective_as_of',c->>'captured_at',
  'from_date',q->'from_date','through_date',q->'through_date','history_complete',true,'group_mode',q->'group_mode',
  'targets',targets,'events','[]'::jsonb,'availability','[]'::jsonb);
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','known_as_of','effective_as_of','from_date','through_date','history_complete','group_mode','targets','events','availability']);
 perform cp7_demand.context(v,'cp7.demand-input.v1');
 known:=cp7_demand.instant(v->'known_as_of');effective:=cp7_demand.instant(v->'effective_as_of');
 lo:=cp7_demand.day(v->'from_date');hi:=cp7_demand.day(v->'through_date');
 if hi<lo or hi-lo>3660 or hi>=(effective at time zone 'Asia/Jakarta')::date then raise exception 'CP7_DEMAND_COMPLETE_DAYS_REQUIRED';end if;
 if jsonb_typeof(v->'history_complete') is distinct from 'boolean' or v->>'group_mode' not in ('AS_SOLD','RESTATED') or v->>'group_mode' is null then raise exception 'CP7_DEMAND_POLICY';end if;
 perform cp7_demand.items(v->'targets',p_targets);
 -- history_build's stock loop order (same statement).
 for p in select value from jsonb_array_elements(c->'facts'->'products')order by value->>'root_id'loop
  stock_order:=array_append(stock_order,p);
 end loop;
 -- Sale id ranges of at most p_sales sales each (ids are unique strings when clean).
 if events_clean then
  select coalesce(jsonb_agg(jsonb_build_array(f.lo,f.hi)order by f.k),'[]')into cuts from(
   select(s.i-1)/p_sales k,min(s.id)lo,max(s.id)hi from(select x->>'id' id,row_number()over(order by x->>'id')i
    from jsonb_array_elements(c->'facts'->'sales')x)s group by 1)f;
 end if;
 return jsonb_build_object('hash',hash,'targets',targets,'stock_order',to_jsonb(stock_order),'events_clean',events_clean,'events',events,
  'availability_clean',avail_clean,'availability',avail,'cuts',coalesce(cuts,'[]'::jsonb),'from',lo,'through',hi,
  'baseline_hash',c#>>'{bounded_history_inputs,inputs,source_hash}');
end $$;

create function cp7_bounded_analysis_stage.run_scenario_unit(j cp7_analysis_stage.jobs,u cp7_analysis_stage.units,c jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare b jsonb:=cp7_analysis_stage.bounds();g jsonb;val jsonb;out jsonb;v jsonb;idx integer;n integer;k integer;per integer;days integer;
 prepared jsonb;keys jsonb;roots jsonb;sub jsonb;avail jsonb;latest jsonb;rows jsonb;offs integer;cut jsonb;
begin
 if u.kind='HIST_PREP'then
  g:=cp7_bounded_analysis_stage.history_prep(c,j.query,(b->>'job_targets')::integer,(b->>'job_history_cells')::bigint,(b->>'sales_per_events_unit')::integer);
  -- A source that is not clean: the single path's whole events/availability.
  if not(g->>'events_clean')::boolean then
   insert into cp7_analysis_stage.target_rows select j.id,'HEV',x.o,null,x.v from jsonb_array_elements(g->'events')with ordinality x(v,o);
  end if;
  if not(g->>'availability_clean')::boolean then
   insert into cp7_analysis_stage.target_rows select j.id,'HAV',f.k,f.key,f.rows from(
    select row_number()over(order by min(x.o))::integer k,x.v->>'target_key' key,jsonb_agg(x.v order by x.o)rows
    from jsonb_array_elements(g->'availability')with ordinality x(v,o)group by x.v->>'target_key')f;
  end if;
  n:=jsonb_array_length(g->'targets');days:=(g->>'through')::date-(g->>'from')::date+1;idx:=1;
  -- One events unit per sale id range; a source that is not clean: one unit
  -- over the whole events array.
  for k in 0..greatest(jsonb_array_length(g->'cuts'),case when(g->>'events_clean')::boolean then 0 else 1 end)-1 loop
   insert into cp7_analysis_stage.units values(j.id,idx,'HIST_EVENTS',k,null,null);idx:=idx+1;end loop;
  insert into cp7_analysis_stage.units values(j.id,idx,'HIST_VALIDATE',0,null,null);idx:=idx+1;
  per:=greatest(1,(b->>'history_cells_per_unit')::integer/greatest(days,1));
  for k in 0..(n-1)/per loop exit when n=0;
   insert into cp7_analysis_stage.units values(j.id,idx,'HIST_ROWS',k,k*per+1,least(n,(k+1)*per));idx:=idx+1;end loop;
  -- At least one stock unit: its per-root sums read every stock row even
  -- without products, as history_build's do.
  per:=(b->>'targets_per_stock_unit')::integer;
  for k in 0..greatest(0,(n-1)/per)loop
   insert into cp7_analysis_stage.units values(j.id,idx,'HIST_STOCK',k,k*per+1,least(n,(k+1)*per));idx:=idx+1;end loop;
  per:=(b->>'targets_per_chunk')::integer;
  for k in 0..(n-1)/per loop exit when n=0;
   insert into cp7_analysis_stage.units values(j.id,idx,'BASE_ROWS',k,k*per+1,least(n,(k+1)*per));idx:=idx+1;end loop;
  insert into cp7_analysis_stage.units values(j.id,idx,'SUPPLY',0,null,null),(j.id,idx+1,'SCENARIO',0,null,null),(j.id,idx+2,'NET_PREP',0,null,null);
  update cp7_analysis_stage.jobs set unit_count=idx+3,targets_total=n where id=j.id;
  return g-'events'-'availability';
 end if;
 g:=cp7_analysis_stage.output(j.id,'HIST_PREP');
 if u.kind='HIST_EVENTS'then
  if(g->>'events_clean')::boolean then
   cut:=g->'cuts'->u.chunk;
   rows:=cp7_planning.history_events(cp7_analysis_stage.event_facts(c,cut->>0,cut->>1));
  else
   select coalesce(jsonb_agg(x.payload order by x.ord),'[]')into rows from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='HEV';
  end if;
  out:=cp7_analysis_stage.events_validate(jsonb_build_object('known_as_of',c->>'captured_at','effective_as_of',c->>'captured_at',
   'from_date',j.query->'from_date','through_date',j.query->'through_date','group_mode',j.query->'group_mode','targets',g->'targets','events',rows));
  -- The selected events of this chunk's lineages, per target (a target's
  -- lineages may lie in several chunks).
  insert into cp7_analysis_stage.target_rows select j.id,'HSEL',u.idx*100000+(row_number()over(order by e.key))::integer,e.key,e.value from jsonb_each(out->'by_target')e;
  return out-'by_target';
 end if;
 if u.kind='HIST_VALIDATE'then
  return cp7_analysis_stage.history_validate(jsonb_build_object('targets',g->'targets',
   'events',(select coalesce(sum((o.output->>'events')::bigint),0)from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
     where o.job_id=j.id and y.kind='HIST_EVENTS'),
   'errors',(select coalesce(jsonb_agg(o.output->'error'order by o.idx),'[]')from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
     where o.job_id=j.id and y.kind='HIST_EVENTS'and o.output?'error')));
 end if;
 val:=cp7_analysis_stage.output(j.id,'HIST_VALIDATE');
 if u.kind='HIST_ROWS'then
  select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into prepared
   from jsonb_array_elements(c#>'{bounded_history_inputs,inputs,history}')x;
  select coalesce(jsonb_agg(prepared->(g->'targets'->(k.i::integer-1)->>'key')order by k.pos),'[]')into rows
   from jsonb_array_elements_text(val->'key_order')with ordinality k(i,pos)
   where k.pos between u.lo and u.hi;
  if jsonb_array_length(rows)<>u.hi-u.lo+1 then raise exception 'CP7_BOUNDED_ANALYSIS_HISTORY_SLICE';end if;
  insert into cp7_analysis_stage.target_rows select j.id,'HIST',u.lo+x.o-1,x.v->>'target_key',x.v
   from jsonb_array_elements(rows)with ordinality x(v,o);
  days:=(g->>'through')::date-(g->>'from')::date+1;
  return jsonb_build_object('rows',jsonb_array_length(rows),'availability_rows',jsonb_array_length(rows)*days);
 end if;
 if u.kind='HIST_STOCK'then
  select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into prepared
   from jsonb_array_elements(c#>'{bounded_history_inputs,inputs,current_stock}')x;
  select coalesce(jsonb_agg(prepared->((p.product->>'root_id')||':'||(p.product->>'size_id'))order by p.o),'[]')into rows
   from jsonb_array_elements(g->'stock_order')with ordinality p(product,o)
   where p.o between u.lo and u.hi;
  if jsonb_array_length(rows)<>greatest(0,u.hi-u.lo+1)then raise exception 'CP7_BOUNDED_ANALYSIS_STOCK_SLICE';end if;
  insert into cp7_analysis_stage.target_rows select j.id,'STOCK',u.lo+x.o-1,x.v->>'target_key',x.v
   from jsonb_array_elements(rows)with ordinality x(v,o);
  return jsonb_build_object('rows',jsonb_array_length(rows));
 end if;
 if u.kind='BASE_ROWS'then
  rows:=cp7_analysis_stage.baseline_rows(c,
   (select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='HIST'and x.ord between u.lo and u.hi),
   (select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='STOCK'),g->>'baseline_hash');
  insert into cp7_analysis_stage.target_rows select j.id,'BASE',u.lo+x.o-1,x.v->>'target_key',x.v from jsonb_array_elements(rows)with ordinality x(v,o);
  return jsonb_build_object('rows',jsonb_array_length(rows));
 end if;
 if u.kind='SUPPLY'then return cp7_analysis_stage.supply(c);end if;
 if u.kind='SCENARIO'then
  -- The skeleton the later units read (the prototype's SCENARIO output shape).
  return jsonb_build_object('scenario',cp7_analysis_stage.schedule(c,cp7_analysis_stage.output(j.id,'SUPPLY')),'rows_null',false);
 end if;
 raise exception 'CP7_ANALYSIS_STAGE_UNKNOWN_UNIT';
end $$;
create function cp7_bounded_analysis_stage.request(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;jid uuid;jq jsonb;c jsonb;b jsonb:=cp7_analysis_stage.bounds();snap pg_snapshot;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);q:=cp7_planning.history_query(p_query);
 if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 jid:=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_request);
 if jid is not null then
  select x.query into jq from cp7_analysis_stage.jobs x where x.id=jid;
  if not exists(select 1 from cp7_analysis_stage.jobs x where x.id=jid
   and x.reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v1')then
   raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
  if jq<>q then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
  if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
  return cp7_analysis_stage.status(jid);
 end if;
 if exists(select 1 from cp7_analysis_native.runs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request)
  or exists(select 1 from cp7_analysis_jobs.jobs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request)then
  raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';
 end if;
 -- One statement: the reference and the snapshot it was read in (all of
 -- source_within is stable, so it reads in this statement's snapshot). A
 -- transaction that already wrote has rows the snapshot cannot place, so its
 -- mark is null and changes are then judged by recording time alone.
 select cp7_bounded_analysis_stage.source(q,true),
  case when pg_current_xact_id_if_assigned()is null then pg_current_snapshot()end into c,snap;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 -- More planned products than the job's declared capacity: refused here with
 -- the declared code, before any job or reference is kept (independent audit
 -- Fable F-AN-01: it used to become a FAILED job at unit 0 under another code).
 if jsonb_array_length(coalesce(c->'facts'->'products','[]'::jsonb))>(b->>'job_targets')::integer then
  raise exception using message='CP7_ANALYSIS_STAGED_TARGET_LIMIT',
   detail=jsonb_build_object('targets_limit',b->'job_targets','refused_at','REQUEST')::text;
 end if;
 jid:=cp7_analysis_stage.create_job((a->>'actor')::uuid,p_request,q,a,c);
 insert into cp7_analysis_stage.capture_marks(job_id,source_snapshot)values(jid,snap);
 return cp7_analysis_stage.status(jid);
end $$;
alter function cp7_bounded_analysis_stage.source_parts(integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.source_parts(integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.schedule_source(integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.schedule_source(integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.netting_source(integer,integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.netting_source(integer,integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.analysis_source(integer,integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.analysis_source(integer,integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.native_work_fingerprint(jsonb) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.native_work_fingerprint(jsonb) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.work_fingerprint(jsonb) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.work_fingerprint(jsonb) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.producer_hash() owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.producer_hash() from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.source(jsonb,boolean) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.source(jsonb,boolean) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.require_inputs(jsonb,jsonb) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.require_inputs(jsonb,jsonb) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.history_prep(jsonb,jsonb,integer,bigint,integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.history_prep(jsonb,jsonb,integer,bigint,integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.run_scenario_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units,jsonb) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.run_scenario_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units,jsonb) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.source_for(jsonb,jsonb) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.source_for(jsonb,jsonb) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.request(jsonb,uuid) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.request(jsonb,uuid) from public,anon,authenticated,service_role;
create or replace function cp7_supply_native.fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case when c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'
 then cp7_bounded_analysis_stage.work_fingerprint(c) else encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts',
  'profiles',c->'profiles','production_policies',c->'production_policies'->'rows',
  'production_scope',c->'production_sources'->'scope',
  'production',c->'production_sources'->'facts')::text,'UTF8'),'sha256'),'hex') end
$$;

create or replace function cp7_analysis_stage.run_scenario_unit(j cp7_analysis_stage.jobs,u cp7_analysis_stage.units,c jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare b jsonb:=cp7_analysis_stage.bounds();g jsonb;val jsonb;out jsonb;v jsonb;idx integer;n integer;k integer;per integer;days integer;
 keys jsonb;roots jsonb;sub jsonb;avail jsonb;latest jsonb;rows jsonb;offs integer;cut jsonb;
begin
 if c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'then
  return cp7_bounded_analysis_stage.run_scenario_unit(j,u,c);end if;
 if u.kind='HIST_PREP'then
  g:=cp7_analysis_stage.history_prep(c,j.query,(b->>'job_targets')::integer,(b->>'job_history_cells')::bigint,(b->>'sales_per_events_unit')::integer);
  -- A source that is not clean: the single path's whole events/availability.
  if not(g->>'events_clean')::boolean then
   insert into cp7_analysis_stage.target_rows select j.id,'HEV',x.o,null,x.v from jsonb_array_elements(g->'events')with ordinality x(v,o);
  end if;
  if not(g->>'availability_clean')::boolean then
   insert into cp7_analysis_stage.target_rows select j.id,'HAV',f.k,f.key,f.rows from(
    select row_number()over(order by min(x.o))::integer k,x.v->>'target_key' key,jsonb_agg(x.v order by x.o)rows
    from jsonb_array_elements(g->'availability')with ordinality x(v,o)group by x.v->>'target_key')f;
  end if;
  n:=jsonb_array_length(g->'targets');days:=(g->>'through')::date-(g->>'from')::date+1;idx:=1;
  -- One events unit per sale id range; a source that is not clean: one unit
  -- over the whole events array.
  for k in 0..greatest(jsonb_array_length(g->'cuts'),case when(g->>'events_clean')::boolean then 0 else 1 end)-1 loop
   insert into cp7_analysis_stage.units values(j.id,idx,'HIST_EVENTS',k,null,null);idx:=idx+1;end loop;
  insert into cp7_analysis_stage.units values(j.id,idx,'HIST_VALIDATE',0,null,null);idx:=idx+1;
  per:=greatest(1,(b->>'history_cells_per_unit')::integer/greatest(days,1));
  for k in 0..(n-1)/per loop exit when n=0;
   insert into cp7_analysis_stage.units values(j.id,idx,'HIST_ROWS',k,k*per+1,least(n,(k+1)*per));idx:=idx+1;end loop;
  -- At least one stock unit: its per-root sums read every stock row even
  -- without products, as history_build's do.
  per:=(b->>'targets_per_stock_unit')::integer;
  for k in 0..greatest(0,(n-1)/per)loop
   insert into cp7_analysis_stage.units values(j.id,idx,'HIST_STOCK',k,k*per+1,least(n,(k+1)*per));idx:=idx+1;end loop;
  per:=(b->>'targets_per_chunk')::integer;
  for k in 0..(n-1)/per loop exit when n=0;
   insert into cp7_analysis_stage.units values(j.id,idx,'BASE_ROWS',k,k*per+1,least(n,(k+1)*per));idx:=idx+1;end loop;
  insert into cp7_analysis_stage.units values(j.id,idx,'SUPPLY',0,null,null),(j.id,idx+1,'SCENARIO',0,null,null),(j.id,idx+2,'NET_PREP',0,null,null);
  update cp7_analysis_stage.jobs set unit_count=idx+3,targets_total=n where id=j.id;
  return g-'events'-'availability';
 end if;
 g:=cp7_analysis_stage.output(j.id,'HIST_PREP');
 if u.kind='HIST_EVENTS'then
  if(g->>'events_clean')::boolean then
   cut:=g->'cuts'->u.chunk;
   rows:=cp7_planning.history_events(cp7_analysis_stage.event_facts(c,cut->>0,cut->>1));
  else
   select coalesce(jsonb_agg(x.payload order by x.ord),'[]')into rows from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='HEV';
  end if;
  out:=cp7_analysis_stage.events_validate(jsonb_build_object('known_as_of',c->>'captured_at','effective_as_of',c->>'captured_at',
   'from_date',j.query->'from_date','through_date',j.query->'through_date','group_mode',j.query->'group_mode','targets',g->'targets','events',rows));
  -- The selected events of this chunk's lineages, per target (a target's
  -- lineages may lie in several chunks).
  insert into cp7_analysis_stage.target_rows select j.id,'HSEL',u.idx*100000+(row_number()over(order by e.key))::integer,e.key,e.value from jsonb_each(out->'by_target')e;
  return out-'by_target';
 end if;
 if u.kind='HIST_VALIDATE'then
  return cp7_analysis_stage.history_validate(jsonb_build_object('targets',g->'targets',
   'events',(select coalesce(sum((o.output->>'events')::bigint),0)from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
     where o.job_id=j.id and y.kind='HIST_EVENTS'),
   'errors',(select coalesce(jsonb_agg(o.output->'error'order by o.idx),'[]')from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
     where o.job_id=j.id and y.kind='HIST_EVENTS'and o.output?'error')));
 end if;
 val:=cp7_analysis_stage.output(j.id,'HIST_VALIDATE');
 if u.kind='HIST_ROWS'then
  select coalesce(jsonb_agg(g->'targets'->(k.i::integer-1)order by k.pos),'[]')into v
   from jsonb_array_elements_text(val->'key_order')with ordinality k(i,pos)where k.pos between u.lo and u.hi;
  select coalesce(jsonb_object_agg(t->>'key',true),'{}')into keys from jsonb_array_elements(v)t;
  if(g->>'availability_clean')::boolean then
   -- The chunk's products and their roots' stock rows (array order kept).
   select coalesce(jsonb_agg(p order by o),'[]'),coalesce(jsonb_object_agg(p->>'root_id',true),'{}')into sub,roots
    from jsonb_array_elements(c->'facts'->'products')with ordinality x(p,o)where keys?((p->>'root_id')||':'||(p->>'size_id'));
   avail:=cp7_planning.history_availability(jsonb_build_object('captured_at',c->'captured_at','facts',jsonb_build_object('products',sub,
    'stock',(select coalesce(jsonb_agg(m order by o),'[]')from jsonb_array_elements(c->'facts'->'stock')with ordinality x(m,o)where roots?(m->>'root_id')))),j.query);
  else
   select coalesce(jsonb_agg(e order by x.ord,e.o),'[]')into avail from cp7_analysis_stage.target_rows x cross join lateral jsonb_array_elements(x.payload)with ordinality e(e,o)
    where x.job_id=j.id and x.kind='HAV'and keys?x.key;
  end if;
  select coalesce(jsonb_object_agg(e->>'lineage_key',e),'{}')into latest from cp7_analysis_stage.target_rows x cross join lateral jsonb_array_elements(x.payload)e
   where x.job_id=j.id and x.kind='HSEL'and keys?x.key;
  rows:=cp7_analysis_stage.history_rows(jsonb_build_object('known_as_of',c->>'captured_at','from_date',j.query->'from_date','through_date',j.query->'through_date',
   'history_complete',true,'targets',v,'keys',keys,'latest',latest,'availability',avail));
  insert into cp7_analysis_stage.target_rows select j.id,'HIST',u.lo+x.o-1,x.v->>'target_key',x.v from jsonb_array_elements(rows)with ordinality x(v,o);
  return jsonb_build_object('rows',jsonb_array_length(rows),'availability_rows',jsonb_array_length(avail));
 end if;
 if u.kind='HIST_STOCK'then
  rows:=cp7_analysis_stage.history_stock(c,(select coalesce(jsonb_agg(x.p order by x.o),'[]')from jsonb_array_elements(g->'stock_order')with ordinality x(p,o)
   where x.o between u.lo and u.hi),g->>'hash');
  insert into cp7_analysis_stage.target_rows select j.id,'STOCK',u.lo+x.o-1,x.v->>'target_key',x.v from jsonb_array_elements(rows)with ordinality x(v,o);
  return jsonb_build_object('rows',jsonb_array_length(rows));
 end if;
 if u.kind='BASE_ROWS'then
  rows:=cp7_analysis_stage.baseline_rows(c,
   (select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='HIST'and x.ord between u.lo and u.hi),
   (select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='STOCK'),g->>'baseline_hash');
  insert into cp7_analysis_stage.target_rows select j.id,'BASE',u.lo+x.o-1,x.v->>'target_key',x.v from jsonb_array_elements(rows)with ordinality x(v,o);
  return jsonb_build_object('rows',jsonb_array_length(rows));
 end if;
 if u.kind='SUPPLY'then return cp7_analysis_stage.supply(c);end if;
 if u.kind='SCENARIO'then
  -- The skeleton the later units read (the prototype's SCENARIO output shape).
  return jsonb_build_object('scenario',cp7_analysis_stage.schedule(c,cp7_analysis_stage.output(j.id,'SUPPLY')),'rows_null',false);
 end if;
 raise exception 'CP7_ANALYSIS_STAGE_UNKNOWN_UNIT';
end $$;
create or replace function cp7_analysis_stage.analysis_skeleton(c jsonb,q jsonb,p_run uuid,a jsonb,scenario jsonb,alloc jsonb,matching jsonb,
 meta jsonb,identity_unknown boolean,tag text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare wip jsonb:=scenario->'wip';p jsonb;e jsonb;eta jsonb;part jsonb;k text;part_hash text;count_facts integer:=0;part_count integer;
 plan_refs jsonb:='[]';plan_aids jsonb:='[]';assumptions jsonb;sources jsonb;recommendations jsonb;edges jsonb;actions jsonb;timeline jsonb;
 models jsonb;materials jsonb;metrics jsonb;warnings jsonb;dependencies jsonb:='[]';known_targets jsonb;v jsonb;
 complete boolean:=(c->>'status'='COMPLETE'or(case when c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'
 then cp7_bounded_analysis_stage.require_inputs(c,q)is not null else false end))and wip->>'status'='COMPLETE';hash text:=cp7_analysis_native.fingerprint(c);
 allocation_known boolean:=alloc->>'status'='SCENARIO';allocated numeric;load numeric;
 scenario_revision bigint:=coalesce((c->'schedule'->>'revision')::bigint,0);
 schedule_assumption jsonb:='[]';fabric_assumptions jsonb[]:='{}';edges_acc jsonb[]:='{}';sources_acc jsonb[]:='{}';
 etas_by_position jsonb;inputs_by_source jsonb;directed_source_keys jsonb;source_inputs jsonb;
 warnings0 jsonb:='["MATERIAL_FEASIBILITY_NOT_PROVEN","ADAPTIVE_MODEL_PROMOTION_NOT_PROVEN","FINANCIAL_DOMAIN_NOT_CAPTURED"]';
begin
 if c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'and c->>'status'='INCOMPLETE'then
  warnings0:=warnings0||'"RAW_NATIVE_CAPTURE_INCOMPLETE_COMPLETE_SQL_HISTORY_INPUTS"'::jsonb;end if;
 if scenario_revision>9007199254740991 then raise exception 'CP7_ANALYSIS_REVISION_RANGE';end if;
 select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)into etas_by_position from(
  select x->>'position_key'k,jsonb_agg(x->'result'order by o)items from jsonb_array_elements(coalesce(scenario->'etas','[]'))with ordinality e(x,o)
  where x->>'position_key'is not null group by x->>'position_key')i;
 select coalesce(jsonb_object_agg(i.k,true),'{}'::jsonb)into directed_source_keys from(
  select distinct x->>'key'k from jsonb_array_elements(coalesce(matching->'sources','[]'))x
  where x->>'key'is not null and x->>'confirmed_target'is not null)i;
 if c->'schedule'<>'null'::jsonb then
  plan_aids:=jsonb_build_array(c->'schedule'->>'plan_id');
  plan_refs:=jsonb_build_array(cp7_wip.ref('PLANNING_SCHEDULE',c->'schedule'->>'plan_id',c->'schedule'->>'revision'));
  schedule_assumption:=jsonb_build_array(jsonb_build_object('id',c->'schedule'->>'plan_id',
   'label','Jadwal, waktu sisa dan perkiraan hasil bagus yang dipilih; bukan hasil produksi aktual',
   'origin','OWNER_INPUT','confirmed_for_operation',false));
 end if;
 select coalesce(jsonb_object_agg(t.key,true),'{}'::jsonb)into known_targets from jsonb_array_elements_text(meta->'known_keys')t(key);
 for e in select value from jsonb_array_elements(coalesce(alloc->'allocation'->'edges','[]'))loop
  if not(known_targets? (e->>'target_key'))then raise exception 'CP7_ANALYSIS_EDGE_TARGET_UNPROVEN';end if;
  eta:=etas_by_position->(e->>'position_key');
  if jsonb_array_length(eta)>1 then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  eta:=eta->0;
  edges_acc:=array_append(edges_acc,jsonb_build_array(jsonb_build_object('source_key',e->'position_key','target_key',e->'target_key','size_id',e->'size_id',
   'input_qty',cp7_analysis_native.fact(e->>'input_pcs','PCS',e->'refs'),
   'projected_output_qty',cp7_analysis_native.fact(e->>'projected_good_pcs','PCS',e->'refs',plan_aids),
   'match',e->'match','eligible_at',eta->'eta','assumption_ids',plan_aids,'refs',e->'refs')));
 end loop;
 select coalesce(jsonb_agg(x.value order by p.ordinality,x.ordinality),'[]'::jsonb)into edges
  from unnest(edges_acc)with ordinality p(items,ordinality)cross join lateral jsonb_array_elements(p.items)with ordinality x;
 select coalesce(jsonb_object_agg(i.k,i.v),'{}'::jsonb)into inputs_by_source from(
  select x->>'source_key'k,jsonb_agg(x->'input_qty'->'value')v from jsonb_array_elements(edges)x where x->>'source_key'is not null group by x->>'source_key')i;
 for p in select value from jsonb_array_elements(coalesce(wip->'positions','[]'))
  where value->'eligible_company_wip'='true'::jsonb and cp7_wip.pcs(value->'remaining_pcs')>0 loop
  eta:=etas_by_position->(p->>'key');
  if jsonb_array_length(eta)>1 then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  eta:=eta->0;source_inputs:=inputs_by_source->(p->>'key');
  select sum(i.qty::numeric)into allocated from jsonb_array_elements_text(coalesce(source_inputs,'[]'))i(qty);
  sources_acc:=array_append(sources_acc,jsonb_build_array(jsonb_build_object('source_key',p->'key','size_id',p->'size_id','stage',p->'stage',
   'supply_kind',case when directed_source_keys?(p->>'key')then 'DIRECTED'else 'CANDIDATE'end,
   'physical_remaining',cp7_analysis_native.fact(p->>'remaining_pcs','PCS',p->'refs'),
   'eligible_input',cp7_analysis_native.fact(p->'projection'->>'eligible_input_pcs','PCS',p->'refs',plan_aids),
   'eligible_projected',cp7_analysis_native.fact(p->'projection'->>'projected_good_pcs','PCS',p->'refs',plan_aids),
   'allocated',cp7_analysis_native.fact(case when allocation_known then coalesce(allocated,0)::text else null end,'PCS',p->'refs'),
   'eta',eta->'eta','eta_basis',case when eta->>'status'='CONDITIONAL'then 'ASSUMED'when eta->>'status'='KNOWN'then 'CONFIRMED_PLAN'else 'UNKNOWN'end,'refs',p->'refs')));
 end loop;
 for part in select value from jsonb_array_elements(c->'fabric_source'->'selected')loop
  if known_targets?(part->>'target_key')then
   fabric_assumptions:=array_append(fabric_assumptions,cp7_analysis_stage.fabric_assumption(part));
  end if;
 end loop;
 for k,part in select key,value from jsonb_each(jsonb_build_object('native_operational',c->'facts','native_production',c->'production_sources'->'facts',
  'native_matching',c->'matching_products','planning_profiles',c->'profiles','production_policy',c->'production_policies'->'rows',
  'selected_schedule',c->'schedule','dated_capacity_clock',c->'planning_time_bucket','analysis_engine',c->'analysis_engine_signature',
  'native_material_requirements',(c->'material_source')-'captured_at',
  'selected_fabric_requirements',(c->'fabric_source')-'captured_at'))loop
  part_hash:=encode(extensions.digest(convert_to(part::text,'UTF8'),'sha256'),'hex');
  if k in('native_operational','native_production')then
   with recursive objects(value)as(select part union all
    select x.value from objects o cross join lateral jsonb_each(case when jsonb_typeof(o.value)='object'then o.value else '{}'end)x
    where jsonb_typeof(x.value)='object')
   select coalesce(sum(jsonb_array_length(x.value)),0)::integer into part_count
    from objects o cross join lateral jsonb_each(case when jsonb_typeof(o.value)='object'then o.value else '{}'end)x
    where jsonb_typeof(x.value)='array';
  else part_count:=case jsonb_typeof(part)when 'array'then jsonb_array_length(part)when 'object'then 1 else 0 end;end if;
  count_facts:=count_facts+part_count;
  dependencies:=dependencies||jsonb_build_array(jsonb_build_object('domain',k,'revision',part_hash,
   'completeness',case when complete then 'COMPLETE'else 'PARTIAL'end,'fact_count',part_count,'source_hash',part_hash));
 end loop;
 select sum((x->>'existing_load_minutes')::numeric)into load from jsonb_array_elements(coalesce(scenario->'capacity'->'inputs'->'windows','[]'))x;
 -- Per-target arrays: their sentinel (or nothing), in build's order.
 assumptions:=schedule_assumption||cp7_analysis_stage.sentinel(meta,tag,'assumptions')||to_jsonb(fabric_assumptions);
 select coalesce(jsonb_agg(x.value order by p.ordinality,x.ordinality),'[]'::jsonb)into sources
  from unnest(sources_acc)with ordinality p(items,ordinality)cross join lateral jsonb_array_elements(p.items)with ordinality x;
 recommendations:=cp7_analysis_stage.sentinel(meta,tag,'recommendations');actions:=cp7_analysis_stage.sentinel(meta,tag,'actions');
 timeline:=cp7_analysis_stage.sentinel(meta,tag,'timeline');models:=cp7_analysis_stage.sentinel(meta,tag,'models');
 materials:=case when meta->'materials_null'='true'::jsonb then null else cp7_analysis_stage.sentinel(meta,tag,'materials')end;
 metrics:=cp7_analysis_stage.sentinel(meta,tag,'metrics');warnings:=warnings0||cp7_analysis_stage.sentinel(meta,tag,'warnings');
 v:=jsonb_build_object('contract_version','cp7.analysis.v2','run_id',p_run,'status',case when complete then 'PARTIAL'else 'BLOCKED'end,
  'snapshot',jsonb_build_object('snapshot_id',c->>'captured_at','effective_as_of',c->>'captured_at','known_as_of',c->>'captured_at','generated_at',c->>'captured_at','timezone','Asia/Jakarta',
   'knowledge_mode','CURRENT','capture_complete',complete,'fact_count',count_facts,'source_hash',hash),
  'versions',jsonb_build_object('engine',c->'analysis_engine_signature','policy',cp7_supply_native.fingerprint(c),'models','native-available-history-fallback-1',
   'template','native-report-1','access_epoch',encode(extensions.digest(convert_to(a::text,'UTF8'),'sha256'),'hex')),
  'scope',jsonb_build_object('actor_scope_id',a->>'actor','allocation_scope_id','GLOBAL_NATIVE_PLANNING','display_filter','ALL'),
  'quality',jsonb_build_object('quantity',case when complete then 'COMPLETE'else 'UNKNOWN'end,
   'demand',case when jsonb_array_length(recommendations)=0 or meta->'demand_unknown'='true'::jsonb then 'UNKNOWN'else 'ASSUMED'end,
   'identity',case when identity_unknown then 'UNKNOWN'when complete then 'COMPLETE'else 'UNKNOWN'end,
   'timing',case when scenario->'capacity'->>'status'='SCENARIO'then 'ASSUMED'else 'UNKNOWN'end,'materials','UNKNOWN',
   'capacity',case when scenario->'capacity'->>'status'='SCENARIO'then 'ASSUMED'else 'UNKNOWN'end,'financial','UNKNOWN'),
  'scenario',jsonb_build_object('id',coalesce(c->'schedule'->>'plan_id','unreviewed-'||hash),'version',scenario_revision,'kind','CONDITIONAL','assumption_ids',plan_aids),
  'sources',sources,'recommendations',recommendations,'timeline',timeline,'actions',actions,'financial_readiness','BLOCKED',
  'stale',jsonb_build_object('is_stale',false,'reasons','[]'::jsonb),'assumptions',assumptions,'dependencies',dependencies,
  'policy_basis',jsonb_build_object('lead_time_new_days',cp7_analysis_native.fact(null,'DAY','[]'),'review_days',cp7_analysis_native.fact(null,'DAY','[]'),
   'buffer_mode','DAYS','buffer_days',cp7_analysis_native.fact(null,'DAY','[]'),'service_target',cp7_analysis_native.fact(null,'PROBABILITY','[]'),
   'rounding_multiple',cp7_analysis_native.fact(null,'PCS','[]')),
  'demand_models',models,'material_needs',materials,
  'capacity_checks',jsonb_build_array(jsonb_build_object('stage','SELECTED_HOMOGENEOUS_CENTRE','calendar_version',coalesce(c->'schedule'->>'plan_id','UNREVIEWED'),
   'available',cp7_analysis_native.fact(scenario->'capacity'->>'capacity_pcs','PCS',plan_refs,plan_aids),
   'existing_load',cp7_analysis_native.fact(load::text,'MINUTE',plan_refs,plan_aids),'feasible_new',cp7_analysis_native.fact(null,'PCS',plan_refs),
   'status',case when scenario->'capacity'->>'status'='SCENARIO'then 'ASSUMED'else 'UNKNOWN'end)),
  'metrics',metrics,'plan_comparisons','[]'::jsonb,'generation_warnings',warnings,'allocation_edges',edges);
 return cp7_analysis_native.finance_apply(v,c);
end $$;
create or replace function cp7_analysis_stage.check_source(p_run uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare r record;a jsonb;hash text;c jsonb;b jsonb:=cp7_analysis_stage.bounds();
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 select j.source_hash,j.reference,j.query into r from cp7_analysis_stage.jobs j where j.run_id=p_run and j.actor=(a->>'actor')::uuid and j.state='DONE';
 hash:=r.source_hash;
 if hash is null then raise exception using errcode='42501',message='CP7_ANALYSIS_RUN_UNAVAILABLE';end if;
 perform cp7_analysis_stage.require_kept(j.id)from cp7_analysis_stage.jobs j where j.run_id=p_run;
 begin
  if r.reference?'bounded_request_contract'then c:=cp7_bounded_analysis_stage.source_for(r.reference,r.query);
  else c:=cp7_analysis_native.source_within((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
  ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');end if;
 exception when serialization_failure then
  if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
  return jsonb_build_object('source_state','ARCHIVED_STALE','checked_at',cp7_planning.utc(statement_timestamp()));
 end;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return jsonb_build_object('source_state',case when cp7_analysis_native.fingerprint(c)=hash then 'UNCHANGED'else 'ARCHIVED_STALE'end,
  'checked_at',c->'captured_at');
end $$;
create or replace function cp7_schedule_staged_review.workspace(p_source_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r record;c jsonb;hash text;plan jsonb;outcome jsonb;
 p jsonb;bound_id text;bound_root text;model text;choices jsonb;requirements jsonb:='[]';
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 select j.run_id id,j.id job_id,j.state job_state,j.query,j.reference facts,j.captured_at,j.source_hash analysis_source_hash,
  cp7_supply_native.fingerprint(j.reference)dependency_hash,
  jsonb_build_object('wip',cp7_wip.normalize_production(j.reference->'production_sources'))result
 into r from cp7_analysis_stage.jobs j where j.request_id=p_source_request and j.actor=(a->>'actor')::uuid and j.state in('RUNNING','DONE','FAILED');
 if r.id is null then raise exception using errcode='42501',message='CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE';end if;
 perform cp7_analysis_stage.require_kept(r.job_id);
 c:=cp7_bounded_analysis_stage.source_for(r.facts,r.query);hash:=cp7_supply_native.fingerprint(c);plan:=cp7_schedule_native.source_at((c->>'captured_at')::timestamptz);
 -- Form guidance belongs to the immutable source being reviewed. A fresh
 -- source check must not silently rebind quantities or an unfinished form.
 for p in select value from jsonb_array_elements(r.result->'wip'->'positions')
  where cp7_schedule_native.route(value->>'stage')is not null and cp7_wip.pcs(value->'remaining_pcs')>0
  order by value->>'key'loop
  bound_id:=case split_part(p->>'pool_key',':',1)
   when 'OPEN'then(select x->>'product_id'from jsonb_array_elements(r.facts->'production_sources'->'facts'->'other'->'origins')x
    where x->>'id'=split_part(p->>'pool_key',':',2))
   when 'NONPO'then(select x->>'product_id'from jsonb_array_elements(r.facts->'production_sources'->'facts'->'other'->'bs')x
    where x->>'id'=split_part(p->>'pool_key',':',2))else null end;
  select coalesce(x.identity_root_id,x.id)::text into bound_root from erp.products x
   where x.id::text=bound_id and x.created_at<=(r.facts->>'captured_at')::timestamptz;
  model:=cp7_schedule_native.position_model(r.facts,p);
  select coalesce(jsonb_agg(jsonb_build_object('target_key',(x->>'root_id')||':'||(x->>'size_id'),
   'product_version_id',x->'id','sku',x->'sku','product_name',x->'product_name')order by x->>'root_id'),'[]')into choices
   from jsonb_array_elements(r.facts->'facts'->'products')x
   where p->'eligible_company_wip'='true'::jsonb and x->>'size_id'=p->>'size_id'and x->>'model_id'=model
    and(bound_root is null or x->>'root_id'=bound_root);
  requirements:=requirements||jsonb_build_array(jsonb_build_object('position_key',p->'key','pool_key',p->'pool_key',
   'stage',p->'stage','size_id',p->'size_id','ownership',p->'ownership','eligible_company_wip',p->'eligible_company_wip',
   'remaining_pcs',p->'remaining_pcs','remaining_route',cp7_schedule_native.route(p->>'stage'),'target_candidates',choices));
 end loop;
 outcome:=jsonb_build_object('contract_version','cp7.planning-schedule-staged.v1','source_run',r.id,'source_request_id',p_source_request,'analysis_state',r.job_state,'current_source_hash',hash,
  'source_hash',r.dependency_hash,'captured_at',cp7_planning.utc(r.captured_at),'staged_review_contract','cp7.schedule-staged-review.v1','analysis_source_hash',r.analysis_source_hash,'history_capture_state',r.facts->'status','production_capture_state',r.result#>'{wip,status}','position_requirements',requirements,
  'source_state',case when hash=r.dependency_hash and cp7_analysis_native.fingerprint(c)=r.analysis_source_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end,
  'plan',plan,'revision',coalesce(plan->>'revision','0'),
  'plan_state',case when plan='null'::jsonb then 'UNREVIEWED'when plan->>'source_hash'=hash then 'SELECTED_ASSUMPTIONS'else 'SOURCE_CHANGED'end,
  'production_go',false);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 if r.facts->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'then
  outcome:=outcome||jsonb_build_object('contract_version','cp7.planning-schedule-staged-bounded.v1',
   'bounded_request_contract',r.facts->'bounded_request_contract','bounded_reference_contract',r.facts->'bounded_reference_contract',
   'history_input_coverage',r.facts#>'{bounded_history_inputs,coverage}');end if;
 return outcome;
end $$;
create or replace function cp7_schedule_staged_review.save(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_schedule_native.commands%rowtype;run record;
 p cp7_schedule_native.plans%rowtype;c jsonb;wip jsonb;hash text;revision bigint;expected bigint;reason text;config jsonb;outcome jsonb;
 selected jsonb;position jsonb;bound_id text;bound_root text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(true);if p_request is null then raise exception 'CP7_SCHEDULE_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p_payload,array['source_run','source_hash','expected_revision','config','reason','staged_review_contract']);
 if p_payload->>'staged_review_contract'is distinct from'cp7.schedule-staged-review.v1'then raise exception 'CP7_SCHEDULE_STAGED_CONTRACT';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:SCHEDULE:REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 select *into old from cp7_schedule_native.commands where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if old.payload<>p_payload then raise exception 'CP7_SCHEDULE_REQUEST_CHANGED';end if;return old.result;
 end if;
 if jsonb_typeof(p_payload->'expected_revision')is distinct from 'string'
  or p_payload->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'
  or jsonb_typeof(p_payload->'source_hash')is distinct from 'string'or p_payload->>'source_hash'!~'^[0-9a-f]{64}$'then
  raise exception 'CP7_SCHEDULE_REVIEW';end if;
 expected:=(p_payload->>'expected_revision')::bigint;
 perform pg_advisory_xact_lock(hashtextextended('CP7:SCHEDULE:GLOBAL',0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 select coalesce(max(x.revision),0)into revision from cp7_schedule_native.plans x;
 if expected<>revision then raise exception 'CP7_SCHEDULE_REVISION_CHANGED';end if;
 select j.run_id id,j.id job_id,j.state job_state,j.reference facts,j.query,j.source_hash analysis_source_hash,
  cp7_supply_native.fingerprint(j.reference)dependency_hash
 into run from cp7_analysis_stage.jobs j where j.run_id=(p_payload->>'source_run')::uuid
  and j.actor=(a->>'actor')::uuid and j.state in('RUNNING','DONE','FAILED');
 if run.id is null then raise exception using errcode='42501',message='CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE';end if;
 perform cp7_analysis_stage.require_kept(run.job_id);
 c:=cp7_bounded_analysis_stage.source_for(run.facts,run.query);hash:=cp7_supply_native.fingerprint(c);
 if hash<>run.dependency_hash or hash<>p_payload->>'source_hash'
  or cp7_analysis_native.fingerprint(c)<>run.analysis_source_hash then raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';end if;
 wip:=cp7_wip.normalize_production(c->'production_sources');config:=cp7_schedule_native.validate(p_payload->'config',c,wip);
 -- A selected destination is metadata, never authority to move a physically
 -- bound opening/non-PO source to a different product root with the same model.
 for selected in select value from jsonb_array_elements(config->'positions')where value->'target_key'<>'null'::jsonb loop
  position:=(select value from jsonb_array_elements(wip->'positions')where value->>'key'=selected->>'position_key');
  bound_id:=case split_part(position->>'pool_key',':',1)
   when 'OPEN'then(select x->>'product_id'from jsonb_array_elements(c->'production_sources'->'facts'->'other'->'origins')x
    where x->>'id'=split_part(position->>'pool_key',':',2))
   when 'NONPO'then(select x->>'product_id'from jsonb_array_elements(c->'production_sources'->'facts'->'other'->'bs')x
    where x->>'id'=split_part(position->>'pool_key',':',2))else null end;
  select coalesce(x.identity_root_id,x.id)::text into bound_root from erp.products x
   where x.id::text=bound_id and x.created_at<=(c->>'captured_at')::timestamptz;
  if bound_root is not null and selected->>'target_key'<>bound_root||':'||(position->>'size_id')then
   raise exception 'CP7_SCHEDULE_NATIVE_TARGET_BOUND';end if;
 end loop;
 reason:=btrim(p_payload->>'reason');if jsonb_typeof(p_payload->'reason')is distinct from 'string'or reason is null or length(reason)not between 1 and 1000 then
  raise exception 'CP7_SCHEDULE_REASON';end if;
 insert into cp7_schedule_native.plans(revision,source_run,source_hash,config,reason,actor,request_id)
 values(revision+1,run.id,hash,config,reason,(a->>'actor')::uuid,p_request)returning *into p;
 outcome:=jsonb_build_object('contract_version','cp7.planning-schedule-staged-outcome.v1','plan_id',p.id,'revision',p.revision::text,
  'source_hash',hash,'request_id',p_request,'quality','SELECTED_ASSUMPTIONS','staged_review_contract','cp7.schedule-staged-review.v1','source_run',run.id,'production_go',false);
 if run.facts->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'then
  outcome:=outcome||jsonb_build_object('contract_version','cp7.planning-schedule-staged-bounded-outcome.v1',
   'bounded_request_contract',run.facts->'bounded_request_contract','bounded_reference_contract',run.facts->'bounded_reference_contract');end if;
 insert into cp7_schedule_native.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p_payload,outcome);
 if cp7_supply_native.fingerprint(cp7_bounded_analysis_stage.source_for(run.facts,run.query))<>hash then
  raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';
 end if;
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 return outcome;
end $$;
create or replace function cp7_analysis_stage.request(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;jid uuid;jq jsonb;c jsonb;b jsonb:=cp7_analysis_stage.bounds();snap pg_snapshot;
begin
 if p_query?'initial_auto'then
  if p_request is not null or jsonb_typeof(p_query)is distinct from'object'then raise exception 'CP7_INITIAL_MODE';end if;
  if jsonb_typeof(p_query->'initial_auto')is distinct from'string'
   or p_query->>'initial_auto'not in('STATUS','ENSURE')
   or (select count(*)from jsonb_object_keys(p_query))<>1 then raise exception 'CP7_INITIAL_MODE';end if;
  return cp7_initial_analysis.current(p_query->>'initial_auto'='ENSURE');
 end if;
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);q:=cp7_planning.history_query(p_query);
 if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 jid:=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_request);
 if jid is not null then
  select x.query into jq from cp7_analysis_stage.jobs x where x.id=jid;
  if exists(select 1 from cp7_analysis_stage.jobs x where x.id=jid and x.reference?'bounded_request_contract')then
   raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
  if jq<>q then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
  if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
  return cp7_analysis_stage.status(jid);
 end if;
 if exists(select 1 from cp7_analysis_native.runs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request)
  or exists(select 1 from cp7_analysis_jobs.jobs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request)then
  raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';
 end if;
 -- One statement: the reference and the snapshot it was read in (all of
 -- source_within is stable, so it reads in this statement's snapshot). A
 -- transaction that already wrote has rows the snapshot cannot place, so its
 -- mark is null and changes are then judged by recording time alone.
 select cp7_analysis_native.source_within((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
  ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED'),
  case when pg_current_xact_id_if_assigned()is null then pg_current_snapshot()end into c,snap;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 -- More planned products than the job's declared capacity: refused here with
 -- the declared code, before any job or reference is kept (independent audit
 -- Fable F-AN-01: it used to become a FAILED job at unit 0 under another code).
 if jsonb_array_length(coalesce(c->'facts'->'products','[]'::jsonb))>(b->>'job_targets')::integer then
  raise exception using message='CP7_ANALYSIS_STAGED_TARGET_LIMIT',
   detail=jsonb_build_object('targets_limit',b->'job_targets','refused_at','REQUEST')::text;
 end if;
 jid:=cp7_analysis_stage.create_job((a->>'actor')::uuid,p_request,q,a,c);
 insert into cp7_analysis_stage.capture_marks(job_id,source_snapshot)values(jid,snap);
 return cp7_analysis_stage.status(jid);
end $$;
grant create on schema public to cp7_capture;
create function public.erp_cp7_request_bounded_staged_analysis_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$select cp7_bounded_analysis_stage.request(p_query,p_request)$$;
alter function public.erp_cp7_request_bounded_staged_analysis_v1(jsonb,uuid) owner to cp7_capture;
revoke all on function public.erp_cp7_request_bounded_staged_analysis_v1(jsonb,uuid) from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_request_bounded_staged_analysis_v1(jsonb,uuid) to authenticated;
revoke create on schema public from cp7_capture;
