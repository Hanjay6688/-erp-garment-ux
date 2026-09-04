-- REVIEWED PRE-USE ROLLBACK FOR ERP v2.6.20 / CP6 Laundry-QC-FG bridge.
-- Refuses rollback after any CP6 physical, financial, stock, HPP, idempotency,
-- or audit fact exists.  Posted history is never deleted as a correction path.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

-- Fence both ledgers before trusting their identity.  SHARE ROW EXCLUSIVE
-- still permits read-only observers but prevents a concurrent installer or
-- ledger rewrite from crossing the rollback decision.
lock table erp.schema_migrations,
  supabase_migrations.schema_migrations
in share row exclusive mode;

do $platform_ledger_guard$
declare
  v_match_count integer;
  v_conflict_count integer;
begin
  select count(*) into v_match_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20_cp6_laundry_qc_fg_authoritative'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'')='4a252c7c895d031cbc92d656808a515294e18a923dc943e62e205a83c3ad5596';

  select count(*) into v_conflict_count
  from supabase_migrations.schema_migrations m
  where(
    m.version='20260904111157'
    or m.name='erp_v2_6_20_cp6_laundry_qc_fg_authoritative'
  ) and not(
    m.name='erp_v2_6_20_cp6_laundry_qc_fg_authoritative'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'')='4a252c7c895d031cbc92d656808a515294e18a923dc943e62e205a83c3ad5596'
  );
  if v_match_count<>1 or v_conflict_count<>0 then
    raise exception 'v2.6.20 rollback refused: platform ledger statement digest is ambiguous (match %, conflict %)',
      v_match_count,v_conflict_count;
  end if;
end
$platform_ledger_guard$;

-- Fence every CP6 entry point and every relation whose shape or history this
-- rollback removes/restores.  A transaction already in flight completes or
-- aborts before these locks are granted; the guard below then sees its final
-- state.  New writers cannot start until this transaction commits/rolls back.
-- Ordinary SELECT remains available throughout the decision.
lock table
  erp.audit_logs,
  erp.cp6_laundry_qc_execution_context,
  erp.cp6_v2620_acl_capsule,
  erp.cp6_v2620_rollback_capsule,
  erp.fg_lots,
  erp.fg_stock_movements,
  erp.idempotency_requests,
  erp.laundry_deliveries,
  erp.laundry_delivery_batch_size_lines,
  erp.laundry_delivery_lines,
  erp.laundry_receipts,
  erp.laundry_receipt_batch_size_lines,
  erp.laundry_receipt_bs_product_allocations,
  erp.laundry_receipt_lines,
  erp.products,
  erp.qc_inspections,
  erp.qc_inspection_items,
  erp.vendor_invoice_items,
  erp.vendor_invoices,
  erp.wip_stage_events
in share row exclusive mode;

do $rollback_guard$
declare
  v_installed_at timestamptz;
  v_fact_count bigint;
  v_request_count bigint;
  v_audit_count bigint;
