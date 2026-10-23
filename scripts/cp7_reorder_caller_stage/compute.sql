create or replace function cp7_stock_formula.compute(p_at timestamptz,p_budget interval)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'set jit=off as $$
declare started timestamptz:=clock_timestamp();deadline timestamptz;source jsonb;operational jsonb;supply jsonb;
 snapshot jsonb;answer jsonb;prepared_rows jsonb;mats jsonb;cfg jsonb;n_items integer;n_low integer;checked timestamptz;wip_read integer:=0;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if p_at is null or p_budget is null or p_budget<interval'0 seconds'then raise exception 'CP7_FORMULA_BUDGET';end if;
 if not pg_try_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0))then
  raise exception using errcode='55P03',message='CP7_FORMULA_BUSY';end if;
 deadline:=started+p_budget;
 -- One statement/MVCC snapshot for threshold/stock and optional current
 -- operational source. Never launch or step a large analysis from a tick.
 with s as materialized(select cp7_reorder_inputs.source_within(5000)c),
 op as materialized(select case when s.c->>'status'='COMPLETE'and clock_timestamp()<deadline
  and exists(select 1 from cp7_analysis_stage.jobs j where j.state='DONE'and j.query=s.c->'query'
   and j.reference->>'reorder_supply_engine'='cp7.reorder-supply.v1'
   and cp7_analysis_stage.retention(j.state,j.updated_at)->>'state'='KEPT')then
   cp7_analysis_native.source_within(5000,10000)||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED')end c from s)
 select s.c,op.c,case when op.c is not null then cp7_reorder_supply.read_job(op.c,s.c->'query')end
  into source,operational,supply from s cross join op;
 checked:=(source->>'captured_at')::timestamptz;
 if supply is null then
  supply:=jsonb_build_object('contract_version','cp7.reorder-supply-cache.v1','checked_at',source->'captured_at',
   'query',source->'query','status','UNKNOWN','reason',case
    when source->>'status'<>'COMPLETE'then'CURRENT_GLOBAL_SOURCE_INCOMPLETE'
    when clock_timestamp()>=deadline then'WIP_READ_TIME_BUDGET_EXHAUSTED'
    when exists(select 1 from cp7_analysis_stage.jobs j where j.state='RUNNING'and j.query=source->'query')then'GLOBAL_ANALYSIS_IN_PROGRESS'
    else'GLOBAL_ANALYSIS_NEEDED'end,'job',null,'projection',null,'apply_enabled',false,'production_go',false);
 else wip_read:=1;end if;
 snapshot:=cp7_reorder_reader.snapshot(source);
 answer:=cp7_reorder_caller.evaluate(snapshot,supply);
 select coalesce(jsonb_agg(x||jsonb_build_object('size_code',sz.size_code::text)),'[]'::jsonb)into prepared_rows
  from jsonb_array_elements(answer->'rows')x left join erp.sizes sz on sz.id=(x->>'size_id')::uuid;
 -- A successor may keep the physical root but change its size/target key.
 -- Remove obsolete keys before upserting: sibling data-modifying CTEs do
 -- not promise that order and can collide on the unique physical root.
 delete from cp7_reorder_caller.evaluations e where not exists(
  select 1 from jsonb_array_elements(prepared_rows)p where p->>'target_key'=e.target_key);
 insert into cp7_reorder_caller.evaluations as e(target_key,root_id,threshold_hash,row,captured_at)
  select p->>'target_key',(p->>'root_id')::uuid,snapshot->>'threshold_hash',p,checked from jsonb_array_elements(prepared_rows)p
  on conflict(target_key)do update set root_id=excluded.root_id,threshold_hash=excluded.threshold_hash,
   row=excluded.row,captured_at=excluded.captured_at
  where e.threshold_hash is distinct from excluded.threshold_hash
   or(e.row-'changed_at'-'projection')is distinct from(excluded.row-'changed_at'-'projection')
   or((e.row->'projection')-'stock_checked_at')is distinct from((excluded.row->'projection')-'stock_checked_at');
 select count(*),count(*)filter(where row->>'state'='AT_OR_BELOW')into n_items,n_low from cp7_reorder_caller.evaluations;
 -- Existing fabric/accessory engine and the shared run contract stay intact.
 mats:=cp7_stock_formula.compute_materials(checked);cfg:=cp7_stock_formula.current_settings();
 insert into cp7_stock_formula.runs as r(id,computed_at,window_from,window_through,settings_revision,service_level,window_days,
  items,at_or_below,wip_read,materials,materials_at_or_below,millis)
 values(true,checked,(source->'query'->>'from_date')::date,(source->'query'->>'through_date')::date,
  (cfg->>'revision')::bigint,(cfg->>'service_level')::numeric,(cfg->>'window_days')::integer,
  n_items,n_low,wip_read,(mats->>'materials')::integer,(mats->>'materials_at_or_below')::integer,
  greatest(0,(extract(epoch from clock_timestamp()-started)*1000)::integer))
 on conflict(id)do update set computed_at=excluded.computed_at,window_from=excluded.window_from,window_through=excluded.window_through,
  settings_revision=excluded.settings_revision,service_level=excluded.service_level,window_days=excluded.window_days,items=excluded.items,
  at_or_below=excluded.at_or_below,wip_read=excluded.wip_read,materials=excluded.materials,materials_at_or_below=excluded.materials_at_or_below,millis=excluded.millis;
 insert into cp7_reorder_caller.use_marks(id,used_at)values(true,checked)on conflict(id)do nothing;
 return jsonb_build_object('computed_at',checked,'items',n_items,'at_or_below',n_low,'wip_read',wip_read)||mats;
end $$;
