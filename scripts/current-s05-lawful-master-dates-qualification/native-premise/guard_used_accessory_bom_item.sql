CREATE OR REPLACE FUNCTION erp.guard_used_accessory_bom_item()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$ DECLARE v_id uuid;v_bom uuid; BEGIN v_id:=CASE WHEN TG_OP='DELETE' THEN OLD.id ELSE NEW.id END;SELECT bom_version_id INTO v_bom FROM erp.accessory_bom_items WHERE id=v_id; IF EXISTS (SELECT 1 FROM erp.fg_accessory_cost_snapshots WHERE bom_item_id=v_id) OR EXISTS (SELECT 1 FROM erp.po_accessory_bom_commitments WHERE bom_version_id=v_bom) THEN RAISE EXCEPTION 'Accessory BOM item is financially committed by a PO/SKU; create a new effective-dated BOM version instead'; END IF; IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;END; $function$;
