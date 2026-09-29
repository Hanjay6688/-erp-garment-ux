create table cp7_wip.runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 groups uuid[] not null,captured_at timestamptz not null,facts jsonb not null,
 result jsonb not null,dependency_hash text not null,unique(actor,request_id)
);
alter table cp7_wip.runs owner to cp7_capture;
alter table cp7_wip.runs enable row level security;
revoke all on cp7_wip.runs from public,anon,authenticated,service_role;
create trigger cp7_wip_immutable before update or delete on cp7_wip.runs for each row execute function cp7_private.immutable_run();

create function cp7_wip.serve(p_run uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;r cp7_wip.runs%rowtype;live jsonb;hash text;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();
 select * into r from cp7_wip.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_WIP_RUN_UNAVAILABLE';end if;
 live:=cp7_wip.capture_cutting_sources(r.groups);
 hash:=encode(extensions.digest(convert_to((live->'facts')::text,'UTF8'),'sha256'),'hex');
 perform cp7_private.access_now();
 return jsonb_build_object('contract_version','cp7.cutting-wip-run.v1','run_id',r.id,'request_id',r.request_id,
  'captured_at',r.captured_at,'knowledge_mode','CURRENT_AT_CAPTURE','capture_complete',true,
  'source_state',case when live->>'status'='COMPLETE' and hash=r.dependency_hash then 'UNCHANGED' else 'ARCHIVED_STALE' end,
  'scope',jsonb_build_object('cutting_group_ids',to_jsonb(r.groups),'includes_opening_non_po',false),
  'result',r.result,'production_go',false);
end $$;
create function cp7_wip.capture(p_groups uuid[],p_request uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;groups uuid[];r cp7_wip.runs%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();
 if p_request is null or p_groups is null or cardinality(p_groups) not between 1 and 50 or array_position(p_groups,null) is not null then raise exception 'CP7_WIP_SCOPE';end if;
 select array_agg(distinct x order by x) into groups from unnest(p_groups) x;
 if cardinality(groups)<>cardinality(p_groups) then raise exception 'CP7_WIP_SCOPE';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:WIP:'||(a->>'actor')||':'||p_request::text,0));
 perform cp7_private.access_now();
 select * into r from cp7_wip.runs where actor=(a->>'actor')::uuid and request_id=p_request;
 if r.id is not null then
  if r.groups<>groups then raise exception 'CP7_WIP_REQUEST_REUSED';end if;
  return cp7_wip.serve(r.id);
 end if;
 with source as materialized(select cp7_wip.capture_cutting_sources(groups) facts),
 normalized as materialized(select facts,cp7_wip.normalize_cutting(facts) result from source where facts->>'status'='COMPLETE')
 insert into cp7_wip.runs(actor,request_id,groups,captured_at,facts,result,dependency_hash)
 select (a->>'actor')::uuid,p_request,groups,(facts->>'captured_at')::timestamptz,facts,result,
  encode(extensions.digest(convert_to((facts->'facts')::text,'UTF8'),'sha256'),'hex') from normalized returning * into r;
 if r.id is null then raise exception 'CP7_WIP_SOURCE_INCOMPLETE';end if;
 perform cp7_private.access_now();
 return cp7_wip.serve(r.id);
end $$;
create function public.erp_cp7_capture_cutting_wip_v1(p_groups uuid[],p_request uuid) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_wip.capture(p_groups,p_request)$$;
create function public.erp_cp7_read_cutting_wip_v1(p_run uuid) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_wip.serve(p_run)$$;
