create or replace function cp7_netting_native.build(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare scenario jsonb;wip jsonb;matching jsonb;models jsonb;p jsonb;t jsonb;m jsonb;s jsonb;tf jsonb;eta jsonb;
 r jsonb;cfg jsonb;line jsonb;alloc jsonb;edges jsonb:='[]';etas jsonb;targets jsonb;
 matches jsonb;hash text;policy text;ready timestamptz;model text;compatible jsonb;
 deadline timestamptz;helps timestamptz;raw_need numeric;directed numeric;candidate numeric;gap numeric;
 budget numeric:=0;all_targets_known boolean:=true;supplies_complete boolean:=true;refs jsonb;production_status text;
 supplies jsonb;net jsonb;raw_net jsonb;directed_edges jsonb;line_edges jsonb;
 eta_list jsonb[]:='{}';target_list jsonb[]:='{}';review_list jsonb[]:='{}';row_list jsonb[]:='{}';
 baseline_lines jsonb[]:='{}';baseline_rows text[]:='{}';planned_index jsonb;
 pair_rows jsonb[]:='{}';eligible jsonb[]:='{}';open_work jsonb[];open_index integer[];supply_list jsonb[];edge_list jsonb[];
 row_keys text[];row_target_keys jsonb[];row_at jsonb;model_targets jsonb;candidates jsonb;leaders integer[];
 eta_at jsonb;eta_repeated jsonb;source_at jsonb;source_repeated jsonb;target_at jsonb;target_repeated jsonb;
 planned_at jsonb;planned_repeated jsonb;i integer;j integer;n integer;first_repeated integer;
 unknown_model jsonb:=jsonb_build_object('match','UNKNOWN','reasons',jsonb_build_array('NATIVE_SOURCE_MODEL_UNPROVEN'));
 model_mismatch jsonb:=jsonb_build_object('match','INCOMPATIBLE','reasons',jsonb_build_array('NATIVE_MODEL_MISMATCH'));
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
 m:=cp7_netting_native.matching_models(c,wip);matching:=m->'matching';models:=m->'models';
 for eta in select value from jsonb_array_elements(scenario->'etas')loop
  eta_list:=array_append(eta_list,jsonb_build_object('position_key',eta->'position_key',
   'at',case when eta->'result'->>'status'in('KNOWN','CONDITIONAL')then cp7_planning.utc((eta->'result'->>'eta')::timestamptz)else null end,
   'refs',eta->'refs'));
 end loop;
 etas:=to_jsonb(eta_list);
 -- Every per-row scan of an array this function composed (ETAs, matching
 -- sources/targets, its own targets) is one map of that array. A key held
 -- twice refuses where the scalar subquery over that array refused; a single
 -- key reads the same element. Composed arrays cannot fail to unnest.
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into eta_at,eta_repeated
  from(select value->>'position_key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(etas)
   where value->>'position_key'is not null group by 1)f;
 -- Existing work is timed in one shared queue. Its projected supply budget is
 -- separate from AFTER-existing-work free capacity for new starts.
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
 for r in select value from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')order by value->>'target_key'loop
  cfg:=r->'profile'->'config';policy:=r->'production_policy'->'policy'->>'state';
  if r->'target'->>'status'is distinct from 'SCENARIO'or r->>'available_fg_pcs'is null then
   all_targets_known:=false;review_list:=array_append(review_list,jsonb_build_object('target_key',r->'target_key','reason','DEMAND_TARGET_STOCK_OR_PRODUCTION_POLICY_UNREVIEWED'));continue;end if;
  if policy is null then all_targets_known:=false;review_list:=array_append(review_list,jsonb_build_object('target_key',r->'target_key','reason','PRODUCTION_POLICY_UNREVIEWED'));end if;
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
  target_list:=array_append(target_list,jsonb_build_object('key',r->'target_key','size_id',r->'size_id',
   'need_pcs',raw_need::text,'deadline',cp7_planning.utc(deadline),
   'risk_at',coalesce(line->'first_known_gap'->'at',to_jsonb(cp7_planning.utc(deadline))),
   'helps_at',cp7_planning.utc(helps),'production_status',production_status,'refs',refs));
  baseline_lines:=array_append(baseline_lines,line);baseline_rows:=array_append(baseline_rows,r::text);
 end loop;
 targets:=to_jsonb(target_list);
 -- Model is an additional Native hard constraint absent from the retained
 -- five-field pure matcher. A source with a Native product binding can only
 -- match that root; unbound critical brand/color remains NEEDS_CHECK.
 -- Evaluate each immutable pair once, in matches() order: eligible positions
 -- outer, targets inner, each in array order. Per position the source and its
 -- model, per target the matching target are read once; a pair keeps only
 -- the model test and the five-field match. A target key repeated among the
 -- matching targets refuses at its first row, after the rows before it.
 -- Results are kept per position in target order; the index never enters
 -- the returned contract.
 select coalesce(array_agg(value->>'target_key' order by o),'{}'),coalesce(array_agg(value->'target_key' order by o),'{}')into row_keys,row_target_keys
  from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')with ordinality a(value,o);
 n:=cardinality(row_keys);
 select coalesce(min(u.j),n+1)into first_repeated from unnest(row_keys)with ordinality u(k,j)where target_repeated?u.k;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into source_at,source_repeated
  from(select value->>'key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(matching->'sources')
   where value->>'key'is not null group by 1)f;
 select coalesce(jsonb_object_agg(f.m,f.ks),'{}')into model_targets
  from(select x->>'model_id' m,jsonb_object_agg((x->>'root_id')||':'||(x->>'size_id'),true)ks from jsonb_array_elements(c->'facts'->'products')x
   where x->>'model_id'is not null and(x->>'root_id')||':'||(x->>'size_id')is not null group by 1)f;
 -- cp7_wip.match_target checks the source and the target independently, and
 -- its verdict reads only the source's quality, size, confirmed target and
 -- constraints. A position with the same source facts and model as an earlier
 -- one (its leader) therefore has the leader's verdicts once one call of its
 -- own has proven its source; that call refuses as its first pair would.
 select coalesce(array_agg(f.leader order by f.i),'{}')into leaders
  from(select g.i,case when g.facts is null then g.i else min(g.i)over(partition by g.facts)end leader
   from(select e.i,case when e.s is not null and e.model is not null then
      jsonb_build_array(e.s->'quality',e.s->'size_id',e.s->'confirmed_target',e.s->'constraints',e.model)::text end facts
     from(select x.i,source_at->(x.p->>'key') s,models->>(x.p::text) model from unnest(eligible)with ordinality x(p,i))e)g)f;
 i:=0;
 foreach p in array eligible loop
  exit when n=0;
  i:=i+1;
  if source_repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  s:=source_at->(p->>'key');model:=models->>(p::text);compatible:=model_targets->model;
  if leaders[i]<i then
   select min(u.j)into j from unnest(row_keys)with ordinality u(k,j)where coalesce(compatible?u.k,false);
   if j is not null then m:=cp7_wip.match_target(s,target_at->row_keys[j]);end if;
   pair_rows:=array_append(pair_rows,pair_rows[leaders[i]]);
  else
   select coalesce(jsonb_agg(case when model is null then unknown_model when not coalesce(compatible?u.k,false)then model_mismatch
     else cp7_wip.match_target(s,target_at->u.k)end order by u.j),'[]')into m
    from unnest(row_keys)with ordinality u(k,j)where u.j<first_repeated;
   pair_rows:=array_append(pair_rows,m);
   if first_repeated<=n then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  end if;
 end loop;
 select coalesce(jsonb_agg(jsonb_build_object('position_key',e.p->'key','target_key',k.tk,'result',x.m)order by e.i,x.j),'[]')into matches
  from unnest(eligible,pair_rows)with ordinality e(p,pr,i)
  cross join lateral jsonb_array_elements(e.pr)with ordinality x(m,j)
  join unnest(row_target_keys)with ordinality k(tk,j)on k.j=x.j;
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
 select coalesce(jsonb_object_agg(f.k,f.v),'{}')into candidates
  from(select value->>'target_key' k,jsonb_agg(value order by o)v from jsonb_array_elements(edges)with ordinality a(value,o)
   where value->>'target_key'is not null and value->>'match'='CANDIDATE_MATCH'group by 1)f;
 select coalesce(jsonb_object_agg(f.k,f.j),'{}')into row_at
  from(select u.k,min(u.j)j from unnest(row_keys)with ordinality u(k,j)where u.k is not null group by 1)f;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}'),
  coalesce(jsonb_object_agg(f.k,f.j),'{}')into planned_at,planned_repeated,planned_index
  from(select value->>'key' k,count(*)n,(array_agg(value))[1] v,min(o)j from jsonb_array_elements(targets)with ordinality a(value,o)
   where value->>'key'is not null group by 1)f;
 for r in select value from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')order by value->>'target_key'loop
  directed:=0;candidate:=0;raw_need:=null;gap:=null;supplies:='[]';directed_edges:='[]';net:=null;
  if planned_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  t:=planned_at->(r->>'target_key');
  if t is not null then
   raw_need:=cp7_wip.pcs(t->'need_pcs');
   -- A fully emptied position stays in the graph as evidence; it is no supply
   -- (the budget loop above skips it too) and must not make the target UNKNOWN.
   -- The open eligible positions are the same for every target: they are
   -- read once, at the first target that reads them, in array order.
   if open_work is null then
    open_work:='{}';open_index:='{}';i:=0;
    foreach p in array eligible loop
     i:=i+1;
     if cp7_wip.pcs(p->'remaining_pcs')>0 then open_work:=array_append(open_work,p);open_index:=array_append(open_index,i);end if;
    end loop;
   end if;
   -- A pair result depends on the target only through its key.
   j:=(row_at->>(r->>'target_key'))::integer;supply_list:='{}';edge_list:='{}';i:=0;
   foreach p in array open_work loop
    i:=i+1;m:=pair_rows[open_index[i]]->(j-1);
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
  -- The timeline reads only this target's edges, in the same order.
  if t is null then line:=jsonb_build_object('status','UNKNOWN','reason','TARGET_NEEDS_OR_POLICY_UNREVIEWED');
  else
   line_edges:=directed_edges||coalesce(candidates->(r->>'target_key'),'[]'::jsonb);
   -- With no supply edges all six immutable arguments equal the first call.
   -- Reuse only that invocation's result; no persisted cache or guard removal.
   -- planned_repeated above rejects duplicate planned keys, but a row skipped
   -- before planning can share its key with a planned one: reuse only when
   -- this is the very row the first call read (same jsonb text).
   if line_edges='[]'::jsonb and baseline_rows[(planned_index->>(r->>'target_key'))::integer]=r::text then
    line:=baseline_lines[(planned_index->>(r->>'target_key'))::integer];
   else line:=cp7_netting_native.timeline(c,r,etas,line_edges,matching,wip);end if;
  end if;
  row_list:=array_append(row_list,r||jsonb_build_object('raw_gap_pcs',raw_need::text,'directed_on_time_good_pcs',net->'directed_on_time_pcs',
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
  'schedule_run_result',scenario,'matching',matching,'match_results',matches,'rows',to_jsonb(row_list),'allocation',alloc,
  'review_queue',to_jsonb(review_list),'existing_timed_projected_good_budget_pcs',budget::text,
  'new_start_capacity',scenario->'capacity','material_state','UNKNOWN','apply_enabled',false,'production_go',false);
end $$;
