CREATE OR REPLACE FUNCTION erp.account_id(p_mapping_key text)
 RETURNS uuid
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$ DECLARE v_id uuid; BEGIN PERFORM erp.require_internal();SELECT account_id INTO v_id FROM erp.accounting_account_mappings WHERE mapping_key=p_mapping_key; IF v_id IS NULL THEN RAISE EXCEPTION 'Accounting mapping % is not configured',p_mapping_key; END IF;RETURN v_id;END; $function$;
