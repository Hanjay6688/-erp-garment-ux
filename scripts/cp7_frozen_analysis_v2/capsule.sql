-- Private frozen inputs only. No request, unit, cache table or old replacement.
create schema cp7_frozen_analysis_v2 authorization cp7_capture;
revoke all on schema cp7_frozen_analysis_v2 from public,anon,authenticated,service_role;

create function cp7_frozen_analysis_v2.base(c jsonb)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select c-array['bounded_request_contract','bounded_reference_contract','bounded_query',
  'bounded_producer_hash','bounded_stock_reference','bounded_history_inputs','bounded_input_coverage',
  'bounded_capture_state','bounded_frozen_stock_summary','bounded_capsule_hash']
$$;

create function cp7_frozen_analysis_v2.admit(c jsonb,q jsonb,p_cap integer)returns void
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare f jsonb:=c->'facts';lo date;hi date;at timestamptz;n integer;
begin
 perform cp7_wip.fields(q,array['from_date','through_date','group_mode']);
 if p_cap is null or p_cap not between 1 and 5000
  or c->>'contract_version'is distinct from'cp7.native-demand-facts.v1'
  or c->>'scope'is distinct from'GLOBAL_CURRENT_PHYSICAL_ROOTS'
  or jsonb_typeof(c)is distinct from'object'then raise exception 'CP7_BOUNDED_HISTORY_SOURCE_SHAPE';end if;
 at:=cp7_demand.instant(c->'captured_at');
 perform cp7_wip.fields(f,array['products','stock','sales','sale_journals','returns','return_journals']);
 perform cp7_demand.items(f->'products',p_cap);perform cp7_demand.items(f->'stock',50001);
 perform cp7_demand.items(f->'sales',50000);perform cp7_demand.items(f->'sale_journals',50000);
 perform cp7_demand.items(f->'returns',50000);perform cp7_demand.items(f->'return_journals',50000);
 n:=jsonb_array_length(f->'products');lo:=cp7_demand.day(q->'from_date');hi:=cp7_demand.day(q->'through_date');
 if hi<lo or hi-lo>3660 or hi>=(at at time zone'Asia/Jakarta')::date
  or q->>'group_mode'is null or q->>'group_mode'not in('AS_SOLD','RESTATED')
  or n::bigint*(hi-lo+1)>(cp7_analysis_stage.bounds()->>'job_history_cells')::bigint then
  raise exception 'CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE';end if;
 if c->>'status'='COMPLETE'then
  if jsonb_array_length(f->'stock')>50000
   or jsonb_array_length(f->'products')>p_cap
   or exists(select 1 from jsonb_each(f)where key not in('products','stock')and jsonb_array_length(value)>50000)
   or jsonb_array_length(f->'products')<>(select count(distinct x->>'root_id')from jsonb_array_elements(f->'products')x)
   or exists(select 1 from jsonb_array_elements(f->'products')x where jsonb_array_length(x->'commercial')>1)
   or exists(select 1 from jsonb_array_elements(f->'sales')x where jsonb_array_length(x->'sold_commercial')>1)
   or exists(select 1 from jsonb_array_elements(f->'sales')sale left join(
    select j->>'sale_id'sale_id,count(*)n from jsonb_array_elements(f->'sale_journals')j
     where j->'reversal_of_id'='null'::jsonb group by 1)originals on originals.sale_id=sale->>'sale_id'
    where sale->>'status'in('POSTED','PARTIAL_PAID','PAID','REVERSED')and coalesce(originals.n,0)<>1)then
   raise exception 'CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE';end if;

 else
  perform cp7_wip.fields(f,array['products','stock','sales','sale_journals','returns','return_journals']);
  if c->>'status'is distinct from'INCOMPLETE'or not(jsonb_array_length(f->'stock')=50001
   or coalesce(c->'stock_raw_omitted'='true'::jsonb and c->'stock_rows_at_least'='50001'::jsonb and jsonb_array_length(f->'stock')=0,false))
   or jsonb_array_length(f->'products')>p_cap
   or exists(select 1 from jsonb_each(f)where key not in('products','stock')and jsonb_array_length(value)>50000)
   or jsonb_array_length(f->'products')<>(select count(distinct x->>'root_id')from jsonb_array_elements(f->'products')x)
   or exists(select 1 from jsonb_array_elements(f->'products')x where jsonb_array_length(x->'commercial')>1)
   or exists(select 1 from jsonb_array_elements(f->'sales')x where jsonb_array_length(x->'sold_commercial')>1)
   or exists(select 1 from jsonb_array_elements(f->'sales')sale left join(
    select j->>'sale_id'sale_id,count(*)n from jsonb_array_elements(f->'sale_journals')j
     where j->'reversal_of_id'='null'::jsonb group by 1)originals on originals.sale_id=sale->>'sale_id'
    where sale->>'status'in('POSTED','PARTIAL_PAID','PAID','REVERSED')and coalesce(originals.n,0)<>1)then
   raise exception 'CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE';end if;

 end if;