begin
  select installed_at into v_installed_at
  from erp.schema_migrations where version='v2.6.20';
  if v_installed_at is null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.19c') then
    raise exception 'v2.6.20 rollback refused: required application markers are absent';
  end if;
  if exists(
       select 1 from erp.schema_migrations m
       where m.version<>'v2.6.20' and m.installed_at>v_installed_at
     ) or exists(
       select 1 from supabase_migrations.schema_migrations m
       where m.version>'20260904111157'
     ) then
    raise exception 'v2.6.20 rollback refused: a successor migration is already installed';
  end if;
  if to_regclass('erp.cp6_v2620_rollback_capsule') is null
     or (select count(*) from erp.cp6_v2620_rollback_capsule)<>9
     or to_regclass('erp.cp6_v2620_acl_capsule') is null
     or (select count(*) from erp.cp6_v2620_acl_capsule)<>13 then
    raise exception 'v2.6.20 rollback refused: exact rollback capsule is missing';
  end if;
  if exists(
    select 1 from erp.cp6_v2620_rollback_capsule c
    where c.definition_sha256 is distinct from encode(extensions.digest(
      convert_to(c.object_definition,'UTF8'),'sha256'
    ),'hex')
      or c.installed_definition_sha256 is null
      or c.installed_definition_sha256 is distinct from case
        when c.object_kind='FUNCTION' then encode(extensions.digest(convert_to(
          pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
        ),'sha256'),'hex')
        else encode(extensions.digest(convert_to(
          pg_get_viewdef(to_regclass(c.object_regidentity),true),'UTF8'
        ),'sha256'),'hex')
      end
  ) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20 installed object/capsule drift';
  end if;
  if exists(
    select 1 from erp.cp6_v2620_acl_capsule c
    where case c.object_kind
      when 'FUNCTION' then to_regprocedure(c.object_regidentity) is null
        or pg_get_userbyid((select p.proowner from pg_proc p
          where p.oid=to_regprocedure(c.object_regidentity))) is distinct from c.owner_snapshot
      else to_regclass(c.object_regidentity) is null
        or pg_get_userbyid((select x.relowner from pg_class x
          where x.oid=to_regclass(c.object_regidentity))) is distinct from c.owner_snapshot
    end
  ) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20 browser-writer ACL capsule target drift';
  end if;

  select
    (select count(*) from erp.laundry_delivery_batch_size_lines)
    +(select count(*) from erp.laundry_receipt_batch_size_lines)
    +(select count(*) from erp.qc_inspection_items
      where source_laundry_receipt_batch_size_line_id is not null)
    +(select count(*) from erp.cp6_laundry_qc_execution_context)
    +(select count(*) from erp.wip_stage_events where source_type in(
      'CP6_LAUNDRY_BS_SIZE_LINE',
      'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL',
      'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL',
      'CP6_LAUNDRY_BS_WIP_REVERSAL'
    ))
    +(select count(*) from erp.products p
      where p.created_at>=v_installed_at or p.updated_at>=v_installed_at)
    into v_fact_count;
  select count(*) into v_request_count
  from erp.idempotency_requests r
  where r.operation_name like 'cp6_laundry_qc_action_v1:%'
    and r.created_at>=v_installed_at;
  select count(*) into v_audit_count
  from erp.audit_logs a
  where a.changed_at>=v_installed_at
    and a.entity_type in(
      'laundry_delivery_batch_size_lines','laundry_receipt_batch_size_lines',
      'laundry_deliveries','laundry_delivery_lines','laundry_receipts',
      'laundry_receipt_lines','laundry_receipt_bs_product_allocations',
      'qc_inspections','qc_inspection_items','fg_lots','fg_stock_movements',
      'products'
    );
  if v_fact_count<>0 or v_request_count<>0 or v_audit_count<>0 then
    raise exception using
      message='v2.6.20 rollback refused: post-install CP6 physical/financial/stock/HPP/idempotency/audit history exists',
      detail=format('facts=%s, idempotency_requests=%s, audit_rows=%s',
        v_fact_count,v_request_count,v_audit_count);
  end if;
end
$rollback_guard$;

drop function public.erp_get_laundry_qc_workspace_v1(text,text);
drop function public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint);

-- Restore exact pre-install function definitions and ACLs before removing the
-- CP6 execution context they no longer reference.
do $restore_functions$
declare
  r erp.cp6_v2620_rollback_capsule%rowtype;
  a record;
  x record;
  v_grantee text;
begin
  for r in select * from erp.cp6_v2620_rollback_capsule
    where object_kind='FUNCTION' order by object_identity
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
        raise exception 'v2.6.20 rollback refused: unsupported function privilege %',a.privilege_type;
      end if;
      v_grantee:=case when a.grantee=0 then 'PUBLIC'
        else format('%I',pg_get_userbyid(a.grantee)) end;
      execute format('grant execute on function %s to %s%s',
        r.object_identity,v_grantee,
        case when a.is_grantable then ' with grant option' else '' end);
    end loop;
  end loop;
end
$restore_functions$;

do $restore_view$
declare
  r erp.cp6_v2620_rollback_capsule%rowtype;
  a record;
  x record;
  v_grantee text;
begin
  for r in select * from erp.cp6_v2620_rollback_capsule
    where object_kind='VIEW' order by object_identity
  loop
    execute format('create or replace view %s with (security_invoker=%s) as %s',
      r.object_identity,case when r.security_invoker_snapshot then 'true' else 'false' end,
      r.object_definition);
    execute format('alter view %s owner to %I',r.object_identity,r.owner_snapshot);
    for x in
      select distinct acl.grantee
      from pg_class c
      cross join lateral aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) acl
      where c.oid=to_regclass(r.object_regidentity)
    loop
      v_grantee:=case when x.grantee=0 then 'PUBLIC'
        else format('%I',pg_get_userbyid(x.grantee)) end;
      execute format('revoke all privileges on table %s from %s',r.object_identity,v_grantee);
    end loop;
    for a in
      select acl.* from aclexplode(coalesce(
        r.acl_snapshot::aclitem[],
        acldefault('r',(select oid from pg_roles where rolname=r.owner_snapshot))
      )) acl order by acl.grantee,acl.privilege_type,acl.is_grantable
    loop
      v_grantee:=case when a.grantee=0 then 'PUBLIC'
        else format('%I',pg_get_userbyid(a.grantee)) end;
      execute format('grant %s on table %s to %s%s',
        a.privilege_type,r.object_identity,v_grantee,
        case when a.is_grantable then ' with grant option' else '' end);
    end loop;
  end loop;
