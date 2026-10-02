-- Standalone prospective learning producer. Not installed by main planning.
-- Native SAVE/POST remains independent of these private metadata commands.
create schema cp7_cutting_model authorization cp7_capture;
revoke all on schema cp7_cutting_model from public,anon,authenticated,service_role;
create table cp7_cutting_model.policies(
 id uuid primary key,actor uuid not null,request_id uuid not null,known_at timestamptz not null,
 context jsonb not null,coverage numeric not null,train_batches integer not null,
 calibration_batches integer not null,holdout_batches integer not null,
 previous_id uuid references cp7_cutting_model.policies(id),unique(actor,request_id)
);
create table cp7_cutting_model.runs(
 id uuid primary key,actor uuid not null,request_id uuid not null,known_at timestamptz not null,
 policy_id uuid references cp7_cutting_model.policies(id),input_record_id uuid not null,
 group_id uuid not null,roll_id uuid not null,source_scope jsonb not null,evaluation jsonb not null,
 unique(actor,request_id)
);
create table cp7_cutting_model.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 recorded_at timestamptz not null,primary key(actor,request_id)
);
alter table cp7_cutting_model.policies owner to cp7_capture;
alter table cp7_cutting_model.runs owner to cp7_capture;
alter table cp7_cutting_model.requests owner to cp7_capture;
alter table cp7_cutting_model.policies enable row level security;
alter table cp7_cutting_model.runs enable row level security;
alter table cp7_cutting_model.requests enable row level security;
create policy cutting_model_policy_private on cp7_cutting_model.policies for all using(false)with check(false);
create policy cutting_model_run_private on cp7_cutting_model.runs for all using(false)with check(false);
create policy cutting_model_request_private on cp7_cutting_model.requests for all using(false)with check(false);
create trigger cutting_model_policy_immutable before update or delete on cp7_cutting_model.policies for each row execute function cp7_private.immutable_run();
create trigger cutting_model_run_immutable before update or delete on cp7_cutting_model.runs for each row execute function cp7_private.immutable_run();
create trigger cutting_model_request_immutable before update or delete on cp7_cutting_model.requests for each row execute function cp7_private.immutable_run();
revoke all on all tables in schema cp7_cutting_model from public,anon,authenticated,service_role;

