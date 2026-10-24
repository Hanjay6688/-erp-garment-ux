-- Explicit prospective model policy metadata. No forecast caller is replaced.
create schema cp7_model_policy authorization cp7_capture;
revoke all on schema cp7_model_policy from public,anon,authenticated,service_role;
create table cp7_model_policy.policies(
 id uuid primary key,revision bigint not null unique check(revision>0),
 registry_id text not null unique references cp7_model_native.registry(id),
 state text not null check(state in('ACTIVE','SUSPENDED')),config jsonb not null,
 template_hash text not null,reason text not null,actor uuid not null,request_id uuid not null,
 recorded_at timestamptz not null
);
create table cp7_model_policy.commands(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
alter table cp7_model_policy.policies owner to cp7_capture;
alter table cp7_model_policy.commands owner to cp7_capture;
alter table cp7_model_policy.policies enable row level security;
alter table cp7_model_policy.commands enable row level security;
create policy no_access on cp7_model_policy.policies for all to public using(false)with check(false);
create policy no_access on cp7_model_policy.commands for all to public using(false)with check(false);
revoke all on cp7_model_policy.policies,cp7_model_policy.commands from public,anon,authenticated,service_role;
create trigger immutable_policy before update or delete on cp7_model_policy.policies
 for each row execute function cp7_private.immutable_run();
create trigger immutable_command before update or delete on cp7_model_policy.commands
 for each row execute function cp7_private.immutable_run();

create function cp7_model_policy.access_now(writing boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare access_value jsonb;
begin
 access_value:=cp7_schedule_native.access_now(writing);
 if writing and coalesce(access_value->'profile'->>'role_code','')not in('OWNER','ADMIN')then
  raise exception using errcode='42501',message='CP7_MODEL_POLICY_OWNER_ADMIN_REQUIRED';end if;
 return access_value;
end $$;

create function cp7_model_policy.template()returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare configuration jsonb;model_template jsonb;
begin
 select r.configuration into configuration from cp7_model_native.registry r where r.id='cp7.native-model-policy.v1';
 if configuration is null then raise exception 'CP7_MODEL_POLICY_TEMPLATE_UNAVAILABLE';end if;
 -- These fixed prospective candidate definitions are reviewed separately from
 -- the user-entered activation thresholds. No proposal threshold is inherited.
 model_template:=jsonb_build_object('baseline',configuration->'baseline','challengers',configuration->'challengers');
 return jsonb_build_object('models',model_template,'hash',encode(pg_catalog.sha256(convert_to(model_template::text,'UTF8')),'hex'));
end $$;

create function cp7_model_policy.source_at(p_at timestamptz)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('policy',jsonb_build_object('id',p.id,'revision',p.revision::text,'registry_id',p.registry_id,
  'recorded_at',cp7_planning.utc(p.recorded_at),'state',p.state,'reason',p.reason,'config',p.config),
  'actor_scope_id',p.actor,'request_id',p.request_id,'template_hash',p.template_hash)
 from cp7_model_policy.policies p where p.recorded_at<=p_at order by p.revision desc limit 1
$$;

create function cp7_model_policy.workspace()returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare access_value jsonb;current_row jsonb;model_template jsonb;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 access_value:=cp7_model_policy.access_now(false);current_row:=cp7_model_policy.source_at(clock_timestamp());model_template:=cp7_model_policy.template();
 outcome:=jsonb_build_object('contract_version','cp7.model-activation-policy-workspace.v1','actor_scope_id',access_value->'actor',
  'access_epoch',encode(pg_catalog.sha256(convert_to(access_value::text,'UTF8')),'hex'),
  'can_write',coalesce(access_value->'profile'->>'role_code','')in('OWNER','ADMIN')and erp.has_permission('master.product.manage')is true,
  'revision',coalesce(current_row->'policy'->>'revision','0'),'current',current_row,
  'state',coalesce(current_row->'policy'->>'state','UNREVIEWED'),'model_template',model_template,
  'forecast_applied',false,'production_go',false);
 if cp7_model_policy.access_now(false)is distinct from access_value then raise exception using errcode='42501',message='CP7_MODEL_POLICY_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function cp7_model_policy.apply(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare access_value jsonb;old_command cp7_model_policy.commands%rowtype;previous cp7_model_policy.policies%rowtype;
 model_template jsonb;configuration jsonb;policy_row jsonb;outcome jsonb;action text;reason text;expected bigint;revision bigint;
 policy_id uuid:=gen_random_uuid();registry_id text;recorded timestamptz;template_hash text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 access_value:=cp7_model_policy.access_now(true);
 if p_request is null then raise exception 'CP7_MODEL_POLICY_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p_payload,array['contract_version','action','config','template_hash','reason','reviewed','expected_revision','access_epoch']);
 if p_payload->>'contract_version'is distinct from'cp7.model-activation-policy-command.v1'then raise exception 'CP7_MODEL_POLICY_CONTRACT';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_model_policy.access_now(true)is distinct from access_value then raise exception using errcode='42501',message='CP7_MODEL_POLICY_ACCESS_CHANGED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:MODEL:POLICY:REQUEST:'||(access_value->>'actor')||':'||p_request::text,0));
 if cp7_model_policy.access_now(true)is distinct from access_value then raise exception using errcode='42501',message='CP7_MODEL_POLICY_ACCESS_CHANGED';end if;
 select *into old_command from cp7_model_policy.commands c where c.actor=(access_value->>'actor')::uuid and c.request_id=p_request;
 if found then
  if old_command.payload<>p_payload then raise exception 'CP7_MODEL_POLICY_REQUEST_CHANGED';end if;
  return old_command.result;
 end if;
 if p_payload->>'access_epoch'is distinct from encode(pg_catalog.sha256(convert_to(cp7_model_policy.access_now(false)::text,'UTF8')),'hex')then
  raise exception using errcode='42501',message='CP7_MODEL_POLICY_ACCESS_CHANGED';end if;
 action:=p_payload->>'action';reason:=btrim(p_payload->>'reason');
 if action is null or action not in('SET','SUSPEND')or p_payload->'reviewed'is distinct from'true'::jsonb
  or jsonb_typeof(p_payload->'reason')is distinct from'string'or reason is null or length(reason)not between 1 and 1000
  or jsonb_typeof(p_payload->'expected_revision')is distinct from'string'or p_payload->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'then raise exception 'CP7_MODEL_POLICY_REVIEW';end if;
 expected:=(p_payload->>'expected_revision')::bigint;
 perform pg_advisory_xact_lock(hashtextextended('CP7:MODEL:POLICY:GLOBAL',0));
 if cp7_model_policy.access_now(true)is distinct from access_value then raise exception using errcode='42501',message='CP7_MODEL_POLICY_ACCESS_CHANGED';end if;
 select *into previous from cp7_model_policy.policies p order by p.revision desc limit 1;
 revision:=coalesce(previous.revision,0);
 if expected<>revision then raise exception 'CP7_MODEL_POLICY_REVISION_CHANGED';end if;
 if action='SET'then
  model_template:=cp7_model_policy.template();template_hash:=model_template->>'hash';
  if p_payload->>'template_hash'is distinct from template_hash then raise exception 'CP7_MODEL_POLICY_TEMPLATE_CHANGED';end if;
  configuration:=p_payload->'config';
 else
  if previous.id is null then raise exception 'CP7_MODEL_POLICY_NOT_SELECTED';end if;
  if p_payload->'config'is distinct from'null'::jsonb or p_payload->'template_hash'is distinct from'null'::jsonb then raise exception 'CP7_MODEL_POLICY_SUSPEND_FIELDS';end if;
  configuration:=previous.config;
  select jsonb_build_object('models',jsonb_build_object('baseline',r.configuration->'baseline','challengers',r.configuration->'challengers'),
   'hash',previous.template_hash)into model_template from cp7_model_native.registry r where r.id=previous.registry_id;
  template_hash:=previous.template_hash;
  if model_template is null or encode(pg_catalog.sha256(convert_to((model_template->'models')::text,'UTF8')),'hex')<>template_hash then raise exception 'CP7_MODEL_POLICY_PRIOR_TEMPLATE_CHANGED';end if;
 end if;
 recorded:=clock_timestamp();registry_id:='cp7.owner-model-policy.'||policy_id::text;
 policy_row:=jsonb_build_object('id',policy_id,'revision',(revision+1)::text,'registry_id',registry_id,
  'recorded_at',cp7_planning.utc(recorded),'state',case when action='SET'then'ACTIVE'else'SUSPENDED'end,'reason',reason,'config',configuration);
 perform cp7_model_activation_gate.policy(policy_row);
 insert into cp7_model_native.registry(id,registered_at,configuration)values(registry_id,recorded,
  (model_template->'models')||jsonb_build_object('policy',configuration->'promotion','meaning','EXPLICIT_OWNER_ACTIVATION_POLICY',
   'activation_policy',jsonb_build_object('id',policy_id,'revision',(revision+1)::text,'recorded_at',cp7_planning.utc(recorded))));
 insert into cp7_model_policy.policies(id,revision,registry_id,state,config,template_hash,reason,actor,request_id,recorded_at)
 values(policy_id,revision+1,registry_id,policy_row->>'state',configuration,template_hash,reason,(access_value->>'actor')::uuid,p_request,recorded);
 outcome:=jsonb_build_object('contract_version','cp7.model-activation-policy-outcome.v1','request_id',p_request,
  'actor_scope_id',access_value->'actor','policy',policy_row,'template_hash',template_hash,'forecast_applied',false,'production_go',false);
 insert into cp7_model_policy.commands(actor,request_id,payload,result)values((access_value->>'actor')::uuid,p_request,p_payload,outcome);
 if action='SET'and cp7_model_policy.template()is distinct from model_template then raise exception 'CP7_MODEL_POLICY_TEMPLATE_CHANGED';end if;
 if cp7_model_policy.access_now(true)is distinct from access_value then raise exception using errcode='42501',message='CP7_MODEL_POLICY_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function public.erp_cp7_get_model_activation_policy_v1()returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'set statement_timeout='8s'as $$select cp7_model_policy.workspace()$$;
create function public.erp_cp7_save_model_activation_policy_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'set statement_timeout='8s'as $$select cp7_model_policy.apply(p_payload,p_request)$$;

alter function cp7_model_policy.access_now(boolean)owner to cp7_capture;
alter function cp7_model_policy.template()owner to cp7_capture;
alter function cp7_model_policy.source_at(timestamp with time zone)owner to cp7_capture;
alter function cp7_model_policy.workspace()owner to cp7_capture;
alter function cp7_model_policy.apply(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_get_model_activation_policy_v1()owner to cp7_capture;
alter function public.erp_cp7_save_model_activation_policy_v1(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_model_policy from public,anon,authenticated,service_role;
revoke all on function public.erp_cp7_get_model_activation_policy_v1(),public.erp_cp7_save_model_activation_policy_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_model_activation_policy_v1(),public.erp_cp7_save_model_activation_policy_v1(jsonb,uuid)to authenticated;
