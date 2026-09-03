-- REVIEWED ROLLBACK FOR ERP v2.6.18 / PRE-CP5 CUTTING BRIDGE BOUNDARY ONLY.
--
-- This rollback restores the exact pre-Cutting-Bridge function definitions, function
-- ACLs/owners, and relation ACLs/owners captured at installation. It refuses
-- to run after Cutting Bridge business facts exist. Never use it to erase live cutting,
-- material, pickup, distribution, WIP, journal, or audit history.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $rollback_guard$
declare
  v_capsule_bad text;
  v_save_def text;
  v_post_def text;
  v_wip_def text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.17a')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.18') then
    raise exception 'v2.6.18 rollback refused: required application markers are absent';
  end if;
  if to_regclass('erp.cutting_bridge_v2618_rollback_capsule') is null
     or (select count(*) from erp.cutting_bridge_v2618_rollback_capsule where object_kind='FUNCTION')<>8
     or (select count(*) from erp.cutting_bridge_v2618_rollback_capsule where object_kind='RELATION')<>9 then
    raise exception 'v2.6.18 rollback refused: exact 8-function/9-relation capsule is missing';
  end if;

  select string_agg(object_identity,',' order by object_identity) into v_capsule_bad
  from erp.cutting_bridge_v2618_rollback_capsule
  where object_kind='FUNCTION' and definition_sha256 is distinct from
    encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex');
  if v_capsule_bad is not null then
    raise exception 'v2.6.18 rollback refused: capsule checksum drift: %',v_capsule_bad;
  end if;

  if to_regclass('erp.cutting_pickups') is null
     or to_regclass('erp.cutting_distribution_batches') is null
     or to_regclass('erp.cutting_distribution_allocations') is null
     or to_regprocedure('public.erp_get_cutting_workspace_v1(text,uuid,integer,integer)') is null
     or to_regprocedure('public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)') is null
     or to_regprocedure('public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)') is null
     or to_regprocedure('public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)') is null
     or to_regprocedure('erp.get_cutting_workspace_v1(text,uuid,integer,integer)') is null
     or to_regprocedure('erp.get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)') is null
     or to_regprocedure('erp.save_cutting_pickup_v1(jsonb,uuid,bigint)') is null then
    raise exception 'v2.6.18 rollback refused: installed object contract is incomplete';
  end if;
  if not exists(
    select 1 from information_schema.columns
    where table_schema='erp' and table_name='cutting_groups' and column_name='source_location_id'
  ) then
    raise exception 'v2.6.18 rollback refused: source-location contract is absent';
  end if;

  select pg_get_functiondef('erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)'::regprocedure)
    into v_save_def;
  select pg_get_functiondef('erp.post_cutting_material_issue(uuid,uuid)'::regprocedure)
    into v_post_def;
  select pg_get_functiondef('erp.get_wip_control_v1(text,uuid,text,text)'::regprocedure)
    into v_wip_def;
  if v_save_def not like '%CUTTING_ROLL_USAGE_MUST_RECONCILE_ISSUED_CONSUMED_AND_REMAINING%'
     or v_save_def not like '%production.cutting.post%'
     or v_post_def not like '%INSUFFICIENT_ROLL_STOCK%'
     or v_post_def not like '%pg_advisory_xact_lock%'
     or v_wip_def not like '%cutting_distribution_allocations%' then
    raise exception 'v2.6.18 rollback refused: installed source drifted after apply';
  end if;

  if exists(select 1 from erp.cutting_pickups)
     or exists(select 1 from erp.cutting_distribution_batches)
     or exists(select 1 from erp.cutting_distribution_allocations)
     or exists(select 1 from erp.cutting_groups where source_location_id is not null)
     or exists(
       select 1 from erp.idempotency_requests
       where operation_name in ('save_cutting_group_before_sewing_v2','save_cutting_pickup_v1')
     )
     or exists(
       select 1 from erp.audit_logs
       where entity_type in ('cutting_pickups','cutting_distribution_batches','cutting_distribution_allocations')
     ) then
    raise exception 'v2.6.18 rollback refused: Cutting Bridge business/audit/idempotency residue exists';
  end if;
end
$rollback_guard$;

drop function public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint);
drop function public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer);
drop function public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint);
drop function public.erp_get_cutting_workspace_v1(text,uuid,integer,integer);

drop trigger trg_07_guard_cutting_source_location on erp.cutting_groups;

drop table erp.cutting_distribution_allocations;
drop table erp.cutting_distribution_batches;
drop table erp.cutting_pickups;

drop function erp.save_cutting_pickup_v1(jsonb,uuid,bigint);
drop function erp.get_cutting_pickup_queue_v1(text,uuid,text,integer,integer);
drop function erp.get_cutting_workspace_v1(text,uuid,integer,integer);
drop function erp.guard_cutting_distribution_detail();
drop function erp.guard_cutting_pickup_lifecycle();
drop function erp.guard_cutting_source_location();

