-- Prepared owner date-confirmation facade, installed only by its gated stage.
-- Changes no category setting, stock, HPP, journal, payroll or pickup note.
create role cp7_good_policy_date nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;

create table cp7_accessory_nonpayable.date_requests_v1(
  request_id uuid primary key,
  actor_id uuid not null references erp.app_users(id),
  request_body jsonb not null,
  response jsonb not null,
  recorded_at timestamptz not null default statement_timestamp()
);
alter table cp7_accessory_nonpayable.date_requests_v1 owner to postgres;
alter table cp7_accessory_nonpayable.date_requests_v1 enable row level security;
revoke all on cp7_accessory_nonpayable.date_requests_v1 from public,anon,authenticated,service_role,cp7_good_policy_date;
create index date_requests_actor_v1 on cp7_accessory_nonpayable.date_requests_v1(actor_id);
create trigger date_requests_immutable_v1 before update or delete
  on cp7_accessory_nonpayable.date_requests_v1 for each row
  execute function cp7_accessory_nonpayable.immutable_v1();
create trigger date_requests_no_truncate_v1 before truncate
  on cp7_accessory_nonpayable.date_requests_v1 for each statement
  execute function cp7_accessory_nonpayable.immutable_v1();

create function cp7_accessory_nonpayable.settings_access_v1(p_write boolean)
returns jsonb language plpgsql volatile security definer set search_path='' as $$
declare access_value jsonb;profile_id uuid;role_code text;can_write boolean;
begin
  if current_setting('transaction_isolation')<>'read committed' then
    raise exception 'NONPAYABLE_FRESH_ACCESS_REQUIRED';
  end if;
  if auth.uid() is null or coalesce(auth.jwt()->>'role','') is distinct from 'authenticated' then
    raise exception using errcode='42501',message='NONPAYABLE_SETTINGS_DENIED';
  end if;
  access_value:=erp.get_my_access_v1();
  role_code:=access_value->'profile'->>'role_code';
  profile_id:=erp.current_app_user_id();
  if access_value->'allowed' is distinct from 'true'::jsonb or role_code not in('OWNER','ADMIN')
     or role_code is null or profile_id is null
     or access_value->'profile'->>'id' is distinct from profile_id::text
     or access_value->'profile'->>'row_version' is null
     or access_value->'profile'->>'role_row_version' is null
     or not erp.has_permission('settings.erp.view') or not erp.has_permission('warehouse.accessory.view') then
    raise exception using errcode='42501',message='NONPAYABLE_SETTINGS_DENIED';
  end if;
  can_write:=role_code='OWNER' and erp.has_permission('settings.erp.manage');
  if p_write and not can_write then
    raise exception using errcode='42501',message='NONPAYABLE_OWNER_DATE_REQUIRED';
  end if;
  return jsonb_build_object('actor',profile_id,'can_write',can_write,
    'epoch',encode(sha256(convert_to(jsonb_build_object('auth_user_id',auth.uid(),
      'profile',access_value->'profile','permissions',access_value->'permissions')::text,'UTF8')),'hex'));
end;$$;

create function cp7_accessory_nonpayable.settings_event_v1(p_event uuid)
returns jsonb language sql stable security definer set search_path='' as $$
  select jsonb_build_object('id',e.id,'version',e.version::text,'status',e.status,
    'recorded_at',to_char(e.set_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
    'reason',e.reason,'categories',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'name',c.category_name)
      order by c.id) from jsonb_array_elements_text(coalesce(e.value->'special_free_category_ids','[]'::jsonb)) x(id)
      left join erp.accessory_categories c on c.id=x.id::uuid),'[]'::jsonb))
  from erp.bc_policy_setting_events_v1 e where e.id=p_event and e.policy_key='ERP_DEC02'
$$;

create function cp7_accessory_nonpayable.settings_workspace_v1(p_payload jsonb)
returns jsonb language plpgsql volatile security definer set search_path='' as $$
declare
  access_value jsonb;source_row erp.bc_policy_settings_v1%rowtype;
  current_event erp.bc_policy_setting_events_v1%rowtype;
  before_version bigint;before_day date;events jsonb;versions jsonb;
  events_more boolean;versions_more boolean;
