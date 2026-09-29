-- Constraints describe explicit source facts/requirements. Optional empty metadata
-- does not reject all WIP. A tariff/history hint never confirms a destination.
create function cp7_wip.match_target(s jsonb,t jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare c jsonb; d jsonb; side jsonb; k text; constraints jsonb; seen jsonb;
 required boolean; missing text[]:='{}'; conflicts text[]:='{}';
 allowed constant text[]:=array['pattern_revision','material','finish','color','brand'];
begin
 perform cp7_wip.fields(s,array['key','quality','size_id','confirmed_target','constraints','refs']);
 perform cp7_wip.fields(t,array['key','size_id','constraints','refs']);
 perform cp7_wip.key(s->'key');perform cp7_wip.key(t->'key');
 perform cp7_wip.key(s->'size_id');perform cp7_wip.key(t->'size_id');
 perform cp7_wip.refs(s->'refs');perform cp7_wip.refs(t->'refs');
 if s->>'quality' is null or s->>'quality' not in ('COMPLETE','PARTIAL','CONFLICT','UNKNOWN') then raise exception 'CP7_WIP_QUALITY';end if;
 if s->'confirmed_target'<>'null'::jsonb then perform cp7_wip.key(s->'confirmed_target');end if;
 foreach side in array array[s,t] loop
  constraints:=side->'constraints';seen:='{}';
  if jsonb_typeof(constraints) is distinct from 'array' or jsonb_array_length(constraints)>5 then raise exception 'CP7_WIP_CONSTRAINTS';end if;
  for c in select value from jsonb_array_elements(constraints) loop
   perform cp7_wip.fields(c,array['field','value','required','basis']);k:=cp7_wip.key(c->'field');
   if not k=any(allowed) or seen ? k or jsonb_typeof(c->'required') is distinct from 'boolean'
     or c->>'basis' is null or c->>'basis' not in ('FACT','HINT','UNKNOWN') then raise exception 'CP7_WIP_CONSTRAINT';end if;
   if c->'value'<>'null'::jsonb then perform cp7_wip.key(c->'value');end if;
   if c->>'basis'='UNKNOWN' and c->'value'<>'null'::jsonb then raise exception 'CP7_WIP_CONSTRAINT';end if;
   seen:=seen||jsonb_build_object(k,true);
  end loop;
 end loop;
 if s->>'quality'<>'COMPLETE' then return jsonb_build_object('match','UNKNOWN','reasons',jsonb_build_array('SOURCE_'||(s->>'quality')));end if;
 if s->>'size_id'<>t->>'size_id' then conflicts:=array_append(conflicts,'SIZE_MISMATCH');end if;
 if s->'confirmed_target'<>'null'::jsonb and s->>'confirmed_target'<>t->>'key' then
  conflicts:=array_append(conflicts,'CONFIRMED_OTHER_TARGET');
 end if;
 foreach k in array allowed loop
  select value into c from jsonb_array_elements(s->'constraints') where value->>'field'=k;
  select value into d from jsonb_array_elements(t->'constraints') where value->>'field'=k;
  required:=coalesce((c->>'required')::boolean,false) or coalesce((d->>'required')::boolean,false);
  if c->>'basis'='FACT' and d->>'basis'='FACT' and c->'value'<>'null'::jsonb and d->'value'<>'null'::jsonb then
   if c->>'value'<>d->>'value' then conflicts:=array_append(conflicts,upper(k)||'_MISMATCH');end if;
  elsif required then missing:=array_append(missing,upper(k)||'_NEEDS_PROOF');end if;
 end loop;
 if cardinality(conflicts)>0 then return jsonb_build_object('match','INCOMPATIBLE','reasons',to_jsonb(conflicts));end if;
 if cardinality(missing)>0 then return jsonb_build_object('match','NEEDS_CHECK','reasons',to_jsonb(missing));end if;
 return jsonb_build_object('match',case when s->>'confirmed_target'=t->>'key' then 'CONFIRMED_TARGET' else 'CANDIDATE_MATCH' end,
  'reasons',jsonb_build_array(case when s->>'confirmed_target'=t->>'key' then 'EXPLICIT_DESTINATION' else 'KNOWN_CONSTRAINTS_COMPATIBLE' end));
end $$;

-- One complete allocation scope and one scenario per call. Presentation filters
-- do not enter this function. Both original pool and remaining-position caps apply.
-- The private caller supplies current captured source/target facts, not a trusted
-- match label. Source snapshot and reviewed version refs bind the computation.
-- P06 must obtain these facts server-side; this pure kernel is not a public API.
create function cp7_wip.check_allocations(positions jsonb, a jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare e jsonb; n jsonb; p jsonb; projection jsonb;used jsonb:='{}';good_used jsonb:='{}';pool_used jsonb:='{}'; seen jsonb:='{}';
 qty numeric;good numeric;cap numeric;k text;pk text; deficits jsonb:='[]';
 matching jsonb;source_facts jsonb;target_facts jsonb;computed jsonb;side jsonb;entry jsonb;facts_seen jsonb;
begin
 perform cp7_wip.fields(a,case when a ? 'matching' then array['scenario_id','scope_id','complete_scope','edges','matching']
  else array['scenario_id','scope_id','complete_scope','edges'] end);
 perform cp7_wip.key(a->'scenario_id');perform cp7_wip.key(a->'scope_id');
 if jsonb_typeof(a->'complete_scope') is distinct from 'boolean' or jsonb_typeof(a->'edges') is distinct from 'array' then raise exception 'CP7_WIP_ALLOCATION_SHAPE';end if;
 if positions->>'contract_version' is distinct from 'cp7.wip-position.v1' or positions->>'status' is distinct from 'COMPLETE'
   or not (a->>'complete_scope')::boolean then
  return jsonb_build_object('status','UNKNOWN','reason','ALLOCATION_SCOPE_INCOMPLETE');
 end if;
 if positions->'allocation_review_required'='true'::jsonb then
  return jsonb_build_object('status','UNKNOWN','reason','SOURCE_REVIEW_REQUIRED');end if;
 if not a ? 'matching' then
  return jsonb_build_object('status','UNKNOWN','reason','MATCHING_FACTS_REQUIRED');end if;
 matching:=a->'matching';
 perform cp7_wip.fields(matching,array['snapshot_id','sources','targets']);
 perform cp7_wip.key(matching->'snapshot_id');
 if matching->>'snapshot_id' is distinct from positions->>'snapshot_id' then raise exception 'CP7_WIP_MATCH_SNAPSHOT';end if;
 foreach side in array array[matching->'sources',matching->'targets'] loop
  if jsonb_typeof(side) is distinct from 'array' or jsonb_array_length(side)>10000 then raise exception 'CP7_WIP_MATCH_FACTS';end if;
  facts_seen:='{}';
  for entry in select value from jsonb_array_elements(side) loop
   k:=cp7_wip.key(entry->'key');
   if facts_seen ? k then raise exception 'CP7_WIP_MATCH_DUPLICATE';end if;
   facts_seen:=facts_seen||jsonb_build_object(k,true);
  end loop;
 end loop;
 if jsonb_array_length(a->'edges')>10000 then raise exception 'CP7_WIP_LIMIT';end if;
 for e in select value from jsonb_array_elements(a->'edges') loop
  perform cp7_wip.fields(e,array['key','position_key','target_key','size_id','input_pcs','projected_good_pcs','match','refs']);
  k:=cp7_wip.key(e->'key');perform cp7_wip.key(e->'target_key');perform cp7_wip.key(e->'size_id');perform cp7_wip.refs(e->'refs');
  if seen ? k then raise exception 'CP7_WIP_DUPLICATE_ALLOCATION';end if;seen:=seen||jsonb_build_object(k,true);
  select value into n from jsonb_array_elements(positions->'positions') where value->>'key'=cp7_wip.key(e->'position_key');
  qty:=cp7_wip.pcs(e->'input_pcs');good:=cp7_wip.pcs(e->'projected_good_pcs');
  if n is null or n->>'size_id'<>e->>'size_id' or n->'eligible_company_wip'<>'true'::jsonb
    or e->>'match' is null or e->>'match' not in ('CONFIRMED_TARGET','CANDIDATE_MATCH')
    or good>qty then raise exception 'CP7_WIP_INELIGIBLE_ALLOCATION';end if;
  select value into source_facts from jsonb_array_elements(matching->'sources') where value->>'key'=n->>'key';
  select value into target_facts from jsonb_array_elements(matching->'targets') where value->>'key'=e->>'target_key';
  if source_facts is null or target_facts is null then raise exception 'CP7_WIP_MATCH_FACTS';end if;
  if source_facts->>'size_id' is distinct from n->>'size_id' or target_facts->>'size_id' is distinct from e->>'size_id'
    or not (source_facts->'refs' @> n->'refs')
    or not (e->'refs' @> source_facts->'refs') or not (e->'refs' @> target_facts->'refs') then
   raise exception 'CP7_WIP_MATCH_BINDING';end if;
  computed:=cp7_wip.match_target(source_facts,target_facts);
  if computed->>'match' not in ('CONFIRMED_TARGET','CANDIDATE_MATCH') then
   raise exception 'CP7_WIP_INELIGIBLE_ALLOCATION';end if;
  if e->>'match' is distinct from computed->>'match' then raise exception 'CP7_WIP_MATCH_STALE';end if;
  k:=n->>'key';pk:=n->>'pool_key';
  projection:=n->'projection';
  if qty>0 and (projection->>'quality' is distinct from 'SCENARIO') then
   return jsonb_build_object('status','UNKNOWN','reason','YIELD_NOT_SELECTED','position_key',k);end if;
  if qty>0 then
   cap:=div(qty*cp7_wip.pcs(projection->'numerator'),cp7_wip.pcs(projection->'denominator'));
   if good>cap then deficits:=deficits||jsonb_build_array(jsonb_build_object('kind','EDGE_YIELD','key',e->'key','excess_pcs',(good-cap)::text));end if;
  end if;
  used:=used||jsonb_build_object(k,coalesce((used->>k)::numeric,0)+qty);
  good_used:=good_used||jsonb_build_object(k,coalesce((good_used->>k)::numeric,0)+good);
  pool_used:=pool_used||jsonb_build_object(pk,coalesce((pool_used->>pk)::numeric,0)+qty);
 end loop;
 for n in select value from jsonb_array_elements(positions->'positions') loop
  k:=n->>'key';qty:=coalesce((used->>k)::numeric,0);
  if qty>cp7_wip.pcs(n->'remaining_pcs') then deficits:=deficits||jsonb_build_array(jsonb_build_object('kind','POSITION','key',k,'excess_pcs',(qty-cp7_wip.pcs(n->'remaining_pcs'))::text));end if;
  if qty>0 and n->'projection'->>'quality'='SCENARIO' then
   if qty>cp7_wip.pcs(n->'projection'->'eligible_input_pcs') then deficits:=deficits||jsonb_build_array(jsonb_build_object('kind','ELIGIBLE_INPUT','key',k,'excess_pcs',(qty-cp7_wip.pcs(n->'projection'->'eligible_input_pcs'))::text));end if;
   if (good_used->>k)::numeric>cp7_wip.pcs(n->'projection'->'projected_good_pcs') then deficits:=deficits||jsonb_build_array(jsonb_build_object('kind','PROJECTED_GOOD','key',k,'excess_pcs',((good_used->>k)::numeric-cp7_wip.pcs(n->'projection'->'projected_good_pcs'))::text));end if;
  end if;
 end loop;
 for p in select value from jsonb_array_elements(positions->'totals') loop
  pk:=p->>'pool_key';qty:=coalesce((pool_used->>pk)::numeric,0);
  if qty>cp7_wip.pcs(p->'wip_pcs') then deficits:=deficits||jsonb_build_array(jsonb_build_object('kind','POOL','key',pk,'excess_pcs',(qty-cp7_wip.pcs(p->'wip_pcs'))::text));end if;
 end loop;
 return jsonb_build_object('status',case when jsonb_array_length(deficits)=0 then 'FEASIBLE' else 'INFEASIBLE' end,
  'scenario_id',a->'scenario_id','scope_id',a->'scope_id','violations',deficits,
  'edges',coalesce((select jsonb_agg(value order by value->>'key') from jsonb_array_elements(a->'edges')),'[]'::jsonb),
  'matching',matching,'matching_basis','RECOMPUTED_FROM_SAME_SNAPSHOT_FACTS',
  'basis','SIMULATION_NOT_RESERVATION');
end $$;
