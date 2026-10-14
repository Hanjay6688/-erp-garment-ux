-- bootstrap lines 15870-16123
CREATE OR REPLACE FUNCTION erp.rebuild_po_hpp(p_po_id uuid, p_reason text DEFAULT 'Recalculate HPP'::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_material numeric(24,6):=0;
  v_material_allocated numeric(24,6):=0;
  v_contractor_material numeric(24,6):=0;
  v_accessory numeric(24,6):=0;
  v_labor numeric(24,6):=0;
  v_commission numeric(24,6):=0;
  v_laundry numeric(24,6):=0;
  v_rework numeric(24,6):=0;
  v_other numeric(24,6):=0;
  v_attendance_hpp numeric(24,6):=0;
  v_shared_attendance_hpp numeric(24,6):=0;
  v_shared_labor numeric(24,6):=0;
  v_shared_commission numeric(24,6):=0;
  v_shared_rework numeric(24,6):=0;
  v_shared_other numeric(24,6):=0;
  v_total_current numeric(24,6):=0;
  v_total_qty integer:=0;
  v_pending boolean:=false;
  r record;
  c record;
  v_old_id uuid;
  v_new_id uuid;
  v_version integer;
  v_lot_accessory numeric(24,6);
  v_lot_cost numeric(24,6);
  v_lot_material numeric(24,6);
  v_pool_material numeric(24,6);
  v_pool_qty numeric(24,6);
  v_batch_id uuid;
  v_state varchar(20);
  v_group_fg_qty numeric(24,6);
  v_group_labor numeric(24,6);
  v_group_commission numeric(24,6);
  v_group_laundry numeric(24,6);
  v_group_rework numeric(24,6);
  v_group_attendance_hpp numeric(24,6);
  v_lot_attendance_hpp numeric(24,6);
  v_lot_labor numeric(24,6);
  v_lot_commission numeric(24,6);
  v_lot_laundry numeric(24,6);
  v_lot_rework numeric(24,6);
  v_lot_other numeric(24,6);
begin
  perform erp.require_internal();
  -- Serialize all HPP rebuilds for the same PO (cron recost, late invoice, QC, reversal).
  perform pg_advisory_xact_lock(hashtextextended('PO_HPP:'||p_po_id::text,0));

  select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_material
  from erp.material_stock_movements msm
  where (msm.source_type='CUTTING_GROUP' and msm.source_id in (select id from erp.cutting_groups where po_id=p_po_id))
     or (msm.source_type='CUTTING_GROUP_RETURN' and msm.source_id in (select id from erp.cutting_groups where po_id=p_po_id));

  select coalesce(sum(cmii.qty*cmii.unit_cost_snapshot),0) into v_contractor_material
  from erp.contractor_material_issue_items cmii
  join erp.contractor_material_issues cmi on cmi.id=cmii.issue_id
  join erp.materials m on m.id=cmii.material_id
  where cmi.po_id=p_po_id and cmi.status='POSTED' and m.material_type<>'ACCESSORY';

  select
    coalesce(sum(case when wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wce.cutting_group_id is null and wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wce.cutting_group_id is null and wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0)
  into v_commission,v_labor,v_shared_commission,v_shared_labor
  from erp.work_completion_lines wcl
  join erp.work_completion_events wce on wce.id=wcl.completion_id
  join erp.work_components wc on wc.id=wcl.work_component_id
  where wce.po_id=p_po_id and wce.status='POSTED';

  with dl as (
    select ldl.id,ldl.cutting_group_id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot,
           coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then lrl.qty_good_received+lrl.qty_bs_laundry else 0 end),0) as qty_costed_actual,
           coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0) else 0 end),0) as actual_cost,
           bool_or(lr.status='POSTED' and lrl.actual_cost_status='PENDING') as has_pending_receipt
    from erp.laundry_delivery_lines ldl
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    left join erp.laundry_receipt_lines lrl on lrl.delivery_line_id=ldl.id
    left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where ld.po_id=p_po_id and ld.status<>'REVERSED'
    group by ldl.id,ldl.cutting_group_id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot
  )
  select coalesce(sum(actual_cost+greatest(qty_sent_pcs-qty_costed_actual,0)*coalesce(estimated_rate_snapshot,0)),0),
         coalesce(bool_or(has_pending_receipt or (qty_sent_pcs>qty_costed_actual and estimated_rate_snapshot is null)),false)
  into v_laundry,v_pending from dl;

  select coalesce(sum(rcl.amount_payable),0),
         coalesce(sum(case when bc.cutting_group_id is null then rcl.amount_payable else 0 end),0)
  into v_rework,v_shared_rework
  from erp.rework_component_lines rcl
  join erp.rework_orders ro on ro.id=rcl.rework_order_id
  join erp.bs_cases bc on bc.id=ro.bs_case_id
  where bc.po_id=p_po_id and ro.status<>'CANCELLED' and coalesce(ro.cost_posted,false)=true;

  select coalesce(sum(adjustment_amount),0),coalesce(sum(case when lot_id is null then adjustment_amount else 0 end),0)
  into v_other,v_shared_other
  from erp.cost_adjustments
  where po_id=p_po_id and component_type='OTHER';

  select
    coalesce(sum(a.allocated_amount),0),
    coalesce(sum(case when a.cutting_group_id is null then a.allocated_amount else 0 end),0)
  into v_attendance_hpp,v_shared_attendance_hpp
  from erp.attendance_hpp_pool_allocations a
  join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
  where a.po_id=p_po_id;

  select coalesce(sum(initial_qty_pcs),0) into v_total_qty
  from erp.fg_lots where po_id=p_po_id and lot_origin='PRODUCTION';
  if v_total_qty<=0 then return; end if;

  for r in select id from erp.fg_lots where po_id=p_po_id and lot_origin='PRODUCTION' order by produced_at,id
  loop perform erp.ensure_fg_accessory_cost_snapshot(r.id); end loop;

  select coalesce(sum(facs.total_hpp_cost),0) into v_accessory
  from erp.fg_accessory_cost_snapshots facs join erp.fg_lots fl on fl.id=facs.lot_id
  where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION';

  v_state:=case when v_pending then 'ESTIMATED' when exists (select 1 from erp.cost_adjustments where po_id=p_po_id) then 'ADJUSTED' else 'ACTUAL' end;

  for r in
    select fl.*,coalesce(fl.cutting_group_id,qi.cutting_group_id) as lineage_group_id
    from erp.fg_lots fl left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
    where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
    order by fl.produced_at,fl.id
  loop
    v_lot_material:=0;v_pool_material:=0;v_pool_qty:=0;v_batch_id:=null;
    v_group_fg_qty:=0;v_group_labor:=0;v_group_commission:=0;v_group_laundry:=0;v_group_rework:=0;v_group_attendance_hpp:=0;

    if r.lineage_group_id is not null then
      select cutting_batch_id into v_batch_id from erp.cutting_groups where id=r.lineage_group_id;
      if v_batch_id is not null then
        select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_pool_material
        from erp.material_stock_movements msm
        where (msm.source_type='CUTTING_GROUP' and msm.source_id in (select id from erp.cutting_groups where cutting_batch_id=v_batch_id))
           or (msm.source_type='CUTTING_GROUP_RETURN' and msm.source_id in (select id from erp.cutting_groups where cutting_batch_id=v_batch_id));
        select effective_pcs::numeric into v_pool_qty from erp.v_cutting_batch_totals where cutting_batch_id=v_batch_id;
      else
        select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_pool_material
        from erp.material_stock_movements msm
        where msm.source_id=r.lineage_group_id and msm.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN');
        select total_pcs::numeric into v_pool_qty from erp.v_cutting_group_totals where cutting_group_id=r.lineage_group_id;
      end if;

      select coalesce(sum(fl2.initial_qty_pcs),0)::numeric into v_group_fg_qty
      from erp.fg_lots fl2 where fl2.po_id=p_po_id and fl2.lot_origin='PRODUCTION' and fl2.cutting_group_id=r.lineage_group_id;

      select
        coalesce(sum(case when wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0),
        coalesce(sum(case when wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0)
      into v_group_labor,v_group_commission
      from erp.work_completion_lines wcl
      join erp.work_completion_events wce on wce.id=wcl.completion_id
      join erp.work_components wc on wc.id=wcl.work_component_id
      where wce.po_id=p_po_id and wce.status='POSTED' and wce.cutting_group_id=r.lineage_group_id;

      with dl as (
        select ldl.id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot,
               coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then lrl.qty_good_received+lrl.qty_bs_laundry else 0 end),0) as qty_costed_actual,
               coalesce(sum(case when lr.status='POSTED' and lrl.actual_cost_status in ('ESTIMATED','FINAL') then coalesce(lrl.actual_cost,0) else 0 end),0) as actual_cost
        from erp.laundry_delivery_lines ldl
        join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
        left join erp.laundry_receipt_lines lrl on lrl.delivery_line_id=ldl.id
        left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
        where ld.po_id=p_po_id and ld.status<>'REVERSED' and ldl.cutting_group_id=r.lineage_group_id
        group by ldl.id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot
      )
      select coalesce(sum(actual_cost+greatest(qty_sent_pcs-qty_costed_actual,0)*coalesce(estimated_rate_snapshot,0)),0)
      into v_group_laundry from dl;

      select coalesce(sum(rcl.amount_payable),0) into v_group_rework
      from erp.rework_component_lines rcl
      join erp.rework_orders ro on ro.id=rcl.rework_order_id
      join erp.bs_cases bc on bc.id=ro.bs_case_id
      where bc.po_id=p_po_id and bc.cutting_group_id=r.lineage_group_id and ro.status<>'CANCELLED' and coalesce(ro.cost_posted,false)=true;

      select coalesce(sum(a.allocated_amount),0) into v_group_attendance_hpp
      from erp.attendance_hpp_pool_allocations a
      join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
      where a.po_id=p_po_id and a.cutting_group_id=r.lineage_group_id;
    end if;

    if coalesce(v_pool_qty,0)>0 then v_lot_material:=v_pool_material*(r.initial_qty_pcs::numeric/v_pool_qty);
    else v_lot_material:=v_material*(r.initial_qty_pcs::numeric/v_total_qty::numeric); end if;
    v_lot_material:=v_lot_material+v_contractor_material*(r.initial_qty_pcs::numeric/v_total_qty::numeric);
    v_material_allocated:=v_material_allocated+v_lot_material;

    if coalesce(v_group_fg_qty,0)>0 then
      v_lot_labor:=v_group_labor*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_labor*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_commission:=v_group_commission*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_commission*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_laundry:=v_group_laundry*(r.initial_qty_pcs::numeric/v_group_fg_qty);
      v_lot_rework:=v_group_rework*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_rework*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_attendance_hpp:=v_group_attendance_hpp*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_attendance_hpp*(r.initial_qty_pcs::numeric/v_total_qty);
    else
      v_lot_labor:=v_labor*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_commission:=v_commission*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_laundry:=v_laundry*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_rework:=v_rework*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_attendance_hpp:=v_shared_attendance_hpp*(r.initial_qty_pcs::numeric/v_total_qty);
    end if;

    select coalesce(sum(total_hpp_cost),0) into v_lot_accessory from erp.fg_accessory_cost_snapshots where lot_id=r.id;
    select coalesce(sum(adjustment_amount),0) into v_lot_other from erp.cost_adjustments where lot_id=r.id and component_type='OTHER';
    v_lot_other:=v_lot_other+v_shared_other*(r.initial_qty_pcs::numeric/v_total_qty);
    v_lot_cost:=v_lot_material+v_lot_labor+v_lot_commission+v_lot_laundry+v_lot_rework+v_lot_attendance_hpp+v_lot_other+v_lot_accessory;
    v_total_current:=v_total_current+v_lot_cost;

    select id into v_old_id from erp.hpp_versions where lot_id=r.id and is_current=true order by version_no desc limit 1;
    select coalesce(max(version_no),0)+1 into v_version from erp.hpp_versions where lot_id=r.id;
    if v_old_id is not null then update erp.hpp_versions set is_current=false where id=v_old_id; end if;

    insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,supersedes_id,calculation_reason,created_by)
    values (r.id,v_version,v_state,r.initial_qty_pcs,v_lot_cost,true,v_old_id,p_reason,erp.current_app_user_id()) returning id into v_new_id;

    insert into erp.hpp_version_components(hpp_version_id,component_type,description,total_cost,source_type,source_id)
    values
      (v_new_id,'MATERIAL',case when v_batch_id is not null then 'Cutting material by effective batch yield + PO-shared non-accessory contractor material' else 'Cutting/legacy material pool + PO-shared non-accessory contractor material' end,v_lot_material,case when v_batch_id is not null then 'CUTTING_BATCH' else 'PO' end,coalesce(v_batch_id,p_po_id)),
      (v_new_id,'LABOR','Labor allocation: same cutting group + PO-shared fallback',v_lot_labor,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'COMMISSION','Commission allocation: same cutting group + PO-shared fallback',v_lot_commission,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'LAUNDRY','Laundry allocation from same cutting group; PENDING uses estimate',v_lot_laundry,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'REWORK','Rework allocation from same cutting group + legacy shared fallback',v_lot_rework,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'LABOR','Attendance HPP: ACTIVE pool allocation by immutable sewing lineage',v_lot_attendance_hpp,'ATTENDANCE_HPP_ACTIVE_ALLOCATION',coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'OTHER','Other/adjustment allocation',v_lot_other,'PO',p_po_id);

    for c in
      select facs.id,facs.total_hpp_cost,ac.category_name,facs.hpp_method
      from erp.fg_accessory_cost_snapshots facs join erp.accessory_categories ac on ac.id=facs.category_id
      where facs.lot_id=r.id order by ac.category_code
    loop
      insert into erp.hpp_version_components(hpp_version_id,component_type,description,total_cost,source_type,source_id)
      values (v_new_id,'ACCESSORY','Accessory category: '||c.category_name||' ['||c.hpp_method||']',c.total_hpp_cost,'FG_ACCESSORY_SNAPSHOT',c.id);
    end loop;

    update erp.fg_stock_movements set unit_hpp_snapshot=(select hpp_per_pcs from erp.hpp_versions where id=v_new_id)
    where lot_id=r.id and movement_type in ('QC_GOOD','REWORK_IN');
  end loop;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values ('production_orders',p_po_id,'RECALCULATE',jsonb_build_object(
    'material_total_issued',v_material+v_contractor_material,'cutting_material_total',v_material,'contractor_nonaccessory_material_total',v_contractor_material,'material_allocated_to_current_fg',v_material_allocated,'material_basis','CUTTING_BATCH_EFFECTIVE_YIELD_PLUS_PO_SHARED_CONTRACTOR_MATERIAL',
    'accessory',v_accessory,'labor',v_labor,'attendance_hpp',v_attendance_hpp,'commission',v_commission,'laundry',v_laundry,'rework',v_rework,'other',v_other,
    'total_current_fg_cost',v_total_current,'cost_state',v_state,'nonmaterial_basis','CUTTING_GROUP_LINEAGE_WITH_PO_SHARED_FALLBACK','accessory_basis','GOOD_FG_X_CATEGORY_BOM'),
    erp.current_app_user_id(),p_reason);
end;
$function$;

alter function "erp"."rebuild_po_hpp"(p_po_id uuid, p_reason text) owner to "postgres";