begin
  access_value:=cp7_accessory_nonpayable.settings_access_v1(false);
  if jsonb_typeof(p_payload) is distinct from 'object' or not p_payload?&array['before_version','before_date']
     or (select count(*) from jsonb_object_keys(p_payload))<>2 then
    raise exception 'NONPAYABLE_SETTINGS_READ_FIELDS';
  end if;
  if p_payload->'before_version' is distinct from 'null'::jsonb then
    if jsonb_typeof(p_payload->'before_version') is distinct from 'string'
       or p_payload->>'before_version'!~'^[1-9][0-9]{0,18}$' then
      raise exception 'NONPAYABLE_SOURCE_CURSOR_REQUIRED';
    end if;
    before_version:=(p_payload->>'before_version')::bigint;
  end if;
  if p_payload->'before_date' is distinct from 'null'::jsonb then
    if jsonb_typeof(p_payload->'before_date') is distinct from 'string'
       or p_payload->>'before_date'!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then
      raise exception 'NONPAYABLE_DATE_CURSOR_REQUIRED';
    end if;
    before_day:=(p_payload->>'before_date')::date;
    if not isfinite(before_day) then raise exception 'NONPAYABLE_FINITE_DATE_REQUIRED';end if;
  end if;
  select * into source_row from erp.bc_policy_settings_v1 s where s.policy_key='ERP_DEC02' for share;
  if not found then raise exception 'NONPAYABLE_ERP_DEC02_SOURCE_REQUIRED';end if;
  perform pg_advisory_xact_lock_shared(hashtextextended('CP7_NONPAYABLE_CATEGORY_TIMELINE',0));
  access_value:=cp7_accessory_nonpayable.settings_access_v1(false);
  select * into current_event from erp.bc_policy_setting_events_v1 e
    where e.policy_key='ERP_DEC02' and e.version=source_row.version;
  if current_event.id is null or current_event.status<>source_row.status
     or current_event.value is distinct from source_row.value then
    raise exception 'NONPAYABLE_EXACT_CURRENT_SOURCE_EVENT_REQUIRED';
  end if;
  select coalesce(jsonb_agg(cp7_accessory_nonpayable.settings_event_v1(e.id) order by e.version desc),'[]'::jsonb)
    into events from(select se.id,se.version from erp.bc_policy_setting_events_v1 se where se.policy_key='ERP_DEC02'
      and(before_version is null or se.version<before_version) order by se.version desc limit 31)e;
  events_more:=jsonb_array_length(events)>30;
  if events_more then events:=events-30;end if;
  select coalesce(jsonb_agg(jsonb_build_object('id',v.id,'effective_from',to_char(v.effective_from,'YYYY-MM-DD'),
      'source_event',cp7_accessory_nonpayable.settings_event_v1(v.source_event_id),'reason',v.reason,
      'recorded_at',to_char(v.recorded_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))
      order by v.effective_from desc),'[]'::jsonb)
    into versions from(select cv.* from cp7_accessory_nonpayable.category_versions_v1 cv
      where before_day is null or cv.effective_from<before_day order by cv.effective_from desc limit 31)v;
  versions_more:=jsonb_array_length(versions)>30;
  if versions_more then versions:=versions-30;end if;
  return jsonb_build_object('contract_version','cp7.good-policy-date-workspace.v1',
    'actor',access_value->'actor','access_epoch',access_value->'epoch','can_write',access_value->'can_write',
    'timeline_token',cp7_accessory_nonpayable.timeline_token_v1(),
    'current_source',cp7_accessory_nonpayable.settings_event_v1(current_event.id),
    'current_source_registered',exists(select 1 from cp7_accessory_nonpayable.category_versions_v1 cv where cv.source_version=source_row.version),
    'source_events',events,'source_has_more',events_more,
    'next_source_before',case when events_more then events->-1->>'version' else null end,
    'versions',versions,'version_has_more',versions_more,
    'next_version_before',case when versions_more then versions->-1->>'effective_from' else null end);
end;$$;

