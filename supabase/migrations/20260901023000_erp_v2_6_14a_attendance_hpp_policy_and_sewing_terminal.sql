-- ERP Garment v2.6.14a — CP3 SOURCE CANDIDATE
-- Explicit normal-Mandor policy + immutable SELESAI_DIJAHIT source ledger.
--
-- SOURCE/UAT/LIVE boundary:
--   * source-only candidate; not applied to ERP Enteng UAT;
--   * no public facade, authenticated grant, hook, scheduler, or Cloudflare change;
--   * ERP-Garment legacy/canonical remains read-only;
--   * QC GOOD, FG, Laundry, Rework, Rewash, and Susulan are forbidden as
--     attendance-HPP denominator sources.

begin;
set local lock_timeout = '10s';
set local statement_timeout = '120s';

do $guard$
begin
  if to_regclass('erp.contractors') is null
     or to_regclass('erp.production_orders') is null
     or to_regclass('erp.work_completion_lines') is null
     or to_regclass('erp.work_components') is null
     or to_regclass('erp.app_users') is null then
    raise exception 'v2.6.14a requires the verified ERP Enteng v2.6.13 baseline';
  end if;
  if to_regclass('erp.contractor_hpp_policy_versions') is not null
     or to_regclass('erp.attendance_hpp_sewing_events') is not null then
    raise exception 'v2.6.14a objects already exist; do not replay or overwrite';
  end if;
end;
$guard$;

-- ---------------------------------------------------------------------------
-- Strict JSON contract. Missing keys, explicit NULL, wrong type, and extra
-- closed-contract keys are different states and are checked explicitly.
-- ---------------------------------------------------------------------------

create or replace function erp.cp3_assert_json_object_v1(
  p_value jsonb,
  p_required_keys text[],
  p_allowed_keys text[],
  p_expected_types jsonb default '{}'::jsonb
)
returns void
language plpgsql
immutable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_missing text[];
  v_extra text[];
  v_key text;
  v_expected text;
  v_actual text;
begin
  if jsonb_typeof(p_value) is distinct from 'object' then
    raise exception 'JSON contract requires an object';
  end if;

  select array_agg(k order by k)
  into v_missing
  from unnest(coalesce(p_required_keys, array[]::text[])) as required(k)
  where not (p_value ? k);

  if coalesce(cardinality(v_missing), 0) > 0 then
    raise exception 'JSON contract missing required keys: %', array_to_string(v_missing, ',');
  end if;

  select array_agg(k order by k)
  into v_extra
  from jsonb_object_keys(p_value) as supplied(k)
  where not (k = any(coalesce(p_allowed_keys, array[]::text[])));

  if coalesce(cardinality(v_extra), 0) > 0 then
    raise exception 'JSON contract contains unexpected keys: %', array_to_string(v_extra, ',');
  end if;

  for v_key, v_expected in
    select key, value
    from jsonb_each_text(coalesce(p_expected_types, '{}'::jsonb))
  loop
    if p_value ? v_key then
      v_actual := jsonb_typeof(p_value -> v_key);
      if not (v_actual = any(string_to_array(v_expected, '|'))) then
        raise exception 'JSON key % expected type %, observed %', v_key, v_expected, v_actual;
      end if;
    end if;
  end loop;
end;
$function$;

create or replace function erp.cp3_assert_typed_operation_manifest_v1(
  p_manifest jsonb,
  p_expected_operation_type text
)
returns void
language plpgsql
immutable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_item jsonb;
  v_action text;
  v_expected text := upper(coalesce(nullif(btrim(p_expected_operation_type), ''), ''));
