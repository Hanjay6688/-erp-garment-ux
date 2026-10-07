-- P19 PROTOTYPE (not wired to the app): staged analysis for up to 5000 Native
-- planning targets. The single capture call (cp7_analysis_native.capture) and
-- its caps are unchanged. A staged job stores ONE reference copy of the source
-- (snapshots.facts) and then computes the same compiler in units, each unit an
-- ordinary request under the unchanged 8 s statement limit:
--   SCENARIO -> NET_PREP -> NET_TARGETS*k -> NET_PAIRS*k -> NET_PLAN
--   -> [ALLOC_PREP -> ALLOC_STEP*k -> ALLOC_FINAL] -> NET_ROWS*k
--   -> FABRIC_PLAN -> ANA_TARGETS*k -> ANA_META -> ANA_TEXT -> RUN_INSERT
--   -> DOC_RENDER -> DOC_SEGMENTS*k
-- Every unit reads only the stored reference and earlier units' immutable
-- outputs, so no unit can mix source versions. The final analysis is byte for
-- byte cp7_analysis_native.build(facts,query,run_id,access) (parity tests).
-- Caps that bounded one call are bounds per unit here (targets per chunk,
-- pairs per chunk, targets per allocation step); the whole job keeps declared
-- caps (targets 5000, positions 1000, pairs 1000000, matching products 10000)
-- and refuses above them. The SCENARIO unit is still the single schedule build
-- (history/baseline/supply/schedule): staging it is open (see DESIGN).
-- Loop bodies below are copies of netting.build, allocate and
-- build_operational; the parity tests guard them. Production should make the
-- single call run the same stage functions over one range instead.
create schema cp7_analysis_stage authorization cp7_capture;
revoke all on schema cp7_analysis_stage from public,anon,authenticated,service_role;

