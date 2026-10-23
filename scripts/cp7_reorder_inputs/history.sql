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

-- Current free FG is refreshed even when the closed-day threshold is cached.
-- Draft reservation validation is still the actual Native availability kernel.
create function cp7_reorder_inputs.current_stock(c jsonb,summary jsonb,hash text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare f jsonb:=c->'facts';products jsonb;stock_by_root jsonb;drafts_by_root jsonb;p jsonb;r jsonb;
 refs jsonb;availability jsonb;native_available numeric;current_rows jsonb[]:='{}';
begin
 select coalesce(jsonb_agg(x order by x->>'root_id'),'[]')into products from jsonb_array_elements(f->'products')x;
 if summary is null or summary='null'::jsonb then
  if c->>'status'is distinct from'COMPLETE'then raise exception 'CP7_REORDER_STOCK_SNAPSHOT_MISMATCH';end if;
  return cp7_analysis_stage.history_stock(c,products,hash);
 end if;
 if c->>'status'is distinct from'INCOMPLETE'or not(jsonb_array_length(f->'stock')=50001
  or coalesce(c->'stock_raw_omitted'='true'::jsonb and c->'stock_rows_at_least'='50001'::jsonb
   and jsonb_array_length(f->'stock')=0,false))
  or summary->>'contract_version'is distinct from'cp7.reorder-stock-summary.v1'
  or summary->>'captured_at'is distinct from cp7_planning.utc((c->>'captured_at')::timestamptz)
  or(summary->>'products')::integer is distinct from jsonb_array_length(products)
  or(summary->>'raw_rows_read')::bigint<50001 or summary->'raw_rows_truncated'is distinct from'false'::jsonb then
  raise exception 'CP7_REORDER_STOCK_SNAPSHOT_MISMATCH';end if;
 select coalesce(jsonb_object_agg(x->>'root_id',x),'{}')into stock_by_root from jsonb_array_elements(summary->'current_stock')x;
 if(select count(*)from jsonb_each(stock_by_root))<>jsonb_array_length(products)then raise exception 'CP7_REORDER_STOCK_SNAPSHOT_MISMATCH';end if;
 select coalesce(jsonb_object_agg(x.root_id,x.drafts),'{}')into drafts_by_root from(
  select value->>'root_id'root_id,jsonb_agg(jsonb_build_object('lineage_key',value->>'id','qty_pcs',value->>'qty_pcs',
   'refs',jsonb_build_array(jsonb_build_object('kind','SALE_ITEM','id',value->>'id','revision',value->>'revision')))order by value->>'id')drafts
  from jsonb_array_elements(f->'sales')where value->>'status'='DRAFT'and value->>'root_id'is not null group by 1)x;
 for p in select value from jsonb_array_elements(products)loop
  r:=stock_by_root->(p->>'root_id');refs:=jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',p->>'id','revision','1'));
  if r is null or r->>'size_id'is distinct from p->>'size_id'then raise exception 'CP7_REORDER_STOCK_SNAPSHOT_MISMATCH';end if;
  native_available:=(r->>'free_pcs')::numeric;
  availability:=cp7_demand.availability(jsonb_build_object('contract_version','cp7.available-input.v1',
   'snapshot_id',hash,'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','target_key',(p->>'root_id')||':'||(p->>'size_id'),
   'size_id',p->'size_id','fg_basis','ON_HAND_AFTER_POSTED','fg_pcs',r->'physical_pcs',
   'open_drafts',coalesce(drafts_by_root->(p->>'root_id'),'[]'),'residual_future_pcs','0','refs',refs));
  if(availability->>'available_fg_pcs')::numeric<>native_available or native_available<0 then
   raise exception 'CP7_PLANNING_NATIVE_RESERVATION_MISMATCH';end if;
  current_rows:=array_append(current_rows,jsonb_build_object('target_key',(p->>'root_id')||':'||(p->>'size_id'),
   'root_id',p->'root_id','size_id',p->'size_id','sku',p->'sku','product_name',p->'product_name',
   'is_active',(p->>'is_active')::boolean,'grade_basis','NATIVE_SELLABLE_GRADE_A_AND_B','availability',availability,
   'projection_basis','CURRENT_STOCK_ONLY_NO_FORECAST','native_available_pcs',native_available::text,'refs',refs));
 end loop;
 return to_jsonb(current_rows);
end $$;
alter function cp7_reorder_inputs.current_stock(jsonb,jsonb,text)owner to cp7_capture;
revoke all on function cp7_reorder_inputs.current_stock(jsonb,jsonb,text)from public,anon,authenticated,service_role;
