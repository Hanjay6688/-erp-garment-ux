create or replace function cp7_analysis_stage.history_prep(c jsonb,q jsonb,p_targets integer,p_cells bigint,p_sales integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare cells bigint;hash text;targets jsonb;events jsonb;avail jsonb;v jsonb;known timestamptz;effective timestamptz;lo date;hi date;
 p jsonb;stock_order jsonb[]:='{}';events_clean boolean;avail_clean boolean;cuts jsonb;
begin
 if c->>'status'is distinct from 'COMPLETE'then raise exception 'CP7_PLANNING_CAPTURE_INCOMPLETE';end if;
 -- The single call's grid expression (same casts, same errors), its bound per job.
 cells:=jsonb_array_length(c->'facts'->'products')*((q->>'through_date')::date-(q->>'from_date')::date+1);
 if jsonb_array_length(c->'facts'->'products')>p_targets then raise exception 'CP7_ANALYSIS_STAGED_TARGET_LIMIT';end if;
 if cells>p_cells then raise exception 'CP7_PLANNING_HISTORY_GRID_LIMIT';end if;
 hash:=encode(extensions.digest(convert_to((c->'facts')::text,'UTF8'),'sha256'),'hex');
 targets:=(select coalesce(jsonb_agg(jsonb_build_object('key',(value->>'root_id')||':'||(value->>'size_id'),
   'size_id',value->>'size_id','current_group_key',coalesce(value->'commercial'->0->>'sku_id',value->>'root_id'),
   'refs',jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',value->>'id','revision','1')))order by value->>'root_id'),'[]')from jsonb_array_elements(c->'facts'->'products'));
 events_clean:=cp7_analysis_stage.events_clean(c);
 if not events_clean then events:=cp7_planning.history_events(c);end if;
 avail_clean:=cp7_analysis_stage.availability_clean(c,q);
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
  'baseline_hash',encode(extensions.digest(convert_to(jsonb_build_object('native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows')::text,'UTF8'),'sha256'),'hex'));
end $$;
