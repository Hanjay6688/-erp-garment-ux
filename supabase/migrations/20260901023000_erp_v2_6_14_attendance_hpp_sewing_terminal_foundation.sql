-- ERP Garment v2.6.14a candidate
-- Attendance payroll cost pool allocated by immutable SELESAI_DIJAHIT facts.
--
-- CHECKPOINT 3 SOURCE-ONLY CANDIDATE.
-- DO NOT APPLY TO ERP ENTENG UAT UNTIL INDEPENDENT DELTA RE-AUDIT PASSES.
-- DO NOT APPLY TO ERP-GARMENT LEGACY/CANONICAL.
--
-- Deliberate boundaries:
--   * denominator is explicit immutable SELESAI_DIJAHIT, never QC GOOD/FG/laundry/rework;
--   * eligibility is role=M­ANDOR + attendance_required=true + explicit NOT Special;
--   * no public facade, no browser grant, no automatic hook into payroll/HPP/claim;
--   * no deferred validator; activation performs one bounded set-based validation;
--   * journal source credits retain exact original payroll debit-line lineage;
--   * timestamps inside the hashed manifest are epoch microseconds;
--   * active-pool cancellation owns reversal atomically; no manual pre-reversal;
--   * all JSON inputs are closed-contract, required-key, type, and NULL checked.

begin;

set local lock_timeout = '10s';
set local statement_timeout = '120s';

-- ---------------------------------------------------------------------------
-- 0. Exact prerequisite and replay guard
-- ---------------------------------------------------------------------------

do $guard$
begin
  if to_regclass('erp.contractors') is null
     or to_regclass('erp.work_completion_events') is null
     or to_regclass('erp.work_completion_lines') is null
     or to_regclass('erp.payroll_settlements') is null
     or to_regclass('erp.payroll_attendance_items') is null
     or to_regclass('erp.journal_entries') is null
     or to_regclass('erp.journal_lines') is null
     or to_regclass('erp.idempotency_requests') is null
     or to_regclass('erp.audit_logs') is null
     or to_regprocedure('erp.post_journal(text,uuid,date,text,jsonb)') is null
     or to_regprocedure('erp.reverse_journal(uuid,text)') is null
     or to_regprocedure('erp._request_hash(jsonb)') is null
     or to_regprocedure('erp._idempotency_begin(text,uuid,text)') is null
     or to_regprocedure('erp._idempotency_complete(text,uuid,jsonb)') is null then
    raise exception 'ERP v2.6.14a requires the v2.6.13 ERP Enteng contract before this additive candidate';
  end if;

  if exists (select 1 from erp.schema_migrations where version = 'v2.6.14a') then
    raise exception 'ERP v2.6.14a is already recorded; never replay or edit a recorded migration';
  end if;
end;
$guard$;

-- ---------------------------------------------------------------------------
-- 1. Strict JSON and deterministic manifest helpers
-- ---------------------------------------------------------------------------

create or replace function erp._cp3_assert_closed_json_object(
  p_value jsonb,
  p_required_keys text[],
  p_allowed_keys text[],
  p_label text
)
returns void
language plpgsql
immutable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_key text;
begin
  if p_value is null or jsonb_typeof(p_value) is distinct from 'object' then
    raise exception '% must be a JSON object', coalesce(p_label, 'payload');
  end if;

  foreach v_key in array coalesce(p_required_keys, array[]::text[])
  loop
    if not (p_value ? v_key)
       or coalesce(jsonb_typeof(p_value -> v_key), 'missing') = 'null' then
      raise exception '% requires non-null key %', coalesce(p_label, 'payload'), v_key;
    end if;
  end loop;

  select k into v_key
  from jsonb_object_keys(p_value) as x(k)
  where not (k = any(coalesce(p_allowed_keys, array[]::text[])))
  order by k
  limit 1;

  if v_key is not null then
    raise exception '% contains unexpected key %', coalesce(p_label, 'payload'), v_key;
  end if;
end;
$function$;

create or replace function erp._cp3_epoch_microseconds(p_value timestamptz)
returns bigint
language sql
immutable
security invoker
set search_path = erp, public, pg_temp
as $function$
  select case when p_value is null then null
    else floor(extract(epoch from p_value) * 1000000)::bigint end
$function$;

create or replace function erp._cp3_manifest_sha256(p_manifest jsonb)
returns text
language sql
immutable
security invoker
set search_path = erp, public, extensions, pg_temp
as $function$
  select encode(
    extensions.digest(convert_to(coalesce(p_manifest, '{}'::jsonb)::text, 'UTF8'), 'sha256'),
    'hex'
  )
$function$;

-- ---------------------------------------------------------------------------
-- 2. Explicit effective-dated Mandor HPP policy
-- ---------------------------------------------------------------------------

create table erp.contractor_hpp_policy_versions (
  id uuid primary key default gen_random_uuid(),
  contractor_id uuid not null references erp.contractors(id),
  effective_from date not null,
  effective_to date,
  contractor_role_snapshot varchar(30) not null,
  attendance_required_snapshot boolean not null,
  is_special boolean not null,
  reason text not null check (btrim(reason) <> ''),
  row_version bigint not null default 1 check (row_version > 0),
  created_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  constraint contractor_hpp_policy_dates_check
    check (effective_to is null or effective_to >= effective_from),
  constraint contractor_hpp_policy_role_check
    check (contractor_role_snapshot = 'MANDOR'),
  constraint contractor_hpp_policy_contractor_from_key
    unique (contractor_id, effective_from)
);

create index idx_contractor_hpp_policy_lookup
  on erp.contractor_hpp_policy_versions(contractor_id, effective_from desc, effective_to);

