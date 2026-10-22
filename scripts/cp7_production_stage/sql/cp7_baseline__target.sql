create or replace function cp7_baseline.target(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare d numeric; l numeric; r numeric; b numeric; h numeric; target numeric; q numeric; sample jsonb; samples numeric[]:='{}';
 modern boolean:=v->>'contract_version'='cp7.target-input.v2';total numeric;days numeric:=1;sd numeric;z numeric;
 lead_safety numeric;horizon_safety numeric;lead_target numeric;
begin
 if modern then
  -- OW10: the Native FG reorder source and the production target use this
  -- same kernel. Keep total/days until the last arithmetic operation: rounding
  -- a repeating daily mean first can incorrectly add one whole PCS.
  perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','mode','daily_total_pcs','counted_days',
   'daily_sd','lead_days','review_days','buffer_days','service_level','refs']);
  perform cp7_demand.context(v,'cp7.target-input.v2');perform cp7_wip.refs(v->'refs');
 else
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','mode','daily_mean','lead_days','review_days','buffer_days','quantile','horizon_samples','refs']);
 perform cp7_demand.context(v,'cp7.target-input.v1');perform cp7_wip.refs(v->'refs');perform cp7_demand.items(v->'horizon_samples',10000);
 end if;
 if v->>'mode' is null or v->>'mode' not in ('DAYS','STATISTICAL') then raise exception 'CP7_BASELINE_BUFFER_MODE';end if;
 if modern then
  if(v->>'mode'='DAYS'and(v->'daily_sd'is distinct from'null'::jsonb or v->'service_level'is distinct from'null'::jsonb))
   or(v->>'mode'='STATISTICAL'and v->'buffer_days'is distinct from'null'::jsonb)then raise exception 'CP7_BASELINE_DOUBLE_BUFFER';end if;
 else
  if v->>'mode'='DAYS' and (v->'quantile'<>'null'::jsonb or jsonb_array_length(v->'horizon_samples')<>0) then raise exception 'CP7_BASELINE_DOUBLE_BUFFER';end if;
  if v->>'mode'='STATISTICAL' and (v->'buffer_days'<>'null'::jsonb or v->'daily_mean'<>'null'::jsonb) then raise exception 'CP7_BASELINE_DOUBLE_BUFFER';end if;
 end if;
 if v->'lead_days'='null'::jsonb or v->'review_days'='null'::jsonb then
  return jsonb_build_object('status','UNKNOWN','reason','HORIZON_UNKNOWN','inputs',v)||
   case when modern then jsonb_build_object('target_pcs',null,'reorder_point_pcs',null)else'{}'::jsonb end;end if;
 l:=cp7_demand.decimal(v->'lead_days');r:=cp7_demand.decimal(v->'review_days');h:=l+r;
 -- Measured lead days can be known zero; the current FG source uses review=0.
 -- Preserve the v1 positive-horizon contract, without treating known zero as
 -- missing in v2. The decimal validator already refuses negative durations.
 if (not modern and h=0) or h>3660 then raise exception 'CP7_BASELINE_HORIZON';end if;
 if modern then
  if v->'daily_total_pcs'='null'::jsonb or v->'counted_days'='null'::jsonb then
   return jsonb_build_object('status','UNKNOWN','reason','DEMAND_UNKNOWN','target_pcs',null,'reorder_point_pcs',null,'inputs',v);end if;
  total:=cp7_demand.decimal(v->'daily_total_pcs');days:=cp7_wip.pcs(v->'counted_days');
  if days<1 or days>3660 then raise exception 'CP7_BASELINE_COUNTED_DAYS';end if;
  d:=total/days;
 end if;
 if v->>'mode'='DAYS' then
  if(not modern and v->'daily_mean'='null'::jsonb)or v->'buffer_days'='null'::jsonb then
   return jsonb_build_object('status','UNKNOWN','reason','DEMAND_OR_BUFFER_UNKNOWN','inputs',v)||
    case when modern then jsonb_build_object('target_pcs',null,'reorder_point_pcs',null)else'{}'::jsonb end;end if;
  if not modern then d:=cp7_demand.decimal(v->'daily_mean');total:=d;end if;
  b:=cp7_demand.decimal(v->'buffer_days');lead_safety:=total*b/days;horizon_safety:=lead_safety;
  lead_target:=ceil(total*(l+b)/days);target:=ceil(total*(h+b)/days);
  if not modern then return jsonb_build_object('status','SCENARIO','kernel_version','target-days-1','horizon_days',h::text,'horizon_demand_pcs',(d*h)::text,
   'buffer_pcs',(d*b)::text,'target_pcs',target::text,'formula','ceil(D * (L + R + B))','inputs',v);
  end if;
 elsif modern then
  if days<14 or v->'daily_sd'='null'::jsonb or v->'service_level'='null'::jsonb then
   return jsonb_build_object('status','UNKNOWN','reason','STATISTICAL_HISTORY_OR_SERVICE_UNKNOWN','target_pcs',null,'reorder_point_pcs',null,'inputs',v);end if;
  -- Postgres stddev_samp is not rounded to the four display decimals. Accept
  -- its bounded full precision; this is a baseline independence assumption,
  -- not a claim of calibrated forecast error or an advanced model promotion.
  if jsonb_typeof(v->'daily_sd')is distinct from'string'or v->>'daily_sd'!~'^(0|[1-9][0-9]{0,29})(\.[0-9]{1,40})?$'
   or jsonb_typeof(v->'service_level')is distinct from'string'or v->>'service_level'not in('0.90','0.95','0.99')then
   raise exception 'CP7_BASELINE_STATISTICAL_INPUT';end if;
  sd:=(v->>'daily_sd')::numeric;z:=case v->>'service_level'when'0.90'then 1.2816 when'0.95'then 1.6449 else 2.3263 end;
  lead_safety:=z*sd*sqrt(l);horizon_safety:=z*sd*sqrt(h);
  lead_target:=ceil(total*l/days+lead_safety);target:=ceil(total*h/days+horizon_safety);
 else
  -- Existing v1 aggregate empirical scenarios keep their exact contract.
  if v->'quantile'='null'::jsonb or jsonb_array_length(v->'horizon_samples')=0 then return jsonb_build_object('status','UNKNOWN','reason','AGGREGATE_HORIZON_DISTRIBUTION_REQUIRED','inputs',v);end if;
  q:=cp7_demand.decimal(v->'quantile');if q<=0 or q>1 then raise exception 'CP7_BASELINE_QUANTILE';end if;
  for sample in select value from jsonb_array_elements(v->'horizon_samples') loop samples:=array_append(samples,cp7_demand.decimal(sample));end loop;
  select array_agg(x order by x) into samples from unnest(samples) x;
  target:=ceil(samples[ceil(q*cardinality(samples))::int]);
  return jsonb_build_object('status','SCENARIO','kernel_version','target-empirical-quantile-1','horizon_days',h::text,'target_pcs',target::text,
   'sample_count',cardinality(samples),'formula','ceil(empirical inverse-CDF quantile of aggregate H demand)','inputs',v,
   'reason','AGGREGATE_HORIZON_SAMPLES_NO_DAILY_QUANTILE_SUM_NO_DAYS_BUFFER');
 end if;
 return jsonb_build_object('status','SCENARIO','kernel_version','target-unified-2','horizon_days',h::text,
  'lead_demand_pcs',(total*l/days)::text,'review_demand_pcs',(total*r/days)::text,
  'lead_safety_pcs',lead_safety::text,'horizon_safety_pcs',horizon_safety::text,
  'reorder_point_pcs',lead_target::text,'target_pcs',target::text,'inputs',v,
  'reason',case v->>'mode'when'DAYS'then'ONE_EXPLICIT_DAYS_BUFFER'else'BASELINE_INDEPENDENT_DAILY_VARIATION_ASSUMPTION'end);
end $$;
