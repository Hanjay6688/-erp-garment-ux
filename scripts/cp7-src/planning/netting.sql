-- One native physical-source universe, one selected remaining-work scenario and
-- one server allocation. Consumer filters and match labels never enter this API.
create schema cp7_netting_native authorization cp7_capture;
revoke all on schema cp7_netting_native from public,anon,authenticated,service_role;

create function cp7_netting_native.source()returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with source as materialized(select cp7_schedule_native.source()c),
 wanted as materialized(
  select x->>'id'id from source,jsonb_array_elements(c->'facts'->'products')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'other'->'origins')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'other'->'bs')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'cutting'->'bs')x
 ),products as materialized(
  select p.id,coalesce(p.identity_root_id,p.id)root_id,p.model_id,p.size_id,p.brand_id,p.color_name,
   p.effective_from,p.effective_to,p.created_at
  from erp.products p join wanted w on w.id=p.id::text cross join source
  where p.created_at<=(c->>'captured_at')::timestamptz order by p.id limit 5001
 )select c||jsonb_build_object('matching_products',coalesce((select jsonb_agg(to_jsonb(p)order by p.id)from products p),'[]'))from source
$$;

create function cp7_netting_native.fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('work_source',cp7_schedule_native.fingerprint(c),
  'matching_products',c->'matching_products')::text,'UTF8'),'sha256'),'hex')
$$;

