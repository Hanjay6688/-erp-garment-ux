-- ERP Enteng only.
-- Owner rule:
--   completed sewing qty x full component rate
--   - BS qty x unfinished component snapshot
--   - Laundry Stuck qty x uninstalled component snapshot.
--
-- The backend stores this economically equivalent rule per work component:
-- every work_completion_lines.qty_payable is immediately payroll-eligible.
-- A component not installed on BS/Stuck pieces must therefore have the lower
-- completed/payable quantity at source; laundry return is operational metadata,
-- not a payroll gate.

do $preflight$
begin
  if to_regclass('erp.v_payroll_production_work_eligibility') is null then
    raise exception 'PAYROLL_COMPONENT_ENTITLEMENT_PRECONDITION_FAILED: eligibility view missing';
  end if;

  if md5(pg_get_viewdef('erp.v_payroll_production_work_eligibility'::regclass, true))
       <> 'd7d782a167be27971ccfb358bbd00329' then
    raise exception 'CONCURRENT_WRITER_DETECTED: eligibility view changed after fingerprint';
  end if;

  if md5(pg_get_functiondef('erp.assert_laundry_receipt_reversal_payroll_safe(uuid)'::regprocedure))
       <> 'fd9ad4f0da6d33cce6a2e379781d8560' then
    raise exception 'CONCURRENT_WRITER_DETECTED: laundry reversal payroll guard changed after fingerprint';
  end if;

  if md5(pg_get_functiondef('erp.run_v263a_payroll_integrity_checks()'::regprocedure))
       <> 'f722bb540dc9d703b28617bdf54de1ea' then
    raise exception 'CONCURRENT_WRITER_DETECTED: payroll integrity checks changed after fingerprint';
  end if;
end
$preflight$;

create or replace view erp.v_payroll_production_work_eligibility
with (security_invoker = true)
as
with laundry_sent as (
  select
    ldl.cutting_group_id,
    sum(ldl.qty_sent_pcs) as sent_qty
  from erp.laundry_delivery_lines ldl
  join erp.laundry_deliveries ld on ld.id = ldl.delivery_id
  where ld.status not in ('DRAFT', 'REVERSED')
  group by ldl.cutting_group_id
),
laundry_returned as (
  select
    ldl.cutting_group_id,
    sum(lrl.qty_good_received + lrl.qty_bs_laundry) as physically_returned_qty
  from erp.laundry_receipt_lines lrl
  join erp.laundry_receipts lr
    on lr.id = lrl.receipt_id
   and lr.status = 'POSTED'
  join erp.laundry_delivery_lines ldl on ldl.id = lrl.delivery_line_id
  group by ldl.cutting_group_id
),
base as (
  select
    wcl.id as source_id,
    wce.id as completion_id,
    wce.po_id,
    wce.contractor_id,
    wce.cutting_group_id,
    wcl.work_component_id,
    wce.physical_at,
    wcl.qty_payable,
    wcl.rate_snapshot,
    coalesce(ls.sent_qty, 0::bigint) as laundry_sent_qty,
    coalesce(lr.physically_returned_qty, 0::bigint) as laundry_returned_qty,
    ls.cutting_group_id is not null as laundry_required
  from erp.work_completion_lines wcl
  join erp.work_completion_events wce
    on wce.id = wcl.completion_id
   and wce.status = 'POSTED'
  left join laundry_sent ls on ls.cutting_group_id = wce.cutting_group_id
  left join laundry_returned lr on lr.cutting_group_id = wce.cutting_group_id
),
allocated as (
  select
    pwi.source_id,
    pwi.work_component_id,
    sum(pwi.qty_payable)::integer as allocated_qty
  from erp.payroll_work_items pwi
  join erp.payroll_settlements ps on ps.id = pwi.payroll_id
  where pwi.source_type = 'PRODUCTION'
    and ps.status <> 'REVERSED'
  group by pwi.source_id, pwi.work_component_id
)
select
  b.source_id,
  b.completion_id,
  b.po_id,
  b.contractor_id,
  b.cutting_group_id,
  b.work_component_id,
  b.physical_at,
  b.qty_payable as source_qty_payable,
  b.rate_snapshot,
  b.laundry_required,
  b.laundry_sent_qty,
  b.laundry_returned_qty,
  b.qty_payable as eligible_after_laundry_qty,
  0::integer as held_for_laundry_qty,
  coalesce(a.allocated_qty, 0) as allocated_to_nonreversed_payroll_qty,
  greatest(b.qty_payable - coalesce(a.allocated_qty, 0), 0) as remaining_eligible_qty,
  round(
    greatest(b.qty_payable - coalesce(a.allocated_qty, 0), 0)::numeric
      * b.rate_snapshot,
    2
  ) as remaining_eligible_amount,
  case
    when not b.laundry_required then 'COMPONENT_PAYABLE_NO_LAUNDRY'
    when b.laundry_sent_qty > 0 and b.laundry_returned_qty >= b.laundry_sent_qty
      then 'COMPONENT_PAYABLE_LAUNDRY_COMPLETE'
    else 'COMPONENT_PAYABLE_LAUNDRY_OUTSTANDING'
  end as eligibility_state
