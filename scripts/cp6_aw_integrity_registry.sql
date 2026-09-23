CREATE OR REPLACE FUNCTION erp.period_integrity_check_registry_v1()
 RETURNS TABLE(check_name text, check_class text, dated_by text)
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO ''
AS $function$
-- P-03: class of every CRITICAL/ERROR current-state check the close engine reads. DATED_EQUIVALENT means a dated
-- detector of the engine necessarily fires whenever this check fails; the engine then reports the check as INFO and
-- lets the detector scope it by date, but only after the detector confirms it at run time. Every other class blocks
-- every date until the owner decides otherwise; a name missing here is UNCLASSIFIED and blocks too (fail closed).
select x.check_name,x.check_class,x.dated_by from (values
  ('NEGATIVE_FG_BALANCE','DATED_EQUIVALENT','FG_QTY_NEGATIVE_ASOF'),
  ('NEGATIVE_MATERIAL_LOCATION_BALANCE','DATED_EQUIVALENT','MATERIAL_QTY_NEGATIVE_ASOF')
) x(check_name,check_class,dated_by)
$function$
