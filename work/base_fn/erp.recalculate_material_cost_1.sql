-- bootstrap lines 16174-16186
CREATE OR REPLACE FUNCTION erp.recalculate_material_cost(p_material_id uuid, p_recalc_from timestamp with time zone)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
begin
  perform erp._recalculate_material_cost_core(p_material_id,p_recalc_from,true);
end;
$function$;

alter function "erp"."recalculate_material_cost"(p_material_id uuid, p_recalc_from timestamp with time zone) owner to "postgres";
