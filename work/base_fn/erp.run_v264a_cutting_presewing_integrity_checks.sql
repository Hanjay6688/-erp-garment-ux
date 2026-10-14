-- bootstrap lines 27264-27336
CREATE OR REPLACE FUNCTION erp.run_v264a_cutting_presewing_integrity_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
AS $function$
  select
    'duplicate_material_movement_reversal', 'CRITICAL', count(*)::bigint,
    'A material movement may have at most one reversal'
  from (
    select reversal_of_id
    from erp.material_stock_movements
    where reversal_of_id is not null
    group by reversal_of_id having count(*) > 1
  ) bad

  union all
  select
    'cutting_issue_flag_without_active_movement', 'CRITICAL', count(*)::bigint,
    'material_issue_posted requires an active CUTTING_GROUP movement'
  from erp.cutting_groups cg
  where cg.material_issue_posted
    and not exists (
      select 1 from erp.material_stock_movements m
      where m.source_type = 'CUTTING_GROUP' and m.source_id = cg.id
        and not exists (
          select 1 from erp.material_stock_movements rv where rv.reversal_of_id = m.id
        )
    )

  union all
  select
    'active_cutting_issue_without_flag', 'CRITICAL', count(*)::bigint,
    'An active CUTTING_GROUP movement requires material_issue_posted=true'
  from erp.cutting_groups cg
  where not cg.material_issue_posted
    and exists (
      select 1 from erp.material_stock_movements m
      where m.source_type = 'CUTTING_GROUP' and m.source_id = cg.id
        and not exists (
          select 1 from erp.material_stock_movements rv where rv.reversal_of_id = m.id
        )
    )

  union all
  select
    'cutting_return_flag_without_active_movement', 'CRITICAL', count(*)::bigint,
    'material_return_posted requires an active CUTTING_GROUP_RETURN movement when returned qty exists'
  from erp.cutting_groups cg
  where cg.material_return_posted
    and exists (
      select 1 from erp.cutting_group_rolls cgr
      where cgr.cutting_group_id = cg.id and cgr.qty_physically_returned > 0
    )
    and not exists (
      select 1 from erp.material_stock_movements m
      where m.source_type = 'CUTTING_GROUP_RETURN' and m.source_id = cg.id
        and not exists (
          select 1 from erp.material_stock_movements rv where rv.reversal_of_id = m.id
        )
    )

  union all
  select
    'presewing_reversal_without_reason', 'ERROR', count(*)::bigint,
    'Every pre-sewing stock reversal must retain a reason in its append-only row'
  from erp.material_stock_movements m
  where m.source_type = 'CUTTING_PRESEWING_REVERSAL'
    and nullif(btrim(m.note), '') is null;
$function$;

alter function "erp"."run_v264a_cutting_presewing_integrity_checks"() owner to "postgres";
