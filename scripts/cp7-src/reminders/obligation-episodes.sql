-- Monitoring metadata only. Accepted AR/AP conditions remain the sole producer.
-- Identity is the Native business source, never an actor, analysis run or clock.
create table cp7_reminder_native.obligation_episodes(
 id uuid primary key default gen_random_uuid(),domain text not null check(domain in('AR','MATERIAL_AP')),
 source_id uuid not null,source_label text not null,episode_number bigint not null check(episode_number>0),
 previous_episode_id uuid references cp7_reminder_native.obligation_episodes(id),
 rule_version text not null check(rule_version='cp7.native-obligation.v1'),
 state text not null check(state in('ACTIVE','RESOLVED','ARCHIVED')),
 freshness text not null check(freshness in('KNOWN','UNKNOWN')),
 condition_state text not null,reason text not null,
 source_revision text not null,native_source_hash text not null,
 first_observed_at timestamptz not null,last_observed_at timestamptz not null,last_known_observed_at timestamptz,
 closed_at timestamptz,revision bigint not null check(revision>0),
 unique(domain,source_id,episode_number),
 check((state='ACTIVE')=(closed_at is null)),
 check(state<>'RESOLVED'or(freshness='KNOWN'and condition_state='ZERO_BALANCE')));
create unique index obligation_one_active on cp7_reminder_native.obligation_episodes(domain,source_id)where state='ACTIVE';
create table cp7_reminder_native.obligation_observations(
 actor uuid not null,request_id uuid not null,source_id uuid not null,domain text not null,
 episode_id uuid references cp7_reminder_native.obligation_episodes(id),
 observed_at timestamptz not null,observation jsonb not null,
 primary key(actor,request_id,source_id));
alter table cp7_reminder_native.obligation_episodes owner to cp7_reminder;
alter table cp7_reminder_native.obligation_observations owner to cp7_reminder;
alter table cp7_reminder_native.obligation_episodes enable row level security;
alter table cp7_reminder_native.obligation_observations enable row level security;
create policy obligation_episode_no_access on cp7_reminder_native.obligation_episodes for all to public using(false)with check(false);
create policy obligation_observation_no_access on cp7_reminder_native.obligation_observations for all to public using(false)with check(false);
revoke all on cp7_reminder_native.obligation_episodes,cp7_reminder_native.obligation_observations from public,anon,authenticated,service_role;

create function cp7_reminder_native.guard_obligation_episode()returns trigger
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'or(old.id,old.domain,old.source_id,old.episode_number,old.previous_episode_id,old.rule_version,old.first_observed_at)
  is distinct from(new.id,new.domain,new.source_id,new.episode_number,new.previous_episode_id,new.rule_version,new.first_observed_at)
  or old.state<>'ACTIVE'then raise exception using errcode='55000',message='CP7_OBLIGATION_EPISODE_HISTORY_IMMUTABLE';end if;
 return new;
end $$;
create trigger obligation_episode_history before update or delete on cp7_reminder_native.obligation_episodes for each row execute function cp7_reminder_native.guard_obligation_episode();
create trigger obligation_observation_immutable before update or delete on cp7_reminder_native.obligation_observations for each row execute function cp7_reminder_native.immutable_request();

