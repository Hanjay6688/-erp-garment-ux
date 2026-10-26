create schema cp7_frozen_choice_preparation authorization cp7_capture;
revoke all on schema cp7_frozen_choice_preparation from public,anon,authenticated,service_role;
create table cp7_frozen_choice_preparation.work(
 job_id uuid primary key, actor uuid not null, source_request uuid not null,
 source_hash text not null, capsule_hash text not null, producer_hash text not null,
 query jsonb not null, captured_at timestamptz not null,
 state text not null check(state in('QUEUED','READY','FAILED','EXPIRED')),
 attempts integer not null default 0 check(attempts between 0 and 3),
 payload jsonb, failure_code text, failure_sqlstate text,
 created_at timestamptz not null default clock_timestamp(),
 updated_at timestamptz not null default clock_timestamp(),
 unique(actor,source_request),
 check((state='READY')=(payload is not null)),
 check((state='FAILED')=(failure_code is not null))
);
alter table cp7_frozen_choice_preparation.work owner to cp7_capture;
alter table cp7_frozen_choice_preparation.work enable row level security;
revoke all on table cp7_frozen_choice_preparation.work from public,anon,authenticated,service_role;

create function cp7_frozen_choice_preparation.guard_work()returns trigger
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if TG_OP='DELETE'then raise exception 'CP7_CHOICE_PREPARATION_IMMUTABLE';end if;
 if(to_jsonb(new)-array['state','attempts','payload','failure_code','failure_sqlstate','updated_at'])
  is distinct from(to_jsonb(old)-array['state','attempts','payload','failure_code','failure_sqlstate','updated_at'])
  or new.attempts<old.attempts or new.attempts>old.attempts+1 or new.updated_at<old.updated_at
  or old.state='EXPIRED'then raise exception 'CP7_CHOICE_PREPARATION_IMMUTABLE';end if;
 if old.state<>'QUEUED'and new.state<>'EXPIRED'then raise exception 'CP7_CHOICE_PREPARATION_IMMUTABLE';end if;
 if new.state='EXPIRED'and exists(select 1 from cp7_analysis_stage.jobs j where j.id=old.job_id
  and cp7_analysis_stage.retention(j.state,j.updated_at)->>'state'<>'EXPIRED')then
  raise exception 'CP7_CHOICE_PREPARATION_NOT_EXPIRED';end if;
 return new;
end $$;
create trigger immutable_preparation_work before update or delete on cp7_frozen_choice_preparation.work
 for each row execute function cp7_frozen_choice_preparation.guard_work();

create function cp7_frozen_choice_preparation.source(p_source_request uuid,p_access text)returns cp7_analysis_stage.jobs
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j cp7_analysis_stage.jobs;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_access is distinct from encode(pg_catalog.sha256(convert_to(a::text,'UTF8')),'hex')then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 select *into j from cp7_analysis_stage.jobs where id=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_source_request);
 if j.id is null or j.state is distinct from'DONE'or j.actor is distinct from(a->>'actor')::uuid then
  raise exception using errcode='42501',message='CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE';end if;
 perform cp7_analysis_stage.require_kept(j.id);
 if j.reference->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v2'
  or j.reference->>'bounded_reference_contract'is distinct from'cp7.bounded-analysis-reference.v2'
  or j.query is distinct from j.reference->'bounded_query'
  or j.captured_at is distinct from(j.reference->>'captured_at')::timestamptz
  or cp7_frozen_analysis_units_v2.coverage(j.id)is distinct from'COMPLETE'then
  raise exception 'CP7_FROZEN_READER_REFERENCE_REQUIRED';end if;
 if cp7_frozen_analysis_units_v2.producer_hash()is distinct from j.reference->>'bounded_producer_hash'then
  raise exception using errcode='40001',message='CP7_PRODUCT_ANALOG_PRODUCER_CHANGED';end if;
 return j;
end $$;

