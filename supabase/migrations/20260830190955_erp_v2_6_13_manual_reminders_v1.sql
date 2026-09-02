-- ERP Garment v2.6.13
-- Private, own-user manual reminders for ERP Enteng UAT.
--
-- Deliberately excluded from V1:
--   * automatic reminders derived from business transactions;
--   * cross-user assignment;
--   * cron, push, email, or WhatsApp delivery;
--   * hard deletion.

begin;

set local lock_timeout = '10s';
set local statement_timeout = '120s';

do $migration_guard$
begin
  if to_regclass('erp.app_users') is null
     or to_regclass('erp.idempotency_requests') is null
     or to_regclass('erp.audit_logs') is null
     or to_regprocedure('erp.current_app_user_id()') is null
     or to_regprocedure('erp.current_app_role()') is null
     or to_regprocedure('erp.require_internal()') is null
     or to_regprocedure('erp._request_hash(jsonb)') is null
     or to_regprocedure('erp._idempotency_begin(text,uuid,text)') is null
     or to_regprocedure('erp._idempotency_complete(text,uuid,jsonb)') is null
     or to_regprocedure('erp.bump_row_version()') is null then
    raise exception 'Manual reminders V1 requires the ERP Enteng baseline and idempotency helpers';
  end if;
end;
$migration_guard$;

create table if not exists erp.manual_reminders (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references erp.app_users(id) on delete restrict,
  title text not null,
  note text not null default '',
  due_at timestamptz not null,
  priority varchar(10) not null default 'NORMAL',
  module varchar(80) not null default 'Operasional',
  status varchar(12) not null default 'OPEN',
  completed_at timestamptz,
  completed_by uuid references erp.app_users(id) on delete restrict,
  cancelled_at timestamptz,
  cancelled_by uuid references erp.app_users(id) on delete restrict,
  cancellation_reason text,
  created_at timestamptz not null default clock_timestamp(),
  created_by uuid not null references erp.app_users(id) on delete restrict,
  updated_at timestamptz not null default clock_timestamp(),
  updated_by uuid not null references erp.app_users(id) on delete restrict,
  last_client_request_id uuid not null,
  row_version bigint not null default 1,
  constraint manual_reminders_title_check
    check (btrim(title) <> '' and char_length(title) <= 200),
  constraint manual_reminders_note_check
    check (char_length(note) <= 4000),
  constraint manual_reminders_due_at_check
    check (isfinite(due_at)),
  constraint manual_reminders_priority_check
    check (priority in ('URGENT','NORMAL','LOW')),
  constraint manual_reminders_module_check
    check (btrim(module) <> '' and char_length(module) <= 80),
  constraint manual_reminders_status_check
    check (status in ('OPEN','DONE','CANCELLED')),
  constraint manual_reminders_reason_check
    check (cancellation_reason is null or (
      btrim(cancellation_reason) <> '' and char_length(cancellation_reason) <= 1000
    )),
  constraint manual_reminders_actor_check
    check (
      owner_user_id = created_by
      and owner_user_id = updated_by
      and (completed_by is null or completed_by = owner_user_id)
      and (cancelled_by is null or cancelled_by = owner_user_id)
    ),
  constraint manual_reminders_lifecycle_check
    check (
      (status = 'OPEN'
        and completed_at is null and completed_by is null
        and cancelled_at is null and cancelled_by is null
        and cancellation_reason is null)
      or
      (status = 'DONE'
        and completed_at is not null and completed_by is not null
        and cancelled_at is null and cancelled_by is null
        and cancellation_reason is null)
      or
      (status = 'CANCELLED'
        and ((completed_at is null and completed_by is null)
          or (completed_at is not null and completed_by is not null))
        and cancelled_at is not null and cancelled_by is not null
        and btrim(coalesce(cancellation_reason, '')) <> '')
    ),
  constraint manual_reminders_row_version_check check (row_version > 0)
);

-- OPEN is the dashboard hot path. The management page passes ACTIVE/other filters explicitly.
create index if not exists idx_manual_reminders_open_due
  on erp.manual_reminders(owner_user_id, due_at, id)
  where status = 'OPEN';

