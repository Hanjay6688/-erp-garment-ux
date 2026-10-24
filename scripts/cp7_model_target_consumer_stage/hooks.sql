create or replace function cp7_baseline_native.source_within(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with c as materialized(select cp7_planning.history_source_within(p_products)value),
 roots as(select array_agg((p->>'root_id')::uuid order by p->>'root_id')ids from c,jsonb_array_elements(value->'facts'->'products')p)
 select value||jsonb_build_object('model_target_source',cp7_model_target_source.capture(
   coalesce((select array_agg((p->>'root_id')||':'||(p->>'size_id')order by p->>'root_id')
    from jsonb_array_elements(value->'facts'->'products')p),array[]::text[]),
   (value->>'captured_at')::timestamptz),'product_analog_choices',cp7_product_analog_consumer.capture(value),
  'analog_consumer_engine',cp7_product_analog_consumer.engine_hash(),'profiles',cp7_profile.source(coalesce(ids,array[]::uuid[]),(value->>'captured_at')::timestamptz),
  'production_policies',cp7_identity.workspace_data(coalesce((select array_agg(distinct(s->>'sku_id')::uuid)
   from jsonb_array_elements(value->'facts'->'products')p cross join lateral jsonb_array_elements(p->'commercial')s),array[]::uuid[]),
   (value->>'captured_at')::timestamptz))from c cross join roots
$$;

create or replace function cp7_reorder_inputs.capture_baseline(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with c as materialized(select cp7_reorder_inputs.capture_history(p_products)value),
 roots as(select array_agg((p->>'root_id')::uuid order by p->>'root_id')ids from c,jsonb_array_elements(value->'facts'->'products')p)
 select value||jsonb_build_object('model_target_source',cp7_model_target_source.capture_for_reorder(
   coalesce((select array_agg((p->>'root_id')||':'||(p->>'size_id')order by p->>'root_id')
    from jsonb_array_elements(value->'facts'->'products')p),array[]::text[]),
   (value->>'captured_at')::timestamptz),'product_analog_choices',cp7_product_analog_consumer.capture(value),
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
 hash:=encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine','model_target_source_hash',c->'model_target_source'->'source_hash')::text,'UTF8'),'sha256'),'hex');
 rows:=array(select value from jsonb_array_elements(cp7_model_target_consumer.rows(c,h->'history'->'rows',h->'current_stock',hash,cp7_product_analog_consumer.prepare(c,h->'history'->'rows',q)))order by value->>'target_key');
 return jsonb_build_object('contract_version','cp7.native-baseline.v3','captured_at',c->>'captured_at',
  'source_hash',hash,'scope','GLOBAL_CURRENT_PHYSICAL_ROOTS','history_run_result',h,
  'rows',to_jsonb(rows),'target_basis','UNIFIED_TARGET_WITH_SELECTED_PROFILE_ASSUMPTIONS','apply_enabled',false,
  'model_basis','CURRENT_POLICY_GATED_DATED_NATIVE_MODELS','production_go',false);
end $$;

create or replace function cp7_baseline_native.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_baseline_native.runs%rowtype;c jsonb;hash text;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();select *into r from cp7_baseline_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_BASELINE_RUN_UNAVAILABLE';end if;
 c:=cp7_baseline_native.source();hash:=encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine','model_target_source_hash',c->'model_target_source'->'source_hash')::text,'UTF8'),'sha256'),'hex');
 outcome:=r.result||jsonb_build_object('run_id',r.id,'request_id',r.request_id,'source_state',
  case when c->>'status'='COMPLETE'and hash=r.dependency_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end);
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_BASELINE_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create or replace function cp7_analysis_stage.baseline_rows(c jsonb,history_rows jsonb,current_stock jsonb,hash text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 return cp7_model_target_consumer.rows(c,history_rows,current_stock,hash,c->'analog_consumer_context');
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
  'baseline_hash',encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine','model_target_source_hash',c->'model_target_source'->'source_hash')::text,'UTF8'),'sha256'),'hex'));
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
   'production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine','model_target_source_hash',c->'model_target_source'->'source_hash','source_kind',path)::text,'UTF8'),'sha256'),'hex');
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
   'production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine','model_target_source_hash',c->'model_target_source'->'source_hash','source_kind',path)::text,'UTF8'),'sha256'),'hex');
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

create or replace function cp7_bounded_analysis_stage.native_work_fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts',
  'profiles',c->'profiles','production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine','model_target_source_hash',c->'model_target_source'->'source_hash',
  'production_scope',c->'production_sources'->'scope',
  'production',c->'production_sources'->'facts')::text,'UTF8'),'sha256'),'hex')
$$;

