-- ERP Garment v2.6.14b — CP3 SOURCE CANDIDATE
-- Deterministic attendance-HPP pool, exact original debit-line lineage,
-- set-based allocation, active-pool cancellation, and journal intents.
--
-- This migration deliberately does NOT call erp.post_journal(). READY means
-- reviewed intent, not posted GL, not enabled route, and not production GO.

begin;
set local lock_timeout = '10s';
set local statement_timeout = '120s';

do $guard$
begin
  if to_regclass('erp.contractor_hpp_policy_versions') is null
     or to_regclass('erp.attendance_hpp_sewing_events') is null
     or to_regclass('erp.payroll_settlements') is null
     or to_regclass('erp.payroll_attendance_items') is null
     or to_regclass('erp.journal_entries') is null
     or to_regclass('erp.journal_lines') is null
     or to_regclass('erp.accounting_account_mappings') is null then
    raise exception 'v2.6.14b requires v2.6.14a and the verified baseline';
  end if;
  if to_regclass('erp.attendance_hpp_pools') is not null then
    raise exception 'v2.6.14b pool objects already exist; do not replay or overwrite';
  end if;
end;
$guard$;

create table erp.attendance_hpp_pools (
  id uuid primary key default gen_random_uuid(),
  pool_number varchar(90) not null unique,
  period_start date not null,
  period_end date not null,
  status varchar(20) not null
    check (status in ('UNASSIGNED','ACTIVE','READY','CANCELLED','REVERSED')),
  numerator_cents bigint not null check (numerator_cents >= 0),
  denominator_qty numeric(24,6) not null check (denominator_qty >= 0),
  source_count integer not null default 0 check (source_count >= 0),
  destination_count integer not null default 0 check (destination_count >= 0),
  operation_manifest jsonb not null,
  manifest_sha256 text not null,
  reason text not null check (btrim(reason) <> ''),
  created_by uuid references erp.app_users(id),
  created_at timestamptz not null default clock_timestamp(),
  ready_by uuid references erp.app_users(id),
  ready_at timestamptz,
  cancelled_by uuid references erp.app_users(id),
  cancelled_at timestamptz,
  cancellation_reason text,
  reversed_by uuid references erp.app_users(id),
  reversed_at timestamptz,
  reversal_reason text,
  row_version bigint not null default 1 check (row_version > 0),
  constraint attendance_hpp_pool_dates_check check (period_end >= period_start),
  constraint attendance_hpp_pool_zero_denominator_check check (
    (status = 'UNASSIGNED' and numerator_cents > 0 and denominator_qty = 0)
    or status <> 'UNASSIGNED'
  )
);

create index idx_attendance_hpp_pools_period
  on erp.attendance_hpp_pools(period_start, period_end, status);

create table erp.attendance_hpp_pool_sources (
  id uuid primary key default gen_random_uuid(),
  pool_id uuid not null references erp.attendance_hpp_pools(id),
  payroll_id uuid not null references erp.payroll_settlements(id),
  contractor_id uuid not null references erp.contractors(id),
  policy_manifest jsonb not null,
  original_journal_entry_id uuid not null references erp.journal_entries(id),
  original_journal_line_id uuid not null references erp.journal_lines(id),
  original_account_id uuid not null,
  original_line_debit_cents bigint not null check (original_line_debit_cents > 0),
  amount_cents bigint not null check (amount_cents > 0),
  source_payload_hash text not null,
  unique (pool_id, original_journal_line_id)
);

create index idx_attendance_hpp_pool_sources_line
  on erp.attendance_hpp_pool_sources(original_journal_line_id, pool_id);
create index idx_attendance_hpp_pool_sources_payroll
  on erp.attendance_hpp_pool_sources(payroll_id, pool_id);

create table erp.attendance_hpp_pool_sewing_sources (
  pool_id uuid not null references erp.attendance_hpp_pools(id),
  sewing_event_id uuid not null references erp.attendance_hpp_sewing_events(id),
  production_order_id uuid not null references erp.production_orders(id),
  contractor_id uuid not null references erp.contractors(id),
  policy_version_id uuid not null references erp.contractor_hpp_policy_versions(id),
  quantity_basis numeric(24,6) not null check (quantity_basis > 0),
  effective_date date not null,
  effective_at_epoch_us bigint not null,
  primary key (pool_id, sewing_event_id)
);

create index idx_attendance_hpp_pool_sewing_destination
  on erp.attendance_hpp_pool_sewing_sources(pool_id, production_order_id);

create table erp.attendance_hpp_pool_allocations (
  id uuid primary key default gen_random_uuid(),
  pool_id uuid not null references erp.attendance_hpp_pools(id),
  source_line_id uuid not null references erp.attendance_hpp_pool_sources(id),
  production_order_id uuid not null references erp.production_orders(id),
  quantity_basis numeric(24,6) not null check (quantity_basis > 0),
  allocated_cents bigint not null check (allocated_cents >= 0),
  allocation_rank integer not null check (allocation_rank > 0),
  unique (pool_id, source_line_id, production_order_id)
);

create index idx_attendance_hpp_allocations_pool_source
  on erp.attendance_hpp_pool_allocations(pool_id, source_line_id);

