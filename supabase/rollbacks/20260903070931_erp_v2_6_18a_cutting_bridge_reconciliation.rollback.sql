-- REVIEWED PRE-USE ROLLBACK FOR ERP v2.6.18a RECONCILIATION ONLY.
--
-- This restores the exact recorded v2.6.18 runtime (including its known
-- private-helper defect) solely so the original v2.6.18 rollback can run next.
-- It refuses to erase Cutting or CP5 business, audit, or idempotency facts.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $rollback_guard$
declare v_bad text;v_internal_def text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.18')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.18a') then
    raise exception 'v2.6.18a rollback refused: required application markers are absent';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.19')
     or to_regclass('erp.bs_resolution_execution_context') is not null then
    raise exception 'v2.6.18a rollback refused: rollback CP5/v2.6.19 first';
  end if;
  if to_regclass('erp.cutting_bridge_v2618a_rollback_capsule') is null
     or (select count(*) from erp.cutting_bridge_v2618a_rollback_capsule)<>8
     or to_regclass('erp.cutting_bridge_v2618_rollback_capsule') is null
     or (select count(*) from erp.cutting_bridge_v2618_rollback_capsule where object_kind='FUNCTION')<>8
     or (select count(*) from erp.cutting_bridge_v2618_rollback_capsule where object_kind='RELATION')<>9
     or to_regclass('erp.cutting_bridge_execution_context') is null
     or to_regclass('erp.idx_material_stock_roll_location') is null
     or to_regclass('erp.idx_material_stock_location_roll') is not null then
    raise exception 'v2.6.18a rollback refused: installed reconciliation contract is incomplete';
  end if;
  select string_agg(object_identity,',' order by object_identity) into v_bad
  from erp.cutting_bridge_v2618a_rollback_capsule
  where definition_sha256 is distinct from
    encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex');
  if v_bad is not null then
    raise exception 'v2.6.18a rollback refused: capsule checksum drift: %',v_bad;
  end if;
  select pg_get_functiondef('erp.require_internal()'::regprocedure) into v_internal_def;
  if v_internal_def not like '%cutting_bridge_execution_context%'
     or position('Cutting Bridge execution context was lost before completion' in
       pg_get_functiondef('erp.post_cutting_material_issue(uuid,uuid)'::regprocedure))=0
     or position('production.bs_rework.view' in
       pg_get_functiondef('erp.list_patterns_v1(text,text,integer,integer)'::regprocedure))=0 then
    raise exception 'v2.6.18a rollback refused: installed function source drifted';
  end if;
  if exists(select 1 from erp.cutting_pickups)
     or exists(select 1 from erp.cutting_distribution_batches)
     or exists(select 1 from erp.cutting_distribution_allocations)
     or exists(select 1 from erp.cutting_groups where source_location_id is not null)
     or exists(select 1 from erp.cutting_bridge_execution_context)
     or exists(
       select 1 from erp.idempotency_requests
       where operation_name in('save_cutting_group_before_sewing_v2','save_cutting_pickup_v1')
     )
     or exists(
       select 1 from erp.audit_logs
       where entity_type in('cutting_pickups','cutting_distribution_batches','cutting_distribution_allocations')
     ) then
    raise exception 'v2.6.18a rollback refused: Cutting business/audit/idempotency history exists';
  end if;
end
$rollback_guard$;

do $restore_functions$
declare r record;a record;v_grantee text;
begin
  for r in
    select object_identity,object_definition,acl_snapshot,owner_snapshot
    from erp.cutting_bridge_v2618a_rollback_capsule
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
          raise exception 'v2.6.18a rollback refused: unsupported function privilege %',a.privilege_type;
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

drop table erp.cutting_bridge_execution_context;

drop index erp.idx_material_stock_roll_location;
create index idx_material_stock_location_roll
  on erp.material_stock_movements(location_id,roll_id,system_created_at,id)
  where roll_id is not null;

alter table erp.cutting_bridge_v2618_rollback_capsule disable row level security;

