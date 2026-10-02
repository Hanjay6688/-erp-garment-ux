-- Explicit local contract rehearsal. This cannot configure a real recipient,
-- provider, scheduler or external transport, and never writes ERP business.
create table cp7_reminder_native.local_bindings(
 id uuid primary key default gen_random_uuid(),actor uuid not null,revision bigint not null check(revision>0),
 previous_id uuid references cp7_reminder_native.local_bindings(id),enabled boolean not null,label text not null,
 environment text not null check(environment='LOCAL_TEST_SINK'),rules jsonb not null,reason text not null,
 created_at timestamptz not null,unique(actor,revision));
create table cp7_reminder_native.local_claims(
 id uuid primary key default gen_random_uuid(),actor uuid not null,run_id uuid not null,
 binding_id uuid not null references cp7_reminder_native.local_bindings(id),condition_key text not null,rule_id text not null,
 episode_id uuid not null references cp7_reminder_native.rule_episodes(id),occurrence_key text not null,
 environment text not null check(environment='LOCAL_TEST_SINK'),source_hash text not null,policy_id uuid not null,
 fence uuid not null default gen_random_uuid(),status text not null check(status in('CLAIMED','LOCAL_SINK_CAPTURED','SUPPRESSED','UNKNOWN')),
 body text not null,body_sha256 text not null,reason text,created_at timestamptz not null,finished_at timestamptz,
 unique(actor,binding_id,environment,occurrence_key),check(status<>'LOCAL_SINK_CAPTURED'or finished_at is not null));
create table cp7_reminder_native.local_resolutions(
 id uuid primary key default gen_random_uuid(),claim_id uuid not null unique references cp7_reminder_native.local_claims(id),
 actor uuid not null,outcome text not null check(outcome in('CAPTURE_CONFIRMED','NOT_CAPTURED_CONFIRMED')),
 reason text not null,created_at timestamptz not null);
alter table cp7_reminder_native.local_bindings owner to cp7_reminder;
alter table cp7_reminder_native.local_claims owner to cp7_reminder;
alter table cp7_reminder_native.local_resolutions owner to cp7_reminder;
alter table cp7_reminder_native.local_bindings enable row level security;
alter table cp7_reminder_native.local_claims enable row level security;
alter table cp7_reminder_native.local_resolutions enable row level security;
create policy local_binding_no_access on cp7_reminder_native.local_bindings for all to public using(false)with check(false);
create policy local_claim_no_access on cp7_reminder_native.local_claims for all to public using(false)with check(false);
create policy local_resolution_no_access on cp7_reminder_native.local_resolutions for all to public using(false)with check(false);
revoke all on cp7_reminder_native.local_bindings,cp7_reminder_native.local_claims,cp7_reminder_native.local_resolutions from public,anon,authenticated,service_role;
create trigger local_binding_immutable before update or delete on cp7_reminder_native.local_bindings for each row execute function cp7_reminder_native.immutable_request();
create trigger local_resolution_immutable before update or delete on cp7_reminder_native.local_resolutions for each row execute function cp7_reminder_native.immutable_request();

create function cp7_reminder_native.guard_local_claim()returns trigger
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'or old.status<>'CLAIMED'or(old.id,old.actor,old.run_id,old.binding_id,old.condition_key,old.rule_id,
  old.episode_id,old.occurrence_key,old.environment,old.source_hash,old.policy_id,old.fence,old.body,old.body_sha256,old.created_at)
  is distinct from(new.id,new.actor,new.run_id,new.binding_id,new.condition_key,new.rule_id,
  new.episode_id,new.occurrence_key,new.environment,new.source_hash,new.policy_id,new.fence,new.body,new.body_sha256,new.created_at)
  or new.status='CLAIMED'then raise exception using errcode='55000',message='CP7_LOCAL_CLAIM_IMMUTABLE';end if;
 return new;
end $$;
create trigger local_claim_history before update or delete on cp7_reminder_native.local_claims for each row execute function cp7_reminder_native.guard_local_claim();

create function cp7_reminder_native.local_access(p_run uuid,rule text default null)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb:=cp7_reminder_native.access_now(p_run);
begin
 perform cp7_reminder_native.policy_scope_access(a,jsonb_build_object('rule_id',coalesce(rule,'PRODUCTION_GAP'),'scope_kind','GLOBAL','scope_key','*'));
 return a;