end $$;

create function cp7_frozen_analysis_v2.stock_reference(c jsonb,stock jsonb)returns void
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 perform cp7_wip.fields(stock,array['contract_version','encoding','layout_sha256','scope','captured_at',
  'row_count','rows_sha256','raw_rows_truncated','raw_rows_materialized_as_JSON_array',
  'raw_native_capture_status_overridden','apply_enabled','production_go']);
 if stock->>'contract_version'is distinct from'cp7.native-stock-row-digest.v2'
  or stock->>'encoding'is distinct from'POSTGRES17_RECORD_SEND_TEXT_AS_UTF8_BYTEA_V1'
  or stock->>'layout_sha256'is distinct from'9fa5d22b53d337a6472898a5eec99ae7b221aea93313d693588e69cc6e83f32a'
  or stock->>'scope'is distinct from'ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS'
  or stock->'captured_at'is distinct from c->'captured_at'
  or jsonb_typeof(stock->'row_count')is distinct from'string'
  or stock->>'row_count'!~'^(0|[1-9][0-9]{0,18})$'
  or jsonb_typeof(stock->'rows_sha256')is distinct from'string'
  or stock->>'rows_sha256'!~'^[0-9a-f]{64}$'
  or stock->'raw_rows_truncated'is distinct from'false'::jsonb
  or stock->'raw_rows_materialized_as_JSON_array'is distinct from'false'::jsonb
  or stock->'raw_native_capture_status_overridden'is distinct from'false'::jsonb
  or stock->'apply_enabled'is distinct from'false'::jsonb
  or stock->'production_go'is distinct from'false'::jsonb then
  raise exception 'CP7_FROZEN_V2_STOCK_REFERENCE';end if;
 if(stock->>'row_count')::numeric>9223372036854775807 then raise exception 'CP7_FROZEN_V2_STOCK_REFERENCE';end if;
end $$;

create function cp7_frozen_analysis_v2.capsule_hash(c jsonb,q jsonb,stock jsonb,summary jsonb,producer text)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('contract','cp7.frozen-analysis-capsule.v2',
  'base',c,'query',q,'full_stock_reference',stock,'frozen_stock_summary',summary,'producer',producer)::text,'UTF8'),'sha256'),'hex')
$$;