create or replace function cp7_supply_native.fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case when c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'
 then cp7_bounded_analysis_stage.work_fingerprint(c) else encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts',
  'profiles',c->'profiles','production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine','model_target_source_hash',c->'model_target_source'->'source_hash',
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
  where n.nspname in('cp7_model_target_source','cp7_model_target_projection','cp7_model_target_consumer','cp7_model_registry_adapter','cp7_model_policy','cp7_model_activation_gate','cp7_product_analog_consumer','cp7_product_analog_choice','cp7_reorder_inputs','cp7_reorder_reader','cp7_planning','cp7_profile','cp7_baseline_native','cp7_analysis_stage','cp7_demand','cp7_baseline','cp7_stock_formula')
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
    'profiles',boundary.c->'profiles','production_policies',boundary.c->'production_policies'->'rows','product_analog_choices',boundary.c->'product_analog_choices','analog_consumer_engine',boundary.c->'analog_consumer_engine','model_target_source_hash',boundary.c->'model_target_source'->'source_hash',
    'query',query.q,'defaults',policy.defaults,'leads',leads.rows,'manuals',manuals.rows,'engine',engine.hash)::text,'UTF8'),'sha256'),'hex'),
  'context_hash',encode(extensions.digest(convert_to(jsonb_build_object('facts',boundary.c->'facts',
    'profiles',boundary.c->'profiles','production_policies',boundary.c->'production_policies'->'rows','product_analog_choices',boundary.c->'product_analog_choices','analog_consumer_engine',boundary.c->'analog_consumer_engine','model_target_source_hash',boundary.c->'model_target_source'->'source_hash',
    'query',query.q,'defaults',policy.defaults,'leads',leads.rows,'manuals',manuals.rows,'engine',engine.hash,
    'complete_stock_summary',complete_stock.summary->'data_hash')::text,'UTF8'),'sha256'),'hex'),
  'apply_enabled',false,'production_go',false)
 from boundary cross join policy cross join leads cross join manuals cross join engine cross join query cross join complete_stock cross join history_stock_key);
end $$;