create table erp.attendance_hpp_destination_debit_intents (
  pool_id uuid not null references erp.attendance_hpp_pools(id),
  production_order_id uuid not null references erp.production_orders(id),
  debit_cents bigint not null check (debit_cents > 0),
  primary key (pool_id, production_order_id)
);

create table erp.attendance_hpp_terminal_credit_intents (
  pool_id uuid not null references erp.attendance_hpp_pools(id),
  source_line_id uuid not null references erp.attendance_hpp_pool_sources(id),
  original_journal_entry_id uuid not null references erp.journal_entries(id),
  original_journal_line_id uuid not null references erp.journal_lines(id),
  original_account_id uuid not null,
  credit_cents bigint not null check (credit_cents > 0),
  primary key (pool_id, source_line_id),
  unique (pool_id, original_journal_line_id)
);

create or replace function erp.guard_attendance_hpp_pool_write_v1()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
begin
  if current_setting('app.attendance_hpp_pool_write', true) is distinct from 'on' then
    raise exception 'Attendance HPP pool evidence is write-protected; use owning RPCs';
  end if;
  if tg_op = 'DELETE' then
    raise exception 'Attendance HPP evidence cannot be deleted';
  end if;
  return new;
end;
$function$;

create trigger trg_guard_attendance_hpp_pools_v1
before insert or update or delete on erp.attendance_hpp_pools
for each row execute function erp.guard_attendance_hpp_pool_write_v1();
create trigger trg_guard_attendance_hpp_pool_sources_v1
before insert or update or delete on erp.attendance_hpp_pool_sources
for each row execute function erp.guard_attendance_hpp_pool_write_v1();
create trigger trg_guard_attendance_hpp_pool_sewing_sources_v1
before insert or update or delete on erp.attendance_hpp_pool_sewing_sources
for each row execute function erp.guard_attendance_hpp_pool_write_v1();
create trigger trg_guard_attendance_hpp_pool_allocations_v1
before insert or update or delete on erp.attendance_hpp_pool_allocations
for each row execute function erp.guard_attendance_hpp_pool_write_v1();
create trigger trg_guard_attendance_hpp_destination_debits_v1
before insert or update or delete on erp.attendance_hpp_destination_debit_intents
for each row execute function erp.guard_attendance_hpp_pool_write_v1();
create trigger trg_guard_attendance_hpp_terminal_credits_v1
before insert or update or delete on erp.attendance_hpp_terminal_credit_intents
for each row execute function erp.guard_attendance_hpp_pool_write_v1();

create trigger trg_audit_attendance_hpp_pools
after insert or update or delete on erp.attendance_hpp_pools
for each row execute function erp.audit_row_change();

-- Resolve an original debit line and prove it belongs to the selected payroll.
-- JSON extraction is used only to tolerate audited column naming variants;
-- missing entry/source lineage fails closed.
create or replace function erp.cp3_payroll_journal_line_snapshot_v1(
  p_payroll_id uuid,
  p_journal_line_id uuid
)
returns jsonb
language plpgsql
stable
security invoker
set search_path = erp, public, pg_temp
as $function$
declare
  v_payroll jsonb;
  v_line jsonb;
  v_entry jsonb;
  v_entry_id uuid;
  v_payroll_entry_id uuid;
  v_debit numeric;
  v_credit numeric;
  v_account_id uuid;
  v_entry_source_id uuid;
  v_entry_source_type text;
  v_linked boolean := false;
begin
  select to_jsonb(p) into v_payroll
  from erp.payroll_settlements p
  where p.id = p_payroll_id;
  if v_payroll is null then raise exception 'Payroll settlement not found'; end if;

  select to_jsonb(j) into v_line
  from erp.journal_lines j
  where j.id = p_journal_line_id;
  if v_line is null then raise exception 'Journal line not found'; end if;

  v_entry_id := nullif(v_line ->> 'journal_entry_id', '')::uuid;
  v_account_id := nullif(v_line ->> 'account_id', '')::uuid;
  v_debit := coalesce(
    nullif(v_line ->> 'debit', '')::numeric,
    nullif(v_line ->> 'debit_amount', '')::numeric,
    0
  );
  v_credit := coalesce(
    nullif(v_line ->> 'credit', '')::numeric,
    nullif(v_line ->> 'credit_amount', '')::numeric,
    0
  );

  if v_entry_id is null or v_account_id is null or v_debit <= 0 or v_credit <> 0 then
    raise exception 'Attendance HPP source must be an identifiable debit-only journal line';
  end if;

  select to_jsonb(e) into v_entry
  from erp.journal_entries e
  where e.id = v_entry_id;
  if v_entry is null then raise exception 'Journal entry not found'; end if;

  v_payroll_entry_id := nullif(coalesce(
    v_payroll ->> 'journal_entry_id',
    v_payroll ->> 'posting_journal_entry_id',
    v_payroll ->> 'posted_journal_entry_id'
  ), '')::uuid;
  if v_payroll_entry_id is not null and v_payroll_entry_id = v_entry_id then
    v_linked := true;
  end if;

  v_entry_source_id := nullif(coalesce(
    v_entry ->> 'source_id',
    v_entry ->> 'reference_id',
    v_entry ->> 'document_id'
  ), '')::uuid;
  v_entry_source_type := upper(coalesce(
    v_entry ->> 'source_type',
    v_entry ->> 'reference_type',
    v_entry ->> 'document_type',
    ''
  ));
  if v_entry_source_id = p_payroll_id
     and v_entry_source_type in ('PAYROLL','PAYROLL_SETTLEMENT','PAYROLL_POSTING') then
    v_linked := true;
  end if;

  if not v_linked then
    raise exception 'Journal line is not authoritatively linked to payroll %', p_payroll_id;
  end if;

  return jsonb_build_object(
    'payroll_id', p_payroll_id,
    'journal_entry_id', v_entry_id,
    'journal_line_id', p_journal_line_id,
    'account_id', v_account_id,
    'debit_cents', round(v_debit * 100)::bigint,
    'credit_cents', round(v_credit * 100)::bigint,
    'entry_source_type', v_entry_source_type,
    'lineage_verified', true
  );