create function cp7_frozen_analysis_v2.reference(c jsonb,q jsonb,stock jsonb,producer text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if cp7_frozen_analysis_v2.base(c)is distinct from c or producer is null or producer!~'^[0-9a-f]{64}$'then
  raise exception 'CP7_FROZEN_V2_BASE_OR_PRODUCER';end if;
 perform cp7_frozen_analysis_v2.stock_reference(c,stock);
 return c||jsonb_build_object('bounded_request_contract','cp7.bounded-analysis-request.v2',
  'bounded_reference_contract','cp7.bounded-analysis-reference.v2','bounded_query',q,
  'bounded_producer_hash',producer,'bounded_stock_reference',stock,
  'bounded_history_inputs',null,'bounded_input_coverage','NOT_CAPTURED','bounded_capture_state','REFERENCE_ONLY');
end $$;

create function cp7_frozen_analysis_v2.seal(c jsonb,q jsonb,stock jsonb,summary jsonb,producer text,p_cap integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare answer jsonb;n integer:=jsonb_array_length(c->'facts'->'products');
begin
 perform cp7_frozen_analysis_v2.admit(c,q,p_cap);
 answer:=cp7_frozen_analysis_v2.reference(c,q,stock,producer);
 if c->>'status'='COMPLETE'then
  if summary is not null or(stock->>'row_count')::bigint<>jsonb_array_length(c->'facts'->'stock')then
   raise exception 'CP7_FROZEN_V2_COMPLETE_STOCK_COUNT';end if;
 else
  if summary->>'contract_version'is distinct from'cp7.reorder-stock-summary.v1'
   or summary->'captured_at'is distinct from c->'captured_at' or summary->'query'is distinct from q
   or summary->'products'is distinct from to_jsonb(n)
   or summary->'raw_rows_truncated'is distinct from'false'::jsonb
   or summary->'Native_capture_status_overridden'is distinct from'false'::jsonb
   or summary->>'data_hash'is null or summary->>'data_hash'!~'^[0-9a-f]{64}$'
   or summary->>'history_data_hash'is null or summary->>'history_data_hash'!~'^[0-9a-f]{64}$'
   or summary->>'raw_rows_read'is null or summary->>'raw_rows_read'!~'^(0|[1-9][0-9]{0,18})$'
   or jsonb_typeof(summary->'availability')is distinct from'array'
   or jsonb_typeof(summary->'current_stock')is distinct from'array'then
   raise exception 'CP7_REORDER_STOCK_SNAPSHOT_MISMATCH';end if;
  if(summary->>'raw_rows_read')::numeric is distinct from(stock->>'row_count')::numeric
   or(summary->>'raw_rows_read')::numeric<50001 then raise exception 'CP7_FROZEN_V2_FULL_STOCK_COUNT';end if;
 end if;
 return answer||jsonb_build_object('bounded_capture_state','FROZEN','bounded_input_coverage','PENDING',
  'bounded_frozen_stock_summary',summary,
  'bounded_capsule_hash',cp7_frozen_analysis_v2.capsule_hash(c,q,stock,summary,producer));
end $$;

create function cp7_frozen_analysis_v2.verify_capsule(c jsonb,q jsonb,p_cap integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare raw jsonb:=cp7_frozen_analysis_v2.base(c);expected jsonb;
begin
 if c->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v2'
  or c->>'bounded_reference_contract'is distinct from'cp7.bounded-analysis-reference.v2'
  or c->'bounded_query'is distinct from q or c->>'bounded_capture_state'is distinct from'FROZEN'
  or c->>'bounded_input_coverage'is distinct from'PENDING'
  or c->'bounded_history_inputs'is distinct from'null'::jsonb then raise exception 'CP7_FROZEN_V2_CAPSULE_BINDING';end if;
 expected:=cp7_frozen_analysis_v2.seal(raw,q,c->'bounded_stock_reference',
  nullif(c->'bounded_frozen_stock_summary','null'::jsonb),c->>'bounded_producer_hash',p_cap);
 if expected is distinct from c then raise exception 'CP7_FROZEN_V2_CAPSULE_BINDING';end if;
 return raw;
end $$;

create function cp7_frozen_analysis_v2.work_fingerprint(c jsonb)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare producer text:=c->>'bounded_producer_hash';
begin
 if c->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v2'
  or c->>'bounded_reference_contract'is distinct from'cp7.bounded-analysis-reference.v2'
  or producer is null or producer!~'^[0-9a-f]{64}$'then raise exception 'CP7_FROZEN_V2_REFERENCE_SHAPE';end if;
 perform cp7_frozen_analysis_v2.stock_reference(c,c->'bounded_stock_reference');
 -- Versioned work identity binds all original facts and every full stock row.
 -- Query, capture time, derived inputs and capsule state never enter it.
 return encode(extensions.digest(convert_to(jsonb_build_object('contract','cp7.bounded-work-source.v2',
  'native',cp7_bounded_analysis_stage.native_work_fingerprint(cp7_frozen_analysis_v2.base(c)),
  'full_stock_rows',(c->'bounded_stock_reference')-'captured_at','producer',producer)::text,'UTF8'),'sha256'),'hex');
end $$;

create function cp7_frozen_analysis_v2.prepare(c jsonb,q jsonb,p_cap integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare raw jsonb;answer jsonb;i jsonb;keys jsonb;n integer;
begin
 raw:=cp7_frozen_analysis_v2.verify_capsule(c,q,p_cap);
 -- This existing compiler is unchanged. Every operand comes from the frozen
 -- capsule; this function has no table read, clock lookup or capture call.
 answer:=cp7_history_bounded.compile(raw,q,nullif(c->'bounded_frozen_stock_summary','null'::jsonb),p_cap);
 i:=answer->'inputs';n:=jsonb_array_length(raw->'facts'->'products');
 if answer->>'contract_version'is distinct from'cp7.bounded-history-inputs.v1'
  or answer->>'coverage'is distinct from'COMPLETE' or answer->'captured_at'is distinct from raw->'captured_at'
  or answer->'query'is distinct from q or answer->'raw_native_capture_status'is distinct from raw->'status'
  or answer->'raw_native_status_overridden'is distinct from'false'::jsonb
  or answer->'apply_enabled'is distinct from'false'::jsonb or answer->'production_go'is distinct from'false'::jsonb
  or i->>'contract_version'is distinct from'cp7.reorder-native-inputs.v1'
  or i->'captured_at'is distinct from raw->'captured_at' or i->'query'is distinct from q
  or i->'products'is distinct from raw->'facts'->'products'
  or i->>'source_hash'is null or i->>'source_hash'!~'^[0-9a-f]{64}$'
  or i->>'history_hash'is null or i->>'history_hash'!~'^[0-9a-f]{64}$'
  or jsonb_typeof(i->'history')is distinct from'array' or jsonb_typeof(i->'current_stock')is distinct from'array'
  or jsonb_typeof(i->'targets')is distinct from'array' then raise exception 'CP7_BOUNDED_ANALYSIS_INPUT_BINDING';end if;
 select coalesce(jsonb_object_agg((p->>'root_id')||':'||(p->>'size_id'),true),'{}')into keys
  from jsonb_array_elements(raw->'facts'->'products')p;
 if exists(select 1 from jsonb_each(jsonb_build_object('history',i->'history','stock',i->'current_stock','targets',i->'targets'))a
  where jsonb_array_length(a.value)<>n or n<>(select count(distinct x->>'target_key')from jsonb_array_elements(a.value)x)
   or exists(select 1 from jsonb_array_elements(a.value)x where not(keys?(x->>'target_key'))))then
  raise exception 'CP7_BOUNDED_ANALYSIS_INPUT_TARGETS';end if;
 return answer;
end $$;

create function cp7_frozen_analysis_v2.producer_hash()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('contract','cp7.frozen-analysis-producer.v2',
  'predecessor',cp7_bounded_analysis_stage.producer_hash(),'new_definitions',(
   select string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text)
   from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where n.nspname in('cp7_frozen_analysis_v2','cp7_history_reference_binary_v2')and p.prokind='f'))::text,'UTF8'),'sha256'),'hex')
