-- bootstrap lines 10845-10868
CREATE OR REPLACE FUNCTION erp.guard_rework_posted_state()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
BEGIN
  IF current_user IN ('postgres','service_role','supabase_admin') THEN IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF; END IF;
  IF TG_OP='INSERT' THEN
    IF COALESCE(NEW.cost_posted,false) OR NEW.good_fg_lot_id IS NOT NULL THEN RAISE EXCEPTION 'Rework posting fields are system-managed'; END IF;
    RETURN NEW;
  END IF;
  IF TG_OP='DELETE' THEN
    IF OLD.cost_posted THEN RAISE EXCEPTION 'Posted rework cannot be deleted directly'; END IF;
    RETURN OLD;
  END IF;
  IF OLD.cost_posted THEN RAISE EXCEPTION 'Posted rework is frozen; use controlled correction/reversal'; END IF;
  IF NEW.cost_posted IS DISTINCT FROM OLD.cost_posted OR NEW.good_fg_lot_id IS DISTINCT FROM OLD.good_fg_lot_id THEN
    RAISE EXCEPTION 'Rework cost/FG posting fields are system-managed';
  END IF;
  RETURN NEW;
END;$function$;

alter function "erp"."guard_rework_posted_state"() owner to "postgres";
