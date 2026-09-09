-- REVIEWED PRE-USE ROLLBACK FOR ERP v2.6.20f / CP6 A01-A04 closure.
-- Refuses after reconciliation output, business use, object drift, or a successor.
-- Posted history is never deleted, rewritten, or reinterpreted.

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
  where m.name='erp_v2_6_20f_cp6_final_runtime_reliability'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      '5ffdf1e5c12ccc964cf41820a78a790f33b10bbe087397d41b62f6e315c928ae',
      '48f0431ca57abc99906d3f578b53ef59f9072fef3fc3e11c0b50a5c3a581279c'
    );
  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20f_cp6_final_runtime_reliability'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') not in(
      '5ffdf1e5c12ccc964cf41820a78a790f33b10bbe087397d41b62f6e315c928ae',
      '48f0431ca57abc99906d3f578b53ef59f9072fef3fc3e11c0b50a5c3a581279c'
    );
  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception 'v2.6.20f rollback refused: platform ledger identity is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_guard$;

lock table
  erp.non_po_hpp_gl_sync_events_v2620f,
  erp.cp6_v2620f_rollback_capsule
in access exclusive mode;

lock table
  erp.audit_logs,
  erp.cp6_laundry_qc_execution_context,
  erp.idempotency_requests,
  erp.journal_entries,
  erp.journal_lines,
  erp.fg_lots,
  erp.fg_stock_movements,
  erp.fg_inventory_balances,
  erp.hpp_versions,
  erp.hpp_version_components,
  erp.po_hpp_gl_events,
  erp.po_hpp_gl_state,
  erp.sales_headers,
  erp.sales_items,
  erp.sale_stock_allocations,
  erp.sales_returns,
  erp.sales_return_items,
  erp.product_conversions,
  erp.product_conversion_allocations,
  erp.laundry_redispatch_participant_events,
  erp.laundry_deliveries,
  erp.laundry_delivery_lines,
  erp.laundry_delivery_batch_size_lines,
  erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,
  erp.laundry_failed_wash_batch_size_lines,
  erp.wip_stage_events
in share row exclusive mode;

do $rollback_guard$
declare
  v_installed_at timestamptz;
  v_platform_version text;
  v_fact_count bigint;
begin
  select min(captured_at) into v_installed_at
  from erp.cp6_v2620f_rollback_capsule;
  if v_installed_at is null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20f')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20e') then
    raise exception 'v2.6.20f rollback refused: required application markers/capsule are absent';
  end if;

  select m.version into strict v_platform_version
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20f_cp6_final_runtime_reliability'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      '5ffdf1e5c12ccc964cf41820a78a790f33b10bbe087397d41b62f6e315c928ae',
      '48f0431ca57abc99906d3f578b53ef59f9072fef3fc3e11c0b50a5c3a581279c'
    );
  if exists(
       select 1 from erp.schema_migrations m
       where m.version<>'v2.6.20f' and m.installed_at>(
         select installed_at from erp.schema_migrations where version='v2.6.20f'
       )
     ) or exists(
       select 1 from supabase_migrations.schema_migrations m
       where m.version>v_platform_version
     ) then
    raise exception 'v2.6.20f rollback refused: a successor migration is already installed';
  end if;

  if (select count(*) from erp.cp6_v2620f_rollback_capsule)<>8
     or exists(
       select 1 from erp.cp6_v2620f_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
          or c.installed_definition_sha256 is null
          or c.installed_definition_sha256 is distinct from encode(extensions.digest(
            convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
          ),'sha256'),'hex')
     ) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20f installed object/capsule drift';
  end if;
  if to_regprocedure('erp.compute_non_po_product_hpp_targets_v2620f(uuid)') is null
     or to_regprocedure('erp.compute_non_po_product_hpp_book_v2620f(uuid)') is null
     or to_regprocedure('erp.assert_non_po_product_hpp_target_book_v2620f(uuid)') is null
     or to_regprocedure('erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)') is null
     or to_regclass('erp.non_po_hpp_gl_sync_events_v2620f') is null then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20f schema object drift';
  end if;

  select
    (select count(*) from erp.non_po_hpp_gl_sync_events_v2620f)
    +(select count(*) from erp.cp6_laundry_qc_execution_context)
    +(select count(*) from erp.idempotency_requests
      where created_at>=v_installed_at and operation_name in(
        'save_sale_draft_v2','post_sale_v2','cancel_sale_draft_v2',
        'post_sales_return','reverse_sale','reverse_sales_return',
        'post_product_conversion'
      ))
    +(select count(*) from erp.hpp_versions where calculated_at>=v_installed_at)
    +(select count(*) from erp.po_hpp_gl_events where created_at>=v_installed_at)
    +(select count(*) from erp.journal_entries
      where posting_at>=v_installed_at and source_type in(
        'SALE','SALES_RETURN','JOURNAL_REVERSAL','PO_HPP_GL_SYNC',
        'PRODUCT_CONVERSION','NON_PO_HPP_GL_SYNC_V2620F'
      ))
    +(select count(*) from erp.fg_stock_movements
      where system_created_at>=v_installed_at and movement_type in(
        'SALE','SALE_RETURN','REVERSAL','REBRAND_OUT','REBRAND_IN'
      ))
    +(select count(*) from erp.audit_logs
      where changed_at>=v_installed_at and entity_type in(
        'fg_lots','hpp_versions','sales_headers','sales_items',
        'sale_stock_allocations','sales_returns','sales_return_items',
        'product_conversions','product_conversion_allocations',
        'laundry_deliveries','laundry_receipts',
        'laundry_failed_wash_attempts','wip_stage_events'
      ))
    into v_fact_count;
  if v_fact_count<>0 then
    raise exception 'v2.6.20f rollback refused: post-install reconciliation or business history exists (%)',
      v_fact_count;
  end if;