drop index erp.idx_material_rolls_roll_number_lower;
drop index erp.idx_material_stock_location_roll;
drop index erp.idx_cutting_groups_source_location_id;
alter table erp.cutting_groups drop constraint cutting_groups_source_location_id_fkey;
alter table erp.cutting_groups drop column source_location_id;

do $restore_functions$
declare
  r record;
  a record;
  v_grantee text;
begin
  for r in
    select object_identity,object_definition,acl_snapshot,owner_snapshot
    from erp.cutting_bridge_v2618_rollback_capsule
    where object_kind='FUNCTION'
    order by object_identity
  loop
    execute r.object_definition;
    execute format('alter function %s owner to %I',r.object_identity,r.owner_snapshot);

    for a in
      select distinct x.grantee
      from pg_proc p
      join pg_namespace n on n.oid=p.pronamespace
      cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) x
      where format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid))=r.object_identity
    loop
      v_grantee:=case when a.grantee=0 then 'PUBLIC' else format('%I',pg_get_userbyid(a.grantee)) end;
      execute format('revoke all privileges on function %s from %s',r.object_identity,v_grantee);
    end loop;

    if r.acl_snapshot is null then
      execute format('grant execute on function %s to PUBLIC',r.object_identity);
    else
      for a in
        select x.* from aclexplode(r.acl_snapshot::aclitem[]) x
        order by x.grantee,x.privilege_type,x.is_grantable
      loop
        if a.privilege_type<>'EXECUTE' then
          raise exception 'v2.6.18 rollback refused: unsupported function privilege %',a.privilege_type;
        end if;
        v_grantee:=case when a.grantee=0 then 'PUBLIC' else format('%I',pg_get_userbyid(a.grantee)) end;
        execute format(
          'grant execute on function %s to %s%s',r.object_identity,v_grantee,
          case when a.is_grantable then ' with grant option' else '' end
        );
      end loop;
    end if;
  end loop;
end
$restore_functions$;

do $restore_relations$
declare
  r record;
  a record;
  v_grantee text;
begin
  for r in
    select object_identity,acl_snapshot,owner_snapshot
    from erp.cutting_bridge_v2618_rollback_capsule
    where object_kind='RELATION'
    order by object_identity
  loop
    execute format('alter table %s owner to %I',r.object_identity,r.owner_snapshot);

    for a in
      select distinct x.grantee
      from pg_class c
      join pg_namespace n on n.oid=c.relnamespace
      cross join lateral aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) x
      where format('%I.%I',n.nspname,c.relname)=r.object_identity
    loop
      v_grantee:=case when a.grantee=0 then 'PUBLIC' else format('%I',pg_get_userbyid(a.grantee)) end;
      execute format('revoke all privileges on table %s from %s',r.object_identity,v_grantee);
    end loop;

    if r.acl_snapshot is null then
      execute format('grant all privileges on table %s to %I with grant option',r.object_identity,r.owner_snapshot);
    else
      for a in
        select x.* from aclexplode(r.acl_snapshot::aclitem[]) x
        order by x.grantee,x.privilege_type,x.is_grantable
      loop
        if a.privilege_type not in ('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN') then
          raise exception 'v2.6.18 rollback refused: unsupported relation privilege %',a.privilege_type;
        end if;
        v_grantee:=case when a.grantee=0 then 'PUBLIC' else format('%I',pg_get_userbyid(a.grantee)) end;
        execute format(
          'grant %s on table %s to %s%s',a.privilege_type,r.object_identity,v_grantee,
          case when a.is_grantable then ' with grant option' else '' end
        );
      end loop;
    end if;
  end loop;
end
$restore_relations$;

do $restore_guard$
declare
  v_bad text;
