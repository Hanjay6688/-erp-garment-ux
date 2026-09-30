-- Versioned bounded NUMERIC kernels. No parameters learned from validation/holdout.
-- Zero is observed zero. A null/censored period blocks these dense-series kernels.
create function cp7_models.predict(method text,observations jsonb,params jsonb,horizon integer) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare x jsonb;y numeric[]:='{}';n int;i int;j int;start_at int:=1;w int;season int;first_positive int;
 alpha numeric;beta numeric;phi numeric;level numeric;trend numeric;old_level numeric;z numeric;interval_mean numeric;p numeric;periods int;f numeric;damping numeric;
 forecasts jsonb:='[]';
begin
 if method is null or method not in ('MEAN','NAIVE','MOVING_MEAN','SES','DAMPED_HOLT','SEASONAL_NAIVE','SBA','TSB') then raise exception 'CP7_MODEL_METHOD';end if;
 if horizon is null or horizon not between 1 and 3660 then raise exception 'CP7_MODEL_HORIZON';end if;
 perform cp7_demand.items(observations,10000);
 for x in select value from jsonb_array_elements(observations) loop
  if x='null'::jsonb then return jsonb_build_object('status','INELIGIBLE','method',method,'reason','GAP_OR_CENSORED_PERIOD_NOT_ZERO');end if;
  y:=array_append(y,cp7_demand.decimal(x));
 end loop;
 n:=cardinality(y);if n=0 then return jsonb_build_object('status','INELIGIBLE','method',method,'reason','NO_OBSERVED_HISTORY');end if;
 perform cp7_wip.fields(params,case method when 'MOVING_MEAN' then array['window'] when 'SES' then array['alpha','initial_level']
  when 'DAMPED_HOLT' then array['alpha','beta','phi','initial_level','initial_trend'] when 'SEASONAL_NAIVE' then array['season']
  when 'SBA' then array['alpha','beta'] when 'TSB' then array['alpha','beta'] else array[]::text[] end);
 if method in ('SES','DAMPED_HOLT','SBA','TSB') then alpha:=cp7_demand.decimal(params->'alpha');if alpha<=0 or alpha>1 then raise exception 'CP7_MODEL_ALPHA';end if;end if;
 if method in ('DAMPED_HOLT','SBA','TSB') then beta:=cp7_demand.decimal(params->'beta');if beta<=0 or beta>1 then raise exception 'CP7_MODEL_BETA';end if;end if;
 if method='MEAN' then select avg(a) into f from unnest(y) a;
 elsif method='NAIVE' then f:=y[n];
 elsif method='MOVING_MEAN' then
  w:=cp7_wip.pcs(params->'window');if w<1 or w>10000 then raise exception 'CP7_MODEL_WINDOW';end if;
  if n<w then return jsonb_build_object('status','INELIGIBLE','method',method,'reason','WINDOW_HISTORY_SHORT');end if;
  select avg(a) into f from unnest(y[(n-w+1):n]) a;
 elsif method in ('SES','DAMPED_HOLT') then
  if params->'initial_level'='null'::jsonb then level:=y[1];start_at:=2;else level:=cp7_demand.decimal(params->'initial_level');end if;
  trend:=0;
  if method='DAMPED_HOLT' then
   phi:=cp7_demand.decimal(params->'phi');if phi<=0 or phi>1 then raise exception 'CP7_MODEL_PHI';end if;
   if jsonb_typeof(params->'initial_trend') is distinct from 'string' or params->>'initial_trend' !~ '^-?(0|[1-9][0-9]{0,19})(\.[0-9]{1,12})?$' then raise exception 'CP7_MODEL_TREND';end if;
   trend:=(params->>'initial_trend')::numeric;
  end if;
  if start_at<=n then
   for i in start_at..n loop
    old_level:=level;
    if method='SES' then level:=alpha*y[i]+(1-alpha)*level;
    else level:=alpha*y[i]+(1-alpha)*(level+phi*trend);trend:=beta*(level-old_level)+(1-beta)*phi*trend;end if;
    level:=round(level,12);trend:=round(trend,12);
   end loop;
  end if;f:=level;
 elsif method='SEASONAL_NAIVE' then
  season:=cp7_wip.pcs(params->'season');if season<1 or season>3660 then raise exception 'CP7_MODEL_SEASON';end if;
  if n<2*season then return jsonb_build_object('status','INELIGIBLE','method',method,'reason','FEWER_THAN_TWO_COMPLETE_SEASONS');end if;
 elsif method='SBA' then
  for i in 1..n loop if y[i]>0 then first_positive:=i;exit;end if;end loop;
  if first_positive is null then f:=0;
  else
   z:=y[first_positive];interval_mean:=first_positive;periods:=1;
   if first_positive<n then
    for i in (first_positive+1)..n loop
     if y[i]>0 then z:=round(alpha*y[i]+(1-alpha)*z,12);interval_mean:=round(beta*periods+(1-beta)*interval_mean,12);periods:=1;else periods:=periods+1;end if;
    end loop;
   end if;f:=(1-beta/2)*z/interval_mean;
  end if;
 elsif method='TSB' then
  p:=case when y[1]>0 then 1 else 0 end;z:=case when y[1]>0 then y[1] else null end;
  if n>1 then for i in 2..n loop
   p:=round(beta*(case when y[i]>0 then 1 else 0 end)+(1-beta)*p,12);
   if y[i]>0 then z:=case when z is null then y[i] else round(alpha*y[i]+(1-alpha)*z,12) end;end if;
  end loop;end if;f:=p*coalesce(z,0);
 end if;
 damping:=0;
 for j in 1..horizon loop
  if method='SEASONAL_NAIVE' then f:=y[n-season+1+((j-1)%season)];
  elsif method='DAMPED_HOLT' then damping:=damping+power(phi,j);f:=level+damping*trend;end if;
  forecasts:=forecasts||jsonb_build_array(round(greatest(0,f),12)::text);
 end loop;
 return jsonb_build_object('status','ELIGIBLE','method',method,'kernel_version',lower(method)||'-1','forecasts',forecasts,
  'training_count',n,'params',params,'reason','FIXED_PARAMETERS_OBSERVED_DENSE_HISTORY_NONNEGATIVE_FORECAST');
