-- Deterministic simulation over ONE complete scope. Not a reservation/optimizer.
-- Source ETA comes from the pinned P04 dated-work kernel; unknown ETA is reviewed.
create function cp7_baseline.allocate(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare t jsonb;p jsonb;s jsonb;tf jsonb;m jsonb;e jsonb;proj jsonb;pool jsonb;eta jsonb;k text;pk text;
 targets_seen jsonb:='{}';positions_seen jsonb:='{}';pools jsonb:='{}';etas jsonb:='{}';used jsonb:='{}';good_used jsonb:='{}';pool_used jsonb:='{}';
 edges jsonb:='[]';results jsonb:='[]';review jsonb:='[]';validation jsonb;capacity numeric;need numeric;left_need numeric;room numeric;good numeric;input_qty numeric;num numeric;den numeric;refs jsonb;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','scenario_id','complete_scope','positions','matching','etas','targets','capacity_pcs','refs']);
 perform cp7_demand.context(v,'cp7.allocation-input.v1');perform cp7_wip.key(v->'scenario_id');perform cp7_wip.refs(v->'refs');
 if jsonb_typeof(v->'complete_scope') is distinct from 'boolean' then raise exception 'CP7_BASELINE_SCOPE';end if;
 if v->'complete_scope'='false'::jsonb then return jsonb_build_object('status','UNKNOWN','reason','COMPLETE_ALLOCATION_SCOPE_REQUIRED');end if;
 if v->'capacity_pcs'='null'::jsonb then return jsonb_build_object('status','UNKNOWN','reason','SHARED_CAPACITY_UNKNOWN');end if;
 capacity:=cp7_wip.pcs(v->'capacity_pcs');
 if v->'positions'->>'snapshot_id' is distinct from v->>'snapshot_id' or v->'matching'->>'snapshot_id' is distinct from v->>'snapshot_id' then raise exception 'CP7_BASELINE_MATCH_SNAPSHOT';end if;
 validation:=cp7_wip.check_allocations(v->'positions',jsonb_build_object('scenario_id',v->'scenario_id','scope_id',v->'scope_id','complete_scope',true,'matching',v->'matching','edges','[]'::jsonb));
 if validation->>'status'<>'FEASIBLE' then return validation;end if;
 perform cp7_demand.items(v->'positions'->'positions',1000);perform cp7_demand.items(v->'positions'->'totals',1000);
 perform cp7_demand.items(v->'targets',1000);perform cp7_demand.items(v->'etas',1000);
 if jsonb_array_length(v->'positions'->'positions')*jsonb_array_length(v->'targets')>100000 then raise exception 'CP7_BASELINE_ALLOCATION_LIMIT';end if;
 for pool in select value from jsonb_array_elements(v->'positions'->'totals') loop
  k:=cp7_wip.key(pool->'pool_key');perform cp7_wip.pcs(pool->'wip_pcs');
  if pools ? k then raise exception 'CP7_BASELINE_DUPLICATE_POOL';end if;pools:=pools||jsonb_build_object(k,pool);
 end loop;
 for p in select value from jsonb_array_elements(v->'positions'->'positions') loop
  k:=cp7_wip.key(p->'key');pk:=cp7_wip.key(p->'pool_key');perform cp7_wip.key(p->'size_id');perform cp7_wip.pcs(p->'remaining_pcs');perform cp7_wip.refs(p->'refs');
  if positions_seen ? k or not pools ? pk or jsonb_typeof(p->'eligible_company_wip') is distinct from 'boolean' then raise exception 'CP7_BASELINE_POSITION';end if;
  positions_seen:=positions_seen||jsonb_build_object(k,true);
  if p->'projection'->>'quality'='SCENARIO' then
   proj:=p->'projection';num:=cp7_wip.pcs(proj->'numerator');den:=cp7_wip.pcs(proj->'denominator');
   perform cp7_wip.pcs(proj->'eligible_input_pcs');perform cp7_wip.pcs(proj->'projected_good_pcs');
   if den=0 or num>den then raise exception 'CP7_BASELINE_YIELD';end if;
  end if;
 end loop;
 for eta in select value from jsonb_array_elements(v->'etas') loop
  perform cp7_wip.fields(eta,array['position_key','at','refs']);k:=cp7_wip.key(eta->'position_key');perform cp7_wip.refs(eta->'refs');
  if etas ? k or not positions_seen ? k then raise exception 'CP7_BASELINE_ETA_BINDING';end if;
  if eta->'at'<>'null'::jsonb then perform cp7_demand.instant(eta->'at');end if;etas:=etas||jsonb_build_object(k,eta);
 end loop;
 for t in select value from jsonb_array_elements(v->'targets') loop
  perform cp7_wip.fields(t,array['key','size_id','need_pcs','deadline','risk_at','helps_at','production_status','refs']);k:=cp7_wip.key(t->'key');perform cp7_wip.key(t->'size_id');perform cp7_wip.refs(t->'refs');
  perform cp7_wip.pcs(t->'need_pcs');
  if targets_seen ? k or t->>'production_status' is null or t->>'production_status' not in ('ACTIVE','STOP') then raise exception 'CP7_BASELINE_TARGET';end if;
  targets_seen:=targets_seen||jsonb_build_object(k,true);
  foreach e in array array[t->'deadline',t->'risk_at',t->'helps_at'] loop if e<>'null'::jsonb then perform cp7_demand.instant(e);end if;end loop;
  select value into tf from jsonb_array_elements(v->'matching'->'targets') where value->>'key'=k;
  if tf is null or tf->>'size_id'<>t->>'size_id' or not ((t->'refs') @> (tf->'refs')) then raise exception 'CP7_BASELINE_TARGET_MATCH_BINDING';end if;
 end loop;
 for t in select value from jsonb_array_elements(v->'targets') order by
  case when value->'risk_at'<>'null'::jsonb then cp7_demand.instant(value->'risk_at') end nulls last,
  case when value->'deadline'<>'null'::jsonb then cp7_demand.instant(value->'deadline') end nulls last,
  case when value->'helps_at'<>'null'::jsonb then cp7_demand.instant(value->'helps_at') end nulls last,
  cp7_wip.pcs(value->'need_pcs') desc,value->>'key' loop
  need:=cp7_wip.pcs(t->'need_pcs');left_need:=need;
  if t->'deadline'='null'::jsonb or t->'risk_at'='null'::jsonb or t->'helps_at'='null'::jsonb then
   review:=review||jsonb_build_array(jsonb_build_object('target_key',t->'key','reason','TIME_UNKNOWN','need_pcs',need::text));continue;end if;
  if t->>'production_status'='ACTIVE' then
   select value into tf from jsonb_array_elements(v->'matching'->'targets') where value->>'key'=t->>'key';
   for p in select value from jsonb_array_elements(v->'positions'->'positions') order by
    case when etas->(value->>'key')->'at'<>'null'::jsonb then cp7_demand.instant(etas->(value->>'key')->'at') end nulls last,value->>'key' loop
    exit when left_need=0 or capacity=0;
    k:=p->>'key';pk:=p->>'pool_key';proj:=p->'projection';eta:=etas->k;
    if p->'eligible_company_wip'='false'::jsonb or p->>'size_id'<>t->>'size_id' then continue;end if;
    if eta is null or eta->'at'='null'::jsonb or proj->>'quality' is distinct from 'SCENARIO' then
     review:=review||jsonb_build_array(jsonb_build_object('position_key',k,'target_key',t->'key','reason','ETA_OR_YIELD_UNKNOWN'));continue;end if;
    if cp7_demand.instant(eta->'at')>cp7_demand.instant(t->'deadline') then continue;end if;
    select value into s from jsonb_array_elements(v->'matching'->'sources') where value->>'key'=k;
    if s is null then raise exception 'CP7_BASELINE_SOURCE_MATCH_BINDING';end if;
    m:=cp7_wip.match_target(s,tf);
    if m->>'match' not in ('CANDIDATE_MATCH','CONFIRMED_TARGET') then
     review:=review||jsonb_build_array(jsonb_build_object('position_key',k,'target_key',t->'key','reason',m));continue;end if;
    num:=cp7_wip.pcs(proj->'numerator');den:=cp7_wip.pcs(proj->'denominator');if num=0 then continue;end if;
    room:=least(cp7_wip.pcs(p->'remaining_pcs'),cp7_wip.pcs(proj->'eligible_input_pcs'))-coalesce((used->>k)::numeric,0);
    room:=least(room,cp7_wip.pcs(pools->pk->'wip_pcs')-coalesce((pool_used->>pk)::numeric,0));
    good:=greatest(0,least(left_need,capacity,floor(room*num/den),cp7_wip.pcs(proj->'projected_good_pcs')-coalesce((good_used->>k)::numeric,0)));
    if good=0 then continue;end if;input_qty:=ceil(good*den/num);
    select jsonb_agg(value order by value::text) into refs from (select distinct value from jsonb_array_elements((s->'refs')||(tf->'refs'))) q;
    edges:=edges||jsonb_build_array(jsonb_build_object('key','edge-'||(jsonb_array_length(edges)+1),'position_key',k,'target_key',t->'key','size_id',t->'size_id',
     'input_pcs',input_qty::text,'projected_good_pcs',good::text,'match',m->'match','refs',refs));
    used:=used||jsonb_build_object(k,coalesce((used->>k)::numeric,0)+input_qty);good_used:=good_used||jsonb_build_object(k,coalesce((good_used->>k)::numeric,0)+good);
    pool_used:=pool_used||jsonb_build_object(pk,coalesce((pool_used->>pk)::numeric,0)+input_qty);capacity:=capacity-good;left_need:=left_need-good;
   end loop;
  end if;
  results:=results||jsonb_build_array(jsonb_build_object('target_key',t->'key','size_id',t->'size_id','need_pcs',need::text,'allocated_good_pcs',(need-left_need)::text,
   'unresolved_pcs',left_need::text,'production_status',t->'production_status','priority_basis',jsonb_build_object('risk_at',t->'risk_at','deadline',t->'deadline','helps_at',t->'helps_at','size_gap',t->'need_pcs','stable_key',t->'key')));
 end loop;
 validation:=cp7_wip.check_allocations(v->'positions',jsonb_build_object('scenario_id',v->'scenario_id','scope_id',v->'scope_id','complete_scope',true,'matching',v->'matching','edges',edges));
 if validation->>'status'<>'FEASIBLE' then raise exception 'CP7_BASELINE_GENERATED_ALLOCATION_INVALID';end if;
 return jsonb_build_object('status','SCENARIO','kernel_version','greedy-allocation-1','scenario_id',v->'scenario_id','snapshot_id',v->'snapshot_id','scope_id',v->'scope_id',
  'rows',results,'review_queue',review,'remaining_capacity_pcs',capacity::text,'allocation',validation,'inputs',v,
  'reason','GLOBAL_SCOPE_RECOMPUTED_MATCH_YIELD_POOL_CAPACITY_PRIORITY_SIMULATION_ONLY');
end $$;
