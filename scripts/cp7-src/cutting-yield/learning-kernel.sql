-- Private empirical learning candidate. No public caller can supply training,
-- policy, chronology, completeness or a prediction. The Native adapter must
-- prove those inputs before installing/exposing a source-bound producer.
create schema cp7_cutting_learning authorization cp7_capture;
revoke all on schema cp7_cutting_learning from public,anon,authenticated,service_role;

create function cp7_cutting_learning.instant(p jsonb,allow_unknown boolean default false)returns timestamptz
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare t timestamptz;
begin
 if p is null or p='null'::jsonb then
  if allow_unknown then return null;end if;raise exception 'CP7_CUTTING_CLOCK_REQUIRED';end if;
 if jsonb_typeof(p)is distinct from'string'or(p#>>'{}')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})$'
  then raise exception 'CP7_CUTTING_CLOCK_REQUIRED';end if;
 t:=(p#>>'{}')::timestamptz;
 if not isfinite(t)then raise exception 'CP7_CUTTING_CLOCK_REQUIRED';end if;return t;
end $$;

create function cp7_cutting_learning.number(p jsonb,allow_unknown boolean default false,whole boolean default false)returns numeric
language plpgsql immutable security invoker set search_path=''as $$
begin
 if p is null or p='null'::jsonb then
  if allow_unknown then return null;end if;raise exception 'CP7_CUTTING_DECIMAL_REQUIRED';end if;
 if jsonb_typeof(p)is distinct from'string'or length(p#>>'{}')>200
  or(p#>>'{}')!~'^[0-9]+(\.[0-9]+)?$'or whole and(p#>>'{}')!~'^[0-9]+$'
  then raise exception 'CP7_CUTTING_DECIMAL_REQUIRED';end if;
 return(p#>>'{}')::numeric;
end $$;

create function cp7_cutting_learning.mix(p jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare r jsonb;divisor bigint:=0;item record;
begin
 if jsonb_typeof(p)is distinct from'array'or jsonb_array_length(p)not between 1 and 1000 then raise exception 'CP7_CUTTING_MIX_REQUIRED';end if;
 if exists(select 1 from jsonb_array_elements(p)x where jsonb_typeof(x)is distinct from'object'
  or not(x?&array['size_id','drawings'])or(select count(*)from jsonb_object_keys(x))<>2
  or jsonb_typeof(x->'size_id')is distinct from'string'or x->>'size_id'!~*'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
  or jsonb_typeof(x->'drawings')is distinct from'string'or x->>'drawings'!~'^[1-9][0-9]{0,9}$'
  or(x->>'drawings')::numeric>2147483647)then raise exception 'CP7_CUTTING_MIX_REQUIRED';end if;
 for item in select lower(x->>'size_id')size_id,sum((x->>'drawings')::bigint)::bigint drawings
  from jsonb_array_elements(p)x group by lower(x->>'size_id')loop divisor:=gcd(divisor,item.drawings);end loop;
 select jsonb_agg(jsonb_build_object('size_id',size_id,'drawings',(drawings/divisor)::text)order by size_id collate "C")into r
  from(select lower(x->>'size_id')size_id,sum((x->>'drawings')::bigint)::bigint drawings
   from jsonb_array_elements(p)x group by lower(x->>'size_id'))s;
 return r;
end $$;

create function cp7_cutting_learning.context(p jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare k text;
begin
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['family','pattern_id','pattern_revision','marker_key','unit','planned_mix'])
  or(select count(*)from jsonb_object_keys(p))<>6 or jsonb_typeof(p->'family')is distinct from'object'
  or not(p->'family'?&array['brand','mill','variant','spec_revision'])or(select count(*)from jsonb_object_keys(p->'family'))<>4
  then raise exception 'CP7_CUTTING_CONTEXT_REQUIRED';end if;
 foreach k in array array['brand','mill','variant','spec_revision']loop
  if jsonb_typeof(p->'family'->k)is distinct from'string'or length(btrim(p->'family'->>k))not between 1 and 200 then raise exception 'CP7_CUTTING_FAMILY_REQUIRED';end if;
 end loop;
 foreach k in array array['pattern_id','pattern_revision','marker_key','unit']loop
  if jsonb_typeof(p->k)is distinct from'string'or length(btrim(p->>k))not between 1 and 200 then raise exception 'CP7_CUTTING_CONTEXT_REQUIRED';end if;
 end loop;
 -- Identity values are not lowercased/guessed across families or Native units.
 return p||jsonb_build_object('planned_mix',cp7_cutting_learning.mix(p->'planned_mix'));
end $$;

create function cp7_cutting_learning.dataset(records jsonb,context_key jsonb,from_at timestamptz,through_at timestamptz,current_batch text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare out_rows jsonb;r jsonb;
begin
 if jsonb_typeof(records)is distinct from'array'or jsonb_array_length(records)>20000 then raise exception 'CP7_CUTTING_DATASET_SCOPE';end if;
 context_key:=cp7_cutting_learning.context(context_key);
 if through_at is null or not isfinite(through_at)or from_at is not null and(not isfinite(from_at)or from_at>=through_at)
  or current_batch is null or length(btrim(current_batch))not between 1 and 200 then raise exception 'CP7_CUTTING_DATASET_SCOPE';end if;
 if exists(select 1 from jsonb_array_elements(records)x where jsonb_typeof(x)is distinct from'object'
  or not(x?&array['slice_key','batch_key','revision_key','physical_at','known_at','input_known_at','native_valid','context','consumed','actual_pcs','width_cm'])
  or(select count(*)from jsonb_object_keys(x))<>11)then raise exception 'CP7_CUTTING_DATASET_FIELDS';end if;
 if exists(select 1 from jsonb_array_elements(records)x where jsonb_typeof(x->'native_valid')is distinct from'boolean'
  or exists(select 1 from unnest(array['slice_key','batch_key','revision_key','physical_at','known_at'])k where jsonb_typeof(x->k)is distinct from'string' or length(x->>k)=0)
  or length(x->>'slice_key')>200 or length(x->>'batch_key')>200 or length(x->>'revision_key')>200
  or cp7_cutting_learning.instant(x->'known_at')<cp7_cutting_learning.instant(x->'physical_at'))then raise exception 'CP7_CUTTING_DATASET_CHRONOLOGY';end if;
 for r in select x from jsonb_array_elements(records)x loop
  perform cp7_cutting_learning.instant(r->'physical_at');perform cp7_cutting_learning.instant(r->'known_at');
  perform cp7_cutting_learning.instant(r->'input_known_at',true);
  perform cp7_cutting_learning.number(r->'consumed',true);perform cp7_cutting_learning.number(r->'actual_pcs',true,true);
  if r->'width_cm'<>'null'::jsonb and cp7_cutting_learning.number(r->'width_cm')<=0 then raise exception 'CP7_CUTTING_WIDTH_REQUIRED';end if;
  if r->'context'<>'null'::jsonb then perform cp7_cutting_learning.context(r->'context');end if;
 end loop;
 -- Native slice identity and its physical batch cannot move between folds.
 -- A real lineage replacement must have a distinct Native slice identity.
 if exists(select 1 from jsonb_array_elements(records)x group by x->>'slice_key'
  having count(distinct x->>'batch_key')>1 or count(distinct(x->>'physical_at')::timestamptz)>1)
  then raise exception 'CP7_CUTTING_SLICE_IDENTITY_CHANGED';end if;
 -- A batch is a physical event, not a size or a later capture. It cannot be
 -- split across folds by assigning its slices different physical timestamps.
 if exists(select 1 from jsonb_array_elements(records)x group by x->>'batch_key'
  having count(distinct(x->>'physical_at')::timestamptz)>1)then raise exception 'CP7_CUTTING_BATCH_SPLIT';end if;
 if exists(select 1 from jsonb_array_elements(records)x group by x->>'slice_key',(x->>'known_at')::timestamptz
  having count(distinct(x-'known_at')::text)>1)then raise exception 'CP7_CUTTING_KNOWLEDGE_CONFLICT';end if;
 with admitted as materialized(
  select x,(x->>'known_at')::timestamptz known from jsonb_array_elements(records)x
   where(x->>'known_at')::timestamptz<=through_at and(x->>'physical_at')::timestamptz<=through_at
    and(from_at is null or(x->>'physical_at')::timestamptz>from_at)and x->>'batch_key'<>current_batch),
 latest as materialized(
  select distinct on(x->>'slice_key')x from admitted order by x->>'slice_key',known desc),
 eligible as(
  select x from latest where x->'native_valid'='true'::jsonb
   and x->>'input_known_at'is not null and(x->>'input_known_at')::timestamptz<(x->>'physical_at')::timestamptz
   and case when x->'context'<>'null'::jsonb then cp7_cutting_learning.context(x->'context')=context_key else false end
   and jsonb_typeof(x->'consumed')='string'and x->>'consumed'~'^[0-9]+(\.[0-9]+)?$'and(x->>'consumed')::numeric>0
   and jsonb_typeof(x->'actual_pcs')='string'and x->>'actual_pcs'~'^[0-9]+$')
 select coalesce(jsonb_agg(jsonb_build_object('slice_key',x->>'slice_key','batch_key',x->>'batch_key',
  'revision_key',x->>'revision_key','physical_at',x->>'physical_at','known_at',x->>'known_at',
  'consumed',x->>'consumed','rate',((x->>'actual_pcs')::numeric/(x->>'consumed')::numeric)::text,
  'width_cm',case when x->>'width_cm'~'^[0-9]+(\.[0-9]+)?$'and(x->>'width_cm')::numeric>0 then x->>'width_cm'else null end)
  order by(x->>'physical_at')::timestamptz,x->>'batch_key',x->>'slice_key'),'[]')into out_rows from eligible;
 return out_rows;
end $$;

create function cp7_cutting_learning.fit(rows jsonb,use_width boolean)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare n bigint;batches bigint;mx numeric;my numeric;denominator numeric;slope numeric:=0;intercept numeric;
begin
 if use_width and exists(select 1 from jsonb_array_elements(rows)x where x->>'width_cm'is null)then return null;end if;
 -- Each physical batch contributes one unit of weight. Subdividing a roll or
 -- repeatedly capturing its revision cannot multiply independent evidence.
 with weighted as(select x,(x->>'consumed')::numeric/sum((x->>'consumed')::numeric)over(partition by x->>'batch_key')w
  from jsonb_array_elements(rows)x)
 select count(*),count(distinct x->>'batch_key'),sum((x->>'width_cm')::numeric*w)/sum(w),sum((x->>'rate')::numeric*w)/sum(w)
  into n,batches,mx,my from weighted;
 if n=0 then return null;end if;
 if use_width then
  with weighted as(select x,(x->>'consumed')::numeric/sum((x->>'consumed')::numeric)over(partition by x->>'batch_key')w
   from jsonb_array_elements(rows)x)
  select sum(((x->>'width_cm')::numeric-mx)^2*w),sum(((x->>'width_cm')::numeric-mx)*((x->>'rate')::numeric-my)*w)
   into denominator,slope from weighted;
  if denominator<=0 then return null;end if;slope:=slope/denominator;
 end if;
 intercept:=my-case when use_width then slope*mx else 0 end;
 return jsonb_build_object('intercept',intercept::text,'slope',slope::text,'use_width',use_width,'train_slices',n::text,'train_batches',batches::text);
end $$;

create function cp7_cutting_learning.band(rows jsonb,model jsonb,coverage numeric)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare scores numeric[];n integer;rank integer;
begin
 if model is null or coverage<=0 or coverage>=1 then return null;end if;
 if model->'use_width'='true'::jsonb and exists(select 1 from jsonb_array_elements(rows)x where x->>'width_cm'is null)then return null;end if;
 with batch_scores as(
  select x->>'batch_key' key,max(abs((x->>'rate')::numeric-(model->>'intercept')::numeric
   -case when model->'use_width'='true'::jsonb then(model->>'slope')::numeric*(x->>'width_cm')::numeric else 0 end))score
   from jsonb_array_elements(rows)x group by x->>'batch_key')
 select array_agg(score order by score,key)into scores from batch_scores;
 n:=coalesce(cardinality(scores),0);rank:=ceil((n+1)*coverage)::integer;
 if rank<1 or rank>n then return null;end if;
 return model||jsonb_build_object('radius',scores[rank]::text,'calibration_batches',n::text,'rank',rank::text,'coverage_target',coverage::text);
end $$;

create function cp7_cutting_learning.score(rows jsonb,model jsonb,coverage numeric)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare result jsonb;
begin
 if model is null or jsonb_array_length(rows)=0 then return null;end if;
 if model->'use_width'='true'::jsonb and exists(select 1 from jsonb_array_elements(rows)x where x->>'width_cm'is null)then return null;end if;
 with residuals as(
  select x->>'batch_key'key,(x->>'consumed')::numeric weight,(x->>'rate')::numeric-(model->>'intercept')::numeric
   -case when model->'use_width'='true'::jsonb then(model->>'slope')::numeric*(x->>'width_cm')::numeric else 0 end error
   from jsonb_array_elements(rows)x),batches as(
  select key,max(abs(error))absolute_error,sum(error*weight)/sum(weight)bias from residuals group by key)
 select jsonb_build_object('batches',count(*)::text,'coverage',avg((absolute_error<=(model->>'radius')::numeric)::integer)::text,
  'mae',avg(absolute_error)::text,'bias',avg(bias)::text,
  'interval_score',avg(2*(model->>'radius')::numeric+2/(1-coverage)*greatest(absolute_error-(model->>'radius')::numeric,0))::text)
 into result from batches;
 return result;
end $$;

create function cp7_cutting_learning.evaluate(records jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare context_key jsonb;train jsonb;calibration jsonb;holdout jsonb;baseline jsonb;width_model jsonb;k text;
 bs jsonb;ws jsonb;selected jsonb;coverage numeric;qty numeric;width numeric;center numeric;radius numeric;
 train_at timestamptz;cal_at timestamptz;eval_at timestamptz;input_at timestamptz;reason text;basis text:='WITHOUT_WIDTH';
 min_qty numeric;max_qty numeric;min_width numeric;max_width numeric;actual numeric;status text;outcome jsonb;
begin
 if jsonb_typeof(q)is distinct from'object'or not(q?&array['context','current_batch_key','policy_known_at','train_through','calibration_through','evaluation_through','input_known_at','coverage','consumed','width_cm','actual_pcs','source_complete'])
  or(select count(*)from jsonb_object_keys(q))<>12 then raise exception 'CP7_CUTTING_EVALUATION_FIELDS';end if;
 outcome:=jsonb_build_object('contract_version','cp7.private-cutting-learning.v1','status','UNAVAILABLE','interval',null,
  'basis',basis,'automatic_activation',false,'business_write',false,'production_go',false,
  'policy_kind','EXPLICIT_PROPOSAL_NOT_FACTORY_GUARANTEE','causal_claim',false);
 if q->'source_complete'is distinct from'true'::jsonb then return outcome||jsonb_build_object('reason','INCOMPLETE_NATIVE_SCOPE');end if;
 if jsonb_typeof(q->'current_batch_key')is distinct from'string'or length(btrim(q->>'current_batch_key'))not between 1 and 200
  then raise exception 'CP7_CUTTING_EVALUATION_FIELDS';end if;
 context_key:=cp7_cutting_learning.context(q->'context');train_at:=cp7_cutting_learning.instant(q->'train_through');
 cal_at:=cp7_cutting_learning.instant(q->'calibration_through');eval_at:=cp7_cutting_learning.instant(q->'evaluation_through');input_at:=cp7_cutting_learning.instant(q->'input_known_at');
 coverage:=cp7_cutting_learning.number(q->'coverage');qty:=cp7_cutting_learning.number(q->'consumed');
 width:=cp7_cutting_learning.number(q->'width_cm',true);actual:=cp7_cutting_learning.number(q->'actual_pcs',true,true);
 if train_at is null or cal_at is null or eval_at is null or input_at is null or not(train_at<cal_at and cal_at<eval_at and eval_at<input_at)
  or cp7_cutting_learning.instant(q->'policy_known_at')>train_at then return outcome||jsonb_build_object('reason','PREKNOWN_POLICY_AND_CHRONOLOGICAL_FOLDS_REQUIRED');end if;
 if coverage is null or coverage<=0 or coverage>=1 or qty is null or qty<=0 or width is not null and width<=0
  then raise exception 'CP7_CUTTING_EVALUATION_NUMERIC';end if;
 train:=cp7_cutting_learning.dataset(records,context_key,null,train_at,q->>'current_batch_key');
 calibration:=cp7_cutting_learning.dataset(records,context_key,train_at,cal_at,q->>'current_batch_key');
 holdout:=cp7_cutting_learning.dataset(records,context_key,cal_at,eval_at,q->>'current_batch_key');
 baseline:=cp7_cutting_learning.band(calibration,cp7_cutting_learning.fit(train,false),coverage);
 bs:=cp7_cutting_learning.score(holdout,baseline,coverage);
 if baseline is null or bs is null then return outcome||jsonb_build_object('reason','INSUFFICIENT_SEPARATE_BATCH_CALIBRATION_OR_HOLDOUT',
  'train_slices',jsonb_array_length(train)::text,'calibration_slices',jsonb_array_length(calibration)::text,'holdout_slices',jsonb_array_length(holdout)::text);end if;
 selected:=baseline;reason:=case when width is null then'WIDTH_NOT_RECORDED_BASELINE_RETAINS_UNOBSERVED_WIDTH_VARIATION'else'WIDTH_CANDIDATE_NOT_QUALIFIED'end;
 -- Fit/calibrate both fixed methods before examining the disjoint holdout.
 -- Width is a candidate only with complete comparable recorded-width inputs.
 width_model:=cp7_cutting_learning.band(calibration,cp7_cutting_learning.fit(train,true),coverage);
 ws:=cp7_cutting_learning.score(holdout,width_model,coverage);
 select min((x->>'consumed')::numeric),max((x->>'consumed')::numeric),min((x->>'width_cm')::numeric),max((x->>'width_cm')::numeric)
  into min_qty,max_qty,min_width,max_width from jsonb_array_elements(train)x;
 if qty<min_qty or qty>max_qty then return outcome||jsonb_build_object('reason','CONSUMPTION_OUTSIDE_TRAINING_SUPPORT','baseline_score',bs);end if;
 if width is not null and not exists(select 1 from jsonb_array_elements(train)x where x->>'width_cm'is null)
  and(width<min_width or width>max_width)then return outcome||jsonb_build_object('reason','WIDTH_OUTSIDE_TRAINING_SUPPORT','baseline_score',bs);end if;
 if width is not null and ws is not null and width between min_width and max_width
  and not exists(select 1 from jsonb_array_elements(calibration||holdout)x where (x->>'width_cm')::numeric not between min_width and max_width)
  and(ws->>'coverage')::numeric>=coverage and(ws->>'interval_score')::numeric<(bs->>'interval_score')::numeric
  and(ws->>'mae')::numeric<=(bs->>'mae')::numeric and abs((ws->>'bias')::numeric)<=abs((bs->>'bias')::numeric)then
  selected:=width_model;basis:='WITH_RECORDED_WIDTH';reason:='RECORDED_WIDTH_CANDIDATE_STRICTLY_BETTER_ON_NEW_BATCH_HOLDOUT';end if;
 if basis='WITHOUT_WIDTH'and(bs->>'coverage')::numeric<coverage then
  return outcome||jsonb_build_object('reason','BASELINE_HOLDOUT_COVERAGE_FAILED','baseline_score',bs,'width_score',ws);end if;
 center:=((selected->>'intercept')::numeric+case when selected->'use_width'='true'::jsonb then(selected->>'slope')::numeric*width else 0 end)*qty;
 radius:=(selected->>'radius')::numeric*qty;
 if center<=0 then return outcome||jsonb_build_object('reason','MODEL_PREDICTION_NOT_PHYSICALLY_SUPPORTED');end if;
 status:=case when actual is null then'PREDICTION_ONLY'when actual<greatest(0,center-radius)then'LOW_REVIEW_REQUIRED'
  when actual>center+radius then'HIGH_REVIEW_REQUIRED'else'WITHIN_EMPIRICAL_INTERVAL'end;
 return outcome||jsonb_build_object('status',status,'reason',reason,'basis',basis,'context',context_key,
  'interval',jsonb_build_object('lower_pcs',greatest(0,center-radius)::text,'center_pcs',center::text,'upper_pcs',(center+radius)::text,
   'calibration_batches',selected->>'calibration_batches','coverage_target',coverage::text,'unit','PCS'),
  'baseline_score',bs,'width_score',ws,'model',selected,
  'baseline_holdout_qualified',(bs->>'coverage')::numeric>=coverage,'selected_holdout_qualified',true,
  'train_rows',train,'calibration_rows',calibration,'holdout_rows',holdout,
  'meaning','EMPIRICAL_NEW_CUTTING_EVENT_RANGE_NOT_CAUSE_OR_DESIGN_LIMIT');
end $$;

alter function cp7_cutting_learning.instant(jsonb,boolean)owner to cp7_capture;
alter function cp7_cutting_learning.number(jsonb,boolean,boolean)owner to cp7_capture;
alter function cp7_cutting_learning.mix(jsonb)owner to cp7_capture;
alter function cp7_cutting_learning.context(jsonb)owner to cp7_capture;
alter function cp7_cutting_learning.dataset(jsonb,jsonb,timestamptz,timestamptz,text)owner to cp7_capture;
alter function cp7_cutting_learning.fit(jsonb,boolean)owner to cp7_capture;
alter function cp7_cutting_learning.band(jsonb,jsonb,numeric)owner to cp7_capture;
alter function cp7_cutting_learning.score(jsonb,jsonb,numeric)owner to cp7_capture;
alter function cp7_cutting_learning.evaluate(jsonb,jsonb)owner to cp7_capture;
revoke all on all functions in schema cp7_cutting_learning from public,anon,authenticated,service_role;