end $$;

-- Recheck the actual current capabilities after every wait without rereading
-- the expensive immutable Original for each rule. The initial authorization
-- and the final source/workspace still use the full protected Native reader.
create function cp7_reminder_native.local_recheck(a jsonb,rule text default null)returns void
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin
 perform cp7_reminder_native.policy_scope_access(a,jsonb_build_object('rule_id',coalesce(rule,'PRODUCTION_GAP'),'scope_kind','GLOBAL','scope_key','*'));

end $$;

create function cp7_reminder_native.local_binding_command(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare a jsonb;actor uuid:=auth.uid();old cp7_reminder_native.local_bindings%rowtype;
 inserted cp7_reminder_native.local_bindings%rowtype;cached cp7_reminder_native.requests%rowtype;r text;result jsonb;expected bigint;
begin
 if p_request is null or p_lookup is null or jsonb_typeof(p)is distinct from'object'
  or not(p?&array['run_id','expected_revision','enabled','label','environment','rules','reason'])or(select count(*)from jsonb_object_keys(p))<>7
  or jsonb_typeof(p->'enabled')is distinct from'boolean'or p->>'environment'is distinct from'LOCAL_TEST_SINK'
  or jsonb_typeof(p->'rules')is distinct from'array'or jsonb_array_length(p->'rules')not between 1 and 4
  or exists(select 1 from jsonb_array_elements(p->'rules')x where jsonb_typeof(x)<>'string'or x#>>'{}'not in('PRODUCTION_GAP','ACCESSORY_NEED','AR_DUE','AP_DUE'))
  or(select count(distinct x)from jsonb_array_elements(p->'rules')x)<>jsonb_array_length(p->'rules')
  or exists(select 1 from jsonb_each(p)e where e.key not in('enabled','rules')and jsonb_typeof(e.value)<>'string')
  or btrim(p->>'label')=''or length(p->>'label')>120 or btrim(p->>'reason')=''or length(p->>'reason')>1000
  or p->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'or(p->>'expected_revision')::numeric>9223372036854775806 then raise exception 'CP7_LOCAL_BINDING_PAYLOAD';end if;
 a:=cp7_reminder_native.local_access((p->>'run_id')::uuid);expected:=(p->>'expected_revision')::bigint;
 for r in select jsonb_array_elements_text(p->'rules')loop perform cp7_reminder_native.local_recheck(a,r);end loop;
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));perform cp7_reminder_native.recheck(a);
 select *into cached from cp7_reminder_native.requests q where q.actor=actor and q.request_id=p_request;
 if found then if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then result:=jsonb_build_object('request_id',p_request,'status','NOT_COMMITTED','binding_id',null,'revision',null);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:LOCAL_BINDING:'||actor::text,0));perform cp7_reminder_native.local_recheck(a);
  for r in select jsonb_array_elements_text(p->'rules')loop perform cp7_reminder_native.local_recheck(a,r);end loop;
  select *into old from cp7_reminder_native.local_bindings q where q.actor=actor order by q.revision desc limit 1;
  if coalesce(old.revision,0)<>expected then raise exception using errcode='40001',message='CP7_LOCAL_BINDING_STALE';end if;
  insert into cp7_reminder_native.local_bindings(actor,revision,previous_id,enabled,label,environment,rules,reason,created_at)
   values(actor,expected+1,old.id,(p->>'enabled')::boolean,p->>'label','LOCAL_TEST_SINK',p->'rules',p->>'reason',clock_timestamp())returning *into inserted;
  result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','binding_id',inserted.id,'revision',inserted.revision::text);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 perform cp7_reminder_native.local_recheck(a);
 for r in select jsonb_array_elements_text(p->'rules')loop perform cp7_reminder_native.local_recheck(a,r);end loop;
 select *into old from cp7_reminder_native.local_bindings q where q.actor=actor order by q.revision desc limit 1;
 return jsonb_build_object('contract_version','cp7.local-binding-command.v1','actor_scope_id',actor,'result',result,
  'binding',case when old.id is null then null else jsonb_build_object('id',old.id,'revision',old.revision::text,'previous_id',old.previous_id,
   'enabled',old.enabled,'label',old.label,'environment',old.environment,'rules',old.rules,'reason',old.reason,'created_at',old.created_at)end,
  'external_delivery_enabled',false,'scheduler_enabled',false);
end $$;

