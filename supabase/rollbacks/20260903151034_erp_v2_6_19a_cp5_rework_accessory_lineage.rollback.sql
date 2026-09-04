-- REVIEWED ROLLBACK FOR ERP v2.6.19a / CP5 REWORK ACCESSORY LINEAGE ONLY.
--
-- This rollback is intentionally pre-use only. It restores the six exact
-- pre-v2.6.19a function definitions, ACLs, owners, and the prior workspace
-- comment. It refuses to erase rework, selected-accessory, FG/HPP,
-- reimbursement, idempotency, or audit history created after v2.6.19a.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $rollback_guard$
declare
  r record;
  v_actual text;
  v_bad text;
  v_installed_at timestamptz;
begin
  select installed_at into v_installed_at
  from erp.schema_migrations
  where version='v2.6.19a';
  if v_installed_at is null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.19') then
    raise exception 'v2.6.19a rollback refused: required application markers are absent';
  end if;

  if to_regclass('erp.bs_resolution_v2619a_rollback_capsule') is null
     or (select count(*) from erp.bs_resolution_v2619a_rollback_capsule)<>6 then
    raise exception 'v2.6.19a rollback refused: exact six-function capsule is missing';
  end if;
  select string_agg(function_identity,',' order by function_identity) into v_bad
  from erp.bs_resolution_v2619a_rollback_capsule
  where definition_sha256 is distinct from
    encode(extensions.digest(convert_to(function_definition,'UTF8'),'sha256'),'hex');
  if v_bad is not null then
    raise exception 'v2.6.19a rollback refused: capsule checksum drift: %',v_bad;
  end if;

  if to_regclass('erp.rework_accessory_decisions') is null
     or to_regclass('erp.rework_accessory_selection_lines') is null
     or to_regclass('erp.idx_bs_case_hold_events_actor') is null
     or to_regclass('erp.ux_rework_orders_good_fg_lot_v2619a') is null
     or to_regprocedure('erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone)') is null
     or to_regprocedure('erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone)') is null
     or to_regprocedure('erp.get_rework_accessory_decision_v1(uuid)') is null
     or to_regprocedure('erp.guard_rework_accessory_lineage_immutable()') is null then
    raise exception 'v2.6.19a rollback refused: installed accessory-lineage contract is incomplete';
  end if;

  for r in
    select * from (values
      ('erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint)','ca6fba986bf22ad2849ecc79fd2fa697'),
      ('erp.ensure_fg_accessory_cost_snapshot(uuid)','9808f90671de7a20ae16a197d8a61fd3'),
      ('erp.post_accessory_reimbursement_accrual(uuid)','87bf4af5a2267075ad49e0d39d3da69f'),
      ('erp.post_rework_completion(uuid)','675b7b52bc0c849c7fc8295afe4a614f'),
      ('erp.save_rework_order_v2(jsonb,uuid,bigint)','5bf622dfba25e85e846ddb8ba0dedac5'),
      ('public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','0316fd7f5e2e3d0347fa1924c599a66c')
    ) expected(identity,expected_md5)
  loop
    if to_regprocedure(r.identity) is null then
      raise exception 'v2.6.19a rollback refused: required function % is absent',r.identity;
    end if;
    select md5(pg_get_functiondef(to_regprocedure(r.identity))) into v_actual;
    if v_actual is distinct from r.expected_md5 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: % changed (% vs %)',
        r.identity,v_actual,r.expected_md5;
    end if;
  end loop;

  if exists(select 1 from erp.rework_accessory_decisions)
     or exists(select 1 from erp.rework_accessory_selection_lines)
     or exists(
       select 1 from erp.rework_orders where created_at>=v_installed_at
     )
     or exists(
       select 1 from erp.fg_lots where created_at>=v_installed_at
     )
     or exists(
       select 1 from erp.fg_accessory_cost_snapshots where snapshotted_at>=v_installed_at
     )
     or exists(
       select 1 from erp.contractor_accessory_reimbursement_entitlements
       where created_at>=v_installed_at or physical_at>=v_installed_at
     )
     or exists(
       select 1 from erp.idempotency_requests
       where operation_name in(
         'save_rework_order_v2','complete_rework_order_v2','save_bs_resolution_action_v1'
       ) and created_at>=v_installed_at
     )
     or exists(
       select 1 from erp.audit_logs
       where entity_type in(
         'rework_accessory_decisions','rework_accessory_selection_lines'
       )
     ) then
    raise exception 'v2.6.19a rollback refused: post-install business/audit/idempotency history exists';
  end if;
