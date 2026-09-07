-- REVIEWED PRE-USE ROLLBACK FOR ERP v2.6.20c / CP6 deep-business repair.
-- Refuses after any relevant business/HPP/sale/payment use. It never deletes
-- or reinterprets posted history.

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
  where m.name='erp_v2_6_20c_cp6_deep_business_reliability'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'd0a13b29dc331ac91482dc689f29f07effc06498b74d150c8b0fd14f27bf6a93',
      '30ceee23966416da54b24387f5bc9f67407ccfa504b15d5887fe5d210d2aa89e'
    );
  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20c_cp6_deep_business_reliability'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') not in(
      'd0a13b29dc331ac91482dc689f29f07effc06498b74d150c8b0fd14f27bf6a93',
      '30ceee23966416da54b24387f5bc9f67407ccfa504b15d5887fe5d210d2aa89e'
    );
  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception 'v2.6.20c rollback refused: platform ledger identity is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_guard$;

lock table
  erp.audit_logs,
  erp.cp6_laundry_qc_execution_context,
  erp.cp6_v2620c_rollback_capsule,
  erp.fg_lots,
  erp.fg_stock_movements,
  erp.hpp_versions,
  erp.hpp_version_components,
  erp.idempotency_requests,
  erp.po_hpp_gl_events,
  erp.po_hpp_gl_state,
  erp.sales_headers,
  erp.sales_items,
  erp.sale_stock_allocations,
  erp.sales_payments,
  erp.vendor_invoices,
  erp.vendor_payments,
  erp.laundry_deliveries,
  erp.laundry_delivery_lines,
  erp.laundry_delivery_batch_size_lines,
  erp.laundry_receipts,
  erp.laundry_receipt_lines,
  erp.laundry_receipt_batch_size_lines,
  erp.laundry_failed_wash_attempts,
  erp.laundry_failed_wash_batch_size_lines,
  erp.qc_inspections,
  erp.qc_inspection_items
in share row exclusive mode;

do $rollback_guard$
declare
  v_installed_at timestamptz;
  v_platform_version text;
  v_fact_count bigint;
begin
  select installed_at into v_installed_at
  from erp.schema_migrations where version='v2.6.20c';
  if v_installed_at is null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20b') then
    raise exception 'v2.6.20c rollback refused: required application markers are absent';
  end if;

  select m.version into strict v_platform_version
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20c_cp6_deep_business_reliability'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'd0a13b29dc331ac91482dc689f29f07effc06498b74d150c8b0fd14f27bf6a93',
      '30ceee23966416da54b24387f5bc9f67407ccfa504b15d5887fe5d210d2aa89e'
    );
  if exists(
       select 1 from erp.schema_migrations m
       where m.version<>'v2.6.20c' and m.installed_at>v_installed_at
     ) or exists(
       select 1 from supabase_migrations.schema_migrations m
       where m.version>v_platform_version
     ) then
    raise exception 'v2.6.20c rollback refused: a successor migration is already installed';
  end if;

  if (select count(*) from erp.cp6_v2620c_rollback_capsule)<>15
     or exists(
       select 1 from erp.cp6_v2620c_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
          or c.installed_definition_sha256 is null
          or c.installed_definition_sha256 is distinct from encode(extensions.digest(
            convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
          ),'sha256'),'hex')
     ) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20c installed object/capsule drift';
  end if;
  if to_regprocedure('erp.cp6_lot_work_cost_v2620c(uuid,text)') is null
     or to_regprocedure('erp.cp6_lot_attendance_cost_v2620c(uuid)') is null
     or to_regprocedure('erp.cp6_lot_failed_wash_cost_v2620c(uuid)') is null
     or to_regprocedure('erp.cp6_lot_rework_cost_v2620c(uuid)') is null
     or to_regprocedure('erp.cp6_po_source_qty_v2620c(uuid)') is null
     or to_regprocedure('erp.search_laundry_bs_products_v2620c(uuid,timestamp with time zone,text,text,integer)') is null
     or to_regprocedure('public.erp_search_laundry_bs_products_v1(uuid,timestamp with time zone,text,text,integer)') is null then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20c schema object drift';
  end if;

  -- Read-only resolver calls leave no residue. Every relevant write route is
  -- counted under locks shared with the actual facades, so an in-flight writer
  -- must finish before this decision is made.
  select
    (select count(*) from erp.cp6_laundry_qc_execution_context)
    +(select count(*) from erp.idempotency_requests
      where created_at>=v_installed_at and(
        operation_name like 'cp6_laundry_qc_action_v1:%'
        or operation_name in('save_sale_draft_v2','post_sale_v2','cancel_sale_draft_v2')
        or operation_name like '%vendor_payment%'))
    +(select count(*) from erp.hpp_versions where calculated_at>=v_installed_at)
    +(select count(*) from erp.po_hpp_gl_events where created_at>=v_installed_at)
    +(select count(*) from erp.audit_logs
      where changed_at>=v_installed_at and entity_type in(
        'production_orders','laundry_deliveries','laundry_delivery_lines',
        'laundry_delivery_batch_size_lines','laundry_receipts',
        'laundry_receipt_lines','laundry_receipt_batch_size_lines',
        'laundry_failed_wash_attempts','laundry_failed_wash_batch_size_lines',
        'qc_inspections','qc_inspection_items','fg_lots','hpp_versions',
        'sales_headers','sales_items','sale_stock_allocations',
        'vendor_invoices','vendor_payments'))
    into v_fact_count;
  if v_fact_count<>0 then
    raise exception 'v2.6.20c rollback refused: post-install business/HPP history exists (%)',v_fact_count;
  end if;