create function cp7_reminder_native.local_preview_command(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare actor uuid:=auth.uid();a jsonb;source jsonb;r jsonb;cached cp7_reminder_native.requests%rowtype;
 binding cp7_reminder_native.local_bindings%rowtype;claim cp7_reminder_native.local_claims%rowtype;episode cp7_reminder_native.rule_episodes%rowtype;
 result jsonb;timing jsonb;last_local timestamptz;at timestamptz;occurrence text;body text;policy_id uuid;attempt bigint;
begin
 if p_request is null or p_lookup is null or jsonb_typeof(p)is distinct from'object'or not(p?&array['run_id','condition_key','source_hash','binding_id'])
  or(select count(*)from jsonb_object_keys(p))<>4 or exists(select 1 from jsonb_each(p)e where jsonb_typeof(e.value)<>'string')
  or p->>'source_hash'!~'^[0-9a-f]{64}$'then raise exception 'CP7_LOCAL_PREVIEW_PAYLOAD';end if;
 a:=cp7_reminder_native.local_access((p->>'run_id')::uuid);
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));perform cp7_reminder_native.recheck(a);
 select *into cached from cp7_reminder_native.requests q where q.actor=actor and q.request_id=p_request;
 if found then if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then result:=jsonb_build_object('request_id',p_request,'status','NOT_COMMITTED','claim_id',null,'fence',null);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:LOCAL_BINDING:'||actor::text,0));perform cp7_reminder_native.recheck(a);
  select *into binding from cp7_reminder_native.local_bindings q where q.actor=actor order by q.revision desc limit 1;
  if binding.id is null or binding.id::text<>p->>'binding_id'or not binding.enabled then raise exception using errcode='40001',message='CP7_LOCAL_BINDING_UNAVAILABLE';end if;
  source:=cp7_reminder_native.condition_source((p->>'run_id')::uuid);
  if source->>'source_hash'<>p->>'source_hash'then raise exception using errcode='40001',message='CP7_LOCAL_SOURCE_CHANGED';end if;
  select x.value into r from jsonb_array_elements(source->'rows')x where x.value->>'key'=p->>'condition_key';
  if r is null or not(binding.rules?(r->>'rule_id'))then raise exception using errcode='42501',message='CP7_LOCAL_CONDITION_UNAVAILABLE';end if;
  perform cp7_reminder_native.local_recheck(a,r->>'rule_id');
  perform pg_advisory_xact_lock(hashtextextended('CP7:RULE_EPISODES:CURRENT_SOURCE',0));perform cp7_reminder_native.recheck(a);
  select *into episode from cp7_reminder_native.rule_episodes q where q.condition_key=r->>'key'and q.state='ACTIVE';
  if episode.id is null or episode.last_observed_at is null or not exists(select 1 from cp7_reminder_native.rule_observations q
   where q.episode_id=episode.id and q.source_hash=source->>'source_hash'and q.observation->'condition'->>'state'='ACTIVE')then
   raise exception using errcode='40001',message='CP7_LOCAL_CURRENT_EPISODE_REQUIRED';end if;
  if r->>'eligibility'<>'LOCAL_PREVIEW_ELIGIBLE'then raise exception using errcode='40001',message='CP7_LOCAL_SUPPRESSED_BY_CURRENT_RULE';end if;
  policy_id:=(r->'policy_binding'->'policy'->>'policy_id')::uuid;at:=(source->>'read_at')::timestamptz;
  select max(captured_at)into last_local from(
   select q.finished_at captured_at from cp7_reminder_native.local_claims q where q.actor=actor
    and q.condition_key=r->>'key'and q.episode_id=episode.id and q.status='LOCAL_SINK_CAPTURED'
   union all select s.created_at from cp7_reminder_native.local_resolutions s join cp7_reminder_native.local_claims q on q.id=s.claim_id
    where q.actor=actor and q.condition_key=r->>'key'and q.episode_id=episode.id and s.outcome='CAPTURE_CONFIRMED')captured;
  timing:=cp7_reminder_native.policy_timing(r->'policy_binding'->'policy'->'config',at,last_local);
  if timing->>'status'<>'READY'then raise exception using errcode='40001',message='CP7_LOCAL_COOLDOWN_OR_QUIET';end if;
  -- One episode+policy per explicitly reviewed local binding occurrence. A
  -- new UUID cannot manufacture another copy after an ambiguous local result.
  -- A confirmed non-capture can authorize a new explicit local attempt. The
  -- old UNKNOWN result, body and fence stay immutable; no worker retries it.
  select count(*)into attempt from cp7_reminder_native.local_resolutions s join cp7_reminder_native.local_claims q on q.id=s.claim_id
   where q.actor=actor and q.binding_id=binding.id and q.condition_key=r->>'key'and q.episode_id=episode.id
    and q.policy_id=policy_id and s.outcome='NOT_CAPTURED_CONFIRMED';
  occurrence:=encode(pg_catalog.sha256(convert_to(jsonb_build_object('binding',binding.id,'environment','LOCAL_TEST_SINK',
   'condition',r->>'key','episode',episode.id,'policy',policy_id,'reviewed_non_capture_count',attempt::text)::text,'UTF8')),'hex');
  select *into claim from cp7_reminder_native.local_claims q where q.actor=actor and q.binding_id=binding.id and q.occurrence_key=occurrence;
  if claim.id is null then
   if exists(select 1 from cp7_reminder_native.local_claims q where q.actor=actor and q.condition_key=r->>'key'
    and q.episode_id=episode.id and q.status in('CLAIMED','UNKNOWN')and not exists(select 1 from cp7_reminder_native.local_resolutions s
     where s.claim_id=q.id))then raise exception using errcode='40001',message='CP7_LOCAL_AMBIGUOUS_EPISODE_NO_NEW_OCCURRENCE';end if;
   source:=cp7_reminder_native.condition_source((p->>'run_id')::uuid);
   if source->>'source_hash'<>p->>'source_hash'then raise exception using errcode='40001',message='CP7_LOCAL_SOURCE_CHANGED';end if;
   select x.value into r from jsonb_array_elements(source->'rows')x where x.value->>'key'=p->>'condition_key';
   timing:=cp7_reminder_native.policy_timing(r->'policy_binding'->'policy'->'config',(source->>'read_at')::timestamptz,last_local);
   if r is null or r->>'eligibility'<>'LOCAL_PREVIEW_ELIGIBLE'or timing->>'status'<>'READY'then
    raise exception using errcode='40001',message='CP7_LOCAL_COOLDOWN_OR_QUIET';end if;
   at:=(source->>'read_at')::timestamptz;
   body:='PRATINJAU LOKAL — BELUM DIKIRIM'||chr(10)||case r->>'rule_id'
    when'PRODUCTION_GAP'then'Kebutuhan produksi'when'ACCESSORY_NEED'then'Kebutuhan aksesori'
    when'AR_DUE'then'Piutang jatuh tempo'else'Utang jatuh tempo'end||chr(10)||(r->>'label')||chr(10)||
    coalesce(r->'value'->>'value','Belum diketahui')||' '||(r->'value'->>'unit')||chr(10)||
    case r->'value'->>'state'when'ASSUMED'then'Berdasarkan skenario yang dipilih.'else'Berdasarkan sumber ERP yang diperiksa.'end||chr(10)||
    'Ini pratinjau lokal. Masalah tetap diperiksa dari transaksi ERP.';
   insert into cp7_reminder_native.local_claims(actor,run_id,binding_id,condition_key,rule_id,episode_id,occurrence_key,environment,
    source_hash,policy_id,status,body,body_sha256,created_at)values(actor,(p->>'run_id')::uuid,binding.id,r->>'key',r->>'rule_id',episode.id,occurrence,
    'LOCAL_TEST_SINK',source->>'source_hash',policy_id,'CLAIMED',body,encode(pg_catalog.sha256(convert_to(body,'UTF8')),'hex'),at)returning *into claim;
  end if;
  result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','claim_id',claim.id,'fence',claim.fence);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 perform cp7_reminder_native.recheck(a);
 if result->>'claim_id'is not null then
  select *into claim from cp7_reminder_native.local_claims q where q.id=(result->>'claim_id')::uuid and q.actor=actor;
  if claim.id is null then raise exception using errcode='42501',message='CP7_LOCAL_CLAIM_UNAVAILABLE';end if;
  perform cp7_reminder_native.local_recheck(a,claim.rule_id);
 end if;
 source:=cp7_reminder_native.condition_source((p->>'run_id')::uuid);
 return jsonb_build_object('contract_version','cp7.local-preview-command.v1','actor_scope_id',actor,'source',source,'result',result,
  'claim',case when claim.id is null then null else jsonb_build_object('id',claim.id,'status',claim.status,'occurrence_key',claim.occurrence_key,
   'binding_id',claim.binding_id,'environment',claim.environment,'condition_key',claim.condition_key,'episode_id',claim.episode_id,
   'policy_id',claim.policy_id,'source_hash',claim.source_hash,'body_sha256',claim.body_sha256,
   'body',case when claim.source_hash=source->>'source_hash'then claim.body else null end,'fence',claim.fence,'created_at',claim.created_at,
   'finished_at',claim.finished_at,'reason',claim.reason)end,'external_delivery_enabled',false,'sent',false);
