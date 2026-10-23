-- OW13a: private initial capture, once per current Owner/Admin, no business writes.
create schema cp7_initial_analysis authorization cp7_capture;
revoke all on schema cp7_initial_analysis from public,anon,authenticated,service_role;
grant usage on schema cp7_initial_analysis to cp7_alert;

create table cp7_initial_analysis.intents(
 actor uuid primary key,request_id uuid not null unique,job_id uuid not null unique references cp7_analysis_stage.jobs(id),
 query jsonb not null,semantic_hash text not null check(semantic_hash~'^[0-9a-f]{64}$'),
 recorded_at timestamptz not null default clock_timestamp()
);
alter table cp7_initial_analysis.intents owner to cp7_capture;
alter table cp7_initial_analysis.intents enable row level security;
create policy initial_no_access on cp7_initial_analysis.intents for all to public using(false)with check(false);
revoke all on cp7_initial_analysis.intents from public,anon,authenticated,service_role,cp7_alert;
create trigger initial_intent_immutable before update or delete on cp7_initial_analysis.intents
 for each row execute function cp7_private.immutable_run();

create function cp7_initial_analysis.readiness(c jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare total integer;active integer;eligible integer;reasons jsonb:='[]';candidates jsonb;
begin
 if jsonb_typeof(c->'facts'->'products')is distinct from'array'
  or jsonb_typeof(c->'profiles')is distinct from'array'then raise exception 'CP7_INITIAL_SOURCE_SHAPE';end if;
 with products as(select p from jsonb_array_elements(c->'facts'->'products')p),
 rows as(select p,(select count(*)from jsonb_array_elements(c->'profiles')x where x->>'root_id'=p->>'root_id')profile_count,
  (select x from jsonb_array_elements(c->'profiles')x where x->>'root_id'=p->>'root_id'limit 1)profile from products),
 checked as(select p,profile_count=1 and profile->>'quality'='SELECTED_ASSUMPTION'
  and profile->>'product_version_id'=p->>'id'and profile->>'size_id'=p->>'size_id'
  and profile->'config'->>'lead_days'is not null and profile->'config'->>'review_days'is not null
  and(profile->'config'->>'buffer_days'is not null or profile->'config'->>'buffer_mode'='STATISTICAL')ready from rows)
 select count(*),count(*)filter(where p->'is_active'='true'::jsonb),
  count(*)filter(where p->'is_active'='true'::jsonb and ready),
  coalesce((select jsonb_agg(jsonb_build_object('root_id',x.p->>'root_id','product_id',x.p->>'id','size_id',x.p->>'size_id',
    'sku',x.p->>'sku','product_name',x.p->>'product_name','profile_ready',coalesce(x.ready,false))order by x.p->>'sku',x.p->>'id')
    from(select*from checked where p->'is_active'='true'::jsonb order by ready nulls first,p->>'sku',p->>'id'limit 20)x),'[]')
 into total,active,eligible,candidates from checked;
 if c->>'status'is distinct from'COMPLETE'then reasons:=reasons||'"SOURCE_INCOMPLETE"'::jsonb;end if;
 if active=0 then reasons:=reasons||'"NO_ACTIVE_PRODUCTS"'::jsonb;
 elsif eligible=0 then reasons:=reasons||'"PLANNING_PROFILE_INCOMPLETE"'::jsonb;end if;
 return jsonb_build_object('ready',jsonb_array_length(reasons)=0,'reasons',reasons,'products_total',total,
  'active_products',active,'eligible_targets',eligible,'candidates',candidates,'candidate_limit',20);
end $$;

create function cp7_initial_analysis.semantic_hash(c jsonb,q jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 -- No capture clock or moving capacity frontier: an initial snapshot is not
 -- requested again merely because another minute passed.
 select encode(extensions.digest(convert_to(jsonb_build_object('contract','cp7.initial-analysis.v1','query',q,
  'native',cp7_supply_native.fingerprint(c),'schedule',c->'schedule','matching_products',c->'matching_products',
  'material_source',(c->'material_source')-'captured_at','fabric_source',(c->'fabric_source')-'captured_at',
  'engine',c->'analysis_engine_signature')::text,'UTF8'),'sha256'),'hex')
$$;

create function cp7_initial_analysis.current(p_ensure boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;c jsonb;snap pg_snapshot;b jsonb:=cp7_analysis_stage.bounds();q jsonb;cfg jsonb;hi date;days integer;
 ready jsonb;fingerprint text;old cp7_initial_analysis.intents%rowtype;job jsonb;jid uuid;req uuid;state text;busy boolean:=false;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')then raise exception using errcode='42501',message='CP7_INITIAL_OWNER_OR_ADMIN_REQUIRED';end if;
 if p_ensure is null then raise exception 'CP7_INITIAL_MODE';end if;
 if p_ensure then busy:=not pg_try_advisory_xact_lock(hashtextextended('CP7:INITIAL:ANALYSIS',0));end if;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_INITIAL_ACCESS_CHANGED';end if;
 cfg:=cp7_stock_formula.current_settings();days:=(cfg->>'window_days')::integer;
 if days is null or days not between 14 and 365 then raise exception 'CP7_INITIAL_WINDOW';end if;
 hi:=(clock_timestamp()at time zone'Asia/Jakarta')::date-1;
 q:=cp7_planning.history_query(jsonb_build_object('from_date',(hi-days+1)::text,'through_date',hi::text,'group_mode','AS_SOLD'));
 -- Stable source and its MVCC mark are read in one statement, just as in the
 -- existing request path. No second capture can replace the readiness input.
 select cp7_analysis_native.source_within((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
  ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED'),
  case when pg_current_xact_id_if_assigned()is null then pg_current_snapshot()end into c,snap;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_INITIAL_ACCESS_CHANGED';end if;
 ready:=cp7_initial_analysis.readiness(c);fingerprint:=cp7_initial_analysis.semantic_hash(c,q);
 select*into old from cp7_initial_analysis.intents x where x.actor=(a->>'actor')::uuid;
 if old.actor is not null then
  if not exists(select 1 from cp7_analysis_stage.jobs j where j.id=old.job_id and j.actor=old.actor
   and j.request_id=old.request_id and j.query=old.query)then raise exception 'CP7_INITIAL_JOB_BINDING';end if;
  job:=cp7_analysis_stage.status(old.job_id);
  state:=case when job->'retention'->>'state'='EXPIRED'then'EXPIRED'else job->>'state'end;
 elsif ready->'ready'='false'::jsonb then state:='NOT_READY';
 elsif busy then state:='BUSY';
 elsif not p_ensure then state:='READY';
 else
  -- Reuse an already captured staged analysis of this same actor, period,
  -- access and semantic source, including a manual request. No second job.
  select j.id,j.request_id into jid,req from cp7_analysis_stage.jobs j
   where j.actor=(a->>'actor')::uuid and j.query=q and j.access_at_capture=a
    and coalesce(j.reference->>'financial_capture','DEFERRED')='DEFERRED'
    and coalesce(j.reference->>'finance_sidecar_mode','DEFERRED')='DEFERRED'
    and cp7_analysis_stage.retention(j.state,j.updated_at)->>'state'<>'EXPIRED'
    and exists(select 1 from cp7_analysis_stage.capture_marks m where m.job_id=j.id)
    and cp7_initial_analysis.semantic_hash(j.reference,j.query)=fingerprint
   order by j.created_at desc,j.id desc limit 1;
  if jid is null then
   if exists(select 1 from cp7_analysis_stage.jobs j where j.actor=(a->>'actor')::uuid and j.state='RUNNING')then state:='BUSY';
   else
    if jsonb_array_length(c->'facts'->'products')>(b->>'job_targets')::integer then raise exception 'CP7_ANALYSIS_STAGED_TARGET_LIMIT';end if;
    req:=gen_random_uuid();
    if exists(select 1 from cp7_analysis_stage.jobs j where j.actor=(a->>'actor')::uuid and j.request_id=req)
     or exists(select 1 from cp7_analysis_native.runs r where r.actor=(a->>'actor')::uuid and r.request_id=req)
     or exists(select 1 from cp7_analysis_jobs.jobs j where j.actor=(a->>'actor')::uuid and j.request_id=req)then raise exception 'CP7_INITIAL_UUID_COLLISION';end if;
    jid:=cp7_analysis_stage.create_job((a->>'actor')::uuid,req,q,a,c);
    insert into cp7_analysis_stage.capture_marks(job_id,source_snapshot)values(jid,snap);
   end if;
  end if;
  if jid is not null then
   insert into cp7_initial_analysis.intents(actor,request_id,job_id,query,semantic_hash)
    values((a->>'actor')::uuid,req,jid,q,fingerprint)returning*into old;
   job:=cp7_analysis_stage.status(jid);state:=job->>'state';
  end if;
 end if;
 if state is null or state not in('NOT_READY','READY','BUSY','RUNNING','DONE','FAILED','EXPIRED')then raise exception 'CP7_INITIAL_JOB_STATE';end if;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_INITIAL_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.initial-analysis.v1','actor',a->>'actor','checked_at',cp7_planning.utc(clock_timestamp()),
  'automatic_scope','INITIAL_ONCE','state',state,'readiness',ready,'query',q,'semantic_hash',fingerprint,
  'job_query',old.query,'job_semantic_hash',old.semantic_hash,'source_changed',case when old.actor is null then false else old.semantic_hash<>fingerprint end,
  'job',job,'apply_enabled',false,'production_go',false);
end $$;

create function cp7_initial_analysis.tick()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare candidate record;prior jsonb;a jsonb;result jsonb;valid boolean;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if not exists(select 1 from pg_catalog.pg_settings where name='statement_timeout'and setting::integer between 1 and 8000)then
  raise exception 'CP7_INITIAL_STATEMENT_LIMIT_REQUIRED';end if;
 prior:=jsonb_build_object('claims',current_setting('request.jwt.claims',true),'sub',current_setting('request.jwt.claim.sub',true),
  'claim',current_setting('request.jwt.claim',true));
 begin
  -- No invented identity: only actors who actually reviewed planning profiles.
  for candidate in select actor,max(recorded_at)at from cp7_profile.profiles group by actor order by max(recorded_at)desc,actor loop
   perform set_config('request.jwt.claims',jsonb_build_object('sub',candidate.actor,'role','authenticated')::text,true),
    set_config('request.jwt.claim.sub','',true),set_config('request.jwt.claim','',true);
   valid:=true;
   begin
    a:=cp7_schedule_native.access_now(false);
    valid:=a->'profile'->>'role_code'in('OWNER','ADMIN');
   exception when insufficient_privilege then valid:=false;
   end;
   if valid is true then
    -- The initial intent is permanent. Once it exists, a cron tick needs no
    -- full source capture; manual/focus STATUS still checks present sources.
    select jsonb_build_object('outcome','INITIAL_ALREADY_REQUESTED','ran',false,'state',j.state,'request_id',i.request_id)
     into result from cp7_initial_analysis.intents i join cp7_analysis_stage.jobs j on j.id=i.job_id
     where i.actor=candidate.actor and j.actor=i.actor and j.request_id=i.request_id and j.query=i.query;
    if result is null then result:=cp7_initial_analysis.current(true);end if;
    if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_INITIAL_ACCESS_CHANGED';end if;
    exit;
   end if;
  end loop;
 exception when query_canceled then
  perform set_config('request.jwt.claims',coalesce(prior->>'claims',''),true),set_config('request.jwt.claim.sub',coalesce(prior->>'sub',''),true),set_config('request.jwt.claim',coalesce(prior->>'claim',''),true);raise;
 when others then
  perform set_config('request.jwt.claims',coalesce(prior->>'claims',''),true),set_config('request.jwt.claim.sub',coalesce(prior->>'sub',''),true),set_config('request.jwt.claim',coalesce(prior->>'claim',''),true);raise;
 end;
 perform set_config('request.jwt.claims',coalesce(prior->>'claims',''),true),set_config('request.jwt.claim.sub',coalesce(prior->>'sub',''),true),set_config('request.jwt.claim',coalesce(prior->>'claim',''),true);
 return coalesce(result,jsonb_build_object('outcome','NO_CURRENT_PLANNING_ACTOR','ran',false));
end $$;

alter function cp7_initial_analysis.readiness(jsonb)owner to cp7_capture;
alter function cp7_initial_analysis.semantic_hash(jsonb,jsonb)owner to cp7_capture;
alter function cp7_initial_analysis.current(boolean)owner to cp7_capture;
alter function cp7_initial_analysis.tick()owner to cp7_capture;
revoke all on all functions in schema cp7_initial_analysis from public,anon,authenticated,service_role,cp7_alert;
grant execute on function cp7_initial_analysis.tick()to cp7_alert;
