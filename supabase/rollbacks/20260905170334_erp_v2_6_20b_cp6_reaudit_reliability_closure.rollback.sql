-- REVIEWED PRE-USE ROLLBACK FOR ERP v2.6.20b / CP6 re-audit closure.
-- Refuses rollback after any relevant business/HPP use. Posted history is
-- never deleted, rewritten, or silently reinterpreted.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

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
  where m.name='erp_v2_6_20b_cp6_reaudit_reliability_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      '1ee29e0b220a50882b567f8deb16545f8a5ffb3a8f99b0b6e7847d70277d7e8a',
      '22f912efd1621909a21954ab05219e1d15a74c0f3c8e3bede2cf278d971e2d0c'
    );
  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20b_cp6_reaudit_reliability_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') not in(
      '1ee29e0b220a50882b567f8deb16545f8a5ffb3a8f99b0b6e7847d70277d7e8a',
      '22f912efd1621909a21954ab05219e1d15a74c0f3c8e3bede2cf278d971e2d0c'
    );
  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception 'v2.6.20b rollback refused: platform ledger identity is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_guard$;

lock table
  erp.audit_logs,
  erp.cp6_laundry_qc_execution_context,
  erp.cp6_v2620b_rollback_capsule,
  erp.fg_lots,
  erp.fg_stock_movements,
  erp.hpp_versions,
  erp.hpp_version_components,
  erp.idempotency_requests,
  erp.laundry_deliveries,
  erp.laundry_delivery_lines,
  erp.laundry_delivery_batch_size_lines,
  erp.laundry_receipts,
  erp.laundry_receipt_lines,
  erp.laundry_receipt_batch_size_lines,
  erp.laundry_failed_wash_attempts,
  erp.laundry_failed_wash_batch_size_lines,
  erp.products,
  erp.qc_inspections,
  erp.qc_inspection_items,
  erp.sewing_terminal_events,
  erp.wip_stage_events
in share row exclusive mode;

do $rollback_guard$
declare
  v_installed_at timestamptz;
  v_platform_version text;
  v_fact_count bigint;
  v_constraint_definition text;
begin
  select installed_at into v_installed_at
  from erp.schema_migrations where version='v2.6.20b';
  if v_installed_at is null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20a') then
    raise exception 'v2.6.20b rollback refused: required application markers are absent';
  end if;

  select m.version into strict v_platform_version
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20b_cp6_reaudit_reliability_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      '1ee29e0b220a50882b567f8deb16545f8a5ffb3a8f99b0b6e7847d70277d7e8a',
      '22f912efd1621909a21954ab05219e1d15a74c0f3c8e3bede2cf278d971e2d0c'
    );
  if exists(
       select 1 from erp.schema_migrations m
       where m.version<>'v2.6.20b' and m.installed_at>v_installed_at
     ) or exists(
       select 1 from supabase_migrations.schema_migrations m
       where m.version>v_platform_version
     ) then
    raise exception 'v2.6.20b rollback refused: a successor migration is already installed';
  end if;

  if (select count(*) from erp.cp6_v2620b_rollback_capsule)<>7
     or exists(
       select 1 from erp.cp6_v2620b_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
          or c.installed_definition_sha256 is null
          or c.installed_definition_sha256 is distinct from encode(extensions.digest(
            convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
          ),'sha256'),'hex')
     ) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20b installed object/capsule drift';
  end if;
  select pg_get_constraintdef(oid) into v_constraint_definition
  from pg_constraint
  where conrelid='erp.cp6_laundry_qc_execution_context'::regclass
    and conname='cp6_laundry_qc_execution_context_action_check';
  if v_constraint_definition is null
     or position('REVERSE_DELIVERY' in v_constraint_definition)=0
     or to_regprocedure('erp.assert_cp6_dispatch_timeline_v2620b(uuid,uuid,timestamp with time zone,jsonb)') is null
     or to_regprocedure('erp.search_final_sku_products_v2620b(uuid,timestamp with time zone,text,text,integer)') is null
     or to_regprocedure('public.erp_search_final_sku_products_v1(uuid,timestamp with time zone,text,text,integer)') is null
     or to_regclass('erp.idx_products_qc_model_size_effective_v2620b') is null
     or to_regclass('erp.idx_sewing_terminal_group_timeline_v2620b') is null
     or to_regclass('erp.idx_wip_delivery_source_timeline_v2620b') is null then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20b schema object drift';
  end if;

  -- Reverting the allocation/timeline implementation after it has generated
  -- a fact would silently reinterpret history. Refuse instead. Read-only SKU
  -- searches create no residue and do not block a reviewed pre-use rollback.
  select
    (select count(*) from erp.cp6_laundry_qc_execution_context)
    +(select count(*) from erp.idempotency_requests
      where operation_name like 'cp6_laundry_qc_action_v1:%'
        and created_at>=v_installed_at)
    +(select count(*) from erp.hpp_versions where calculated_at>=v_installed_at)
    +(select count(*) from erp.products
      where created_at>=v_installed_at or updated_at>=v_installed_at)
    +(select count(*) from erp.audit_logs
      where changed_at>=v_installed_at and entity_type in(
        'production_orders','laundry_deliveries','laundry_delivery_lines',
        'laundry_delivery_batch_size_lines','laundry_receipts',
        'laundry_receipt_lines','laundry_receipt_batch_size_lines',
        'laundry_failed_wash_attempts','laundry_failed_wash_batch_size_lines',
        'qc_inspections','qc_inspection_items','fg_lots','hpp_versions',
        'vendor_invoices','vendor_invoice_items','products'
      ))
    into v_fact_count;
  if v_fact_count<>0 then
    raise exception 'v2.6.20b rollback refused: post-install business/HPP history exists (%)',
      v_fact_count;
  end if;