end $$;

create function cp7_reminder_native.local_finish(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare actor uuid:=auth.uid();a jsonb;source jsonb;r jsonb;binding cp7_reminder_native.local_bindings%rowtype;
 claim cp7_reminder_native.local_claims%rowtype;cached cp7_reminder_native.requests%rowtype;result jsonb;outcome text;reason text;last_local timestamptz;timing jsonb;
begin
 if p_request is null or p_lookup is null or jsonb_typeof(p)is distinct from'object'or not(p?&array['run_id','claim_id','fence','outcome'])
  or(select count(*)from jsonb_object_keys(p))<>4 or exists(select 1 from jsonb_each(p)e where jsonb_typeof(e.value)<>'string')
  or p->>'outcome'not in('LOCAL_CAPTURE','UNKNOWN')then raise exception 'CP7_LOCAL_OUTCOME_PAYLOAD';end if;
 a:=cp7_reminder_native.local_access((p->>'run_id')::uuid);
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));perform cp7_reminder_native.recheck(a);
 select *into cached from cp7_reminder_native.requests q where q.actor=actor and q.request_id=p_request;
 if found then if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then result:=jsonb_build_object('request_id',p_request,'status','NOT_COMMITTED','claim_id',p->'claim_id','local_status',null);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 else
  -- Same binding/episode lock order as claim. Revalidation occurs after waits.
  perform pg_advisory_xact_lock(hashtextextended('CP7:LOCAL_BINDING:'||actor::text,0));perform cp7_reminder_native.recheck(a);
  perform pg_advisory_xact_lock(hashtextextended('CP7:RULE_EPISODES:CURRENT_SOURCE',0));perform cp7_reminder_native.recheck(a);
  select *into claim from cp7_reminder_native.local_claims q where q.id=(p->>'claim_id')::uuid and q.actor=actor for update;
  if claim.id is null or claim.fence::text<>p->>'fence'then raise exception using errcode='42501',message='CP7_LOCAL_FENCE_DENIED';end if;
  perform cp7_reminder_native.local_recheck(a,claim.rule_id);
  source:=cp7_reminder_native.condition_source((p->>'run_id')::uuid);select x.value into r from jsonb_array_elements(source->'rows')x where x.value->>'key'=claim.condition_key;
  if r is null then raise exception using errcode='42501',message='CP7_LOCAL_CONDITION_UNAVAILABLE';end if;
  select *into binding from cp7_reminder_native.local_bindings q where q.actor=actor order by q.revision desc limit 1;
  select max(captured_at)into last_local from(
   select q.finished_at captured_at from cp7_reminder_native.local_claims q where q.actor=actor and q.id<>claim.id
    and q.condition_key=claim.condition_key and q.episode_id=claim.episode_id and q.status='LOCAL_SINK_CAPTURED'
   union all select s.created_at from cp7_reminder_native.local_resolutions s join cp7_reminder_native.local_claims q on q.id=s.claim_id
    where q.actor=actor and q.condition_key=claim.condition_key and q.episode_id=claim.episode_id and s.outcome='CAPTURE_CONFIRMED')captured;
  timing:=cp7_reminder_native.policy_timing(r->'policy_binding'->'policy'->'config',(source->>'read_at')::timestamptz,last_local);
  if claim.status='CLAIMED'then
   if binding.id is distinct from claim.binding_id or not coalesce(binding.enabled,false)then outcome:='SUPPRESSED';reason:='BINDING_CHANGED_OR_DISABLED';
   elsif source->>'source_hash'<>claim.source_hash or r is null or r->>'eligibility'<>'LOCAL_PREVIEW_ELIGIBLE'then outcome:='SUPPRESSED';reason:='SOURCE_POLICY_QUIET_OR_CONDITION_CHANGED';
   elsif not exists(select 1 from cp7_reminder_native.rule_episodes q where q.id=claim.episode_id and q.state='ACTIVE')then outcome:='SUPPRESSED';reason:='EPISODE_NO_LONGER_ACTIVE';
   elsif timing->>'status'<>'READY'then outcome:='SUPPRESSED';reason:='CURRENT_COOLDOWN_OR_QUIET';
   elsif p->>'outcome'='UNKNOWN'then outcome:='UNKNOWN';reason:='LOCAL_OUTCOME_UNCERTAIN_NO_AUTOMATIC_RESEND';
   else outcome:='LOCAL_SINK_CAPTURED';reason:='EXPLICIT_LOCAL_CONTRACT_CAPTURE_NOT_EXTERNAL_DELIVERY';end if;
   update cp7_reminder_native.local_claims q set status=outcome,reason=reason,finished_at=clock_timestamp()where q.id=claim.id returning *into claim;
  end if;
  result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','claim_id',claim.id,'local_status',claim.status);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 select *into claim from cp7_reminder_native.local_claims q where q.id=(p->>'claim_id')::uuid and q.actor=actor;
 if claim.id is null or claim.fence::text<>p->>'fence'then raise exception using errcode='42501',message='CP7_LOCAL_FENCE_DENIED';end if;
 perform cp7_reminder_native.local_recheck(a,claim.rule_id);perform cp7_reminder_native.recheck(a);
 return jsonb_build_object('contract_version','cp7.local-outcome-command.v1','actor_scope_id',actor,'result',result,
  'current_local_status',claim.status,'external_delivery_enabled',false,'sent',false,'business_resolved_by_delivery',false);
