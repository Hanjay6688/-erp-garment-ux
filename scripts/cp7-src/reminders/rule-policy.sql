-- Explicit versioned settings. No defaults, business writes or delivery.
create table cp7_reminder_native.rule_policies(
 id uuid primary key default gen_random_uuid(),rule_id text not null
  check(rule_id in('PRODUCTION_GAP','ACCESSORY_NEED','AR_DUE','AP_DUE')),
 scope_kind text not null check(scope_kind in('GLOBAL','TARGET')),scope_key text not null,
 revision bigint not null check(revision>0),previous_id uuid references cp7_reminder_native.rule_policies(id),
 config jsonb not null,reason text not null,created_at timestamptz not null,created_by uuid not null,
 unique(rule_id,scope_kind,scope_key,revision),
 check((scope_kind='GLOBAL'and scope_key='*')or(scope_kind='TARGET'and rule_id in('PRODUCTION_GAP','ACCESSORY_NEED'))));
alter table cp7_reminder_native.rule_policies owner to cp7_reminder;
alter table cp7_reminder_native.rule_policies enable row level security;
create policy rule_policy_no_access on cp7_reminder_native.rule_policies for all to public using(false)with check(false);
revoke all on cp7_reminder_native.rule_policies from public,anon,authenticated,service_role;
create trigger rule_policy_immutable before update or delete on cp7_reminder_native.rule_policies
 for each row execute function cp7_reminder_native.immutable_request();

create function cp7_reminder_native.policy_validate(rule text,c jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare quiet jsonb:=c->'quiet';unit text:=c->>'threshold_unit';value text:=c->>'threshold_value';cooldown text:=c->>'cooldown_minutes';
begin
 if rule not in('PRODUCTION_GAP','ACCESSORY_NEED','AR_DUE','AP_DUE')
  or jsonb_typeof(c)is distinct from'object'or not(c?&array['enabled','threshold_value','threshold_unit','cooldown_minutes','quiet'])
  or(select count(*)from jsonb_object_keys(c))<>5
  or jsonb_typeof(c->'enabled')not in('boolean','null')
  or jsonb_typeof(c->'threshold_value')not in('string','null')
  or jsonb_typeof(c->'threshold_unit')not in('string','null')
  or jsonb_typeof(c->'cooldown_minutes')not in('string','null')
  or value is not null and(value!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,12})?$'or unit is null)
  or unit is not null and unit!~'^[A-Z][A-Z0-9/_-]{0,23}$'
  or rule='PRODUCTION_GAP'and unit is not null and unit<>'PCS'
  or rule in('AR_DUE','AP_DUE')and(unit is not null and unit<>'DAY'or value is not null and value!~'^(0|[1-9][0-9]{0,5})$')
  or cooldown is not null and(cooldown!~'^(0|[1-9][0-9]{0,5})$'or cooldown::numeric>525600)
  or jsonb_typeof(quiet)is distinct from'object'or not(quiet?&array['enabled','starts_at','ends_at','timezone'])
  or(select count(*)from jsonb_object_keys(quiet))<>4 or quiet->>'timezone'is distinct from'Asia/Jakarta'
  or jsonb_typeof(quiet->'enabled')not in('boolean','null')
  or jsonb_typeof(quiet->'starts_at')not in('string','null')or jsonb_typeof(quiet->'ends_at')not in('string','null')
 then raise exception 'CP7_RULE_POLICY_CONFIG';end if;
 if quiet->'enabled'='true'::jsonb then
  if coalesce(quiet->>'starts_at','')!~'^([01][0-9]|2[0-3]):[0-5][0-9]$'
   or coalesce(quiet->>'ends_at','')!~'^([01][0-9]|2[0-3]):[0-5][0-9]$'
   or quiet->>'starts_at'=quiet->>'ends_at'then raise exception 'CP7_RULE_POLICY_QUIET';end if;
 elsif quiet->>'starts_at'is not null or quiet->>'ends_at'is not null then raise exception 'CP7_RULE_POLICY_QUIET';end if;
 -- Null is not zero and is not disabled. Disabled rules retain their settings.
 return c;
end $$;

