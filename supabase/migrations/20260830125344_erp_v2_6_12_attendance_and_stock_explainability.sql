-- ERP Garment v2.6.12
-- Attendance roster/rate history and truthful stock explainability foundation.
--
-- This is an additive delta after the v2.6.11a UAT closure. It deliberately:
--   * does not edit or replay the v2.6.11a artifacts;
--   * preserves existing attendance rows and payroll snapshots;
--   * keeps erp.* tables private and exposes only narrow public RPCs;
--   * treats fg_inventory_balances.cached_qty_pcs as AVAILABLE stock because
--     SALE_RESERVE has already reduced that cache;
--   * does not invent demand, lead-time, WIP-to-SKU, HPP, or reorder formula
--     inputs that are not yet authoritative in the backend.

begin;

set local lock_timeout = '10s';
set local statement_timeout = '120s';

do $migration_guard$
begin
  if to_regclass('erp.contractor_workers') is null
     or to_regclass('erp.attendance_records') is null
     or to_regclass('erp.payroll_attendance_items') is null
     or to_regclass('erp.payroll_settlements') is null
     or to_regclass('erp.fg_inventory_balances') is null
     or to_regclass('erp.fg_stock_movements') is null then
    raise exception 'ERP v2.6.12 requires the ERP Garment baseline schema before this additive delta';
  end if;
end;
$migration_guard$;

-- ---------------------------------------------------------------------------
-- 1. Lightweight worker roster and effective-dated daily rates
-- ---------------------------------------------------------------------------

alter table erp.contractor_workers
  add column if not exists job_description text,
  add column if not exists row_version bigint not null default 1,
  add column if not exists created_by uuid references erp.app_users(id),
  add column if not exists updated_by uuid references erp.app_users(id);

alter table erp.contractor_workers
  drop constraint if exists contractor_workers_row_version_check;
alter table erp.contractor_workers
  add constraint contractor_workers_row_version_check check (row_version > 0);

alter table erp.contractor_workers
  drop constraint if exists contractor_workers_active_dates_check;
alter table erp.contractor_workers
  add constraint contractor_workers_active_dates_check
  check (left_at is null or joined_at is null or left_at >= joined_at);

drop trigger if exists trg_00_worker_row_version on erp.contractor_workers;
create trigger trg_00_worker_row_version
before update on erp.contractor_workers
for each row execute function erp.bump_row_version();

create or replace function erp.guard_worker_daily_rate_cache()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
begin
  if new.daily_rate is distinct from old.daily_rate
     and current_setting('app.worker_rate_write', true) is distinct from 'on' then
    raise exception 'contractor_workers.daily_rate is a current cache; use erp_set_worker_daily_rate_v1';
  end if;
  return new;
end;
$function$;

drop trigger if exists trg_01_guard_worker_daily_rate_cache on erp.contractor_workers;
create trigger trg_01_guard_worker_daily_rate_cache
before update of daily_rate on erp.contractor_workers
for each row execute function erp.guard_worker_daily_rate_cache();

create table if not exists erp.worker_daily_rate_versions (
  id uuid primary key default gen_random_uuid(),
  worker_id uuid not null references erp.contractor_workers(id),
  daily_rate numeric(24,6) not null check (daily_rate >= 0),
  effective_from date not null,
  effective_to date,
  change_reason text not null check (btrim(change_reason) <> ''),
  created_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  constraint worker_daily_rate_versions_dates_check
    check (effective_to is null or effective_to >= effective_from),
  constraint worker_daily_rate_versions_worker_from_key
    unique (worker_id, effective_from)
);

create index if not exists idx_worker_rate_versions_lookup
  on erp.worker_daily_rate_versions(worker_id, effective_from desc);

create or replace function erp.guard_worker_daily_rate_version()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
declare
  v_worker_id uuid := case when tg_op = 'DELETE' then old.worker_id else new.worker_id end;
begin
  if current_setting('app.worker_rate_write', true) is distinct from 'on' then
    raise exception 'Worker rate history is write-protected; use erp_set_worker_daily_rate_v1';
  end if;

  if tg_op = 'DELETE' then
    raise exception 'Worker rate history cannot be deleted';
  end if;

  if tg_op = 'UPDATE'
     and (new.worker_id, new.daily_rate, new.effective_from, new.change_reason,
          new.created_by, new.created_at)
         is distinct from
         (old.worker_id, old.daily_rate, old.effective_from, old.change_reason,
          old.created_by, old.created_at) then
    raise exception 'Existing worker rate facts are immutable; only effective_to may be closed';
  end if;

  perform pg_advisory_xact_lock(hashtextextended('WORKER_RATE|' || v_worker_id::text, 0));

  if exists (
    select 1
    from erp.worker_daily_rate_versions r
    where r.worker_id = v_worker_id
      and r.id <> coalesce(new.id, gen_random_uuid())
      and daterange(r.effective_from, coalesce(r.effective_to + 1, 'infinity'::date), '[)')
          && daterange(new.effective_from, coalesce(new.effective_to + 1, 'infinity'::date), '[)')
  ) then
    raise exception 'Worker daily-rate periods cannot overlap';
  end if;

  return new;
end;
$function$;

drop trigger if exists trg_guard_worker_daily_rate_version
  on erp.worker_daily_rate_versions;
create trigger trg_guard_worker_daily_rate_version
before insert or update or delete on erp.worker_daily_rate_versions
for each row execute function erp.guard_worker_daily_rate_version();

drop trigger if exists trg_audit_worker_daily_rate_versions
  on erp.worker_daily_rate_versions;
create trigger trg_audit_worker_daily_rate_versions
after insert or update or delete on erp.worker_daily_rate_versions
for each row execute function erp.audit_row_change();

select set_config('app.worker_rate_write', 'on', true);

insert into erp.worker_daily_rate_versions(
  worker_id, daily_rate, effective_from, change_reason, created_by
)
select
  w.id,
  w.daily_rate,
  least(
    coalesce(w.joined_at, 'infinity'::date),
    coalesce((
      select min(a.attendance_date)
      from erp.attendance_records a
      where a.worker_id = w.id
    ), 'infinity'::date),
    coalesce(w.created_at::date, current_date)
  ),
  'v2.6.12 baseline copied from contractor_workers.daily_rate; no existing payroll snapshot changed',
  w.created_by
from erp.contractor_workers w
where not exists (
  select 1 from erp.worker_daily_rate_versions r where r.worker_id = w.id
)
on conflict (worker_id, effective_from) do nothing;

select set_config('app.worker_rate_write', 'off', true);

create or replace function erp.worker_daily_rate_version_id_at(
  p_worker_id uuid,
  p_effective_date date
)
returns uuid
language sql
stable
security invoker
set search_path = erp, public, pg_temp
as $function$
  select r.id
  from erp.worker_daily_rate_versions r
  where r.worker_id = p_worker_id
    and p_effective_date >= r.effective_from
    and (r.effective_to is null or p_effective_date <= r.effective_to)
  order by r.effective_from desc, r.created_at desc, r.id desc
  limit 1
$function$;

create or replace function erp.worker_daily_rate_at(
  p_worker_id uuid,
  p_effective_date date
)
returns numeric
language sql
stable
security invoker
set search_path = erp, public, pg_temp
as $function$
  select r.daily_rate
  from erp.worker_daily_rate_versions r
  where r.worker_id = p_worker_id
    and p_effective_date >= r.effective_from
    and (r.effective_to is null or p_effective_date <= r.effective_to)
  order by r.effective_from desc, r.created_at desc, r.id desc
  limit 1
$function$;

create or replace function erp.require_worker_daily_rate_at(
  p_worker_id uuid,
  p_effective_date date
)
returns numeric
language plpgsql
stable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_rate numeric;
begin
  v_rate := erp.worker_daily_rate_at(p_worker_id, p_effective_date);
  if v_rate is null then
    raise exception 'Worker % has no daily-rate version covering %', p_worker_id, p_effective_date;
  end if;
  return v_rate;
end;
$function$;

