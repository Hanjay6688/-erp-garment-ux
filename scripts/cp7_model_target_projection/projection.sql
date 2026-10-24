-- Private arithmetic prototype. It does not select/authorize a model or replace
-- a caller. A future consumer must use current, server-owned v2 admission.
create schema cp7_model_target_projection authorization cp7_capture;
revoke all on schema cp7_model_target_projection from public,anon,authenticated,service_role;

create function cp7_model_target_projection.sum_window(values_json jsonb,from_day numeric,through_day numeric)returns numeric
language plpgsql immutable security invoker set search_path=''as $$
declare amount numeric:=0;item jsonb;ord bigint;value numeric;
begin
 if jsonb_typeof(values_json)is distinct from'array'or jsonb_array_length(values_json)not between 1 and 90
  or from_day is null or through_day is null or from_day<0 or through_day<from_day
  or through_day>jsonb_array_length(values_json)then raise exception 'CP7_MODEL_TARGET_WINDOW';end if;
 for item,ord in select x.v,x.o from jsonb_array_elements(values_json)with ordinality x(v,o)loop
  -- Model kernels retain twelve decimal places; never round the daily vector
  -- to a whole PCS or average it before the final target ceiling.
  if jsonb_typeof(item)is distinct from'string'or item#>>'{}'!~'^(0|[1-9][0-9]{0,29})(\.[0-9]{1,30})?$'then
   raise exception 'CP7_MODEL_TARGET_FORECAST_DECIMAL';end if;
  value:=(item#>>'{}')::numeric;
  amount:=amount+value*greatest(0,least(through_day,ord::numeric)-greatest(from_day,ord::numeric-1));
 end loop;
 return amount;
end $$;

create function cp7_model_target_projection.project(v jsonb,forecast jsonb,p_day date)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare base jsonb;outcome jsonb;values_json jsonb;l numeric;r numeric;h numeric;b numeric;
 lead_demand numeric;review_demand numeric;lead_safety numeric;horizon_safety numeric;
 origin date;forecast_days integer;mode text;
begin
 if v->>'contract_version'is distinct from'cp7.target-input.v2'then raise exception 'CP7_MODEL_TARGET_BASELINE_CONTRACT';end if;
 -- This is the qualified shared baseline kernel, including its exact UNKNOWN,
 -- double-buffer, statistical minimum and explicit service-level guards.
 base:=cp7_baseline.target(v);
 perform cp7_wip.fields(forecast,array['contract_version','forecast_from_date','forecasts']);
 if forecast->>'contract_version'is distinct from'cp7.model-target-vector.v1'or p_day is null then
  raise exception 'CP7_MODEL_TARGET_VECTOR_CONTRACT';end if;
 origin:=cp7_demand.day(forecast->'forecast_from_date');values_json:=forecast->'forecasts';
 perform cp7_model_target_projection.sum_window(values_json,0,0);
 forecast_days:=jsonb_array_length(values_json);
 outcome:=jsonb_build_object('contract_version','cp7.model-target-projection.v1','state','BASELINE_REQUIRED',
  'reason',null,'baseline',base,'projected',null,'forecast',forecast,'model_authorized',false,
  'caller_replaced',false,'forecast_applied',false,'production_go',false);
 if origin<>p_day then return outcome||jsonb_build_object('reason','DATED_FORECAST_ORIGIN_NOT_CURRENT');end if;
 if base->>'status'is distinct from'SCENARIO'then
  return outcome||jsonb_build_object('reason','EXISTING_BASELINE_INPUTS_NOT_READY');end if;
 l:=cp7_demand.decimal(v->'lead_days');r:=cp7_demand.decimal(v->'review_days');h:=l+r;mode:=v->>'mode';
 b:=case when mode='DAYS'then cp7_demand.decimal(v->'buffer_days')else 0 end;
 -- No flat extrapolation, truncation, repeated last day, or averaged horizon.
 if greatest(l+b,h+b)>forecast_days then
  return outcome||jsonb_build_object('reason','FULL_DATED_TARGET_AND_REORDER_VECTOR_REQUIRED');end if;
 lead_demand:=cp7_model_target_projection.sum_window(values_json,0,l);
 review_demand:=cp7_model_target_projection.sum_window(values_json,l,h);
 if mode='DAYS'then
  lead_safety:=cp7_model_target_projection.sum_window(values_json,l,l+b);
  horizon_safety:=cp7_model_target_projection.sum_window(values_json,h,h+b);
 else
  -- Preserve the already selected baseline variation assumption exactly.
  -- Historical demand SD is not relabelled as calibrated forecast error.
  lead_safety:=(base->>'lead_safety_pcs')::numeric;
  horizon_safety:=(base->>'horizon_safety_pcs')::numeric;
 end if;
 return outcome||jsonb_build_object('state','ARITHMETIC_CANDIDATE','reason',
  case when mode='DAYS'then'ONE_DATED_VECTOR_WITH_ONE_EXPLICIT_DAYS_BUFFER'
   else'DATED_POINT_FORECAST_WITH_EXISTING_HISTORICAL_VARIATION_ASSUMPTION'end,
  'projected',jsonb_build_object('kernel_version','target-forecast-vector-1','horizon_days',h::text,
   'lead_demand_pcs',lead_demand::text,'review_demand_pcs',review_demand::text,
   'lead_safety_pcs',lead_safety::text,'horizon_safety_pcs',horizon_safety::text,
   'reorder_point_pcs',ceil(lead_demand+lead_safety)::text,
   'target_pcs',ceil(lead_demand+review_demand+horizon_safety)::text,
   'buffer_basis',case when mode='DAYS'then'ONE_EXPLICIT_DAYS_BUFFER'else'BASELINE_INDEPENDENT_DAILY_VARIATION_ASSUMPTION'end,
   'calibrated_forecast_interval',false));
end $$;

alter function cp7_model_target_projection.sum_window(jsonb,numeric,numeric)owner to cp7_capture;
alter function cp7_model_target_projection.project(jsonb,jsonb,date)owner to cp7_capture;
revoke all on all functions in schema cp7_model_target_projection from public,anon,authenticated,service_role;