create function cp7_cutting_model.payload(p jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
declare k text;coverage numeric;
begin
 if p->>'action'='POLICY' then
  perform cp7_wip.fields(p,array['action','group_id','roll_id','expected_group_version','expected_input_version','expected_policy_id','coverage','train_batches','calibration_batches','holdout_batches','explicit_review']);
  if (select count(*)from jsonb_object_keys(p))<>11 or p->'explicit_review'is distinct from'true'::jsonb then raise exception 'CP7_CUTTING_MODEL_POLICY_PAYLOAD';end if;
  coverage:=cp7_cutting_learning.number(p->'coverage');
  if coverage<=0 or coverage>=1 then raise exception 'CP7_CUTTING_MODEL_COVERAGE';end if;
  foreach k in array array['train_batches','calibration_batches','holdout_batches']loop
   if cp7_cutting_learning.number(p->k,false,true)not between 3 and 10000 then raise exception 'CP7_CUTTING_MODEL_FOLD_COUNTS';end if;
  end loop;
  if (p->>'train_batches')::integer+(p->>'calibration_batches')::integer+(p->>'holdout_batches')::integer>20000
   or ceil(((p->>'calibration_batches')::integer+1)*coverage)>(p->>'calibration_batches')::integer then raise exception 'CP7_CUTTING_MODEL_CALIBRATION_SUPPORT';end if;
  if jsonb_typeof(p->'expected_policy_id')not in('string','null')then raise exception 'CP7_CUTTING_MODEL_POLICY_PAYLOAD';end if;
  if p->>'expected_policy_id'is not null then perform(p->>'expected_policy_id')::uuid;end if;
 elsif p->>'action'='CHECK' then
  perform cp7_wip.fields(p,array['action','group_id','roll_id','expected_group_version','expected_input_version','policy_id']);
  if (select count(*)from jsonb_object_keys(p))<>6 or jsonb_typeof(p->'policy_id')is distinct from'string'then raise exception 'CP7_CUTTING_MODEL_PAYLOAD';end if;
  perform(p->>'policy_id')::uuid;
 else raise exception 'CP7_CUTTING_MODEL_ACTION';end if;
 foreach k in array array['group_id','roll_id']loop
  if jsonb_typeof(p->k)is distinct from'string'then raise exception 'CP7_CUTTING_MODEL_PAYLOAD';end if;perform(p->>k)::uuid;
 end loop;
 foreach k in array array['expected_group_version','expected_input_version']loop
  if jsonb_typeof(p->k)is distinct from'string'or(p->>k)!~'^[1-9][0-9]{0,18}$'or(p->>k)::numeric>9223372036854775807 then raise exception 'CP7_CUTTING_MODEL_VERSION';end if;
 end loop;
 return p;
end $$;

create function cp7_cutting_model.policy_view(r cp7_cutting_model.policies)returns jsonb
language sql immutable security invoker set search_path=''as $$
 select jsonb_build_object('id',r.id,'actor_scope_id',r.actor,'request_id',r.request_id,
  'known_at',cp7_planning.utc(r.known_at),'context',r.context,'coverage',r.coverage::text,
  'train_batches',r.train_batches::text,'calibration_batches',r.calibration_batches::text,
  'holdout_batches',r.holdout_batches::text,'previous_id',r.previous_id,
  'policy_kind','EXPLICIT_PROSPECTIVE_PROPOSAL_NOT_FACTORY_GUARANTEE','automatic_activation',false)
$$;

create function cp7_cutting_model.workspace(gid uuid,rid uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''as $$
declare a jsonb;w jsonb;feature jsonb;policy cp7_cutting_model.policies%rowtype;
begin
 a:=cp7_cutting_inputs.access_now();w:=cp7_cutting_inputs.workspace(gid);
 select x into feature from jsonb_array_elements(w->'record'->'values'->'rolls')x where(x->>'roll_id')::uuid=rid;
 if feature is not null then
  select *into policy from cp7_cutting_model.policies where actor=(a->>'actor')::uuid and context=feature->'context'order by known_at desc,id desc limit 1;
 end if;
 if cp7_cutting_inputs.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_MODEL_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-cutting-model-workspace.v1','actor_scope_id',a->'actor',
  'group_id',gid,'roll_id',rid,'input',w,'feature',feature,'policy',case when policy.id is null then null else cp7_cutting_model.policy_view(policy)end,
  'business_write',false,'automatic_activation',false,'production_go',false);
end $$;

-- All current Native group identities are retained; every actor-owned input
-- group is read, including removed/unavailable groups. No LIMIT hides history.
-- The empirical sample scope is this actor's prospective recorded contexts.
create function cp7_cutting_model.collect(actor_id uuid,current_group uuid)returns jsonb
language plpgsql stable security invoker set search_path=''as $$
declare groups jsonb;scope_rows jsonb:='[]';records jsonb:='[]';unavailable jsonb:='[]';p cp7_cutting_inputs.plans%rowtype;
 s jsonb;ob cp7_cutting_observations.runs%rowtype;native_count bigint;
begin
 select count(*)into native_count from erp.cutting_groups;
 if native_count>20000 then raise exception 'CP7_CUTTING_MODEL_NATIVE_SCOPE_TOO_LARGE';end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'version',row_version::text,'physical_at',cp7_planning.utc(cut_at),'posted',material_issue_posted)order by id),'[]')into groups from erp.cutting_groups;
 for p in select distinct on(group_id)*from cp7_cutting_inputs.plans where actor=actor_id order by group_id,version desc loop
  s:=cp7_cutting_inputs.source(p.group_id);
  -- Repeated identical captures are one known physical observation. Keep the
  -- first genuine capture of the *current* exact source/input, not a fake clock.
  select *into ob from cp7_cutting_observations.runs where actor=actor_id and group_id=p.group_id
   and input_record_id=p.id and native_source is not distinct from s order by captured_at,id limit 1;
  scope_rows:=scope_rows||jsonb_build_array(jsonb_build_object('group_id',p.group_id,'input_record_id',p.id,'native_source',s,'observation_id',ob.id));
  if p.group_id=current_group then continue;end if;
  if ob.id is null then
   unavailable:=unavailable||jsonb_build_array(jsonb_build_object('group_id',p.group_id,'reason','CURRENT_SOURCE_OBSERVATION_REQUIRED'));
  else records:=records||ob.records;end if;
 end loop;
 if jsonb_array_length(records)>20000 then raise exception 'CP7_CUTTING_MODEL_RECORD_SCOPE_TOO_LARGE';end if;
 return jsonb_build_object('native_groups',groups,'input_groups',scope_rows,'records',records,'unavailable',unavailable,
  'source_complete',jsonb_array_length(unavailable)=0,'sample_scope','ACTOR_PROSPECTIVE_INPUT_CONTEXTS_NOT_UNRECORDED_FACTORY_HISTORY');
