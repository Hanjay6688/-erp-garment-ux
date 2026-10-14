-- bootstrap lines 25557-25575
CREATE OR REPLACE FUNCTION erp.validate_material_stock_movement_lineage()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  if new.location_id is null then raise exception 'Material stock movement requires a location'; end if;
  if not exists (select 1 from erp.locations l where l.id=new.location_id and l.is_active=true and l.location_type='RAW_MATERIAL_WAREHOUSE') then
    raise exception 'Material stock movement location must be an active raw-material warehouse';
  end if;
  if new.roll_id is not null and not exists (select 1 from erp.material_rolls mr where mr.id=new.roll_id and mr.material_id=new.material_id) then
    raise exception 'Material movement roll does not belong to the selected material';
  end if;
  return new;
end;
$function$;

alter function "erp"."validate_material_stock_movement_lineage"() owner to "postgres";
