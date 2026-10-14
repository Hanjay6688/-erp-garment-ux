-- bootstrap lines 26612-26657
CREATE OR REPLACE FUNCTION erp.cutting_group_has_downstream_after_pickup(p_cutting_group_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
  select
       exists(select 1 from erp.wip_stage_events w where w.cutting_group_id = p_cutting_group_id)
    or exists(
      select 1 from erp.work_completion_events w
      where w.cutting_group_id = p_cutting_group_id and w.status <> 'DRAFT'
    )
    or exists(
      select 1
      from erp.laundry_delivery_lines ldl
      join erp.laundry_deliveries ld on ld.id = ldl.delivery_id
      where ldl.cutting_group_id = p_cutting_group_id
        and ld.status not in ('DRAFT','REVERSED')
    )
    or exists(
      select 1
      from erp.qc_inspection_items qi
      join erp.qc_inspections qh on qh.id = qi.inspection_id
      where qi.cutting_group_id = p_cutting_group_id and qh.status <> 'DRAFT'
    )
    or exists(
      select 1 from erp.fg_lots f
      where f.cutting_group_id = p_cutting_group_id
        and f.lot_origin <> 'VOIDED_PRODUCTION'
    )
    or exists(
      select 1 from erp.bs_cases b
      where b.cutting_group_id = p_cutting_group_id and b.status <> 'CANCELLED'
    )
    or exists(
      select 1 from erp.scrap_batches s
      where s.source_cutting_group_id = p_cutting_group_id
    )
    or exists(
      select 1 from erp.cutting_qty_correction_lines c
      where c.cutting_group_id = p_cutting_group_id
    );
$function$;

alter function "erp"."cutting_group_has_downstream_after_pickup"(p_cutting_group_id uuid) owner to "postgres";