-- Same lock observation as existing cp7_analysis_jobs.worker_active: status
-- reads do not take the worker lock or turn another reader into RUNNING.
create function cp7_frozen_choice_preparation.worker_active(p_job uuid)returns boolean
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select exists(select 1 from pg_catalog.pg_locks l
  where l.locktype='advisory'and l.granted and l.objsubid=1
   and l.database=(select d.oid from pg_catalog.pg_database d where d.datname=pg_catalog.current_database())
   and l.classid=((hashtextextended('CP7:FROZEN_CHOICE_PREP:'||p_job::text,0)>>32)&4294967295)::oid
   and l.objid=(hashtextextended('CP7:FROZEN_CHOICE_PREP:'||p_job::text,0)&4294967295)::oid)
$$;

create function cp7_frozen_choice_preparation.status(j cp7_analysis_stage.jobs,p_busy boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare w cp7_frozen_choice_preparation.work;
begin
 select *into w from cp7_frozen_choice_preparation.work where job_id=j.id;
 if w.job_id is null then
  if p_busy then raise exception 'CP7_CHOICE_PREPARATION_START_IN_FLIGHT';end if;
  raise exception 'CP7_CHOICE_PREPARATION_NOT_STARTED';end if;
 if w.actor is distinct from j.actor or w.source_request is distinct from j.request_id
  or w.source_hash is distinct from j.source_hash or w.query is distinct from j.query
  or w.captured_at is distinct from j.captured_at
  or w.capsule_hash is distinct from j.reference->>'bounded_capsule_hash'
  or w.producer_hash is distinct from j.reference->>'bounded_producer_hash'then
  raise exception 'CP7_CHOICE_PREPARATION_BINDING';end if;
 return jsonb_build_object('contract_version','cp7.frozen-choice-preparation.v1',
  'source_request',w.source_request,'run_id',j.run_id,
  'reference',jsonb_build_object('captured_at',j.captured_at,'source_hash',j.source_hash),
  'state',case when w.state='QUEUED'and p_busy then'RUNNING'else w.state end,
  'stage','FROZEN_INPUTS','units_done',case when w.state='READY'then 1 else 0 end,'unit_count',1,
  'created_at',w.created_at,'last_progress_at',w.updated_at,'unit_attempts',w.attempts,
  'failure_code',w.failure_code,'failure_sqlstate',w.failure_sqlstate,
  'worker_active',p_busy,'choice_saved',false,'production_go',false);
end $$;

create function cp7_frozen_choice_preparation.request(p_source_request uuid,p_access text)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare j cp7_analysis_stage.jobs;busy boolean;
begin
 j:=cp7_frozen_choice_preparation.source(p_source_request,p_access);
 busy:=not pg_try_advisory_xact_lock(hashtextextended('CP7:FROZEN_CHOICE_PREP_ENQUEUE:'||j.id::text,0));
 if not busy then
  insert into cp7_frozen_choice_preparation.work(job_id,actor,source_request,source_hash,capsule_hash,producer_hash,query,captured_at,state)
   values(j.id,j.actor,j.request_id,j.source_hash,j.reference->>'bounded_capsule_hash',j.reference->>'bounded_producer_hash',j.query,j.captured_at,'QUEUED')
   on conflict(job_id)do nothing;
 end if;
 j:=cp7_frozen_choice_preparation.source(p_source_request,p_access);
 if busy and not exists(select 1 from cp7_frozen_choice_preparation.work where job_id=j.id)then
  raise exception 'CP7_CHOICE_PREPARATION_START_IN_FLIGHT';end if;
 return cp7_frozen_choice_preparation.status(j,cp7_frozen_choice_preparation.worker_active(j.id));
end $$;

create function cp7_frozen_choice_preparation.get(p_source_request uuid,p_access text)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare j cp7_analysis_stage.jobs;
begin
 j:=cp7_frozen_choice_preparation.source(p_source_request,p_access);
 return cp7_frozen_choice_preparation.status(j,cp7_frozen_choice_preparation.worker_active(j.id));
end $$;

create function cp7_frozen_choice_preparation.step(p_source_request uuid,p_access text)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare j cp7_analysis_stage.jobs;w cp7_frozen_choice_preparation.work;
 cached jsonb;inputs jsonb;limit_ms integer;problem text;code text;timed boolean;
begin
 select setting::integer into limit_ms from pg_settings where name='statement_timeout';
 if limit_ms is null or limit_ms not between 1 and 8000 then raise exception 'CP7_RUNNER_STATEMENT_LIMIT_REQUIRED';end if;
 j:=cp7_frozen_choice_preparation.source(p_source_request,p_access);
 if not pg_try_advisory_xact_lock(hashtextextended('CP7:FROZEN_CHOICE_PREP:'||j.id::text,0))then
  return cp7_frozen_choice_preparation.status(j,true);end if;
 j:=cp7_frozen_choice_preparation.source(p_source_request,p_access);
 perform cp7_frozen_choice_preparation.status(j,false);
 select *into w from cp7_frozen_choice_preparation.work where job_id=j.id;
 if w.state<>'QUEUED'then return cp7_frozen_choice_preparation.status(j,false);end if;
 begin
  select payload into cached from cp7_analysis_stage.target_rows
   where job_id=j.id and kind='FROZEN_INPUTS_V2'and ord=1 and key=j.reference->>'bounded_capsule_hash';
  if cached is null then
   inputs:=cp7_frozen_analysis_v2.prepare(j.reference,j.query,(cp7_analysis_stage.bounds()->>'job_targets')::integer);
   cached:=cp7_frozen_analysis_units_v2.pack(j,inputs);
   inputs:=cp7_frozen_analysis_units_v2.unpack(j,cached);
  else
   inputs:=cp7_frozen_analysis_units_v2.unpack(j,cached);
  end if;
  -- The same source/actor/producer/retention is checked after the work. This
  -- does not recapture live stock or relabel any source as current for SAVE.
  if cp7_frozen_choice_preparation.source(p_source_request,p_access)is distinct from j then
   raise exception 'CP7_CHOICE_PREPARATION_SOURCE_CHANGED';end if;
  update cp7_frozen_choice_preparation.work set state='READY',payload=cached,updated_at=clock_timestamp()where job_id=j.id;
 exception when query_canceled or others then
  problem:=SQLERRM;code:=SQLSTATE;timed:=code='57014';
  update cp7_frozen_choice_preparation.work set attempts=attempts+1,
   state=case when timed and attempts<2 then'QUEUED'else'FAILED'end,
   failure_code=case when timed and attempts<2 then null when timed then'CP7_CHOICE_PREPARATION_TIME_LIMIT'
    when problem~'^CP7_[A-Z0-9_]+$'then problem else'CP7_CHOICE_PREPARATION_FAILED'end,
   failure_sqlstate=case when timed and attempts<2 then null else code end,
   payload=null,updated_at=clock_timestamp()where job_id=j.id;
 end;
 -- A current access loss is still an access refusal, never a readable failure
 -- payload containing protected analysis information.
 j:=cp7_frozen_choice_preparation.source(p_source_request,p_access);
 return cp7_frozen_choice_preparation.status(j,false);
end $$;

-- Only existing validated inputs may be consumed inside the SAVE transaction.
-- The old public reader is unchanged; this helper never calls prepare.
create function cp7_frozen_choice_preparation.reference(j cp7_analysis_stage.jobs)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare cached jsonb;inputs jsonb;c jsonb:=j.reference;w cp7_frozen_choice_preparation.work;
begin
 if j.id is null or j.state is distinct from'DONE'
  or c->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v2'
  or c->>'bounded_reference_contract'is distinct from'cp7.bounded-analysis-reference.v2'
  or cp7_frozen_analysis_units_v2.coverage(j.id)is distinct from'COMPLETE'then
  raise exception 'CP7_FROZEN_READER_REFERENCE_REQUIRED';end if;
 perform cp7_analysis_stage.require_kept(j.id);
 if cp7_frozen_analysis_units_v2.producer_hash()is distinct from c->>'bounded_producer_hash'then
  raise exception using errcode='40001',message='CP7_PRODUCT_ANALOG_PRODUCER_CHANGED';end if;
 select x.payload into cached from cp7_analysis_stage.target_rows x
  where x.job_id=j.id and x.kind='FROZEN_INPUTS_V2'and x.ord=1 and x.key=c->>'bounded_capsule_hash';
 if cached is null then
  select *into w from cp7_frozen_choice_preparation.work where job_id=j.id;
  if w.state is distinct from'READY'then raise exception 'CP7_CHOICE_PREPARATION_REQUIRED';end if;
  perform cp7_frozen_choice_preparation.status(j,false);
  cached:=w.payload;
 end if;
 inputs:=cp7_frozen_analysis_units_v2.unpack(j,cached);
 return c||jsonb_build_object('bounded_history_inputs',inputs,'bounded_input_coverage','COMPLETE');
end $$;

-- Private optional hook for the existing K4 runner. No scheduler is installed.
-- Each invocation is one original job and the same bounded step as the client.
create function cp7_frozen_choice_preparation.run_next()returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare w cp7_frozen_choice_preparation.work;a jsonb;s jsonb;prior jsonb;code text;problem text;limit_ms integer;timed boolean;
begin
 select setting::integer into limit_ms from pg_settings where name='statement_timeout';
 if limit_ms is null or limit_ms not between 1 and 8000 then raise exception 'CP7_RUNNER_STATEMENT_LIMIT_REQUIRED';end if;
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 select *into w from cp7_frozen_choice_preparation.work where state='QUEUED'order by updated_at,job_id limit 1 for update skip locked;
 if not found then return jsonb_build_object('ran',false,'outcome','IDLE');end if;
 prior:=jsonb_build_object('claims',current_setting('request.jwt.claims',true),'sub',current_setting('request.jwt.claim.sub',true),
  'claim',current_setting('request.jwt.claim',true));
 perform set_config('request.jwt.claims',jsonb_build_object('sub',w.actor,'role','authenticated')::text,true),
  set_config('request.jwt.claim.sub','',true),set_config('request.jwt.claim','',true);
 begin
  a:=cp7_schedule_native.access_now(false);
  s:=cp7_frozen_choice_preparation.step(w.source_request,encode(pg_catalog.sha256(convert_to(a::text,'UTF8')),'hex'));
 exception when query_canceled or others then
  -- OTHERS excludes57014. Also bound cancellations in access/source checks
  -- outside step's inner compiler block; never requeue these indefinitely.
  -- The failed subtransaction rolled back its changes. Count this one attempt
  -- on the already-selected row, then restore all caller claims below.
  code:=SQLSTATE;problem:=SQLERRM;timed:=code='57014';
  update cp7_frozen_choice_preparation.work set
   attempts=attempts+case when timed then 1 else 0 end,
   state=case when timed and attempts<2 then'QUEUED'else'FAILED'end,payload=null,
   failure_code=case when timed and attempts<2 then null when timed then'CP7_CHOICE_PREPARATION_TIME_LIMIT'
    when problem~'^CP7_[A-Z0-9_]+$'then problem else'CP7_CHOICE_PREPARATION_FAILED'end,
   failure_sqlstate=case when timed and attempts<2 then null else code end,
   updated_at=clock_timestamp()where job_id=w.job_id
   returning jsonb_build_object('state',state)into s;
 end;
 perform set_config('request.jwt.claims',coalesce(prior->>'claims',''),true),
  set_config('request.jwt.claim.sub',coalesce(prior->>'sub',''),true),set_config('request.jwt.claim',coalesce(prior->>'claim',''),true);
 return jsonb_build_object('ran',true,'job_id',w.job_id,'state',s->'state');
end $$;

-- Bounded cleanup of only this extension's expired payloads. Existing K2/K3,
-- retained pages/documents and immutable choice receipts are not rewritten.
create function cp7_frozen_choice_preparation.purge_expired(p_limit integer)returns integer
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare w cp7_frozen_choice_preparation.work;removed integer:=0;
begin
 if p_limit is null or p_limit not between 1 and 1000 then raise exception 'CP7_ANALYSIS_RETENTION_LIMIT';end if;
 for w in select x.*from cp7_frozen_choice_preparation.work x left join cp7_analysis_stage.jobs j on j.id=x.job_id
  where x.state<>'EXPIRED'and(j.id is null or cp7_analysis_stage.retention(j.state,j.updated_at)->>'state'='EXPIRED')
  order by x.updated_at,x.job_id limit p_limit for update of x skip locked loop
  if pg_try_advisory_xact_lock(hashtextextended('CP7:FROZEN_CHOICE_PREP:'||w.job_id::text,0))then
   update cp7_frozen_choice_preparation.work set state='EXPIRED',payload=null,
    failure_code=null,failure_sqlstate=null,updated_at=clock_timestamp()where job_id=w.job_id;
   removed:=removed+1;
  end if;
 end loop;
 return removed;
end $$;
