-- REVIEWED ROLLBACK FOR ERP v2.6.17 / PRE-CP5 CHECKPOINT ONLY.
-- This rollback is intentionally fail-closed once real access, pattern, or WIP
-- state exists. Cleanly reassign/remove that state through owning lifecycles
-- before attempting rollback.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $rollback_guard$
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.17') then
    raise exception 'v2.6.17 rollback refused: application marker is absent';
  end if;
  if to_regclass('erp.cp45_v2617_rollback_capsule') is null
     or (select count(*) from erp.cp45_v2617_rollback_capsule)<>3
     or exists(
       select 1 from erp.cp45_v2617_rollback_capsule
       where definition_sha256 is distinct from
         encode(extensions.digest(convert_to(function_definition,'UTF8'),'sha256'),'hex')
     ) then
    raise exception 'v2.6.17 rollback refused: exact function capsule is missing or invalid';
  end if;
  if exists(select 1 from erp.app_users where role not in ('OWNER','ADMIN','STAFF','CUSTOMER')) then
    raise exception 'v2.6.17 rollback refused: reassign custom-role users first';
  end if;
  if exists(select 1 from erp.app_roles where not is_system)
     or exists(select 1 from erp.app_access_audit)
     or exists(select 1 from erp.production_patterns)
     or exists(select 1 from erp.production_pattern_audit)
     or exists(select 1 from erp.wip_control_flags)
     or exists(select 1 from erp.cutting_groups where pattern_id is not null)
     or exists(
       select 1 from erp.idempotency_requests
       where operation_name in (
         'save_role_v1','deactivate_role_v1','save_app_user_v2','save_pattern_v1',
         'deactivate_pattern_v1','assign_pattern_v1','set_wip_control_flag_v1'
       )
     ) then
    raise exception 'v2.6.17 rollback refused: access/pattern/WIP lifecycle residue exists';
  end if;
end
$rollback_guard$;

drop function public.erp_post_final_sku_allocation_v1(jsonb,uuid,bigint);
drop function public.erp_set_wip_control_flag_v1(jsonb,uuid,bigint);
drop function public.erp_get_wip_control_v1(text,uuid,text,text);
drop function public.erp_assign_pattern_v1(uuid,uuid,text,uuid,bigint);
drop function public.erp_deactivate_pattern_v1(uuid,text,uuid,bigint);
drop function public.erp_save_pattern_v1(jsonb,uuid,bigint);
drop function public.erp_list_patterns_v1(text,text,integer,integer);
drop function public.erp_save_app_user_v3(jsonb,uuid,bigint);
drop function public.erp_deactivate_role_v1(uuid,text,uuid,bigint);
drop function public.erp_save_role_v1(jsonb,uuid,bigint);
drop function public.erp_get_access_admin_v1();
drop function public.erp_get_my_access_v1();

drop function erp.post_final_sku_allocation_v1(jsonb,uuid,bigint);
drop trigger trg_00_guard_posted_qc_item_immutable on erp.qc_inspection_items;
drop function erp.guard_posted_qc_item_immutable();
drop function erp.set_wip_control_flag_v1(jsonb,uuid,bigint);
drop function erp.get_wip_control_v1(text,uuid,text,text);
drop view erp.v_wip_control_status_v1;

drop trigger trg_20_touch_wip_control_flags on erp.wip_control_flags;
drop trigger trg_10_bump_wip_control_flags on erp.wip_control_flags;
drop table erp.wip_control_flags;

drop function erp.assign_pattern_v1(uuid,uuid,text,uuid,bigint);
drop function erp.deactivate_pattern_v1(uuid,text,uuid,bigint);
drop function erp.save_pattern_v1(jsonb,uuid,bigint);
drop function erp.list_patterns_v1(text,text,integer,integer);