create or replace function erp.guard_manual_reminder_write()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
begin
  if tg_op = 'DELETE' then
    raise exception 'Manual reminders cannot be deleted; use erp_cancel_my_reminder_v1';
  end if;

  if current_setting('app.manual_reminder_write', true) is distinct from 'on' then
    raise exception 'Manual reminders are write-protected; use the reminder RPC facade';
  end if;

  if tg_op = 'UPDATE' then
    if (new.id, new.owner_user_id, new.created_at, new.created_by)
       is distinct from
       (old.id, old.owner_user_id, old.created_at, old.created_by) then
      raise exception 'Reminder identity, owner, and creation facts are immutable';
    end if;
    if old.status = 'CANCELLED' then
      raise exception 'Cancelled reminders are terminal';
    end if;
  end if;

  return new;
end;
$function$;

create or replace function erp.audit_manual_reminder_change()
returns trigger
language plpgsql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
declare
  v_action text := coalesce(nullif(current_setting('app.manual_reminder_action', true), ''), tg_op);
  v_old jsonb;
  v_new jsonb;
begin
  -- audit_logs is shared with internal staff, so title, note, module, and the
  -- private cancellation reason are intentionally never copied into it.
  if tg_op = 'UPDATE' then
    v_old := jsonb_build_object(
      'row_version', old.row_version,
      'content_redacted', true
    );
  end if;

  v_new := jsonb_build_object(
    'row_version', new.row_version,
    'title_changed', case when tg_op = 'INSERT' then true else new.title is distinct from old.title end,
    'note_changed', case when tg_op = 'INSERT' then true else new.note is distinct from old.note end,
    'module_changed', case when tg_op = 'INSERT' then true else new.module is distinct from old.module end,
    'content_redacted', true
  );

  insert into erp.audit_logs(
    entity_type, entity_id, action, old_data, new_data, changed_by, change_reason
  ) values (
    'manual_reminders', new.id, case when tg_op = 'INSERT' then 'INSERT' else 'UPDATE' end,
    v_old, v_new, erp.current_app_user_id(),
    'Manual reminder ' || lower(v_action)
  );

  return new;
end;
$function$;

drop trigger if exists trg_00_guard_manual_reminder_write on erp.manual_reminders;
create trigger trg_00_guard_manual_reminder_write
before insert or update or delete on erp.manual_reminders
for each row execute function erp.guard_manual_reminder_write();

drop trigger if exists trg_01_bump_manual_reminder_version on erp.manual_reminders;
create trigger trg_01_bump_manual_reminder_version
before update on erp.manual_reminders
for each row execute function erp.bump_row_version();

drop trigger if exists trg_90_audit_manual_reminder on erp.manual_reminders;
create trigger trg_90_audit_manual_reminder
after insert or update on erp.manual_reminders
for each row execute function erp.audit_manual_reminder_change();

create or replace function erp.require_manual_reminder_actor()
returns uuid
language plpgsql
stable
security definer
set search_path = erp, public, auth, pg_temp
as $function$
declare
  v_actor uuid;
  v_role text;
begin
  perform erp.require_internal();
  v_actor := erp.current_app_user_id();
  v_role := erp.current_app_role();
  if v_actor is null or v_role not in ('OWNER','ADMIN','STAFF') then
    raise exception 'Mapped active internal ERP user required';
  end if;
  return v_actor;
end;
$function$;

create or replace function erp.list_my_reminders_v1(
  p_filter text default 'ACTIVE',
  p_limit integer default 200
)
returns jsonb
language plpgsql
stable
security definer
set search_path = erp, public, auth, pg_temp
as $function$
declare
  v_actor uuid := erp.require_manual_reminder_actor();
  v_filter text := upper(coalesce(nullif(btrim(p_filter), ''), 'ACTIVE'));
  v_items jsonb;
  v_counts jsonb;
