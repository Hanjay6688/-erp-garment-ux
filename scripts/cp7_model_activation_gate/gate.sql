-- Private eligibility prototype. No default policy, registry or business write.
create schema cp7_model_activation_gate authorization cp7_capture;
revoke all on schema cp7_model_activation_gate from public,anon,authenticated,service_role;

create function cp7_model_activation_gate.policy(p jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare config jsonb;method jsonb;minimum_days integer;maximum_horizon integer;summary jsonb;
begin
 perform cp7_wip.fields(p,array['id','revision','registry_id','recorded_at','state','reason','config']);
 if jsonb_typeof(p->'id')is distinct from'string'or(p->>'id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or cp7_wip.pcs(p->'revision')<1 then raise exception 'CP7_MODEL_ACTIVATION_POLICY_ID';end if;
 perform(p->>'id')::uuid;perform cp7_wip.key(p->'registry_id');perform cp7_demand.instant(p->'recorded_at');
 if p->>'state'is null or p->>'state'not in('ACTIVE','SUSPENDED')then raise exception 'CP7_MODEL_ACTIVATION_POLICY_STATE';end if;
 if jsonb_typeof(p->'reason')is distinct from'string'or length(btrim(p->>'reason'))not between 1 and 1000 then raise exception 'CP7_MODEL_ACTIVATION_POLICY_REASON';end if;
 config:=p->'config';perform cp7_wip.fields(config,array['minimum_training_days','maximum_horizon_days','allowed_methods','promotion']);
 minimum_days:=cp7_wip.pcs(config->'minimum_training_days');maximum_horizon:=cp7_wip.pcs(config->'maximum_horizon_days');
 -- Bounds come from the existing Native366-day/90-horizon adapter. No factory
 -- minimum or winner threshold is supplied by this function.
 if minimum_days not between 1 and 366 or maximum_horizon not between 1 and 90 then raise exception 'CP7_MODEL_ACTIVATION_POLICY_BOUNDS';end if;
 perform cp7_demand.items(config->'allowed_methods',7);
 for method in select value from jsonb_array_elements(config->'allowed_methods')loop
  if jsonb_typeof(method)is distinct from'string'or(method#>>'{}')not in('NAIVE','MOVING_MEAN','SES','DAMPED_HOLT','SEASONAL_NAIVE','SBA','TSB')then raise exception 'CP7_MODEL_ACTIVATION_METHOD';end if;
 end loop;
 if(select count(distinct value)from jsonb_array_elements(config->'allowed_methods'))<>jsonb_array_length(config->'allowed_methods')then raise exception 'CP7_MODEL_ACTIVATION_DUPLICATE_METHOD';end if;
 summary:=jsonb_build_object('fold_count','0','requested_folds','0','mae',null,'signed_bias',null,'tail_abs_error',null);
 perform cp7_models.promotion(summary,summary,config->'promotion');
 return p;
end $$;

create function cp7_model_activation_gate.decide(d jsonb,r jsonb,p jsonb,current_context jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare policy jsonb;reason text;selected jsonb;forecast jsonb;recomputed jsonb;h integer;holdout jsonb;origin date;
begin
 perform cp7_wip.fields(current_context,array['target_key','size_id','source_hash','engine_hash','known_as_of','horizon_days','forecast_from_date']);
 perform cp7_wip.key(current_context->'target_key');perform cp7_wip.key(current_context->'size_id');
 perform cp7_wip.key(current_context->'source_hash');perform cp7_wip.key(current_context->'engine_hash');
 perform cp7_demand.instant(current_context->'known_as_of');h:=cp7_wip.pcs(current_context->'horizon_days');
 if(current_context->>'target_key')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or split_part(current_context->>'target_key',':',2)is distinct from current_context->>'size_id'
  or(current_context->>'source_hash')!~'^[0-9a-f]{64}$'or(current_context->>'engine_hash')!~'^[0-9a-f]{32}$'then raise exception 'CP7_MODEL_ACTIVATION_CONTEXT';end if;
 origin:=cp7_demand.day(current_context->'forecast_from_date');
 if origin<>(cp7_demand.instant(current_context->'known_as_of')at time zone'Asia/Jakarta')::date then raise exception 'CP7_MODEL_ACTIVATION_CURRENT_DAY';end if;
 if h not between 1 and 90 then raise exception 'CP7_MODEL_ACTIVATION_HORIZON';end if;
 if p is null or p='null'::jsonb then reason:='EXPLICIT_ACTIVATION_POLICY_REQUIRED';
 else
  policy:=cp7_model_activation_gate.policy(p);
  if policy->>'state'='SUSPENDED'then reason:='ACTIVATION_POLICY_SUSPENDED';
  elsif d is null or d='null'::jsonb or r is null or r='null'::jsonb then reason:='NATIVE_EVALUATION_REQUIRED';
  elsif d->>'knowledge_basis'is distinct from'ACTUAL_IMMUTABLE_NATIVE_CAPTURE_TIMES'
   or d->'no_retrospective_availability_backfill'is distinct from'true'::jsonb then reason:='NATIVE_KNOWLEDGE_PROOF_REQUIRED';
  elsif d->'target_key'is distinct from current_context->'target_key'or d->'size_id'is distinct from current_context->'size_id'
   or d->'source_hash'is distinct from current_context->'source_hash'or d->'engine_hash'is distinct from current_context->'engine_hash'
   or cp7_demand.instant(d->'known_as_of')>cp7_demand.instant(current_context->'known_as_of')then reason:='MODEL_EVIDENCE_NOT_CURRENT';
  elsif d->'configuration'->>'meaning'is distinct from'EXPLICIT_OWNER_ACTIVATION_POLICY'
   or d->'registry_id'is distinct from policy->'registry_id'
   or d->'configuration'->'activation_policy'is distinct from jsonb_build_object('id',policy->'id','revision',policy->'revision','recorded_at',policy->'recorded_at')
   or d->'configuration'->'policy'is distinct from policy->'config'->'promotion'
   or cp7_demand.instant(policy->'recorded_at')>cp7_demand.instant(d->'registered_at')then reason:='POLICY_NOT_PROSPECTIVELY_REGISTERED';
  elsif origin<>cp7_demand.day(d->'through_date')+1 then reason:='MODEL_FORECAST_ORIGIN_NOT_CURRENT';
  elsif h<>(d->'query'->>'horizon_days')::integer or h>(policy->'config'->>'maximum_horizon_days')::integer then reason:='MODEL_HORIZON_NOT_QUALIFIED';
  else
   -- This is a one-time admission proof over an immutable private dataset, not
   -- an arbitrary client result or a per-row forecast computation. Existing
   -- kernel workload and no-future-knowledge guards remain authoritative.
   recomputed:=cp7_model_native.build(d);
   if r is distinct from recomputed then raise exception 'CP7_MODEL_ACTIVATION_RESULT_MISMATCH';end if;
   if r->>'selection_status'is distinct from'CHALLENGER_RECOMMENDED'then reason:=r->>'reason';
   else
    selected:=(select x->'model'from jsonb_array_elements(r->'evaluation'->'challengers')x where x->'model'->>'id'=r->>'selected_model_id');
    forecast:=r->'forecast';
    if selected is null then raise exception 'CP7_MODEL_ACTIVATION_SELECTED_MODEL_MISSING';end if;
    if not(policy->'config'->'allowed_methods'? (selected->>'method'))then reason:='METHOD_NOT_EXPLICITLY_ALLOWED';
    elsif forecast->>'status'is distinct from'ELIGIBLE'then reason:='CURRENT_TRAINING_NOT_ELIGIBLE';
    elsif(forecast->>'training_count')::integer<(policy->'config'->>'minimum_training_days')::integer then reason:='CURRENT_TRAINING_BELOW_POLICY_MINIMUM';
    else
     holdout:=(select x from jsonb_array_elements(r->'evaluation'->'holdout'->'results')x where x->>'model_id'=r->>'selected_model_id');
     if r->'evaluation'->'holdout'->'used_for_selection'is distinct from'false'::jsonb then raise exception 'CP7_MODEL_ACTIVATION_HOLDOUT_SELECTION_FORBIDDEN';end if;
     if holdout is null or holdout->'score'is null or holdout->'score'='null'::jsonb then reason:='SEPARATE_HOLDOUT_INCOMPLETE';
     elsif jsonb_array_length(forecast->'forecasts')<>h or forecast->'method'is distinct from selected->'method'or forecast->'params'is distinct from selected->'params'then raise exception 'CP7_MODEL_ACTIVATION_FORECAST_BINDING';
     end if;
    end if;
   end if;
  end if;
 end if;
 return jsonb_build_object('contract_version','cp7.model-activation-gate.v1','state',case when reason is null then'ELIGIBLE'else'BASELINE_REQUIRED'end,
  'reason',coalesce(reason,'EXPLICIT_POLICY_PAIRED_BACKTEST_AND_CURRENT_NATIVE_EVIDENCE'),
  'target_key',current_context->'target_key','size_id',current_context->'size_id','source_hash',current_context->'source_hash',
  'engine_hash',current_context->'engine_hash','known_as_of',current_context->'known_as_of','horizon_days',h::text,'forecast_from_date',origin::text,
  'policy_id',policy->'id','policy_revision',policy->'revision','policy_recorded_at',policy->'recorded_at',
  'registry_id',policy->'registry_id','selected_model',case when reason is null then selected else null end,
  'forecast',case when reason is null then forecast else null end,'holdout_used_for_selection',false,
  'forecast_applied',false,'production_go',false);
end $$;

alter function cp7_model_activation_gate.policy(jsonb)owner to cp7_capture;
alter function cp7_model_activation_gate.decide(jsonb,jsonb,jsonb,jsonb)owner to cp7_capture;
revoke all on all functions in schema cp7_model_activation_gate from public,anon,authenticated,service_role;