end $$;

create function cp7_cutting_model.evaluate(scope jsonb,policy cp7_cutting_model.policies,w jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
declare batches jsonb;rows jsonb;cutoffs timestamptz[];row jsonb;at timestamptz;prior timestamptz;
 required integer;reason text;qty numeric;pcs numeric;current_slice jsonb;outcome jsonb;
begin
 outcome:=jsonb_build_object('status','UNAVAILABLE','interval',null,'automatic_activation',false,'business_write',false,'production_go',false);
 if scope->'source_complete'is distinct from'true'::jsonb then return outcome||jsonb_build_object('reason','CURRENT_HISTORY_RECAPTURE_REQUIRED','unavailable',scope->'unavailable');end if;
 if w->'input'->'record_matches_native_identity'is distinct from'true'::jsonb then return outcome||jsonb_build_object('reason','CURRENT_INPUT_IDENTITY_UNAVAILABLE');end if;
 if w->'input'->'group'->'posted'='true'::jsonb and w->'input'->'preknown_before_physical'is distinct from'true'::jsonb then return outcome||jsonb_build_object('reason','PLAN_RECORDED_AFTER_PHYSICAL_EVENT');end if;
 required:=policy.train_batches+policy.calibration_batches+policy.holdout_batches;
 if policy.known_at>=(w->'input'->'record'->>'known_at')::timestamptz then return outcome||jsonb_build_object('reason','PROSPECTIVE_SEPARATE_BATCHES_REQUIRED','available_batches','0','required_batches',required::text);end if;
 rows:=cp7_cutting_learning.dataset(scope->'records',policy.context,policy.known_at,
  (w->'input'->'record'->>'known_at')::timestamptz,w->>'group_id');
 with grouped as(select x->>'batch_key'key,max((x->>'known_at')::timestamptz)known,max((x->>'physical_at')::timestamptz)physical
  from jsonb_array_elements(rows)x group by x->>'batch_key')
 select coalesce(jsonb_agg(jsonb_build_object('key',key,'known',cp7_planning.utc(known),'physical',cp7_planning.utc(physical))order by physical,key),'[]')into batches from grouped;
 if jsonb_array_length(batches)<required then return outcome||jsonb_build_object('reason','PROSPECTIVE_SEPARATE_BATCHES_REQUIRED','available_batches',jsonb_array_length(batches)::text,'required_batches',required::text);end if;
 cutoffs:=array[]::timestamptz[];at:=null;prior:=policy.known_at;
 for i in 0..required-1 loop
  row:=batches->i;
  if(row->>'physical')::timestamptz<=prior then reason:='OBSERVATION_CAPTURE_OVERLAPS_LATER_PHYSICAL_FOLD';exit;end if;
  at:=greatest(at,(row->>'known')::timestamptz,(row->>'physical')::timestamptz);
  if i+1 in(policy.train_batches,policy.train_batches+policy.calibration_batches,required)then
   cutoffs:=array_append(cutoffs,at);prior:=at;
  end if;
 end loop;
 if reason is not null then return outcome||jsonb_build_object('reason',reason);end if;
 if cutoffs[3]>=(w->'input'->'record'->>'known_at')::timestamptz then return outcome||jsonb_build_object('reason','CURRENT_PLAN_MUST_FOLLOW_HOLDOUT');end if;
 select x into current_slice from jsonb_array_elements(w->'current_source'->'cutting'->'slices')x where(x->>'roll_id')::uuid=(w->>'roll_id')::uuid;
 qty:=cp7_cutting_learning.number(current_slice->'consumed_native',true);
 if qty is null or qty<=0 then return outcome||jsonb_build_object('reason','CURRENT_NATIVE_CONSUMPTION_UNAVAILABLE');end if;
 if current_slice->'material_issue_posted'='true'::jsonb and w->'input'->'preknown_before_physical'='true'::jsonb then
  select sum(cp7_cutting_learning.number(x->'qty_pcs',false,true))into pcs from jsonb_array_elements(current_slice->'outputs')x;
 end if;
 return cp7_cutting_learning.evaluate(scope->'records',jsonb_build_object('context',policy.context,'current_batch_key',w->>'group_id',
  'policy_known_at',cp7_planning.utc(policy.known_at),'train_through',cp7_planning.utc(cutoffs[1]),'calibration_through',cp7_planning.utc(cutoffs[2]),
  'evaluation_through',cp7_planning.utc(cutoffs[3]),'input_known_at',w->'input'->'record'->'known_at','coverage',policy.coverage::text,
  'consumed',qty::text,'width_cm',w->'feature'->'width_cm','actual_pcs',pcs::text,'source_complete',true))
  ||jsonb_build_object('prospective_policy_id',policy.id,'sample_scope',scope->'sample_scope');
end $$;

create function cp7_cutting_model.command(p_payload jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''as $$
#variable_conflict use_variable
declare a jsonb;actor uuid;p jsonb;w jsonb;s jsonb;fresh jsonb;scope jsonb;new_scope jsonb;
 cached cp7_cutting_model.requests%rowtype;policy cp7_cutting_model.policies%rowtype;previous cp7_cutting_model.policies%rowtype;
 run cp7_cutting_model.runs%rowtype;result jsonb;at timestamptz;
begin
 a:=cp7_cutting_inputs.access_now(true);actor:=(a->>'actor')::uuid;p:=cp7_cutting_model.payload(p_payload);
 if p_request is null or p_lookup is null then raise exception 'CP7_CUTTING_MODEL_REQUEST';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:CUTTING_MODEL_REQUEST:'||actor::text||':'||p_request::text,0));
 if cp7_cutting_inputs.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_MODEL_ACCESS_CHANGED';end if;
 select *into cached from cp7_cutting_model.requests where requests.actor=actor and request_id=p_request;
 if cached.request_id is not null then
  if cached.payload<>p then raise exception 'CP7_CUTTING_MODEL_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then
  result:=jsonb_build_object('status','NOT_COMMITTED','request_id',p_request,'action',p->'action','policy',null,'model',null);
  insert into cp7_cutting_model.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:CUTTING_INPUT_GROUP:'||actor::text||':'||(p->>'group_id'),0));
  if cp7_cutting_inputs.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_MODEL_ACCESS_CHANGED';end if;
  w:=cp7_cutting_model.workspace((p->>'group_id')::uuid,(p->>'roll_id')::uuid);s:=cp7_cutting_inputs.source((p->>'group_id')::uuid);
  if w->'input'->'group'->>'version'is distinct from p->>'expected_group_version'
   or w->'input'->'record'->>'version'is distinct from p->>'expected_input_version'
   or w->'input'->'record_matches_native_identity'is distinct from'true'::jsonb or jsonb_typeof(w->'feature')is distinct from'object'then raise exception 'CP7_CUTTING_MODEL_SOURCE_CHANGED';end if;
  at:=clock_timestamp();
  if p->>'action'='POLICY' then
   perform pg_advisory_xact_lock(hashtextextended('CP7:CUTTING_MODEL_POLICY:'||actor::text||':'||(w->'feature'->'context')::text,0));
   select *into previous from cp7_cutting_model.policies where policies.actor=actor and context=w->'feature'->'context'order by known_at desc,id desc limit 1;
   if previous.id is distinct from(p->>'expected_policy_id')::uuid then raise exception 'CP7_CUTTING_MODEL_POLICY_CHANGED';end if;
   if cp7_cutting_inputs.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_MODEL_ACCESS_CHANGED';end if;
   at:=clock_timestamp();
   insert into cp7_cutting_model.policies values(gen_random_uuid(),actor,p_request,at,w->'feature'->'context',(p->>'coverage')::numeric,
    (p->>'train_batches')::integer,(p->>'calibration_batches')::integer,(p->>'holdout_batches')::integer,previous.id)returning *into policy;
   result:=jsonb_build_object('status','COMMITTED','request_id',p_request,'action','POLICY','policy',cp7_cutting_model.policy_view(policy),'model',null);
  else
   select *into policy from cp7_cutting_model.policies where id=(p->>'policy_id')::uuid and policies.actor=actor;
   if policy.id is null or policy.context is distinct from w->'feature'->'context'then raise exception 'CP7_CUTTING_MODEL_POLICY_CONTEXT';end if;
   scope:=cp7_cutting_model.collect(actor,(p->>'group_id')::uuid);w:=w||jsonb_build_object('current_source',s);
   insert into cp7_cutting_model.runs values(gen_random_uuid(),actor,p_request,clock_timestamp(),policy.id,(w->'input'->'record'->>'id')::uuid,
    (p->>'group_id')::uuid,(p->>'roll_id')::uuid,scope,cp7_cutting_model.evaluate(scope,policy,w))returning *into run;
   result:=jsonb_build_object('status','COMMITTED','request_id',p_request,'action','CHECK','policy',cp7_cutting_model.policy_view(policy),
    'model',jsonb_build_object('id',run.id,'known_at',cp7_planning.utc(run.known_at),'input_record_id',run.input_record_id,
     'source_scope',scope,'evaluation',run.evaluation,'business_write',false,'automatic_activation',false,'production_go',false));
  end if;
  fresh:=cp7_cutting_inputs.source((p->>'group_id')::uuid);
  if fresh is distinct from s then raise exception 'CP7_CUTTING_MODEL_SOURCE_CHANGED';end if;
  insert into cp7_cutting_model.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 w:=cp7_cutting_model.workspace((p->>'group_id')::uuid,(p->>'roll_id')::uuid);
 if result->'model'<>'null'::jsonb then new_scope:=cp7_cutting_model.collect(actor,(p->>'group_id')::uuid);end if;
 if cached.request_id is null and not p_lookup and p->>'action'='CHECK'and new_scope is distinct from scope then raise exception 'CP7_CUTTING_MODEL_HISTORY_CHANGED';end if;
 if cp7_cutting_inputs.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_MODEL_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-cutting-model-command.v1','actor_scope_id',actor,'result',result,'current',w,
  'original_matches_current_inputs',coalesce(result->>'status'='COMMITTED'and(result->'model'->>'input_record_id')::uuid=(w->'input'->'record'->>'id')::uuid,false),
  'original_matches_current_history',coalesce(result->>'status'='COMMITTED'and result->'model'->'source_scope'=new_scope,false),
  'original_matches_current_policy',coalesce(result->>'status'='COMMITTED'and result->'policy'->>'id'=w->'policy'->>'id',false),
  'business_write',false,'automatic_activation',false,'production_go',false);
end $$;
alter function cp7_cutting_model.payload(jsonb)owner to cp7_capture;
alter function cp7_cutting_model.policy_view(cp7_cutting_model.policies)owner to cp7_capture;
alter function cp7_cutting_model.workspace(uuid,uuid)owner to cp7_capture;
alter function cp7_cutting_model.collect(uuid,uuid)owner to cp7_capture;
alter function cp7_cutting_model.evaluate(jsonb,cp7_cutting_model.policies,jsonb)owner to cp7_capture;
alter function cp7_cutting_model.command(jsonb,uuid,boolean)owner to cp7_capture;
revoke all on all functions in schema cp7_cutting_model from public,anon,authenticated,service_role;
create function public.erp_cp7_get_cutting_model_workspace_v1(p_group uuid,p_roll uuid)returns jsonb language sql volatile security definer set search_path=''as $$select cp7_cutting_model.workspace(p_group,p_roll)$$;
create function public.erp_cp7_capture_cutting_model_v1(p_payload jsonb,p_request uuid)returns jsonb language sql volatile security definer set search_path=''as $$select cp7_cutting_model.command(p_payload,p_request,false)$$;
create function public.erp_cp7_get_cutting_model_request_v1(p_payload jsonb,p_request uuid)returns jsonb language sql volatile security definer set search_path=''as $$select cp7_cutting_model.command(p_payload,p_request,true)$$;
grant create on schema public to cp7_capture;
alter function public.erp_cp7_get_cutting_model_workspace_v1(uuid,uuid)owner to cp7_capture;
alter function public.erp_cp7_capture_cutting_model_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_get_cutting_model_request_v1(jsonb,uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_get_cutting_model_workspace_v1(uuid,uuid),public.erp_cp7_capture_cutting_model_v1(jsonb,uuid),public.erp_cp7_get_cutting_model_request_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_cutting_model_workspace_v1(uuid,uuid),public.erp_cp7_capture_cutting_model_v1(jsonb,uuid),public.erp_cp7_get_cutting_model_request_v1(jsonb,uuid)to authenticated;
