-- ERP Garment v2.6.14c — CP3 SOURCE CANDIDATE HARDENING
-- Cross-row/source invariants that remain private and source-only.

begin;
set local lock_timeout = '10s';
set local statement_timeout = '120s';

do $guard$
begin
  if to_regclass('erp.contractor_hpp_policy_versions') is null
     or to_regclass('erp.attendance_hpp_sewing_events') is null
     or to_regclass('erp.attendance_hpp_pools') is null then
    raise exception 'v2.6.14c requires v2.6.14a and v2.6.14b';
  end if;
end;
$guard$;

-- The append-only trigger independently rechecks source and lineage. A caller
-- cannot bypass the owning RPC merely by setting the internal write GUC.
create or replace function erp.guard_attendance_hpp_sewing_event_v1()
returns trigger
language plpgsql
set search_path = erp, public, pg_temp
as $function$
declare
  v_source erp.attendance_hpp_sewing_events%rowtype;
  v_policy erp.contractor_hpp_policy_versions%rowtype;
begin
  if current_setting('app.attendance_hpp_sewing_write', true) is distinct from 'on' then
    raise exception 'Sewing-terminal events are append-only; use authoritative record/correct/reverse RPCs';
  end if;
  if tg_op <> 'INSERT' then
    raise exception 'Sewing-terminal facts cannot be updated or deleted';
  end if;
  if new.event_type <> 'SELESAI_DIJAHIT'
     or new.business_source_kind <> 'SEWING_TERMINAL'
     or not isfinite(new.effective_at) then
    raise exception 'Only finite explicit SELESAI_DIJAHIT / SEWING_TERMINAL facts are accepted';
  end if;

  select * into v_policy
  from erp.contractor_hpp_policy_versions p
  where p.id = new.policy_version_id;
  if v_policy.id is null
     or v_policy.contractor_id <> new.contractor_id
     or new.effective_date < v_policy.effective_from
     or (v_policy.effective_to is not null and new.effective_date > v_policy.effective_to)
     or v_policy.contractor_role <> 'MANDOR'
     or not v_policy.attendance_required
     or v_policy.is_special then
    raise exception 'Sewing event policy does not prove explicit normal-Mandor eligibility on effective_date';
  end if;

  if new.event_action in ('RECORD','CORRECTION') then
    perform erp.cp3_validate_sewing_source_v1(
      new.source_work_completion_line_id,
      new.production_order_id,
      new.contractor_id,
      new.quantity_signed
    );
  end if;

  if new.event_action = 'REVERSAL' then
    select * into v_source
    from erp.attendance_hpp_sewing_events e
    where e.id = new.reversal_of_event_id;
    if v_source.id is null
       or v_source.event_action not in ('RECORD','CORRECTION')
       or new.production_order_id <> v_source.production_order_id
       or new.contractor_id <> v_source.contractor_id
       or new.source_work_completion_line_id <> v_source.source_work_completion_line_id
       or new.effective_date <> v_source.effective_date
       or new.effective_at <> v_source.effective_at
       or new.policy_version_id <> v_source.policy_version_id
       or new.quantity_signed <> -v_source.quantity_signed then
      raise exception 'Reversal must exactly negate one authoritative sewing event';
    end if;
  elsif new.event_action = 'CORRECTION' then
    select * into v_source
    from erp.attendance_hpp_sewing_events e
    where e.id = new.correction_of_event_id;
    if v_source.id is null
       or v_source.event_action not in ('RECORD','CORRECTION')
       or new.production_order_id <> v_source.production_order_id
       or new.contractor_id <> v_source.contractor_id
       or new.source_work_completion_line_id <> v_source.source_work_completion_line_id then
      raise exception 'Correction must retain source production, Mandor, and completion-line lineage';
    end if;
  end if;

  return new;
end;
$function$;

-- Replace the validator with additional cross-source completeness checks while
-- preserving one bounded set-based query scoped to exactly one pool.
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
    (select count(distinct s.contractor_id) from erp.attendance_hpp_pool_sources s where s.pool_id=p_pool_id) source_contractor_count,
    (select coalesce(sum(s.quantity_basis),0) from erp.attendance_hpp_pool_sewing_sources s where s.pool_id=p_pool_id) sewing_qty,
    (select count(distinct s.production_order_id) from erp.attendance_hpp_pool_sewing_sources s where s.pool_id=p_pool_id) sewing_destination_count,
    (select count(*) from erp.attendance_hpp_pool_sewing_sources s
      where s.pool_id=p_pool_id and not exists (
        select 1 from erp.attendance_hpp_pool_sources ps
        where ps.pool_id=p_pool_id and ps.contractor_id=s.contractor_id
      )) sewing_without_payroll_contractor_count,
    (select count(*) from erp.attendance_hpp_pool_sources s
      where s.pool_id=p_pool_id and (
        jsonb_typeof(s.policy_manifest) is distinct from 'array'
        or jsonb_array_length(s.policy_manifest)=0
      )) invalid_policy_manifest_count,
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
    case when t.sewing_destination_count <> p.destination_count then 'DESTINATION_COUNT_MISMATCH' end,
    case when t.sewing_without_payroll_contractor_count <> 0 then 'SEWING_CONTRACTOR_WITHOUT_PAYROLL_SOURCE' end,
    case when t.invalid_policy_manifest_count <> 0 then 'INVALID_POLICY_MANIFEST' end,
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
  'source_contractor_count', t.source_contractor_count,
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

comment on function erp.guard_attendance_hpp_sewing_event_v1() is
  'Append-only defense-in-depth: exact reversal/correction lineage, explicit normal-Mandor policy, and authoritative sewing source are rechecked inside the trigger.';
comment on function erp.cp3_validate_pool_v1(uuid) is
  'Bounded set-based one-pool validator including source/destination count, policy manifest, and sewing-contractor/payroll-source completeness.';

insert into erp.schema_migrations(version,description,installed_at)
values (
  'v2.6.14-cp3-hardening',
  'CP3 source candidate hardening: trigger-level sewing lineage/policy/source verification and bounded pool contractor/source completeness checks',
  clock_timestamp()
);

notify pgrst, 'reload schema';
commit;
