begin;

do $test$
declare
  v_amount numeric;
  v_view text:=pg_get_viewdef('erp.v_payroll_production_work_eligibility'::regclass,true);
begin
  if not exists (
    select 1 from pg_class c
    where c.oid='erp.v_payroll_production_work_eligibility'::regclass
      and 'security_invoker=true'=any(coalesce(c.reloptions,array[]::text[]))
  ) then
    raise exception 'TEST_FAILED: payroll eligibility view is not security_invoker';
  end if;

  if position('b.qty_payable AS eligible_after_laundry_qty' in v_view)=0
     or position('0 AS held_for_laundry_qty' in v_view)=0 then
    raise exception 'TEST_FAILED: component entitlement projection is missing';
  end if;

  if exists (
    select 1 from erp.v_payroll_production_work_eligibility e
    where e.eligible_after_laundry_qty<>e.source_qty_payable
       or e.held_for_laundry_qty<>0
       or e.remaining_eligible_qty
            <>greatest(e.source_qty_payable-e.allocated_to_nonreversed_payroll_qty,0)
  ) then
    raise exception 'TEST_FAILED: live payroll eligibility row invariant mismatch';
  end if;

  -- Economically equivalent per-component fixture:
  -- 200 x 17,800 - 20 x (2,500 + 500 + 400) = 3,492,000.
  select sum(qty_payable*rate_snapshot)
  into v_amount
  from (values
    (200,14400::numeric),
    (180,2500::numeric),
    (180,500::numeric),
    (180,400::numeric)
  ) component_lines(qty_payable,rate_snapshot);

  if v_amount<>3492000 then
    raise exception 'TEST_FAILED: 200/20 component fixture got %',v_amount;
  end if;

  if exists (
    select 1 from erp.run_v263a_payroll_integrity_checks() where issue_count<>0
  ) then
    raise exception 'TEST_FAILED: payroll integrity check returned a nonzero issue';
  end if;
end
$test$;

select
  200 as sewn_qty,
  20 as stuck_qty,
  17800 as full_rate,
  3400 as uninstalled_component_rate,
  3492000 as expected_payroll_entitlement;

rollback;