create function cp7_accessory_nonpayable.settings_save_v1(p_payload jsonb,p_request uuid,p_cancel boolean)
returns jsonb language plpgsql volatile security definer set search_path='' as $$
declare
  access_value jsonb;fresh_access jsonb;previous cp7_accessory_nonpayable.date_requests_v1%rowtype;
  source_version bigint;effective_day date;source_event uuid;reason_text text;made jsonb;reply_value jsonb;
begin
  access_value:=cp7_accessory_nonpayable.settings_access_v1(true);
  if p_request is null or p_cancel is null or jsonb_typeof(p_payload) is distinct from 'object'
     or not p_payload?&array['contract_version','actor','access_epoch','effective_from','source_event_id',
       'expected_current_version','expected_timeline','reason','reviewed']
     or (select count(*) from jsonb_object_keys(p_payload))<>9
     or p_payload->>'contract_version' is distinct from 'cp7.good-policy-date-command.v1'
     or p_payload->'reviewed' is distinct from 'true'::jsonb
     or p_payload->>'actor' is distinct from access_value->>'actor' then
    raise exception 'NONPAYABLE_DATE_COMMAND_REVIEW_REQUIRED';
  end if;
  if jsonb_typeof(p_payload->'source_event_id') is distinct from 'string'
     or p_payload->>'source_event_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
     or jsonb_typeof(p_payload->'effective_from') is distinct from 'string'
     or p_payload->>'effective_from'!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
     or jsonb_typeof(p_payload->'expected_current_version') is distinct from 'string'
     or p_payload->>'expected_current_version'!~'^[1-9][0-9]{0,18}$'
     or jsonb_typeof(p_payload->'expected_timeline') is distinct from 'string'
     or p_payload->>'expected_timeline'!~'^[0-9a-f]{64}$'
     or jsonb_typeof(p_payload->'access_epoch') is distinct from 'string'
     or p_payload->>'access_epoch'!~'^[0-9a-f]{64}$'
     or jsonb_typeof(p_payload->'reason') is distinct from 'string' then
    raise exception 'NONPAYABLE_DATE_COMMAND_FIELDS';
  end if;
  source_event:=(p_payload->>'source_event_id')::uuid;
  effective_day:=(p_payload->>'effective_from')::date;
  reason_text:=p_payload->>'reason';
  if not isfinite(effective_day) or length(btrim(reason_text)) not between 1 and 1000
     or btrim(reason_text)<>reason_text then raise exception 'NONPAYABLE_DATE_AND_REASON_REQUIRED';end if;
  -- Use the same outer financial lock order as GOOD and the existing Native
  -- policy writers, then the BC row and the private timeline lock.
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select s.version into source_version from erp.bc_policy_settings_v1 s where s.policy_key='ERP_DEC02' for share;
  if not found then raise exception 'NONPAYABLE_ERP_DEC02_SOURCE_REQUIRED';end if;
  perform pg_advisory_xact_lock(hashtextextended('CP7_NONPAYABLE_CATEGORY_TIMELINE',0));
  fresh_access:=cp7_accessory_nonpayable.settings_access_v1(true);
  if fresh_access is distinct from access_value then
    raise exception using errcode='42501',message='NONPAYABLE_SETTINGS_ACCESS_CHANGED';
  end if;
  select * into previous from cp7_accessory_nonpayable.date_requests_v1 r where r.request_id=p_request;
  if previous.request_id is not null then
    if previous.actor_id::text is distinct from access_value->>'actor' or previous.request_body is distinct from p_payload then
      raise exception 'NONPAYABLE_DATE_REQUEST_INTENT_CHANGED';
    end if;
    return previous.response;
  end if;
  -- A lost reply must not trap the owner behind an unconfirmable request.
  -- Cancel only an absent request under the same locks, storing an immutable
  -- tombstone. A late arrival replays CANCELLED. If already SAVED, the stored
  -- success above is returned; an effective policy is never silently undone.
  if p_cancel then
    reply_value:=jsonb_build_object('contract_version','cp7.good-policy-date-outcome.v1',
      'request_id',p_request,'actor',access_value->'actor','effective_from',p_payload->'effective_from',
      'id',null,'source_event_id',p_payload->'source_event_id','source_version',null,
      'reason',reason_text,'status','CANCELLED');
    insert into cp7_accessory_nonpayable.date_requests_v1(request_id,actor_id,request_body,response)
      values(p_request,(access_value->>'actor')::uuid,p_payload,reply_value);
    return reply_value;
  end if;
  if p_payload->>'access_epoch' is distinct from access_value->>'epoch' then
    raise exception using errcode='42501',message='NONPAYABLE_SETTINGS_ACCESS_CHANGED';
  end if;
  if p_payload->>'expected_current_version' is distinct from source_version::text then
    raise exception 'NONPAYABLE_CURRENT_SOURCE_STALE: kategori berubah; baca ulang';
  end if;
  made:=cp7_accessory_nonpayable.record_version_v1(effective_day,source_event,p_request,
    p_payload->>'expected_timeline',reason_text);
  reply_value:=jsonb_build_object('contract_version','cp7.good-policy-date-outcome.v1',
    'request_id',p_request,'actor',access_value->'actor','effective_from',made->'effective_from',
    'id',made->'id','source_event_id',made->'source_event_id','source_version',made->'source_version',
    'reason',reason_text,'status','SAVED');
  insert into cp7_accessory_nonpayable.date_requests_v1(request_id,actor_id,request_body,response)
    values(p_request,(access_value->>'actor')::uuid,p_payload,reply_value);
  return reply_value;
