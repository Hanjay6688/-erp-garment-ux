-- REVIEWED ROLLBACK FOR ERP v2.6.17a / CP4.5 CORRECTION ONLY.
-- Restores the exact v2.6.17 function definitions, ACLs, and owners. It is
-- intentionally fail-closed after any pattern assignment has become business
-- history; never re-enable the overwrite-capable boundary around live data.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $rollback_guard$
declare
  v_assign_def text;
  v_snapshot_def text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.17')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.17a') then
    raise exception 'v2.6.17a rollback refused: required application markers are absent';
  end if;
  if to_regclass('erp.cp45_v2617a_rollback_capsule') is null
     or (select count(*) from erp.cp45_v2617a_rollback_capsule)<>2
     or exists(
       select 1 from erp.cp45_v2617a_rollback_capsule
       where definition_sha256 is distinct from
         encode(extensions.digest(convert_to(function_definition,'UTF8'),'sha256'),'hex')
     ) then
    raise exception 'v2.6.17a rollback refused: exact function capsule is missing or invalid';
  end if;
  if to_regprocedure('erp.assert_pattern_initial_assignment_allowed(uuid)') is null
     or to_regprocedure('erp.assign_pattern_v1(uuid,uuid,text,uuid,bigint)') is null
     or to_regprocedure('erp.guard_pattern_assignment_snapshot()') is null then
    raise exception 'v2.6.17a rollback refused: correction function contract is incomplete';
  end if;

  select pg_get_functiondef('erp.assign_pattern_v1(uuid,uuid,text,uuid,bigint)'::regprocedure) into v_assign_def;
  select pg_get_functiondef('erp.guard_pattern_assignment_snapshot()'::regprocedure) into v_snapshot_def;
  if v_assign_def not like '%assert_pattern_initial_assignment_allowed%'
     or v_snapshot_def not like '%old.pattern_id is not null%'
     or v_snapshot_def not like '%PATTERN_ASSIGNMENT_SNAPSHOT_IMMUTABLE%' then
    raise exception 'v2.6.17a rollback refused: corrected source drifted after apply';
  end if;

  if exists(select 1 from erp.cutting_groups where pattern_id is not null)
     or exists(
       select 1 from erp.production_pattern_audit
       where entity_type='ASSIGNMENT' or action='ASSIGN'
     )
     or exists(
       select 1 from erp.idempotency_requests
       where operation_name='assign_pattern_v1'
     ) then
    raise exception 'v2.6.17a rollback refused: pattern assignment history/idempotency residue exists';
  end if;
end
$rollback_guard$;

do $restore_functions$
declare
  r record;
  a record;
  v_grantee text;
begin
  for r in
    select function_identity,function_definition,acl_snapshot,owner_snapshot
    from erp.cp45_v2617a_rollback_capsule
    order by function_identity
  loop
    execute r.function_definition;
    execute format('alter function %s owner to %I',r.function_identity,r.owner_snapshot);

    -- CREATE OR REPLACE preserves current grants. Remove all of them and then
    -- rebuild the exact pre-v2.6.17a ACL captured before correction.
    for a in
      select distinct x.grantee
      from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) x
      where format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid))=r.function_identity
    loop
      v_grantee:=case when a.grantee=0 then 'PUBLIC' else format('%I',pg_get_userbyid(a.grantee)) end;
      execute format('revoke all privileges on function %s from %s',r.function_identity,v_grantee);
    end loop;

    if r.acl_snapshot is null then
      execute format('grant execute on function %s to PUBLIC',r.function_identity);
    else
      for a in
        select x.* from aclexplode(r.acl_snapshot::aclitem[]) x
        order by x.grantee,x.privilege_type,x.is_grantable
      loop
        if a.privilege_type<>'EXECUTE' then
          raise exception 'v2.6.17a rollback refused: unsupported function privilege %',a.privilege_type;
        end if;
        v_grantee:=case when a.grantee=0 then 'PUBLIC' else format('%I',pg_get_userbyid(a.grantee)) end;
        execute format(
          'grant execute on function %s to %s%s',r.function_identity,v_grantee,
          case when a.is_grantable then ' with grant option' else '' end
        );
      end loop;
    end if;
  end loop;
end
$restore_functions$;

drop function erp.assert_pattern_initial_assignment_allowed(uuid);