end
$restore_view$;

-- Restore the exact effective predecessor ACL for every direct Laundry/QC
-- writer closed by CP6.  This executes inside the rollback transaction, so no
-- intermediate grant is externally visible.
do $restore_browser_writer_acls$
declare
  r erp.cp6_v2620_acl_capsule%rowtype;
  a record;
  x record;
  v_grantee text;
  v_owner oid;
begin
  for r in select * from erp.cp6_v2620_acl_capsule order by object_kind,object_identity
  loop
    select oid into v_owner from pg_roles where rolname=r.owner_snapshot;
    if v_owner is null then
      raise exception 'v2.6.20 rollback refused: ACL owner role % vanished',r.owner_snapshot;
    end if;
    if r.object_kind='FUNCTION' then
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
      for a in select acl.* from aclexplode(coalesce(
        r.acl_snapshot::aclitem[],acldefault('f',v_owner)
      )) acl order by acl.grantee,acl.privilege_type,acl.is_grantable
      loop
        if a.privilege_type<>'EXECUTE' then
          raise exception 'v2.6.20 rollback refused: unsupported function ACL %',a.privilege_type;
        end if;
        v_grantee:=case when a.grantee=0 then 'PUBLIC'
          else format('%I',pg_get_userbyid(a.grantee)) end;
        execute format('grant execute on function %s to %s%s',
          r.object_identity,v_grantee,
          case when a.is_grantable then ' with grant option' else '' end);
      end loop;
    else
      execute format('alter table %s owner to %I',r.object_identity,r.owner_snapshot);
      for x in
        select distinct acl.grantee
        from pg_class c
        cross join lateral aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) acl
        where c.oid=to_regclass(r.object_regidentity)
      loop
        v_grantee:=case when x.grantee=0 then 'PUBLIC'
          else format('%I',pg_get_userbyid(x.grantee)) end;
        execute format('revoke all privileges on table %s from %s',r.object_identity,v_grantee);
      end loop;
      for a in select acl.* from aclexplode(coalesce(
        r.acl_snapshot::aclitem[],acldefault('r',v_owner)
      )) acl order by acl.grantee,acl.privilege_type,acl.is_grantable
      loop
        v_grantee:=case when a.grantee=0 then 'PUBLIC'
          else format('%I',pg_get_userbyid(a.grantee)) end;
        execute format('grant %s on table %s to %s%s',
          a.privilege_type,r.object_identity,v_grantee,
          case when a.is_grantable then ' with grant option' else '' end);
      end loop;
    end if;
  end loop;
end
$restore_browser_writer_acls$;

drop function erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint);
drop function erp.get_laundry_qc_workspace_v1(text,text);

drop trigger trg_append_cp6_laundry_wip_reversal_v2620 on erp.laundry_receipts;
drop trigger trg_append_cp6_laundry_wip_reversal_v2620 on erp.laundry_deliveries;
drop function erp.append_cp6_laundry_wip_reversal_v2620();
drop index erp.uq_cp6_wip_reversal_source_v2620;
drop index erp.idx_products_brand_sku_effective_v2620;

drop trigger trg_01_guard_cp6_qc_batch_size_source_v2620 on erp.qc_inspection_items;
drop function erp.guard_cp6_qc_batch_size_source_v2620();
drop trigger trg_guard_cp6_delivery_lineage_on_post_v2620 on erp.laundry_deliveries;
drop trigger trg_guard_cp6_receipt_lineage_on_post_v2620 on erp.laundry_receipts;
drop trigger trg_guard_cp6_vendor_invoice_receipt_on_post_v2620 on erp.vendor_invoices;
drop trigger trg_guard_cp6_delivery_batch_size_v2620 on erp.laundry_delivery_batch_size_lines;
drop trigger trg_guard_cp6_receipt_batch_size_v2620 on erp.laundry_receipt_batch_size_lines;
drop trigger trg_audit_cp6_delivery_batch_size_v2620 on erp.laundry_delivery_batch_size_lines;
drop trigger trg_audit_cp6_receipt_batch_size_v2620 on erp.laundry_receipt_batch_size_lines;
drop function erp.guard_cp6_laundry_delivery_batch_size_v2620();
drop function erp.guard_cp6_laundry_receipt_batch_size_v2620();
drop function erp.guard_cp6_laundry_lineage_on_post_v2620();
drop function erp.guard_cp6_laundry_receipt_lineage_on_post_v2620();
drop function erp.guard_cp6_vendor_invoice_receipt_on_post_v2620();

alter table erp.qc_inspection_items drop constraint qc_items_cp6_source_batch_size_fkey;
drop index erp.idx_qc_items_cp6_source_batch_size_v2620;
alter table erp.qc_inspection_items drop column source_laundry_receipt_batch_size_line_id;