end $$;

create function cp7_models.score(actual jsonb,forecast jsonb,training jsonb,season integer) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare a numeric[]:='{}';f numeric[]:='{}';t numeric[]:='{}';x jsonb;i int;n int;mae numeric:=0;bias numeric:=0;mse numeric:=0;da numeric:=0;ds numeric:=0;den_count int;
begin
 perform cp7_demand.items(actual,3660);perform cp7_demand.items(forecast,3660);perform cp7_demand.items(training,10000);
 for x in select value from jsonb_array_elements(actual) loop a:=array_append(a,cp7_demand.decimal(x));end loop;
 for x in select value from jsonb_array_elements(forecast) loop f:=array_append(f,cp7_demand.decimal(x));end loop;
 for x in select value from jsonb_array_elements(training) loop t:=array_append(t,cp7_demand.decimal(x));end loop;
 n:=cardinality(a);if n=0 or n<>cardinality(f) or season is null or season<1 or season>3660 then raise exception 'CP7_MODEL_SCORE_SHAPE';end if;
 for i in 1..n loop mae:=mae+abs(f[i]-a[i]);bias:=bias+f[i]-a[i];mse:=mse+power(f[i]-a[i],2);end loop;
 den_count:=cardinality(t)-season;
 if den_count>0 then for i in (season+1)..cardinality(t) loop da:=da+abs(t[i]-t[i-season]);ds:=ds+power(t[i]-t[i-season],2);end loop;da:=da/den_count;ds:=ds/den_count;end if;
 return jsonb_build_object('count',n,'mae',(mae/n)::text,'signed_bias',(bias/n)::text,'horizon_total_abs_error',abs(bias)::text,
  'mase',case when da>0 then (mae/n/da)::text else null end,'rmsse',case when ds>0 then sqrt(mse/n/ds)::text else null end,
  'mase_denominator',case when den_count>0 then da::text else null end,'rmsse_denominator',case when den_count>0 then ds::text else null end,
  'scaled_score_status',case when den_count<=0 then 'NA_TRAINING_SHORT' when da=0 then 'NA_ZERO_DENOMINATOR' else 'DEFINED' end,
  'bias_convention','FORECAST_MINUS_ACTUAL');
end $$;