end;$$;

create function public.erp_cp7_get_good_policy_dates_v1(p_payload jsonb)
returns jsonb language sql volatile security definer set search_path='' as $$
  select cp7_accessory_nonpayable.settings_workspace_v1(p_payload)
$$;
create function public.erp_cp7_save_good_policy_date_v1(p_payload jsonb,p_request uuid,p_cancel boolean default false)
returns jsonb language sql volatile security definer set search_path='' as $$
  select cp7_accessory_nonpayable.settings_save_v1(p_payload,p_request,p_cancel)
$$;

alter function cp7_accessory_nonpayable.settings_access_v1(boolean) owner to postgres;
alter function cp7_accessory_nonpayable.settings_event_v1(uuid) owner to postgres;
alter function cp7_accessory_nonpayable.settings_workspace_v1(jsonb) owner to postgres;
alter function cp7_accessory_nonpayable.settings_save_v1(jsonb,uuid,boolean) owner to postgres;
revoke all on function cp7_accessory_nonpayable.settings_access_v1(boolean),
  cp7_accessory_nonpayable.settings_event_v1(uuid),cp7_accessory_nonpayable.settings_workspace_v1(jsonb),
  cp7_accessory_nonpayable.settings_save_v1(jsonb,uuid,boolean)
  from public,anon,authenticated,service_role,cp7_good_policy_date;
grant usage on schema cp7_accessory_nonpayable to cp7_good_policy_date;
grant execute on function cp7_accessory_nonpayable.settings_workspace_v1(jsonb),
  cp7_accessory_nonpayable.settings_save_v1(jsonb,uuid,boolean) to cp7_good_policy_date;

-- The gated installer first verifies public's raw ACL is explicit, and checks
-- it is restored exactly after this statement-only ownership grant.
-- PostgreSQL 17 gives a non-superuser creator ADMIN, but no SET option.
-- Grant SET only for these two ownership transfers, then remove our own grant.
-- The bootstrap administrator's automatic ADMIN-only grant remains explicit
-- in the complete catalogue transition; it conveys no inherited/SET access.
grant cp7_good_policy_date to postgres with admin false, inherit false, set true;
grant create on schema public to cp7_good_policy_date;
alter function public.erp_cp7_get_good_policy_dates_v1(jsonb) owner to cp7_good_policy_date;
alter function public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean) owner to cp7_good_policy_date;
revoke create on schema public from cp7_good_policy_date;
revoke cp7_good_policy_date from postgres granted by postgres;
revoke all on function public.erp_cp7_get_good_policy_dates_v1(jsonb),
  public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean) from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_good_policy_dates_v1(jsonb),
  public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean) to authenticated;
