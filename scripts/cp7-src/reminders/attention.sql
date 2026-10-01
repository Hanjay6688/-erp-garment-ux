-- Attention and native own-user manual tasks are separate from business state.
-- This role can delegate only to accepted reminder writers; no stock/money/HPP
-- writer, direct business DML, external transport or automatic closure is added.
create role cp7_reminder nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_reminder_native authorization cp7_reminder;
revoke all on schema cp7_reminder_native from public,anon,authenticated,service_role;
grant usage on schema erp,auth,public to cp7_reminder;
grant select on erp.manual_reminders to cp7_reminder;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text),
 public.erp_cp7_read_analysis_v1(uuid),public.erp_list_my_reminders_v1(text,integer),
 public.erp_save_my_reminder_v1(jsonb,uuid,bigint),public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint),
 public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)to cp7_reminder;

create table cp7_reminder_native.attention(actor uuid not null,run_id uuid not null,action_key text not null,
 source_hash text not null,semantic_hash text not null,state text not null check(state in('NEW','ACK','SNOOZED','DONE')),
 resume_at timestamptz,native_reminder_id uuid,revision bigint not null check(revision>0),
 created_at timestamptz not null,updated_at timestamptz not null,
 primary key(actor,run_id,action_key),check((state='SNOOZED')=(resume_at is not null)));
create table cp7_reminder_native.requests(actor uuid not null,request_id uuid not null,payload jsonb not null,
 result jsonb not null,created_at timestamptz not null,primary key(actor,request_id));
alter table cp7_reminder_native.attention owner to cp7_reminder;
alter table cp7_reminder_native.requests owner to cp7_reminder;
alter table cp7_reminder_native.attention enable row level security;
alter table cp7_reminder_native.requests enable row level security;
create policy reminder_attention_no_access on cp7_reminder_native.attention for all to public using(false)with check(false);
create policy reminder_request_no_access on cp7_reminder_native.requests for all to public using(false)with check(false);
revoke all on all tables in schema cp7_reminder_native from public,anon,authenticated,service_role;

create function cp7_reminder_native.immutable_request()returns trigger
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin raise exception using errcode='55000',message='CP7_REMINDER_REQUEST_IMMUTABLE';end $$;
create function cp7_reminder_native.guard_attention()returns trigger
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'then raise exception using errcode='55000',message='CP7_REMINDER_BINDING_IMMUTABLE';end if;
 if(new.actor,new.run_id,new.action_key,new.source_hash,new.semantic_hash,new.created_at)
  is distinct from(old.actor,old.run_id,old.action_key,old.source_hash,old.semantic_hash,old.created_at)then
  raise exception using errcode='55000',message='CP7_REMINDER_BINDING_IMMUTABLE';end if;
 return new;