-- ---------------------------------------------------------------- netting --
-- Everything netting.build computes before its first target loop, plus the
-- pair-matrix maps it computes after it (they read only arrays the earlier
-- steps already read, so computing them first raises nothing new).
create function cp7_analysis_stage.netting_prep(c jsonb,scenario jsonb,p_targets integer,p_pairs bigint,p_match integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare wip jsonb:=scenario->'wip';hash text;m jsonb;matching jsonb;models jsonb;p jsonb;eta jsonb;etas jsonb;
 eta_list jsonb[]:='{}';eligible jsonb[]:='{}';budget numeric:=0;supplies_complete boolean:=true;
 eta_at jsonb;eta_repeated jsonb;target_at jsonb;target_repeated jsonb;source_at jsonb;source_repeated jsonb;
 row_keys text[];row_target_keys jsonb[];n integer;first_repeated integer;model_targets jsonb;leaders integer[];row_at jsonb;
 rows jsonb:=scenario->'supply_run_result'->'baseline_run_result'->'rows';sorted integer[]:='{}';ord_i bigint;
begin
 hash:=cp7_netting_native.fingerprint(c);
 if wip->>'status'is distinct from 'COMPLETE'then return jsonb_build_object('wip_complete',false,'hash',hash,
  'alloc',jsonb_build_object('status','UNKNOWN','reason','NATIVE_QUANTITY_CAPTURE_INCOMPLETE'));end if;
 -- Single call: positions x rows above 100000 refuse here. Staged: pairs are
 -- computed in chunks of at most 100000 (netting_pairs); p_pairs bounds the job.
 if jsonb_array_length(wip->'positions')*jsonb_array_length(rows)>p_pairs
  or jsonb_array_length(wip->'positions')>1000 then raise exception 'CP7_NETTING_WORK_LIMIT';end if;
 if jsonb_array_length(rows)>p_targets then raise exception 'CP7_ANALYSIS_STAGED_TARGET_LIMIT';end if;
 m:=cp7_netting_native.matching_models_within(c,wip,p_match);matching:=m->'matching';models:=m->'models';
 for eta in select value from jsonb_array_elements(scenario->'etas')loop
  eta_list:=array_append(eta_list,jsonb_build_object('position_key',eta->'position_key',
   'at',case when eta->'result'->>'status'in('KNOWN','CONDITIONAL')then cp7_planning.utc((eta->'result'->>'eta')::timestamptz)else null end,
   'refs',eta->'refs'));
 end loop;
 etas:=to_jsonb(eta_list);
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into eta_at,eta_repeated
  from(select value->>'position_key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(etas)
   where value->>'position_key'is not null group by 1)f;
 for p in select value from jsonb_array_elements(wip->'positions')where value->'eligible_company_wip'='true'::jsonb loop
  if eta_repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  eta:=eta_at->(p->>'key');eligible:=array_append(eligible,p);
  if p->'projection'->>'quality'='SCENARIO'and eta->>'at'is not null then
   budget:=budget+cp7_wip.pcs(p->'projection'->'projected_good_pcs');
  elsif cp7_wip.pcs(p->'remaining_pcs')>0 then supplies_complete:=false;end if;
 end loop;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into target_at,target_repeated
  from(select value->>'key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(matching->'targets')
   where value->>'key'is not null group by 1)f;
 -- The rows in the build's loop order (same sort, same input order).
 for ord_i in select x.o from jsonb_array_elements(rows)with ordinality x(value,o)order by x.value->>'target_key'loop
  sorted:=array_append(sorted,ord_i::integer);
 end loop;
 select coalesce(array_agg(value->>'target_key' order by o),'{}'),coalesce(array_agg(value->'target_key' order by o),'{}')into row_keys,row_target_keys
  from jsonb_array_elements(rows)with ordinality a(value,o);
 n:=cardinality(row_keys);
 select coalesce(min(u.j),n+1)into first_repeated from unnest(row_keys)with ordinality u(k,j)where target_repeated?u.k;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into source_at,source_repeated
  from(select value->>'key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(matching->'sources')
   where value->>'key'is not null group by 1)f;
 select coalesce(jsonb_object_agg(f.m,f.ks),'{}')into model_targets
  from(select x->>'model_id' m,jsonb_object_agg((x->>'root_id')||':'||(x->>'size_id'),true)ks from jsonb_array_elements(c->'facts'->'products')x
   where x->>'model_id'is not null and(x->>'root_id')||':'||(x->>'size_id')is not null group by 1)f;
 select coalesce(array_agg(f.leader order by f.i),'{}')into leaders
  from(select g.i,case when g.facts is null then g.i else min(g.i)over(partition by g.facts)end leader
   from(select e.i,case when e.s is not null and e.model is not null then
      jsonb_build_array(e.s->'quality',e.s->'size_id',e.s->'confirmed_target',e.s->'constraints',e.model)::text end facts
     from(select x.i,source_at->(x.p->>'key') s,models->>(x.p::text) model from unnest(eligible)with ordinality x(p,i))e)g)f;
 select coalesce(jsonb_object_agg(f.k,f.j),'{}')into row_at
  from(select u.k,min(u.j)j from unnest(row_keys)with ordinality u(k,j)where u.k is not null group by 1)f;
 return jsonb_build_object('wip_complete',true,'hash',hash,'ready',c->>'captured_at','snapshot_id',wip->'snapshot_id',
  'matching',matching,'models',models,'etas',etas,'eta_at',eta_at,'eta_repeated',eta_repeated,'eligible',to_jsonb(eligible),
  'budget',budget::text,'supplies_complete',supplies_complete,'target_at',target_at,'target_repeated',target_repeated,
  'row_keys',to_jsonb(row_keys),'row_target_keys',to_jsonb(row_target_keys),'n',n,'first_repeated',first_repeated,
  'source_at',source_at,'source_repeated',source_repeated,'model_targets',model_targets,'leaders',to_jsonb(leaders),
  'row_at',row_at,'sorted',to_jsonb(sorted));
end $$;

-- netting.build's first target loop for one chunk of rows (loop order).
-- c needs captured_at and schedule; wip needs snapshot_id (timeline and net
-- read nothing else of them).
create function cp7_analysis_stage.netting_targets(g jsonb,c jsonb,wip jsonb,rows jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare r jsonb;cfg jsonb;policy text;production_status text;raw_net jsonb;raw_need numeric;deadline timestamptz;helps timestamptz;
 line jsonb;tf jsonb;refs jsonb;out jsonb[]:='{}';reviews jsonb[];all_known boolean:=true;ready timestamptz:=(g->>'ready')::timestamptz;
 target_repeated jsonb:=g->'target_repeated';target_at jsonb:=g->'target_at';etas jsonb:=g->'etas';matching jsonb:=g->'matching';hash text:=g->>'hash';
begin
 for r in select x.value from jsonb_array_elements(rows)with ordinality x(value,o)order by x.o loop
  cfg:=r->'profile'->'config';policy:=r->'production_policy'->'policy'->>'state';reviews:='{}';
  if r->'target'->>'status'is distinct from 'SCENARIO'or r->>'available_fg_pcs'is null then
   all_known:=false;out:=array_append(out,jsonb_build_object('planned',false,'reviews',jsonb_build_array(
    jsonb_build_object('target_key',r->'target_key','reason','DEMAND_TARGET_STOCK_OR_PRODUCTION_POLICY_UNREVIEWED'))));continue;end if;
  if policy is null then all_known:=false;reviews:=array_append(reviews,jsonb_build_object('target_key',r->'target_key','reason','PRODUCTION_POLICY_UNREVIEWED'));end if;
  production_status:=case when policy='ACTIVE'then 'ACTIVE'when policy in('PAUSED','STOPPED')then 'STOP'else 'UNKNOWN'end;
  raw_net:=cp7_baseline.net(jsonb_build_object('contract_version','cp7.net-input.v1','snapshot_id',wip->'snapshot_id',
   'scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',coalesce(c->'schedule'->'plan_id',to_jsonb('unreviewed-'||hash)),
   'target_key',r->'target_key','size_id',r->'size_id','deadline',cp7_planning.utc(ready),
   'target_pcs',r->'target'->'target_pcs','available_fg_pcs',r->'available_fg_pcs','supplies','[]'::jsonb,'refs',r->'refs'));
  raw_need:=cp7_wip.pcs(raw_net->'q_base_pcs');
  deadline:=ready+((cp7_demand.decimal(cfg->'lead_days')+cp7_demand.decimal(cfg->'review_days'))::text||' days')::interval;
  helps:=ready+(cp7_demand.decimal(cfg->'lead_days')::text||' days')::interval;
  line:=cp7_netting_native.timeline(c,r,etas,'[]'::jsonb,matching,wip);
  if target_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  tf:=target_at->(r->>'target_key');
  select jsonb_agg(x order by x::text)into refs from(select distinct value x from jsonb_array_elements((r->'refs')||(tf->'refs')))u;
  out:=array_append(out,jsonb_build_object('planned',true,'reviews',to_jsonb(reviews),'line',line,
   'target',jsonb_build_object('key',r->'target_key','size_id',r->'size_id',
   'need_pcs',raw_need::text,'deadline',cp7_planning.utc(deadline),
   'risk_at',coalesce(line->'first_known_gap'->'at',to_jsonb(cp7_planning.utc(deadline))),
   'helps_at',cp7_planning.utc(helps),'production_status',production_status,'refs',refs)));
 end loop;
 return jsonb_build_object('rows',to_jsonb(out),'all_known',all_known);
end $$;

-- netting.build's pair loop for eligible positions lo..hi (1-based, eligible
-- order) against every row. leader_rows holds the pair row of each leader
-- before lo (a later position with a leader's facts reuses its verdicts).
create function cp7_analysis_stage.netting_pairs(g jsonb,lo integer,hi integer,leader_rows jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare p jsonb;s jsonb;model text;compatible jsonb;m jsonb;j integer;i integer;n integer:=(g->>'n')::integer;
 first_repeated integer:=(g->>'first_repeated')::integer;row_keys text[];leaders integer[];out jsonb[]:='{}';
 source_at jsonb:=g->'source_at';source_repeated jsonb:=g->'source_repeated';models jsonb:=g->'models';
 model_targets jsonb:=g->'model_targets';target_at jsonb:=g->'target_at';eligible jsonb:=g->'eligible';
 unknown_model jsonb:=jsonb_build_object('match','UNKNOWN','reasons',jsonb_build_array('NATIVE_SOURCE_MODEL_UNPROVEN'));
 model_mismatch jsonb:=jsonb_build_object('match','INCOMPATIBLE','reasons',jsonb_build_array('NATIVE_MODEL_MISMATCH'));
begin
 if n=0 then return '[]'::jsonb;end if;
 select coalesce(array_agg(x.k order by x.o),'{}')into row_keys from jsonb_array_elements_text(g->'row_keys')with ordinality x(k,o);
 select coalesce(array_agg(x.k::integer order by x.o),'{}')into leaders from jsonb_array_elements_text(g->'leaders')with ordinality x(k,o);
 for i in lo..hi loop
  p:=eligible->(i-1);
  if source_repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  s:=source_at->(p->>'key');model:=models->>(p::text);compatible:=model_targets->model;
  if leaders[i]<i then
   select min(u.j)into j from unnest(row_keys)with ordinality u(k,j)where coalesce(compatible?u.k,false);
   if j is not null then m:=cp7_wip.match_target(s,target_at->row_keys[j]);end if;
   out:=array_append(out,case when leaders[i]>=lo then out[leaders[i]-lo+1] else leader_rows->(leaders[i]::text)end);
  else
   select coalesce(jsonb_agg(case when model is null then unknown_model when not coalesce(compatible?u.k,false)then model_mismatch
     else cp7_wip.match_target(s,target_at->u.k)end order by u.j),'[]')into m
    from unnest(row_keys)with ordinality u(k,j)where u.j<first_repeated;
   out:=array_append(out,m);
   if first_repeated<=n then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  end if;
 end loop;
 return to_jsonb(out);
end $$;

-- What netting.build decides between its pair loop and the allocation: the
-- planned targets, whether allocation runs, and the allocation input.
-- targets: every planned target entry in loop order; all_known: the first
-- loop's flag over all chunks.
create function cp7_analysis_stage.netting_plan(g jsonb,c jsonb,wip jsonb,schedule_state text,targets jsonb,all_known boolean)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare alloc jsonb;v jsonb;planned_at jsonb;planned_repeated jsonb;
begin
 if not all_known then alloc:=jsonb_build_object('status','UNKNOWN','reason','GLOBAL_TARGET_NEEDS_OR_POLICY_NOT_FULLY_REVIEWED');
 elsif schedule_state<>'SELECTED_ASSUMPTIONS'then alloc:=jsonb_build_object('status','UNKNOWN','reason','SOURCE_BOUND_WORK_YIELD_NOT_REVIEWED');
 elsif not(g->>'supplies_complete')::boolean then alloc:=jsonb_build_object('status','UNKNOWN','reason','EXISTING_SUPPLY_YIELD_OR_SHARED_ETA_UNKNOWN');
 else
  v:=jsonb_build_object('contract_version','cp7.allocation-input.v1',
   'snapshot_id',wip->'snapshot_id','scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',c->'schedule'->'plan_id',
   'complete_scope',true,'positions',wip,'matching',g->'matching','etas',g->'etas','targets',targets,
   'capacity_pcs',g->>'budget','refs',jsonb_build_array(cp7_wip.ref('PLANNING_SCHEDULE',c->'schedule'->>'plan_id',c->'schedule'->>'revision')));
 end if;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into planned_at,planned_repeated
  from(select value->>'key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(targets)
   where value->>'key'is not null group by 1)f;
 return jsonb_build_object('alloc',alloc,'allocation_input',v,'planned_at',planned_at,'planned_repeated',planned_repeated);
end $$;

-- netting.build's second target loop for one chunk. rows: this chunk's rows
-- (loop order) each as {ord,row}; first: the first loop's output per ord;
-- planned_ord: target key -> ord of its planned row; pairs: target key -> its
-- match results in match_results order, each {i: eligible index, e: entry}
-- (a position key may be null; the index is not); candidates: target key ->
-- its allocated CANDIDATE_MATCH edges in allocation edge order.
create function cp7_analysis_stage.netting_rows(g jsonb,c jsonb,wip jsonb,capacity jsonb,alloc_status text,plan jsonb,
 planned_ord jsonb,rows jsonb,first jsonb,pairs jsonb,candidates jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare x jsonb;r jsonb;t jsonb;p jsonb;m jsonb;eta jsonb;line jsonb;net jsonb;supplies jsonb;directed_edges jsonb;line_edges jsonb;
 raw_need numeric;gap numeric;directed numeric;candidate numeric;open_work jsonb[];open_index integer[];i integer;w integer;supply_list jsonb[];edge_list jsonb[];
 row_list jsonb[]:='{}';by_position jsonb;hash text:=g->>'hash';eta_at jsonb:=g->'eta_at';eta_repeated jsonb:=g->'eta_repeated';
 planned_at jsonb:=plan->'planned_at';planned_repeated jsonb:=plan->'planned_repeated';etas jsonb:=g->'etas';matching jsonb:=g->'matching';
begin
 for x in select y.value from jsonb_array_elements(rows)with ordinality y(value,o)order by y.o loop
  r:=x->'row';directed:=0;candidate:=0;raw_need:=null;gap:=null;supplies:='[]';directed_edges:='[]';net:=null;
  if planned_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  t:=planned_at->(r->>'target_key');
  if t is not null then
   raw_need:=cp7_wip.pcs(t->'need_pcs');
   if open_work is null then
    open_work:='{}';open_index:='{}';i:=0;
    for p in select value from jsonb_array_elements(g->'eligible')loop
     i:=i+1;
     if cp7_wip.pcs(p->'remaining_pcs')>0 then open_work:=array_append(open_work,p);open_index:=array_append(open_index,i);end if;
    end loop;
   end if;
   -- The pair result of each open position for this key's first row: the
   -- first result of that position in the key's match results.
   select coalesce(jsonb_object_agg(f.k,f.v),'{}')into by_position from(
    select y.value->>'i' k,(array_agg(y.value->'e'->'result' order by y.o))[1] v
    from jsonb_array_elements(coalesce(pairs->(r->>'target_key'),'[]'))with ordinality y(value,o)group by 1)f;
   supply_list:='{}';edge_list:='{}';
   for w in 1..coalesce(cardinality(open_work),0) loop
    p:=open_work[w];m:=by_position->(open_index[w]::text);
    if eta_repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
    eta:=eta_at->(p->>'key');
    if m->>'match'='CONFIRMED_TARGET'then
     supply_list:=array_append(supply_list,jsonb_build_object('physical_key',p->'key','snapshot_id',wip->'snapshot_id',
      'target_key',r->'target_key','size_id',r->'size_id','kind','DIRECTED',
      'qty_pcs',case when p->'projection'->>'quality'='SCENARIO'then p->'projection'->'projected_good_pcs'else null end,
      'eta',coalesce(eta->'at','null'::jsonb),'eligible',true,'refs',p->'refs'));
     if p->'projection'->>'quality'='SCENARIO'and eta->>'at'is not null then
      edge_list:=array_append(edge_list,jsonb_build_object('key',p->'key','position_key',p->'key',
       'target_key',r->'target_key','projected_good_pcs',p->'projection'->'projected_good_pcs','refs',p->'refs'));
     end if;
    end if;
   end loop;
   for p in select value from jsonb_array_elements(candidates->(r->>'target_key'))loop
    if eta_repeated?(p->>'position_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
    eta:=eta_at->(p->>'position_key');
    supply_list:=array_append(supply_list,jsonb_build_object('physical_key',p->'position_key','snapshot_id',wip->'snapshot_id',
     'target_key',r->'target_key','size_id',r->'size_id','kind','ALLOCATED_CANDIDATE','qty_pcs',p->'projected_good_pcs',
     'eta',eta->'at','eligible',true,'refs',p->'refs'));
   end loop;
   supplies:=to_jsonb(supply_list);directed_edges:=to_jsonb(edge_list);
   net:=cp7_baseline.net(jsonb_build_object('contract_version','cp7.net-input.v1','snapshot_id',wip->'snapshot_id',
    'scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',coalesce(c->'schedule'->'plan_id',to_jsonb('unreviewed-'||hash)),
    'target_key',r->'target_key','size_id',r->'size_id','deadline',t->'deadline',
    'target_pcs',r->'target'->'target_pcs','available_fg_pcs',r->'available_fg_pcs','supplies',supplies,'refs',r->'refs'));
   gap:=(net->>'q_base_pcs')::numeric;directed:=coalesce((net->>'directed_on_time_pcs')::numeric,0);
   candidate:=coalesce((net->>'candidate_on_time_pcs')::numeric,0);
  end if;
  if t is null then line:=jsonb_build_object('status','UNKNOWN','reason','TARGET_NEEDS_OR_POLICY_UNREVIEWED');
  else
   line_edges:=directed_edges||coalesce(candidates->(r->>'target_key'),'[]'::jsonb);
   -- build() reuses the first loop's timeline only for the very row that
   -- loop planned: a planned key is unique here (planned_repeated refused
   -- above), so that row is the one with this key's planned ord.
   if line_edges='[]'::jsonb and(planned_ord->>(r->>'target_key'))::integer=(x->>'ord')::integer then
    line:=first->(x->>'ord')->'line';
   else line:=cp7_netting_native.timeline(c,r,etas,line_edges,matching,wip);end if;
  end if;
  row_list:=array_append(row_list,r||jsonb_build_object('raw_gap_pcs',raw_need::text,'directed_on_time_good_pcs',net->'directed_on_time_pcs',
   'base_gap_pcs',net->'q_base_pcs','conditional_gap_pcs',case when alloc_status='SCENARIO'then net->'q_conditional_pcs'else null end,
   'net',net,
   'candidate_allocated_good_pcs',case when alloc_status='SCENARIO'then candidate::text else null end,
   'timeline',line,'start_new_pcs',case when t->>'production_status'='STOP'then '0'else null end,
   'material_state','UNKNOWN','new_start_capacity',capacity,'apply_enabled',false,
   'netting_basis','NATIVE_AVAILABLE_FG_ONCE_SOURCE_BOUND_YIELD_AND_ONE_SHARED_REMAINING_CALENDAR',
   'reason','SCENARIO_EXISTING_SUPPLY_DISTINCT_FROM_NEW_START_MATERIAL_FEASIBILITY'));
 end loop;
 return to_jsonb(row_list);
end $$;

-- ------------------------------------------------------------- allocation --
-- cp7_baseline.allocate as prep (all validation, the priority order and the
-- per-position arrays), steps over the priority order with carried state
-- (capacity, used, good used, pool used, edge count) and a final validation.
-- The verdict memo is per step: a dropped memo only repeats match_target
-- calls the memo had proven, with the same results.
create function cp7_analysis_stage.alloc_prep(v jsonb,p_targets integer,p_visits bigint)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare t jsonb;p jsonb;tf jsonb;eta jsonb;pool jsonb;e jsonb;proj jsonb;k text;pk text;validation jsonb;capacity numeric;
 num numeric;den numeric;room numeric;good numeric;i integer;repeated integer;sources_n integer;targets_n integer;
 pool_at jsonb;position_at jsonb;eta_at jsonb;source_at jsonb;target_at jsonb;target_ids jsonb;size_lists jsonb;ordered jsonb[]:='{}';
 pool_wip numeric[]:='{}';position_keys text[]:='{}';position_pools integer[]:='{}';remaining numeric[]:='{}';
 eligible_input numeric[]:='{}';projected_good numeric[]:='{}';numerators numeric[]:='{}';denominators numeric[]:='{}';
 eta_times timestamptz[];reviewed boolean[];source_ids integer[];source_confirmed text[];
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','scenario_id','complete_scope','positions','matching','etas','targets','capacity_pcs','refs']);
 perform cp7_demand.context(v,'cp7.allocation-input.v1');perform cp7_wip.key(v->'scenario_id');perform cp7_wip.refs(v->'refs');
 if jsonb_typeof(v->'complete_scope') is distinct from 'boolean' then raise exception 'CP7_BASELINE_SCOPE';end if;
 if v->'complete_scope'='false'::jsonb then return jsonb_build_object('result',jsonb_build_object('status','UNKNOWN','reason','COMPLETE_ALLOCATION_SCOPE_REQUIRED'));end if;
 if v->'capacity_pcs'='null'::jsonb then return jsonb_build_object('result',jsonb_build_object('status','UNKNOWN','reason','SHARED_CAPACITY_UNKNOWN'));end if;
 capacity:=cp7_wip.pcs(v->'capacity_pcs');
 if v->'positions'->>'snapshot_id' is distinct from v->>'snapshot_id' or v->'matching'->>'snapshot_id' is distinct from v->>'snapshot_id' then raise exception 'CP7_BASELINE_MATCH_SNAPSHOT';end if;
 validation:=cp7_wip.check_allocations(v->'positions',jsonb_build_object('scenario_id',v->'scenario_id','scope_id',v->'scope_id','complete_scope',true,'matching',v->'matching','edges','[]'::jsonb));
 if validation->>'status'<>'FEASIBLE' then return jsonb_build_object('result',validation);end if;
 perform cp7_demand.items(v->'positions'->'positions',1000);perform cp7_demand.items(v->'positions'->'totals',1000);
 perform cp7_demand.items(v->'targets',p_targets);perform cp7_demand.items(v->'etas',1000);
 -- Single call: positions x targets above 100000 refuse here. Staged: the
 -- job bound (p_visits) refuses here; each alloc_step is bounded on its own.
 if jsonb_array_length(v->'positions'->'positions')*jsonb_array_length(v->'targets')>p_visits then raise exception 'CP7_BASELINE_ALLOCATION_LIMIT';end if;
 select min(f.o) into repeated from(select a.o,row_number()over(partition by a.value->>'pool_key' order by a.o)n
  from jsonb_array_elements(v->'positions'->'totals')with ordinality a(value,o)where a.value->>'pool_key' is not null)f where f.n>1;
 i:=0;
 for pool in select value from jsonb_array_elements(v->'positions'->'totals') loop
  i:=i+1;k:=cp7_wip.key(pool->'pool_key');pool_wip:=array_append(pool_wip,cp7_wip.pcs(pool->'wip_pcs'));
  if i=repeated then raise exception 'CP7_BASELINE_DUPLICATE_POOL';end if;
 end loop;
 select coalesce(jsonb_object_agg(a.value->>'pool_key',a.o),'{}') into pool_at from jsonb_array_elements(v->'positions'->'totals')with ordinality a(value,o);
 select min(f.o) into repeated from(select a.o,row_number()over(partition by a.value->>'key' order by a.o)n
  from jsonb_array_elements(v->'positions'->'positions')with ordinality a(value,o)where a.value->>'key' is not null)f where f.n>1;
 i:=0;
 for p in select value from jsonb_array_elements(v->'positions'->'positions') loop
  i:=i+1;
  k:=cp7_wip.key(p->'key');pk:=cp7_wip.key(p->'pool_key');perform cp7_wip.key(p->'size_id');remaining:=array_append(remaining,cp7_wip.pcs(p->'remaining_pcs'));perform cp7_wip.refs(p->'refs');
  if i=repeated or not pool_at ? pk or jsonb_typeof(p->'eligible_company_wip') is distinct from 'boolean' then raise exception 'CP7_BASELINE_POSITION';end if;
  position_keys:=array_append(position_keys,k);position_pools:=array_append(position_pools,(pool_at->>pk)::integer);
  num:=null;den:=null;room:=null;good:=null;
  if p->'projection'->>'quality'='SCENARIO' then
   proj:=p->'projection';num:=cp7_wip.pcs(proj->'numerator');den:=cp7_wip.pcs(proj->'denominator');
   room:=cp7_wip.pcs(proj->'eligible_input_pcs');good:=cp7_wip.pcs(proj->'projected_good_pcs');
   if den=0 or num>den then raise exception 'CP7_BASELINE_YIELD';end if;
  end if;
  numerators:=array_append(numerators,num);denominators:=array_append(denominators,den);
  eligible_input:=array_append(eligible_input,room);projected_good:=array_append(projected_good,good);
 end loop;
 select coalesce(jsonb_object_agg(a.value->>'key',a.o),'{}') into position_at from jsonb_array_elements(v->'positions'->'positions')with ordinality a(value,o);
 select min(f.o) into repeated from(select a.o,row_number()over(partition by a.value->>'position_key' order by a.o)n
  from jsonb_array_elements(v->'etas')with ordinality a(value,o)where a.value->>'position_key' is not null)f where f.n>1;
 i:=0;
 for eta in select value from jsonb_array_elements(v->'etas') loop
  i:=i+1;
  perform cp7_wip.fields(eta,array['position_key','at','refs']);k:=cp7_wip.key(eta->'position_key');perform cp7_wip.refs(eta->'refs');
  if i=repeated or not position_at ? k then raise exception 'CP7_BASELINE_ETA_BINDING';end if;
  if eta->'at'<>'null'::jsonb then perform cp7_demand.instant(eta->'at');end if;
 end loop;
 select coalesce(jsonb_object_agg(a.value->>'position_key',a.value),'{}') into eta_at from jsonb_array_elements(v->'etas')a;
 select min(f.o) into repeated from(select a.o,row_number()over(partition by a.value->>'key' order by a.o)n
  from jsonb_array_elements(v->'targets')with ordinality a(value,o)where a.value->>'key' is not null)f where f.n>1;
 i:=0;
 for t in select value from jsonb_array_elements(v->'targets') loop
  i:=i+1;
  perform cp7_wip.fields(t,array['key','size_id','need_pcs','deadline','risk_at','helps_at','production_status','refs']);k:=cp7_wip.key(t->'key');perform cp7_wip.key(t->'size_id');perform cp7_wip.refs(t->'refs');
  perform cp7_wip.pcs(t->'need_pcs');
  if i=repeated or t->>'production_status' is null or t->>'production_status' not in ('ACTIVE','STOP') then raise exception 'CP7_BASELINE_TARGET';end if;
  foreach e in array array[t->'deadline',t->'risk_at',t->'helps_at'] loop if e<>'null'::jsonb then perform cp7_demand.instant(e);end if;end loop;
  if target_at is null then
   select coalesce(jsonb_object_agg(a.value->>'key',a.value),'{}') into target_at from jsonb_array_elements(v->'matching'->'targets')a;
  end if;
  tf:=target_at->k;
  if tf is null or tf->>'size_id'<>t->>'size_id' or not ((t->'refs') @> (tf->'refs')) then raise exception 'CP7_BASELINE_TARGET_MATCH_BINDING';end if;
 end loop;
 -- The main loop's priority order (same ORDER BY, same input order).
 for t in select value from jsonb_array_elements(v->'targets') order by
  case when value->'risk_at'<>'null'::jsonb then cp7_demand.instant(value->'risk_at') end nulls last,
  case when value->'deadline'<>'null'::jsonb then cp7_demand.instant(value->'deadline') end nulls last,
  case when value->'helps_at'<>'null'::jsonb then cp7_demand.instant(value->'helps_at') end nulls last,
  cp7_wip.pcs(value->'need_pcs') desc,value->>'key' loop
  ordered:=array_append(ordered,t);
 end loop;
 -- The size lists and fact classes allocate builds at its first timed
 -- ACTIVE target. Every operand was validated above, so building them here
 -- raises nothing; they are unused when no such target exists.
 with x as(select a.o::integer o,a.value p,case when eta_at->(a.value->>'key')->'at'<>'null'::jsonb then cp7_demand.instant(eta_at->(a.value->>'key')->'at') end at
   from jsonb_array_elements(v->'positions'->'positions')with ordinality a(value,o)),
  r as(select x.o,x.p,x.at,row_number()over(order by x.at nulls last,x.p->>'key')rk from x)
 select(select coalesce(jsonb_object_agg(g.sz,g.os),'{}')from(select r.p->>'size_id' sz,jsonb_agg(r.o order by r.rk)os from r
    where r.p->'eligible_company_wip'<>'false'::jsonb group by 1)g),
  coalesce(array_agg(r.at order by r.o),'{}'),
  coalesce(array_agg(eta_at->(r.p->>'key') is null or eta_at->(r.p->>'key')->'at'='null'::jsonb or r.p->'projection'->>'quality' is distinct from 'SCENARIO' order by r.o),'{}')
  into size_lists,eta_times,reviewed from r;
 select coalesce(jsonb_object_agg(a.value->>'key',a.value),'{}') into source_at from jsonb_array_elements(v->'matching'->'sources')a;
 select coalesce(array_agg(f.id order by f.o),'{}'),coalesce(array_agg(f.s->>'confirmed_target' order by f.o),'{}'),coalesce(max(f.id),0) into source_ids,source_confirmed,sources_n
  from(select x.o,x.s,dense_rank()over(order by jsonb_build_array(x.s->'quality',x.s->'size_id',x.s->'confirmed_target'='null'::jsonb,x.s->'constraints')::text collate "C")::integer id
   from(select a.o,source_at->(a.value->>'key') s from jsonb_array_elements(v->'positions'->'positions')with ordinality a(value,o))x)f;
 select coalesce(jsonb_object_agg(f.k,f.id),'{}'),coalesce(max(f.id),0) into target_ids,targets_n
  from(select x.k,dense_rank()over(order by jsonb_build_array(x.tf->'size_id',x.tf->'constraints')::text collate "C")::integer id
   from(select a.value->>'key' k,target_at->(a.value->>'key') tf from jsonb_array_elements(v->'targets')a)x)f;
 return jsonb_build_object('ordered',to_jsonb(ordered),'target_at',target_at,'source_at',source_at,'size_lists',size_lists,
  'eta_times',to_jsonb(eta_times),'reviewed',to_jsonb(reviewed),'source_ids',to_jsonb(source_ids),'source_confirmed',to_jsonb(source_confirmed),
  'sources_n',sources_n,'target_ids',target_ids,'targets_n',targets_n,'position_keys',to_jsonb(position_keys),
  'position_pools',to_jsonb(position_pools),'remaining',to_jsonb(remaining),'eligible_input',to_jsonb(eligible_input),
  'projected_good',to_jsonb(projected_good),'numerators',to_jsonb(numerators),'denominators',to_jsonb(denominators),
  'carry',jsonb_build_object('capacity',capacity::text,'edges',0,
   'used',to_jsonb(array_fill(0::numeric,array[cardinality(position_keys)])),'good_used',to_jsonb(array_fill(0::numeric,array[cardinality(position_keys)])),
   'pool_used',to_jsonb(array_fill(0::numeric,array[cardinality(pool_wip)]))),'pool_wip',to_jsonb(pool_wip));
end $$;

create function cp7_analysis_stage.numerics(a jsonb)returns numeric[]
language sql immutable security invoker set search_path=''as $$
 select coalesce(array_agg(x.v::numeric order by x.o),'{}')from jsonb_array_elements_text(a)with ordinality x(v,o)
$$;

-- allocate's main loop for priority positions lo..hi of the ordered targets.
create function cp7_analysis_stage.alloc_step(s0 jsonb,carry jsonb,lo integer,hi integer,p_visits integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare t jsonb;s jsonb;tf jsonb;m jsonb;refs jsonb;k text;need numeric;left_need numeric;room numeric;good numeric;input_qty numeric;num numeric;den numeric;
 o integer;w integer;slot integer;target_id integer;target_proven boolean;deadline timestamptz;capacity numeric:=(carry->>'capacity')::numeric;edges_before integer:=(carry->>'edges')::integer;
 position_keys text[];position_pools integer[];remaining numeric[];eligible_input numeric[];projected_good numeric[];numerators numeric[];denominators numeric[];
 pool_wip numeric[];used numeric[];good_used numeric[];pool_used numeric[];eta_times timestamptz[];reviewed boolean[];source_ids integer[];source_confirmed text[];
 proven boolean[];verdicts jsonb[];sources_n integer:=(s0->>'sources_n')::integer;targets_n integer:=(s0->>'targets_n')::integer;
 target_at jsonb:=s0->'target_at';source_at jsonb:=s0->'source_at';size_lists jsonb:=s0->'size_lists';target_ids jsonb:=s0->'target_ids';
 edge_list jsonb[]:='{}';row_list jsonb[]:='{}';review_list jsonb[]:='{}';
begin
 select coalesce(array_agg(x.v order by x.o),'{}')into position_keys from jsonb_array_elements_text(s0->'position_keys')with ordinality x(v,o);
 if(hi-lo+1)::bigint*cardinality(position_keys)>p_visits then raise exception 'CP7_BASELINE_ALLOCATION_LIMIT';end if;
 select coalesce(array_agg(x.v::integer order by x.o),'{}')into position_pools from jsonb_array_elements_text(s0->'position_pools')with ordinality x(v,o);
 remaining:=cp7_analysis_stage.numerics(s0->'remaining');eligible_input:=cp7_analysis_stage.numerics(s0->'eligible_input');
 projected_good:=cp7_analysis_stage.numerics(s0->'projected_good');numerators:=cp7_analysis_stage.numerics(s0->'numerators');
 denominators:=cp7_analysis_stage.numerics(s0->'denominators');pool_wip:=cp7_analysis_stage.numerics(s0->'pool_wip');
 used:=cp7_analysis_stage.numerics(carry->'used');good_used:=cp7_analysis_stage.numerics(carry->'good_used');pool_used:=cp7_analysis_stage.numerics(carry->'pool_used');
 select coalesce(array_agg(x.v::timestamptz order by x.o),'{}')into eta_times from jsonb_array_elements_text(s0->'eta_times')with ordinality x(v,o);
 select coalesce(array_agg(x.v::boolean order by x.o),'{}')into reviewed from jsonb_array_elements_text(s0->'reviewed')with ordinality x(v,o);
 select coalesce(array_agg(x.v::integer order by x.o),'{}')into source_ids from jsonb_array_elements_text(s0->'source_ids')with ordinality x(v,o);
 select coalesce(array_agg(x.v order by x.o),'{}')into source_confirmed from jsonb_array_elements_text(s0->'source_confirmed')with ordinality x(v,o);
 proven:=array_fill(false,array[cardinality(position_keys)]);verdicts:=array_fill(null::jsonb,array[2*sources_n*targets_n]);
 for t in select x.value from jsonb_array_elements(s0->'ordered')with ordinality x(value,o)where x.o between lo and hi order by x.o loop
  need:=cp7_wip.pcs(t->'need_pcs');left_need:=need;
  if t->'deadline'='null'::jsonb or t->'risk_at'='null'::jsonb or t->'helps_at'='null'::jsonb then
   review_list:=array_append(review_list,jsonb_build_object('target_key',t->'key','reason','TIME_UNKNOWN','need_pcs',need::text));continue;end if;
  if t->>'production_status'='ACTIVE' then
   tf:=target_at->(t->>'key');
   deadline:=cp7_demand.instant(t->'deadline');target_id:=(target_ids->>(t->>'key'))::integer;target_proven:=false;
   for o in select value::integer from jsonb_array_elements_text(size_lists->(t->>'size_id')) loop
    exit when left_need=0 or capacity=0;
    k:=position_keys[o];w:=position_pools[o];
    if reviewed[o] then
     review_list:=array_append(review_list,jsonb_build_object('position_key',k,'target_key',t->'key','reason','ETA_OR_YIELD_UNKNOWN'));continue;end if;
    if eta_times[o]>deadline then continue;end if;
    s:=source_at->k;
    if s is null then raise exception 'CP7_BASELINE_SOURCE_MATCH_BINDING';end if;
    slot:=((target_id-1)*sources_n+source_ids[o]-1)*2+case when source_confirmed[o]=tf->>'key' then 2 else 1 end;
    m:=case when target_proven and proven[o] then verdicts[slot] end;
    if m is null then m:=cp7_wip.match_target(s,tf);verdicts[slot]:=m;proven[o]:=true;target_proven:=true;end if;
    if m->>'match' not in ('CANDIDATE_MATCH','CONFIRMED_TARGET') then
     review_list:=array_append(review_list,jsonb_build_object('position_key',k,'target_key',t->'key','reason',m));continue;end if;
    num:=numerators[o];den:=denominators[o];if num=0 then continue;end if;
    room:=least(remaining[o],eligible_input[o])-used[o];
    room:=least(room,pool_wip[w]-pool_used[w]);
    good:=greatest(0,least(left_need,capacity,floor(room*num/den),projected_good[o]-good_used[o]));
    if good=0 then continue;end if;input_qty:=ceil(good*den/num);
    select jsonb_agg(value order by value::text) into refs from (select distinct value from jsonb_array_elements((s->'refs')||(tf->'refs'))) q;
    edge_list:=array_append(edge_list,jsonb_build_object('key','edge-'||(edges_before+cardinality(edge_list)+1),'position_key',k,'target_key',t->'key','size_id',t->'size_id',
     'input_pcs',input_qty::text,'projected_good_pcs',good::text,'match',m->'match','refs',refs));
    used[o]:=used[o]+input_qty;good_used[o]:=good_used[o]+good;
    pool_used[w]:=pool_used[w]+input_qty;capacity:=capacity-good;left_need:=left_need-good;
   end loop;
  end if;
  row_list:=array_append(row_list,jsonb_build_object('target_key',t->'key','size_id',t->'size_id','need_pcs',need::text,'allocated_good_pcs',(need-left_need)::text,
   'unresolved_pcs',left_need::text,'production_status',t->'production_status','priority_basis',jsonb_build_object('risk_at',t->'risk_at','deadline',t->'deadline','helps_at',t->'helps_at','size_gap',t->'need_pcs','stable_key',t->'key')));
 end loop;
 return jsonb_build_object('carry',jsonb_build_object('capacity',capacity::text,'edges',edges_before+cardinality(edge_list),
  'used',to_jsonb(used),'good_used',to_jsonb(good_used),'pool_used',to_jsonb(pool_used)),
  'edges',to_jsonb(edge_list),'rows',to_jsonb(row_list),'reviews',to_jsonb(review_list));
end $$;

create function cp7_analysis_stage.alloc_final(v jsonb,carry jsonb,edges jsonb,rows jsonb,reviews jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare validation jsonb;
begin
 validation:=cp7_wip.check_allocations(v->'positions',jsonb_build_object('scenario_id',v->'scenario_id','scope_id',v->'scope_id','complete_scope',true,'matching',v->'matching','edges',edges));
 if validation->>'status'<>'FEASIBLE' then raise exception 'CP7_BASELINE_GENERATED_ALLOCATION_INVALID';end if;
 return jsonb_build_object('status','SCENARIO','kernel_version','greedy-allocation-1','scenario_id',v->'scenario_id','snapshot_id',v->'snapshot_id','scope_id',v->'scope_id',
  'rows',rows,'review_queue',reviews,'remaining_capacity_pcs',carry->>'capacity','allocation',validation,'inputs',v,
  'reason','GLOBAL_SCOPE_RECOMPUTED_MATCH_YIELD_POOL_CAPACITY_PRIORITY_SIMULATION_ONLY');
end $$;

-- --------------------------------------------------------------- analysis --
-- build_operational's per-target loop for one chunk of netting rows (loop
-- order). The maps hold only this chunk's keys, built as build builds them.
create function cp7_analysis_stage.analysis_targets(c jsonb,rows jsonb,products_by_root jsonb,stock_by_target jsonb,history_by_target jsonb,
 edges_by_target jsonb,match_results_by_target jsonb,plan_aids jsonb,fabric_plan jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare r jsonb;refs jsonb;policy text;product jsonb;stock jsonb;hist jsonb;commercial jsonb;row_aids jsonb;v jsonb;timeline jsonb;target_timeline jsonb;
 assumptions_acc jsonb[]:='{}';warnings_acc jsonb[]:='{}';actions_acc jsonb[]:='{}';recommendations_acc jsonb[]:='{}';models_acc jsonb[]:='{}';
 materials_acc jsonb[]:='{}';metrics_acc jsonb[]:='{}';timeline_acc jsonb[]:='{}';known_keys text[]:='{}';materials_null boolean:=false;
 demand_unknown boolean:=false;captured text:=c->>'captured_at';
begin
 for r in select x.value from jsonb_array_elements(rows)with ordinality x(value,o)order by x.o loop
  if r->'demand_estimate'->>'daily_pcs'is null then demand_unknown:=true;end if;
  refs:=r->'refs';policy:=r->'production_policy'->'policy'->>'state';
  if policy is null then
   warnings_acc:=array_append(warnings_acc,jsonb_build_array('PRODUCTION_POLICY_UNREVIEWED:'||(r->>'target_key')));
   actions_acc:=array_append(actions_acc,jsonb_build_array(jsonb_build_object('key','review-policy-'||(r->>'target_key'),
    'intent','REVIEW_SOURCE','source_keys','[]'::jsonb,'target_keys','[]'::jsonb,'primary_reason','PRODUCTION_POLICY_UNREVIEWED',
    'conditional',false,'source_links',refs,'display_priority',jsonb_build_object('rank',null,'lane','REVIEW_DATA',
     'basis',jsonb_build_array('Status produksi produk perlu diperiksa'),'rule_version','native-review-1'))));continue;
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
   assumptions_acc:=array_append(assumptions_acc,jsonb_build_array(jsonb_build_object('id',r->'profile'->>'profile_id',
    'label','Aturan permintaan dan target yang dipilih untuk '||(r->>'sku'),
    'origin','OWNER_INPUT','confirmed_for_operation',false)));
  end if;
  commercial:=product->'commercial'->0;known_keys:=array_append(known_keys,r->>'target_key');
  recommendations_acc:=array_append(recommendations_acc,jsonb_build_array(jsonb_build_object(
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
   'suggested_new',cp7_analysis_native.fact(case when policy in('PAUSED','STOPPED')then '0'else null end,'PCS',refs),
   'rounding_extra',cp7_analysis_native.fact(null,'PCS',refs),
   'feasible_new',cp7_analysis_native.fact(case when policy in('PAUSED','STOPPED')then '0'else null end,'PCS',refs),
   'unresolved_qty',cp7_analysis_native.fact(case when policy in('PAUSED','STOPPED')then r->>'base_gap_pcs'else null end,'PCS',refs,row_aids),
   'reason_codes',jsonb_build_array('MATERIAL_FEASIBILITY_NOT_PROVEN'),'assumption_ids',row_aids)));
  if r->'demand_estimate'->>'daily_pcs'is not null and r->'target'->>'horizon_days'is not null then
  models_acc:=array_append(models_acc,jsonb_build_array(jsonb_build_object('target_key',r->'target_key','method_id',coalesce(r->'demand_estimate'->>'basis','NATIVE_AVAILABLE_HISTORY'),
   'version','native-available-history-fallback-1','mode','FALLBACK',
   'demand_rate',cp7_analysis_native.fact(r->'demand_estimate'->>'daily_pcs','PCS/DAY',refs,row_aids),
   'observed_days',hist->'available_days','stockout_days',hist->'stockout_days','unknown_days',hist->'unknown_days',
   'horizon_days',ceil((r->'target'->>'horizon_days')::numeric),
   'selection_reason','Native available-history/manual fallback; no backtest promotion without earlier-known training evidence',
   'validation_fold_ids','[]'::jsonb,'scores','[]'::jsonb)));
  end if;
  v:=cp7_analysis_native.material_needs(c,r,row_aids);
  if v is null then materials_null:=true;elsif not materials_null then materials_acc:=array_append(materials_acc,'[]'::jsonb||v);end if;
  v:=cp7_fabric_native.needs(c,r,row_aids,fabric_plan);
  if v is null then materials_null:=true;elsif not materials_null then materials_acc:=array_append(materials_acc,'[]'::jsonb||v);end if;
  metrics_acc:=array_append(metrics_acc,jsonb_build_array(jsonb_build_object('metric_id','AVAILABLE_FG_PCS:'||(r->>'target_key'),'version','native-availability-1',
   'value',cp7_analysis_native.fact(r->>'available_fg_pcs','PCS',refs),'formula_ref','NATIVE_PHYSICAL_MINUS_ACTIVE_DRAFT_RESERVATIONS_ONCE',
   'operands',jsonb_build_array(cp7_analysis_native.fact(stock->'availability'->>'physical_fg_pcs','PCS',stock->'refs'),
    cp7_analysis_native.fact(stock->'availability'->>'reserved_pcs','PCS',stock->'refs')),
   'readiness','READY','scope_kind','TARGET','scope_key',r->'target_key',
   'period_start',((captured::timestamptz)at time zone 'Asia/Jakarta')::date::text,
   'period_end',((captured::timestamptz)at time zone 'Asia/Jakarta')::date::text,'knowledge_mode','CURRENT')));
  actions_acc:=array_append(actions_acc,jsonb_build_array(jsonb_build_object('key','review-material-'||(r->>'target_key'),'intent','REVIEW_SOURCE',
   'source_keys','[]'::jsonb,'target_keys',jsonb_build_array(r->'target_key'),'primary_reason','MATERIAL_FEASIBILITY_NOT_PROVEN',
   'conditional',true,'source_links',refs,'display_priority',jsonb_build_object('rank',null,'lane','REVIEW_DATA',
    'basis',jsonb_build_array('Periksa bahan dan batas produksi baru'),'rule_version','native-review-1'))));
  timeline:='[]';
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
    'timing_policy_id','selected-native-each24h-from-capture-1','event_refs',t.e->'refs')order by t.ordinal),'[]'::jsonb)into target_timeline from classified t;
  timeline:=timeline||target_timeline;
  end;
  timeline_acc:=array_append(timeline_acc,timeline);
 end loop;
 return jsonb_build_object(
  'assumptions',(select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)from unnest(assumptions_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o)),
  'warnings',(select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)from unnest(warnings_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o)),
  'actions',(select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)from unnest(actions_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o)),
  'recommendations',(select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)from unnest(recommendations_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o)),
  'models',(select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)from unnest(models_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o)),
  'materials',case when materials_null then null else(select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)from unnest(materials_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o))end,
  'materials_null',materials_null,
  'metrics',(select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)from unnest(metrics_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o)),
  'timeline',(select coalesce(jsonb_agg(x.value order by p.o,x.o),'[]'::jsonb)from unnest(timeline_acc)with ordinality p(v,o)cross join lateral jsonb_array_elements(p.v)with ordinality x(value,o)),
  'known_keys',to_jsonb(known_keys),'demand_unknown',demand_unknown);
