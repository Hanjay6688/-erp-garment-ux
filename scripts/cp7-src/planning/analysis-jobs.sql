-- P19 background analysis and complete-Original segment transport.
-- A job is the unchanged capture compiler run in its own ordinary authenticated
-- request under the existing statement limit; no limit is raised. Its state is
-- committed per (actor, request UUID), so after a reload the operator sees when
-- the calculation started, whether a worker still holds it, that it stopped, or
-- its result. A stopped calculation commits nothing but its FAILED state.
-- A finished Original is cut once into immutable segments. A segment holds at
-- most 2,000,000 characters, so its UTF8 body never exceeds the existing
-- 8,000,000-byte body bound. Each segment read requires the actor's unchanged
-- current access (the epoch returned by the manifest, which performs the full
-- serve-equivalent check once) instead of recomputing the source per segment.
create schema cp7_analysis_jobs authorization cp7_capture;
revoke all on schema cp7_analysis_jobs from public,anon,authenticated,service_role;
create table cp7_analysis_jobs.jobs(actor uuid not null,request_id uuid not null,query jsonb not null,
 finance text not null check(finance in('INCLUDED','DEFERRED')),
 requested_at timestamptz not null,started_at timestamptz not null,attempts integer not null check(attempts>0),
 state text not null check(state in('WAITING','DONE','FAILED')),finished_at timestamptz,
 run_id uuid references cp7_analysis_native.runs(id),failure_sqlstate text,failure_code text,
 primary key(actor,request_id),
 check((state='DONE')=(run_id is not null)),check((state='FAILED')=(failure_code is not null)),
 check((state='WAITING')=(finished_at is null)),check(started_at>=requested_at));
create table cp7_analysis_jobs.documents(run_id uuid primary key references cp7_analysis_native.runs(id),
 utf8_bytes bigint not null check(utf8_bytes>0),characters bigint not null check(characters>0),sha256 text not null,
 segment_count integer not null check(segment_count>0),segment_characters integer not null check(segment_characters=2000000));
create table cp7_analysis_jobs.segments(run_id uuid not null references cp7_analysis_jobs.documents(run_id),
 idx integer not null check(idx>=0),body text not null,utf8_bytes integer not null check(utf8_bytes between 1 and 8000000),
 sha256 text not null,primary key(run_id,idx));
create index cp7_analysis_jobs_run on cp7_analysis_jobs.jobs(run_id);
alter table cp7_analysis_jobs.jobs owner to cp7_capture;
alter table cp7_analysis_jobs.documents owner to cp7_capture;
alter table cp7_analysis_jobs.segments owner to cp7_capture;
alter table cp7_analysis_jobs.jobs enable row level security;
alter table cp7_analysis_jobs.documents enable row level security;
alter table cp7_analysis_jobs.segments enable row level security;
create policy cp7_analysis_jobs_no_access on cp7_analysis_jobs.jobs for all to public using(false)with check(false);
create policy cp7_analysis_documents_no_access on cp7_analysis_jobs.documents for all to public using(false)with check(false);
create policy cp7_analysis_segments_no_access on cp7_analysis_jobs.segments for all to public using(false)with check(false);
revoke all on cp7_analysis_jobs.jobs,cp7_analysis_jobs.documents,cp7_analysis_jobs.segments from public,anon,authenticated,service_role;
create trigger immutable_analysis_document before update or delete on cp7_analysis_jobs.documents for each row execute function cp7_private.immutable_run();
create trigger immutable_analysis_segment before update or delete on cp7_analysis_jobs.segments for each row execute function cp7_private.immutable_run();

-- The capture compiler's own per-request lock. A job worker holds exactly it.
create function cp7_analysis_jobs.compute_key(p_actor uuid,p_request uuid)returns bigint
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select hashtextextended('CP7:ANALYSIS:'||p_actor::text||':'||p_request::text,0)
$$;
-- Observes the lock without taking it, so a status read never delays a worker.
create function cp7_analysis_jobs.worker_active(p_actor uuid,p_request uuid)returns boolean
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select exists(select 1 from pg_catalog.pg_locks l
  where l.locktype='advisory'and l.granted and l.objsubid=1
   and l.database=(select d.oid from pg_catalog.pg_database d where d.datname=pg_catalog.current_database())
   and l.classid=((cp7_analysis_jobs.compute_key(p_actor,p_request)>>32)&4294967295)::oid
   and l.objid=(cp7_analysis_jobs.compute_key(p_actor,p_request)&4294967295)::oid)
