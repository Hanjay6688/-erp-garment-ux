-- bootstrap lines 9545-9565
CREATE OR REPLACE FUNCTION erp.guard_laundry_claim_resolution()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  if current_user in ('postgres','service_role','supabase_admin') then if tg_op='DELETE' then return old; else return new; end if; end if;
  if tg_op='DELETE' then
    if old.status in ('SETTLED','WRITTEN_OFF') then raise exception 'Resolved laundry claim cannot be deleted directly'; end if;
    return old;
  end if;
  if old.status in ('SETTLED','WRITTEN_OFF') then raise exception 'Resolved laundry claim is frozen'; end if;
  if new.status in ('SETTLED','WRITTEN_OFF') and new.status is distinct from old.status then
    raise exception 'Use resolve_laundry_claim() for final claim settlement/write-off';
  end if;
  return new;
end;
$function$;

alter function "erp"."guard_laundry_claim_resolution"() owner to "postgres";
