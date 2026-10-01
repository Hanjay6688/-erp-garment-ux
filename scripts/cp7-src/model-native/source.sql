create function cp7_model_native.query(q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare h integer;root uuid;size uuid;
begin
 perform cp7_wip.fields(q,array['history_run_id','target_key','horizon_days']);
 if jsonb_typeof(q->'history_run_id')is distinct from'string'or jsonb_typeof(q->'target_key')is distinct from'string'
  or(q->>'target_key')!~'^[0-9a-f-]{36}:[0-9a-f-]{36}$'then raise exception 'CP7_MODEL_NATIVE_QUERY';end if;
 perform(q->>'history_run_id')::uuid;root:=split_part(q->>'target_key',':',1)::uuid;size:=split_part(q->>'target_key',':',2)::uuid;
 h:=cp7_wip.pcs(q->'horizon_days');if h not between 1 and 90 then raise exception 'CP7_MODEL_NATIVE_HORIZON';end if;
 return jsonb_build_object('history_run_id',(q->>'history_run_id')::uuid,'target_key',root::text||':'||size::text,'horizon_days',h::text);
end $$;

create function cp7_model_native.dataset(q jsonb,p_actor uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare r cp7_planning.history_runs%rowtype;target jsonb;product jsonb;series jsonb;registry cp7_model_native.registry%rowtype;
 lo date;hi date;captures bigint;hash text;engine text;
begin
 select *into r from cp7_planning.history_runs where id=(q->>'history_run_id')::uuid and actor=p_actor;
 if r.id is null then raise exception using errcode='42501',message='CP7_MODEL_NATIVE_HISTORY_UNAVAILABLE';end if;
 lo:=(r.query->>'from_date')::date;hi:=(r.query->>'through_date')::date;
 if hi-lo>365 then raise exception 'CP7_MODEL_NATIVE_WINDOW_LIMIT';end if;
 target:=(select x from jsonb_array_elements(r.result->'history'->'rows')x where x->>'target_key'=q->>'target_key');
 if target is null then raise exception 'CP7_MODEL_NATIVE_TARGET_UNAVAILABLE';end if;
 product:=(select x from jsonb_array_elements(r.result->'current_stock')x where x->>'target_key'=q->>'target_key');
 if product is null then raise exception 'CP7_MODEL_NATIVE_TARGET_UNAVAILABLE';end if;
 select *into registry from cp7_model_native.registry where id='cp7.native-model-policy.v1';
 if registry.id is null then raise exception 'CP7_MODEL_NATIVE_REGISTRY_UNAVAILABLE';end if;
 select count(*)into captures from cp7_planning.history_runs h where h.actor=p_actor and h.captured_at<=r.captured_at
  and h.query->>'group_mode'=r.query->>'group_mode'and(h.query->>'from_date')::date<=hi and(h.query->>'through_date')::date>=lo;
 if captures>500 then raise exception 'CP7_MODEL_NATIVE_CAPTURE_SCOPE_LIMIT';end if;
 -- Native snapshots already contain the exact demand and availability result.
 -- Their ACTUAL capture time is the earliest admitted knowledge. Never turn
 -- a physical date, posted_at or a current RESTATED view into past knowledge.
 with observations as(
  select h.id,h.captured_at,d.value d,
   jsonb_build_array(d.value->'state',d.value->'training_pcs')meaning
  from cp7_planning.history_runs h cross join lateral jsonb_array_elements(h.result->'history'->'rows')t(value)
  cross join lateral jsonb_array_elements(t.value->'days')d(value)
  where h.actor=p_actor and h.captured_at<=r.captured_at and h.query->>'group_mode'=r.query->>'group_mode'
   and t.value->>'target_key'=q->>'target_key'and(d.value->>'date')::date between lo and hi
 ), ordered as(
  select *,lag(meaning)over(partition by d->>'date'order by captured_at,id)previous from observations
 ), changed as(
  select *,row_number()over(partition by d->>'date'order by captured_at,id)revision from ordered where previous is distinct from meaning
 )
 select coalesce(jsonb_agg(jsonb_build_object('date',d->>'date','known_at',cp7_planning.utc(captured_at),'revision',revision::text,
  'state',case d->>'state'when'AVAILABLE'then'OBSERVED'when'STOCKOUT'then'CENSORED'else'UNKNOWN'end,
  'value',d->'training_pcs','refs',jsonb_build_array(jsonb_build_object('kind','NATIVE_HISTORY_RUN','id',id::text,'revision','1')))
  order by d->>'date',revision),'[]')into series from changed;
 if jsonb_array_length(series)>20000 then raise exception 'CP7_MODEL_NATIVE_SERIES_LIMIT';end if;
 select md5(string_agg(pg_get_functiondef(p.oid),E'\n'order by p.proname,p.oid::regprocedure::text))into engine
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('cp7_models','cp7_model_native');
 hash:=encode(extensions.digest(convert_to(jsonb_build_object('history_source_hash',r.dependency_hash,'series',series,
  'registry',registry.configuration,'registered_at',cp7_planning.utc(registry.registered_at),'engine',engine)::text,'UTF8'),'sha256'),'hex');
 return jsonb_build_object('history_run_id',r.id,'query',q,'target_key',q->>'target_key','size_id',target->>'size_id',
  'known_as_of',cp7_planning.utc(r.captured_at),'from_date',lo::text,'through_date',hi::text,
  'series',series,'registry_id',registry.id,'registered_at',cp7_planning.utc(registry.registered_at),'configuration',registry.configuration,
  'product_sku',product->>'sku','product_name',product->>'product_name',
  'source_hash',hash,'history_source_hash',r.dependency_hash,'engine_hash',engine,
  'fallback_daily_mean',target->'available_sales_mean','refs',target->'refs',
  'knowledge_basis','ACTUAL_IMMUTABLE_NATIVE_CAPTURE_TIMES','no_retrospective_availability_backfill',true);
end $$;
