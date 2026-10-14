-- bootstrap lines 29091-29118
CREATE OR REPLACE FUNCTION erp.is_cutting_group_presewing_reversible(p_cutting_group_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
  select coalesce((
    select
      cg.status in ('CUT','PICKED_UP')
      and not cg.material_issue_posted
      and not cg.material_return_posted
      and not exists (
        select 1 from erp.material_stock_movements m
        where m.source_id = cg.id
          and m.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN')
          and not exists (
            select 1 from erp.material_stock_movements rv
            where rv.reversal_of_id = m.id
          )
      )
      and not erp.cutting_group_has_downstream_after_pickup(cg.id)
    from erp.cutting_groups cg
    where cg.id = p_cutting_group_id
  ), false);
$function$;

alter function "erp"."is_cutting_group_presewing_reversible"(p_cutting_group_id uuid) owner to "postgres";