end;
$function$;

-- One set-based validation query scoped to one pool. No deferred per-row
-- trigger re-scans the whole pool at COMMIT.
create or replace function erp.cp3_validate_pool_v1(p_pool_id uuid)
returns jsonb
language sql
stable
security invoker
set search_path = erp, public, pg_temp
as $function$
with pool as (
  select * from erp.attendance_hpp_pools where id = p_pool_id
), totals as (
  select
    (select coalesce(sum(s.amount_cents),0) from erp.attendance_hpp_pool_sources s where s.pool_id=p_pool_id) source_cents,
    (select count(*) from erp.attendance_hpp_pool_sources s where s.pool_id=p_pool_id) source_count,
    (select coalesce(sum(s.quantity_basis),0) from erp.attendance_hpp_pool_sewing_sources s where s.pool_id=p_pool_id) sewing_qty,
    (select coalesce(sum(a.allocated_cents),0) from erp.attendance_hpp_pool_allocations a where a.pool_id=p_pool_id) allocation_cents,
    (select coalesce(sum(d.debit_cents),0) from erp.attendance_hpp_destination_debit_intents d where d.pool_id=p_pool_id) debit_cents,
    (select coalesce(sum(c.credit_cents),0) from erp.attendance_hpp_terminal_credit_intents c where c.pool_id=p_pool_id) credit_cents,
    (select count(*) from erp.attendance_hpp_terminal_credit_intents c where c.pool_id=p_pool_id) credit_count
), issues as (
  select issue
  from pool p cross join totals t
  cross join lateral unnest(array_remove(array[
    case when t.source_cents <> p.numerator_cents then 'SOURCE_TOTAL_MISMATCH' end,
    case when t.source_count <> p.source_count then 'SOURCE_COUNT_MISMATCH' end,
    case when t.sewing_qty <> p.denominator_qty then 'DENOMINATOR_MISMATCH' end,
    case when p.status <> 'UNASSIGNED' and t.allocation_cents <> p.numerator_cents then 'ALLOCATION_TOTAL_MISMATCH' end,
    case when p.status <> 'UNASSIGNED' and t.debit_cents <> p.numerator_cents then 'DESTINATION_DEBIT_MISMATCH' end,
    case when p.status <> 'UNASSIGNED' and t.credit_cents <> p.numerator_cents then 'TERMINAL_CREDIT_MISMATCH' end,
    case when p.status <> 'UNASSIGNED' and t.credit_count <> t.source_count then 'TERMINAL_CREDIT_CARDINALITY_MISMATCH' end,
    case when p.numerator_cents > 0 and p.denominator_qty = 0 and p.status <> 'UNASSIGNED' then 'ZERO_DENOMINATOR_NOT_UNASSIGNED' end,
    case when p.status = 'UNASSIGNED' and p.denominator_qty <> 0 then 'UNASSIGNED_WITH_NONZERO_DENOMINATOR' end
  ], null)) issue
)
select jsonb_build_object(
  'pool_id', p.id,
  'status', p.status,
  'numerator_cents', p.numerator_cents,
  'denominator_qty', p.denominator_qty,
  'source_count', t.source_count,
  'terminal_credit_count', t.credit_count,
  'source_cents', t.source_cents,
  'allocation_cents', t.allocation_cents,
  'destination_debit_cents', t.debit_cents,
  'terminal_credit_cents', t.credit_cents,
  'issue_count', (select count(*) from issues),
  'issues', coalesce((select jsonb_agg(issue order by issue) from issues), '[]'::jsonb),
  'complexity_class', 'O(pool_sources + pool_destinations + allocations)'
)
from pool p cross join totals t
$function$;

