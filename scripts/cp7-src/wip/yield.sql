-- Yield is an explicit versioned scenario input, never an invented production
-- default. Physical input, eligible input and projected GOOD remain separate.
create function cp7_wip.project_yield(positions jsonb,policies jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare policy jsonb;n jsonb;projection jsonb;rows jsonb[]:='{}';k text;
 qty numeric;num numeric;den numeric;
 o bigint;repeated boolean[];by_key jsonb;by_policy jsonb;
begin
 if positions->>'contract_version' is distinct from 'cp7.wip-position.v1' or positions->>'status' is distinct from 'COMPLETE' then
  return jsonb_build_object('status','UNKNOWN','reason','YIELD_SOURCE_INCOMPLETE');end if;
 if jsonb_typeof(policies) is distinct from 'array' or jsonb_array_length(policies)>10000 then raise exception 'CP7_WIP_YIELD_SHAPE';end if;
 -- Linear form of the per-policy scans: a key repeated at an earlier valid
 -- policy is flagged by position, and each policy still sees the first
 -- position with its key. The position map is built where the first lookup
 -- used to scan, so the same input fails at the same point.
 select array_agg(f.r order by f.o)into repeated from(select ordinality o,case when jsonb_typeof(value->'position_key')='string'
   then row_number()over(partition by value->>'position_key' order by ordinality)>1 else false end r
  from jsonb_array_elements(policies)with ordinality)f;
 o:=0;
 for policy in select value from jsonb_array_elements(policies) loop
  o:=o+1;
  perform cp7_wip.fields(policy,array['position_key','eligible_input_pcs','numerator','denominator','basis','assumption_id','refs']);
  k:=cp7_wip.key(policy->'position_key');perform cp7_wip.refs(policy->'refs');
  if repeated[o] then raise exception 'CP7_WIP_YIELD_DUPLICATE';end if;
  if by_key is null then
   select coalesce(jsonb_object_agg(f.k,f.value),'{}')into by_key from(select distinct on(value->>'key')value->>'key' k,value
    from jsonb_array_elements(positions->'positions')with ordinality where value->>'key'is not null order by value->>'key',ordinality)f;
  end if;
  n:=by_key->k;
  qty:=cp7_wip.pcs(policy->'eligible_input_pcs');num:=cp7_wip.pcs(policy->'numerator');den:=cp7_wip.pcs(policy->'denominator');
  if n is null or n->'eligible_company_wip'<>'true'::jsonb or qty>cp7_wip.pcs(n->'remaining_pcs') or den=0 or num>den
    or policy->>'basis' is null or policy->>'basis' not in ('CONFIRMED_PLAN','HISTORY','ASSUMED') then raise exception 'CP7_WIP_YIELD_POLICY';end if;
  if policy->>'basis'='ASSUMED' then perform cp7_wip.key(policy->'assumption_id');
  elsif policy->'assumption_id'<>'null'::jsonb then raise exception 'CP7_WIP_YIELD_ASSUMPTION';end if;
 end loop;
 select coalesce(jsonb_object_agg(value->>'position_key',value),'{}')into by_policy from jsonb_array_elements(policies);
 for n in select value from jsonb_array_elements(positions->'positions') loop
  policy:=by_policy->(n->>'key');
  projection:=jsonb_build_object('quality','UNKNOWN','reason','YIELD_NOT_SELECTED');
  if policy is not null then
   qty:=cp7_wip.pcs(policy->'eligible_input_pcs');num:=cp7_wip.pcs(policy->'numerator');den:=cp7_wip.pcs(policy->'denominator');
   projection:=policy||jsonb_build_object('quality','SCENARIO','projected_good_pcs',div(qty*num,den)::text,
    'expected_loss_pcs',(qty-div(qty*num,den))::text,'not_actual_bs',true);
  end if;
  rows:=array_append(rows,n||jsonb_build_object('projection',projection));
 end loop;
 return jsonb_set(positions,'{positions}',to_jsonb(rows));
end $$;
