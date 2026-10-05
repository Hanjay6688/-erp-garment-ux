-- Shared condition episodes are not own-user review states or delivery rows.
create table cp7_reminder_native.rule_episodes(
 id uuid primary key default gen_random_uuid(),condition_key text not null,rule_id text not null,
 episode_number bigint not null check(episode_number>0),previous_id uuid references cp7_reminder_native.rule_episodes(id),
 state text not null check(state in('ACTIVE','RESOLVED','ARCHIVED')),freshness text not null check(freshness in('KNOWN','ASSUMED','UNKNOWN')),
 condition_state text not null,first_observed_at timestamptz not null,last_observed_at timestamptz not null,
 resolved_at timestamptz,archived_at timestamptz,unique(condition_key,episode_number),
 check((state='RESOLVED')=(resolved_at is not null)),check((state='ARCHIVED')=(archived_at is not null)));
create unique index rule_episode_one_active on cp7_reminder_native.rule_episodes(condition_key)where state='ACTIVE';
create table cp7_reminder_native.rule_observations(
 actor uuid not null,request_id uuid not null,condition_key text not null,episode_id uuid references cp7_reminder_native.rule_episodes(id),
 source_hash text not null,observed_at timestamptz not null,observation jsonb not null,primary key(actor,request_id,condition_key));
alter table cp7_reminder_native.rule_episodes owner to cp7_reminder;
alter table cp7_reminder_native.rule_observations owner to cp7_reminder;
alter table cp7_reminder_native.rule_episodes enable row level security;
alter table cp7_reminder_native.rule_observations enable row level security;
create policy rule_episode_no_access on cp7_reminder_native.rule_episodes for all to public using(false)with check(false);
create policy rule_observation_no_access on cp7_reminder_native.rule_observations for all to public using(false)with check(false);
revoke all on cp7_reminder_native.rule_episodes,cp7_reminder_native.rule_observations from public,anon,authenticated,service_role;

create function cp7_reminder_native.guard_rule_episode()returns trigger
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'or old.state<>'ACTIVE'or(old.id,old.condition_key,old.rule_id,old.episode_number,old.previous_id,old.first_observed_at)
  is distinct from(new.id,new.condition_key,new.rule_id,new.episode_number,new.previous_id,new.first_observed_at)
  or new.last_observed_at<old.last_observed_at or(new.state='RESOLVED'and(new.freshness<>'KNOWN'or new.condition_state<>'RESOLVED'))
  or(new.state='ARCHIVED'and(new.freshness<>'KNOWN'or new.condition_state<>'INACTIVE_DOCUMENT'or new.archived_at<>new.last_observed_at))then
  raise exception using errcode='55000',message='CP7_RULE_EPISODE_IMMUTABLE';end if;
 return new;
end $$;
create trigger rule_episode_history before update or delete on cp7_reminder_native.rule_episodes for each row execute function cp7_reminder_native.guard_rule_episode();
create trigger rule_observation_immutable before update or delete on cp7_reminder_native.rule_observations for each row execute function cp7_reminder_native.immutable_request();

