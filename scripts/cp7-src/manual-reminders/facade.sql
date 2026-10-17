-- R3-03 (owner D16-1, "selesain biar gausa sembunyiin"): the Reminder menu (admin-reminders) on real data.
-- A thin facade over the accepted Native own-user manual reminders (supabase/migrations/
-- 20260830190955_erp_v2_6_13_manual_reminders_v1.sql, table erp.manual_reminders). It adds what Native does not check:
-- the access catalog keys settings.reminder.view (read) and settings.reminder.manage (write). Everything else stays
-- Native: the own-user scope, the OWNER/ADMIN/STAFF actor rule (erp.require_manual_reminder_actor), request idempotency,
-- optimistic locking (STALE_VERSION), no delete, cancel only with a reason, cancelled is terminal, audit rows.
-- This schema holds no table and writes no row itself: every write is one call of a Native writer with the same client
-- request id and expected version the screen sent, so a resend gives the Native cached answer and the same outcome.
-- The only extra read of Native state is erp.idempotency_requests, to refuse a request id that was already used for
-- another reminder action (Native keys its cache per operation, so SAVE and CANCEL with one id would both run).
-- Refusals: 42501 CP7_REMINDERS_DENIED (no key), 42501 CP7_REMINDERS_ROLE_DENIED (refused by the Native actor rule),
-- 42501 CP7_REMINDERS_ACCESS_CHANGED, P0001 CP7_REMINDERS_STALE / _NOT_FOUND (also another user's reminder) / _NOT_OPEN /
-- _CANCELLED / _REQUEST_CHANGED / _FIELDS / _QUERY / _SOURCE.
create role cp7_reminders_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create role cp7_reminders_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_reminders authorization cp7_reminders_read;
revoke all on schema cp7_reminders from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_reminders to postgres,cp7_reminders_write;

-- The catalog keys of the menu, on the current access row. Read needs the view key; a write needs view and manage.
create function cp7_reminders.access(p_manage boolean)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare v_access jsonb;
begin
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_REMINDERS_DENIED';end if;
 v_access:=erp.get_my_access_v1();
 if v_access->'allowed'is distinct from'true'::jsonb or not erp.has_permission('settings.reminder.view')
  or(p_manage and not erp.has_permission('settings.reminder.manage'))then
  raise exception using errcode='42501',message='CP7_REMINDERS_DENIED';end if;
 return v_access;
end $$;

-- The Native own-user list (its full 200-row window, its own order). A role the Native actor rule refuses stays refused.
create function cp7_reminders.native_list(p_filter text)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare v_list jsonb;v_message text;
begin
 begin
  v_list:=public.erp_list_my_reminders_v1(p_filter,200);
 exception when others then
  get stacked diagnostics v_message=message_text;
  if v_message in('Mapped active internal ERP user required','Internal ERP access required')then
   raise exception using errcode='42501',message='CP7_REMINDERS_ROLE_DENIED';end if;
  raise;
 end;
 if jsonb_typeof(v_list)is distinct from'object'or jsonb_typeof(v_list->'items')is distinct from'array'
  or jsonb_typeof(v_list->'counts')is distinct from'object'
  or exists(select 1 from unnest(array['open','done','cancelled'])c(k)
   where jsonb_typeof(v_list->'counts'->c.k)is distinct from'number'or(v_list->'counts'->>c.k)!~'^[0-9]{1,9}$')then
  raise exception 'CP7_REMINDERS_SOURCE';end if;
 return v_list;
end $$;

-- One Native writer call; the Native refusals are given their CP7 names (the Native transaction part is rolled back).
create function cp7_reminders.native_write(p_action text,p_id uuid,p_payload jsonb,p_request uuid,p_expected bigint)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare v_native jsonb;v_message text;
begin
 begin
  if p_action='SAVE'then v_native:=public.erp_save_my_reminder_v1(p_payload,p_request,p_expected);
  elsif p_action in('DONE','UNDONE')then v_native:=public.erp_set_my_reminder_done_v1(p_id,p_action='DONE',p_request,p_expected);
  elsif p_action='CANCEL'then v_native:=public.erp_cancel_my_reminder_v1(p_id,p_payload->>'reason',p_request,p_expected);
  else raise exception 'CP7_REMINDERS_FIELDS';end if;
 exception when others then
  get stacked diagnostics v_message=message_text;
  if v_message in('Mapped active internal ERP user required','Internal ERP access required')then
   raise exception using errcode='42501',message='CP7_REMINDERS_ROLE_DENIED';
  elsif v_message like'STALE\_VERSION %'then raise exception 'CP7_REMINDERS_STALE';
  elsif v_message='Reminder not found'then raise exception 'CP7_REMINDERS_NOT_FOUND';
  elsif v_message like'client\_request\_id was already used with a different payload%'then raise exception 'CP7_REMINDERS_REQUEST_CHANGED';
  elsif v_message like'Only OPEN reminders can be edited%'then raise exception 'CP7_REMINDERS_NOT_OPEN';
  elsif v_message='Cancelled reminders are terminal'then raise exception 'CP7_REMINDERS_CANCELLED';
  end if;
  raise;
 end;
 return v_native;
end $$;

-- The reminder list of the signed-in user: one filter, a page of at most 100 inside the Native 200-row window, the Native
-- counts, and for every OPEN reminder its WIB due state (OVERDUE when due_at <= now, else TODAY/TOMORROW/LATER by the WIB
-- date). One snapshot (stable): the page, the counts and the open list agree.
create function cp7_reminders.workspace(p_query jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare v_filter text;v_limit integer;v_offset integer;v_list jsonb;v_open jsonb;v_now timestamptz:=statement_timestamp();
 v_today date;v_total integer;v_window integer;v_items jsonb;v_due jsonb;v_counts jsonb;
begin
 perform cp7_reminders.access(false);
 if jsonb_typeof(p_query)is distinct from'object'
  or exists(select 1 from jsonb_object_keys(p_query)q(k)where q.k not in('filter','limit','offset'))
  or(p_query?'filter'and(jsonb_typeof(p_query->'filter')<>'string'or p_query->>'filter'not in('ACTIVE','OPEN','DONE','CANCELLED','ALL')))
  or(p_query?'limit'and(jsonb_typeof(p_query->'limit')<>'number'or(p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query?'offset'and(jsonb_typeof(p_query->'offset')<>'number'or(p_query->>'offset')!~'^[0-9]{1,3}$'))then
  raise exception 'CP7_REMINDERS_QUERY';end if;
 v_filter:=coalesce(p_query->>'filter','ACTIVE');
 v_limit:=coalesce((p_query->>'limit')::integer,50);
 v_offset:=coalesce((p_query->>'offset')::integer,0);
 if v_limit not between 1 and 100 or v_offset not between 0 and 199 then raise exception 'CP7_REMINDERS_QUERY';end if;
 v_list:=cp7_reminders.native_list(v_filter);
 v_open:=case when v_filter='OPEN'then v_list else cp7_reminders.native_list('OPEN')end;
 v_counts:=v_list->'counts';
 v_total:=case v_filter when'ACTIVE'then(v_counts->>'open')::integer+(v_counts->>'done')::integer
  when'OPEN'then(v_counts->>'open')::integer when'DONE'then(v_counts->>'done')::integer
  when'CANCELLED'then(v_counts->>'cancelled')::integer
  else(v_counts->>'open')::integer+(v_counts->>'done')::integer+(v_counts->>'cancelled')::integer end;
 v_window:=jsonb_array_length(v_list->'items');
 if v_window<>least(v_total,200)or v_open->'counts'is distinct from v_counts
  or jsonb_array_length(v_open->'items')<>least((v_counts->>'open')::integer,200)then raise exception 'CP7_REMINDERS_SOURCE';end if;
 v_today:=(v_now at time zone'Asia/Jakarta')::date;
 select coalesce(jsonb_agg(e.item||jsonb_build_object('due_state',case
   when e.item->>'status'<>'OPEN'then null
   when(e.item->>'due_at')::timestamptz<=v_now then'OVERDUE'
   when((e.item->>'due_at')::timestamptz at time zone'Asia/Jakarta')::date=v_today then'TODAY'
   when((e.item->>'due_at')::timestamptz at time zone'Asia/Jakarta')::date=v_today+1 then'TOMORROW'
   else'LATER'end)order by e.n),'[]'::jsonb)
  into v_items from jsonb_array_elements(v_list->'items')with ordinality e(item,n)where e.n>v_offset and e.n<=v_offset+v_limit;
 select jsonb_build_object(
   'overdue',count(*)filter(where(o.item->>'due_at')::timestamptz<=v_now),
   'today',count(*)filter(where(o.item->>'due_at')::timestamptz>v_now
    and((o.item->>'due_at')::timestamptz at time zone'Asia/Jakarta')::date=v_today),
   'tomorrow',count(*)filter(where((o.item->>'due_at')::timestamptz at time zone'Asia/Jakarta')::date=v_today+1
    and(o.item->>'due_at')::timestamptz>v_now),
   'complete',(v_counts->>'open')::integer<=200)
  into v_due from jsonb_array_elements(v_open->'items')o(item);
 return jsonb_build_object('contract_version','cp7.reminders-workspace.v1','filter',v_filter,
  'page',jsonb_build_object('limit',v_limit,'offset',v_offset,'total',v_total,'shown',jsonb_array_length(v_items),'window',v_window,
   'window_limit',200,'next_offset',case when v_offset+v_limit<v_window then v_offset+v_limit end,'beyond_window',v_total-v_window),
  'items',v_items,'counts',v_counts,'due',v_due,'today',v_today,'read_at',v_list->'read_at',
  'can_manage',erp.has_permission('settings.reminder.manage'),'business_DML',false);
end $$;

-- SAVE (create when payload id is null, else edit an OPEN reminder), DONE, UNDONE (reopen a DONE one), CANCEL (with a
-- reason, terminal). p_expected is the row_version the screen read (null only for a create). The Native writer gets the
-- same request id and expected version; its cached answer on a resend gives this same outcome.
create function cp7_reminders.command(p_action text,p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare v_access jsonb;v_keys text[];v_id uuid;v_expected bigint;v_due timestamptz;v_operation text;v_actor text;
 v_native jsonb;v_answer jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 v_access:=cp7_reminders.access(true);
 if p_request is null or p_action is null or p_action not in('SAVE','DONE','UNDONE','CANCEL')
  or jsonb_typeof(p_payload)is distinct from'object'or(p_expected is not null and p_expected!~'^[1-9][0-9]{0,17}$')then
  raise exception 'CP7_REMINDERS_FIELDS';end if;
 v_keys:=case p_action when'SAVE'then array['id','title','note','due_at','priority','module']
  when'CANCEL'then array['id','reason']else array['id']end;
 if not(p_payload?&v_keys)or exists(select 1 from jsonb_object_keys(p_payload)f(k)where f.k<>all(v_keys))
  or exists(select 1 from jsonb_each(p_payload)g where g.key<>'id'and jsonb_typeof(g.value)<>'string')
  or jsonb_typeof(p_payload->'id')not in('string','null')then raise exception 'CP7_REMINDERS_FIELDS';end if;
 if jsonb_typeof(p_payload->'id')='string'then
  if(p_payload->>'id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'then raise exception 'CP7_REMINDERS_FIELDS';end if;
  v_id:=(p_payload->>'id')::uuid;
 end if;
 -- A create has no id and no expected version; every other command names both.
 if(v_id is null)<>(p_expected is null)or(v_id is null and p_action<>'SAVE')then raise exception 'CP7_REMINDERS_FIELDS';end if;
 v_expected:=p_expected::bigint;
 if p_action='SAVE'then
  if char_length(btrim(p_payload->>'title'))not between 1 and 200 or char_length(p_payload->>'note')>4000
   or char_length(btrim(p_payload->>'module'))not between 1 and 80 or p_payload->>'priority'not in('URGENT','NORMAL','LOW')
   or(p_payload->>'due_at')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]{1,6})?)?(Z|[+-][0-9]{2}:[0-9]{2})$'then
   raise exception 'CP7_REMINDERS_FIELDS';end if;
  begin v_due:=(p_payload->>'due_at')::timestamptz;exception when others then raise exception 'CP7_REMINDERS_FIELDS';end;
  if not isfinite(v_due)then raise exception 'CP7_REMINDERS_FIELDS';end if;
 elsif p_action='CANCEL'and char_length(btrim(p_payload->>'reason'))not between 5 and 1000 then raise exception 'CP7_REMINDERS_FIELDS';
 end if;
 -- One request id is one reminder action: the Native cache is per writer, so the same id for another writer is refused.
 v_operation:=case p_action when'SAVE'then'save_my_reminder_v1'when'CANCEL'then'cancel_my_reminder_v1'else'set_my_reminder_done_v1'end;
 v_actor:=erp._idempotency_actor_key();
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDERS_REQUEST:'||coalesce(v_actor,'')||':'||p_request::text,0));
 if exists(select 1 from erp.idempotency_requests q where q.actor_key=v_actor and q.client_request_id=p_request
   and q.operation_name in('save_my_reminder_v1','set_my_reminder_done_v1','cancel_my_reminder_v1')and q.operation_name<>v_operation)then
  raise exception 'CP7_REMINDERS_REQUEST_CHANGED';end if;
 if cp7_reminders.access(true)is distinct from v_access then raise exception using errcode='42501',message='CP7_REMINDERS_ACCESS_CHANGED';end if;
 v_native:=cp7_reminders.native_write(p_action,v_id,p_payload,p_request,v_expected);
 v_answer:=case when p_action='SAVE'then jsonb_build_object('reminder_id',v_native->'reminder'->'id','status',v_native->'reminder'->'status',
   'row_version',v_native->'reminder'->'row_version')
  else jsonb_build_object('reminder_id',v_native->'reminder_id','status',v_native->'status','row_version',v_native->'row_version')end;
 if v_native->>'client_request_id'is distinct from p_request::text or jsonb_typeof(v_answer->'reminder_id')is distinct from'string'
  or(v_id is not null and v_answer->>'reminder_id'is distinct from v_id::text)
  or v_answer->>'status'is distinct from(case p_action when'DONE'then'DONE'when'CANCEL'then'CANCELLED'else'OPEN'end)
  or jsonb_typeof(v_answer->'row_version')is distinct from'number'or(v_answer->>'row_version')!~'^[1-9][0-9]{0,17}$'
  or(v_answer->>'row_version')::bigint<coalesce(v_expected,1)then raise exception 'CP7_REMINDERS_SOURCE';end if;
 if cp7_reminders.access(true)is distinct from v_access then raise exception using errcode='42501',message='CP7_REMINDERS_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.reminders-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,
  'request_id',p_request,'created',p_action='SAVE'and v_id is null)||v_answer;
end $$;

create function public.erp_cp7_get_reminders_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminders.workspace(p_query)$$;
create function public.erp_cp7_save_reminder_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminders.command(p_action,p_payload,p_request,p_expected)$$;
alter function cp7_reminders.access(boolean)owner to postgres;
alter function cp7_reminders.native_list(text)owner to postgres;
alter function cp7_reminders.native_write(text,uuid,jsonb,uuid,bigint)owner to postgres;
alter function cp7_reminders.workspace(jsonb)owner to postgres;
alter function cp7_reminders.command(text,jsonb,uuid,text)owner to postgres;
grant create on schema public to cp7_reminders_read,cp7_reminders_write;
alter function public.erp_cp7_get_reminders_v1(jsonb)owner to cp7_reminders_read;
alter function public.erp_cp7_save_reminder_v1(text,jsonb,uuid,text)owner to cp7_reminders_write;
revoke create on schema public from cp7_reminders_read,cp7_reminders_write;
revoke all on function cp7_reminders.access(boolean),cp7_reminders.native_list(text),cp7_reminders.native_write(text,uuid,jsonb,uuid,bigint),
 cp7_reminders.workspace(jsonb),cp7_reminders.command(text,jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_reminders_read,cp7_reminders_write;
grant execute on function cp7_reminders.workspace(jsonb)to cp7_reminders_read;
grant execute on function cp7_reminders.command(text,jsonb,uuid,text)to cp7_reminders_write;
revoke all on function public.erp_cp7_get_reminders_v1(jsonb),public.erp_cp7_save_reminder_v1(text,jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_reminders_v1(jsonb),public.erp_cp7_save_reminder_v1(text,jsonb,uuid,text)to authenticated;
