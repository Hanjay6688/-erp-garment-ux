create function cp7_models.window(series jsonb,lo date,hi date,known_before timestamptz) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare values_out jsonb;sources jsonb;
begin
 if lo is null or hi is null or known_before is null or hi<lo or hi-lo>9999 then raise exception 'CP7_MODEL_WINDOW_RANGE';end if;
 with latest as (
  select distinct on (value->>'date') value from jsonb_array_elements(series)
  where cp7_demand.instant(value->'known_at')<=known_before
  order by value->>'date',cp7_wip.pcs(value->'revision') desc
 ), grid as (select lo+i as d from generate_series(0,hi-lo) i)
 select jsonb_agg(case when value->>'state'='OBSERVED' then value->'value' else 'null'::jsonb end order by d),
  jsonb_agg(jsonb_build_object('date',d::text,'revision',value->'revision','known_at',value->'known_at','state',coalesce(value->>'state','UNKNOWN'),'refs',value->'refs') order by d)
 into values_out,sources from grid left join latest on latest.value->>'date'=grid.d::text;
 return jsonb_build_object('values',values_out,'sources',sources);
end $$;

create function cp7_models.promotion(b jsonb,c jsonb,policy jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare s jsonb;minimum_folds int;improvement numeric;bias_allowance numeric;tail_allowance numeric;reasons jsonb:='[]';
begin
 perform cp7_wip.fields(policy,array['minimum_complete_folds','minimum_mae_improvement','maximum_bias_worsening','maximum_tail_worsening','season_lag']);
 minimum_folds:=cp7_wip.pcs(policy->'minimum_complete_folds');improvement:=cp7_demand.decimal(policy->'minimum_mae_improvement');
 bias_allowance:=cp7_demand.decimal(policy->'maximum_bias_worsening');tail_allowance:=cp7_demand.decimal(policy->'maximum_tail_worsening');
 if minimum_folds<1 or minimum_folds>100 or cp7_wip.pcs(policy->'season_lag') not between 1 and 3660 then raise exception 'CP7_MODEL_POLICY';end if;
 foreach s in array array[b,c] loop
  perform cp7_wip.fields(s,array['fold_count','requested_folds','mae','signed_bias','tail_abs_error']);
  perform cp7_wip.pcs(s->'fold_count');perform cp7_wip.pcs(s->'requested_folds');
  if (s->>'fold_count')::numeric>(s->>'requested_folds')::numeric then raise exception 'CP7_MODEL_FOLD_COUNT';end if;
  if (s->>'fold_count')::numeric>0 then
   if jsonb_typeof(s->'mae') is distinct from 'string' or jsonb_typeof(s->'signed_bias') is distinct from 'string' or jsonb_typeof(s->'tail_abs_error') is distinct from 'string'
    or s->>'mae' !~ '^[0-9]+(\.[0-9]+)?$' or s->>'signed_bias' !~ '^-?[0-9]+(\.[0-9]+)?$' or s->>'tail_abs_error' !~ '^[0-9]+(\.[0-9]+)?$'
    or (s->>'mae')::numeric<abs((s->>'signed_bias')::numeric) then raise exception 'CP7_MODEL_METRIC';end if;
  elsif s->'mae'<>'null'::jsonb or s->'signed_bias'<>'null'::jsonb or s->'tail_abs_error'<>'null'::jsonb then raise exception 'CP7_MODEL_EMPTY_METRIC';end if;
 end loop;
 if b->>'requested_folds'<>c->>'requested_folds' then raise exception 'CP7_MODEL_PAIRED_FOLDS';end if;
 if (b->>'fold_count')::int<minimum_folds or (c->>'fold_count')::int<minimum_folds or b->>'fold_count'<>b->>'requested_folds' or c->>'fold_count'<>c->>'requested_folds' or b->'mae'='null'::jsonb or c->'mae'='null'::jsonb then
  reasons:=reasons||jsonb_build_array('INSUFFICIENT_COMPLETE_PAIRED_FOLDS');
 else
  if (b->>'mae')::numeric-(c->>'mae')::numeric<=improvement then reasons:=reasons||jsonb_build_array('NO_STRICT_PRIMARY_IMPROVEMENT');end if;
  if abs((c->>'signed_bias')::numeric)>abs((b->>'signed_bias')::numeric)+bias_allowance then reasons:=reasons||jsonb_build_array('BIAS_GUARD_FAILED');end if;
  if (c->>'tail_abs_error')::numeric>(b->>'tail_abs_error')::numeric+tail_allowance then reasons:=reasons||jsonb_build_array('TAIL_GUARD_FAILED');end if;
 end if;
 return jsonb_build_object('promote',jsonb_array_length(reasons)=0,'reasons',reasons,'policy',policy,'baseline',b,'challenger',c,
  'meaning','TECHNICAL_RECOMMENDATION_NOT_MODEL_REGISTRY_WRITE');
end $$;

create function cp7_models.evaluate(v jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare r jsonb;k text;seen jsonb:='{}';models jsonb;model jsonb;fold jsonb;folds_seen jsonb:='{}';model_ids jsonb:='{}';
 lo date;hi date;origin date;last_validation date;holdout_origin date;h int;holdout_h int;known timestamptz;cutoff timestamptz;first_cutoff timestamptz;
 train jsonb;actual jsonb;prediction jsonb;score jsonb;fold_results jsonb;results jsonb:='[]';summary jsonb;b jsonb;candidate jsonb;decision jsonb;
 count_complete int;mae numeric;bias numeric;tail numeric;selected text;best_mae numeric;holdout_results jsonb:='[]';models_with_decision jsonb:='[]';
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','target_key','size_id','known_as_of','series_start','series_end','series','baseline','challengers','folds','holdout','policy','refs']);
 perform cp7_demand.context(v,'cp7.model-evaluation-input.v1');perform cp7_wip.key(v->'target_key');perform cp7_wip.key(v->'size_id');perform cp7_wip.refs(v->'refs');
 known:=cp7_demand.instant(v->'known_as_of');lo:=cp7_demand.day(v->'series_start');hi:=cp7_demand.day(v->'series_end');
 if hi<lo or hi-lo>9999 or hi>=(known at time zone 'Asia/Jakarta')::date then raise exception 'CP7_MODEL_SERIES_RANGE';end if;
 perform cp7_demand.items(v->'series',20000);perform cp7_demand.items(v->'challengers',8);perform cp7_demand.items(v->'folds',100);
 if jsonb_array_length(v->'folds')=0 then raise exception 'CP7_MODEL_FOLDS_REQUIRED';end if;
 perform cp7_wip.fields(v->'holdout',array['origin','horizon']);holdout_origin:=cp7_demand.day(v->'holdout'->'origin');holdout_h:=cp7_wip.pcs(v->'holdout'->'horizon');
 if holdout_h not between 1 and 3660 or holdout_origin<lo or holdout_origin+holdout_h>hi then raise exception 'CP7_MODEL_HOLDOUT_RANGE';end if;
 for r in select value from jsonb_array_elements(v->'series') loop
  perform cp7_wip.fields(r,array['date','known_at','revision','state','value','refs']);perform cp7_demand.day(r->'date');perform cp7_demand.instant(r->'known_at');perform cp7_wip.pcs(r->'revision');perform cp7_wip.refs(r->'refs');
  if cp7_demand.day(r->'date')<lo or cp7_demand.day(r->'date')>hi then raise exception 'CP7_MODEL_OBSERVATION_RANGE';end if;
  if r->>'state' is null or r->>'state' not in ('OBSERVED','CENSORED','UNKNOWN') then raise exception 'CP7_MODEL_OBSERVATION_STATE';end if;
  if r->>'state'='OBSERVED' then perform cp7_demand.decimal(r->'value');elsif r->'value'<>'null'::jsonb then raise exception 'CP7_MODEL_CENSORED_NOT_ZERO';end if;
  k:=jsonb_build_array(r->>'date',r->>'revision')::text;
  if seen ? k and seen->k<>r then raise exception 'CP7_MODEL_REVISION_CONFLICT';end if;seen:=seen||jsonb_build_object(k,r);
 end loop;
 -- Same fixed horizon and all requested folds: no cherry-picking a model's easy folds.
 for fold in select value from jsonb_array_elements(v->'folds') loop
  perform cp7_wip.fields(fold,array['id','origin','horizon']);k:=cp7_wip.key(fold->'id');origin:=cp7_demand.day(fold->'origin');h:=cp7_wip.pcs(fold->'horizon');
  if folds_seen ? k or folds_seen ? ('origin:'||origin::text) or h<>holdout_h or origin<lo or origin+h>holdout_origin then raise exception 'CP7_MODEL_FOLD_LEAKAGE_OR_SHAPE';end if;
  folds_seen:=folds_seen||jsonb_build_object(k,true,'origin:'||origin::text,true);
  cutoff:=((origin+1)::timestamp at time zone 'Asia/Jakarta')-interval '1 microsecond';first_cutoff:=least(first_cutoff,cutoff);
  last_validation:=greatest(last_validation,origin+h);
 end loop;
 if (hi-lo+1)*jsonb_array_length(v->'folds')*(1+jsonb_array_length(v->'challengers'))>200000 then raise exception 'CP7_MODEL_EVALUATION_LIMIT';end if;
 models:=jsonb_build_array(v->'baseline')||(v->'challengers');
 for model in select value from jsonb_array_elements(models) loop
  perform cp7_wip.fields(model,array['id','method','params','registered_at']);k:=cp7_wip.key(model->'id');perform cp7_wip.key(model->'method');
  if model_ids ? k or cp7_demand.instant(model->'registered_at')>first_cutoff then raise exception 'CP7_MODEL_CONFIG_AFTER_VALIDATION_START';end if;model_ids:=model_ids||jsonb_build_object(k,true);
  count_complete:=0;mae:=0;bias:=0;tail:=0;fold_results:='[]';
  for fold in select value from jsonb_array_elements(v->'folds') order by value->>'origin',value->>'id' loop
   origin:=cp7_demand.day(fold->'origin');h:=cp7_wip.pcs(fold->'horizon');cutoff:=((origin+1)::timestamp at time zone 'Asia/Jakarta')-interval '1 microsecond';
   train:=cp7_models.window(v->'series',lo,origin,cutoff);actual:=cp7_models.window(v->'series',origin+1,origin+h,known);
   prediction:=cp7_models.predict(model->>'method',train->'values',model->'params',h);score:=null;
   if prediction->>'status'='ELIGIBLE' and not (actual->'values' @> '[null]'::jsonb) then
    score:=cp7_models.score(actual->'values',prediction->'forecasts',train->'values',cp7_wip.pcs(v->'policy'->'season_lag')::int);
    count_complete:=count_complete+1;mae:=mae+(score->>'mae')::numeric;bias:=bias+(score->>'signed_bias')::numeric;tail:=greatest(tail,(score->>'horizon_total_abs_error')::numeric);
   end if;
   fold_results:=fold_results||jsonb_build_array(jsonb_build_object('fold',fold,'training',train,'actual',actual,'prediction',prediction,'score',score,
    'status',case when score is null then 'INCOMPLETE' else 'COMPLETE' end,'training_known_cutoff',to_char(cutoff at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')));
  end loop;
  summary:=jsonb_build_object('fold_count',count_complete::text,'requested_folds',jsonb_array_length(v->'folds')::text,
   'mae',case when count_complete>0 then (mae/count_complete)::text else null end,'signed_bias',case when count_complete>0 then (bias/count_complete)::text else null end,
   'tail_abs_error',case when count_complete>0 then tail::text else null end);
  results:=results||jsonb_build_array(jsonb_build_object('model',model,'summary',summary,'folds',fold_results));
 end loop;
 b:=results->0;selected:=v->'baseline'->>'id';best_mae:=(b->'summary'->>'mae')::numeric;
 -- Equal MAE retains baseline; ties between winning challengers use declared order.
 for candidate in select value from jsonb_array_elements(results) with ordinality where ordinality>1 loop
  decision:=cp7_models.promotion(b->'summary',candidate->'summary',v->'policy');
  if decision->'promote'='true'::jsonb and (candidate->'summary'->>'mae')::numeric<best_mae then selected:=candidate->'model'->>'id';best_mae:=(candidate->'summary'->>'mae')::numeric;end if;
  models_with_decision:=models_with_decision||jsonb_build_array(candidate||jsonb_build_object('decision',decision));
 end loop;
 -- Holdout is read only AFTER selection. It never influences parameters/selection.
 cutoff:=((holdout_origin+1)::timestamp at time zone 'Asia/Jakarta')-interval '1 microsecond';
 train:=cp7_models.window(v->'series',lo,holdout_origin,cutoff);actual:=cp7_models.window(v->'series',holdout_origin+1,holdout_origin+holdout_h,known);
 for model in select value from jsonb_array_elements(models) where value->>'id' in (selected,v->'baseline'->>'id') loop
  prediction:=cp7_models.predict(model->>'method',train->'values',model->'params',holdout_h);score:=null;
  if prediction->>'status'='ELIGIBLE' and not (actual->'values' @> '[null]'::jsonb) then score:=cp7_models.score(actual->'values',prediction->'forecasts',train->'values',cp7_wip.pcs(v->'policy'->'season_lag')::int);end if;
  holdout_results:=holdout_results||jsonb_build_array(jsonb_build_object('model_id',model->'id','prediction',prediction,'score',score,'actual',actual,'training',train));
 end loop;
 return jsonb_build_object('contract_version','cp7.model-evaluation-result.v1','kernel_version','rolling-evaluation-1','snapshot_id',v->'snapshot_id','scope_id',v->'scope_id',
  'target_key',v->'target_key','size_id',v->'size_id','known_as_of',v->'known_as_of','selected_model_id',selected,'baseline',b,'challengers',models_with_decision,
  'selection_basis','COMPLETE_PAIRED_CHRONOLOGICAL_VALIDATION_ONLY','selection_status',case when selected=v->'baseline'->>'id' then 'BASELINE_RETAINED' else 'CHALLENGER_RECOMMENDED' end,
  'activation_status','REVIEW_REQUIRED','automatic_activation',false,
  'holdout',jsonb_build_object('definition',v->'holdout','results',holdout_results,'used_for_selection',false),
  'policy',v->'policy','refs',v->'refs','reason','NO_REGISTRY_WRITE_NO_HOLDOUT_RETUNING_NO_BUSINESS_ACCURACY_CLAIM');
end $$;