$$;
create function cp7_analysis_jobs.status(j cp7_analysis_jobs.jobs)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract_version','cp7.native-analysis-job.v1','request_id',j.request_id,'query',j.query,
  'state',case when j.state<>'WAITING'then j.state when cp7_analysis_jobs.worker_active(j.actor,j.request_id)then 'RUNNING'else 'WAITING'end,
  'requested_at',to_char(j.requested_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
  'started_at',to_char(j.started_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
  'finished_at',to_char(j.finished_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),'attempts',j.attempts,
  'run_id',j.run_id,'failure',case when j.state='FAILED'then jsonb_build_object('sqlstate',j.failure_sqlstate,'code',j.failure_code)end,
  'apply_enabled',false,'production_go',false)
$$;
-- The immutable part of the serve outcome: everything except the live
-- source_state, which the manifest supplies at read time.
create function cp7_analysis_jobs.original(r cp7_analysis_native.runs)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract_version','cp7.native-analysis-run.v1','run_id',r.id,'request_id',r.request_id,
  'analysis',r.result,'product_labels',coalesce((select jsonb_agg(jsonb_build_object('target_key',x->>'root_id'||':'||(x->>'size_id'),
   'sku',coalesce(x->'commercial'->0->>'sku',x->>'sku'),'product_name',x->>'product_name')order by x->>'root_id')
   from jsonb_array_elements(r.facts->'facts'->'products')x),'[]'::jsonb),
  'query',r.query,'financial_source',r.facts->'financial_source','apply_enabled',false,'production_go',false)
$$;
create function cp7_analysis_jobs.store(p_run uuid)returns cp7_analysis_jobs.documents
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare d cp7_analysis_jobs.documents%rowtype;r cp7_analysis_native.runs%rowtype;body text;n constant integer:=2000000;
begin
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-DOCUMENT:'||p_run::text,0));
 select *into d from cp7_analysis_jobs.documents where run_id=p_run;
 if found then return d;end if;
 select *into r from cp7_analysis_native.runs where id=p_run;
 if r.id is null then raise exception using errcode='42501',message='CP7_ANALYSIS_RUN_UNAVAILABLE';end if;
 body:=cp7_analysis_jobs.original(r)::text;
 insert into cp7_analysis_jobs.documents(run_id,utf8_bytes,characters,sha256,segment_count,segment_characters)
 values(p_run,octet_length(body),length(body),encode(pg_catalog.sha256(convert_to(body,'UTF8')),'hex'),(length(body)+n-1)/n,n)
 returning *into d;
 insert into cp7_analysis_jobs.segments(run_id,idx,body,utf8_bytes,sha256)
 select p_run,s.i,s.part,octet_length(s.part),encode(pg_catalog.sha256(convert_to(s.part,'UTF8')),'hex')
 from(select g.i,substr(body,g.i*n+1,n)part from generate_series(0,d.segment_count-1)g(i))s;
 return d;
end $$;
create function cp7_analysis_jobs.request(p_query jsonb,p_request uuid,p_finance text)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;j cp7_analysis_jobs.jobs%rowtype;r cp7_analysis_native.runs%rowtype;now_at timestamptz:=clock_timestamp();
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if p_finance is null or p_finance not in('INCLUDED','DEFERRED')then raise exception 'CP7_ANALYSIS_FINANCE_MODE';end if;
 a:=cp7_schedule_native.access_now(false);q:=cp7_planning.history_query(p_query);
 if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-JOB:'||(a->>'actor')||':'||p_request::text,0));
 select *into j from cp7_analysis_jobs.jobs where actor=(a->>'actor')::uuid and request_id=p_request;
 if found and(j.query<>q or j.finance<>p_finance)then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
 -- An ordinary capture may already own this UUID; its Original is the result
 -- only for the same query and the same finance mode.
 select *into r from cp7_analysis_native.runs where actor=(a->>'actor')::uuid and request_id=p_request;
 if r.id is not null and(r.query<>q or cp7_analysis_native.finance_mode(r.facts)<>p_finance)then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
 if j.actor is null then
  insert into cp7_analysis_jobs.jobs(actor,request_id,query,finance,requested_at,started_at,attempts,state,finished_at,run_id)
  values((a->>'actor')::uuid,p_request,q,p_finance,now_at,now_at,1,case when r.id is null then 'WAITING'else 'DONE'end,
   case when r.id is not null then now_at end,r.id)returning *into j;
 elsif j.state<>'DONE'then
  if r.id is not null then
   update cp7_analysis_jobs.jobs set state='DONE',run_id=r.id,finished_at=now_at,failure_sqlstate=null,failure_code=null
   where actor=j.actor and request_id=j.request_id returning *into j;
  elsif not cp7_analysis_jobs.worker_active(j.actor,j.request_id)then
   -- Waiting, stopped or failed and no worker holds it: start again. Nothing
   -- of an earlier attempt was committed except its state.
   update cp7_analysis_jobs.jobs set state='WAITING',started_at=now_at,attempts=attempts+1,finished_at=null,failure_sqlstate=null,failure_code=null
   where actor=j.actor and request_id=j.request_id returning *into j;
  end if;
 end if;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return cp7_analysis_jobs.status(j);
