-- bootstrap lines 16958-16965
CREATE OR REPLACE FUNCTION erp.require_rework_cost_before_payroll()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$ DECLARE v_posted boolean; BEGIN IF NEW.source_type='REWORK' THEN SELECT ro.cost_posted INTO v_posted FROM erp.rework_component_lines rcl JOIN erp.rework_orders ro ON ro.id=rcl.rework_order_id WHERE rcl.id=NEW.source_id; IF COALESCE(v_posted,false)=false THEN RAISE EXCEPTION 'Rework cost must be posted before it can enter payroll'; END IF; END IF;RETURN NEW;END; $function$;

alter function "erp"."require_rework_cost_before_payroll"() owner to "postgres";
