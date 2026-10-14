-- bootstrap lines 15470-15558
CREATE OR REPLACE FUNCTION erp.prepare_rework_component_line()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_order erp.rework_orders%rowtype;
  v_case erp.bs_cases%rowtype;
  v_component erp.bs_case_components%rowtype;
  v_model uuid;
  v_original_contractor uuid;
  v_rate_id uuid;
  v_rate numeric(18,2);
  v_po_snapshot uuid;
  v_remaining integer;
begin
  select * into v_order from erp.rework_orders where id=new.rework_order_id for update;
  if v_order.id is null then raise exception 'Rework order not found'; end if;
  if v_order.status not in('OPEN','IN_PROGRESS','PARTIAL') or v_order.cost_posted then
    raise exception 'Rework component lines are editable only before completion/cost posting';
  end if;
  select * into v_component from erp.bs_case_components where id=new.bs_case_component_id for update;
  if v_component.id is null then raise exception 'BS component not found'; end if;
  if v_component.bs_case_id<>v_order.bs_case_id then
    raise exception 'Rework component belongs to a different BS case';
  end if;
  select * into v_case from erp.bs_cases where id=v_order.bs_case_id;
  if new.qty_performed>v_order.qty_sent then
    raise exception 'Rework component qty performed % exceeds rework qty sent %',new.qty_performed,v_order.qty_sent;
  end if;
  v_remaining:=greatest(
    v_case.qty_pcs-v_component.completed_before_bs_qty-v_component.lifetime_newly_completed_qty,0
  );
  new.qty_newly_payable:=least(new.qty_performed,v_remaining);
  new.source_contractor_rate_id:=null;
  new.source_po_component_snapshot_id:=null;

  if v_order.destination_type='LAUNDRY' then
    new.rate_snapshot:=0;
    new.rate_basis:='LAUNDRY_ZERO';
    return new;
  end if;

  select coalesce(po.model_id,p.model_id),coalesce(po.contractor_id,v_case.responsible_contractor_id)
  into v_model,v_original_contractor
  from erp.bs_cases bc
  left join erp.production_orders po on po.id=bc.po_id
  left join erp.products p on p.id=bc.product_id
  where bc.id=v_case.id;
  if v_model is null then
    raise exception 'Contractor rework requires PO or product model lineage for server-side rate resolution';
  end if;

  select r.id,r.rate_per_pcs into v_rate_id,v_rate
  from erp.contractor_work_rates r
  where r.contractor_id=v_order.contractor_id
    and r.model_id=v_model
    and r.work_component_id=v_component.work_component_id
    and r.effective_from<=v_order.physical_sent_at
    and (r.effective_to is null or r.effective_to>v_order.physical_sent_at)
  order by r.effective_from desc,r.id desc limit 1;

  if v_rate_id is not null then
    new.rate_snapshot:=v_rate;
    new.source_contractor_rate_id:=v_rate_id;
    new.rate_basis:='CONTRACTOR_RATE';
    return new;
  end if;

  if v_order.contractor_id is distinct from v_original_contractor then
    raise exception 'Cross-Mandor rework requires an explicit effective contractor rate for this model/component';
  end if;
  select s.id,s.rate_per_pcs_snapshot into v_po_snapshot,v_rate
  from erp.po_work_component_snapshots s
  where s.po_id=v_case.po_id and s.work_component_id=v_component.work_component_id
  order by s.committed_at desc,s.id desc limit 1;
  if v_po_snapshot is null then
    raise exception 'No effective contractor rate or PO component snapshot exists for rework pricing';
  end if;
  new.rate_snapshot:=v_rate;
  new.source_po_component_snapshot_id:=v_po_snapshot;
  new.rate_basis:='PO_SNAPSHOT';
  return new;
end;
$function$;

alter function "erp"."prepare_rework_component_line"() owner to "postgres";
