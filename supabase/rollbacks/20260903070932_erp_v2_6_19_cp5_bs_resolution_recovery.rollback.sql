-- REVIEWED ROLLBACK FOR ERP v2.6.19 / CP5 BS RESOLUTION BOUNDARY ONLY.
--
-- This rollback is intentionally pre-use only. It restores exact pre-CP5
-- function definitions, ACLs, owners, and relation ACLs/owners. It refuses to
-- erase HOLD history, CP5 idempotency, audit, BS, rework, claim, FG, HPP, or
-- accounting facts created after the boundary became active.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $rollback_guard$
declare v_bad text;v_read_def text;v_write_def text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.18')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.18a')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.19') then
    raise exception 'v2.6.19 rollback refused: required application markers are absent';
  end if;
  if to_regclass('erp.bs_resolution_v2619_rollback_capsule') is null
     or (select count(*) from erp.bs_resolution_v2619_rollback_capsule where object_kind='FUNCTION')<>20
     or (select count(*) from erp.bs_resolution_v2619_rollback_capsule where object_kind='RELATION')<>10 then
    raise exception 'v2.6.19 rollback refused: exact 20-function/10-relation capsule is missing';
  end if;
  select string_agg(object_identity,',' order by object_identity) into v_bad
  from erp.bs_resolution_v2619_rollback_capsule
  where object_kind='FUNCTION' and definition_sha256 is distinct from
    encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex');
  if v_bad is not null then
    raise exception 'v2.6.19 rollback refused: capsule checksum drift: %',v_bad;
  end if;
  if to_regclass('erp.bs_case_hold_events') is null
     or to_regclass('erp.bs_resolution_execution_context') is null
     or to_regclass('erp.cutting_bridge_execution_context') is null
     or to_regprocedure('erp.get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)') is null
     or to_regprocedure('erp.save_bs_resolution_action_v1(text,jsonb,uuid,bigint)') is null
     or to_regprocedure('public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)') is null
     or to_regprocedure('public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)') is null then
    raise exception 'v2.6.19 rollback refused: installed CP5 object contract is incomplete';
  end if;
  select pg_get_functiondef('erp.get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)'::regprocedure)
    into v_read_def;
  select pg_get_functiondef('erp.save_bs_resolution_action_v1(text,jsonb,uuid,bigint)'::regprocedure)
    into v_write_def;
  if v_read_def not like '%production.bs_rework.view%'
     or v_read_def not like '%bs_case_hold_events%'
     or v_write_def not like '%production.bs_rework.post%'
     or v_write_def not like '%REVERSE_REWORK_COMPLETION%'
     or v_write_def not like '%REVERSE_CLAIM_RESOLUTION%' then
    raise exception 'v2.6.19 rollback refused: installed CP5 source drifted after apply';
  end if;
  if exists(select 1 from erp.bs_case_hold_events)
     or exists(select 1 from erp.bs_resolution_execution_context)
     or exists(
       select 1 from erp.idempotency_requests
       where operation_name='save_bs_resolution_action_v1'
     )
     or exists(
       select 1 from erp.audit_logs where entity_type='bs_case_hold_events'
     )
     or exists(select 1 from erp.bs_cases where status='ON_HOLD') then
    raise exception 'v2.6.19 rollback refused: CP5 business/audit/idempotency history exists';
  end if;
end
$rollback_guard$;

drop function public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint);
drop function public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer);
drop function erp.save_bs_resolution_action_v1(text,jsonb,uuid,bigint);
drop function erp.get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer);

drop trigger trg_guard_bs_case_hold_event_immutable on erp.bs_case_hold_events;
drop trigger trg_audit_bs_case_hold_events on erp.bs_case_hold_events;
drop table erp.bs_case_hold_events;
drop function erp.guard_bs_case_hold_event_immutable();

alter table erp.bs_cases drop constraint bs_cases_status_check;
alter table erp.bs_cases add constraint bs_cases_status_check check(status in(
  'OPEN','IN_REWORK','PARTIAL','RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED'
));

do $restore_functions$
declare r record;a record;v_grantee text;
begin
  for r in
    select object_identity,object_definition,acl_snapshot,owner_snapshot
    from erp.bs_resolution_v2619_rollback_capsule
    where object_kind='FUNCTION' order by object_identity
  loop
    execute r.object_definition;
    execute format('alter function %s owner to %I',r.object_identity,r.owner_snapshot);
    for a in
      select distinct x.grantee
      from pg_proc p join pg_namespace n on n.oid=p.pronamespace
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
          raise exception 'v2.6.19 rollback refused: unsupported function privilege %',a.privilege_type;
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

-- require_internal is now back to its exact pre-CP5 definition: the CP5
-- capability is gone while the earlier Cutting Bridge capability remains.
drop table erp.bs_resolution_execution_context;

