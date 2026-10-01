create function cp7_model_native.build(d jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare lo date:=(d->>'from_date')::date;hi date:=(d->>'through_date')::date;
 h integer:=(d->'query'->>'horizon_days')::integer;holdout date;first_origin date;folds jsonb;models jsonb;input jsonb;
 evaluation jsonb;forecast jsonb;selected jsonb;training jsonb;reason text;at text:=d->>'registered_at';
begin
 holdout:=hi-h;first_origin:=hi-4*h;
 if first_origin-lo<1 then reason:='INSUFFICIENT_CHRONOLOGICAL_HISTORY';
 elsif(at::timestamptz)>((first_origin+1)::timestamp at time zone'Asia/Jakarta')-interval'1 microsecond'then
  reason:='REGISTRY_NOT_KNOWN_BEFORE_VALIDATION';
 else
  select jsonb_agg(jsonb_build_object('id','native-fold-'||i,'origin',(first_origin+(i-1)*h)::text,'horizon',h::text)order by i)into folds from generate_series(1,3)i;
  select jsonb_agg(x||jsonb_build_object('registered_at',at)order by ord)into models
   from jsonb_array_elements(d->'configuration'->'challengers')with ordinality a(x,ord);
  input:=jsonb_build_object('contract_version','cp7.model-evaluation-input.v1','snapshot_id',d->>'source_hash',
   'scope_id','OWN_NATIVE_CAPTURE_HISTORY','target_key',d->>'target_key','size_id',d->>'size_id',
   'known_as_of',d->>'known_as_of','series_start',lo::text,'series_end',hi::text,'series',d->'series',
   'baseline',(d->'configuration'->'baseline')||jsonb_build_object('registered_at',at),'challengers',models,'folds',folds,
   'holdout',jsonb_build_object('origin',holdout::text,'horizon',h::text),'policy',d->'configuration'->'policy','refs',d->'refs');
  evaluation:=cp7_models.evaluate(input);
  selected:=(select x from jsonb_array_elements(jsonb_build_array(input->'baseline')||(input->'challengers'))x where x->>'id'=evaluation->>'selected_model_id');
  training:=cp7_models.window(d->'series',lo,hi,(d->>'known_as_of')::timestamptz);
  forecast:=cp7_models.predict(selected->>'method',training->'values',selected->'params',h);
  reason:=case when evaluation->>'selection_status'='CHALLENGER_RECOMMENDED'then'COMPLETE_VALIDATION_RECOMMENDATION_REQUIRES_REVIEW'
   when evaluation->'baseline'->'summary'->>'fold_count'='0'then'HISTORICAL_NATIVE_KNOWLEDGE_INSUFFICIENT'
   else'BASELINE_RETAINED_BY_PAIRED_PROMOTION_GUARDS'end;
 end if;
 return jsonb_build_object('contract_version','cp7.native-model-result.v1','target_key',d->>'target_key','size_id',d->>'size_id',
  'history_run_id',d->'history_run_id','from_date',d->>'from_date','through_date',d->>'through_date','known_as_of',d->>'known_as_of',
  'product_sku',d->>'product_sku','product_name',d->>'product_name',
  'source_hash',d->>'source_hash','registry_id',d->>'registry_id','registry_registered_at',at,
  'knowledge_basis',d->>'knowledge_basis','no_retrospective_availability_backfill',true,
  'horizon_days',h,'series_revision_count',jsonb_array_length(d->'series'),
  'selection_status',coalesce(evaluation->>'selection_status','BASELINE_RETAINED'),
  'selected_model_id',coalesce(evaluation->>'selected_model_id',d->'configuration'->'baseline'->>'id'),
  'reason',reason,'fallback_daily_mean',d->'fallback_daily_mean','evaluation',evaluation,'forecast',forecast,
  'automatic_activation',false,'apply_allowed',false,'production_go',false,
  'policy_meaning',d->'configuration'->>'meaning');
end $$;

create function cp7_model_native.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_model_native.runs%rowtype;history jsonb;engine text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();select *into r from cp7_model_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_MODEL_NATIVE_RUN_UNAVAILABLE';end if;
 history:=cp7_planning.serve_history(r.history_run_id);
 select md5(string_agg(pg_get_functiondef(p.oid),E'\n'order by p.proname,p.oid::regprocedure::text))into engine
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('cp7_models','cp7_model_native');
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MODEL_NATIVE_ACCESS_CHANGED';end if;
 return r.result||jsonb_build_object('run_id',r.id,'request_id',r.request_id,'actor_scope_id',a->>'actor','captured_at',cp7_planning.utc(r.captured_at),
  'source_state',case when history->>'source_state'='UNCHANGED'and engine=r.input->>'engine_hash'then'UNCHANGED'else'ARCHIVED_STALE'end);
end $$;

create function cp7_model_native.capture(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;r cp7_model_native.runs%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();q:=cp7_model_native.query(p_query);
 if p_request is null then raise exception 'CP7_MODEL_NATIVE_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:MODEL_EVALUATION:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MODEL_NATIVE_ACCESS_CHANGED';end if;
 select *into r from cp7_model_native.runs where actor=(a->>'actor')::uuid and request_id=p_request;
 if r.id is not null then if r.query<>q then raise exception 'CP7_MODEL_NATIVE_REQUEST_CHANGED';end if;return cp7_model_native.serve(r.id);end if;
 with source as materialized(select cp7_model_native.dataset(q,(a->>'actor')::uuid)d),
  calculated as materialized(select d,cp7_model_native.build(d)result from source)
 insert into cp7_model_native.runs(actor,request_id,query,history_run_id,captured_at,registry_id,input,result,dependency_hash)
 select(a->>'actor')::uuid,p_request,q,(d->>'history_run_id')::uuid,clock_timestamp(),d->>'registry_id',d,result,d->>'source_hash'from calculated returning *into r;
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MODEL_NATIVE_ACCESS_CHANGED';end if;
 return cp7_model_native.serve(r.id);
end $$;
create function public.erp_cp7_capture_model_evaluation_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_model_native.capture(p_query,p_request)$$;
create function public.erp_cp7_read_model_evaluation_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_model_native.serve(p_run)$$;