create function cp7_reminder_native.obligation_access(p jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;permission text;
begin
 if jsonb_typeof(p)is distinct from'object'or not p?&array['run_id','domain']
  or(select count(*)from jsonb_object_keys(p))<>2
  or jsonb_typeof(p->'run_id')is distinct from'string'or jsonb_typeof(p->'domain')is distinct from'string'
  or p->>'domain'not in('AR','MATERIAL_AP')then raise exception 'CP7_OBLIGATION_PAYLOAD';end if;
 a:=cp7_reminder_native.access_now((p->>'run_id')::uuid);
 permission:=case p->>'domain'when'AR'then'finance.ar.view'else'finance.ap.view'end;
 if not erp.has_permission(permission)then raise exception using errcode='42501',message='CP7_OBLIGATION_ACCESS_DENIED';end if;
 return a;
end $$;

create function cp7_reminder_native.obligation_evaluate(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare a jsonb:=cp7_reminder_native.obligation_access(p);again jsonb;actor uuid:=auth.uid();domain text:=p->>'domain';
 cached cp7_reminder_native.requests%rowtype;episode cp7_reminder_native.obligation_episodes%rowtype;
 source jsonb;conditions jsonb:='[]';c jsonb;observations jsonb:='[]';observation jsonb;result jsonb;
 source_id uuid;seen uuid[]:='{}';at timestamptz;source_status text:='COMPLETE';source_hash text;as_of text;
 freshness text;transition text;reason text;episode_state text;incomplete boolean:=false;
begin
 if p_request is null or p_lookup is null then raise exception 'CP7_OBLIGATION_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));
 again:=cp7_reminder_native.obligation_access(p);
 if again->'access'is distinct from a->'access'then raise exception using errcode='42501',message='CP7_OBLIGATION_ACCESS_CHANGED';end if;
 select *into cached from cp7_reminder_native.requests r where r.actor=actor and r.request_id=p_request;
 if found then
  if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;
  result:=cached.result;
 else
  if p_lookup then
   -- An absent committed result is sealed while the same command lock is held.
   result:=jsonb_build_object('request_id',p_request,'status','NOT_COMMITTED','domain',domain,
    'source_status','NOT_EVALUATED','source_hash',null,'as_of',null,'source_read_at',null,'observed_at',null,'source_total',null,'rows','[]'::jsonb);
  else
   -- Shared business identity across authorized actors; source is read only
   -- after this lock, so an older pre-wait snapshot cannot overwrite recovery.
   perform pg_advisory_xact_lock(hashtextextended('CP7:OBLIGATION_DOMAIN:'||domain,0));
   again:=cp7_reminder_native.obligation_access(p);
   if again->'access'is distinct from a->'access'then raise exception using errcode='42501',message='CP7_OBLIGATION_ACCESS_CHANGED';end if;
   begin
    source:=case domain when'AR'then cp7_reminder_native.receivable_source()else cp7_reminder_native.payable_source()end;
   exception when raise_exception then
    if sqlerrm not in('CP7_REMINDER_AR_SOURCE_INCOMPLETE','CP7_REMINDER_AP_SOURCE_INCOMPLETE')then raise;end if;
    incomplete:=true;source_status:='INCOMPLETE';
   end;
   -- Monitoring observation time is after the serialized source read. Keep
   -- the producer's one statement clock separately; a pre-wait clock must
   -- not move first/last monitoring observations backwards across workers.
   at:=clock_timestamp();source_hash:=source->>'source_hash';as_of:=source->>'as_of';
   if not incomplete then
    conditions:=case domain when'AR'then
     (select coalesce(jsonb_agg(n.value||jsonb_build_object('source_label',(select h.value->>'number'from jsonb_array_elements(source->'pages')s(value) cross join lateral jsonb_array_elements(s.value->'page'->'rows')h(value) where h.value->>'id'=n.value->>'source_id'))),'[]')from jsonb_array_elements(source->'conditions')n(value))else
     (select coalesce(jsonb_agg((r->'condition')||jsonb_build_object('source_id',r->'liability'->>'purchase_id','source_label',r->'liability'->>'purchase_number')),'[]')from jsonb_array_elements(source->'rows')r)end;
   end if;
   -- Missing/partial is a failed observation, never a healthy empty source.
   conditions:=conditions||coalesce((select jsonb_agg(jsonb_build_object('source_id',e.source_id,'source_label',e.source_label,'state','SOURCE_UNKNOWN',
    'source_revision',e.source_revision,'native_source_hash',e.native_source_hash,'business_resolved',false))
    from cp7_reminder_native.obligation_episodes e where e.domain=domain and e.state='ACTIVE'and not exists(
     select 1 from jsonb_array_elements(conditions)x where x->>'source_id'=e.source_id::text)),'[]');
   if jsonb_array_length(conditions)>10000 then raise exception 'CP7_OBLIGATION_SCOPE_INCOMPLETE';end if;
   for c in select value from jsonb_array_elements(conditions)loop
    source_id:=(c->>'source_id')::uuid;
    if coalesce(c->>'source_label','')=''then raise exception 'CP7_OBLIGATION_SOURCE_LABEL_INCOMPLETE';end if;
    if source_id=any(seen)then raise exception 'CP7_OBLIGATION_DUPLICATE_SOURCE';end if;seen:=array_append(seen,source_id);
    select *into episode from cp7_reminder_native.obligation_episodes e where e.domain=domain and e.source_id=source_id order by episode_number desc limit 1 for update;
    freshness:=case when c->>'state'in('UNKNOWN_BALANCE','SOURCE_UNKNOWN')then'UNKNOWN'else'KNOWN'end;
    reason:=case when c->>'state'='SOURCE_UNKNOWN'then case when incomplete then'SOURCE_INCOMPLETE'else'MISSING_FROM_COMPLETE_SOURCE'end
     when freshness='UNKNOWN'then'NATIVE_BALANCE_UNKNOWN'when c->'business_resolved'='true'::jsonb then'NATIVE_ZERO_AND_REQUIRED_INVOICE_COVERAGE'
     when c->>'state'in('DRAFT_ONLY','INACTIVE_DOCUMENT')then'NATIVE_DOCUMENT_INACTIVE'else'NATIVE_CONDITION_REQUIRES_REVIEW'end;
    episode_state:=case when c->'business_resolved'='true'::jsonb then'RESOLVED'when c->>'state'in('DRAFT_ONLY','INACTIVE_DOCUMENT')then'ARCHIVED'else'ACTIVE'end;
    transition:='NO_EPISODE';
    if episode.id is not null and episode.state='ACTIVE'then
     transition:=case when freshness='UNKNOWN'then'DATA_UNKNOWN'when episode_state='RESOLVED'then'RESOLVED'when episode_state='ARCHIVED'then'ARCHIVED'else'OBSERVED'end;
     update cp7_reminder_native.obligation_episodes e set state=episode_state,freshness=freshness,
      condition_state=case when c->>'state'='SOURCE_UNKNOWN'then e.condition_state else c->>'state'end,reason=reason,
      source_label=c->>'source_label',source_revision=c->>'source_revision',native_source_hash=c->>'native_source_hash',last_observed_at=at,
      last_known_observed_at=case when freshness='KNOWN'then at else e.last_known_observed_at end,
      closed_at=case when episode_state='ACTIVE'then null else at end,revision=e.revision+1 where e.id=episode.id returning *into episode;
    elsif episode_state='ACTIVE'then
     transition:=case when episode.id is null then'OPENED'else'REOPENED_NEW_EPISODE'end;
     insert into cp7_reminder_native.obligation_episodes(domain,source_id,source_label,episode_number,previous_episode_id,rule_version,state,freshness,
      condition_state,reason,source_revision,native_source_hash,first_observed_at,last_observed_at,last_known_observed_at,revision)
     values(domain,source_id,c->>'source_label',coalesce(episode.episode_number,0)+1,episode.id,'cp7.native-obligation.v1','ACTIVE',freshness,
      c->>'state',reason,c->>'source_revision',c->>'native_source_hash',at,at,case when freshness='KNOWN'then at else null end,1)returning *into episode;
    end if;
    observation:=jsonb_build_object('source_id',source_id,'source_label',c->>'source_label','condition_state',c->>'state','freshness',freshness,'reason',reason,
     'source_revision',c->>'source_revision','native_source_hash',case when c->>'state'='SOURCE_UNKNOWN'then null else c->>'native_source_hash'end,
     'business_resolved',coalesce(c->'business_resolved','false'::jsonb),'transition',transition,
     'episode',case when episode.id is null then null else jsonb_build_object('id',episode.id,'number',episode.episode_number::text,
      'previous_episode_id',episode.previous_episode_id,'state',episode.state,'freshness',episode.freshness,
      'first_observed_at',episode.first_observed_at,'last_observed_at',episode.last_observed_at,'last_known_observed_at',episode.last_known_observed_at,'closed_at',episode.closed_at,'revision',episode.revision::text)end);
    insert into cp7_reminder_native.obligation_observations values(actor,p_request,source_id,domain,episode.id,at,observation);
    observations:=observations||jsonb_build_array(observation);
   end loop;
   result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','domain',domain,'source_status',source_status,
    'source_hash',source_hash,'as_of',as_of,'source_read_at',source->>'read_at','observed_at',at,'source_total',source->>'total','rows',observations);
  end if;
  again:=cp7_reminder_native.obligation_access(p);
  if again->'access'is distinct from a->'access'then raise exception using errcode='42501',message='CP7_OBLIGATION_ACCESS_CHANGED';end if;
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,statement_timestamp());
 end if;
 again:=cp7_reminder_native.obligation_access(p);
 if again->'access'is distinct from a->'access'then raise exception using errcode='42501',message='CP7_OBLIGATION_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-obligation-observation.v1','actor_scope_id',actor,
  'analysis',again->'analysis','rule_version','cp7.native-obligation.v1','read_kind','SAVED_OBSERVATION',
  'result',result,'read_at',clock_timestamp());
