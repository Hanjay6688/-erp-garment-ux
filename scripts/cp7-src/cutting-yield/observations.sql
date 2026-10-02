-- Source-bound observation candidate, not registered in the main bundle.
-- Caller supplies only Native/private version references, never training facts.
create schema cp7_cutting_observations authorization cp7_capture;
revoke all on schema cp7_cutting_observations from public,anon,authenticated,service_role;
create table cp7_cutting_observations.runs(
 id uuid primary key,actor uuid not null,request_id uuid not null,group_id uuid not null,
 captured_at timestamptz not null,input_record_id uuid references cp7_cutting_inputs.plans(id),
 native_source jsonb,records jsonb not null,exclusions jsonb not null,
 unique(actor,request_id)
);
create table cp7_cutting_observations.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 recorded_at timestamptz not null,primary key(actor,request_id)
);
alter table cp7_cutting_observations.runs owner to cp7_capture;
alter table cp7_cutting_observations.requests owner to cp7_capture;
alter table cp7_cutting_observations.runs enable row level security;
alter table cp7_cutting_observations.requests enable row level security;
create policy cutting_observation_private on cp7_cutting_observations.runs for all using(false)with check(false);
create policy cutting_observation_request_private on cp7_cutting_observations.requests for all using(false)with check(false);
revoke all on all tables in schema cp7_cutting_observations from public,anon,authenticated,service_role;
create trigger cutting_observation_immutable before update or delete on cp7_cutting_observations.runs for each row execute function cp7_private.immutable_run();
create trigger cutting_observation_request_immutable before update or delete on cp7_cutting_observations.requests for each row execute function cp7_private.immutable_run();

