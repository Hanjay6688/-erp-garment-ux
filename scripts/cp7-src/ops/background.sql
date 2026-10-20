-- D17-14 / OW-02. Continue work already requested by an actor after the
-- browser closes. One existing unit per tick, under the same 8 s limit and
-- current access checks. No new schedule, public RPC, business write or send.
-- The oldest progress gets a turn; a locked family does not block another.
create schema cp7_background authorization cp7_capture;
revoke all on schema cp7_background from public,anon,authenticated,service_role;
grant usage,create on schema cp7_background to cp7_reminder;
-- Only unfinished work belongs in the runner's queue indexes. Completed
-- archives must not make every minute's scheduler scan grow without bound.
create index cp7_report_running on cp7_analysis_stage.report_jobs(updated_at,id)where state='RUNNING';
create index cp7_reminder_set_running on cp7_reminder_native.staged_condition_sets(updated_at,run_id)where state='RUNNING';
create index cp7_analysis_job_waiting on cp7_analysis_jobs.jobs(started_at,actor,request_id)where state='WAITING';

-- The scheduler sees only the age of pending reminder work. It does not
-- acquire permission to read the reminder tables or execute a claim/send.
create function cp7_background.reminder_pending_at()returns timestamptz
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select min(updated_at)from cp7_reminder_native.staged_condition_sets where state='RUNNING'
$$;
alter function cp7_background.reminder_pending_at()owner to cp7_reminder;

create function cp7_background.reminder_next()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare j cp7_reminder_native.staged_condition_sets%rowtype;s cp7_reminder_native.staged_condition_sets%rowtype;prior jsonb;
begin
 select *into j from cp7_reminder_native.staged_condition_sets x where x.state='RUNNING'
  order by x.updated_at,x.run_id limit 1 for update skip locked;
 if not found then return jsonb_build_object('ran',false,'outcome','IDLE');end if;
 prior:=jsonb_build_object('claims',current_setting('request.jwt.claims',true),'sub',current_setting('request.jwt.claim.sub',true),
  'claim',current_setting('request.jwt.claim',true));
 perform set_config('request.jwt.claims',jsonb_build_object('sub',j.actor,'role','authenticated')::text,true),
  set_config('request.jwt.claim.sub','',true),set_config('request.jwt.claim','',true);
 begin
  perform cp7_reminder_native.staged_set_step(j.run_id);
 exception
  when query_canceled then
   update cp7_reminder_native.staged_condition_sets set unit_attempts=unit_attempts+1,updated_at=clock_timestamp(),
    state=case when unit_attempts+1>=3 then 'FAILED'else state end,
    failure_unit=case when unit_attempts+1>=3 then units_done end,failure_sqlstate=case when unit_attempts+1>=3 then SQLSTATE end,
    failure_code=case when unit_attempts+1>=3 then 'CP7_REMINDER_V2_STAGE_STOPPED'end,failure_message=case when unit_attempts+1>=3 then SQLERRM end
    where run_id=j.run_id;
  when others then
   -- Includes revocation before or during the unit. The failed subtransaction
   -- discards its output before recording failure on the actor's own job.
   update cp7_reminder_native.staged_condition_sets set state='FAILED',updated_at=clock_timestamp(),failure_unit=units_done,
    failure_sqlstate=SQLSTATE,failure_code=case when SQLSTATE='42501'then 'CP7_REMINDER_ACCESS_CHANGED'
     when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM else 'CP7_REMINDER_V2_STAGE_ERROR'end,failure_message=SQLERRM where run_id=j.run_id;
 end;
 perform set_config('request.jwt.claims',coalesce(prior->>'claims',''),true),set_config('request.jwt.claim.sub',coalesce(prior->>'sub',''),true),
  set_config('request.jwt.claim',coalesce(prior->>'claim',''),true);
 select *into s from cp7_reminder_native.staged_condition_sets where run_id=j.run_id;
 return jsonb_build_object('ran',true,'family','REMINDER','outcome',case when s.state='DONE'then 'JOB_DONE'when s.state='FAILED'then 'JOB_FAILED'
  when s.units_done>j.units_done then 'UNIT_STORED'else 'UNIT_RETRY'end,'job_id',j.run_id,'unit',j.units_done,
  'units_done',s.units_done,'unit_count',s.unit_count,'state',s.state);
