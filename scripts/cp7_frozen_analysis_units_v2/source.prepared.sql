-- Private helpers for composed v2 unit routing. Not installed by default.
create function cp7_frozen_analysis_units_v2.producer_hash()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('contract','cp7.frozen-analysis-unit-producer.v2',
  'capsule',cp7_frozen_analysis_v2.producer_hash(),'adapter',(
   select string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text)
   from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where p.prokind='f'and(n.nspname='cp7_frozen_analysis_units_v2'or p.oid=any(array[
    'cp7_analysis_stage.run_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units)'::regprocedure,
    'cp7_analysis_stage.run_scenario_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units,jsonb)'::regprocedure,
    'cp7_supply_native.fingerprint(jsonb)'::regprocedure,
    'cp7_analysis_stage.analysis_skeleton(jsonb,jsonb,uuid,jsonb,jsonb,jsonb,jsonb,jsonb,boolean,text)'::regprocedure,
    'cp7_schedule_staged_review.workspace(uuid)'::regprocedure,
    'cp7_schedule_staged_review.save(jsonb,uuid)'::regprocedure]))))::text,'UTF8'),'sha256'),'hex')
$$;

create function cp7_frozen_analysis_units_v2.source(q jsonb,p_with_capsule boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare c jsonb;producer text;
begin
 c:=cp7_frozen_analysis_v2.source(q,p_with_capsule);
 producer:=cp7_frozen_analysis_units_v2.producer_hash();
 if p_with_capsule then
  return cp7_frozen_analysis_v2.seal(cp7_frozen_analysis_v2.base(c),q,c->'bounded_stock_reference',
   nullif(c->'bounded_frozen_stock_summary','null'::jsonb),producer,(cp7_analysis_stage.bounds()->>'job_targets')::integer);
 end if;
 return cp7_frozen_analysis_v2.reference(cp7_frozen_analysis_v2.base(c),q,c->'bounded_stock_reference',producer);
end $$;

create function cp7_frozen_analysis_units_v2.coverage(p_job uuid)returns text
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare j cp7_analysis_stage.jobs;
begin
 select *into j from cp7_analysis_stage.jobs x where x.id=p_job;
 if j.id is null or j.reference->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v2'
  or not exists(select 1 from cp7_analysis_stage.units u where u.job_id=j.id and u.idx=0 and u.kind='HIST_PREP')then
  raise exception 'CP7_FROZEN_UNIT_IDENTITY';end if;
 -- Progress advances atomically after the successful first unit. It survives
 -- K3 removal of temporary inputs and never rewrites the frozen reference.
 return case when j.units_done>0 then 'COMPLETE'else 'PENDING'end;
end $$;

alter function cp7_frozen_analysis_units_v2.producer_hash()owner to cp7_capture;
alter function cp7_frozen_analysis_units_v2.source(jsonb,boolean)owner to cp7_capture;
alter function cp7_frozen_analysis_units_v2.coverage(uuid)owner to cp7_capture;
revoke all on function cp7_frozen_analysis_units_v2.producer_hash()from public,anon,authenticated,service_role;
revoke all on function cp7_frozen_analysis_units_v2.source(jsonb,boolean)from public,anon,authenticated,service_role;
revoke all on function cp7_frozen_analysis_units_v2.coverage(uuid)from public,anon,authenticated,service_role;
