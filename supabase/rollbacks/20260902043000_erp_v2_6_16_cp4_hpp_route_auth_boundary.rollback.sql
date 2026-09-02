-- REVIEWED ROLLBACK FOR ERP v2.6.16 / CP4 R1 ONLY.
-- Fail closed when an ACTIVE pool still depends on the persistent HPP route.

begin;
set local lock_timeout='10s';
set local statement_timeout='120s';

do $rollback_guard$
declare v_expected integer;v_invalid integer;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.16') then
    raise exception 'CP4 rollback refused: v2.6.16 marker is absent';
  end if;
  if to_regclass('erp.cp4_v2616_rollback_capsule') is null then
    raise exception 'CP4 rollback refused: exact rollback capsule is absent';
  end if;
  if exists(select 1 from erp.attendance_hpp_pools where status='ACTIVE') then
    raise exception 'CP4 rollback refused: cancel every ACTIVE attendance HPP pool through its owning lifecycle first';
  end if;
  select count(*) into v_expected from erp.cp4_v2616_rollback_capsule;
  if v_expected<>3 then
    raise exception 'CP4 rollback refused: expected three exact function definitions, found %',v_expected;
  end if;
  select count(*) into v_invalid
  from erp.cp4_v2616_rollback_capsule
  where definition_sha256 is distinct from
        encode(extensions.digest(convert_to(function_definition,'UTF8'),'sha256'),'hex');
  if v_invalid<>0 then
    raise exception 'CP4 rollback refused: rollback capsule definition digest mismatch';
  end if;
end
$rollback_guard$;

-- Remove the API surface before restoring the inner lifecycle bytes.
drop function public.erp_cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint);
drop function public.erp_activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint);
drop function public.erp_create_attendance_hpp_pool_v1(jsonb,uuid);
drop function public.erp_preview_attendance_hpp_pool_v1(date,date);
drop function public.erp_reverse_sewing_terminal_v1(uuid,text,uuid);
drop function public.erp_record_sewing_terminal_v1(jsonb,uuid);
drop function public.erp_set_contractor_hpp_policy_v1(jsonb,uuid,uuid);

do $restore_functions$
declare r record;
begin
  for r in
    select function_identity,function_definition
    from erp.cp4_v2616_rollback_capsule
    order by case
      when function_identity like 'erp.rebuild_po_hpp(%' then 10
      when function_identity like 'erp.activate_attendance_hpp_pool_v1(%' then 20
      when function_identity like 'erp.cancel_attendance_hpp_pool_v1(%' then 30
      else 999 end,
      function_identity
  loop
    execute r.function_definition;
  end loop;
end
$restore_functions$;

do $restore_guard$
declare v_bad text;
begin
  select string_agg(c.function_identity,',' order by c.function_identity) into v_bad
  from erp.cp4_v2616_rollback_capsule c
  left join (
    select
      p.oid,p.proacl,p.proowner,
      format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)) function_identity
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='erp'
  ) p on p.function_identity=c.function_identity
  where p.oid is null
     or encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
        is distinct from c.definition_sha256
     or (case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end)
        is distinct from c.acl_snapshot
     or pg_get_userbyid(p.proowner) is distinct from c.owner_snapshot;
  if v_bad is not null then
    raise exception 'CP4 rollback exact function/ACL/owner restoration failed: %',v_bad;
  end if;
end
$restore_guard$;

drop view erp.v_attendance_hpp_active_allocation_by_po_group;
delete from erp.schema_migrations where version='v2.6.16';
delete from supabase_migrations.schema_migrations where version='20260902043000';
drop table erp.cp4_v2616_rollback_capsule;

select pg_notify('pgrst','reload schema');
commit;