end $$;

alter function cp7_reminder_native.guard_local_claim()owner to cp7_reminder;
alter function cp7_reminder_native.local_recheck(jsonb,text)owner to cp7_reminder;
revoke all on function cp7_reminder_native.local_recheck(jsonb,text)from public,anon,authenticated,service_role;
alter function cp7_reminder_native.local_access(uuid,text)owner to cp7_reminder;
alter function cp7_reminder_native.local_binding_command(jsonb,uuid,boolean)owner to cp7_reminder;
alter function cp7_reminder_native.local_preview_command(jsonb,uuid,boolean)owner to cp7_reminder;
alter function cp7_reminder_native.local_finish(jsonb,uuid,boolean)owner to cp7_reminder;
revoke all on function cp7_reminder_native.guard_local_claim(),cp7_reminder_native.local_access(uuid,text),
 cp7_reminder_native.local_binding_command(jsonb,uuid,boolean),cp7_reminder_native.local_preview_command(jsonb,uuid,boolean),cp7_reminder_native.local_finish(jsonb,uuid,boolean)
 from public,anon,authenticated,service_role;
create function cp7_reminder_native.local_manual_resolution(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare actor uuid:=auth.uid();a jsonb;source jsonb;claim cp7_reminder_native.local_claims%rowtype;
 saved cp7_reminder_native.local_resolutions%rowtype;cached cp7_reminder_native.requests%rowtype;result jsonb;
begin
 if p_request is null or p_lookup is null or jsonb_typeof(p)is distinct from'object'
  or not(p?&array['run_id','claim_id','fence','outcome','reason'])or(select count(*)from jsonb_object_keys(p))<>5
  or exists(select 1 from jsonb_each(p)e where jsonb_typeof(e.value)<>'string')
  or p->>'outcome'not in('CAPTURE_CONFIRMED','NOT_CAPTURED_CONFIRMED')or btrim(p->>'reason')=''or length(p->>'reason')>1000
  then raise exception 'CP7_LOCAL_RESOLUTION_PAYLOAD';end if;
 a:=cp7_reminder_native.local_access((p->>'run_id')::uuid);
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));perform cp7_reminder_native.recheck(a);
 select *into cached from cp7_reminder_native.requests q where q.actor=actor and q.request_id=p_request;
 if found then if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then result:=jsonb_build_object('request_id',p_request,'status','NOT_COMMITTED','claim_id',p->'claim_id','resolution_id',null);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:LOCAL_BINDING:'||actor::text,0));perform cp7_reminder_native.recheck(a);
  perform pg_advisory_xact_lock(hashtextextended('CP7:RULE_EPISODES:CURRENT_SOURCE',0));perform cp7_reminder_native.recheck(a);
  select *into claim from cp7_reminder_native.local_claims q where q.id=(p->>'claim_id')::uuid and q.actor=actor for update;
  if claim.id is null or claim.fence::text<>p->>'fence'then raise exception using errcode='42501',message='CP7_LOCAL_FENCE_DENIED';end if;
  perform cp7_reminder_native.local_recheck(a,claim.rule_id);
  source:=cp7_reminder_native.condition_source((p->>'run_id')::uuid);
  if not exists(select 1 from jsonb_array_elements(source->'rows')x where x->>'key'=claim.condition_key)then
   raise exception using errcode='42501',message='CP7_LOCAL_CONDITION_UNAVAILABLE';end if;
  if claim.status<>'UNKNOWN'then raise exception using errcode='40001',message='CP7_LOCAL_UNKNOWN_REQUIRED';end if;
  select *into saved from cp7_reminder_native.local_resolutions q where q.claim_id=claim.id;
  if saved.id is not null then raise exception using errcode='40001',message='CP7_LOCAL_ALREADY_RESOLVED';end if;
  insert into cp7_reminder_native.local_resolutions(claim_id,actor,outcome,reason,created_at)
   values(claim.id,actor,p->>'outcome',p->>'reason',clock_timestamp())returning *into saved;
  result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','claim_id',claim.id,'resolution_id',saved.id);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 select *into claim from cp7_reminder_native.local_claims q where q.id=(p->>'claim_id')::uuid and q.actor=actor;
 if claim.id is null or claim.fence::text<>p->>'fence'then raise exception using errcode='42501',message='CP7_LOCAL_FENCE_DENIED';end if;
 perform cp7_reminder_native.local_recheck(a,claim.rule_id);perform cp7_reminder_native.recheck(a);
 return jsonb_build_object('contract_version','cp7.local-resolution-command.v1','actor_scope_id',actor,'result',result,
  'original_local_status',claim.status,'external_delivery_enabled',false,'sent',false,'business_resolved_by_delivery',false);