create or replace function erp.set_worker_daily_rate_v1(
  p_worker_id uuid,
  p_daily_rate numeric,
  p_effective_from date,
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
  v_operation constant text := 'set_worker_daily_rate_v1';
  v_hash text;
  v_cached jsonb;
  v_worker erp.contractor_workers%rowtype;
  v_next_from date;
  v_new_id uuid;
  v_response jsonb;
begin
  perform erp.require_owner_admin();

  if p_worker_id is null or p_effective_from is null or p_expected_version is null then
    raise exception 'worker_id, effective_from, and expected_version are required';
  end if;
  if p_daily_rate is null or p_daily_rate < 0 then
    raise exception 'daily_rate must be zero or positive';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'Rate change reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'worker_id', p_worker_id,
    'daily_rate', p_daily_rate,
    'effective_from', p_effective_from,
    'reason', p_reason,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_worker
  from erp.contractor_workers
  where id = p_worker_id
  for update;

  if v_worker.id is null then raise exception 'Worker not found'; end if;
  if v_worker.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_worker.row_version;
  end if;
  if v_worker.joined_at is not null and p_effective_from < v_worker.joined_at then
    raise exception 'Rate effective date cannot be earlier than worker start date';
  end if;
  if exists (
    select 1 from erp.worker_daily_rate_versions r
    where r.worker_id = p_worker_id and r.effective_from = p_effective_from
  ) then
    raise exception 'A worker rate version already starts on this date; use a later effective date';
  end if;

  perform set_config('app.change_reason', p_reason, true);
  perform set_config('app.worker_rate_write', 'on', true);
  perform pg_advisory_xact_lock(hashtextextended('WORKER_RATE|' || p_worker_id::text, 0));

  select min(r.effective_from) into v_next_from
  from erp.worker_daily_rate_versions r
  where r.worker_id = p_worker_id and r.effective_from > p_effective_from;

  update erp.worker_daily_rate_versions r
  set effective_to = p_effective_from - 1
  where r.worker_id = p_worker_id
    and r.effective_from < p_effective_from
    and (r.effective_to is null or r.effective_to >= p_effective_from);

  insert into erp.worker_daily_rate_versions(
    worker_id, daily_rate, effective_from, effective_to, change_reason, created_by
  ) values (
    p_worker_id, p_daily_rate, p_effective_from,
    case when v_next_from is null then null else v_next_from - 1 end,
    p_reason, erp.current_app_user_id()
  ) returning id into v_new_id;

  update erp.contractor_workers w
  set daily_rate = coalesce(erp.worker_daily_rate_at(w.id, current_date), w.daily_rate),
      updated_by = erp.current_app_user_id()
  where w.id = p_worker_id;

  select jsonb_build_object(
    'worker_id', w.id,
    'rate_version_id', v_new_id,
    'daily_rate', p_daily_rate,
    'effective_from', p_effective_from,
    'effective_to', case when v_next_from is null then null else v_next_from - 1 end,
    'current_daily_rate', w.daily_rate,
    'row_version', w.row_version
  ) into v_response
  from erp.contractor_workers w
  where w.id = p_worker_id;

  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create table if not exists erp.worker_employment_periods (
  id uuid primary key default gen_random_uuid(),
  worker_id uuid not null references erp.contractor_workers(id),
  started_on date not null,
  ended_on date,
  start_reason text not null check (btrim(start_reason) <> ''),
  end_reason text,
  created_by uuid references erp.app_users(id),
  ended_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  ended_at timestamptz,
  constraint worker_employment_periods_dates_check
    check (ended_on is null or ended_on >= started_on),
  constraint worker_employment_periods_end_reason_check
    check ((ended_on is null and end_reason is null)
      or (ended_on is not null and btrim(coalesce(end_reason, '')) <> '')),
  constraint worker_employment_periods_worker_start_key
    unique (worker_id, started_on)
);

create index if not exists idx_worker_employment_periods_lookup
  on erp.worker_employment_periods(worker_id, started_on desc);

create or replace function erp.guard_worker_employment_period()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
declare
  v_worker_id uuid := case when tg_op = 'DELETE' then old.worker_id else new.worker_id end;
begin
  if current_setting('app.worker_employment_write', true) is distinct from 'on' then
    raise exception 'Worker employment history is write-protected; use erp_save_worker_roster_v1';
  end if;
  if tg_op = 'DELETE' then
    raise exception 'Worker employment history cannot be deleted';
  end if;
  if tg_op = 'UPDATE'
     and (new.worker_id, new.started_on, new.start_reason, new.created_by, new.created_at)
         is distinct from
         (old.worker_id, old.started_on, old.start_reason, old.created_by, old.created_at) then
    raise exception 'Existing employment starts are immutable; only the stop fact may be added';
  end if;

  perform pg_advisory_xact_lock(hashtextextended('WORKER_EMPLOYMENT|' || v_worker_id::text, 0));
  if exists (
    select 1
    from erp.worker_employment_periods e
    where e.worker_id = v_worker_id
      and e.id <> new.id
      and daterange(e.started_on, coalesce(e.ended_on + 1, 'infinity'::date), '[)')
          && daterange(new.started_on, coalesce(new.ended_on + 1, 'infinity'::date), '[)')
  ) then
    raise exception 'Worker employment periods cannot overlap';
  end if;
  return new;
end;
$function$;

drop trigger if exists trg_guard_worker_employment_period
  on erp.worker_employment_periods;
create trigger trg_guard_worker_employment_period
before insert or update or delete on erp.worker_employment_periods
for each row execute function erp.guard_worker_employment_period();

drop trigger if exists trg_audit_worker_employment_periods
  on erp.worker_employment_periods;
create trigger trg_audit_worker_employment_periods
after insert or update or delete on erp.worker_employment_periods
for each row execute function erp.audit_row_change();

select set_config('app.worker_employment_write', 'on', true);

insert into erp.worker_employment_periods(
  worker_id, started_on, ended_on, start_reason, end_reason, created_by, ended_by, ended_at
)
select
  w.id,
  least(
    coalesce(w.joined_at, 'infinity'::date),
    coalesce((select min(a.attendance_date) from erp.attendance_records a where a.worker_id = w.id), 'infinity'::date),
    coalesce(w.left_at, 'infinity'::date),
    coalesce(w.created_at::date, current_date)
  ),
  w.left_at,
  'v2.6.12 baseline employment episode; no attendance/payroll history changed',
  case when w.left_at is null then null else 'Legacy stop date copied from contractor_workers.left_at' end,
  w.created_by,
  case when w.left_at is null then null else w.updated_by end,
  case when w.left_at is null then null else coalesce(w.updated_at, clock_timestamp()) end
from erp.contractor_workers w
where not exists (
  select 1 from erp.worker_employment_periods e where e.worker_id = w.id
)
on conflict (worker_id, started_on) do nothing;

select set_config('app.worker_employment_write', 'off', true);

create or replace function erp.worker_is_employed_on(
  p_worker_id uuid,
  p_effective_date date
)
returns boolean
language sql
stable
security invoker
set search_path = erp, public, pg_temp
as $function$
  select exists (
    select 1
    from erp.worker_employment_periods e
    where e.worker_id = p_worker_id
      and p_effective_date >= e.started_on
      and (e.ended_on is null or p_effective_date <= e.ended_on)
  )
$function$;

create or replace function erp.save_worker_roster_v1(
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
  v_operation constant text := 'save_worker_roster_v1';
  v_hash text;
  v_cached jsonb;
  v_worker_id uuid := nullif(p_payload->>'worker_id', '')::uuid;
  v_contractor_id uuid := nullif(p_payload->>'contractor_id', '')::uuid;
  v_worker_name text := nullif(btrim(p_payload->>'worker_name'), '');
  v_job_description text := nullif(btrim(p_payload->>'job_description'), '');
  v_pay_scheme text := upper(coalesce(nullif(btrim(p_payload->>'pay_scheme'), ''), 'DAILY'));
  v_joined_at date := nullif(p_payload->>'joined_at', '')::date;
  v_left_at date := nullif(p_payload->>'left_at', '')::date;
  v_reactivated_on date := nullif(p_payload->>'reactivated_at', '')::date;
  v_is_active boolean := coalesce((p_payload->>'is_active')::boolean, true);
  v_initial_rate numeric := coalesce((p_payload->>'initial_daily_rate')::numeric, 0);
  v_rate_from date := coalesce(nullif(p_payload->>'rate_effective_from', '')::date, v_joined_at, current_date);
  v_reason text := nullif(btrim(p_payload->>'reason'), '');
  v_existing erp.contractor_workers%rowtype;
  v_response jsonb;
begin
  perform erp.require_owner_admin();

  if v_contractor_id is null or v_worker_name is null
     or v_job_description is null or v_joined_at is null then
    raise exception 'contractor_id, worker_name, job_description, and joined_at are required';
  end if;
  if not exists (
    select 1 from erp.contractors c
    where c.id = v_contractor_id and c.contractor_type = 'MANDOR'
  ) then
    raise exception 'Worker roster contractor must be an existing MANDOR';
  end if;
  if v_reason is null then raise exception 'Worker change reason is required'; end if;
  if v_pay_scheme not in ('DAILY','PIECE','HYBRID','NONE') then
    raise exception 'Unsupported pay_scheme';
  end if;
  if v_left_at is not null and v_is_active then
    raise exception 'An active worker cannot have a stop date; clear left_at or deactivate the worker';
  end if;
  if not v_is_active and v_left_at is null then
    raise exception 'A deactivated worker requires left_at';
  end if;
  if not v_is_active and v_left_at > current_date then
    raise exception 'A worker stop date cannot be in the future because roster status changes immediately';
  end if;
  if v_reactivated_on > current_date then
    raise exception 'reactivated_at cannot be in the future because roster status changes immediately';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  perform set_config('app.change_reason', v_reason, true);

  if v_worker_id is null then
    if p_expected_version is not null then
      raise exception 'expected_version must be null when creating a worker';
    end if;
    if v_initial_rate < 0 then
      raise exception 'initial_daily_rate cannot be negative';
    end if;
    if v_rate_from > v_joined_at then
      raise exception 'Initial daily rate must cover the worker start date';
    end if;
    if exists (
      select 1
      from erp.attendance_periods p
      where p.contractor_id = v_contractor_id
        and p.status in ('POSTED','CORRECTED')
        and daterange(p.period_start, p.period_end + 1, '[)')
            && daterange(v_joined_at, coalesce(v_left_at + 1, 'infinity'::date), '[)')
    ) then
      raise exception 'A new worker start cannot overlap posted attendance history; reverse/correct roster chronology first';
    end if;

    insert into erp.contractor_workers(
      contractor_id, worker_code, worker_name, job_description, pay_scheme,
      daily_rate, is_active, joined_at, left_at, notes, created_by, updated_by
    ) values (
      v_contractor_id, nullif(btrim(p_payload->>'worker_code'), ''), v_worker_name,
      v_job_description, v_pay_scheme,
      v_initial_rate, v_is_active, v_joined_at, v_left_at,
      nullif(btrim(p_payload->>'notes'), ''),
      erp.current_app_user_id(), erp.current_app_user_id()
    ) returning id into v_worker_id;

    perform set_config('app.worker_rate_write', 'on', true);
    insert into erp.worker_daily_rate_versions(
      worker_id, daily_rate, effective_from, change_reason, created_by
    ) values (
      v_worker_id, v_initial_rate, v_rate_from, v_reason, erp.current_app_user_id()
    );

    perform set_config('app.worker_employment_write', 'on', true);
    insert into erp.worker_employment_periods(
      worker_id, started_on, ended_on, start_reason, end_reason,
      created_by, ended_by, ended_at
    ) values (
      v_worker_id, v_joined_at, v_left_at, v_reason,
      case when v_left_at is null then null else v_reason end,
      erp.current_app_user_id(),
      case when v_left_at is null then null else erp.current_app_user_id() end,
      case when v_left_at is null then null else clock_timestamp() end
    );
  else
    select * into v_existing
    from erp.contractor_workers
    where id = v_worker_id
    for update;

    if v_existing.id is null then raise exception 'Worker not found'; end if;
    if p_expected_version is null or v_existing.row_version <> p_expected_version then
      raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_existing.row_version;
    end if;
    if v_existing.contractor_id <> v_contractor_id then
      raise exception 'A worker cannot be moved between contractors; create a new roster identity';
    end if;
    if v_pay_scheme is distinct from v_existing.pay_scheme and exists (
      select 1
      from erp.attendance_periods p
      join erp.worker_employment_periods e on e.worker_id = v_worker_id
      where p.contractor_id = v_contractor_id
        and p.status in ('POSTED','CORRECTED')
        and daterange(p.period_start, p.period_end + 1, '[)')
            && daterange(e.started_on, coalesce(e.ended_on + 1, 'infinity'::date), '[)')
    ) then
      raise exception 'Worker pay_scheme cannot change across posted attendance history';
    end if;
    if v_joined_at is distinct from v_existing.joined_at then
      raise exception 'Original worker start date is immutable; use employment episodes for reactivation';
    end if;
    if v_joined_at is not null and v_joined_at < (
      select min(r.effective_from)
      from erp.worker_daily_rate_versions r
      where r.worker_id = v_worker_id
    ) then
      raise exception 'Worker start date cannot precede the first daily-rate version';
    end if;
    if exists (
      select 1
      from erp.attendance_records a
      where a.worker_id = v_worker_id
        and (a.attendance_date < v_joined_at
          or (v_left_at is not null and a.attendance_date > v_left_at))
    ) then
      raise exception 'Worker start/stop dates cannot exclude existing attendance history';
    end if;

    perform set_config('app.worker_employment_write', 'on', true);
    if v_existing.is_active and not v_is_active then
      update erp.worker_employment_periods e
      set ended_on = v_left_at,
          end_reason = v_reason,
          ended_by = erp.current_app_user_id(),
          ended_at = clock_timestamp()
      where e.worker_id = v_worker_id and e.ended_on is null;
      if not found then
        raise exception 'Active worker has no open employment episode';
      end if;
    elsif not v_existing.is_active and v_is_active then
      if v_reactivated_on is null then
        raise exception 'reactivated_at is required when activating a stopped worker';
      end if;
      if v_reactivated_on <= coalesce((
        select max(e.ended_on) from erp.worker_employment_periods e where e.worker_id = v_worker_id
      ), '-infinity'::date) then
        raise exception 'reactivated_at must be after the previous employment stop date';
      end if;
      if exists (
        select 1
        from erp.attendance_periods p
        where p.contractor_id = v_contractor_id
          and p.status in ('POSTED','CORRECTED')
          and daterange(p.period_start, p.period_end + 1, '[)')
              && daterange(v_reactivated_on, 'infinity'::date, '[)')
      ) then
        raise exception 'A reactivation start cannot overlap posted attendance history; reverse/correct roster chronology first';
      end if;
      perform erp.require_worker_daily_rate_at(v_worker_id, v_reactivated_on);
      insert into erp.worker_employment_periods(
        worker_id, started_on, start_reason, created_by
      ) values (
        v_worker_id, v_reactivated_on, v_reason, erp.current_app_user_id()
      );
    elsif not v_existing.is_active and not v_is_active
          and v_left_at is distinct from v_existing.left_at then
      raise exception 'Stopped employment date is historical; reactivate then create a new episode';
    end if;

    update erp.contractor_workers
    set worker_code = nullif(btrim(p_payload->>'worker_code'), ''),
        worker_name = v_worker_name,
        job_description = v_job_description,
        pay_scheme = v_pay_scheme,
        is_active = v_is_active,
        joined_at = v_joined_at,
        left_at = v_left_at,
        notes = nullif(btrim(p_payload->>'notes'), ''),
        updated_by = erp.current_app_user_id()
    where id = v_worker_id;
  end if;

  select jsonb_build_object(
    'worker_id', w.id,
    'contractor_id', w.contractor_id,
    'worker_name', w.worker_name,
    'job_description', w.job_description,
    'pay_scheme', w.pay_scheme,
    'daily_rate', erp.worker_daily_rate_at(w.id, current_date),
    'is_active', w.is_active,
    'joined_at', w.joined_at,
    'left_at', w.left_at,
    'reactivated_at', (
      select max(e.started_on) from erp.worker_employment_periods e where e.worker_id = w.id
    ),
    'notes', w.notes,
    'row_version', w.row_version
  ) into v_response
  from erp.contractor_workers w
  where w.id = v_worker_id;

  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

-- ---------------------------------------------------------------------------
-- 2. Attendance period/header lifecycle and immutable payroll snapshots
-- ---------------------------------------------------------------------------

create table if not exists erp.attendance_periods (
  id uuid primary key default gen_random_uuid(),
  period_number varchar(80) not null unique,
  contractor_id uuid not null references erp.contractors(id),
  period_start date not null,
  period_end date not null,
  pay_date date not null,
  status varchar(20) not null default 'DRAFT'
    check (status in ('DRAFT','POSTED','CORRECTED','REVERSED')),
  correction_of_period_id uuid references erp.attendance_periods(id),
  notes text,
  posting_reason text,
  reversal_reason text,
  created_by uuid references erp.app_users(id),
  posted_by uuid references erp.app_users(id),
  reversed_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  posted_at timestamptz,
  reversed_at timestamptz,
  row_version bigint not null default 1 check (row_version > 0),
  constraint attendance_periods_dates_check check (period_end >= period_start),
  constraint attendance_periods_correction_self_check
    check (correction_of_period_id is null or correction_of_period_id <> id)
);

create index if not exists idx_attendance_periods_contractor_dates
  on erp.attendance_periods(contractor_id, period_start desc, period_end desc);

create or replace function erp.guard_attendance_period_overlap()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
begin
  perform pg_advisory_xact_lock(hashtextextended('ATTENDANCE_PERIOD|' || new.contractor_id::text, 0));

  if new.status <> 'REVERSED' and exists (
    select 1
    from erp.attendance_periods p
    where p.contractor_id = new.contractor_id
      and p.id <> new.id
      and p.status in ('DRAFT','POSTED')
      and p.id is distinct from new.correction_of_period_id
      and p.correction_of_period_id is distinct from new.id
      and daterange(p.period_start, p.period_end + 1, '[)')
          && daterange(new.period_start, new.period_end + 1, '[)')
  ) then
    raise exception 'Active attendance periods for one contractor cannot overlap';
  end if;
  return new;
end;
$function$;

create or replace function erp.guard_attendance_period_lifecycle()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
begin
  if tg_op = 'DELETE' then
    raise exception 'Attendance periods cannot be deleted; reverse them with a reason';
  end if;

  if old.status <> 'DRAFT'
     and current_setting('app.attendance_period_lifecycle', true) is distinct from 'on' then
    raise exception 'Posted attendance is immutable; use correction/reversal workflow';
  end if;

  if old.status = 'DRAFT' and new.status not in ('DRAFT','POSTED','REVERSED')
     and current_setting('app.attendance_period_lifecycle', true) is distinct from 'on' then
    raise exception 'Invalid attendance lifecycle transition';
  end if;

  return new;
end;
$function$;

drop trigger if exists trg_00_attendance_period_row_version on erp.attendance_periods;
create trigger trg_00_attendance_period_row_version
before update on erp.attendance_periods
for each row execute function erp.bump_row_version();

drop trigger if exists trg_attendance_period_touch on erp.attendance_periods;
create trigger trg_attendance_period_touch
before update on erp.attendance_periods
for each row execute function erp.touch_updated_at();

drop trigger if exists trg_attendance_period_overlap on erp.attendance_periods;
create trigger trg_attendance_period_overlap
before insert or update of contractor_id, period_start, period_end, status
on erp.attendance_periods
for each row execute function erp.guard_attendance_period_overlap();

drop trigger if exists trg_guard_attendance_period_lifecycle on erp.attendance_periods;
create trigger trg_guard_attendance_period_lifecycle
before update or delete on erp.attendance_periods
for each row execute function erp.guard_attendance_period_lifecycle();

drop trigger if exists trg_audit_attendance_periods on erp.attendance_periods;
create trigger trg_audit_attendance_periods
after insert or update or delete on erp.attendance_periods
for each row execute function erp.audit_row_change();

alter table erp.attendance_records
  add column if not exists attendance_period_id uuid references erp.attendance_periods(id),
  add column if not exists record_lifecycle varchar(20),
  add column if not exists supersedes_attendance_record_id uuid references erp.attendance_records(id),
  add column if not exists row_version bigint not null default 1,
  add column if not exists created_by uuid references erp.app_users(id),
  add column if not exists updated_by uuid references erp.app_users(id),
  add column if not exists change_reason text;

alter table erp.attendance_records
  drop constraint if exists attendance_records_row_version_check;
alter table erp.attendance_records
  add constraint attendance_records_row_version_check check (row_version > 0);

alter table erp.attendance_records
  drop constraint if exists attendance_records_lifecycle_check;
alter table erp.attendance_records
  add constraint attendance_records_lifecycle_check
  check (record_lifecycle is null or record_lifecycle in ('DRAFT','POSTED','CORRECTED','REVERSED'));

-- Legacy rows keep record_lifecycle NULL and remain current posted facts. New
-- periods use explicit lifecycle values so a correction can coexist as DRAFT
-- without rewriting the original attendance fact.
alter table erp.attendance_records
  drop constraint if exists attendance_records_worker_id_attendance_date_key;

create unique index if not exists uq_attendance_current_worker_date
  on erp.attendance_records(worker_id, attendance_date)
  where record_lifecycle is null or record_lifecycle = 'POSTED';

create unique index if not exists uq_attendance_period_worker_date
  on erp.attendance_records(attendance_period_id, worker_id, attendance_date)
  where attendance_period_id is not null;

create index if not exists idx_attendance_records_period_worker_date
  on erp.attendance_records(attendance_period_id, worker_id, attendance_date);

create or replace function erp.guard_attendance_record_period_and_dates()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
declare
  v_worker erp.contractor_workers%rowtype;
  v_period erp.attendance_periods%rowtype;
  v_existing_period_id uuid := case when tg_op = 'INSERT' then null else old.attendance_period_id end;
begin
  if tg_op = 'DELETE' then
    if v_existing_period_id is not null then
      select * into v_period from erp.attendance_periods where id = v_existing_period_id;
      if v_period.status <> 'DRAFT' then
        raise exception 'Posted attendance details cannot be deleted';
      end if;
    end if;
    return old;
  end if;

  if tg_op = 'INSERT' and new.attendance_period_id is null
     and new.record_lifecycle is not null then
    raise exception 'New attendance rows require an attendance period';
  end if;

  select * into v_worker from erp.contractor_workers where id = new.worker_id;
  if v_worker.id is null or v_worker.contractor_id <> new.contractor_id then
    raise exception 'Worker does not belong to selected contractor';
  end if;
  if not erp.worker_is_employed_on(new.worker_id, new.attendance_date) then
    raise exception 'Attendance date is outside the worker employment periods';
  end if;

  if new.attendance_period_id is not null then
    select * into v_period
    from erp.attendance_periods
    where id = new.attendance_period_id;

    if v_period.id is null then raise exception 'Attendance period not found'; end if;
    if v_period.status <> 'DRAFT'
       and current_setting('app.attendance_period_lifecycle', true) is distinct from 'on' then
      raise exception 'Posted attendance details are immutable';
    end if;
    if v_period.contractor_id <> new.contractor_id then
      raise exception 'Attendance record contractor does not match its period';
    end if;
    if new.attendance_date not between v_period.period_start and v_period.period_end then
      raise exception 'Attendance date is outside its period';
    end if;
  end if;

  if tg_op = 'UPDATE' and v_existing_period_id is not null then
    select * into v_period from erp.attendance_periods where id = v_existing_period_id;
    if v_period.status <> 'DRAFT'
       and current_setting('app.attendance_period_lifecycle', true) is distinct from 'on' then
      raise exception 'Posted attendance details are immutable';
    end if;
  end if;

  return new;
end;
$function$;

drop trigger if exists trg_00_attendance_row_version on erp.attendance_records;
create trigger trg_00_attendance_row_version
before update on erp.attendance_records
for each row execute function erp.bump_row_version();

drop trigger if exists trg_guard_attendance_record_period_and_dates
  on erp.attendance_records;
create trigger trg_guard_attendance_record_period_and_dates
before insert or update or delete on erp.attendance_records
for each row execute function erp.guard_attendance_record_period_and_dates();

create or replace function erp.save_attendance_period_v1(
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_version bigint default null,
  p_preview_only boolean default false
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'save_attendance_period_v1';
  v_hash text;
  v_cached jsonb;
  v_period_id uuid := nullif(p_payload->>'period_id', '')::uuid;
  v_contractor_id uuid := nullif(p_payload->>'contractor_id', '')::uuid;
  v_period_number text := nullif(btrim(p_payload->>'period_number'), '');
  v_period_start date := nullif(p_payload->>'period_start', '')::date;
  v_period_end date := nullif(p_payload->>'period_end', '')::date;
  v_pay_date date := nullif(p_payload->>'pay_date', '')::date;
  v_correction_of uuid := nullif(p_payload->>'correction_of_period_id', '')::uuid;
  v_reason text := nullif(btrim(p_payload->>'reason'), '');
  v_lines jsonb := coalesce(p_payload->'attendance', '[]'::jsonb);
  v_period erp.attendance_periods%rowtype;
  v_original erp.attendance_periods%rowtype;
  v_preview jsonb;
  v_response jsonb;
  v_duplicate_count integer;
  r record;
begin
  perform erp.require_internal();

  if v_contractor_id is null or v_period_number is null
     or v_period_start is null or v_period_end is null or v_pay_date is null then
    raise exception 'contractor_id, period_number, period_start, period_end, and pay_date are required';
  end if;
  if v_period_end < v_period_start then raise exception 'period_end cannot precede period_start'; end if;
  if v_reason is null then raise exception 'Attendance change reason is required'; end if;
  if jsonb_typeof(v_lines) <> 'array' then raise exception 'attendance must be a JSON array'; end if;
  if v_correction_of is not null then perform erp.require_owner_admin(); end if;
  if not exists (
    select 1 from erp.contractors c
    where c.id = v_contractor_id and c.contractor_type = 'MANDOR'
  ) then
    raise exception 'Attendance contractor must be an existing MANDOR';
  end if;

  select count(*) - count(distinct (x.worker_id::text || '|' || x.attendance_date::text))
  into v_duplicate_count
  from jsonb_to_recordset(v_lines) as x(
    worker_id uuid,
    attendance_date date,
    status text,
    paid_fraction numeric,
    notes text,
    supersedes_attendance_record_id uuid
  );
  if v_duplicate_count > 0 then
    raise exception 'Duplicate worker/date exists in attendance payload';
  end if;

  for r in
    select *
    from jsonb_to_recordset(v_lines) as x(
      worker_id uuid,
      attendance_date date,
      status text,
      paid_fraction numeric,
      notes text,
      supersedes_attendance_record_id uuid
    )
  loop
    if r.worker_id is null or r.attendance_date is null then
      raise exception 'Each attendance line requires worker_id and attendance_date';
    end if;
    if upper(coalesce(r.status, 'PRESENT')) not in
       ('PRESENT','ABSENT','HALF_DAY','SICK','LEAVE','OFF') then
      raise exception 'Unsupported attendance status %', r.status;
    end if;
    if r.paid_fraction is not null and (r.paid_fraction < 0 or r.paid_fraction > 1) then
      raise exception 'paid_fraction must be between 0 and 1';
    end if;
    if upper(coalesce(r.status, 'PRESENT')) = 'HALF_DAY'
       and coalesce(r.paid_fraction, 0.5) > 0.5 then
      raise exception 'HALF_DAY paid_fraction cannot exceed 0.5';
    end if;
    if r.attendance_date not between v_period_start and v_period_end then
      raise exception 'Attendance date % is outside period', r.attendance_date;
    end if;
    if not exists (
      select 1
      from erp.contractor_workers w
      where w.id = r.worker_id
        and w.contractor_id = v_contractor_id
        and erp.worker_is_employed_on(w.id, r.attendance_date)
    ) then
      raise exception 'Worker % is not eligible on %', r.worker_id, r.attendance_date;
    end if;
  end loop;

  select jsonb_build_object(
    'line_count', count(*),
    'paid_day_equivalent', coalesce(sum(
      case
        when upper(coalesce(x.status, 'PRESENT')) in ('ABSENT','OFF') then 0
        when upper(coalesce(x.status, 'PRESENT')) = 'HALF_DAY' then least(coalesce(x.paid_fraction, 0.5), 0.5)
        else coalesce(x.paid_fraction, 1)
      end
    ), 0),
    'estimated_amount', coalesce(sum(
      erp.require_worker_daily_rate_at(x.worker_id, x.attendance_date) *
      case
        when upper(coalesce(x.status, 'PRESENT')) in ('ABSENT','OFF') then 0
        when upper(coalesce(x.status, 'PRESENT')) = 'HALF_DAY' then least(coalesce(x.paid_fraction, 0.5), 0.5)
        else coalesce(x.paid_fraction, 1)
      end
    ), 0),
    'preview_only', p_preview_only
  ) into v_preview
  from jsonb_to_recordset(v_lines) as x(
    worker_id uuid,
    attendance_date date,
    status text,
    paid_fraction numeric,
    notes text,
    supersedes_attendance_record_id uuid
  );

  if p_preview_only then return v_preview; end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  perform set_config('app.change_reason', v_reason, true);

  if v_period_id is null then
    if p_expected_version is not null then
      raise exception 'expected_version must be null when creating an attendance period';
    end if;

    if v_correction_of is not null then
      select * into v_original
      from erp.attendance_periods
      where id = v_correction_of
      for update;

      if v_original.id is null or v_original.status <> 'POSTED' then
        raise exception 'Correction source must be a POSTED attendance period';
      end if;
      if v_original.contractor_id <> v_contractor_id
         or v_original.period_start <> v_period_start
         or v_original.period_end <> v_period_end then
        raise exception 'Correction must keep contractor and attendance date range';
      end if;
      if exists (
        select 1
        from erp.payroll_attendance_items pai
        join erp.payroll_settlements ps on ps.id = pai.payroll_id
        join erp.attendance_records ar on ar.id = pai.attendance_record_id
        where ar.attendance_period_id = v_original.id
          and ps.status <> 'REVERSED'
      ) then
        raise exception 'Attendance correction requires its consuming payroll to be reversed first';
      end if;
      if exists (
        select 1
        from erp.attendance_records source_row
        where source_row.attendance_period_id = v_original.id
          and not exists (
            select 1
            from jsonb_to_recordset(v_lines) as x(
              worker_id uuid,
              attendance_date date,
              status text,
              paid_fraction numeric,
              notes text,
              supersedes_attendance_record_id uuid
            )
            where x.worker_id = source_row.worker_id
              and x.attendance_date = source_row.attendance_date
              and x.supersedes_attendance_record_id = source_row.id
          )
      ) then
        raise exception 'Correction must explicitly supersede every source attendance row';
      end if;
    end if;

    insert into erp.attendance_periods(
      period_number, contractor_id, period_start, period_end, pay_date,
      correction_of_period_id, notes, created_by
    ) values (
      v_period_number, v_contractor_id, v_period_start, v_period_end, v_pay_date,
      v_correction_of, nullif(btrim(p_payload->>'notes'), ''), erp.current_app_user_id()
    ) returning * into v_period;
    v_period_id := v_period.id;
  else
    select * into v_period
    from erp.attendance_periods
    where id = v_period_id
    for update;

    if v_period.id is null then raise exception 'Attendance period not found'; end if;
    if v_period.status <> 'DRAFT' then
      raise exception 'Only DRAFT attendance can be saved';
    end if;
    if p_expected_version is null or v_period.row_version <> p_expected_version then
      raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_period.row_version;
    end if;
    if v_period.contractor_id <> v_contractor_id then
      raise exception 'Attendance contractor cannot be changed';
    end if;
    if v_period.correction_of_period_id is not null then
      perform erp.require_owner_admin();
      if v_correction_of is distinct from v_period.correction_of_period_id then
        raise exception 'correction_of_period_id cannot change or be omitted while editing a correction';
      end if;
    end if;
    if exists (
      select 1
      from erp.attendance_records a
      where a.attendance_period_id = v_period.id
        and a.attendance_date not between v_period_start and v_period_end
    ) then
      raise exception 'Attendance period cannot shrink while DRAFT rows exist outside the new date range';
    end if;

    update erp.attendance_periods
    set period_number = v_period_number,
        period_start = v_period_start,
        period_end = v_period_end,
        pay_date = v_pay_date,
        notes = nullif(btrim(p_payload->>'notes'), '')
    where id = v_period_id
    returning * into v_period;
  end if;

  if v_period.correction_of_period_id is null and exists (
    select 1
    from jsonb_to_recordset(v_lines) as x(
      worker_id uuid,
      attendance_date date,
      status text,
      paid_fraction numeric,
      notes text,
      supersedes_attendance_record_id uuid
    )
    where x.supersedes_attendance_record_id is not null
  ) then
    raise exception 'Non-correction attendance cannot declare supersedes lineage';
  end if;

  if v_period.correction_of_period_id is not null and exists (
    select 1
    from erp.attendance_records source_row
    where source_row.attendance_period_id = v_period.correction_of_period_id
      and not exists (
        select 1
        from jsonb_to_recordset(v_lines) as x(
          worker_id uuid,
          attendance_date date,
          status text,
          paid_fraction numeric,
          notes text,
          supersedes_attendance_record_id uuid
        )
        where x.worker_id = source_row.worker_id
          and x.attendance_date = source_row.attendance_date
          and x.supersedes_attendance_record_id = source_row.id
      )
  ) then
    raise exception 'Correction must explicitly supersede every source attendance row';
  end if;

  if v_period.correction_of_period_id is not null and exists (
    select 1
    from jsonb_to_recordset(v_lines) as x(
      worker_id uuid,
      attendance_date date,
      status text,
      paid_fraction numeric,
      notes text,
      supersedes_attendance_record_id uuid
    )
    where not exists (
      select 1
      from erp.attendance_records source_row
      where source_row.attendance_period_id = v_period.correction_of_period_id
        and source_row.id = x.supersedes_attendance_record_id
        and source_row.worker_id = x.worker_id
        and source_row.attendance_date = x.attendance_date
    )
  ) then
    raise exception 'Every correction line must supersede its exact source worker/date row';
  end if;

  for r in
    select *
    from jsonb_to_recordset(v_lines) as x(
      worker_id uuid,
      attendance_date date,
      status text,
      paid_fraction numeric,
      notes text,
      supersedes_attendance_record_id uuid
    )
  loop
    insert into erp.attendance_records(
      contractor_id, worker_id, attendance_date, status, paid_fraction, notes,
      attendance_period_id, record_lifecycle, supersedes_attendance_record_id,
      created_by, updated_by, change_reason
    ) values (
      v_contractor_id, r.worker_id, r.attendance_date,
      upper(coalesce(r.status, 'PRESENT')),
      case
        when upper(coalesce(r.status, 'PRESENT')) in ('ABSENT','OFF') then 0
        when upper(coalesce(r.status, 'PRESENT')) = 'HALF_DAY'
          then least(coalesce(r.paid_fraction, 0.5), 0.5)
        else coalesce(r.paid_fraction, 1)
      end,
      r.notes,
      v_period_id, 'DRAFT', r.supersedes_attendance_record_id,
      erp.current_app_user_id(), erp.current_app_user_id(), v_reason
    )
    on conflict (attendance_period_id, worker_id, attendance_date)
      where attendance_period_id is not null
    do update set
      status = excluded.status,
      paid_fraction = excluded.paid_fraction,
      notes = excluded.notes,
      supersedes_attendance_record_id = excluded.supersedes_attendance_record_id,
      updated_by = erp.current_app_user_id(),
      change_reason = v_reason;
  end loop;

  -- The payload is a full DRAFT matrix snapshot. A missing cell is unrecorded,
  -- never silently inferred as ABSENT/OFF. DRAFT-only removal is audited by the
  -- existing row audit trigger; POSTED history remains undeletable.
  delete from erp.attendance_records a
  where a.attendance_period_id = v_period_id
    and a.record_lifecycle = 'DRAFT'
    and not exists (
      select 1
      from jsonb_to_recordset(v_lines) as x(
        worker_id uuid,
        attendance_date date,
        status text,
        paid_fraction numeric,
        notes text,
        supersedes_attendance_record_id uuid
      )
      where x.worker_id = a.worker_id
        and x.attendance_date = a.attendance_date
    );

  -- Detail writes are part of the period document and advance its optimistic
  -- lock even when header fields did not change.
  if v_period.row_version = coalesce(p_expected_version, v_period.row_version) then
    update erp.attendance_periods
    set updated_at = clock_timestamp()
    where id = v_period_id
    returning * into v_period;
  else
    select * into v_period from erp.attendance_periods where id = v_period_id;
  end if;

  v_response := jsonb_build_object(
    'period_id', v_period.id,
    'period_number', v_period.period_number,
    'status', v_period.status,
    'row_version', v_period.row_version,
    'preview', v_preview - 'preview_only',
    'attendance_required', (
      select c.attendance_required from erp.contractors c where c.id = v_contractor_id
    )
  );

  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.post_attendance_period_v1(
  p_period_id uuid,
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
  v_operation constant text := 'post_attendance_period_v1';
  v_hash text;
  v_cached jsonb;
  v_period erp.attendance_periods%rowtype;
  v_original erp.attendance_periods%rowtype;
  v_response jsonb;
  v_missing_count bigint;
  v_uncovered_rate_count bigint;
begin
  perform erp.require_internal();
  if p_period_id is null or p_expected_version is null then
    raise exception 'period_id and expected_version are required';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'Attendance posting reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'period_id', p_period_id,
    'reason', p_reason,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_period
  from erp.attendance_periods
  where id = p_period_id
  for update;

  if v_period.id is null then raise exception 'Attendance period not found'; end if;
  if v_period.status <> 'DRAFT' then raise exception 'Only DRAFT attendance can be posted'; end if;
  if v_period.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_period.row_version;
  end if;

  if v_period.correction_of_period_id is not null then
    perform erp.require_owner_admin();
  end if;

  if (select attendance_required from erp.contractors where id = v_period.contractor_id)
     and not exists (
       select 1 from erp.attendance_records a where a.attendance_period_id = v_period.id
     ) then
    raise exception 'Attendance-required contractor needs attendance details before posting';
  end if;

  if (select attendance_required from erp.contractors where id = v_period.contractor_id) then
    select count(*) into v_missing_count
    from erp.contractor_workers w
    cross join lateral generate_series(
      v_period.period_start::timestamptz,
      v_period.period_end::timestamptz,
      interval '1 day'
    ) day_value
    where w.contractor_id = v_period.contractor_id
      and w.pay_scheme in ('DAILY','HYBRID')
      and erp.worker_is_employed_on(w.id, day_value::date)
      and not exists (
        select 1
        from erp.attendance_records a
        where a.attendance_period_id = v_period.id
          and a.worker_id = w.id
          and a.attendance_date = day_value::date
          and a.record_lifecycle = 'DRAFT'
      );

    if v_missing_count > 0 then
      raise exception 'Attendance period has % unrecorded eligible worker/day cells; blanks are not ABSENT or OFF',
        v_missing_count;
    end if;

    select count(*) into v_uncovered_rate_count
    from erp.contractor_workers w
    cross join lateral generate_series(
      v_period.period_start::timestamptz,
      v_period.period_end::timestamptz,
      interval '1 day'
    ) day_value
    where w.contractor_id = v_period.contractor_id
      and w.pay_scheme in ('DAILY','HYBRID')
      and erp.worker_is_employed_on(w.id, day_value::date)
      and erp.worker_daily_rate_at(w.id, day_value::date) is null;

    if v_uncovered_rate_count > 0 then
      raise exception 'Attendance period has % eligible worker/day cells without an effective daily rate',
        v_uncovered_rate_count;
    end if;
  end if;

  perform set_config('app.change_reason', p_reason, true);
  perform set_config('app.attendance_period_lifecycle', 'on', true);

  if v_period.correction_of_period_id is not null then
    select * into v_original
    from erp.attendance_periods
    where id = v_period.correction_of_period_id
    for update;

    if v_original.status <> 'POSTED' then
      raise exception 'Correction source is no longer POSTED';
    end if;
    if exists (
      select 1
      from erp.payroll_attendance_items pai
      join erp.payroll_settlements ps on ps.id = pai.payroll_id
      join erp.attendance_records ar on ar.id = pai.attendance_record_id
      where ar.attendance_period_id = v_original.id
        and ps.status <> 'REVERSED'
    ) then
      raise exception 'Attendance correction requires its consuming payroll to be reversed first';
    end if;
    if exists (
      select 1
      from erp.attendance_records source_row
      where source_row.attendance_period_id = v_original.id
        and not exists (
          select 1
          from erp.attendance_records replacement
          where replacement.attendance_period_id = v_period.id
            and replacement.worker_id = source_row.worker_id
            and replacement.attendance_date = source_row.attendance_date
            and replacement.supersedes_attendance_record_id = source_row.id
        )
    ) then
      raise exception 'Correction does not explicitly supersede every source attendance row';
    end if;

    update erp.attendance_records
    set record_lifecycle = 'CORRECTED',
        change_reason = p_reason,
        updated_by = erp.current_app_user_id()
    where attendance_period_id = v_original.id;

    update erp.attendance_periods
    set status = 'CORRECTED', posting_reason = p_reason
    where id = v_original.id;
  end if;

  if exists (
    select 1
    from erp.attendance_records draft_row
    join erp.attendance_records current_row
      on current_row.worker_id = draft_row.worker_id
     and current_row.attendance_date = draft_row.attendance_date
     and current_row.id <> draft_row.id
     and coalesce(current_row.record_lifecycle, 'POSTED') = 'POSTED'
    where draft_row.attendance_period_id = v_period.id
  ) then
    raise exception 'Another posted attendance fact already exists for worker/date';
  end if;

  update erp.attendance_records
  set record_lifecycle = 'POSTED',
      change_reason = p_reason,
      updated_by = erp.current_app_user_id()
  where attendance_period_id = v_period.id;

  update erp.attendance_periods
  set status = 'POSTED',
      posting_reason = p_reason,
      posted_at = clock_timestamp(),
      posted_by = erp.current_app_user_id()
  where id = v_period.id
  returning * into v_period;

  v_response := jsonb_build_object(
    'period_id', v_period.id,
    'status', v_period.status,
    'row_version', v_period.row_version,
    'posted_at', v_period.posted_at,
    'correction_of_period_id', v_period.correction_of_period_id
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.reverse_attendance_period_v1(
  p_period_id uuid,
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
  v_operation constant text := 'reverse_attendance_period_v1';
  v_hash text;
  v_cached jsonb;
  v_period erp.attendance_periods%rowtype;
  v_source erp.attendance_periods%rowtype;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  if p_period_id is null or p_expected_version is null then
    raise exception 'period_id and expected_version are required';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'Attendance reversal reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'period_id', p_period_id,
    'reason', p_reason,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_period
  from erp.attendance_periods
  where id = p_period_id
  for update;

  if v_period.id is null then raise exception 'Attendance period not found'; end if;
  if v_period.status <> 'POSTED' then raise exception 'Only POSTED attendance can be reversed'; end if;
  if v_period.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_period.row_version;
  end if;
  if exists (
    select 1
    from erp.payroll_attendance_items pai
    join erp.payroll_settlements ps on ps.id = pai.payroll_id
    join erp.attendance_records ar on ar.id = pai.attendance_record_id
    where ar.attendance_period_id = v_period.id
      and ps.status <> 'REVERSED'
  ) then
    raise exception 'Attendance reversal requires its consuming payroll to be reversed first';
  end if;

  perform set_config('app.change_reason', p_reason, true);
  perform set_config('app.attendance_period_lifecycle', 'on', true);

  if v_period.correction_of_period_id is not null then
    select * into v_source
    from erp.attendance_periods
    where id = v_period.correction_of_period_id
    for update;
    if v_source.id is null or v_source.status <> 'CORRECTED' then
      raise exception 'Correction source cannot be restored from status %', v_source.status;
    end if;
  end if;

  update erp.attendance_records
  set record_lifecycle = 'REVERSED',
      change_reason = p_reason,
      updated_by = erp.current_app_user_id()
  where attendance_period_id = v_period.id;

  if v_source.id is not null then
    update erp.attendance_records
    set record_lifecycle = 'POSTED',
        change_reason = 'Restored after correction reversal: ' || p_reason,
        updated_by = erp.current_app_user_id()
    where attendance_period_id = v_source.id
      and record_lifecycle = 'CORRECTED';

    update erp.attendance_periods
    set status = 'POSTED',
        posting_reason = 'Restored after correction reversal: ' || p_reason
    where id = v_source.id;
  end if;

  update erp.attendance_periods
  set status = 'REVERSED',
      reversal_reason = p_reason,
      reversed_at = clock_timestamp(),
      reversed_by = erp.current_app_user_id()
  where id = v_period.id
  returning * into v_period;

  v_response := jsonb_build_object(
    'period_id', v_period.id,
    'status', v_period.status,
    'row_version', v_period.row_version,
    'reversed_at', v_period.reversed_at,
    'restored_source_period_id', v_source.id
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

alter table erp.payroll_attendance_items
  add column if not exists worker_rate_version_id uuid references erp.worker_daily_rate_versions(id),
  add column if not exists attendance_date_snapshot date,
  add column if not exists worker_name_snapshot text,
  add column if not exists job_description_snapshot text;

create index if not exists idx_payroll_attendance_rate_version
  on erp.payroll_attendance_items(worker_rate_version_id)
  where worker_rate_version_id is not null;

-- Replace only the attendance-rate lookup in the existing payroll builder.
-- Every other payroll/HPP/deduction rule remains byte-for-byte equivalent in
-- behavior to the audited implementation.
create or replace function erp.populate_payroll_draft(p_payroll_id uuid)
returns void
language plpgsql
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  p erp.payroll_settlements%rowtype;
  r record;
  v_remaining numeric(24,6);
  v_apply numeric(24,6);
  v_budget numeric(24,6) := 0;
  v_attendance_required boolean;
begin
  perform erp.require_internal();
  select * into p from erp.payroll_settlements where id = p_payroll_id for update;
  if p.id is null or p.status not in ('DRAFT','CALCULATED','REVIEW') then
    raise exception 'Payroll draft cannot be rebuilt in current status';
  end if;
  perform pg_advisory_xact_lock(hashtextextended(p.contractor_id::text, 0));

  delete from erp.payroll_work_items where payroll_id = p.id;
  delete from erp.payroll_attendance_items where payroll_id = p.id;
  delete from erp.payroll_deductions
    where payroll_id = p.id and contractor_issue_item_id is not null;
  delete from erp.payroll_reimbursements
    where payroll_id = p.id and source_type = 'ACCESSORY_BOM';

  insert into erp.payroll_work_items(
    payroll_id, po_id, work_component_id, source_type, source_id,
    qty_payable, rate_snapshot
  )
  select p.id, e.po_id, e.work_component_id, e.source_type, e.source_id,
         e.remaining_qty, e.rate_snapshot
  from erp.v_payroll_eligible_work_lines e
  where e.contractor_id = p.contractor_id
    and e.eligible_at::date <= p.period_end
    and e.remaining_qty > 0
  order by e.eligible_at, e.source_type, e.source_id;

  select attendance_required into v_attendance_required
  from erp.contractors where id = p.contractor_id;

  if v_attendance_required then
    insert into erp.payroll_attendance_items(
      payroll_id, worker_id, attendance_record_id,
      paid_fraction_snapshot, daily_rate_snapshot,
      worker_rate_version_id, attendance_date_snapshot,
      worker_name_snapshot, job_description_snapshot
    )
    select
      p.id,
      ar.worker_id,
      ar.id,
      ar.paid_fraction,
      erp.require_worker_daily_rate_at(ar.worker_id, ar.attendance_date),
      erp.worker_daily_rate_version_id_at(ar.worker_id, ar.attendance_date),
      ar.attendance_date,
      cw.worker_name,
      cw.job_description
    from erp.attendance_records ar
    join erp.contractor_workers cw on cw.id = ar.worker_id
    left join erp.attendance_periods ap on ap.id = ar.attendance_period_id
    where ar.contractor_id = p.contractor_id
      and ar.attendance_date between p.period_start and p.period_end
      and cw.pay_scheme in ('DAILY','HYBRID')
      and ar.paid_fraction > 0
      and (ar.attendance_period_id is null or ap.status = 'POSTED')
      and coalesce(ar.record_lifecycle, 'POSTED') = 'POSTED'
    order by ar.attendance_date, ar.id;
  end if;

  insert into erp.payroll_reimbursements(
    payroll_id, amount, description, source_type, source_id, po_id
  )
  select p.id, round(e.amount, 2),
         'Accessory reimbursement from accepted GOOD FG',
         'ACCESSORY_BOM', e.id, e.po_id
  from erp.contractor_accessory_reimbursement_entitlements e
  where e.contractor_id = p.contractor_id
    and e.amount > 0
    and e.payroll_status <> 'CANCELLED'
    and e.physical_at::date <= p.period_end
    and not exists (
      select 1
      from erp.payroll_reimbursements pr
      join erp.payroll_settlements ps2 on ps2.id = pr.payroll_id
      where pr.source_type = 'ACCESSORY_BOM'
        and pr.source_id = e.id
        and ps2.id <> p.id
        and ps2.status <> 'REVERSED'
    )
  order by e.physical_at, e.id;

  update erp.contractor_accessory_reimbursement_entitlements e
  set payroll_status = 'ALLOCATED'
  where exists (
    select 1
    from erp.payroll_reimbursements pr
    where pr.payroll_id = p.id
      and pr.source_type = 'ACCESSORY_BOM'
      and pr.source_id = e.id
  );

  perform erp.recalculate_payroll(p.id);
  select greatest(net_payable, 0) into v_budget
  from erp.payroll_settlements where id = p.id;

  for r in
    select
      cmii.id,
      cmii.total_receivable,
      cmi.physical_at,
      cmii.total_receivable - coalesce((
        select sum(pd.amount)
        from erp.payroll_deductions pd
        join erp.payroll_settlements ps2 on ps2.id = pd.payroll_id
        where pd.contractor_issue_item_id = cmii.id
          and ps2.id <> p.id
          and ps2.status <> 'REVERSED'
      ), 0) as remaining_amount
    from erp.contractor_material_issue_items cmii
    join erp.contractor_material_issues cmi on cmi.id = cmii.issue_id
    where cmi.contractor_id = p.contractor_id
      and cmi.status = 'POSTED'
      and cmi.physical_at::date <= p.period_end
    order by cmi.physical_at, cmii.id
  loop
    exit when v_budget <= 0;
    v_remaining := greatest(r.remaining_amount, 0);
    v_apply := least(v_remaining, v_budget);
    if v_apply > 0 then
      insert into erp.payroll_deductions(
        payroll_id, deduction_type, contractor_issue_item_id, amount, notes
      ) values (
        p.id, 'MATERIAL_KASBON', r.id, round(v_apply, 2),
        'Auto capped outstanding material/accessory kasbon (FIFO)'
      );
      v_budget := greatest(v_budget - round(v_apply, 2), 0);
    end if;
  end loop;

  perform erp.recalculate_payroll(p.id);
  for r in
    select cmii.id
    from erp.contractor_material_issue_items cmii
    join erp.contractor_material_issues cmi on cmi.id = cmii.issue_id
    where cmi.contractor_id = p.contractor_id
      and cmi.status = 'POSTED'
  loop
    perform erp.refresh_contractor_issue_payroll_status(r.id);
  end loop;
end;
$function$;

-- ---------------------------------------------------------------------------
-- 3. Versioned stock policy + immutable explainability snapshots
-- ---------------------------------------------------------------------------

create table if not exists erp.stock_policy_versions (
  id uuid primary key default gen_random_uuid(),
  subject_type varchar(20) not null check (subject_type in ('FG','MATERIAL')),
  product_id uuid references erp.products(id),
  material_id uuid references erp.materials(id),
  location_id uuid references erp.locations(id),
  basis_source varchar(30) not null
    check (basis_source in ('BELUM_DIATUR','MANUAL','REKOMENDASI_SISTEM')),
  manual_reorder_point_qty numeric(24,6),
  manual_target_stock_qty numeric(24,6),
  minimum_sample_days integer not null default 30 check (minimum_sample_days > 0),
  effective_from date not null,
  effective_to date,
  reason text not null check (btrim(reason) <> ''),
  formula_version text not null default 'STOCK_EXPLAINABILITY_V1',
  approved_by uuid references erp.app_users(id),
  created_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  constraint stock_policy_subject_check check (
    (subject_type = 'FG' and product_id is not null and material_id is null)
    or (subject_type = 'MATERIAL' and material_id is not null and product_id is null)
  ),
  constraint stock_policy_dates_check
    check (effective_to is null or effective_to >= effective_from),
  constraint stock_policy_manual_values_check check (
    (basis_source = 'MANUAL'
      and manual_reorder_point_qty is not null
      and manual_target_stock_qty is not null
      and manual_reorder_point_qty >= 0
      and manual_target_stock_qty >= manual_reorder_point_qty)
    or (basis_source <> 'MANUAL'
      and manual_reorder_point_qty is null
      and manual_target_stock_qty is null)
  )
);

create index if not exists idx_stock_policy_fg_lookup
  on erp.stock_policy_versions(product_id, location_id, effective_from desc)
  where subject_type = 'FG';
create index if not exists idx_stock_policy_material_lookup
  on erp.stock_policy_versions(material_id, location_id, effective_from desc)
  where subject_type = 'MATERIAL';

create or replace function erp.guard_stock_policy_version()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
declare
  v_key text;
begin
  if current_setting('app.stock_policy_write', true) is distinct from 'on' then
    raise exception 'Stock policy history is write-protected; use erp_set_fg_stock_policy_v1';
  end if;

  if tg_op = 'DELETE' then
    raise exception 'Stock policy history cannot be deleted';
  end if;

  if tg_op = 'UPDATE'
     and (new.subject_type, new.product_id, new.material_id, new.location_id,
          new.basis_source, new.manual_reorder_point_qty,
          new.manual_target_stock_qty, new.minimum_sample_days,
          new.effective_from, new.reason, new.formula_version,
          new.approved_by, new.created_by, new.created_at)
         is distinct from
         (old.subject_type, old.product_id, old.material_id, old.location_id,
          old.basis_source, old.manual_reorder_point_qty,
          old.manual_target_stock_qty, old.minimum_sample_days,
          old.effective_from, old.reason, old.formula_version,
          old.approved_by, old.created_by, old.created_at) then
    raise exception 'Existing stock policy facts are immutable; only effective_to may be closed';
  end if;

  v_key := new.subject_type || '|' ||
    coalesce(new.product_id::text, new.material_id::text) || '|' ||
    coalesce(new.location_id::text, '*');
  perform pg_advisory_xact_lock(hashtextextended('STOCK_POLICY|' || v_key, 0));

  if exists (
    select 1
    from erp.stock_policy_versions p
    where p.subject_type = new.subject_type
      and p.id <> new.id
      and p.product_id is not distinct from new.product_id
      and p.material_id is not distinct from new.material_id
      and p.location_id is not distinct from new.location_id
      and daterange(p.effective_from, coalesce(p.effective_to + 1, 'infinity'::date), '[)')
          && daterange(new.effective_from, coalesce(new.effective_to + 1, 'infinity'::date), '[)')
  ) then
    raise exception 'Stock policy periods cannot overlap for the same item/location';
  end if;

  return new;
end;
$function$;

drop trigger if exists trg_guard_stock_policy_version on erp.stock_policy_versions;
create trigger trg_guard_stock_policy_version
before insert or update or delete on erp.stock_policy_versions
for each row execute function erp.guard_stock_policy_version();

drop trigger if exists trg_audit_stock_policy_versions on erp.stock_policy_versions;
create trigger trg_audit_stock_policy_versions
after insert or update or delete on erp.stock_policy_versions
for each row execute function erp.audit_row_change();

create or replace function erp.set_fg_stock_policy_v1(
  p_product_id uuid,
  p_location_id uuid,
  p_basis_source text,
  p_manual_reorder_point_qty numeric,
  p_manual_target_stock_qty numeric,
  p_minimum_sample_days integer,
  p_effective_from date,
  p_reason text,
  p_expected_policy_id uuid,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'set_fg_stock_policy_v1';
  v_basis text := upper(coalesce(nullif(btrim(p_basis_source), ''), 'BELUM_DIATUR'));
  v_hash text;
  v_cached jsonb;
  v_current erp.stock_policy_versions%rowtype;
  v_next_from date;
  v_new erp.stock_policy_versions%rowtype;
  v_response jsonb;
begin
  perform erp.require_owner_admin();

  if p_product_id is null or p_effective_from is null then
    raise exception 'product_id and effective_from are required';
  end if;
  if not exists (select 1 from erp.products p where p.id = p_product_id) then
    raise exception 'Finished-good product not found';
  end if;
  if p_location_id is not null and not exists (
    select 1 from erp.locations l
    where l.id = p_location_id and l.location_type = 'FG_WAREHOUSE'
  ) then
    raise exception 'FG stock policy location must be an FG warehouse';
  end if;
  if v_basis not in ('BELUM_DIATUR','MANUAL') then
    raise exception 'REKOMENDASI_SISTEM cannot be selected by a user before an authoritative recommendation snapshot exists';
  end if;
  if v_basis = 'MANUAL' and (
    p_manual_reorder_point_qty is null or p_manual_target_stock_qty is null
    or p_manual_reorder_point_qty < 0
    or p_manual_target_stock_qty < p_manual_reorder_point_qty
  ) then
    raise exception 'Manual policy requires target_stock >= reorder_point >= 0';
  end if;
  if v_basis = 'BELUM_DIATUR' and (
    p_manual_reorder_point_qty is not null or p_manual_target_stock_qty is not null
  ) then
    raise exception 'BELUM_DIATUR cannot carry manual threshold values';
  end if;
  if coalesce(p_minimum_sample_days, 30) <= 0 then
    raise exception 'minimum_sample_days must be positive';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'Stock policy reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'product_id', p_product_id,
    'location_id', p_location_id,
    'basis_source', v_basis,
    'manual_reorder_point_qty', p_manual_reorder_point_qty,
    'manual_target_stock_qty', p_manual_target_stock_qty,
    'minimum_sample_days', coalesce(p_minimum_sample_days, 30),
    'effective_from', p_effective_from,
    'reason', p_reason,
    'expected_policy_id', p_expected_policy_id
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  perform pg_advisory_xact_lock(hashtextextended(
    'STOCK_POLICY|FG|' || p_product_id::text || '|' || coalesce(p_location_id::text, '*'), 0
  ));

  select * into v_current
  from erp.stock_policy_versions p
  where p.subject_type = 'FG'
    and p.product_id = p_product_id
    and p.location_id is not distinct from p_location_id
    and p_effective_from >= p.effective_from
    and (p.effective_to is null or p_effective_from <= p.effective_to)
  order by p.effective_from desc, p.id desc
  limit 1
  for update;

  if v_current.id is distinct from p_expected_policy_id then
    raise exception 'STALE_POLICY expected %, current %', p_expected_policy_id, v_current.id;
  end if;
  if v_current.effective_from = p_effective_from then
    raise exception 'A stock policy already starts on this date; create a later effective version';
  end if;

  perform set_config('app.change_reason', p_reason, true);
  perform set_config('app.stock_policy_write', 'on', true);

  select min(p.effective_from) into v_next_from
  from erp.stock_policy_versions p
  where p.subject_type = 'FG'
    and p.product_id = p_product_id
    and p.location_id is not distinct from p_location_id
    and p.effective_from > p_effective_from;

  update erp.stock_policy_versions p
  set effective_to = p_effective_from - 1
  where p.subject_type = 'FG'
    and p.product_id = p_product_id
    and p.location_id is not distinct from p_location_id
    and p.effective_from < p_effective_from
    and (p.effective_to is null or p.effective_to >= p_effective_from);

  insert into erp.stock_policy_versions(
    subject_type, product_id, location_id, basis_source,
    manual_reorder_point_qty, manual_target_stock_qty, minimum_sample_days,
    effective_from, effective_to, reason, approved_by, created_by
  ) values (
    'FG', p_product_id, p_location_id, v_basis,
    case when v_basis = 'MANUAL' then p_manual_reorder_point_qty else null end,
    case when v_basis = 'MANUAL' then p_manual_target_stock_qty else null end,
    coalesce(p_minimum_sample_days, 30), p_effective_from,
    case when v_next_from is null then null else v_next_from - 1 end,
    p_reason, erp.current_app_user_id(), erp.current_app_user_id()
  ) returning * into v_new;

  v_response := jsonb_build_object(
    'policy_version_id', v_new.id,
    'product_id', v_new.product_id,
    'location_id', v_new.location_id,
    'basis_source', v_new.basis_source,
    'manual_reorder_point_qty', v_new.manual_reorder_point_qty,
    'manual_target_stock_qty', v_new.manual_target_stock_qty,
    'minimum_sample_days', v_new.minimum_sample_days,
    'effective_from', v_new.effective_from,
    'effective_to', v_new.effective_to,
    'formula_version', v_new.formula_version
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create table if not exists erp.stock_explainability_snapshots (
  id uuid primary key default gen_random_uuid(),
  subject_type varchar(20) not null check (subject_type in ('FG','MATERIAL')),
  product_id uuid references erp.products(id),
  material_id uuid references erp.materials(id),
  location_id uuid references erp.locations(id),
  calculated_at timestamptz not null default clock_timestamp(),
  source_as_of timestamptz not null,
  health_status varchar(30) not null check (health_status in (
    'BELUM_CUKUP_DATA','AMAN','RENDAH','PERLU_PESAN','PERLU_PRODUKSI','KRITIS'
  )),
  basis_source varchar(30) not null check (basis_source in (
    'BELUM_DIATUR','MANUAL','REKOMENDASI_SISTEM'
  )),
  policy_version_id uuid references erp.stock_policy_versions(id),
  physical_stock_qty numeric(24,6) not null,
  reserved_qty numeric(24,6) not null default 0,
  available_stock_qty numeric(24,6) not null,
  confirmed_incoming_qty numeric(24,6),
  projected_stock_qty numeric(24,6),
  average_daily_demand numeric(24,6),
  data_period_start date,
  data_period_end date,
  available_days integer,
  stockout_days integer,
  lead_time_days numeric(12,3),
  safety_stock_qty numeric(24,6),
  reorder_point_qty numeric(24,6),
  target_stock_qty numeric(24,6),
  recommended_qty numeric(24,6),
  confidence numeric(7,6),
  formula_version text not null,
  formula_expression text not null,
  source_manifest jsonb not null default '{}'::jsonb,
  calculation_key text not null unique,
  created_by uuid references erp.app_users(id),
  constraint stock_explainability_subject_check check (
    (subject_type = 'FG' and product_id is not null and material_id is null)
    or (subject_type = 'MATERIAL' and material_id is not null and product_id is null)
  ),
  constraint stock_explainability_balance_check
    check (physical_stock_qty = available_stock_qty + reserved_qty),
  constraint stock_explainability_nonnegative_check check (
    physical_stock_qty >= 0 and reserved_qty >= 0 and available_stock_qty >= 0
    and (confirmed_incoming_qty is null or confirmed_incoming_qty >= 0)
    and (recommended_qty is null or recommended_qty >= 0)
    and (confidence is null or (confidence >= 0 and confidence <= 1))
  ),
  constraint stock_explainability_projected_check check (
    projected_stock_qty is null
    or (confirmed_incoming_qty is not null
        and projected_stock_qty = available_stock_qty + confirmed_incoming_qty)
  ),
  constraint stock_explainability_period_check check (
    data_period_end is null or data_period_start is null
    or data_period_end >= data_period_start
  )
);

create index if not exists idx_stock_explainability_fg_latest
  on erp.stock_explainability_snapshots(product_id, location_id, calculated_at desc)
  where subject_type = 'FG';

create or replace function erp.guard_stock_explainability_immutable()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
begin
  raise exception 'Stock explainability snapshots are immutable; write a new snapshot';
end;
$function$;

drop trigger if exists trg_guard_stock_explainability_immutable
  on erp.stock_explainability_snapshots;
create trigger trg_guard_stock_explainability_immutable
before update or delete on erp.stock_explainability_snapshots
for each row execute function erp.guard_stock_explainability_immutable();

drop trigger if exists trg_audit_stock_explainability_snapshots
  on erp.stock_explainability_snapshots;
create trigger trg_audit_stock_explainability_snapshots
after insert or update or delete on erp.stock_explainability_snapshots
for each row execute function erp.audit_row_change();

create or replace view erp.v_fg_stock_position_v1
with (security_invoker = true)
as
with active_reservations as (
  select
    m.product_id,
    m.location_id,
    m.quality_grade,
    sum(abs(m.qty_signed))::bigint as reserved_qty_pcs
  from erp.fg_stock_movements m
  where m.movement_type = 'SALE_RESERVE'
    and not exists (
      select 1
      from erp.fg_stock_movements rv
      where rv.reversal_of_id = m.id
    )
  group by m.product_id, m.location_id, m.quality_grade
)
select
  b.product_id,
  b.location_id,
  b.quality_grade,
  (b.cached_qty_pcs + coalesce(r.reserved_qty_pcs, 0))::bigint as physical_stock_qty_pcs,
  coalesce(r.reserved_qty_pcs, 0)::bigint as reserved_qty_pcs,
  b.cached_qty_pcs::bigint as available_stock_qty_pcs,
  b.updated_at as stock_updated_at
from erp.fg_inventory_balances b
left join active_reservations r
  on r.product_id = b.product_id
 and r.location_id = b.location_id
 and r.quality_grade = b.quality_grade;

comment on view erp.v_fg_stock_position_v1 is
  'Authoritative FG position: cached_qty_pcs is already sellable/available after SALE_RESERVE; physical = available + active reservation. Never subtract reservation twice.';

-- ---------------------------------------------------------------------------
-- 4. Narrow public RPC facade (no direct erp schema/table exposure)
-- ---------------------------------------------------------------------------

create or replace function public.erp_save_worker_roster_v1(
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_version bigint default null
)
returns jsonb
language sql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
  select erp.save_worker_roster_v1(p_payload, p_client_request_id, p_expected_version)
$function$;

create or replace function public.erp_set_worker_daily_rate_v1(
  p_worker_id uuid,
  p_daily_rate numeric,
  p_effective_from date,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language sql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
  select erp.set_worker_daily_rate_v1(
    p_worker_id, p_daily_rate, p_effective_from, p_reason,
    p_client_request_id, p_expected_version
  )
$function$;

create or replace function public.erp_save_attendance_period_v1(
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_version bigint default null,
  p_preview_only boolean default false
)
returns jsonb
language sql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
  select erp.save_attendance_period_v1(
    p_payload, p_client_request_id, p_expected_version, p_preview_only
  )
$function$;

create or replace function public.erp_post_attendance_period_v1(
  p_period_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language sql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
  select erp.post_attendance_period_v1(
    p_period_id, p_reason, p_client_request_id, p_expected_version
  )
$function$;

create or replace function public.erp_reverse_attendance_period_v1(
  p_period_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language sql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
  select erp.reverse_attendance_period_v1(
    p_period_id, p_reason, p_client_request_id, p_expected_version
  )
$function$;

create or replace function public.erp_set_fg_stock_policy_v1(
  p_product_id uuid,
  p_location_id uuid,
  p_basis_source text,
  p_manual_reorder_point_qty numeric,
  p_manual_target_stock_qty numeric,
  p_minimum_sample_days integer,
  p_effective_from date,
  p_reason text,
  p_expected_policy_id uuid,
  p_client_request_id uuid
)
returns jsonb
language sql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
  select erp.set_fg_stock_policy_v1(
    p_product_id, p_location_id, p_basis_source,
    p_manual_reorder_point_qty, p_manual_target_stock_qty,
    p_minimum_sample_days, p_effective_from, p_reason,
    p_expected_policy_id, p_client_request_id
  )
$function$;

create or replace function public.erp_get_attendance_workspace_v1(
  p_contractor_id uuid,
  p_period_start date,
  p_period_end date,
  p_include_inactive boolean default false
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
declare
  v_result jsonb;
begin
  perform erp.require_internal();
  if p_contractor_id is null or p_period_start is null or p_period_end is null
     or p_period_end < p_period_start then
    raise exception 'Valid contractor_id, period_start, and period_end are required';
  end if;

  select jsonb_build_object(
    'contractor', jsonb_build_object(
      'id', c.id,
      'name', c.contractor_name,
      'attendance_required', c.attendance_required
    ),
    'period_start', p_period_start,
    'period_end', p_period_end,
    'workers', coalesce((
      select jsonb_agg(jsonb_build_object(
        'worker_id', w.id,
        'worker_code', w.worker_code,
        'worker_name', w.worker_name,
        'job_description', w.job_description,
        'pay_scheme', w.pay_scheme,
        'current_daily_rate', erp.worker_daily_rate_at(w.id, current_date),
        'joined_at', w.joined_at,
        'left_at', w.left_at,
        'is_active', w.is_active,
        'notes', w.notes,
        'row_version', w.row_version,
        'rate_versions', (
          select coalesce(jsonb_agg(to_jsonb(rv) order by rv.effective_from), '[]'::jsonb)
          from erp.worker_daily_rate_versions rv where rv.worker_id = w.id
        ),
        'employment_periods', (
          select coalesce(jsonb_agg(jsonb_build_object(
            'id', ep.id,
            'started_on', ep.started_on,
            'ended_on', ep.ended_on,
            'start_reason', ep.start_reason,
            'end_reason', ep.end_reason
          ) order by ep.started_on), '[]'::jsonb)
          from erp.worker_employment_periods ep where ep.worker_id = w.id
        ),
        'attendance', (
          select coalesce(jsonb_agg(jsonb_build_object(
            'id', a.id,
            'attendance_period_id', a.attendance_period_id,
            'attendance_date', a.attendance_date,
            'status', a.status,
            'record_lifecycle', coalesce(a.record_lifecycle, 'LEGACY_POSTED'),
            'supersedes_attendance_record_id', a.supersedes_attendance_record_id,
            'paid_fraction', a.paid_fraction,
            'notes', a.notes,
            'row_version', a.row_version
          ) order by a.attendance_date), '[]'::jsonb)
          from erp.attendance_records a
          where a.worker_id = w.id
            and a.attendance_date between p_period_start and p_period_end
        )
      ) order by w.worker_name, w.id)
      from erp.contractor_workers w
      where w.contractor_id = c.id
        and (p_include_inactive or w.is_active)
        and exists (
          select 1
          from erp.worker_employment_periods ep
          where ep.worker_id = w.id
            and daterange(ep.started_on, coalesce(ep.ended_on + 1, 'infinity'::date), '[)')
                && daterange(p_period_start, p_period_end + 1, '[)')
        )
    ), '[]'::jsonb),
    'periods', coalesce((
      select jsonb_agg(jsonb_build_object(
        'id', ap.id,
        'period_number', ap.period_number,
        'period_start', ap.period_start,
        'period_end', ap.period_end,
        'pay_date', ap.pay_date,
        'status', ap.status,
        'correction_of_period_id', ap.correction_of_period_id,
        'row_version', ap.row_version
      ) order by ap.period_start, ap.id)
      from erp.attendance_periods ap
      where ap.contractor_id = c.id
        and daterange(ap.period_start, ap.period_end + 1, '[)')
            && daterange(p_period_start, p_period_end + 1, '[)')
    ), '[]'::jsonb)
  ) into v_result
  from erp.contractors c
  where c.id = p_contractor_id;

  if v_result is null then raise exception 'Contractor not found'; end if;
  return v_result;
end;
$function$;

create or replace function public.erp_get_fg_stock_explainability_v1(
  p_product_id uuid default null,
  p_location_id uuid default null
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, pg_temp
as $function$
declare
  v_result jsonb;
begin
  perform erp.require_internal();

  with positions as (
    select p.*
    from erp.v_fg_stock_position_v1 p
    where (p_product_id is null or p.product_id = p_product_id)
      and (p_location_id is null or p.location_id = p_location_id)
      and p.quality_grade = 'GRADE_A'
  )
  select coalesce(jsonb_agg(jsonb_build_object(
    'product_id', p.product_id,
    'location_id', p.location_id,
    'quality_grade', p.quality_grade,
    'physical_stock_qty_pcs', p.physical_stock_qty_pcs,
    'reserved_qty_pcs', p.reserved_qty_pcs,
    'available_stock_qty_pcs', p.available_stock_qty_pcs,
    'confirmed_incoming_qty_pcs', null,
    'projected_stock_qty_pcs', null,
    'average_daily_demand', null,
    'lead_time_days', null,
    'safety_stock_qty_pcs', null,
    'reorder_point_qty_pcs', null,
    'recommended_qty_pcs', null,
    'health_status', 'BELUM_CUKUP_DATA',
    'basis_source', coalesce(policy.basis_source, 'BELUM_DIATUR'),
    'policy_version_id', policy.id,
    'manual_reorder_point_qty_pcs', policy.manual_reorder_point_qty,
    'manual_target_stock_qty_pcs', policy.manual_target_stock_qty,
    'minimum_sample_days', policy.minimum_sample_days,
    'confidence', null,
    'calculation_readiness', 'BLOCKED_AUTHORITATIVE_INPUTS',
    'manual_policy_status', case
      when policy.basis_source = 'MANUAL' then 'STORED_NOT_CALCULATED'
      else null
    end,
    'formula_version', 'STOCK_EXPLAINABILITY_V1_INPUTS_NOT_CONNECTED',
    'formula', 'physical = available + reserved; projected/demand/lead-time recommendation awaits authoritative adapters',
    'stock_updated_at', p.stock_updated_at,
    'calculated_at', null,
    'read_at', clock_timestamp(),
    'links', jsonb_build_object(
      'stock_movements', jsonb_build_object('product_id', p.product_id, 'location_id', p.location_id),
      'sale_reservations', jsonb_build_object('movement_type', 'SALE_RESERVE')
    )
  ) order by p.product_id, p.location_id, p.quality_grade), '[]'::jsonb)
  into v_result
  from positions p
  left join lateral (
    select sp.*
    from erp.stock_policy_versions sp
    where sp.subject_type = 'FG'
      and sp.product_id = p.product_id
      and (sp.location_id is null or sp.location_id = p.location_id)
      and current_date >= sp.effective_from
      and (sp.effective_to is null or current_date <= sp.effective_to)
    order by (sp.location_id is not null) desc, sp.effective_from desc, sp.id desc
    limit 1
  ) policy on true;

  return v_result;
end;
$function$;

-- New tables stay private. RLS is defense in depth, not an API grant.
alter table erp.worker_daily_rate_versions enable row level security;
alter table erp.worker_employment_periods enable row level security;
alter table erp.attendance_periods enable row level security;
alter table erp.stock_policy_versions enable row level security;
alter table erp.stock_explainability_snapshots enable row level security;

drop policy if exists internal_read on erp.worker_daily_rate_versions;
create policy internal_read on erp.worker_daily_rate_versions
for select to authenticated
using ((select erp.current_app_role()) in ('OWNER','ADMIN','STAFF'));

drop policy if exists internal_read on erp.worker_employment_periods;
create policy internal_read on erp.worker_employment_periods
for select to authenticated
using ((select erp.current_app_role()) in ('OWNER','ADMIN','STAFF'));

drop policy if exists internal_read on erp.attendance_periods;
create policy internal_read on erp.attendance_periods
for select to authenticated
using ((select erp.current_app_role()) in ('OWNER','ADMIN','STAFF'));

drop policy if exists internal_read on erp.stock_policy_versions;
create policy internal_read on erp.stock_policy_versions
for select to authenticated
using ((select erp.current_app_role()) in ('OWNER','ADMIN','STAFF'));

drop policy if exists internal_read on erp.stock_explainability_snapshots;
create policy internal_read on erp.stock_explainability_snapshots
for select to authenticated
using ((select erp.current_app_role()) in ('OWNER','ADMIN','STAFF'));

revoke all on erp.worker_daily_rate_versions from public, anon, authenticated;
revoke all on erp.worker_employment_periods from public, anon, authenticated;
revoke all on erp.attendance_periods from public, anon, authenticated;
revoke all on erp.stock_policy_versions from public, anon, authenticated;
revoke all on erp.stock_explainability_snapshots from public, anon, authenticated;
revoke all on erp.v_fg_stock_position_v1 from public, anon, authenticated;

grant all on erp.worker_daily_rate_versions to service_role;
grant all on erp.worker_employment_periods to service_role;
grant all on erp.attendance_periods to service_role;
grant all on erp.stock_policy_versions to service_role;
grant all on erp.stock_explainability_snapshots to service_role;
grant select on erp.v_fg_stock_position_v1 to service_role;

revoke execute on function public.erp_save_worker_roster_v1(
  jsonb, uuid, bigint
) from public, anon;
revoke execute on function public.erp_set_worker_daily_rate_v1(
  uuid, numeric, date, text, uuid, bigint
) from public, anon;
revoke execute on function public.erp_save_attendance_period_v1(
  jsonb, uuid, bigint, boolean
) from public, anon;
revoke execute on function public.erp_post_attendance_period_v1(
  uuid, text, uuid, bigint
) from public, anon;
revoke execute on function public.erp_reverse_attendance_period_v1(
  uuid, text, uuid, bigint
) from public, anon;
revoke execute on function public.erp_set_fg_stock_policy_v1(
  uuid, uuid, text, numeric, numeric, integer, date, text, uuid, uuid
) from public, anon;
revoke execute on function public.erp_get_attendance_workspace_v1(
  uuid, date, date, boolean
) from public, anon;
revoke execute on function public.erp_get_fg_stock_explainability_v1(
  uuid, uuid
) from public, anon;

grant execute on function public.erp_save_worker_roster_v1(
  jsonb, uuid, bigint
) to authenticated, service_role;
grant execute on function public.erp_set_worker_daily_rate_v1(
  uuid, numeric, date, text, uuid, bigint
) to authenticated, service_role;
grant execute on function public.erp_save_attendance_period_v1(
  jsonb, uuid, bigint, boolean
) to authenticated, service_role;
grant execute on function public.erp_post_attendance_period_v1(
  uuid, text, uuid, bigint
) to authenticated, service_role;
grant execute on function public.erp_reverse_attendance_period_v1(
  uuid, text, uuid, bigint
) to authenticated, service_role;
grant execute on function public.erp_set_fg_stock_policy_v1(
  uuid, uuid, text, numeric, numeric, integer, date, text, uuid, uuid
) to authenticated, service_role;
grant execute on function public.erp_get_attendance_workspace_v1(
  uuid, date, date, boolean
) to authenticated, service_role;
grant execute on function public.erp_get_fg_stock_explainability_v1(
  uuid, uuid
) to authenticated, service_role;

-- Internal helpers are never direct browser endpoints.
revoke execute on function erp.save_worker_roster_v1(jsonb, uuid, bigint)
  from public, anon, authenticated;
revoke execute on function erp.set_worker_daily_rate_v1(
  uuid, numeric, date, text, uuid, bigint
) from public, anon, authenticated;
revoke execute on function erp.worker_daily_rate_at(uuid, date)
  from public, anon, authenticated;
revoke execute on function erp.require_worker_daily_rate_at(uuid, date)
  from public, anon, authenticated;
revoke execute on function erp.worker_is_employed_on(uuid, date)
  from public, anon, authenticated;
revoke execute on function erp.worker_daily_rate_version_id_at(uuid, date)
  from public, anon, authenticated;
revoke execute on function erp.save_attendance_period_v1(jsonb, uuid, bigint, boolean)
  from public, anon, authenticated;
revoke execute on function erp.post_attendance_period_v1(uuid, text, uuid, bigint)
  from public, anon, authenticated;
revoke execute on function erp.reverse_attendance_period_v1(uuid, text, uuid, bigint)
  from public, anon, authenticated;
revoke execute on function erp.set_fg_stock_policy_v1(
  uuid, uuid, text, numeric, numeric, integer, date, text, uuid, uuid
) from public, anon, authenticated;

grant execute on function erp.save_worker_roster_v1(jsonb, uuid, bigint) to service_role;
grant execute on function erp.set_worker_daily_rate_v1(
  uuid, numeric, date, text, uuid, bigint
) to service_role;
grant execute on function erp.worker_daily_rate_at(uuid, date) to service_role;
grant execute on function erp.require_worker_daily_rate_at(uuid, date) to service_role;
grant execute on function erp.worker_is_employed_on(uuid, date) to service_role;
grant execute on function erp.worker_daily_rate_version_id_at(uuid, date) to service_role;
grant execute on function erp.save_attendance_period_v1(jsonb, uuid, bigint, boolean)
  to service_role;
grant execute on function erp.post_attendance_period_v1(uuid, text, uuid, bigint)
  to service_role;
grant execute on function erp.reverse_attendance_period_v1(uuid, text, uuid, bigint)
  to service_role;
grant execute on function erp.set_fg_stock_policy_v1(
  uuid, uuid, text, numeric, numeric, integer, date, text, uuid, uuid
) to service_role;

comment on table erp.worker_daily_rate_versions is
  'Effective-dated worker daily-rate facts. Payroll snapshots resolve by attendance date; history is never overwritten.';
comment on table erp.worker_employment_periods is
  'Effective-dated employment episodes for leave/rejoin gaps under one stable worker ID.';
comment on table erp.attendance_periods is
  'Attendance document header. DRAFT may change; POSTED/CORRECTED/REVERSED facts require lifecycle RPCs.';
comment on table erp.stock_policy_versions is
  'Effective-dated policy/basis history. Health status is deliberately not user-editable and lives only in calculated results.';
comment on table erp.stock_explainability_snapshots is
  'Immutable calculation evidence. Insert only after authoritative demand/incoming adapters exist; never fabricate inputs.';

notify pgrst, 'reload schema';

commit;