create function cp7_reminder_native.policy_scope_access(a jsonb,p jsonb)returns void
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin
 perform cp7_reminder_native.recheck(a,case p->>'rule_id'when'AR_DUE'then'AR'when'AP_DUE'then'MATERIAL_AP'else null end);
 if a->'access'->'profile'->>'role_code'not in('OWNER','ADMIN')or not erp.has_permission('master.product.manage')then
  raise exception using errcode='42501',message='CP7_RULE_POLICY_MANAGE_DENIED';end if;
 if p->>'scope_kind'='GLOBAL'then
  if p->>'scope_key'<>'*'then raise exception 'CP7_RULE_POLICY_SCOPE';end if;
 elsif p->>'scope_kind'='TARGET'and p->>'rule_id'in('PRODUCTION_GAP','ACCESSORY_NEED')then
  if not exists(select 1 from jsonb_array_elements(a->'analysis'->'analysis'->'recommendations')r
   where r->'target'->>'key'=p->>'scope_key')then raise exception using errcode='42501',message='CP7_RULE_POLICY_TARGET_UNAVAILABLE';end if;
 else raise exception 'CP7_RULE_POLICY_SCOPE';end if;
end $$;

create function cp7_reminder_native.policy_rows(a jsonb)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with latest as materialized(
  select distinct on(rule_id,scope_kind,scope_key)*from cp7_reminder_native.rule_policies
  order by rule_id,scope_kind,scope_key,revision desc),visible as(
  select *from latest p where
   (p.rule_id not in('AR_DUE','AP_DUE')or erp.has_permission(case p.rule_id when'AR_DUE'then'finance.ar.view'else'finance.ap.view'end))
   and(p.scope_kind='GLOBAL'or exists(select 1 from jsonb_array_elements(a->'analysis'->'analysis'->'recommendations')r
    where r->'target'->>'key'=p.scope_key)))
 select coalesce(jsonb_agg(jsonb_build_object('policy_id',id,'rule_id',rule_id,'scope_kind',scope_kind,'scope_key',scope_key,
  'revision',revision::text,'previous_id',previous_id,'config',config,'reason',reason,'created_at',created_at,'created_by',created_by)
  order by rule_id,scope_kind,scope_key),'[]'::jsonb)from visible
$$;

create function cp7_reminder_native.policy_workspace(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb:=cp7_reminder_native.access_now(p_run);rows jsonb;again jsonb;allowed jsonb;
begin
 rows:=cp7_reminder_native.policy_rows(a);
 if jsonb_array_length(rows)>4000 then raise exception 'CP7_RULE_POLICY_SCOPE_INCOMPLETE';end if;
 select jsonb_agg(rule order by rule)into allowed from unnest(array['PRODUCTION_GAP','ACCESSORY_NEED','AR_DUE','AP_DUE'])rule
  where rule not in('AR_DUE','AP_DUE')or erp.has_permission(case rule when'AR_DUE'then'finance.ar.view'else'finance.ap.view'end);
 again:=cp7_reminder_native.access_now(p_run);
 if again->'access'is distinct from a->'access'then raise exception using errcode='42501',message='CP7_RULE_POLICY_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-rule-policy-workspace.v1','actor_scope_id',auth.uid(),
  'analysis',again->'analysis','allowed_rules',allowed,'rows',rows,'page_complete',true,'total',jsonb_array_length(rows)::text,
  'source_hash',encode(pg_catalog.sha256(convert_to(rows::text,'UTF8')),'hex'),
  'read_at',clock_timestamp(),'manage_allowed',a->'access'->'profile'->>'role_code'in('OWNER','ADMIN')and erp.has_permission('master.product.manage'),
  'missing_policy','UNCONFIGURED_NOT_ZERO_NOT_DISABLED','external_delivery_enabled',false);
end $$;

