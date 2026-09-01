-- ERP Garment v2.6.14 candidate — attendance HPP via immutable SELESAI_DIJAHIT facts
-- CP3_OPERATION: DOMAIN=ATTENDANCE_HPP TYPE=ATTENDANCE_HPP_FOUNDATION
-- SOURCE-ONLY CP3 FOUNDATION: NO EXISTING-TABLE HOOKS, NO BROWSER GRANTS, NO UAT APPLY.
-- The candidate intentionally creates only isolated foundation objects and internal RPCs.
-- Activation into payroll reversal, HPP rebuild/queue, and browser/API grants belongs to CP4
-- after independent delta review, rollback fixtures, and real concurrency pass.

begin;

set local lock_timeout = '5s';
set local statement_timeout = '120s';
set local idle_in_transaction_session_timeout = '120s';

-- Fail closed if the reviewed UAT baseline is not present. This migration is additive;
-- it never edits or replays an installed migration.
do $preflight$
begin
  if to_regclass('erp.contractors') is null
     or to_regclass('erp.payroll_settlements') is null
     or to_regclass('erp.payroll_attendance_items') is null
     or to_regclass('erp.work_completion_events') is null
     or to_regclass('erp.cutting_groups') is null
     or to_regclass('erp.journal_entries') is null
     or to_regclass('erp.journal_lines') is null
     or to_regprocedure('erp.post_journal(text,uuid,date,text,jsonb)') is null
     or to_regprocedure('erp.reverse_journal(uuid,text)') is null
     or to_regprocedure('erp._idempotency_begin(text,uuid,text)') is null
     or to_regprocedure('erp._idempotency_complete(text,uuid,jsonb)') is null
  then
    raise exception 'CP3 attendance HPP prerequisite baseline is incomplete';
  end if;

  if to_regclass('erp.attendance_hpp_pools') is not null
     or to_regclass('erp.sewing_terminal_events') is not null
  then
    raise exception 'CP3 attendance HPP objects already exist; inspect state before retry';
  end if;
end;
$preflight$;

create table erp.contractor_hpp_policy_versions (
  id uuid primary key default gen_random_uuid(),
  contractor_id uuid not null references erp.contractors(id),
  effective_from date not null,
  effective_to date,
  role_snapshot varchar(30) not null,
  attendance_required boolean not null,
  is_special boolean not null,
  change_reason text not null,
  created_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  row_version bigint not null default 1,
  constraint contractor_hpp_policy_dates_check
    check (effective_to is null or effective_to >= effective_from),
  constraint contractor_hpp_policy_reason_check
    check (btrim(change_reason) <> ''),
  constraint contractor_hpp_policy_row_version_check
    check (row_version > 0),
  constraint contractor_hpp_policy_from_key
    unique (contractor_id, effective_from)
);

create index idx_contractor_hpp_policy_cover
  on erp.contractor_hpp_policy_versions(contractor_id, effective_from, effective_to);

create table erp.sewing_terminal_events (
  id uuid primary key default gen_random_uuid(),
  event_number varchar(80) not null unique,
  event_type varchar(30) not null default 'SELESAI_DIJAHIT'
    check (event_type = 'SELESAI_DIJAHIT'),
  origin_type varchar(40) not null default 'CUTTING_GROUP_SEWING'
    check (origin_type = 'CUTTING_GROUP_SEWING'),
  po_id uuid not null references erp.production_orders(id),
  contractor_id uuid not null references erp.contractors(id),
  cutting_group_id uuid not null references erp.cutting_groups(id),
  qty_pcs integer not null check (qty_pcs > 0),
  physical_at timestamptz not null,
  status varchar(20) not null default 'POSTED'
    check (status in ('POSTED','CORRECTED','REVERSED')),
  correction_of_event_id uuid references erp.sewing_terminal_events(id),
  change_reason text not null check (btrim(change_reason) <> ''),
  created_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  row_version bigint not null default 1 check (row_version > 0),
  constraint sewing_terminal_correction_self_check
    check (correction_of_event_id is null or correction_of_event_id <> id),
  constraint sewing_terminal_correction_unique
    unique (correction_of_event_id)
);

create index idx_sewing_terminal_period_eligible
  on erp.sewing_terminal_events(physical_at, contractor_id, status, id);
create index idx_sewing_terminal_group_status
  on erp.sewing_terminal_events(cutting_group_id, status, physical_at, id);
create index idx_sewing_terminal_po_status
  on erp.sewing_terminal_events(po_id, status, physical_at, id);

create table erp.attendance_hpp_pools (
  id uuid primary key default gen_random_uuid(),
  pool_number varchar(80) not null unique,
  period_start date not null,
  period_end date not null,
  status varchar(20) not null default 'ACTIVE'
    check (status in ('ACTIVE','POSTED','CANCELLED','REVERSED','CORRECTED')),
  correction_of_pool_id uuid references erp.attendance_hpp_pools(id),
  numerator_amount numeric(20,2) not null default 0 check (numerator_amount >= 0),
  denominator_qty integer not null default 0 check (denominator_qty >= 0),
  allocated_amount numeric(20,2) not null default 0 check (allocated_amount >= 0),
  manifest jsonb not null default '{}'::jsonb,
  manifest_digest varchar(64),
  allocation_journal_entry_id uuid references erp.journal_entries(id),
  reversal_journal_entry_id uuid references erp.journal_entries(id),
  change_reason text not null check (btrim(change_reason) <> ''),
  created_by uuid references erp.app_users(id),
  posted_by uuid references erp.app_users(id),
  cancelled_by uuid references erp.app_users(id),
  reversed_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  posted_at timestamptz,
  cancelled_at timestamptz,
  reversed_at timestamptz,
  row_version bigint not null default 1 check (row_version > 0),
  constraint attendance_hpp_pool_dates_check check (period_end >= period_start),
  constraint attendance_hpp_pool_correction_self_check
    check (correction_of_pool_id is null or correction_of_pool_id <> id),
  constraint attendance_hpp_pool_correction_unique unique (correction_of_pool_id),
  constraint attendance_hpp_pool_manifest_digest_check
    check (manifest_digest is null or manifest_digest ~ '^[0-9a-f]{64}$')
);

create index idx_attendance_hpp_pool_period_status
  on erp.attendance_hpp_pools(period_start, period_end, status, id);

create table erp.attendance_hpp_pool_sources (
  id uuid primary key default gen_random_uuid(),
  pool_id uuid not null references erp.attendance_hpp_pools(id) on delete cascade,
  payroll_id uuid not null references erp.payroll_settlements(id),
  contractor_id uuid not null references erp.contractors(id),
  policy_version_id uuid not null references erp.contractor_hpp_policy_versions(id),
  source_journal_entry_id uuid not null references erp.journal_entries(id),
  source_journal_line_id uuid not null references erp.journal_lines(id),
  attendance_amount numeric(20,2) not null check (attendance_amount > 0),
  source_line_debit_snapshot numeric(20,2) not null check (source_line_debit_snapshot > 0),
  role_snapshot varchar(30) not null,
  attendance_required_snapshot boolean not null,
  is_special_snapshot boolean not null,
  payroll_row_version_snapshot bigint not null check (payroll_row_version_snapshot > 0),
  source_posting_epoch_us bigint not null,
  period_start_snapshot date not null,
  period_end_snapshot date not null,
  created_at timestamptz not null default clock_timestamp(),
  constraint attendance_hpp_pool_source_payroll_unique unique (pool_id, payroll_id),
  constraint attendance_hpp_pool_source_journal_line_unique unique (pool_id, source_journal_line_id),
  constraint attendance_hpp_pool_source_eligibility_check
    check (role_snapshot = 'MANDOR' and attendance_required_snapshot and not is_special_snapshot),
  constraint attendance_hpp_pool_source_period_check
    check (period_end_snapshot >= period_start_snapshot),
  constraint attendance_hpp_pool_source_amount_check
    check (source_line_debit_snapshot >= attendance_amount)
);

create index idx_attendance_hpp_sources_payroll
  on erp.attendance_hpp_pool_sources(payroll_id, pool_id);
create index idx_attendance_hpp_sources_journal_line
  on erp.attendance_hpp_pool_sources(source_journal_line_id, pool_id);

create table erp.attendance_hpp_pool_allocations (
  id uuid primary key default gen_random_uuid(),
  pool_id uuid not null references erp.attendance_hpp_pools(id) on delete cascade,
  sewing_terminal_event_id uuid not null references erp.sewing_terminal_events(id),
  po_id uuid not null references erp.production_orders(id),
  contractor_id uuid not null references erp.contractors(id),
  cutting_group_id uuid not null references erp.cutting_groups(id),
  policy_version_id uuid not null references erp.contractor_hpp_policy_versions(id),
  qty_pcs integer not null check (qty_pcs > 0),
  allocation_amount numeric(20,2) not null check (allocation_amount >= 0),
  event_row_version_snapshot bigint not null check (event_row_version_snapshot > 0),
  event_physical_epoch_us bigint not null,
  created_at timestamptz not null default clock_timestamp(),
  constraint attendance_hpp_allocation_event_unique unique (pool_id, sewing_terminal_event_id)
);

create index idx_attendance_hpp_allocations_po
  on erp.attendance_hpp_pool_allocations(po_id, pool_id, cutting_group_id);
create index idx_attendance_hpp_allocations_event
  on erp.attendance_hpp_pool_allocations(sewing_terminal_event_id, pool_id);

create table erp.attendance_hpp_journal_credit_map (
  pool_id uuid not null references erp.attendance_hpp_pools(id) on delete cascade,
  source_journal_line_id uuid not null references erp.journal_lines(id),
  reclass_journal_line_id uuid not null references erp.journal_lines(id),
  amount numeric(20,2) not null check (amount > 0),
  primary key (pool_id, source_journal_line_id),
  unique (pool_id, reclass_journal_line_id)
);

create table erp.attendance_hpp_journal_debit_map (
  pool_id uuid not null references erp.attendance_hpp_pools(id) on delete cascade,
  po_id uuid not null references erp.production_orders(id),
  reclass_journal_line_id uuid not null references erp.journal_lines(id),
  amount numeric(20,2) not null check (amount > 0),
  primary key (pool_id, po_id),
  unique (pool_id, reclass_journal_line_id)
);

-- New relations are private even before grants are considered.
alter table erp.contractor_hpp_policy_versions enable row level security;
alter table erp.sewing_terminal_events enable row level security;
alter table erp.attendance_hpp_pools enable row level security;
alter table erp.attendance_hpp_pool_sources enable row level security;
alter table erp.attendance_hpp_pool_allocations enable row level security;
alter table erp.attendance_hpp_journal_credit_map enable row level security;
alter table erp.attendance_hpp_journal_debit_map enable row level security;