begin
  if v_filter not in ('ACTIVE','OPEN','DONE','CANCELLED','ALL') then
    raise exception 'Reminder filter must be ACTIVE, OPEN, DONE, CANCELLED, or ALL';
  end if;
  if p_limit is null or p_limit < 1 or p_limit > 200 then
    raise exception 'Reminder limit must be between 1 and 200';
  end if;

  select coalesce(jsonb_agg(q.item order by q.status_rank, q.priority_rank, q.sort_at, q.id), '[]'::jsonb)
  into v_items
  from (
    select
      r.id,
      case r.status when 'OPEN' then 0 when 'DONE' then 1 else 2 end as status_rank,
      case r.priority when 'URGENT' then 0 when 'NORMAL' then 1 else 2 end as priority_rank,
      case when r.status = 'OPEN' then r.due_at else r.updated_at end as sort_at,
      jsonb_build_object(
        'id', r.id,
        'title', r.title,
        'note', r.note,
        'due_at', r.due_at,
        'priority', r.priority,
        'module', r.module,
        'status', r.status,
        'completed_at', r.completed_at,
        'cancelled_at', r.cancelled_at,
        'cancellation_reason', r.cancellation_reason,
        'created_at', r.created_at,
        'updated_at', r.updated_at,
        'row_version', r.row_version
      ) as item
    from erp.manual_reminders r
    where r.owner_user_id = v_actor
      and (
        v_filter = 'ALL'
        or (v_filter = 'ACTIVE' and r.status in ('OPEN','DONE'))
        or r.status = v_filter
      )
    order by
      case r.status when 'OPEN' then 0 when 'DONE' then 1 else 2 end,
      case r.priority when 'URGENT' then 0 when 'NORMAL' then 1 else 2 end,
      case when r.status = 'OPEN' then r.due_at else r.updated_at end,
      r.id
    limit p_limit
  ) q;

  select jsonb_build_object(
    'open', count(*) filter (where r.status = 'OPEN'),
    'done', count(*) filter (where r.status = 'DONE'),
    'cancelled', count(*) filter (where r.status = 'CANCELLED')
  ) into v_counts
  from erp.manual_reminders r
  where r.owner_user_id = v_actor;

  return jsonb_build_object(
    'items', v_items,
    'counts', v_counts,
    'read_at', statement_timestamp()
  );
end;
$function$;

