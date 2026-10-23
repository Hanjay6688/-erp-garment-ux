-- OW10 private pure projection. No Native reads, DML, allocations or public RPC.
-- Caller/source/cache integration is a separate, still-open stage.
create schema cp7_reorder_supply authorization cp7_capture;
revoke all on schema cp7_reorder_supply from public,anon,authenticated,service_role;

create function cp7_reorder_supply.project(v jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare b jsonb;r jsonb;s jsonb;k text;budgets jsonb;seen jsonb:='{}';results jsonb[]:='{}';
 net jsonb;why text;captured timestamptz;checked timestamptz;lo date;hi date;q jsonb;
 entries integer:=0;total numeric;source_limit numeric;conflict record;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','scenario_id','captured_at','checked_at',
  'source_hash','current_source_hash','source_state','complete_scope','wip_status','allocation_status','query','expected_query','budgets','targets','refs']);
 perform cp7_demand.context(v,'cp7.reorder-supply-input.v1');perform cp7_wip.key(v->'scenario_id');perform cp7_wip.refs(v->'refs');
 captured:=cp7_demand.instant(v->'captured_at');checked:=cp7_demand.instant(v->'checked_at');
 if checked<captured or v->>'scope_id'<>'GLOBAL_NATIVE_PLANNING'
  or jsonb_typeof(v->'complete_scope')is distinct from'boolean'
  or v->>'source_state'is null or v->>'source_state'not in('CURRENT','ARCHIVED_STALE','UNKNOWN')
  or v->>'wip_status'is null or v->>'wip_status'not in('COMPLETE','UNKNOWN')
  or v->>'allocation_status'is null or v->>'allocation_status'not in('SCENARIO','UNKNOWN')then raise exception 'CP7_REORDER_SUPPLY_CONTEXT';end if;
 foreach k in array array['source_hash','current_source_hash']loop
  if jsonb_typeof(v->k)is distinct from'string'or v->>k!~'^[0-9a-f]{64}$'then raise exception 'CP7_REORDER_SUPPLY_HASH';end if;
 end loop;
 foreach k in array array['query','expected_query']loop
  q:=v->k;perform cp7_wip.fields(q,array['from_date','through_date','group_mode']);
  lo:=cp7_demand.day(q->'from_date');hi:=cp7_demand.day(q->'through_date');
  if hi<lo or hi-lo>3660 or hi>=(case when k='query'then captured else checked end at time zone'Asia/Jakarta')::date
   or q->>'group_mode'is null or q->>'group_mode'not in('AS_SOLD','RESTATED')then raise exception 'CP7_REORDER_SUPPLY_QUERY';end if;
 end loop;
 perform cp7_demand.items(v->'budgets',1000);perform cp7_demand.items(v->'targets',5000);
 for b in select value from jsonb_array_elements(v->'budgets')loop
  perform cp7_wip.fields(b,array['physical_key','snapshot_id','size_id','projected_good_pcs','eta','eligible']);
  perform cp7_wip.key(b->'physical_key');perform cp7_wip.key(b->'size_id');
  if b->>'snapshot_id'is distinct from v->>'snapshot_id'or jsonb_typeof(b->'eligible')is distinct from'boolean'then raise exception 'CP7_REORDER_BUDGET_BINDING';end if;
  if b->'projected_good_pcs'<>'null'::jsonb then perform cp7_wip.pcs(b->'projected_good_pcs');end if;
  if b->'eta'<>'null'::jsonb then perform cp7_demand.instant(b->'eta');end if;
 end loop;
 if(select count(*)from jsonb_array_elements(v->'budgets'))<>(select count(distinct x->>'physical_key')from jsonb_array_elements(v->'budgets')x)then
  raise exception 'CP7_REORDER_DUPLICATE_BUDGET';end if;
 select coalesce(jsonb_object_agg(x->>'physical_key',x),'{}'::jsonb)into budgets from jsonb_array_elements(v->'budgets')x;
 why:=case when v->'complete_scope'<>'true'::jsonb then'GLOBAL_SCOPE_INCOMPLETE'
  when v->>'wip_status'<>'COMPLETE'then'GLOBAL_WIP_INCOMPLETE'
  when v->>'source_state'<>'CURRENT'or v->>'source_hash'<>v->>'current_source_hash'then'GLOBAL_SOURCE_CHANGED'
  when v->'query'<>v->'expected_query'then'DEMAND_PERIOD_OR_GROUPING_CHANGED'end;
 for r in select value from jsonb_array_elements(v->'targets')loop
  perform cp7_wip.fields(r,array['target_key','size_id','reorder_point_pcs','target_pcs','available_fg_pcs','lead_deadline','deadline','supplies','refs']);
  k:=cp7_wip.key(r->'target_key');perform cp7_wip.key(r->'size_id');perform cp7_wip.refs(r->'refs');
  if seen?k then raise exception 'CP7_REORDER_DUPLICATE_TARGET';end if;seen:=seen||jsonb_build_object(k,true);
  if r->'reorder_point_pcs'<>'null'::jsonb then perform cp7_wip.pcs(r->'reorder_point_pcs');end if;
  if r->'target_pcs'<>'null'::jsonb then perform cp7_wip.pcs(r->'target_pcs');end if;
  if r->'available_fg_pcs'<>'null'::jsonb and(jsonb_typeof(r->'available_fg_pcs')is distinct from'string'
    or r->>'available_fg_pcs'!~'^-?(0|[1-9][0-9]{0,29})$')then raise exception 'CP7_REORDER_AVAILABLE_FG';end if;
  if r->'lead_deadline'<>'null'::jsonb and cp7_demand.instant(r->'lead_deadline')<captured then raise exception 'CP7_REORDER_LEAD_BEFORE_CAPTURE';end if;
  if r->'deadline'<>'null'::jsonb then perform cp7_demand.instant(r->'deadline');end if;
  if r->'supplies'<>'null'::jsonb then perform cp7_demand.items(r->'supplies',10000);entries:=entries+jsonb_array_length(r->'supplies');end if;
  if entries>10000 then raise exception 'CP7_REORDER_GLOBAL_SUPPLY_LIMIT';end if;
  for s in select value from jsonb_array_elements(case when r->'supplies'='null'::jsonb then'[]'::jsonb else r->'supplies'end)loop
   perform cp7_wip.fields(s,array['physical_key','snapshot_id','target_key','size_id','kind','qty_pcs','eta','eligible','refs']);
   perform cp7_wip.key(s->'physical_key');perform cp7_wip.refs(s->'refs');
   if s->>'kind'is null or s->>'kind'not in('DIRECTED','ALLOCATED_CANDIDATE')then raise exception 'CP7_REORDER_WIP_KIND';end if;
   if s->>'snapshot_id'is distinct from v->>'snapshot_id'or s->>'target_key'is distinct from k
    or s->>'size_id'is distinct from r->>'size_id'or jsonb_typeof(s->'eligible')is distinct from'boolean'then raise exception 'CP7_REORDER_SUPPLY_BINDING';end if;
   if s->'qty_pcs'<>'null'::jsonb then perform cp7_wip.pcs(s->'qty_pcs');end if;
   if s->'eta'<>'null'::jsonb then perform cp7_demand.instant(s->'eta');end if;
   b:=budgets->(s->>'physical_key');
   if b is null or b->>'size_id'is distinct from s->>'size_id'or b->'eta'is distinct from s->'eta'
    or(s->'eligible'='true'::jsonb and b->'eligible'<>'true'::jsonb)then raise exception 'CP7_REORDER_POSITION_BINDING';end if;
   if s->'eligible'='true'::jsonb and s->'qty_pcs'<>'null'::jsonb and b->'projected_good_pcs'='null'::jsonb then raise exception 'CP7_REORDER_BUDGET_UNKNOWN_CREDIT';end if;
   if s->>'kind'='ALLOCATED_CANDIDATE'and v->>'allocation_status'<>'SCENARIO'then raise exception 'CP7_REORDER_UNPROVEN_ALLOCATION';end if;
  end loop;
  net:=null;
  if r->'supplies'='null'::jsonb then
   -- Native leaves this null when matching/netting was not computed. It is
   -- not an empty list and is never passed to netting as zero supply.
   net:=null;
  elsif r->'deadline'='null'::jsonb or r->'lead_deadline'='null'::jsonb then
   if r->'supplies'<>'[]'::jsonb then raise exception 'CP7_REORDER_TARGET_HORIZON_UNKNOWN_SUPPLY';end if;
  else
   -- Exactly the same kernel/one conserved supplies list for L and L+R.
   net:=cp7_baseline.net(jsonb_build_object('contract_version','cp7.net-input.v2','snapshot_id',v->'snapshot_id',
    'scope_id',v->'scope_id','scenario_id',v->'scenario_id','target_key',r->'target_key','size_id',r->'size_id',
    'deadline',r->'deadline','lead_deadline',r->'lead_deadline','reorder_point_pcs',r->'reorder_point_pcs',
    'target_pcs',r->'target_pcs','available_fg_pcs',r->'available_fg_pcs','supplies',r->'supplies','refs',r->'refs'));
   if v->>'allocation_status'='UNKNOWN'then
    -- No allocation proof is not a proven zero candidate quantity. The
    -- directed base stays usable; all conditional facts stay unknown.
    net:=net||jsonb_build_object('q_conditional_pcs',null,'candidate_on_time_pcs',null,
     'lead_position_conditional_pcs',null,'conditional_reorder_state','UNKNOWN',
     'lead_net',net->'lead_net'||jsonb_build_object('q_conditional_pcs',null,'candidate_on_time_pcs',null));
   end if;
  end if;
  results:=array_append(results,jsonb_build_object('target_key',r->'target_key','size_id',r->'size_id',
   'status',case when why is not null or net is null then'UNKNOWN'else net->>'status'end,
   'reason',coalesce(why,case when r->'supplies'='null'::jsonb then'TARGET_SUPPLY_UNKNOWN'
     when net is null then'TARGET_HORIZON_UNKNOWN'else net->>'reason'end),
   'net',case when why is null then net end));
 end loop;
 -- Exact duplicates are idempotent per target, as in net(). A conflicting
 -- duplicate, multiple DIRECTED targets or mixed DIRECTED/candidate is refused.
 for conflict in
  with entries as(select rt.target->>'target_key'target_key,st.supply from jsonb_array_elements(v->'targets')rt(target)
   cross join lateral jsonb_array_elements(case when rt.target->'supplies'='null'::jsonb then'[]'::jsonb else rt.target->'supplies'end)st(supply)),
  unique_entries as(select distinct e.target_key,e.supply from entries e)
  select u.supply->>'physical_key'physical_key,count(distinct u.target_key)targets,count(distinct u.supply->>'kind')kinds,
   bool_or(u.supply->>'kind'='DIRECTED')directed,sum(case when u.supply->'eligible'='true'::jsonb then(u.supply->>'qty_pcs')::numeric else 0 end)used,
   count(*)n,count(distinct target_key)n_targets
  from unique_entries u group by u.supply->>'physical_key'
 loop
  b:=budgets->conflict.physical_key;
  if conflict.n<>conflict.n_targets or(conflict.directed and(conflict.targets<>1 or conflict.kinds<>1))then raise exception 'CP7_REORDER_PHYSICAL_SOURCE_CONFLICT';end if;
  source_limit:=(b->>'projected_good_pcs')::numeric;total:=conflict.used;
  if total>source_limit then raise exception 'CP7_REORDER_GLOBAL_BUDGET_EXCEEDED';end if;
 end loop;
 return jsonb_build_object('contract_version','cp7.reorder-supply.v1','snapshot_id',v->'snapshot_id','scope_id',v->'scope_id',
  'captured_at',v->'captured_at','checked_at',v->'checked_at','query',v->'query','source_hash',v->'source_hash',
  'status',case when why is not null or exists(select 1 from unnest(results)x where x->>'status'<>'SCENARIO')then'UNKNOWN'
    when v->>'allocation_status'='UNKNOWN'then'PARTIAL'else'SCENARIO'end,
  'reason',coalesce(why,case when v->>'allocation_status'='UNKNOWN'then'GLOBAL_CANDIDATE_ALLOCATION_UNKNOWN'end),
  'allocation_status',v->'allocation_status','rows',to_jsonb(results),
  'basis','SAME_GLOBAL_ALLOCATION_PROJECTED_GOOD_UNIQUE_PHYSICAL_SIZE_TWO_HORIZONS','apply_enabled',false,'production_go',false);
end $$;
alter function cp7_reorder_supply.project(jsonb)owner to cp7_capture;
revoke all on function cp7_reorder_supply.project(jsonb)from public,anon,authenticated,service_role;
