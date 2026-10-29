CREATE OR REPLACE FUNCTION erp.guard_used_accessory_bom_version()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$ DECLARE v_last_basis timestamptz; BEGIN v_last_basis:=erp.accessory_bom_last_committed_at(OLD.id); IF v_last_basis IS NULL THEN IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF; END IF; IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Financially committed accessory BOM version cannot be deleted'; END IF; IF NEW.product_id IS DISTINCT FROM OLD.product_id OR NEW.effective_from IS DISTINCT FROM OLD.effective_from OR NEW.is_active IS DISTINCT FROM OLD.is_active THEN RAISE EXCEPTION 'Committed accessory BOM identity/start/active flag is immutable; close it after commitment and create a successor version'; END IF; IF NEW.effective_to IS NOT NULL AND NEW.effective_to<=v_last_basis THEN RAISE EXCEPTION 'Accessory BOM effective_to cannot precede/equal its financial commitment time'; END IF;RETURN NEW;END; $function$;
