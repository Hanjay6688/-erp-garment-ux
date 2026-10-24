-- Derived from the exact legacy Native dataset; immutable scoped captures only.
create schema cp7_model_scoped_dataset authorization cp7_capture;
revoke all on schema cp7_model_scoped_dataset from public,anon,authenticated,service_role;

create function cp7_model_scoped_dataset.native_dataset(q jsonb,p_actor uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare r cp7_model_history_runtime.runs%rowtype;target jsonb;product jsonb;series jsonb;registry cp7_model_native.registry%rowtype;
 lo date;hi date;captures bigint;hash text;engine text;
begin
 q:=cp7_model_native.query(q);
 select *into r from cp7_model_history_runtime.runs where id=(q->>'history_run_id')::uuid and actor=p_actor;
 if r.id is null then raise exception using errcode='42501',message='CP7_SCOPED_MODEL_HISTORY_UNAVAILABLE';end if;
 if r.query->'target_key'is distinct from q->'target_key'
  or r.result->>'scope'is distinct from'SINGLE_CURRENT_PHYSICAL_ROOT'then raise exception 'CP7_SCOPED_MODEL_TARGET_BINDING';end if;
 lo:=(r.query->>'from_date')::date;hi:=(r.query->>'through_date')::date;
 if hi-lo>365 then raise exception 'CP7_SCOPED_MODEL_WINDOW_LIMIT';end if;
 target:=(select x from jsonb_array_elements(r.result->'history'->'rows')x where x->>'target_key'=q->>'target_key');
 if target is null then raise exception 'CP7_SCOPED_MODEL_TARGET_UNAVAILABLE';end if;
 product:=(select x from jsonb_array_elements(r.result->'current_stock')x where x->>'target_key'=q->>'target_key');
 if product is null then raise exception 'CP7_SCOPED_MODEL_TARGET_UNAVAILABLE';end if;
 select *into registry from cp7_model_native.registry where id='cp7.native-model-policy.v1';
 if registry.id is null then raise exception 'CP7_SCOPED_MODEL_REGISTRY_UNAVAILABLE';end if;
 select count(*)into captures from cp7_model_history_runtime.runs h where h.actor=p_actor and h.captured_at<=r.captured_at
  and h.query->'target_key'=q->'target_key'
  and h.query->>'group_mode'=r.query->>'group_mode'and(h.query->>'from_date')::date<=hi and(h.query->>'through_date')::date>=lo;
 if captures>500 then raise exception 'CP7_SCOPED_MODEL_CAPTURE_SCOPE_LIMIT';end if;
 -- Native snapshots already contain the exact demand and availability result.
 -- Their ACTUAL capture time is the earliest admitted knowledge. Never turn
 -- a physical date, posted_at or a current RESTATED view into past knowledge.
 with observations as(
  select h.id,h.captured_at,d.value d,
   jsonb_build_array(d.value->'state',d.value->'training_pcs')meaning
  from cp7_model_history_runtime.runs h cross join lateral jsonb_array_elements(h.result->'history'->'rows')t(value)
  cross join lateral jsonb_array_elements(t.value->'days')d(value)
  where h.actor=p_actor and h.captured_at<=r.captured_at and h.query->>'group_mode'=r.query->>'group_mode'
   and h.query->'target_key'=q->'target_key'
   and t.value->>'target_key'=q->>'target_key'and(d.value->>'date')::date between lo and hi
 ), ordered as(
  select *,lag(meaning)over(partition by d->>'date'order by captured_at,id)previous from observations
 ), changed as(
  select *,row_number()over(partition by d->>'date'order by captured_at,id)revision from ordered where previous is distinct from meaning
 )
 select coalesce(jsonb_agg(jsonb_build_object('date',d->>'date','known_at',cp7_planning.utc(captured_at),'revision',revision::text,
  'state',case d->>'state'when'AVAILABLE'then'OBSERVED'when'STOCKOUT'then'CENSORED'else'UNKNOWN'end,
  'value',d->'training_pcs','refs',jsonb_build_array(jsonb_build_object('kind','NATIVE_SCOPED_HISTORY_RUN','id',id::text,'revision','1')))
  order by d->>'date',revision),'[]')into series from changed;
 if jsonb_array_length(series)>20000 then raise exception 'CP7_SCOPED_MODEL_SERIES_LIMIT';end if;
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

create function cp7_model_scoped_dataset.engine()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select md5(cp7_model_registry_adapter.engine()||':'||cp7_model_history_runtime.engine()||':'||
  string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text))
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='cp7_model_scoped_dataset'and p.prokind='f'
$$;

create function cp7_model_scoped_dataset.dataset(q jsonb,p_actor uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;before_history jsonb;after_history jsonb;d jsonb;policy_source jsonb;registry jsonb;
 engine text;answer jsonb;
begin
 a:=cp7_private.access_now();q:=cp7_model_native.query(q);
 if p_actor is distinct from(a->>'actor')::uuid then
  raise exception using errcode='42501',message='CP7_SCOPED_MODEL_ACTOR_CHANGED';end if;
 before_history:=cp7_model_history_runtime.serve((q->>'history_run_id')::uuid);
 if before_history->'current_guard'->>'source_state'is distinct from'UNCHANGED'then
  raise exception 'CP7_SCOPED_MODEL_HISTORY_STALE';end if;
 engine:=cp7_model_scoped_dataset.engine();
 d:=cp7_model_scoped_dataset.native_dataset(q,p_actor);
 policy_source:=cp7_model_policy.source_at(cp7_demand.instant(d->'known_as_of'));
 if policy_source is not null then
  select jsonb_build_object('id',r.id,'registered_at',cp7_planning.utc(r.registered_at),'configuration',r.configuration)
   into registry from cp7_model_native.registry r where r.id=policy_source->'policy'->>'registry_id';
  if registry is null then raise exception 'CP7_SCOPED_MODEL_POLICY_REGISTRY_UNAVAILABLE';end if;
 end if;
 -- Reuse the reviewed policy/assessment adapter. Only the source of immutable
 -- observations changes; there is no new policy, forecast or promotion rule.
 answer:=cp7_model_registry_adapter.bind(d,policy_source,registry,engine);
 after_history:=cp7_model_history_runtime.serve((q->>'history_run_id')::uuid);
 if after_history->'current_guard'->>'source_state'is distinct from'UNCHANGED'
  or after_history-'current_guard'is distinct from before_history-'current_guard'
  or engine is distinct from cp7_model_scoped_dataset.engine()then
  raise exception using errcode='40001',message='CP7_SCOPED_MODEL_SOURCE_CHANGED';end if;
 if cp7_private.access_now()is distinct from a then
  raise exception using errcode='42501',message='CP7_SCOPED_MODEL_ACCESS_CHANGED';end if;
 return answer;
end $$;

alter function cp7_model_scoped_dataset.native_dataset(jsonb,uuid)owner to cp7_capture;
alter function cp7_model_scoped_dataset.engine()owner to cp7_capture;
alter function cp7_model_scoped_dataset.dataset(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_model_scoped_dataset from public,anon,authenticated,service_role;