create or replace function erp.prepare_attendance_hpp_pool_v1(
  p_payload jsonb,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = erp, public, auth, extensions, pg_temp
as $function$
declare
  v_operation constant text := 'prepare_attendance_hpp_pool_v1';
  v_hash text;
  v_cached jsonb;
  v_period_start date;
  v_period_end date;
  v_reason text;
  v_lines jsonb;
  v_line jsonb;
  v_pool erp.attendance_hpp_pools%rowtype;
  v_payroll jsonb;
  v_payroll_id uuid;
  v_payroll_status text;
  v_contractor_id uuid;
  v_journal_line_id uuid;
  v_amount_cents bigint;
  v_journal jsonb;
  v_labor_account_id uuid;
  v_policy_manifest jsonb;
  v_attendance_cents bigint;
  v_used_cents bigint;
  v_manifest jsonb;
  v_manifest_sha text;
  v_validation jsonb;
  v_response jsonb;
begin
  perform erp.require_internal();
  perform erp.cp3_assert_json_object_v1(
    p_payload,
    array['period_start','period_end','source_lines','reason'],
    array['period_start','period_end','source_lines','reason','pool_number'],
    jsonb_build_object(
      'period_start','string','period_end','string','source_lines','array',
      'reason','string','pool_number','string|null'
    )
  );

  v_period_start := (p_payload ->> 'period_start')::date;
  v_period_end := (p_payload ->> 'period_end')::date;
  v_reason := nullif(btrim(p_payload ->> 'reason'), '');
  v_lines := p_payload -> 'source_lines';

  if v_period_end < v_period_start then raise exception 'period_end cannot precede period_start'; end if;
  if v_period_end - v_period_start > 62 then raise exception 'Attendance HPP period is bounded to 63 days'; end if;
  if v_reason is null then raise exception 'Pool reason is required'; end if;
  if jsonb_array_length(v_lines) = 0 then raise exception 'At least one payroll journal source line is required'; end if;

  select account_id into v_labor_account_id
  from erp.accounting_account_mappings
  where mapping_key = 'LABOR_COST';
  if v_labor_account_id is null then raise exception 'LABOR_COST accounting mapping is missing'; end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'contract_version', 'ATTENDANCE_HPP_POOL_V1'
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then return v_cached; end if;

  perform pg_advisory_xact_lock(hashtextextended(
    'ATTENDANCE_HPP_POOL|' || v_period_start::text || '|' || v_period_end::text, 0
  ));
  perform set_config('app.change_reason', v_reason, true);
  perform set_config('app.attendance_hpp_pool_write', 'on', true);

  insert into erp.attendance_hpp_pools(
    pool_number, period_start, period_end, status,
    numerator_cents, denominator_qty, operation_manifest, manifest_sha256,
    reason, created_by
  ) values (
    coalesce(nullif(btrim(p_payload ->> 'pool_number'), ''),
      'AHP-' || to_char(v_period_start,'YYYYMMDD') || '-' || left(replace(p_client_request_id::text,'-',''),12)),
    v_period_start, v_period_end, 'ACTIVE',
    0, 0, '{}'::jsonb, repeat('0',64), v_reason, erp.current_app_user_id()
  ) returning * into v_pool;

  for v_line in select value from jsonb_array_elements(v_lines)
  loop
    perform erp.cp3_assert_json_object_v1(
      v_line,
      array['payroll_id','original_journal_line_id','amount_cents'],
      array['payroll_id','original_journal_line_id','amount_cents'],
      jsonb_build_object('payroll_id','string','original_journal_line_id','string','amount_cents','number')
    );

    v_payroll_id := (v_line ->> 'payroll_id')::uuid;
    v_journal_line_id := (v_line ->> 'original_journal_line_id')::uuid;
    v_amount_cents := (v_line ->> 'amount_cents')::bigint;
    if v_amount_cents <= 0 then raise exception 'Source amount_cents must be positive'; end if;

    select to_jsonb(p) into v_payroll
    from erp.payroll_settlements p
    where p.id = v_payroll_id
    for update;
    if v_payroll is null then raise exception 'Payroll settlement not found'; end if;

    v_payroll_status := upper(coalesce(v_payroll ->> 'status',''));
    if v_payroll_status not in ('POSTED','APPROVED','PAID','SETTLED') then
      raise exception 'Payroll % status % is not an accepted terminal attendance source',
        v_payroll_id, v_payroll_status;
    end if;
    if nullif(v_payroll ->> 'period_start','')::date is distinct from v_period_start
       or nullif(v_payroll ->> 'period_end','')::date is distinct from v_period_end then
      raise exception 'Payroll period must exactly match the HPP pool period';
    end if;

    v_contractor_id := nullif(v_payroll ->> 'contractor_id','')::uuid;
    if v_contractor_id is null then raise exception 'Payroll contractor identity is missing'; end if;

    select jsonb_agg(jsonb_build_object(
      'policy_version_id', p.id,
      'effective_from', p.effective_from,
      'effective_to', p.effective_to,
      'contractor_role', p.contractor_role,
      'attendance_required', p.attendance_required,
      'is_special', p.is_special
    ) order by p.effective_from, p.id)
    into v_policy_manifest
    from erp.contractor_hpp_policy_versions p
    where p.contractor_id = v_contractor_id
      and daterange(p.effective_from, coalesce(p.effective_to + 1, 'infinity'::date), '[)')
          && daterange(v_period_start, v_period_end + 1, '[)');

    if exists (
      select 1
      from generate_series(v_period_start, v_period_end, interval '1 day') d
      where not exists (
        select 1
        from erp.contractor_hpp_policy_versions p
        where p.contractor_id = v_contractor_id
          and d::date >= p.effective_from
          and (p.effective_to is null or d::date <= p.effective_to)
          and p.contractor_role = 'MANDOR'
          and p.attendance_required
          and not p.is_special
      )
    ) then
      raise exception 'Contractor % lacks full-period explicit normal-Mandor eligibility', v_contractor_id;
    end if;

    select round(coalesce(sum(
      pai.paid_fraction_snapshot * pai.daily_rate_snapshot
    ),0) * 100)::bigint
    into v_attendance_cents
    from erp.payroll_attendance_items pai
    where pai.payroll_id = v_payroll_id;
    if v_attendance_cents <= 0 then
      raise exception 'Payroll % has no positive attendance amount', v_payroll_id;
    end if;

    v_journal := erp.cp3_payroll_journal_line_snapshot_v1(v_payroll_id, v_journal_line_id);
    if (v_journal ->> 'account_id')::uuid <> v_labor_account_id then
      raise exception 'Original journal line must debit LABOR_COST';
    end if;
    if (v_journal ->> 'debit_cents')::bigint < v_amount_cents then
      raise exception 'Source slice exceeds original journal-line debit';
    end if;

    select coalesce(sum(s.amount_cents),0) into v_used_cents
    from erp.attendance_hpp_pool_sources s
    join erp.attendance_hpp_pools p on p.id = s.pool_id
    where s.original_journal_line_id = v_journal_line_id
      and p.status not in ('CANCELLED','REVERSED');
    if v_used_cents + v_amount_cents > (v_journal ->> 'debit_cents')::bigint then
      raise exception 'Original journal line is already over-consumed by active HPP pools';
    end if;

    insert into erp.attendance_hpp_pool_sources(
      pool_id, payroll_id, contractor_id, policy_manifest,
      original_journal_entry_id, original_journal_line_id, original_account_id,
      original_line_debit_cents, amount_cents, source_payload_hash
    ) values (
      v_pool.id, v_payroll_id, v_contractor_id, v_policy_manifest,
      (v_journal ->> 'journal_entry_id')::uuid,
      v_journal_line_id, (v_journal ->> 'account_id')::uuid,
      (v_journal ->> 'debit_cents')::bigint, v_amount_cents,
      erp._request_hash(v_line)
    );
  end loop;

  if exists (
    select 1
    from erp.attendance_hpp_pool_sources s
    where s.pool_id = v_pool.id
    group by s.payroll_id
    having sum(s.amount_cents) is distinct from (
      select round(coalesce(sum(pai.paid_fraction_snapshot * pai.daily_rate_snapshot),0) * 100)::bigint
      from erp.payroll_attendance_items pai
      where pai.payroll_id = s.payroll_id
    )
  ) then
    raise exception 'Each payroll source slice must equal its posted attendance snapshot amount exactly';
  end if;

  insert into erp.attendance_hpp_pool_sewing_sources(
    pool_id, sewing_event_id, production_order_id, contractor_id,
    policy_version_id, quantity_basis, effective_date, effective_at_epoch_us
  )
  select
    v_pool.id, e.id, e.production_order_id, e.contractor_id,
    e.policy_version_id, e.quantity_signed, e.effective_date,
    floor(extract(epoch from e.effective_at) * 1000000)::bigint
  from erp.v_attendance_hpp_active_sewing_events_v1 e
  where e.effective_date between v_period_start and v_period_end
    and e.quantity_signed > 0
  order by e.effective_date, e.effective_at, e.id;

  update erp.attendance_hpp_pools p
  set numerator_cents = (
        select coalesce(sum(s.amount_cents),0)
        from erp.attendance_hpp_pool_sources s where s.pool_id=p.id
      ),
      denominator_qty = (
        select coalesce(sum(s.quantity_basis),0)
        from erp.attendance_hpp_pool_sewing_sources s where s.pool_id=p.id
      ),
      source_count = (
        select count(*) from erp.attendance_hpp_pool_sources s where s.pool_id=p.id
      ),
      destination_count = (
        select count(distinct s.production_order_id)
        from erp.attendance_hpp_pool_sewing_sources s where s.pool_id=p.id
      )
  where p.id = v_pool.id
  returning * into v_pool;

  if v_pool.numerator_cents > 0 and v_pool.denominator_qty = 0 then
    update erp.attendance_hpp_pools
    set status = 'UNASSIGNED', row_version = row_version + 1
    where id = v_pool.id
    returning * into v_pool;
  else
    -- Largest remainder allocation is set-based and deterministic. Each
    -- original debit line is distributed independently so terminal credit
    -- cardinality and exact cents cannot collapse by contractor/account.
    with po_qty as (
      select production_order_id, sum(quantity_basis) qty
      from erp.attendance_hpp_pool_sewing_sources
      where pool_id = v_pool.id
      group by production_order_id
    ), raw as (
      select
        s.id source_line_id,
        q.production_order_id,
        q.qty,
        s.amount_cents,
        (s.amount_cents::numeric * q.qty / v_pool.denominator_qty) raw_cents
      from erp.attendance_hpp_pool_sources s
      cross join po_qty q
      where s.pool_id = v_pool.id
    ), ranked as (
      select
        r.*,
        floor(r.raw_cents)::bigint base_cents,
        row_number() over (
          partition by r.source_line_id
          order by (r.raw_cents - floor(r.raw_cents)) desc, r.production_order_id
        ) allocation_rank,
        r.amount_cents - sum(floor(r.raw_cents)::bigint) over (
          partition by r.source_line_id
        ) remainder_cents
      from raw r
    )
    insert into erp.attendance_hpp_pool_allocations(
      pool_id, source_line_id, production_order_id,
      quantity_basis, allocated_cents, allocation_rank
    )
    select
      v_pool.id, source_line_id, production_order_id, qty,
      base_cents + case when allocation_rank <= remainder_cents then 1 else 0 end,
      allocation_rank
    from ranked
    where base_cents + case when allocation_rank <= remainder_cents then 1 else 0 end > 0;

    insert into erp.attendance_hpp_destination_debit_intents(
      pool_id, production_order_id, debit_cents
    )
    select v_pool.id, a.production_order_id, sum(a.allocated_cents)
    from erp.attendance_hpp_pool_allocations a
    where a.pool_id = v_pool.id
    group by a.production_order_id
    having sum(a.allocated_cents) > 0;

    insert into erp.attendance_hpp_terminal_credit_intents(
      pool_id, source_line_id, original_journal_entry_id,
      original_journal_line_id, original_account_id, credit_cents
    )
    select
      v_pool.id, s.id, s.original_journal_entry_id,
      s.original_journal_line_id, s.original_account_id, s.amount_cents
    from erp.attendance_hpp_pool_sources s
    where s.pool_id = v_pool.id;
  end if;

  select jsonb_build_object(
    'operation_type', 'ATTENDANCE_HPP_POOL',
    'version', 'ATTENDANCE_HPP_POOL_V1',
    'period_start_epoch_us',
      floor(extract(epoch from (v_period_start::timestamp at time zone 'UTC')) * 1000000)::bigint,
    'period_end_epoch_us',
      floor(extract(epoch from ((v_period_end + 1)::timestamp at time zone 'UTC')) * 1000000)::bigint - 1,
    'operations', coalesce((
      select jsonb_agg(op order by sort_key, stable_id)
      from (
        select 10 sort_key, s.id::text stable_id, jsonb_build_object(
          'operation_type','ATTENDANCE_HPP_POOL','action','PREPARE',
          'source_line_id',s.id,
          'original_journal_line_id',s.original_journal_line_id,
          'account_id',s.original_account_id,
          'amount_cents',s.amount_cents,
          'pool_id',v_pool.id
        ) op
        from erp.attendance_hpp_pool_sources s where s.pool_id=v_pool.id
        union all
        select 20, a.id::text, jsonb_build_object(
          'operation_type','ATTENDANCE_HPP_POOL','action','ALLOCATE',
          'source_line_id',a.source_line_id,
          'production_order_id',a.production_order_id,
          'amount_cents',a.allocated_cents,
          'quantity_basis',a.quantity_basis,
          'pool_id',v_pool.id
        )
        from erp.attendance_hpp_pool_allocations a where a.pool_id=v_pool.id
        union all
        select 30, d.production_order_id::text, jsonb_build_object(
          'operation_type','ATTENDANCE_HPP_POOL','action','DESTINATION_DEBIT',
          'production_order_id',d.production_order_id,
          'amount_cents',d.debit_cents,
          'pool_id',v_pool.id
        )
        from erp.attendance_hpp_destination_debit_intents d where d.pool_id=v_pool.id
        union all
        select 40, c.source_line_id::text, jsonb_build_object(
          'operation_type','ATTENDANCE_HPP_POOL','action','TERMINAL_CREDIT',
          'source_line_id',c.source_line_id,
          'original_journal_line_id',c.original_journal_line_id,
          'account_id',c.original_account_id,
          'amount_cents',c.credit_cents,
          'pool_id',v_pool.id
        )
        from erp.attendance_hpp_terminal_credit_intents c where c.pool_id=v_pool.id
      ) operations(sort_key, stable_id, op)
    ), '[]'::jsonb)
  ) into v_manifest;

  perform erp.cp3_assert_typed_operation_manifest_v1(v_manifest, 'ATTENDANCE_HPP_POOL');
  v_manifest_sha := encode(extensions.digest(convert_to(v_manifest::text, 'UTF8'), 'sha256'), 'hex');

  update erp.attendance_hpp_pools
  set operation_manifest = v_manifest,
      manifest_sha256 = v_manifest_sha,
      row_version = row_version + 1
  where id = v_pool.id
  returning * into v_pool;

  v_validation := erp.cp3_validate_pool_v1(v_pool.id);
  if v_pool.status = 'ACTIVE' and (v_validation ->> 'issue_count')::integer <> 0 then
    raise exception 'Prepared HPP pool failed validation: %', v_validation -> 'issues';
  end if;

  v_response := jsonb_build_object(
    'pool_id', v_pool.id,
    'pool_number', v_pool.pool_number,
    'status', v_pool.status,
    'numerator_cents', v_pool.numerator_cents,
    'denominator_qty', v_pool.denominator_qty,
    'manifest_sha256', v_pool.manifest_sha256,
    'row_version', v_pool.row_version,
    'validation', v_validation,
    'gl_posted', false,
    'route_enabled', false
  );
  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

-- ACTIVE/UNASSIGNED cancellation is atomic. No manual pre-reversal is needed.
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
  v_manifest jsonb;
  v_response jsonb;
begin
  perform erp.require_internal();
  if p_pool_id is null or p_expected_version is null or coalesce(btrim(p_reason),'')='' then
    raise exception 'pool_id, expected_version, and cancellation reason are required';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'pool_id',p_pool_id,'reason',p_reason,'expected_version',p_expected_version,
    'contract_version','ATTENDANCE_HPP_POOL_V1'
  ));
  v_cached := erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_pool from erp.attendance_hpp_pools where id=p_pool_id for update;
  if v_pool.id is null then raise exception 'HPP pool not found'; end if;
  if v_pool.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_pool.row_version;
  end if;
  if v_pool.status not in ('ACTIVE','UNASSIGNED') then
    raise exception 'Only ACTIVE or UNASSIGNED pool can be cancelled directly; observed %',v_pool.status;
  end if;

  v_manifest := jsonb_build_object(
    'operation_type','ATTENDANCE_HPP_POOL','version','ATTENDANCE_HPP_POOL_V1',
    'period_start_epoch_us',floor(extract(epoch from (v_pool.period_start::timestamp at time zone 'UTC'))*1000000)::bigint,
    'period_end_epoch_us',floor(extract(epoch from ((v_pool.period_end+1)::timestamp at time zone 'UTC'))*1000000)::bigint-1,
    'operations',jsonb_build_array(jsonb_build_object(
      'operation_type','ATTENDANCE_HPP_POOL','action','CANCEL','pool_id',v_pool.id,'reason',p_reason
    ))
  );
  perform erp.cp3_assert_typed_operation_manifest_v1(v_manifest,'ATTENDANCE_HPP_POOL');

  perform set_config('app.change_reason',p_reason,true);
  perform set_config('app.attendance_hpp_pool_write','on',true);
  update erp.attendance_hpp_pools
  set status='CANCELLED',cancelled_at=clock_timestamp(),cancelled_by=erp.current_app_user_id(),
      cancellation_reason=p_reason,operation_manifest=v_manifest,
      manifest_sha256=encode(extensions.digest(convert_to(v_manifest::text,'UTF8'),'sha256'),'hex'),
      row_version=row_version+1
  where id=p_pool_id
  returning * into v_pool;

  v_response:=jsonb_build_object(
    'pool_id',v_pool.id,'status',v_pool.status,'row_version',v_pool.row_version,
    'manifest_sha256',v_pool.manifest_sha256,'gl_posted',false,'residue_deleted',false
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

create or replace function erp.finalize_attendance_hpp_pool_intent_v1(
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
  v_operation constant text := 'finalize_attendance_hpp_pool_intent_v1';
  v_hash text;
  v_cached jsonb;
  v_pool erp.attendance_hpp_pools%rowtype;
  v_validation jsonb;
  v_manifest jsonb;
  v_response jsonb;
begin
  perform erp.require_internal();
  if p_pool_id is null or p_expected_version is null or coalesce(btrim(p_reason),'')='' then
    raise exception 'pool_id, expected_version, and finalization reason are required';
  end if;

  v_hash:=erp._request_hash(jsonb_build_object(
    'pool_id',p_pool_id,'reason',p_reason,'expected_version',p_expected_version,
    'contract_version','ATTENDANCE_HPP_POOL_V1'
  ));
  v_cached:=erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_pool from erp.attendance_hpp_pools where id=p_pool_id for update;
  if v_pool.id is null then raise exception 'HPP pool not found'; end if;
  if v_pool.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_pool.row_version;
  end if;
  if v_pool.status<>'ACTIVE' then raise exception 'Only ACTIVE pool can become READY'; end if;

  v_validation:=erp.cp3_validate_pool_v1(v_pool.id);
  if (v_validation->>'issue_count')::integer<>0 then
    raise exception 'HPP pool cannot finalize with issues: %',v_validation->'issues';
  end if;
  if v_pool.numerator_cents>0 and v_pool.denominator_qty=0 then
    raise exception 'Positive attendance pool with zero SELESAI_DIJAHIT stays UNASSIGNED';
  end if;

  v_manifest:=jsonb_set(
    v_pool.operation_manifest,
    '{operations}',
    (v_pool.operation_manifest->'operations') || jsonb_build_array(jsonb_build_object(
      'operation_type','ATTENDANCE_HPP_POOL','action','READY','pool_id',v_pool.id,'reason',p_reason
    )),
    false
  );
  perform erp.cp3_assert_typed_operation_manifest_v1(v_manifest,'ATTENDANCE_HPP_POOL');

  perform set_config('app.change_reason',p_reason,true);
  perform set_config('app.attendance_hpp_pool_write','on',true);
  update erp.attendance_hpp_pools
  set status='READY',ready_at=clock_timestamp(),ready_by=erp.current_app_user_id(),
      operation_manifest=v_manifest,
      manifest_sha256=encode(extensions.digest(convert_to(v_manifest::text,'UTF8'),'sha256'),'hex'),
      row_version=row_version+1
  where id=p_pool_id
  returning * into v_pool;

  v_response:=jsonb_build_object(
    'pool_id',v_pool.id,'status',v_pool.status,'row_version',v_pool.row_version,
    'manifest_sha256',v_pool.manifest_sha256,'validation',v_validation,
    'journal_intent_ready',true,'gl_posted',false,'route_enabled',false
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

create or replace function erp.reverse_attendance_hpp_pool_intent_v1(
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
  v_operation constant text := 'reverse_attendance_hpp_pool_intent_v1';
  v_hash text;
  v_cached jsonb;
  v_pool erp.attendance_hpp_pools%rowtype;
  v_manifest jsonb;
  v_response jsonb;
begin
  perform erp.require_owner_admin();
  if p_pool_id is null or p_expected_version is null or coalesce(btrim(p_reason),'')='' then
    raise exception 'pool_id, expected_version, and reversal reason are required';
  end if;

  v_hash:=erp._request_hash(jsonb_build_object(
    'pool_id',p_pool_id,'reason',p_reason,'expected_version',p_expected_version,
    'contract_version','ATTENDANCE_HPP_POOL_V1'
  ));
  v_cached:=erp._idempotency_begin(v_operation,p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;

  select * into v_pool from erp.attendance_hpp_pools where id=p_pool_id for update;
  if v_pool.id is null then raise exception 'HPP pool not found'; end if;
  if v_pool.row_version<>p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_pool.row_version;
  end if;
  if v_pool.status<>'READY' then raise exception 'Only READY journal intent can be reversed'; end if;

  v_manifest:=jsonb_set(
    v_pool.operation_manifest,
    '{operations}',
    (v_pool.operation_manifest->'operations') || jsonb_build_array(jsonb_build_object(
      'operation_type','ATTENDANCE_HPP_POOL','action','REVERSE','pool_id',v_pool.id,'reason',p_reason
    )),
    false
  );
  perform erp.cp3_assert_typed_operation_manifest_v1(v_manifest,'ATTENDANCE_HPP_POOL');

  perform set_config('app.change_reason',p_reason,true);
  perform set_config('app.attendance_hpp_pool_write','on',true);
  update erp.attendance_hpp_pools
  set status='REVERSED',reversed_at=clock_timestamp(),reversed_by=erp.current_app_user_id(),
      reversal_reason=p_reason,operation_manifest=v_manifest,
      manifest_sha256=encode(extensions.digest(convert_to(v_manifest::text,'UTF8'),'sha256'),'hex'),
      row_version=row_version+1
  where id=p_pool_id
  returning * into v_pool;

  v_response:=jsonb_build_object(
    'pool_id',v_pool.id,'status',v_pool.status,'row_version',v_pool.row_version,
    'manifest_sha256',v_pool.manifest_sha256,'gl_posted',false,'intent_reversed',true
  );
  return erp._idempotency_complete(v_operation,p_client_request_id,v_response);
end;
$function$;

-- Private surface: no browser facade, no authenticated execute, no hook.
alter table erp.attendance_hpp_pools enable row level security;
alter table erp.attendance_hpp_pool_sources enable row level security;
alter table erp.attendance_hpp_pool_sewing_sources enable row level security;
alter table erp.attendance_hpp_pool_allocations enable row level security;
alter table erp.attendance_hpp_destination_debit_intents enable row level security;
alter table erp.attendance_hpp_terminal_credit_intents enable row level security;

revoke all on table
  erp.attendance_hpp_pools,
  erp.attendance_hpp_pool_sources,
  erp.attendance_hpp_pool_sewing_sources,
  erp.attendance_hpp_pool_allocations,
  erp.attendance_hpp_destination_debit_intents,
  erp.attendance_hpp_terminal_credit_intents
from public, anon, authenticated;

grant all on table
  erp.attendance_hpp_pools,
  erp.attendance_hpp_pool_sources,
  erp.attendance_hpp_pool_sewing_sources,
  erp.attendance_hpp_pool_allocations,
  erp.attendance_hpp_destination_debit_intents,
  erp.attendance_hpp_terminal_credit_intents
to service_role;

revoke execute on function erp.cp3_payroll_journal_line_snapshot_v1(uuid,uuid) from public,anon,authenticated;
revoke execute on function erp.cp3_validate_pool_v1(uuid) from public,anon,authenticated;
revoke execute on function erp.prepare_attendance_hpp_pool_v1(jsonb,uuid) from public,anon,authenticated;
revoke execute on function erp.cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint) from public,anon,authenticated;
revoke execute on function erp.finalize_attendance_hpp_pool_intent_v1(uuid,text,uuid,bigint) from public,anon,authenticated;
revoke execute on function erp.reverse_attendance_hpp_pool_intent_v1(uuid,text,uuid,bigint) from public,anon,authenticated;

grant execute on function erp.cp3_payroll_journal_line_snapshot_v1(uuid,uuid) to service_role;
grant execute on function erp.cp3_validate_pool_v1(uuid) to service_role;
grant execute on function erp.prepare_attendance_hpp_pool_v1(jsonb,uuid) to service_role;
grant execute on function erp.cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint) to service_role;
grant execute on function erp.finalize_attendance_hpp_pool_intent_v1(uuid,text,uuid,bigint) to service_role;
grant execute on function erp.reverse_attendance_hpp_pool_intent_v1(uuid,text,uuid,bigint) to service_role;

comment on table erp.attendance_hpp_terminal_credit_intents is
  'Exactly one terminal credit intent per original payroll LABOR_COST debit line; never collapsed by contractor/account.';
comment on function erp.cp3_validate_pool_v1(uuid) is
  'Set-based bounded validation for one pool. No deferred row-by-row O(N^2) commit rescan.';
comment on function erp.finalize_attendance_hpp_pool_intent_v1(uuid,text,uuid,bigint) is
  'Marks reviewed journal intent READY. It does not call post_journal and does not enable production posting.';

insert into erp.schema_migrations(version,description,installed_at)
values (
  'v2.6.14-cp3-foundation',
  'Private source candidate: explicit normal-Mandor policy, immutable SELESAI_DIJAHIT denominator, payroll-linked original debit-line allocation intents, deterministic manifest, active cancellation, strict JSON, bounded validation; no public facade/hooks/GL post',
  clock_timestamp()
);

notify pgrst, 'reload schema';
commit;