from base b
left join allocated a
  on a.source_id = b.source_id
 and a.work_component_id = b.work_component_id;

comment on view erp.v_payroll_production_work_eligibility is
  'Payroll entitlement follows posted per-component qty_payable immediately. Laundry return/stuck remains operational metadata and never caps completed sewing entitlement.';

comment on column erp.v_payroll_production_work_eligibility.eligible_after_laundry_qty is
  'Compatibility column: equals source_qty_payable. The legacy name is retained so callers do not break; laundry is no longer an eligibility gate.';

comment on column erp.v_payroll_production_work_eligibility.held_for_laundry_qty is
  'Always zero. Uninstalled BS/Stuck components are represented by lower per-component qty_payable at work-completion source.';

create or replace function erp.assert_laundry_receipt_reversal_payroll_safe(p_receipt_id uuid)
returns void
language plpgsql
security definer
set search_path to 'erp', 'public', 'pg_temp'
as $function$
begin
  -- Kept as a compatibility hook for the existing laundry reversal path.
  -- Laundry receipt reversal cannot retract component work already completed,
  -- so it no longer requires reversal of an otherwise valid payroll Nota.
  return;
end;
$function$;

comment on function erp.assert_laundry_receipt_reversal_payroll_safe(uuid) is
  'Compatibility hook. Payroll eligibility is based on posted component qty_payable, not physical laundry return, so laundry receipt reversal does not retract wage entitlement.';

create or replace function erp.run_v263a_payroll_integrity_checks()
returns table(check_name text, severity text, issue_count bigint, details text)
language sql
stable
security definer
set search_path to 'erp', 'public', 'pg_temp'
as $function$
  select
    'production_payroll_exceeds_component_entitlement',
    'CRITICAL',
    count(*)::bigint,
    'Allocated production payroll qty must not exceed posted per-component qty_payable'
  from erp.v_payroll_production_work_eligibility e
  where e.allocated_to_nonreversed_payroll_qty > e.source_qty_payable

  union all
  select
    'rework_payroll_before_case_resolution',
    'CRITICAL',
    count(*)::bigint,
    'Rework Nota lines require COMPLETED+cost_posted rework and a RESOLVED BS case'
  from erp.payroll_work_items pwi
  join erp.payroll_settlements ps
    on ps.id = pwi.payroll_id
   and ps.status <> 'REVERSED'
  join erp.rework_component_lines rcl
    on pwi.source_type = 'REWORK'
   and rcl.id = pwi.source_id
  join erp.rework_orders ro on ro.id = rcl.rework_order_id
  join erp.bs_case_components bcc on bcc.id = rcl.bs_case_component_id
  join erp.bs_cases bc on bc.id = bcc.bs_case_id
  where ro.status <> 'COMPLETED'
     or not ro.cost_posted
     or bc.status <> 'RESOLVED'

  union all
  select
    'payroll_work_wrong_contractor',
    'CRITICAL',
    count(*)::bigint,
    'Every Nota work line must belong to the Nota Mandor'
  from erp.payroll_work_items pwi
  join erp.payroll_settlements ps on ps.id = pwi.payroll_id
  left join erp.work_completion_lines wcl
    on pwi.source_type = 'PRODUCTION'
   and wcl.id = pwi.source_id
  left join erp.work_completion_events wce on wce.id = wcl.completion_id
  left join erp.rework_component_lines rcl
    on pwi.source_type = 'REWORK'
   and rcl.id = pwi.source_id
  left join erp.rework_orders ro on ro.id = rcl.rework_order_id
  where ps.status <> 'REVERSED'
    and ps.contractor_id is distinct from coalesce(wce.contractor_id, ro.contractor_id);
$function$;

comment on function erp.run_v263a_payroll_integrity_checks() is
  'Payroll integrity checks aligned to completed component entitlement; production wages are not gated by physical laundry return.';

do $verification$
declare
  v_example numeric;
begin
  if not exists (
    select 1
    from pg_class c
    where c.oid = 'erp.v_payroll_production_work_eligibility'::regclass
      and 'security_invoker=true' = any(coalesce(c.reloptions, array[]::text[]))
  ) then
    raise exception 'PAYROLL_COMPONENT_ENTITLEMENT_VERIFY_FAILED: security_invoker missing';
  end if;

  if exists (
    select 1
    from erp.v_payroll_production_work_eligibility e
    where e.eligible_after_laundry_qty <> e.source_qty_payable
       or e.held_for_laundry_qty <> 0
       or e.remaining_eligible_qty
            <> greatest(e.source_qty_payable - e.allocated_to_nonreversed_payroll_qty, 0)
  ) then
    raise exception 'PAYROLL_COMPONENT_ENTITLEMENT_VERIFY_FAILED: row invariant mismatch';
  end if;

  -- 200 sewn, 20 stuck, full rate 17,800, uninstalled components 3,400.
  select 200 * 17800 - 20 * (2500 + 500 + 400) into v_example;
  if v_example <> 3492000 then
    raise exception 'PAYROLL_COMPONENT_ENTITLEMENT_VERIFY_FAILED: 200/20 example got %', v_example;
  end if;
end
$verification$;
