create or replace function cp7_stock_formula.fg_source()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare outcome jsonb;lvl numeric:=(cp7_stock_formula.current_settings()->>'service_level')::numeric;s jsonb;stock jsonb;
begin
 if erp.has_permission('warehouse.fg.view')is not true then raise exception using errcode='42501',message='CP7_FORMULA_FG_SOURCE_DENIED';end if;
 if cp7_stock_formula.ensure_computed()then
  select jsonb_build_object('rows',coalesce(jsonb_agg(cp7_stock_formula.alert_row(e.row,lvl)order by e.row->>'sku',e.target_key)
   filter(where e.row->>'state'='AT_OR_BELOW'),'[]'),
   'states',coalesce(jsonb_object_agg(e.target_key,case when e.row->>'state'='ABOVE'then'ABOVE_REORDER_POINT'else'NO_REORDER_POINT'end)
    filter(where e.row->>'state'<>'AT_OR_BELOW'),'{}'))into outcome from cp7_reorder_caller.evaluations e;
 else
  -- No model WIP or old projected credit is reused while the lock is held.
  -- Validate the threshold key and current free stock, then check EVERY row,
  -- including a newly low item. A changed threshold leaves alerts unchecked.
  s:=cp7_reorder_inputs.source_within(5000);
  if not exists(select 1 from cp7_reorder_caller.use_marks)
   or(select count(*)from cp7_reorder_caller.evaluations)<>(select count(*)from jsonb_array_elements(s->'native'->'facts'->'products')p where p->'is_active'='true'::jsonb)
   or exists(select 1 from cp7_reorder_caller.evaluations e where e.threshold_hash is distinct from s->>'threshold_hash')then
   raise exception using errcode='55P03',message='CP7_FORMULA_BUSY_SOURCE_CHANGED';end if;
  stock:=cp7_reorder_inputs.current_stock(s->'native',s->'stock_summary',s->>'context_hash');
  with live as(select e.target_key,e.row||(jsonb_build_object('free_pcs',x->'native_available_pcs',
    'wip_pcs',null,'wip_status','UNKNOWN','wip_reason','GLOBAL_SOURCE_NOT_REVALIDATED_WHILE_BUSY'))r
   from cp7_reorder_caller.evaluations e join jsonb_array_elements(stock)x on x->>'target_key'=e.target_key),
  checked as(select target_key,jsonb_set(r,'{projection}',r->'projection'||jsonb_build_object('analysis_at',null,
   'base_position_pcs',null,'conditional_position_pcs',null,'candidate_pcs',null))r,
   r->>'point'is not null and(r->>'point')::numeric>0 and(r->>'free_pcs')::numeric<=(r->>'point')::numeric low from live)
  select jsonb_build_object('rows',coalesce(jsonb_agg(cp7_stock_formula.alert_row(r,lvl)order by r->>'sku',target_key)filter(where low),'[]'),
   'states',coalesce(jsonb_object_agg(target_key,case when r->>'point'is null or(r->>'point')::numeric=0 then'NO_REORDER_POINT'else'ABOVE_REORDER_POINT'end)
    filter(where not low),'{}'))into outcome from checked;
 end if;
 if erp.has_permission('warehouse.fg.view')is not true then raise exception using errcode='42501',message='CP7_FORMULA_FG_SOURCE_DENIED';end if;
 return outcome;
end $$;