end $$;

create function cp7_reminder_native.local_workspace(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare a jsonb:=cp7_reminder_native.local_access(p_run);actor uuid:=auth.uid();source jsonb;binding cp7_reminder_native.local_bindings%rowtype;
 claims jsonb;r text;
begin
 source:=cp7_reminder_native.condition_source(p_run);
 select *into binding from cp7_reminder_native.local_bindings q where q.actor=actor order by q.revision desc limit 1;
 if binding.id is not null then for r in select jsonb_array_elements_text(binding.rules)loop perform cp7_reminder_native.local_recheck(a,r);end loop;end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',q.id,'run_id',q.run_id,'status',q.status,'occurrence_key',q.occurrence_key,
  'binding_id',q.binding_id,'environment',q.environment,'condition_key',q.condition_key,'rule_id',q.rule_id,'episode_id',q.episode_id,
  'policy_id',q.policy_id,'source_hash',q.source_hash,'body_sha256',q.body_sha256,
  'body',case when q.source_hash=source->>'source_hash'and q.status<>'SUPPRESSED'then q.body else null end,
  'fence',q.fence,'created_at',q.created_at,'finished_at',q.finished_at,'reason',q.reason,
  'resolution',case when s.id is null then null else jsonb_build_object('id',s.id,'outcome',s.outcome,'reason',s.reason,'created_at',s.created_at)end)
  order by q.created_at,q.id),'[]')into claims from cp7_reminder_native.local_claims q left join cp7_reminder_native.local_resolutions s on s.claim_id=q.id
  where q.actor=actor and exists(select 1 from jsonb_array_elements(source->'rows')x where x->>'key'=q.condition_key);
 if jsonb_array_length(claims)>4000 or octet_length(claims::text)>8000000 then raise exception 'CP7_LOCAL_HISTORY_INCOMPLETE';end if;
 perform cp7_reminder_native.recheck(a);
 return jsonb_build_object('contract_version','cp7.native-local-workspace.v1','actor_scope_id',actor,'source',source,
  'binding',case when binding.id is null then null else jsonb_build_object('id',binding.id,'revision',binding.revision::text,'previous_id',binding.previous_id,
   'enabled',binding.enabled,'label',binding.label,'environment',binding.environment,'rules',binding.rules,'reason',binding.reason,'created_at',binding.created_at)end,
  'claims',claims,'page_complete',true,'total',jsonb_array_length(claims)::text,'external_delivery_enabled',false,'scheduler_enabled',false,'sent',false);
