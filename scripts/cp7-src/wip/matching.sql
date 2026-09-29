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
create function cp7_wip.check_allocations(positions jsonb, a jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare e jsonb; n jsonb; p jsonb; used jsonb:='{}';pool_used jsonb:='{}'; seen jsonb:='{}';
 qty numeric; k text;pk text; deficits jsonb:='[]';
begin
 perform cp7_wip.fields(a,array['scenario_id','scope_id','complete_scope','edges']);
 perform cp7_wip.key(a->'scenario_id');perform cp7_wip.key(a->'scope_id');
 if jsonb_typeof(a->'complete_scope') is distinct from 'boolean' or jsonb_typeof(a->'edges') is distinct from 'array' then raise exception 'CP7_WIP_ALLOCATION_SHAPE';end if;
 if positions->>'contract_version' is distinct from 'cp7.wip-position.v1' or positions->>'status' is distinct from 'COMPLETE'
   or not (a->>'complete_scope')::boolean then
  return jsonb_build_object('status','UNKNOWN','reason','ALLOCATION_SCOPE_INCOMPLETE');
 end if;
 if jsonb_array_length(a->'edges')>10000 then raise exception 'CP7_WIP_LIMIT';end if;
 for e in select value from jsonb_array_elements(a->'edges') loop
  perform cp7_wip.fields(e,array['key','position_key','target_key','size_id','input_pcs','projected_good_pcs','match','refs']);
  k:=cp7_wip.key(e->'key');perform cp7_wip.key(e->'target_key');perform cp7_wip.key(e->'size_id');perform cp7_wip.refs(e->'refs');
  if seen ? k then raise exception 'CP7_WIP_DUPLICATE_ALLOCATION';end if;seen:=seen||jsonb_build_object(k,true);
  select value into n from jsonb_array_elements(positions->'positions') where value->>'key'=cp7_wip.key(e->'position_key');
  qty:=cp7_wip.pcs(e->'input_pcs');
  if n is null or n->>'size_id'<>e->>'size_id' or n->'eligible_company_wip'<>'true'::jsonb
    or e->>'match' is null or e->>'match' not in ('CONFIRMED_TARGET','CANDIDATE_MATCH')
    or cp7_wip.pcs(e->'projected_good_pcs')>qty then raise exception 'CP7_WIP_INELIGIBLE_ALLOCATION';end if;
  k:=n->>'key';pk:=n->>'pool_key';
  used:=used||jsonb_build_object(k,coalesce((used->>k)::numeric,0)+qty);
  pool_used:=pool_used||jsonb_build_object(pk,coalesce((pool_used->>pk)::numeric,0)+qty);
 end loop;
 for n in select value from jsonb_array_elements(positions->'positions') loop
  k:=n->>'key';qty:=coalesce((used->>k)::numeric,0);
  if qty>cp7_wip.pcs(n->'remaining_pcs') then deficits:=deficits||jsonb_build_array(jsonb_build_object('kind','POSITION','key',k,'excess_pcs',(qty-cp7_wip.pcs(n->'remaining_pcs'))::text));end if;
 end loop;
 for p in select value from jsonb_array_elements(positions->'totals') loop
  pk:=p->>'pool_key';qty:=coalesce((pool_used->>pk)::numeric,0);
  if qty>cp7_wip.pcs(p->'wip_pcs') then deficits:=deficits||jsonb_build_array(jsonb_build_object('kind','POOL','key',pk,'excess_pcs',(qty-cp7_wip.pcs(p->'wip_pcs'))::text));end if;
 end loop;
 return jsonb_build_object('status',case when jsonb_array_length(deficits)=0 then 'FEASIBLE' else 'INFEASIBLE' end,
  'scenario_id',a->'scenario_id','scope_id',a->'scope_id','violations',deficits,
  'basis','SIMULATION_NOT_RESERVATION');
end $$;
