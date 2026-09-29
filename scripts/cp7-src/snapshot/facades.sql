create function cp7_private.serve(p_run uuid,p_domain text,p_cursor text,p_limit integer) returns jsonb
language plpgsql volatile security invoker set search_path='' set timezone='Asia/Jakarta' as $$
declare a jsonb; r cp7_private.analysis_runs%rowtype; p jsonb; live jsonb;
 money boolean; n integer; pos integer:=0; page jsonb; answer jsonb; prefix text;
begin
 if current_setting('transaction_isolation')<>'read committed' then
  raise exception using errcode='25001',message='CP7_FRESH_ACCESS_TRANSACTION_REQUIRED';
 end if;
 a:=cp7_private.access_now();
 if p_domain is null or p_domain not in ('physical','commercial','cutting_candidates','stock_movements','sales_lines','lot_cost')
    or p_limit is null or p_limit not between 1 and 100 then
  raise exception using errcode='22023',message='CP7_PAGE_INVALID';
 end if;
 if p_domain='lot_cost' and not (a->>'financial')::boolean then
  raise exception using errcode='42501',message='CP7_FINANCIAL_ACCESS_DENIED';
 end if;
 select * into r from cp7_private.analysis_runs where id=p_run and actor=auth.uid();
 if not found then raise exception using errcode='42501',message='CP7_RUN_UNAVAILABLE'; end if;
 money:=r.financial_captured and (a->>'financial')::boolean;
 if p_domain='lot_cost' and not money then
  raise exception using errcode='22023',message='CP7_FINANCIAL_NOT_CAPTURED';
 end if;
 p:=cp7_private.project(r.payload,money);
 n:=(p->'counts'->>p_domain)::integer;
 if p_cursor is not null then
  prefix:=p_run::text||':'||p_domain||':';
  if left(p_cursor,length(prefix))<>prefix or substr(p_cursor,length(prefix)+1)!~'^(0|[1-9][0-9]{0,3})$' then
   raise exception using errcode='22023',message='CP7_CURSOR_INVALID';
  end if;
  pos:=substr(p_cursor,length(prefix)+1)::integer;
  if pos>n then raise exception using errcode='22023',message='CP7_CURSOR_INVALID'; end if;
 end if;
 select coalesce(jsonb_agg(value order by ordinality),'[]') into page
 from jsonb_array_elements(p->'sources'->p_domain) with ordinality
 where ordinality>pos and ordinality<=pos+p_limit;
 live:=cp7_private.project(cp7_private.capture_sources(r.root_id,money),money);
 answer:=jsonb_build_object('contract_version','cp7.snapshot-page.v1','run_id',r.id,
  'scope',p->'scope','snapshot',p->'snapshot','financial_captured',money,
  'counts',p->'counts','projection_hash',p->'snapshot_hash',
  'source_state',case when live->>'status'<>'COMPLETE' then 'SOURCE_UNAVAILABLE'
    when live->>'snapshot_hash'<>p->>'snapshot_hash' then 'ARCHIVED_STALE' else 'CURRENT' end,
  'page',jsonb_build_object('domain',p_domain,'total',n,'rows',page,
    'next_cursor',case when pos+p_limit<n then p_run::text||':'||p_domain||':'||(pos+p_limit)::text else null end));
 -- A revocation committed while sources were being read refuses the response.
 if cp7_private.access_now()<>a then
  raise exception using errcode='42501',message='CP7_ACCESS_CHANGED';
 end if;
 return answer;
end $$;

create function cp7_private.capture_run(p_root uuid,p_request uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' set timezone='Asia/Jakarta' as $$
declare a jsonb; r cp7_private.analysis_runs%rowtype; money boolean;
begin
 if current_setting('transaction_isolation')<>'read committed' then
  raise exception using errcode='25001',message='CP7_FRESH_ACCESS_TRANSACTION_REQUIRED';
 end if;
 a:=cp7_private.access_now();
 if p_root is null or p_request is null then raise exception using errcode='22023',message='CP7_REQUEST_INVALID'; end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7_CAPTURE:'||auth.uid()::text||':'||p_request::text,0));
 select * into r from cp7_private.analysis_runs where actor=auth.uid() and request_id=p_request;
 if found then
  if r.root_id<>p_root then raise exception using errcode='22023',message='CP7_REQUEST_REUSED'; end if;
 else
  money:=(a->>'financial')::boolean;
  -- Facts, domain hashes and manifest are persisted by this one statement.
  with facts as materialized (
   select cp7_private.project(cp7_private.capture_sources(p_root,money),money) p
  ) insert into cp7_private.analysis_runs(actor,request_id,root_id,financial_captured,captured_at,access_at_capture,payload,dependencies)
   select auth.uid(),p_request,p_root,money,(p->'snapshot'->>'generated_at')::timestamptz,a,p,cp7_private.dependencies(p)
   from facts where p->>'status'='COMPLETE'
   returning * into r;
  if not found then raise exception using errcode='22023',message='CP7_SOURCE_INCOMPLETE'; end if;
 end if;
 if cp7_private.access_now()<>a then raise exception using errcode='42501',message='CP7_ACCESS_CHANGED'; end if;
 return cp7_private.serve(r.id,'physical',null,100);
end $$;

create function public.erp_cp7_capture_snapshot_v1(p_root uuid,p_request uuid) returns jsonb
language sql volatile security definer set search_path='' as $$
 select cp7_private.capture_run(p_root,p_request)
$$;
create function public.erp_cp7_read_snapshot_v1(p_run uuid,p_domain text default 'physical',p_cursor text default null,p_limit integer default 100) returns jsonb
language sql volatile security definer set search_path='' as $$
 select cp7_private.serve(p_run,p_domain,p_cursor,p_limit)
$$;

grant create on schema public to cp7_capture;
alter function public.erp_cp7_capture_snapshot_v1(uuid,uuid) owner to cp7_capture;
alter function public.erp_cp7_read_snapshot_v1(uuid,text,text,integer) owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on all functions in schema cp7_private from public,anon,authenticated,service_role;
grant execute on all functions in schema cp7_private to cp7_capture;
revoke all on function public.erp_cp7_capture_snapshot_v1(uuid,uuid),public.erp_cp7_read_snapshot_v1(uuid,text,text,integer) from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_snapshot_v1(uuid,uuid),public.erp_cp7_read_snapshot_v1(uuid,text,text,integer) to authenticated;