end $$;

-- build_operational after its target loop, plus build's finance overlay
-- (without the semantic hash). The per-target arrays are not materialized:
-- each is one sentinel string (tag||field) when it has items, where ANA_TEXT
-- puts the stored text of every chunk. meta: known_keys, demand_unknown,
-- materials_null and the item count per field over all chunks.
create function cp7_analysis_stage.analysis_skeleton(c jsonb,q jsonb,p_run uuid,a jsonb,scenario jsonb,alloc jsonb,matching jsonb,
 meta jsonb,identity_unknown boolean,tag text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare wip jsonb:=scenario->'wip';p jsonb;e jsonb;eta jsonb;part jsonb;k text;part_hash text;count_facts integer:=0;part_count integer;
 plan_refs jsonb:='[]';plan_aids jsonb:='[]';assumptions jsonb;sources jsonb;recommendations jsonb;edges jsonb;actions jsonb;timeline jsonb;
 models jsonb;materials jsonb;metrics jsonb;warnings jsonb;dependencies jsonb:='[]';known_targets jsonb;v jsonb;
 complete boolean:=c->>'status'='COMPLETE'and wip->>'status'='COMPLETE';hash text:=cp7_analysis_native.fingerprint(c);
 allocation_known boolean:=alloc->>'status'='SCENARIO';allocated numeric;load numeric;
 scenario_revision bigint:=coalesce((c->'schedule'->>'revision')::bigint,0);
 schedule_assumption jsonb:='[]';fabric_assumptions jsonb[]:='{}';edges_acc jsonb[]:='{}';sources_acc jsonb[]:='{}';
 etas_by_position jsonb;inputs_by_source jsonb;directed_source_keys jsonb;source_inputs jsonb;
 warnings0 jsonb:='["MATERIAL_FEASIBILITY_NOT_PROVEN","ADAPTIVE_MODEL_PROMOTION_NOT_PROVEN","FINANCIAL_DOMAIN_NOT_CAPTURED"]';
begin
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
   fabric_assumptions:=array_append(fabric_assumptions,jsonb_build_object('id',part->>'id',
    'label','Pemakaian kain per PCS untuk '||(part->>'target_key')||' yang dipilih; bukan konsumsi, pemasangan atau alokasi aktual',
    'origin','OWNER_INPUT','confirmed_for_operation',false));
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
  'versions',jsonb_build_object('engine',c->'analysis_engine_signature','policy',cp7_supply_native.fingerprint(c),'models','native-available-history-fallback-1',
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

create function cp7_analysis_stage.sentinel(meta jsonb,tag text,field text)returns jsonb
language sql immutable security invoker set search_path=''as $$
 select case when coalesce((meta->'counts'->>field)::integer,0)>0 then jsonb_build_array(tag||field)else '[]'::jsonb end
$$;
-- The fields whose items are stored as chunk text and joined in ANA_TEXT.
create function cp7_analysis_stage.fragment_fields()returns text[]
language sql immutable security invoker set search_path=''as $$
 select array['assumptions','warnings','actions','recommendations','models','materials','metrics','timeline']
$$;

-- ------------------------------------------------------------------- jobs --
-- A job is one actor's request over ONE stored reference (snapshots.facts).
-- units is the plan (fixed once NET_PREP has run: 2 units before, all after);
-- outputs and the per-target tables are written once per unit, never changed.
-- Progress is read from these rows, so a reload shows the true state.
create table cp7_analysis_stage.jobs(id uuid primary key,actor uuid not null,request_id uuid not null,query jsonb not null,
 run_id uuid not null unique,access_at_capture jsonb not null,captured_at timestamptz not null,source_hash text not null,
 state text not null check(state in('RUNNING','DONE','FAILED')),unit_count integer not null check(unit_count>0),
 units_done integer not null default 0,plan_final boolean not null default false,targets_total integer,positions_total integer,
 unit_attempts integer not null default 0,failure_unit integer,failure_sqlstate text,failure_code text,
 created_at timestamptz not null,updated_at timestamptz not null,unique(actor,request_id),
 check(units_done between 0 and unit_count),check((state='FAILED')=(failure_code is not null)),
 check((state='DONE')=(plan_final and units_done=unit_count)));
create table cp7_analysis_stage.snapshots(job_id uuid primary key references cp7_analysis_stage.jobs(id),facts jsonb not null,source_hash text not null);
create table cp7_analysis_stage.units(job_id uuid not null references cp7_analysis_stage.jobs(id),idx integer not null check(idx>=0),
 kind text not null,chunk integer not null,lo integer,hi integer,primary key(job_id,idx));
create table cp7_analysis_stage.outputs(job_id uuid not null,idx integer not null,output jsonb not null,server_ms numeric not null,
 finished_at timestamptz not null,primary key(job_id,idx),foreign key(job_id,idx)references cp7_analysis_stage.units(job_id,idx));
create table cp7_analysis_stage.target_rows(job_id uuid not null references cp7_analysis_stage.jobs(id),kind text not null,ord integer not null,
 key text,payload jsonb not null,primary key(job_id,kind,ord));
create index cp7_analysis_stage_target_key on cp7_analysis_stage.target_rows(job_id,kind,key);
create table cp7_analysis_stage.pair_rows(job_id uuid not null references cp7_analysis_stage.jobs(id),i integer not null,pair_row jsonb not null,primary key(job_id,i));
create table cp7_analysis_stage.pair_lists(job_id uuid not null references cp7_analysis_stage.jobs(id),chunk integer not null,key text not null,
 results jsonb not null,primary key(job_id,key,chunk));
-- Per-target array items of one ANA_TARGETS chunk as canonical jsonb text
-- (the items joined by ', ', no brackets), and the assembled analysis text.
create table cp7_analysis_stage.fragments(job_id uuid not null references cp7_analysis_stage.jobs(id),idx integer not null,field text not null,
 body text not null,items integer not null check(items>=0),primary key(job_id,field,idx));
create table cp7_analysis_stage.texts(job_id uuid not null references cp7_analysis_stage.jobs(id),kind text not null,body text not null,
 sha256 text not null,primary key(job_id,kind));
do $$declare t text;begin
 foreach t in array array['jobs','snapshots','units','outputs','target_rows','pair_rows','pair_lists','fragments','texts']loop
  execute format('alter table cp7_analysis_stage.%I owner to cp7_capture',t);
  execute format('alter table cp7_analysis_stage.%I enable row level security',t);
  execute format('create policy cp7_analysis_stage_no_access on cp7_analysis_stage.%I for all to public using(false)with check(false)',t);
  execute format('revoke all on cp7_analysis_stage.%I from public,anon,authenticated,service_role',t);
 end loop;
 foreach t in array array['snapshots','units','outputs','target_rows','pair_rows','pair_lists','fragments','texts']loop
  execute format('create trigger immutable_stage_%s before update or delete on cp7_analysis_stage.%I for each row execute function cp7_private.immutable_run()',t,t);
 end loop;
end $$;

-- Declared bounds. Per unit: targets per chunk, pairs per chunk, position-
-- target visits per allocation step. Per job: targets, positions (netting),
-- pairs, matching products. Chunk sizes are LOCAL_PG16_DEV-derived (see DESIGN).
create function cp7_analysis_stage.bounds()returns jsonb
language sql immutable security invoker set search_path=''as $$
 select jsonb_build_object('targets_per_chunk',500,'pairs_per_chunk',100000,'visits_per_allocation_step',100000,
  'allocation_targets_per_step',1000,'targets_per_segment_unit',1000,'job_targets',5000,'job_pairs',1000000,'job_matching_products',10000)
$$;

create function cp7_analysis_stage.status(p_job uuid)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract_version','cp7.native-analysis-staged-job.v0','job_id',j.id,'request_id',j.request_id,
  'state',j.state,'units_done',j.units_done,'unit_count',j.unit_count,'plan_final',j.plan_final,
  'stage',u.kind,'stage_index',(select count(distinct x.kind)from cp7_analysis_stage.units x where x.job_id=j.id and x.idx<=coalesce(u.idx,j.units_done-1)),
  'stage_count',(select count(distinct x.kind)from cp7_analysis_stage.units x where x.job_id=j.id),
  'targets_total',j.targets_total,
  'targets_done_in_stage',(select coalesce(sum(x.hi-x.lo+1),0)from cp7_analysis_stage.units x where x.job_id=j.id and x.kind=u.kind and x.idx<j.units_done and x.lo is not null),
  'reference',jsonb_build_object('captured_at',j.captured_at,'source_hash',j.source_hash),
  'last_progress_at',j.updated_at,'unit_attempts',j.unit_attempts,
  'run_id',case when j.state='DONE'then j.run_id end,
  'failure',case when j.state='FAILED'then jsonb_build_object('unit',j.failure_unit,'sqlstate',j.failure_sqlstate,'code',j.failure_code)end,
  'apply_enabled',false,'production_go',false)
 from cp7_analysis_stage.jobs j left join cp7_analysis_stage.units u on u.job_id=j.id and u.idx=j.units_done where j.id=p_job
$$;

-- The reference: one stored copy of the source, fingerprinted once. In this
-- prototype the caller hands the captured facts; the capture stage(s) are DESIGN.
create function cp7_analysis_stage.create_job(p_actor uuid,p_request uuid,p_query jsonb,p_access jsonb,p_facts jsonb)returns uuid
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare j uuid:=gen_random_uuid();now_at timestamptz:=clock_timestamp();hash text:=cp7_analysis_native.fingerprint(p_facts);
begin
 insert into cp7_analysis_stage.jobs(id,actor,request_id,query,run_id,access_at_capture,captured_at,source_hash,state,unit_count,
  targets_total,created_at,updated_at)
 values(j,p_actor,p_request,p_query,gen_random_uuid(),p_access,(p_facts->>'captured_at')::timestamptz,hash,'RUNNING',2,
  jsonb_array_length(p_facts->'facts'->'products'),now_at,now_at);
 insert into cp7_analysis_stage.snapshots values(j,p_facts,hash);
 insert into cp7_analysis_stage.units values(j,0,'SCENARIO',0,null,null),(j,1,'NET_PREP',0,null,null);
 return j;
end $$;

create function cp7_analysis_stage.output(p_job uuid,p_kind text)returns jsonb
language sql stable security invoker set search_path=''as $$
 select o.output||'{}'::jsonb from cp7_analysis_stage.outputs o join cp7_analysis_stage.units u using(job_id,idx)
 where o.job_id=p_job and u.kind=p_kind order by u.idx desc limit 1
$$;

create function cp7_analysis_stage.tag(p_job uuid)returns text
language sql immutable security invoker set search_path=''as $$select 'P19-STAGED-'||p_job::text||'-'$$;

-- cp7_analysis_jobs.store for a document already rendered as text, in two
-- kinds of unit: the document row (sizes, hash, segment count), then segments
-- lo..hi (0-based). Same rows as store(): 2,000,000-character segments with
-- their UTF8 sizes and hashes. Each unit finds its first cut by scanning
-- characters once (store() locates every segment from the start, quadratic
-- in the length; LOCAL 65 MB: store() 25 s).
create function cp7_analysis_stage.document_row(p_run uuid,body text)returns cp7_analysis_jobs.documents
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare d cp7_analysis_jobs.documents%rowtype;n constant integer:=2000000;
begin
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-DOCUMENT:'||p_run::text,0));
 if exists(select 1 from cp7_analysis_jobs.documents where run_id=p_run)then raise exception 'CP7_ANALYSIS_DOCUMENT_EXISTS';end if;
 insert into cp7_analysis_jobs.documents(run_id,utf8_bytes,characters,sha256,segment_count,segment_characters)
 values(p_run,octet_length(body),length(body),encode(pg_catalog.sha256(convert_to(body,'UTF8')),'hex'),(length(body)+n-1)/n,n)
 returning *into d;
 return d;
end $$;
create function cp7_analysis_stage.document_segments(p_run uuid,body text,lo integer,hi integer)returns integer
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare n constant integer:=2000000;rest text;part text;i integer:=lo;
begin
 -- right(s,-k) and left(s,k) find their cut by scanning k characters;
 -- substr(s,k+1) would count every remaining character instead.
 if lo>hi then return 0;end if;
 -- right(s,-0) is '' (right(s,0)), so the first segment starts at body.
 rest:=case when lo=0 then body else right(body,-(lo*n))end;
 while i<=hi loop
  part:=left(rest,n);rest:=right(rest,-n);
  insert into cp7_analysis_jobs.segments(run_id,idx,body,utf8_bytes,sha256)
  values(p_run,i,part,octet_length(part),encode(pg_catalog.sha256(convert_to(part,'UTF8')),'hex'));
  i:=i+1;
 end loop;
 return greatest(0,hi-lo+1);
end $$;

-- One unit. Reads the stored reference and earlier outputs only.
create function cp7_analysis_stage.run_unit(j cp7_analysis_stage.jobs,u cp7_analysis_stage.units)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare c jsonb;scenario jsonb;g jsonb;out jsonb;rows jsonb;b jsonb:=cp7_analysis_stage.bounds();idx integer;n integer;e integer;
 m integer;t integer:=(b->>'targets_per_chunk')::integer;k integer;p integer;s0 jsonb;carry jsonb;plan jsonb;alloc jsonb;v jsonb;
 alloc_runs boolean;keys text[];small jsonb;wip jsonb;ek jsonb;rk jsonb;rtk jsonb;
begin
 select s.facts||'{}'::jsonb into c from cp7_analysis_stage.snapshots s where s.job_id=j.id;
 if u.kind='SCENARIO'then
  -- Stand-in: the single schedule build (history, baseline, supply, schedule).
  scenario:=cp7_schedule_native.build(c,j.query);
  insert into cp7_analysis_stage.target_rows select j.id,'BASE',x.o,x.v->>'target_key',x.v
   from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')with ordinality x(v,o);
  insert into cp7_analysis_stage.target_rows select j.id,'STOCK',x.o,x.v->>'target_key',x.v
   from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'history_run_result'->'current_stock')with ordinality x(v,o);
  insert into cp7_analysis_stage.target_rows select j.id,'HIST',x.o,x.v->>'target_key',x.v
   from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'history_run_result'->'history'->'rows')with ordinality x(v,o);
  return jsonb_build_object('scenario',scenario#-'{supply_run_result,baseline_run_result,rows}'
   #-'{supply_run_result,baseline_run_result,history_run_result,current_stock}'#-'{supply_run_result,baseline_run_result,history_run_result,history,rows}',
   'rows_null',scenario->'supply_run_result'->'baseline_run_result'->'rows'is null);
 end if;
 scenario:=cp7_analysis_stage.output(j.id,'SCENARIO')->'scenario';wip:=scenario->'wip';
 small:=jsonb_build_object('captured_at',c->'captured_at','schedule',c->'schedule');
 if u.kind='NET_PREP'then
  select case when cp7_analysis_stage.output(j.id,'SCENARIO')->'rows_null'='true'::jsonb then null else coalesce(jsonb_agg(x.payload order by x.ord),'[]')end
   into rows from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='BASE';
  -- An absent rows array stays absent (SQL NULL), as build reads it.
  g:=cp7_analysis_stage.netting_prep(c,jsonb_build_object('wip',wip,'etas',scenario->'etas','supply_run_result',
   jsonb_build_object('baseline_run_result',case when rows is null then '{}'::jsonb else jsonb_build_object('rows',rows)end)),
   (b->>'job_targets')::integer,(b->>'job_pairs')::bigint,(b->>'job_matching_products')::integer);
  -- The fixed plan.
  idx:=2;n:=coalesce(jsonb_array_length(rows),0);
  if g->'wip_complete'='true'::jsonb then
   e:=jsonb_array_length(g->'eligible');
   for k in 0..(n-1)/t loop exit when n=0;
    insert into cp7_analysis_stage.units values(j.id,idx,'NET_TARGETS',k,k*t+1,least(n,(k+1)*t));idx:=idx+1;end loop;
   if n>0 and e>0 then
    p:=greatest(1,(b->>'pairs_per_chunk')::integer/n);
    for k in 0..(e-1)/p loop
     insert into cp7_analysis_stage.units values(j.id,idx,'NET_PAIRS',k,k*p+1,least(e,(k+1)*p));idx:=idx+1;end loop;
   end if;
   insert into cp7_analysis_stage.units values(j.id,idx,'NET_PLAN',0,null,null);idx:=idx+1;
   -- Allocation runs iff build() would call allocate (its three tests in its
   -- order; a NULL schedule state is not "unreviewed" there either). NET_PLAN
   -- checks its own decision against this plan.
   alloc_runs:=not exists(select 1 from jsonb_array_elements(coalesce(rows,'[]'))x where x->'target'->>'status'is distinct from 'SCENARIO'
     or x->>'available_fg_pcs'is null or x->'production_policy'->'policy'->>'state'is null)
    and not coalesce(scenario->>'schedule_state'<>'SELECTED_ASSUMPTIONS',false)and(g->>'supplies_complete')::boolean;
   if alloc_runs then
    insert into cp7_analysis_stage.units values(j.id,idx,'ALLOC_PREP',0,null,null);idx:=idx+1;
    m:=greatest(1,least((b->>'allocation_targets_per_step')::integer,
     (b->>'visits_per_allocation_step')::integer/greatest(1,jsonb_array_length(wip->'positions'))));
    for k in 0..greatest(0,(n-1)/m) loop
     insert into cp7_analysis_stage.units values(j.id,idx,'ALLOC_STEP',k,k*m+1,least(n,(k+1)*m));idx:=idx+1;end loop;
    insert into cp7_analysis_stage.units values(j.id,idx,'ALLOC_FINAL',0,null,null);idx:=idx+1;
   end if;
   for k in 0..(n-1)/t loop exit when n=0;
    insert into cp7_analysis_stage.units values(j.id,idx,'NET_ROWS',k,k*t+1,least(n,(k+1)*t));idx:=idx+1;end loop;
  end if;
  insert into cp7_analysis_stage.units values(j.id,idx,'FABRIC_PLAN',0,null,null);idx:=idx+1;
  if g->'wip_complete'='true'::jsonb then
   for k in 0..(n-1)/t loop exit when n=0;
    insert into cp7_analysis_stage.units values(j.id,idx,'ANA_TARGETS',k,k*t+1,least(n,(k+1)*t));idx:=idx+1;end loop;
  end if;
  insert into cp7_analysis_stage.units values(j.id,idx,'ANA_META',0,null,null),(j.id,idx+1,'ANA_TEXT',0,null,null),
   (j.id,idx+2,'RUN_INSERT',0,null,null),(j.id,idx+3,'DOC_RENDER',0,null,null);idx:=idx+4;
  -- The segment count is known only once the document is rendered; a fixed
  -- number of units splits whatever count it is.
  for k in 0..(greatest(n,1)-1)/(b->>'targets_per_segment_unit')::integer loop
   insert into cp7_analysis_stage.units values(j.id,idx,'DOC_SEGMENTS',k,null,null);idx:=idx+1;end loop;
  update cp7_analysis_stage.jobs set unit_count=idx,plan_final=true,targets_total=n,
   positions_total=coalesce(jsonb_array_length(g->'eligible'),0)where id=j.id;
  return g;
 end if;
 g:=cp7_analysis_stage.output(j.id,'NET_PREP');
 if u.kind='NET_TARGETS'then
  select coalesce(jsonb_agg(x.payload order by s.o),'[]')into rows
   from jsonb_array_elements_text(g->'sorted')with ordinality s(i,o)
   join cp7_analysis_stage.target_rows x on x.job_id=j.id and x.kind='BASE'and x.ord=s.i::integer where s.o between u.lo and u.hi;
  out:=cp7_analysis_stage.netting_targets(g,small,jsonb_build_object('snapshot_id',wip->'snapshot_id'),rows);
  insert into cp7_analysis_stage.target_rows select j.id,'NET1',u.lo+x.o-1,y.v->>'target_key',x.v
   from jsonb_array_elements(out->'rows')with ordinality x(v,o) cross join lateral(select rows->(x.o::integer-1) v)y;
  return jsonb_build_object('all_known',out->'all_known');
 end if;
 if u.kind='NET_PAIRS'then
  select coalesce(jsonb_object_agg(x.i::text,x.pair_row),'{}')into v from cp7_analysis_stage.pair_rows x
   where x.job_id=j.id and x.i<u.lo and x.i in(select l::integer from jsonb_array_elements_text(g->'leaders')l);
  out:=cp7_analysis_stage.netting_pairs(g,u.lo,u.hi,v);
  insert into cp7_analysis_stage.pair_rows select j.id,u.lo+x.o-1,x.v from jsonb_array_elements(out)with ordinality x(v,o);
  -- Per target key, its results in match_results order (position, then row).
  select jsonb_agg(x->'key'order by o)into ek from jsonb_array_elements(g->'eligible')with ordinality e(x,o);
  rk:=g->'row_keys';rtk:=g->'row_target_keys';
  insert into cp7_analysis_stage.pair_lists select j.id,u.chunk,f.k,f.results from(
   select rk->>(r.j::integer-1) k,jsonb_agg(jsonb_build_object('i',u.lo+x.o::integer-1,
     'e',jsonb_build_object('position_key',ek->(u.lo+x.o::integer-2),'target_key',rtk->(r.j::integer-1),'result',r.v))order by x.o,r.j)results
   from jsonb_array_elements(out)with ordinality x(v,o)cross join lateral jsonb_array_elements(x.v)with ordinality r(v,j)
   where rk->>(r.j::integer-1)is not null group by 1)f(k,results);
  return jsonb_build_object('identity_unknown',exists(select 1 from jsonb_array_elements(out)x cross join lateral jsonb_array_elements(x)r
   where r->>'match'in('UNKNOWN','NEEDS_CHECK')),
   -- The target keys (as stored, null included) the fabric plan reads as unresolved.
   'unresolved',(select coalesce(jsonb_agg(distinct rtk->(r.j::integer-1)),'[]')from jsonb_array_elements(out)x
    cross join lateral jsonb_array_elements(x)with ordinality r(v,j)where r.v->>'match'in('UNKNOWN','NEEDS_CHECK')));
 end if;
 if u.kind='NET_PLAN'then
  plan:=cp7_analysis_stage.netting_plan(g,small,wip,scenario->>'schedule_state',
   (select coalesce(jsonb_agg(x.payload->'target' order by x.ord),'[]')from cp7_analysis_stage.target_rows x
     where x.job_id=j.id and x.kind='NET1'and x.payload->'planned'='true'::jsonb),
   not exists(select 1 from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
     where o.job_id=j.id and y.kind='NET_TARGETS'and o.output->'all_known'='false'::jsonb));
  if(jsonb_typeof(plan->'allocation_input')='object')is distinct from exists(select 1 from cp7_analysis_stage.units y where y.job_id=j.id and y.kind='ALLOC_PREP')then
   raise exception 'CP7_ANALYSIS_STAGE_PLAN_MISMATCH';end if;
  return plan||jsonb_build_object('planned_ord',(select coalesce(jsonb_object_agg(f.k,f.o),'{}')from(select x.key k,min(x.ord)o
   from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='NET1'and x.payload->'planned'='true'::jsonb and x.key is not null group by 1)f));
 end if;
 plan:=coalesce(cp7_analysis_stage.output(j.id,'NET_PLAN'),jsonb_build_object('alloc',g->'alloc'));
 if u.kind='ALLOC_PREP'then return cp7_analysis_stage.alloc_prep(plan->'allocation_input',(b->>'job_targets')::integer,(b->>'job_pairs')::bigint);end if;
 if u.kind='ALLOC_STEP'then
  s0:=cp7_analysis_stage.output(j.id,'ALLOC_PREP');
  if s0?'result'or u.lo>jsonb_array_length(s0->'ordered')then return jsonb_build_object('carry',coalesce(cp7_analysis_stage.output(j.id,'ALLOC_STEP')->'carry',s0->'carry'),
   'edges','[]'::jsonb,'rows','[]'::jsonb,'reviews','[]'::jsonb);end if;
  carry:=coalesce((select o.output->'carry'from cp7_analysis_stage.outputs o where o.job_id=j.id and o.idx=u.idx-1 and u.chunk>0),s0->'carry');
  return cp7_analysis_stage.alloc_step(s0,carry,u.lo,least(u.hi,jsonb_array_length(s0->'ordered')),(b->>'visits_per_allocation_step')::integer);
 end if;
 if u.kind='ALLOC_FINAL'then
  s0:=cp7_analysis_stage.output(j.id,'ALLOC_PREP');
  if s0?'result'then return s0->'result';end if;
  select jsonb_agg(o.output order by y.idx)into v from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
   where o.job_id=j.id and y.kind='ALLOC_STEP';
  alloc:=cp7_analysis_stage.alloc_final(plan->'allocation_input',v->-1->'carry',
   (select coalesce(jsonb_agg(x.value order by s.o,x.o),'[]')from jsonb_array_elements(v)with ordinality s(value,o)cross join lateral jsonb_array_elements(s.value->'edges')with ordinality x(value,o)),
   (select coalesce(jsonb_agg(x.value order by s.o,x.o),'[]')from jsonb_array_elements(v)with ordinality s(value,o)cross join lateral jsonb_array_elements(s.value->'rows')with ordinality x(value,o)),
   (select coalesce(jsonb_agg(x.value order by s.o,x.o),'[]')from jsonb_array_elements(v)with ordinality s(value,o)cross join lateral jsonb_array_elements(s.value->'reviews')with ordinality x(value,o)));
  return alloc-'inputs';
 end if;
 alloc:=coalesce(cp7_analysis_stage.output(j.id,'ALLOC_FINAL'),plan->'alloc');
 if u.kind='NET_ROWS'then
  select coalesce(jsonb_agg(jsonb_build_object('ord',s.o,'row',x.payload)order by s.o),'[]'),coalesce(array_agg(x.key),'{}')into rows,keys
   from jsonb_array_elements_text(g->'sorted')with ordinality s(i,o)
   join cp7_analysis_stage.target_rows x on x.job_id=j.id and x.kind='BASE'and x.ord=s.i::integer where s.o between u.lo and u.hi;
  out:=cp7_analysis_stage.netting_rows(g,small,jsonb_build_object('snapshot_id',wip->'snapshot_id'),scenario->'capacity',alloc->>'status',plan,
   plan->'planned_ord',rows,
   (select coalesce(jsonb_object_agg(x.ord::text,x.payload),'{}')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='NET1'and x.ord between u.lo and u.hi),
   (select coalesce(jsonb_object_agg(f.key,f.results),'{}')from(select x.key,jsonb_agg(r.value order by x.chunk,r.o)results
     from cp7_analysis_stage.pair_lists x cross join lateral jsonb_array_elements(x.results)with ordinality r(value,o)
     where x.job_id=j.id and x.key=any(keys)group by x.key)f),
   (select coalesce(jsonb_object_agg(f.k,f.v),'{}')from(select value->>'target_key' k,jsonb_agg(value order by o)v
     from jsonb_array_elements(coalesce(alloc->'allocation'->'edges','[]'))with ordinality a(value,o)
     where value->>'target_key'=any(keys)and value->>'match'='CANDIDATE_MATCH'group by 1)f));
  insert into cp7_analysis_stage.target_rows select j.id,'NETROW',u.lo+x.o-1,x.v->>'target_key',x.v from jsonb_array_elements(out)with ordinality x(v,o);
  -- The only row fields the fabric plan reads (DESIGN: verify on the real plan).
  insert into cp7_analysis_stage.target_rows select j.id,'FAB',u.lo+x.o-1,x.v->>'target_key',jsonb_build_object('target_key',x.v->'target_key',
   'production_policy',jsonb_build_object('policy',jsonb_build_object('state',x.v->'production_policy'->'policy'->'state')),
   'conditional_gap_pcs',x.v->'conditional_gap_pcs','net',jsonb_build_object('inputs',jsonb_build_object('deadline',x.v->'net'->'inputs'->'deadline')))
   from jsonb_array_elements(out)with ordinality x(v,o);
  return jsonb_build_object('rows',jsonb_array_length(out));
 end if;
 if u.kind='FABRIC_PLAN'then
  -- Global: the fabric plan reads every netting row and match result.
  return jsonb_build_object('plan',cp7_fabric_native.plan(c,jsonb_build_object(
   'rows',(select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='FAB'),
   'match_results',(select coalesce(jsonb_agg(jsonb_build_object('target_key',k.value,'result',jsonb_build_object('match','UNKNOWN'))),'[]')
     from(select distinct k.value from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
      cross join lateral jsonb_array_elements(o.output->'unresolved')k where o.job_id=j.id and y.kind='NET_PAIRS')k))));
 end if;
 if u.kind='ANA_TARGETS'then
  select coalesce(jsonb_agg(x.payload order by x.ord),'[]'),coalesce(array_agg(x.key),'{}')into rows,keys
   from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='NETROW'and x.ord between u.lo and u.hi;
  out:=cp7_analysis_stage.analysis_targets(c,rows,
   (select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)from(select x->>'root_id'k,jsonb_agg(x)items from jsonb_array_elements(c->'facts'->'products')x
     where x->>'root_id'=any(select split_part(y,':',1)from unnest(keys)y)group by x->>'root_id')i),
   (select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)from(select x.key k,jsonb_agg(x.payload order by x.ord)items from cp7_analysis_stage.target_rows x
     where x.job_id=j.id and x.kind='STOCK'and x.key=any(keys)group by x.key)i),
   (select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)from(select x.key k,jsonb_agg(x.payload order by x.ord)items from cp7_analysis_stage.target_rows x
     where x.job_id=j.id and x.kind='HIST'and x.key=any(keys)group by x.key)i),
   (select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)from(select x->>'target_key'k,jsonb_agg(x order by o)items
     from jsonb_array_elements(coalesce(alloc->'allocation'->'edges','[]'))with ordinality e(x,o)where x->>'target_key'=any(keys)group by x->>'target_key')i),
   (select coalesce(jsonb_object_agg(f.key,f.results),'{}')from(select x.key,jsonb_agg(r.value->'e' order by x.chunk,r.o)results
     from cp7_analysis_stage.pair_lists x cross join lateral jsonb_array_elements(x.results)with ordinality r(value,o)
     where x.job_id=j.id and x.key=any(keys)group by x.key)f),
   case when c->'schedule'<>'null'::jsonb then jsonb_build_array(c->'schedule'->>'plan_id')else '[]'::jsonb end,
   cp7_analysis_stage.output(j.id,'FABRIC_PLAN')->'plan');
  insert into cp7_analysis_stage.fragments select j.id,u.idx,f.field,coalesce(substr(t.body,2,length(t.body)-2),''),jsonb_array_length(out->f.field)
   from unnest(cp7_analysis_stage.fragment_fields())f(field)cross join lateral(select(out->f.field)::text body)t where jsonb_typeof(out->f.field)='array';
  return jsonb_build_object('known_keys',out->'known_keys','demand_unknown',out->'demand_unknown','materials_null',out->'materials_null',
   'counts',(select jsonb_object_agg(f.field,coalesce(jsonb_array_length(out->f.field),0))from unnest(cp7_analysis_stage.fragment_fields())f(field)
     where jsonb_typeof(out->f.field)='array'));
 end if;
 if u.kind='ANA_META'then
  return jsonb_build_object('skeleton',cp7_analysis_stage.analysis_skeleton(c,j.query,j.run_id,j.access_at_capture,scenario,alloc,g->'matching',
   jsonb_build_object(
    'known_keys',(select coalesce(jsonb_agg(k.value order by y.idx,k.o),'[]')from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
      cross join lateral jsonb_array_elements(o.output->'known_keys')with ordinality k(value,o)where o.job_id=j.id and y.kind='ANA_TARGETS'),
    'demand_unknown',exists(select 1 from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
      where o.job_id=j.id and y.kind='ANA_TARGETS'and o.output->'demand_unknown'='true'::jsonb),
    'materials_null',exists(select 1 from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
      where o.job_id=j.id and y.kind='ANA_TARGETS'and o.output->'materials_null'='true'::jsonb),
    'counts',(select coalesce(jsonb_object_agg(f.field,f.n),'{}')from(select x.field,sum(x.items)n from cp7_analysis_stage.fragments x where x.job_id=j.id group by 1)f)),
   exists(select 1 from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
     where o.job_id=j.id and y.kind='NET_PAIRS'and o.output->'identity_unknown'='true'::jsonb),cp7_analysis_stage.tag(j.id)));
 end if;
 if u.kind='ANA_TEXT'then
  -- The analysis text: the skeleton's canonical text with each sentinel
  -- replaced by every chunk's items, then build's semantic hash of it.
  declare skel jsonb:=cp7_analysis_stage.output(j.id,'ANA_META')->'skeleton';s0 text;s1 text;f text;frag text;hash text;tag text:=cp7_analysis_stage.tag(j.id);
  begin
   s0:=skel::text;s1:=(skel||jsonb_build_object('semantic_hash',tag||'hash'))::text;
   foreach f in array cp7_analysis_stage.fragment_fields()loop
    select string_agg(x.body,', 'order by x.idx)into frag from cp7_analysis_stage.fragments x where x.job_id=j.id and x.field=f and x.items>0;
    if frag is not null then s0:=replace(s0,'"'||tag||f||'"',frag);s1:=replace(s1,'"'||tag||f||'"',frag);end if;
   end loop;
   hash:=encode(extensions.digest(convert_to(s0,'UTF8'),'sha256'),'hex');
   s1:=replace(s1,'"'||tag||'hash"','"'||hash||'"');
   insert into cp7_analysis_stage.texts values(j.id,'ANALYSIS',s1,encode(extensions.digest(convert_to(s1,'UTF8'),'sha256'),'hex'));
   return jsonb_build_object('semantic_hash',hash,'utf8_bytes',octet_length(s1));
  end;
 end if;
 if u.kind='RUN_INSERT'then
  insert into cp7_analysis_native.runs(id,actor,request_id,query,captured_at,access_at_capture,facts,result,dependency_hash)
  select j.run_id,j.actor,j.request_id,j.query,j.captured_at,j.access_at_capture,c,t.body::jsonb,j.source_hash
  from cp7_analysis_stage.texts t where t.job_id=j.id and t.kind='ANALYSIS';
  return jsonb_build_object('run_id',j.run_id);
 end if;
 if u.kind='DOC_RENDER'then
  -- The Original exactly as cp7_analysis_jobs.original() renders the run,
  -- from the analysis text (no 60+ MB jsonb rendering).
  declare tag text:=cp7_analysis_stage.tag(j.id);body text;
  begin
   select replace(cp7_analysis_jobs.original(row(j.run_id,j.actor,j.request_id,j.query,j.captured_at,j.access_at_capture,c,
     to_jsonb(tag||'analysis'),j.source_hash)::cp7_analysis_native.runs)::text,'"'||tag||'analysis"',t.body)into body
    from cp7_analysis_stage.texts t where t.job_id=j.id and t.kind='ANALYSIS';
   insert into cp7_analysis_stage.texts values(j.id,'DOCUMENT',body,encode(pg_catalog.sha256(convert_to(body,'UTF8')),'hex'));
   return to_jsonb(cp7_analysis_stage.document_row(j.run_id,body));
  end;
 end if;
 if u.kind='DOC_SEGMENTS'then
  declare d cp7_analysis_jobs.documents%rowtype;units integer;first integer;last integer;
  begin
   select *into d from cp7_analysis_jobs.documents where run_id=j.run_id;
   select count(*)into units from cp7_analysis_stage.units y where y.job_id=j.id and y.kind='DOC_SEGMENTS';
   first:=(u.chunk*d.segment_count)/units;last:=((u.chunk+1)*d.segment_count)/units-1;
   return jsonb_build_object('segments',cp7_analysis_stage.document_segments(j.run_id,
    (select t.body from cp7_analysis_stage.texts t where t.job_id=j.id and t.kind='DOCUMENT'),first,last),'first',first,'last',last);
  end;
 end if;
 raise exception 'CP7_ANALYSIS_STAGE_UNKNOWN_UNIT';
