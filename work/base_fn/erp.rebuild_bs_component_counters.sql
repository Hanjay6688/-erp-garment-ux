-- bootstrap lines 15817-15869
CREATE OR REPLACE FUNCTION erp.rebuild_bs_component_counters(p_bs_case_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  b erp.bs_cases%rowtype;
  c record;
  v_newly integer;
  v_paid_rework integer;
  v_prod_total integer;
  v_prod_paid integer;
  v_base_paid integer;
begin
  perform erp.require_internal();
  select * into b from erp.bs_cases where id=p_bs_case_id for update;
  if b.id is null then return; end if;

  for c in select * from erp.bs_case_components where bs_case_id=b.id for update
  loop
    select coalesce(sum(rcl.qty_newly_payable),0)::integer into v_newly
    from erp.rework_component_lines rcl
    join erp.rework_orders ro on ro.id=rcl.rework_order_id
    where rcl.bs_case_component_id=c.id and ro.status<>'CANCELLED';

    select coalesce(sum(pwi.qty_payable),0)::integer into v_paid_rework
    from erp.payroll_work_items pwi
    join erp.payroll_settlements ps on ps.id=pwi.payroll_id
    join erp.rework_component_lines rcl on rcl.id=pwi.source_id
    where pwi.source_type='REWORK' and rcl.bs_case_component_id=c.id and ps.status='PAID';

    select coalesce(sum(wcl.qty_payable),0)::integer into v_prod_total
    from erp.work_completion_lines wcl
    join erp.work_completion_events wce on wce.id=wcl.completion_id
    where wce.po_id=b.po_id and wcl.work_component_id=c.work_component_id and wce.status='POSTED';

    select coalesce(sum(pwi.qty_payable),0)::integer into v_prod_paid
    from erp.payroll_work_items pwi
    join erp.payroll_settlements ps on ps.id=pwi.payroll_id
    where pwi.source_type='PRODUCTION' and pwi.po_id=b.po_id and pwi.work_component_id=c.work_component_id and ps.status='PAID';

    v_base_paid:=case when v_prod_total>0 and v_prod_paid>=v_prod_total then c.completed_before_bs_qty else 0 end;
    update erp.bs_case_components
    set lifetime_newly_completed_qty=greatest(v_newly,0),
        lifetime_paid_qty=least(b.qty_pcs,greatest(v_base_paid,0)+greatest(v_paid_rework,0))
    where id=c.id;
  end loop;
end;
$function$;

alter function "erp"."rebuild_bs_component_counters"(p_bs_case_id uuid) owner to "postgres";
