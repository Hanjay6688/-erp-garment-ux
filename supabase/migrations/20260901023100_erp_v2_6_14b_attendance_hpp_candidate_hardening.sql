-- ERP Garment v2.6.14b candidate hardening.
-- Source-only follow-up to v2.6.14a; not approved for UAT application.

begin;

set local lock_timeout = '10s';
set local statement_timeout = '120s';

-- Exactly one direct successor may identify one cancelled pool as its correction source.
create unique index if not exists uq_attendance_hpp_one_direct_correction
  on erp.attendance_hpp_pools(correction_of_pool_id)
  where correction_of_pool_id is not null;

-- Open-ended policy coverage is represented by a present JSON key with a JSON null
-- value. Required-key validation still rejects a missing key, while allowing that
-- one explicitly nullable field. All other contract keys remain non-null and closed.
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
      array['payroll_id','contractor_id','policy_version_id','contractor_role_snapshot','attendance_required_snapshot','is_special_snapshot','policy_effective_from','original_debit_journal_line_id','original_debit_amount_cents','attendance_amount_cents'],
      array['payroll_id','contractor_id','policy_version_id','contractor_role_snapshot','attendance_required_snapshot','is_special_snapshot','policy_effective_from','policy_effective_to','original_debit_journal_line_id','original_debit_amount_cents','attendance_amount_cents'],
      'attendance HPP source'
    );
    if not (v_item ? 'policy_effective_to') then
      raise exception 'attendance HPP source requires key policy_effective_to, which may be JSON null for open-ended coverage';
    end if;
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

-- Persist a reviewable exclusion explanation without changing the hashed allocation
-- basis. This function is deterministic and read-only; it makes Special and
-- attendance-not-required exclusions visible rather than implicit.
create or replace function erp.attendance_hpp_exclusion_summary_v1(
  p_period_start date,
  p_period_end date
)
returns jsonb
language sql
stable
security definer
set search_path = erp, public, pg_temp
as $function$
with payroll_exclusions as (
  select
    ps.id payroll_id,
    ps.contractor_id,
    ps.attendance_total,
    case
      when pol.id is null then 'MISSING_EXPLICIT_POLICY'
      when pol.contractor_role_snapshot <> 'MANDOR' then 'ROLE_NOT_MANDOR'
      when not pol.attendance_required_snapshot then 'ATTENDANCE_NOT_REQUIRED'
      when pol.is_special then 'SPECIAL'
      else null
    end exclusion_reason
  from erp.payroll_settlements ps
  left join lateral (
    select p.*
    from erp.contractor_hpp_policy_versions p
    where p.contractor_id=ps.contractor_id
      and p.effective_from<=p_period_start
      and (p.effective_to is null or p.effective_to>=p_period_end)
    order by p.effective_from desc,p.id desc
    limit 1
  ) pol on true
  where ps.status='PAID'
    and ps.period_start=p_period_start
    and ps.period_end=p_period_end
    and ps.attendance_total>0
), sewing_exclusions as (
  select
    e.id sewing_terminal_event_id,
    e.contractor_id,
    e.po_id,
    e.qty_signed sewing_qty,
    erp._cp3_epoch_microseconds(e.physical_at) physical_at_epoch_us,
    case
      when pol.id is null then 'MISSING_EXPLICIT_POLICY'
      when pol.contractor_role_snapshot <> 'MANDOR' then 'ROLE_NOT_MANDOR'
      when not pol.attendance_required_snapshot then 'ATTENDANCE_NOT_REQUIRED'
      when pol.is_special then 'SPECIAL'
      else null
    end exclusion_reason
  from erp.sewing_terminal_events e
  left join lateral (
    select p.*
    from erp.contractor_hpp_policy_versions p
    where p.contractor_id=e.contractor_id
      and p.effective_from<=p_period_start
      and (p.effective_to is null or p.effective_to>=p_period_end)
    order by p.effective_from desc,p.id desc
    limit 1
  ) pol on true
  where e.event_kind='SELESAI_DIJAHIT'
    and e.physical_at::date between p_period_start and p_period_end
    and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id)
)
select jsonb_build_object(
  'excluded_payrolls',coalesce((
    select jsonb_agg(jsonb_build_object(
      'payroll_id',payroll_id,
      'contractor_id',contractor_id,
      'attendance_amount_cents',round(attendance_total*100)::bigint,
      'reason',exclusion_reason
    ) order by contractor_id,payroll_id)
    from payroll_exclusions where exclusion_reason is not null
  ),'[]'::jsonb),
  'excluded_sewing_events',coalesce((
    select jsonb_agg(jsonb_build_object(
      'sewing_terminal_event_id',sewing_terminal_event_id,
      'contractor_id',contractor_id,
      'po_id',po_id,
      'sewing_qty',sewing_qty,
      'physical_at_epoch_us',physical_at_epoch_us,
      'reason',exclusion_reason
    ) order by physical_at_epoch_us,sewing_terminal_event_id)
    from sewing_exclusions where exclusion_reason is not null
  ),'[]'::jsonb)
)
$function$;

revoke execute on function erp.attendance_hpp_exclusion_summary_v1(date,date)
  from public,anon,authenticated,service_role;

insert into erp.schema_migrations(version,description,installed_at)
values(
  'v2.6.14b',
  'Candidate hardening: nullable open-ended policy manifest key, one direct correction lineage, deterministic visible exclusion summary',
  clock_timestamp()
);

commit;
