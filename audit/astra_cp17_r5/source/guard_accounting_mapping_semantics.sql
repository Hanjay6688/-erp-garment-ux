CREATE OR REPLACE FUNCTION erp.guard_accounting_mapping_semantics()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare v_expected text;v_type text;v_active boolean;
begin
  if tg_op='DELETE' then
    v_expected:=erp.expected_mapping_account_type(old.mapping_key);
    if v_expected is not null then raise exception 'Core accounting mapping % tidak boleh dihapus. Pindahkan ke akun aktif dengan tipe % jika perlu.',old.mapping_key,v_expected; end if;
    return old;
  end if;
  if tg_op='UPDATE' and new.mapping_key is distinct from old.mapping_key and erp.expected_mapping_account_type(old.mapping_key) is not null then
    raise exception 'Core accounting mapping key % tidak boleh di-rename',old.mapping_key;
  end if;
  v_expected:=erp.expected_mapping_account_type(new.mapping_key);
  select account_type,is_active into v_type,v_active from erp.chart_accounts where id=new.account_id;
  if v_type is null then raise exception 'Mapped chart account tidak ditemukan'; end if;
  if not coalesce(v_active,false) then raise exception 'Accounting mapping % harus memakai chart account aktif',new.mapping_key; end if;
  if v_expected is not null and v_type<>v_expected then raise exception 'Accounting mapping % wajib memakai account type %, bukan %',new.mapping_key,v_expected,v_type; end if;
  return new;
end;
$function$;