end
$rollback_guard$;

-- Official-timestamp and connector-generated ledgers must both match the name
-- and frozen source SHA-256. Guard and DELETE predicates are intentionally
-- identical.
do $platform_ledger_guard$
declare
  v_match_count integer;
  v_conflict_count integer;
begin
  select count(*) into v_match_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_19a_cp5_rework_accessory_lineage'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'')='204b9246f3c8c6464476da1a7f1574f5e0ae4c46f024c082704795b3eef5210f'
  ;
  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where(
    m.version='20260903151034'
    or m.name='erp_v2_6_19a_cp5_rework_accessory_lineage'
  ) and not(
    m.name='erp_v2_6_19a_cp5_rework_accessory_lineage'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'')='204b9246f3c8c6464476da1a7f1574f5e0ae4c46f024c082704795b3eef5210f'
  );
  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception 'v2.6.19a rollback refused: platform ledger identity is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_ledger_guard$;

do $restore_functions$
declare
  r record;
  a record;
  v_grantee text;
begin
  for r in
    select function_identity,function_definition,acl_snapshot,owner_snapshot
    from erp.bs_resolution_v2619a_rollback_capsule
    order by function_identity
  loop
    execute r.function_definition;
    execute format('alter function %s owner to %I',r.function_identity,r.owner_snapshot);
    for a in
      select distinct x.grantee
      from pg_proc p
      join pg_namespace n on n.oid=p.pronamespace
      cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) x
      where format('%I.%I(%s)',n.nspname,p.proname,
        pg_get_function_identity_arguments(p.oid))=r.function_identity
    loop
      v_grantee:=case when a.grantee=0 then 'PUBLIC'
        else format('%I',pg_get_userbyid(a.grantee)) end;
      execute format('revoke all privileges on function %s from %s',
        r.function_identity,v_grantee);
    end loop;
    if r.acl_snapshot is null then
      execute format('grant execute on function %s to PUBLIC',r.function_identity);
    else
      for a in
        select x.* from aclexplode(r.acl_snapshot::aclitem[]) x
        order by x.grantee,x.privilege_type,x.is_grantable
      loop
        if a.privilege_type<>'EXECUTE' then
          raise exception 'v2.6.19a rollback refused: unsupported function privilege %',
            a.privilege_type;
        end if;
        v_grantee:=case when a.grantee=0 then 'PUBLIC'
          else format('%I',pg_get_userbyid(a.grantee)) end;
        execute format('grant execute on function %s to %s%s',
          r.function_identity,v_grantee,
          case when a.is_grantable then ' with grant option' else '' end);
      end loop;
    end if;
  end loop;
end
$restore_functions$;

comment on function public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer) is
  'CP5 guarded BS/Rework/Laundry-claim workspace with server-side Pattern, lifecycle, and search filters.';

drop index erp.idx_bs_case_hold_events_actor;
drop index erp.ux_rework_orders_good_fg_lot_v2619a;
drop table erp.rework_accessory_selection_lines;
drop table erp.rework_accessory_decisions;
drop function erp.get_rework_accessory_decision_v1(uuid);
drop function erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone);
drop function erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone);
drop function erp.guard_rework_accessory_lineage_immutable();

do $restore_guard$
declare
  v_bad text;
