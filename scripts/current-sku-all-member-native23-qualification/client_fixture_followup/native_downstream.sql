CREATE OR REPLACE FUNCTION erp.fg_lot_has_active_downstream(p_lot_id uuid, p_origin_movement_type text, p_origin_source_type text, p_origin_source_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE
 SET search_path TO 'erp', 'public'
AS $function$
  select exists(
    select 1
    from erp.fg_stock_movements fm
    where fm.lot_id=p_lot_id
      and fm.movement_type<>'REVERSAL'
      and not (
        fm.movement_type=p_origin_movement_type
        and fm.source_type=p_origin_source_type
        and fm.source_id=p_origin_source_id
      )
      and not exists(
        select 1 from erp.fg_stock_movements rv
        where rv.reversal_of_id=fm.id
      )
  );
$function$