drop table erp.laundry_receipt_batch_size_lines;
drop table erp.laundry_delivery_batch_size_lines;
drop table erp.cp6_laundry_qc_execution_context;

drop trigger trg_00_bump_row_version_v2620 on erp.laundry_deliveries;
drop trigger trg_00_bump_row_version_v2620 on erp.qc_inspections;
alter table erp.laundry_deliveries
  drop constraint laundry_deliveries_row_version_v2620_check,
  drop column row_version;
alter table erp.qc_inspections
  drop constraint qc_inspections_row_version_v2620_check,
  drop column row_version;

do $restore_guard$
declare
  r erp.cp6_v2620_rollback_capsule%rowtype;
  a erp.cp6_v2620_acl_capsule%rowtype;
  v_actual text[];
  v_expected text[];
  v_owner oid;
begin
  for r in select * from erp.cp6_v2620_rollback_capsule order by object_identity
  loop
    if r.object_kind='FUNCTION' and encode(extensions.digest(convert_to(
         pg_get_functiondef(to_regprocedure(r.object_regidentity)),'UTF8'
       ),'sha256'),'hex') is distinct from r.definition_sha256 then
      raise exception 'v2.6.20 rollback failed exact function restoration for %',r.object_identity;
    elsif r.object_kind='VIEW' and encode(extensions.digest(convert_to(
         pg_get_viewdef(to_regclass(r.object_regidentity),true),'UTF8'
       ),'sha256'),'hex') is distinct from r.definition_sha256 then
      raise exception 'v2.6.20 rollback failed exact view restoration for %',r.object_identity;
    end if;
  end loop;
  for a in select * from erp.cp6_v2620_acl_capsule order by object_kind,object_identity
  loop
    select oid into v_owner from pg_roles where rolname=a.owner_snapshot;
    if a.object_kind='FUNCTION' then
      select array_agg(acl::text order by acl::text) into v_actual
      from pg_proc p cross join lateral unnest(coalesce(
        p.proacl,acldefault('f',p.proowner)
      )) x(acl) where p.oid=to_regprocedure(a.object_regidentity);
      select array_agg(acl::text order by acl::text) into v_expected
      from unnest(coalesce(a.acl_snapshot::aclitem[],acldefault('f',v_owner))) x(acl);
    else
      select array_agg(acl::text order by acl::text) into v_actual
      from pg_class c cross join lateral unnest(coalesce(
        c.relacl,acldefault('r',c.relowner)
      )) x(acl) where c.oid=to_regclass(a.object_regidentity);
      select array_agg(acl::text order by acl::text) into v_expected
      from unnest(coalesce(a.acl_snapshot::aclitem[],acldefault('r',v_owner))) x(acl);
    end if;
    if v_actual is distinct from v_expected then
      raise exception 'v2.6.20 rollback failed exact ACL restoration for %',a.object_identity;
    end if;
  end loop;
  if to_regclass('erp.laundry_delivery_batch_size_lines') is not null
     or to_regclass('erp.laundry_receipt_batch_size_lines') is not null
     or to_regclass('erp.cp6_laundry_qc_execution_context') is not null
     or to_regclass('erp.uq_cp6_wip_reversal_source_v2620') is not null
     or to_regclass('erp.idx_products_brand_sku_effective_v2620') is not null
     or to_regprocedure('erp.append_cp6_laundry_wip_reversal_v2620()') is not null
     or to_regprocedure('erp.guard_cp6_vendor_invoice_receipt_on_post_v2620()') is not null
     or to_regprocedure('public.erp_get_laundry_qc_workspace_v1(text,text)') is not null
     or to_regprocedure('public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint)') is not null
     or exists(select 1 from information_schema.columns
       where table_schema='erp' and table_name='laundry_deliveries' and column_name='row_version')
     or exists(select 1 from information_schema.columns
       where table_schema='erp' and table_name='qc_inspections' and column_name='row_version')
     or exists(select 1 from information_schema.columns
       where table_schema='erp' and table_name='qc_inspection_items'
         and column_name='source_laundry_receipt_batch_size_line_id') then
    raise exception 'v2.6.20 rollback left CP6 schema residue';
  end if;
end
$restore_guard$;

delete from erp.schema_migrations where version='v2.6.20';
delete from supabase_migrations.schema_migrations m
where m.name='erp_v2_6_20_cp6_laundry_qc_fg_authoritative'
  and coalesce(encode(extensions.digest(
    convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
  ),'hex'),'')='4a252c7c895d031cbc92d656808a515294e18a923dc943e62e205a83c3ad5596';

drop table erp.cp6_v2620_acl_capsule;
drop table erp.cp6_v2620_rollback_capsule;
select pg_notify('pgrst','reload schema');
commit;