create policy contractor_hpp_policy_explicit_deny
  on erp.contractor_hpp_policy_versions for all to anon, authenticated using (false) with check (false);
create policy sewing_terminal_explicit_deny
  on erp.sewing_terminal_events for all to anon, authenticated using (false) with check (false);
create policy attendance_hpp_pool_explicit_deny
  on erp.attendance_hpp_pools for all to anon, authenticated using (false) with check (false);
create policy attendance_hpp_source_explicit_deny
  on erp.attendance_hpp_pool_sources for all to anon, authenticated using (false) with check (false);
create policy attendance_hpp_allocation_explicit_deny
  on erp.attendance_hpp_pool_allocations for all to anon, authenticated using (false) with check (false);
create policy attendance_hpp_credit_map_explicit_deny
  on erp.attendance_hpp_journal_credit_map for all to anon, authenticated using (false) with check (false);
create policy attendance_hpp_debit_map_explicit_deny
  on erp.attendance_hpp_journal_debit_map for all to anon, authenticated using (false) with check (false);

create or replace function erp._cp3_assert_json_object_v1(
  p_payload jsonb,
  p_required text[],
  p_optional text[],
  p_context text
) returns void
language plpgsql
immutable
set search_path to 'erp','public','pg_temp'
as $function$
declare
  v_missing text[];
  v_null_keys text[];
  v_extra text[];
begin
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    raise exception '% must be a JSON object', p_context;
  end if;

  select array_agg(k order by k) into v_missing
  from unnest(coalesce(p_required, array[]::text[])) k
  where not (p_payload ? k);
  if coalesce(cardinality(v_missing),0) > 0 then
    raise exception '% is missing required keys: %', p_context, array_to_string(v_missing, ', ');
  end if;

  select array_agg(k order by k) into v_null_keys
  from unnest(coalesce(p_required, array[]::text[])) k
  where jsonb_typeof(p_payload->k) = 'null';
  if coalesce(cardinality(v_null_keys),0) > 0 then
    raise exception '% has null required keys: %', p_context, array_to_string(v_null_keys, ', ');
  end if;

  select array_agg(k order by k) into v_extra
  from jsonb_object_keys(p_payload) k
  where not (k = any(coalesce(p_required, array[]::text[]) || coalesce(p_optional, array[]::text[])));
  if coalesce(cardinality(v_extra),0) > 0 then
    raise exception '% has unexpected keys: %', p_context, array_to_string(v_extra, ', ');
  end if;
end;
$function$;

create or replace function erp._cp3_epoch_us(p_value timestamptz)
returns bigint
language sql
immutable
set search_path to 'erp','public','pg_temp'
as $function$
  select case when p_value is null then null
              else round(extract(epoch from p_value) * 1000000)::bigint end
$function$;

create or replace function erp._cp3_guard_policy_write()
returns trigger
language plpgsql
set search_path to 'erp','public','pg_temp'
as $function$
begin
  if coalesce(current_setting('app.cp3_policy_write', true), 'off') <> 'on' then
    raise exception 'Contractor HPP policy is write-protected; use the owning policy RPC';
  end if;
  if tg_op = 'DELETE' then
    raise exception 'Contractor HPP policy versions are immutable; create a forward version';
  end if;
  if tg_op = 'UPDATE' and exists (
    select 1 from erp.attendance_hpp_pool_sources s where s.policy_version_id = old.id
    union all
    select 1 from erp.attendance_hpp_pool_allocations a where a.policy_version_id = old.id
  ) then
    raise exception 'A policy snapshot used by an HPP pool is immutable';
  end if;
  return new;
end;
$function$;

create or replace function erp._cp3_guard_policy_overlap()
returns trigger
language plpgsql
set search_path to 'erp','public','pg_temp'
as $function$
begin
  perform pg_advisory_xact_lock(hashtextextended('CP3_HPP_POLICY|' || new.contractor_id::text, 0));
  if exists (
    select 1
    from erp.contractor_hpp_policy_versions p
    where p.contractor_id = new.contractor_id
      and p.id <> new.id
      and p.effective_from <= coalesce(new.effective_to, 'infinity'::date)
      and coalesce(p.effective_to, 'infinity'::date) >= new.effective_from
  ) then
    raise exception 'Overlapping contractor HPP policy effective range';
  end if;
  return new;
end;
$function$;

create trigger trg_10_contractor_hpp_policy_write
before insert or update or delete on erp.contractor_hpp_policy_versions
for each row execute function erp._cp3_guard_policy_write();
create trigger trg_20_contractor_hpp_policy_overlap
before insert or update of contractor_id,effective_from,effective_to on erp.contractor_hpp_policy_versions
for each row execute function erp._cp3_guard_policy_overlap();
create trigger trg_30_contractor_hpp_policy_row_version
before update on erp.contractor_hpp_policy_versions
for each row execute function erp.bump_row_version();
create trigger trg_40_contractor_hpp_policy_touch
before update on erp.contractor_hpp_policy_versions
for each row execute function erp.touch_updated_at();
create trigger trg_90_audit_contractor_hpp_policy
  after insert or update or delete on erp.contractor_hpp_policy_versions
  for each row execute function erp.audit_row_change();

create or replace function erp.save_contractor_hpp_policy_v1(
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_version bigint default null
) returns jsonb
language plpgsql
security definer
set search_path to 'erp','public','auth','extensions','pg_temp'
as $function$
declare
  v_operation constant text := 'save_contractor_hpp_policy_v1';
  v_hash text;
  v_cached jsonb;
  v_id uuid;
  v_contractor erp.contractors%rowtype;
  v_row erp.contractor_hpp_policy_versions%rowtype;
  v_response jsonb;
  v_effective_to date;
  v_previous_setting text;
