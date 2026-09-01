-- Manual rollback for 20260901161322_erp_v2_6_15_payroll_component_entitlement.sql.
-- ERP Enteng only. This intentionally restores the legacy laundry-return gate.

do $preflight$
begin
  if md5(pg_get_viewdef('erp.v_payroll_production_work_eligibility'::regclass, true))
       <> '5e04553cdbb7e91404191dd4ca30a57b' then
    raise exception 'CONCURRENT_WRITER_DETECTED: candidate eligibility view changed before rollback';
  end if;

  if md5(pg_get_functiondef('erp.assert_laundry_receipt_reversal_payroll_safe(uuid)'::regprocedure))
       <> 'e1693a04b22a2870a50266e648cca574' then
    raise exception 'CONCURRENT_WRITER_DETECTED: candidate reversal guard changed before rollback';
  end if;

  if md5(pg_get_functiondef('erp.run_v263a_payroll_integrity_checks()'::regprocedure))
       <> '0740acdebe12fe8d47d48bbd67cb8ab3' then
    raise exception 'CONCURRENT_WRITER_DETECTED: candidate integrity checks changed before rollback';
  end if;
end
$preflight$;

create or replace view erp.v_payroll_production_work_eligibility
with (security_invoker = true)
as
with laundry_sent as (
  select ldl.cutting_group_id,sum(ldl.qty_sent_pcs) as sent_qty
  from erp.laundry_delivery_lines ldl
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  where ld.status not in ('DRAFT','REVERSED')
  group by ldl.cutting_group_id
),
laundry_returned as (
  select ldl.cutting_group_id,
         sum(lrl.qty_good_received+lrl.qty_bs_laundry) as physically_returned_qty
  from erp.laundry_receipt_lines lrl
  join erp.laundry_receipts lr on lr.id=lrl.receipt_id and lr.status='POSTED'
  join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
  group by ldl.cutting_group_id
),
base as (
  select wcl.id as source_id,wce.id as completion_id,wce.po_id,wce.contractor_id,
         wce.cutting_group_id,wcl.work_component_id,wce.physical_at,wcl.qty_payable,
         wcl.rate_snapshot,coalesce(ls.sent_qty,0::bigint) as laundry_sent_qty,
         coalesce(lr.physically_returned_qty,0::bigint) as laundry_returned_qty,
         ls.cutting_group_id is not null as laundry_required,
         coalesce(sum(wcl.qty_payable) over (
           partition by wce.cutting_group_id,wcl.work_component_id
           order by wce.physical_at,wce.id,wcl.id
           rows between unbounded preceding and 1 preceding
         ),0::bigint) as prior_component_qty,
         sum(wcl.qty_payable) over (
           partition by wce.cutting_group_id,wcl.work_component_id
           order by wce.physical_at,wce.id,wcl.id
           rows between unbounded preceding and current row
         ) as cumulative_component_qty
  from erp.work_completion_lines wcl
  join erp.work_completion_events wce on wce.id=wcl.completion_id and wce.status='POSTED'
  left join laundry_sent ls on ls.cutting_group_id=wce.cutting_group_id
  left join laundry_returned lr on lr.cutting_group_id=wce.cutting_group_id
),
eligible as (
  select b.*,
         case
           when b.cutting_group_id is null or not b.laundry_required then b.qty_payable
           else greatest(
             least(b.cumulative_component_qty,b.laundry_returned_qty)
             - least(b.prior_component_qty,b.laundry_returned_qty),
             0::bigint
           )::integer
         end as eligible_after_laundry_qty
  from base b
),
allocated as (
  select pwi.source_id,pwi.work_component_id,sum(pwi.qty_payable)::integer as allocated_qty
  from erp.payroll_work_items pwi
  join erp.payroll_settlements ps on ps.id=pwi.payroll_id
  where pwi.source_type='PRODUCTION' and ps.status<>'REVERSED'
  group by pwi.source_id,pwi.work_component_id
)
select e.source_id,e.completion_id,e.po_id,e.contractor_id,e.cutting_group_id,
       e.work_component_id,e.physical_at,e.qty_payable as source_qty_payable,
       e.rate_snapshot,e.laundry_required,e.laundry_sent_qty,e.laundry_returned_qty,
       e.eligible_after_laundry_qty,
       e.qty_payable-e.eligible_after_laundry_qty as held_for_laundry_qty,
       coalesce(a.allocated_qty,0) as allocated_to_nonreversed_payroll_qty,
       greatest(e.eligible_after_laundry_qty-coalesce(a.allocated_qty,0),0) as remaining_eligible_qty,
       round(greatest(e.eligible_after_laundry_qty-coalesce(a.allocated_qty,0),0)::numeric
             * e.rate_snapshot,2) as remaining_eligible_amount,
       case
         when not e.laundry_required then 'NO_LAUNDRY_REQUIRED'
         when e.eligible_after_laundry_qty=e.qty_payable then 'PHYSICALLY_RETURNED'
         when e.eligible_after_laundry_qty=0 then 'HELD_AT_LAUNDRY'
         else 'PARTIALLY_RELEASED'
       end as eligibility_state
