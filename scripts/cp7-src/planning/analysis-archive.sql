-- Durable actor-owned report pointers. Never return cached stock/money facts
-- from the index; reopening still executes the original current-authority read.
create index cp7_analysis_actor_time on cp7_analysis_native.runs(actor,captured_at desc,id desc);
create function cp7_analysis_native.archives(p jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;report_access boolean;preflight_access boolean;page_size integer;
 cursor_id uuid;cursor_at timestamptz;rows jsonb;total bigint;remaining bigint;next_id text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if jsonb_typeof(p)is distinct from 'object'or not p?&array['before_run','limit']
  or exists(select 1 from jsonb_object_keys(p)k where k not in('before_run','limit'))
  or jsonb_typeof(p->'before_run')not in('null','string')
  or jsonb_typeof(p->'limit')is distinct from 'number'or(p->>'limit')!~'^[1-9][0-9]{0,1}$'
  then raise exception 'CP7_ANALYSIS_ARCHIVE_QUERY';end if;
 page_size:=(p->>'limit')::integer;if page_size>50 then raise exception 'CP7_ANALYSIS_ARCHIVE_QUERY';end if;
 cursor_id:=(p->>'before_run')::uuid;
 report_access:=coalesce(a->'profile'->>'role_code'in('OWNER','ADMIN')and erp.has_permission('finance.reports.view'),false);
 preflight_access:=report_access and erp.has_permission('finance.period_close.manage');
 if cursor_id is not null then
  select r.captured_at into cursor_at from cp7_analysis_native.runs r
  where r.actor=(a->>'actor')::uuid and r.id=cursor_id
   and(coalesce(r.facts->'financial_source','null')='null'::jsonb or report_access)
   and(coalesce(r.facts->'financial_source'->'report'->'close_preflight','null')='null'::jsonb or preflight_access);
  if not found then raise exception using errcode='42501',message='CP7_ANALYSIS_ARCHIVE_CURSOR_UNAVAILABLE';end if;
 end if;
 with visible as materialized(
  select r.id,r.captured_at,r.request_id,r.query,r.result->'snapshot'->>'generated_at'original_at,
   r.result->'snapshot'->>'source_hash'original_source_hash,r.result->>'semantic_hash'original_semantic_hash
  from cp7_analysis_native.runs r where r.actor=(a->>'actor')::uuid
   and(coalesce(r.facts->'financial_source','null')='null'::jsonb or report_access)
   and(coalesce(r.facts->'financial_source'->'report'->'close_preflight','null')='null'::jsonb or preflight_access)),
 eligible as materialized(select *from visible where cursor_id is null or(captured_at,id)<(cursor_at,cursor_id)),
 page as materialized(select *from eligible order by captured_at desc,id desc limit page_size)
 select coalesce((select jsonb_agg(jsonb_build_object('runId',id,'requestId',request_id,'query',query,
  'capturedAt',original_at,'sourceHash',original_source_hash,
  'semanticHash',original_semantic_hash)order by captured_at desc,id desc)from page),'[]'),
  (select count(*)from visible),(select count(*)from eligible),
  (select id::text from page order by captured_at,id limit 1)
 into rows,total,remaining,next_id;
 if cp7_schedule_native.access_now(false)is distinct from a
  or report_access is distinct from coalesce(a->'profile'->>'role_code'in('OWNER','ADMIN')and erp.has_permission('finance.reports.view'),false)
  or preflight_access is distinct from(report_access and erp.has_permission('finance.period_close.manage'))then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-analysis-archives.v1','actor_scope_id',a->>'actor',
  'rows',rows,'total_visible',total::text,'next_before_run',case when remaining>page_size then next_id else null end,
  'page_complete',true,'read_at',statement_timestamp());
end $$;
alter function cp7_analysis_native.archives(jsonb)owner to cp7_capture;
revoke all on function cp7_analysis_native.archives(jsonb)from public,anon,authenticated,service_role;
create function public.erp_cp7_list_analysis_archives_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_native.archives(p_query)$$;
alter function public.erp_cp7_list_analysis_archives_v1(jsonb)owner to cp7_capture;
revoke all on function public.erp_cp7_list_analysis_archives_v1(jsonb)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_list_analysis_archives_v1(jsonb)to authenticated;