create function cp7_reminder_native.policy_resolve(rows jsonb,rule text,target text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare chosen jsonb;basis text;
begin
 select r into chosen from jsonb_array_elements(rows)r where r->>'rule_id'=rule
  and r->>'scope_kind'='TARGET'and r->>'scope_key'=target;
 if chosen is not null then basis:='EXACT_TARGET';else
  select r into chosen from jsonb_array_elements(rows)r where r->>'rule_id'=rule and r->>'scope_kind'='GLOBAL'and r->>'scope_key'='*';
  basis:=case when chosen is null then'MISSING'else'GLOBAL'end;
 end if;
 -- A target config is one explicit version. Its null fields do not silently
 -- inherit pieces of another version; disabling it never enables the global.
 return jsonb_build_object('rule_id',rule,'target_key',target,'basis',basis,'policy',chosen);
end $$;

create function cp7_reminder_native.policy_timing(c jsonb,p_at timestamptz,p_last_local timestamptz)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare state text;next_at timestamptz;quiet_end timestamptz;cooldown_end timestamptz;
 quiet jsonb:=c->'quiet';local_at timestamp:=p_at at time zone'Asia/Jakarta';minute text:=to_char(local_at,'HH24:MI');
 starts text:=quiet->>'starts_at';ends text:=quiet->>'ends_at';inside boolean:=false;next_local timestamp;next_minute text;
begin
 if p_at is null then raise exception 'CP7_RULE_POLICY_CLOCK_REQUIRED';end if;
 if c is null or c->'enabled'='null'::jsonb then state:='UNCONFIGURED';
 elsif c->'enabled'='false'::jsonb then state:='DISABLED';
 elsif c->>'threshold_value'is null or c->>'threshold_unit'is null or c->>'cooldown_minutes'is null
  or quiet->>'enabled'is null then state:='UNCONFIGURED';
 elsif p_last_local>p_at then state:='CLOCK_CONFLICT';
 else
  if quiet->'enabled'='true'::jsonb then
   inside:=case when starts<ends then minute>=starts and minute<ends else minute>=starts or minute<ends end;
   if inside then quiet_end:=((local_at::date+(ends::time))+
    case when starts>ends and minute>=starts then interval'1 day'else interval'0 day'end)at time zone'Asia/Jakarta';end if;
  end if;
  cooldown_end:=p_last_local+(c->>'cooldown_minutes')::integer*interval'1 minute';
  state:=case when inside then'QUIET'when cooldown_end>p_at then'COOLDOWN'else'READY'end;
  if state in('QUIET','COOLDOWN')then
   next_at:=greatest(quiet_end,cooldown_end);
   -- A long cooldown can end inside a *later day's* quiet interval. Return
   -- the first usable local preview instant, not a second unusable wake-up.
   if quiet->'enabled'='true'::jsonb and next_at is not null then
    next_local:=next_at at time zone'Asia/Jakarta';next_minute:=to_char(next_local,'HH24:MI');
    if (case when starts<ends then next_minute>=starts and next_minute<ends else next_minute>=starts or next_minute<ends end) then
     next_at:=((next_local::date+ends::time)+case when starts>ends and next_minute>=starts then interval'1 day'else interval'0 day'end)at time zone'Asia/Jakarta';
    end if;
   end if;
  end if;
 end if;
 return jsonb_build_object('status',state,'ready',state='READY','checked_at',p_at,'next_at',next_at,
  'meaning','LOCAL_PREVIEW_ELIGIBILITY_ONLY_NOT_DELIVERY_OR_BUSINESS_RESOLUTION');
end $$;

create function cp7_reminder_native.policy_command(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare a jsonb;again jsonb;actor uuid:=auth.uid();cached cp7_reminder_native.requests%rowtype;
 old cp7_reminder_native.rule_policies%rowtype;inserted cp7_reminder_native.rule_policies%rowtype;result jsonb;expected bigint;
begin
 if p_request is null or p_lookup is null or jsonb_typeof(p)is distinct from'object'
  or not(p?&array['run_id','rule_id','scope_kind','scope_key','expected_revision','config','reason'])
  or(select count(*)from jsonb_object_keys(p))<>7
  or exists(select 1 from jsonb_each(p)e where e.key<>'config'and jsonb_typeof(e.value)<>'string')
  or p->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'or(p->>'expected_revision')::numeric>9223372036854775806
  or btrim(p->>'reason')=''or length(p->>'reason')>1000 then raise exception 'CP7_RULE_POLICY_PAYLOAD';end if;
 perform cp7_reminder_native.policy_validate(p->>'rule_id',p->'config');expected:=(p->>'expected_revision')::bigint;
 a:=cp7_reminder_native.access_now((p->>'run_id')::uuid);perform cp7_reminder_native.policy_scope_access(a,p);
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));
 perform cp7_reminder_native.policy_scope_access(a,p);
 select *into cached from cp7_reminder_native.requests r where r.actor=actor and r.request_id=p_request;
 if found then
  if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then
  result:=jsonb_build_object('request_id',p_request,'run_id',p->'run_id','rule_id',p->'rule_id','scope_kind',p->'scope_kind',
   'scope_key',p->'scope_key','status','NOT_COMMITTED','policy_id',null,'revision',null);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:RULE_POLICY:'||(p->>'rule_id')||':'||(p->>'scope_kind')||':'||(p->>'scope_key'),0));
  perform cp7_reminder_native.policy_scope_access(a,p);
  again:=cp7_reminder_native.access_now((p->>'run_id')::uuid);
  if again->'access'is distinct from a->'access'then raise exception using errcode='42501',message='CP7_RULE_POLICY_ACCESS_CHANGED';end if;
  if again->'analysis'->>'source_state'<>'UNCHANGED'then raise exception using errcode='40001',message='CP7_RULE_POLICY_SOURCE_CHANGED';end if;
  select *into old from cp7_reminder_native.rule_policies r where r.rule_id=p->>'rule_id'and r.scope_kind=p->>'scope_kind'
   and r.scope_key=p->>'scope_key'order by r.revision desc limit 1;
  if coalesce(old.revision,0)<>expected then raise exception using errcode='40001',message='CP7_RULE_POLICY_STALE_REVISION';end if;
  insert into cp7_reminder_native.rule_policies(rule_id,scope_kind,scope_key,revision,previous_id,config,reason,created_at,created_by)
   values(p->>'rule_id',p->>'scope_kind',p->>'scope_key',expected+1,old.id,p->'config',p->>'reason',clock_timestamp(),actor)returning *into inserted;
  result:=jsonb_build_object('request_id',p_request,'run_id',p->'run_id','rule_id',p->'rule_id','scope_kind',p->'scope_kind',
   'scope_key',p->'scope_key','status','COMMITTED','policy_id',inserted.id,'revision',inserted.revision::text);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 perform cp7_reminder_native.policy_scope_access(a,p);
 again:=cp7_reminder_native.policy_workspace((p->>'run_id')::uuid);
 if again->'analysis'->>'source_state'<>'UNCHANGED'and result->>'status'='COMMITTED'and cached.actor is null then
  raise exception using errcode='40001',message='CP7_RULE_POLICY_SOURCE_CHANGED';end if;
 return again||jsonb_build_object('request_result',result);