begin
  perform erp.require_owner_admin();
  perform erp._cp3_assert_json_object_v1(
    p_payload,
    array['contractor_id','effective_from','attendance_required','is_special','change_reason'],
    array['id','effective_to'],
    'contractor HPP policy payload'
  );
  if jsonb_typeof(p_payload->'contractor_id') <> 'string'
     or jsonb_typeof(p_payload->'effective_from') <> 'string'
     or jsonb_typeof(p_payload->'attendance_required') <> 'boolean'
     or jsonb_typeof(p_payload->'is_special') <> 'boolean'
     or jsonb_typeof(p_payload->'change_reason') <> 'string'
     or (p_payload ? 'effective_to' and jsonb_typeof(p_payload->'effective_to') not in ('string','null'))
     or (p_payload ? 'id' and jsonb_typeof(p_payload->'id') not in ('string','null'))
  then
    raise exception 'Contractor HPP policy payload has invalid field types';
  end if;
  if nullif(btrim(p_payload->>'change_reason'),'') is null then
    raise exception 'change_reason is required';
  end if;

  v_id := nullif(p_payload->>'id','')::uuid;
  v_effective_to := nullif(p_payload->>'effective_to','')::date;
  select * into v_contractor from erp.contractors where id=(p_payload->>'contractor_id')::uuid;
  if v_contractor.id is null then raise exception 'Contractor not found'; end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload',p_payload,'expected_version',p_expected_version,
    'role_snapshot',v_contractor.contractor_type
  ));
  v_cached := erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  v_previous_setting := current_setting('app.cp3_policy_write', true);
  perform set_config('app.cp3_policy_write','on',true);
  if v_id is null then
    if p_expected_version is not null then
      raise exception 'expected_version must be null for a new policy version';
    end if;
    insert into erp.contractor_hpp_policy_versions(
      contractor_id,effective_from,effective_to,role_snapshot,
      attendance_required,is_special,change_reason,created_by
    ) values (
      v_contractor.id,(p_payload->>'effective_from')::date,v_effective_to,
      v_contractor.contractor_type,(p_payload->>'attendance_required')::boolean,
      (p_payload->>'is_special')::boolean,btrim(p_payload->>'change_reason'),
      erp.current_app_user_id()
    ) returning * into v_row;
  else
    if p_expected_version is null then raise exception 'expected_version is required'; end if;
    select * into v_row from erp.contractor_hpp_policy_versions where id=v_id for update;
    if v_row.id is null then raise exception 'Contractor HPP policy version not found'; end if;
    if v_row.row_version <> p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_row.row_version;
    end if;
    if v_row.contractor_id is distinct from v_contractor.id then
      raise exception 'Policy contractor identity cannot be changed';
    end if;
    update erp.contractor_hpp_policy_versions
    set effective_from=(p_payload->>'effective_from')::date,
        effective_to=v_effective_to,
        role_snapshot=v_contractor.contractor_type,
        attendance_required=(p_payload->>'attendance_required')::boolean,
        is_special=(p_payload->>'is_special')::boolean,
        change_reason=btrim(p_payload->>'change_reason')
    where id=v_id returning * into v_row;
  end if;
  perform set_config('app.cp3_policy_write',coalesce(v_previous_setting,'off'),true);

  v_response := jsonb_build_object(
    'policy_version_id',v_row.id,
    'contractor_id',v_row.contractor_id,
    'effective_from',v_row.effective_from,
    'effective_to',v_row.effective_to,
    'role_snapshot',v_row.role_snapshot,
    'attendance_required',v_row.attendance_required,
    'is_special',v_row.is_special,
    'row_version',v_row.row_version
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

create or replace function erp._cp3_guard_sewing_terminal_write()
returns trigger
language plpgsql
set search_path to 'erp','public','pg_temp'
as $function$
begin
  if coalesce(current_setting('app.cp3_sewing_terminal_write', true), 'off') <> 'on' then
    raise exception 'SELESAI_DIJAHIT facts are write-protected; use the owning sewing RPC';
  end if;
  if tg_op = 'DELETE' then
    raise exception 'SELESAI_DIJAHIT facts cannot be deleted; use reversal';
  end if;
  if tg_op = 'UPDATE' then
    if new.event_number is distinct from old.event_number
       or new.event_type is distinct from old.event_type
       or new.origin_type is distinct from old.origin_type
       or new.po_id is distinct from old.po_id
       or new.contractor_id is distinct from old.contractor_id
       or new.cutting_group_id is distinct from old.cutting_group_id
       or new.qty_pcs is distinct from old.qty_pcs
       or new.physical_at is distinct from old.physical_at
       or new.correction_of_event_id is distinct from old.correction_of_event_id
       or new.created_by is distinct from old.created_by
       or new.created_at is distinct from old.created_at
    then
      raise exception 'SELESAI_DIJAHIT fact identity/quantity/time is immutable; insert a correction fact';
    end if;
  end if;
  return new;
end;
$function$;

create trigger trg_10_sewing_terminal_write
before insert or update or delete on erp.sewing_terminal_events
for each row execute function erp._cp3_guard_sewing_terminal_write();
create trigger trg_20_sewing_terminal_row_version
before update on erp.sewing_terminal_events
for each row execute function erp.bump_row_version();
create trigger trg_30_sewing_terminal_touch
before update on erp.sewing_terminal_events
for each row execute function erp.touch_updated_at();
create trigger trg_90_audit_sewing_terminal
  after insert or update or delete on erp.sewing_terminal_events
  for each row execute function erp.audit_row_change();

create or replace function erp._cp3_assert_sewing_capacity(
  p_cutting_group_id uuid,
  p_excluding_event_id uuid,
  p_replacement_qty integer
) returns void
language plpgsql
security definer
set search_path to 'erp','public','pg_temp'
as $function$
declare
  v_cut_qty bigint;
  v_active_qty bigint;
  v_sent_qty bigint;
begin
  perform 1 from erp.cutting_groups where id=p_cutting_group_id for update;
  if not found then raise exception 'Cutting group not found'; end if;

  select coalesce(total_pcs,0) into v_cut_qty
  from erp.v_cutting_group_totals where cutting_group_id=p_cutting_group_id;
  if coalesce(v_cut_qty,0) <= 0 then
    raise exception 'Cutting group has no positive authoritative effective cut quantity';
  end if;

  select coalesce(sum(qty_pcs),0) into v_active_qty
  from erp.sewing_terminal_events
  where cutting_group_id=p_cutting_group_id and status='POSTED'
    and id is distinct from p_excluding_event_id;
  v_active_qty := v_active_qty + coalesce(p_replacement_qty,0);

  select coalesce(sum(ldl.qty_sent_pcs),0) into v_sent_qty
  from erp.laundry_delivery_lines ldl
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  where ldl.cutting_group_id=p_cutting_group_id
    and ld.status not in ('DRAFT','REVERSED');

  if v_active_qty > v_cut_qty then
    raise exception 'SELESAI_DIJAHIT qty % exceeds authoritative cut qty %',v_active_qty,v_cut_qty;
  end if;
  if v_active_qty < v_sent_qty then
    raise exception 'SELESAI_DIJAHIT qty % cannot fall below already-sent laundry qty %',v_active_qty,v_sent_qty;
  end if;
end;
$function$;

create or replace function erp.record_sewing_terminal_v1(
  p_payload jsonb,
  p_client_request_id uuid
) returns jsonb
language plpgsql
security definer
set search_path to 'erp','public','auth','extensions','pg_temp'
as $function$
declare
  v_operation constant text := 'record_sewing_terminal_v1';
  v_hash text;
  v_cached jsonb;
  v_po erp.production_orders%rowtype;
  v_group erp.cutting_groups%rowtype;
  v_row erp.sewing_terminal_events%rowtype;
  v_physical_at timestamptz;
  v_response jsonb;
  v_previous_setting text;
begin
  perform erp.require_internal();
  perform erp._cp3_assert_json_object_v1(
    p_payload,
    array['event_number','po_id','cutting_group_id','qty_pcs','physical_at','reason'],
    array[]::text[],
    'SELESAI_DIJAHIT payload'
  );
  if jsonb_typeof(p_payload->'event_number') <> 'string'
     or jsonb_typeof(p_payload->'po_id') <> 'string'
     or jsonb_typeof(p_payload->'cutting_group_id') <> 'string'
     or jsonb_typeof(p_payload->'qty_pcs') <> 'number'
     or jsonb_typeof(p_payload->'physical_at') <> 'string'
     or jsonb_typeof(p_payload->'reason') <> 'string'
  then raise exception 'SELESAI_DIJAHIT payload has invalid field types'; end if;
  if nullif(btrim(p_payload->>'event_number'),'') is null
     or nullif(btrim(p_payload->>'reason'),'') is null
  then raise exception 'event_number and reason are required'; end if;
  if (p_payload->>'qty_pcs')::integer <= 0 then raise exception 'qty_pcs must be positive'; end if;
  v_physical_at := (p_payload->>'physical_at')::timestamptz;
  if v_physical_at > clock_timestamp()+interval '5 minutes' then
    raise exception 'SELESAI_DIJAHIT physical_at cannot be in the future';
  end if;

  v_hash := erp._request_hash(p_payload);
  v_cached := erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_po from erp.production_orders where id=(p_payload->>'po_id')::uuid for update;
  if v_po.id is null or v_po.contractor_id is null then
    raise exception 'PO with assigned Mandor is required';
  end if;
  select * into v_group from erp.cutting_groups
  where id=(p_payload->>'cutting_group_id')::uuid for update;
  if v_group.id is null or v_group.po_id is distinct from v_po.id then
    raise exception 'Cutting group does not belong to the PO';
  end if;
  if v_group.picked_up_at is null or v_physical_at < v_group.picked_up_at then
    raise exception 'SELESAI_DIJAHIT cannot precede Mandor pickup';
  end if;
  if v_po.contractor_id is distinct from (select contractor_id from erp.production_orders where id=v_po.id) then
    raise exception 'PO Mandor changed during sewing record';
  end if;
  perform erp._cp3_assert_sewing_capacity(v_group.id,null,(p_payload->>'qty_pcs')::integer);

  v_previous_setting := current_setting('app.cp3_sewing_terminal_write', true);
  perform set_config('app.cp3_sewing_terminal_write','on',true);
  insert into erp.sewing_terminal_events(
    event_number,po_id,contractor_id,cutting_group_id,qty_pcs,physical_at,
    status,change_reason,created_by
  ) values (
    btrim(p_payload->>'event_number'),v_po.id,v_po.contractor_id,v_group.id,
    (p_payload->>'qty_pcs')::integer,v_physical_at,'POSTED',
    btrim(p_payload->>'reason'),erp.current_app_user_id()
  ) returning * into v_row;
  perform set_config('app.cp3_sewing_terminal_write',coalesce(v_previous_setting,'off'),true);

  v_response := jsonb_build_object(
    'sewing_terminal_event_id',v_row.id,
    'event_number',v_row.event_number,
    'event_type',v_row.event_type,
    'origin_type',v_row.origin_type,
    'status',v_row.status,
    'qty_pcs',v_row.qty_pcs,
    'physical_at_epoch_us',erp._cp3_epoch_us(v_row.physical_at),
    'row_version',v_row.row_version
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

create or replace function erp.correct_sewing_terminal_v1(
  p_event_id uuid,
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_version bigint
) returns jsonb
language plpgsql
security definer
set search_path to 'erp','public','auth','extensions','pg_temp'
as $function$
declare
  v_operation constant text := 'correct_sewing_terminal_v1';
  v_hash text;
  v_cached jsonb;
  v_source erp.sewing_terminal_events%rowtype;
  v_replacement erp.sewing_terminal_events%rowtype;
  v_physical_at timestamptz;
  v_response jsonb;
  v_previous_setting text;
begin
  perform erp.require_owner_admin();
  perform erp._cp3_assert_json_object_v1(
    p_payload,array['replacement_event_number','qty_pcs','physical_at','reason'],array[]::text[],
    'SELESAI_DIJAHIT correction payload'
  );
  if jsonb_typeof(p_payload->'replacement_event_number') <> 'string'
     or jsonb_typeof(p_payload->'qty_pcs') <> 'number'
     or jsonb_typeof(p_payload->'physical_at') <> 'string'
     or jsonb_typeof(p_payload->'reason') <> 'string'
  then raise exception 'SELESAI_DIJAHIT correction payload has invalid field types'; end if;
  if p_expected_version is null then raise exception 'expected_version is required'; end if;
  if nullif(btrim(p_payload->>'replacement_event_number'),'') is null
     or nullif(btrim(p_payload->>'reason'),'') is null
  then raise exception 'replacement_event_number and reason are required'; end if;
  if (p_payload->>'qty_pcs')::integer <= 0 then raise exception 'qty_pcs must be positive'; end if;
  v_physical_at := (p_payload->>'physical_at')::timestamptz;
  if v_physical_at > clock_timestamp()+interval '5 minutes' then
    raise exception 'SELESAI_DIJAHIT physical_at cannot be in the future';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'event_id',p_event_id,'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_source from erp.sewing_terminal_events where id=p_event_id for update;
  if v_source.id is null then raise exception 'SELESAI_DIJAHIT event not found'; end if;
  if v_source.status <> 'POSTED' then raise exception 'Only POSTED SELESAI_DIJAHIT can be corrected'; end if;
  if v_source.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_source.row_version;
  end if;
  if exists (
    select 1
    from erp.attendance_hpp_pool_allocations a
    join erp.attendance_hpp_pools p on p.id=a.pool_id
    where a.sewing_terminal_event_id=v_source.id and p.status in ('ACTIVE','POSTED')
  ) then
    raise exception 'Cancel/reverse the consuming attendance HPP pool before correcting SELESAI_DIJAHIT';
  end if;
  if v_physical_at < (select picked_up_at from erp.cutting_groups where id=v_source.cutting_group_id) then
    raise exception 'SELESAI_DIJAHIT cannot precede Mandor pickup';
  end if;
  perform erp._cp3_assert_sewing_capacity(
    v_source.cutting_group_id,v_source.id,(p_payload->>'qty_pcs')::integer
  );

  v_previous_setting := current_setting('app.cp3_sewing_terminal_write', true);
  perform set_config('app.cp3_sewing_terminal_write','on',true);
  update erp.sewing_terminal_events
  set status='CORRECTED',change_reason=btrim(p_payload->>'reason')
  where id=v_source.id;
  insert into erp.sewing_terminal_events(
    event_number,po_id,contractor_id,cutting_group_id,qty_pcs,physical_at,
    status,correction_of_event_id,change_reason,created_by
  ) values (
    btrim(p_payload->>'replacement_event_number'),v_source.po_id,v_source.contractor_id,
    v_source.cutting_group_id,(p_payload->>'qty_pcs')::integer,v_physical_at,
    'POSTED',v_source.id,btrim(p_payload->>'reason'),erp.current_app_user_id()
  ) returning * into v_replacement;
  perform set_config('app.cp3_sewing_terminal_write',coalesce(v_previous_setting,'off'),true);

  v_response := jsonb_build_object(
    'source_event_id',v_source.id,'source_status','CORRECTED',
    'replacement_event_id',v_replacement.id,'replacement_status',v_replacement.status,
    'replacement_row_version',v_replacement.row_version
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

create or replace function erp.reverse_sewing_terminal_v1(
  p_event_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
) returns jsonb
language plpgsql
security definer
set search_path to 'erp','public','auth','extensions','pg_temp'
as $function$
declare
  v_operation constant text := 'reverse_sewing_terminal_v1';
  v_hash text;
  v_cached jsonb;
  v_row erp.sewing_terminal_events%rowtype;
  v_source erp.sewing_terminal_events%rowtype;
  v_response jsonb;
  v_previous_setting text;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null or p_expected_version is null then
    raise exception 'reason and expected_version are required';
  end if;
  v_hash := erp._request_hash(jsonb_build_object(
    'event_id',p_event_id,'reason',btrim(p_reason),'expected_version',p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_row from erp.sewing_terminal_events where id=p_event_id for update;
  if v_row.id is null then raise exception 'SELESAI_DIJAHIT event not found'; end if;
  if v_row.status <> 'POSTED' then raise exception 'Only POSTED SELESAI_DIJAHIT can be reversed'; end if;
  if v_row.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_row.row_version;
  end if;
  if exists (
    select 1
    from erp.attendance_hpp_pool_allocations a
    join erp.attendance_hpp_pools p on p.id=a.pool_id
    where a.sewing_terminal_event_id=v_row.id and p.status in ('ACTIVE','POSTED')
  ) then
    raise exception 'Cancel/reverse the consuming attendance HPP pool before reversing SELESAI_DIJAHIT';
  end if;
  if v_row.correction_of_event_id is not null then
    select * into v_source
    from erp.sewing_terminal_events
    where id=v_row.correction_of_event_id
    for update;
    if v_source.id is null or v_source.status<>'CORRECTED' then
      raise exception 'Correction source cannot be restored from status %',v_source.status;
    end if;
    perform erp._cp3_assert_sewing_capacity(
      v_row.cutting_group_id,v_row.id,v_source.qty_pcs
    );
  else
    perform erp._cp3_assert_sewing_capacity(v_row.cutting_group_id,v_row.id,0);
  end if;

  v_previous_setting := current_setting('app.cp3_sewing_terminal_write', true);
  perform set_config('app.cp3_sewing_terminal_write','on',true);
  update erp.sewing_terminal_events
  set status='REVERSED',change_reason=btrim(p_reason)
  where id=v_row.id returning * into v_row;
  if v_source.id is not null then
    update erp.sewing_terminal_events
    set status='POSTED',change_reason='Restored after correction reversal: '||btrim(p_reason)
    where id=v_source.id returning * into v_source;
  end if;
  perform set_config('app.cp3_sewing_terminal_write',coalesce(v_previous_setting,'off'),true);

  v_response := jsonb_build_object(
    'sewing_terminal_event_id',v_row.id,'status',v_row.status,'row_version',v_row.row_version,
    'restored_source_event_id',v_source.id,
    'restored_source_row_version',v_source.row_version
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

create or replace function erp._cp3_guard_attendance_hpp_write()
returns trigger
language plpgsql
set search_path to 'erp','public','pg_temp'
as $function$
begin
  if coalesce(current_setting('app.cp3_attendance_hpp_write', true), 'off') <> 'on' then
    raise exception '% is system-managed; use attendance HPP owning RPCs',tg_table_name;
  end if;
  if tg_op='DELETE' and tg_table_name='attendance_hpp_pools' then
    raise exception 'Attendance HPP pools cannot be deleted; cancel or reverse them';
  end if;
  return case when tg_op='DELETE' then old else new end;
end;
$function$;

create trigger trg_10_attendance_hpp_pool_write
before insert or update or delete on erp.attendance_hpp_pools
for each row execute function erp._cp3_guard_attendance_hpp_write();
create trigger trg_20_attendance_hpp_pool_row_version
before update on erp.attendance_hpp_pools
for each row execute function erp.bump_row_version();
create trigger trg_30_attendance_hpp_pool_touch
before update on erp.attendance_hpp_pools
for each row execute function erp.touch_updated_at();
create trigger trg_90_audit_attendance_hpp_pool
  after insert or update or delete on erp.attendance_hpp_pools
  for each row execute function erp.audit_row_change();

create trigger trg_10_attendance_hpp_source_write
before insert or update or delete on erp.attendance_hpp_pool_sources
for each row execute function erp._cp3_guard_attendance_hpp_write();
create trigger trg_10_attendance_hpp_allocation_write
before insert or update or delete on erp.attendance_hpp_pool_allocations
for each row execute function erp._cp3_guard_attendance_hpp_write();
create trigger trg_10_attendance_hpp_credit_map_write
before insert or update or delete on erp.attendance_hpp_journal_credit_map
for each row execute function erp._cp3_guard_attendance_hpp_write();
create trigger trg_10_attendance_hpp_debit_map_write
before insert or update or delete on erp.attendance_hpp_journal_debit_map
for each row execute function erp._cp3_guard_attendance_hpp_write();

create or replace function erp.attendance_hpp_pool_manifest_v1(p_pool_id uuid)
returns jsonb
language sql
stable
security definer
set search_path to 'erp','public','pg_temp'
as $function$
  select jsonb_build_object(
    'contract','ATTENDANCE_HPP_SEWING_TERMINAL_V1',
    'pool_id',p.id,
    'pool_number',p.pool_number,
    'period_start',p.period_start,
    'period_end',p.period_end,
    'correction_of_pool_id',p.correction_of_pool_id,
    'numerator_amount',p.numerator_amount,
    'denominator_qty',p.denominator_qty,
    'allocated_amount',p.allocated_amount,
    'sources',coalesce((
      select jsonb_agg(jsonb_build_object(
        'payroll_id',s.payroll_id,
        'contractor_id',s.contractor_id,
        'policy_version_id',s.policy_version_id,
        'source_journal_entry_id',s.source_journal_entry_id,
        'source_journal_line_id',s.source_journal_line_id,
        'attendance_amount',s.attendance_amount,
        'source_line_debit_snapshot',s.source_line_debit_snapshot,
        'role_snapshot',s.role_snapshot,
        'attendance_required_snapshot',s.attendance_required_snapshot,
        'is_special_snapshot',s.is_special_snapshot,
        'payroll_row_version_snapshot',s.payroll_row_version_snapshot,
        'source_posting_epoch_us',s.source_posting_epoch_us,
        'period_start_snapshot',s.period_start_snapshot,
        'period_end_snapshot',s.period_end_snapshot
      ) order by s.source_journal_line_id,s.payroll_id)
      from erp.attendance_hpp_pool_sources s where s.pool_id=p.id
    ),'[]'::jsonb),
    'allocations',coalesce((
      select jsonb_agg(jsonb_build_object(
        'sewing_terminal_event_id',a.sewing_terminal_event_id,
        'po_id',a.po_id,
        'contractor_id',a.contractor_id,
        'cutting_group_id',a.cutting_group_id,
        'policy_version_id',a.policy_version_id,
        'qty_pcs',a.qty_pcs,
        'allocation_amount',a.allocation_amount,
        'event_row_version_snapshot',a.event_row_version_snapshot,
        'event_physical_epoch_us',a.event_physical_epoch_us
      ) order by a.sewing_terminal_event_id,a.po_id)
      from erp.attendance_hpp_pool_allocations a where a.pool_id=p.id
    ),'[]'::jsonb)
  )
  from erp.attendance_hpp_pools p where p.id=p_pool_id
$function$;

create or replace function erp.attendance_hpp_pool_digest_v1(p_pool_id uuid)
returns text
language sql
stable
security definer
set search_path to 'erp','public','extensions','pg_temp'
as $function$
  select erp._request_hash(erp.attendance_hpp_pool_manifest_v1(p_pool_id))
$function$;

create or replace function erp.validate_attendance_hpp_pool_v1(p_pool_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path to 'erp','public','pg_temp'
as $function$
declare
  v_pool erp.attendance_hpp_pools%rowtype;
  v_source_count bigint;
  v_allocation_count bigint;
  v_source_total numeric(20,2);
  v_allocation_total numeric(20,2);
  v_qty_total bigint;
  v_manifest jsonb;
  v_digest text;
  v_issue_count bigint:=0;
begin
  select * into v_pool from erp.attendance_hpp_pools where id=p_pool_id;
  if v_pool.id is null then raise exception 'Attendance HPP pool not found'; end if;

  select count(*),coalesce(sum(attendance_amount),0)
  into v_source_count,v_source_total
  from erp.attendance_hpp_pool_sources where pool_id=v_pool.id;
  select count(*),coalesce(sum(qty_pcs),0),coalesce(sum(allocation_amount),0)
  into v_allocation_count,v_qty_total,v_allocation_total
  from erp.attendance_hpp_pool_allocations where pool_id=v_pool.id;

  if v_source_count=0 or v_source_total<=0 then v_issue_count:=v_issue_count+1; end if;
  if v_allocation_count=0 or v_qty_total<=0 then v_issue_count:=v_issue_count+1; end if;
  if round(v_source_total,2) is distinct from round(v_pool.numerator_amount,2) then v_issue_count:=v_issue_count+1; end if;
  if v_qty_total is distinct from v_pool.denominator_qty::bigint then v_issue_count:=v_issue_count+1; end if;
  if round(v_allocation_total,2) is distinct from round(v_pool.numerator_amount,2)
     or round(v_pool.allocated_amount,2) is distinct from round(v_pool.numerator_amount,2)
  then v_issue_count:=v_issue_count+1; end if;

  select count(*) into v_source_count
  from erp.attendance_hpp_pool_sources s
  join erp.payroll_settlements ps on ps.id=s.payroll_id
  join erp.contractor_hpp_policy_versions pv on pv.id=s.policy_version_id
  join erp.journal_entries je on je.id=s.source_journal_entry_id
  join erp.journal_lines jl on jl.id=s.source_journal_line_id
  where s.pool_id=v_pool.id
    and (
      ps.status<>'PAID'
      or ps.period_start is distinct from v_pool.period_start
      or ps.period_end is distinct from v_pool.period_end
      or round(ps.attendance_total,2) is distinct from round(s.attendance_amount,2)
      or pv.role_snapshot<>'MANDOR' or not pv.attendance_required or pv.is_special
      or pv.effective_from>v_pool.period_start
      or (pv.effective_to is not null and pv.effective_to<v_pool.period_end)
      or je.status<>'POSTED' or je.source_type<>'PAYROLL_EXTRA_ACCRUAL' or je.source_id is distinct from ps.id
      or jl.journal_entry_id is distinct from je.id
      or jl.account_id is distinct from erp.account_id('LABOR_COST')
      or round(jl.debit,2)<round(s.attendance_amount,2)
      or erp._cp3_epoch_us(je.posting_at) is distinct from s.source_posting_epoch_us
    );
  v_issue_count:=v_issue_count+v_source_count;

  select count(*) into v_allocation_count
  from erp.attendance_hpp_pool_allocations a
  join erp.sewing_terminal_events e on e.id=a.sewing_terminal_event_id
  join erp.contractor_hpp_policy_versions pv on pv.id=a.policy_version_id
  where a.pool_id=v_pool.id
    and (
      e.status<>'POSTED' or e.event_type<>'SELESAI_DIJAHIT' or e.origin_type<>'CUTTING_GROUP_SEWING'
      or e.po_id is distinct from a.po_id or e.contractor_id is distinct from a.contractor_id
      or e.cutting_group_id is distinct from a.cutting_group_id
      or e.qty_pcs is distinct from a.qty_pcs or e.row_version is distinct from a.event_row_version_snapshot
      or e.physical_at::date<v_pool.period_start or e.physical_at::date>v_pool.period_end
      or erp._cp3_epoch_us(e.physical_at) is distinct from a.event_physical_epoch_us
      or pv.role_snapshot<>'MANDOR' or not pv.attendance_required or pv.is_special
      or pv.effective_from>v_pool.period_start
      or (pv.effective_to is not null and pv.effective_to<v_pool.period_end)
    );
  v_issue_count:=v_issue_count+v_allocation_count;

  v_manifest:=erp.attendance_hpp_pool_manifest_v1(v_pool.id);
  v_digest:=erp._request_hash(v_manifest);
  if v_pool.manifest is distinct from v_manifest or v_pool.manifest_digest is distinct from v_digest then
    v_issue_count:=v_issue_count+1;
  end if;

  if v_issue_count>0 then
    raise exception 'Attendance HPP pool validation failed with % issue(s)',v_issue_count;
  end if;
  return jsonb_build_object(
    'pool_id',v_pool.id,'status',v_pool.status,
    'source_count',(select count(*) from erp.attendance_hpp_pool_sources where pool_id=v_pool.id),
    'allocation_count',(select count(*) from erp.attendance_hpp_pool_allocations where pool_id=v_pool.id),
    'numerator_amount',v_pool.numerator_amount,'denominator_qty',v_pool.denominator_qty,
    'allocated_amount',v_pool.allocated_amount,'manifest_digest',v_pool.manifest_digest,
    'validation','PASS'
  );
end;
$function$;

create or replace function erp.preview_attendance_hpp_pool_v1(
  p_period_start date,
  p_period_end date
) returns jsonb
language plpgsql
stable
security definer
set search_path to 'erp','public','pg_temp'
as $function$
declare
  v_missing_policy bigint;
  v_source_amount numeric(20,2);
  v_source_count bigint;
  v_denominator bigint;
  v_event_count bigint;
begin
  perform erp.require_internal();
  if p_period_start is null or p_period_end is null or p_period_end<p_period_start then
    raise exception 'Valid period_start/period_end are required';
  end if;

  select count(*) into v_missing_policy
  from erp.payroll_settlements ps
  where ps.status='PAID' and ps.period_start=p_period_start and ps.period_end=p_period_end
    and ps.attendance_total>0
    and (select count(*) from erp.contractor_hpp_policy_versions pv
         where pv.contractor_id=ps.contractor_id and pv.effective_from<=p_period_start
           and (pv.effective_to is null or pv.effective_to>=p_period_end))<>1;
  if v_missing_policy>0 then raise exception '% attendance payroll source(s) lack one full-period HPP policy',v_missing_policy; end if;

  select count(*),coalesce(sum(round(ps.attendance_total,2)),0)
  into v_source_count,v_source_amount
  from erp.payroll_settlements ps
  join erp.contractor_hpp_policy_versions pv
    on pv.contractor_id=ps.contractor_id and pv.effective_from<=p_period_start
   and (pv.effective_to is null or pv.effective_to>=p_period_end)
  where ps.status='PAID' and ps.period_start=p_period_start and ps.period_end=p_period_end
    and ps.attendance_total>0 and pv.role_snapshot='MANDOR'
    and pv.attendance_required and not pv.is_special;

  select count(*) into v_missing_policy
  from erp.sewing_terminal_events e
  where e.status='POSTED' and e.event_type='SELESAI_DIJAHIT'
    and e.physical_at::date between p_period_start and p_period_end
    and (select count(*) from erp.contractor_hpp_policy_versions pv
         where pv.contractor_id=e.contractor_id and pv.effective_from<=p_period_start
           and (pv.effective_to is null or pv.effective_to>=p_period_end))<>1;
  if v_missing_policy>0 then raise exception '% SELESAI_DIJAHIT fact(s) lack one full-period HPP policy',v_missing_policy; end if;

  select count(*),coalesce(sum(e.qty_pcs),0)
  into v_event_count,v_denominator
  from erp.sewing_terminal_events e
  join erp.contractor_hpp_policy_versions pv
    on pv.contractor_id=e.contractor_id and pv.effective_from<=p_period_start
   and (pv.effective_to is null or pv.effective_to>=p_period_end)
  where e.status='POSTED' and e.event_type='SELESAI_DIJAHIT'
    and e.origin_type='CUTTING_GROUP_SEWING'
    and e.physical_at::date between p_period_start and p_period_end
    and pv.role_snapshot='MANDOR' and pv.attendance_required and not pv.is_special;

  if v_source_amount>0 and v_denominator=0 then
    raise exception 'Positive attendance HPP pool % has zero eligible SELESAI_DIJAHIT denominator',v_source_amount;
  end if;
  return jsonb_build_object(
    'period_start',p_period_start,'period_end',p_period_end,
    'source_count',v_source_count,'numerator_amount',v_source_amount,
    'event_count',v_event_count,'denominator_qty',v_denominator,
    'basis','SELESAI_DIJAHIT','qc_good_used',false,'rework_good_used',false
  );
end;
$function$;

create or replace function erp._cp3_create_attendance_hpp_pool(
  p_pool_number text,
  p_period_start date,
  p_period_end date,
  p_reason text,
  p_correction_of_pool_id uuid default null
) returns uuid
language plpgsql
security definer
set search_path to 'erp','public','pg_temp'
as $function$
declare
  v_pool_id uuid;
  v_missing bigint;
  v_source_amount numeric(20,2);
  v_denominator bigint;
  v_total_cents bigint;
  v_base_cents bigint;
  v_extra_cents bigint;
  v_manifest jsonb;
  v_digest text;
begin
  if nullif(btrim(p_pool_number),'') is null or nullif(btrim(p_reason),'') is null then
    raise exception 'pool_number and reason are required';
  end if;
  if p_period_start is null or p_period_end is null or p_period_end<p_period_start then
    raise exception 'Valid period_start/period_end are required';
  end if;
  -- One global range lock prevents two differently-keyed overlapping periods
  -- from being created concurrently. The period lock remains the narrow lock
  -- used by post/cancel/reverse/correct for the same exact pool period.
  perform pg_advisory_xact_lock(hashtextextended('CP3_ATT_HPP_POOL_RANGE',0));
  perform pg_advisory_xact_lock(hashtextextended(
    'CP3_ATT_HPP_PERIOD|'||p_period_start::text||'|'||p_period_end::text,0
  ));

  if p_correction_of_pool_id is null and exists (
    select 1 from erp.attendance_hpp_pools p
    where p.status in ('ACTIVE','POSTED')
      and p.period_start<=p_period_end and p.period_end>=p_period_start
  ) then raise exception 'An overlapping ACTIVE/POSTED attendance HPP pool already exists'; end if;
  if p_correction_of_pool_id is not null and not exists (
    select 1 from erp.attendance_hpp_pools p
    where p.id=p_correction_of_pool_id and p.period_start=p_period_start
      and p.period_end=p_period_end and p.status='POSTED'
  ) then raise exception 'Correction source must be a POSTED pool for the same period'; end if;

  insert into erp.attendance_hpp_pools(
    pool_number,period_start,period_end,status,correction_of_pool_id,
    change_reason,created_by
  ) values (
    btrim(p_pool_number),p_period_start,p_period_end,'ACTIVE',p_correction_of_pool_id,
    btrim(p_reason),erp.current_app_user_id()
  ) returning id into v_pool_id;

  select count(*) into v_missing
  from erp.payroll_settlements ps
  where ps.status='PAID' and ps.period_start=p_period_start and ps.period_end=p_period_end
    and ps.attendance_total>0
    and (select count(*) from erp.contractor_hpp_policy_versions pv
         where pv.contractor_id=ps.contractor_id and pv.effective_from<=p_period_start
           and (pv.effective_to is null or pv.effective_to>=p_period_end))<>1;
  if v_missing>0 then raise exception '% attendance payroll source(s) lack one full-period HPP policy',v_missing; end if;

  select count(*) into v_missing
  from erp.payroll_settlements ps
  join erp.contractor_hpp_policy_versions pv
    on pv.contractor_id=ps.contractor_id and pv.effective_from<=p_period_start
   and (pv.effective_to is null or pv.effective_to>=p_period_end)
  where ps.status='PAID' and ps.period_start=p_period_start and ps.period_end=p_period_end
    and ps.attendance_total>0 and pv.role_snapshot='MANDOR'
    and pv.attendance_required and not pv.is_special
    and round(ps.attendance_total,2) is distinct from round(coalesce((
      select sum(pai.amount) from erp.payroll_attendance_items pai where pai.payroll_id=ps.id
    ),0),2);
  if v_missing>0 then raise exception '% eligible payroll source(s) do not reconcile to attendance items',v_missing; end if;

  select count(*) into v_missing
  from erp.payroll_settlements ps
  join erp.contractor_hpp_policy_versions pv
    on pv.contractor_id=ps.contractor_id and pv.effective_from<=p_period_start
   and (pv.effective_to is null or pv.effective_to>=p_period_end)
  where ps.status='PAID' and ps.period_start=p_period_start and ps.period_end=p_period_end
    and ps.attendance_total>0 and pv.role_snapshot='MANDOR'
    and pv.attendance_required and not pv.is_special
    and (select count(*)
         from erp.journal_entries je
         join erp.journal_lines jl on jl.journal_entry_id=je.id
         where je.source_type='PAYROLL_EXTRA_ACCRUAL' and je.source_id=ps.id and je.status='POSTED'
           and jl.account_id=erp.account_id('LABOR_COST') and jl.debit>0)<>1;
  if v_missing>0 then raise exception '% eligible payroll source(s) lack exactly one posted LABOR_COST debit line',v_missing; end if;

  insert into erp.attendance_hpp_pool_sources(
    pool_id,payroll_id,contractor_id,policy_version_id,
    source_journal_entry_id,source_journal_line_id,attendance_amount,
    source_line_debit_snapshot,role_snapshot,attendance_required_snapshot,is_special_snapshot,
    payroll_row_version_snapshot,source_posting_epoch_us,period_start_snapshot,period_end_snapshot
  )
  select v_pool_id,ps.id,ps.contractor_id,pv.id,je.id,jl.id,
         round(ps.attendance_total,2),round(jl.debit,2),pv.role_snapshot,
         pv.attendance_required,pv.is_special,ps.row_version,
         erp._cp3_epoch_us(je.posting_at),ps.period_start,ps.period_end
  from erp.payroll_settlements ps
  join erp.contractor_hpp_policy_versions pv
    on pv.contractor_id=ps.contractor_id and pv.effective_from<=p_period_start
   and (pv.effective_to is null or pv.effective_to>=p_period_end)
  join erp.journal_entries je
    on je.source_type='PAYROLL_EXTRA_ACCRUAL' and je.source_id=ps.id and je.status='POSTED'
  join erp.journal_lines jl
    on jl.journal_entry_id=je.id and jl.account_id=erp.account_id('LABOR_COST') and jl.debit>0
  where ps.status='PAID' and ps.period_start=p_period_start and ps.period_end=p_period_end
    and ps.attendance_total>0 and pv.role_snapshot='MANDOR'
    and pv.attendance_required and not pv.is_special
  order by jl.id,ps.id;

  select coalesce(sum(attendance_amount),0) into v_source_amount
  from erp.attendance_hpp_pool_sources where pool_id=v_pool_id;
  if v_source_amount<=0 then raise exception 'No positive eligible normal-Mandor attendance payroll source exists'; end if;

  select count(*) into v_missing
  from erp.sewing_terminal_events e
  where e.status='POSTED' and e.event_type='SELESAI_DIJAHIT'
    and e.physical_at::date between p_period_start and p_period_end
    and (select count(*) from erp.contractor_hpp_policy_versions pv
         where pv.contractor_id=e.contractor_id and pv.effective_from<=p_period_start
           and (pv.effective_to is null or pv.effective_to>=p_period_end))<>1;
  if v_missing>0 then raise exception '% SELESAI_DIJAHIT fact(s) lack one full-period HPP policy',v_missing; end if;

  insert into erp.attendance_hpp_pool_allocations(
    pool_id,sewing_terminal_event_id,po_id,contractor_id,cutting_group_id,
    policy_version_id,qty_pcs,allocation_amount,event_row_version_snapshot,event_physical_epoch_us
  )
  select v_pool_id,e.id,e.po_id,e.contractor_id,e.cutting_group_id,pv.id,e.qty_pcs,0,
         e.row_version,erp._cp3_epoch_us(e.physical_at)
  from erp.sewing_terminal_events e
  join erp.contractor_hpp_policy_versions pv
    on pv.contractor_id=e.contractor_id and pv.effective_from<=p_period_start
   and (pv.effective_to is null or pv.effective_to>=p_period_end)
  where e.status='POSTED' and e.event_type='SELESAI_DIJAHIT'
    and e.origin_type='CUTTING_GROUP_SEWING'
    and e.physical_at::date between p_period_start and p_period_end
    and pv.role_snapshot='MANDOR' and pv.attendance_required and not pv.is_special
  order by e.id;

  select coalesce(sum(qty_pcs),0) into v_denominator
  from erp.attendance_hpp_pool_allocations where pool_id=v_pool_id;
  if v_denominator=0 then
    raise exception 'Positive attendance HPP pool % has zero eligible SELESAI_DIJAHIT denominator',v_source_amount;
  end if;

  v_total_cents:=round(v_source_amount*100)::bigint;
  with ranked as (
    select a.id,a.sewing_terminal_event_id,a.qty_pcs,
           floor((v_total_cents::numeric*a.qty_pcs::numeric)/v_denominator::numeric)::bigint as base_cents,
           mod(v_total_cents::numeric*a.qty_pcs::numeric,v_denominator::numeric)::bigint as remainder_cents
    from erp.attendance_hpp_pool_allocations a where a.pool_id=v_pool_id
  ), scored as (
    select r.*,row_number() over(order by remainder_cents desc,sewing_terminal_event_id) as remainder_rank,
           sum(base_cents) over() as base_total
    from ranked r
  )
  update erp.attendance_hpp_pool_allocations a
  set allocation_amount=(s.base_cents + case when s.remainder_rank <= v_total_cents-s.base_total then 1 else 0 end)::numeric/100
  from scored s where a.id=s.id;

  select coalesce(sum(round(allocation_amount*100)::bigint),0),
         coalesce(sum(round(allocation_amount*100)::bigint),0)
  into v_base_cents,v_extra_cents
  from erp.attendance_hpp_pool_allocations where pool_id=v_pool_id;
  if v_base_cents is distinct from v_total_cents then
    raise exception 'Deterministic cent allocation residue: expected %, got %',v_total_cents,v_base_cents;
  end if;

  update erp.attendance_hpp_pools
  set numerator_amount=v_source_amount,denominator_qty=v_denominator,
      allocated_amount=v_total_cents::numeric/100
  where id=v_pool_id;
  v_manifest:=erp.attendance_hpp_pool_manifest_v1(v_pool_id);
  v_digest:=erp._request_hash(v_manifest);
  update erp.attendance_hpp_pools set manifest=v_manifest,manifest_digest=v_digest where id=v_pool_id;
  perform erp.validate_attendance_hpp_pool_v1(v_pool_id);
  return v_pool_id;
end;
$function$;

create or replace function erp.create_attendance_hpp_pool_v1(
  p_payload jsonb,
  p_client_request_id uuid
) returns jsonb
language plpgsql
security definer
set search_path to 'erp','public','auth','extensions','pg_temp'
as $function$
declare
  v_operation constant text := 'create_attendance_hpp_pool_v1';
  v_hash text;
  v_cached jsonb;
  v_pool_id uuid;
  v_pool erp.attendance_hpp_pools%rowtype;
  v_response jsonb;
  v_previous_setting text;
begin
  perform erp.require_owner_admin();
  perform erp._cp3_assert_json_object_v1(
    p_payload,array['pool_number','period_start','period_end','reason'],array['correction_of_pool_id'],
    'attendance HPP pool payload'
  );
  if jsonb_typeof(p_payload->'pool_number')<>'string'
     or jsonb_typeof(p_payload->'period_start')<>'string'
     or jsonb_typeof(p_payload->'period_end')<>'string'
     or jsonb_typeof(p_payload->'reason')<>'string'
     or (p_payload?'correction_of_pool_id' and jsonb_typeof(p_payload->'correction_of_pool_id') not in ('string','null'))
  then raise exception 'Attendance HPP pool payload has invalid field types'; end if;
  v_hash:=erp._request_hash(p_payload);
  v_cached:=erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  v_previous_setting:=current_setting('app.cp3_attendance_hpp_write',true);
  perform set_config('app.cp3_attendance_hpp_write','on',true);
  v_pool_id:=erp._cp3_create_attendance_hpp_pool(
    p_payload->>'pool_number',(p_payload->>'period_start')::date,(p_payload->>'period_end')::date,
    p_payload->>'reason',nullif(p_payload->>'correction_of_pool_id','')::uuid
  );
  perform set_config('app.cp3_attendance_hpp_write',coalesce(v_previous_setting,'off'),true);
  select * into v_pool from erp.attendance_hpp_pools where id=v_pool_id;
  v_response:=jsonb_build_object(
    'pool_id',v_pool.id,'pool_number',v_pool.pool_number,'status',v_pool.status,
    'row_version',v_pool.row_version,'numerator_amount',v_pool.numerator_amount,
    'denominator_qty',v_pool.denominator_qty,'allocated_amount',v_pool.allocated_amount,
    'manifest_digest',v_pool.manifest_digest
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

create or replace function erp._cp3_post_attendance_hpp_pool(
  p_pool_id uuid,
  p_reason text
) returns uuid
language plpgsql
security definer
set search_path to 'erp','public','pg_temp'
as $function$
declare
  v_pool erp.attendance_hpp_pools%rowtype;
  v_journal_lines jsonb;
  v_journal_id uuid;
  v_labour_account uuid;
  v_wip_account uuid;
  v_expected bigint;
  v_actual bigint;
begin
  select * into v_pool from erp.attendance_hpp_pools where id=p_pool_id for update;
  if v_pool.id is null then raise exception 'Attendance HPP pool not found'; end if;
  if v_pool.status<>'ACTIVE' then raise exception 'Only ACTIVE attendance HPP pool can be posted'; end if;
  perform erp.validate_attendance_hpp_pool_v1(v_pool.id);

  select coalesce(jsonb_agg(line order by sort_group,sort_key),'[]'::jsonb)
  into v_journal_lines
  from (
    select 1 sort_group,a.po_id::text sort_key,
           jsonb_build_object(
             'mapping_key','WIP','debit',round(sum(a.allocation_amount),2),'credit',0,
             'po_id',a.po_id,
             'description','ATT_HPP|POOL='||v_pool.id::text||'|DEST_PO='||a.po_id::text
           ) line
    from erp.attendance_hpp_pool_allocations a
    where a.pool_id=v_pool.id
    group by a.po_id having round(sum(a.allocation_amount),2)>0
    union all
    select 2,s.source_journal_line_id::text,
           jsonb_build_object(
             'mapping_key','LABOR_COST','debit',0,'credit',round(s.attendance_amount,2),
             'contractor_id',s.contractor_id,
             'description','ATT_HPP|POOL='||v_pool.id::text||'|SOURCE_LINE='||s.source_journal_line_id::text
           )
    from erp.attendance_hpp_pool_sources s where s.pool_id=v_pool.id
  ) q;

  if jsonb_array_length(v_journal_lines)<2 then raise exception 'Attendance HPP journal needs debit and credit lines'; end if;
  v_journal_id:=erp.post_journal(
    'ATTENDANCE_HPP_ALLOCATION',v_pool.id,v_pool.period_end,
    'Attendance HPP allocation by immutable SELESAI_DIJAHIT',v_journal_lines
  );
  v_labour_account:=erp.account_id('LABOR_COST');
  v_wip_account:=erp.account_id('WIP');

  insert into erp.attendance_hpp_journal_credit_map(
    pool_id,source_journal_line_id,reclass_journal_line_id,amount
  )
  select v_pool.id,s.source_journal_line_id,jl.id,round(s.attendance_amount,2)
  from erp.attendance_hpp_pool_sources s
  join erp.journal_lines jl
    on jl.journal_entry_id=v_journal_id and jl.account_id=v_labour_account
   and jl.credit=round(s.attendance_amount,2)
   and jl.description='ATT_HPP|POOL='||v_pool.id::text||'|SOURCE_LINE='||s.source_journal_line_id::text
  where s.pool_id=v_pool.id;

  insert into erp.attendance_hpp_journal_debit_map(
    pool_id,po_id,reclass_journal_line_id,amount
  )
  select v_pool.id,a.po_id,jl.id,round(sum(a.allocation_amount),2)
  from erp.attendance_hpp_pool_allocations a
  join erp.journal_lines jl
    on jl.journal_entry_id=v_journal_id and jl.account_id=v_wip_account
   and jl.po_id=a.po_id
   and jl.description='ATT_HPP|POOL='||v_pool.id::text||'|DEST_PO='||a.po_id::text
  where a.pool_id=v_pool.id
  group by a.po_id,jl.id;

  select count(*) into v_expected from erp.attendance_hpp_pool_sources where pool_id=v_pool.id;
  select count(*) into v_actual from erp.attendance_hpp_journal_credit_map where pool_id=v_pool.id;
  if v_actual<>v_expected then raise exception 'Terminal credit lineage count mismatch expected %, got %',v_expected,v_actual; end if;
  select count(*) into v_expected from (
    select po_id from erp.attendance_hpp_pool_allocations where pool_id=v_pool.id
    group by po_id having round(sum(allocation_amount),2)>0
  ) x;
  select count(*) into v_actual from erp.attendance_hpp_journal_debit_map where pool_id=v_pool.id;
  if v_actual<>v_expected then raise exception 'Destination debit lineage count mismatch expected %, got %',v_expected,v_actual; end if;

  update erp.attendance_hpp_pools
  set status='POSTED',allocation_journal_entry_id=v_journal_id,
      posted_at=clock_timestamp(),posted_by=erp.current_app_user_id(),change_reason=btrim(p_reason)
  where id=v_pool.id;
  return v_journal_id;
end;
$function$;

create or replace function erp.post_attendance_hpp_pool_v1(
  p_pool_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
) returns jsonb
language plpgsql
security definer
set search_path to 'erp','public','auth','extensions','pg_temp'
as $function$
declare
  v_operation constant text := 'post_attendance_hpp_pool_v1';
  v_hash text;v_cached jsonb;v_pool erp.attendance_hpp_pools%rowtype;
  v_journal_id uuid;v_response jsonb;v_previous_setting text;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null or p_expected_version is null then
    raise exception 'reason and expected_version are required';
  end if;
  select period_start,period_end,manifest_digest
  into v_pool.period_start,v_pool.period_end,v_pool.manifest_digest
  from erp.attendance_hpp_pools where id=p_pool_id;
  if v_pool.period_start is null then raise exception 'Attendance HPP pool not found'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'pool_id',p_pool_id,'reason',btrim(p_reason),'expected_version',p_expected_version,
    'manifest_digest',v_pool.manifest_digest
  ));
  v_cached:=erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform pg_advisory_xact_lock(hashtextextended(
    'CP3_ATT_HPP_PERIOD|'||v_pool.period_start::text||'|'||v_pool.period_end::text,0
  ));
  select * into v_pool from erp.attendance_hpp_pools where id=p_pool_id for update;
  if v_pool.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_pool.row_version;
  end if;

  v_previous_setting:=current_setting('app.cp3_attendance_hpp_write',true);
  perform set_config('app.cp3_attendance_hpp_write','on',true);
  v_journal_id:=erp._cp3_post_attendance_hpp_pool(v_pool.id,p_reason);
  perform set_config('app.cp3_attendance_hpp_write',coalesce(v_previous_setting,'off'),true);
  select * into v_pool from erp.attendance_hpp_pools where id=v_pool.id;
  v_response:=jsonb_build_object(
    'pool_id',v_pool.id,'status',v_pool.status,'row_version',v_pool.row_version,
    'journal_entry_id',v_journal_id,'manifest_digest',v_pool.manifest_digest
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

create or replace function erp.cancel_attendance_hpp_pool_v1(
  p_pool_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
) returns jsonb
language plpgsql
security definer
set search_path to 'erp','public','auth','extensions','pg_temp'
as $function$
declare
  v_operation constant text := 'cancel_attendance_hpp_pool_v1';
  v_hash text;v_cached jsonb;v_pool erp.attendance_hpp_pools%rowtype;
  v_response jsonb;v_previous_setting text;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null or p_expected_version is null then
    raise exception 'reason and expected_version are required';
  end if;
  select period_start,period_end,manifest_digest
  into v_pool.period_start,v_pool.period_end,v_pool.manifest_digest
  from erp.attendance_hpp_pools where id=p_pool_id;
  if v_pool.period_start is null then raise exception 'Attendance HPP pool not found'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'pool_id',p_pool_id,'reason',btrim(p_reason),'expected_version',p_expected_version,
    'manifest_digest',v_pool.manifest_digest
  ));
  v_cached:=erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform pg_advisory_xact_lock(hashtextextended(
    'CP3_ATT_HPP_PERIOD|'||v_pool.period_start::text||'|'||v_pool.period_end::text,0
  ));
  select * into v_pool from erp.attendance_hpp_pools where id=p_pool_id for update;
  if v_pool.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_pool.row_version;
  end if;
  if v_pool.status<>'ACTIVE' then raise exception 'Only ACTIVE attendance HPP pool can be cancelled'; end if;
  if v_pool.allocation_journal_entry_id is not null then raise exception 'ACTIVE pool unexpectedly has a journal'; end if;

  v_previous_setting:=current_setting('app.cp3_attendance_hpp_write',true);
  perform set_config('app.cp3_attendance_hpp_write','on',true);
  update erp.attendance_hpp_pools
  set status='CANCELLED',cancelled_at=clock_timestamp(),cancelled_by=erp.current_app_user_id(),
      change_reason=btrim(p_reason)
  where id=v_pool.id returning * into v_pool;
  perform set_config('app.cp3_attendance_hpp_write',coalesce(v_previous_setting,'off'),true);
  v_response:=jsonb_build_object(
    'pool_id',v_pool.id,'status',v_pool.status,'row_version',v_pool.row_version,
    'journal_entry_id',v_pool.allocation_journal_entry_id
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

create or replace function erp._cp3_reverse_attendance_hpp_pool(
  p_pool_id uuid,
  p_reason text,
  p_terminal_status text
) returns uuid
language plpgsql
security definer
set search_path to 'erp','public','pg_temp'
as $function$
declare
  v_pool erp.attendance_hpp_pools%rowtype;
  v_reversal_journal uuid;
begin
  if p_terminal_status not in ('REVERSED','CORRECTED') then raise exception 'Invalid terminal pool status'; end if;
  select * into v_pool from erp.attendance_hpp_pools where id=p_pool_id for update;
  if v_pool.id is null then raise exception 'Attendance HPP pool not found'; end if;
  if v_pool.status<>'POSTED' then raise exception 'Only POSTED attendance HPP pool can be reversed/corrected'; end if;
  if v_pool.allocation_journal_entry_id is null then raise exception 'Posted attendance HPP pool has no journal'; end if;
  v_reversal_journal:=erp.reverse_journal(v_pool.allocation_journal_entry_id,btrim(p_reason));
  update erp.attendance_hpp_pools
  set status=p_terminal_status,reversal_journal_entry_id=v_reversal_journal,
      reversed_at=clock_timestamp(),reversed_by=erp.current_app_user_id(),change_reason=btrim(p_reason)
  where id=v_pool.id;
  return v_reversal_journal;
end;
$function$;

create or replace function erp.reverse_attendance_hpp_pool_v1(
  p_pool_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
) returns jsonb
language plpgsql
security definer
set search_path to 'erp','public','auth','extensions','pg_temp'
as $function$
declare
  v_operation constant text := 'reverse_attendance_hpp_pool_v1';
  v_hash text;v_cached jsonb;v_pool erp.attendance_hpp_pools%rowtype;
  v_reversal_journal uuid;v_response jsonb;v_previous_setting text;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null or p_expected_version is null then
    raise exception 'reason and expected_version are required';
  end if;
  select period_start,period_end,allocation_journal_entry_id
  into v_pool.period_start,v_pool.period_end,v_pool.allocation_journal_entry_id
  from erp.attendance_hpp_pools where id=p_pool_id;
  if v_pool.period_start is null then raise exception 'Attendance HPP pool not found'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'pool_id',p_pool_id,'reason',btrim(p_reason),'expected_version',p_expected_version,
    'journal_entry_id',v_pool.allocation_journal_entry_id
  ));
  v_cached:=erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform pg_advisory_xact_lock(hashtextextended(
    'CP3_ATT_HPP_PERIOD|'||v_pool.period_start::text||'|'||v_pool.period_end::text,0
  ));
  select * into v_pool from erp.attendance_hpp_pools where id=p_pool_id for update;
  if v_pool.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_pool.row_version;
  end if;

  v_previous_setting:=current_setting('app.cp3_attendance_hpp_write',true);
  perform set_config('app.cp3_attendance_hpp_write','on',true);
  v_reversal_journal:=erp._cp3_reverse_attendance_hpp_pool(v_pool.id,p_reason,'REVERSED');
  perform set_config('app.cp3_attendance_hpp_write',coalesce(v_previous_setting,'off'),true);
  select * into v_pool from erp.attendance_hpp_pools where id=v_pool.id;
  v_response:=jsonb_build_object(
    'pool_id',v_pool.id,'status',v_pool.status,'row_version',v_pool.row_version,
    'reversal_journal_entry_id',v_reversal_journal
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

create or replace function erp.correct_attendance_hpp_pool_v1(
  p_source_pool_id uuid,
  p_replacement_pool_number text,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
) returns jsonb
language plpgsql
security definer
set search_path to 'erp','public','auth','extensions','pg_temp'
as $function$
declare
  v_operation constant text := 'correct_attendance_hpp_pool_v1';
  v_hash text;v_cached jsonb;v_source erp.attendance_hpp_pools%rowtype;
  v_replacement erp.attendance_hpp_pools%rowtype;
  v_replacement_id uuid;v_old_reversal uuid;v_new_journal uuid;
  v_response jsonb;v_previous_setting text;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_replacement_pool_number),'') is null
     or nullif(btrim(p_reason),'') is null or p_expected_version is null
  then raise exception 'replacement_pool_number, reason, and expected_version are required'; end if;
  select period_start,period_end,manifest_digest
  into v_source.period_start,v_source.period_end,v_source.manifest_digest
  from erp.attendance_hpp_pools where id=p_source_pool_id;
  if v_source.period_start is null then raise exception 'Source attendance HPP pool not found'; end if;
  v_hash:=erp._request_hash(jsonb_build_object(
    'source_pool_id',p_source_pool_id,'replacement_pool_number',btrim(p_replacement_pool_number),
    'reason',btrim(p_reason),'expected_version',p_expected_version,
    'source_manifest_digest',v_source.manifest_digest
  ));
  v_cached:=erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform pg_advisory_xact_lock(hashtextextended(
    'CP3_ATT_HPP_PERIOD|'||v_source.period_start::text||'|'||v_source.period_end::text,0
  ));
  select * into v_source from erp.attendance_hpp_pools where id=p_source_pool_id for update;
  if v_source.status<>'POSTED' then raise exception 'Only POSTED pool can be corrected'; end if;
  if v_source.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_source.row_version;
  end if;

  v_previous_setting:=current_setting('app.cp3_attendance_hpp_write',true);
  perform set_config('app.cp3_attendance_hpp_write','on',true);
  v_replacement_id:=erp._cp3_create_attendance_hpp_pool(
    p_replacement_pool_number,v_source.period_start,v_source.period_end,p_reason,v_source.id
  );
  v_old_reversal:=erp._cp3_reverse_attendance_hpp_pool(v_source.id,p_reason,'CORRECTED');
  v_new_journal:=erp._cp3_post_attendance_hpp_pool(v_replacement_id,p_reason);
  perform set_config('app.cp3_attendance_hpp_write',coalesce(v_previous_setting,'off'),true);
  select * into v_source from erp.attendance_hpp_pools where id=v_source.id;
  select * into v_replacement from erp.attendance_hpp_pools where id=v_replacement_id;
  v_response:=jsonb_build_object(
    'source_pool_id',v_source.id,'source_status',v_source.status,
    'source_reversal_journal_entry_id',v_old_reversal,
    'replacement_pool_id',v_replacement.id,'replacement_status',v_replacement.status,
    'replacement_row_version',v_replacement.row_version,
    'replacement_journal_entry_id',v_new_journal,
    'replacement_manifest_digest',v_replacement.manifest_digest
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

-- A bounded set-based integrity surface. No deferred row trigger rescans the pool.
create or replace function erp.run_v2614_attendance_hpp_integrity_checks()
returns table(check_name text,severity text,issue_count bigint,details text)
language sql
stable
security definer
set search_path to 'erp','public','pg_temp'
as $function$
  select 'overlapping_contractor_hpp_policy','CRITICAL',count(*)::bigint,
         'Contractor HPP policy ranges must not overlap'
  from erp.contractor_hpp_policy_versions a
  join erp.contractor_hpp_policy_versions b
    on b.contractor_id=a.contractor_id and b.id>a.id
   and a.effective_from<=coalesce(b.effective_to,'infinity'::date)
   and coalesce(a.effective_to,'infinity'::date)>=b.effective_from

  union all
  select 'posted_sewing_over_cut_capacity','CRITICAL',count(*)::bigint,
         'Posted SELESAI_DIJAHIT cannot exceed authoritative effective cut qty'
  from (
    select e.cutting_group_id,sum(e.qty_pcs) qty,coalesce(v.total_pcs,0) capacity
    from erp.sewing_terminal_events e
    left join erp.v_cutting_group_totals v on v.cutting_group_id=e.cutting_group_id
    where e.status='POSTED'
    group by e.cutting_group_id,v.total_pcs
  ) x where x.qty>x.capacity

  union all
  select 'overlapping_active_or_posted_pool_period','CRITICAL',count(*)::bigint,
         'ACTIVE/POSTED global attendance HPP pool ranges must not overlap'
  from erp.attendance_hpp_pools a
  join erp.attendance_hpp_pools b on b.id>a.id
   and a.status in ('ACTIVE','POSTED') and b.status in ('ACTIVE','POSTED')
   and a.period_start<=b.period_end and a.period_end>=b.period_start

  union all
  select 'pool_amount_or_qty_mismatch','CRITICAL',count(*)::bigint,
         'Pool source, denominator, and allocation totals must reconcile exactly'
  from erp.attendance_hpp_pools p
  where p.numerator_amount is distinct from coalesce((select sum(s.attendance_amount) from erp.attendance_hpp_pool_sources s where s.pool_id=p.id),0)
     or p.denominator_qty is distinct from coalesce((select sum(a.qty_pcs) from erp.attendance_hpp_pool_allocations a where a.pool_id=p.id),0)::integer
     or p.allocated_amount is distinct from coalesce((select sum(a.allocation_amount) from erp.attendance_hpp_pool_allocations a where a.pool_id=p.id),0)

  union all
  select 'posted_pool_credit_lineage_mismatch','CRITICAL',count(*)::bigint,
         'Every original payroll LABOR_COST debit line must map to exactly one terminal reclass credit line'
  from erp.attendance_hpp_pools p
  where p.status='POSTED' and (
    (select count(*) from erp.attendance_hpp_pool_sources s where s.pool_id=p.id)
    <>
    (select count(*) from erp.attendance_hpp_journal_credit_map m where m.pool_id=p.id)
  )

  union all
  select 'pool_manifest_digest_mismatch','CRITICAL',count(*)::bigint,
         'Stored canonical manifest/digest must equal the deterministic current snapshot'
  from erp.attendance_hpp_pools p
  where p.manifest is distinct from erp.attendance_hpp_pool_manifest_v1(p.id)
     or p.manifest_digest is distinct from erp.attendance_hpp_pool_digest_v1(p.id)

  union all
  select 'browser_direct_cp3_write_grant','CRITICAL',count(*)::bigint,
         'CP3 foundation tables/functions must remain ungranted until CP4 activation'
  from information_schema.role_table_grants g
  where g.table_schema='erp'
    and g.table_name in (
      'contractor_hpp_policy_versions','sewing_terminal_events','attendance_hpp_pools',
      'attendance_hpp_pool_sources','attendance_hpp_pool_allocations',
      'attendance_hpp_journal_credit_map','attendance_hpp_journal_debit_map'
    )
    and g.grantee in ('anon','authenticated')
    and g.privilege_type in ('INSERT','UPDATE','DELETE');
$function$;

create or replace view erp.v_po_attendance_hpp_allocation_v1
with (security_invoker=true, security_barrier=true)
as
select a.po_id,a.cutting_group_id,p.id as pool_id,p.period_start,p.period_end,
       sum(a.qty_pcs)::bigint as sewing_qty_pcs,
       sum(a.allocation_amount)::numeric(20,2) as attendance_hpp_amount
from erp.attendance_hpp_pool_allocations a
join erp.attendance_hpp_pools p on p.id=a.pool_id
where p.status='POSTED'
group by a.po_id,a.cutting_group_id,p.id,p.period_start,p.period_end;

comment on view erp.v_po_attendance_hpp_allocation_v1 is
  'Private CP3 source for future CP4 HPP rebuild integration. No grants in CP3.';
comment on table erp.sewing_terminal_events is
  'Immutable SELESAI_DIJAHIT facts only. QC GOOD, Laundry return, FG, Susulan, and Rework GOOD are not accepted denominator origins.';
comment on table erp.attendance_hpp_pools is
  'Global normal-Mandor attendance HPP pool, exact-period numerator and immutable SELESAI_DIJAHIT denominator. CP3 foundation is not activated into production HPP hooks.';

-- Explicitly remove PostgreSQL default PUBLIC function EXECUTE and all browser/service grants.
revoke all on table erp.contractor_hpp_policy_versions from public,anon,authenticated,service_role;
revoke all on table erp.sewing_terminal_events from public,anon,authenticated,service_role;
revoke all on table erp.attendance_hpp_pools from public,anon,authenticated,service_role;
revoke all on table erp.attendance_hpp_pool_sources from public,anon,authenticated,service_role;
revoke all on table erp.attendance_hpp_pool_allocations from public,anon,authenticated,service_role;
revoke all on table erp.attendance_hpp_journal_credit_map from public,anon,authenticated,service_role;
revoke all on table erp.attendance_hpp_journal_debit_map from public,anon,authenticated,service_role;
revoke all on table erp.v_po_attendance_hpp_allocation_v1 from public,anon,authenticated,service_role;

revoke all on function erp._cp3_assert_json_object_v1(jsonb,text[],text[],text) from public,anon,authenticated,service_role;
revoke all on function erp._cp3_epoch_us(timestamptz) from public,anon,authenticated,service_role;
revoke all on function erp._cp3_guard_policy_write() from public,anon,authenticated,service_role;
revoke all on function erp._cp3_guard_policy_overlap() from public,anon,authenticated,service_role;
revoke all on function erp.save_contractor_hpp_policy_v1(jsonb,uuid,bigint) from public,anon,authenticated,service_role;
revoke all on function erp._cp3_guard_sewing_terminal_write() from public,anon,authenticated,service_role;
revoke all on function erp._cp3_assert_sewing_capacity(uuid,uuid,integer) from public,anon,authenticated,service_role;
revoke all on function erp.record_sewing_terminal_v1(jsonb,uuid) from public,anon,authenticated,service_role;
revoke all on function erp.correct_sewing_terminal_v1(uuid,jsonb,uuid,bigint) from public,anon,authenticated,service_role;
revoke all on function erp.reverse_sewing_terminal_v1(uuid,text,uuid,bigint) from public,anon,authenticated,service_role;
revoke all on function erp._cp3_guard_attendance_hpp_write() from public,anon,authenticated,service_role;
revoke all on function erp.attendance_hpp_pool_manifest_v1(uuid) from public,anon,authenticated,service_role;
revoke all on function erp.attendance_hpp_pool_digest_v1(uuid) from public,anon,authenticated,service_role;
revoke all on function erp.validate_attendance_hpp_pool_v1(uuid) from public,anon,authenticated,service_role;
revoke all on function erp.preview_attendance_hpp_pool_v1(date,date) from public,anon,authenticated,service_role;
revoke all on function erp._cp3_create_attendance_hpp_pool(text,date,date,text,uuid) from public,anon,authenticated,service_role;
revoke all on function erp.create_attendance_hpp_pool_v1(jsonb,uuid) from public,anon,authenticated,service_role;
revoke all on function erp._cp3_post_attendance_hpp_pool(uuid,text) from public,anon,authenticated,service_role;
revoke all on function erp.post_attendance_hpp_pool_v1(uuid,text,uuid,bigint) from public,anon,authenticated,service_role;
revoke all on function erp.cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint) from public,anon,authenticated,service_role;
revoke all on function erp._cp3_reverse_attendance_hpp_pool(uuid,text,text) from public,anon,authenticated,service_role;
revoke all on function erp.reverse_attendance_hpp_pool_v1(uuid,text,uuid,bigint) from public,anon,authenticated,service_role;
revoke all on function erp.correct_attendance_hpp_pool_v1(uuid,text,text,uuid,bigint) from public,anon,authenticated,service_role;
revoke all on function erp.run_v2614_attendance_hpp_integrity_checks() from public,anon,authenticated,service_role;

insert into erp.schema_migrations(version,description,installed_at)
values(
  'v2.6.14',
  'CP3 source-only attendance HPP foundation: explicit Special policy, immutable SELESAI_DIJAHIT denominator, deterministic manifest, source-debit journal lineage, active-pool cancel, correction/reversal, bounded validators; no hooks/grants',
  clock_timestamp()
);

commit;