end $$;

-- One ordinary request: run the job's next unit, persist it, report progress.
-- A concurrent caller does not wait (skip locked) and only reads the status.
-- The statement limit stopping a unit is retried by the next call (inputs are
-- immutable, so a retry computes the same unit); three stops fail the job.
-- Any other refusal fails the job with its code: the reference is fixed, so a
-- retry would refuse the same way.
create function cp7_analysis_stage.step(p_job uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare j cp7_analysis_stage.jobs%rowtype;u cp7_analysis_stage.units%rowtype;out jsonb;t0 timestamptz;
begin
 select *into j from cp7_analysis_stage.jobs where id=p_job for update skip locked;
 if not found then
  if not exists(select 1 from cp7_analysis_stage.jobs where id=p_job)then raise exception 'CP7_ANALYSIS_JOB_UNAVAILABLE';end if;
  return cp7_analysis_stage.status(p_job)||jsonb_build_object('worker_active',true);
 end if;
 if j.state<>'RUNNING'then return cp7_analysis_stage.status(p_job);end if;
 select *into u from cp7_analysis_stage.units where job_id=j.id and idx=j.units_done;
 begin
  t0:=clock_timestamp();
  out:=cp7_analysis_stage.run_unit(j,u);
  insert into cp7_analysis_stage.outputs values(j.id,u.idx,out,round(extract(epoch from clock_timestamp()-t0)*1000,1),clock_timestamp());
  update cp7_analysis_stage.jobs set units_done=units_done+1,unit_attempts=0,updated_at=clock_timestamp(),
   state=case when plan_final and units_done+1=unit_count then 'DONE'else 'RUNNING'end where id=j.id;
 exception
  when query_canceled then
   update cp7_analysis_stage.jobs set unit_attempts=unit_attempts+1,updated_at=clock_timestamp(),
    state=case when unit_attempts+1>=3 then 'FAILED'else state end,
    failure_unit=case when unit_attempts+1>=3 then u.idx end,failure_sqlstate=case when unit_attempts+1>=3 then SQLSTATE end,
    failure_code=case when unit_attempts+1>=3 then 'CP7_ANALYSIS_STAGE_STOPPED'end where id=j.id;
  when others then
   update cp7_analysis_stage.jobs set state='FAILED',updated_at=clock_timestamp(),failure_unit=u.idx,failure_sqlstate=SQLSTATE,
    failure_code=case when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM else 'CP7_ANALYSIS_STAGE_ERROR'end where id=j.id;
 end;
 return cp7_analysis_stage.status(p_job);
end $$;
