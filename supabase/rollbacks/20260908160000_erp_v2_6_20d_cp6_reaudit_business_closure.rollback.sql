-- REVIEWED PRE-USE ROLLBACK FOR ERP v2.6.20d / CP6 re-audit closure.
-- Refuses after derived redispatch lineage, financial repair, or any relevant
-- business write. Posted history is never deleted or reinterpreted.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';

lock table erp.schema_migrations,
  supabase_migrations.schema_migrations
in share row exclusive mode;

do $platform_guard$
declare
  v_match_count integer;
  v_conflict_count integer;
begin
  select count(*) into v_match_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20d_cp6_reaudit_business_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'f013c65bdae0ac002557d7d165d4e0d447588e87b009c2c4e6785ef8a03abde8',
      'b71bc9fc752a7f28f1813f8ae240611d477877f919b0b82abfe3d16c8ece80fb'
    );
  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20d_cp6_reaudit_business_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') not in(
      'f013c65bdae0ac002557d7d165d4e0d447588e87b009c2c4e6785ef8a03abde8',
      'b71bc9fc752a7f28f1813f8ae240611d477877f919b0b82abfe3d16c8ece80fb'
    );
  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception 'v2.6.20d rollback refused: platform ledger identity is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_guard$;

-- The successor-only relations are dropped below.  Take their final
-- ACCESS EXCLUSIVE mode before holding any other business-table lock so the
-- DROP cannot upgrade a weaker lock while a live facade retains AccessShare.
-- This is deliberately first: an already-running writer finishes before the
-- rollback owns anything else, while a rollback-first writer waits without
-- creating the AccessShare -> RowExclusive -> AccessExclusive deadlock cycle.
lock table
  erp.laundry_redispatch_participant_allocations,
  erp.cp6_v2620d_rollback_capsule
in access exclusive mode;

lock table
  erp.audit_logs,
  erp.cp6_laundry_qc_execution_context,
  erp.journal_entries,
  erp.journal_lines,
  erp.fg_lots,
  erp.fg_stock_movements,
  erp.hpp_versions,
  erp.hpp_version_components,
  erp.idempotency_requests,
  erp.po_hpp_gl_events,
  erp.po_hpp_gl_state,
  erp.po_wip_close_events,
  erp.sales_headers,
  erp.sales_items,
  erp.sale_stock_allocations,
  erp.sales_returns,
  erp.sales_return_items,
  erp.sales_payments,
  erp.laundry_deliveries,
  erp.laundry_delivery_lines,
  erp.laundry_delivery_batch_size_lines,
  erp.laundry_receipts,
  erp.laundry_receipt_lines,
  erp.laundry_receipt_batch_size_lines,
  erp.laundry_failed_wash_attempts,
  erp.laundry_failed_wash_batch_size_lines
in share row exclusive mode;

do $rollback_guard$
declare
  v_installed_at timestamptz;
  v_platform_version text;
  v_fact_count bigint;
begin
  select min(captured_at) into v_installed_at
  from erp.cp6_v2620d_rollback_capsule;
  if v_installed_at is null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20d')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20c') then
    raise exception 'v2.6.20d rollback refused: required application markers/capsule are absent';
  end if;

  select m.version into strict v_platform_version
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20d_cp6_reaudit_business_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'f013c65bdae0ac002557d7d165d4e0d447588e87b009c2c4e6785ef8a03abde8',
      'b71bc9fc752a7f28f1813f8ae240611d477877f919b0b82abfe3d16c8ece80fb'
    );
  if exists(
       select 1 from erp.schema_migrations m
       where m.version<>'v2.6.20d' and m.installed_at>(
         select installed_at from erp.schema_migrations where version='v2.6.20d'
       )
     ) or exists(
       select 1 from supabase_migrations.schema_migrations m
       where m.version>v_platform_version
     ) then
    raise exception 'v2.6.20d rollback refused: a successor migration is already installed';
  end if;

  if (select count(*) from erp.cp6_v2620d_rollback_capsule)<>10
     or exists(
       select 1 from erp.cp6_v2620d_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
          or c.installed_definition_sha256 is null
          or c.installed_definition_sha256 is distinct from encode(extensions.digest(
            convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
          ),'sha256'),'hex')
     ) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20d installed object/capsule drift';
  end if;
  if to_regclass('erp.laundry_redispatch_participant_allocations') is null
     or to_regprocedure('erp.guard_laundry_redispatch_participant_v2620d()') is null
     or to_regprocedure('erp.allocate_laundry_redispatch_participants_v2620d(uuid)') is null
     or to_regprocedure('erp.cp6_lot_failed_wash_cost_v2620d(uuid)') is null
     or to_regprocedure('erp.compute_po_hpp_gl_targets_v2620d(uuid)') is null
     or to_regprocedure('erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)') is null
     or to_regprocedure('erp.compute_po_hpp_gl_book_v2620d(uuid)') is null
     or to_regprocedure('erp.assert_po_hpp_target_book_v2620d(uuid)') is null then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20d schema object drift';
  end if;

  -- All changed write routes touch at least one locked fact below. Read-only
  -- report/resolver calls intentionally leave no residue and keep pre-use
  -- rollback available. Migration-authored repair facts also make rollback
  -- refuse, because reverting their semantics would misstate retained history.
  select
    (select count(*) from erp.cp6_laundry_qc_execution_context)
    +(select count(*) from erp.laundry_redispatch_participant_allocations)
    +(select count(*) from erp.idempotency_requests
      where created_at>=v_installed_at and(
        operation_name like 'cp6_laundry_qc_action_v1:%'
        or operation_name in(
          'save_sale_draft_v2','post_sale_v2','cancel_sale_draft_v2',
          'post_sales_return','reverse_sale','reverse_sales_return'
        )))
    +(select count(*) from erp.hpp_versions where calculated_at>=v_installed_at)
    +(select count(*) from erp.po_hpp_gl_events where created_at>=v_installed_at)
    +(select count(*) from erp.journal_entries
      where posting_at>=v_installed_at and source_type in(
        'SALE','SALES_RETURN','JOURNAL_REVERSAL','PO_HPP_GL_SYNC'
      ))
    +(select count(*) from erp.fg_stock_movements
      where system_created_at>=v_installed_at and movement_type in(
        'SALE','SALE_RETURN','REVERSAL'
      ))
    +(select count(*) from erp.audit_logs
      where changed_at>=v_installed_at and entity_type in(
        'laundry_redispatch_participant_allocations',
        'laundry_deliveries','laundry_delivery_lines',
        'laundry_delivery_batch_size_lines','laundry_receipts',
        'laundry_receipt_lines','laundry_receipt_batch_size_lines',
        'laundry_failed_wash_attempts','laundry_failed_wash_batch_size_lines',
        'fg_lots','hpp_versions','sales_headers','sales_items',
        'sale_stock_allocations','sales_returns','sales_return_items'
      ))
    into v_fact_count;
  if v_fact_count<>0 then
    raise exception 'v2.6.20d rollback refused: post-install lineage/business/HPP history exists (%)',
      v_fact_count;
  end if;
