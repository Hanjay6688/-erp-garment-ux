create schema cp7_bounded_analysis_stage authorization cp7_capture;
revoke all on schema cp7_bounded_analysis_stage from public,anon,authenticated,service_role;
create function cp7_bounded_analysis_stage.source_parts(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with source as materialized(select cp7_reorder_inputs.capture_baseline(p_products)c),
 parts as materialized(select c,cp7_supply_native.wip_source_parts((c->>'captured_at')::timestamptz)p from source)
 select jsonb_build_object('c',c||jsonb_build_object('production_sources',p->'source'),'proofs',p->'proofs')from parts
$$;
create function cp7_bounded_analysis_stage.schedule_source(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with source as materialized(select (cp7_bounded_analysis_stage.source_parts(p_products)->'c')c)
 select c||jsonb_build_object('schedule',cp7_schedule_native.source_at((c->>'captured_at')::timestamptz),
  'planning_time_bucket',cp7_planning.utc(date_trunc('minute',(c->>'captured_at')::timestamptz)))from source
$$;
create function cp7_bounded_analysis_stage.netting_source(p_products integer,p_match integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with source as materialized(select cp7_bounded_analysis_stage.schedule_source(p_products)c),
 wanted as materialized(
  select x->>'id'id from source,jsonb_array_elements(c->'facts'->'products')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'other'->'origins')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'other'->'bs')x
  union select x->>'product_id'from source,jsonb_array_elements(c->'production_sources'->'facts'->'cutting'->'bs')x
 ),products as materialized(
  select p.id,coalesce(p.identity_root_id,p.id)root_id,p.model_id,p.size_id,p.brand_id,p.color_name,
   p.effective_from,p.effective_to,p.created_at
  from erp.products p join wanted w on w.id=p.id::text cross join source
  where p.created_at<=(c->>'captured_at')::timestamptz order by p.id limit p_match+1
 )select c||jsonb_build_object('matching_products',coalesce((select jsonb_agg(to_jsonb(p)order by p.id)from products p),'[]'))from source
$$;
create function cp7_bounded_analysis_stage.analysis_source(p_products integer,p_match integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with native as materialized(select cp7_bounded_analysis_stage.netting_source(p_products,p_match)c),
 engine as(select encode(extensions.digest(convert_to(string_agg(
  p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')signature
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname in('cp7_planning','cp7_profile','cp7_supply_native','cp7_schedule_native','cp7_netting_native','cp7_analysis_native','cp7_analysis_stage','cp7_fabric_native','cp7_wip','cp7_demand','cp7_baseline','cp7_models','cp7_finance','cp7_reorder_supply','cp7_bounded_analysis_stage')
   or p.oid='erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure)
 select c||jsonb_build_object('reorder_supply_engine','cp7.reorder-supply.v1','analysis_engine_signature',signature,
  'material_source',cp7_analysis_native.material_source(c->'facts'->'products',(c->>'captured_at')::timestamptz),
  'fabric_source',cp7_fabric_native.source(c->'facts'->'products',(c->>'captured_at')::timestamptz))from native cross join engine
$$;
create function cp7_bounded_analysis_stage.native_work_fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts',
  'profiles',c->'profiles','production_policies',c->'production_policies'->'rows',
  'production_scope',c->'production_sources'->'scope',
  'production',c->'production_sources'->'facts')::text,'UTF8'),'sha256'),'hex')
$$;


create function cp7_bounded_analysis_stage.producer_hash()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),
  E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname in('cp7_bounded_analysis_stage','cp7_history_bounded','cp7_history_reference')and p.prokind='f'
$$;
create function cp7_bounded_analysis_stage.work_fingerprint(c jsonb)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare stock jsonb:=c->'bounded_stock_reference';producer text:=c->>'bounded_producer_hash';
begin
 if c->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v1'
  or c->>'bounded_reference_contract'is distinct from'cp7.bounded-analysis-reference.v1'
  or producer is null or producer!~'^[0-9a-f]{64}$'
  or stock->>'contract_version'is distinct from'cp7.native-stock-row-digest.v1'
  or stock->>'scope'is distinct from'ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS'
  or stock->'captured_at'is distinct from c->'captured_at'
  or stock->>'rows_sha256'is null or stock->>'rows_sha256'!~'^[0-9a-f]{64}$'
  or stock->>'row_count'is null or stock->>'row_count'!~'^(0|[1-9][0-9]{0,19})$'
  or stock->'raw_rows_truncated'is distinct from'false'::jsonb
  or stock->'raw_native_capture_status_overridden'is distinct from'false'::jsonb then
  raise exception 'CP7_BOUNDED_ANALYSIS_REFERENCE_SHAPE';end if;
 -- No capture clock or selected demand query enters work-calendar identity.
 return encode(extensions.digest(convert_to(jsonb_build_object('contract','cp7.bounded-work-source.v1',
  'native',cp7_bounded_analysis_stage.native_work_fingerprint(c),'full_stock_rows',stock->'rows_sha256',
  'producer',producer)::text,'UTF8'),'sha256'),'hex');
end $$;
create function cp7_bounded_analysis_stage.source(p_query jsonb,p_with_inputs boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare q jsonb;c jsonb;b jsonb:=cp7_analysis_stage.bounds();stock jsonb;summary jsonb;inputs jsonb;
 lo date;hi date;products integer;
begin
 if p_with_inputs is null then raise exception 'CP7_BOUNDED_ANALYSIS_CAPTURE_MODE';end if;
 q:=cp7_planning.history_query(p_query);
 c:=cp7_bounded_analysis_stage.analysis_source((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
   ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');
 products:=jsonb_array_length(c->'facts'->'products');
 if products>(b->>'job_targets')::integer then raise exception 'CP7_ANALYSIS_STAGED_TARGET_LIMIT';end if;
 lo:=cp7_demand.day(q->'from_date');hi:=cp7_demand.day(q->'through_date');
 if hi<lo or hi-lo>3660 or hi>=((c->>'captured_at')::timestamptz at time zone'Asia/Jakarta')::date
  or products::bigint*(hi-lo+1)>(b->>'job_history_cells')::bigint then raise exception 'CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE';end if;
 stock:=cp7_history_reference.stock_digest(c->'facts'->'products',(c->>'captured_at')::timestamptz);
 if p_with_inputs then
  if c->'stock_raw_omitted'='true'::jsonb or jsonb_array_length(c->'facts'->'stock')=50001 then
   summary:=cp7_reorder_inputs.stock_summary(c->'facts'->'products',(c->>'captured_at')::timestamptz,q);
  end if;
  inputs:=cp7_history_bounded.compile(c,q,summary,(b->>'job_targets')::integer);
  if inputs->>'coverage'is distinct from'COMPLETE'or inputs->'raw_native_capture_status'is distinct from c->'status'
   or inputs->'captured_at'is distinct from c->'captured_at'or inputs->'query'is distinct from q then
   raise exception 'CP7_BOUNDED_ANALYSIS_INPUT_BINDING';end if;
 end if;
 return c||jsonb_build_object('bounded_request_contract','cp7.bounded-analysis-request.v1',
  'bounded_reference_contract','cp7.bounded-analysis-reference.v1','bounded_query',q,
  'bounded_producer_hash',cp7_bounded_analysis_stage.producer_hash(),'bounded_stock_reference',stock,
  'bounded_history_inputs',inputs);
end $$;

alter function cp7_bounded_analysis_stage.source_parts(integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.source_parts(integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.schedule_source(integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.schedule_source(integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.netting_source(integer,integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.netting_source(integer,integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.analysis_source(integer,integer) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.analysis_source(integer,integer) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.native_work_fingerprint(jsonb) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.native_work_fingerprint(jsonb) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.work_fingerprint(jsonb) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.work_fingerprint(jsonb) from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.producer_hash() owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.producer_hash() from public,anon,authenticated,service_role;
alter function cp7_bounded_analysis_stage.source(jsonb,boolean) owner to cp7_capture;
revoke all on function cp7_bounded_analysis_stage.source(jsonb,boolean) from public,anon,authenticated,service_role;