end $$;
create function cp7_reminder_native.request_status(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare run_id uuid:=(p->>'run_id')::uuid;a jsonb;cached cp7_reminder_native.requests%rowtype;outcome jsonb;
begin
 a:=cp7_reminder_native.access_now(run_id);if p_request is null then raise exception 'CP7_REMINDER_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||auth.uid()::text||':'||p_request::text,0));
 if erp.get_my_access_v1()is distinct from a->'access'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 select *into cached from cp7_reminder_native.requests where actor=auth.uid()and request_id=p_request;
 if found then
  if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;outcome:=cached.result;
 else
  if jsonb_typeof(p)is distinct from 'object'or not p?&array['run_id','action_key','action','details','expected_revision']
   or exists(select 1 from jsonb_object_keys(p)k where k not in('run_id','action_key','action','details','expected_revision'))
   or exists(select 1 from jsonb_each(p)e where e.key<>'details'and jsonb_typeof(e.value)<>'string')
   or jsonb_typeof(p->'details')is distinct from 'object'or(p->>'expected_revision')!~'^(0|[1-9][0-9]{0,18})$'
   or(p->>'action')not in('ACK','DONE','NEW','SNOOZE','SCHEDULE','CANCEL_SCHEDULE')
   or not exists(select 1 from jsonb_array_elements(a->'analysis'->'analysis'->'actions')x where x->>'key'=p->>'action_key')
   or exists(select 1 from jsonb_object_keys(p->'details')k where k not in('title','note','due_at','priority','resume_at','reason','expected_native_revision'))
   or exists(select 1 from jsonb_each(p->'details')e where jsonb_typeof(e.value)not in('string','null'))then raise exception 'CP7_REMINDER_PAYLOAD';end if;
  outcome:=jsonb_build_object('request_id',p_request,'run_id',run_id,'action_key',p->>'action_key','revision',null,'status','NOT_COMMITTED');
  -- Seal this absent intent while holding its request lock. A delayed original
  -- command must replay this immutable refusal after resolution; it cannot
  -- arrive later and create a task after the client has retired the intent.
  insert into cp7_reminder_native.requests values(auth.uid(),p_request,p,outcome,statement_timestamp());
 end if;
 return cp7_reminder_native.workspace(run_id)||jsonb_build_object('request_result',outcome);
end $$;
create trigger reminder_request_immutable before update or delete on cp7_reminder_native.requests for each row execute function cp7_reminder_native.immutable_request();
create trigger reminder_attention_binding before update or delete on cp7_reminder_native.attention for each row execute function cp7_reminder_native.guard_attention();
create function cp7_reminder_native.exact_numbers(p jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare r jsonb;
begin
 case jsonb_typeof(p)when 'number'then return to_jsonb(p::text);
 when 'object'then select coalesce(jsonb_object_agg(k,cp7_reminder_native.exact_numbers(v)),'{}')into r from jsonb_each(p)e(k,v);return r;
 when 'array'then select coalesce(jsonb_agg(cp7_reminder_native.exact_numbers(v)order by n),'[]')into r from jsonb_array_elements(p)with ordinality e(v,n);return r;
 else return p;end case;
end $$;
create function cp7_reminder_native.access_now(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;k text;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();if a->'allowed'is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_DENIED';end if;
 foreach k in array array['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']loop
  if not erp.has_permission(k)then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_DENIED';end if;
 end loop;
 -- This preserves current actor and all original financial-source capabilities
 -- before any saved attention or command replay can become visible.
 r:=public.erp_cp7_read_analysis_v1(p_run);
 return jsonb_build_object('access',a,'analysis',r);
end $$;
create function cp7_reminder_native.workspace(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb:=cp7_reminder_native.access_now(p_run);manual jsonb;rows jsonb;
begin
 manual:=cp7_reminder_native.manual_source(p_run);
 if exists(select 1 from cp7_reminder_native.attention t where t.actor=auth.uid()and t.run_id=p_run and t.native_reminder_id is not null
  and not exists(select 1 from jsonb_array_elements(manual->'items')x where x->>'id'=t.native_reminder_id::text))then raise exception 'CP7_REMINDER_NATIVE_BINDING_UNAVAILABLE';end if;
 select coalesce(jsonb_agg(jsonb_build_object('action_key',x->>'key',
  'condition',case when a->'analysis'->>'source_state'='ARCHIVED_STALE'then 'SOURCE_CHANGED'else 'REVIEW_REQUIRED'end,
  'attention',jsonb_build_object('state',coalesce(t.state,'NEW'),'resume_at',t.resume_at,'revision',coalesce(t.revision,0)::text,
   'updated_at',t.updated_at,'resume_due',coalesce(t.state='SNOOZED'and t.resume_at<=statement_timestamp(),false)),
  'manual',case when t.native_reminder_id is null then null else(select m from jsonb_array_elements(manual->'items')m where m->>'id'=t.native_reminder_id::text)end,
  'business_resolved',false)order by x->>'key'),'[]')into rows
 from jsonb_array_elements(a->'analysis'->'analysis'->'actions')x left join cp7_reminder_native.attention t
  on t.actor=auth.uid()and t.run_id=p_run and t.action_key=x->>'key';
 if erp.get_my_access_v1()is distinct from a->'access'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.analysis-attention.v1','analysis',a->'analysis','rows',rows,
  'read_at',statement_timestamp(),'native_manual_page_complete',true,'delivery',jsonb_build_object('status','NOT_CONFIGURED','sent',false));
end $$;
create function cp7_reminder_native.command(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare run_id uuid;key text;action text;details jsonb;expected bigint;actor uuid:=auth.uid();a jsonb;again jsonb;
 t cp7_reminder_native.attention%rowtype;cached cp7_reminder_native.requests%rowtype;state text;resume timestamptz;
 manual jsonb;native jsonb;native_id uuid;native_version bigint;expected_native bigint;response jsonb;
begin
 if jsonb_typeof(p)is distinct from 'object'or not p?&array['run_id','action_key','action','details','expected_revision']
  or exists(select 1 from jsonb_object_keys(p)k where k not in('run_id','action_key','action','details','expected_revision'))
  or exists(select 1 from jsonb_each(p)e where e.key<>'details'and jsonb_typeof(e.value)<>'string')
  or jsonb_typeof(p->'details')is distinct from 'object'or(p->>'expected_revision')!~'^(0|[1-9][0-9]{0,18})$'
  or p_request is null then raise exception 'CP7_REMINDER_PAYLOAD';end if;
 run_id:=(p->>'run_id')::uuid;key:=p->>'action_key';action:=p->>'action';details:=p->'details';expected:=(p->>'expected_revision')::bigint;
 if action not in('ACK','DONE','NEW','SNOOZE','SCHEDULE','CANCEL_SCHEDULE')or key=''then raise exception 'CP7_REMINDER_ACTION';end if;
 if exists(select 1 from jsonb_object_keys(details)k where k not in('title','note','due_at','priority','resume_at','reason','expected_native_revision'))
  or exists(select 1 from jsonb_each(details)e where jsonb_typeof(e.value)not in('string','null'))then raise exception 'CP7_REMINDER_DETAILS';end if;
 a:=cp7_reminder_native.access_now(run_id);
 if not exists(select 1 from jsonb_array_elements(a->'analysis'->'analysis'->'actions')x where x->>'key'=key)then raise exception 'CP7_REMINDER_ACTION_UNAVAILABLE';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));
 again:=cp7_reminder_native.access_now(run_id);if again->'access'is distinct from a->'access'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 select *into cached from cp7_reminder_native.requests where requests.actor=actor and request_id=p_request;
 if found then if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;return cp7_reminder_native.workspace(run_id)||jsonb_build_object('request_result',cached.result);end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_ATTENTION:'||actor::text||':'||run_id::text||':'||key,0));
 again:=cp7_reminder_native.access_now(run_id);if again->'access'is distinct from a->'access'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 select *into t from cp7_reminder_native.attention q where q.actor=actor and q.run_id=run_id and q.action_key=key for update;
 if coalesce(t.revision,0)<>expected then raise exception 'CP7_REMINDER_STALE_REVISION';end if;
 state:=coalesce(t.state,'NEW');resume:=t.resume_at;native_id:=t.native_reminder_id;
 if native_id is not null then
  manual:=cp7_reminder_native.manual_source(run_id);
  native:=(select x from jsonb_array_elements(manual->'items')x where x->>'id'=native_id::text);
  if native is null then raise exception 'CP7_REMINDER_NATIVE_BINDING_UNAVAILABLE';end if;
  if coalesce(details->>'expected_native_revision','')!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_REMINDER_NATIVE_REVISION_REQUIRED';end if;
  native_version:=(native->>'row_version')::bigint;expected_native:=(details->>'expected_native_revision')::bigint;
  if native_version<>expected_native then raise exception 'CP7_REMINDER_NATIVE_STALE_REVISION';end if;
 end if;
 if action in('ACK','DONE','NEW')then
  state:=action;
  if native_id is not null and action in('DONE','NEW')then perform public.erp_set_my_reminder_done_v1(native_id,action='DONE',p_request,native_version);end if;
 elsif action='SNOOZE'then
  if coalesce(details->>'resume_at','')!~'^\d{4}-\d{2}-\d{2}T.*(Z|[+-]\d{2}:\d{2})$'then raise exception 'CP7_REMINDER_RESUME_REQUIRED';end if;
  resume:=(details->>'resume_at')::timestamptz;if not isfinite(resume)or resume<=clock_timestamp()then raise exception 'CP7_REMINDER_RESUME_FUTURE_REQUIRED';end if;
  state:='SNOOZED';
  if native_id is not null then
   if native->>'status'<>'OPEN'then raise exception 'CP7_REMINDER_NATIVE_OPEN_REQUIRED';end if;
   perform public.erp_save_my_reminder_v1(jsonb_build_object('id',native_id,'title',native->>'title','note',native->>'note','due_at',resume,'priority',native->>'priority','module',native->>'module'),p_request,native_version);
  end if;
 elsif action='SCHEDULE'then
  if coalesce(details->>'due_at','')!~'^\d{4}-\d{2}-\d{2}T.*(Z|[+-]\d{2}:\d{2})$'then raise exception 'CP7_REMINDER_DUE_REQUIRED';end if;
  if native_id is not null and native->>'status'='DONE'then
   response:=public.erp_set_my_reminder_done_v1(native_id,false,p_request,native_version);native_version:=(response->>'row_version')::bigint;
  elsif native_id is not null and native->>'status'='CANCELLED'then native_id:=null;native_version:=null;end if;
  response:=public.erp_save_my_reminder_v1(jsonb_build_object('id',native_id,'title',details->>'title','note',coalesce(details->>'note',''),
   'due_at',details->>'due_at','priority',details->>'priority','module','Perencanaan CP7'),p_request,native_version);
  native_id:=(response->'reminder'->>'id')::uuid;state:='NEW';
 elsif action='CANCEL_SCHEDULE'then
  if native_id is null then raise exception 'CP7_REMINDER_NATIVE_BINDING_UNAVAILABLE';end if;
  perform public.erp_cancel_my_reminder_v1(native_id,details->>'reason',p_request,native_version);
 end if;
 if state<>'SNOOZED'then resume:=null;end if;
 insert into cp7_reminder_native.attention(actor,run_id,action_key,source_hash,semantic_hash,state,resume_at,native_reminder_id,revision,created_at,updated_at)
 values(actor,run_id,key,a->'analysis'->'analysis'->'snapshot'->>'source_hash',a->'analysis'->'analysis'->>'semantic_hash',state,resume,native_id,expected+1,statement_timestamp(),statement_timestamp())
 on conflict on constraint attention_pkey do update set state=excluded.state,resume_at=excluded.resume_at,native_reminder_id=excluded.native_reminder_id,revision=excluded.revision,updated_at=excluded.updated_at;
 again:=cp7_reminder_native.access_now(run_id);if again->'access'is distinct from a->'access'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 response:=jsonb_build_object('request_id',p_request,'run_id',run_id,'action_key',key,'revision',(expected+1)::text,'status','COMMITTED');
 insert into cp7_reminder_native.requests values(actor,p_request,p,response,statement_timestamp());
 return cp7_reminder_native.workspace(run_id)||jsonb_build_object('request_result',response);
end $$;
create function cp7_reminder_native.manual_source(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb:=cp7_reminder_native.access_now(p_run);items jsonb;expected bigint;
begin
 -- Run the unchanged Native own-user guard, then read only linked own rows.
 -- Native's200-row management page must not truncate this source merely
 -- because the same user has unrelated manual tasks elsewhere in the ERP.
 perform public.erp_list_my_reminders_v1('ALL',1);
 select coalesce(jsonb_agg(jsonb_build_object('id',r.id,'title',r.title,'note',r.note,'due_at',r.due_at,
  'priority',r.priority,'module',r.module,'status',r.status,'completed_at',r.completed_at,
  'cancelled_at',r.cancelled_at,'cancellation_reason',r.cancellation_reason,
  'created_at',r.created_at,'updated_at',r.updated_at,'row_version',r.row_version::text)order by r.id),'[]')into items
 from erp.manual_reminders r join cp7_reminder_native.attention t on t.native_reminder_id=r.id
 where t.actor=auth.uid()and t.run_id=p_run and r.owner_user_id=(a->'access'->'profile'->>'id')::uuid;
 select count(*)into expected from cp7_reminder_native.attention where actor=auth.uid()and run_id=p_run and native_reminder_id is not null;
 if expected<>jsonb_array_length(items)then raise exception 'CP7_REMINDER_NATIVE_BINDING_UNAVAILABLE';end if;
 return jsonb_build_object('items',items);
end $$;
alter function cp7_reminder_native.immutable_request()owner to cp7_reminder;
alter function cp7_reminder_native.guard_attention()owner to cp7_reminder;
alter function cp7_reminder_native.exact_numbers(jsonb)owner to cp7_reminder;
alter function cp7_reminder_native.access_now(uuid)owner to cp7_reminder;
alter function cp7_reminder_native.workspace(uuid)owner to cp7_reminder;
alter function cp7_reminder_native.command(jsonb,uuid)owner to cp7_reminder;
alter function cp7_reminder_native.manual_source(uuid)owner to cp7_reminder;
alter function cp7_reminder_native.request_status(jsonb,uuid)owner to cp7_reminder;
revoke all on all functions in schema cp7_reminder_native from public,anon,authenticated,service_role;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_get_analysis_attention_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.workspace(p_run)$$;
create function public.erp_cp7_save_analysis_attention_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.command(p_payload,p_request)$$;
create function public.erp_cp7_get_analysis_attention_request_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.request_status(p_payload,p_request)$$;
alter function public.erp_cp7_get_analysis_attention_v1(uuid)owner to cp7_reminder;
alter function public.erp_cp7_save_analysis_attention_v1(jsonb,uuid)owner to cp7_reminder;
alter function public.erp_cp7_get_analysis_attention_request_v1(jsonb,uuid)owner to cp7_reminder;
revoke create on schema public from cp7_reminder;
revoke all on function public.erp_cp7_get_analysis_attention_v1(uuid),public.erp_cp7_save_analysis_attention_v1(jsonb,uuid),public.erp_cp7_get_analysis_attention_request_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_analysis_attention_v1(uuid),public.erp_cp7_save_analysis_attention_v1(jsonb,uuid),public.erp_cp7_get_analysis_attention_request_v1(jsonb,uuid)to authenticated;
