-- bootstrap lines 11614-11636
CREATE OR REPLACE FUNCTION erp.lock_current_hpp_per_pcs(p_lot_id uuid)
 RETURNS numeric
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_hpp numeric(20,6);
begin
  perform erp.require_internal();
  select hv.hpp_per_pcs
    into v_hpp
  from erp.hpp_versions hv
  where hv.lot_id=p_lot_id and hv.is_current=true
  order by hv.version_no desc
  limit 1
  for share;
  return v_hpp;
end;
$function$;

alter function "erp"."lock_current_hpp_per_pcs"(p_lot_id uuid) owner to "postgres";
