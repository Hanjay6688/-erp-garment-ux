-- Compare complete captured dependency vectors, not wall-clock timestamps.
-- The integrator owns the required-domain set and authoritative vector capture.
-- This pure function neither refreshes a run nor authorizes serving/applying it.
create function cp7_baseline.dependencies(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare a jsonb;b jsonb;e jsonb;d text;side text;reasons jsonb;rows jsonb:='[]';
 expected_map jsonb;current_map jsonb;changed boolean:=false;unknown boolean:=false;
 status text;captured timestamptz;checked timestamptz;
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','captured_at','checked_at','required_domains','expected','current','refs']);
 perform cp7_demand.context(v,'cp7.dependency-check-input.v1');perform cp7_wip.refs(v->'refs');
 captured:=cp7_demand.instant(v->'captured_at');checked:=cp7_demand.instant(v->'checked_at');
 if checked<captured then raise exception 'CP7_DEPENDENCY_TIME_ORDER';end if;
 perform cp7_demand.items(v->'required_domains',128);
 if jsonb_array_length(v->'required_domains')=0 then raise exception 'CP7_DEPENDENCY_REQUIRED_DOMAINS';end if;
 for e in select value from jsonb_array_elements(v->'required_domains') loop perform cp7_wip.key(e);end loop;
 if (select count(distinct value) from jsonb_array_elements(v->'required_domains'))<>jsonb_array_length(v->'required_domains') then
  raise exception 'CP7_DEPENDENCY_DUPLICATE_DOMAIN';end if;
 foreach side in array array['expected','current'] loop
  perform cp7_demand.items(v->side,128);
  for e in select value from jsonb_array_elements(v->side) loop
   perform cp7_wip.fields(e,array['domain','revision','completeness','fact_count','source_hash']);
   perform cp7_wip.key(e->'domain');perform cp7_wip.key(e->'revision');
   if e->>'completeness' is null or e->>'completeness' not in ('COMPLETE','ASSUMED','UNKNOWN','CONFLICT','PARTIAL','NOT_APPLICABLE') then raise exception 'CP7_DEPENDENCY_COMPLETENESS';end if;
   if jsonb_typeof(e->'fact_count') is distinct from 'number' or (e->>'fact_count') !~ '^(0|[1-9][0-9]{0,14})$' then raise exception 'CP7_DEPENDENCY_FACT_COUNT';end if;
   if jsonb_typeof(e->'source_hash') is distinct from 'string' or (e->>'source_hash') !~ '^[0-9a-f]{64}$' then raise exception 'CP7_DEPENDENCY_HASH';end if;
  end loop;
  if (select count(distinct value->>'domain') from jsonb_array_elements(v->side))<>jsonb_array_length(v->side) then raise exception 'CP7_DEPENDENCY_DUPLICATE_DOMAIN';end if;
 end loop;
 select coalesce(jsonb_object_agg(value->>'domain',value),'{}') into expected_map from jsonb_array_elements(v->'expected');
 select coalesce(jsonb_object_agg(value->>'domain',value),'{}') into current_map from jsonb_array_elements(v->'current');
 for d in select domain from (
  select jsonb_object_keys(expected_map) as domain union select jsonb_object_keys(current_map)
  union select value#>>'{}' from jsonb_array_elements(v->'required_domains')) domains order by domain collate "C" loop
  a:=expected_map->d;b:=current_map->d;reasons:='[]';
  -- An absent current observation is not proof of deletion. Deletion must be
  -- represented by an authoritative new revision/hash (including a tombstone).
  if a is null or b is null then
   if a is null and b is not null and not (v->'required_domains' ? d) then
    changed:=true;reasons:=reasons||'"DEPENDENCY_ADDED"'::jsonb;
   else unknown:=true;reasons:=reasons||'"MISSING_DEPENDENCY_EVIDENCE"'::jsonb;end if;
  else
   if a->>'revision'<>b->>'revision' then changed:=true;reasons:=reasons||'"REVISION_CHANGED"'::jsonb;end if;
   if a->>'source_hash'<>b->>'source_hash' then changed:=true;reasons:=reasons||'"SOURCE_HASH_CHANGED"'::jsonb;end if;
   if a->'fact_count'<>b->'fact_count' then changed:=true;reasons:=reasons||'"FACT_COUNT_CHANGED"'::jsonb;end if;
   if a->>'completeness'<>b->>'completeness' then changed:=true;reasons:=reasons||'"COMPLETENESS_CHANGED"'::jsonb;end if;
  end if;
  if (a is not null and a->>'completeness' not in ('COMPLETE','NOT_APPLICABLE'))
     or (b is not null and b->>'completeness' not in ('COMPLETE','NOT_APPLICABLE')) then
   unknown:=true;reasons:=reasons||'"DEPENDENCY_NOT_COMPLETE"'::jsonb;end if;
  rows:=rows||jsonb_build_array(jsonb_build_object('domain',d,'expected',a,'current',b,'reasons',reasons));
 end loop;
 status:=case when changed then 'STALE' when unknown then 'UNKNOWN' else 'CURRENT' end;
 return jsonb_build_object('kernel_version','dependency-vector-1','status',status,
  'dependencies_match',case when changed then false when unknown then null else true end,
  'evidence_complete',not unknown,'recompute_required',status<>'CURRENT','checks',rows,
  'reason','REVISION_HASH_COMPLETENESS_VECTOR_NOT_TIMESTAMP_ONLY','authorization_checked',false,'inputs',v);
end $$;