do $restore_relations$
declare r record;a record;v_grantee text;
begin
  for r in
    select object_identity,acl_snapshot,owner_snapshot
    from erp.bs_resolution_v2619_rollback_capsule
    where object_kind='RELATION' order by object_identity
  loop
    execute format('alter table %s owner to %I',r.object_identity,r.owner_snapshot);
    for a in
      select distinct x.grantee
      from pg_class c join pg_namespace n on n.oid=c.relnamespace
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
        if a.privilege_type not in(
          'SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN'
        ) then
          raise exception 'v2.6.19 rollback refused: unsupported relation privilege %',a.privilege_type;
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
declare v_bad text;v_status_constraint text;v_internal_def text;
begin
  select string_agg(c.object_identity,',' order by c.object_identity) into v_bad
  from erp.bs_resolution_v2619_rollback_capsule c
  left join(
    select p.oid,p.proacl,p.proowner,
      format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)) object_identity
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  ) p on p.object_identity=c.object_identity
  where c.object_kind='FUNCTION' and(
    p.oid is null
    or encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
       is distinct from c.definition_sha256
    or coalesce((select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,x.privilege_type,x.is_grantable)
         order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
       from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) x),array[]::text[])
       is distinct from coalesce((select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,x.privilege_type,x.is_grantable)
         order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
       from aclexplode(coalesce(c.acl_snapshot::aclitem[],acldefault('f',p.proowner))) x),array[]::text[])
    or pg_get_userbyid(p.proowner) is distinct from c.owner_snapshot
  );
  if v_bad is not null then
    raise exception 'v2.6.19 rollback exact function/ACL/owner restoration failed: %',v_bad;
  end if;

  select string_agg(c.object_identity,',' order by c.object_identity) into v_bad
  from erp.bs_resolution_v2619_rollback_capsule c
  left join(
    select x.oid,x.relacl,x.relowner,format('%I.%I',n.nspname,x.relname) object_identity
    from pg_class x join pg_namespace n on n.oid=x.relnamespace
  ) p on p.object_identity=c.object_identity
  where c.object_kind='RELATION' and(
    p.oid is null
    or coalesce((select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,x.privilege_type,x.is_grantable)
         order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
       from aclexplode(coalesce(p.relacl,acldefault('r',p.relowner))) x),array[]::text[])
       is distinct from coalesce((select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,x.privilege_type,x.is_grantable)
         order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
       from aclexplode(coalesce(c.acl_snapshot::aclitem[],acldefault('r',p.relowner))) x),array[]::text[])
    or pg_get_userbyid(p.relowner) is distinct from c.owner_snapshot
  );
  if v_bad is not null then
    raise exception 'v2.6.19 rollback exact relation ACL/owner restoration failed: %',v_bad;
  end if;

  select pg_get_constraintdef(c.oid,true) into v_status_constraint
  from pg_constraint c
  where c.conrelid='erp.bs_cases'::regclass and c.conname='bs_cases_status_check';
  select pg_get_functiondef('erp.require_internal()'::regprocedure) into v_internal_def;
  if v_status_constraint like '%ON_HOLD%'
     or md5(pg_get_functiondef('erp.refresh_bs_case_status(uuid)'::regprocedure))
       is distinct from 'ee4c1b83f51f194c16d7ee470f2b199f'
     or md5(pg_get_functiondef('erp.guard_bs_case_lifecycle()'::regprocedure))
       is distinct from 'a5c9065c699693f5339618ada86e9dbf'
     or to_regclass('erp.bs_case_hold_events') is not null
     or to_regclass('erp.bs_resolution_execution_context') is not null
     or to_regclass('erp.cutting_bridge_execution_context') is null
     or v_internal_def not like '%cutting_bridge_execution_context%'
     or v_internal_def like '%bs_resolution_execution_context%'
     or to_regprocedure('public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)') is not null
     or to_regprocedure('public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)') is not null then
    raise exception 'v2.6.19 rollback left CP5 runtime residue';
  end if;
end
$restore_guard$;

-- Local/full-schema installs use the official generated version. Connector
-- installs may use a generated ledger version; that path must match name and
-- the SHA-256 of the frozen migration bytes. Guard and DELETE predicates are
-- intentionally identical.
do $platform_ledger_guard$
declare v_match_count integer;v_conflict_count integer;
begin
  select count(*) into v_match_count
  from supabase_migrations.schema_migrations m
  where(
    m.version='20260903070932' and m.name='erp_v2_6_19_cp5_bs_resolution_recovery'
  ) or(
    m.name='erp_v2_6_19_cp5_bs_resolution_recovery'
    and coalesce(encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex'),'')
      ='5c3e0b77eea21ae0a01763a9ed002c9a6850fdbf89bb5bfb384ac3bcbe00d1a9'
  );
  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where(m.version='20260903070932' or m.name='erp_v2_6_19_cp5_bs_resolution_recovery')
    and not(
      (m.version='20260903070932' and m.name='erp_v2_6_19_cp5_bs_resolution_recovery')
      or(m.name='erp_v2_6_19_cp5_bs_resolution_recovery'
        and coalesce(encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex'),'')
          ='5c3e0b77eea21ae0a01763a9ed002c9a6850fdbf89bb5bfb384ac3bcbe00d1a9')
    );
  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception 'v2.6.19 rollback refused: platform ledger identity is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_ledger_guard$;

delete from erp.schema_migrations where version='v2.6.19';
delete from supabase_migrations.schema_migrations m
where(
  m.version='20260903070932' and m.name='erp_v2_6_19_cp5_bs_resolution_recovery'
) or(
  m.name='erp_v2_6_19_cp5_bs_resolution_recovery'
  and coalesce(encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex'),'')
    ='5c3e0b77eea21ae0a01763a9ed002c9a6850fdbf89bb5bfb384ac3bcbe00d1a9'
);

drop table erp.bs_resolution_v2619_rollback_capsule;
select pg_notify('pgrst','reload schema');
commit;
