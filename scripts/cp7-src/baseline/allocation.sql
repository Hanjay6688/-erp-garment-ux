-- Deterministic simulation over ONE complete scope. Not a reservation/optimizer.
-- Source ETA comes from the pinned P04 dated-work kernel; unknown ETA is reviewed.
-- P19: linear in positions and targets with the same bytes and first refusal.
-- Each input array is checked in the same order with the same calls; a key
-- seen before refuses at its first repeat, as the growing set did. Lookups
-- read key maps, and lists are built with array_append (not jsonb ||).
create function cp7_baseline.allocate(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare t jsonb;p jsonb;s jsonb;tf jsonb;m jsonb;e jsonb;proj jsonb;pool jsonb;eta jsonb;k text;pk text;
 validation jsonb;capacity numeric;need numeric;left_need numeric;room numeric;good numeric;input_qty numeric;num numeric;den numeric;refs jsonb;
 i integer;o integer;w integer;slot integer;repeated integer;sources_n integer;targets_n integer;target_id integer;target_proven boolean;deadline timestamptz;
 pool_at jsonb;position_at jsonb;eta_at jsonb;source_at jsonb;target_at jsonb;target_ids jsonb;size_lists jsonb;
 pool_wip numeric[]:='{}';pool_used numeric[];position_keys text[]:='{}';position_pools integer[]:='{}';remaining numeric[]:='{}';
 eligible_input numeric[]:='{}';projected_good numeric[]:='{}';numerators numeric[]:='{}';denominators numeric[]:='{}';
 used numeric[];good_used numeric[];reviewed boolean[];eta_times timestamptz[];source_ids integer[];source_confirmed text[];proven boolean[];verdicts jsonb[];
 edge_list jsonb[]:='{}';row_list jsonb[]:='{}';review_list jsonb[]:='{}';
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
 -- FEASIBLE proves the matching sources and targets are arrays of objects
 -- with distinct string keys: a key map reads the element each scan found.
 perform cp7_demand.items(v->'positions'->'positions',1000);perform cp7_demand.items(v->'positions'->'totals',1000);
 perform cp7_demand.items(v->'targets',1000);perform cp7_demand.items(v->'etas',1000);
 if jsonb_array_length(v->'positions'->'positions')*jsonb_array_length(v->'targets')>100000 then raise exception 'CP7_BASELINE_ALLOCATION_LIMIT';end if;
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
 for t in select value from jsonb_array_elements(v->'targets') order by
  case when value->'risk_at'<>'null'::jsonb then cp7_demand.instant(value->'risk_at') end nulls last,
  case when value->'deadline'<>'null'::jsonb then cp7_demand.instant(value->'deadline') end nulls last,
  case when value->'helps_at'<>'null'::jsonb then cp7_demand.instant(value->'helps_at') end nulls last,
  cp7_wip.pcs(value->'need_pcs') desc,value->>'key' loop
  need:=cp7_wip.pcs(t->'need_pcs');left_need:=need;
  if t->'deadline'='null'::jsonb or t->'risk_at'='null'::jsonb or t->'helps_at'='null'::jsonb then
   review_list:=array_append(review_list,jsonb_build_object('target_key',t->'key','reason','TIME_UNKNOWN','need_pcs',need::text));continue;end if;
  if t->>'production_status'='ACTIVE' then
   tf:=target_at->(t->>'key');
   if size_lists is null then
    -- The positions in the per-target order (ETA nulls last, then key) are
    -- the same for every target: sorted once, and per size only the eligible
    -- ones, the only ones a target can act on.
    with x as(select a.o::integer o,a.value p,case when eta_at->(a.value->>'key')->'at'<>'null'::jsonb then cp7_demand.instant(eta_at->(a.value->>'key')->'at') end at
      from jsonb_array_elements(v->'positions'->'positions')with ordinality a(value,o)),
     r as(select x.o,x.p,x.at,row_number()over(order by x.at nulls last,x.p->>'key')rk from x)
    select(select coalesce(jsonb_object_agg(g.sz,g.os),'{}')from(select r.p->>'size_id' sz,jsonb_agg(r.o order by r.rk)os from r
       where r.p->'eligible_company_wip'<>'false'::jsonb group by 1)g),
     coalesce(array_agg(r.at order by r.o),'{}'),
     coalesce(array_agg(eta_at->(r.p->>'key') is null or eta_at->(r.p->>'key')->'at'='null'::jsonb or r.p->'projection'->>'quality' is distinct from 'SCENARIO' order by r.o),'{}')
     into size_lists,eta_times,reviewed from r;
    used:=array_fill(0::numeric,array[cardinality(position_keys)]);good_used:=used;pool_used:=array_fill(0::numeric,array[cardinality(pool_wip)]);
    -- cp7_wip.match_target checks the source and the target independently;
    -- its verdict reads only the source's quality, size, constraints and
    -- whether its confirmed target is null, this target or another, and the
    -- target's size and constraints. Once a call of their own has proven a
    -- source and a target, a pair with the same facts as an earlier pair has
    -- that pair's verdict; any other pair calls it and refuses as it did.
    select coalesce(jsonb_object_agg(a.value->>'key',a.value),'{}') into source_at from jsonb_array_elements(v->'matching'->'sources')a;
    select coalesce(array_agg(f.id order by f.o),'{}'),coalesce(array_agg(f.s->>'confirmed_target' order by f.o),'{}'),coalesce(max(f.id),0) into source_ids,source_confirmed,sources_n
     from(select x.o,x.s,dense_rank()over(order by jsonb_build_array(x.s->'quality',x.s->'size_id',x.s->'confirmed_target'='null'::jsonb,x.s->'constraints')::text collate "C")::integer id
      from(select a.o,source_at->(a.value->>'key') s from jsonb_array_elements(v->'positions'->'positions')with ordinality a(value,o))x)f;
    select coalesce(jsonb_object_agg(f.k,f.id),'{}'),coalesce(max(f.id),0) into target_ids,targets_n
     from(select x.k,dense_rank()over(order by jsonb_build_array(x.tf->'size_id',x.tf->'constraints')::text collate "C")::integer id
      from(select a.value->>'key' k,target_at->(a.value->>'key') tf from jsonb_array_elements(v->'targets')a)x)f;
    proven:=array_fill(false,array[cardinality(position_keys)]);verdicts:=array_fill(null::jsonb,array[2*sources_n*targets_n]);
   end if;
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
    edge_list:=array_append(edge_list,jsonb_build_object('key','edge-'||(cardinality(edge_list)+1),'position_key',k,'target_key',t->'key','size_id',t->'size_id',
     'input_pcs',input_qty::text,'projected_good_pcs',good::text,'match',m->'match','refs',refs));
    used[o]:=used[o]+input_qty;good_used[o]:=good_used[o]+good;
    pool_used[w]:=pool_used[w]+input_qty;capacity:=capacity-good;left_need:=left_need-good;
   end loop;
  end if;
  row_list:=array_append(row_list,jsonb_build_object('target_key',t->'key','size_id',t->'size_id','need_pcs',need::text,'allocated_good_pcs',(need-left_need)::text,
   'unresolved_pcs',left_need::text,'production_status',t->'production_status','priority_basis',jsonb_build_object('risk_at',t->'risk_at','deadline',t->'deadline','helps_at',t->'helps_at','size_gap',t->'need_pcs','stable_key',t->'key')));
 end loop;
 validation:=cp7_wip.check_allocations(v->'positions',jsonb_build_object('scenario_id',v->'scenario_id','scope_id',v->'scope_id','complete_scope',true,'matching',v->'matching','edges',to_jsonb(edge_list)));
 if validation->>'status'<>'FEASIBLE' then raise exception 'CP7_BASELINE_GENERATED_ALLOCATION_INVALID';end if;
 return jsonb_build_object('status','SCENARIO','kernel_version','greedy-allocation-1','scenario_id',v->'scenario_id','snapshot_id',v->'snapshot_id','scope_id',v->'scope_id',
  'rows',to_jsonb(row_list),'review_queue',to_jsonb(review_list),'remaining_capacity_pcs',capacity::text,'allocation',validation,'inputs',v,
  'reason','GLOBAL_SCOPE_RECOMPUTED_MATCH_YIELD_POOL_CAPACITY_PRIORITY_SIMULATION_ONLY');
end $$;