end
$rollback_guard$;

do $restore_functions$
declare
  r erp.cp6_v2620d_rollback_capsule%rowtype;
  a record;
  x record;
  v_grantee text;
  v_restored_sha text;
begin
  for r in select * from erp.cp6_v2620d_rollback_capsule order by object_identity
  loop
    execute r.object_definition;
    execute format('alter function %s owner to %I',r.object_identity,r.owner_snapshot);
    for x in
      select distinct acl.grantee
      from pg_proc p
      cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) acl
      where p.oid=to_regprocedure(r.object_regidentity)
    loop
      v_grantee:=case when x.grantee=0 then 'PUBLIC'
        else format('%I',pg_get_userbyid(x.grantee)) end;
      execute format(
        'revoke all privileges on function %s from %s',r.object_identity,v_grantee
      );
    end loop;
    for a in
      select acl.* from aclexplode(coalesce(
        r.acl_snapshot::aclitem[],
        acldefault('f',(select oid from pg_roles where rolname=r.owner_snapshot))
      )) acl order by acl.grantee,acl.privilege_type,acl.is_grantable
    loop
      if a.privilege_type<>'EXECUTE' then
        raise exception 'v2.6.20d rollback refused: unsupported function privilege %',
          a.privilege_type;
      end if;
      v_grantee:=case when a.grantee=0 then 'PUBLIC'
        else format('%I',pg_get_userbyid(a.grantee)) end;
      execute format('grant execute on function %s to %s%s',
        r.object_identity,v_grantee,
        case when a.is_grantable then ' with grant option' else '' end);
    end loop;
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.object_regidentity)),'UTF8'
    ),'sha256'),'hex') into v_restored_sha;
    if v_restored_sha is distinct from r.definition_sha256 then
      raise exception 'v2.6.20d rollback failed exact restoration for %',r.object_identity;
    end if;
  end loop;
end
$restore_functions$;

drop trigger trg_audit_laundry_redispatch_participant_v2620d
  on erp.laundry_redispatch_participant_allocations;
drop trigger trg_guard_laundry_redispatch_participant_v2620d
  on erp.laundry_redispatch_participant_allocations;
drop function erp.guard_laundry_redispatch_participant_v2620d();

drop function erp.assert_po_hpp_target_book_v2620d(uuid);
drop function erp.compute_po_hpp_gl_book_v2620d(uuid);
drop function erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid);
drop function erp.compute_po_hpp_gl_targets_v2620d(uuid);
drop function erp.cp6_lot_failed_wash_cost_v2620d(uuid);
drop function erp.allocate_laundry_redispatch_participants_v2620d(uuid);
drop table erp.laundry_redispatch_participant_allocations;

drop table erp.cp6_v2620d_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20d';

do $delete_platform_and_guard$
declare
  v_deleted integer;
begin
  delete from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20d_cp6_reaudit_business_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'f013c65bdae0ac002557d7d165d4e0d447588e87b009c2c4e6785ef8a03abde8',
      'b71bc9fc752a7f28f1813f8ae240611d477877f919b0b82abfe3d16c8ece80fb'
    );
  get diagnostics v_deleted=row_count;
  if v_deleted<>1 then
    raise exception 'v2.6.20d rollback failed exact platform-ledger delete';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20d')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20d_cp6_reaudit_business_closure')
     or to_regclass('erp.cp6_v2620d_rollback_capsule') is not null
     or to_regclass('erp.laundry_redispatch_participant_allocations') is not null
     or to_regprocedure('erp.guard_laundry_redispatch_participant_v2620d()') is not null
     or to_regprocedure('erp.allocate_laundry_redispatch_participants_v2620d(uuid)') is not null
     or to_regprocedure('erp.cp6_lot_failed_wash_cost_v2620d(uuid)') is not null
     or to_regprocedure('erp.compute_po_hpp_gl_targets_v2620d(uuid)') is not null
     or to_regprocedure('erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)') is not null
     or to_regprocedure('erp.compute_po_hpp_gl_book_v2620d(uuid)') is not null
     or to_regprocedure('erp.assert_po_hpp_target_book_v2620d(uuid)') is not null then
    raise exception 'v2.6.20d rollback left schema or ledger residue';
  end if;
end
$delete_platform_and_guard$;

commit;
