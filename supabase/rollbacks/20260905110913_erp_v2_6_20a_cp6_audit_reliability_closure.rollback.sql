-- REVIEWED PRE-USE ROLLBACK FOR ERP v2.6.20a / CP6 audit closure.
-- Refuses rollback after CP6 business use. Posted history is never deleted.

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
  where m.name='erp_v2_6_20a_cp6_audit_reliability_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'd628334354f4f9c5cdbbc39f1c8ee1a54b0c283cd178f582191a98dfa5224347',
      '4ddafa3af937da7a8c0beb4a6a74d9d1447ef6f9c43b321fd513726ba597fcb2'
    );
  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20a_cp6_audit_reliability_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') not in(
      'd628334354f4f9c5cdbbc39f1c8ee1a54b0c283cd178f582191a98dfa5224347',
      '4ddafa3af937da7a8c0beb4a6a74d9d1447ef6f9c43b321fd513726ba597fcb2'
    );
  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception 'v2.6.20a rollback refused: platform ledger identity is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_guard$;

lock table
  erp.audit_logs,
  erp.cp6_laundry_qc_execution_context,
  erp.cp6_v2620a_rollback_capsule,
  erp.idempotency_requests,
  erp.laundry_failed_wash_attempts,
  erp.laundry_failed_wash_batch_size_lines,
  erp.laundry_deliveries,
  erp.laundry_delivery_batch_size_lines,
  erp.laundry_delivery_lines,
  erp.laundry_receipts,
  erp.laundry_receipt_batch_size_lines,
  erp.laundry_receipt_lines,
  erp.qc_inspections,
  erp.qc_inspection_items,
  erp.vendor_invoice_items,
  erp.vendor_invoices,
  erp.wip_stage_events
in share row exclusive mode;

do $rollback_guard$
declare
  v_installed_at timestamptz;
  v_platform_version text;
  v_fact_count bigint;
begin
  select installed_at into v_installed_at
  from erp.schema_migrations where version='v2.6.20a';
  if v_installed_at is null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20') then
    raise exception 'v2.6.20a rollback refused: required application markers are absent';
  end if;

  select m.version into strict v_platform_version
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20a_cp6_audit_reliability_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'd628334354f4f9c5cdbbc39f1c8ee1a54b0c283cd178f582191a98dfa5224347',
      '4ddafa3af937da7a8c0beb4a6a74d9d1447ef6f9c43b321fd513726ba597fcb2'
    );
  if exists(
       select 1 from erp.schema_migrations m
       where m.version<>'v2.6.20a' and m.installed_at>v_installed_at
     ) or exists(
       select 1 from supabase_migrations.schema_migrations m
       where m.version>v_platform_version
     ) then
    raise exception 'v2.6.20a rollback refused: a successor migration is already installed';
  end if;

  if (select count(*) from erp.cp6_v2620a_rollback_capsule)<>4
     or exists(
       select 1 from erp.cp6_v2620a_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
          or c.installed_definition_sha256 is null
          or c.installed_definition_sha256 is distinct from encode(extensions.digest(
            convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
          ),'sha256'),'hex')
     ) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20a installed object/capsule drift';
  end if;

  -- v2.6.20 itself permits rollback only before CP6 use.  Keep the same hard
  -- boundary here so recovery cannot re-expose the audited race to live data.
  select
    (select count(*) from erp.laundry_delivery_batch_size_lines)
    +(select count(*) from erp.laundry_receipt_batch_size_lines)
    +(select count(*) from erp.laundry_failed_wash_attempts)
    +(select count(*) from erp.laundry_failed_wash_batch_size_lines)
    +(select count(*) from erp.qc_inspection_items
      where source_laundry_receipt_batch_size_line_id is not null)
    +(select count(*) from erp.cp6_laundry_qc_execution_context)
    +(select count(*) from erp.idempotency_requests
      where operation_name like 'cp6_laundry_qc_action_v1:%'
        and created_at>=v_installed_at)
    +(select count(*) from erp.products
      where created_at>=v_installed_at or updated_at>=v_installed_at)
    +(select count(*) from erp.audit_logs
      where changed_at>=v_installed_at and entity_type in(
        'laundry_delivery_batch_size_lines','laundry_receipt_batch_size_lines',
        'laundry_failed_wash_attempts','laundry_failed_wash_batch_size_lines',
        'laundry_deliveries','laundry_delivery_lines','laundry_receipts',
        'laundry_receipt_lines','qc_inspections','qc_inspection_items',
        'vendor_invoices','vendor_invoice_items','products'
      ))
    into v_fact_count;
  if v_fact_count<>0 then
    raise exception 'v2.6.20a rollback refused: CP6 business/idempotency history exists (%)',v_fact_count;
  end if;
end
$rollback_guard$;

do $restore_functions$
declare
  r erp.cp6_v2620a_rollback_capsule%rowtype;
  a record;
  x record;
  v_grantee text;
  v_restored_sha text;
begin
  for r in select * from erp.cp6_v2620a_rollback_capsule order by object_identity
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
        raise exception 'v2.6.20a rollback refused: unsupported function privilege %',a.privilege_type;
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
      raise exception 'v2.6.20a rollback failed exact restoration for %',r.object_identity;
    end if;
  end loop;
end
$restore_functions$;

drop index erp.idx_laundry_failed_wash_attempts_delivery_v2620a;
drop table erp.cp6_v2620a_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20a';

do $delete_platform_and_guard$
declare
  v_deleted integer;
begin
  delete from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20a_cp6_audit_reliability_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'd628334354f4f9c5cdbbc39f1c8ee1a54b0c283cd178f582191a98dfa5224347',
      '4ddafa3af937da7a8c0beb4a6a74d9d1447ef6f9c43b321fd513726ba597fcb2'
    );
  get diagnostics v_deleted=row_count;
  if v_deleted<>1 then
    raise exception 'v2.6.20a rollback failed exact platform-ledger delete';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20a')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20a_cp6_audit_reliability_closure')
     or to_regclass('erp.cp6_v2620a_rollback_capsule') is not null
     or to_regclass('erp.idx_laundry_failed_wash_attempts_delivery_v2620a') is not null then
    raise exception 'v2.6.20a rollback left schema or ledger residue';
  end if;
end
$delete_platform_and_guard$;

commit;
