create function erp.guard_last_active_owner()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare v_old_owner boolean;v_new_owner boolean:=false;
begin
  -- A postgres-only, transaction-local escape hatch exists solely so the
  -- hosted synthetic Auth proof can return an otherwise-empty UAT to its exact
  -- zero-user baseline. It is unreachable through the Data API and does not
  -- weaken application/service-role lifecycle calls.
  if session_user in ('postgres','supabase_admin')
     and current_setting('erp.cp45_allow_synthetic_cleanup',true)='on' then
    if tg_op='DELETE' then return old; else return new; end if;
  end if;
  select (r.role_code='OWNER' and old.is_active and old.auth_user_id is not null)
  into v_old_owner from erp.app_roles r where r.id=old.role_id;
  if not coalesce(v_old_owner,false) then
    if tg_op='DELETE' then return old; else return new; end if;
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('erp.active_owner_roster',0));
  if tg_op='UPDATE' then
    select (r.role_code='OWNER' and new.is_active and new.auth_user_id is not null)
    into v_new_owner from erp.app_roles r where r.id=new.role_id;
  end if;
  if not coalesce(v_new_owner,false) and not exists(
    select 1 from erp.app_users u join erp.app_roles r on r.id=u.role_id
    where u.id<>old.id and u.is_active and u.auth_user_id is not null
      and r.role_code='OWNER' and r.is_active
  ) then
    raise exception using errcode='42501',message='LAST_ACTIVE_OWNER_PROTECTED';
  end if;
  if tg_op='DELETE' then return old; else return new; end if;
end
$function$;