create or replace function cp7_bounded_analysis_stage.analysis_source(p_products integer,p_match integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with native as materialized(select cp7_bounded_analysis_stage.netting_source(p_products,p_match)c),
 engine as(select encode(extensions.digest(convert_to(string_agg(
  p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')signature
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname in('cp7_model_target_source','cp7_model_target_projection','cp7_model_target_consumer','cp7_model_registry_adapter','cp7_model_policy','cp7_model_activation_gate','cp7_product_analog_consumer','cp7_product_analog_choice','cp7_planning','cp7_profile','cp7_supply_native','cp7_schedule_native','cp7_netting_native','cp7_analysis_native','cp7_analysis_stage','cp7_fabric_native','cp7_wip','cp7_demand','cp7_baseline','cp7_models','cp7_finance','cp7_reorder_supply','cp7_bounded_analysis_stage')
   or p.oid='erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure)
 select c||jsonb_build_object('reorder_supply_engine','cp7.reorder-supply.v1','analysis_engine_signature',signature,
  'material_source',cp7_analysis_native.material_source(c->'facts'->'products',(c->>'captured_at')::timestamptz),
  'fabric_source',cp7_fabric_native.source(c->'facts'->'products',(c->>'captured_at')::timestamptz))from native cross join engine
$$;

create or replace function cp7_analysis_native.source_within(p_products integer,p_match integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with native as materialized(select cp7_netting_native.source_within(p_products,p_match)c),
 engine as(select encode(extensions.digest(convert_to(string_agg(
  p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')signature
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname in('cp7_model_target_source','cp7_model_target_projection','cp7_model_target_consumer','cp7_model_registry_adapter','cp7_model_policy','cp7_model_activation_gate','cp7_product_analog_consumer','cp7_product_analog_choice','cp7_planning','cp7_profile','cp7_supply_native','cp7_schedule_native','cp7_netting_native','cp7_analysis_native','cp7_analysis_stage','cp7_fabric_native','cp7_wip','cp7_demand','cp7_baseline','cp7_models','cp7_finance','cp7_reorder_supply')
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
 where n.nspname in('cp7_model_target_source','cp7_model_target_projection','cp7_model_target_consumer','cp7_model_registry_adapter','cp7_model_policy','cp7_model_activation_gate','cp7_product_analog_consumer','cp7_product_analog_choice','cp7_bounded_analysis_stage','cp7_history_bounded','cp7_history_reference')and p.prokind='f'
$$;

create or replace function cp7_reorder_caller.evaluate(v jsonb,supply jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare products jsonb;stocks jsonb;projections jsonb;seen jsonb;history_statistics jsonb;p jsonb;product jsonb;stock jsonb;
 projected jsonb;net jsonb;lead_net jsonb;kernel jsonb;config jsonb;hist jsonb;k text;root text;item jsonb;
 free numeric;point numeric;good numeric;base_position numeric;candidate numeric;conditional_position numeric;
 status text;reason text;state text;basis text;bound boolean;analysis_at timestamptz;lead numeric;review numeric;
 rows_out jsonb[]:='{}';metadata jsonb;row_value jsonb;
begin
 perform cp7_wip.fields(v,array['points','products','threshold_source_hash','input_path','history_statistics',
  'contract_version','captured_at','query','defaults','leads','manuals','current_stock','threshold_hash',
  'threshold_captured_at','context_hash','engine_hash','native_capture_status','cache_hit','live_ROP_caller_changed','apply_enabled','production_go']);
 if v->>'contract_version'is distinct from'cp7.reorder-reader-snapshot.v1'
  or v->'points'->'query'is distinct from v->'query'or v->'apply_enabled'is distinct from'false'::jsonb
  or v->'production_go'is distinct from'false'::jsonb then raise exception 'CP7_REORDER_EVALUATE_SNAPSHOT';end if;
 perform cp7_demand.instant(v->'captured_at');perform cp7_demand.instant(v->'threshold_captured_at');
 perform cp7_demand.items(v->'products',5000);perform cp7_demand.items(v->'current_stock',5000);
 perform cp7_demand.items(v->'points'->'rows',5000);
 perform cp7_wip.fields(supply,array['contract_version','checked_at','query','status','reason','job','projection','apply_enabled','production_go']);
 if supply->>'contract_version'is distinct from'cp7.reorder-supply-cache.v1'
  or supply->>'status'is null or supply->>'status'not in('UNKNOWN','SCENARIO','PARTIAL')
  or supply->'query'is distinct from v->'query'or supply->'apply_enabled'is distinct from'false'::jsonb
  or supply->'production_go'is distinct from'false'::jsonb then raise exception 'CP7_REORDER_EVALUATE_SUPPLY';end if;
 select coalesce(jsonb_object_agg(x->>'root_id',x),'{}')into products from jsonb_array_elements(v->'products')x;
 select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into stocks from jsonb_array_elements(v->'current_stock')x;
 if(select count(*)from jsonb_each(products))<>jsonb_array_length(v->'products')
  or(select count(*)from jsonb_each(stocks))<>jsonb_array_length(v->'current_stock')then raise exception 'CP7_REORDER_EVALUATE_DUPLICATE';end if;
 if supply->'projection'<>'null'::jsonb then
  if supply->'projection'->'query'is distinct from v->'query'then raise exception 'CP7_REORDER_EVALUATE_SUPPLY';end if;
  perform cp7_demand.items(supply->'projection'->'rows',5000);
  select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into projections from jsonb_array_elements(supply->'projection'->'rows')x;
  if(select count(*)from jsonb_each(projections))<>jsonb_array_length(supply->'projection'->'rows')then raise exception 'CP7_REORDER_EVALUATE_DUPLICATE';end if;
  if supply->'projection'->>'contract_version'is distinct from'cp7.reorder-supply.v1'
   or(select count(*)from jsonb_each(projections))<>jsonb_array_length(v->'points'->'rows')
   or exists(select 1 from jsonb_each(projections)x where not stocks?x.key)then
   raise exception 'CP7_REORDER_EVALUATE_SUPPLY_SCOPE';end if;
 end if;
 -- Build the validated identity set once, instead of copying a growing
 -- object for every target. Keep the same duplicate/scope refusal.
 select coalesce(jsonb_object_agg(cp7_wip.key(x->'target_key'),true),'{}')into seen
  from jsonb_array_elements(v->'points'->'rows')x;
 if(select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'points'->'rows')then
  raise exception 'CP7_REORDER_EVALUATE_IDENTITY';end if;
 history_statistics:=v->'history_statistics';
 for p in select value from jsonb_array_elements(v->'points'->'rows')loop
  k:=cp7_wip.key(p->'target_key');root:=split_part(k,':',1);product:=products->root;stock:=stocks->k;
  if product is null or stock is null or product->'id'is distinct from p->'product_version_id'
   or product->'size_id'is distinct from p->'size_id'or stock->'size_id'is distinct from p->'size_id'
   or stock->>'root_id'is distinct from root then raise exception 'CP7_REORDER_EVALUATE_IDENTITY';end if;
  free:=cp7_wip.pcs(stock->'native_available_pcs');
  point:=null;if p->'point_pcs'<>'null'::jsonb then point:=cp7_wip.pcs(p->'point_pcs');end if;
  kernel:=p->'target';config:=kernel->'inputs';hist:=history_statistics->k;
  if hist is null then raise exception 'CP7_REORDER_EVALUATE_HISTORY';end if;
  good:=null;base_position:=null;candidate:=null;conditional_position:=null;analysis_at:=null;
  status:='UNKNOWN';reason:=coalesce(supply->>'reason','GLOBAL_ALLOCATION_UNAVAILABLE');net:=null;lead_net:=null;
  projected:=projections->k;lead:=null;review:=null;
  if p->'lead_days'<>'null'::jsonb then lead:=cp7_demand.decimal(p->'lead_days');end if;
  if config->'review_days'<>'null'::jsonb then review:=cp7_demand.decimal(config->'review_days');end if;
  bound:=false;
  if supply->>'status'in('SCENARIO','PARTIAL')and projected->>'status'='SCENARIO'
   and projected->'net'->'lead_net'->>'status'='SCENARIO'and lead is not null and review is not null
   and supply->'job'->>'state'='DONE'then
   net:=projected->'net';lead_net:=net->'lead_net';analysis_at:=cp7_demand.instant(supply->'job'->'captured_at');
   -- ROP manual replaces the trigger only. Reuse the Native L position,
   -- comparing it with that manual threshold; do not change the production
   -- target or call net() with a point above its own full target.
   bound:=projected->'size_id'=p->'size_id'and net->'inputs'->>'target_key'=k
    and net->'inputs'->'size_id'=p->'size_id'
    and net->'inputs'->'target_pcs'=kernel->'target_pcs'
    and net->'inputs'->'reorder_point_pcs'=p->'formula_point_pcs'
    and cp7_demand.instant(net->'inputs'->'lead_deadline')=analysis_at+lead*interval'1 day'
    and cp7_demand.instant(net->'inputs'->'deadline')=analysis_at+(lead+review)*interval'1 day'
    and(net->'inputs'->>'available_fg_pcs')::numeric=free
    and cp7_demand.instant(supply->'checked_at')>=cp7_demand.instant(v->'captured_at');
   if bound then
    good:=cp7_wip.pcs(lead_net->'directed_on_time_pcs')+cp7_wip.pcs(lead_net->'incoming_on_time_pcs');
    base_position:=free+good;
    if base_position is distinct from(net->>'lead_position_base_pcs')::numeric then raise exception 'CP7_REORDER_EVALUATE_POSITION';end if;
    if net->'lead_position_conditional_pcs'<>'null'::jsonb then
     conditional_position:=(net->>'lead_position_conditional_pcs')::numeric;candidate:=conditional_position-base_position;
     if candidate<0 then raise exception 'CP7_REORDER_EVALUATE_POSITION';end if;
    end if;
    status:='COMPLETE';reason:=null;
   else reason:='CURRENT_TARGET_STOCK_OR_HORIZON_CHANGED';end if;
  elsif projected is not null then reason:=coalesce(projected->>'reason',reason);end if;
  if status<>'COMPLETE'then net:=null;lead_net:=null;analysis_at:=null;end if;
  basis:=case when point is null then'NOT_ENOUGH_DATA'when p->>'point_basis'='MANUAL'then'MANUAL'else'FORMULA'end;
  state:=case when point is null or point=0 then'NO_POINT'
   when coalesce(base_position,free)<=point then'AT_OR_BELOW'else'ABOVE'end;
  metadata:=jsonb_build_object('contract_version','cp7.fg-reorder-projection.v3','target_demand',p->'demand_provenance',
   'threshold_source',p->'source_kind','threshold_checked_at',v->'threshold_captured_at','stock_checked_at',v->'captured_at',
   'analysis_at',case when analysis_at is not null then cp7_planning.utc(analysis_at)end,
   'lead_deadline',case when bound then net->'inputs'->'lead_deadline'else'null'::jsonb end,
   'target_deadline',case when bound then net->'inputs'->'deadline'else'null'::jsonb end,
   'base_position_pcs',base_position::text,'conditional_position_pcs',conditional_position::text,
   'candidate_pcs',candidate::text,'target_pcs',kernel->'target_pcs',
   'production_base_pcs',case when bound then net->'q_base_pcs'else'null'::jsonb end,
   'production_conditional_pcs',case when bound then net->'q_conditional_pcs'else'null'::jsonb end,
   'manual_state',p->'manual_state','manual_reference',p->'manual_reference',
   'raw_WIP_credited',false,'candidate_mutes_alert',false);
  row_value:=jsonb_build_object('contract_version','cp7.fg-reorder-row.v2','target_key',k,'root_id',root,
   'size_id',p->'size_id','model_id',product->'model_id','product_id',product->'id','sku',product->'sku',
   'product_name',product->'product_name','size_code',null,'free_pcs',free::text,'sales_pcs',p->'available_total_pcs',
   'counted_days',(p->>'available_days')::integer,'sale_days',(hist->>'sale_days')::integer,
   -- Display the demand input the Native target actually used. A selected
   -- manual demand profile must not be labelled with its historical mean.
   'daily_mean',((config->>'daily_total_pcs')::numeric/nullif((config->>'counted_days')::numeric,0))::text,
   'daily_sd',config->'daily_sd','lead_days',p->'lead_days','lead_basis',p->'lead_basis',
   'lead_lots',null,'lead_groups',null,'buffer_mode',config->'mode','buffer_days',config->'buffer_days',
   'service_level',case when config->>'mode'='STATISTICAL'then config->'service_level'else'null'::jsonb end,
   'z',case when config->>'mode'='STATISTICAL'then cp7_stock_formula.z((config->>'service_level')::numeric)::text end,
   'safety_pcs',kernel->'lead_safety_pcs','formula_point',p->'formula_point_pcs',
   'manual_point',case when p->>'manual_state'='ACTIVE'then p->'point_pcs'else'null'::jsonb end,
   'manual_revision',case when p->'manual_reference'<>'null'::jsonb then(p->'manual_reference'->>'revision')::integer end,
   'point',point::text,'basis',basis,'reason',case when point is null then p->'reason'else'null'::jsonb end,
   'wip_pcs',good::text,'wip_status',status,'wip_reason',reason,'state',state,'changed_at',v->'captured_at','projection',metadata);
  if product->'is_active'='true'::jsonb then rows_out:=array_append(rows_out,row_value);end if;
 end loop;
 if(select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'products')
  or(select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'current_stock')then raise exception 'CP7_REORDER_EVALUATE_SCOPE';end if;
 return jsonb_build_object('contract_version','cp7.fg-reorder-evaluation.v2','captured_at',v->'captured_at',
  'query',v->'query','rows',to_jsonb(rows_out),'live_ROP_caller_changed',false,'apply_enabled',false,'production_go',false);
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
   'analog_resolution',row_value->'analog_resolution',
   'demand_provenance',(row_value->'demand_provenance')||jsonb_build_object(
    'model',case when profile->>'quality'='UNREVIEWED'then(row_value->'model_resolution')||jsonb_build_object(
     'state','BASELINE_RETAINED','reason','EXISTING_REORDER_DEFAULTS_RETAINED_UNREVIEWED_PROFILE',
     'baseline_target',kernel,'forecast',null,'forecast_applied',false)else row_value->'model_resolution'end,
    'basis',case when profile->>'quality'='UNREVIEWED'and counted>=14 then'OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'else coalesce(row_value->'demand_estimate'->>'basis','UNKNOWN')end,
    'daily_total_pcs',kernel->'inputs'->'daily_total_pcs','counted_days',kernel->'inputs'->'counted_days',
    'daily_sd',kernel->'inputs'->'daily_sd','target_pcs',kernel->'target_pcs','reorder_point_pcs',kernel->'reorder_point_pcs'),
   'manual_state',manual_state,'manual_reference',manual_row,
   'supply_alignment',case when source_kind='PLANNING_PROFILE'and point_basis='FORMULA'and reason is null then'NATIVE_TARGET'else'NEEDS_EXPLICIT_BINDING'end));
 end loop;
 if (select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'history')
  or (select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'products')then raise exception 'CP7_REORDER_HISTORY_SCOPE_MISMATCH';end if;
 selection_hash:=encode(extensions.digest(convert_to(jsonb_build_object('native_source',v->'source_hash',
  'query',v->'query','defaults',defaults,'leads',leads,'manuals',manuals,'compiler','reorder-points-1')::text,'UTF8'),'sha256'),'hex');
 return jsonb_build_object('contract_version','cp7.reorder-native-points.v1','captured_at',v->'captured_at','query',v->'query',
  'native_source_hash',v->'source_hash','selection_hash',selection_hash,'rows',to_jsonb(output_rows),'apply_enabled',false,'production_go',false);
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
  'versions',jsonb_build_object('engine',c->'analysis_engine_signature','policy',cp7_supply_native.fingerprint(c),'models','policy-gated-dated-model-target-1',
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

create or replace function cp7_netting_native.timeline(c jsonb,r jsonb,etas jsonb,edges jsonb,matching jsonb,wip jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare cfg jsonb:=r->'profile'->'config';rate numeric;horizon numeric;remaining numeric;duration numeric;qty numeric;
 ready timestamptz:=(c->>'captured_at')::timestamptz;deadline timestamptz;at_time timestamptz;
 model_input jsonb:=r->'model_resolution';model_applied boolean:=coalesce(r->'model_resolution'->>'state'='MODEL_PROJECTED',false);
 projection jsonb;timeline_input jsonb;timeline_result jsonb;events jsonb[]:='{}';e jsonb;eta jsonb;i integer:=0;seq integer:=0;eta_at jsonb;eta_repeated jsonb;
begin
 if r->'target'->>'status'is distinct from 'SCENARIO'or r->'demand_estimate'->>'daily_pcs'is null then
  return jsonb_build_object('status','UNKNOWN','reason','SELECTED_TARGET_OR_DEMAND_UNKNOWN');end if;
 if r->>'available_fg_pcs'like '-%'then return jsonb_build_object('status','UNKNOWN',
  'reason','NATIVE_RESERVATIONS_EXCEED_ON_HAND_SIGNED_GAP_PRESERVED');end if;
 if model_applied then
  if r->'target'->'model_input'is distinct from model_input
   or model_input->>'source_hash'is distinct from c->'model_target_source'->>'source_hash'
   or model_input->'forecast_applied'is distinct from'true'::jsonb then raise exception 'CP7_MODEL_TIMELINE_BINDING';end if;
  if cfg->'lead_days'is distinct from r->'target'->'inputs'->'lead_days'
   or cfg->'review_days'is distinct from r->'target'->'inputs'->'review_days'then raise exception 'CP7_MODEL_TIMELINE_PROFILE';end if;
  projection:=cp7_model_target_projection.project(model_input->'baseline_target'->'inputs',
   jsonb_build_object('contract_version','cp7.model-target-vector.v1','forecast_from_date',model_input->'forecast_from_date',
    'forecasts',model_input->'forecast'->'forecasts'),(ready at time zone'Asia/Jakarta')::date);
  if projection->>'state'is distinct from'ARITHMETIC_CANDIDATE'or r->'target'is distinct from
   ((projection->'baseline')||(projection->'projected')||jsonb_build_object('reason',projection->'reason',
    'model_input',model_input,'forecast_applied',true))then raise exception 'CP7_MODEL_TIMELINE_TARGET_MISMATCH';end if;
 else rate:=cp7_demand.decimal(r->'demand_estimate'->'daily_pcs');end if;
 horizon:=cp7_demand.decimal(cfg->'lead_days')+cp7_demand.decimal(cfg->'review_days');
 deadline:=ready+(horizon::text||' days')::interval;remaining:=horizon;
 while remaining>0 loop
  duration:=least(1,remaining);i:=i+1;
  if i>3660 then raise exception 'CP7_NETTING_TIMELINE_HORIZON_LIMIT';end if;
  at_time:=least(deadline,ready+(i::text||' days')::interval);qty:=case when model_applied then cp7_model_target_projection.sum_window(model_input->'forecast'->'forecasts',i-1,i-1+duration)else ceil(rate*duration*1000000000000)/1000000000000 end;
  events:=array_append(events,jsonb_build_object('key','forecast-day-'||i,'at',cp7_planning.utc(at_time),
   'sequence',(10000+i)::text,'kind','DEMAND','qty_pcs',case when model_applied then qty::text else qty::numeric(42,12)::text end,'refs',r->'refs'));
  remaining:=remaining-duration;
 end loop;
 for e in select value from jsonb_array_elements(edges)where value->>'target_key'=r->>'target_key'order by value->>'key'loop
  -- One ETA per edge position. The map is built where the per-edge scan
  -- first ran; a repeated position key fails as that scan did.
  if eta_at is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into eta_at,eta_repeated
    from(select value->>'position_key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(etas)
     where value->>'position_key'is not null group by 1)f;
  end if;
  if eta_repeated?(e->>'position_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  eta:=eta_at->(e->>'position_key');
  if eta->'at'='null'::jsonb then continue;end if;
  at_time:=cp7_demand.instant(eta->'at');
  if at_time>deadline then continue;end if;
  seq:=seq+1;events:=array_append(events,jsonb_build_object('key','supply-'||(e->>'key'),
   'at',cp7_planning.utc(at_time),'sequence',seq::text,'kind','SUPPLY','qty_pcs',e->'projected_good_pcs','refs',e->'refs'));
 end loop;
 timeline_input:=jsonb_build_object('contract_version',case when model_applied then'cp7.model-target-timeline-input.v1'else'cp7.timeline-input.v1'end,
  'snapshot_id',wip->'snapshot_id','scope_id','GLOBAL_NATIVE_PLANNING','target_key',r->'target_key',
  'size_id',r->'size_id','mode','BACKLOG','initial_fg_pcs',r->'available_fg_pcs',
  'from_at',cp7_planning.utc(ready),'through_at',cp7_planning.utc(deadline),'events',to_jsonb(events),'refs',r->'refs');
 timeline_result:=case when model_applied then cp7_model_target_consumer.timeline(timeline_input)else cp7_baseline.timeline(timeline_input)end;
 return timeline_result||jsonb_build_object('timing_basis',case when model_applied then'DATED_MODEL_VECTOR_AT_EACH_24H_END_FROM_CAPTURE'else'SELECTED_DAILY_RESIDUAL_AT_EACH_24H_END_FROM_CAPTURE'end,
   'unmet_mode_basis','EXPLICIT_TECHNICAL_BACKLOG_SCENARIO','buffer_consumed_as_demand',false);
end $$;

create or replace function cp7_analysis_stage.analysis_targets(c jsonb,rows jsonb,products_by_root jsonb,stock_by_target jsonb,history_by_target jsonb,
 edges_by_target jsonb,match_results_by_target jsonb,plan_aids jsonb,fabric_plan jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare r jsonb;refs jsonb;policy text;product jsonb;stock jsonb;hist jsonb;commercial jsonb;row_aids jsonb;rounded jsonb;rounding_aids jsonb;v jsonb;target_timeline jsonb;
 t_assumptions jsonb;t_warnings jsonb;t_actions jsonb;t_recommendations jsonb;t_models jsonb;t_materials jsonb;t_metrics jsonb;t_timeline jsonb;
 targets_acc jsonb[]:='{}';known_keys text[]:='{}';materials_null boolean:=false;
 demand_unknown boolean:=false;captured text:=c->>'captured_at';
begin
 for r in select x.value from jsonb_array_elements(rows)with ordinality x(value,o)order by x.o loop
  t_assumptions:='[]';t_warnings:='[]';t_actions:='[]';t_recommendations:='[]';t_models:='[]';t_materials:='[]';t_metrics:='[]';t_timeline:='[]';
  if r->'demand_estimate'->>'daily_pcs'is null then demand_unknown:=true;end if;
  refs:=r->'refs';policy:=r->'production_policy'->'policy'->>'state';
  if policy is null then
   t_warnings:=jsonb_build_array('PRODUCTION_POLICY_UNREVIEWED:'||(r->>'target_key'));
   t_actions:=jsonb_build_array(jsonb_build_object('key','review-policy-'||(r->>'target_key'),
    'intent','REVIEW_SOURCE','source_keys','[]'::jsonb,'target_keys','[]'::jsonb,'primary_reason','PRODUCTION_POLICY_UNREVIEWED',
    'conditional',false,'source_links',refs,'display_priority',jsonb_build_object('rank',null,'lane','REVIEW_DATA',
     'basis',jsonb_build_array('Status produksi produk perlu diperiksa'),'rule_version','native-review-1')));
   targets_acc:=array_append(targets_acc,jsonb_build_object('assumptions',t_assumptions,'warnings',t_warnings,'actions',t_actions,
    'recommendations',t_recommendations,'models',t_models,'materials',t_materials,'metrics',t_metrics,'timeline',t_timeline));continue;
  end if;
  product:=products_by_root->split_part(r->>'target_key',':',1);
  stock:=stock_by_target->(r->>'target_key');hist:=history_by_target->(r->>'target_key');
  if jsonb_array_length(product)>1 or jsonb_array_length(stock)>1 or jsonb_array_length(hist)>1 then
   raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';
  end if;
  product:=product->0;stock:=stock->0;hist:=hist->0;
  row_aids:=plan_aids;
  if r->'profile'->>'quality'='SELECTED_ASSUMPTION'then
   row_aids:=row_aids||jsonb_build_array(r->'profile'->>'profile_id');
   t_assumptions:=jsonb_build_array(jsonb_build_object('id',r->'profile'->>'profile_id',
    'label','Aturan permintaan dan target yang dipilih untuk '||(r->>'sku'),
    'origin','OWNER_INPUT','confirmed_for_operation',false));
  end if;
  commercial:=product->'commercial'->0;known_keys:=array_append(known_keys,r->>'target_key');
  rounded:=cp7_analysis_native.rounded_suggestion(r);rounding_aids:=case when rounded->>'applied'='true'then row_aids else '[]'::jsonb end;
  t_recommendations:=jsonb_build_array(jsonb_build_object(
   'target',jsonb_build_object('kind','PRODUCT','key',r->'target_key','brand_id',product->'brand_id',
    'product_id',product->'root_id','product_version_id',product->'id','size_id',r->'size_id',
    'commercial_identity',jsonb_build_object('state',case when commercial is null then 'LEGACY_UNMAPPED'else 'RESOLVED'end,
     'sku_id',commercial->'sku_id','sku_version_id',commercial->'version_id',
     'membership_version_id',case when commercial is null then null else(commercial->>'version_id')||':'||(product->>'root_id')end,
     'grouping_basis','CURRENT_RESTATED')),
   'production_state',policy,'actual_fg',cp7_analysis_native.fact(stock->'availability'->>'physical_fg_pcs','PCS',stock->'refs'),
   'target_qty',cp7_analysis_native.fact(r->'target'->>'target_pcs','PCS',refs,row_aids),
   'q_base',cp7_analysis_native.fact(r->>'base_gap_pcs','PCS',refs,row_aids),
   'q_conditional',cp7_analysis_native.fact(r->>'conditional_gap_pcs','PCS',refs,row_aids),
   'suggested_new',cp7_analysis_native.fact(rounded->>'suggested_pcs','PCS',refs,rounding_aids),
   'rounding_extra',cp7_analysis_native.fact(rounded->>'extra_pcs','PCS',refs,rounding_aids),
   'feasible_new',cp7_analysis_native.fact(case when policy in('PAUSED','STOPPED')then '0'else null end,'PCS',refs),
   'unresolved_qty',cp7_analysis_native.fact(case when policy in('PAUSED','STOPPED')then r->>'base_gap_pcs'else null end,'PCS',refs,row_aids),
   'reason_codes',jsonb_build_array('MATERIAL_FEASIBILITY_NOT_PROVEN'),'assumption_ids',row_aids));
  if r->'demand_estimate'->>'daily_pcs'is not null and r->'target'->>'horizon_days'is not null then
  t_models:=jsonb_build_array(jsonb_build_object('target_key',r->'target_key','method_id',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then r->'model_resolution'->'selected_model'->>'method'else coalesce(r->'demand_estimate'->>'basis','NATIVE_AVAILABLE_HISTORY')end,
   'version',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then'policy-gated-dated-model-target-1'else'native-available-history-fallback-1'end,'mode',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then'EVALUATED'else'FALLBACK'end,
   'demand_rate',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then jsonb_build_object('state','NOT_APPLICABLE','unit','PCS/DAY','reason','DATED_VECTOR_HAS_NO_SINGLE_DAILY_RATE','refs',refs)else cp7_analysis_native.fact(r->'demand_estimate'->>'daily_pcs','PCS/DAY',refs,row_aids)end,
   'observed_days',hist->'available_days','stockout_days',hist->'stockout_days','unknown_days',hist->'unknown_days',
   'horizon_days',ceil((r->'target'->>'horizon_days')::numeric),
   'selection_reason',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then 'Current policy-gated dated vector; immutable model run '||(r->'model_resolution'->>'run_id')||'; historical variation remains a selected assumption'else'Native available-history/manual fallback; no backtest promotion without earlier-known training evidence'end,
   'validation_fold_ids','[]'::jsonb,'scores','[]'::jsonb));
  end if;
  v:=cp7_analysis_native.material_needs(c,r,row_aids);
  if v is null then materials_null:=true;else t_materials:=t_materials||('[]'::jsonb||v);end if;
  v:=cp7_fabric_native.needs(c,r,row_aids,fabric_plan);
  if v is null then materials_null:=true;else t_materials:=t_materials||('[]'::jsonb||v);end if;
  t_metrics:=jsonb_build_array(jsonb_build_object('metric_id','AVAILABLE_FG_PCS:'||(r->>'target_key'),'version','native-availability-1',
   'value',cp7_analysis_native.fact(r->>'available_fg_pcs','PCS',refs),'formula_ref','NATIVE_PHYSICAL_MINUS_ACTIVE_DRAFT_RESERVATIONS_ONCE',
   'operands',jsonb_build_array(cp7_analysis_native.fact(stock->'availability'->>'physical_fg_pcs','PCS',stock->'refs'),
    cp7_analysis_native.fact(stock->'availability'->>'reserved_pcs','PCS',stock->'refs')),
   'readiness','READY','scope_kind','TARGET','scope_key',r->'target_key',
   'period_start',((captured::timestamptz)at time zone 'Asia/Jakarta')::date::text,
   'period_end',((captured::timestamptz)at time zone 'Asia/Jakarta')::date::text,'knowledge_mode','CURRENT'));
  t_actions:=jsonb_build_array(jsonb_build_object('key','review-material-'||(r->>'target_key'),'intent','REVIEW_SOURCE',
   'source_keys','[]'::jsonb,'target_keys',jsonb_build_array(r->'target_key'),'primary_reason','MATERIAL_FEASIBILITY_NOT_PROVEN',
   'conditional',true,'source_links',refs,'display_priority',jsonb_build_object('rank',null,'lane','REVIEW_DATA',
    'basis',jsonb_build_array('Periksa bahan dan batas produksi baru'),'rule_version','native-review-1')));
  declare n jsonb:=jsonb_build_object('allocation',jsonb_build_object('allocation',jsonb_build_object('edges',
   coalesce(edges_by_target->(r->>'target_key'),'[]'::jsonb))),'match_results',coalesce(match_results_by_target->(r->>'target_key'),'[]'::jsonb));
  begin
  with events as materialized(
   select x.value event,x.value->'event' e,x.ordinality ordinal
    from jsonb_array_elements(coalesce(r->'timeline'->'events','[]'))with ordinality x),
  classified as materialized(
   select events.*,case when events.e->>'kind'='SUPPLY'then coalesce(
    (select x->>'match'from jsonb_array_elements(coalesce(n->'allocation'->'allocation'->'edges','[]'))x
     where 'supply-'||(x->>'key')=events.e->>'key'and x->>'target_key'=r->>'target_key'limit 1),
    case when exists(select 1 from jsonb_array_elements(n->'match_results')x
     where 'supply-'||(x->>'position_key')=events.e->>'key'and x->>'target_key'=r->>'target_key'and x->'result'->>'match'='CONFIRMED_TARGET')then'CONFIRMED_TARGET'end)
    else null end supply_match from events)
  select coalesce(jsonb_agg(jsonb_build_object('date',((t.e->>'at')::timestamptz at time zone 'Asia/Jakarta')::date::text,
    'target_key',r->'target_key','demand',cp7_analysis_native.fact(case when t.e->>'kind'='DEMAND'then t.e->>'qty_pcs'else '0'end,'PCS',t.e->'refs',row_aids),
    'directed_supply',cp7_analysis_native.fact(case when t.e->>'kind'='DEMAND'or t.supply_match='CANDIDATE_MATCH'then '0'
     when t.supply_match='CONFIRMED_TARGET'then t.e->>'qty_pcs'else null end,'PCS',t.e->'refs',row_aids),
    'candidate_supply',cp7_analysis_native.fact(case when t.e->>'kind'='DEMAND'or t.supply_match='CONFIRMED_TARGET'then '0'
     when t.supply_match='CANDIDATE_MATCH'then t.e->>'qty_pcs'else null end,'PCS',t.e->'refs',row_aids),
    'proposed_new_supply',cp7_analysis_native.fact(null,'PCS',t.e->'refs'),'balance_end',cp7_analysis_native.fact(t.event->>'balance_pcs','PCS',t.e->'refs',row_aids),
    'mode','BACKLOG','assumed',true,'unmet_demand',cp7_analysis_native.fact(t.event->>'new_unmet_pcs','PCS',t.e->'refs',row_aids),
    'backlog_qty',cp7_analysis_native.fact(case when t.event->>'balance_pcs'is not null then greatest(0,-(t.event->>'balance_pcs')::numeric)::text else null end,'PCS',t.e->'refs',row_aids),
    'min_intraday_balance',cp7_analysis_native.fact(r->'timeline'->>'minimum_balance_pcs','PCS',t.e->'refs',row_aids),
    'first_gap_at',r->'timeline'->'first_known_gap'->'at','timing_basis','DATE_POLICY',
    'timing_policy_id',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then'dated-model-each24h-from-capture-1'else'selected-native-each24h-from-capture-1'end,'event_refs',t.e->'refs')order by t.ordinal),'[]'::jsonb)into target_timeline from classified t;
  t_timeline:=t_timeline||target_timeline;
  end;
  targets_acc:=array_append(targets_acc,jsonb_build_object('assumptions',t_assumptions,'warnings',t_warnings,'actions',t_actions,
   'recommendations',t_recommendations,'models',t_models,'materials',t_materials,'metrics',t_metrics,'timeline',t_timeline));
 end loop;
 return jsonb_build_object('targets',to_jsonb(targets_acc),'known_keys',to_jsonb(known_keys),'demand_unknown',demand_unknown,'materials_null',materials_null);
end $$;