from eligible e
left join allocated a
  on a.source_id=e.source_id and a.work_component_id=e.work_component_id;

comment on view erp.v_payroll_production_work_eligibility is null;
comment on column erp.v_payroll_production_work_eligibility.eligible_after_laundry_qty is null;
comment on column erp.v_payroll_production_work_eligibility.held_for_laundry_qty is null;

create or replace function erp.assert_laundry_receipt_reversal_payroll_safe(p_receipt_id uuid)
returns void
language plpgsql
security definer
set search_path to 'erp','public','pg_temp'
as $function$
declare r record;v_release integer;
begin
  for r in
    select wce.cutting_group_id,wcl.work_component_id,
           coalesce(sum(pwi.qty_payable),0)::integer allocated_qty
    from erp.payroll_work_items pwi
    join erp.payroll_settlements ps on ps.id=pwi.payroll_id and ps.status<>'REVERSED'
    join erp.work_completion_lines wcl on pwi.source_type='PRODUCTION' and wcl.id=pwi.source_id
    join erp.work_completion_events wce on wce.id=wcl.completion_id
    where wce.cutting_group_id in(
      select ldl.cutting_group_id
      from erp.laundry_receipt_lines lrl
      join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
      where lrl.receipt_id=p_receipt_id
    )
    group by wce.cutting_group_id,wcl.work_component_id
  loop
    select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0)::integer
      into v_release
    from erp.laundry_receipt_lines lrl
    join erp.laundry_receipts lr on lr.id=lrl.receipt_id and lr.status='POSTED'
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    where ldl.cutting_group_id=r.cutting_group_id and lr.id<>p_receipt_id;
    if r.allocated_qty>v_release then
      raise exception 'Laundry receipt reversal would retract payroll eligibility below allocated Nota qty for Potongan/component; reverse affected Nota first';
    end if;
  end loop;
end;
$function$;

comment on function erp.assert_laundry_receipt_reversal_payroll_safe(uuid) is null;

create or replace function erp.run_v263a_payroll_integrity_checks()
returns table(check_name text,severity text,issue_count bigint,details text)
language sql
stable
security definer
set search_path to 'erp','public','pg_temp'
as $function$
  select
    'production_payroll_exceeds_laundry_release','CRITICAL',count(*)::bigint,
    'Allocated production payroll qty must not exceed physical laundry-return eligibility'
  from erp.v_payroll_production_work_eligibility e
  where e.allocated_to_nonreversed_payroll_qty>e.eligible_after_laundry_qty

  union all
  select
    'rework_payroll_before_case_resolution','CRITICAL',count(*)::bigint,
    'Rework Nota lines require COMPLETED+cost_posted rework and a RESOLVED BS case'
  from erp.payroll_work_items pwi
  join erp.payroll_settlements ps on ps.id=pwi.payroll_id and ps.status<>'REVERSED'
  join erp.rework_component_lines rcl on pwi.source_type='REWORK' and rcl.id=pwi.source_id
  join erp.rework_orders ro on ro.id=rcl.rework_order_id
  join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
  join erp.bs_cases bc on bc.id=bcc.bs_case_id
  where ro.status<>'COMPLETED' or not ro.cost_posted or bc.status<>'RESOLVED'

  union all
  select
    'payroll_work_wrong_contractor','CRITICAL',count(*)::bigint,
    'Every Nota work line must belong to the Nota Mandor'
  from erp.payroll_work_items pwi
  join erp.payroll_settlements ps on ps.id=pwi.payroll_id
  left join erp.work_completion_lines wcl on pwi.source_type='PRODUCTION' and wcl.id=pwi.source_id
  left join erp.work_completion_events wce on wce.id=wcl.completion_id
  left join erp.rework_component_lines rcl on pwi.source_type='REWORK' and rcl.id=pwi.source_id
  left join erp.rework_orders ro on ro.id=rcl.rework_order_id
  where ps.status<>'REVERSED'
    and ps.contractor_id is distinct from coalesce(wce.contractor_id,ro.contractor_id);
$function$;

comment on function erp.run_v263a_payroll_integrity_checks() is null;

do $verification$
declare
  v_view text:=pg_get_viewdef('erp.v_payroll_production_work_eligibility'::regclass,true);
  v_guard text:=pg_get_functiondef('erp.assert_laundry_receipt_reversal_payroll_safe(uuid)'::regprocedure);
  v_checks text:=pg_get_functiondef('erp.run_v263a_payroll_integrity_checks()'::regprocedure);
begin
  if position('cumulative_component_qty' in v_view)=0
     or position('laundry_returned_qty' in v_view)=0
     or position('r.allocated_qty>v_release' in v_guard)=0
     or position('production_payroll_exceeds_laundry_release' in v_checks)=0
     or not exists (
       select 1 from pg_class c
       where c.oid='erp.v_payroll_production_work_eligibility'::regclass
         and 'security_invoker=true'=any(coalesce(c.reloptions,array[]::text[]))
     ) then
    raise exception 'PAYROLL_COMPONENT_ENTITLEMENT_ROLLBACK_VERIFY_FAILED';
  end if;
end
$verification$;