end
$rollback_guard$;

do $restore_functions$
declare
  r erp.cp6_v2620c_rollback_capsule%rowtype;
  a record;
  x record;
  v_grantee text;
  v_restored_sha text;
begin
  for r in select * from erp.cp6_v2620c_rollback_capsule order by object_identity
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
        raise exception 'v2.6.20c rollback refused: unsupported function privilege %',a.privilege_type;
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
      raise exception 'v2.6.20c rollback failed exact restoration for %',r.object_identity;
    end if;
  end loop;
end
$restore_functions$;

drop function public.erp_search_laundry_bs_products_v1(uuid,timestamptz,text,text,integer);
drop function erp.search_laundry_bs_products_v2620c(uuid,timestamptz,text,text,integer);
drop function erp.cp6_lot_failed_wash_cost_v2620c(uuid);
drop function erp.cp6_lot_attendance_cost_v2620c(uuid);
drop function erp.cp6_lot_work_cost_v2620c(uuid,text);
drop function erp.cp6_lot_rework_cost_v2620c(uuid);
drop function erp.cp6_po_source_qty_v2620c(uuid);

-- Exact predecessor state: these four tables existed with RLS disabled.
alter table erp.cp3_r4_rollback_capsule disable row level security;
alter table erp.cp4_v2616_rollback_capsule disable row level security;
alter table erp.cp45_v2617_rollback_capsule disable row level security;
alter table erp.cp45_v2617a_rollback_capsule disable row level security;

drop table erp.cp6_v2620c_rollback_capsule;
delete from erp.schema_migrations where version='v2.6.20c';

do $delete_platform_and_guard$
declare
  v_deleted integer;
begin
  delete from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20c_cp6_deep_business_reliability'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'd0a13b29dc331ac91482dc689f29f07effc06498b74d150c8b0fd14f27bf6a93',
      '30ceee23966416da54b24387f5bc9f67407ccfa504b15d5887fe5d210d2aa89e'
    );
  get diagnostics v_deleted=row_count;
  if v_deleted<>1 then
    raise exception 'v2.6.20c rollback failed exact platform-ledger delete';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20c')
     or exists(select 1 from supabase_migrations.schema_migrations
       where name='erp_v2_6_20c_cp6_deep_business_reliability')
     or to_regclass('erp.cp6_v2620c_rollback_capsule') is not null
     or to_regprocedure('erp.cp6_lot_work_cost_v2620c(uuid,text)') is not null
     or to_regprocedure('erp.cp6_lot_attendance_cost_v2620c(uuid)') is not null
     or to_regprocedure('erp.cp6_lot_failed_wash_cost_v2620c(uuid)') is not null
     or to_regprocedure('erp.cp6_lot_rework_cost_v2620c(uuid)') is not null
     or to_regprocedure('erp.cp6_po_source_qty_v2620c(uuid)') is not null
     or to_regprocedure('erp.search_laundry_bs_products_v2620c(uuid,timestamp with time zone,text,text,integer)') is not null
     or to_regprocedure('public.erp_search_laundry_bs_products_v1(uuid,timestamp with time zone,text,text,integer)') is not null
     or exists(
       select 1 from (values
         ('erp.cp3_r4_rollback_capsule'),('erp.cp4_v2616_rollback_capsule'),
         ('erp.cp45_v2617_rollback_capsule'),('erp.cp45_v2617a_rollback_capsule')
       ) x(identity)
       join pg_class c on c.oid=to_regclass(x.identity)
       where c.relrowsecurity
     ) then
    raise exception 'v2.6.20c rollback left schema, RLS, or ledger residue';
  end if;
end
$delete_platform_and_guard$;

commit;
