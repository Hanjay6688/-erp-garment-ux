-- Prepared private unit adapter, not installed or routed by default.
create schema cp7_frozen_analysis_units_v2 authorization cp7_capture;
revoke all on schema cp7_frozen_analysis_units_v2 from public,anon,authenticated,service_role;

create function cp7_frozen_analysis_units_v2.binding(j cp7_analysis_stage.jobs)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract','cp7.frozen-analysis-unit-cache.v2','job_id',j.id,'actor',j.actor,
  'request_id',j.request_id,'run_id',j.run_id,'query',j.query,'captured_at',j.reference->'captured_at',
  'capsule_sha256',j.reference->'bounded_capsule_hash','producer',j.reference->'bounded_producer_hash')
$$;

create function cp7_frozen_analysis_units_v2.pack(j cp7_analysis_stage.jobs,inputs jsonb)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('binding',cp7_frozen_analysis_units_v2.binding(j),'inputs',inputs,
  'inputs_sha256',encode(extensions.digest(convert_to(inputs::text,'UTF8'),'sha256'),'hex'))
$$;

create function cp7_frozen_analysis_units_v2.unpack(j cp7_analysis_stage.jobs,payload jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 perform cp7_wip.fields(payload,array['binding','inputs','inputs_sha256']);
 if payload->'binding'is distinct from cp7_frozen_analysis_units_v2.binding(j)
  or payload->'inputs'is null or payload->'inputs'='null'::jsonb
  or payload->>'inputs_sha256'is distinct from encode(extensions.digest(convert_to((payload->'inputs')::text,'UTF8'),'sha256'),'hex')
  or payload->'inputs'->>'coverage'is distinct from'COMPLETE'
  or payload->'inputs'->'captured_at'is distinct from j.reference->'captured_at'
  or payload->'inputs'->'query'is distinct from j.query
  or payload->'inputs'->'raw_native_capture_status'is distinct from j.reference->'status'then
  raise exception 'CP7_FROZEN_UNIT_CACHE_BINDING';end if;
 return payload->'inputs';
end $$;

create function cp7_frozen_analysis_units_v2.unit_reference(j cp7_analysis_stage.jobs,u cp7_analysis_stage.units)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare c jsonb:=j.reference||'{}'::jsonb;inputs jsonb;cached jsonb;
begin
 if c->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v2'then return c;end if;
 if j.state is distinct from'RUNNING'or u.job_id is distinct from j.id or u.idx is distinct from j.units_done then
  raise exception 'CP7_FROZEN_UNIT_IDENTITY';end if;
 if u.kind='HIST_PREP'then
  if u.idx<>0 then raise exception 'CP7_FROZEN_UNIT_IDENTITY';end if;
  inputs:=cp7_frozen_analysis_v2.prepare(c,j.query,(cp7_analysis_stage.bounds()->>'job_targets')::integer);
  cached:=cp7_frozen_analysis_units_v2.pack(j,inputs);
  -- Native target_rows already has an immutable work-row trigger and the
  -- existing K3 cleanup owns its deletion. Never rewrite a cached row.
  insert into cp7_analysis_stage.target_rows(job_id,kind,ord,key,payload)
   values(j.id,'FROZEN_INPUTS_V2',1,c->>'bounded_capsule_hash',cached);
 else
  select x.payload into cached from cp7_analysis_stage.target_rows x
   where x.job_id=j.id and x.kind='FROZEN_INPUTS_V2'and x.ord=1 and x.key=c->>'bounded_capsule_hash';
  if cached is null then raise exception 'CP7_FROZEN_UNIT_CACHE_MISSING';end if;
  inputs:=cp7_frozen_analysis_units_v2.unpack(j,cached);
 end if;
 -- Only this local value carries compiled inputs. Native jobs.reference is
 -- never updated; its complete frozen source and PENDING receipt stay exact.
 return c||jsonb_build_object('bounded_history_inputs',inputs,'bounded_input_coverage','COMPLETE');
end $$;

alter function cp7_frozen_analysis_units_v2.binding(cp7_analysis_stage.jobs)owner to cp7_capture;
alter function cp7_frozen_analysis_units_v2.pack(cp7_analysis_stage.jobs,jsonb)owner to cp7_capture;
alter function cp7_frozen_analysis_units_v2.unpack(cp7_analysis_stage.jobs,jsonb)owner to cp7_capture;
alter function cp7_frozen_analysis_units_v2.unit_reference(cp7_analysis_stage.jobs,cp7_analysis_stage.units)owner to cp7_capture;
revoke all on function cp7_frozen_analysis_units_v2.binding(cp7_analysis_stage.jobs)from public,anon,authenticated,service_role;
revoke all on function cp7_frozen_analysis_units_v2.pack(cp7_analysis_stage.jobs,jsonb)from public,anon,authenticated,service_role;
revoke all on function cp7_frozen_analysis_units_v2.unpack(cp7_analysis_stage.jobs,jsonb)from public,anon,authenticated,service_role;
revoke all on function cp7_frozen_analysis_units_v2.unit_reference(cp7_analysis_stage.jobs,cp7_analysis_stage.units)from public,anon,authenticated,service_role;