create function cp7_netting_native.bound_product(c jsonb,p jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare id text;rw jsonb;bs jsonb;facts jsonb:=c->'production_sources'->'facts';
begin
 if split_part(p->>'pool_key',':',1)='OPEN'then
  select x->>'product_id'into id from jsonb_array_elements(facts->'other'->'origins')x
   where x->>'id'=split_part(p->>'pool_key',':',2);
 elsif split_part(p->>'pool_key',':',1)='NONPO'then
  select x->>'product_id'into id from jsonb_array_elements(facts->'other'->'bs')x
   where x->>'id'=split_part(p->>'pool_key',':',2);
 elsif p->>'stage'='REWORK'then
  select x into rw from jsonb_array_elements((facts->'cutting'->'reworks')||(facts->'other'->'reworks'))x
   where x->>'id'=split_part(p->>'key',':',2);
  select x->>'product_id'into id from jsonb_array_elements((facts->'cutting'->'bs')||(facts->'other'->'bs'))x
   where x->>'id'=rw->>'bs_case_id';
 end if;
 return(select x from jsonb_array_elements(c->'matching_products')x where x->>'id'=id);
end $$;

create function cp7_netting_native.matching(c jsonb,wip jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare p jsonb;product jsonb;g jsonb;constraints jsonb;refs jsonb;sources jsonb:='[]';targets jsonb:='[]';model text;confirmed text;quality text;
begin
 if jsonb_array_length(c->'matching_products')>5000 then raise exception 'CP7_NETTING_MATCH_SOURCE_LIMIT';end if;
 for product in select value from jsonb_array_elements(c->'facts'->'products')order by value->>'root_id'loop
  select x into g from jsonb_array_elements(c->'matching_products')x where x->>'id'=product->>'id';
  if g is null then raise exception 'CP7_NETTING_NATIVE_PRODUCT_MISSING';end if;
  refs:=jsonb_build_array(cp7_wip.ref('erp.products',g->>'id',g->>'effective_from'));
  constraints:=jsonb_build_array(
   jsonb_build_object('field','brand','value',g->'brand_id','required',true,'basis','FACT'),
   jsonb_build_object('field','color','value',g->'color_name','required',true,'basis','FACT'));
  targets:=targets||jsonb_build_array(jsonb_build_object('key',(g->>'root_id')||':'||(g->>'size_id'),
   'size_id',g->'size_id','constraints',constraints,'refs',refs));
 end loop;
 for p in select value from jsonb_array_elements(wip->'positions')order by value->>'key'loop
  product:=cp7_netting_native.bound_product(c,p);model:=cp7_schedule_native.position_model(c,p);quality:=null;
  constraints:='[]';refs:=p->'refs';confirmed:=null;
  if product is not null then
   if product->>'size_id'<>p->>'size_id'then raise exception 'CP7_NETTING_NATIVE_SOURCE_SIZE';end if;
   model:=product->>'model_id';confirmed:=(product->>'root_id')||':'||(product->>'size_id');
   if exists(select 1 from jsonb_array_elements(c->'facts'->'products')x
    where x->>'root_id'=product->>'root_id'and x->>'model_id'<>model)then quality:='CONFLICT';end if;
   constraints:=jsonb_build_array(
    jsonb_build_object('field','brand','value',product->'brand_id','required',true,'basis','FACT'),
    jsonb_build_object('field','color','value',product->'color_name','required',true,'basis','FACT'));
   refs:=refs||jsonb_build_array(cp7_wip.ref('erp.products',product->>'id',product->>'effective_from'));
  elsif split_part(p->>'pool_key',':',1)='CUT'then
   select x into g from jsonb_array_elements(c->'production_sources'->'facts'->'cutting'->'groups')x
    where x->>'id'=split_part(p->>'pool_key',':',2);
   if g->>'pattern_id'is not null and g->>'pattern_revision_snapshot'is not null then
    constraints:=constraints||jsonb_build_array(jsonb_build_object('field','pattern_revision',
     'value',(g->>'pattern_id')||':'||(g->>'pattern_revision_snapshot'),'required',false,'basis','FACT'));
   end if;
  end if;
  -- Brand/color are critical target attributes. An unbound cut cannot acquire
  -- them from a tariff SKU, a similar name or the user's target selection.
  sources:=sources||jsonb_build_array(jsonb_build_object('key',p->'key','size_id',p->'size_id',
   'quality',coalesce(quality,case when model is null then 'UNKNOWN'else 'COMPLETE'end),
   'confirmed_target',confirmed,'constraints',constraints,'refs',refs));
 end loop;
 return jsonb_build_object('snapshot_id',wip->'snapshot_id','sources',sources,'targets',targets);
end $$;

create function cp7_netting_native.matches(c jsonb,p jsonb,t jsonb,matching jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare s jsonb;target jsonb;model text;product jsonb;
begin
 s:=(select x from jsonb_array_elements(matching->'sources')x where x->>'key'=p->>'key');
 target:=(select x from jsonb_array_elements(matching->'targets')x where x->>'key'=t->>'target_key');
 product:=cp7_netting_native.bound_product(c,p);
 model:=coalesce(product->>'model_id',cp7_schedule_native.position_model(c,p));
 if model is null then return jsonb_build_object('match','UNKNOWN','reasons',jsonb_build_array('NATIVE_SOURCE_MODEL_UNPROVEN'));end if;
 if not exists(select 1 from jsonb_array_elements(c->'facts'->'products')x
  where(x->>'root_id')||':'||(x->>'size_id')=t->>'target_key'and x->>'model_id'=model)then
  return jsonb_build_object('match','INCOMPATIBLE','reasons',jsonb_build_array('NATIVE_MODEL_MISMATCH'));end if;
 return cp7_wip.match_target(s,target);
end $$;

create function cp7_netting_native.timeline(c jsonb,r jsonb,etas jsonb,edges jsonb,matching jsonb,wip jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare cfg jsonb:=r->'profile'->'config';rate numeric;horizon numeric;remaining numeric;duration numeric;qty numeric;
 ready timestamptz:=(c->>'captured_at')::timestamptz;deadline timestamptz;at_time timestamptz;
 events jsonb:='[]';e jsonb;eta jsonb;i integer:=0;seq integer:=0;
begin
 if r->'target'->>'status'is distinct from 'SCENARIO'or r->'demand_estimate'->>'daily_pcs'is null then
  return jsonb_build_object('status','UNKNOWN','reason','SELECTED_TARGET_OR_DEMAND_UNKNOWN');end if;
 if r->>'available_fg_pcs'like '-%'then return jsonb_build_object('status','UNKNOWN',
  'reason','NATIVE_RESERVATIONS_EXCEED_ON_HAND_SIGNED_GAP_PRESERVED');end if;
 rate:=cp7_demand.decimal(r->'demand_estimate'->'daily_pcs');
 horizon:=cp7_demand.decimal(cfg->'lead_days')+cp7_demand.decimal(cfg->'review_days');
 deadline:=ready+(horizon::text||' days')::interval;remaining:=horizon;
 while remaining>0 loop
  duration:=least(1,remaining);i:=i+1;
  if i>3660 then raise exception 'CP7_NETTING_TIMELINE_HORIZON_LIMIT';end if;
  at_time:=least(deadline,ready+(i::text||' days')::interval);qty:=ceil(rate*duration*1000000000000)/1000000000000;
  events:=events||jsonb_build_array(jsonb_build_object('key','forecast-day-'||i,'at',cp7_planning.utc(at_time),
   'sequence',(10000+i)::text,'kind','DEMAND','qty_pcs',qty::numeric(42,12)::text,'refs',r->'refs'));
  remaining:=remaining-duration;
 end loop;
 for e in select value from jsonb_array_elements(edges)where value->>'target_key'=r->>'target_key'order by value->>'key'loop
  eta:=(select x from jsonb_array_elements(etas)x where x->>'position_key'=e->>'position_key');
  if eta->'at'='null'::jsonb then continue;end if;
  at_time:=cp7_demand.instant(eta->'at');
  if at_time>deadline then continue;end if;
  seq:=seq+1;events:=events||jsonb_build_array(jsonb_build_object('key','supply-'||(e->>'key'),
   'at',cp7_planning.utc(at_time),'sequence',seq::text,'kind','SUPPLY','qty_pcs',e->'projected_good_pcs','refs',e->'refs'));
 end loop;
 return cp7_baseline.timeline(jsonb_build_object('contract_version','cp7.timeline-input.v1',
  'snapshot_id',wip->'snapshot_id','scope_id','GLOBAL_NATIVE_PLANNING','target_key',r->'target_key',
  'size_id',r->'size_id','mode','BACKLOG','initial_fg_pcs',r->'available_fg_pcs',
  'from_at',cp7_planning.utc(ready),'through_at',cp7_planning.utc(deadline),'events',events,'refs',r->'refs'))
  ||jsonb_build_object('timing_basis','SELECTED_DAILY_RESIDUAL_AT_EACH_24H_END_FROM_CAPTURE',
   'unmet_mode_basis','EXPLICIT_TECHNICAL_BACKLOG_SCENARIO','buffer_consumed_as_demand',false);
end $$;

create function cp7_netting_native.build(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare scenario jsonb;wip jsonb;matching jsonb;p jsonb;t jsonb;m jsonb;s jsonb;tf jsonb;eta jsonb;
 r jsonb;cfg jsonb;line jsonb;alloc jsonb;allocrow jsonb;edges jsonb:='[]';etas jsonb:='[]';targets jsonb:='[]';
 matches jsonb:='[]';rows jsonb:='[]';reviews jsonb:='[]';hash text;policy text;ready timestamptz;
 deadline timestamptz;helps timestamptz;raw_need numeric;directed numeric;candidate numeric;gap numeric;
 budget numeric:=0;all_targets_known boolean:=true;supplies_complete boolean:=true;refs jsonb;production_status text;needs jsonb:='{}';
 supplies jsonb;net jsonb;net_input jsonb;raw_net jsonb;directed_edges jsonb;match_index jsonb;match_index_unique boolean;
begin
 scenario:=cp7_schedule_native.build(c,q);wip:=scenario->'wip';hash:=cp7_netting_native.fingerprint(c);
 ready:=(c->>'captured_at')::timestamptz;
 if wip->>'status'is distinct from 'COMPLETE'then
  return jsonb_build_object('contract_version','cp7.native-netting.v1','captured_at',c->>'captured_at',
   'source_hash',hash,'status','UNKNOWN','schedule_run_result',scenario,'rows','[]'::jsonb,
   'allocation',jsonb_build_object('status','UNKNOWN','reason','NATIVE_QUANTITY_CAPTURE_INCOMPLETE'),
   'apply_enabled',false,'production_go',false);
 end if;
 if jsonb_array_length(wip->'positions')*jsonb_array_length(scenario->'supply_run_result'->'baseline_run_result'->'rows')>100000
  or jsonb_array_length(wip->'positions')>1000 then raise exception 'CP7_NETTING_WORK_LIMIT';end if;
 matching:=cp7_netting_native.matching(c,wip);
 for eta in select value from jsonb_array_elements(scenario->'etas')loop
  etas:=etas||jsonb_build_array(jsonb_build_object('position_key',eta->'position_key',
   'at',case when eta->'result'->>'status'in('KNOWN','CONDITIONAL')then cp7_planning.utc((eta->'result'->>'eta')::timestamptz)else null end,
   'refs',eta->'refs'));
 end loop;
 -- Existing work is timed in one shared queue. Its projected supply budget is
 -- separate from AFTER-existing-work free capacity for new starts.
 for p in select value from jsonb_array_elements(wip->'positions')where value->'eligible_company_wip'='true'::jsonb loop
  eta:=(select x from jsonb_array_elements(etas)x where x->>'position_key'=p->>'key');
  if p->'projection'->>'quality'='SCENARIO'and eta->>'at'is not null then
   budget:=budget+cp7_wip.pcs(p->'projection'->'projected_good_pcs');
  elsif cp7_wip.pcs(p->'remaining_pcs')>0 then supplies_complete:=false;end if;
 end loop;
 for r in select value from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')order by value->>'target_key'loop
  cfg:=r->'profile'->'config';policy:=r->'production_policy'->'policy'->>'state';
  if r->'target'->>'status'is distinct from 'SCENARIO'or r->>'available_fg_pcs'is null then
   all_targets_known:=false;reviews:=reviews||jsonb_build_array(jsonb_build_object('target_key',r->'target_key','reason','DEMAND_TARGET_STOCK_OR_PRODUCTION_POLICY_UNREVIEWED'));continue;end if;
  if policy is null then all_targets_known:=false;reviews:=reviews||jsonb_build_array(jsonb_build_object('target_key',r->'target_key','reason','PRODUCTION_POLICY_UNREVIEWED'));end if;
  production_status:=case when policy='ACTIVE'then 'ACTIVE'when policy in('PAUSED','STOPPED')then 'STOP'else 'UNKNOWN'end;
  raw_net:=cp7_baseline.net(jsonb_build_object('contract_version','cp7.net-input.v1','snapshot_id',wip->'snapshot_id',
   'scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',coalesce(c->'schedule'->'plan_id',to_jsonb('unreviewed-'||hash)),
   'target_key',r->'target_key','size_id',r->'size_id','deadline',cp7_planning.utc(ready),
   'target_pcs',r->'target'->'target_pcs','available_fg_pcs',r->'available_fg_pcs','supplies','[]'::jsonb,'refs',r->'refs'));
  raw_need:=cp7_wip.pcs(raw_net->'q_base_pcs');
  deadline:=ready+((cp7_demand.decimal(cfg->'lead_days')+cp7_demand.decimal(cfg->'review_days'))::text||' days')::interval;
  helps:=ready+(cp7_demand.decimal(cfg->'lead_days')::text||' days')::interval;
  line:=cp7_netting_native.timeline(c,r,etas,'[]'::jsonb,matching,wip);
  tf:=(select x from jsonb_array_elements(matching->'targets')x where x->>'key'=r->>'target_key');
  select jsonb_agg(x order by x::text)into refs from(select distinct value x from jsonb_array_elements((r->'refs')||(tf->'refs')))u;
  targets:=targets||jsonb_build_array(jsonb_build_object('key',r->'target_key','size_id',r->'size_id',
   'need_pcs',raw_need::text,'deadline',cp7_planning.utc(deadline),
   'risk_at',coalesce(line->'first_known_gap'->'at',to_jsonb(cp7_planning.utc(deadline))),
   'helps_at',cp7_planning.utc(helps),'production_status',production_status,'refs',refs));
  needs:=needs||jsonb_build_object(r->>'target_key',raw_need::text);
 end loop;
 -- Model is an additional Native hard constraint absent from the retained
 -- five-field pure matcher. A source with a Native product binding can only
 -- match that root; unbound critical brand/color remains NEEDS_CHECK.
 -- Evaluate each immutable pair once and aggregate in the original array
 -- order. The local index never enters the returned matching/result contract.
 with pair_results as materialized(
  select pp.position->'key' position_key,rr.target->'target_key' target_key,
   pp.p_ordinal,rr.t_ordinal,
   jsonb_build_array(pp.position->>'key',rr.target->>'target_key')::text pair_key,
   cp7_netting_native.matches(c,pp.position,rr.target,matching) pair_result
  from jsonb_array_elements(wip->'positions')with ordinality pp(position,p_ordinal)
  cross join jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')with ordinality rr(target,t_ordinal)
  where pp.position->'eligible_company_wip'='true'::jsonb)
 select coalesce(jsonb_agg(jsonb_build_object('position_key',pr.position_key,'target_key',pr.target_key,
   'result',pr.pair_result)order by pr.p_ordinal,pr.t_ordinal),'[]'::jsonb),
  coalesce(jsonb_object_agg(pr.pair_key,pr.pair_result),'{}'::jsonb),
  count(*)=count(distinct pr.pair_key)
 into matches,match_index,match_index_unique from pair_results pr;
 if not all_targets_known then alloc:=jsonb_build_object('status','UNKNOWN','reason','GLOBAL_TARGET_NEEDS_OR_POLICY_NOT_FULLY_REVIEWED');
 elsif scenario->>'schedule_state'<>'SELECTED_ASSUMPTIONS'then alloc:=jsonb_build_object('status','UNKNOWN','reason','SOURCE_BOUND_WORK_YIELD_NOT_REVIEWED');
 elsif not supplies_complete then alloc:=jsonb_build_object('status','UNKNOWN','reason','EXISTING_SUPPLY_YIELD_OR_SHARED_ETA_UNKNOWN');
 else
  -- Exact Native model mismatch must remain a hard conflict inside the kernel,
  -- too. Bound product sources already have exact destination; every unbound
  -- source requires missing brand/color proof and cannot generate an edge.
  alloc:=cp7_baseline.allocate(jsonb_build_object('contract_version','cp7.allocation-input.v1',
   'snapshot_id',wip->'snapshot_id','scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',c->'schedule'->'plan_id',
   'complete_scope',true,'positions',wip,'matching',matching,'etas',etas,'targets',targets,
   'capacity_pcs',budget::text,'refs',jsonb_build_array(cp7_wip.ref('PLANNING_SCHEDULE',c->'schedule'->>'plan_id',c->'schedule'->>'revision'))));
  edges:=coalesce(alloc->'allocation'->'edges','[]'::jsonb);
 end if;
 for r in select value from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')order by value->>'target_key'loop
  directed:=0;candidate:=0;raw_need:=null;gap:=null;supplies:='[]';directed_edges:='[]';net:=null;
  t:=(select x from jsonb_array_elements(targets)x where x->>'key'=r->>'target_key');
  if t is not null then
   raw_need:=cp7_wip.pcs(t->'need_pcs');
   -- A fully emptied position stays in the graph as evidence; it is no supply
   -- (the budget loop above skips it too) and must not make the target UNKNOWN.
   for p in select value from jsonb_array_elements(wip->'positions')where value->'eligible_company_wip'='true'::jsonb
    and cp7_wip.pcs(value->'remaining_pcs')>0 loop
    m:=case when match_index_unique then
     match_index->(jsonb_build_array(p->>'key',r->>'target_key')::text)
     else cp7_netting_native.matches(c,p,r,matching)end;eta:=(select x from jsonb_array_elements(etas)x where x->>'position_key'=p->>'key');
    if m->>'match'='CONFIRMED_TARGET'then
     supplies:=supplies||jsonb_build_array(jsonb_build_object('physical_key',p->'key','snapshot_id',wip->'snapshot_id',
      'target_key',r->'target_key','size_id',r->'size_id','kind','DIRECTED',
      'qty_pcs',case when p->'projection'->>'quality'='SCENARIO'then p->'projection'->'projected_good_pcs'else null end,
      'eta',coalesce(eta->'at','null'::jsonb),'eligible',true,'refs',p->'refs'));
     if p->'projection'->>'quality'='SCENARIO'and eta->>'at'is not null then
      directed_edges:=directed_edges||jsonb_build_array(jsonb_build_object('key',p->'key','position_key',p->'key',
       'target_key',r->'target_key','projected_good_pcs',p->'projection'->'projected_good_pcs','refs',p->'refs'));
     end if;
    end if;
   end loop;
   for p in select value from jsonb_array_elements(edges)where value->>'target_key'=r->>'target_key'and value->>'match'='CANDIDATE_MATCH'loop
    eta:=(select x from jsonb_array_elements(etas)x where x->>'position_key'=p->>'position_key');
    supplies:=supplies||jsonb_build_array(jsonb_build_object('physical_key',p->'position_key','snapshot_id',wip->'snapshot_id',
     'target_key',r->'target_key','size_id',r->'size_id','kind','ALLOCATED_CANDIDATE','qty_pcs',p->'projected_good_pcs',
     'eta',eta->'at','eligible',true,'refs',p->'refs'));
   end loop;
   net:=cp7_baseline.net(jsonb_build_object('contract_version','cp7.net-input.v1','snapshot_id',wip->'snapshot_id',
    'scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',coalesce(c->'schedule'->'plan_id',to_jsonb('unreviewed-'||hash)),
    'target_key',r->'target_key','size_id',r->'size_id','deadline',t->'deadline',
    'target_pcs',r->'target'->'target_pcs','available_fg_pcs',r->'available_fg_pcs','supplies',supplies,'refs',r->'refs'));
   gap:=(net->>'q_base_pcs')::numeric;directed:=coalesce((net->>'directed_on_time_pcs')::numeric,0);
   candidate:=coalesce((net->>'candidate_on_time_pcs')::numeric,0);
  end if;
  line:=case when t is null then jsonb_build_object('status','UNKNOWN','reason','TARGET_NEEDS_OR_POLICY_UNREVIEWED')
   else cp7_netting_native.timeline(c,r,etas,directed_edges||(select coalesce(jsonb_agg(value),'[]')from jsonb_array_elements(edges)where value->>'match'='CANDIDATE_MATCH'),matching,wip)end;
  rows:=rows||jsonb_build_array(r||jsonb_build_object('raw_gap_pcs',raw_need::text,'directed_on_time_good_pcs',net->'directed_on_time_pcs',
   'base_gap_pcs',net->'q_base_pcs','conditional_gap_pcs',case when alloc->>'status'='SCENARIO'then net->'q_conditional_pcs'else null end,
   'net',net,
   'candidate_allocated_good_pcs',case when alloc->>'status'='SCENARIO'then candidate::text else null end,
   'timeline',line,'start_new_pcs',case when t->>'production_status'='STOP'then '0'else null end,
   'material_state','UNKNOWN','new_start_capacity',scenario->'capacity','apply_enabled',false,
   'netting_basis','NATIVE_AVAILABLE_FG_ONCE_SOURCE_BOUND_YIELD_AND_ONE_SHARED_REMAINING_CALENDAR',
   'reason','SCENARIO_EXISTING_SUPPLY_DISTINCT_FROM_NEW_START_MATERIAL_FEASIBILITY'));
 end loop;
 return jsonb_build_object('contract_version','cp7.native-netting.v1','captured_at',c->>'captured_at',
  'source_hash',hash,'status',case when all_targets_known and alloc->>'status'='SCENARIO'then 'SCENARIO'else 'PARTIAL'end,
  'schedule_run_result',scenario,'matching',matching,'match_results',matches,'rows',rows,'allocation',alloc,
  'review_queue',reviews,'existing_timed_projected_good_budget_pcs',budget::text,
  'new_start_capacity',scenario->'capacity','material_state','UNKNOWN','apply_enabled',false,'production_go',false);
end $$;

create table cp7_netting_native.runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 query jsonb not null,captured_at timestamptz not null,access_at_capture jsonb not null,
 facts jsonb not null,result jsonb not null,dependency_hash text not null,unique(actor,request_id)
);
alter table cp7_netting_native.runs owner to cp7_capture;
alter table cp7_netting_native.runs enable row level security;
create policy cp7_netting_no_access on cp7_netting_native.runs for all to public using(false)with check(false);
revoke all on cp7_netting_native.runs from public,anon,authenticated,service_role;
create trigger immutable_netting_run before update or delete on cp7_netting_native.runs
 for each row execute function cp7_private.immutable_run();

create function cp7_netting_native.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_netting_native.runs%rowtype;c jsonb;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);select *into r from cp7_netting_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_NETTING_RUN_UNAVAILABLE';end if;
 c:=cp7_netting_native.source();outcome:=r.result||jsonb_build_object('run_id',r.id,'request_id',r.request_id,
  'source_state',case when cp7_netting_native.fingerprint(c)=r.dependency_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_NETTING_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function cp7_netting_native.capture(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;r cp7_netting_native.runs%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);q:=cp7_planning.history_query(p_query);
 if p_request is null then raise exception 'CP7_NETTING_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:NETTING:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_NETTING_ACCESS_CHANGED';end if;
 select *into r from cp7_netting_native.runs where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if r.query<>q then raise exception 'CP7_NETTING_REQUEST_CHANGED';end if;return cp7_netting_native.serve(r.id);
 end if;
 with source as materialized(select cp7_netting_native.source()c),
 calculated as materialized(select c,cp7_netting_native.build(c,q)result from source)
 insert into cp7_netting_native.runs(actor,request_id,query,captured_at,access_at_capture,facts,result,dependency_hash)
 select(a->>'actor')::uuid,p_request,q,(c->>'captured_at')::timestamptz,a,c,result,result->>'source_hash'
 from calculated returning *into r;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_NETTING_ACCESS_CHANGED';end if;
 return cp7_netting_native.serve(r.id);
end $$;

alter function cp7_netting_native.source()owner to cp7_capture;
alter function cp7_netting_native.fingerprint(jsonb)owner to cp7_capture;
alter function cp7_netting_native.bound_product(jsonb,jsonb)owner to cp7_capture;
alter function cp7_netting_native.matching(jsonb,jsonb)owner to cp7_capture;
alter function cp7_netting_native.matches(jsonb,jsonb,jsonb,jsonb)owner to cp7_capture;
alter function cp7_netting_native.timeline(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)owner to cp7_capture;
alter function cp7_netting_native.build(jsonb,jsonb)owner to cp7_capture;
alter function cp7_netting_native.serve(uuid)owner to cp7_capture;
alter function cp7_netting_native.capture(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_netting_native from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
create function public.erp_cp7_capture_netting_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_netting_native.capture(p_query,p_request)$$;
create function public.erp_cp7_read_netting_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_netting_native.serve(p_run)$$;
alter function public.erp_cp7_capture_netting_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_netting_v1(uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_capture_netting_v1(jsonb,uuid),public.erp_cp7_read_netting_v1(uuid)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_netting_v1(jsonb,uuid),public.erp_cp7_read_netting_v1(uuid)to authenticated;
