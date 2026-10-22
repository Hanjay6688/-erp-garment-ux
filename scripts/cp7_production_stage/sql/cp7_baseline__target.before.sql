create or replace function cp7_baseline.target(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare d numeric; l numeric; r numeric; b numeric; h numeric; target numeric; q numeric; sample jsonb; samples numeric[]:='{}';
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','mode','daily_mean','lead_days','review_days','buffer_days','quantile','horizon_samples','refs']);
 perform cp7_demand.context(v,'cp7.target-input.v1');perform cp7_wip.refs(v->'refs');perform cp7_demand.items(v->'horizon_samples',10000);
 if v->>'mode' is null or v->>'mode' not in ('DAYS','STATISTICAL') then raise exception 'CP7_BASELINE_BUFFER_MODE';end if;
 if v->>'mode'='DAYS' and (v->'quantile'<>'null'::jsonb or jsonb_array_length(v->'horizon_samples')<>0) then raise exception 'CP7_BASELINE_DOUBLE_BUFFER';end if;
 if v->>'mode'='STATISTICAL' and (v->'buffer_days'<>'null'::jsonb or v->'daily_mean'<>'null'::jsonb) then raise exception 'CP7_BASELINE_DOUBLE_BUFFER';end if;
 if v->'lead_days'='null'::jsonb or v->'review_days'='null'::jsonb then return jsonb_build_object('status','UNKNOWN','reason','HORIZON_UNKNOWN','inputs',v);end if;
 l:=cp7_demand.decimal(v->'lead_days');r:=cp7_demand.decimal(v->'review_days');h:=l+r;
 if h<=0 or h>3660 then raise exception 'CP7_BASELINE_HORIZON';end if;
 if v->>'mode'='DAYS' then
  if v->'daily_mean'='null'::jsonb or v->'buffer_days'='null'::jsonb then return jsonb_build_object('status','UNKNOWN','reason','DEMAND_OR_BUFFER_UNKNOWN','inputs',v);end if;
  d:=cp7_demand.decimal(v->'daily_mean');b:=cp7_demand.decimal(v->'buffer_days');target:=ceil(d*(h+b));
  return jsonb_build_object('status','SCENARIO','kernel_version','target-days-1','horizon_days',h::text,'horizon_demand_pcs',(d*h)::text,
   'buffer_pcs',(d*b)::text,'target_pcs',target::text,'formula','ceil(D * (L + R + B))','inputs',v);
 end if;
 if v->'quantile'='null'::jsonb or jsonb_array_length(v->'horizon_samples')=0 then return jsonb_build_object('status','UNKNOWN','reason','AGGREGATE_HORIZON_DISTRIBUTION_REQUIRED','inputs',v);end if;
 q:=cp7_demand.decimal(v->'quantile');if q<=0 or q>1 then raise exception 'CP7_BASELINE_QUANTILE';end if;
 for sample in select value from jsonb_array_elements(v->'horizon_samples') loop samples:=array_append(samples,cp7_demand.decimal(sample));end loop;
 select array_agg(x order by x) into samples from unnest(samples) x;
 target:=ceil(samples[ceil(q*cardinality(samples))::int]);
 return jsonb_build_object('status','SCENARIO','kernel_version','target-empirical-quantile-1','horizon_days',h::text,'target_pcs',target::text,
  'sample_count',cardinality(samples),'formula','ceil(empirical inverse-CDF quantile of aggregate H demand)','inputs',v,
  'reason','AGGREGATE_HORIZON_SAMPLES_NO_DAILY_QUANTILE_SUM_NO_DAYS_BUFFER');
end $$;
