CREATE OR REPLACE FUNCTION erp.guard_protected_role()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_code text;v_new_code text;
begin
  if tg_table_name='app_roles' then
    v_code:=old.role_code;
  elsif tg_op='INSERT' then
    select role_code into v_code from erp.app_roles where id=new.role_id;
  elsif tg_op='DELETE' then
    select role_code into v_code from erp.app_roles where id=old.role_id;
  else
    select role_code into v_code from erp.app_roles where id=old.role_id;
    select role_code into v_new_code from erp.app_roles where id=new.role_id;
  end if;
  if v_code='OWNER' or v_new_code='OWNER' then
    raise exception using errcode='42501',message='PROTECTED_OWNER_ROLE_CANNOT_BE_CHANGED';
  end if;
  if tg_op='DELETE' then return old; else return new; end if;
end
$function$
