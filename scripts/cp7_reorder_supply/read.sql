-- Private operational cache reader. Caller supplies ONE fresh current Native
-- capture and its canonical demand query, then checks current access again.
-- It must not expose the raw private result through a warehouse facade.
create function cp7_reorder_supply.read_job(p_current jsonb,p_query jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare current_source jsonb;checked timestamptz;checked_text text;lo date;hi date;hash text;
 j cp7_analysis_stage.jobs%rowtype;scope jsonb;budget jsonb;r record;row_value jsonb;inputs jsonb;
 lead numeric;review numeric;targets jsonb[]:='{}';n integer;projection jsonb;reason text;progress jsonb;result jsonb;
begin
 if jsonb_typeof(p_current)is distinct from'object'then raise exception 'CP7_REORDER_CURRENT_SOURCE_SHAPE';end if;
 perform cp7_wip.fields(p_query,array['from_date','through_date','group_mode']);
 checked_text:=p_current->>'captured_at';
 if jsonb_typeof(p_current->'captured_at')is distinct from'string'then raise exception 'CP7_REORDER_CURRENT_CLOCK_REQUIRED';end if;
 if right(checked_text,6)='+00:00'then checked_text:=left(checked_text,length(checked_text)-6)||'Z';end if;
 checked:=cp7_demand.instant(to_jsonb(checked_text));
 lo:=cp7_demand.day(p_query->'from_date');hi:=cp7_demand.day(p_query->'through_date');
 if hi<lo or hi-lo>3660 or hi>=(checked at time zone'Asia/Jakarta')::date
  or p_query->>'group_mode'is null or p_query->>'group_mode'not in('AS_SOLD','RESTATED')then raise exception 'CP7_REORDER_CACHE_QUERY';end if;
 result:=jsonb_build_object('contract_version','cp7.reorder-supply-cache.v1','checked_at',cp7_planning.utc(checked),
  'query',p_query,'status','UNKNOWN','reason',null,'job',null,'projection',null,'apply_enabled',false,'production_go',false);
 if p_current->>'status'is distinct from'COMPLETE'then return result||jsonb_build_object('reason','CURRENT_SOURCE_INCOMPLETE');end if;
 if p_current->>'reorder_supply_engine'is distinct from'cp7.reorder-supply.v1'then return result||jsonb_build_object('reason','CURRENT_ENGINE_NOT_READY');end if;
 -- Operational facts only; no money/source/capture function is invoked here.
 current_source:=p_current||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');
 hash:=cp7_analysis_native.fingerprint(current_source);
 if hash is null or hash!~'^[0-9a-f]{64}$'then raise exception 'CP7_REORDER_CURRENT_HASH';end if;
 select *into j from cp7_analysis_stage.jobs x where x.state='DONE'and x.query=p_query and x.source_hash=hash
  and x.reference->>'reorder_supply_engine'='cp7.reorder-supply.v1'
  and x.captured_at<=checked and cp7_analysis_stage.retention(x.state,x.updated_at)->>'state'='KEPT'
  and cp7_analysis_native.finance_mode(x.reference)='DEFERRED'
  order by x.captured_at desc,x.id desc limit 1;
 if j.id is null then
  select jsonb_build_object('state',x.state,'units_done',x.units_done,'unit_count',x.unit_count)
   into progress from cp7_analysis_stage.jobs x where x.state='RUNNING'and x.query=p_query and x.source_hash=hash
    and x.reference->>'reorder_supply_engine'='cp7.reorder-supply.v1'and x.captured_at<=checked
   order by x.updated_at desc,x.id desc limit 1;
  reason:=case when progress is not null then'GLOBAL_ANALYSIS_IN_PROGRESS'
   when exists(select 1 from cp7_analysis_stage.jobs x where x.state='DONE'and x.query=p_query
    and x.reference->>'reorder_supply_engine'='cp7.reorder-supply.v1')then'GLOBAL_ANALYSIS_STALE_OR_EXPIRED'else'GLOBAL_ANALYSIS_NEEDED'end;
  return result||jsonb_build_object('reason',reason,'job',progress);
 end if;
 -- Same immutable retained index/capture/page-set boundary that plan v2 uses.
 -- Do not read every sealed page or recreate a second allocation for each SKU.
 if not exists(select 1 from cp7_analysis_stage.capture_marks x where x.job_id=j.id)
  or not exists(select 1 from cp7_analysis_stage.headers h join cp7_analysis_stage.page_sets s on s.run_id=h.run_id
   where h.job_id=j.id and h.run_id=j.run_id and h.targets_total=j.targets_total and(s.totals->>'targets')::integer=h.targets_total)then
  raise exception 'CP7_REORDER_CACHE_BOUNDARY_MISSING';end if;
 select x.scope into scope from cp7_analysis_stage.plan_scope x where x.job_id=j.id;
 budget:=scope->'reorder_supply_budget';
 if jsonb_typeof(scope)is distinct from'object'or jsonb_typeof(budget)is distinct from'object'
  or budget->>'contract_version'is distinct from'cp7.reorder-supply-budget.v1'then raise exception 'CP7_REORDER_CACHE_BUDGET_MISSING';end if;
 if budget->>'status'is distinct from'COMPLETE'or scope->>'wip_status'is distinct from'COMPLETE'then
  return result||jsonb_build_object('reason','GLOBAL_WIP_INCOMPLETE','job',jsonb_build_object('state','DONE','captured_at',cp7_planning.utc(j.captured_at)));end if;
 if scope->>'schedule_state'is distinct from'SELECTED_ASSUMPTIONS'or jsonb_typeof(scope->'schedule'->'plan_id')is distinct from'string'then
  return result||jsonb_build_object('reason','GLOBAL_SCHEDULE_UNREVIEWED','job',jsonb_build_object('state','DONE','captured_at',cp7_planning.utc(j.captured_at)));end if;
 if scope->>'alloc_status'is null or scope->>'alloc_status'not in('SCENARIO','UNKNOWN')then raise exception 'CP7_REORDER_CACHE_ALLOCATION_STATE';end if;
 select count(*)into n from cp7_analysis_stage.plan_targets x where x.job_id=j.id;
 if n is distinct from j.targets_total or n>5000 then raise exception 'CP7_REORDER_CACHE_TARGET_COUNT';end if;
 for r in select x.target_key,x.row from cp7_analysis_stage.plan_targets x where x.job_id=j.id order by x.ord loop
  row_value:=r.row;inputs:=row_value->'target'->'inputs';lead:=null;review:=null;
  if jsonb_typeof(row_value)is distinct from'object'or not row_value?&array['target_key','size_id','target','available_fg_pcs','supplies']
   or jsonb_typeof(row_value->'target')is distinct from'object'or not(row_value->'target')?&array['inputs','target_pcs','reorder_point_pcs']
   or jsonb_typeof(inputs)is distinct from'object'or not inputs?&array['contract_version','lead_days','review_days','refs']
   or row_value->>'target_key'is distinct from r.target_key or inputs->>'contract_version'is distinct from'cp7.target-input.v2'then
   raise exception 'CP7_REORDER_CACHE_TARGET_BINDING';end if;
  if inputs->'lead_days'<>'null'::jsonb then lead:=cp7_demand.decimal(inputs->'lead_days');end if;
  if inputs->'review_days'<>'null'::jsonb then review:=cp7_demand.decimal(inputs->'review_days');end if;
  targets:=array_append(targets,jsonb_build_object('target_key',row_value->'target_key','size_id',row_value->'size_id',
   'reorder_point_pcs',row_value->'target'->'reorder_point_pcs','target_pcs',row_value->'target'->'target_pcs',
   'available_fg_pcs',row_value->'available_fg_pcs','lead_deadline',case when lead is not null then cp7_planning.utc(j.captured_at+lead*interval'1 day')end,
   'deadline',case when lead is not null and review is not null then cp7_planning.utc(j.captured_at+(lead+review)*interval'1 day')end,
   'supplies',row_value->'supplies','refs',inputs->'refs'));
 end loop;
 projection:=cp7_reorder_supply.project(jsonb_build_object('contract_version','cp7.reorder-supply-input.v1',
  'snapshot_id',budget->'snapshot_id','scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',scope->'schedule'->'plan_id',
  'captured_at',cp7_planning.utc(j.captured_at),'checked_at',cp7_planning.utc(checked),'source_hash',j.source_hash,
  'current_source_hash',hash,'source_state','CURRENT','complete_scope',true,'wip_status',scope->'wip_status',
  'allocation_status',scope->'alloc_status','query',j.query,'expected_query',p_query,'budgets',budget->'rows','targets',to_jsonb(targets),
  'refs',jsonb_build_array(jsonb_build_object('kind','STAGED_GLOBAL_ALLOCATION','id',j.run_id::text,'revision',j.source_hash))));
 return result||jsonb_build_object('status',projection->'status','reason',projection->'reason','projection',projection,
  'job',jsonb_build_object('state','DONE','run_id',j.run_id,'captured_at',cp7_planning.utc(j.captured_at),'targets_total',j.targets_total));
end $$;
alter function cp7_reorder_supply.read_job(jsonb,jsonb)owner to cp7_capture;
revoke all on function cp7_reorder_supply.read_job(jsonb,jsonb)from public,anon,authenticated,service_role;