end $$;
alter function cp7_background.reminder_next()owner to cp7_reminder;

create function cp7_background.report_next()returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare j cp7_analysis_stage.report_jobs%rowtype;s cp7_analysis_stage.report_jobs%rowtype;prior jsonb;
begin
 select *into j from cp7_analysis_stage.report_jobs x where x.state='RUNNING'
  order by x.updated_at,x.id limit 1 for update skip locked;
 if not found then return jsonb_build_object('ran',false,'outcome','IDLE');end if;
 prior:=jsonb_build_object('claims',current_setting('request.jwt.claims',true),'sub',current_setting('request.jwt.claim.sub',true),
  'claim',current_setting('request.jwt.claim',true));
 perform set_config('request.jwt.claims',jsonb_build_object('sub',j.actor,'role','authenticated')::text,true),
  set_config('request.jwt.claim.sub','',true),set_config('request.jwt.claim','',true);
 begin
  perform cp7_analysis_stage.report_step(j.request_id);
 exception
  when query_canceled then
   update cp7_analysis_stage.report_jobs set unit_attempts=unit_attempts+1,updated_at=clock_timestamp(),
    state=case when unit_attempts+1>=3 then 'FAILED'else state end,
    failure_unit=case when unit_attempts+1>=3 then units_done end,failure_sqlstate=case when unit_attempts+1>=3 then SQLSTATE end,
    failure_code=case when unit_attempts+1>=3 then 'CP7_REPORT_V2_STAGE_STOPPED'end,failure_message=case when unit_attempts+1>=3 then SQLERRM end where id=j.id;
  when others then
   update cp7_analysis_stage.report_jobs set state='FAILED',updated_at=clock_timestamp(),failure_unit=units_done,failure_sqlstate=SQLSTATE,
    failure_code=case when SQLSTATE='42501'then 'CP7_REPORT_ACCESS_CHANGED'
     when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM else 'CP7_REPORT_V2_STAGE_ERROR'end,failure_message=SQLERRM where id=j.id;
 end;
 perform set_config('request.jwt.claims',coalesce(prior->>'claims',''),true),set_config('request.jwt.claim.sub',coalesce(prior->>'sub',''),true),
  set_config('request.jwt.claim',coalesce(prior->>'claim',''),true);
 select *into s from cp7_analysis_stage.report_jobs where id=j.id;
 return jsonb_build_object('ran',true,'family','REPORT','outcome',case when s.state='DONE'then 'JOB_DONE'when s.state='FAILED'then 'JOB_FAILED'
  when s.units_done>j.units_done then 'UNIT_STORED'else 'UNIT_RETRY'end,'job_id',j.id,'unit',j.units_done,
  'units_done',s.units_done,'unit_count',s.unit_count,'state',s.state);
end $$;
alter function cp7_background.report_next()owner to cp7_capture;