do $restore_guard$
declare v_bad text;
begin
  select string_agg(c.object_identity,',' order by c.object_identity) into v_bad
  from erp.cutting_bridge_v2618a_rollback_capsule c
  left join(
    select p.oid,p.proacl,p.proowner,
      format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)) object_identity
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  ) p on p.object_identity=c.object_identity
  where p.oid is null
     or encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
        is distinct from c.definition_sha256
     or coalesce((
       select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,x.privilege_type,x.is_grantable)
         order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
       from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) x
     ),array[]::text[]) is distinct from coalesce((
       select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,x.privilege_type,x.is_grantable)
         order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
       from aclexplode(coalesce(c.acl_snapshot::aclitem[],acldefault('f',p.proowner))) x
     ),array[]::text[])
     or pg_get_userbyid(p.proowner) is distinct from c.owner_snapshot;
  if v_bad is not null then
    raise exception 'v2.6.18a rollback exact function/ACL/owner restoration failed: %',v_bad;
  end if;
  if md5(pg_get_functiondef('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)'::regprocedure))
       is distinct from 'cb366d2728b7e7f6693fdc0098c239cb'
     or md5(pg_get_functiondef('erp.sync_material_cost_revaluation(uuid)'::regprocedure))
       is distinct from '0188292c0383564b59c17743a26c3195'
     or md5(pg_get_functiondef('erp.post_journal(text,uuid,date,text,jsonb)'::regprocedure))
       is distinct from 'c692b9ce872625113cb7677bf53b7fb1'
     or md5(pg_get_functiondef('erp.refresh_accessory_hpp_after_material_recost(uuid,text)'::regprocedure))
       is distinct from '31e871d98fdcf9c17aeb88b1598da585'
     or md5(pg_get_functiondef('erp.refresh_material_cost_checkpoint(uuid,date)'::regprocedure))
       is distinct from '97280ef7ea68595d003b20204358a735'
     or md5(pg_get_functiondef('erp.require_internal()'::regprocedure))
       is distinct from '785838675ae23699ce163e4218f058bf'
     or md5(pg_get_functiondef('erp.list_patterns_v1(text,text,integer,integer)'::regprocedure))
       is distinct from 'feff17283c331b4883b208227bc99079'
     or md5(pg_get_functiondef('erp.post_cutting_material_issue(uuid,uuid)'::regprocedure))
       is distinct from 'bf91c08814f5eba65412439b7edb07bb'
     or to_regclass('erp.cutting_bridge_execution_context') is not null
     or to_regclass('erp.idx_material_stock_location_roll') is null
     or to_regclass('erp.idx_material_stock_roll_location') is not null
     or (select relrowsecurity from pg_class where oid='erp.cutting_bridge_v2618_rollback_capsule'::regclass) then
    raise exception 'v2.6.18a rollback left reconciliation runtime residue';
  end if;
end
$restore_guard$;

-- Local validation uses the reviewed filename. A connector-generated ledger
-- version must instead match both the semantic name and exact source hash.
do $platform_ledger_guard$
declare v_match_count integer;v_conflict_count integer;
begin
  select count(*) into v_match_count
  from supabase_migrations.schema_migrations m
  where(
    m.version='20260903070931' and m.name='erp_v2_6_18a_cutting_bridge_reconciliation'
  ) or(
    m.name='erp_v2_6_18a_cutting_bridge_reconciliation'
    and coalesce(encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex'),'')
      ='d024a9ef2c8b1d5d9c529669b0b46a7588575f3bdc6788252c1b90d0ab2aae6a'
  );
  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where(m.version='20260903070931' or m.name='erp_v2_6_18a_cutting_bridge_reconciliation')
    and not(
      (m.version='20260903070931' and m.name='erp_v2_6_18a_cutting_bridge_reconciliation')
      or(m.name='erp_v2_6_18a_cutting_bridge_reconciliation'
        and coalesce(encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex'),'')
          ='d024a9ef2c8b1d5d9c529669b0b46a7588575f3bdc6788252c1b90d0ab2aae6a')
    );
  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception 'v2.6.18a rollback refused: platform ledger identity is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_ledger_guard$;

delete from erp.schema_migrations where version='v2.6.18a';
delete from supabase_migrations.schema_migrations m
where(
  m.version='20260903070931' and m.name='erp_v2_6_18a_cutting_bridge_reconciliation'
) or(
  m.name='erp_v2_6_18a_cutting_bridge_reconciliation'
  and coalesce(encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex'),'')
    ='d024a9ef2c8b1d5d9c529669b0b46a7588575f3bdc6788252c1b90d0ab2aae6a'
);

drop table erp.cutting_bridge_v2618a_rollback_capsule;
select pg_notify('pgrst','reload schema');
commit;