end $$;

create function cp7_reminder_native.local_command(p jsonb,p_request uuid,operation text,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare result jsonb;workspace jsonb;
begin
 case operation when'BINDING'then result:=cp7_reminder_native.local_binding_command(p,p_request,p_lookup);
 when'PREVIEW'then result:=cp7_reminder_native.local_preview_command(p,p_request,p_lookup);
 when'OUTCOME'then result:=cp7_reminder_native.local_finish(p,p_request,p_lookup);
 when'RESOLUTION'then result:=cp7_reminder_native.local_manual_resolution(p,p_request,p_lookup);
 else raise exception 'CP7_LOCAL_OPERATION';end case;
 workspace:=cp7_reminder_native.local_workspace((p->>'run_id')::uuid);
 if result->'result'->>'claim_id'is not null and not exists(select 1 from jsonb_array_elements(workspace->'claims')x
  where x->>'id'=result->'result'->>'claim_id')then raise exception using errcode='42501',message='CP7_LOCAL_CONDITION_UNAVAILABLE';end if;
 return jsonb_build_object('contract_version','cp7.native-local-command.v1','actor_scope_id',auth.uid(),'operation',operation,
  'workspace',workspace,'result',result->'result');
end $$;

alter function cp7_reminder_native.local_manual_resolution(jsonb,uuid,boolean)owner to cp7_reminder;
alter function cp7_reminder_native.local_workspace(uuid)owner to cp7_reminder;
alter function cp7_reminder_native.local_command(jsonb,uuid,text,boolean)owner to cp7_reminder;
revoke all on function cp7_reminder_native.local_manual_resolution(jsonb,uuid,boolean),cp7_reminder_native.local_workspace(uuid),cp7_reminder_native.local_command(jsonb,uuid,text,boolean)
 from public,anon,authenticated,service_role;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_get_local_reminders_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.local_workspace(p_run)$$;
create function public.erp_cp7_save_local_binding_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.local_command(p_payload,p_request,'BINDING',false)$$;
create function public.erp_cp7_claim_local_preview_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.local_command(p_payload,p_request,'PREVIEW',false)$$;
create function public.erp_cp7_finish_local_preview_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.local_command(p_payload,p_request,'OUTCOME',false)$$;
create function public.erp_cp7_resolve_local_preview_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.local_command(p_payload,p_request,'RESOLUTION',false)$$;
create function public.erp_cp7_get_local_reminder_request_v1(p_payload jsonb,p_request uuid,p_operation text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.local_command(p_payload,p_request,p_operation,true)$$;
alter function public.erp_cp7_get_local_reminders_v1(uuid)owner to cp7_reminder;
alter function public.erp_cp7_save_local_binding_v1(jsonb,uuid)owner to cp7_reminder;
alter function public.erp_cp7_claim_local_preview_v1(jsonb,uuid)owner to cp7_reminder;
alter function public.erp_cp7_finish_local_preview_v1(jsonb,uuid)owner to cp7_reminder;
alter function public.erp_cp7_resolve_local_preview_v1(jsonb,uuid)owner to cp7_reminder;
alter function public.erp_cp7_get_local_reminder_request_v1(jsonb,uuid,text)owner to cp7_reminder;
revoke create on schema public from cp7_reminder;
revoke all on function public.erp_cp7_get_local_reminders_v1(uuid),public.erp_cp7_save_local_binding_v1(jsonb,uuid),public.erp_cp7_claim_local_preview_v1(jsonb,uuid),
 public.erp_cp7_finish_local_preview_v1(jsonb,uuid),public.erp_cp7_resolve_local_preview_v1(jsonb,uuid),public.erp_cp7_get_local_reminder_request_v1(jsonb,uuid,text)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_local_reminders_v1(uuid),public.erp_cp7_save_local_binding_v1(jsonb,uuid),public.erp_cp7_claim_local_preview_v1(jsonb,uuid),
 public.erp_cp7_finish_local_preview_v1(jsonb,uuid),public.erp_cp7_resolve_local_preview_v1(jsonb,uuid),public.erp_cp7_get_local_reminder_request_v1(jsonb,uuid,text)to authenticated;