begin
  select string_agg(c.function_identity,',' order by c.function_identity) into v_bad
  from erp.bs_resolution_v2619a_rollback_capsule c
  left join(
    select p.oid,p.proacl,p.proowner,
      format('%I.%I(%s)',n.nspname,p.proname,
        pg_get_function_identity_arguments(p.oid)) function_identity
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  ) p on p.function_identity=c.function_identity
  where p.oid is null
     or encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
        is distinct from c.definition_sha256
     or coalesce((
       select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,
         x.privilege_type,x.is_grantable)
         order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
       from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) x
     ),array[]::text[]) is distinct from coalesce((
       select array_agg(format('%s:%s:%s:%s',x.grantor,x.grantee,
         x.privilege_type,x.is_grantable)
         order by x.grantor,x.grantee,x.privilege_type,x.is_grantable)
       from aclexplode(coalesce(c.acl_snapshot::aclitem[],acldefault('f',p.proowner))) x
     ),array[]::text[])
     or pg_get_userbyid(p.proowner) is distinct from c.owner_snapshot;
  if v_bad is not null then
    raise exception 'v2.6.19a rollback exact function/ACL/owner restoration failed: %',v_bad;
  end if;

  if md5(pg_get_functiondef(
       'erp.complete_rework_order_v2(uuid,integer,integer,timestamp with time zone,uuid,text,uuid,bigint)'::regprocedure
     )) is distinct from 'c59e0fc2f14934d3947ce5cc7f3c78bb'
     or md5(pg_get_functiondef(
       'erp.ensure_fg_accessory_cost_snapshot(uuid)'::regprocedure
     )) is distinct from 'aae034da6699fb2f7b4c5f817e8d9f50'
     or md5(pg_get_functiondef(
       'erp.post_accessory_reimbursement_accrual(uuid)'::regprocedure
     )) is distinct from '36804117ef5af6f018c199518bd2e915'
     or md5(pg_get_functiondef(
       'erp.post_rework_completion(uuid)'::regprocedure
     )) is distinct from 'bf610b5a00636297eab1f640bdc5da8c'
     or md5(pg_get_functiondef(
       'erp.save_rework_order_v2(jsonb,uuid,bigint)'::regprocedure
     )) is distinct from 'd4f297f43858bb3c819c9cacec2972ab'
     or md5(pg_get_functiondef(
       'public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)'::regprocedure
     )) is distinct from 'f4f238d3b029c63d8d4c7753e3b661a1'
     or obj_description(
       'public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)'::regprocedure,
       'pg_proc'
     ) is distinct from
       'CP5 guarded BS/Rework/Laundry-claim workspace with server-side Pattern, lifecycle, and search filters.'
     or to_regclass('erp.rework_accessory_decisions') is not null
     or to_regclass('erp.rework_accessory_selection_lines') is not null
     or to_regclass('erp.idx_bs_case_hold_events_actor') is not null
     or to_regclass('erp.ux_rework_orders_good_fg_lot_v2619a') is not null
     or to_regprocedure('erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone)') is not null
     or to_regprocedure('erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone)') is not null
     or to_regprocedure('erp.get_rework_accessory_decision_v1(uuid)') is not null
     or to_regprocedure('erp.guard_rework_accessory_lineage_immutable()') is not null then
    raise exception 'v2.6.19a rollback left accessory-lineage runtime residue or restored source drift';
  end if;
end
$restore_guard$;

delete from erp.schema_migrations where version='v2.6.19a';
delete from supabase_migrations.schema_migrations m
where m.name='erp_v2_6_19a_cp5_rework_accessory_lineage'
  and coalesce(encode(extensions.digest(
    convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
  ),'hex'),'')='204b9246f3c8c6464476da1a7f1574f5e0ae4c46f024c082704795b3eef5210f'
;

drop table erp.bs_resolution_v2619a_rollback_capsule;
select pg_notify('pgrst','reload schema');
commit;