drop trigger trg_06_require_pattern_identity on erp.cutting_groups;
drop trigger trg_05_pattern_assignment_snapshot on erp.cutting_groups;
alter table erp.cutting_groups drop constraint cutting_groups_pattern_id_fkey;
alter table erp.cutting_groups drop constraint cutting_groups_pattern_snapshot_check;
drop index erp.idx_cutting_groups_pattern_id;
alter table erp.cutting_groups
  drop column pattern_id,
  drop column pattern_code_snapshot,
  drop column pattern_name_snapshot,
  drop column pattern_revision_snapshot;
drop function erp.guard_pattern_assignment_snapshot();
drop function erp.require_pattern_identity_on_app_write();
drop trigger trg_production_pattern_audit_immutable on erp.production_pattern_audit;
drop table erp.production_pattern_audit;
drop trigger trg_20_touch_production_patterns on erp.production_patterns;
drop trigger trg_10_bump_production_patterns on erp.production_patterns;
drop table erp.production_patterns;

drop function erp.deactivate_role_v1(uuid,text,uuid,bigint);
drop function erp.save_role_v1(jsonb,uuid,bigint);
drop function erp.get_access_admin_v1();
drop function erp.get_my_access_v1();
drop function erp.role_permission_keys(uuid);
drop function erp.require_permission(text);
drop function erp.has_permission(text);

drop trigger trg_02_guard_last_active_owner on erp.app_users;
drop trigger trg_01_sync_app_user_role on erp.app_users;
drop trigger trg_cp45_guard_last_owner_auth_delete on auth.users;
drop function erp.guard_last_owner_auth_delete();
drop function erp.guard_last_active_owner();
drop function erp.sync_app_user_role_assignment();

alter table erp.app_users drop constraint app_users_role_id_fkey;
alter table erp.app_users drop constraint app_users_role_code_check;
alter table erp.app_users drop column role_id;
alter table erp.app_users add constraint app_users_role_check check(
  role::text = any(array[
    'OWNER'::character varying::text,'ADMIN'::character varying::text,
    'STAFF'::character varying::text,'CUSTOMER'::character varying::text
  ])
);

drop trigger trg_guard_protected_role_permissions on erp.app_role_permissions;
drop trigger trg_app_access_audit_immutable on erp.app_access_audit;
drop table erp.app_role_permissions;
drop table erp.app_access_audit;
drop trigger trg_20_touch_app_roles on erp.app_roles;
drop trigger trg_10_bump_app_roles on erp.app_roles;
drop trigger trg_00_guard_protected_role on erp.app_roles;
drop table erp.app_roles;
drop table erp.app_permissions;
drop function erp.guard_protected_role();
drop function erp.guard_access_catalog_immutability();

do $restore_functions$
declare r record;
begin
  for r in
    select function_identity,function_definition
    from erp.cp45_v2617_rollback_capsule
    order by function_identity
  loop
    execute r.function_definition;
  end loop;
end
$restore_functions$;

do $restore_guard$
declare v_bad text;
begin
  select string_agg(c.function_identity,',' order by c.function_identity) into v_bad
  from erp.cp45_v2617_rollback_capsule c
  left join (
    select p.oid,p.proacl,p.proowner,
      format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)) function_identity
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp'
  ) p on p.function_identity=c.function_identity
  where p.oid is null
     or encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
        is distinct from c.definition_sha256
     or (case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end)
        is distinct from c.acl_snapshot
     or pg_get_userbyid(p.proowner) is distinct from c.owner_snapshot;
  if v_bad is not null then
    raise exception 'v2.6.17 rollback exact function/ACL/owner restoration failed: %',v_bad;
  end if;
  if md5(pg_get_functiondef('erp.require_owner_admin()'::regprocedure))
     is distinct from '965de305e5a381cfdf5588f2b9d4babc' then
    raise exception 'v2.6.17 rollback changed the frozen CP4 owner guard';
  end if;
end
$restore_guard$;

delete from erp.schema_migrations where version='v2.6.17';
delete from supabase_migrations.schema_migrations where version='20260902104937';
drop table erp.cp45_v2617_rollback_capsule;

select pg_notify('pgrst','reload schema');
commit;
