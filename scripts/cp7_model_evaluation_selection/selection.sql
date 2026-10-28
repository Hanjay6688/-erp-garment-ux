-- Private bridge for target integration. No caller replacement or forecast math.
create schema cp7_model_evaluation_selection authorization cp7_capture;
revoke all on schema cp7_model_evaluation_selection from public,anon,authenticated,service_role;

create function cp7_model_evaluation_selection.latest(p_targets text[],p_actor uuid,p_at timestamptz)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare result jsonb;
begin
 if p_actor is null or p_at is null or not isfinite(p_at)or p_at>clock_timestamp()
  or p_targets is null or cardinality(p_targets)>5000
  or cardinality(p_targets)<>(select count(distinct t)from unnest(p_targets)t)
  or exists(select 1 from unnest(p_targets)t where t is null or t!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')then
  raise exception 'CP7_MODEL_SELECTION_QUERY';end if;
 -- Do not filter by admission, model method, policy, history period or winner.
 -- A newer baseline/stale result must prevent reuse of an older eligible one.
 with candidates as materialized(
  select r.query->>'target_key'target,r.id,r.captured_at,2 runtime
   from cp7_model_registry_adapter.runs r
   where r.actor=p_actor and r.query->>'target_key'=any(p_targets)and r.captured_at<=p_at
  union all
  select r.query->>'target_key',r.id,r.captured_at,3
   from cp7_model_scoped_evaluation.runs r
   where r.actor=p_actor and r.query->>'target_key'=any(p_targets)and r.captured_at<=p_at
 ), selected as materialized(
  -- Exact timestamp ties prefer v3, then the greatest UUID within that runtime.
  -- Runtime remains part of identity even if two tables contain the same UUID.
  select distinct on(c.target)c.* from candidates c
   order by c.target,c.captured_at desc,c.runtime desc,c.id desc
 )
 select coalesce(jsonb_agg(jsonb_build_object('target_key',t.target,'run_id',r.id,
  'runtime',case r.runtime when 2 then'GLOBAL_V2'when 3 then'SCOPED_V3'else null end,
  'read_method',case r.runtime when 2 then'erp_cp7_read_model_evaluation_v2'when 3 then'erp_cp7_read_model_evaluation_v3'else null end,
  'captured_at',case when r.id is null then null else cp7_planning.utc(r.captured_at)end)
  order by t.target collate"C"),'[]')into result
 from unnest(p_targets)t(target)left join selected r on r.target=t.target;
 return result;
end $$;

create function cp7_model_evaluation_selection.current(p_target text,p_known timestamptz)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;actor uuid;selected jsonb;answer jsonb;after_answer jsonb;expected text;checked timestamptz;identity jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();actor:=(a->>'actor')::uuid;
 selected:=cp7_model_evaluation_selection.latest(array[p_target],actor,p_known)->0;
 if selected is distinct from cp7_model_evaluation_selection.latest(array[p_target],actor,clock_timestamp())->0 then
  raise exception using errcode='40001',message='CP7_MODEL_SELECTION_NEWER_EVALUATION';end if;
 if selected->>'runtime'='GLOBAL_V2'then
  answer:=cp7_model_registry_adapter.serve((selected->>'run_id')::uuid);expected:='cp7.native-model-run.v2';
 elsif selected->>'runtime'='SCOPED_V3'then
  answer:=cp7_model_scoped_evaluation.serve((selected->>'run_id')::uuid);expected:='cp7.scoped-model-run.v3';
 elsif selected->'run_id'is distinct from'null'::jsonb then raise exception 'CP7_MODEL_SELECTION_RUNTIME';end if;
 if answer is not null then
  if answer->>'contract_version'is distinct from expected or answer->>'actor_scope_id'is distinct from actor::text
   or answer->'run_id'is distinct from selected->'run_id' or answer->'captured_at'is distinct from selected->'captured_at'
   or answer->'query'->>'target_key'is distinct from p_target or answer->'production_go'is distinct from'false'::jsonb
   or answer->'forecast_applied'is distinct from'false'::jsonb
   or answer->'current_guard'->>'state'is null then raise exception 'CP7_MODEL_SELECTION_READER_BINDING';end if;
  if selected->>'runtime'='GLOBAL_V2' then
   after_answer:=cp7_model_registry_adapter.serve((selected->>'run_id')::uuid);
  else after_answer:=cp7_model_scoped_evaluation.serve((selected->>'run_id')::uuid);end if;
  if after_answer-'current_guard'is distinct from answer-'current_guard'
   or (after_answer->'current_guard')-'checked_at'is distinct from (answer->'current_guard')-'checked_at'then
   raise exception using errcode='40001',message='CP7_MODEL_SELECTION_SOURCE_CHANGED_DURING_READ';end if;
  answer:=after_answer;
 end if;
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MODEL_SELECTION_ACCESS_CHANGED';end if;
 checked:=clock_timestamp();
 if selected is distinct from cp7_model_evaluation_selection.latest(array[p_target],actor,checked)->0
  or(p_known at time zone'Asia/Jakarta')::date is distinct from(checked at time zone'Asia/Jakarta')::date then
  raise exception using errcode='40001',message='CP7_MODEL_SELECTION_CHANGED_DURING_READ';end if;
 identity:=jsonb_build_object('contract_version','cp7.model-evaluation-reference.v1',
  'actor_scope_id',actor,'access',a,'selection',selected,
  'assessment',answer->'assessment','current_guard',(answer->'current_guard')-'checked_at');
 return jsonb_build_object('contract_version','cp7.model-evaluation-reference.v1','actor_scope_id',actor,
  'selection',selected,'model',answer,'source_hash',encode(pg_catalog.sha256(convert_to(identity::text,'UTF8')),'hex'),
  'known_as_of',cp7_planning.utc(p_known),'checked_at',cp7_planning.utc(checked),
  'target_caller_integrated',false,'forecast_applied',false,'production_go',false);
end $$;

alter function cp7_model_evaluation_selection.latest(text[],uuid,timestamp with time zone)owner to cp7_capture;
alter function cp7_model_evaluation_selection.current(text,timestamp with time zone)owner to cp7_capture;
revoke all on all functions in schema cp7_model_evaluation_selection from public,anon,authenticated,service_role;
