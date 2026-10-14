-- bootstrap lines 25721-25783
CREATE OR REPLACE FUNCTION erp.validate_payroll_work_item_source()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_source_qty integer;
  v_source_component uuid;
  v_source_po uuid;
  v_source_contractor uuid;
  v_payroll_contractor uuid;
  v_already integer;
begin
  perform pg_advisory_xact_lock(hashtextextended(
    'PAYWORK|'||new.source_type||'|'||new.source_id::text||'|'||new.work_component_id::text,0
  ));
  select contractor_id into v_payroll_contractor
  from erp.payroll_settlements where id=new.payroll_id;

  if new.source_type='PRODUCTION' then
    select eligible_after_laundry_qty,work_component_id,po_id,contractor_id
    into v_source_qty,v_source_component,v_source_po,v_source_contractor
    from erp.v_payroll_production_work_eligibility
    where source_id=new.source_id;
  elsif new.source_type='REWORK' then
    select rcl.qty_newly_payable,bcc.work_component_id,bc.po_id,ro.contractor_id
    into v_source_qty,v_source_component,v_source_po,v_source_contractor
    from erp.rework_component_lines rcl
    join erp.bs_case_components bcc on bcc.id=rcl.bs_case_component_id
    join erp.bs_cases bc on bc.id=bcc.bs_case_id
    join erp.rework_orders ro on ro.id=rcl.rework_order_id
    where rcl.id=new.source_id
      and ro.destination_type='CONTRACTOR'
      and ro.status='COMPLETED'
      and ro.cost_posted
      and bc.status='RESOLVED';
  else
    raise exception 'Payroll source_type must be PRODUCTION or REWORK';
  end if;

  if v_source_qty is null then raise exception 'Payroll source is not currently eligible'; end if;
  if new.work_component_id<>v_source_component then raise exception 'Payroll work component does not match source'; end if;
  if new.po_id is distinct from v_source_po then raise exception 'Payroll PO does not match source'; end if;
  if v_source_contractor is not null and v_payroll_contractor<>v_source_contractor then
    raise exception 'Payroll contractor does not match work source';
  end if;

  select coalesce(sum(pwi.qty_payable),0) into v_already
  from erp.payroll_work_items pwi
  join erp.payroll_settlements ps on ps.id=pwi.payroll_id
  where pwi.source_type=new.source_type and pwi.source_id=new.source_id
    and pwi.work_component_id=new.work_component_id and pwi.id<>new.id
    and ps.status<>'REVERSED';
  if v_already+new.qty_payable>v_source_qty then
    raise exception 'Payroll would overpay/early-pay work source. Eligible %, already %, new %',
      v_source_qty,v_already,new.qty_payable;
  end if;
  return new;
end;
$function$;

alter function "erp"."validate_payroll_work_item_source"() owner to "postgres";