create function cp7_reminder_native.rule_episode_evaluate(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare a jsonb;source jsonb;final_source jsonb;r jsonb;observation jsonb;observations jsonb:='[]';
 cached cp7_reminder_native.requests%rowtype;episode cp7_reminder_native.rule_episodes%rowtype;previous cp7_reminder_native.rule_episodes%rowtype;
 result jsonb;transition text;freshness text;at timestamptz;actor uuid:=auth.uid();
begin
 if p_request is null or p_lookup is null or jsonb_typeof(p)is distinct from'object'or not(p?&array['run_id','source_hash'])
  or(select count(*)from jsonb_object_keys(p))<>2 or exists(select 1 from jsonb_each(p)e where jsonb_typeof(e.value)<>'string')
  or p->>'source_hash'!~'^[0-9a-f]{64}$'then raise exception 'CP7_RULE_EPISODE_PAYLOAD';end if;
 a:=cp7_reminder_native.original_authority((p->>'run_id')::uuid);
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));perform cp7_reminder_native.recheck(a);
 select *into cached from cp7_reminder_native.requests q where q.actor=actor and q.request_id=p_request;
 if found then
  if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then
  result:=jsonb_build_object('request_id',p_request,'status','NOT_COMMITTED','source_hash',p->'source_hash','rows','[]'::jsonb);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:RULE_EPISODES:CURRENT_SOURCE',0));perform cp7_reminder_native.recheck(a);
  source:=cp7_reminder_native.condition_source((p->>'run_id')::uuid);
  if source->>'source_hash'<>p->>'source_hash'then raise exception using errcode='40001',message='CP7_RULE_EPISODE_SOURCE_CHANGED';end if;
  at:=(source->>'read_at')::timestamptz;
  for r in select x.value from jsonb_array_elements(source->'rows')x loop
   select *into episode from cp7_reminder_native.rule_episodes q where q.condition_key=r->>'key'and q.state='ACTIVE'for update;
   transition:='OBSERVED_NO_ACTIVE_EPISODE';freshness:=case when r->>'state'in('DATA_REVIEW','SOURCE_CHANGED')then'UNKNOWN'
    when r->'value'->>'state'='ASSUMED'then'ASSUMED'else'KNOWN'end;
   if(r->>'state'='ACTIVE'or r->>'economic_state'='OPEN'or(r->>'state'='DATA_REVIEW'and r->>'domain'in(
    'OPENING_AR','OPENING_AP','PAYROLL_AP','ACCESSORY_AP','LAUNDRY_AP','LAUNDRY_RECEIPT','LAUNDRY_OPENING_UNINVOICED')))and episode.id is null then
    -- A real Native document with unresolved evidence gets an UNKNOWN review
    -- episode, not an invented overdue amount or a delivery permission.
    select *into previous from cp7_reminder_native.rule_episodes q where q.condition_key=r->>'key'order by q.episode_number desc limit 1;
    insert into cp7_reminder_native.rule_episodes(condition_key,rule_id,episode_number,previous_id,state,freshness,condition_state,first_observed_at,last_observed_at)
     values(r->>'key',r->>'rule_id',coalesce(previous.episode_number,0)+1,previous.id,'ACTIVE',freshness,r->>'state',at,at)returning *into episode;
    transition:=case when previous.id is null then'OPENED'else'REOPENED_NEW_EPISODE'end;
   elsif episode.id is not null then
    if r->>'economic_state'='INACTIVE'and r->>'state'='NO_CURRENT_GAP'
     and r->>'reason'in('INACTIVE_DOCUMENT','DRAFT_ONLY')and r->'business_resolved'='false'::jsonb then
     -- Explicit current Native inactivity closes this source's alert episode,
     -- never the debt by payment. Absence, partial coverage and UNKNOWN cannot
     -- archive it. The replacement document owns a different condition key.
     update cp7_reminder_native.rule_episodes q set state='ARCHIVED',freshness='KNOWN',condition_state='INACTIVE_DOCUMENT',
      last_observed_at=at,archived_at=at where q.id=episode.id returning *into episode;transition:='ARCHIVED_INACTIVE_DOCUMENT';
    elsif r->'business_resolved'='true'::jsonb and r->>'state'='RESOLVED'then
     update cp7_reminder_native.rule_episodes q set state='RESOLVED',freshness='KNOWN',condition_state='RESOLVED',last_observed_at=at,resolved_at=at where q.id=episode.id returning *into episode;transition:='RESOLVED';
    else
     update cp7_reminder_native.rule_episodes q set freshness=freshness,condition_state=r->>'state',last_observed_at=at where q.id=episode.id returning *into episode;
     transition:=case when freshness='UNKNOWN'then'UNKNOWN_RETAINED'when r->>'state'='NO_CURRENT_GAP'then'SCENARIO_NO_ALERT_EPISODE_RETAINED'else'ACTIVE_RETAINED'end;
    end if;
   end if;
   observation:=jsonb_build_object('condition',r,'episode',case when episode.id is null then null else jsonb_build_object(
    'id',episode.id,'number',episode.episode_number::text,'previous_id',episode.previous_id,'state',episode.state,'freshness',episode.freshness,
    'first_observed_at',episode.first_observed_at,'last_observed_at',episode.last_observed_at,'resolved_at',episode.resolved_at)
     ||case when episode.state='ARCHIVED'then jsonb_build_object('archived_at',episode.archived_at)else'{}'::jsonb end end,'transition',transition);
   insert into cp7_reminder_native.rule_observations values(actor,p_request,r->>'key',episode.id,source->>'source_hash',at,observation);
   observations:=observations||jsonb_build_array(observation);
  end loop;
  -- An excluded domain or absent source is never a zero-balance proof. Old
  -- unseen episodes remain intact and cannot be implicitly closed by this read.
  final_source:=cp7_reminder_native.condition_source((p->>'run_id')::uuid);
  if final_source->>'source_hash'<>source->>'source_hash'then raise exception using errcode='40001',message='CP7_RULE_EPISODE_SOURCE_CHANGED';end if;
  result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','source_hash',source->'source_hash','rows',observations);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 perform cp7_reminder_native.recheck(a);
 -- A new commit already read and fenced the complete current Native source.
 -- Reuse that final read; cached/negative outcomes still read fresh facts.
 if final_source is not null then source:=final_source;
 else source:=cp7_reminder_native.condition_source((p->>'run_id')::uuid);end if;
 -- Cached observation is visible only when its domain still appears in the
 -- caller's current authorized source. Source-changed results remain history,
 -- never current business resolution or a delivery permission.
 if exists(select 1 from jsonb_array_elements(result->'rows')x where not cp7_reminder_native.condition_domain_access(cp7_reminder_native.condition_domain(x->'condition'->>'key')))then raise exception using errcode='42501',message='CP7_RULE_EPISODE_DOMAIN_DENIED';end if;
 return jsonb_build_object('contract_version','cp7.native-rule-observations.v2','actor_scope_id',actor,'source',source,'result',result,
  'result_freshness',case when result->>'source_hash'=source->>'source_hash'then'CURRENT_SOURCE'else'HISTORICAL_SOURCE_CHANGED'end,
  'external_delivery_enabled',false,'business_DML',false);
end $$;

alter function cp7_reminder_native.guard_rule_episode()owner to cp7_reminder;
alter function cp7_reminder_native.rule_episode_evaluate(jsonb,uuid,boolean)owner to cp7_reminder;
revoke all on function cp7_reminder_native.guard_rule_episode(),cp7_reminder_native.rule_episode_evaluate(jsonb,uuid,boolean)from public,anon,authenticated,service_role;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_evaluate_rule_episodes_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.rule_episode_evaluate(p_payload,p_request,false)$$;
create function public.erp_cp7_get_rule_episode_request_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.rule_episode_evaluate(p_payload,p_request,true)$$;
alter function public.erp_cp7_evaluate_rule_episodes_v1(jsonb,uuid)owner to cp7_reminder;
alter function public.erp_cp7_get_rule_episode_request_v1(jsonb,uuid)owner to cp7_reminder;
revoke create on schema public from cp7_reminder;
revoke all on function public.erp_cp7_evaluate_rule_episodes_v1(jsonb,uuid),public.erp_cp7_get_rule_episode_request_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_evaluate_rule_episodes_v1(jsonb,uuid),public.erp_cp7_get_rule_episode_request_v1(jsonb,uuid)to authenticated;