create function cp7_background.analysis_next()returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare j cp7_analysis_jobs.jobs%rowtype;s cp7_analysis_jobs.jobs%rowtype;prior jsonb;claimed boolean:=false;
begin
 -- Acquire the page's existing two advisory locks in its existing order,
 -- without waiting. A page and cron can never compute the same job twice.
 for j in select *from cp7_analysis_jobs.jobs x where x.state='WAITING'order by x.started_at,x.actor,x.request_id loop
  if not pg_try_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-REQUEST:'||j.actor::text||':'||j.request_id::text,0))then continue;end if;
  if not pg_try_advisory_xact_lock(cp7_analysis_jobs.compute_key(j.actor,j.request_id))then continue;end if;
  select *into j from cp7_analysis_jobs.jobs x where x.actor=j.actor and x.request_id=j.request_id and x.state='WAITING';
  if found then claimed:=true;exit;end if;
 end loop;
 if not claimed then return jsonb_build_object('ran',false,'outcome','IDLE');end if;
 prior:=jsonb_build_object('claims',current_setting('request.jwt.claims',true),'sub',current_setting('request.jwt.claim.sub',true),
  'claim',current_setting('request.jwt.claim',true));
 perform set_config('request.jwt.claims',jsonb_build_object('sub',j.actor,'role','authenticated')::text,true),
  set_config('request.jwt.claim.sub','',true),set_config('request.jwt.claim','',true);
 begin
  perform cp7_analysis_jobs.run(j.request_id);
 exception
  when query_canceled then
   update cp7_analysis_jobs.jobs set state='FAILED',finished_at=clock_timestamp(),failure_sqlstate=SQLSTATE,failure_code='CP7_ANALYSIS_JOB_STOPPED'
    where actor=j.actor and request_id=j.request_id;
  when others then
   update cp7_analysis_jobs.jobs set state='FAILED',finished_at=clock_timestamp(),failure_sqlstate=SQLSTATE,
    failure_code=case when SQLSTATE='42501'then 'CP7_ANALYSIS_ACCESS_CHANGED'
     when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM else 'CP7_ANALYSIS_JOB_ERROR'end where actor=j.actor and request_id=j.request_id;
 end;
 perform set_config('request.jwt.claims',coalesce(prior->>'claims',''),true),set_config('request.jwt.claim.sub',coalesce(prior->>'sub',''),true),
  set_config('request.jwt.claim',coalesce(prior->>'claim',''),true);
 select *into s from cp7_analysis_jobs.jobs where actor=j.actor and request_id=j.request_id;
 return jsonb_build_object('ran',true,'family','ANALYSIS','outcome',case when s.state='DONE'then 'JOB_DONE'else 'JOB_FAILED'end,
  'job_id',j.request_id,'unit',0,'units_done',case when s.state='DONE'then 1 else 0 end,'unit_count',1,'state',s.state);
end $$;
alter function cp7_background.analysis_next()owner to cp7_capture;

create function cp7_background.run_next()returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare limit_ms integer;f record;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 select setting::integer into limit_ms from pg_catalog.pg_settings where name='statement_timeout';
 if limit_ms is null or limit_ms not between 1 and 8000 then
  raise exception using errcode='55000',message='CP7_RUNNER_STATEMENT_LIMIT_REQUIRED',
   detail=jsonb_build_object('statement_timeout_ms',limit_ms,'required','statement_timeout 1..8000 ms')::text;
 end if;
 -- Same nonblocking heartbeat as K4; reports/reminders also keep it fresh.
 if pg_try_advisory_xact_lock(hashtextextended('CP7:K4_RUNNER_HEARTBEAT',0))then
  insert into cp7_analysis_stage.runner as heartbeat(id,last_tick_at,statement_timeout_ms)values(true,clock_timestamp(),limit_ms)
   on conflict(id)do update set last_tick_at=excluded.last_tick_at,statement_timeout_ms=excluded.statement_timeout_ms
   where heartbeat.last_tick_at<excluded.last_tick_at-interval'10 seconds'or heartbeat.statement_timeout_ms<>excluded.statement_timeout_ms;
 end if;
 for f in select *from(
  select 'STAGED'::text family,min(updated_at)pending_at from cp7_analysis_stage.jobs where state='RUNNING'
  union all select 'REPORT',min(updated_at)from cp7_analysis_stage.report_jobs where state='RUNNING'
  union all select 'ANALYSIS',min(started_at)from cp7_analysis_jobs.jobs where state='WAITING'
  union all select 'REMINDER',cp7_background.reminder_pending_at()
 )q where pending_at is not null order by pending_at,family loop
  r:=case f.family when 'STAGED'then cp7_analysis_stage.run_next()when 'REPORT'then cp7_background.report_next()
   when 'ANALYSIS'then cp7_background.analysis_next()else cp7_background.reminder_next()end;
  if coalesce((r->>'ran')::boolean,false)or r->>'outcome'='ACCESS_CHANGED_DURING_UNIT'then return r;end if;
 end loop;
 return jsonb_build_object('ran',false,'outcome','IDLE');
end $$;
alter function cp7_background.run_next()owner to cp7_capture;

revoke create on schema cp7_background from cp7_reminder;
revoke all on all functions in schema cp7_background from public,anon,authenticated,service_role;
grant execute on function cp7_background.reminder_pending_at(),cp7_background.reminder_next()to cp7_capture;
-- Signature, owner, security, privileges, schedule and statement limit stay
-- identical. Only the private dispatcher called by the existing tick changes.
create or replace function cp7_ops.analysis_tick()returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_background.run_next()||jsonb_build_object('tick','cp7-staged-runner','at',clock_timestamp())
$$;