end $$;
create function cp7_analysis_jobs.run(p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j cp7_analysis_jobs.jobs%rowtype;r cp7_analysis_native.runs%rowtype;run_id uuid:=gen_random_uuid();
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;
 -- The same lock as the ordinary capture: one computation per actor/UUID.
 perform pg_advisory_xact_lock(cp7_analysis_jobs.compute_key((a->>'actor')::uuid,p_request));
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 select *into j from cp7_analysis_jobs.jobs where actor=(a->>'actor')::uuid and request_id=p_request;
 if not found then raise exception 'CP7_ANALYSIS_JOB_UNAVAILABLE';end if;
 if j.state<>'WAITING'then return cp7_analysis_jobs.status(j);end if;
 begin
  select *into r from cp7_analysis_native.runs where actor=j.actor and request_id=p_request;
  if r.id is null then
   with source as materialized(select cp7_analysis_native.source_for(j.query,j.finance)c),
    calculated as materialized(select c,cp7_analysis_native.build(c,j.query,run_id,a)result from source)
   insert into cp7_analysis_native.runs(id,actor,request_id,query,captured_at,access_at_capture,facts,result,dependency_hash)
   select run_id,j.actor,p_request,j.query,(c->>'captured_at')::timestamptz,a,c,result,cp7_analysis_native.fingerprint(c)from calculated
   returning *into r;
  elsif r.query<>j.query or cp7_analysis_native.finance_mode(r.facts)<>j.finance then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';
  end if;
  perform cp7_analysis_jobs.store(r.id);
  if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
  update cp7_analysis_jobs.jobs set state='DONE',run_id=r.id,finished_at=clock_timestamp()
  where actor=j.actor and request_id=j.request_id returning *into j;
 exception
  -- The existing statement limit (or a cancelled connection) stopped it.
  when query_canceled then
   update cp7_analysis_jobs.jobs set state='FAILED',finished_at=clock_timestamp(),failure_sqlstate=SQLSTATE,failure_code='CP7_ANALYSIS_JOB_STOPPED'
   where actor=j.actor and request_id=j.request_id returning *into j;
  when others then
   update cp7_analysis_jobs.jobs set state='FAILED',finished_at=clock_timestamp(),failure_sqlstate=SQLSTATE,
    failure_code=case when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM else 'CP7_ANALYSIS_JOB_ERROR'end
   where actor=j.actor and request_id=j.request_id returning *into j;
 end;
 return cp7_analysis_jobs.status(j);
end $$;
create function cp7_analysis_jobs.get(p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j cp7_analysis_jobs.jobs%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 select *into j from cp7_analysis_jobs.jobs where actor=(a->>'actor')::uuid and request_id=p_request;
 if not found then raise exception 'CP7_ANALYSIS_JOB_UNAVAILABLE';end if;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return cp7_analysis_jobs.status(j);
end $$;
-- Same refusals as serve: actor-bound run, protected finance still visible.
create function cp7_analysis_jobs.manifest(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_analysis_native.runs%rowtype;c jsonb;d cp7_analysis_jobs.documents%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);select *into r from cp7_analysis_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_ANALYSIS_RUN_UNAVAILABLE';end if;
 c:=cp7_analysis_native.source_for(r.query,cp7_analysis_native.finance_mode(r.facts));
 if r.facts->'financial_source' is not null and r.facts->'financial_source'<>'null'::jsonb and coalesce(c->'financial_source','null')='null'::jsonb then
  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_DENIED';
 end if;
 if coalesce(r.facts->'financial_source'->'report'->'close_preflight','null')<>'null'::jsonb
  and coalesce(c->'financial_source'->'report'->'close_preflight','null')='null'::jsonb then
  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_DENIED';
 end if;
 d:=cp7_analysis_jobs.store(r.id);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-analysis-manifest.v1','run_id',r.id,'request_id',r.request_id,
  'source_state',case when cp7_analysis_native.fingerprint(c)=r.dependency_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end,
  'access_epoch',encode(pg_catalog.sha256(convert_to(a::text,'UTF8')),'hex'),
  'document',jsonb_build_object('utf8_bytes',d.utf8_bytes,'characters',d.characters,'sha256',d.sha256,
   'segment_count',d.segment_count,'segment_characters',d.segment_characters),
  'apply_enabled',false,'production_go',false);
end $$;
create function cp7_analysis_jobs.segment(p_run uuid,p_index integer,p_access text)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;d cp7_analysis_jobs.documents%rowtype;s cp7_analysis_jobs.segments%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_access is distinct from encode(pg_catalog.sha256(convert_to(a::text,'UTF8')),'hex')then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';
 end if;
 if not exists(select 1 from cp7_analysis_native.runs where id=p_run and actor=(a->>'actor')::uuid)then
  raise exception using errcode='42501',message='CP7_ANALYSIS_RUN_UNAVAILABLE';
 end if;
 select *into d from cp7_analysis_jobs.documents where run_id=p_run;
 select *into s from cp7_analysis_jobs.segments where run_id=p_run and idx=p_index;
 if s.run_id is null then raise exception 'CP7_ANALYSIS_SEGMENT_UNAVAILABLE';end if;
 return jsonb_build_object('contract_version','cp7.native-analysis-segment.v1','run_id',p_run,'index',s.idx,
  'segment_count',d.segment_count,'document_sha256',d.sha256,'document_utf8_bytes',d.utf8_bytes,
  'utf8_bytes',s.utf8_bytes,'sha256',s.sha256,'body',s.body);
end $$;
alter function cp7_analysis_jobs.compute_key(uuid,uuid)owner to cp7_capture;
alter function cp7_analysis_jobs.worker_active(uuid,uuid)owner to cp7_capture;
alter function cp7_analysis_jobs.status(cp7_analysis_jobs.jobs)owner to cp7_capture;
alter function cp7_analysis_jobs.original(cp7_analysis_native.runs)owner to cp7_capture;
alter function cp7_analysis_jobs.store(uuid)owner to cp7_capture;
alter function cp7_analysis_jobs.request(jsonb,uuid,text)owner to cp7_capture;
alter function cp7_analysis_jobs.run(uuid)owner to cp7_capture;
alter function cp7_analysis_jobs.get(uuid)owner to cp7_capture;
alter function cp7_analysis_jobs.manifest(uuid)owner to cp7_capture;
alter function cp7_analysis_jobs.segment(uuid,integer,text)owner to cp7_capture;
revoke all on all functions in schema cp7_analysis_jobs from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
create function public.erp_cp7_request_analysis_job_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_jobs.request(p_query,p_request,'INCLUDED')$$;
create function public.erp_cp7_request_operational_analysis_job_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_jobs.request(p_query,p_request,'DEFERRED')$$;
create function public.erp_cp7_run_analysis_job_v1(p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_jobs.run(p_request)$$;
create function public.erp_cp7_get_analysis_job_v1(p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_jobs.get(p_request)$$;
create function public.erp_cp7_read_analysis_manifest_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_jobs.manifest(p_run)$$;
create function public.erp_cp7_read_analysis_segment_v1(p_run uuid,p_index integer,p_access text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_jobs.segment(p_run,p_index,p_access)$$;
alter function public.erp_cp7_request_analysis_job_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_request_operational_analysis_job_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_run_analysis_job_v1(uuid)owner to cp7_capture;
alter function public.erp_cp7_get_analysis_job_v1(uuid)owner to cp7_capture;
alter function public.erp_cp7_read_analysis_manifest_v1(uuid)owner to cp7_capture;
alter function public.erp_cp7_read_analysis_segment_v1(uuid,integer,text)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_request_analysis_job_v1(jsonb,uuid),public.erp_cp7_request_operational_analysis_job_v1(jsonb,uuid),public.erp_cp7_run_analysis_job_v1(uuid),
 public.erp_cp7_get_analysis_job_v1(uuid),public.erp_cp7_read_analysis_manifest_v1(uuid),
 public.erp_cp7_read_analysis_segment_v1(uuid,integer,text)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_request_analysis_job_v1(jsonb,uuid),public.erp_cp7_request_operational_analysis_job_v1(jsonb,uuid),public.erp_cp7_run_analysis_job_v1(uuid),
 public.erp_cp7_get_analysis_job_v1(uuid),public.erp_cp7_read_analysis_manifest_v1(uuid),
 public.erp_cp7_read_analysis_segment_v1(uuid,integer,text)to authenticated;
