-- Private v2 adapter; v1 datasets, captures, results and request namespace stay intact.
-- No installer, public facade, policy default or forecast consumer is added here.
create schema cp7_model_registry_adapter authorization cp7_capture;
revoke all on schema cp7_model_registry_adapter from public,anon,authenticated,service_role;

create function cp7_model_registry_adapter.engine()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select md5(string_agg(pg_get_functiondef(p.oid),E'\n'order by n.nspname,p.proname,p.oid::regprocedure::text))
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname in('cp7_models','cp7_model_native','cp7_model_activation_gate','cp7_model_policy','cp7_model_registry_adapter')
$$;

create function cp7_model_registry_adapter.bind(d jsonb,policy_source jsonb,registry jsonb,p_engine text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare policy jsonb;configuration jsonb;model_template jsonb;outcome jsonb;legacy_hash text;
begin
 perform cp7_wip.fields(d,array['history_run_id','query','target_key','size_id','known_as_of','from_date','through_date',
  'series','registry_id','registered_at','configuration','product_sku','product_name','source_hash','history_source_hash',
  'engine_hash','fallback_daily_mean','refs','knowledge_basis','no_retrospective_availability_backfill']);
 if d->>'knowledge_basis'is distinct from'ACTUAL_IMMUTABLE_NATIVE_CAPTURE_TIMES'
  or d->'no_retrospective_availability_backfill'is distinct from'true'::jsonb
  or d->>'registry_id'is distinct from'cp7.native-model-policy.v1'
  or d->'configuration'->>'meaning'is distinct from'TECHNICAL_PROPOSAL_NOT_OWNER_SERVICE_TARGET'
  or(d->>'source_hash')is null or(d->>'source_hash')!~'^[0-9a-f]{64}$'
  or(d->>'engine_hash')is null or(d->>'engine_hash')!~'^[0-9a-f]{32}$'
  or p_engine is null or p_engine!~'^[0-9a-f]{32}$'then raise exception 'CP7_MODEL_REGISTRY_NATIVE_BINDING';end if;
 perform cp7_demand.instant(d->'known_as_of');
 if cp7_model_native.query(d->'query')is distinct from d->'query'
  or d->'query'->'target_key'is distinct from d->'target_key'
  or d->'query'->'history_run_id'is distinct from d->'history_run_id'
  or split_part(d->>'target_key',':',2)is distinct from d->>'size_id'then raise exception 'CP7_MODEL_REGISTRY_QUERY_BINDING';end if;
 -- Verify the existing adapter's exact input digest before extending its meaning.
 legacy_hash:=encode(pg_catalog.sha256(convert_to(jsonb_build_object('history_source_hash',d->'history_source_hash',
  'series',d->'series','registry',d->'configuration','registered_at',d->'registered_at','engine',d->'engine_hash')::text,'UTF8')),'hex');
 if legacy_hash is distinct from d->>'source_hash'then raise exception 'CP7_MODEL_REGISTRY_NATIVE_SOURCE_CHANGED';end if;
 outcome:=d;
 if policy_source is not null and policy_source<>'null'::jsonb then
  perform cp7_wip.fields(policy_source,array['policy','actor_scope_id','request_id','template_hash']);
  policy:=cp7_model_activation_gate.policy(policy_source->'policy');
  if jsonb_typeof(policy_source->'actor_scope_id')is distinct from'string'
   or jsonb_typeof(policy_source->'request_id')is distinct from'string'
   or(policy_source->>'actor_scope_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or(policy_source->>'request_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or(policy_source->>'template_hash')is null or(policy_source->>'template_hash')!~'^[0-9a-f]{64}$'
   or cp7_demand.instant(policy->'recorded_at')>cp7_demand.instant(d->'known_as_of')then raise exception 'CP7_MODEL_REGISTRY_POLICY_NOT_KNOWN';end if;
  perform cp7_wip.fields(registry,array['id','registered_at','configuration']);
  configuration:=registry->'configuration';
  perform cp7_wip.fields(configuration,array['baseline','challengers','policy','meaning','activation_policy']);
  model_template:=jsonb_build_object('baseline',configuration->'baseline','challengers',configuration->'challengers');
  if registry->'id'is distinct from policy->'registry_id'
   or cp7_demand.instant(registry->'registered_at')is distinct from cp7_demand.instant(policy->'recorded_at')
   or configuration->>'meaning'is distinct from'EXPLICIT_OWNER_ACTIVATION_POLICY'
   or configuration->'policy'is distinct from policy->'config'->'promotion'
   or configuration->'activation_policy'is distinct from jsonb_build_object('id',policy->'id','revision',policy->'revision','recorded_at',policy->'recorded_at')
   or encode(pg_catalog.sha256(convert_to(model_template::text,'UTF8')),'hex')is distinct from policy_source->>'template_hash'
   then raise exception 'CP7_MODEL_REGISTRY_POLICY_BINDING';end if;
  -- The reviewed registry fixes every candidate's parameters. Only explicitly
  -- permitted candidates participate in selection; an unpermitted winner must
  -- not hide a permitted challenger that actually beats the baseline.
  configuration:=jsonb_set(configuration,'{challengers}',(select coalesce(jsonb_agg(x order by ord),'[]'::jsonb)
   from jsonb_array_elements(configuration->'challengers')with ordinality a(x,ord)
   where policy->'config'->'allowed_methods'?(x->>'method')));
  outcome:=outcome||jsonb_build_object('registry_id',registry->'id','registered_at',registry->'registered_at','configuration',configuration);
 elsif registry is not null and registry<>'null'::jsonb then raise exception 'CP7_MODEL_REGISTRY_UNEXPECTED_REGISTRY';
 end if;
 outcome:=(outcome-'source_hash')||jsonb_build_object('contract_version','cp7.native-model-dataset.v2',
  'policy_source',policy_source,'native_source_hash',d->'source_hash','native_engine_hash',d->'engine_hash','engine_hash',p_engine);
 return outcome||jsonb_build_object('source_hash',encode(pg_catalog.sha256(convert_to(outcome::text,'UTF8')),'hex'));
end $$;

create function cp7_model_registry_adapter.dataset(q jsonb,p_actor uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare native_dataset jsonb;policy_source jsonb;registry jsonb;
begin
 native_dataset:=cp7_model_native.dataset(cp7_model_native.query(q),p_actor);
 policy_source:=cp7_model_policy.source_at(cp7_demand.instant(native_dataset->'known_as_of'));
 if policy_source is not null then
  select jsonb_build_object('id',r.id,'registered_at',cp7_planning.utc(r.registered_at),'configuration',r.configuration)
   into registry from cp7_model_native.registry r where r.id=policy_source->'policy'->>'registry_id';
  if registry is null then raise exception 'CP7_MODEL_REGISTRY_POLICY_REGISTRY_UNAVAILABLE';end if;
 end if;
 return cp7_model_registry_adapter.bind(native_dataset,policy_source,registry,cp7_model_registry_adapter.engine());
end $$;

create function cp7_model_registry_adapter.assess(d jsonb,current_context jsonb,current_policy_source jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare evaluation jsonb;admission jsonb;hash text;policy_current boolean;no_challenger boolean;
begin
 if d->>'contract_version'is distinct from'cp7.native-model-dataset.v2'then raise exception 'CP7_MODEL_REGISTRY_DATASET_CONTRACT';end if;
 hash:=encode(pg_catalog.sha256(convert_to((d-'source_hash')::text,'UTF8')),'hex');
 if hash is distinct from d->>'source_hash'then raise exception 'CP7_MODEL_REGISTRY_DATASET_CHANGED';end if;
 no_challenger:=jsonb_array_length(d->'configuration'->'challengers')=0;
 -- Empty permission is an explicit baseline-only policy. The legacy builder
 -- requires at least one challenger; do not invent one or rewrite v1 for it.
 if not no_challenger then evaluation:=cp7_model_native.build(d);end if;
 admission:=cp7_model_activation_gate.decide(d,evaluation,d->'policy_source'->'policy',current_context);
 if no_challenger and admission->>'reason'='NATIVE_EVALUATION_REQUIRED'then
  admission:=admission||jsonb_build_object('reason','NO_EXPLICITLY_ALLOWED_CHALLENGER');
 end if;
 policy_current:=coalesce(current_policy_source,'null'::jsonb)is not distinct from d->'policy_source';
 if not policy_current then
  admission:=admission||jsonb_build_object('state','BASELINE_REQUIRED','reason','ACTIVATION_POLICY_CHANGED',
   'selected_model',null,'forecast',null);
 end if;
 return jsonb_build_object('contract_version','cp7.native-model-assessment.v2','source_hash',d->'source_hash','engine_hash',d->'engine_hash',
  'source',jsonb_build_object('history_run_id',d->'history_run_id','target_key',d->'target_key','size_id',d->'size_id',
   'product_sku',d->'product_sku','product_name',d->'product_name','from_date',d->'from_date','through_date',d->'through_date',
   'known_as_of',d->'known_as_of','registry_id',d->'registry_id','registered_at',d->'registered_at',
   'horizon_days',d->'query'->'horizon_days','series_revision_count',jsonb_array_length(d->'series'),
   'knowledge_basis',d->'knowledge_basis','no_retrospective_availability_backfill',d->'no_retrospective_availability_backfill'),
  'policy_source',d->'policy_source','policy_current',policy_current,'evaluation',evaluation,
  'evaluation_state',case when no_challenger then'NOT_REQUESTED_NO_ALLOWED_CHALLENGER'else'EVALUATED'end,
  'baseline',jsonb_build_object('method','MEAN','daily_mean',d->'fallback_daily_mean'),'activation',admission,
  'current_consumption_recheck_required',true,'automatic_activation',false,'apply_allowed',false,'forecast_applied',false,'production_go',false);
end $$;

alter function cp7_model_registry_adapter.engine()owner to cp7_capture;
alter function cp7_model_registry_adapter.bind(jsonb,jsonb,jsonb,text)owner to cp7_capture;
alter function cp7_model_registry_adapter.dataset(jsonb,uuid)owner to cp7_capture;
alter function cp7_model_registry_adapter.assess(jsonb,jsonb,jsonb)owner to cp7_capture;
revoke all on all functions in schema cp7_model_registry_adapter from public,anon,authenticated,service_role;
