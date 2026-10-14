-- bootstrap lines 9216-9231
CREATE OR REPLACE FUNCTION erp.guard_cutting_group_delete_after_use()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  if current_user in ('postgres','service_role','supabase_admin') then return old; end if;
  if not erp.is_cutting_group_presewing_reversible(old.id) then
    raise exception 'Potongan sudah memiliki jahitan/transaksi fisik/biaya/downstream dan tidak boleh dihapus. Gunakan koreksi/reversal.';
  end if;
  return old;
end;
$function$;

alter function "erp"."guard_cutting_group_delete_after_use"() owner to "postgres";
