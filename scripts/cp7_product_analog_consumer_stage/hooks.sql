create or replace function cp7_baseline_native.source_within(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with c as materialized(select cp7_planning.history_source_within(p_products)value),
 roots as(select array_agg((p->>'root_id')::uuid order by p->>'root_id')ids from c,jsonb_array_elements(value->'facts'->'products')p)
 select value||jsonb_build_object('product_analog_choices',cp7_product_analog_consumer.capture(value),
  'analog_consumer_engine',cp7_product_analog_consumer.engine_hash(),'profiles',cp7_profile.source(coalesce(ids,array[]::uuid[]),(value->>'captured_at')::timestamptz),
  'production_policies',cp7_identity.workspace_data(coalesce((select array_agg(distinct(s->>'sku_id')::uuid)
   from jsonb_array_elements(value->'facts'->'products')p cross join lateral jsonb_array_elements(p->'commercial')s),array[]::uuid[]),
   (value->>'captured_at')::timestamptz))from c cross join roots
$$;

create or replace function cp7_reorder_inputs.capture_baseline(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with c as materialized(select cp7_reorder_inputs.capture_history(p_products)value),
 roots as(select array_agg((p->>'root_id')::uuid order by p->>'root_id')ids from c,jsonb_array_elements(value->'facts'->'products')p)
 select value||jsonb_build_object('product_analog_choices',cp7_product_analog_consumer.capture(value),
  'analog_consumer_engine',cp7_product_analog_consumer.engine_hash(),'profiles',cp7_profile.source(coalesce(ids,array[]::uuid[]),(value->>'captured_at')::timestamptz),
  'production_policies',cp7_identity.workspace_data(coalesce((select array_agg(distinct(s->>'sku_id')::uuid)
   from jsonb_array_elements(value->'facts'->'products')p cross join lateral jsonb_array_elements(p->'commercial')s),array[]::uuid[]),
   (value->>'captured_at')::timestamptz))from c cross join roots
$$;

create or replace function cp7_baseline_native.build(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare h jsonb;r jsonb;cfg jsonb;p jsonb;stock jsonb;estimate jsonb;target jsonb;manual jsonb;own jsonb;
 refs jsonb;profile_refs jsonb;hash text;total numeric;sd numeric;policy jsonb;state text;rows jsonb[]:='{}';root text;
 profiles jsonb;profiles_repeated jsonb;stocks jsonb;stocks_repeated jsonb;policies jsonb;
begin
 h:=cp7_planning.history_build(c,q);
 hash:=encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine')::text,'UTF8'),'sha256'),'hex');
 rows:=array(select value from jsonb_array_elements(cp7_product_analog_consumer.baseline_rows(c,h->'history'->'rows',h->'current_stock',hash,cp7_product_analog_consumer.prepare(c,h->'history'->'rows',q)))order by value->>'target_key');
 return jsonb_build_object('contract_version',case when exists(select 1 from jsonb_array_elements(c->'profiles')x where x#>>'{config,buffer_mode}'='STATISTICAL')then'cp7.native-baseline.v2'else'cp7.native-baseline.v1'end,'captured_at',c->>'captured_at',
  'source_hash',hash,'scope','GLOBAL_CURRENT_PHYSICAL_ROOTS','history_run_result',h,
  'rows',to_jsonb(rows),'target_basis',case when exists(select 1 from jsonb_array_elements(c->'profiles')x where x#>>'{config,buffer_mode}'='STATISTICAL')then'UNIFIED_TARGET_WITH_SELECTED_PROFILE_ASSUMPTIONS'else'DAYS_WITH_SELECTED_PROFILE_ASSUMPTIONS'end,'apply_enabled',false,
  'model_basis','BASELINE_ADAPTIVE_PROMOTION_NOT_PROVEN','production_go',false);
end $$;

create or replace function cp7_analysis_stage.baseline_rows(c jsonb,history_rows jsonb,current_stock jsonb,hash text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 return cp7_product_analog_consumer.baseline_rows(c,history_rows,current_stock,hash,c->'analog_consumer_context');
end $$;

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
  'baseline_hash',encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine')::text,'UTF8'),'sha256'),'hex'));
end $$;

create or replace function cp7_reorder_inputs.history(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare limits jsonb:=cp7_analysis_stage.bounds();g jsonb;ev jsonb;validated jsonb;stock jsonb;
 n integer;days integer;per integer;offset_at integer:=0;selected jsonb;keys jsonb;roots jsonb;products jsonb;
 availability jsonb;latest jsonb;chunk_rows jsonb;chunk_targets jsonb;
 rows_out jsonb[]:='{}';targets_out jsonb[]:='{}';item jsonb;
begin
 perform cp7_wip.fields(q,array['from_date','through_date','group_mode']);
 -- The same preflight, complete collections, caps and closed date query as
 -- the existing staged path. A refusal is never converted to an empty row.
 g:=cp7_analysis_stage.history_prep(c,q,(limits->>'job_targets')::integer,
  (limits->>'job_history_cells')::bigint,(limits->>'sales_per_events_unit')::integer);
 ev:=cp7_analysis_stage.events_validate(jsonb_build_object('known_as_of',c->'captured_at',
  'effective_as_of',c->'captured_at','from_date',q->'from_date','through_date',q->'through_date',
  'group_mode',q->'group_mode','targets',g->'targets','events',cp7_planning.history_events(c)));
 validated:=cp7_analysis_stage.history_validate(jsonb_build_object('targets',g->'targets',
  'events',ev->'events','errors',case when ev?'error'then jsonb_build_array(ev->'error')else'[]'::jsonb end));
 stock:=cp7_analysis_stage.history_stock(c,g->'stock_order',g->>'hash');
 n:=jsonb_array_length(g->'targets');days:=(g->>'through')::date-(g->>'from')::date+1;
 per:=greatest(1,(limits->>'history_cells_per_unit')::integer/greatest(days,1));
 while offset_at<n loop
  select coalesce(jsonb_agg(g->'targets'->(entry.i::integer-1)order by entry.pos),'[]')into selected
   from jsonb_array_elements_text(validated->'key_order')with ordinality entry(i,pos)
   where entry.pos>offset_at and entry.pos<=offset_at+per;
  select coalesce(jsonb_object_agg(target->>'key',true),'{}')into keys from jsonb_array_elements(selected)target;
  if(g->>'availability_clean')::boolean then
   select coalesce(jsonb_agg(p order by ord),'[]'),coalesce(jsonb_object_agg(p->>'root_id',true),'{}')into products,roots
    from jsonb_array_elements(c->'facts'->'products')with ordinality source_products(p,ord)
    where keys?((p->>'root_id')||':'||(p->>'size_id'));
   availability:=cp7_planning.history_availability(jsonb_build_object('captured_at',c->'captured_at',
    'facts',jsonb_build_object('products',products,'stock',
     (select coalesce(jsonb_agg(m order by ord),'[]')from jsonb_array_elements(c->'facts'->'stock')with ordinality source_stock(m,ord)
       where roots?(m->>'root_id')))),q);
  else
   select coalesce(jsonb_agg(a order by ord),'[]')into availability
    from jsonb_array_elements(g->'availability')with ordinality source_availability(a,ord)where keys?(a->>'target_key');
  end if;
  select coalesce(jsonb_object_agg(event->>'lineage_key',event),'{}')into latest
   from jsonb_each(ev->'by_target')event_targets cross join lateral jsonb_array_elements(event_targets.value)event
   where keys?event_targets.key;
  chunk_rows:=cp7_analysis_stage.history_rows(jsonb_build_object('known_as_of',c->'captured_at',
   'from_date',q->'from_date','through_date',q->'through_date','history_complete',true,
   'targets',selected,'keys',keys,'latest',latest,'availability',availability));
  for item in select value from jsonb_array_elements(chunk_rows)loop rows_out:=array_append(rows_out,item);end loop;
  offset_at:=offset_at+per;
 end loop;
 c:=c||jsonb_build_object('analog_consumer_context',cp7_product_analog_consumer.prepare(c,to_jsonb(rows_out),q));
 offset_at:=0;
 while offset_at<n loop
  select coalesce(jsonb_agg(x order by ord),'[]')into chunk_rows from jsonb_array_elements(to_jsonb(rows_out))with ordinality all_history(x,ord)where ord>offset_at and ord<=offset_at+per;
  chunk_targets:=cp7_analysis_stage.baseline_rows(c,chunk_rows,stock,g->>'baseline_hash');
  for item in select value from jsonb_array_elements(chunk_targets)loop targets_out:=array_append(targets_out,item);end loop;
  offset_at:=offset_at+per;
 end loop;
 return jsonb_build_object('contract_version','cp7.reorder-native-inputs.v1','captured_at',c->'captured_at',
  'query',q,'source_hash',g->'baseline_hash','history_hash',g->'hash',
  'target_engine','EXISTING_NATIVE_STAGED_BASELINE','products',c->'facts'->'products','history',to_jsonb(rows_out),
  'current_stock',stock,'targets',to_jsonb(targets_out),'apply_enabled',false,'production_go',false);
end $$;

create or replace function cp7_reorder_inputs.compile(s jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare c jsonb;f jsonb;q jsonb;summary jsonb;inputs jsonb;compiled jsonb;path text;p_products integer;
 limits jsonb:=cp7_analysis_stage.bounds();hash text;baseline_hash text;targets jsonb;v jsonb;ev jsonb;validated jsonb;
 first_day date;last_day date;day_count integer;n integer;per integer;offset_at integer:=0;
 selected jsonb;keys jsonb;latest jsonb;availability jsonb;chunk_rows jsonb;chunk_targets jsonb;
 stock jsonb;stock_by_root jsonb;drafts_by_root jsonb;p jsonb;r jsonb;refs jsonb;native_available numeric;
 current_rows jsonb[]:='{}';rows_out jsonb[]:='{}';targets_out jsonb[]:='{}';item jsonb;
begin
 perform cp7_wip.fields(s,array['contract_version','status','captured_at','query','native','defaults','product_bound',
  'stock_summary','leads','manuals','engine_hash','context_hash','threshold_hash','apply_enabled','production_go']);
 if s->>'contract_version'is distinct from'cp7.reorder-native-source.v1'
  or s->'apply_enabled'is distinct from'false'::jsonb or s->'production_go'is distinct from'false'::jsonb
  or jsonb_typeof(s->'product_bound')is distinct from'number'or(s->>'product_bound')!~'^[0-9]{1,4}$'then
  raise exception 'CP7_REORDER_SOURCE_SNAPSHOT_SHAPE';end if;
 p_products:=(s->>'product_bound')::integer;c:=s->'native';f:=c->'facts';q:=s->'query';
 if p_products not between 1 and 5000 or s->'status'is distinct from c->'status'
  or s->'captured_at'is distinct from c->'captured_at'then raise exception 'CP7_REORDER_SOURCE_SNAPSHOT_BINDING';end if;
 if c->>'status'='COMPLETE'then
  inputs:=cp7_reorder_inputs.history(c,q);path:='COMPLETE_NATIVE_CAPTURE';
 else
  -- The pinned Native source's COMPLETE predicate, except that its one raw
  -- stock array is replaced by ALL visible SQL movements below. No status on
  -- c is changed, no stock is discarded and no other overflow is accepted.
  perform cp7_wip.fields(f,array['products','stock','sales','sale_journals','returns','return_journals']);
  if c->>'status'is distinct from'INCOMPLETE'or not(jsonb_array_length(f->'stock')=50001
   or coalesce(c->'stock_raw_omitted'='true'::jsonb and c->'stock_rows_at_least'='50001'::jsonb and jsonb_array_length(f->'stock')=0,false))
   or jsonb_array_length(f->'products')>p_products
   or exists(select 1 from jsonb_each(f)where key not in('products','stock')and jsonb_array_length(value)>50000)
   or jsonb_array_length(f->'products')<>(select count(distinct x->>'root_id')from jsonb_array_elements(f->'products')x)
   or exists(select 1 from jsonb_array_elements(f->'products')x where jsonb_array_length(x->'commercial')>1)
   or exists(select 1 from jsonb_array_elements(f->'sales')x where jsonb_array_length(x->'sold_commercial')>1)
   or exists(select 1 from jsonb_array_elements(f->'sales')sale left join(
    select j->>'sale_id'sale_id,count(*)n from jsonb_array_elements(f->'sale_journals')j
     where j->'reversal_of_id'='null'::jsonb group by 1)originals on originals.sale_id=sale->>'sale_id'
    where sale->>'status'in('POSTED','PARTIAL_PAID','PAID','REVERSED')and coalesce(originals.n,0)<>1)then
   raise exception 'CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE';end if;
  summary:=s->'stock_summary';
  if summary->>'contract_version'is distinct from'cp7.reorder-stock-summary.v1'
   or summary->>'captured_at'is distinct from cp7_planning.utc((c->>'captured_at')::timestamptz)
   or summary->'query'is distinct from q or(summary->>'products')::integer is distinct from jsonb_array_length(f->'products')
   or summary->'raw_rows_truncated'is distinct from'false'::jsonb or summary->'Native_capture_status_overridden'is distinct from'false'::jsonb
   or(summary->>'raw_rows_read')::bigint<greatest(jsonb_array_length(f->'stock'),
    case when c->'stock_raw_omitted'='true'::jsonb then 50001 else 0 end)then
   raise exception 'CP7_REORDER_STOCK_SNAPSHOT_MISMATCH';end if;
  path:='COMPLETE_SQL_STOCK_SUMMARY_RAW_NATIVE_INCOMPLETE';
  hash:=encode(extensions.digest(convert_to(jsonb_build_object('native_non_stock',f-'stock',
   'complete_stock_summary',summary->'data_hash','source_kind',path)::text,'UTF8'),'sha256'),'hex');
  baseline_hash:=encode(extensions.digest(convert_to(jsonb_build_object('native_non_stock',f-'stock',
   'complete_stock_summary',summary->'data_hash','profiles',c->'profiles',
   'production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine','source_kind',path)::text,'UTF8'),'sha256'),'hex');
  first_day:=cp7_demand.day(q->'from_date');last_day:=cp7_demand.day(q->'through_date');day_count:=last_day-first_day+1;
  targets:=(select coalesce(jsonb_agg(jsonb_build_object('key',(value->>'root_id')||':'||(value->>'size_id'),
   'size_id',value->>'size_id','current_group_key',coalesce(value->'commercial'->0->>'sku_id',value->>'root_id'),
   'refs',jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',value->>'id','revision','1')))order by value->>'root_id'),'[]')
   from jsonb_array_elements(f->'products'));
  v:=jsonb_build_object('contract_version','cp7.demand-input.v1','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','known_as_of',c->'captured_at','effective_as_of',c->'captured_at',
   'from_date',q->'from_date','through_date',q->'through_date','history_complete',true,'group_mode',q->'group_mode',
   'targets',targets,'events','[]'::jsonb,'availability','[]'::jsonb);
  perform cp7_demand.context(v,'cp7.demand-input.v1');perform cp7_demand.items(targets,(limits->>'job_targets')::integer);
  if day_count<1 or last_day-first_day>3660 or last_day>=((c->>'captured_at')::timestamptz at time zone'Asia/Jakarta')::date
   or jsonb_array_length(targets)*day_count>(limits->>'job_history_cells')::bigint then
   raise exception 'CP7_REORDER_STOCK_SCOPE_BOUND';end if;
  ev:=cp7_analysis_stage.events_validate(v||jsonb_build_object('events',cp7_planning.history_events(c)));
  validated:=cp7_analysis_stage.history_validate(jsonb_build_object('targets',targets,'events',ev->'events',
   'errors',case when ev?'error'then jsonb_build_array(ev->'error')else'[]'::jsonb end));
  stock:=cp7_reorder_inputs.current_stock(c,summary,hash);n:=jsonb_array_length(targets);
  per:=greatest(1,(limits->>'history_cells_per_unit')::integer/greatest(day_count,1));
  while offset_at<n loop
   select coalesce(jsonb_agg(targets->(entry.i::integer-1)order by entry.pos),'[]')into selected
    from jsonb_array_elements_text(validated->'key_order')with ordinality entry(i,pos)
    where entry.pos>offset_at and entry.pos<=offset_at+per;
   select coalesce(jsonb_object_agg(target->>'key',true),'{}')into keys from jsonb_array_elements(selected)target;
   select coalesce(jsonb_agg(a order by ord),'[]')into availability
    from jsonb_array_elements(summary->'availability')with ordinality source_availability(a,ord)where keys?(a->>'target_key');
   select coalesce(jsonb_object_agg(event->>'lineage_key',event),'{}')into latest
    from jsonb_each(ev->'by_target')event_targets cross join lateral jsonb_array_elements(event_targets.value)event
    where keys?event_targets.key;
   chunk_rows:=cp7_analysis_stage.history_rows(jsonb_build_object('known_as_of',c->'captured_at',
    'from_date',q->'from_date','through_date',q->'through_date','history_complete',true,
    'targets',selected,'keys',keys,'latest',latest,'availability',availability));
   for item in select value from jsonb_array_elements(chunk_rows)loop rows_out:=array_append(rows_out,item);end loop;
   offset_at:=offset_at+per;
  end loop;
  c:=c||jsonb_build_object('analog_consumer_context',cp7_product_analog_consumer.prepare(c,to_jsonb(rows_out),q));
  offset_at:=0;
  while offset_at<n loop
   select coalesce(jsonb_agg(x order by ord),'[]')into chunk_rows from jsonb_array_elements(to_jsonb(rows_out))with ordinality all_history(x,ord)where ord>offset_at and ord<=offset_at+per;
   chunk_targets:=cp7_analysis_stage.baseline_rows(c,chunk_rows,stock,baseline_hash);
   for item in select value from jsonb_array_elements(chunk_targets)loop targets_out:=array_append(targets_out,item);end loop;
   offset_at:=offset_at+per;
  end loop;
  inputs:=jsonb_build_object('contract_version','cp7.reorder-native-inputs.v1','captured_at',c->'captured_at','query',q,
   'source_hash',baseline_hash,'history_hash',hash,'target_engine','EXISTING_NATIVE_STAGED_BASELINE',
   'products',f->'products','history',to_jsonb(rows_out),'current_stock',stock,'targets',to_jsonb(targets_out),
   'apply_enabled',false,'production_go',false);
 end if;
 compiled:=cp7_reorder_inputs.points(inputs,s->'defaults',s->'leads',s->'manuals');
 return jsonb_build_object('contract_version','cp7.reorder-read-points.v1','captured_at',c->'captured_at','query',q,
  'native_capture_status',c->'status','input_path',path,'engine_hash',s->'engine_hash',
  'context_hash',encode(extensions.digest(convert_to(jsonb_build_object('source',s->'context_hash',
   'reorder_source',inputs->'source_hash','path',path)::text,'UTF8'),'sha256'),'hex'),
  'inputs',inputs,'points',compiled,'complete_stock_raw_rows_read',summary->'raw_rows_read',
  'live_ROP_caller_changed',false,'apply_enabled',false,'production_go',false);
end $$;

create or replace function cp7_history_bounded.compile(p_capture jsonb,p_query jsonb,p_summary jsonb,p_products integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare c jsonb;f jsonb;q jsonb;summary jsonb;inputs jsonb;compiled jsonb;path text;
 limits jsonb:=cp7_analysis_stage.bounds();hash text;baseline_hash text;targets jsonb;v jsonb;ev jsonb;validated jsonb;
 first_day date;last_day date;day_count integer;n integer;per integer;offset_at integer:=0;
 selected jsonb;keys jsonb;latest jsonb;availability jsonb;chunk_rows jsonb;chunk_targets jsonb;
 stock jsonb;stock_by_root jsonb;drafts_by_root jsonb;p jsonb;r jsonb;refs jsonb;native_available numeric;
 current_rows jsonb[]:='{}';rows_out jsonb[]:='{}';targets_out jsonb[]:='{}';item jsonb;
begin
 perform cp7_wip.fields(p_query,array['from_date','through_date','group_mode']);
 if p_products is null or p_products not between 1 and 5000
  or p_capture->>'contract_version'is distinct from'cp7.native-demand-facts.v1'
  or p_capture->>'scope'is distinct from'GLOBAL_CURRENT_PHYSICAL_ROOTS'
  or jsonb_array_length(p_capture->'facts'->'products')>p_products then
  raise exception 'CP7_BOUNDED_HISTORY_SOURCE_SHAPE';end if;
 perform cp7_demand.instant(p_capture->'captured_at');
 c:=p_capture;f:=c->'facts';q:=p_query;summary:=p_summary;
 if c->>'status'='COMPLETE'then
  inputs:=cp7_reorder_inputs.history(c,q);path:='COMPLETE_NATIVE_CAPTURE';
 else
  -- The pinned Native source's COMPLETE predicate, except that its one raw
  -- stock array is replaced by ALL visible SQL movements below. No status on
  -- c is changed, no stock is discarded and no other overflow is accepted.
  perform cp7_wip.fields(f,array['products','stock','sales','sale_journals','returns','return_journals']);
  if c->>'status'is distinct from'INCOMPLETE'or not(jsonb_array_length(f->'stock')=50001
   or coalesce(c->'stock_raw_omitted'='true'::jsonb and c->'stock_rows_at_least'='50001'::jsonb and jsonb_array_length(f->'stock')=0,false))
   or jsonb_array_length(f->'products')>p_products
   or exists(select 1 from jsonb_each(f)where key not in('products','stock')and jsonb_array_length(value)>50000)
   or jsonb_array_length(f->'products')<>(select count(distinct x->>'root_id')from jsonb_array_elements(f->'products')x)
   or exists(select 1 from jsonb_array_elements(f->'products')x where jsonb_array_length(x->'commercial')>1)
   or exists(select 1 from jsonb_array_elements(f->'sales')x where jsonb_array_length(x->'sold_commercial')>1)
   or exists(select 1 from jsonb_array_elements(f->'sales')sale left join(
    select j->>'sale_id'sale_id,count(*)n from jsonb_array_elements(f->'sale_journals')j
     where j->'reversal_of_id'='null'::jsonb group by 1)originals on originals.sale_id=sale->>'sale_id'
    where sale->>'status'in('POSTED','PARTIAL_PAID','PAID','REVERSED')and coalesce(originals.n,0)<>1)then
   raise exception 'CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE';end if;
  if summary->>'contract_version'is distinct from'cp7.reorder-stock-summary.v1'
   or summary->>'captured_at'is distinct from cp7_planning.utc((c->>'captured_at')::timestamptz)
   or summary->'query'is distinct from q or(summary->>'products')::integer is distinct from jsonb_array_length(f->'products')
   or summary->'raw_rows_truncated'is distinct from'false'::jsonb or summary->'Native_capture_status_overridden'is distinct from'false'::jsonb
   or(summary->>'raw_rows_read')::bigint<greatest(jsonb_array_length(f->'stock'),
    case when c->'stock_raw_omitted'='true'::jsonb then 50001 else 0 end)then
   raise exception 'CP7_REORDER_STOCK_SNAPSHOT_MISMATCH';end if;
  path:='COMPLETE_SQL_STOCK_SUMMARY_RAW_NATIVE_INCOMPLETE';
  hash:=encode(extensions.digest(convert_to(jsonb_build_object('native_non_stock',f-'stock',
   'complete_stock_summary',summary->'data_hash','source_kind',path)::text,'UTF8'),'sha256'),'hex');
  baseline_hash:=encode(extensions.digest(convert_to(jsonb_build_object('native_non_stock',f-'stock',
   'complete_stock_summary',summary->'data_hash','profiles',c->'profiles',
   'production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine','source_kind',path)::text,'UTF8'),'sha256'),'hex');
  first_day:=cp7_demand.day(q->'from_date');last_day:=cp7_demand.day(q->'through_date');day_count:=last_day-first_day+1;
  targets:=(select coalesce(jsonb_agg(jsonb_build_object('key',(value->>'root_id')||':'||(value->>'size_id'),
   'size_id',value->>'size_id','current_group_key',coalesce(value->'commercial'->0->>'sku_id',value->>'root_id'),
   'refs',jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',value->>'id','revision','1')))order by value->>'root_id'),'[]')
   from jsonb_array_elements(f->'products'));
  v:=jsonb_build_object('contract_version','cp7.demand-input.v1','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','known_as_of',c->'captured_at','effective_as_of',c->'captured_at',
   'from_date',q->'from_date','through_date',q->'through_date','history_complete',true,'group_mode',q->'group_mode',
   'targets',targets,'events','[]'::jsonb,'availability','[]'::jsonb);
  perform cp7_demand.context(v,'cp7.demand-input.v1');perform cp7_demand.items(targets,(limits->>'job_targets')::integer);
  if day_count<1 or last_day-first_day>3660 or last_day>=((c->>'captured_at')::timestamptz at time zone'Asia/Jakarta')::date
   or jsonb_array_length(targets)*day_count>(limits->>'job_history_cells')::bigint then
   raise exception 'CP7_REORDER_STOCK_SCOPE_BOUND';end if;
  ev:=cp7_analysis_stage.events_validate(v||jsonb_build_object('events',cp7_planning.history_events(c)));
  validated:=cp7_analysis_stage.history_validate(jsonb_build_object('targets',targets,'events',ev->'events',
   'errors',case when ev?'error'then jsonb_build_array(ev->'error')else'[]'::jsonb end));
  stock:=cp7_reorder_inputs.current_stock(c,summary,hash);n:=jsonb_array_length(targets);
  per:=greatest(1,(limits->>'history_cells_per_unit')::integer/greatest(day_count,1));
  while offset_at<n loop
   select coalesce(jsonb_agg(targets->(entry.i::integer-1)order by entry.pos),'[]')into selected
    from jsonb_array_elements_text(validated->'key_order')with ordinality entry(i,pos)
    where entry.pos>offset_at and entry.pos<=offset_at+per;
   select coalesce(jsonb_object_agg(target->>'key',true),'{}')into keys from jsonb_array_elements(selected)target;
   select coalesce(jsonb_agg(a order by ord),'[]')into availability
    from jsonb_array_elements(summary->'availability')with ordinality source_availability(a,ord)where keys?(a->>'target_key');
   select coalesce(jsonb_object_agg(event->>'lineage_key',event),'{}')into latest
    from jsonb_each(ev->'by_target')event_targets cross join lateral jsonb_array_elements(event_targets.value)event
    where keys?event_targets.key;
   chunk_rows:=cp7_analysis_stage.history_rows(jsonb_build_object('known_as_of',c->'captured_at',
    'from_date',q->'from_date','through_date',q->'through_date','history_complete',true,
    'targets',selected,'keys',keys,'latest',latest,'availability',availability));
   for item in select value from jsonb_array_elements(chunk_rows)loop rows_out:=array_append(rows_out,item);end loop;
   offset_at:=offset_at+per;
  end loop;
  c:=c||jsonb_build_object('analog_consumer_context',cp7_product_analog_consumer.prepare(c,to_jsonb(rows_out),q));
  offset_at:=0;
  while offset_at<n loop
   select coalesce(jsonb_agg(x order by ord),'[]')into chunk_rows from jsonb_array_elements(to_jsonb(rows_out))with ordinality all_history(x,ord)where ord>offset_at and ord<=offset_at+per;
   chunk_targets:=cp7_analysis_stage.baseline_rows(c,chunk_rows,stock,baseline_hash);
   for item in select value from jsonb_array_elements(chunk_targets)loop targets_out:=array_append(targets_out,item);end loop;
   offset_at:=offset_at+per;
  end loop;
  inputs:=jsonb_build_object('contract_version','cp7.reorder-native-inputs.v1','captured_at',c->'captured_at','query',q,
   'source_hash',baseline_hash,'history_hash',hash,'target_engine','EXISTING_NATIVE_STAGED_BASELINE',
   'products',f->'products','history',to_jsonb(rows_out),'current_stock',stock,'targets',to_jsonb(targets_out),
   'apply_enabled',false,'production_go',false);
 end if;
 return jsonb_build_object('contract_version','cp7.bounded-history-inputs.v1',
  'captured_at',c->'captured_at','query',q,'raw_native_capture_status',c->'status',
  'coverage','COMPLETE','input_path',path,'inputs',inputs,
  'raw_stock_rows_read',summary->'raw_rows_read','stock_raw_omitted',coalesce(c->'stock_raw_omitted','false'::jsonb),
  'raw_native_status_overridden',false,'apply_enabled',false,'production_go',false);
end $$;

create or replace function cp7_bounded_analysis_stage.run_scenario_unit(j cp7_analysis_stage.jobs,u cp7_analysis_stage.units,c jsonb)returns jsonb
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
  c:=c||jsonb_build_object('analog_consumer_context',cp7_product_analog_consumer.prepare(c,
   (select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='HIST'),j.query));
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
  c:=c||jsonb_build_object('analog_consumer_context',cp7_product_analog_consumer.prepare(c,
   (select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='HIST'),j.query));
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

create or replace function cp7_bounded_analysis_stage.analysis_source(p_products integer,p_match integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with native as materialized(select cp7_bounded_analysis_stage.netting_source(p_products,p_match)c),
 engine as(select encode(extensions.digest(convert_to(string_agg(
  p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')signature
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname in('cp7_product_analog_consumer','cp7_product_analog_choice','cp7_planning','cp7_profile','cp7_supply_native','cp7_schedule_native','cp7_netting_native','cp7_analysis_native','cp7_analysis_stage','cp7_fabric_native','cp7_wip','cp7_demand','cp7_baseline','cp7_models','cp7_finance','cp7_reorder_supply','cp7_bounded_analysis_stage')
   or p.oid='erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure)
 select c||jsonb_build_object('reorder_supply_engine','cp7.reorder-supply.v1','analysis_engine_signature',signature,
  'material_source',cp7_analysis_native.material_source(c->'facts'->'products',(c->>'captured_at')::timestamptz),
  'fabric_source',cp7_fabric_native.source(c->'facts'->'products',(c->>'captured_at')::timestamptz))from native cross join engine
$$;

create or replace function cp7_bounded_analysis_stage.producer_hash()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),
  E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname in('cp7_product_analog_consumer','cp7_product_analog_choice','cp7_bounded_analysis_stage','cp7_history_bounded','cp7_history_reference')and p.prokind='f'
$$;

create or replace function cp7_bounded_analysis_stage.native_work_fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts',
  'profiles',c->'profiles','production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine',
  'production_scope',c->'production_sources'->'scope',
  'production',c->'production_sources'->'facts')::text,'UTF8'),'sha256'),'hex')
$$;

create or replace function cp7_supply_native.fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case when c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'
 then cp7_bounded_analysis_stage.work_fingerprint(c) else encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts',
  'profiles',c->'profiles','production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine',
  'production_scope',c->'production_sources'->'scope',
  'production',c->'production_sources'->'facts')::text,'UTF8'),'sha256'),'hex') end
$$;

create or replace function cp7_reorder_inputs.source_within(p_products integer)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if p_products is null or p_products not between 1 and 5000 then raise exception 'CP7_REORDER_SOURCE_PRODUCT_BOUND';end if;
 return(
 with native as materialized(select cp7_reorder_inputs.capture_baseline(p_products)c),
 boundary as materialized(select c,(c->>'captured_at')::timestamptz at from native),
 policy as materialized(select jsonb_build_object(
  'service_level',to_char((cp7_stock_formula.current_settings()->>'service_level')::numeric,'FM0.00'),
  'window_days',cp7_stock_formula.current_settings()->>'window_days')defaults),
 wanted_models as materialized(select distinct(x->>'model_id')::uuid model_id
  from native,jsonb_array_elements(c->'facts'->'products')x where x->>'model_id'is not null),
 lead_observations as materialized(
  select po.model_id,g.id group_id,extract(epoch from lot.produced_at-g.cut_at)/86400.0 days
  from erp.fg_lots lot join erp.cutting_groups g on g.id=lot.cutting_group_id
  join erp.production_orders po on po.id=g.po_id join wanted_models wanted on wanted.model_id=po.model_id
  join erp.qc_inspection_items qi on qi.id=lot.qc_item_id join erp.qc_inspections qc on qc.id=qi.inspection_id cross join boundary
  where lot.lot_origin='PRODUCTION'and qc.status='POSTED'and g.material_issue_posted
   and lot.produced_at<=boundary.at and lot.produced_at>boundary.at-interval'365 days'and lot.produced_at>=g.cut_at),
 lead_rows as materialized(select model_id,count(*)lots,count(distinct group_id)groups,
  case when count(distinct group_id)>=3 then round(percentile_cont(0.5)within group(order by days)::numeric,2)end days
  from lead_observations group by model_id),
 leads as materialized(select coalesce(jsonb_agg(jsonb_build_object('model_id',model_id::text,'lead_days',days::text,
  'lot_count',lots::text,'group_count',groups::text)order by model_id),'[]')rows from lead_rows),
 latest_manual as materialized(select distinct on(m.root_id)m.root_id,m.product_version_id,m.size_id,m.revision,m.reorder_point_pcs
  from cp7_stock_formula.manual_points m cross join boundary
  where m.root_id::text in(select x->>'root_id'from jsonb_array_elements(boundary.c->'facts'->'products')x)
   and m.recorded_at<=boundary.at order by m.root_id,m.revision desc),
 manuals as materialized(select coalesce(jsonb_agg(jsonb_build_object('root_id',root_id::text,'product_version_id',product_version_id::text,
  'size_id',size_id::text,'revision',revision::text,'reorder_point_pcs',reorder_point_pcs::text)order by root_id),'[]')rows from latest_manual),
 engine as materialized(select encode(extensions.digest(convert_to(string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),
  E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')hash
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname in('cp7_product_analog_consumer','cp7_product_analog_choice','cp7_reorder_inputs','cp7_reorder_reader','cp7_planning','cp7_profile','cp7_baseline_native','cp7_analysis_stage','cp7_demand','cp7_baseline','cp7_stock_formula')
   and p.prokind='f'),
 query as materialized(select jsonb_build_object(
  'from_date',((boundary.at at time zone'Asia/Jakarta')::date-(policy.defaults->>'window_days')::integer)::text,
  'through_date',((boundary.at at time zone'Asia/Jakarta')::date-1)::text,'group_mode','AS_SOLD')q from boundary cross join policy),
 complete_stock as materialized(select case when boundary.c->'stock_raw_omitted'='true'::jsonb
  or jsonb_array_length(boundary.c->'facts'->'stock')=50001 then
  cp7_reorder_inputs.stock_summary(boundary.c->'facts'->'products',boundary.at,query.q)end summary
  from boundary cross join query),
 history_stock_key as materialized(select case when complete_stock.summary is not null then complete_stock.summary->'history_data_hash'
  else(select coalesce(jsonb_agg(m order by ord),'[]')from jsonb_array_elements(boundary.c->'facts'->'stock')with ordinality movements(m,ord)
   where(m->>'physical_at')::timestamptz<((boundary.at at time zone'Asia/Jakarta')::date::timestamp at time zone'Asia/Jakarta'))end value
  from boundary cross join complete_stock)
 select jsonb_build_object('contract_version','cp7.reorder-native-source.v1','status',boundary.c->'status',
  'captured_at',boundary.c->'captured_at','query',query.q,'native',boundary.c,'defaults',policy.defaults,'product_bound',p_products,
  'stock_summary',complete_stock.summary,
  'leads',leads.rows,'manuals',manuals.rows,'engine_hash',engine.hash,
  'threshold_hash',encode(extensions.digest(convert_to(jsonb_build_object('native_non_stock',(boundary.c->'facts')-'stock',
    'native_status',boundary.c->'status','product_bound',p_products,'history_stock',history_stock_key.value,
    'profiles',boundary.c->'profiles','production_policies',boundary.c->'production_policies'->'rows','product_analog_choices',boundary.c->'product_analog_choices','analog_consumer_engine',boundary.c->'analog_consumer_engine',
    'query',query.q,'defaults',policy.defaults,'leads',leads.rows,'manuals',manuals.rows,'engine',engine.hash)::text,'UTF8'),'sha256'),'hex'),
  'context_hash',encode(extensions.digest(convert_to(jsonb_build_object('facts',boundary.c->'facts',
    'profiles',boundary.c->'profiles','production_policies',boundary.c->'production_policies'->'rows','product_analog_choices',boundary.c->'product_analog_choices','analog_consumer_engine',boundary.c->'analog_consumer_engine',
    'query',query.q,'defaults',policy.defaults,'leads',leads.rows,'manuals',manuals.rows,'engine',engine.hash,
    'complete_stock_summary',complete_stock.summary->'data_hash')::text,'UTF8'),'sha256'),'hex'),
  'apply_enabled',false,'production_go',false)
 from boundary cross join policy cross join leads cross join manuals cross join engine cross join query cross join complete_stock cross join history_stock_key);
end $$;

create or replace function cp7_reorder_inputs.points(v jsonb,defaults jsonb,leads jsonb,manuals jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare row_value jsonb;hist jsonb;profile jsonb;config jsonb;kernel jsonb;lead_row jsonb;manual_row jsonb;
 by_history jsonb;by_product jsonb;product jsonb;by_lead jsonb:='{}';by_manual jsonb:='{}';seen jsonb:='{}';item jsonb;key text;root text;
 total numeric;counted numeric;sd numeric;mean_value numeric;lead_days numeric;point text;formula_point text;
 source_kind text;reason text;point_basis text;manual_state text;checked timestamptz;window_days integer;
 output_rows jsonb[]:='{}';selection_hash text;
begin
 perform cp7_wip.fields(v,array['contract_version','captured_at','query','source_hash','history_hash','target_engine','products','history','current_stock','targets','apply_enabled','production_go']);
 perform cp7_wip.fields(defaults,array['service_level','window_days']);
 if v->>'contract_version'is distinct from'cp7.reorder-native-inputs.v1'
  or v->>'target_engine'is distinct from'EXISTING_NATIVE_STAGED_BASELINE'
  or v->'apply_enabled'is distinct from'false'::jsonb or v->'production_go'is distinct from'false'::jsonb
  or defaults->>'service_level'is null or defaults->>'service_level'not in('0.90','0.95','0.99')
  or jsonb_typeof(defaults->'service_level')is distinct from'string'
  or jsonb_typeof(defaults->'window_days')is distinct from'string'or defaults->>'window_days'!~'^[0-9]{2,3}$'then
  raise exception 'CP7_REORDER_INPUT_POLICY';end if;
 checked:=cp7_demand.instant(v->'captured_at');window_days:=(defaults->>'window_days')::integer;
 if window_days not between 14 and 365
  or v->'query'->>'from_date'is distinct from((checked at time zone'Asia/Jakarta')::date-window_days)::text
  or v->'query'->>'through_date'is distinct from((checked at time zone'Asia/Jakarta')::date-1)::text then
  raise exception 'CP7_REORDER_INPUT_PERIOD';end if;
 perform cp7_wip.fields(v->'query',array['from_date','through_date','group_mode']);
 if v->'query'->>'group_mode'is distinct from'AS_SOLD'then raise exception 'CP7_REORDER_INPUT_GROUP_MODE';end if;
 perform cp7_demand.items(v->'targets',5000);perform cp7_demand.items(v->'history',5000);
 perform cp7_demand.items(v->'products',5000);
 perform cp7_demand.items(leads,5000);perform cp7_demand.items(manuals,5000);
 for item in select value from jsonb_array_elements(leads)loop
  perform cp7_wip.fields(item,array['model_id','lead_days','lot_count','group_count']);key:=cp7_wip.key(item->'model_id');
  if by_lead?key then raise exception 'CP7_REORDER_LEAD_DUPLICATE';end if;
  perform cp7_wip.pcs(item->'lot_count');perform cp7_wip.pcs(item->'group_count');
  if cp7_wip.pcs(item->'group_count')>cp7_wip.pcs(item->'lot_count')then raise exception 'CP7_REORDER_LEAD_COUNTS';end if;
  if item->'lead_days'<>'null'::jsonb then
   perform cp7_demand.decimal(item->'lead_days');
   if cp7_wip.pcs(item->'group_count')<3 then raise exception 'CP7_REORDER_LEAD_UNPROVEN';end if;
  end if;
  by_lead:=by_lead||jsonb_build_object(key,item);
 end loop;
 for item in select value from jsonb_array_elements(manuals)loop
  perform cp7_wip.fields(item,array['root_id','product_version_id','size_id','revision','reorder_point_pcs']);
  key:=cp7_wip.key(item->'root_id');perform cp7_wip.key(item->'product_version_id');perform cp7_wip.key(item->'size_id');perform cp7_wip.pcs(item->'revision');
  if by_manual?key then raise exception 'CP7_REORDER_MANUAL_DUPLICATE';end if;
  if item->'reorder_point_pcs'<>'null'::jsonb and cp7_wip.pcs(item->'reorder_point_pcs')>10000000 then raise exception 'CP7_REORDER_MANUAL_RANGE';end if;
  by_manual:=by_manual||jsonb_build_object(key,item);
 end loop;
 select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into by_history from jsonb_array_elements(v->'history')x;
 if (select count(*)from jsonb_each(by_history))<>jsonb_array_length(v->'history')then raise exception 'CP7_REORDER_HISTORY_DUPLICATE';end if;
 select coalesce(jsonb_object_agg(x->>'root_id',x),'{}')into by_product from jsonb_array_elements(v->'products')x;
 if (select count(*)from jsonb_each(by_product))<>jsonb_array_length(v->'products')then raise exception 'CP7_REORDER_PRODUCT_DUPLICATE';end if;
 for row_value in select value from jsonb_array_elements(v->'targets')loop
  key:=cp7_wip.key(row_value->'target_key');root:=split_part(key,':',1);hist:=by_history->key;
  if seen?key or hist is null or row_value->>'size_id'is distinct from hist->>'size_id'then raise exception 'CP7_REORDER_TARGET_HISTORY_BINDING';end if;
  seen:=seen||jsonb_build_object(key,true);profile:=row_value->'profile';config:=profile->'config';product:=by_product->root;
  if jsonb_typeof(profile)is distinct from'object'or profile->>'root_id'is distinct from root then raise exception 'CP7_REORDER_TARGET_PROFILE_BINDING';end if;
  if product is null or product->>'id'is distinct from profile->>'product_version_id'or product->>'size_id'is distinct from row_value->>'size_id'then raise exception 'CP7_REORDER_TARGET_PRODUCT_BINDING';end if;
  lead_row:=by_lead->(product->>'model_id');manual_row:=by_manual->root;
  select coalesce(sum((day->>'gross_observed_pcs')::numeric),0),count(*),stddev_samp((day->>'gross_observed_pcs')::numeric)
   into total,counted,sd from jsonb_array_elements(hist->'days')day where day->>'state'='AVAILABLE';
  if counted is distinct from(hist->>'available_days')::numeric then raise exception 'CP7_REORDER_AVAILABLE_DAY_BINDING';end if;
  mean_value:=case when counted>0 then total/counted end;lead_days:=null;reason:=null;
  if profile->>'quality'='SELECTED_ASSUMPTION'then
   -- Keep the exact Native target, not a rounded mean or a second lead rule.
   kernel:=row_value->'target';source_kind:='PLANNING_PROFILE';
   if kernel->'inputs'->>'contract_version'is distinct from'cp7.target-input.v2'then raise exception 'CP7_REORDER_TARGET_KERNEL_BINDING';end if;
   if kernel->'inputs'->'lead_days'<>'null'::jsonb then lead_days:=cp7_demand.decimal(kernel->'inputs'->'lead_days');end if;
   mean_value:=case when kernel->'inputs'->'daily_total_pcs'<>'null'::jsonb and kernel->'inputs'->'counted_days'<>'null'::jsonb
    then cp7_demand.decimal(kernel->'inputs'->'daily_total_pcs')/nullif(cp7_wip.pcs(kernel->'inputs'->'counted_days'),0)end;
   reason:=case when kernel->>'status'is distinct from'SCENARIO'then kernel->>'reason'end;
  elsif profile->>'quality'='UNREVIEWED'then
   source_kind:='NATIVE_HISTORY_WITH_EXISTING_DEFAULTS';
   if lead_row->'lead_days'<>'null'::jsonb then lead_days:=cp7_demand.decimal(lead_row->'lead_days');end if;
   kernel:=cp7_baseline.target(jsonb_build_object('contract_version','cp7.target-input.v2','snapshot_id',v->'source_hash',
    'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','mode','STATISTICAL','daily_total_pcs',case when counted>=14 then total::text end,
    'counted_days',case when counted>=14 then counted::text end,'daily_sd',case when counted>=14 then sd::text end,
    'lead_days',lead_days::text,'review_days','0','buffer_days',null,'service_level',defaults->'service_level','refs',hist->'refs'));
   reason:=case when counted<14 then'FEWER_THAN_14_NATIVE_AVAILABLE_DAYS'when lead_days is null then'NO_PROVEN_LEAD_TIME'
    when kernel->>'status'is distinct from'SCENARIO'then kernel->>'reason'end;
  else
   source_kind:='PROFILE_UNAVAILABLE';kernel:=row_value->'target';reason:='PROFILE_IDENTITY_OR_VERSION_CHANGED';
  end if;
  formula_point:=case when reason is null then kernel->>'reorder_point_pcs'end;point:=formula_point;
  point_basis:=case when formula_point is not null then'FORMULA'else'UNKNOWN'end;manual_state:='NONE';
  if manual_row is not null then
   manual_state:=case when manual_row->'reorder_point_pcs'='null'::jsonb then'CLEARED'
    when manual_row->>'product_version_id'is distinct from profile->>'product_version_id'or manual_row->>'size_id'is distinct from row_value->>'size_id'then'STALE_IDENTITY'
    else'ACTIVE'end;
   if manual_state='ACTIVE'then point:=manual_row->>'reorder_point_pcs';point_basis:='MANUAL';reason:=null;
   elsif manual_state='STALE_IDENTITY'then point:=null;point_basis:='UNKNOWN';reason:='MANUAL_POINT_VERSION_CHANGED';end if;
  end if;
  output_rows:=array_append(output_rows,jsonb_build_object('target_key',key,'size_id',row_value->'size_id',
   'product_version_id',profile->'product_version_id','source_kind',source_kind,'point_basis',point_basis,'point_pcs',point,
   'formula_point_pcs',formula_point,'reason',reason,'daily_mean',mean_value::text,'available_days',counted::text,
   'available_total_pcs',total::text,'daily_sd',sd::text,'lead_days',lead_days::text,
   'lead_basis',case when lead_days is null then null when source_kind='PLANNING_PROFILE'then'PROFILE'else'MEASURED'end,
   'target',kernel,'demand_basis',row_value->'demand_estimate'->'basis',
   'analog_resolution',row_value->'analog_resolution','manual_state',manual_state,'manual_reference',manual_row,
   'supply_alignment',case when source_kind='PLANNING_PROFILE'and point_basis='FORMULA'and reason is null then'NATIVE_TARGET'else'NEEDS_EXPLICIT_BINDING'end));
 end loop;
 if (select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'history')
  or (select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'products')then raise exception 'CP7_REORDER_HISTORY_SCOPE_MISMATCH';end if;
 selection_hash:=encode(extensions.digest(convert_to(jsonb_build_object('native_source',v->'source_hash',
  'query',v->'query','defaults',defaults,'leads',leads,'manuals',manuals,'compiler','reorder-points-1')::text,'UTF8'),'sha256'),'hex');
 return jsonb_build_object('contract_version','cp7.reorder-native-points.v1','captured_at',v->'captured_at','query',v->'query',
  'native_source_hash',v->'source_hash','selection_hash',selection_hash,'rows',to_jsonb(output_rows),'apply_enabled',false,'production_go',false);
end $$;

create or replace function cp7_product_analog_choice.apply(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_product_analog_choice.commands%rowtype;saved cp7_product_analog_choice.choices%rowtype;
 j cp7_analysis_stage.jobs%rowtype;target text;action text;reason text;expected bigint;rev bigint;
 reviewed jsonb;material jsonb;current_source jsonb;outcome jsonb;scale numeric;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(true);
 if p_request is null then raise exception 'CP7_ANALOG_CHOICE_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p_payload,array['contract_version','source_request','source_hash','access_epoch',
  'target_key','source_key','scale_factor','reason','reviewed','expected_revision','action']);
 if p_payload->>'contract_version'is distinct from'cp7.product-analog-choice-command.v1' then raise exception 'CP7_ANALOG_CHOICE_CONTRACT';end if;
 -- Take the Native envelope before either metadata lock; recheck access after waits.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALOG:REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 select *into old from cp7_product_analog_choice.commands where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if old.payload<>p_payload then raise exception 'CP7_ANALOG_CHOICE_REQUEST_CHANGED';end if;
  return old.result;
 end if;
 if p_payload->>'access_epoch'is distinct from encode(pg_catalog.sha256(convert_to(cp7_schedule_native.access_now(false)::text,'UTF8')),'hex')then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 target:=cp7_wip.key(p_payload->'target_key');action:=p_payload->>'action';reason:=btrim(p_payload->>'reason');
 if action is null or action not in('CONFIRM','CLEAR')or p_payload->'reviewed'is distinct from'true'::jsonb
  or jsonb_typeof(p_payload->'reason')is distinct from'string'or reason is null or length(reason)not between 1 and 1000
  or jsonb_typeof(p_payload->'expected_revision')is distinct from'string'
  or p_payload->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'then raise exception 'CP7_ANALOG_CHOICE_REVIEW';end if;
 expected:=(p_payload->>'expected_revision')::bigint;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALOG:TARGET:'||target,0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 select coalesce(max(x.revision),0)into rev from cp7_product_analog_choice.choices x where x.target_key=target;
 if expected<>rev then raise exception 'CP7_ANALOG_CHOICE_REVISION_CHANGED';end if;
 if action='CONFIRM'then
  scale:=cp7_demand.decimal(p_payload->'scale_factor');
  if scale<=0 then raise exception 'CP7_ANALOG_CHOICE_SCALE';end if;
  reviewed:=cp7_product_analog_stage.read_candidates((p_payload->>'source_request')::uuid,target,0,1,p_payload->>'access_epoch');
  if reviewed#>>'{reference,source_hash}'is distinct from p_payload->>'source_hash'then raise exception 'CP7_ANALOG_CHOICE_REFERENCE_CHANGED';end if;
  select *into j from cp7_analysis_stage.jobs where run_id=(reviewed->>'run_id')::uuid;
  current_source:=cp7_bounded_analysis_stage.source_for(j.reference,j.query);
  if cp7_analysis_native.fingerprint(current_source)is distinct from j.source_hash then
   raise exception using errcode='40001',message='CP7_ANALOG_CHOICE_SOURCE_CHANGED';end if;
  material:=cp7_product_analog_choice.material(j.reference,target,p_payload->>'source_key')||jsonb_build_object(
   'source_request',p_payload->'source_request','source_run',j.run_id,'analysis_source_hash',j.source_hash,
   'identity_hash',reviewed->'identity_hash','producer_hash',reviewed->'producer_hash',
   'scale_factor',scale::text,'reviewed',true);
 else
  if rev=0 then raise exception 'CP7_ANALOG_CHOICE_NOT_SELECTED';end if;
  if p_payload->'source_request'is distinct from'null'::jsonb or p_payload->'source_hash'is distinct from'null'::jsonb
   or p_payload->'source_key'is distinct from'null'::jsonb or p_payload->'scale_factor'is distinct from'null'::jsonb then
   raise exception 'CP7_ANALOG_CHOICE_CLEAR_FIELDS';end if;
  material:='null'::jsonb;
 end if;
 insert into cp7_product_analog_choice.choices(target_key,revision,action,evidence,reason,actor,request_id)
 values(target,rev+1,action,material,reason,(a->>'actor')::uuid,p_request)returning *into saved;
 outcome:=jsonb_build_object('contract_version','cp7.product-analog-choice-outcome.v1','choice_id',saved.id,
  'target_key',target,'revision',saved.revision::text,'action',action,'request_id',p_request,
  'recorded_at',saved.recorded_at,'evidence',material,'reason',reason,'actor_scope_id',a->'actor',
  'state',case when action='CLEAR'then'CLEARED'else'CONFIRMED_ASSUMPTION'end,
  'forecast_applied',false,'production_go',false);
 insert into cp7_product_analog_choice.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p_payload,outcome);
 if action='CONFIRM'then
  current_source:=cp7_product_analog_consumer.normalize_confirmed_delta(j.reference,cp7_bounded_analysis_stage.source_for(j.reference,j.query),outcome);
  if cp7_analysis_native.fingerprint(current_source)is distinct from j.source_hash then
   raise exception using errcode='40001',message='CP7_ANALOG_CHOICE_SOURCE_CHANGED';end if;
 end if;
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create or replace function cp7_analysis_native.source_within(p_products integer,p_match integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with native as materialized(select cp7_netting_native.source_within(p_products,p_match)c),
 engine as(select encode(extensions.digest(convert_to(string_agg(
  p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')signature
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname in('cp7_product_analog_consumer','cp7_product_analog_choice','cp7_planning','cp7_profile','cp7_supply_native','cp7_schedule_native','cp7_netting_native','cp7_analysis_native','cp7_analysis_stage','cp7_fabric_native','cp7_wip','cp7_demand','cp7_baseline','cp7_models','cp7_finance','cp7_reorder_supply')
   or p.oid='erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure)
 select c||jsonb_build_object('reorder_supply_engine','cp7.reorder-supply.v1','analysis_engine_signature',signature,
  'material_source',cp7_analysis_native.material_source(c->'facts'->'products',(c->>'captured_at')::timestamptz),
  'fabric_source',cp7_fabric_native.source(c->'facts'->'products',(c->>'captured_at')::timestamptz))from native cross join engine
$$;