end $$;
alter function cp7_reminder_native.guard_obligation_episode()owner to cp7_reminder;
alter function cp7_reminder_native.obligation_access(jsonb)owner to cp7_reminder;
alter function cp7_reminder_native.obligation_evaluate(jsonb,uuid,boolean)owner to cp7_reminder;
revoke all on function cp7_reminder_native.guard_obligation_episode(),cp7_reminder_native.obligation_access(jsonb),cp7_reminder_native.obligation_evaluate(jsonb,uuid,boolean)from public,anon,authenticated,service_role;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_evaluate_obligation_episodes_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.obligation_evaluate(p_payload,p_request,false)$$;
create function public.erp_cp7_get_obligation_episode_request_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.obligation_evaluate(p_payload,p_request,true)$$;
alter function public.erp_cp7_evaluate_obligation_episodes_v1(jsonb,uuid)owner to cp7_reminder;
alter function public.erp_cp7_get_obligation_episode_request_v1(jsonb,uuid)owner to cp7_reminder;
revoke create on schema public from cp7_reminder;
revoke all on function public.erp_cp7_evaluate_obligation_episodes_v1(jsonb,uuid),public.erp_cp7_get_obligation_episode_request_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_evaluate_obligation_episodes_v1(jsonb,uuid),public.erp_cp7_get_obligation_episode_request_v1(jsonb,uuid)to authenticated;