do $restore_guard$
declare v_bad text;
begin
  select string_agg(c.function_identity,',' order by c.function_identity) into v_bad
  from erp.cp45_v2617a_rollback_capsule c
  left join (
    select p.oid,p.proacl,p.proowner,
      format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)) function_identity
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp'
  ) p on p.function_identity=c.function_identity
  where p.oid is null
     or encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
        is distinct from c.definition_sha256
     or coalesce((
          select array_agg(format('%s:%s:%s:%s',a.grantor,a.grantee,a.privilege_type,a.is_grantable)
            order by a.grantor,a.grantee,a.privilege_type,a.is_grantable)
          from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
        ),array[]::text[])
        is distinct from coalesce((
          select array_agg(format('%s:%s:%s:%s',a.grantor,a.grantee,a.privilege_type,a.is_grantable)
            order by a.grantor,a.grantee,a.privilege_type,a.is_grantable)
          from aclexplode(coalesce(c.acl_snapshot::aclitem[],acldefault('f',p.proowner))) a
        ),array[]::text[])
     or pg_get_userbyid(p.proowner) is distinct from c.owner_snapshot;
  if v_bad is not null then
    raise exception 'v2.6.17a rollback exact function/ACL/owner restoration failed: %',v_bad;
  end if;

  if md5(pg_get_functiondef('erp.assign_pattern_v1(uuid,uuid,text,uuid,bigint)'::regprocedure))
       is distinct from '5d291996e4297426b790e64eef163412'
     or md5(pg_get_functiondef('erp.guard_pattern_assignment_snapshot()'::regprocedure))
       is distinct from '8da2f40884705902230695dbf85a5fea'
     or not exists(
       select 1 from pg_trigger
       where tgrelid='erp.cutting_groups'::regclass
         and tgname='trg_05_pattern_assignment_snapshot'
         and tgfoid='erp.guard_pattern_assignment_snapshot()'::regprocedure
         and tgenabled<>'D'
         and not tgisinternal
     ) or md5(pg_get_functiondef('erp.require_owner_admin()'::regprocedure))
       is distinct from '965de305e5a381cfdf5588f2b9d4babc' then
    raise exception 'v2.6.17a rollback failed to restore the exact CP4.5/CP4 boundary';
  end if;
end
$restore_guard$;

-- Supabase records connector-applied migrations with the apply timestamp as
-- the platform version. Local/full-schema validation records the reviewed
-- filename version instead. Accept exactly one of those two ledger shapes,
-- and bind the connector shape to the exact reviewed migration bytes.
do $platform_ledger_guard$
declare
  v_match_count integer;
  v_conflict_count integer;
begin
  select count(*) into v_match_count
  from supabase_migrations.schema_migrations m
  where (
       m.version='20260902180726'
       and m.name='erp_v2_6_17a_cp45_pattern_assignment_immutability'
     )
     or (
       m.name='erp_v2_6_17a_cp45_pattern_assignment_immutability'
       and coalesce(
         encode(
           extensions.digest(
             convert_to(array_to_string(m.statements,E'\n'),'UTF8'),
             'sha256'
           ),
           'hex'
         ),
         ''
       )='62a25994d2b3be0986ca83492f4d29d2ebad17c1795543045827a77d55ef816a'
     );

  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where (m.version='20260902180726'
         or m.name='erp_v2_6_17a_cp45_pattern_assignment_immutability')
    and not (
      (
        m.version='20260902180726'
        and m.name='erp_v2_6_17a_cp45_pattern_assignment_immutability'
      )
      or (
        m.name='erp_v2_6_17a_cp45_pattern_assignment_immutability'
        and coalesce(
          encode(
            extensions.digest(
              convert_to(array_to_string(m.statements,E'\n'),'UTF8'),
              'sha256'
            ),
            'hex'
          ),
          ''
        )='62a25994d2b3be0986ca83492f4d29d2ebad17c1795543045827a77d55ef816a'
      )
    );

  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception
      'v2.6.17a rollback refused: platform ledger identity is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_ledger_guard$;

delete from erp.schema_migrations where version='v2.6.17a';
delete from supabase_migrations.schema_migrations m
where (
     m.version='20260902180726'
     and m.name='erp_v2_6_17a_cp45_pattern_assignment_immutability'
   )
   or (
     m.name='erp_v2_6_17a_cp45_pattern_assignment_immutability'
     and coalesce(
       encode(
         extensions.digest(
           convert_to(array_to_string(m.statements,E'\n'),'UTF8'),
           'sha256'
         ),
         'hex'
       ),
       ''
     )='62a25994d2b3be0986ca83492f4d29d2ebad17c1795543045827a77d55ef816a'
   );
drop table erp.cp45_v2617a_rollback_capsule;

select pg_notify('pgrst','reload schema');
commit;
