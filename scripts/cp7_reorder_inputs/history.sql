-- Shared Native demand/profile inputs for the small reorder refresh.
-- Orchestrates the ACTUAL staged history and target functions; no second
-- sale, availability, demand, lead, buffer or target formula lives here.
-- Private, read-only; installation and the live ROP caller remain separate.
create schema cp7_reorder_inputs authorization cp7_capture;
revoke all on schema cp7_reorder_inputs from public,anon,authenticated,service_role;

create function cp7_reorder_inputs.history(c jsonb,q jsonb)returns jsonb
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
  chunk_targets:=cp7_analysis_stage.baseline_rows(c,chunk_rows,stock,g->>'baseline_hash');
  for item in select value from jsonb_array_elements(chunk_rows)loop rows_out:=array_append(rows_out,item);end loop;
  for item in select value from jsonb_array_elements(chunk_targets)loop targets_out:=array_append(targets_out,item);end loop;
  offset_at:=offset_at+per;
 end loop;
 return jsonb_build_object('contract_version','cp7.reorder-native-inputs.v1','captured_at',c->'captured_at',
  'query',q,'source_hash',g->'baseline_hash','history_hash',g->'hash',
  'target_engine','EXISTING_NATIVE_STAGED_BASELINE','products',c->'facts'->'products','history',to_jsonb(rows_out),
  'current_stock',stock,'targets',to_jsonb(targets_out),'apply_enabled',false,'production_go',false);
end $$;
alter function cp7_reorder_inputs.history(jsonb,jsonb)owner to cp7_capture;
revoke all on function cp7_reorder_inputs.history(jsonb,jsonb)from public,anon,authenticated,service_role;