create or replace function erp.set_contractor_hpp_policy_v1(
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_policy_id uuid default null
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'set_contractor_hpp_policy_v1';
  v_hash text;
  v_cached jsonb;
  v_contractor_id uuid;
  v_effective_from date;
  v_is_special boolean;
  v_attendance_required boolean;
  v_reason text;
  v_contractor erp.contractors%rowtype;
  v_current erp.contractor_hpp_policy_versions%rowtype;
  v_next_from date;
  v_new erp.contractor_hpp_policy_versions%rowtype;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  perform erp._cp3_assert_closed_json_object(
    p_payload,
    array['contractor_id','effective_from','is_special','attendance_required','reason'],
    array['contractor_id','effective_from','is_special','attendance_required','reason'],
    'contractor HPP policy payload'
  );

  if jsonb_typeof(p_payload->'contractor_id') is distinct from 'string'
     or jsonb_typeof(p_payload->'effective_from') is distinct from 'string'
     or jsonb_typeof(p_payload->'is_special') is distinct from 'boolean'
     or jsonb_typeof(p_payload->'attendance_required') is distinct from 'boolean'
     or jsonb_typeof(p_payload->'reason') is distinct from 'string' then
    raise exception 'contractor HPP policy payload has invalid field types';
  end if;

  v_contractor_id := (p_payload->>'contractor_id')::uuid;
  v_effective_from := (p_payload->>'effective_from')::date;
  v_is_special := (p_payload->>'is_special')::boolean;
  v_attendance_required := (p_payload->>'attendance_required')::boolean;
  v_reason := nullif(btrim(p_payload->>'reason'), '');

  if v_reason is null then raise exception 'HPP policy reason is required'; end if;
  if v_effective_from is null then raise exception 'effective_from is required'; end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'expected_policy_id', p_expected_policy_id
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_contractor
  from erp.contractors
  where id = v_contractor_id
  for update;

  if v_contractor.id is null then raise exception 'Contractor not found'; end if;
  if v_contractor.contractor_type <> 'MANDOR' then
    raise exception 'Attendance HPP policy is only valid for role MANDOR';
  end if;
  if v_contractor.attendance_required is distinct from v_attendance_required then
    raise exception 'attendance_required payload must explicitly match contractor master; update master first, then write a new HPP policy version';
  end if;

  perform pg_advisory_xact_lock(hashtextextended('CONTRACTOR_HPP_POLICY|' || v_contractor_id::text, 0));

  select * into v_current
  from erp.contractor_hpp_policy_versions p
  where p.contractor_id = v_contractor_id
    and v_effective_from >= p.effective_from
    and (p.effective_to is null or v_effective_from <= p.effective_to)
  order by p.effective_from desc, p.id desc
  limit 1
  for update;

  if v_current.id is distinct from p_expected_policy_id then
    raise exception 'STALE_POLICY expected %, current %', p_expected_policy_id, v_current.id;
  end if;
  if v_current.effective_from = v_effective_from then
    raise exception 'A contractor HPP policy already starts on this date';
  end if;

  select min(p.effective_from) into v_next_from
  from erp.contractor_hpp_policy_versions p
  where p.contractor_id = v_contractor_id
    and p.effective_from > v_effective_from;

  update erp.contractor_hpp_policy_versions p
  set effective_to = v_effective_from - 1,
      row_version = row_version + 1
  where p.contractor_id = v_contractor_id
    and p.effective_from < v_effective_from
    and (p.effective_to is null or p.effective_to >= v_effective_from);

  insert into erp.contractor_hpp_policy_versions(
    contractor_id, effective_from, effective_to,
    contractor_role_snapshot, attendance_required_snapshot,
    is_special, reason, created_by
  ) values (
    v_contractor_id, v_effective_from,
    case when v_next_from is null then null else v_next_from - 1 end,
    'MANDOR', v_attendance_required,
    v_is_special, v_reason, erp.current_app_user_id()
  ) returning * into v_new;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'contractor_hpp_policy_versions', v_new.id, 'INSERT',
    jsonb_build_object(
      'contractor_id', v_new.contractor_id,
      'effective_from', v_new.effective_from,
      'effective_to', v_new.effective_to,
      'contractor_role_snapshot', v_new.contractor_role_snapshot,
      'attendance_required_snapshot', v_new.attendance_required_snapshot,
      'is_special', v_new.is_special
    ),
    erp.current_app_user_id(), v_reason
  );

  v_response := jsonb_build_object(
    'policy_version_id', v_new.id,
    'contractor_id', v_new.contractor_id,
    'effective_from', v_new.effective_from,
    'effective_to', v_new.effective_to,
    'contractor_role_snapshot', v_new.contractor_role_snapshot,
    'attendance_required_snapshot', v_new.attendance_required_snapshot,
    'is_special', v_new.is_special,
    'row_version', v_new.row_version
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

-- ---------------------------------------------------------------------------
-- 3. Immutable authoritative SELESAI_DIJAHIT events
-- ---------------------------------------------------------------------------

create table erp.sewing_terminal_events (
  id uuid primary key default gen_random_uuid(),
  event_number varchar(90) not null unique,
  event_kind varchar(30) not null
    check (event_kind in ('SELESAI_DIJAHIT','REVERSAL')),
  reversal_of_id uuid references erp.sewing_terminal_events(id),
  source_work_completion_id uuid references erp.work_completion_events(id),
  contractor_id uuid not null references erp.contractors(id),
  po_id uuid not null references erp.production_orders(id),
  cutting_group_id uuid references erp.cutting_groups(id),
  physical_at timestamptz not null,
  qty_signed integer not null check (qty_signed <> 0),
  reason text not null check (btrim(reason) <> ''),
  row_version bigint not null default 1 check (row_version > 0),
  created_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  constraint sewing_terminal_event_shape_check check (
    (event_kind = 'SELESAI_DIJAHIT'
      and reversal_of_id is null
      and source_work_completion_id is not null
      and qty_signed > 0)
    or
    (event_kind = 'REVERSAL'
      and reversal_of_id is not null
      and source_work_completion_id is null
      and qty_signed < 0)
  )
);

create unique index uq_sewing_terminal_source_completion
  on erp.sewing_terminal_events(source_work_completion_id)
  where event_kind = 'SELESAI_DIJAHIT';

create unique index uq_sewing_terminal_one_reversal
  on erp.sewing_terminal_events(reversal_of_id)
  where event_kind = 'REVERSAL';

create index idx_sewing_terminal_period_contractor
  on erp.sewing_terminal_events(physical_at, contractor_id, po_id, cutting_group_id);

create or replace function erp.record_sewing_terminal_v1(
  p_payload jsonb,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'record_sewing_terminal_v1';
  v_hash text;
  v_cached jsonb;
  v_work_completion_id uuid;
  v_qty integer;
  v_reason text;
  v_work erp.work_completion_events%rowtype;
  v_max_line_qty integer;
  v_cutting_qty bigint;
  v_existing_terminal_qty bigint;
  v_event erp.sewing_terminal_events%rowtype;
  v_response jsonb;
begin
  perform erp.require_internal();
  perform erp._cp3_assert_closed_json_object(
    p_payload,
    array['work_completion_id','qty_pcs','reason'],
    array['work_completion_id','qty_pcs','reason'],
    'SELESAI_DIJAHIT payload'
  );

  if jsonb_typeof(p_payload->'work_completion_id') is distinct from 'string'
     or jsonb_typeof(p_payload->'qty_pcs') is distinct from 'number'
     or jsonb_typeof(p_payload->'reason') is distinct from 'string' then
    raise exception 'SELESAI_DIJAHIT payload has invalid field types';
  end if;

  v_work_completion_id := (p_payload->>'work_completion_id')::uuid;
  v_qty := (p_payload->>'qty_pcs')::integer;
  v_reason := nullif(btrim(p_payload->>'reason'), '');

  if v_qty <= 0 then raise exception 'SELESAI_DIJAHIT qty must be positive'; end if;
  if v_reason is null then raise exception 'SELESAI_DIJAHIT reason is required'; end if;

  v_hash := erp._request_hash(jsonb_build_object('payload', p_payload));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_work
  from erp.work_completion_events
  where id = v_work_completion_id
  for update;

  if v_work.id is null then raise exception 'Work completion not found'; end if;
  if v_work.status <> 'POSTED' then
    raise exception 'SELESAI_DIJAHIT can only reference a POSTED production work completion';
  end if;
  if v_work.cutting_group_id is null then
    raise exception 'SELESAI_DIJAHIT requires cutting-group lineage';
  end if;
  if not exists (
    select 1 from erp.contractors c
    where c.id = v_work.contractor_id and c.contractor_type = 'MANDOR'
  ) then
    raise exception 'SELESAI_DIJAHIT source contractor must have explicit role MANDOR';
  end if;
  if exists (
    select 1 from erp.sewing_terminal_events e
    where e.source_work_completion_id = v_work.id
      and e.event_kind = 'SELESAI_DIJAHIT'
  ) then
    raise exception 'This work completion already has an authoritative SELESAI_DIJAHIT event';
  end if;

  select max(l.qty_completed)::integer into v_max_line_qty
  from erp.work_completion_lines l
  where l.completion_id = v_work.id;

  if coalesce(v_max_line_qty, 0) <= 0 or v_qty > v_max_line_qty then
    raise exception 'SELESAI_DIJAHIT qty % exceeds the maximum completed qty % recorded by the owning work completion',
      v_qty, coalesce(v_max_line_qty, 0);
  end if;

  perform 1 from erp.cutting_groups where id = v_work.cutting_group_id for update;
  select coalesce(v.total_pcs, 0)::bigint into v_cutting_qty
  from erp.v_cutting_group_totals v
  where v.cutting_group_id = v_work.cutting_group_id;

  select coalesce(sum(e.qty_signed), 0)::bigint into v_existing_terminal_qty
  from erp.sewing_terminal_events e
  where e.cutting_group_id = v_work.cutting_group_id;

  if v_existing_terminal_qty + v_qty > coalesce(v_cutting_qty, 0) then
    raise exception 'Cumulative SELESAI_DIJAHIT qty would exceed cutting-group physical qty. Current %, new %, maximum %',
      v_existing_terminal_qty, v_qty, coalesce(v_cutting_qty, 0);
  end if;

  insert into erp.sewing_terminal_events(
    event_number, event_kind, source_work_completion_id,
    contractor_id, po_id, cutting_group_id, physical_at,
    qty_signed, reason, created_by
  ) values (
    'SEW-' || to_char(v_work.physical_at at time zone 'UTC', 'YYYYMMDDHH24MISSUS') || '-' || substr(gen_random_uuid()::text, 1, 8),
    'SELESAI_DIJAHIT', v_work.id,
    v_work.contractor_id, v_work.po_id, v_work.cutting_group_id, v_work.physical_at,
    v_qty, v_reason, erp.current_app_user_id()
  ) returning * into v_event;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'sewing_terminal_events', v_event.id, 'POST',
    jsonb_build_object(
      'event_kind', v_event.event_kind,
      'source_work_completion_id', v_event.source_work_completion_id,
      'contractor_id', v_event.contractor_id,
      'po_id', v_event.po_id,
      'cutting_group_id', v_event.cutting_group_id,
      'physical_at_epoch_us', erp._cp3_epoch_microseconds(v_event.physical_at),
      'qty_signed', v_event.qty_signed
    ),
    erp.current_app_user_id(), v_reason
  );

  v_response := jsonb_build_object(
    'sewing_terminal_event_id', v_event.id,
    'event_number', v_event.event_number,
    'event_kind', v_event.event_kind,
    'source_work_completion_id', v_event.source_work_completion_id,
    'physical_at_epoch_us', erp._cp3_epoch_microseconds(v_event.physical_at),
    'qty_pcs', v_event.qty_signed,
    'row_version', v_event.row_version
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.reverse_sewing_terminal_v1(
  p_event_id uuid,
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
  v_operation constant text := 'reverse_sewing_terminal_v1';
  v_hash text;
  v_cached jsonb;
  v_original erp.sewing_terminal_events%rowtype;
  v_reversal erp.sewing_terminal_events%rowtype;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  if p_event_id is null or p_expected_version is null then
    raise exception 'event_id and expected_version are required';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'SELESAI_DIJAHIT reversal reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'event_id', p_event_id,
    'reason', btrim(p_reason),
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_original
  from erp.sewing_terminal_events
  where id = p_event_id
  for update;

  if v_original.id is null or v_original.event_kind <> 'SELESAI_DIJAHIT' then
    raise exception 'Original SELESAI_DIJAHIT event not found';
  end if;
  if v_original.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_original.row_version;
  end if;
  if exists (select 1 from erp.sewing_terminal_events where reversal_of_id = v_original.id) then
    raise exception 'SELESAI_DIJAHIT event is already reversed';
  end if;
  if exists (
    select 1
    from erp.attendance_hpp_pool_allocations a
    join erp.attendance_hpp_pools p on p.id = a.pool_id
    where a.sewing_terminal_event_id = v_original.id
      and p.status = 'ACTIVE'
  ) then
    raise exception 'SELESAI_DIJAHIT is consumed by an ACTIVE attendance HPP pool; cancel that pool first';
  end if;

  insert into erp.sewing_terminal_events(
    event_number, event_kind, reversal_of_id,
    contractor_id, po_id, cutting_group_id, physical_at,
    qty_signed, reason, created_by
  ) values (
    'SEW-RV-' || to_char(clock_timestamp() at time zone 'UTC', 'YYYYMMDDHH24MISSUS') || '-' || substr(gen_random_uuid()::text, 1, 8),
    'REVERSAL', v_original.id,
    v_original.contractor_id, v_original.po_id, v_original.cutting_group_id,
    v_original.physical_at, -v_original.qty_signed,
    btrim(p_reason), erp.current_app_user_id()
  ) returning * into v_reversal;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'sewing_terminal_events', v_original.id, 'REVERSE',
    jsonb_build_object(
      'reversal_event_id', v_reversal.id,
      'qty_signed', v_reversal.qty_signed,
      'original_physical_at_epoch_us', erp._cp3_epoch_microseconds(v_original.physical_at)
    ),
    erp.current_app_user_id(), btrim(p_reason)
  );

  v_response := jsonb_build_object(
    'original_event_id', v_original.id,
    'reversal_event_id', v_reversal.id,
    'status', 'REVERSED',
    'qty_reversed', v_original.qty_signed
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

-- ---------------------------------------------------------------------------
-- 4. Attendance HPP pool, exact source/debit lineage, and allocations
-- ---------------------------------------------------------------------------

create table erp.attendance_hpp_pools (
  id uuid primary key default gen_random_uuid(),
  pool_number varchar(90) not null unique,
  period_start date not null,
  period_end date not null,
  status varchar(20) not null default 'DRAFT'
    check (status in ('DRAFT','ACTIVE','CANCELLED')),
  correction_of_pool_id uuid references erp.attendance_hpp_pools(id),
  numerator_amount numeric(20,2) not null check (numerator_amount >= 0),
  denominator_qty bigint not null check (denominator_qty >= 0),
  unit_cost_per_sewn_pcs numeric(28,12),
  source_manifest jsonb not null,
  source_manifest_sha256 varchar(64) not null,
  post_journal_entry_id uuid references erp.journal_entries(id),
  cancellation_journal_entry_id uuid references erp.journal_entries(id),
  reason text not null check (btrim(reason) <> ''),
  cancellation_reason text,
  row_version bigint not null default 1 check (row_version > 0),
  created_by uuid references erp.app_users(id),
  activated_by uuid references erp.app_users(id),
  cancelled_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  activated_at timestamptz,
  cancelled_at timestamptz,
  constraint attendance_hpp_pool_dates_check check (period_end >= period_start),
  constraint attendance_hpp_pool_manifest_hash_check
    check (source_manifest_sha256 ~ '^[0-9a-f]{64}$'),
  constraint attendance_hpp_pool_positive_basis_check check (
    numerator_amount = 0 or denominator_qty > 0
  ),
  constraint attendance_hpp_pool_lifecycle_shape_check check (
    (status = 'DRAFT' and post_journal_entry_id is null and cancellation_journal_entry_id is null)
    or (status = 'ACTIVE' and post_journal_entry_id is not null and cancellation_journal_entry_id is null)
    or (status = 'CANCELLED' and post_journal_entry_id is not null and cancellation_journal_entry_id is not null)
  )
);

create unique index uq_attendance_hpp_one_active_period
  on erp.attendance_hpp_pools(period_start, period_end)
  where status = 'ACTIVE';

create index idx_attendance_hpp_pool_status_period
  on erp.attendance_hpp_pools(status, period_start, period_end);

create table erp.attendance_hpp_pool_sources (
  id uuid primary key default gen_random_uuid(),
  pool_id uuid not null references erp.attendance_hpp_pools(id),
  payroll_id uuid not null references erp.payroll_settlements(id),
  contractor_id uuid not null references erp.contractors(id),
  policy_version_id uuid not null references erp.contractor_hpp_policy_versions(id),
  original_debit_journal_line_id uuid not null references erp.journal_lines(id),
  contractor_role_snapshot varchar(30) not null check (contractor_role_snapshot = 'MANDOR'),
  attendance_required_snapshot boolean not null check (attendance_required_snapshot),
  is_special_snapshot boolean not null check (not is_special_snapshot),
  attendance_amount numeric(20,2) not null check (attendance_amount > 0),
  created_at timestamptz not null default clock_timestamp(),
  constraint attendance_hpp_pool_source_key unique (pool_id, payroll_id),
  constraint attendance_hpp_pool_source_debit_key unique (pool_id, original_debit_journal_line_id)
);

create index idx_attendance_hpp_pool_sources_payroll
  on erp.attendance_hpp_pool_sources(payroll_id, pool_id);

create table erp.attendance_hpp_pool_allocations (
  id uuid primary key default gen_random_uuid(),
  pool_id uuid not null references erp.attendance_hpp_pools(id),
  pool_source_id uuid not null references erp.attendance_hpp_pool_sources(id),
  sewing_terminal_event_id uuid not null references erp.sewing_terminal_events(id),
  contractor_id uuid not null references erp.contractors(id),
  po_id uuid not null references erp.production_orders(id),
  cutting_group_id uuid references erp.cutting_groups(id),
  sewing_qty integer not null check (sewing_qty > 0),
  allocated_amount numeric(20,2) not null check (allocated_amount >= 0),
  created_at timestamptz not null default clock_timestamp(),
  constraint attendance_hpp_pool_allocation_key
    unique (pool_source_id, sewing_terminal_event_id)
);

create index idx_attendance_hpp_allocations_pool_po
  on erp.attendance_hpp_pool_allocations(pool_id, po_id, cutting_group_id);

create table erp.attendance_hpp_journal_line_links (
  id uuid primary key default gen_random_uuid(),
  pool_id uuid not null references erp.attendance_hpp_pools(id),
  journal_line_id uuid not null references erp.journal_lines(id),
  link_type varchar(30) not null
    check (link_type in ('DESTINATION_DEBIT','SOURCE_CREDIT')),
  pool_source_id uuid references erp.attendance_hpp_pool_sources(id),
  original_debit_journal_line_id uuid references erp.journal_lines(id),
  po_id uuid references erp.production_orders(id),
  amount numeric(20,2) not null check (amount > 0),
  created_at timestamptz not null default clock_timestamp(),
  constraint attendance_hpp_journal_link_shape_check check (
    (link_type = 'DESTINATION_DEBIT'
      and po_id is not null
      and pool_source_id is null
      and original_debit_journal_line_id is null)
    or
    (link_type = 'SOURCE_CREDIT'
      and po_id is null
      and pool_source_id is not null
      and original_debit_journal_line_id is not null)
  ),
  constraint attendance_hpp_journal_line_link_key unique (pool_id, journal_line_id)
);

create or replace view erp.v_attendance_hpp_active_allocation_by_po
with (security_invoker = true)
as
select
  p.id as pool_id,
  p.period_start,
  p.period_end,
  a.po_id,
  sum(a.sewing_qty)::bigint as sewing_qty,
  sum(a.allocated_amount)::numeric(20,2) as attendance_hpp_amount
from erp.attendance_hpp_pools p
join erp.attendance_hpp_pool_allocations a on a.pool_id = p.id
where p.status = 'ACTIVE'
group by p.id, p.period_start, p.period_end, a.po_id;

-- ---------------------------------------------------------------------------
-- 5. Deterministic source manifest: closed operation, epoch timestamps
-- ---------------------------------------------------------------------------

create or replace function erp._build_attendance_hpp_manifest_v1(
  p_period_start date,
  p_period_end date
)
returns jsonb
language sql
stable
security definer
set search_path = erp, public, pg_temp
as $function$
with eligible_payrolls as (
  select
    ps.id as payroll_id,
    ps.contractor_id,
    ps.attendance_total::numeric(20,2) as attendance_amount,
    pol.id as policy_version_id,
    pol.contractor_role_snapshot,
    pol.attendance_required_snapshot,
    pol.is_special,
    pol.effective_from as policy_effective_from,
    pol.effective_to as policy_effective_to,
    jl.id as original_debit_journal_line_id,
    jl.debit::numeric(20,2) as original_debit_amount
  from erp.payroll_settlements ps
  join lateral (
    select p.*
    from erp.contractor_hpp_policy_versions p
    where p.contractor_id = ps.contractor_id
      and p.effective_from <= p_period_start
      and (p.effective_to is null or p.effective_to >= p_period_end)
    order by p.effective_from desc, p.id desc
    limit 1
  ) pol on true
  join lateral (
    select jl.*
    from erp.journal_entries je
    join erp.journal_lines jl on jl.journal_entry_id = je.id
    where je.source_id = ps.id
      and je.source_type in ('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL')
      and je.status = 'POSTED'
      and jl.account_id = erp.account_id('LABOR_COST')
      and jl.debit > 0
    order by case when je.source_type = 'PAYROLL_ATTENDANCE_ACCRUAL' then 0 else 1 end,
             je.posting_at, je.id, jl.id
    limit 1
  ) jl on true
  where ps.status = 'PAID'
    and ps.period_start = p_period_start
    and ps.period_end = p_period_end
    and ps.attendance_total > 0
    and pol.contractor_role_snapshot = 'MANDOR'
    and pol.attendance_required_snapshot
    and not pol.is_special
), eligible_sewing as (
  select
    e.id as sewing_terminal_event_id,
    e.source_work_completion_id,
    e.contractor_id,
    e.po_id,
    e.cutting_group_id,
    e.physical_at,
    e.qty_signed as sewing_qty,
    pol.id as policy_version_id,
    pol.contractor_role_snapshot,
    pol.attendance_required_snapshot,
    pol.is_special
  from erp.sewing_terminal_events e
  join erp.work_completion_events w on w.id = e.source_work_completion_id
  join lateral (
    select p.*
    from erp.contractor_hpp_policy_versions p
    where p.contractor_id = e.contractor_id
      and p.effective_from <= p_period_start
      and (p.effective_to is null or p.effective_to >= p_period_end)
    order by p.effective_from desc, p.id desc
    limit 1
  ) pol on true
  where e.event_kind = 'SELESAI_DIJAHIT'
    and e.physical_at::date between p_period_start and p_period_end
    and w.status = 'POSTED'
    and pol.contractor_role_snapshot = 'MANDOR'
    and pol.attendance_required_snapshot
    and not pol.is_special
    and not exists (
      select 1 from erp.sewing_terminal_events rv
      where rv.event_kind = 'REVERSAL' and rv.reversal_of_id = e.id
    )
), source_json as (
  select coalesce(jsonb_agg(jsonb_build_object(
    'payroll_id', payroll_id,
    'contractor_id', contractor_id,
    'policy_version_id', policy_version_id,
    'contractor_role_snapshot', contractor_role_snapshot,
    'attendance_required_snapshot', attendance_required_snapshot,
    'is_special_snapshot', is_special,
    'policy_effective_from', policy_effective_from::text,
    'policy_effective_to', policy_effective_to::text,
    'original_debit_journal_line_id', original_debit_journal_line_id,
    'original_debit_amount_cents', round(original_debit_amount * 100)::bigint,
    'attendance_amount_cents', round(attendance_amount * 100)::bigint
  ) order by contractor_id, payroll_id, original_debit_journal_line_id), '[]'::jsonb) value,
  coalesce(sum(round(attendance_amount * 100)::bigint), 0)::bigint numerator_cents
  from eligible_payrolls
), destination_json as (
  select coalesce(jsonb_agg(jsonb_build_object(
    'sewing_terminal_event_id', sewing_terminal_event_id,
    'source_work_completion_id', source_work_completion_id,
    'contractor_id', contractor_id,
    'po_id', po_id,
    'cutting_group_id', cutting_group_id,
    'policy_version_id', policy_version_id,
    'contractor_role_snapshot', contractor_role_snapshot,
    'attendance_required_snapshot', attendance_required_snapshot,
    'is_special_snapshot', is_special,
    'physical_at_epoch_us', erp._cp3_epoch_microseconds(physical_at),
    'sewing_qty', sewing_qty
  ) order by physical_at, sewing_terminal_event_id), '[]'::jsonb) value,
  coalesce(sum(sewing_qty), 0)::bigint denominator_qty
  from eligible_sewing
)
select jsonb_build_object(
  'contract_version', 'ATTENDANCE_HPP_SEWING_TERMINAL_V1',
  'operation_type', 'ATTENDANCE_HPP_POOL',
  'period_start', p_period_start::text,
  'period_end', p_period_end::text,
  'numerator_cents', source_json.numerator_cents,
  'denominator_qty', destination_json.denominator_qty,
  'sources', source_json.value,
  'destinations', destination_json.value
)
from source_json, destination_json
$function$;

create or replace function erp._assert_attendance_hpp_manifest_v1(p_manifest jsonb)
returns void
language plpgsql
immutable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_item jsonb;
begin
  perform erp._cp3_assert_closed_json_object(
    p_manifest,
    array['contract_version','operation_type','period_start','period_end','numerator_cents','denominator_qty','sources','destinations'],
    array['contract_version','operation_type','period_start','period_end','numerator_cents','denominator_qty','sources','destinations'],
    'attendance HPP manifest'
  );

  if p_manifest->>'contract_version' is distinct from 'ATTENDANCE_HPP_SEWING_TERMINAL_V1'
     or p_manifest->>'operation_type' is distinct from 'ATTENDANCE_HPP_POOL' then
    raise exception 'Attendance HPP manifest discriminator is invalid; claim/transfer/carry-forward/movement payloads are not accepted';
  end if;
  if jsonb_typeof(p_manifest->'sources') is distinct from 'array'
     or jsonb_typeof(p_manifest->'destinations') is distinct from 'array'
     or jsonb_typeof(p_manifest->'numerator_cents') is distinct from 'number'
     or jsonb_typeof(p_manifest->'denominator_qty') is distinct from 'number' then
    raise exception 'Attendance HPP manifest has invalid top-level types';
  end if;

  for v_item in select value from jsonb_array_elements(p_manifest->'sources')
  loop
    perform erp._cp3_assert_closed_json_object(
      v_item,
      array['payroll_id','contractor_id','policy_version_id','contractor_role_snapshot','attendance_required_snapshot','is_special_snapshot','policy_effective_from','policy_effective_to','original_debit_journal_line_id','original_debit_amount_cents','attendance_amount_cents'],
      array['payroll_id','contractor_id','policy_version_id','contractor_role_snapshot','attendance_required_snapshot','is_special_snapshot','policy_effective_from','policy_effective_to','original_debit_journal_line_id','original_debit_amount_cents','attendance_amount_cents'],
      'attendance HPP source'
    );
    if v_item->>'contractor_role_snapshot' is distinct from 'MANDOR'
       or (v_item->>'attendance_required_snapshot')::boolean is distinct from true
       or (v_item->>'is_special_snapshot')::boolean is distinct from false then
      raise exception 'Attendance HPP source is not an eligible normal Mandor snapshot';
    end if;
  end loop;

  for v_item in select value from jsonb_array_elements(p_manifest->'destinations')
  loop
    perform erp._cp3_assert_closed_json_object(
      v_item,
      array['sewing_terminal_event_id','source_work_completion_id','contractor_id','po_id','cutting_group_id','policy_version_id','contractor_role_snapshot','attendance_required_snapshot','is_special_snapshot','physical_at_epoch_us','sewing_qty'],
      array['sewing_terminal_event_id','source_work_completion_id','contractor_id','po_id','cutting_group_id','policy_version_id','contractor_role_snapshot','attendance_required_snapshot','is_special_snapshot','physical_at_epoch_us','sewing_qty'],
      'attendance HPP destination'
    );
    if v_item->>'contractor_role_snapshot' is distinct from 'MANDOR'
       or (v_item->>'attendance_required_snapshot')::boolean is distinct from true
       or (v_item->>'is_special_snapshot')::boolean is distinct from false then
      raise exception 'Attendance HPP destination is not an eligible normal Mandor snapshot';
    end if;
  end loop;
end;
$function$;

-- ---------------------------------------------------------------------------
-- 6. Preview/create: no journal, no HPP hook, exact-cent deterministic allocation
-- ---------------------------------------------------------------------------

create or replace function erp.preview_attendance_hpp_pool_v1(
  p_period_start date,
  p_period_end date
)
returns jsonb
language plpgsql
stable
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  v_manifest jsonb;
  v_missing_policy_count bigint;
  v_bad_attendance_snapshot_count bigint;
  v_bad_journal_count bigint;
  v_numerator_cents bigint;
  v_denominator_qty bigint;
begin
  perform erp.require_internal();
  if p_period_start is null or p_period_end is null or p_period_end < p_period_start then
    raise exception 'Valid period_start and period_end are required';
  end if;

  select count(*) into v_missing_policy_count
  from erp.payroll_settlements ps
  join erp.contractors c on c.id = ps.contractor_id
  where ps.status = 'PAID'
    and ps.period_start = p_period_start
    and ps.period_end = p_period_end
    and ps.attendance_total > 0
    and c.contractor_type = 'MANDOR'
    and not exists (
      select 1
      from erp.contractor_hpp_policy_versions p
      where p.contractor_id = ps.contractor_id
        and p.effective_from <= p_period_start
        and (p.effective_to is null or p.effective_to >= p_period_end)
    );
  if v_missing_policy_count > 0 then
    raise exception '% paid attendance payroll(s) lack one explicit HPP policy covering the full period', v_missing_policy_count;
  end if;

  select count(*) into v_bad_attendance_snapshot_count
  from erp.payroll_settlements ps
  where ps.status = 'PAID'
    and ps.period_start = p_period_start
    and ps.period_end = p_period_end
    and abs(ps.attendance_total - coalesce((
      select sum(pai.amount) from erp.payroll_attendance_items pai where pai.payroll_id = ps.id
    ), 0)) > 0.01;
  if v_bad_attendance_snapshot_count > 0 then
    raise exception '% payroll attendance total(s) do not reconcile to immutable attendance items', v_bad_attendance_snapshot_count;
  end if;

  select count(*) into v_bad_journal_count
  from erp.payroll_settlements ps
  join lateral (
    select count(*) as line_count, max(jl.debit) as debit_amount
    from erp.journal_entries je
    join erp.journal_lines jl on jl.journal_entry_id = je.id
    where je.source_id = ps.id
      and je.source_type in ('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL')
      and je.status = 'POSTED'
      and jl.account_id = erp.account_id('LABOR_COST')
      and jl.debit > 0
  ) x on true
  where ps.status = 'PAID'
    and ps.period_start = p_period_start
    and ps.period_end = p_period_end
    and ps.attendance_total > 0
    and (x.line_count <> 1 or x.debit_amount + 0.01 < ps.attendance_total);
  if v_bad_journal_count > 0 then
    raise exception '% paid attendance payroll(s) lack one unambiguous LABOR_COST debit line covering attendance amount', v_bad_journal_count;
  end if;

  v_manifest := erp._build_attendance_hpp_manifest_v1(p_period_start, p_period_end);
  perform erp._assert_attendance_hpp_manifest_v1(v_manifest);
  v_numerator_cents := (v_manifest->>'numerator_cents')::bigint;
  v_denominator_qty := (v_manifest->>'denominator_qty')::bigint;

  if v_numerator_cents <= 0 then
    raise exception 'No eligible normal-Mandor attendance payroll cost exists for this exact period';
  end if;
  if v_denominator_qty <= 0 then
    raise exception 'POSITIVE_POOL_ZERO_SEWING_OUTPUT: attendance cost exists but immutable SELESAI_DIJAHIT denominator is zero; keep cost unassigned/WIP and do not use QC GOOD fallback';
  end if;

  return jsonb_build_object(
    'status', 'READY',
    'manifest', v_manifest,
    'manifest_sha256', erp._cp3_manifest_sha256(v_manifest),
    'numerator_amount', v_numerator_cents / 100.0,
    'denominator_qty', v_denominator_qty,
    'unit_cost_per_sewn_pcs', (v_numerator_cents / 100.0) / v_denominator_qty
  );
end;
$function$;

create or replace function erp.create_attendance_hpp_pool_v1(
  p_payload jsonb,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'create_attendance_hpp_pool_v1';
  v_hash text;
  v_cached jsonb;
  v_period_start date;
  v_period_end date;
  v_reason text;
  v_correction_of uuid;
  v_preview jsonb;
  v_manifest jsonb;
  v_pool erp.attendance_hpp_pools%rowtype;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  perform erp._cp3_assert_closed_json_object(
    p_payload,
    array['period_start','period_end','reason'],
    array['period_start','period_end','reason','correction_of_pool_id'],
    'attendance HPP pool payload'
  );
  if jsonb_typeof(p_payload->'period_start') is distinct from 'string'
     or jsonb_typeof(p_payload->'period_end') is distinct from 'string'
     or jsonb_typeof(p_payload->'reason') is distinct from 'string'
     or (p_payload ? 'correction_of_pool_id'
         and coalesce(jsonb_typeof(p_payload->'correction_of_pool_id'), 'missing') not in ('string','null')) then
    raise exception 'Attendance HPP pool payload has invalid field types';
  end if;

  v_period_start := (p_payload->>'period_start')::date;
  v_period_end := (p_payload->>'period_end')::date;
  v_reason := nullif(btrim(p_payload->>'reason'), '');
  v_correction_of := nullif(p_payload->>'correction_of_pool_id', '')::uuid;
  if v_reason is null then raise exception 'Attendance HPP pool reason is required'; end if;

  v_hash := erp._request_hash(jsonb_build_object('payload', p_payload));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  perform pg_advisory_xact_lock(hashtextextended(
    'ATTENDANCE_HPP_PERIOD|' || v_period_start::text || '|' || v_period_end::text, 0
  ));

  if exists (
    select 1 from erp.attendance_hpp_pools p
    where p.period_start = v_period_start
      and p.period_end = v_period_end
      and p.status in ('DRAFT','ACTIVE')
  ) then
    raise exception 'A DRAFT/ACTIVE attendance HPP pool already exists for this exact period';
  end if;
  if v_correction_of is not null and not exists (
    select 1 from erp.attendance_hpp_pools p
    where p.id = v_correction_of
      and p.status = 'CANCELLED'
      and p.period_start = v_period_start
      and p.period_end = v_period_end
  ) then
    raise exception 'correction_of_pool_id must reference a CANCELLED pool for the same exact period';
  end if;

  v_preview := erp.preview_attendance_hpp_pool_v1(v_period_start, v_period_end);
  v_manifest := v_preview->'manifest';

  insert into erp.attendance_hpp_pools(
    pool_number, period_start, period_end, correction_of_pool_id,
    numerator_amount, denominator_qty, unit_cost_per_sewn_pcs,
    source_manifest, source_manifest_sha256,
    reason, created_by
  ) values (
    'AHPP-' || to_char(clock_timestamp() at time zone 'UTC', 'YYYYMMDDHH24MISSUS') || '-' || substr(gen_random_uuid()::text, 1, 8),
    v_period_start, v_period_end, v_correction_of,
    (v_preview->>'numerator_amount')::numeric,
    (v_preview->>'denominator_qty')::bigint,
    (v_preview->>'unit_cost_per_sewn_pcs')::numeric,
    v_manifest, v_preview->>'manifest_sha256',
    v_reason, erp.current_app_user_id()
  ) returning * into v_pool;

  insert into erp.attendance_hpp_pool_sources(
    pool_id, payroll_id, contractor_id, policy_version_id,
    original_debit_journal_line_id,
    contractor_role_snapshot, attendance_required_snapshot, is_special_snapshot,
    attendance_amount
  )
  select
    v_pool.id,
    (x->>'payroll_id')::uuid,
    (x->>'contractor_id')::uuid,
    (x->>'policy_version_id')::uuid,
    (x->>'original_debit_journal_line_id')::uuid,
    x->>'contractor_role_snapshot',
    (x->>'attendance_required_snapshot')::boolean,
    (x->>'is_special_snapshot')::boolean,
    ((x->>'attendance_amount_cents')::bigint / 100.0)::numeric(20,2)
  from jsonb_array_elements(v_manifest->'sources') x;

  with destination as (
    select
      (x->>'sewing_terminal_event_id')::uuid sewing_terminal_event_id,
      (x->>'contractor_id')::uuid contractor_id,
      (x->>'po_id')::uuid po_id,
      nullif(x->>'cutting_group_id', '')::uuid cutting_group_id,
      (x->>'sewing_qty')::integer sewing_qty,
      sum((x->>'sewing_qty')::bigint) over (
        order by (x->>'physical_at_epoch_us')::bigint,
                 (x->>'sewing_terminal_event_id')::uuid
        rows between unbounded preceding and current row
      ) cumulative_qty,
      coalesce(sum((x->>'sewing_qty')::bigint) over (
        order by (x->>'physical_at_epoch_us')::bigint,
                 (x->>'sewing_terminal_event_id')::uuid
        rows between unbounded preceding and 1 preceding
      ), 0) previous_cumulative_qty
    from jsonb_array_elements(v_manifest->'destinations') x
  ), source as (
    select s.*, round(s.attendance_amount * 100)::bigint source_cents
    from erp.attendance_hpp_pool_sources s
    where s.pool_id = v_pool.id
  )
  insert into erp.attendance_hpp_pool_allocations(
    pool_id, pool_source_id, sewing_terminal_event_id,
    contractor_id, po_id, cutting_group_id,
    sewing_qty, allocated_amount
  )
  select
    v_pool.id, s.id, d.sewing_terminal_event_id,
    d.contractor_id, d.po_id, d.cutting_group_id,
    d.sewing_qty,
    (
      floor(s.source_cents::numeric * d.cumulative_qty::numeric / v_pool.denominator_qty)
      - floor(s.source_cents::numeric * d.previous_cumulative_qty::numeric / v_pool.denominator_qty)
    ) / 100.0
  from source s cross join destination d
  order by s.id, d.cumulative_qty, d.sewing_terminal_event_id;

  if exists (
    select 1
    from erp.attendance_hpp_pool_sources s
    left join erp.attendance_hpp_pool_allocations a on a.pool_source_id = s.id
    where s.pool_id = v_pool.id
    group by s.id, s.attendance_amount
    having round(coalesce(sum(a.allocated_amount), 0), 2) is distinct from round(s.attendance_amount, 2)
  ) then
    raise exception 'Deterministic allocation failed to reconcile a source debit line exactly to cents';
  end if;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'attendance_hpp_pools', v_pool.id, 'CREATE_DRAFT',
    jsonb_build_object(
      'period_start', v_pool.period_start,
      'period_end', v_pool.period_end,
      'numerator_amount', v_pool.numerator_amount,
      'denominator_qty', v_pool.denominator_qty,
      'manifest_sha256', v_pool.source_manifest_sha256,
      'correction_of_pool_id', v_pool.correction_of_pool_id
    ),
    erp.current_app_user_id(), v_reason
  );

  v_response := jsonb_build_object(
    'pool_id', v_pool.id,
    'pool_number', v_pool.pool_number,
    'status', v_pool.status,
    'row_version', v_pool.row_version,
    'numerator_amount', v_pool.numerator_amount,
    'denominator_qty', v_pool.denominator_qty,
    'unit_cost_per_sewn_pcs', v_pool.unit_cost_per_sewn_pcs,
    'manifest_sha256', v_pool.source_manifest_sha256
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

-- ---------------------------------------------------------------------------
-- 7. One bounded set-based validator; no deferred row-by-row validator
-- ---------------------------------------------------------------------------

create or replace function erp.validate_attendance_hpp_pool_v1(p_pool_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = erp, public, pg_temp
as $function$
declare
  v_pool erp.attendance_hpp_pools%rowtype;
  v_source_count bigint;
  v_destination_count bigint;
  v_bad_sources bigint;
  v_bad_allocations bigint;
  v_current_manifest jsonb;
  v_source_total numeric(20,2);
  v_allocation_total numeric(20,2);
  v_journal_debit numeric(20,2);
  v_journal_credit numeric(20,2);
  v_source_credit_link_count bigint;
begin
  select * into v_pool from erp.attendance_hpp_pools where id = p_pool_id;
  if v_pool.id is null then raise exception 'Attendance HPP pool not found'; end if;

  select count(*), coalesce(sum(attendance_amount), 0)
    into v_source_count, v_source_total
  from erp.attendance_hpp_pool_sources where pool_id = v_pool.id;

  select count(distinct sewing_terminal_event_id), coalesce(sum(allocated_amount), 0)
    into v_destination_count, v_allocation_total
  from erp.attendance_hpp_pool_allocations where pool_id = v_pool.id;

  select count(*) into v_bad_sources
  from erp.attendance_hpp_pool_sources s
  join erp.payroll_settlements ps on ps.id = s.payroll_id
  join erp.contractor_hpp_policy_versions p on p.id = s.policy_version_id
  join erp.journal_lines jl on jl.id = s.original_debit_journal_line_id
  join erp.journal_entries je on je.id = jl.journal_entry_id
  where s.pool_id = v_pool.id
    and (
      s.contractor_role_snapshot is distinct from 'MANDOR'
      or s.attendance_required_snapshot is distinct from true
      or s.is_special_snapshot is distinct from false
      or ps.status is distinct from 'PAID'
      or ps.period_start is distinct from v_pool.period_start
      or ps.period_end is distinct from v_pool.period_end
      or p.contractor_id is distinct from s.contractor_id
      or p.effective_from > v_pool.period_start
      or (p.effective_to is not null and p.effective_to < v_pool.period_end)
      or je.status is distinct from 'POSTED'
      or je.source_id is distinct from ps.id
      or je.source_type not in ('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL')
      or jl.debit + 0.01 < s.attendance_amount
    );

  select count(*) into v_bad_allocations
  from erp.attendance_hpp_pool_allocations a
  join erp.attendance_hpp_pool_sources s on s.id = a.pool_source_id
  join erp.sewing_terminal_events e on e.id = a.sewing_terminal_event_id
  join erp.work_completion_events w on w.id = e.source_work_completion_id
  where a.pool_id = v_pool.id
    and (
      s.pool_id is distinct from v_pool.id
      or e.event_kind is distinct from 'SELESAI_DIJAHIT'
      or e.qty_signed <= 0
      or e.physical_at::date not between v_pool.period_start and v_pool.period_end
      or w.status is distinct from 'POSTED'
      or exists (select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id = e.id)
      or a.contractor_id is distinct from e.contractor_id
      or a.po_id is distinct from e.po_id
      or a.cutting_group_id is distinct from e.cutting_group_id
      or a.sewing_qty is distinct from e.qty_signed
    );

  if v_source_count = 0 or v_destination_count = 0
     or v_bad_sources > 0 or v_bad_allocations > 0
     or round(v_source_total, 2) is distinct from round(v_pool.numerator_amount, 2)
     or round(v_allocation_total, 2) is distinct from round(v_pool.numerator_amount, 2)
     or v_pool.denominator_qty <> (
       select coalesce(sum(e.qty_signed), 0)::bigint
       from erp.sewing_terminal_events e
       where e.id in (
         select distinct sewing_terminal_event_id
         from erp.attendance_hpp_pool_allocations
         where pool_id = v_pool.id
       )
     )
     or exists (
       select 1
       from erp.attendance_hpp_pool_sources s
       left join erp.attendance_hpp_pool_allocations a on a.pool_source_id = s.id
       where s.pool_id = v_pool.id
       group by s.id, s.attendance_amount
       having round(coalesce(sum(a.allocated_amount), 0), 2) is distinct from round(s.attendance_amount, 2)
     ) then
    raise exception 'Attendance HPP pool failed bounded set-based source/allocation validation';
  end if;

  v_current_manifest := erp._build_attendance_hpp_manifest_v1(v_pool.period_start, v_pool.period_end);
  perform erp._assert_attendance_hpp_manifest_v1(v_current_manifest);
  if erp._cp3_manifest_sha256(v_current_manifest) is distinct from v_pool.source_manifest_sha256
     or v_current_manifest is distinct from v_pool.source_manifest then
    raise exception 'STALE_POOL_INPUT: payroll, policy, journal debit, or SELESAI_DIJAHIT facts changed after preview';
  end if;

  if v_pool.status in ('ACTIVE','CANCELLED') then
    select coalesce(sum(jl.debit),0), coalesce(sum(jl.credit),0)
      into v_journal_debit, v_journal_credit
    from erp.journal_lines jl
    where jl.journal_entry_id = v_pool.post_journal_entry_id;

    select count(*) into v_source_credit_link_count
    from erp.attendance_hpp_journal_line_links l
    where l.pool_id = v_pool.id and l.link_type = 'SOURCE_CREDIT';

    if round(v_journal_debit,2) is distinct from round(v_pool.numerator_amount,2)
       or round(v_journal_credit,2) is distinct from round(v_pool.numerator_amount,2)
       or v_source_credit_link_count <> v_source_count
       or exists (
         select 1
         from erp.attendance_hpp_pool_sources s
         left join erp.attendance_hpp_journal_line_links l
           on l.pool_source_id = s.id
          and l.link_type = 'SOURCE_CREDIT'
         where s.pool_id = v_pool.id
         group by s.id, s.original_debit_journal_line_id, s.attendance_amount
         having count(l.id) <> 1
            or bool_or(l.original_debit_journal_line_id is distinct from s.original_debit_journal_line_id)
            or round(coalesce(sum(l.amount),0),2) is distinct from round(s.attendance_amount,2)
       ) then
      raise exception 'Attendance HPP journal does not reconcile one terminal credit per original pool debit line';
    end if;
  end if;

  return jsonb_build_object(
    'pool_id', v_pool.id,
    'status', v_pool.status,
    'source_count', v_source_count,
    'destination_count', v_destination_count,
    'numerator_amount', v_pool.numerator_amount,
    'denominator_qty', v_pool.denominator_qty,
    'manifest_sha256', v_pool.source_manifest_sha256,
    'validation', 'PASS'
  );
end;
$function$;

-- ---------------------------------------------------------------------------
-- 8. Activate and cancel: owning atomic orchestration
-- ---------------------------------------------------------------------------

create or replace function erp.activate_attendance_hpp_pool_v1(
  p_pool_id uuid,
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
  v_operation constant text := 'activate_attendance_hpp_pool_v1';
  v_hash text;
  v_cached jsonb;
  v_pool erp.attendance_hpp_pools%rowtype;
  v_lines jsonb := '[]'::jsonb;
  v_journal_id uuid;
  v_line record;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  if p_pool_id is null or p_expected_version is null then
    raise exception 'pool_id and expected_version are required';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'Attendance HPP activation reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'pool_id', p_pool_id,
    'reason', btrim(p_reason),
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_pool
  from erp.attendance_hpp_pools
  where id = p_pool_id
  for update;

  if v_pool.id is null then raise exception 'Attendance HPP pool not found'; end if;
  if v_pool.status <> 'DRAFT' then raise exception 'Only DRAFT attendance HPP pool can be activated'; end if;
  if v_pool.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_pool.row_version;
  end if;
  if v_pool.numerator_amount <= 0 or v_pool.denominator_qty <= 0 then
    raise exception 'Attendance HPP activation requires positive numerator and immutable SELESAI_DIJAHIT denominator';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(
    'ATTENDANCE_HPP_PERIOD|' || v_pool.period_start::text || '|' || v_pool.period_end::text, 0
  ));

  if exists (
    select 1 from erp.attendance_hpp_pools p
    where p.id <> v_pool.id
      and p.period_start = v_pool.period_start
      and p.period_end = v_pool.period_end
      and p.status = 'ACTIVE'
  ) then
    raise exception 'Another ACTIVE attendance HPP pool already owns this exact period';
  end if;

  perform erp.validate_attendance_hpp_pool_v1(v_pool.id);

  select coalesce(jsonb_agg(jsonb_build_object(
    'mapping_key', 'WIP',
    'debit', amount,
    'credit', 0,
    'contractor_id', contractor_id,
    'po_id', po_id,
    'description', 'Attendance HPP destination PO ' || po_id::text
  ) order by po_id, contractor_id), '[]'::jsonb)
  into v_lines
  from (
    select po_id, contractor_id, round(sum(allocated_amount),2) amount
    from erp.attendance_hpp_pool_allocations
    where pool_id = v_pool.id
    group by po_id, contractor_id
    having round(sum(allocated_amount),2) > 0
  ) d;

  v_lines := v_lines || coalesce((
    select jsonb_agg(jsonb_build_object(
      'account_id', jl.account_id,
      'debit', 0,
      'credit', round(s.attendance_amount,2),
      'contractor_id', s.contractor_id,
      'description', 'Attendance HPP source debit line ' || s.original_debit_journal_line_id::text
    ) order by s.original_debit_journal_line_id)
    from erp.attendance_hpp_pool_sources s
    join erp.journal_lines jl on jl.id = s.original_debit_journal_line_id
    where s.pool_id = v_pool.id
  ), '[]'::jsonb);

  v_journal_id := erp.post_journal(
    'ATTENDANCE_HPP_POOL', v_pool.id, v_pool.period_end,
    'Allocate normal-Mandor attendance cost by immutable SELESAI_DIJAHIT',
    v_lines
  );

  for v_line in
    select jl.id, jl.po_id, jl.debit
    from erp.journal_lines jl
    where jl.journal_entry_id = v_journal_id
      and jl.debit > 0
      and jl.po_id is not null
  loop
    insert into erp.attendance_hpp_journal_line_links(
      pool_id, journal_line_id, link_type, po_id, amount
    ) values (
      v_pool.id, v_line.id, 'DESTINATION_DEBIT', v_line.po_id, v_line.debit
    );
  end loop;

  for v_line in
    select s.id as pool_source_id, s.original_debit_journal_line_id,
           s.attendance_amount, jl2.id as journal_line_id
    from erp.attendance_hpp_pool_sources s
    join erp.journal_lines jl2
      on jl2.journal_entry_id = v_journal_id
     and jl2.credit = round(s.attendance_amount,2)
     and jl2.description = 'Attendance HPP source debit line ' || s.original_debit_journal_line_id::text
    where s.pool_id = v_pool.id
    order by s.original_debit_journal_line_id
  loop
    insert into erp.attendance_hpp_journal_line_links(
      pool_id, journal_line_id, link_type,
      pool_source_id, original_debit_journal_line_id, amount
    ) values (
      v_pool.id, v_line.journal_line_id, 'SOURCE_CREDIT',
      v_line.pool_source_id, v_line.original_debit_journal_line_id,
      v_line.attendance_amount
    );
  end loop;

  update erp.attendance_hpp_pools
  set status = 'ACTIVE',
      post_journal_entry_id = v_journal_id,
      activated_by = erp.current_app_user_id(),
      activated_at = clock_timestamp(),
      row_version = row_version + 1
  where id = v_pool.id
  returning * into v_pool;

  perform erp.validate_attendance_hpp_pool_v1(v_pool.id);

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'attendance_hpp_pools', v_pool.id, 'ACTIVATE',
    jsonb_build_object(
      'journal_entry_id', v_journal_id,
      'numerator_amount', v_pool.numerator_amount,
      'denominator_qty', v_pool.denominator_qty,
      'manifest_sha256', v_pool.source_manifest_sha256
    ),
    erp.current_app_user_id(), btrim(p_reason)
  );

  v_response := jsonb_build_object(
    'pool_id', v_pool.id,
    'status', v_pool.status,
    'row_version', v_pool.row_version,
    'journal_entry_id', v_pool.post_journal_entry_id,
    'validation', 'PASS'
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.cancel_attendance_hpp_pool_v1(
  p_pool_id uuid,
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
  v_operation constant text := 'cancel_attendance_hpp_pool_v1';
  v_hash text;
  v_cached jsonb;
  v_pool erp.attendance_hpp_pools%rowtype;
  v_reversal_journal_id uuid;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  if p_pool_id is null or p_expected_version is null then
    raise exception 'pool_id and expected_version are required';
  end if;
  if coalesce(btrim(p_reason), '') = '' then
    raise exception 'Attendance HPP cancellation reason is required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'pool_id', p_pool_id,
    'reason', btrim(p_reason),
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_pool
  from erp.attendance_hpp_pools
  where id = p_pool_id
  for update;

  if v_pool.id is null then raise exception 'Attendance HPP pool not found'; end if;
  if v_pool.status <> 'ACTIVE' then
    raise exception 'Only ACTIVE attendance HPP pool can be cancelled; no manual pre-reversal is accepted';
  end if;
  if v_pool.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %', p_expected_version, v_pool.row_version;
  end if;
  if v_pool.post_journal_entry_id is null then
    raise exception 'ACTIVE attendance HPP pool has no source journal; cancellation stopped to avoid residue';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(
    'ATTENDANCE_HPP_PERIOD|' || v_pool.period_start::text || '|' || v_pool.period_end::text, 0
  ));

  if not exists (
    select 1 from erp.journal_entries je
    where je.id = v_pool.post_journal_entry_id
      and je.status = 'POSTED'
      and je.source_type = 'ATTENDANCE_HPP_POOL'
      and je.source_id = v_pool.id
  ) then
    raise exception 'Pool journal is not an active posted ATTENDANCE_HPP_POOL journal';
  end if;

  v_reversal_journal_id := erp.reverse_journal(v_pool.post_journal_entry_id, btrim(p_reason));

  update erp.attendance_hpp_pools
  set status = 'CANCELLED',
      cancellation_journal_entry_id = v_reversal_journal_id,
      cancellation_reason = btrim(p_reason),
      cancelled_by = erp.current_app_user_id(),
      cancelled_at = clock_timestamp(),
      row_version = row_version + 1
  where id = v_pool.id
  returning * into v_pool;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)
  values (
    'attendance_hpp_pools', v_pool.id, 'CANCEL_ACTIVE',
    jsonb_build_object(
      'post_journal_entry_id', v_pool.post_journal_entry_id,
      'cancellation_journal_entry_id', v_pool.cancellation_journal_entry_id,
      'previous_status', 'ACTIVE',
      'new_status', 'CANCELLED'
    ),
    erp.current_app_user_id(), btrim(p_reason)
  );

  v_response := jsonb_build_object(
    'pool_id', v_pool.id,
    'status', v_pool.status,
    'row_version', v_pool.row_version,
    'reversal_journal_entry_id', v_pool.cancellation_journal_entry_id,
    'residue_expected', 0
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

-- ---------------------------------------------------------------------------
-- 9. Security boundary: private foundation, no route activation grant/hook
-- ---------------------------------------------------------------------------

alter table erp.contractor_hpp_policy_versions enable row level security;
alter table erp.sewing_terminal_events enable row level security;
alter table erp.attendance_hpp_pools enable row level security;
alter table erp.attendance_hpp_pool_sources enable row level security;
alter table erp.attendance_hpp_pool_allocations enable row level security;
alter table erp.attendance_hpp_journal_line_links enable row level security;

revoke all on table erp.contractor_hpp_policy_versions from public, anon, authenticated, service_role;
revoke all on table erp.sewing_terminal_events from public, anon, authenticated, service_role;
revoke all on table erp.attendance_hpp_pools from public, anon, authenticated, service_role;
revoke all on table erp.attendance_hpp_pool_sources from public, anon, authenticated, service_role;
revoke all on table erp.attendance_hpp_pool_allocations from public, anon, authenticated, service_role;
revoke all on table erp.attendance_hpp_journal_line_links from public, anon, authenticated, service_role;
revoke all on table erp.v_attendance_hpp_active_allocation_by_po from public, anon, authenticated, service_role;

revoke execute on function erp._cp3_assert_closed_json_object(jsonb,text[],text[],text) from public, anon, authenticated, service_role;
revoke execute on function erp._cp3_epoch_microseconds(timestamptz) from public, anon, authenticated, service_role;
revoke execute on function erp._cp3_manifest_sha256(jsonb) from public, anon, authenticated, service_role;
revoke execute on function erp.set_contractor_hpp_policy_v1(jsonb,uuid,uuid) from public, anon, authenticated, service_role;
revoke execute on function erp.record_sewing_terminal_v1(jsonb,uuid) from public, anon, authenticated, service_role;
revoke execute on function erp.reverse_sewing_terminal_v1(uuid,text,uuid,bigint) from public, anon, authenticated, service_role;
revoke execute on function erp._build_attendance_hpp_manifest_v1(date,date) from public, anon, authenticated, service_role;
revoke execute on function erp._assert_attendance_hpp_manifest_v1(jsonb) from public, anon, authenticated, service_role;
revoke execute on function erp.preview_attendance_hpp_pool_v1(date,date) from public, anon, authenticated, service_role;
revoke execute on function erp.create_attendance_hpp_pool_v1(jsonb,uuid) from public, anon, authenticated, service_role;
revoke execute on function erp.validate_attendance_hpp_pool_v1(uuid) from public, anon, authenticated, service_role;
revoke execute on function erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint) from public, anon, authenticated, service_role;
revoke execute on function erp.cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint) from public, anon, authenticated, service_role;

comment on table erp.contractor_hpp_policy_versions is
  'Explicit effective-dated Mandor HPP eligibility. Special is independent from attendance_required and never inferred from a name.';
comment on table erp.sewing_terminal_events is
  'Immutable authoritative SELESAI_DIJAHIT facts and append-only reversals. Never infer this denominator from QC GOOD, FG, laundry, rework, or component names.';
comment on table erp.attendance_hpp_pools is
  'Attendance cost reclassification pool. DRAFT is previewed evidence; ACTIVE has one posted allocation journal; CANCELLED owns its journal reversal.';
comment on view erp.v_attendance_hpp_active_allocation_by_po is
  'Read model only. CP3 intentionally does not hook this allocation into rebuild_po_hpp; activation/grants belong to CP4 after independent audit.';

insert into erp.schema_migrations(version, description, installed_at)
values (
  'v2.6.14a',
  'Private no-hook/no-grant attendance HPP foundation using immutable SELESAI_DIJAHIT, explicit normal-Mandor policy, exact debit-line journal lineage, deterministic manifest, and active-pool cancellation',
  clock_timestamp()
);

notify pgrst, 'reload schema';

commit;