create or replace function erp.save_my_reminder_v1(
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_version bigint default null
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'save_my_reminder_v1';
  v_actor uuid := erp.require_manual_reminder_actor();
  v_id uuid;
  v_title text;
  v_note text;
  v_due_text text;
  v_due_at timestamptz;
  v_priority text;
  v_module text;
  v_hash text;
  v_cached jsonb;
  v_row erp.manual_reminders%rowtype;
  v_response jsonb;
begin
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    raise exception 'Reminder payload must be a JSON object';
  end if;
  if exists (
    select 1 from jsonb_object_keys(p_payload) k
    where k not in ('id','title','note','due_at','priority','module')
  ) then
    raise exception 'Reminder payload contains unsupported fields';
  end if;
  if exists (
    select 1
    from jsonb_each(p_payload) item
    where item.key in ('id','title','note','due_at','priority','module')
      and jsonb_typeof(item.value) not in ('string','null')
  ) then
    raise exception 'Reminder payload fields must be strings or null';
  end if;

  begin
    v_id := nullif(btrim(p_payload->>'id'), '')::uuid;
  exception when invalid_text_representation then
    raise exception 'Reminder id must be a UUID';
  end;

  v_title := btrim(coalesce(p_payload->>'title', ''));
  v_note := coalesce(p_payload->>'note', '');
  v_due_text := btrim(coalesce(p_payload->>'due_at', ''));
  v_priority := upper(coalesce(nullif(btrim(p_payload->>'priority'), ''), 'NORMAL'));
  v_module := coalesce(nullif(btrim(p_payload->>'module'), ''), 'Operasional');

  if v_title = '' or char_length(v_title) > 200 then
    raise exception 'Reminder title must contain 1 to 200 characters';
  end if;
  if char_length(v_note) > 4000 then
    raise exception 'Reminder note cannot exceed 4000 characters';
  end if;
  if char_length(v_module) > 80 then
    raise exception 'Reminder module cannot exceed 80 characters';
  end if;
  if v_priority not in ('URGENT','NORMAL','LOW') then
    raise exception 'Reminder priority must be URGENT, NORMAL, or LOW';
  end if;
  if v_due_text = '' or v_due_text !~* '(Z|[+-][0-9]{2}:[0-9]{2})$' then
    raise exception 'Reminder due_at must be ISO-8601 with an explicit UTC offset';
  end if;
  begin
    v_due_at := v_due_text::timestamptz;
  exception when others then
    raise exception 'Reminder due_at is invalid';
  end;
  if not isfinite(v_due_at) then
    raise exception 'Reminder due_at must be finite';
  end if;

  if v_id is null and p_expected_version is not null then
    raise exception 'expected_version must be null when creating a reminder';
  end if;
  if v_id is not null and (p_expected_version is null or p_expected_version < 1) then
    raise exception 'A positive expected_version is required when updating a reminder';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'id', v_id,
    'title', v_title,
    'note', v_note,
    'due_at', v_due_at,
    'priority', v_priority,
    'module', v_module,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  if v_id is null then
    perform set_config('app.manual_reminder_write', 'on', true);
    perform set_config('app.manual_reminder_action', 'CREATE', true);
    insert into erp.manual_reminders(
      owner_user_id, title, note, due_at, priority, module,
      created_by, updated_by, last_client_request_id
    ) values (
      v_actor, v_title, v_note, v_due_at, v_priority, v_module,
      v_actor, v_actor, p_client_request_id
    ) returning * into v_row;
  else
    select * into v_row
    from erp.manual_reminders r
    where r.id = v_id and r.owner_user_id = v_actor
    for update;

    if v_row.id is null then raise exception 'Reminder not found'; end if;
    if v_row.row_version <> p_expected_version then
      raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_row.row_version;
    end if;
    if v_row.status <> 'OPEN' then
      raise exception 'Only OPEN reminders can be edited; reopen DONE reminders first';
    end if;

    if (v_row.title, v_row.note, v_row.due_at, v_row.priority, v_row.module)
       is distinct from
       (v_title, v_note, v_due_at, v_priority, v_module) then
      perform set_config('app.manual_reminder_write', 'on', true);
      perform set_config('app.manual_reminder_action', 'EDIT', true);
      update erp.manual_reminders r
      set title = v_title,
          note = v_note,
          due_at = v_due_at,
          priority = v_priority,
          module = v_module,
          updated_at = clock_timestamp(),
          updated_by = v_actor,
          last_client_request_id = p_client_request_id
      where r.id = v_id and r.owner_user_id = v_actor
      returning * into v_row;
    end if;
  end if;

  perform set_config('app.manual_reminder_write', 'off', true);
  perform set_config('app.manual_reminder_action', '', true);

  v_response := jsonb_build_object(
    'reminder', jsonb_build_object(
      'id', v_row.id,
      'title', v_row.title,
      'note', v_row.note,
      'due_at', v_row.due_at,
      'priority', v_row.priority,
      'module', v_row.module,
      'status', v_row.status,
      'completed_at', v_row.completed_at,
      'cancelled_at', v_row.cancelled_at,
      'cancellation_reason', v_row.cancellation_reason,
      'created_at', v_row.created_at,
      'updated_at', v_row.updated_at,
      'row_version', v_row.row_version
    ),
    'client_request_id', p_client_request_id
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.set_my_reminder_done_v1(
  p_reminder_id uuid,
  p_done boolean,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'set_my_reminder_done_v1';
  v_actor uuid := erp.require_manual_reminder_actor();
  v_hash text;
  v_cached jsonb;
  v_row erp.manual_reminders%rowtype;
  v_target_status text;
  v_response jsonb;
begin
  if p_reminder_id is null or p_done is null or p_expected_version is null or p_expected_version < 1 then
    raise exception 'reminder_id, done, and a positive expected_version are required';
  end if;
  v_target_status := case when p_done then 'DONE' else 'OPEN' end;
  v_hash := erp._request_hash(jsonb_build_object(
    'reminder_id', p_reminder_id,
    'done', p_done,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_row
  from erp.manual_reminders r
  where r.id = p_reminder_id and r.owner_user_id = v_actor
  for update;

  if v_row.id is null then raise exception 'Reminder not found'; end if;
  if v_row.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_row.row_version;
  end if;
  if v_row.status = 'CANCELLED' then raise exception 'Cancelled reminders are terminal'; end if;

  if v_row.status <> v_target_status then
    perform set_config('app.manual_reminder_write', 'on', true);
    perform set_config('app.manual_reminder_action', case when p_done then 'COMPLETE' else 'REOPEN' end, true);
    update erp.manual_reminders r
    set status = v_target_status,
        completed_at = case when p_done then clock_timestamp() else null end,
        completed_by = case when p_done then v_actor else null end,
        updated_at = clock_timestamp(),
        updated_by = v_actor,
        last_client_request_id = p_client_request_id
    where r.id = p_reminder_id and r.owner_user_id = v_actor
    returning * into v_row;
  end if;

  perform set_config('app.manual_reminder_write', 'off', true);
  perform set_config('app.manual_reminder_action', '', true);

  v_response := jsonb_build_object(
    'reminder_id', v_row.id,
    'status', v_row.status,
    'completed_at', v_row.completed_at,
    'row_version', v_row.row_version,
    'client_request_id', p_client_request_id
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.cancel_my_reminder_v1(
  p_reminder_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'cancel_my_reminder_v1';
  v_actor uuid := erp.require_manual_reminder_actor();
  v_reason text := btrim(coalesce(p_reason, ''));
  v_hash text;
  v_cached jsonb;
  v_row erp.manual_reminders%rowtype;
  v_response jsonb;
begin
  if p_reminder_id is null or p_expected_version is null or p_expected_version < 1 then
    raise exception 'reminder_id and a positive expected_version are required';
  end if;
  if v_reason = '' or char_length(v_reason) > 1000 then
    raise exception 'Cancellation reason must contain 1 to 1000 characters';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'reminder_id', p_reminder_id,
    'reason', v_reason,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_row
  from erp.manual_reminders r
  where r.id = p_reminder_id and r.owner_user_id = v_actor
  for update;

  if v_row.id is null then raise exception 'Reminder not found'; end if;
  if v_row.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_row.row_version;
  end if;
  if v_row.status = 'CANCELLED' then raise exception 'Cancelled reminders are terminal'; end if;

  perform set_config('app.manual_reminder_write', 'on', true);
  perform set_config('app.manual_reminder_action', 'CANCEL', true);
  update erp.manual_reminders r
  set status = 'CANCELLED',
      cancelled_at = clock_timestamp(),
      cancelled_by = v_actor,
      cancellation_reason = v_reason,
      updated_at = clock_timestamp(),
      updated_by = v_actor,
      last_client_request_id = p_client_request_id
  where r.id = p_reminder_id and r.owner_user_id = v_actor
  returning * into v_row;

  perform set_config('app.manual_reminder_write', 'off', true);
  perform set_config('app.manual_reminder_action', '', true);

  v_response := jsonb_build_object(
    'reminder_id', v_row.id,
    'status', v_row.status,
    'cancelled_at', v_row.cancelled_at,
    'row_version', v_row.row_version,
    'client_request_id', p_client_request_id
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

-- Public browser facades. Every internal function rechecks the mapped actor.
create or replace function public.erp_list_my_reminders_v1(
  p_filter text default 'ACTIVE',
  p_limit integer default 200
)
returns jsonb
language sql
stable
security definer
set search_path = erp, public, auth, pg_temp
as $function$
  select erp.list_my_reminders_v1(p_filter, p_limit)
$function$;

create or replace function public.erp_save_my_reminder_v1(
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_version bigint default null
)
returns jsonb
language sql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
  select erp.save_my_reminder_v1(p_payload, p_client_request_id, p_expected_version)
$function$;

create or replace function public.erp_set_my_reminder_done_v1(
  p_reminder_id uuid,
  p_done boolean,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language sql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
  select erp.set_my_reminder_done_v1(
    p_reminder_id, p_done, p_client_request_id, p_expected_version
  )
$function$;

create or replace function public.erp_cancel_my_reminder_v1(
  p_reminder_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language sql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
  select erp.cancel_my_reminder_v1(
    p_reminder_id, p_reason, p_client_request_id, p_expected_version
  )
$function$;

alter table erp.manual_reminders enable row level security;

drop policy if exists own_internal_read on erp.manual_reminders;
create policy own_internal_read on erp.manual_reminders
for select to authenticated
using (
  owner_user_id = (select erp.current_app_user_id())
  and (select erp.current_app_role()) in ('OWNER','ADMIN','STAFF')
);

revoke all on erp.manual_reminders from public, anon, authenticated;
grant all on erp.manual_reminders to service_role;

revoke execute on function public.erp_list_my_reminders_v1(text, integer)
  from public, anon, authenticated;
revoke execute on function public.erp_save_my_reminder_v1(jsonb, uuid, bigint)
  from public, anon, authenticated;
revoke execute on function public.erp_set_my_reminder_done_v1(uuid, boolean, uuid, bigint)
  from public, anon, authenticated;
revoke execute on function public.erp_cancel_my_reminder_v1(uuid, text, uuid, bigint)
  from public, anon, authenticated;

grant execute on function public.erp_list_my_reminders_v1(text, integer)
  to authenticated, service_role;
grant execute on function public.erp_save_my_reminder_v1(jsonb, uuid, bigint)
  to authenticated, service_role;
grant execute on function public.erp_set_my_reminder_done_v1(uuid, boolean, uuid, bigint)
  to authenticated, service_role;
grant execute on function public.erp_cancel_my_reminder_v1(uuid, text, uuid, bigint)
  to authenticated, service_role;

-- Private implementations and trigger helpers are never browser endpoints.
revoke execute on function erp.require_manual_reminder_actor()
  from public, anon, authenticated;
revoke execute on function erp.list_my_reminders_v1(text, integer)
  from public, anon, authenticated;
revoke execute on function erp.save_my_reminder_v1(jsonb, uuid, bigint)
  from public, anon, authenticated;
revoke execute on function erp.set_my_reminder_done_v1(uuid, boolean, uuid, bigint)
  from public, anon, authenticated;
revoke execute on function erp.cancel_my_reminder_v1(uuid, text, uuid, bigint)
  from public, anon, authenticated;
revoke execute on function erp.guard_manual_reminder_write()
  from public, anon, authenticated;
revoke execute on function erp.audit_manual_reminder_change()
  from public, anon, authenticated;

grant execute on function erp.require_manual_reminder_actor() to service_role;
grant execute on function erp.list_my_reminders_v1(text, integer) to service_role;
grant execute on function erp.save_my_reminder_v1(jsonb, uuid, bigint) to service_role;
grant execute on function erp.set_my_reminder_done_v1(uuid, boolean, uuid, bigint)
  to service_role;
grant execute on function erp.cancel_my_reminder_v1(uuid, text, uuid, bigint)
  to service_role;
grant execute on function erp.guard_manual_reminder_write() to service_role;
grant execute on function erp.audit_manual_reminder_change() to service_role;

comment on table erp.manual_reminders is
  'Own-user manual reminders. V1 has no cross-user assignment, delivery scheduler, automatic business triggers, or hard delete.';
comment on function public.erp_list_my_reminders_v1(text, integer) is
  'Lists only the authenticated internal user own reminders; ACTIVE hides cancelled rows.';
comment on function public.erp_save_my_reminder_v1(jsonb, uuid, bigint) is
  'Creates or edits an OPEN own-user reminder with idempotency and optimistic locking.';
comment on function public.erp_set_my_reminder_done_v1(uuid, boolean, uuid, bigint) is
  'Completes or reopens an own-user reminder with idempotency and optimistic locking.';
comment on function public.erp_cancel_my_reminder_v1(uuid, text, uuid, bigint) is
  'Cancels without deleting an own-user reminder; cancellation is terminal and reasoned.';

notify pgrst, 'reload schema';

commit;
