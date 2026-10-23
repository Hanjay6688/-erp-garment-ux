-- Assemble the minute-reader inputs in one SQL snapshot. Raw Native capture
-- remains unchanged: only its stock-array overflow can use the separate,
-- complete SQL stock summary. Every other Native completeness guard stays.
create function cp7_reorder_inputs.compile(s jsonb)returns jsonb
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
  if c->>'status'is distinct from'INCOMPLETE'or jsonb_array_length(f->'stock')<>50001
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
   or(summary->>'raw_rows_read')::bigint<jsonb_array_length(f->'stock')then
   raise exception 'CP7_REORDER_STOCK_SNAPSHOT_MISMATCH';end if;
  path:='COMPLETE_SQL_STOCK_SUMMARY_RAW_NATIVE_INCOMPLETE';
  hash:=encode(extensions.digest(convert_to(jsonb_build_object('native_non_stock',f-'stock',
   'complete_stock_summary',summary->'data_hash','source_kind',path)::text,'UTF8'),'sha256'),'hex');
  baseline_hash:=encode(extensions.digest(convert_to(jsonb_build_object('native_non_stock',f-'stock',
   'complete_stock_summary',summary->'data_hash','profiles',c->'profiles',
   'production_policies',c->'production_policies'->'rows','source_kind',path)::text,'UTF8'),'sha256'),'hex');
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
   chunk_targets:=cp7_analysis_stage.baseline_rows(c,chunk_rows,stock,baseline_hash);
   for item in select value from jsonb_array_elements(chunk_rows)loop rows_out:=array_append(rows_out,item);end loop;
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
alter function cp7_reorder_inputs.compile(jsonb)owner to cp7_capture;
revoke all on function cp7_reorder_inputs.compile(jsonb)from public,anon,authenticated,service_role;

-- A caller with a cache can read one source snapshot, compare context_hash,
-- then compile that exact snapshot only on a miss. This convenience entry
-- point performs the same sequence without a cache or any persistent writes.
create function cp7_reorder_inputs.read_points(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select cp7_reorder_inputs.compile(cp7_reorder_inputs.source_within(p_products))
$$;
alter function cp7_reorder_inputs.read_points(integer)owner to cp7_capture;
revoke all on function cp7_reorder_inputs.read_points(integer)from public,anon,authenticated,service_role;