end
$rollback_guard$;

do $restore_functions$
declare
  r erp.cp6_v2620f_rollback_capsule%rowtype;
  a record;
  x record;
  v_grantee text;
  v_restored_sha text;
begin
  for r in
    select * from erp.cp6_v2620f_rollback_capsule order by object_identity
  loop
    execute r.object_definition;
    execute format('alter function %s owner to %I',
      r.object_identity,r.owner_snapshot);
    for x in
      select distinct acl.grantee
      from pg_proc p
      cross join lateral aclexplode(
        coalesce(p.proacl,acldefault('f',p.proowner))
      ) acl
      where p.oid=to_regprocedure(r.object_regidentity)
    loop
      v_grantee:=case when x.grantee=0 then 'PUBLIC'
        else format('%I',pg_get_userbyid(x.grantee)) end;
      execute format('revoke all privileges on function %s from %s',
        r.object_identity,v_grantee);
    end loop;
    for a in
      select acl.* from aclexplode(coalesce(
        r.acl_snapshot::aclitem[],
        acldefault('f',(select oid from pg_roles where rolname=r.owner_snapshot))
      )) acl order by acl.grantee,acl.privilege_type,acl.is_grantable
    loop
      if a.privilege_type<>'EXECUTE' then
        raise exception 'v2.6.20f rollback refused: unsupported function privilege %',
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
      raise exception 'v2.6.20f rollback restore hash mismatch for %',
        r.object_identity;
    end if;
  end loop;
end
$restore_functions$;

drop trigger trg_guard_non_po_hpp_gl_sync_event_v2620f
  on erp.non_po_hpp_gl_sync_events_v2620f;
drop function erp.guard_non_po_hpp_gl_sync_event_v2620f();
drop function erp.sync_non_po_product_hpp_to_gl_v2620f(
  uuid,date,text,uuid,text
);
drop function erp.assert_non_po_product_hpp_target_book_v2620f(uuid);
drop function erp.compute_non_po_product_hpp_book_v2620f(uuid);
drop function erp.compute_non_po_product_hpp_targets_v2620f(uuid);
drop table erp.non_po_hpp_gl_sync_events_v2620f;
drop table erp.cp6_v2620f_rollback_capsule;

delete from erp.schema_migrations where version='v2.6.20f';
delete from supabase_migrations.schema_migrations
where name='erp_v2_6_20f_cp6_final_runtime_reliability'
  and coalesce(encode(extensions.digest(
    convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'
  ),'hex'),'') in(
    '5ffdf1e5c12ccc964cf41820a78a790f33b10bbe087397d41b62f6e315c928ae',
    '48f0431ca57abc99906d3f578b53ef59f9072fef3fc3e11c0b50a5c3a581279c'
  );

do $rollback_postcheck$
begin
  if exists(select 1 from erp.schema_migrations where version='v2.6.20f')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20f_cp6_final_runtime_reliability')
     or to_regclass('erp.cp6_v2620f_rollback_capsule') is not null
     or to_regclass('erp.non_po_hpp_gl_sync_events_v2620f') is not null
     or to_regprocedure('erp.compute_non_po_product_hpp_targets_v2620f(uuid)') is not null then
    raise exception 'v2.6.20f rollback postcondition failed';
  end if;
end
$rollback_postcheck$;

commit;