end $$;

alter function cp7_reminder_native.policy_validate(text,jsonb)owner to cp7_reminder;
alter function cp7_reminder_native.policy_scope_access(jsonb,jsonb)owner to cp7_reminder;
alter function cp7_reminder_native.policy_rows(jsonb)owner to cp7_reminder;
alter function cp7_reminder_native.policy_workspace(uuid)owner to cp7_reminder;
alter function cp7_reminder_native.policy_resolve(jsonb,text,text)owner to cp7_reminder;
alter function cp7_reminder_native.policy_timing(jsonb,timestamptz,timestamptz)owner to cp7_reminder;
alter function cp7_reminder_native.policy_command(jsonb,uuid,boolean)owner to cp7_reminder;
revoke all on function cp7_reminder_native.policy_validate(text,jsonb),cp7_reminder_native.policy_scope_access(jsonb,jsonb),
 cp7_reminder_native.policy_rows(jsonb),cp7_reminder_native.policy_workspace(uuid),cp7_reminder_native.policy_resolve(jsonb,text,text),
 cp7_reminder_native.policy_timing(jsonb,timestamptz,timestamptz),cp7_reminder_native.policy_command(jsonb,uuid,boolean)
 from public,anon,authenticated,service_role;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_get_reminder_policy_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.policy_workspace(p_run)$$;
create function public.erp_cp7_save_reminder_policy_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.policy_command(p_payload,p_request,false)$$;
create function public.erp_cp7_get_reminder_policy_request_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.policy_command(p_payload,p_request,true)$$;
alter function public.erp_cp7_get_reminder_policy_v1(uuid)owner to cp7_reminder;
alter function public.erp_cp7_save_reminder_policy_v1(jsonb,uuid)owner to cp7_reminder;
alter function public.erp_cp7_get_reminder_policy_request_v1(jsonb,uuid)owner to cp7_reminder;
revoke create on schema public from cp7_reminder;
revoke all on function public.erp_cp7_get_reminder_policy_v1(uuid),public.erp_cp7_save_reminder_policy_v1(jsonb,uuid),
 public.erp_cp7_get_reminder_policy_request_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_reminder_policy_v1(uuid),public.erp_cp7_save_reminder_policy_v1(jsonb,uuid),
 public.erp_cp7_get_reminder_policy_request_v1(jsonb,uuid)to authenticated;