begin
  perform erp.cp3_assert_json_object_v1(
    p_manifest,
    array['operation_type','operations','version'],
    array['operation_type','operations','version','period_start_epoch_us','period_end_epoch_us'],
    jsonb_build_object('operation_type','string','operations','array','version','string')
  );

  if upper(p_manifest ->> 'operation_type') is distinct from v_expected then
    raise exception 'Manifest operation_type mismatch: expected %, observed %',
      v_expected, p_manifest ->> 'operation_type';
  end if;

  for v_item in select value from jsonb_array_elements(p_manifest -> 'operations')
  loop
    perform erp.cp3_assert_json_object_v1(
      v_item,
      array['operation_type','action'],
      array[
        'operation_type','action','source_line_id','original_journal_line_id',
        'production_order_id','account_id','amount_cents','quantity_basis',
        'pool_id','reason'
      ],
      jsonb_build_object('operation_type','string','action','string')
    );

    if upper(v_item ->> 'operation_type') is distinct from v_expected then
      raise exception 'Mixed operation injection rejected: expected %, observed %',
        v_expected, v_item ->> 'operation_type';
    end if;

    v_action := upper(v_item ->> 'action');
    if v_expected = 'LAUNDRY_CLAIM' then
      if v_action not in ('LAUNDRY_CLAIM_SETTLEMENT','LAUNDRY_CLAIM_REVERSAL') then
        raise exception 'LAUNDRY_CLAIM manifest cannot carry action %', v_action;
      end if;
    elsif v_expected = 'ATTENDANCE_HPP_POOL' then
      if v_action not in (
        'PREPARE','ALLOCATE','DESTINATION_DEBIT','TERMINAL_CREDIT',
        'READY','CANCEL','REVERSE'
      ) then
        raise exception 'ATTENDANCE_HPP_POOL manifest cannot carry action %', v_action;
      end if;
    else
      raise exception 'Unsupported operation_type %', v_expected;
    end if;
  end loop;
end;
$function$;

-- ---------------------------------------------------------------------------
-- Effective-dated contractor HPP policy.
-- Eligibility is three explicit facts: MANDOR + attendance_required + NOT Special.
-- ---------------------------------------------------------------------------

create table erp.contractor_hpp_policy_versions (
  id uuid primary key default gen_random_uuid(),
  contractor_id uuid not null references erp.contractors(id),
  contractor_role varchar(20) not null check (contractor_role = 'MANDOR'),
  attendance_required boolean not null,
  is_special boolean not null,
  effective_from date not null,
  effective_to date,
  reason text not null check (btrim(reason) <> ''),
  created_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  row_version bigint not null default 1 check (row_version > 0),
  constraint contractor_hpp_policy_dates_check
    check (effective_to is null or effective_to >= effective_from),
  constraint contractor_hpp_policy_unique_start
    unique (contractor_id, effective_from)
);

create index idx_contractor_hpp_policy_lookup
  on erp.contractor_hpp_policy_versions(contractor_id, effective_from desc);

create or replace function erp.guard_contractor_hpp_policy_version_v1()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
declare
  v_contractor_id uuid := case when tg_op = 'DELETE' then old.contractor_id else new.contractor_id end;
begin
  if current_setting('app.contractor_hpp_policy_write', true) is distinct from 'on' then
    raise exception 'Contractor HPP policy history is write-protected; use set_contractor_hpp_policy_v1';
  end if;
  if tg_op = 'DELETE' then
    raise exception 'Contractor HPP policy history cannot be deleted';
  end if;

  if tg_op = 'UPDATE'
     and (new.contractor_id, new.contractor_role, new.attendance_required,
          new.is_special, new.effective_from, new.reason,
          new.created_by, new.created_at)
         is distinct from
         (old.contractor_id, old.contractor_role, old.attendance_required,
          old.is_special, old.effective_from, old.reason,
          old.created_by, old.created_at) then
    raise exception 'Existing contractor HPP policy facts are immutable; only effective_to may close';
  end if;

  perform pg_advisory_xact_lock(hashtextextended('CONTRACTOR_HPP_POLICY|' || v_contractor_id::text, 0));
  if exists (
    select 1
    from erp.contractor_hpp_policy_versions p
    where p.contractor_id = v_contractor_id
      and p.id <> new.id
      and daterange(p.effective_from, coalesce(p.effective_to + 1, 'infinity'::date), '[)')
          && daterange(new.effective_from, coalesce(new.effective_to + 1, 'infinity'::date), '[)')
  ) then
    raise exception 'Contractor HPP policy periods cannot overlap';
  end if;
  return new;
end;
$function$;

create trigger trg_guard_contractor_hpp_policy_version_v1
before insert or update or delete on erp.contractor_hpp_policy_versions
for each row execute function erp.guard_contractor_hpp_policy_version_v1();

create trigger trg_audit_contractor_hpp_policy_versions
after insert or update or delete on erp.contractor_hpp_policy_versions
for each row execute function erp.audit_row_change();

