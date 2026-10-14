-- bootstrap lines 6601-6609
CREATE OR REPLACE FUNCTION erp.apply_rework_component_entitlement()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$ BEGIN UPDATE erp.bs_case_components SET lifetime_newly_completed_qty=lifetime_newly_completed_qty+NEW.qty_newly_payable WHERE id=NEW.bs_case_component_id;RETURN NEW; END; $function$;

alter function "erp"."apply_rework_component_entitlement"() owner to "postgres";