begin
  select string_agg(c.object_identity,',' order by c.object_identity) into v_bad
  from erp.cutting_bridge_v2618_rollback_capsule c
  left join (
    select p.oid,p.proacl,p.proowner,
      format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)) object_identity
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  ) p on p.object_identity=c.object_identity
  where c.object_kind='FUNCTION' and (
       p.oid is null
       or encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
          is distinct from c.definition_sha256
       or coalesce((
            select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,x.privilege_type,x.is_grantable)
              order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
            from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) x
          ),array[]::text[])
          is distinct from coalesce((
            select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,x.privilege_type,x.is_grantable)
              order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
            from aclexplode(coalesce(c.acl_snapshot::aclitem[],acldefault('f',p.proowner))) x
          ),array[]::text[])
       or pg_get_userbyid(p.proowner) is distinct from c.owner_snapshot
  );
  if v_bad is not null then
    raise exception 'v2.6.18 rollback exact function/ACL/owner restoration failed: %',v_bad;
  end if;

  select string_agg(c.object_identity,',' order by c.object_identity) into v_bad
  from erp.cutting_bridge_v2618_rollback_capsule c
  left join (
    select x.oid,x.relacl,x.relowner,format('%I.%I',n.nspname,x.relname) object_identity
    from pg_class x join pg_namespace n on n.oid=x.relnamespace
  ) p on p.object_identity=c.object_identity
  where c.object_kind='RELATION' and (
       p.oid is null
       or coalesce((
            select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,x.privilege_type,x.is_grantable)
              order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
            from aclexplode(coalesce(p.relacl,acldefault('r',p.relowner))) x
          ),array[]::text[])
          is distinct from coalesce((
            select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,x.privilege_type,x.is_grantable)
              order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
            from aclexplode(coalesce(c.acl_snapshot::aclitem[],acldefault('r',p.relowner))) x
          ),array[]::text[])
       or pg_get_userbyid(p.relowner) is distinct from c.owner_snapshot
  );
  if v_bad is not null then
    raise exception 'v2.6.18 rollback exact relation ACL/owner restoration failed: %',v_bad;
  end if;

  if md5(pg_get_functiondef('erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)'::regprocedure))
       is distinct from '609cea93ef82bfc12db64b8a363cd2cc'
     or md5(pg_get_functiondef('erp.post_cutting_material_issue(uuid,uuid)'::regprocedure))
       is distinct from '4fb3ff74878223f225f43a62a8d3abc3'
     or md5(pg_get_functiondef('erp.get_wip_control_v1(text,uuid,text,text)'::regprocedure))
       is distinct from '39d0d7d26688baecb07084037cc89787'
     or md5(pg_get_functiondef('erp.require_owner_admin()'::regprocedure))
       is distinct from '965de305e5a381cfdf5588f2b9d4babc' then
    raise exception 'v2.6.18 rollback failed to restore the exact CP4.5/CP4 runtime boundary';
  end if;

  if to_regclass('erp.cutting_pickups') is not null
     or to_regclass('erp.cutting_distribution_batches') is not null
     or to_regclass('erp.cutting_distribution_allocations') is not null
     or to_regprocedure('public.erp_get_cutting_workspace_v1(text,uuid,integer,integer)') is not null
     or to_regprocedure('public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)') is not null
     or to_regprocedure('public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)') is not null
     or to_regprocedure('public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)') is not null
     or exists(
       select 1 from information_schema.columns
       where table_schema='erp' and table_name='cutting_groups' and column_name='source_location_id'
     ) then
    raise exception 'v2.6.18 rollback left Cutting Bridge runtime residue';
  end if;
end
$restore_guard$;

-- Local/full-schema installs use the reviewed filename version. Connector
-- installs may use a generated version, so that path must match exact name and
-- the SHA-256 of the frozen migration bytes. Guard and DELETE predicates are
-- intentionally identical.
do $platform_ledger_guard$
declare
  v_match_count integer;
  v_conflict_count integer;
begin
  select count(*) into v_match_count
  from supabase_migrations.schema_migrations m
  where (
       m.version='20260903022604'
       and m.name='erp_v2_6_18_cutting_persistence_pickup_wip'
     )
     or (
       m.name='erp_v2_6_18_cutting_persistence_pickup_wip'
       and coalesce(
         encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex'),
         ''
       )='41cc50f1fbf171e89608232221c66d4b2b60806dd681fd298942dbdf94ffd58f'
     );

  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where (m.version='20260903022604' or m.name='erp_v2_6_18_cutting_persistence_pickup_wip')
    and not (
      (m.version='20260903022604' and m.name='erp_v2_6_18_cutting_persistence_pickup_wip')
      or (
        m.name='erp_v2_6_18_cutting_persistence_pickup_wip'
        and coalesce(
          encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex'),
          ''
        )='41cc50f1fbf171e89608232221c66d4b2b60806dd681fd298942dbdf94ffd58f'
      )
    );

  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception
      'v2.6.18 rollback refused: platform ledger identity is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_ledger_guard$;

delete from erp.schema_migrations where version='v2.6.18';
delete from supabase_migrations.schema_migrations m
where (
     m.version='20260903022604'
     and m.name='erp_v2_6_18_cutting_persistence_pickup_wip'
   )
   or (
     m.name='erp_v2_6_18_cutting_persistence_pickup_wip'
     and coalesce(
       encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex'),
       ''
     )='41cc50f1fbf171e89608232221c66d4b2b60806dd681fd298942dbdf94ffd58f'
   );

drop table erp.cutting_bridge_v2618_rollback_capsule;

select pg_notify('pgrst','reload schema');
commit;