create function cp7_cutting_observations.payload(p jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
begin
 perform cp7_wip.fields(p,array['group_id','expected_group_version','expected_input_version']);
 if not p?&array['group_id','expected_group_version','expected_input_version']
  or jsonb_typeof(p->'group_id')is distinct from'string'
  or jsonb_typeof(p->'expected_group_version')not in('null','string')
  or jsonb_typeof(p->'expected_input_version')not in('null','string')
  or(p->>'expected_group_version'is not null and(p->>'expected_group_version')!~'^[1-9][0-9]{0,18}$')
  or(p->>'expected_input_version'is not null and(p->>'expected_input_version')!~'^[1-9][0-9]{0,18}$')then raise exception 'CP7_CUTTING_OBSERVATION_PAYLOAD';end if;
 perform(p->>'group_id')::uuid;
 return jsonb_build_object('group_id',(p->>'group_id')::uuid,'expected_group_version',p->'expected_group_version','expected_input_version',p->'expected_input_version');
end $$;

-- Pure private projection. Public command obtains every argument from Native
-- tables/private immutable input history and a real database clock.
create function cp7_cutting_observations.project(s jsonb,plan jsonb,previous jsonb,at timestamptz,revision uuid)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare x jsonb;old jsonb;feature jsonb;context_key jsonb;records jsonb:='[]';excluded jsonb:='[]';seen text[]:=array[]::text[];
 physical timestamptz;input_at timestamptz;valid boolean;matching boolean:=false;pcs numeric;consumed numeric;reason text;
begin
 if at is null or not isfinite(at)or revision is null or jsonb_typeof(previous)is distinct from'array'then raise exception 'CP7_CUTTING_OBSERVATION_SOURCE';end if;
 if s is not null and jsonb_array_length(s->'cutting'->'slices')>1000 then raise exception 'CP7_CUTTING_OBSERVATION_SCOPE';end if;
 if s is not null and plan is not null then
  -- Missing pattern/roll/size is unavailable, never a guessed context.
  if s->'group'->>'pattern_id'is not null and s->'group'->>'pattern_revision'is not null
   and jsonb_array_length(s->'cutting'->'slices')between 1 and 1000 then
   matching:=plan->'native_anchor'=cp7_cutting_inputs.anchor(s);
  end if;
 end if;
 for x in select value from jsonb_array_elements(coalesce(s->'cutting'->'slices','[]'))loop
  seen:=array_append(seen,x->>'slice_id');physical:=(x->>'cut_at')::timestamptz;
  select value into old from jsonb_array_elements(previous)where value->>'slice_key'=x->>'slice_id';
  select value into feature from jsonb_array_elements(coalesce(plan->'values'->'rolls','[]'))where value->>'roll_id'=x->>'roll_id';
  context_key:=feature->'context';input_at:=(plan->>'known_at')::timestamptz;reason:=null;
  if physical is null or not isfinite(physical)then raise exception 'CP7_CUTTING_OBSERVATION_PHYSICAL';end if;
  if physical>at and old is null then
   excluded:=excluded||jsonb_build_array(jsonb_build_object('slice_id',x->'slice_id','reason','PHYSICAL_EVENT_NOT_YET_KNOWN'));
   continue;
  end if;
  -- Do not move an old physical batch between temporal folds after a rewrite.
  if old is not null and(physical is distinct from(old->>'physical_at')::timestamptz or x->>'group_id'<>old->>'batch_key')then
   reason:='NATIVE_PHYSICAL_IDENTITY_CHANGED';physical:=(old->>'physical_at')::timestamptz;
  end if;
  if context_key is not null then perform cp7_cutting_learning.context(context_key);end if;
  consumed:=cp7_cutting_learning.number(x->'consumed_native',true);
  select sum(cp7_cutting_learning.number(y->'qty_pcs',false,true))into pcs from jsonb_array_elements(x->'outputs')y;
  valid:=reason is null and x->'material_issue_posted'='true'::jsonb and matching
   and feature is not null and context_key->>'unit'=x->>'unit_code'
   and feature->>'material_id'=x->>'material_id'and input_at<physical and physical<=at
   and consumed>0 and pcs is not null;
  valid:=coalesce(valid,false);
  if not valid then
   reason:=coalesce(reason,case when x->'material_issue_posted'is distinct from'true'::jsonb then'NATIVE_UNPOSTED_OR_CANCELLED'
    when not matching or feature is null then'INPUT_IDENTITY_UNAVAILABLE_OR_CHANGED'
    when input_at is null or input_at>=physical then'INPUT_RECORDED_AFTER_PHYSICAL_EVENT'
    else'NATIVE_OUTPUT_OR_CONSUMPTION_UNAVAILABLE'end);
   excluded:=excluded||jsonb_build_array(jsonb_build_object('slice_id',x->'slice_id','reason',reason));
  end if;
  records:=records||jsonb_build_array(jsonb_build_object('slice_key',x->'slice_id','batch_key',coalesce(old->'batch_key',x->'group_id'),
   'revision_key',revision,'physical_at',cp7_planning.utc(physical),'known_at',cp7_planning.utc(at),
   'input_known_at',case when input_at is null then null else cp7_planning.utc(input_at)end,'native_valid',valid,
   'context',context_key,'consumed',consumed::text,'actual_pcs',pcs::text,'width_cm',feature->'width_cm'));
 end loop;
 for old in select value from jsonb_array_elements(previous)where not(value->>'slice_key'=any(seen))loop
  -- Cancellation/removal is the latest revision, so an older valid row cannot
  -- survive by being filtered before latest-revision selection.
  records:=records||jsonb_build_array(old||jsonb_build_object('native_valid',false,'known_at',cp7_planning.utc(at),'revision_key',revision));
  excluded:=excluded||jsonb_build_array(jsonb_build_object('slice_id',old->'slice_key','reason','NATIVE_SLICE_OR_GROUP_REMOVED'));
 end loop;
 return jsonb_build_object('records',records,'exclusions',excluded);
end $$;

create function cp7_cutting_observations.view(r cp7_cutting_observations.runs)returns jsonb
language sql stable security invoker set search_path=''as $$
 select jsonb_build_object('id',r.id,'actor_scope_id',r.actor,'request_id',r.request_id,'group_id',r.group_id,
  'known_at',cp7_planning.utc(r.captured_at),'input_record_id',r.input_record_id,
  'native_source',r.native_source,'records',r.records,'exclusions',r.exclusions,
  'knowledge_basis','REAL_CAPTURE_CLOCK_NOT_HISTORICAL_IMPUTATION','model_trained',false,'production_go',false)
$$;

create function cp7_cutting_observations.command(p_payload jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare a jsonb;actor uuid;p jsonb;s jsonb;fresh jsonb;plan cp7_cutting_inputs.plans%rowtype;prior cp7_cutting_observations.runs%rowtype;
 cached cp7_cutting_observations.requests%rowtype;run cp7_cutting_observations.runs%rowtype;result jsonb;projection jsonb;at timestamptz;
begin
 a:=cp7_cutting_inputs.access_now(true);actor:=(a->>'actor')::uuid;p:=cp7_cutting_observations.payload(p_payload);
 if p_request is null or p_lookup is null then raise exception 'CP7_CUTTING_OBSERVATION_REQUEST';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:CUTTING_OBSERVATION_REQUEST:'||actor::text||':'||p_request::text,0));
 if cp7_cutting_inputs.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_OBSERVATION_ACCESS_CHANGED';end if;
 select *into cached from cp7_cutting_observations.requests where requests.actor=actor and request_id=p_request;
 if cached.request_id is not null then
  if cached.payload<>p then raise exception 'CP7_CUTTING_OBSERVATION_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then
  result:=jsonb_build_object('status','NOT_COMMITTED','request_id',p_request,'observation',null);
  insert into cp7_cutting_observations.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:CUTTING_INPUT_GROUP:'||actor::text||':'||(p->>'group_id'),0));
  if cp7_cutting_inputs.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_OBSERVATION_ACCESS_CHANGED';end if;
  s:=cp7_cutting_inputs.source((p->>'group_id')::uuid);
  select *into plan from cp7_cutting_inputs.plans where plans.actor=actor and group_id=(p->>'group_id')::uuid order by version desc limit 1;
  if s->'group'->>'version'is distinct from p->>'expected_group_version'or plan.version::text is distinct from p->>'expected_input_version'then raise exception 'CP7_CUTTING_OBSERVATION_SOURCE_CHANGED';end if;
  select *into prior from cp7_cutting_observations.runs where runs.actor=actor and group_id=(p->>'group_id')::uuid order by captured_at desc,id desc limit 1;
  at:=clock_timestamp();run.id:=gen_random_uuid();
  projection:=cp7_cutting_observations.project(s,case when plan.id is null then null else cp7_cutting_inputs.record_view(plan)end,coalesce(prior.records,'[]'),at,run.id);
  insert into cp7_cutting_observations.runs values(run.id,actor,p_request,(p->>'group_id')::uuid,at,plan.id,s,projection->'records',projection->'exclusions')returning *into run;
  fresh:=cp7_cutting_inputs.source((p->>'group_id')::uuid);
  if fresh is distinct from s then raise exception 'CP7_CUTTING_OBSERVATION_SOURCE_CHANGED';end if;
  result:=jsonb_build_object('status','COMMITTED','request_id',p_request,'observation',cp7_cutting_observations.view(run));
  insert into cp7_cutting_observations.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 fresh:=cp7_cutting_inputs.source((p->>'group_id')::uuid);
 select *into plan from cp7_cutting_inputs.plans where plans.actor=actor and group_id=(p->>'group_id')::uuid order by version desc limit 1;
 if cp7_cutting_inputs.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_OBSERVATION_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-cutting-observation-command.v1','actor_scope_id',actor,'result',result,
  'current_native_source',fresh,'current_input_record_id',plan.id,
  'original_matches_current_inputs',result->>'status'='COMMITTED'and(result->'observation'->>'input_record_id')::uuid is not distinct from plan.id,
  'original_matches_current_native',result->>'status'='COMMITTED'and result->'observation'->'native_source'is not distinct from fresh,
  'model_trained',false,'business_write',false,'automatic_activation',false,'production_go',false);
end $$;
alter function cp7_cutting_observations.payload(jsonb)owner to cp7_capture;
alter function cp7_cutting_observations.project(jsonb,jsonb,jsonb,timestamptz,uuid)owner to cp7_capture;
alter function cp7_cutting_observations.view(cp7_cutting_observations.runs)owner to cp7_capture;
alter function cp7_cutting_observations.command(jsonb,uuid,boolean)owner to cp7_capture;
revoke all on all functions in schema cp7_cutting_observations from public,anon,authenticated,service_role;
create function public.erp_cp7_capture_cutting_observation_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_observations.command(p_payload,p_request,false)$$;
create function public.erp_cp7_get_cutting_observation_request_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_observations.command(p_payload,p_request,true)$$;
grant create on schema public to cp7_capture;
alter function public.erp_cp7_capture_cutting_observation_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_get_cutting_observation_request_v1(jsonb,uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_capture_cutting_observation_v1(jsonb,uuid),public.erp_cp7_get_cutting_observation_request_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_cutting_observation_v1(jsonb,uuid),public.erp_cp7_get_cutting_observation_request_v1(jsonb,uuid)to authenticated;
