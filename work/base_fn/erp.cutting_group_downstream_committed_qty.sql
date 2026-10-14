-- bootstrap lines 26552-26611
CREATE OR REPLACE FUNCTION erp.cutting_group_downstream_committed_qty(p_cutting_group_id uuid)
 RETURNS bigint
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
  select greatest(
    coalesce((
      select max(s.stage_qty)
      from (
        select w.stage_to, sum(coalesce(w.qty_pcs, 0))::bigint as stage_qty
        from erp.wip_stage_events w
        where w.cutting_group_id = p_cutting_group_id
          and w.stage_to in ('SEWING','LAUNDRY','QC','FINISHED','ON_HOLD')
        group by w.stage_to
      ) s
    ), 0),
    coalesce((
      select max(s.component_qty)
      from (
        select l.po_component_snapshot_id,
               sum(l.qty_completed)::bigint as component_qty
        from erp.work_completion_events h
        join erp.work_completion_lines l on l.completion_id = h.id
        where h.cutting_group_id = p_cutting_group_id
          and h.status = 'POSTED'
        group by l.po_component_snapshot_id
      ) s
    ), 0),
    coalesce((
      select sum(ldl.qty_sent_pcs)::bigint
      from erp.laundry_delivery_lines ldl
      join erp.laundry_deliveries ld on ld.id = ldl.delivery_id
      where ldl.cutting_group_id = p_cutting_group_id
        and ld.status not in ('DRAFT','REVERSED')
    ), 0),
    coalesce((
      select sum(qi.qty_good_pcs + qi.qty_bs_pcs)::bigint
      from erp.qc_inspection_items qi
      join erp.qc_inspections qh on qh.id = qi.inspection_id
      where qi.cutting_group_id = p_cutting_group_id
        and qh.status = 'POSTED'
    ), 0),
    coalesce((
      select sum(fl.initial_qty_pcs)::bigint
      from erp.fg_lots fl
      where fl.cutting_group_id = p_cutting_group_id
        and fl.lot_origin = 'PRODUCTION'
    ), 0),
    coalesce((
      select sum(b.qty_pcs)::bigint
      from erp.bs_cases b
      where b.cutting_group_id = p_cutting_group_id
        and b.status <> 'CANCELLED'
    ), 0)
  );
$function$;

alter function "erp"."cutting_group_downstream_committed_qty"(p_cutting_group_id uuid) owner to "postgres";
