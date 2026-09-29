-- One declared scope, one capture clock and one statement snapshot across the
-- three origin types. This is not a sum of separately captured runs.
create function cp7_wip.production_scope(s jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare k text;a uuid[];result jsonb:='{}';n integer:=0;
begin
 perform cp7_wip.fields(s,array['cutting_groups','opening_items','unsourced_bs']);
 foreach k in array array['cutting_groups','opening_items','unsourced_bs'] loop
  if jsonb_typeof(s->k) is distinct from 'array' or jsonb_array_length(s->k)>50
   or exists(select 1 from jsonb_array_elements(s->k) where jsonb_typeof(value)<>'string') then raise exception 'CP7_WIP_SCOPE';end if;
  select coalesce(array_agg(distinct value::uuid order by value::uuid),'{}'::uuid[]) into a from jsonb_array_elements_text(s->k);
  if cardinality(a)<>jsonb_array_length(s->k) then raise exception 'CP7_WIP_SCOPE';end if;
  n:=n+cardinality(a);result:=result||jsonb_build_object(k,to_jsonb(a));
 end loop;
 if n not between 1 and 50 then raise exception 'CP7_WIP_SCOPE';end if;
 return result;
end $$;
create function cp7_wip.capture_production_sources(s jsonb) returns jsonb
language sql stable security invoker set search_path='' as $$
with clock as materialized(select clock_timestamp() at),
cutting as materialized(select cp7_wip.capture_cutting_sources(array(select value::uuid from jsonb_array_elements_text(s->'cutting_groups')),at) data from clock),
other as materialized(select cp7_wip.capture_other_sources(array(select value::uuid from jsonb_array_elements_text(s->'opening_items')),
 array(select value::uuid from jsonb_array_elements_text(s->'unsourced_bs')),at) data from clock)
select jsonb_build_object('contract_version','cp7.production-facts.v1','captured_at',clock.at,
 'status',case when cutting.data->>'status'='COMPLETE' and other.data->>'status'='COMPLETE' then 'COMPLETE' else 'INCOMPLETE' end,
 'facts',jsonb_build_object('cutting',cutting.data->'facts','other',other.data->'facts')) from clock,cutting,other
$$;
create function cp7_wip.normalize_production(capture jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare cut jsonb;other jsonb;g jsonb;graph jsonb;e jsonb;prefix text;result jsonb;
begin
 if capture->>'contract_version' is distinct from 'cp7.production-facts.v1' or capture->>'status' is distinct from 'COMPLETE' then
  return jsonb_build_object('status','UNKNOWN','reason','PRODUCTION_CAPTURE_INCOMPLETE');end if;
 cut:=cp7_wip.normalize_cutting(jsonb_build_object('contract_version','cp7.cutting-facts.v1','status','COMPLETE','captured_at',capture->'captured_at','facts',capture->'facts'->'cutting'));
 other:=cp7_wip.normalize_other(jsonb_build_object('contract_version','cp7.other-wip-facts.v1','status','COMPLETE','captured_at',capture->'captured_at','facts',capture->'facts'->'other'));
 if cut->>'status'<>'COMPLETE' then return cut||jsonb_build_object('component','CUTTING');end if;
 if other->>'status'<>'COMPLETE' then return other||jsonb_build_object('component','OPENING_UNSOURCED');end if;
 g:=jsonb_build_object('contract_version','cp7.wip-graph.v1','snapshot_id',capture->>'captured_at','complete',true,'pools','[]'::jsonb,'nodes','[]'::jsonb,'events','[]'::jsonb);
 foreach prefix in array array['cutting','other'] loop
  graph:=case when prefix='cutting' then cut->'graph' else other->'graph' end;
  g:=jsonb_set(g,'{pools}',(g->'pools')||(graph->'pools'));g:=jsonb_set(g,'{nodes}',(g->'nodes')||(graph->'nodes'));
  for e in select value from jsonb_array_elements(graph->'events') loop
   e:=e||jsonb_build_object('key',prefix||':'||(e->>'key'),'ordinal',(jsonb_array_length(g->'events')+1)::text,
    'reverses_key',case when e->>'reverses_key' is null then null else prefix||':'||(e->>'reverses_key') end);
   g:=jsonb_set(g,'{events}',g->'events'||jsonb_build_array(e));
  end loop;
 end loop;
 result:=cp7_wip.reconcile(g);
 return result||jsonb_build_object('graph',g,'source_basis','ONE_CAPTURE_EXPLICIT_PRODUCTION_ORIGINS',
  'scope','SELECTED_ORIGINS_ONLY','fg_basis','PRODUCTION_DISPOSITION_NOT_CURRENT_ON_HAND',
  'allocation_review_required',cut->'allocation_review_required','attention',cut->'attention',
  'sewing_detail','SUBSTAGE_NOT_ALLOCATABLE_FROM_GROUP_EVENTS','rewash_review_required',cut->'rewash_review_required',
  'timing',jsonb_build_object('quality','UNKNOWN','reason','NO_CALENDAR_OR_REMAINING_WORK_SELECTED','eta',null,'on_time',null));
end $$;

create table cp7_wip.production_runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 scope jsonb not null,captured_at timestamptz not null,facts jsonb not null,
 result jsonb not null,dependency_hash text not null,unique(actor,request_id)
);
alter table cp7_wip.production_runs owner to cp7_capture;
alter table cp7_wip.production_runs enable row level security;
revoke all on cp7_wip.production_runs from public,anon,authenticated,service_role;
create trigger cp7_production_immutable before update or delete on cp7_wip.production_runs for each row execute function cp7_private.immutable_run();
create function cp7_wip.serve_production(p_run uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;r cp7_wip.production_runs%rowtype;live jsonb;hash text;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();
 select * into r from cp7_wip.production_runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_WIP_RUN_UNAVAILABLE';end if;
 live:=cp7_wip.capture_production_sources(r.scope);
 hash:=encode(extensions.digest(convert_to((live->'facts')::text,'UTF8'),'sha256'),'hex');
 perform cp7_private.access_now();
 return jsonb_build_object('contract_version','cp7.production-wip-run.v1','run_id',r.id,'request_id',r.request_id,
  'captured_at',r.captured_at,'knowledge_mode','CURRENT_AT_CAPTURE','capture_complete',true,
  'source_state',case when live->>'status'='COMPLETE' and hash=r.dependency_hash then 'UNCHANGED' else 'ARCHIVED_STALE' end,
  'scope',r.scope,'result',r.result,'production_go',false);
end $$;
create function cp7_wip.capture_production(p_scope jsonb,p_request uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;s jsonb;r cp7_wip.production_runs%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();s:=cp7_wip.production_scope(p_scope);
 if p_request is null then raise exception 'CP7_WIP_SCOPE';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:PRODUCTION:'||(a->>'actor')||':'||p_request::text,0));
 perform cp7_private.access_now();
 select * into r from cp7_wip.production_runs where actor=(a->>'actor')::uuid and request_id=p_request;
 if r.id is not null then
  if r.scope<>s then raise exception 'CP7_WIP_REQUEST_REUSED';end if;
  return cp7_wip.serve_production(r.id);
 end if;
 with source as materialized(select cp7_wip.capture_production_sources(s) facts),
 normalized as materialized(select facts,cp7_wip.normalize_production(facts) result from source where facts->>'status'='COMPLETE')
 insert into cp7_wip.production_runs(actor,request_id,scope,captured_at,facts,result,dependency_hash)
 select (a->>'actor')::uuid,p_request,s,(facts->>'captured_at')::timestamptz,facts,result,
  encode(extensions.digest(convert_to((facts->'facts')::text,'UTF8'),'sha256'),'hex') from normalized returning * into r;
 if r.id is null then raise exception 'CP7_WIP_SOURCE_INCOMPLETE';end if;
 perform cp7_private.access_now();
 return cp7_wip.serve_production(r.id);
end $$;
create function public.erp_cp7_capture_production_wip_v1(p_scope jsonb,p_request uuid) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_wip.capture_production(p_scope,p_request)$$;
create function public.erp_cp7_read_production_wip_v1(p_run uuid) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_wip.serve_production(p_run)$$;
