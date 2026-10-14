-- bootstrap lines 9973-10008
CREATE OR REPLACE FUNCTION erp.guard_material_negative_stock()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare v_available numeric(24,6);
begin
  if new.qty_signed>=0 then return new; end if;
  if new.location_id is null then raise exception 'Material OUT movement requires location_id'; end if;

  perform pg_advisory_xact_lock(hashtextextended(
    'MATSTOCK|'||new.material_id::text||'|'||coalesce(new.roll_id::text,'NO_ROLL')||'|'||new.location_id::text,0
  ));

  if new.source_type='MATERIAL_PURCHASE_REVERSAL'
     and current_setting('erp.allow_source_replacement_negative',true)='on' then
    return new;
  end if;

  if new.roll_id is not null then
    select coalesce(sum(qty_signed),0) into v_available from erp.material_stock_movements
    where material_id=new.material_id and roll_id=new.roll_id and location_id=new.location_id;
  else
    select coalesce(sum(qty_signed),0) into v_available from erp.material_stock_movements
    where material_id=new.material_id and roll_id is null and location_id=new.location_id;
  end if;
  if v_available+new.qty_signed < -0.000001 then
    raise exception 'Material stock would become negative at selected location/roll. Available %, requested out %',v_available,abs(new.qty_signed);
  end if;
  return new;
end;
$function$;

alter function "erp"."guard_material_negative_stock"() owner to "postgres";