create or replace function erp.set_contractor_hpp_policy_v1(
  p_payload jsonb,
  p_client_request_id uuid
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
  v_role text;
  v_attendance_required boolean;
  v_is_special boolean;
  v_effective_from date;
  v_reason text;
  v_expected_policy_id uuid;
  v_current erp.contractor_hpp_policy_versions%rowtype;
  v_next_from date;
  v_new erp.contractor_hpp_policy_versions%rowtype;
  v_contractor jsonb;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  perform erp.cp3_assert_json_object_v1(
    p_payload,
    array['contractor_id','contractor_role','attendance_required','is_special','effective_from','reason'],
    array['contractor_id','contractor_role','attendance_required','is_special','effective_from','reason','expected_policy_id'],
    jsonb_build_object(
      'contractor_id','string','contractor_role','string',
      'attendance_required','boolean','is_special','boolean',
      'effective_from','string','reason','string','expected_policy_id','string|null'
    )
  );

  v_contractor_id := (p_payload ->> 'contractor_id')::uuid;
  v_role := upper(p_payload ->> 'contractor_role');
  v_attendance_required := (p_payload ->> 'attendance_required')::boolean;
  v_is_special := (p_payload ->> 'is_special')::boolean;
  v_effective_from := (p_payload ->> 'effective_from')::date;
  v_reason := nullif(btrim(p_payload ->> 'reason'), '');
  v_expected_policy_id := nullif(p_payload ->> 'expected_policy_id', '')::uuid;

  if v_role <> 'MANDOR' then raise exception 'HPP attendance policy role must be MANDOR'; end if;
  if v_reason is null then raise exception 'Policy reason is required'; end if;

  select to_jsonb(c) into v_contractor
  from erp.contractors c
  where c.id = v_contractor_id;
  if v_contractor is null then raise exception 'Contractor not found'; end if;
  if upper(coalesce(v_contractor ->> 'contractor_type', '')) <> 'MANDOR' then
    raise exception 'Contractor must have authoritative contractor_type MANDOR';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'contract_version', 'ATTENDANCE_HPP_POLICY_V1'
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  perform pg_advisory_xact_lock(hashtextextended('CONTRACTOR_HPP_POLICY|' || v_contractor_id::text, 0));
  select * into v_current
  from erp.contractor_hpp_policy_versions p
  where p.contractor_id = v_contractor_id
    and v_effective_from >= p.effective_from
    and (p.effective_to is null or v_effective_from <= p.effective_to)
  order by p.effective_from desc, p.id desc
  limit 1
  for update;

  if v_current.id is distinct from v_expected_policy_id then
    raise exception 'STALE_POLICY expected %, current %', v_expected_policy_id, v_current.id;
  end if;
  if v_current.effective_from = v_effective_from then
    raise exception 'A contractor HPP policy already starts on this date';
  end if;

  select min(p.effective_from) into v_next_from
  from erp.contractor_hpp_policy_versions p
  where p.contractor_id = v_contractor_id
    and p.effective_from > v_effective_from;

  perform set_config('app.change_reason', v_reason, true);
  perform set_config('app.contractor_hpp_policy_write', 'on', true);

  update erp.contractor_hpp_policy_versions p
  set effective_to = v_effective_from - 1,
      row_version = row_version + 1
  where p.contractor_id = v_contractor_id
    and p.effective_from < v_effective_from
    and (p.effective_to is null or p.effective_to >= v_effective_from);

  insert into erp.contractor_hpp_policy_versions(
    contractor_id, contractor_role, attendance_required, is_special,
    effective_from, effective_to, reason, created_by
  ) values (
    v_contractor_id, v_role, v_attendance_required, v_is_special,
    v_effective_from,
    case when v_next_from is null then null else v_next_from - 1 end,
    v_reason, erp.current_app_user_id()
  ) returning * into v_new;

  v_response := jsonb_build_object(
    'policy_version_id', v_new.id,
    'contractor_id', v_new.contractor_id,
    'contractor_role', v_new.contractor_role,
    'attendance_required', v_new.attendance_required,
    'is_special', v_new.is_special,
    'eligible_for_attendance_hpp',
      (v_new.contractor_role = 'MANDOR' and v_new.attendance_required and not v_new.is_special),
    'effective_from', v_new.effective_from,
    'effective_to', v_new.effective_to,
    'row_version', v_new.row_version
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.require_eligible_contractor_hpp_policy_v1(
  p_contractor_id uuid,
  p_effective_date date
)
returns erp.contractor_hpp_policy_versions
language plpgsql
stable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_policy erp.contractor_hpp_policy_versions%rowtype;
begin
  select * into v_policy
  from erp.contractor_hpp_policy_versions p
  where p.contractor_id = p_contractor_id
    and p_effective_date >= p.effective_from
    and (p.effective_to is null or p_effective_date <= p.effective_to)
  order by p.effective_from desc, p.id desc
  limit 1;

  if v_policy.id is null then
    raise exception 'No explicit HPP policy covers contractor % on %', p_contractor_id, p_effective_date;
  end if;
  if v_policy.contractor_role <> 'MANDOR'
     or not v_policy.attendance_required
     or v_policy.is_special then
    raise exception 'Contractor % is not eligible for attendance HPP on %', p_contractor_id, p_effective_date;
  end if;
  return v_policy;
end;
$function$;

-- ---------------------------------------------------------------------------
-- Immutable SELESAI_DIJAHIT ledger.
-- effective_date is explicit and controls period membership. effective_at is
-- provenance only; epoch serialization is independent of session TimeZone.
-- ---------------------------------------------------------------------------

create table erp.attendance_hpp_sewing_events (
  id uuid primary key default gen_random_uuid(),
  event_key uuid not null unique,
  event_action varchar(20) not null check (event_action in ('RECORD','REVERSAL','CORRECTION')),
  event_type varchar(30) not null check (event_type = 'SELESAI_DIJAHIT'),
  business_source_kind varchar(30) not null check (business_source_kind = 'SEWING_TERMINAL'),
  production_order_id uuid not null references erp.production_orders(id),
  contractor_id uuid not null references erp.contractors(id),
  source_work_completion_line_id uuid not null references erp.work_completion_lines(id),
  effective_date date not null,
  effective_at timestamptz not null,
  quantity_signed numeric(24,6) not null check (quantity_signed <> 0),
  policy_version_id uuid not null references erp.contractor_hpp_policy_versions(id),
  reversal_of_event_id uuid references erp.attendance_hpp_sewing_events(id),
  correction_of_event_id uuid references erp.attendance_hpp_sewing_events(id),
  source_payload_hash text not null,
  reason text not null check (btrim(reason) <> ''),
  created_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  constraint attendance_hpp_sewing_action_shape check (
    (event_action = 'RECORD' and quantity_signed > 0
      and reversal_of_event_id is null and correction_of_event_id is null)
    or
    (event_action = 'REVERSAL' and quantity_signed < 0
      and reversal_of_event_id is not null and correction_of_event_id is null)
    or
    (event_action = 'CORRECTION' and quantity_signed > 0
      and reversal_of_event_id is null and correction_of_event_id is not null)
  )
);

create unique index uq_attendance_hpp_single_reversal
  on erp.attendance_hpp_sewing_events(reversal_of_event_id)
  where reversal_of_event_id is not null;
create unique index uq_attendance_hpp_single_correction
  on erp.attendance_hpp_sewing_events(correction_of_event_id)
  where correction_of_event_id is not null;
create index idx_attendance_hpp_sewing_period
  on erp.attendance_hpp_sewing_events(effective_date, contractor_id, production_order_id);
create index idx_attendance_hpp_sewing_source
  on erp.attendance_hpp_sewing_events(source_work_completion_line_id, created_at);

create or replace function erp.guard_attendance_hpp_sewing_event_v1()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
begin
  if current_setting('app.attendance_hpp_sewing_write', true) is distinct from 'on' then
    raise exception 'Sewing-terminal events are append-only; use authoritative record/correct/reverse RPCs';
  end if;
  if tg_op <> 'INSERT' then
    raise exception 'Sewing-terminal facts cannot be updated or deleted';
  end if;
  return new;
end;
$function$;

create trigger trg_guard_attendance_hpp_sewing_event_v1
before insert or update or delete on erp.attendance_hpp_sewing_events
for each row execute function erp.guard_attendance_hpp_sewing_event_v1();
create trigger trg_audit_attendance_hpp_sewing_events
after insert or update or delete on erp.attendance_hpp_sewing_events
for each row execute function erp.audit_row_change();

create or replace view erp.v_attendance_hpp_active_sewing_events_v1
with (security_invoker = true)
as
select e.*
from erp.attendance_hpp_sewing_events e
where e.event_action in ('RECORD','CORRECTION')
  and not exists (
    select 1
    from erp.attendance_hpp_sewing_events r
    where r.reversal_of_event_id = e.id
  );

create or replace function erp.cp3_validate_sewing_source_v1(
  p_source_work_completion_line_id uuid,
  p_production_order_id uuid,
  p_contractor_id uuid,
  p_quantity numeric
)
returns jsonb
language plpgsql
stable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_source jsonb;
  v_component jsonb;
  v_source_type text;
  v_component_label text;
  v_component_id uuid;
  v_po uuid;
  v_contractor uuid;
  v_max_qty numeric;
begin
  select to_jsonb(w) into v_source
  from erp.work_completion_lines w
  where w.id = p_source_work_completion_line_id;
  if v_source is null then raise exception 'Work completion line not found'; end if;

  v_source_type := upper(coalesce(
    nullif(v_source ->> 'source_type', ''),
    nullif(v_source ->> 'completion_type', ''),
    nullif(v_source ->> 'work_type', ''),
    ''
  ));
  if v_source_type ~ '(QC|FG|LAUNDRY|REWORK|REWASH|SUSULAN|RETURN)' then
    raise exception 'Source type % is downstream, not SELESAI_DIJAHIT', v_source_type;
  end if;

  v_component_id := nullif(v_source ->> 'work_component_id', '')::uuid;
  if v_component_id is not null then
    select to_jsonb(c) into v_component
    from erp.work_components c
    where c.id = v_component_id;
  end if;
  v_component_label := upper(concat_ws('|',
    v_source_type,
    v_component ->> 'component_code',
    v_component ->> 'component_name',
    v_component ->> 'component_type',
    v_component ->> 'process_code'
  ));
  if v_component_label !~ '(SEW|JAHIT)' then
    raise exception 'Work completion source is not explicitly a sewing/Jahit component';
  end if;

  v_po := nullif(coalesce(v_source ->> 'po_id', v_source ->> 'production_order_id'), '')::uuid;
  if v_po is not null and v_po <> p_production_order_id then
    raise exception 'Work completion source belongs to a different production order';
  end if;
  v_contractor := nullif(coalesce(v_source ->> 'contractor_id', v_source ->> 'mandor_id'), '')::uuid;
  if v_contractor is not null and v_contractor <> p_contractor_id then
    raise exception 'Work completion source belongs to a different contractor';
  end if;

  v_max_qty := coalesce(
    nullif(v_source ->> 'qty_completed', '')::numeric,
    nullif(v_source ->> 'completed_qty', '')::numeric,
    nullif(v_source ->> 'quantity', '')::numeric,
    nullif(v_source ->> 'qty', '')::numeric
  );
  if v_max_qty is not null and p_quantity > v_max_qty then
    raise exception 'SELESAI_DIJAHIT quantity exceeds authoritative completion-line quantity';
  end if;
  return v_source;
end;
$function$;

create or replace function erp.record_sewing_terminal_event_v1(
  p_payload jsonb,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'record_sewing_terminal_event_v1';
  v_hash text;
  v_cached jsonb;
  v_po_id uuid;
  v_contractor_id uuid;
  v_source_line_id uuid;
  v_effective_date date;
  v_effective_at timestamptz;
  v_qty numeric;
  v_reason text;
  v_policy erp.contractor_hpp_policy_versions%rowtype;
  v_event erp.attendance_hpp_sewing_events%rowtype;
  v_response jsonb;
begin
  perform erp.require_internal();
  perform erp.cp3_assert_json_object_v1(
    p_payload,
    array[
      'event_type','business_source_kind','production_order_id','contractor_id',
      'source_work_completion_line_id','effective_date','effective_at','quantity','reason'
    ],
    array[
      'event_type','business_source_kind','production_order_id','contractor_id',
      'source_work_completion_line_id','effective_date','effective_at','quantity','reason'
    ],
    jsonb_build_object(
      'event_type','string','business_source_kind','string',
      'production_order_id','string','contractor_id','string',
      'source_work_completion_line_id','string','effective_date','string',
      'effective_at','string','quantity','number','reason','string'
    )
  );

  if upper(p_payload ->> 'event_type') <> 'SELESAI_DIJAHIT'
     or upper(p_payload ->> 'business_source_kind') <> 'SEWING_TERMINAL' then
    raise exception 'Only explicit SELESAI_DIJAHIT / SEWING_TERMINAL events are accepted';
  end if;

  v_po_id := (p_payload ->> 'production_order_id')::uuid;
  v_contractor_id := (p_payload ->> 'contractor_id')::uuid;
  v_source_line_id := (p_payload ->> 'source_work_completion_line_id')::uuid;
  v_effective_date := (p_payload ->> 'effective_date')::date;
  v_effective_at := (p_payload ->> 'effective_at')::timestamptz;
  v_qty := (p_payload ->> 'quantity')::numeric;
  v_reason := nullif(btrim(p_payload ->> 'reason'), '');

  if v_qty <= 0 then raise exception 'SELESAI_DIJAHIT quantity must be positive'; end if;
  if v_reason is null then raise exception 'Sewing-terminal reason is required'; end if;
  if not exists (select 1 from erp.production_orders p where p.id = v_po_id) then
    raise exception 'Production order not found';
  end if;

  perform erp.cp3_validate_sewing_source_v1(v_source_line_id, v_po_id, v_contractor_id, v_qty);
  v_policy := erp.require_eligible_contractor_hpp_policy_v1(v_contractor_id, v_effective_date);

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'effective_at_epoch_us', floor(extract(epoch from v_effective_at) * 1000000)::bigint,
    'contract_version', 'SELESAI_DIJAHIT_V1'
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  perform pg_advisory_xact_lock(hashtextextended('SEWING_TERMINAL|' || v_source_line_id::text, 0));
  if exists (
    select 1
    from erp.v_attendance_hpp_active_sewing_events_v1 e
    where e.source_work_completion_line_id = v_source_line_id
  ) then
    raise exception 'An active SELESAI_DIJAHIT event already exists for this source line';
  end if;

  perform set_config('app.change_reason', v_reason, true);
  perform set_config('app.attendance_hpp_sewing_write', 'on', true);
  insert into erp.attendance_hpp_sewing_events(
    event_key, event_action, event_type, business_source_kind,
    production_order_id, contractor_id, source_work_completion_line_id,
    effective_date, effective_at, quantity_signed, policy_version_id,
    source_payload_hash, reason, created_by
  ) values (
    p_client_request_id, 'RECORD', 'SELESAI_DIJAHIT', 'SEWING_TERMINAL',
    v_po_id, v_contractor_id, v_source_line_id,
    v_effective_date, v_effective_at, v_qty, v_policy.id,
    v_hash, v_reason, erp.current_app_user_id()
  ) returning * into v_event;

  v_response := jsonb_build_object(
    'event_id', v_event.id,
    'event_action', v_event.event_action,
    'event_type', v_event.event_type,
    'production_order_id', v_event.production_order_id,
    'contractor_id', v_event.contractor_id,
    'effective_date', v_event.effective_date,
    'effective_at_epoch_us', floor(extract(epoch from v_event.effective_at) * 1000000)::bigint,
    'quantity', v_event.quantity_signed,
    'policy_version_id', v_event.policy_version_id,
    'is_active', true
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.reverse_sewing_terminal_event_v1(
  p_event_id uuid,
  p_reason text,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'reverse_sewing_terminal_event_v1';
  v_hash text;
  v_cached jsonb;
  v_source erp.attendance_hpp_sewing_events%rowtype;
  v_reversal erp.attendance_hpp_sewing_events%rowtype;
  v_response jsonb;
begin
  perform erp.require_internal();
  if p_event_id is null or coalesce(btrim(p_reason), '') = '' then
    raise exception 'event_id and reversal reason are required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'event_id', p_event_id, 'reason', p_reason, 'contract_version', 'SELESAI_DIJAHIT_V1'
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_source
  from erp.attendance_hpp_sewing_events e
  where e.id = p_event_id and e.event_action in ('RECORD','CORRECTION')
  for update;
  if v_source.id is null then raise exception 'Active sewing event source not found'; end if;
  if exists (select 1 from erp.attendance_hpp_sewing_events r where r.reversal_of_event_id = v_source.id) then
    raise exception 'Sewing event has already been reversed';
  end if;

  perform pg_advisory_xact_lock(hashtextextended('SEWING_TERMINAL|' || v_source.source_work_completion_line_id::text, 0));
  perform set_config('app.change_reason', p_reason, true);
  perform set_config('app.attendance_hpp_sewing_write', 'on', true);
  insert into erp.attendance_hpp_sewing_events(
    event_key, event_action, event_type, business_source_kind,
    production_order_id, contractor_id, source_work_completion_line_id,
    effective_date, effective_at, quantity_signed, policy_version_id,
    reversal_of_event_id, source_payload_hash, reason, created_by
  ) values (
    p_client_request_id, 'REVERSAL', 'SELESAI_DIJAHIT', 'SEWING_TERMINAL',
    v_source.production_order_id, v_source.contractor_id, v_source.source_work_completion_line_id,
    v_source.effective_date, v_source.effective_at, -v_source.quantity_signed, v_source.policy_version_id,
    v_source.id, v_hash, p_reason, erp.current_app_user_id()
  ) returning * into v_reversal;

  v_response := jsonb_build_object(
    'source_event_id', v_source.id,
    'reversal_event_id', v_reversal.id,
    'quantity_signed', v_reversal.quantity_signed,
    'effective_date', v_reversal.effective_date,
    'effective_at_epoch_us', floor(extract(epoch from v_reversal.effective_at) * 1000000)::bigint,
    'is_active', false
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

create or replace function erp.correct_sewing_terminal_event_v1(
  p_event_id uuid,
  p_new_effective_date date,
  p_new_effective_at timestamptz,
  p_new_quantity numeric,
  p_reason text,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'correct_sewing_terminal_event_v1';
  v_hash text;
  v_cached jsonb;
  v_source erp.attendance_hpp_sewing_events%rowtype;
  v_policy erp.contractor_hpp_policy_versions%rowtype;
  v_reverse_id uuid;
  v_corrected erp.attendance_hpp_sewing_events%rowtype;
  v_response jsonb;
begin
  perform erp.require_internal();
  if p_event_id is null or p_new_effective_date is null or p_new_effective_at is null
     or p_new_quantity <= 0 or coalesce(btrim(p_reason), '') = '' then
    raise exception 'event_id, positive new quantity, effective date/time, and reason are required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'event_id', p_event_id,
    'new_effective_date', p_new_effective_date,
    'new_effective_at_epoch_us', floor(extract(epoch from p_new_effective_at) * 1000000)::bigint,
    'new_quantity', p_new_quantity,
    'reason', p_reason,
    'contract_version', 'SELESAI_DIJAHIT_V1'
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_source
  from erp.attendance_hpp_sewing_events e
  where e.id = p_event_id and e.event_action in ('RECORD','CORRECTION')
  for update;
  if v_source.id is null then raise exception 'Active sewing event source not found'; end if;
  if exists (select 1 from erp.attendance_hpp_sewing_events r where r.reversal_of_event_id = v_source.id) then
    raise exception 'Sewing event is no longer active';
  end if;

  perform erp.cp3_validate_sewing_source_v1(
    v_source.source_work_completion_line_id,
    v_source.production_order_id,
    v_source.contractor_id,
    p_new_quantity
  );
  v_policy := erp.require_eligible_contractor_hpp_policy_v1(v_source.contractor_id, p_new_effective_date);

  perform pg_advisory_xact_lock(hashtextextended('SEWING_TERMINAL|' || v_source.source_work_completion_line_id::text, 0));
  perform set_config('app.change_reason', p_reason, true);
  perform set_config('app.attendance_hpp_sewing_write', 'on', true);

  insert into erp.attendance_hpp_sewing_events(
    event_key, event_action, event_type, business_source_kind,
    production_order_id, contractor_id, source_work_completion_line_id,
    effective_date, effective_at, quantity_signed, policy_version_id,
    reversal_of_event_id, source_payload_hash, reason, created_by
  ) values (
    gen_random_uuid(), 'REVERSAL', 'SELESAI_DIJAHIT', 'SEWING_TERMINAL',
    v_source.production_order_id, v_source.contractor_id, v_source.source_work_completion_line_id,
    v_source.effective_date, v_source.effective_at, -v_source.quantity_signed, v_source.policy_version_id,
    v_source.id, v_hash, 'Correction reversal: ' || p_reason, erp.current_app_user_id()
  ) returning id into v_reverse_id;

  insert into erp.attendance_hpp_sewing_events(
    event_key, event_action, event_type, business_source_kind,
    production_order_id, contractor_id, source_work_completion_line_id,
    effective_date, effective_at, quantity_signed, policy_version_id,
    correction_of_event_id, source_payload_hash, reason, created_by
  ) values (
    p_client_request_id, 'CORRECTION', 'SELESAI_DIJAHIT', 'SEWING_TERMINAL',
    v_source.production_order_id, v_source.contractor_id, v_source.source_work_completion_line_id,
    p_new_effective_date, p_new_effective_at, p_new_quantity, v_policy.id,
    v_source.id, v_hash, p_reason, erp.current_app_user_id()
  ) returning * into v_corrected;

  v_response := jsonb_build_object(
    'source_event_id', v_source.id,
    'reversal_event_id', v_reverse_id,
    'corrected_event_id', v_corrected.id,
    'effective_date', v_corrected.effective_date,
    'effective_at_epoch_us', floor(extract(epoch from v_corrected.effective_at) * 1000000)::bigint,
    'quantity', v_corrected.quantity_signed,
    'policy_version_id', v_corrected.policy_version_id,
    'is_active', true
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

-- Private surface. CP4 may add reviewed public facades only after CP3 PASS.
alter table erp.contractor_hpp_policy_versions enable row level security;
alter table erp.attendance_hpp_sewing_events enable row level security;

revoke all on table
  erp.contractor_hpp_policy_versions,
  erp.attendance_hpp_sewing_events,
  erp.v_attendance_hpp_active_sewing_events_v1
from public, anon, authenticated;
grant all on table erp.contractor_hpp_policy_versions, erp.attendance_hpp_sewing_events to service_role;
grant select on erp.v_attendance_hpp_active_sewing_events_v1 to service_role;

revoke execute on function erp.cp3_assert_json_object_v1(jsonb,text[],text[],jsonb) from public,anon,authenticated;
revoke execute on function erp.cp3_assert_typed_operation_manifest_v1(jsonb,text) from public,anon,authenticated;
revoke execute on function erp.set_contractor_hpp_policy_v1(jsonb,uuid) from public,anon,authenticated;
revoke execute on function erp.require_eligible_contractor_hpp_policy_v1(uuid,date) from public,anon,authenticated;
revoke execute on function erp.cp3_validate_sewing_source_v1(uuid,uuid,uuid,numeric) from public,anon,authenticated;
revoke execute on function erp.record_sewing_terminal_event_v1(jsonb,uuid) from public,anon,authenticated;
revoke execute on function erp.reverse_sewing_terminal_event_v1(uuid,text,uuid) from public,anon,authenticated;
revoke execute on function erp.correct_sewing_terminal_event_v1(uuid,date,timestamptz,numeric,text,uuid) from public,anon,authenticated;

grant execute on function erp.cp3_assert_json_object_v1(jsonb,text[],text[],jsonb) to service_role;
grant execute on function erp.cp3_assert_typed_operation_manifest_v1(jsonb,text) to service_role;
grant execute on function erp.set_contractor_hpp_policy_v1(jsonb,uuid) to service_role;
grant execute on function erp.require_eligible_contractor_hpp_policy_v1(uuid,date) to service_role;
grant execute on function erp.cp3_validate_sewing_source_v1(uuid,uuid,uuid,numeric) to service_role;
grant execute on function erp.record_sewing_terminal_event_v1(jsonb,uuid) to service_role;
grant execute on function erp.reverse_sewing_terminal_event_v1(uuid,text,uuid) to service_role;
grant execute on function erp.correct_sewing_terminal_event_v1(uuid,date,timestamptz,numeric,text,uuid) to service_role;

comment on table erp.contractor_hpp_policy_versions is
  'Explicit effective-dated attendance-HPP eligibility. Special is independent from attendance_required and never inferred from a name.';
comment on table erp.attendance_hpp_sewing_events is
  'Append-only authoritative SELESAI_DIJAHIT ledger. QC GOOD, FG, Laundry, Rework, Rewash, and Susulan are invalid denominator sources.';

notify pgrst, 'reload schema';
commit;