$$;

create function cp7_frozen_analysis_v2.source(p_query jsonb,p_with_capsule boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare q jsonb;c jsonb;b jsonb:=cp7_analysis_stage.bounds();stock jsonb;summary jsonb;producer text;
begin
 if p_with_capsule is null then raise exception 'CP7_BOUNDED_ANALYSIS_CAPTURE_MODE';end if;
 q:=cp7_planning.history_query(p_query);
 c:=cp7_bounded_analysis_stage.analysis_source((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
  ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');
 perform cp7_frozen_analysis_v2.admit(c,q,(b->>'job_targets')::integer);
 stock:=cp7_history_reference_binary_v2.stock_digest(c->'facts'->'products',(c->>'captured_at')::timestamptz);
 producer:=cp7_frozen_analysis_v2.producer_hash();
 if not p_with_capsule then return cp7_frozen_analysis_v2.reference(c,q,stock,producer);end if;
 if c->>'status'='INCOMPLETE'then
  summary:=cp7_reorder_inputs.stock_summary(c->'facts'->'products',(c->>'captured_at')::timestamptz,q);
 end if;
 return cp7_frozen_analysis_v2.seal(c,q,stock,summary,producer,(b->>'job_targets')::integer);
end $$;
alter function cp7_frozen_analysis_v2.base(jsonb) owner to cp7_capture;
revoke all on function cp7_frozen_analysis_v2.base(jsonb) from public,anon,authenticated,service_role;
alter function cp7_frozen_analysis_v2.admit(jsonb,jsonb,integer) owner to cp7_capture;
revoke all on function cp7_frozen_analysis_v2.admit(jsonb,jsonb,integer) from public,anon,authenticated,service_role;
alter function cp7_frozen_analysis_v2.stock_reference(jsonb,jsonb) owner to cp7_capture;
revoke all on function cp7_frozen_analysis_v2.stock_reference(jsonb,jsonb) from public,anon,authenticated,service_role;
alter function cp7_frozen_analysis_v2.capsule_hash(jsonb,jsonb,jsonb,jsonb,text) owner to cp7_capture;
revoke all on function cp7_frozen_analysis_v2.capsule_hash(jsonb,jsonb,jsonb,jsonb,text) from public,anon,authenticated,service_role;
alter function cp7_frozen_analysis_v2.reference(jsonb,jsonb,jsonb,text) owner to cp7_capture;
revoke all on function cp7_frozen_analysis_v2.reference(jsonb,jsonb,jsonb,text) from public,anon,authenticated,service_role;
alter function cp7_frozen_analysis_v2.seal(jsonb,jsonb,jsonb,jsonb,text,integer) owner to cp7_capture;
revoke all on function cp7_frozen_analysis_v2.seal(jsonb,jsonb,jsonb,jsonb,text,integer) from public,anon,authenticated,service_role;
alter function cp7_frozen_analysis_v2.verify_capsule(jsonb,jsonb,integer) owner to cp7_capture;
revoke all on function cp7_frozen_analysis_v2.verify_capsule(jsonb,jsonb,integer) from public,anon,authenticated,service_role;
alter function cp7_frozen_analysis_v2.work_fingerprint(jsonb) owner to cp7_capture;
revoke all on function cp7_frozen_analysis_v2.work_fingerprint(jsonb) from public,anon,authenticated,service_role;
alter function cp7_frozen_analysis_v2.prepare(jsonb,jsonb,integer) owner to cp7_capture;
revoke all on function cp7_frozen_analysis_v2.prepare(jsonb,jsonb,integer) from public,anon,authenticated,service_role;
alter function cp7_frozen_analysis_v2.producer_hash() owner to cp7_capture;
revoke all on function cp7_frozen_analysis_v2.producer_hash() from public,anon,authenticated,service_role;
alter function cp7_frozen_analysis_v2.source(jsonb,boolean) owner to cp7_capture;
revoke all on function cp7_frozen_analysis_v2.source(jsonb,boolean) from public,anon,authenticated,service_role;
