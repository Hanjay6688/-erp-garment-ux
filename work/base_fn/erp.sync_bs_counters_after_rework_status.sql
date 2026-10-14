-- bootstrap lines 24552-24565
CREATE OR REPLACE FUNCTION erp.sync_bs_counters_after_rework_status()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
begin
  if old.status is distinct from new.status then perform erp.rebuild_bs_component_counters(new.bs_case_id); end if;
  return new;
end;
$function$;

alter function "erp"."sync_bs_counters_after_rework_status"() owner to "postgres";
