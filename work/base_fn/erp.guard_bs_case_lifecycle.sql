-- bootstrap lines 8982-9012
CREATE OR REPLACE FUNCTION erp.guard_bs_case_lifecycle()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  if current_user in ('postgres','service_role','supabase_admin') then
    if tg_op='DELETE' then return old; else return new; end if;
  end if;
  if tg_op='INSERT' then
    new.status:='OPEN';
    return new;
  end if;
  if tg_op='DELETE' then
    raise exception 'BS case cannot be deleted directly; use controlled correction/resolution flow';
  end if;
  if new.status is distinct from old.status then raise exception 'BS status is system-managed by rework/resolution posting'; end if;
  if new.qty_pcs is distinct from old.qty_pcs
     or new.po_id is distinct from old.po_id
     or new.cutting_group_id is distinct from old.cutting_group_id
     or new.qc_item_id is distinct from old.qc_item_id
     or new.product_id is distinct from old.product_id
     or new.detected_at_stage is distinct from old.detected_at_stage
     or new.physical_at is distinct from old.physical_at then
    raise exception 'BS quantity/lineage is immutable; use controlled correction flow';
  end if;
  return new;
end;$function$;

alter function "erp"."guard_bs_case_lifecycle"() owner to "postgres";