end
$rollback_guard$;

do $restore_functions$
declare
  r erp.cp6_v2620b_rollback_capsule%rowtype;
  a record;
  x record;
  v_grantee text;
  v_restored_sha text;
begin
  for r in select * from erp.cp6_v2620b_rollback_capsule order by object_identity
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
      execute format('revoke all privileges on function %s from %s',r.object_identity,v_grantee);
    end loop;
    for a in
      select acl.* from aclexplode(coalesce(
        r.acl_snapshot::aclitem[],
        acldefault('f',(select oid from pg_roles where rolname=r.owner_snapshot))
      )) acl order by acl.grantee,acl.privilege_type,acl.is_grantable
    loop
      if a.privilege_type<>'EXECUTE' then
        raise exception 'v2.6.20b rollback refused: unsupported function privilege %',a.privilege_type;
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
      raise exception 'v2.6.20b rollback failed exact restoration for %',r.object_identity;
    end if;
  end loop;
end
$restore_functions$;

alter table erp.cp6_laundry_qc_execution_context
  drop constraint cp6_laundry_qc_execution_context_action_check;
alter table erp.cp6_laundry_qc_execution_context
  add constraint cp6_laundry_qc_execution_context_action_check check(action in(
    'POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','POST_FINAL_SKU'
  ));

drop function public.erp_search_final_sku_products_v1(uuid,timestamptz,text,text,integer);
drop function erp.search_final_sku_products_v2620b(uuid,timestamptz,text,text,integer);
drop function erp.assert_cp6_dispatch_timeline_v2620b(uuid,uuid,timestamptz,jsonb);
drop index erp.idx_wip_delivery_source_timeline_v2620b;
drop index erp.idx_sewing_terminal_group_timeline_v2620b;
drop index erp.idx_products_qc_model_size_effective_v2620b;
drop table erp.cp6_v2620b_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20b';

do $delete_platform_and_guard$
declare
  v_deleted integer;
  v_constraint_definition text;
begin
  delete from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20b_cp6_reaudit_reliability_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      '1ee29e0b220a50882b567f8deb16545f8a5ffb3a8f99b0b6e7847d70277d7e8a',
      '22f912efd1621909a21954ab05219e1d15a74c0f3c8e3bede2cf278d971e2d0c'
    );
  get diagnostics v_deleted=row_count;
  if v_deleted<>1 then
    raise exception 'v2.6.20b rollback failed exact platform-ledger delete';
  end if;
  select pg_get_constraintdef(oid) into v_constraint_definition
  from pg_constraint
  where conrelid='erp.cp6_laundry_qc_execution_context'::regclass
    and conname='cp6_laundry_qc_execution_context_action_check';
  if exists(select 1 from erp.schema_migrations where version='v2.6.20b')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20b_cp6_reaudit_reliability_closure')
     or to_regclass('erp.cp6_v2620b_rollback_capsule') is not null
     or to_regclass('erp.idx_products_qc_model_size_effective_v2620b') is not null
     or to_regclass('erp.idx_sewing_terminal_group_timeline_v2620b') is not null
     or to_regclass('erp.idx_wip_delivery_source_timeline_v2620b') is not null
     or to_regprocedure('erp.assert_cp6_dispatch_timeline_v2620b(uuid,uuid,timestamp with time zone,jsonb)') is not null
     or to_regprocedure('erp.search_final_sku_products_v2620b(uuid,timestamp with time zone,text,text,integer)') is not null
     or to_regprocedure('public.erp_search_final_sku_products_v1(uuid,timestamp with time zone,text,text,integer)') is not null
     or v_constraint_definition is null
     or position('REVERSE_DELIVERY' in v_constraint_definition)>0 then
    raise exception 'v2.6.20b rollback left schema or ledger residue';
  end if;
end
$delete_platform_and_guard$;

commit;
