-- ERP Garment v2.6.20 / CP6 Laundry, QC, and Final-SKU authoritative bridge.
--
-- Reliability Data adalah Dewa. Keuangan, stok, dan HPP adalah Raja.
-- Laporan keuangan termasuk di dalam wilayah Keuangan. This migration connects UX intent to immutable
-- batch/size facts without deleting or overwriting posted history.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

-- Serialize the entire identity-check/capsule/install boundary with every
-- well-formed migration writer.  Without this lock a second installer could
-- replace a predecessor after the drift guard but before its rollback bytes
-- are captured.
lock table erp.schema_migrations,
  erp.products,
  supabase_migrations.schema_migrations in share row exclusive mode;

do $guard$
declare
  v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.19c') then
    raise exception 'ERP v2.6.20 requires v2.6.19c first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20') then
    raise exception 'ERP v2.6.20 is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.cp6_v2620_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620_acl_capsule') is not null
     or to_regclass('erp.laundry_delivery_batch_size_lines') is not null
     or to_regclass('erp.laundry_receipt_batch_size_lines') is not null
     or to_regclass('erp.laundry_failed_wash_attempts') is not null
     or to_regclass('erp.laundry_failed_wash_batch_size_lines') is not null
     or to_regclass('erp.cp6_laundry_qc_execution_context') is not null
     or to_regclass('erp.idx_products_brand_sku_effective_v2620') is not null
     or to_regclass('erp.uq_cp6_wip_reversal_source_v2620') is not null
     or to_regprocedure('erp.append_cp6_laundry_wip_reversal_v2620()') is not null
     or to_regprocedure('erp.guard_cp6_vendor_invoice_receipt_on_post_v2620()') is not null
     or to_regprocedure('public.erp_get_laundry_qc_workspace_v1(text,text)') is not null
     or to_regprocedure('public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint)') is not null then
    raise exception 'ERP v2.6.20 target guard: prior CP6 residue exists';
  end if;
  if to_regclass('erp.cutting_distribution_batches') is null
     or to_regclass('erp.cutting_distribution_allocations') is null
     or to_regclass('erp.laundry_deliveries') is null
     or to_regclass('erp.laundry_receipts') is null
     or to_regclass('erp.qc_inspections') is null
     or to_regprocedure('erp.require_internal()') is null
     or to_regprocedure('erp.post_laundry_delivery(uuid)') is null
     or to_regprocedure('erp.post_laundry_receipt(uuid)') is null
     or to_regprocedure('erp.post_final_sku_allocation_v1(jsonb,uuid,bigint)') is null
     or to_regprocedure('erp.reverse_laundry_delivery(uuid,text)') is null
     or to_regprocedure('erp.reverse_laundry_receipt(uuid,text)') is null
     or to_regprocedure('erp.reverse_qc(uuid,text)') is null
     or to_regprocedure('erp.validate_product_identity_period()') is null
     or to_regprocedure('erp.run_v259_integrity_checks()') is null
     or to_regprocedure('erp.apply_migration_master_rows(uuid)') is null
     or to_regprocedure('erp._cp3_assert_closed_json_object(jsonb,text[],text[],text)') is null
     or to_regprocedure('erp.apply_cutting_correction_and_post_laundry(uuid,uuid,text,text,text,jsonb,timestamp with time zone)') is null
     or to_regprocedure('erp.post_laundry_receipt_v2(uuid,uuid,bigint,text)') is null
     or to_regprocedure('erp.save_laundry_receipt_draft_v2(jsonb,uuid,bigint)') is null
     or to_regprocedure('erp.post_qc(uuid)') is null
     or to_regprocedure('erp.post_fg_partial_completion_v2(jsonb,uuid,bigint)') is null
     or to_regprocedure('erp.post_fg_partial_completion_v2_legacy_v2610(jsonb,uuid,bigint)') is null
     or to_regprocedure('erp.post_vendor_invoice(uuid)') is null
     or to_regprocedure('erp.reverse_vendor_invoice(uuid,text)') is null
     or to_regprocedure('erp.desired_laundry_accrual(uuid)') is null
     or to_regprocedure('erp.sync_laundry_accrual(uuid,date)') is null
     or to_regprocedure('erp.rebuild_po_hpp(uuid,text)') is null
     or to_regprocedure('erp.propagate_conversion_hpp_for_po(uuid)') is null
     or to_regprocedure('erp.sync_po_hpp_to_gl(uuid,date)') is null
     or to_regprocedure('erp.post_journal(text,uuid,date,text,jsonb)') is null
     or to_regprocedure('erp.reverse_journal(uuid,text)') is null then
    raise exception 'ERP v2.6.20 target guard: canonical Laundry/QC dependencies are incomplete';
  end if;

  -- Do not install a stricter identity contract over ambiguous old rows. The
  -- products lock above keeps this decision stable until the new trigger is
  -- active. Cross-brand reuse of a SKU number is intentionally valid; only
  -- contradictions inside one Brand + SKU identity (or its version chain)
  -- fail closed. CP6 never guesses, merges, or rewrites historical products.
  if exists(
    select 1
    from erp.products a
    join erp.products b on a.id<b.id
    where (
      a.identity_root_id=b.identity_root_id
      or (
        a.identity_root_id<>b.identity_root_id
        and a.brand_id=b.brand_id
        and lower(btrim(a.sku))=lower(btrim(b.sku))
        and (
          a.size_id=b.size_id
          or a.model_id<>b.model_id
          or lower(btrim(a.color_name))<>lower(btrim(b.color_name))
        )
      )
      or (
        a.identity_root_id<>b.identity_root_id
        and a.model_id=b.model_id
        and a.brand_id=b.brand_id
        and lower(btrim(a.color_name))=lower(btrim(b.color_name))
        and a.size_id=b.size_id
      )
    )
      and tstzrange(
        a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)'
      ) && tstzrange(
        b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)'
      )
  ) or exists(
    select 1
    from erp.products p
    left join erp.products r on r.id=p.identity_root_id
    where r.id is null or r.identity_root_id<>r.id
  ) or exists(
    select 1
    from erp.products p
    left join erp.products old on old.id=p.supersedes_product_id
    where (p.id=p.identity_root_id and p.supersedes_product_id is not null)
       or (p.id<>p.identity_root_id and (
         p.supersedes_product_id is null
         or old.id is null
         or p.identity_root_id<>old.identity_root_id
         or old.effective_to is distinct from p.effective_from
       ))
  ) then
    raise exception 'ERP v2.6.20 pre-existing product identity ambiguity: repair Brand + SKU + Model history before install';
  end if;

  select md5(pg_get_functiondef('erp.require_internal()'::regprocedure)) into v_actual;
  if v_actual is distinct from '8027894e8403d6b5a289056e37151ee8' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: require_internal changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.post_laundry_delivery(uuid)'::regprocedure)) into v_actual;
  if v_actual is distinct from 'e8ae6b674bca5056932c9e55e87bce9f' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: post_laundry_delivery changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.post_laundry_receipt(uuid)'::regprocedure)) into v_actual;
  if v_actual is distinct from '55ff5dbf95b37dcfbd05b651defc3531' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: post_laundry_receipt changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.post_final_sku_allocation_v1(jsonb,uuid,bigint)'::regprocedure)) into v_actual;
  if v_actual is distinct from 'fb2ed5bb9239e18b2ae6649d8cda1ce3' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: post_final_sku_allocation changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('public.erp_post_final_sku_allocation_v1(jsonb,uuid,bigint)'::regprocedure)) into v_actual;
  if v_actual is distinct from '66cc50518b1f6613db77a039f5717b4c' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: public post_final_sku_allocation facade changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.validate_product_identity_period()'::regprocedure)) into v_actual;
  if v_actual is distinct from '7cdee5936a160a1e71a2aa2840da48c4' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: product identity validator changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.run_v259_integrity_checks()'::regprocedure)) into v_actual;
  if v_actual is distinct from '2ffff9a88888675822e7d8ab69674415' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: product identity checker changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.apply_migration_master_rows(uuid)'::regprocedure)) into v_actual;
  if v_actual is distinct from '0272a1db007565dcd49b95ed888afef7' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: master migration writer changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef(
    'erp._cp3_assert_closed_json_object(jsonb,text[],text[],text)'::regprocedure
  )) into v_actual;
  if v_actual is distinct from '2f8378ac4a05349829bfa3e2cc5aee72' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: closed JSON validator changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef(
    'erp.apply_cutting_correction_and_post_laundry(uuid,uuid,text,text,text,jsonb,timestamp with time zone)'::regprocedure
  )) into v_actual;
  if v_actual is distinct from '3e21ecd169627ff27ef52e38f1d8f502' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Laundry cutting bridge changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef(
    'erp.post_laundry_receipt_v2(uuid,uuid,bigint,text)'::regprocedure
  )) into v_actual;
  if v_actual is distinct from '1e2bcb68ebaaff2183631a5469248c6a' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Laundry receipt v2 writer changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef(
    'erp.save_laundry_receipt_draft_v2(jsonb,uuid,bigint)'::regprocedure
  )) into v_actual;
  if v_actual is distinct from '76d3f2681c6df98550b381edaff7e25a' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Laundry receipt draft writer changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.reverse_laundry_delivery(uuid,text)'::regprocedure)) into v_actual;
  if v_actual is distinct from 'aa63c57f6b8bb3c538a8998b1c6f600d' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Laundry delivery reversal changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.reverse_laundry_receipt(uuid,text)'::regprocedure)) into v_actual;
  if v_actual is distinct from '9072777adc4e8c3d2817d1bfece4bf8d' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Laundry receipt reversal changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.post_qc(uuid)'::regprocedure)) into v_actual;
  if v_actual is distinct from '4c307365b48248dd37fd4612890db8c8' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: QC posting changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.reverse_qc(uuid,text)'::regprocedure)) into v_actual;
  if v_actual is distinct from '1aef93b9b97bf59243f0a0e82f1cc698' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: QC reversal changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef(
    'erp.post_fg_partial_completion_v2(jsonb,uuid,bigint)'::regprocedure
  )) into v_actual;
  if v_actual is distinct from '1982eef2790eefeac5dd08033b60f62c' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Final-SKU partial posting changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef(
    'erp.post_fg_partial_completion_v2_legacy_v2610(jsonb,uuid,bigint)'::regprocedure
  )) into v_actual;
  if v_actual is distinct from '4704db79cbcd2ad70384c6dbdfe85572' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Final-SKU document-number writer changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.post_vendor_invoice(uuid)'::regprocedure)) into v_actual;
  if v_actual is distinct from 'b2e8ffa3e9caf72aaa101a34bded5001' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: vendor invoice posting changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.reverse_vendor_invoice(uuid,text)'::regprocedure)) into v_actual;
  if v_actual is distinct from '43cec1668118c4a9c30939be72cc45b5' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: vendor invoice reversal changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.desired_laundry_accrual(uuid)'::regprocedure)) into v_actual;
  if v_actual is distinct from '4ded5af2c9c604357d18c783b00dcdb9' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: desired Laundry accrual changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.sync_laundry_accrual(uuid,date)'::regprocedure)) into v_actual;
  if v_actual is distinct from '9d5afd8d5c23e81a924a87cb4ef0037d' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Laundry accrual synchronizer changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.rebuild_po_hpp(uuid,text)'::regprocedure)) into v_actual;
  if v_actual is distinct from 'bf5593c35375abb35c0c6d531ee375e6' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP rebuild changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.propagate_conversion_hpp_for_po(uuid)'::regprocedure)) into v_actual;
  if v_actual is distinct from 'f3c86a2a1d282927d9c9e1af1404fa93' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: conversion HPP propagation changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.sync_po_hpp_to_gl(uuid,date)'::regprocedure)) into v_actual;
  if v_actual is distinct from '0ecc997982964a03e0d8c93efcb9ddcc' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP-to-GL synchronizer changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.post_journal(text,uuid,date,text,jsonb)'::regprocedure)) into v_actual;
  if v_actual is distinct from 'dbf6138ccc575950fc6aed789863af8c' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: journal posting changed (%)',v_actual;
  end if;
  select md5(pg_get_functiondef('erp.reverse_journal(uuid,text)'::regprocedure)) into v_actual;
  if v_actual is distinct from '6ee9da4164624f08381415b01630f323' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: journal reversal changed (%)',v_actual;
  end if;
  select encode(extensions.digest(
    convert_to(pg_get_viewdef('erp.v_fg_partial_completion_progress'::regclass,true),'UTF8'),'sha256'
  ),'hex') into v_actual;
  -- pg_get_viewdef is not a parse/deparse fixed point. Permit only the exact
  -- live UAT 17.6 predecessor and the independently verified, semantically
  -- equivalent 17.6.1 immutable-catalog replay used by disposable CI.
  if coalesce(v_actual,'') not in(
    '7897479ca27144e599b6607b60f5b9bed08bdea57171ff6ba8ec81ce46f20037',
    'efb2d15345589645f2184c3a749da42acc11bad1d4585988c3e02c5c762464e6'
  ) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: FG progress view changed (%)',v_actual;
  end if;
  select encode(extensions.digest(
    convert_to(pg_get_viewdef('erp.v_wip_control_status_v1'::regclass,true),'UTF8'),'sha256'
  ),'hex') into v_actual;
  if coalesce(v_actual,'') not in(
    '2aa2bab69b86be921b022eaca8142a1523124c05bd639b8a641ccf572ac8ded4',
    'a823510e0e5e5f57dc124001db93ec9636e8120970281473e10fedc54089420a'
  ) then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: WIP control view changed (%)',v_actual;
  end if;
end
$guard$;

-- Exact pre-install definitions are retained so the reviewed rollback can
-- restore owner, ACL, and bytes instead of guessing an earlier state.
create table erp.cp6_v2620_rollback_capsule(
  object_kind text not null check(object_kind in('FUNCTION','VIEW')),
  object_identity text primary key,
  object_regidentity text not null unique,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  security_invoker_snapshot boolean,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.cp6_v2620_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620_rollback_capsule
  from public,anon,authenticated,service_role;

insert into erp.cp6_v2620_rollback_capsule(
  object_kind,object_identity,object_regidentity,object_definition,
  definition_sha256,acl_snapshot,owner_snapshot
)
select
  'FUNCTION',
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp.require_internal()'::regprocedure,
  'public.erp_post_final_sku_allocation_v1(jsonb,uuid,bigint)'::regprocedure,
  'erp.validate_product_identity_period()'::regprocedure,
  'erp.run_v259_integrity_checks()'::regprocedure,
  'erp.apply_migration_master_rows(uuid)'::regprocedure,
  'erp.desired_laundry_accrual(uuid)'::regprocedure,
  'erp.sync_laundry_accrual(uuid,date)'::regprocedure,
  'erp.rebuild_po_hpp(uuid,text)'::regprocedure,
  'erp.post_fg_partial_completion_v2_legacy_v2610(jsonb,uuid,bigint)'::regprocedure
);

insert into erp.cp6_v2620_rollback_capsule(
  object_kind,object_identity,object_regidentity,object_definition,
  definition_sha256,acl_snapshot,owner_snapshot,security_invoker_snapshot
)
select
  'VIEW',format('%I.%I',n.nspname,c.relname),format('%I.%I',n.nspname,c.relname),
  pg_get_viewdef(c.oid,true),
  encode(extensions.digest(convert_to(pg_get_viewdef(c.oid,true),'UTF8'),'sha256'),'hex'),
  case when c.relacl is null then null else array(select a::text from unnest(c.relacl) a) end,
  pg_get_userbyid(c.relowner),
  coalesce((select o.option_value='true' from pg_options_to_table(c.reloptions) o
            where o.option_name='security_invoker'),false)
from pg_class c
join pg_namespace n on n.oid=c.relnamespace
where c.oid in(
  'erp.v_fg_partial_completion_progress'::regclass,
  'erp.v_wip_control_status_v1'::regclass
);

do $capsule_guard$
begin
  if (select count(*) from erp.cp6_v2620_rollback_capsule)<>11
     or exists(
       select 1 from erp.cp6_v2620_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
     )
     or (select md5(c.object_definition) from erp.cp6_v2620_rollback_capsule c
         where c.object_regidentity='erp.require_internal()'::regprocedure::text)
          is distinct from '8027894e8403d6b5a289056e37151ee8'
     or (select md5(c.object_definition) from erp.cp6_v2620_rollback_capsule c
         where c.object_regidentity='public.erp_post_final_sku_allocation_v1(jsonb,uuid,bigint)'::regprocedure::text)
          is distinct from '66cc50518b1f6613db77a039f5717b4c'
     or (select md5(c.object_definition) from erp.cp6_v2620_rollback_capsule c
         where c.object_regidentity='erp.validate_product_identity_period()'::regprocedure::text)
          is distinct from '7cdee5936a160a1e71a2aa2840da48c4'
     or (select md5(c.object_definition) from erp.cp6_v2620_rollback_capsule c
         where c.object_regidentity='erp.run_v259_integrity_checks()'::regprocedure::text)
          is distinct from '2ffff9a88888675822e7d8ab69674415'
     or (select md5(c.object_definition) from erp.cp6_v2620_rollback_capsule c
         where c.object_regidentity='erp.apply_migration_master_rows(uuid)'::regprocedure::text)
          is distinct from '0272a1db007565dcd49b95ed888afef7'
     or (select md5(c.object_definition) from erp.cp6_v2620_rollback_capsule c
         where c.object_regidentity='erp.desired_laundry_accrual(uuid)'::regprocedure::text)
          is distinct from '4ded5af2c9c604357d18c783b00dcdb9'
     or (select md5(c.object_definition) from erp.cp6_v2620_rollback_capsule c
         where c.object_regidentity='erp.sync_laundry_accrual(uuid,date)'::regprocedure::text)
          is distinct from '9d5afd8d5c23e81a924a87cb4ef0037d'
     or (select md5(c.object_definition) from erp.cp6_v2620_rollback_capsule c
         where c.object_regidentity='erp.rebuild_po_hpp(uuid,text)'::regprocedure::text)
          is distinct from 'bf5593c35375abb35c0c6d531ee375e6'
     or (select md5(c.object_definition) from erp.cp6_v2620_rollback_capsule c
         where c.object_regidentity='erp.post_fg_partial_completion_v2_legacy_v2610(jsonb,uuid,bigint)'::regprocedure::text)
          is distinct from '4704db79cbcd2ad70384c6dbdfe85572'
     or coalesce((select c.definition_sha256 from erp.cp6_v2620_rollback_capsule c
         where c.object_regidentity='erp.v_fg_partial_completion_progress'),'') not in(
          '7897479ca27144e599b6607b60f5b9bed08bdea57171ff6ba8ec81ce46f20037',
          'efb2d15345589645f2184c3a749da42acc11bad1d4585988c3e02c5c762464e6'
        )
     or coalesce((select c.definition_sha256 from erp.cp6_v2620_rollback_capsule c
         where c.object_regidentity='erp.v_wip_control_status_v1'),'') not in(
          '2aa2bab69b86be921b022eaca8142a1523124c05bd639b8a641ccf572ac8ded4',
          'a823510e0e5e5f57dc124001db93ec9636e8120970281473e10fedc54089420a'
        ) then
    raise exception 'ERP v2.6.20 rollback capsule is incomplete or invalid';
  end if;
end
$capsule_guard$;

-- Browser-facing Laundry/QC is now one aggregate RPC boundary. Preserve the
-- exact predecessor ACLs so rollback can restore them, then close every old
-- table/function mutation path that could bypass batch/size conservation.
create table erp.cp6_v2620_acl_capsule(
  object_kind text not null check(object_kind in('FUNCTION','TABLE')),
  object_identity text primary key,
  object_regidentity text not null unique,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.cp6_v2620_acl_capsule enable row level security;
revoke all on table erp.cp6_v2620_acl_capsule
  from public,anon,authenticated,service_role;

insert into erp.cp6_v2620_acl_capsule(
  object_kind,object_identity,object_regidentity,acl_snapshot,owner_snapshot
)
select 'FUNCTION',
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,
  case when p.proacl is null then null else array(
    select a::text from unnest(p.proacl) a order by a::text
  ) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp.apply_cutting_correction_and_post_laundry(uuid,uuid,text,text,text,jsonb,timestamp with time zone)'::regprocedure,
  'erp.post_laundry_delivery(uuid)'::regprocedure,
  'erp.post_laundry_receipt_v2(uuid,uuid,bigint,text)'::regprocedure,
  'erp.save_laundry_receipt_draft_v2(jsonb,uuid,bigint)'::regprocedure,
  'erp.reverse_laundry_delivery(uuid,text)'::regprocedure,
  'erp.reverse_laundry_receipt(uuid,text)'::regprocedure,
  'erp.post_qc(uuid)'::regprocedure,
  'erp.reverse_qc(uuid,text)'::regprocedure,
  'erp.post_fg_partial_completion_v2(jsonb,uuid,bigint)'::regprocedure
);

insert into erp.cp6_v2620_acl_capsule(
  object_kind,object_identity,object_regidentity,acl_snapshot,owner_snapshot
)
select 'TABLE',format('%I.%I',n.nspname,c.relname),c.oid::regclass::text,
  case when c.relacl is null then null else array(
    select a::text from unnest(c.relacl) a order by a::text
  ) end,
  pg_get_userbyid(c.relowner)
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where c.oid in(
  'erp.laundry_deliveries'::regclass,
  'erp.laundry_delivery_lines'::regclass,
  'erp.qc_inspections'::regclass,
  'erp.qc_inspection_items'::regclass
);

do $acl_capsule_guard$
begin
  if (select count(*) from erp.cp6_v2620_acl_capsule)<>13 then
    raise exception 'ERP v2.6.20 browser-writer ACL capsule is incomplete';
  end if;
end
$acl_capsule_guard$;

revoke insert,update,delete on table
  erp.laundry_deliveries,erp.laundry_delivery_lines,
  erp.qc_inspections,erp.qc_inspection_items
from authenticated;
revoke all on function
  erp.apply_cutting_correction_and_post_laundry(uuid,uuid,text,text,text,jsonb,timestamp with time zone),
  erp.post_laundry_delivery(uuid),
  erp.post_laundry_receipt_v2(uuid,uuid,bigint,text),
  erp.save_laundry_receipt_draft_v2(jsonb,uuid,bigint),
  erp.reverse_laundry_delivery(uuid,text),
  erp.reverse_laundry_receipt(uuid,text),
  erp.post_qc(uuid),
  erp.reverse_qc(uuid,text),
  erp.post_fg_partial_completion_v2(jsonb,uuid,bigint)
from authenticated;

alter table erp.laundry_deliveries
  add column row_version bigint not null default 1,
  add constraint laundry_deliveries_row_version_v2620_check check(row_version>0);
alter table erp.qc_inspections
  add column row_version bigint not null default 1,
  add constraint qc_inspections_row_version_v2620_check check(row_version>0);
alter table erp.qc_inspection_items
  add column source_laundry_receipt_batch_size_line_id uuid;

create trigger trg_00_bump_row_version_v2620
before update on erp.laundry_deliveries
for each row execute function erp.bump_row_version();
create trigger trg_00_bump_row_version_v2620
before update on erp.qc_inspections
for each row execute function erp.bump_row_version();

create table erp.laundry_delivery_batch_size_lines(
  id uuid primary key default gen_random_uuid(),
  delivery_line_id uuid not null references erp.laundry_delivery_lines(id) on delete restrict,
  distribution_batch_id uuid not null references erp.cutting_distribution_batches(id) on delete restrict,
  size_id uuid not null references erp.sizes(id) on delete restrict,
  qty_sent_pcs integer not null check(qty_sent_pcs>0),
  created_by uuid not null references erp.app_users(id) on delete restrict,
  created_at timestamptz not null default clock_timestamp(),
  unique(delivery_line_id,distribution_batch_id,size_id)
);
create index idx_laundry_delivery_batch_size_source_v2620
  on erp.laundry_delivery_batch_size_lines(distribution_batch_id,size_id,delivery_line_id);

create table erp.laundry_receipt_batch_size_lines(
  id uuid primary key default gen_random_uuid(),
  receipt_line_id uuid not null references erp.laundry_receipt_lines(id) on delete restrict,
  delivery_batch_size_line_id uuid not null references erp.laundry_delivery_batch_size_lines(id) on delete restrict,
  size_id uuid not null references erp.sizes(id) on delete restrict,
  qty_good_received integer not null default 0 check(qty_good_received>=0),
  qty_bs_laundry integer not null default 0 check(qty_bs_laundry>=0),
  bs_product_id uuid references erp.products(id) on delete restrict,
  created_by uuid not null references erp.app_users(id) on delete restrict,
  created_at timestamptz not null default clock_timestamp(),
  check(qty_good_received+qty_bs_laundry>0),
  check((qty_bs_laundry=0 and bs_product_id is null) or (qty_bs_laundry>0 and bs_product_id is not null)),
  unique(receipt_line_id,delivery_batch_size_line_id)
);
create index idx_laundry_receipt_batch_size_source_v2620
  on erp.laundry_receipt_batch_size_lines(delivery_batch_size_line_id,receipt_line_id);

-- A paid failed wash is a service fact, not a fake physical receipt.  The
-- receipt header/line is retained only as the canonical vendor-invoice source;
-- exact attempted pieces live here and never enter GOOD, BS, QC, or FG.
create table erp.laundry_failed_wash_attempts(
  id uuid primary key default gen_random_uuid(),
  receipt_id uuid not null unique references erp.laundry_receipts(id) on delete restrict,
  receipt_line_id uuid not null unique references erp.laundry_receipt_lines(id) on delete restrict,
  delivery_id uuid not null references erp.laundry_deliveries(id) on delete restrict,
  custody_outcome text not null check(custody_outcome in('RETRY_AT_VENDOR','RETURN_UNPROCESSED')),
  qty_attempted_pcs integer not null check(qty_attempted_pcs>0),
  return_wip_event_id uuid unique references erp.wip_stage_events(id) on delete restrict,
  reason text not null check(length(btrim(reason))>=4),
  created_by uuid not null references erp.app_users(id) on delete restrict,
  created_at timestamptz not null default clock_timestamp(),
  check((custody_outcome='RETRY_AT_VENDOR' and return_wip_event_id is null)
     or custody_outcome='RETURN_UNPROCESSED')
);

create table erp.laundry_failed_wash_batch_size_lines(
  id uuid primary key default gen_random_uuid(),
  attempt_id uuid not null references erp.laundry_failed_wash_attempts(id) on delete restrict,
  delivery_batch_size_line_id uuid not null references erp.laundry_delivery_batch_size_lines(id) on delete restrict,
  size_id uuid not null references erp.sizes(id) on delete restrict,
  qty_attempted_pcs integer not null check(qty_attempted_pcs>0),
  created_by uuid not null references erp.app_users(id) on delete restrict,
  created_at timestamptz not null default clock_timestamp(),
  unique(attempt_id,delivery_batch_size_line_id)
);
create index idx_failed_wash_source_size_v2620
  on erp.laundry_failed_wash_batch_size_lines(delivery_batch_size_line_id,attempt_id);
create index idx_products_brand_sku_effective_v2620
  on erp.products(brand_id,lower(btrim(sku)),size_id,effective_from,effective_to,id);

-- The predecessor derived a UNIQUE document number from only the first ten
-- UUID hex characters. Keep its transactional/idempotency behavior intact,
-- but eliminate that 40-bit collision surface for every CP6 Final-SKU post.
CREATE OR REPLACE FUNCTION erp.post_fg_partial_completion_v2_legacy_v2610(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'extensions', 'pg_temp'
AS $function$
declare
  v_operation constant text := 'post_fg_partial_completion_v2';
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_group erp.cutting_groups%rowtype;
  v_po_status text;
  v_group_id uuid := nullif(p_payload->>'cutting_group_id', '')::uuid;
  v_destination_location_id uuid := nullif(p_payload->>'destination_location_id', '')::uuid;
  v_physical_at timestamptz := coalesce(
    nullif(p_payload->>'physical_at', '')::timestamptz,
    clock_timestamp()
  );
  v_reason text := nullif(btrim(p_payload->>'reason'), '');
  v_lines jsonb := p_payload->'lines';
  v_qc_id uuid := gen_random_uuid();
  v_inspection_number text;
  v_total_qty bigint;
  v_good_qty bigint;
  v_bs_qty bigint;
  v_effective_qty bigint;
  v_prior_qty bigint;
  v_stock_qty bigint;
  v_stock_event_count bigint;
  v_progress erp.v_fg_partial_completion_progress%rowtype;
begin
  perform erp.require_internal();
  if p_expected_version is null then
    raise exception 'expected_version is required';
  end if;
  if v_group_id is null then
    raise exception 'cutting_group_id is required';
  end if;
  if v_destination_location_id is null then
    raise exception 'destination_location_id is required';
  end if;
  if v_reason is null then
    raise exception 'Completion reason is required';
  end if;
  if v_physical_at > clock_timestamp() + interval '5 minutes' then
    raise exception 'Tanggal/jam penyelesaian FG berada di masa depan';
  end if;
  if jsonb_typeof(v_lines) <> 'array' or jsonb_array_length(v_lines) = 0 then
    raise exception 'Partial FG completion requires at least one line';
  end if;

  v_hash := erp._request_hash(jsonb_build_object(
    'payload', p_payload,
    'expected_version', p_expected_version
  ));
  v_cached := erp._idempotency_begin(v_operation, p_client_request_id, v_hash);
  if v_cached is not null then
    return v_cached;
  end if;

  perform set_config('app.change_reason', v_reason, true);

  select * into v_group
  from erp.cutting_groups
  where id = v_group_id
  for update;
  if v_group.id is null then
    raise exception 'Potongan not found';
  end if;
  if v_group.row_version <> p_expected_version then
    raise exception 'STALE_VERSION expected %, current %',
      p_expected_version, v_group.row_version;
  end if;

  select status into v_po_status
  from erp.production_orders
  where id = v_group.po_id
  for update;
  if v_po_status in ('FINISHED', 'CANCELLED') then
    raise exception 'PO berstatus % dan tidak menerima penyelesaian FG baru', v_po_status;
  end if;

  if not exists (
    select 1 from erp.locations l
    where l.id = v_destination_location_id
      and l.is_active = true
      and l.location_type = 'FG_WAREHOUSE'
  ) then
    raise exception 'Destination must be an active FG warehouse';
  end if;

  if exists (
    select 1
    from jsonb_to_recordset(v_lines) as x(
      final_product_id uuid,
      qty_good_pcs integer,
      qty_bs_pcs integer,
      source_laundry_receipt_line_id uuid,
      notes text
    )
    where coalesce(x.qty_good_pcs, 0) < 0
       or coalesce(x.qty_bs_pcs, 0) < 0
       or coalesce(x.qty_good_pcs, 0) + coalesce(x.qty_bs_pcs, 0) <= 0
       or x.final_product_id is null
  ) then
    raise exception 'Every completion line requires a SKU and a positive GOOD/BS quantity';
  end if;

  if exists (
    select 1
    from jsonb_to_recordset(v_lines) as x(
      final_product_id uuid,
      qty_good_pcs integer,
      qty_bs_pcs integer,
      source_laundry_receipt_line_id uuid,
      notes text
    )
    group by x.final_product_id, x.source_laundry_receipt_line_id
    having count(*) > 1
  ) then
    raise exception 'Duplicate SKU and laundry source lines are not allowed';
  end if;

  select
    sum(coalesce(x.qty_good_pcs, 0) + coalesce(x.qty_bs_pcs, 0))::bigint,
    sum(coalesce(x.qty_good_pcs, 0))::bigint,
    sum(coalesce(x.qty_bs_pcs, 0))::bigint
  into v_total_qty, v_good_qty, v_bs_qty
  from jsonb_to_recordset(v_lines) as x(
    final_product_id uuid,
    qty_good_pcs integer,
    qty_bs_pcs integer,
    source_laundry_receipt_line_id uuid,
    notes text
  );

  select effective_qty_pcs, qc_accounted_qty_pcs
  into v_effective_qty, v_prior_qty
  from erp.v_fg_partial_completion_progress
  where cutting_group_id = v_group.id;
  if coalesce(v_effective_qty, 0) <= 0 then
    raise exception 'Potongan has no effective quantity available for FG';
  end if;
  if coalesce(v_prior_qty, 0) + coalesce(v_total_qty, 0) > v_effective_qty then
    raise exception
      'Qty penyelesaian melebihi sisa Potongan. Efektif %, sudah diposting %, input %.',
      v_effective_qty, coalesce(v_prior_qty, 0), coalesce(v_total_qty, 0);
  end if;

  -- The request UUID is already the idempotency identity. Use all 128 bits
  -- in the human document key: truncating to 40 bits lets distinct valid
  -- requests collide and rejects a real posting at the unique constraint.
  v_inspection_number := 'FGP-'
    || to_char(v_physical_at, 'YYMMDD') || '-'
    || upper(replace(p_client_request_id::text, '-', ''));

  insert into erp.qc_inspections(
    id, inspection_number, po_id, physical_at, status,
    notes, created_by, destination_location_id
  ) values (
    v_qc_id, v_inspection_number, v_group.po_id, v_physical_at, 'DRAFT',
    'Partial FG completion: ' || v_reason,
    erp.current_app_user_id(), v_destination_location_id
  );

  insert into erp.qc_inspection_items(
    inspection_id, cutting_group_id, source_laundry_receipt_line_id,
    final_product_id, qty_good_pcs, qty_bs_pcs, notes
  )
  select
    v_qc_id,
    v_group.id,
    x.source_laundry_receipt_line_id,
    x.final_product_id,
    coalesce(x.qty_good_pcs, 0),
    coalesce(x.qty_bs_pcs, 0),
    nullif(btrim(x.notes), '')
  from jsonb_to_recordset(v_lines) as x(
    final_product_id uuid,
    qty_good_pcs integer,
    qty_bs_pcs integer,
    source_laundry_receipt_line_id uuid,
    notes text
  );

  perform erp.post_qc(v_qc_id);

  -- Invalidate stale partial-completion drafts after every successful posting.
  update erp.cutting_groups
  set updated_at = clock_timestamp()
  where id = v_group.id
  returning * into v_group;

  select * into v_progress
  from erp.v_fg_partial_completion_progress
  where cutting_group_id = v_group.id;

  select
    coalesce(sum(m.qty_signed), 0)::bigint,
    count(*)::bigint
  into v_stock_qty, v_stock_event_count
  from erp.fg_stock_movements m
  where m.movement_type = 'QC_GOOD'
    and m.source_type = 'QC_ITEM'
    and m.source_id in (
      select i.id from erp.qc_inspection_items i where i.inspection_id = v_qc_id
    );

  v_response := jsonb_build_object(
    'qc_inspection_id', v_qc_id,
    'inspection_number', v_inspection_number,
    'cutting_group_id', v_group.id,
    'po_id', v_group.po_id,
    'completion_status', v_progress.completion_status,
    'posted_qty_pcs', v_total_qty,
    'good_qty_pcs', v_good_qty,
    'bs_qty_pcs', v_bs_qty,
    'fg_stock_in_qty_pcs', v_stock_qty,
    'fg_stock_event_count', v_stock_event_count,
    'cumulative_qc_qty_pcs', v_progress.qc_accounted_qty_pcs,
    'remaining_qc_qty_pcs', v_progress.remaining_qc_qty_pcs,
    'completion_count', v_progress.completion_count,
    'row_version', v_group.row_version,
    'document_status', 'POSTED'
  );

  return erp._idempotency_complete(v_operation, p_client_request_id, v_response);
end;
$function$;

alter function erp.post_fg_partial_completion_v2_legacy_v2610(jsonb,uuid,bigint)
  owner to postgres;

-- The delivery rate is only a forecast for pieces whose actual process is not
-- known yet.  Once a POSTED receipt records an ESTIMATED actual process/rate,
-- both HPP and the unbilled accrual must use that same immutable receipt cost.
-- FINAL receipt cost has moved to AP, so only still-unbilled ESTIMATED actual
-- cost remains accrued.  This prevents an interim report from showing HPP at
-- one process/rate while WIP/accrued manufacturing still uses another.
create or replace function erp.desired_laundry_accrual(p_po_id uuid)
returns numeric
language sql
stable
security definer
set search_path=''
as $function$
  with posted_receipt_cost as(
    select
      lrl.delivery_line_id,
      coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry) filter(
        where lr.status='POSTED'
          and lrl.actual_cost_status in('ESTIMATED','FINAL')
      ),0) as costed_qty,
      coalesce(sum(lrl.actual_cost) filter(
        where lr.status='POSTED' and lrl.actual_cost_status='ESTIMATED'
      ),0) as unbilled_actual_estimate
    from erp.laundry_receipt_lines lrl
    join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    group by lrl.delivery_line_id
  ), line_status as(
    select
      ldl.qty_sent_pcs,
      ldl.estimated_rate_snapshot,
      coalesce(rc.costed_qty,0) as costed_qty,
      coalesce(rc.unbilled_actual_estimate,0) as unbilled_actual_estimate
    from erp.laundry_delivery_lines ldl
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    left join posted_receipt_cost rc on rc.delivery_line_id=ldl.id
    where ld.po_id=p_po_id and ld.status not in('DRAFT','REVERSED')
  ), active_delivery_amount as(
    select coalesce(sum(
      unbilled_actual_estimate
      +greatest(qty_sent_pcs-costed_qty,0)*coalesce(estimated_rate_snapshot,0)
    ),0)::numeric amount
    from line_status
  ), returned_failed_wash_amount as(
    select coalesce(sum(rl.actual_cost),0)::numeric amount
    from erp.laundry_failed_wash_attempts a
    join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
    join erp.laundry_receipts r on r.id=a.receipt_id and r.status='POSTED'
    join erp.laundry_deliveries d on d.id=a.delivery_id and d.status='REVERSED'
    where d.po_id=p_po_id and rl.actual_cost_status='ESTIMATED'
  )
  select a.amount+f.amount
  from active_delivery_amount a cross join returned_failed_wash_amount f
$function$;
alter function erp.desired_laundry_accrual(uuid) owner to postgres;
revoke all on function erp.desired_laundry_accrual(uuid)
  from public,anon,authenticated,service_role;

-- The predecessor synchronizer locks the state row, but a PO has no row on
-- its first accrual. Two first callers could therefore both observe zero,
-- post the same delta twice, and only serialize at the final UPSERT. Use the
-- same per-PO transaction fence as rebuild_po_hpp before reading the state so
-- invoice, reversal, foreground, and background callers share one money/HPP
-- order even while the state row is absent.
create or replace function erp.sync_laundry_accrual(
  p_po_id uuid,p_effective_date date default current_date
)
returns void
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_old numeric(24,6):=0;
  v_new numeric(24,6):=0;
  v_delta numeric(24,6):=0;
  v_event uuid;
  v_journal uuid;
  v_abs numeric(24,2);
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('PO_HPP:'||p_po_id::text,0));
  select accrued_amount into v_old
  from erp.laundry_cost_accrual_state
  where po_id=p_po_id
  for update;
  v_old:=coalesce(v_old,0);
  v_new:=coalesce(erp.desired_laundry_accrual(p_po_id),0);
  v_delta:=v_new-v_old;
  if abs(v_delta)<=0.005 then
    insert into erp.laundry_cost_accrual_state(po_id,accrued_amount,updated_at)
    values(p_po_id,v_new,now())
    on conflict(po_id) do update set
      accrued_amount=excluded.accrued_amount,updated_at=now();
    return;
  end if;
  insert into erp.laundry_cost_accrual_events(
    po_id,old_amount,new_amount,delta_amount,effective_date
  ) values(p_po_id,v_old,v_new,v_delta,p_effective_date)
  returning id into v_event;
  v_abs:=round(abs(v_delta),2);
  if v_delta>0 then
    v_journal:=erp.post_journal(
      'LAUNDRY_ESTIMATE_ACCRUAL',v_event,p_effective_date,
      'Laundry estimate accrual',jsonb_build_array(
        jsonb_build_object('mapping_key','WIP','debit',v_abs,'credit',0,'po_id',p_po_id),
        jsonb_build_object('mapping_key','ACCRUED_MANUFACTURING','debit',0,'credit',v_abs,'po_id',p_po_id)
      )
    );
  else
    v_journal:=erp.post_journal(
      'LAUNDRY_ESTIMATE_ACCRUAL',v_event,p_effective_date,
      'Laundry estimate accrual reduction',jsonb_build_array(
        jsonb_build_object('mapping_key','ACCRUED_MANUFACTURING','debit',v_abs,'credit',0,'po_id',p_po_id),
        jsonb_build_object('mapping_key','WIP','debit',0,'credit',v_abs,'po_id',p_po_id)
      )
    );
  end if;
  update erp.laundry_cost_accrual_events
  set journal_entry_id=v_journal where id=v_event;
  insert into erp.laundry_cost_accrual_state(po_id,accrued_amount,updated_at)
  values(p_po_id,v_new,now())
  on conflict(po_id) do update set
    accrued_amount=excluded.accrued_amount,updated_at=now();
end
$function$;
alter function erp.sync_laundry_accrual(uuid,date) owner to postgres;

-- The predecessor HPP builder already owns every allocation rule.  Patch only
-- its two Laundry totals, under an exact predecessor MD5 gate captured above:
-- an active delivery already includes service-only attempts, while a fully
-- returned delivery contributes only its retained failed-wash attempt costs.
-- The exact pre-definition remains in the rollback capsule.
do $patch_failed_wash_hpp$
declare
  v_definition text;
  v_global_anchor constant text:='  into v_laundry,v_pending from dl;';
  v_group_anchor constant text:='      into v_group_laundry from dl;';
  v_global_addition constant text:=$sql$

  select v_laundry+coalesce(sum(rl.actual_cost),0)
    into v_laundry
  from erp.laundry_failed_wash_attempts a
  join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
  join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
  join erp.laundry_deliveries ld on ld.id=a.delivery_id and ld.status='REVERSED'
  where ld.po_id=p_po_id and rl.actual_cost_status in('ESTIMATED','FINAL');
$sql$;
  v_group_addition constant text:=$sql$

      select v_group_laundry+coalesce(sum(rl.actual_cost),0)
        into v_group_laundry
      from erp.laundry_failed_wash_attempts a
      join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
      join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
      join erp.laundry_deliveries ld on ld.id=a.delivery_id and ld.status='REVERSED'
      join erp.laundry_delivery_lines ldl on ldl.delivery_id=ld.id
      where ld.po_id=p_po_id and ldl.cutting_group_id=r.lineage_group_id
        and rl.actual_cost_status in('ESTIMATED','FINAL');
$sql$;
begin
  select pg_get_functiondef('erp.rebuild_po_hpp(uuid,text)'::regprocedure)
    into v_definition;
  if (length(v_definition)-length(replace(v_definition,v_global_anchor,'')))
       /length(v_global_anchor)<>1
     or (length(v_definition)-length(replace(v_definition,v_group_anchor,'')))
       /length(v_group_anchor)<>1
     or position('laundry_failed_wash_attempts' in v_definition)>0 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP Laundry patch anchors are not exact';
  end if;
  v_definition:=replace(v_definition,v_global_anchor,v_global_anchor||v_global_addition);
  v_definition:=replace(v_definition,v_group_anchor,v_group_anchor||v_group_addition);
  execute v_definition;
  if (select (length(pg_get_functiondef('erp.rebuild_po_hpp(uuid,text)'::regprocedure))
       -length(replace(pg_get_functiondef('erp.rebuild_po_hpp(uuid,text)'::regprocedure),
         'laundry_failed_wash_attempts','')))/length('laundry_failed_wash_attempts'))<>2 then
    raise exception 'CP6 failed-wash HPP installation is incomplete';
  end if;
end
$patch_failed_wash_hpp$;

-- WIP stage history is append-only.  The predecessor reversal functions
-- restore document/finance/stock state but do not append the inverse of their
-- physical stage events.  Catch the canonical status transition itself so
-- every supported caller (not only this facade) gets one linked inverse.
create unique index uq_cp6_wip_reversal_source_v2620
  on erp.wip_stage_events(source_type,source_id)
  where source_type in(
    'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL',
    'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL',
    'CP6_LAUNDRY_BS_WIP_REVERSAL'
  );

create function erp.append_cp6_laundry_wip_reversal_v2620()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_reason text:=coalesce(
    nullif(btrim(current_setting('app.change_reason',true)),''),
    'Canonical Laundry document reversal'
  );
  v_physical_at timestamptz:=coalesce(
    nullif(current_setting('app.physical_at',true),'')::timestamptz,
    clock_timestamp()
  );
begin
  if old.status='REVERSED' or new.status<>'REVERSED' then return new; end if;

  if tg_table_name='laundry_receipts' then
    if old.status<>'POSTED' then return new; end if;

    if exists(
      select 1
      from erp.laundry_receipt_lines l
      left join erp.wip_stage_events w
        on w.source_type='LAUNDRY_RECEIPT_LINE' and w.source_id=l.id
      where l.receipt_id=new.id and l.qty_good_received+l.qty_bs_laundry>0
      group by l.id,l.qty_good_received,l.qty_bs_laundry
      having count(w.id)<>1 or count(w.id) filter(where
        w.po_id=(select d.po_id from erp.laundry_deliveries d where d.id=new.delivery_id)
        and w.stage_from='LAUNDRY' and w.stage_to='QC'
        and w.qty_pcs=l.qty_good_received+l.qty_bs_laundry
      )<>1
    ) or exists(
      select 1
      from erp.laundry_receipt_batch_size_lines x
      join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
      left join erp.wip_stage_events w
        on w.source_type='CP6_LAUNDRY_BS_SIZE_LINE' and w.source_id=x.id
      where l.receipt_id=new.id and x.qty_bs_laundry>0
      group by x.id,x.qty_bs_laundry
      having count(w.id)<>1 or count(w.id) filter(where
        w.stage_from='QC' and w.stage_to='ON_HOLD'
        and w.qty_pcs=x.qty_bs_laundry
      )<>1
    ) then
      raise exception 'Laundry receipt reversal refused: posted WIP source history is missing or duplicated';
    end if;

    insert into erp.wip_stage_events(
      po_id,cutting_group_id,stage_from,stage_to,qty_pcs,contractor_id,
      source_type,source_id,physical_at,created_by,notes
    )
    select
      w.po_id,w.cutting_group_id,w.stage_to,w.stage_from,w.qty_pcs,w.contractor_id,
      case
        when w.source_type='LAUNDRY_RECEIPT_LINE'
          then 'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'
        else 'CP6_LAUNDRY_BS_WIP_REVERSAL'
      end,
      w.id,v_physical_at,erp.current_app_user_id(),
      'Append-only inverse of WIP event '||w.id::text||': '||v_reason
    from erp.wip_stage_events w
    where(
      (w.source_type='LAUNDRY_RECEIPT_LINE' and exists(
        select 1 from erp.laundry_receipt_lines l
        where l.receipt_id=new.id and l.id=w.source_id
          and w.po_id=(select d.po_id from erp.laundry_deliveries d where d.id=new.delivery_id)
          and w.stage_from='LAUNDRY' and w.stage_to='QC'
          and w.qty_pcs=l.qty_good_received+l.qty_bs_laundry
      ))
      or
      (w.source_type='CP6_LAUNDRY_BS_SIZE_LINE' and exists(
        select 1
        from erp.laundry_receipt_batch_size_lines x
        join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
        where l.receipt_id=new.id and x.id=w.source_id
          and w.stage_from='QC' and w.stage_to='ON_HOLD'
          and w.qty_pcs=x.qty_bs_laundry
      ))
    )
    on conflict do nothing;

    if exists(
      select 1
      from erp.wip_stage_events w
      left join erp.wip_stage_events rv
        on rv.source_id=w.id
       and rv.source_type=case
         when w.source_type='LAUNDRY_RECEIPT_LINE'
           then 'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'
         else 'CP6_LAUNDRY_BS_WIP_REVERSAL'
       end
       and rv.po_id=w.po_id
       and rv.cutting_group_id is not distinct from w.cutting_group_id
       and rv.stage_from=w.stage_to and rv.stage_to=w.stage_from
       and rv.qty_pcs is not distinct from w.qty_pcs
      where(
        (w.source_type='LAUNDRY_RECEIPT_LINE' and exists(
          select 1 from erp.laundry_receipt_lines l
          where l.receipt_id=new.id and l.id=w.source_id
            and w.po_id=(select d.po_id from erp.laundry_deliveries d where d.id=new.delivery_id)
            and w.stage_from='LAUNDRY' and w.stage_to='QC'
            and w.qty_pcs=l.qty_good_received+l.qty_bs_laundry
        ))
        or
        (w.source_type='CP6_LAUNDRY_BS_SIZE_LINE' and exists(
          select 1
          from erp.laundry_receipt_batch_size_lines x
          join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
          where l.receipt_id=new.id and x.id=w.source_id
            and w.stage_from='QC' and w.stage_to='ON_HOLD'
            and w.qty_pcs=x.qty_bs_laundry
        ))
      )
      group by w.id having count(rv.id)<>1
    ) then
      raise exception 'Laundry receipt reversal did not conserve append-only WIP history';
    end if;

  elsif tg_table_name='laundry_deliveries' then
    if old.status not in('SENT','PARTIAL_RETURN','RETURNED','CLOSED') then return new; end if;

    if exists(
      select 1
      from erp.laundry_delivery_lines l
      left join erp.wip_stage_events w
        on w.source_type='LAUNDRY_DELIVERY_LINE' and w.source_id=l.id
      where l.delivery_id=new.id
      group by l.id,l.qty_sent_pcs
      having count(w.id)<>1 or count(w.id) filter(where
        w.po_id=new.po_id
        and w.stage_from='SEWING' and w.stage_to='LAUNDRY'
        and w.qty_pcs=l.qty_sent_pcs
      )<>1
    ) then
      raise exception 'Laundry delivery reversal refused: posted WIP source history is missing or duplicated';
    end if;

    insert into erp.wip_stage_events(
      po_id,cutting_group_id,stage_from,stage_to,qty_pcs,contractor_id,
      source_type,source_id,physical_at,created_by,notes
    )
    select
      w.po_id,w.cutting_group_id,w.stage_to,w.stage_from,w.qty_pcs,w.contractor_id,
      'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL',w.id,v_physical_at,
      erp.current_app_user_id(),
      'Append-only inverse of WIP event '||w.id::text||': '||v_reason
    from erp.wip_stage_events w
    where w.source_type='LAUNDRY_DELIVERY_LINE'
      and w.po_id=new.po_id
      and w.stage_from='SEWING' and w.stage_to='LAUNDRY'
      and exists(
        select 1 from erp.laundry_delivery_lines l
        where l.delivery_id=new.id and l.id=w.source_id
          and w.qty_pcs=l.qty_sent_pcs
      )
    on conflict do nothing;

    if exists(
      select 1
      from erp.wip_stage_events w
      left join erp.wip_stage_events rv
        on rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
       and rv.source_id=w.id and rv.po_id=w.po_id
       and rv.cutting_group_id is not distinct from w.cutting_group_id
       and rv.stage_from=w.stage_to and rv.stage_to=w.stage_from
       and rv.qty_pcs is not distinct from w.qty_pcs
      where w.source_type='LAUNDRY_DELIVERY_LINE'
        and w.po_id=new.po_id
        and w.stage_from='SEWING' and w.stage_to='LAUNDRY'
        and exists(
          select 1 from erp.laundry_delivery_lines l
          where l.delivery_id=new.id and l.id=w.source_id
            and w.qty_pcs=l.qty_sent_pcs
        )
      group by w.id having count(rv.id)<>1
    ) then
      raise exception 'Laundry delivery reversal did not conserve append-only WIP history';
    end if;
  else
    raise exception 'Unexpected CP6 Laundry WIP reversal trigger table %',tg_table_name;
  end if;
  return new;
end
$function$;

alter function erp.append_cp6_laundry_wip_reversal_v2620() owner to postgres;
revoke all on function erp.append_cp6_laundry_wip_reversal_v2620()
  from public,anon,authenticated,service_role;

create trigger trg_append_cp6_laundry_wip_reversal_v2620
after update of status on erp.laundry_receipts
for each row execute function erp.append_cp6_laundry_wip_reversal_v2620();
create trigger trg_append_cp6_laundry_wip_reversal_v2620
after update of status on erp.laundry_deliveries
for each row execute function erp.append_cp6_laundry_wip_reversal_v2620();

alter table erp.qc_inspection_items
  add constraint qc_items_cp6_source_batch_size_fkey
  foreign key(source_laundry_receipt_batch_size_line_id)
  references erp.laundry_receipt_batch_size_lines(id) on delete restrict;
create index idx_qc_items_cp6_source_batch_size_v2620
  on erp.qc_inspection_items(source_laundry_receipt_batch_size_line_id)
  where source_laundry_receipt_batch_size_line_id is not null;

create table erp.cp6_laundry_qc_execution_context(
  backend_pid integer not null,
  transaction_id bigint not null,
  actor_key text not null,
  action text not null check(action in(
    'POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','POST_FINAL_SKU'
  )),
  permission_key text not null,
  client_request_id uuid not null,
  payload jsonb not null,
  created_at timestamptz not null default clock_timestamp(),
  primary key(backend_pid,transaction_id)
);

alter table erp.laundry_delivery_batch_size_lines enable row level security;
alter table erp.laundry_receipt_batch_size_lines enable row level security;
alter table erp.laundry_failed_wash_attempts enable row level security;
alter table erp.laundry_failed_wash_batch_size_lines enable row level security;
alter table erp.cp6_laundry_qc_execution_context enable row level security;
revoke all on table
  erp.laundry_delivery_batch_size_lines,
  erp.laundry_receipt_batch_size_lines,
  erp.laundry_failed_wash_attempts,
  erp.laundry_failed_wash_batch_size_lines,
  erp.cp6_laundry_qc_execution_context
from public,anon,authenticated,service_role;

create or replace function erp.require_internal()
returns void
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_app_role text;
  v_jwt_role text;
begin
  if session_user in('postgres','supabase_admin') then return; end if;
  begin
    v_jwt_role:=coalesce(auth.jwt()->>'role','');
  exception when others then
    v_jwt_role:='';
  end;
  if v_jwt_role='service_role' then return; end if;
  if exists(
    select 1
    from erp.cutting_bridge_execution_context c
    where c.backend_pid=pg_backend_pid()
      and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key()
      and c.action='POST_CUTTING'
      and c.permission_key='production.cutting.post'
      and erp.has_permission(c.permission_key)
  ) then return; end if;
  if exists(
    select 1
    from erp.bs_resolution_execution_context c
    where c.backend_pid=pg_backend_pid()
      and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key()
      and c.permission_key in(
        'production.bs_rework.create','production.bs_rework.post','production.bs_rework.reverse'
      )
      and erp.has_permission(c.permission_key)
  ) then return; end if;
  if exists(
    select 1
    from erp.cp6_laundry_qc_execution_context c
    where c.backend_pid=pg_backend_pid()
      and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key()
      and(
        (c.action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH')
          and c.permission_key='production.laundry.post')
        or(c.action='POST_FINAL_SKU'
          and c.permission_key='production.final_sku.post')
      )
      and erp.has_permission(c.permission_key)
  ) then return; end if;
  v_app_role:=erp.current_app_role();
  if v_app_role not in('OWNER','ADMIN','STAFF') then
    raise exception 'Internal ERP access required';
  end if;
end
$function$;
alter function erp.require_internal() owner to postgres;
revoke all on function erp.require_internal() from public,anon,authenticated;
grant execute on function erp.require_internal() to service_role;

-- Human identity is Brand -> SKU number -> Model.  One human SKU may have
-- several exact-size product roots because stock/HPP remain size-bound.  The
-- variants inside one brand + SKU must keep the same model/color, while the
-- same number under another brand may legitimately use another model. Pattern
-- is deliberately absent: it remains immutable cutting/production lineage.
create or replace function erp.validate_product_identity_period()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_end timestamptz:=coalesce(new.effective_to,'infinity'::timestamptz);
  v_root_identity uuid;
  v_predecessor_identity uuid;
  v_predecessor_end timestamptz;
begin
  if tg_op='UPDATE' then
    if row(
      new.id,new.sku,new.model_id,new.brand_id,new.color_name,new.size_id,
      new.identity_root_id,new.effective_from,new.effective_to,new.supersedes_product_id
    ) is distinct from row(
      old.id,old.sku,old.model_id,old.brand_id,old.color_name,old.size_id,
      old.identity_root_id,old.effective_from,old.effective_to,old.supersedes_product_id
    ) then
      raise exception 'Identitas dan periode SKU immutable setelah row dibuat; ubah nama/status tampilan saja atau buat successor terkontrol, jangan menulis ulang sejarah stok/HPP';
    end if;
  end if;
  if new.identity_root_id is null then new.identity_root_id:=new.id; end if;
  if new.effective_from is null then new.effective_from:=clock_timestamp(); end if;
  if new.effective_to is not null and new.effective_to<=new.effective_from then
    raise exception 'Tanggal akhir identitas SKU harus setelah tanggal mulai berlaku';
  end if;

  -- A version chain is accounting lineage, not editable display metadata.
  -- Serialize every member on the immutable root and reject missing roots,
  -- detached successors, branches, or a timestamp change that would rewrite
  -- the predecessor/successor boundary underneath historical stock and HPP.
  perform pg_advisory_xact_lock(hashtextextended(
    'SKUROOT:'||new.identity_root_id::text,0
  ));
  if new.identity_root_id=new.id then
    if new.supersedes_product_id is not null then
      raise exception 'Root identitas SKU tidak boleh menunjuk predecessor';
    end if;
  else
    select r.identity_root_id into v_root_identity
    from erp.products r where r.id=new.identity_root_id;
    if v_root_identity is distinct from new.identity_root_id then
      raise exception 'identity_root_id SKU wajib menunjuk root yang valid dan menunjuk dirinya sendiri';
    end if;
    if new.supersedes_product_id is null then
      raise exception 'Versi SKU non-root wajib menunjuk predecessor';
    end if;
    select p.identity_root_id,p.effective_to
      into v_predecessor_identity,v_predecessor_end
    from erp.products p where p.id=new.supersedes_product_id;
    if v_predecessor_identity is distinct from new.identity_root_id
       or v_predecessor_end is distinct from new.effective_from then
      raise exception 'Predecessor SKU wajib satu root dan berakhir tepat saat successor mulai';
    end if;
    if exists(
      select 1 from erp.products p
      where p.supersedes_product_id=new.supersedes_product_id and p.id<>new.id
    ) then
      raise exception 'Satu versi SKU tidak boleh memiliki lebih dari satu successor';
    end if;
  end if;
  if exists(
    select 1 from erp.products p
    where p.supersedes_product_id=new.id and p.id<>new.id
      and (p.identity_root_id is distinct from new.identity_root_id
        or p.effective_from is distinct from new.effective_to)
  ) then
    raise exception 'Perubahan periode SKU akan memutus rantai successor yang sudah ada';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(
    'BRANDSKU:'||new.brand_id::text||':'||lower(btrim(new.sku)),0
  ));
  perform pg_advisory_xact_lock(hashtextextended(
    'SKUCOMBO:'||new.model_id::text||':'||new.brand_id::text||':'
      ||lower(btrim(new.color_name))||':'||new.size_id::text,0
  ));

  if exists(
    select 1 from erp.products p
    where p.id<>new.id and p.identity_root_id=new.identity_root_id
      and tstzrange(p.effective_from,coalesce(p.effective_to,'infinity'::timestamptz),'[)')
          && tstzrange(new.effective_from,v_end,'[)')
  ) then
    raise exception 'Periode perubahan SKU bertumpuk dengan versi SKU yang sama. Koreksi tanggal berlaku terlebih dahulu.';
  end if;

  if exists(
    select 1 from erp.products p
    where p.id<>new.id and p.identity_root_id<>new.identity_root_id
      and p.brand_id=new.brand_id
      and lower(btrim(p.sku))=lower(btrim(new.sku))
      and p.size_id=new.size_id
      and tstzrange(p.effective_from,coalesce(p.effective_to,'infinity'::timestamptz),'[)')
          && tstzrange(new.effective_from,v_end,'[)')
  ) then
    raise exception 'Nomor SKU % untuk merek dan size ini sudah punya identitas aktif',new.sku;
  end if;

  if exists(
    select 1 from erp.products p
    where p.id<>new.id and p.identity_root_id<>new.identity_root_id
      and p.brand_id=new.brand_id
      and lower(btrim(p.sku))=lower(btrim(new.sku))
      and (p.model_id<>new.model_id
        or lower(btrim(p.color_name))<>lower(btrim(new.color_name)))
      and tstzrange(p.effective_from,coalesce(p.effective_to,'infinity'::timestamptz),'[)')
          && tstzrange(new.effective_from,v_end,'[)')
  ) then
    raise exception 'Varian size untuk merek + nomor SKU yang sama wajib memakai model dan warna yang sama';
  end if;

  if exists(
    select 1 from erp.products p
    where p.id<>new.id and p.identity_root_id<>new.identity_root_id
      and p.model_id=new.model_id and p.brand_id=new.brand_id
      and lower(btrim(p.color_name))=lower(btrim(new.color_name))
      and p.size_id=new.size_id
      and tstzrange(p.effective_from,coalesce(p.effective_to,'infinity'::timestamptz),'[)')
          && tstzrange(new.effective_from,v_end,'[)')
  ) then
    raise exception 'Kombinasi model/merek/warna/size sudah dipakai SKU lain pada periode yang sama';
  end if;
  return new;
end
$function$;

create or replace function erp.run_v259_integrity_checks()
returns table(check_name text,severity text,issue_count bigint,details text)
language plpgsql
stable security definer
set search_path=''
as $function$
begin
  perform erp.require_owner_admin();
  return query
    select 'PRODUCT_IDENTITY_SAME_ROOT_OVERLAP','ERROR',count(*)::bigint,
      'One logical SKU root must not have overlapping identity periods'
    from erp.products a join erp.products b on a.id<b.id
      and a.identity_root_id=b.identity_root_id
      and tstzrange(a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)')
        && tstzrange(b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)');
  return query
    select 'PRODUCT_IDENTITY_SKU_CROSS_ROOT_OVERLAP','ERROR',count(*)::bigint,
      'One brand + SKU number + size must not belong to different logical roots at the same time'
    from erp.products a join erp.products b on a.id<b.id
      and a.identity_root_id<>b.identity_root_id and a.brand_id=b.brand_id
      and lower(btrim(a.sku))=lower(btrim(b.sku)) and a.size_id=b.size_id
      and tstzrange(a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)')
        && tstzrange(b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)');
  return query
    select 'PRODUCT_IDENTITY_BRAND_SKU_VARIANT_MISMATCH','ERROR',count(*)::bigint,
      'Size variants inside one brand + SKU number must keep the same model and color'
    from erp.products a join erp.products b on a.id<b.id
      and a.identity_root_id<>b.identity_root_id and a.brand_id=b.brand_id
      and lower(btrim(a.sku))=lower(btrim(b.sku))
      and (a.model_id<>b.model_id
        or lower(btrim(a.color_name))<>lower(btrim(b.color_name)))
      and tstzrange(a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)')
        && tstzrange(b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)');
  return query
    select 'PRODUCT_IDENTITY_COMBO_CROSS_ROOT_OVERLAP','ERROR',count(*)::bigint,
      'Model/brand/color/size combination must not map to different logical SKU roots at the same time'
    from erp.products a join erp.products b on a.id<b.id
      and a.identity_root_id<>b.identity_root_id and a.model_id=b.model_id
      and a.brand_id=b.brand_id and lower(btrim(a.color_name))=lower(btrim(b.color_name))
      and a.size_id=b.size_id
      and tstzrange(a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)')
        && tstzrange(b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)');
  return query
    select 'PRODUCT_IDENTITY_ROOT_INVALID','ERROR',count(*)::bigint,
      'Every identity_root_id must point to a root product whose identity_root_id points to itself'
    from erp.products p left join erp.products r on r.id=p.identity_root_id
    where r.id is null or r.identity_root_id<>r.id;
  return query
    select 'PRODUCT_SUCCESSOR_CHAIN_MISMATCH','ERROR',count(*)::bigint,
      'Roots have no predecessor; every non-root stays in one root and starts exactly when its predecessor ends'
    from erp.products p left join erp.products old on old.id=p.supersedes_product_id
    where (p.id=p.identity_root_id and p.supersedes_product_id is not null)
       or (p.id<>p.identity_root_id and (
         p.supersedes_product_id is null or old.id is null
         or p.identity_root_id<>old.identity_root_id
         or old.effective_to is distinct from p.effective_from
       ));
  return query
    select 'PRODUCT_SUCCESSOR_BRANCH','ERROR',count(*)::bigint,
      'One product identity version must have at most one direct successor'
    from(
      select p.supersedes_product_id
      from erp.products p
      where p.supersedes_product_id is not null
      group by p.supersedes_product_id having count(*)>1
    ) branched;
  return query
    select 'PRODUCT_PRICE_OVERLAP','ERROR',count(*)::bigint,
      'Selling-price versions for one product must not overlap'
    from erp.product_price_versions a join erp.product_price_versions b on a.id<b.id
      and a.product_id=b.product_id
      and tstzrange(a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)')
        && tstzrange(b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)');
  return query
    select 'WORK_RATE_OVERLAP','ERROR',count(*)::bigint,
      'Contractor work-rate versions for the same contractor/model/component must not overlap'
    from erp.contractor_work_rates a join erp.contractor_work_rates b on a.id<b.id
      and a.contractor_id=b.contractor_id and a.model_id=b.model_id
      and a.work_component_id=b.work_component_id
      and tstzrange(a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)')
        && tstzrange(b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)');
  return query
    select 'CONTRACTOR_ACCESSORY_PRICE_OVERLAP','ERROR',count(*)::bigint,
      'Accessory selling-price versions for the same contractor/category must not overlap'
    from erp.contractor_accessory_price_versions a
    join erp.contractor_accessory_price_versions b on a.id<b.id
      and a.contractor_id is not distinct from b.contractor_id
      and a.category_id=b.category_id
      and tstzrange(a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)')
        && tstzrange(b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)');
  return query
    select 'CONTRACTOR_MATERIAL_PRICE_OVERLAP','ERROR',count(*)::bigint,
      'Material selling-price versions for the same contractor/material must not overlap'
    from erp.contractor_material_price_versions a
    join erp.contractor_material_price_versions b on a.id<b.id
      and a.contractor_id is not distinct from b.contractor_id
      and a.material_id=b.material_id
      and tstzrange(a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)')
        && tstzrange(b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)');
  return query
    select 'LAUNDRY_RATE_OVERLAP','ERROR',count(*)::bigint,
      'Laundry rate versions for the same vendor/process must not overlap'
    from erp.laundry_vendor_rate_versions a join erp.laundry_vendor_rate_versions b on a.id<b.id
      and a.vendor_id=b.vendor_id and a.wash_process_id=b.wash_process_id
      and tstzrange(a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)')
        && tstzrange(b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)');
  return query
    select 'ACCESSORY_BOM_OVERLAP','ERROR',count(*)::bigint,
      'Active accessory BOM versions for one SKU must not overlap'
    from erp.accessory_bom_versions a join erp.accessory_bom_versions b on a.id<b.id
      and a.product_id=b.product_id and a.is_active and b.is_active
      and tstzrange(a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)')
        && tstzrange(b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)');
  return query
    select 'WORK_BOM_OVERLAP','ERROR',count(*)::bigint,
      'Active Work BOM versions for one model must not overlap'
    from erp.work_bom_versions a join erp.work_bom_versions b on a.id<b.id
      and a.model_id=b.model_id and a.is_active and b.is_active
      and tstzrange(a.effective_from,coalesce(a.effective_to,'infinity'::timestamptz),'[)')
        && tstzrange(b.effective_from,coalesce(b.effective_to,'infinity'::timestamptz),'[)');
end
$function$;

create or replace function erp.apply_migration_master_rows(p_batch_id uuid)
returns integer
language plpgsql
security definer
set search_path=''
as $function$
declare
  r record;
  j jsonb;
  v_id uuid;
  v_model uuid;
  v_brand uuid;
  v_size uuid;
  v_category uuid;
  v_material uuid;
  v_supplier uuid;
  v_cutover timestamptz;
  v_count integer:=0;
  v_existing record;
begin
  perform erp.require_owner_admin();
  if (select status from erp.migration_batches where id=p_batch_id) not in('READY','POSTING') then
    raise exception 'Migration batch must be READY';
  end if;
  if exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and validation_status<>'VALID') then
    raise exception 'Migration batch contains unvalidated/error rows';
  end if;
  select cutover_at into v_cutover from erp.migration_batches where id=p_batch_id;
  update erp.migration_batches set status='POSTING',error_message=null where id=p_batch_id;

  for r in
    select * from erp.migration_staging_rows
    where batch_id=p_batch_id and validation_status='VALID'
      and entity_type in(
        'BRAND','SIZE','MODEL','CUSTOMER','SUPPLIER','CONTRACTOR',
        'ACCESSORY_CATEGORY','MATERIAL','MATERIAL_ROLL','PRODUCT'
      )
    order by case entity_type
      when 'BRAND' then 10 when 'SIZE' then 20 when 'MODEL' then 30
      when 'CUSTOMER' then 40 when 'SUPPLIER' then 50 when 'CONTRACTOR' then 60
      when 'ACCESSORY_CATEGORY' then 70 when 'MATERIAL' then 80
      when 'MATERIAL_ROLL' then 85 when 'PRODUCT' then 90 else 999 end,
      source_row_no
  loop
    j:=r.normalized_payload;
    v_id:=null;
    case r.entity_type
      when 'BRAND' then
        insert into erp.brands(brand_code,brand_name,is_active)
        values(j->>'brand_code',j->>'brand_name',coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(brand_code) do update set
          brand_name=excluded.brand_name,is_active=excluded.is_active,updated_at=now()
        returning id into v_id;
      when 'SIZE' then
        insert into erp.sizes(size_code,sort_order,is_active)
        values(j->>'size_code',coalesce(nullif(j->>'sort_order','')::integer,0),
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(size_code) do update set
          sort_order=excluded.sort_order,is_active=excluded.is_active
        returning id into v_id;
      when 'MODEL' then
        insert into erp.product_models(model_code,model_name,description,is_active)
        values(j->>'model_code',j->>'model_name',j->>'description',
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(model_code) do update set
          model_name=excluded.model_name,description=excluded.description,
          is_active=excluded.is_active,updated_at=now()
        returning id into v_id;
      when 'CUSTOMER' then
        insert into erp.customers(customer_code,customer_name,phone,address,is_active)
        values(j->>'customer_code',j->>'customer_name',j->>'phone',j->>'address',
          coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(customer_code) do update set
          customer_name=excluded.customer_name,phone=excluded.phone,address=excluded.address,
          is_active=excluded.is_active,updated_at=now()
        returning id into v_id;
      when 'SUPPLIER' then
        insert into erp.suppliers(
          supplier_code,supplier_name,supplier_type,phone,address,is_active
        ) values(
          j->>'supplier_code',j->>'supplier_name',
          coalesce(nullif(upper(j->>'supplier_type'),''),'MATERIAL'),
          j->>'phone',j->>'address',coalesce(nullif(j->>'is_active','')::boolean,true)
        )
        on conflict(supplier_code) do update set
          supplier_name=excluded.supplier_name,supplier_type=excluded.supplier_type,
          phone=excluded.phone,address=excluded.address,is_active=excluded.is_active
        returning id into v_id;
      when 'CONTRACTOR' then
        insert into erp.contractors(
          contractor_code,contractor_name,contractor_type,attendance_required,is_active,notes
        ) values(
          j->>'contractor_code',j->>'contractor_name',
          coalesce(nullif(upper(j->>'contractor_type'),''),'MANDOR'),
          coalesce(nullif(j->>'attendance_required','')::boolean,true),
          coalesce(nullif(j->>'is_active','')::boolean,true),j->>'notes'
        )
        on conflict(contractor_code) do update set
          contractor_name=excluded.contractor_name,contractor_type=excluded.contractor_type,
          attendance_required=excluded.attendance_required,is_active=excluded.is_active,
          notes=excluded.notes,updated_at=now()
        returning id into v_id;
      when 'ACCESSORY_CATEGORY' then
        insert into erp.accessory_categories(
          category_code,category_name,base_uom_code,is_active,notes
        ) values(
          j->>'category_code',j->>'category_name',upper(j->>'base_uom_code'),
          coalesce(nullif(j->>'is_active','')::boolean,true),j->>'notes'
        )
        on conflict(category_code) do update set
          category_name=excluded.category_name,is_active=excluded.is_active,
          notes=excluded.notes,updated_at=now()
        returning id into v_id;
      when 'MATERIAL' then
        v_category:=null;
        if nullif(btrim(coalesce(j->>'accessory_category_code','')),'') is not null then
          select id into v_category from erp.accessory_categories
          where category_code=j->>'accessory_category_code';
          if v_category is null then
            raise exception 'Unknown accessory category % for material %',
              j->>'accessory_category_code',j->>'material_sku';
          end if;
        end if;
        insert into erp.materials(
          material_sku,material_name,material_type,unit_code,accessory_category_id,is_active
        ) values(
          j->>'material_sku',j->>'material_name',upper(j->>'material_type'),
          upper(j->>'unit_code'),v_category,
          coalesce(nullif(j->>'is_active','')::boolean,true)
        )
        on conflict(material_sku) do update set
          material_name=excluded.material_name,
          accessory_category_id=excluded.accessory_category_id,
          is_active=excluded.is_active,updated_at=now()
        returning id into v_id;
      when 'MATERIAL_ROLL' then
        select id into v_material from erp.materials
        where material_sku=j->>'material_sku' and material_type='FABRIC';
        if v_material is null then
          raise exception 'MATERIAL_ROLL material % is not a FABRIC material',j->>'material_sku';
        end if;
        v_supplier:=null;
        if nullif(btrim(coalesce(j->>'supplier_code','')),'') is not null then
          select id into v_supplier from erp.suppliers where supplier_code=j->>'supplier_code';
          if v_supplier is null then
            raise exception 'Unknown supplier % for roll %',j->>'supplier_code',j->>'roll_number';
          end if;
        end if;
        if exists(select 1 from erp.material_rolls
          where material_id=v_material and roll_number=j->>'roll_number') then
          raise exception 'Migration roll already exists for material %, roll %',
            j->>'material_sku',j->>'roll_number';
        end if;
        insert into erp.material_rolls(
          material_id,purchase_item_id,supplier_id,roll_number,original_qty,
          cached_qty,status,received_at,notes
        ) values(
          v_material,null,v_supplier,j->>'roll_number',(j->>'opening_qty')::numeric,
          0,'AVAILABLE',v_cutover,coalesce(j->>'notes','Legacy roll at migration cutover')
        ) returning id into v_id;
      when 'PRODUCT' then
        select id into v_model from erp.product_models where model_code=j->>'model_code';
        select id into v_brand from erp.brands where brand_code=j->>'brand_code';
        select id into v_size from erp.sizes where size_code=j->>'size_code';
        if v_model is null or v_brand is null or v_size is null then
          raise exception 'Product % has unresolved model/brand/size mapping',j->>'sku';
        end if;
        insert into erp.product_model_sizes(model_id,size_id)
        values(v_model,v_size) on conflict(model_id,size_id) do nothing;

        select p.* into v_existing
        from erp.products p
        where p.brand_id=v_brand
          and lower(btrim(p.sku))=lower(btrim(j->>'sku'))
          and p.size_id=v_size
          and p.effective_from<=v_cutover
          and(p.effective_to is null or p.effective_to>v_cutover)
        order by p.effective_from desc,p.id desc limit 1;

        if v_existing.id is null then
          if exists(
            select 1 from erp.products p
            where p.brand_id=v_brand
              and lower(btrim(p.sku))=lower(btrim(j->>'sku'))
              and p.size_id=v_size
          ) then
            raise exception 'Migration product % already has identity history for brand % / size % but no version valid at cutover %. Do not guess a historical version; fix migration mapping/effective dates first.',
              j->>'sku',j->>'brand_code',j->>'size_code',v_cutover;
          end if;
          insert into erp.products(
            sku,model_id,brand_id,color_name,size_id,product_name,
            is_portal_visible,is_active,effective_from
          ) values(
            j->>'sku',v_model,v_brand,j->>'color_name',v_size,j->>'product_name',
            coalesce(nullif(j->>'is_portal_visible','')::boolean,true),
            coalesce(nullif(j->>'is_active','')::boolean,true),v_cutover
          ) returning id into v_id;
        else
          if v_existing.model_id is distinct from v_model
             or v_existing.brand_id is distinct from v_brand
             or lower(btrim(v_existing.color_name)) is distinct from lower(btrim(j->>'color_name'))
             or v_existing.size_id is distinct from v_size then
            raise exception 'Migration product % identity differs from the brand + SKU version already valid at cutover. Use controlled identity-version mapping instead of overwriting history.',j->>'sku';
          end if;
          v_id:=v_existing.id;
          update erp.products set
            product_name=j->>'product_name',
            is_portal_visible=coalesce(nullif(j->>'is_portal_visible','')::boolean,true),
            is_active=coalesce(nullif(j->>'is_active','')::boolean,true),updated_at=now()
          where id=v_id;
        end if;
    end case;
    update erp.migration_staging_rows set
      posted_entity_type=r.entity_type,posted_entity_id=v_id,
      posted_at=now(),updated_at=now()
    where id=r.id;
    v_count:=v_count+1;
  end loop;
  return v_count;
end
$function$;

alter function erp.validate_product_identity_period() owner to postgres;
alter function erp.run_v259_integrity_checks() owner to postgres;
alter function erp.apply_migration_master_rows(uuid) owner to postgres;
revoke all on function erp.validate_product_identity_period()
  from public,anon,authenticated,service_role;

create function erp.guard_cp6_qc_batch_size_source_v2620()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_context_payload jsonb;
  v_source_id uuid:=new.source_laundry_receipt_batch_size_line_id;
  v_receipt_line uuid;
  v_size uuid;
  v_good bigint;
  v_product_size uuid;
  v_product_model uuid;
  v_source_model uuid;
  v_source_group uuid;
  v_source_po uuid;
  v_qc_po uuid;
  v_receipt_physical_at timestamptz;
  v_qc_physical_at timestamptz;
  v_prior bigint;
begin
  if new.source_laundry_receipt_line_id is null then
    if v_source_id is not null then
      raise exception 'Direct QC cannot carry a Laundry batch/size source';
    end if;
    if exists(
      select 1 from erp.cp6_laundry_qc_execution_context c
      where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
        and c.actor_key=erp._idempotency_actor_key() and c.action='POST_FINAL_SKU'
    ) then
      raise exception using errcode='23514',message='CP6_LAUNDRY_SIZE_LINEAGE_REQUIRED';
    end if;
    return new;
  end if;

  if v_source_id is null then
    select c.payload into v_context_payload
    from erp.cp6_laundry_qc_execution_context c
    where c.backend_pid=pg_backend_pid()
      and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key()
      and c.action='POST_FINAL_SKU';
    if v_context_payload is not null then
      select nullif(x.value->>'source_laundry_receipt_batch_size_line_id','')::uuid
        into v_source_id
      from jsonb_array_elements(v_context_payload->'lines') x
      where nullif(x.value->>'final_product_id','')::uuid=new.final_product_id
        and nullif(x.value->>'source_laundry_receipt_line_id','')::uuid=new.source_laundry_receipt_line_id
        and coalesce(nullif(x.value->>'qty_good_pcs','')::integer,0)=new.qty_good_pcs
        and coalesce(nullif(x.value->>'qty_bs_pcs','')::integer,0)=new.qty_bs_pcs;
    end if;
    if v_source_id is null then
      -- Historical rows remain readable. New receipt-linked QC facts do not
      -- get a trusted-writer exemption: every caller must provide exact
      -- receipt/batch/size lineage through the CP6 facade. Otherwise a private
      -- legacy writer could bypass size conservation while still posting FG,
      -- HPP, reimbursement, and journals.
      raise exception using errcode='23514',message='CP6_LAUNDRY_SIZE_LINEAGE_REQUIRED';
    end if;
    new.source_laundry_receipt_batch_size_line_id:=v_source_id;
  end if;

  select x.receipt_line_id,x.size_id,x.qty_good_received,po.model_id,
    dl.cutting_group_id,po.id,q.po_id,r.physical_at,q.physical_at
    into v_receipt_line,v_size,v_good,v_source_model,
      v_source_group,v_source_po,v_qc_po,v_receipt_physical_at,v_qc_physical_at
  from erp.laundry_receipt_batch_size_lines x
  join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
  join erp.laundry_receipts r on r.id=rl.receipt_id
  join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
  join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
  join erp.cutting_groups g on g.id=dl.cutting_group_id
  join erp.production_orders po on po.id=g.po_id and po.id=d.po_id
  join erp.qc_inspections q on q.id=new.inspection_id
  where x.id=v_source_id and r.status='POSTED'
  for update of r,x;
  if v_receipt_line is distinct from new.source_laundry_receipt_line_id then
    raise exception 'QC batch/size source does not belong to its receipt line';
  end if;
  if v_source_group is distinct from new.cutting_group_id
     or v_source_po is distinct from v_qc_po then
    raise exception 'QC batch/size source belongs to a different Potongan/PO';
  end if;
  if v_qc_physical_at<v_receipt_physical_at then
    raise exception 'QC physical time cannot be earlier than its authoritative Laundry receipt';
  end if;
  select p.size_id,p.model_id into v_product_size,v_product_model
  from erp.products p
  join erp.product_models m on m.id=p.model_id and m.is_active
  join erp.brands b on b.id=p.brand_id and b.is_active
  join erp.sizes s on s.id=p.size_id and s.is_active
  where p.id=new.final_product_id and p.is_active
    and p.effective_from<=v_qc_physical_at
    and(p.effective_to is null or p.effective_to>v_qc_physical_at)
  for share of p,m,b,s;
  if v_product_size is distinct from v_size or v_product_model is distinct from v_source_model then
    raise exception 'Final SKU must be active at physical QC time and match the Laundry receipt model/size';
  end if;
  select coalesce(sum(i.qty_good_pcs+i.qty_bs_pcs),0)::bigint into v_prior
  from erp.qc_inspection_items i
  join erp.qc_inspections q on q.id=i.inspection_id
  where i.source_laundry_receipt_batch_size_line_id=v_source_id
    and i.id<>new.id and q.status<>'REVERSED';
  if v_prior+new.qty_good_pcs+new.qty_bs_pcs>coalesce(v_good,0) then
    raise exception 'QC quantity exceeds GOOD returned for the exact Laundry batch/size. Good %, prior QC %, this QC %',
      coalesce(v_good,0),v_prior,new.qty_good_pcs+new.qty_bs_pcs;
  end if;
  return new;
end
$function$;
alter function erp.guard_cp6_qc_batch_size_source_v2620() owner to postgres;
revoke all on function erp.guard_cp6_qc_batch_size_source_v2620()
  from public,anon,authenticated,service_role;
create trigger trg_01_guard_cp6_qc_batch_size_source_v2620
before insert or update of source_laundry_receipt_line_id,
  source_laundry_receipt_batch_size_line_id,final_product_id,qty_good_pcs,qty_bs_pcs
on erp.qc_inspection_items
for each row execute function erp.guard_cp6_qc_batch_size_source_v2620();

-- Laundry BS is already a terminal, product-bound BS fact at receipt posting.
-- It must reduce remaining QC but must never become QC-ready a second time.
create or replace view erp.v_fg_partial_completion_progress
with (security_invoker=true)
as
with qc as(
  select i.cutting_group_id,
    coalesce(sum(i.qty_good_pcs),0)::bigint raw_qc_good_qty_pcs,
    coalesce(sum(i.qty_bs_pcs),0)::bigint raw_qc_bs_qty_pcs,
    coalesce(sum(i.qty_good_pcs+i.qty_bs_pcs),0)::bigint raw_qc_accounted_qty_pcs,
    coalesce(sum(i.qty_good_pcs+i.qty_bs_pcs)
      filter(where i.source_laundry_receipt_line_id is not null),0)::bigint laundry_qc_accounted_qty_pcs,
    coalesce(sum(i.qty_good_pcs+i.qty_bs_pcs)
      filter(where i.source_laundry_receipt_line_id is null),0)::bigint direct_qc_accounted_qty_pcs,
    count(distinct q.id)::bigint completion_count,
    max(q.physical_at) last_completion_at
  from erp.qc_inspection_items i
  join erp.qc_inspections q on q.id=i.inspection_id
  where q.status='POSTED'
  group by i.cutting_group_id
),latest_completion as(
  select distinct on(i.cutting_group_id)
    i.cutting_group_id,q.completion_mode
  from erp.qc_inspection_items i
  join erp.qc_inspections q on q.id=i.inspection_id
  where q.status='POSTED' and q.completion_mode is not null
  order by i.cutting_group_id,q.physical_at desc,q.id desc
),laundry as(
  select l.cutting_group_id,coalesce(sum(l.qty_sent_pcs),0)::bigint laundry_sent_qty_pcs
  from erp.laundry_delivery_lines l
  join erp.laundry_deliveries d on d.id=l.delivery_id
  where d.status not in('DRAFT','REVERSED')
  group by l.cutting_group_id
),laundry_returned as(
  select dl.cutting_group_id,
    coalesce(sum(rl.qty_good_received),0)::bigint laundry_good_returned_qty_pcs,
    coalesce(sum(rl.qty_bs_laundry),0)::bigint laundry_bs_returned_qty_pcs,
    coalesce(sum(rl.qty_good_received+rl.qty_bs_laundry),0)::bigint laundry_returned_qty_pcs
  from erp.laundry_receipt_lines rl
  join erp.laundry_receipts r on r.id=rl.receipt_id
  join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
  join erp.laundry_deliveries d on d.id=dl.delivery_id
  where r.status='POSTED' and d.status<>'REVERSED'
  group by dl.cutting_group_id
),resolved_claim as(
  -- CP5 makes MISSING/STUCK delivery-bound. Count it only when the delivery
  -- resolves to exactly one Potongan; ambiguous legacy multi-group deliveries
  -- are never guessed into a terminal quantity.
  select source.cutting_group_id,
    coalesce(sum(c.qty_claimed),0)::bigint resolved_claim_qty_pcs
  from erp.laundry_claims c
  join lateral(
    select min(dl.cutting_group_id::text)::uuid cutting_group_id
    from erp.laundry_delivery_lines dl
    where dl.delivery_id=c.delivery_id
    having count(distinct dl.cutting_group_id)=1
  ) source on true
  where c.claim_type in('MISSING','STUCK') and c.status in('SETTLED','WRITTEN_OFF')
  group by source.cutting_group_id
),progress as(
  select g.id cutting_group_id,g.po_id,g.group_number,g.row_version,po.status po_status,
    coalesce(t.total_pcs,0)::bigint effective_qty_pcs,
    coalesce(q.raw_qc_good_qty_pcs,0)::bigint qc_good_qty_pcs,
    (coalesce(q.raw_qc_bs_qty_pcs,0)+coalesce(lr.laundry_bs_returned_qty_pcs,0)
      +coalesce(rc.resolved_claim_qty_pcs,0))::bigint qc_bs_qty_pcs,
    (coalesce(q.raw_qc_accounted_qty_pcs,0)+coalesce(lr.laundry_bs_returned_qty_pcs,0)
      +coalesce(rc.resolved_claim_qty_pcs,0))::bigint qc_accounted_qty_pcs,
    greatest(coalesce(t.total_pcs,0)-coalesce(q.raw_qc_accounted_qty_pcs,0)
      -coalesce(lr.laundry_bs_returned_qty_pcs,0)
      -coalesce(rc.resolved_claim_qty_pcs,0),0)::bigint remaining_qc_qty_pcs,
    coalesce(q.direct_qc_accounted_qty_pcs,0)::bigint direct_qc_accounted_qty_pcs,
    coalesce(q.laundry_qc_accounted_qty_pcs,0)::bigint laundry_qc_accounted_qty_pcs,
    coalesce(l.laundry_sent_qty_pcs,0)::bigint laundry_sent_qty_pcs,
    coalesce(lr.laundry_good_returned_qty_pcs,0)::bigint laundry_good_returned_qty_pcs,
    coalesce(lr.laundry_bs_returned_qty_pcs,0)::bigint laundry_bs_returned_qty_pcs,
    coalesce(lr.laundry_returned_qty_pcs,0)::bigint laundry_returned_qty_pcs,
    coalesce(rc.resolved_claim_qty_pcs,0)::bigint resolved_claim_qty_pcs,
    greatest(coalesce(lr.laundry_good_returned_qty_pcs,0)
      -coalesce(q.laundry_qc_accounted_qty_pcs,0),0)::bigint ready_for_qc_qty_pcs,
    greatest(coalesce(l.laundry_sent_qty_pcs,0)-coalesce(lr.laundry_returned_qty_pcs,0)
      -coalesce(rc.resolved_claim_qty_pcs,0),0)::bigint laundry_outstanding_qty_pcs,
    (coalesce(q.direct_qc_accounted_qty_pcs,0)+coalesce(l.laundry_sent_qty_pcs,0))::bigint source_accounted_qty_pcs,
    greatest(coalesce(t.total_pcs,0)-coalesce(q.direct_qc_accounted_qty_pcs,0)
      -coalesce(l.laundry_sent_qty_pcs,0),0)::bigint remaining_source_qty_pcs,
    coalesce(q.completion_count,0)::bigint completion_count,
    q.last_completion_at,lc.completion_mode last_completion_mode
  from erp.cutting_groups g
  join erp.production_orders po on po.id=g.po_id
  left join erp.v_cutting_group_totals t on t.cutting_group_id=g.id
  left join qc q on q.cutting_group_id=g.id
  left join latest_completion lc on lc.cutting_group_id=g.id
  left join laundry l on l.cutting_group_id=g.id
  left join laundry_returned lr on lr.cutting_group_id=g.id
  left join resolved_claim rc on rc.cutting_group_id=g.id
)
select
  cutting_group_id,po_id,group_number,row_version,po_status,effective_qty_pcs,
  qc_good_qty_pcs,qc_bs_qty_pcs,qc_accounted_qty_pcs,remaining_qc_qty_pcs,
  direct_qc_accounted_qty_pcs,laundry_sent_qty_pcs,source_accounted_qty_pcs,
  remaining_source_qty_pcs,completion_count,last_completion_at,
  case
    when po_status='FINISHED' then 'FINISHED'
    when qc_accounted_qty_pcs=0 then 'OPEN'
    when ready_for_qc_qty_pcs>0 and last_completion_mode='PARTIAL_SELECTION' then 'PARTIAL_SELECTION'
    when ready_for_qc_qty_pcs>0 then 'READY_FOR_QC'
    when laundry_outstanding_qty_pcs>0 then 'WAITING_LAUNDRY'
    when remaining_qc_qty_pcs>0 and last_completion_mode='PARTIAL_SELECTION' then 'PARTIAL_SELECTION'
    when remaining_qc_qty_pcs>0 then 'OPEN_SOURCE'
    else 'QC_COMPLETE'
  end::text completion_status,
  laundry_qc_accounted_qty_pcs,laundry_good_returned_qty_pcs,
  laundry_bs_returned_qty_pcs,laundry_returned_qty_pcs,resolved_claim_qty_pcs,
  ready_for_qc_qty_pcs,laundry_outstanding_qty_pcs,last_completion_mode
from progress;

alter view erp.v_fg_partial_completion_progress owner to postgres;
revoke all on table erp.v_fg_partial_completion_progress from public,anon;
grant select on table erp.v_fg_partial_completion_progress to authenticated,service_role;

-- Reconcile CP5 delivery-bound STUCK/MISSING claims with the WIP control view.
-- An open claim is an explicit issue instead of generic in-transit stock; a
-- SETTLED/WRITTEN_OFF claim is terminal loss. Legacy receipt-side stuck/missing
-- remains supported, and greatest() prevents counting the same issue twice.
create or replace view erp.v_wip_control_status_v1
with (security_invoker=true)
as
with sewing as(
  select e.cutting_group_id,coalesce(sum(e.qty_signed),0)::bigint sewn_qty_pcs
  from erp.sewing_terminal_events e
  where e.cutting_group_id is not null
  group by e.cutting_group_id
),laundry as(
  select l.cutting_group_id,
    coalesce(sum(l.qty_sent_pcs) filter(where d.status='DRAFT'),0)::bigint laundry_draft_qty_pcs,
    coalesce(sum(l.qty_sent_pcs) filter(where d.status not in('DRAFT','REVERSED')),0)::bigint laundry_sent_qty_pcs
  from erp.laundry_delivery_lines l
  join erp.laundry_deliveries d on d.id=l.delivery_id
  group by l.cutting_group_id
),receipt as(
  select dl.cutting_group_id,
    coalesce(sum(rl.qty_good_received+rl.qty_bs_laundry),0)::bigint laundry_good_bs_qty_pcs,
    coalesce(sum(rl.qty_stuck),0)::bigint laundry_stuck_qty_pcs,
    coalesce(sum(rl.qty_missing),0)::bigint laundry_missing_qty_pcs
  from erp.laundry_receipt_lines rl
  join erp.laundry_receipts rr on rr.id=rl.receipt_id and rr.status='POSTED'
  join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
  join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
  group by dl.cutting_group_id
),claim as(
  select source.cutting_group_id,
    coalesce(sum(c.qty_claimed) filter(where c.status<>'REJECTED'),0)::bigint active_issue_qty_pcs,
    coalesce(sum(c.qty_claimed) filter(where c.status in('SETTLED','WRITTEN_OFF')),0)::bigint resolved_issue_qty_pcs
  from erp.laundry_claims c
  join lateral(
    select min(dl.cutting_group_id::text)::uuid cutting_group_id
    from erp.laundry_delivery_lines dl
    where dl.delivery_id=c.delivery_id
    having count(distinct dl.cutting_group_id)=1
  ) source on true
  where c.claim_type in('MISSING','STUCK')
  group by source.cutting_group_id
),bs as(
  select b.cutting_group_id,count(*)::bigint open_bs_count
  from erp.bs_cases b
  where b.cutting_group_id is not null
    and b.status not in('RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED')
  group by b.cutting_group_id
),rework as(
  select b.cutting_group_id,count(*)::bigint open_rework_count
  from erp.rework_orders r
  join erp.bs_cases b on b.id=r.bs_case_id
  where b.cutting_group_id is not null and r.status not in('COMPLETED','CANCELLED')
  group by b.cutting_group_id
),blocker as(
  select f.cutting_group_id,count(*)::bigint open_flag_count,
    coalesce(jsonb_agg(jsonb_build_object(
      'id',f.id,'type',f.flag_type,'note',f.note,'row_version',f.row_version
    ) order by f.flag_type,f.id),'[]'::jsonb) open_flags
  from erp.wip_control_flags f where f.status='OPEN'
  group by f.cutting_group_id
),measured as(
  select
    g.id cutting_group_id,g.po_id,g.cutting_batch_id,g.group_number,g.status group_status,
    g.row_version,g.updated_at,po.po_number,po.status po_status,po.current_stage,
    m.model_code,m.model_name,g.executor_name,g.picked_up_at,g.notes,g.pattern_id,
    coalesce(g.pattern_code_snapshot,p.pattern_code) pattern_code,
    coalesce(g.pattern_revision_snapshot,p.revision) pattern_revision,
    coalesce(g.pattern_name_snapshot,p.pattern_name,g.pattern_type) pattern_name,
    p.sort_order pattern_sort_order,p.is_active pattern_is_active,
    coalesce(q.total_pcs,0)::bigint effective_qty_pcs,
    greatest(coalesce(s.sewn_qty_pcs,0),0)::bigint sewn_qty_pcs,
    greatest(coalesce(q.total_pcs,0)-greatest(
      coalesce(s.sewn_qty_pcs,0),coalesce(l.laundry_sent_qty_pcs,0),coalesce(fg.qc_accounted_qty_pcs,0)
    ),0)::bigint unfinished_sewing_qty_pcs,
    greatest(coalesce(s.sewn_qty_pcs,0)-coalesce(l.laundry_sent_qty_pcs,0)
      -coalesce(fg.direct_qc_accounted_qty_pcs,0),0)::bigint unsent_ready_qty_pcs,
    coalesce(l.laundry_draft_qty_pcs,0)::bigint laundry_draft_qty_pcs,
    coalesce(l.laundry_sent_qty_pcs,0)::bigint laundry_sent_qty_pcs,
    greatest(coalesce(l.laundry_sent_qty_pcs,0)-coalesce(rr.laundry_good_bs_qty_pcs,0)
      -greatest(coalesce(rr.laundry_stuck_qty_pcs,0)+coalesce(rr.laundry_missing_qty_pcs,0),
        coalesce(cl.active_issue_qty_pcs,0)),0)::bigint laundry_in_transit_qty_pcs,
    coalesce(rr.laundry_good_bs_qty_pcs,0)::bigint laundry_good_bs_qty_pcs,
    greatest(greatest(
      coalesce(rr.laundry_stuck_qty_pcs,0)+coalesce(rr.laundry_missing_qty_pcs,0),
      coalesce(cl.active_issue_qty_pcs,0)
    )-coalesce(cl.resolved_issue_qty_pcs,0),0)::bigint unresolved_laundry_issue_qty_pcs,
    coalesce(fg.ready_for_qc_qty_pcs,0)::bigint pending_final_sku_handoff_qty_pcs,
    coalesce(fg.remaining_qc_qty_pcs,coalesce(q.total_pcs,0))::bigint remaining_final_sku_qty_pcs,
    coalesce(bs.open_bs_count,0)::bigint open_bs_count,
    coalesce(rw.open_rework_count,0)::bigint open_rework_count,
    coalesce(bl.open_flag_count,0)::bigint open_flag_count,
    coalesce(bl.open_flags,'[]'::jsonb) open_flags
  from erp.cutting_groups g
  join erp.production_orders po on po.id=g.po_id
  join erp.product_models m on m.id=po.model_id
  left join erp.production_patterns p on p.id=g.pattern_id
  left join erp.v_cutting_group_totals q on q.cutting_group_id=g.id
  left join sewing s on s.cutting_group_id=g.id
  left join laundry l on l.cutting_group_id=g.id
  left join receipt rr on rr.cutting_group_id=g.id
  left join claim cl on cl.cutting_group_id=g.id
  left join erp.v_fg_partial_completion_progress fg on fg.cutting_group_id=g.id
  left join bs on bs.cutting_group_id=g.id
  left join rework rw on rw.cutting_group_id=g.id
  left join blocker bl on bl.cutting_group_id=g.id
)
select measured.*,
  case
    when po_status='CANCELLED'
      and unsent_ready_qty_pcs=0 and laundry_draft_qty_pcs=0
      and laundry_in_transit_qty_pcs=0 and unresolved_laundry_issue_qty_pcs=0
      and pending_final_sku_handoff_qty_pcs=0
      and open_bs_count=0 and open_rework_count=0 and open_flag_count=0
      then 'COMPLETED'
    when effective_qty_pcs>0 and unfinished_sewing_qty_pcs=0
      and unsent_ready_qty_pcs=0 and laundry_draft_qty_pcs=0
      and laundry_in_transit_qty_pcs=0 and unresolved_laundry_issue_qty_pcs=0
      and pending_final_sku_handoff_qty_pcs=0 and remaining_final_sku_qty_pcs=0
      and open_bs_count=0 and open_rework_count=0 and open_flag_count=0
      then 'COMPLETED'
    else 'ACTIVE'
  end::text control_status,
  jsonb_build_object(
    'unfinished_sewing',unfinished_sewing_qty_pcs>0,
    'unsent_ready',unsent_ready_qty_pcs>0,
    'laundry_draft',laundry_draft_qty_pcs>0,
    'laundry_in_transit',laundry_in_transit_qty_pcs>0,
    'laundry_issue',unresolved_laundry_issue_qty_pcs>0,
    'pending_final_sku_handoff',pending_final_sku_handoff_qty_pcs>0,
    'remaining_final_sku',remaining_final_sku_qty_pcs>0,
    'open_bs',open_bs_count>0,'open_rework',open_rework_count>0,
    'operator_flag',open_flag_count>0
  ) blockers
from measured;

alter view erp.v_wip_control_status_v1 owner to postgres;
revoke all on table erp.v_wip_control_status_v1 from public,anon,authenticated,service_role;

create function erp.get_laundry_qc_workspace_v1(
  p_scope text default 'LAUNDRY',p_query text default null
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
declare
  v_scope text:=upper(coalesce(nullif(btrim(p_scope),''),'LAUNDRY'));
  v_query text:=lower(nullif(btrim(p_query),''));
  v_vendors jsonb;
  v_processes jsonb;
  v_rates jsonb;
  v_locations jsonb;
  v_products jsonb;
  v_ready jsonb:='[]'::jsonb;
  v_deliveries jsonb:='[]'::jsonb;
  v_qc_queue jsonb:='[]'::jsonb;
  v_qc_history jsonb:='[]'::jsonb;
  v_lineage_issue_count bigint:=0;
begin
  if v_scope not in('LAUNDRY','QC') then raise exception 'scope must be LAUNDRY or QC'; end if;
  if v_scope='LAUNDRY' then perform erp.require_permission('production.laundry.view');
  else perform erp.require_permission('production.final_sku.view'); end if;

  select coalesce(jsonb_agg(jsonb_build_object(
    'id',v.id,'code',v.vendor_code,'name',v.vendor_name
  ) order by v.vendor_name,v.id),'[]'::jsonb) into v_vendors
  from erp.laundry_vendors v where v.is_active;
  select coalesce(jsonb_agg(jsonb_build_object(
    'id',w.id,'code',w.process_code,'name',w.process_name
  ) order by w.process_name,w.id),'[]'::jsonb) into v_processes
  from erp.wash_processes w where w.is_active;
  select coalesce(jsonb_agg(to_jsonb(x) order by x.vendor_id,x.wash_process_id,x.effective_from desc,x.id),'[]'::jsonb)
    into v_rates
  from(
    select r.id,r.vendor_id,r.wash_process_id,r.rate_per_pcs,r.effective_from,r.effective_to
    from erp.laundry_vendor_rate_versions r
    join erp.laundry_vendors v on v.id=r.vendor_id and v.is_active
    join erp.wash_processes w on w.id=r.wash_process_id and w.is_active
    order by r.vendor_id,r.wash_process_id,r.effective_from desc,r.created_at desc,r.id desc
  ) x;
  select coalesce(jsonb_agg(jsonb_build_object(
    'id',l.id,'code',l.location_code,'name',l.location_name
  ) order by l.location_name,l.id),'[]'::jsonb) into v_locations
  from erp.locations l where l.is_active and l.location_type='FG_WAREHOUSE';
  select coalesce(jsonb_agg(jsonb_build_object(
    'id',p.id,'sku',p.sku,'name',p.product_name,'model_id',p.model_id,
    'model_code',m.model_code,'model_name',m.model_name,
    'brand_id',p.brand_id,'brand_code',b.brand_code,'brand_name',b.brand_name,
    'size_id',p.size_id,'size_code',s.size_code,'color',p.color_name,
    'effective_from',p.effective_from,'effective_to',p.effective_to
  ) order by b.brand_name,p.sku,m.model_name,p.color_name,s.sort_order,p.id),'[]'::jsonb) into v_products
  from erp.products p
  join erp.product_models m on m.id=p.model_id and m.is_active
  join erp.brands b on b.id=p.brand_id and b.is_active
  join erp.sizes s on s.id=p.size_id and s.is_active
  where p.is_active and p.is_portal_visible;

  -- Read paths are also an integrity boundary. Never hide a malformed CP6
  -- chain by dropping it from a join and showing a smaller, apparently valid
  -- queue. Legacy rows without CP6 child lineage are reported separately;
  -- every row claiming CP6 lineage must be exact and no facade-created
  -- DRAFT/context residue may survive a commit.
  select
    (select count(*)
     from erp.laundry_delivery_batch_size_lines x
     join erp.laundry_delivery_lines dl on dl.id=x.delivery_line_id
     join erp.laundry_deliveries d on d.id=dl.delivery_id
     join erp.cutting_distribution_batches b on b.id=x.distribution_batch_id
     join erp.cutting_pickups p on p.id=b.pickup_id
     join erp.cutting_groups g on g.id=dl.cutting_group_id
     where p.status<>'POSTED'
        or p.cutting_group_id<>dl.cutting_group_id
        or g.po_id<>d.po_id
        or not exists(
          select 1
          from erp.cutting_distribution_allocations a
          join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
          join erp.cutting_group_size_slots sl on sl.id=y.size_slot_id
          where a.batch_id=x.distribution_batch_id and sl.size_id=x.size_id
          having coalesce(sum(a.qty_pcs),0)>0
        ))
    +(select count(*) from(
       select d.id
       from erp.laundry_deliveries d
       join erp.laundry_delivery_lines dl on dl.delivery_id=d.id
       join erp.laundry_delivery_batch_size_lines x on x.delivery_line_id=dl.id
       group by d.id,d.status
       having d.status='DRAFT'
          or count(distinct dl.id)<>1
          or count(distinct x.distribution_batch_id)<>1
          or sum(x.qty_sent_pcs)<>max(dl.qty_sent_pcs)
     ) broken_delivery)
    +(select count(*)
     from erp.laundry_receipt_batch_size_lines x
     join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
     join erp.laundry_receipts r on r.id=rl.receipt_id
     join erp.laundry_delivery_batch_size_lines sx on sx.id=x.delivery_batch_size_line_id
     join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
     join erp.laundry_deliveries d on d.id=dl.delivery_id
     where rl.delivery_line_id<>sx.delivery_line_id
        or r.delivery_id<>d.id
        or x.size_id<>sx.size_id
        or (x.qty_bs_laundry>0 and not exists(
          select 1
          from erp.products product
          join erp.production_orders po on po.id=d.po_id and po.model_id=product.model_id
          where product.id=x.bs_product_id and product.size_id=x.size_id
            and product.effective_from<=r.physical_at
            and(product.effective_to is null or product.effective_to>r.physical_at)
        )))
    +(select count(*) from(
       select r.id
       from erp.laundry_receipts r
       join erp.laundry_receipt_lines rl on rl.receipt_id=r.id
       join erp.laundry_receipt_batch_size_lines x on x.receipt_line_id=rl.id
       group by r.id,r.status
       having r.status='DRAFT'
          or count(distinct rl.id)<>1
          or sum(x.qty_good_received)<>max(rl.qty_good_received)
          or sum(x.qty_bs_laundry)<>max(rl.qty_bs_laundry)
          or max(rl.qty_stuck)<>0 or max(rl.qty_missing)<>0
     ) broken_receipt)
    +(select count(*)
      from erp.laundry_failed_wash_attempts a
      join erp.laundry_receipts r on r.id=a.receipt_id
      join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
      join erp.laundry_deliveries d on d.id=a.delivery_id
      where r.delivery_id<>a.delivery_id or rl.receipt_id<>r.id
         or dl.delivery_id<>d.id
         or rl.qty_good_received<>0 or rl.qty_bs_laundry<>0
         or rl.qty_stuck<>0 or rl.qty_missing<>0
         or rl.actual_wash_process_id is null
         or rl.actual_rate_snapshot is null or rl.actual_rate_snapshot<0
         or rl.actual_cost_status not in('ESTIMATED','FINAL')
         or rl.actual_cost is distinct from round(a.qty_attempted_pcs*rl.actual_rate_snapshot,2)
         or exists(select 1 from erp.laundry_receipt_batch_size_lines x
           where x.receipt_line_id=rl.id)
         or (select coalesce(sum(x.qty_attempted_pcs),0)
             from erp.laundry_failed_wash_batch_size_lines x
             where x.attempt_id=a.id)<>a.qty_attempted_pcs
         or exists(
           select 1 from erp.laundry_failed_wash_batch_size_lines x
           join erp.laundry_delivery_batch_size_lines s
             on s.id=x.delivery_batch_size_line_id
           where x.attempt_id=a.id and(
             s.delivery_line_id<>dl.id or s.size_id<>x.size_id
             or x.qty_attempted_pcs>s.qty_sent_pcs
           )
         )
         or (a.custody_outcome='RETRY_AT_VENDOR' and a.return_wip_event_id is not null)
         or (a.custody_outcome='RETURN_UNPROCESSED' and not exists(
           select 1 from erp.wip_stage_events rv
           join erp.wip_stage_events src
             on src.id=rv.source_id and src.source_type='LAUNDRY_DELIVERY_LINE'
           where rv.id=a.return_wip_event_id and src.source_id=dl.id
             and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
             and rv.stage_from='LAUNDRY' and rv.stage_to='SEWING'
             and rv.qty_pcs=a.qty_attempted_pcs
         )))
    +(select count(*)
     from erp.qc_inspection_items qi
     join erp.qc_inspections q on q.id=qi.inspection_id
     left join erp.laundry_receipt_batch_size_lines rx
       on rx.id=qi.source_laundry_receipt_batch_size_line_id
     left join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
     left join erp.laundry_receipts r on r.id=rl.receipt_id
     left join erp.laundry_delivery_batch_size_lines sx on sx.id=rx.delivery_batch_size_line_id
     left join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
     left join erp.laundry_deliveries d on d.id=dl.delivery_id
     left join erp.cutting_groups g on g.id=dl.cutting_group_id
     left join erp.products product on product.id=qi.final_product_id
     where qi.source_laundry_receipt_batch_size_line_id is not null
       and (rx.id is null
         or qi.source_laundry_receipt_line_id is distinct from rx.receipt_line_id
         or (q.status<>'REVERSED' and r.status is distinct from 'POSTED')
         or (q.status<>'REVERSED' and d.status='REVERSED')
         or r.delivery_id is distinct from d.id
         or qi.cutting_group_id is distinct from dl.cutting_group_id
         or q.po_id is distinct from d.po_id
         or g.po_id is distinct from d.po_id
         or product.size_id is distinct from rx.size_id
         or product.model_id is distinct from(
           select po.model_id from erp.production_orders po where po.id=d.po_id
         )
         or product.effective_from>q.physical_at
         or(product.effective_to is not null and product.effective_to<=q.physical_at)))
    +(select count(*) from erp.cp6_laundry_qc_execution_context)
  into v_lineage_issue_count;

  if v_scope='LAUNDRY' then
    select coalesce(jsonb_agg(to_jsonb(z) order by z.po_number,z.group_number,z.batch_no,z.distribution_batch_id),'[]'::jsonb)
      into v_ready
    from(
      select b.id distribution_batch_id,b.batch_no,p.id pickup_id,p.cutting_group_id,
        g.row_version cutting_group_row_version,g.group_number,g.pattern_id,
        coalesce(g.pattern_code_snapshot,pat.pattern_code) pattern_code,
        coalesce(g.pattern_revision_snapshot,pat.revision) pattern_revision,
        coalesce(g.pattern_name_snapshot,pat.pattern_name,g.pattern_type) pattern_name,
        po.id po_id,po.po_number,po.status po_status,m.model_code,m.model_name,
        c.id contractor_id,c.contractor_code,c.contractor_name,p.picked_up_at,
        coalesce(w.unsent_ready_qty_pcs,0)::bigint group_unsent_ready_qty_pcs,
        coalesce((
          select jsonb_agg(to_jsonb(q) order by q.sort_order,q.size_code,q.size_id)
          from(
            select s.id size_id,s.size_code,s.sort_order,
              sum(a.qty_pcs)::bigint allocated_qty_pcs,
              coalesce((
                select sum(x.qty_sent_pcs)
                from erp.laundry_delivery_batch_size_lines x
                join erp.laundry_delivery_lines dl on dl.id=x.delivery_line_id
                join erp.laundry_deliveries d on d.id=dl.delivery_id
                where x.distribution_batch_id=b.id and x.size_id=s.id
                  and d.status not in('DRAFT','REVERSED')
              ),0)::bigint sent_qty_pcs,
              greatest(sum(a.qty_pcs)-coalesce((
                select sum(x.qty_sent_pcs)
                from erp.laundry_delivery_batch_size_lines x
                join erp.laundry_delivery_lines dl on dl.id=x.delivery_line_id
                join erp.laundry_deliveries d on d.id=dl.delivery_id
                where x.distribution_batch_id=b.id and x.size_id=s.id
                  and d.status not in('DRAFT','REVERSED')
              ),0),0)::bigint available_qty_pcs
            from erp.cutting_distribution_allocations a
            join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
            join erp.cutting_group_size_slots sl on sl.id=y.size_slot_id
            join erp.sizes s on s.id=sl.size_id
            where a.batch_id=b.id
            group by s.id,s.size_code,s.sort_order
          ) q
        ),'[]'::jsonb) sizes
      from erp.cutting_distribution_batches b
      join erp.cutting_pickups p on p.id=b.pickup_id and p.status='POSTED'
      join erp.cutting_groups g on g.id=p.cutting_group_id
      join erp.production_orders po on po.id=g.po_id
      join erp.product_models m on m.id=po.model_id
      join erp.contractors c on c.id=p.contractor_id
      left join erp.production_patterns pat on pat.id=g.pattern_id
      left join erp.v_wip_control_status_v1 w on w.cutting_group_id=g.id
      where po.status not in('FINISHED','CANCELLED')
        and coalesce(w.unsent_ready_qty_pcs,0)>0
        and(v_query is null or lower(concat_ws(' ',po.po_number,g.group_number,
          m.model_code,m.model_name,c.contractor_code,c.contractor_name,
          g.pattern_code_snapshot,g.pattern_name_snapshot,b.batch_no::text)) like '%'||v_query||'%')
        and exists(
          select 1
          from(
            select sl.size_id,sum(a.qty_pcs)::bigint allocated_qty_pcs
            from erp.cutting_distribution_allocations a
            join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
            join erp.cutting_group_size_slots sl on sl.id=y.size_slot_id
            where a.batch_id=b.id group by sl.size_id
          ) cap
          where cap.allocated_qty_pcs>coalesce((
            select sum(x.qty_sent_pcs)
            from erp.laundry_delivery_batch_size_lines x
            join erp.laundry_delivery_lines dl on dl.id=x.delivery_line_id
            join erp.laundry_deliveries d on d.id=dl.delivery_id
            where x.distribution_batch_id=b.id and x.size_id=cap.size_id
              and d.status not in('DRAFT','REVERSED')
          ),0)
        )
    ) z;

    select coalesce(jsonb_agg(to_jsonb(z) order by z.physical_at desc,z.delivery_id desc),'[]'::jsonb)
      into v_deliveries
    from(
      select d.id delivery_id,d.delivery_number,d.row_version,d.status,d.physical_at,
        d.target_dyeing_color,d.special_instruction,d.po_id,po.po_number,po.model_id,
        g.id cutting_group_id,g.group_number,g.row_version cutting_group_row_version,
        m.model_code,m.model_name,c.contractor_name,v.id vendor_id,v.vendor_code,v.vendor_name,
        w.id wash_process_id,w.process_code,w.process_name,
        dl.id delivery_line_id,dl.qty_sent_pcs,dl.estimated_rate_snapshot,
        round(dl.qty_sent_pcs*coalesce(dl.estimated_rate_snapshot,0),2) estimated_cost,
        x.distribution_batch_id,b.batch_no,
        coalesce((select sum(rl.qty_good_received+rl.qty_bs_laundry)
          from erp.laundry_receipt_lines rl join erp.laundry_receipts r on r.id=rl.receipt_id
          where rl.delivery_line_id=dl.id and r.status='POSTED'),0)::bigint returned_qty_pcs,
        case when d.status='REVERSED' then 0 else greatest(dl.qty_sent_pcs-coalesce((select sum(rl.qty_good_received+rl.qty_bs_laundry)
          from erp.laundry_receipt_lines rl join erp.laundry_receipts r on r.id=rl.receipt_id
          where rl.delivery_line_id=dl.id and r.status='POSTED'),0),0) end::bigint physical_outstanding_qty_pcs,
        case when d.status='REVERSED' then dl.qty_sent_pcs else 0 end::bigint returned_unprocessed_qty_pcs,
        coalesce((select sum(cl.qty_claimed) from erp.laundry_claims cl
          where cl.delivery_id=d.id and cl.claim_type in('STUCK','MISSING')
            and cl.status<>'REJECTED'),0)::bigint active_claim_qty_pcs,
        rev.reversal_blocker is null as reversible,
        rev.reversal_blocker,
        coalesce((select jsonb_agg(to_jsonb(sq) order by sq.sort_order,sq.size_code,sq.delivery_batch_size_line_id)
          from(
            select sx.id delivery_batch_size_line_id,s.id size_id,s.size_code,s.sort_order,
              sx.qty_sent_pcs,
              coalesce(sum(rx.qty_good_received) filter(where rh.status='POSTED'),0)::bigint good_returned_qty_pcs,
              coalesce(sum(rx.qty_bs_laundry) filter(where rh.status='POSTED'),0)::bigint bs_returned_qty_pcs,
              case when d.status='REVERSED' then 0 else
                greatest(sx.qty_sent_pcs-coalesce(sum(rx.qty_good_received+rx.qty_bs_laundry)
                  filter(where rh.status='POSTED'),0),0) end::bigint outstanding_qty_pcs
            from erp.laundry_delivery_batch_size_lines sx
            join erp.sizes s on s.id=sx.size_id
            left join erp.laundry_receipt_batch_size_lines rx on rx.delivery_batch_size_line_id=sx.id
            left join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
            left join erp.laundry_receipts rh on rh.id=rl.receipt_id
            where sx.delivery_line_id=dl.id
            group by sx.id,s.id,s.size_code,s.sort_order,sx.qty_sent_pcs
          ) sq),'[]'::jsonb) sizes,
        coalesce((select jsonb_agg(jsonb_build_object(
          'id',r.id,'number',r.receipt_number,'status',r.status,'row_version',r.row_version,
          'physical_at',r.physical_at,'actual_cost',rl.actual_cost,
          'actual_rate',rl.actual_rate_snapshot,'cost_status',rl.actual_cost_status,
          'event_kind',case when fa.id is null then 'PHYSICAL_RECEIPT' else 'FAILED_WASH_ATTEMPT' end,
          'failed_wash_attempt_id',fa.id,'custody_outcome',fa.custody_outcome,
          'attempted_qty_pcs',fa.qty_attempted_pcs,'process_name',aw.process_name,
          'reversible',rr.reversal_blocker is null,
          'reversal_blocker',rr.reversal_blocker
        ) order by r.physical_at desc,r.id desc)
          from erp.laundry_receipts r join erp.laundry_receipt_lines rl on rl.receipt_id=r.id
          left join erp.laundry_failed_wash_attempts fa on fa.receipt_line_id=rl.id
          left join erp.wash_processes aw on aw.id=rl.actual_wash_process_id
          cross join lateral(
            select case
              when r.status<>'POSTED' then 'Receipt bukan POSTED aktif.'
              when po.status='FINISHED' then 'PO sudah FINISHED; reopen downstream terlebih dahulu.'
              when fa.id is not null and exists(
                select 1 from erp.vendor_invoice_items vii
                join erp.vendor_invoices vi on vi.id=vii.invoice_id
                where vii.receipt_line_id=rl.id and vi.status<>'REVERSED'
              ) then 'Biaya cuci gagal sudah ditagih; reverse invoice vendor aktif terlebih dahulu.'
              when fa.id is not null and(
                exists(select 1 from erp.laundry_receipt_batch_size_lines bx
                  where bx.receipt_line_id=rl.id)
                or exists(select 1 from erp.qc_inspection_items qi
                  where qi.source_laundry_receipt_line_id=rl.id)
                or exists(select 1 from erp.wip_stage_events wip
                  where wip.source_type='LAUNDRY_RECEIPT_LINE' and wip.source_id=rl.id)
              ) then 'Attempt cuci gagal memiliki histori fisik/QC yang tidak semestinya; reversal dikunci untuk investigasi.'
              when fa.id is not null then null
              when d.status='REVERSED' then 'Surat kirim sumber sudah direverse.'
              when exists(
                select 1 from erp.qc_inspection_items qi
                join erp.qc_inspections qh on qh.id=qi.inspection_id
                where qi.source_laundry_receipt_line_id=rl.id and qh.status<>'REVERSED'
              ) then 'Receipt sudah dipakai QC; reverse QC aktif terlebih dahulu.'
              when exists(
                select 1 from erp.vendor_invoice_items vii
                join erp.vendor_invoices vi on vi.id=vii.invoice_id
                where vii.receipt_line_id=rl.id and vi.status<>'REVERSED'
              ) then 'Receipt sudah ditagih; reverse invoice vendor aktif terlebih dahulu.'
              when exists(
                select 1 from erp.laundry_claims lc
                where(lc.receipt_line_id=rl.id or lc.delivery_id=d.id)
                  and lc.status<>'REJECTED'
              ) then 'Receipt/surat kirim masih dipakai claim; bereskan claim terlebih dahulu.'
              when exists(
                select 1 from erp.bs_cases bc
                where(bc.source_laundry_receipt_line_id=rl.id
                  or bc.bs_number='BS-LAU-'||r.receipt_number||'-'||substr(rl.id::text,1,8))
                  and(
                    exists(select 1 from erp.rework_orders ro
                      where ro.bs_case_id=bc.id and ro.status<>'CANCELLED')
                    or exists(select 1 from erp.bs_resolutions br where br.bs_case_id=bc.id)
                  )
              ) then 'BS dari receipt sudah diproses; reverse downstream BS terlebih dahulu.'
              when(
                select count(*) from erp.wip_stage_events wip
                where wip.source_type='LAUNDRY_RECEIPT_LINE' and wip.source_id=rl.id
              )<>1 or(
                select count(*) from erp.wip_stage_events wip
                where wip.source_type='LAUNDRY_RECEIPT_LINE'
                  and wip.source_id=rl.id and wip.po_id=d.po_id
                  and wip.stage_from='LAUNDRY' and wip.stage_to='QC'
                  and wip.qty_pcs=rl.qty_good_received+rl.qty_bs_laundry
              )<>1 then 'Histori WIP receipt tidak utuh; reversal dikunci untuk investigasi.'
              when exists(
                select 1
                from erp.laundry_receipt_batch_size_lines bx
                where bx.receipt_line_id=rl.id and bx.qty_bs_laundry>0
                  and((
                      select count(*) from erp.wip_stage_events wip
                      where wip.source_type='CP6_LAUNDRY_BS_SIZE_LINE'
                        and wip.source_id=bx.id
                    )<>1 or(
                      select count(*) from erp.wip_stage_events wip
                      where wip.source_type='CP6_LAUNDRY_BS_SIZE_LINE'
                        and wip.source_id=bx.id and wip.stage_from='QC'
                        and wip.stage_to='ON_HOLD' and wip.qty_pcs=bx.qty_bs_laundry
                    )<>1)
              ) then 'Histori WIP BS Laundry tidak utuh; reversal dikunci untuk investigasi.'
              else null
            end reversal_blocker
          ) rr
          where r.delivery_id=d.id),'[]'::jsonb) receipts
      from erp.laundry_deliveries d
      join erp.laundry_delivery_lines dl on dl.delivery_id=d.id
      join erp.laundry_delivery_batch_size_lines x on x.delivery_line_id=dl.id
      join erp.cutting_distribution_batches b on b.id=x.distribution_batch_id
      join erp.cutting_groups g on g.id=dl.cutting_group_id and g.po_id=d.po_id
      join erp.production_orders po on po.id=d.po_id and po.id=g.po_id
      join erp.product_models m on m.id=po.model_id
      join erp.cutting_pickups p on p.id=b.pickup_id and p.status='POSTED'
        and p.cutting_group_id=g.id
      join erp.contractors c on c.id=p.contractor_id
      join erp.laundry_vendors v on v.id=d.vendor_id
      left join erp.wash_processes w on w.id=d.target_wash_process_id
      cross join lateral(
        select case
          when d.status not in('SENT','PARTIAL_RETURN','RETURNED','CLOSED')
            then 'Surat kirim bukan dokumen posted aktif.'
          when po.status='FINISHED'
            then 'PO sudah FINISHED; reopen downstream terlebih dahulu.'
          when exists(select 1 from erp.laundry_receipts r
            where r.delivery_id=d.id and r.status<>'REVERSED')
            then 'Masih ada receipt aktif; reverse receipt terlebih dahulu.'
          when exists(select 1 from erp.laundry_claims cl
            where cl.delivery_id=d.id and cl.status<>'REJECTED')
            then 'Masih ada claim aktif/terselesaikan; bereskan claim terlebih dahulu.'
          when exists(
            select 1
            from erp.laundry_delivery_lines lx
            left join erp.wip_stage_events wip
              on wip.source_type='LAUNDRY_DELIVERY_LINE' and wip.source_id=lx.id
            where lx.delivery_id=d.id
            group by lx.id,lx.qty_sent_pcs
            having count(wip.id)<>1 or count(wip.id) filter(where
              wip.po_id=d.po_id and wip.stage_from='SEWING' and wip.stage_to='LAUNDRY'
              and wip.qty_pcs=lx.qty_sent_pcs
            )<>1
          ) then 'Histori WIP surat kirim tidak utuh; reversal dikunci untuk investigasi.'
          else null
        end reversal_blocker
      ) rev
      where(v_query is null or lower(concat_ws(' ',d.delivery_number,po.po_number,g.group_number,
        m.model_code,m.model_name,v.vendor_code,v.vendor_name,w.process_code,w.process_name)) like '%'||v_query||'%')
      group by d.id,d.delivery_number,d.row_version,d.status,d.physical_at,
        d.target_dyeing_color,d.special_instruction,d.po_id,po.po_number,po.model_id,po.status,g.id,g.group_number,g.row_version,
        m.model_code,m.model_name,c.contractor_name,v.id,v.vendor_code,v.vendor_name,
        w.id,w.process_code,w.process_name,dl.id,dl.qty_sent_pcs,dl.estimated_rate_snapshot,
        x.distribution_batch_id,b.batch_no,rev.reversal_blocker
    ) z;
  else
    select coalesce(jsonb_agg(to_jsonb(z) order by z.po_number,z.group_number,z.batch_no,z.size_sort,z.size_code,z.source_batch_size_line_id),'[]'::jsonb)
      into v_qc_queue
    from(
      select rx.id source_batch_size_line_id,rx.receipt_line_id,rl.receipt_id,
        r.receipt_number,r.physical_at receipt_physical_at,
        sx.distribution_batch_id,b.batch_no,sx.delivery_line_id,d.id delivery_id,
        d.delivery_number,v.vendor_name,dl.cutting_group_id,g.group_number,g.row_version cutting_group_row_version,
        po.id po_id,po.po_number,po.model_id,m.model_code,m.model_name,
        rx.size_id,s.size_code,s.sort_order size_sort,rx.qty_good_received,
        coalesce((select sum(i.qty_good_pcs+i.qty_bs_pcs)
          from erp.qc_inspection_items i join erp.qc_inspections q on q.id=i.inspection_id
          where i.source_laundry_receipt_batch_size_line_id=rx.id and q.status<>'REVERSED'),0)::bigint qc_accounted_qty_pcs,
        greatest(rx.qty_good_received-coalesce((select sum(i.qty_good_pcs+i.qty_bs_pcs)
          from erp.qc_inspection_items i join erp.qc_inspections q on q.id=i.inspection_id
          where i.source_laundry_receipt_batch_size_line_id=rx.id and q.status<>'REVERSED'),0),0)::bigint available_for_qc_qty_pcs,
        fp.completion_status,fp.remaining_qc_qty_pcs
      from erp.laundry_receipt_batch_size_lines rx
      join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
      join erp.laundry_delivery_batch_size_lines sx on sx.id=rx.delivery_batch_size_line_id
      join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
        and dl.id=rl.delivery_line_id
      join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
      join erp.laundry_receipts r on r.id=rl.receipt_id and r.status='POSTED'
        and r.delivery_id=d.id
      join erp.cutting_distribution_batches b on b.id=sx.distribution_batch_id
      join erp.cutting_pickups p on p.id=b.pickup_id and p.status='POSTED'
        and p.cutting_group_id=dl.cutting_group_id
      join erp.cutting_groups g on g.id=dl.cutting_group_id and g.po_id=d.po_id
      join erp.production_orders po on po.id=d.po_id and po.id=g.po_id
      join erp.product_models m on m.id=po.model_id
      join erp.laundry_vendors v on v.id=d.vendor_id
      join erp.sizes s on s.id=rx.size_id and s.id=sx.size_id
      join erp.v_fg_partial_completion_progress fp on fp.cutting_group_id=g.id
      where rx.qty_good_received>coalesce((select sum(i.qty_good_pcs+i.qty_bs_pcs)
          from erp.qc_inspection_items i join erp.qc_inspections q on q.id=i.inspection_id
          where i.source_laundry_receipt_batch_size_line_id=rx.id and q.status<>'REVERSED'),0)
        and(v_query is null or lower(concat_ws(' ',r.receipt_number,d.delivery_number,po.po_number,
          g.group_number,m.model_code,m.model_name,v.vendor_name,s.size_code,b.batch_no::text)) like '%'||v_query||'%')
    ) z;

    select coalesce(jsonb_agg(to_jsonb(z) order by z.physical_at desc,z.qc_inspection_id desc),'[]'::jsonb)
      into v_qc_history
    from(
      select q.id qc_inspection_id,q.inspection_number,q.status,q.row_version,q.physical_at,
        q.destination_location_id,l.location_name,q.po_id,po.po_number,
        sum(i.qty_good_pcs)::bigint good_qty_pcs,sum(i.qty_bs_pcs)::bigint bs_qty_pcs,
        count(distinct i.cutting_group_id)::integer cutting_group_count,
        rev.reversal_blocker is null as reversible,rev.reversal_blocker
      from erp.qc_inspections q
      join erp.qc_inspection_items i on i.inspection_id=q.id
      join erp.production_orders po on po.id=q.po_id
      left join erp.locations l on l.id=q.destination_location_id
      cross join lateral(
        select case
          when q.status<>'POSTED' then 'Finalisasi QC bukan POSTED aktif.'
          when po.status='FINISHED' then 'PO sudah FINISHED; reopen downstream terlebih dahulu.'
          when exists(
            select 1 from erp.bs_cases bc
            where bc.qc_item_id in(select x.id from erp.qc_inspection_items x where x.inspection_id=q.id)
              and bc.status<>'CANCELLED'
              and(
                exists(select 1 from erp.rework_orders ro
                  where ro.bs_case_id=bc.id and ro.status<>'CANCELLED')
                or exists(select 1 from erp.bs_resolutions br where br.bs_case_id=bc.id)
              )
          ) then 'BS hasil QC sudah diproses; reverse downstream BS terlebih dahulu.'
          when exists(
            select 1 from erp.fg_lots fl
            where fl.qc_item_id in(select x.id from erp.qc_inspection_items x where x.inspection_id=q.id)
              and fl.lot_origin='PRODUCTION'
              and erp.fg_lot_has_active_downstream(fl.id,'QC_GOOD','QC_ITEM',fl.qc_item_id)
          ) then 'FG hasil QC masih dipakai transaksi downstream aktif.'
          when exists(
            select 1 from erp.contractor_accessory_reimbursement_entitlements e
            join erp.fg_lots fl on fl.id=e.lot_id
            where fl.qc_item_id in(select x.id from erp.qc_inspection_items x where x.inspection_id=q.id)
              and fl.lot_origin='PRODUCTION' and e.payroll_status<>'UNALLOCATED'
          ) then 'Reimbursement aksesori sudah masuk payroll; reverse payroll terlebih dahulu.'
          else null
        end reversal_blocker
      ) rev
      where i.source_laundry_receipt_batch_size_line_id is not null
        and(v_query is null or lower(concat_ws(' ',q.inspection_number,po.po_number,l.location_name)) like '%'||v_query||'%')
      group by q.id,q.inspection_number,q.status,q.row_version,q.physical_at,
        q.destination_location_id,l.location_name,q.po_id,po.po_number,po.status,rev.reversal_blocker
    ) z;
  end if;

  return jsonb_build_object(
    'contract_version','CP6_V2620','scope',v_scope,'generated_at',statement_timestamp(),
    'lookups',jsonb_build_object(
      'vendors',v_vendors,'wash_processes',v_processes,'rate_versions',v_rates,
      'fg_locations',v_locations,'products',v_products
    ),
    'readiness',jsonb_build_object(
      'laundry_writer_ready',v_lineage_issue_count=0
        and jsonb_array_length(v_vendors)>0
        and jsonb_array_length(v_processes)>0 and jsonb_array_length(v_rates)>0,
      'qc_writer_ready',v_lineage_issue_count=0
        and jsonb_array_length(v_locations)>0 and jsonb_array_length(v_products)>0,
      'lineage_integrity_ok',v_lineage_issue_count=0,
      'lineage_issue_count',v_lineage_issue_count,
      'no_fixture_fallback',true,
      'failed_wash_with_charge_supported',true
    ),
    'ready_batches',v_ready,'deliveries',v_deliveries,
    'qc_queue',v_qc_queue,'qc_history',v_qc_history,
    'legacy_unlinked',jsonb_build_object(
      'delivery_count',(select count(*) from erp.laundry_deliveries d
        where not exists(select 1 from erp.laundry_delivery_lines dl
          join erp.laundry_delivery_batch_size_lines x on x.delivery_line_id=dl.id
          where dl.delivery_id=d.id)),
      'receipt_count',(select count(*) from erp.laundry_receipts r
        where not exists(select 1 from erp.laundry_receipt_lines rl
          join erp.laundry_receipt_batch_size_lines x on x.receipt_line_id=rl.id
          where rl.receipt_id=r.id)
          and not exists(select 1 from erp.laundry_failed_wash_attempts a
            where a.receipt_id=r.id))
    )
  );
end
$function$;

alter function erp.get_laundry_qc_workspace_v1(text,text) owner to postgres;
revoke all on function erp.get_laundry_qc_workspace_v1(text,text)
  from public,anon,authenticated,service_role;

create function erp.save_laundry_qc_action_v1(
  p_action text,p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_action text:=upper(nullif(btrim(p_action),''));
  v_reason text:=nullif(btrim(p_payload->>'reason'),'');
  v_custody_outcome text:=upper(nullif(btrim(p_payload->>'custody_outcome'),''));
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_actor uuid:=erp.current_app_user_id();
  v_physical_raw text:=nullif(btrim(p_payload->>'physical_at'),'');
  v_physical_at timestamptz;
  v_batch_id uuid:=nullif(p_payload->>'distribution_batch_id','')::uuid;
  v_group_id uuid:=nullif(p_payload->>'cutting_group_id','')::uuid;
  v_delivery_id uuid:=nullif(p_payload->>'delivery_id','')::uuid;
  v_receipt_id uuid;
  v_failed_wash_attempt_id uuid;
  v_return_wip_event_id uuid;
  v_qc_id uuid:=nullif(p_payload->>'qc_inspection_id','')::uuid;
  v_vendor_id uuid:=nullif(p_payload->>'vendor_id','')::uuid;
  v_process_id uuid:=nullif(p_payload->>'wash_process_id','')::uuid;
  v_location_id uuid:=nullif(p_payload->>'destination_location_id','')::uuid;
  v_target_color text:=nullif(btrim(p_payload->>'target_dyeing_color'),'');
  v_lines jsonb:=p_payload->'lines';
  v_line jsonb;
  v_rate numeric(18,2);
  v_rate_count integer;
  v_group_count integer;
  v_total bigint;
  v_good bigint;
  v_bs bigint;
  v_available bigint;
  v_available_at_physical_time bigint;
  v_ready_after_qc bigint;
  v_delivery_line_id uuid;
  v_receipt_line_id uuid;
  v_number text;
  v_nested jsonb;
  v_group erp.cutting_groups%rowtype;
  v_po erp.production_orders%rowtype;
  v_delivery erp.laundry_deliveries%rowtype;
  v_receipt erp.laundry_receipts%rowtype;
  v_qc erp.qc_inspections%rowtype;
begin
  if p_client_request_id is null then raise exception 'client_request_id UUID is required'; end if;
  if v_actor is null then raise exception 'Active ERP app user is required'; end if;
  if v_action not in(
    'POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','REVERSE_DELIVERY',
    'REVERSE_RECEIPT','POST_FINAL_SKU','REVERSE_FINAL_SKU'
  ) then raise exception 'Unsupported CP6 Laundry/QC action %',coalesce(v_action,'NULL'); end if;

  -- Physical time is operator intent. Validate it before the generic closed-payload
  -- gate so missing, timezone-less, and calendar-invalid values all fail with one
  -- actionable domain message instead of a helper or native cast error.
  if v_action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','POST_FINAL_SKU') then
    if jsonb_typeof(p_payload->'physical_at') is distinct from 'string'
       or v_physical_raw is null
       or v_physical_raw !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}(:\d{2})?)$' then
      raise exception 'An explicit timezone-qualified physical_at is required; server time is never a transactional default';
    end if;
    begin
      v_physical_at:=v_physical_raw::timestamptz;
    exception
      when data_exception then
        raise exception 'An explicit timezone-qualified physical_at is required; server time is never a transactional default';
    end;
  end if;

  -- Do not let JSON coercion reinterpret a physical count or silently ignore
  -- a misspelled field.  Every connected writer uses one closed, canonical
  -- payload shape before idempotency or business mutation begins.
  if v_action='POST_DELIVERY' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['distribution_batch_id','vendor_id','wash_process_id','target_dyeing_color',
        'physical_at','reason','lines'],
      array['distribution_batch_id','vendor_id','wash_process_id','target_dyeing_color',
        'physical_at','reason','notes','lines'],
      'CP6 POST_DELIVERY payload'
    );
    if jsonb_typeof(p_payload->'distribution_batch_id')<>'string'
       or jsonb_typeof(p_payload->'vendor_id')<>'string'
       or jsonb_typeof(p_payload->'wash_process_id')<>'string'
       or jsonb_typeof(p_payload->'target_dyeing_color')<>'string'
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array'
       or(p_payload ? 'notes' and jsonb_typeof(p_payload->'notes') not in('string','null')) then
      raise exception 'CP6 POST_DELIVERY payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,array['size_id','qty_sent_pcs'],array['size_id','qty_sent_pcs'],
        'CP6 POST_DELIVERY line'
      );
      if jsonb_typeof(v_line->'size_id')<>'string'
         or jsonb_typeof(v_line->'qty_sent_pcs')<>'number'
         or(v_line->>'qty_sent_pcs')!~'^(0|[1-9][0-9]*)$' then
        raise exception 'CP6 POST_DELIVERY line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_RECEIPT' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['delivery_id','wash_process_id','physical_at','reason','lines'],
      array['delivery_id','wash_process_id','physical_at','reason','lines'],
      'CP6 POST_RECEIPT payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or jsonb_typeof(p_payload->'wash_process_id')<>'string'
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_RECEIPT payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,
        array['delivery_batch_size_line_id','qty_good_received','qty_bs_laundry'],
        array['delivery_batch_size_line_id','qty_good_received','qty_bs_laundry','bs_product_id'],
        'CP6 POST_RECEIPT line'
      );
      if not(v_line ? 'bs_product_id')
         or jsonb_typeof(v_line->'delivery_batch_size_line_id')<>'string'
         or jsonb_typeof(v_line->'qty_good_received')<>'number'
         or(v_line->>'qty_good_received')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'qty_bs_laundry')<>'number'
         or(v_line->>'qty_bs_laundry')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'bs_product_id') not in('string','null') then
        raise exception 'CP6 POST_RECEIPT line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_FAILED_WASH' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines'],
      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines'],
      'CP6 POST_FAILED_WASH payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or jsonb_typeof(p_payload->'wash_process_id')<>'string'
       or jsonb_typeof(p_payload->'custody_outcome')<>'string'
       or v_custody_outcome not in('RETRY_AT_VENDOR','RETURN_UNPROCESSED')
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_FAILED_WASH payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,array['delivery_batch_size_line_id','qty_attempted_pcs'],
        array['delivery_batch_size_line_id','qty_attempted_pcs'],
        'CP6 POST_FAILED_WASH line'
      );
      if jsonb_typeof(v_line->'delivery_batch_size_line_id')<>'string'
         or jsonb_typeof(v_line->'qty_attempted_pcs')<>'number'
         or(v_line->>'qty_attempted_pcs')!~'^[1-9][0-9]*$' then
        raise exception 'CP6 POST_FAILED_WASH line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_FINAL_SKU' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['cutting_group_id','destination_location_id','physical_at','reason',
        'good_qty_pcs','completion_mode','lines'],
      array['cutting_group_id','destination_location_id','physical_at','reason',
        'good_qty_pcs','completion_mode','lines'],
      'CP6 POST_FINAL_SKU payload'
    );
    if jsonb_typeof(p_payload->'cutting_group_id')<>'string'
       or jsonb_typeof(p_payload->'destination_location_id')<>'string'
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'good_qty_pcs')<>'number'
       or(p_payload->>'good_qty_pcs')!~'^(0|[1-9][0-9]*)$'
       or jsonb_typeof(p_payload->'completion_mode')<>'string'
       or(p_payload->>'completion_mode') not in('ALL_READY','PARTIAL_SELECTION')
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_FINAL_SKU payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,
        array['final_product_id','qty_good_pcs','qty_bs_pcs',
          'source_laundry_receipt_line_id','source_laundry_receipt_batch_size_line_id'],
        array['final_product_id','qty_good_pcs','qty_bs_pcs',
          'source_laundry_receipt_line_id','source_laundry_receipt_batch_size_line_id','notes'],
        'CP6 POST_FINAL_SKU line'
      );
      if jsonb_typeof(v_line->'final_product_id')<>'string'
         or jsonb_typeof(v_line->'qty_good_pcs')<>'number'
         or(v_line->>'qty_good_pcs')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'qty_bs_pcs')<>'number'
         or(v_line->>'qty_bs_pcs')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'source_laundry_receipt_line_id')<>'string'
         or jsonb_typeof(v_line->'source_laundry_receipt_batch_size_line_id')<>'string'
         or(v_line ? 'notes' and jsonb_typeof(v_line->'notes') not in('string','null')) then
        raise exception 'CP6 POST_FINAL_SKU line has invalid field types';
      end if;
    end loop;
  elsif v_action='REVERSE_DELIVERY' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['delivery_id','reason'],array['delivery_id','reason'],
      'CP6 REVERSE_DELIVERY payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_DELIVERY payload has invalid field types';
    end if;
  elsif v_action='REVERSE_RECEIPT' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['receipt_id','reason'],array['receipt_id','reason'],
      'CP6 REVERSE_RECEIPT payload'
    );
    if jsonb_typeof(p_payload->'receipt_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_RECEIPT payload has invalid field types';
    end if;
  else
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['qc_inspection_id','reason'],array['qc_inspection_id','reason'],
      'CP6 REVERSE_FINAL_SKU payload'
    );
    if jsonb_typeof(p_payload->'qc_inspection_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_FINAL_SKU payload has invalid field types';
    end if;
  end if;
  if v_reason is null or length(v_reason)<4 then raise exception 'A clear reason of at least 4 characters is required'; end if;
  if v_physical_at>clock_timestamp()+interval '5 minutes' then
    raise exception 'Physical time cannot be more than five minutes in the future';
  end if;

  if v_action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH') then
    perform erp.require_permission('production.laundry.post');
    if v_action='POST_DELIVERY' then perform erp.require_permission('production.laundry.create'); end if;
  elsif v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT') then
    perform erp.require_permission('production.laundry.reverse');
  elsif v_action='POST_FINAL_SKU' then
    perform erp.require_permission('production.final_sku.post');
  else
    perform erp.require_permission('production.final_sku.reverse');
  end if;

  v_hash:=erp._request_hash(jsonb_build_object(
    'action',v_action,'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin(
    'cp6_laundry_qc_action_v1:'||lower(v_action),p_client_request_id,v_hash
  );
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_action='POST_DELIVERY' then
    if p_expected_version is null then raise exception 'Potongan expected_version is required'; end if;
    if v_batch_id is null or v_vendor_id is null or v_process_id is null
       or v_target_color is null then
      raise exception 'Distribution batch, vendor, wash process, and target color are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Laundry delivery requires positive size lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      where x.size_id is null or coalesce(x.qty_sent_pcs,0)<=0
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      group by x.size_id having count(*)>1
    ) then raise exception 'Laundry delivery size lines must be unique and positive'; end if;

    -- Resolve the immutable Potongan key without retaining a row lock, then
    -- take the shared CP6 fence before every business row.  The locked re-read
    -- below rejects a source that changed while this transaction waited; it
    -- must never continue under a fence for the wrong Potongan.
    select p.cutting_group_id into v_group_id
    from erp.cutting_distribution_batches b
    join erp.cutting_pickups p on p.id=b.pickup_id and p.status='POSTED'
    where b.id=v_batch_id;
    if v_group_id is null then raise exception 'Authoritative POSTED distribution batch was not found'; end if;
    -- Every CP6 mutation that can change Laundry/QC progress shares this
    -- transaction fence.  Cross-document actions on one Potongan therefore
    -- have one serial order even when their individual row locks do not meet.
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    perform 1
    from erp.cutting_distribution_batches b
    join erp.cutting_pickups p on p.id=b.pickup_id
    where b.id=v_batch_id and p.status='POSTED'
      and p.cutting_group_id=v_group_id
    for update of b,p;
    if not found then
      raise exception 'Authoritative POSTED distribution batch changed while waiting for the Potongan fence; refetch before retrying';
    end if;
    select * into v_group from erp.cutting_groups where id=v_group_id for update;
    if v_group.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_group.row_version;
    end if;
    select * into v_po from erp.production_orders where id=v_group.po_id for update;
    if v_po.status in('FINISHED','CANCELLED') then
      raise exception 'PO status % cannot receive a new Laundry delivery',v_po.status;
    end if;
    if v_physical_at<v_group.picked_up_at then
      raise exception 'Laundry send time cannot be earlier than the physical contractor pickup';
    end if;
    perform 1 from erp.laundry_vendors v
    where v.id=v_vendor_id and v.is_active for share;
    if not found then
      raise exception 'An active authoritative Laundry vendor is required';
    end if;
    perform 1 from erp.wash_processes w
    where w.id=v_process_id and w.is_active for share;
    if not found then
      raise exception 'An active authoritative wash process is required';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('LRATE:'||v_vendor_id::text||':'||v_process_id::text,0));
    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at);
    if v_rate_count<>1 then
      raise exception 'Exactly one authoritative Laundry rate must be effective for this vendor/process/time; found %',v_rate_count;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at)
    order by r.id for share;

    if exists(
      select 1
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      left join lateral(
        select coalesce(sum(a.qty_pcs),0)::bigint qty
        from erp.cutting_distribution_allocations a
        join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
        join erp.cutting_group_size_slots s on s.id=y.size_slot_id
        where a.batch_id=v_batch_id and s.size_id=x.size_id
      ) cap on true
      left join lateral(
        select coalesce(sum(sx.qty_sent_pcs),0)::bigint qty
        from erp.laundry_delivery_batch_size_lines sx
        join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
        join erp.laundry_deliveries d on d.id=dl.delivery_id
        where sx.distribution_batch_id=v_batch_id and sx.size_id=x.size_id
          and d.status not in('DRAFT','REVERSED')
      ) used on true
      where x.qty_sent_pcs>cap.qty-used.qty
    ) then raise exception 'Requested Laundry size quantity exceeds its remaining distribution-batch capacity'; end if;
    select sum(x.qty_sent_pcs)::bigint into v_total
    from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
    select coalesce(w.unsent_ready_qty_pcs,0)::bigint into v_available
    from erp.v_wip_control_status_v1 w where w.cutting_group_id=v_group.id;
    if v_total>coalesce(v_available,0) then
      raise exception 'Laundry send exceeds sewn-and-unsent capacity. Ready %, requested %',coalesce(v_available,0),v_total;
    end if;
    select greatest(
      coalesce((
        select sum(e.qty_signed) from erp.sewing_terminal_events e
        where e.cutting_group_id=v_group.id and e.physical_at<=v_physical_at
      ),0)
      -coalesce((
        select sum(dl.qty_sent_pcs)
        from erp.laundry_delivery_lines dl
        join erp.laundry_deliveries d on d.id=dl.delivery_id
        where dl.cutting_group_id=v_group.id
          and d.status not in('DRAFT','REVERSED') and d.physical_at<=v_physical_at
      ),0)
      -coalesce((
        select sum(i.qty_good_pcs+i.qty_bs_pcs)
        from erp.qc_inspection_items i
        join erp.qc_inspections q on q.id=i.inspection_id
        where i.cutting_group_id=v_group.id
          and i.source_laundry_receipt_line_id is null
          and q.status='POSTED' and q.physical_at<=v_physical_at
      ),0),0
    )::bigint into v_available_at_physical_time;
    if v_total>v_available_at_physical_time then
      raise exception 'Laundry send time predates sufficient authoritative sewing output. Ready at physical time %, requested %',
        v_available_at_physical_time,v_total;
    end if;

    v_delivery_id:=gen_random_uuid();
    v_delivery_line_id:=gen_random_uuid();
    -- The UUID is already the immutable document identity. Keep all 128 bits
    -- in the unique human key so two valid postings can never be rejected by
    -- the former 40-bit display prefix collision surface.
    v_number:='LDR-'||to_char(v_physical_at,'YYMMDD')||'-'
      ||upper(replace(v_delivery_id::text,'-',''));
    insert into erp.laundry_deliveries(
      id,delivery_number,po_id,vendor_id,target_dyeing_color,target_wash_process_id,
      special_instruction,physical_at,status,created_by
    ) values(
      v_delivery_id,v_number,v_group.po_id,v_vendor_id,v_target_color,v_process_id,
      nullif(btrim(p_payload->>'notes'),''),v_physical_at,'DRAFT',v_actor
    );
    insert into erp.laundry_delivery_lines(
      id,delivery_id,cutting_group_id,qty_sent_pcs,estimated_rate_snapshot,
      estimated_cost_status,notes
    ) values(
      v_delivery_line_id,v_delivery_id,v_group.id,v_total,v_rate,'ESTIMATED',
      'CP6 immutable distribution batch/size handoff: '||v_reason
    );
    insert into erp.laundry_delivery_batch_size_lines(
      delivery_line_id,distribution_batch_id,size_id,qty_sent_pcs,created_by
    ) select v_delivery_line_id,v_batch_id,x.size_id,x.qty_sent_pcs,v_actor
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    perform erp.post_laundry_delivery(v_delivery_id);
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id;
    select * into v_group from erp.cutting_groups where id=v_group.id;
    v_response:=jsonb_build_object(
      'action',v_action,'delivery_id',v_delivery.id,'delivery_number',v_delivery.delivery_number,
      'status',v_delivery.status,'row_version',v_delivery.row_version,
      'cutting_group_id',v_group.id,'cutting_group_row_version',v_group.row_version,
      'qty_sent_pcs',v_total,'rate_per_pcs',v_rate,
      'estimated_cost',round(v_total*v_rate,2),
      'stock_effect','SEWING_TO_LAUNDRY','hpp_effect','LAUNDRY_ACCRUAL_REBUILT'
    );

  elsif v_action='POST_RECEIPT' then
    if p_expected_version is null or v_delivery_id is null then
      raise exception 'Delivery and expected_version are required';
    end if;
    if v_process_id is null then raise exception 'Actual wash process is required'; end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Laundry receipt requires positive batch/size return lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) where x.delivery_batch_size_line_id is null
        or coalesce(x.qty_good_received,0)<0 or coalesce(x.qty_bs_laundry,0)<0
        or coalesce(x.qty_good_received,0)+coalesce(x.qty_bs_laundry,0)<=0
        or(coalesce(x.qty_bs_laundry,0)>0 and x.bs_product_id is null)
        or(coalesce(x.qty_bs_laundry,0)=0 and x.bs_product_id is not null)
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) group by x.delivery_batch_size_line_id having count(*)>1
    ) then raise exception 'Receipt size lines must be unique, positive, and bind every Laundry BS to a product'; end if;

    select min(dl.cutting_group_id::text)::uuid,count(*)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 receipt requires one authoritative delivery line';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id for update;
    if v_delivery.id is null or v_delivery.status not in('SENT','PARTIAL_RETURN') then
      raise exception 'Laundry receipt requires an active SENT/PARTIAL_RETURN delivery';
    end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    if v_physical_at<v_delivery.physical_at then
      raise exception 'Laundry return time cannot be earlier than the send time';
    end if;
    if exists(select 1 from erp.laundry_claims c where c.delivery_id=v_delivery.id
      and c.claim_type in('STUCK','MISSING') and c.status<>'REJECTED') then
      raise exception 'Reverse/reject the active STUCK/MISSING claim before posting a late physical return';
    end if;
    perform 1 from erp.wash_processes w
    where w.id=v_process_id and w.is_active for share;
    if not found then
      raise exception 'An active authoritative actual wash process is required';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('LRATE:'||v_delivery.vendor_id::text||':'||v_process_id::text,0));
    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at);
    if v_rate_count<>1 then
      raise exception 'Exactly one authoritative actual Laundry rate must be effective for this vendor/process/time; found %',v_rate_count;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at)
    order by r.id for share;
    select min(dl.id::text)::uuid into v_delivery_line_id
    from erp.laundry_delivery_lines dl
    where dl.delivery_id=v_delivery.id and dl.cutting_group_id=v_group_id;
    if v_delivery_line_id is null or(
      select count(*) from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id
    )<>1 then raise exception 'Connected CP6 receipt requires one authoritative delivery line'; end if;
    perform 1
    from erp.laundry_delivery_batch_size_lines sx
    join jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_good_received integer,
      qty_bs_laundry integer,bs_product_id uuid
    ) on x.delivery_batch_size_line_id=sx.id
    order by sx.id for update of sx;
    if(
      select count(*) from erp.laundry_delivery_batch_size_lines sx
      join jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) on x.delivery_batch_size_line_id=sx.id
      where sx.delivery_line_id=v_delivery_line_id
    )<>jsonb_array_length(v_lines) then
      raise exception 'A receipt source does not belong to this CP6 delivery';
    end if;
    if exists(
      select 1
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      )
      join erp.laundry_delivery_batch_size_lines sx on sx.id=x.delivery_batch_size_line_id
      where coalesce(x.qty_good_received,0)+coalesce(x.qty_bs_laundry,0)>
        sx.qty_sent_pcs-coalesce((
          select sum(rx.qty_good_received+rx.qty_bs_laundry)
          from erp.laundry_receipt_batch_size_lines rx
          join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
          join erp.laundry_receipts rh on rh.id=rl.receipt_id
          where rx.delivery_batch_size_line_id=sx.id and rh.status='POSTED'
        ),0)
    ) then raise exception 'Laundry receipt exceeds remaining quantity for an exact batch/size source'; end if;

    select sum(coalesce(x.qty_good_received,0))::bigint,
           sum(coalesce(x.qty_bs_laundry,0))::bigint
      into v_good,v_bs
    from jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_good_received integer,
      qty_bs_laundry integer,bs_product_id uuid
    );
    v_total:=v_good+v_bs;
    v_receipt_id:=gen_random_uuid();
    v_receipt_line_id:=gen_random_uuid();
    v_number:='LRC-'||to_char(v_physical_at,'YYMMDD')||'-'
      ||upper(replace(v_receipt_id::text,'-',''));
    insert into erp.laundry_receipts(
      id,receipt_number,delivery_id,physical_at,status,created_by
    ) values(v_receipt_id,v_number,v_delivery.id,v_physical_at,'DRAFT',v_actor);
    insert into erp.laundry_receipt_lines(
      id,receipt_id,delivery_line_id,actual_wash_process_id,
      qty_good_received,qty_bs_laundry,qty_stuck,qty_missing,
      actual_rate_snapshot,actual_cost_status,actual_cost,notes
    ) values(
      v_receipt_line_id,v_receipt_id,v_delivery_line_id,v_process_id,
      -- A physical receipt proves the process/rate snapshot, not the vendor
      -- invoice.  Keep the amount ESTIMATED so the delivery accrual remains a
      -- liability until post_vendor_invoice atomically replaces it with AP.
      -- Marking this FINAL here would release accrual early and leave negative
      -- WIP after the same cost moves into FG/HPP.
      v_good,v_bs,0,0,v_rate,'ESTIMATED',round(v_total*v_rate,2),
      'CP6 immutable physical batch/size return: '||v_reason
    );
    insert into erp.laundry_receipt_batch_size_lines(
      receipt_line_id,delivery_batch_size_line_id,size_id,
      qty_good_received,qty_bs_laundry,bs_product_id,created_by
    ) select v_receipt_line_id,x.delivery_batch_size_line_id,sx.size_id,
        coalesce(x.qty_good_received,0),coalesce(x.qty_bs_laundry,0),x.bs_product_id,v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) join erp.laundry_delivery_batch_size_lines sx on sx.id=x.delivery_batch_size_line_id;
    insert into erp.laundry_receipt_bs_product_allocations(
      receipt_line_id,product_id,qty_bs,notes,created_by
    ) select v_receipt_line_id,x.bs_product_id,sum(x.qty_bs_laundry)::integer,
        'CP6 immutable Laundry-BS product/size declaration',v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) where x.qty_bs_laundry>0 group by x.bs_product_id;
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    perform erp.post_laundry_receipt(v_receipt_id);
    -- The predecessor function records every physical return as LAUNDRY → QC.
    -- Laundry BS is terminal at this boundary, so append the balancing
    -- QC → ON_HOLD event instead of rewriting/deleting the predecessor event.
    insert into erp.wip_stage_events(
      po_id,cutting_group_id,stage_from,stage_to,qty_pcs,
      source_type,source_id,physical_at,created_by,notes
    )
    select v_delivery.po_id,dl.cutting_group_id,'QC','ON_HOLD',x.qty_bs_laundry,
      'CP6_LAUNDRY_BS_SIZE_LINE',x.id,v_physical_at,v_actor,
      'Laundry BS is terminal and must never become QC-ready'
    from erp.laundry_receipt_batch_size_lines x
    join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
    join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
    where x.receipt_line_id=v_receipt_line_id and x.qty_bs_laundry>0;
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'receipt_id',v_receipt.id,'receipt_number',v_receipt.receipt_number,
      'receipt_status',v_receipt.status,'receipt_row_version',v_receipt.row_version,
      'delivery_id',v_delivery.id,'delivery_status',v_delivery.status,
      'delivery_row_version',v_delivery.row_version,'good_qty_pcs',v_good,'bs_qty_pcs',v_bs,
      'rate_per_pcs',v_rate,'actual_cost',round(v_total*v_rate,2),
      'cost_status','ESTIMATED_UNBILLED','accrual_effect','PRESERVED_UNTIL_VENDOR_INVOICE',
      'stock_effect','LAUNDRY_GOOD_TO_QC_AND_BS_TO_ON_HOLD',
      'hpp_effect','ACTUAL_LAUNDRY_COST_REBUILT'
    );

  elsif v_action='POST_FAILED_WASH' then
    if p_expected_version is null or v_delivery_id is null or v_process_id is null then
      raise exception 'Delivery, failed process, and expected_version are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Paid failed wash requires positive attempted batch/size lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) where x.delivery_batch_size_line_id is null or coalesce(x.qty_attempted_pcs,0)<=0
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) group by x.delivery_batch_size_line_id having count(*)>1
    ) then
      raise exception 'Failed-wash size lines must be unique positive integer pieces';
    end if;

    select min(dl.cutting_group_id::text)::uuid,count(*)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected failed-wash action requires one authoritative delivery line';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries
    where id=v_delivery_id for update;
    if v_delivery.id is null or v_delivery.status not in('SENT','PARTIAL_RETURN') then
      raise exception 'Paid failed wash requires an active SENT/PARTIAL_RETURN delivery';
    end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    if v_physical_at<v_delivery.physical_at
       or exists(select 1 from erp.laundry_receipts r
         where r.delivery_id=v_delivery.id and r.status='POSTED'
           and r.physical_at>v_physical_at) then
      raise exception 'Failed-wash physical time cannot precede the send or later posted Laundry history';
    end if;
    if exists(select 1 from erp.laundry_claims c
      where c.delivery_id=v_delivery.id and c.status<>'REJECTED') then
      raise exception 'Resolve/reject active Laundry claims before recording a failed-wash service attempt';
    end if;
    perform 1 from erp.wash_processes w
    where w.id=v_process_id and w.is_active for share;
    if not found then raise exception 'An active authoritative failed wash process is required'; end if;
    perform pg_advisory_xact_lock(hashtextextended(
      'LRATE:'||v_delivery.vendor_id::text||':'||v_process_id::text,0
    ));
    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at);
    if v_rate_count<>1 then
      raise exception 'Exactly one authoritative failed-wash rate must be effective for this vendor/process/time; found %',v_rate_count;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at)
    order by r.id for share;
    select min(dl.id::text)::uuid into v_delivery_line_id
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id;
    perform 1
    from erp.laundry_delivery_batch_size_lines s
    join jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_attempted_pcs integer
    ) on x.delivery_batch_size_line_id=s.id
    order by s.id for update of s;
    if (select count(*)
        from erp.laundry_delivery_batch_size_lines s
        join jsonb_to_recordset(v_lines) x(
          delivery_batch_size_line_id uuid,qty_attempted_pcs integer
        ) on x.delivery_batch_size_line_id=s.id
        where s.delivery_line_id=v_delivery_line_id)<>jsonb_array_length(v_lines)
       or exists(
         select 1
         from jsonb_to_recordset(v_lines) x(
           delivery_batch_size_line_id uuid,qty_attempted_pcs integer
         )
         join erp.laundry_delivery_batch_size_lines s
           on s.id=x.delivery_batch_size_line_id
         where x.qty_attempted_pcs>s.qty_sent_pcs-coalesce((
           select sum(rx.qty_good_received+rx.qty_bs_laundry)
           from erp.laundry_receipt_batch_size_lines rx
           join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
           join erp.laundry_receipts rh on rh.id=rl.receipt_id
           where rx.delivery_batch_size_line_id=s.id and rh.status='POSTED'
         ),0)
       ) then
      raise exception 'Failed-wash attempted quantity exceeds the exact pieces still in Laundry custody';
    end if;
    select sum(x.qty_attempted_pcs)::bigint into v_total
    from jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_attempted_pcs integer
    );
    if v_custody_outcome='RETURN_UNPROCESSED' and(
      v_delivery.status<>'SENT'
      or exists(
        select 1 from erp.laundry_receipt_lines rl
        join erp.laundry_receipts rh on rh.id=rl.receipt_id
        left join erp.laundry_failed_wash_attempts a on a.receipt_line_id=rl.id
        where rh.delivery_id=v_delivery.id and rh.status='POSTED'
          and a.id is null and rl.qty_good_received+rl.qty_bs_laundry>0
      )
      or jsonb_array_length(v_lines)<>(
        select count(*) from erp.laundry_delivery_batch_size_lines s
        where s.delivery_line_id=v_delivery_line_id
      )
      or exists(
        select 1 from erp.laundry_delivery_batch_size_lines s
        left join jsonb_to_recordset(v_lines) x(
          delivery_batch_size_line_id uuid,qty_attempted_pcs integer
        ) on x.delivery_batch_size_line_id=s.id
        where s.delivery_line_id=v_delivery_line_id
          and x.qty_attempted_pcs is distinct from s.qty_sent_pcs
      )
    ) then
      raise exception 'Return-unprocessed is deliberately all-or-nothing: every exact sent size must return before redispatch';
    end if;

    v_receipt_id:=gen_random_uuid();
    v_receipt_line_id:=gen_random_uuid();
    v_failed_wash_attempt_id:=gen_random_uuid();
    v_number:='LFW-'||to_char(v_physical_at,'YYMMDD')||'-'
      ||upper(replace(v_receipt_id::text,'-',''));
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    insert into erp.laundry_receipts(
      id,receipt_number,delivery_id,physical_at,status,created_by
    ) values(v_receipt_id,v_number,v_delivery.id,v_physical_at,'DRAFT',v_actor);
    insert into erp.laundry_receipt_lines(
      id,receipt_id,delivery_line_id,actual_wash_process_id,
      qty_good_received,qty_bs_laundry,qty_stuck,qty_missing,
      actual_rate_snapshot,actual_cost_status,actual_cost,notes
    ) values(
      v_receipt_line_id,v_receipt_id,v_delivery_line_id,v_process_id,
      0,0,0,0,v_rate,'ESTIMATED',round(v_total*v_rate,2),
      'CP6 paid failed-wash service only; no physical Good/BS receipt: '||v_reason
    );
    insert into erp.laundry_failed_wash_attempts(
      id,receipt_id,receipt_line_id,delivery_id,custody_outcome,
      qty_attempted_pcs,reason,created_by
    ) values(
      v_failed_wash_attempt_id,v_receipt_id,v_receipt_line_id,v_delivery.id,
      v_custody_outcome,v_total,v_reason,v_actor
    );
    insert into erp.laundry_failed_wash_batch_size_lines(
      attempt_id,delivery_batch_size_line_id,size_id,qty_attempted_pcs,created_by
    ) select v_failed_wash_attempt_id,x.delivery_batch_size_line_id,s.size_id,
        x.qty_attempted_pcs,v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) join erp.laundry_delivery_batch_size_lines s
        on s.id=x.delivery_batch_size_line_id;

    if v_custody_outcome='RETURN_UNPROCESSED' then
      perform set_config('app.physical_at',v_physical_at::text,true);
      update erp.laundry_deliveries
      set status='REVERSED',updated_at=clock_timestamp()
      where id=v_delivery.id;
      select min(rv.id::text)::uuid,count(*)::integer
        into v_return_wip_event_id,v_group_count
      from erp.wip_stage_events rv
      join erp.wip_stage_events src
        on src.id=rv.source_id and src.source_type='LAUNDRY_DELIVERY_LINE'
      join erp.laundry_delivery_lines dl
        on dl.id=src.source_id and dl.delivery_id=v_delivery.id
      where rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL';
      if v_group_count<>1 or v_return_wip_event_id is null then
        raise exception 'Return-unprocessed did not create exactly one linked physical WIP inverse';
      end if;
      update erp.laundry_failed_wash_attempts
      set return_wip_event_id=v_return_wip_event_id
      where id=v_failed_wash_attempt_id;
    else
      update erp.laundry_deliveries set updated_at=clock_timestamp()
      where id=v_delivery.id;
    end if;

    update erp.laundry_receipts
    set status='POSTED',updated_at=clock_timestamp()
    where id=v_receipt_id;

    if v_custody_outcome='RETURN_UNPROCESSED' then
      update erp.cutting_groups g
      set status=case
        when exists(
          select 1 from erp.laundry_receipt_lines rl
          join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
          join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
          join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
          where dl.cutting_group_id=g.id and rl.qty_good_received+rl.qty_bs_laundry>0
        ) then 'RETURNED'
        when exists(
          select 1 from erp.laundry_delivery_lines dl
          join erp.laundry_deliveries d on d.id=dl.delivery_id
          where dl.cutting_group_id=g.id and d.status not in('DRAFT','REVERSED')
        ) then 'LAUNDRY'
        when g.picked_up_at is not null then 'PICKED_UP' else 'CUT' end
      where g.id=v_group_id;
      select * into v_po from erp.production_orders where id=v_delivery.po_id for update;
      if v_po.status not in('ON_HOLD','CANCELLED') then
        update erp.production_orders po set
          status=case
            when exists(select 1 from erp.qc_inspections q
              where q.po_id=po.id and q.status='POSTED') then 'QC'
            when exists(select 1 from erp.laundry_deliveries d
              where d.po_id=po.id and d.status not in('DRAFT','REVERSED')) then 'LAUNDRY'
            when exists(select 1 from erp.cutting_groups g
              where g.po_id=po.id and g.picked_up_at is not null) then 'SEWING'
            else 'CUTTING' end,
          current_stage=case
            when exists(select 1 from erp.qc_inspections q
              where q.po_id=po.id and q.status='POSTED') then 'QC'
            when exists(select 1 from erp.laundry_deliveries d
              where d.po_id=po.id and d.status not in('DRAFT','REVERSED')) then 'LAUNDRY'
            when exists(select 1 from erp.cutting_groups g
              where g.po_id=po.id and g.picked_up_at is not null) then 'SEWING'
            else 'CUTTING' end,
          updated_at=clock_timestamp()
        where po.id=v_po.id;
      end if;
    end if;

    perform erp.sync_laundry_accrual(v_delivery.po_id,v_physical_at::date);
    if exists(select 1 from erp.fg_lots f where f.po_id=v_delivery.po_id) then
      perform erp.rebuild_po_hpp(
        v_delivery.po_id,'Paid failed-wash service attempt '||v_failed_wash_attempt_id::text
      );
      perform erp.propagate_conversion_hpp_for_po(v_delivery.po_id);
      perform erp.sync_po_hpp_to_gl(v_delivery.po_id,v_physical_at::date);
    end if;
    insert into erp.audit_logs(
      entity_type,entity_id,action,new_data,changed_by,change_reason
    ) values(
      'laundry_failed_wash_attempts',v_failed_wash_attempt_id,'POST',
      jsonb_build_object(
        'receipt_id',v_receipt_id,'delivery_id',v_delivery.id,
        'custody_outcome',v_custody_outcome,'qty_attempted_pcs',v_total,
        'rate_per_pcs',v_rate,'estimated_cost',round(v_total*v_rate,2),
        'history_deleted',false
      ),v_actor,v_reason
    );
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'failed_wash_attempt_id',v_failed_wash_attempt_id,
      'receipt_id',v_receipt.id,'receipt_number',v_receipt.receipt_number,
      'receipt_status',v_receipt.status,'receipt_row_version',v_receipt.row_version,
      'delivery_id',v_delivery.id,'delivery_status',v_delivery.status,
      'delivery_row_version',v_delivery.row_version,
      'custody_outcome',v_custody_outcome,'qty_attempted_pcs',v_total,
      'rate_per_pcs',v_rate,'actual_cost',round(v_total*v_rate,2),
      'cost_status','ESTIMATED_UNBILLED',
      'stock_effect',case when v_custody_outcome='RETRY_AT_VENDOR'
        then 'PHYSICAL_STAYS_AT_LAUNDRY' else 'LAUNDRY_TO_SEWING_RETURN' end,
      'hpp_effect','FAILED_WASH_COST_REBUILT_WITHOUT_GOOD_BS_OR_FG'
    );

  elsif v_action='REVERSE_DELIVERY' then
    if p_expected_version is null or v_delivery_id is null then
      raise exception 'Delivery and expected_version are required';
    end if;
    select min(dl.cutting_group_id::text)::uuid,count(distinct dl.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 delivery reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id for update;
    if v_delivery.id is null then raise exception 'Laundry delivery not found'; end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    perform erp.reverse_laundry_delivery(v_delivery.id,v_reason);
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'delivery_id',v_delivery.id,'status',v_delivery.status,
      'row_version',v_delivery.row_version,'history_deleted',false,
      'stock_effect','LAUNDRY_TO_SEWING_REVERSED','hpp_effect','LAUNDRY_ACCRUAL_REBUILT'
    );

  elsif v_action='REVERSE_RECEIPT' then
    if p_expected_version is null or nullif(p_payload->>'receipt_id','') is null then
      raise exception 'Receipt and expected_version are required';
    end if;
    v_receipt_id:=(p_payload->>'receipt_id')::uuid;
    select min(dl.cutting_group_id::text)::uuid,count(distinct dl.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.laundry_receipt_lines rl
    join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
    where rl.receipt_id=v_receipt_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 receipt reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id for update;
    if v_receipt.id is null then raise exception 'Laundry receipt not found'; end if;
    if v_receipt.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_receipt.row_version;
    end if;
    select a.id,a.custody_outcome into v_failed_wash_attempt_id,v_custody_outcome
    from erp.laundry_failed_wash_attempts a where a.receipt_id=v_receipt.id
    for update;
    if v_failed_wash_attempt_id is null then
      perform erp.reverse_laundry_receipt(v_receipt.id,v_reason);
      select * into v_receipt from erp.laundry_receipts where id=v_receipt.id;
      v_response:=jsonb_build_object(
        'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
        'row_version',v_receipt.row_version,'history_deleted',false,
        'stock_effect','LAUNDRY_RETURN_REVERSED','hpp_effect','LAUNDRY_AND_FG_HPP_REBUILT'
      );
    else
      if v_receipt.status='REVERSED' then
        v_response:=jsonb_build_object(
          'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
          'row_version',v_receipt.row_version,'history_deleted',false,
          'stock_effect','NO_OP_ALREADY_REVERSED',
          'hpp_effect','NO_OP_ALREADY_REVERSED'
        );
      else
        if v_receipt.status<>'POSTED' then
          raise exception 'Only a POSTED failed-wash service attempt can be reversed';
        end if;
        select * into v_delivery from erp.laundry_deliveries
        where id=v_receipt.delivery_id for update;
        select * into v_po from erp.production_orders
        where id=v_delivery.po_id for update;
        if v_po.status='FINISHED' then
          raise exception 'PO sudah FINISHED. Reopen downstream before reversing failed-wash cost history.';
        end if;
        if exists(
          select 1 from erp.vendor_invoice_items i
          join erp.vendor_invoices h on h.id=i.invoice_id
          where i.receipt_line_id in(
            select l.id from erp.laundry_receipt_lines l where l.receipt_id=v_receipt.id
          ) and h.status<>'REVERSED'
        ) then
          raise exception 'Penerimaan laundry ini sudah masuk invoice vendor. Reverse invoice vendor aktif terlebih dahulu.';
        end if;
        if exists(
          select 1 from erp.qc_inspection_items i
          join erp.qc_inspections h on h.id=i.inspection_id
          where i.source_laundry_receipt_line_id in(
            select l.id from erp.laundry_receipt_lines l where l.receipt_id=v_receipt.id
          ) and h.status<>'REVERSED'
        ) or exists(
          select 1 from erp.laundry_receipt_batch_size_lines x
          join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
          where l.receipt_id=v_receipt.id
        ) then
          raise exception 'Failed-wash service-only receipt unexpectedly owns physical/QC facts; reversal stopped for investigation';
        end if;
        update erp.laundry_receipts
        set status='REVERSED',updated_at=clock_timestamp()
        where id=v_receipt.id;
        -- A RETURN_UNPROCESSED custody fact remains immutable. Reversing the
        -- vendor charge never resurrects the old dispatch; a later physical
        -- handoff is a new delivery with its own time, rate, and lineage.
        update erp.laundry_deliveries set updated_at=clock_timestamp()
        where id=v_delivery.id;
        perform erp.sync_laundry_accrual(v_delivery.po_id,current_date);
        if exists(select 1 from erp.fg_lots f where f.po_id=v_delivery.po_id) then
          perform erp.rebuild_po_hpp(
            v_delivery.po_id,'Failed-wash service cost reversed '||v_failed_wash_attempt_id::text
          );
          perform erp.propagate_conversion_hpp_for_po(v_delivery.po_id);
          perform erp.sync_po_hpp_to_gl(v_delivery.po_id,current_date);
        end if;
        insert into erp.audit_logs(
          entity_type,entity_id,action,new_data,changed_by,change_reason
        ) values(
          'laundry_failed_wash_attempts',v_failed_wash_attempt_id,'REVERSE',
          jsonb_build_object(
            'receipt_id',v_receipt.id,'custody_outcome',v_custody_outcome,
            'physical_return_preserved',v_custody_outcome='RETURN_UNPROCESSED',
            'history_deleted',false
          ),v_actor,v_reason
        );
        select * into v_receipt from erp.laundry_receipts where id=v_receipt.id;
        select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
        v_response:=jsonb_build_object(
          'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
          'row_version',v_receipt.row_version,'delivery_id',v_delivery.id,
          'delivery_status',v_delivery.status,'delivery_row_version',v_delivery.row_version,
          'history_deleted',false,'custody_outcome',v_custody_outcome,
          'stock_effect',case when v_custody_outcome='RETURN_UNPROCESSED'
            then 'PHYSICAL_RETURN_PRESERVED' else 'PHYSICAL_STAYS_AT_LAUNDRY' end,
          'hpp_effect','FAILED_WASH_COST_REVERSED_AND_REPORTS_REBUILT'
        );
      end if;
    end if;

  elsif v_action='POST_FINAL_SKU' then
    if p_expected_version is null or v_group_id is null or v_location_id is null then
      raise exception 'Potongan, destination FG location, and expected_version are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Final SKU posting requires at least one allocation line';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      ) where x.final_product_id is null
        or coalesce(x.qty_good_pcs,0)<0 or coalesce(x.qty_bs_pcs,0)<0
        or coalesce(x.qty_good_pcs,0)+coalesce(x.qty_bs_pcs,0)<=0
        or x.source_laundry_receipt_line_id is null
        or x.source_laundry_receipt_batch_size_line_id is null
    ) then raise exception 'Every connected Final SKU line needs positive quantity and exact receipt/batch/size lineage'; end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      ) group by x.final_product_id,x.source_laundry_receipt_line_id
      having count(*)>1
    ) then raise exception 'Duplicate Final SKU/source lines are not allowed'; end if;

    perform 1 from erp.locations l
    where l.id=v_location_id and l.is_active and l.location_type='FG_WAREHOUSE'
    for share;
    if not found then raise exception 'Destination must be an active FG warehouse'; end if;

    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    -- The shared Potongan fence is acquired before receipt headers. A
    -- concurrent reversal cannot change
    -- POSTED -> REVERSED after a child source was checked but before QC/FG was
    -- committed.  Lock every referenced header deterministically, then
    -- re-check the complete exact-source chain while those locks are held.
    perform 1
    from erp.laundry_receipts r
    where r.id in(
      select distinct rl.receipt_id
      from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      )
      join erp.laundry_receipt_batch_size_lines sx
        on sx.id=x.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl
        on rl.id=sx.receipt_line_id
    )
    order by r.id
    for update;
    if(
      select count(*)
      from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      )
      join erp.laundry_receipt_batch_size_lines sx
        on sx.id=x.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl
        on rl.id=sx.receipt_line_id
       and rl.id=x.source_laundry_receipt_line_id
      join erp.laundry_receipts r on r.id=rl.receipt_id and r.status='POSTED'
      join erp.laundry_delivery_lines dl
        on dl.id=rl.delivery_line_id and dl.cutting_group_id=v_group_id
      join erp.laundry_deliveries d
        on d.id=dl.delivery_id and d.status<>'REVERSED'
      join erp.cutting_groups g
        on g.id=v_group_id and g.po_id=d.po_id
    )<>jsonb_array_length(v_lines) then
      raise exception 'Every Final SKU source must belong to the same Potongan and an authoritative POSTED Laundry receipt';
    end if;
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.final_sku.post',p_client_request_id,p_payload
    );
    v_nested:=erp.post_final_sku_allocation_v1(p_payload,p_client_request_id,p_expected_version);
    -- completion_mode is operational/reporting state, not browser-owned
    -- metadata.  The predecessor persists the declaration before returning
    -- the authoritative post-mutation progress.  Reject a lie in either
    -- direction here; the exception rolls the nested QC, FG, BS, HPP,
    -- journal, row-version, and both idempotency envelopes back atomically.
    v_ready_after_qc:=nullif(v_nested->>'ready_for_qc_qty_pcs','')::bigint;
    if v_ready_after_qc is null then
      raise exception 'CP6 Final-SKU writer did not return authoritative ready-for-QC balance';
    end if;
    if ((p_payload->>'completion_mode')='ALL_READY' and v_ready_after_qc<>0)
       or ((p_payload->>'completion_mode')='PARTIAL_SELECTION' and v_ready_after_qc=0) then
      raise exception
        'CP6 completion_mode % conflicts with authoritative ready-for-QC remainder % after atomic posting',
        p_payload->>'completion_mode',v_ready_after_qc;
    end if;
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    v_qc_id:=nullif(v_nested->>'qc_inspection_id','')::uuid;
    select * into v_qc from erp.qc_inspections where id=v_qc_id;
    v_response:=v_nested||jsonb_build_object(
      'action',v_action,'qc_row_version',v_qc.row_version,
      'stock_effect','FG_GOOD_AND_QC_BS_POSTED',
      'hpp_effect','SERVER_REBUILT_FROM_IMMUTABLE_SNAPSHOTS',
      'browser_formula_used',false
    );

  else
    if p_expected_version is null or v_qc_id is null then
      raise exception 'QC inspection and expected_version are required';
    end if;
    select min(i.cutting_group_id::text)::uuid,count(distinct i.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.qc_inspection_items i where i.inspection_id=v_qc_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 Final-SKU reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_qc from erp.qc_inspections where id=v_qc_id for update;
    if v_qc.id is null then raise exception 'QC inspection not found'; end if;
    if v_qc.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_qc.row_version;
    end if;
    perform erp.reverse_qc(v_qc.id,v_reason);
    select * into v_qc from erp.qc_inspections where id=v_qc.id;
    v_response:=jsonb_build_object(
      'action',v_action,'qc_inspection_id',v_qc.id,'status',v_qc.status,
      'row_version',v_qc.row_version,'history_deleted',false,
      'stock_effect','FG_AND_BS_REVERSED','hpp_effect','HPP_AND_GL_REBUILT'
    );
  end if;

  if exists(
    select 1 from erp.cp6_laundry_qc_execution_context c
    where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
  ) then raise exception 'CP6 execution context leaked after action'; end if;
  v_response:=v_response||jsonb_build_object(
    'contract_version','CP6_V2620',
    'client_request_id',p_client_request_id,
    'committed',true
  );
  return erp._idempotency_complete(
    'cp6_laundry_qc_action_v1:'||lower(v_action),p_client_request_id,v_response
  );
end
$function$;

alter function erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint) owner to postgres;
revoke all on function erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)
  from public,anon,authenticated,service_role;

create function erp.guard_cp6_laundry_delivery_batch_size_v2620()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_row erp.laundry_delivery_batch_size_lines%rowtype;
  v_delivery_status text;
  v_group_id uuid;
  v_batch_group uuid;
  v_pickup_status text;
  v_allocated bigint;
begin
  if tg_op='DELETE' then v_row:=old; else v_row:=new; end if;
  if tg_op='UPDATE' and old.delivery_line_id is distinct from new.delivery_line_id then
    if exists(
      select 1 from erp.laundry_delivery_lines l
      join erp.laundry_deliveries d on d.id=l.delivery_id
      where l.id=old.delivery_line_id and d.status<>'DRAFT'
    ) then
      raise exception using errcode='42501',message='POSTED_LAUNDRY_BATCH_SIZE_LINEAGE_IMMUTABLE';
    end if;
  end if;
  select d.status,dl.cutting_group_id into v_delivery_status,v_group_id
  from erp.laundry_delivery_lines dl
  join erp.laundry_deliveries d on d.id=dl.delivery_id
  where dl.id=v_row.delivery_line_id;
  if v_delivery_status is null then raise exception 'CP6 Laundry delivery parent was not found'; end if;
  if v_delivery_status<>'DRAFT' then
    raise exception using errcode='42501',message='POSTED_LAUNDRY_BATCH_SIZE_LINEAGE_IMMUTABLE';
  end if;
  if tg_op='DELETE' then return old; end if;

  select p.cutting_group_id,p.status into v_batch_group,v_pickup_status
  from erp.cutting_distribution_batches b
  join erp.cutting_pickups p on p.id=b.pickup_id
  where b.id=new.distribution_batch_id;
  if v_batch_group is distinct from v_group_id or v_pickup_status is distinct from 'POSTED' then
    raise exception 'Laundry batch/size source must be a POSTED distribution batch from the same Potongan';
  end if;
  select coalesce(sum(a.qty_pcs),0)::bigint into v_allocated
  from erp.cutting_distribution_allocations a
  join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
  join erp.cutting_group_size_slots s on s.id=y.size_slot_id
  where a.batch_id=new.distribution_batch_id and s.size_id=new.size_id;
  if v_allocated<=0 then
    raise exception 'Selected size has no quantity in the authoritative distribution batch';
  end if;
  return new;
end
$function$;

create function erp.guard_cp6_laundry_receipt_batch_size_v2620()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_row erp.laundry_receipt_batch_size_lines%rowtype;
  v_receipt_status text;
  v_receipt_delivery uuid;
  v_receipt_delivery_line uuid;
  v_source_delivery_line uuid;
  v_source_size uuid;
  v_source_po uuid;
  v_product_size uuid;
  v_product_model uuid;
  v_receipt_physical_at timestamptz;
begin
  if tg_op='DELETE' then v_row:=old; else v_row:=new; end if;
  if tg_op='UPDATE' and old.receipt_line_id is distinct from new.receipt_line_id then
    if exists(
      select 1 from erp.laundry_receipt_lines l
      join erp.laundry_receipts r on r.id=l.receipt_id
      where l.id=old.receipt_line_id and r.status<>'DRAFT'
    ) then
      raise exception using errcode='42501',message='POSTED_LAUNDRY_RECEIPT_BATCH_SIZE_LINEAGE_IMMUTABLE';
    end if;
  end if;
  select r.status,r.delivery_id,rl.delivery_line_id,r.physical_at
    into v_receipt_status,v_receipt_delivery,v_receipt_delivery_line,v_receipt_physical_at
  from erp.laundry_receipt_lines rl
  join erp.laundry_receipts r on r.id=rl.receipt_id
  where rl.id=v_row.receipt_line_id;
  if v_receipt_status is null then raise exception 'CP6 Laundry receipt parent was not found'; end if;
  if v_receipt_status<>'DRAFT' then
    raise exception using errcode='42501',message='POSTED_LAUNDRY_RECEIPT_BATCH_SIZE_LINEAGE_IMMUTABLE';
  end if;
  if tg_op='DELETE' then return old; end if;

  select x.delivery_line_id,x.size_id,d.po_id
    into v_source_delivery_line,v_source_size,v_source_po
  from erp.laundry_delivery_batch_size_lines x
  join erp.laundry_delivery_lines dl on dl.id=x.delivery_line_id
  join erp.laundry_deliveries d on d.id=dl.delivery_id
  where x.id=new.delivery_batch_size_line_id
  for update of d,x;
  if v_source_delivery_line is distinct from v_receipt_delivery_line
     or not exists(
       select 1 from erp.laundry_delivery_lines dl
       where dl.id=v_source_delivery_line and dl.delivery_id=v_receipt_delivery
     ) then
    raise exception 'Laundry receipt batch/size source belongs to a different delivery line';
  end if;
  if new.size_id is distinct from v_source_size then
    raise exception 'Laundry receipt size must equal its immutable delivery size';
  end if;
  if new.qty_bs_laundry>0 then
    select p.size_id,p.model_id into v_product_size,v_product_model
    from erp.products p
    join erp.product_models m on m.id=p.model_id and m.is_active
    join erp.brands b on b.id=p.brand_id and b.is_active
    join erp.sizes s on s.id=p.size_id and s.is_active
    where p.id=new.bs_product_id and p.is_active
      and p.effective_from<=v_receipt_physical_at
      and(p.effective_to is null or p.effective_to>v_receipt_physical_at)
    for share of p,m,b,s;
    if v_product_size is distinct from new.size_id
       or v_product_model is distinct from(
         select po.model_id from erp.production_orders po where po.id=v_source_po
       ) then
      raise exception 'Laundry BS product must be active at physical receipt time and match the source PO model/size';
    end if;
  end if;
  return new;
end
$function$;

-- Failed-wash facts may only be assembled inside the one public facade while
-- their receipt is DRAFT.  Once posted, neither the attempted sizes nor the
-- custody declaration can be edited or deleted.
create function erp.guard_cp6_failed_wash_attempt_v2620()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_row erp.laundry_failed_wash_attempts%rowtype;
  v_receipt_status text;
  v_receipt_delivery uuid;
  v_line_receipt uuid;
  v_line_delivery uuid;
begin
  if not exists(
    select 1 from erp.cp6_laundry_qc_execution_context c
    where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key()
      and c.action='POST_FAILED_WASH'
      and c.permission_key='production.laundry.post'
      and erp.has_permission(c.permission_key)
  ) then
    raise exception using errcode='42501',message='FAILED_WASH_FACTS_REQUIRE_AUTHORITATIVE_FACADE';
  end if;
  if tg_op='DELETE' then v_row:=old; else v_row:=new; end if;
  select r.status,r.delivery_id,rl.receipt_id,dl.delivery_id
    into v_receipt_status,v_receipt_delivery,v_line_receipt,v_line_delivery
  from erp.laundry_receipts r
  join erp.laundry_receipt_lines rl on rl.id=v_row.receipt_line_id
  join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
  where r.id=v_row.receipt_id;
  if v_receipt_status is distinct from 'DRAFT'
     or v_receipt_delivery is distinct from v_row.delivery_id
     or v_line_receipt is distinct from v_row.receipt_id
     or v_line_delivery is distinct from v_row.delivery_id then
    raise exception using errcode='42501',message='POSTED_OR_MISMATCHED_FAILED_WASH_FACT_IMMUTABLE';
  end if;
  if tg_op='DELETE' then
    raise exception using errcode='42501',message='FAILED_WASH_HISTORY_DELETE_FORBIDDEN';
  end if;
  if new.created_by is distinct from erp.current_app_user_id() then
    raise exception 'Failed-wash actor must equal the authenticated ERP app user';
  end if;
  if tg_op='UPDATE' and row(
      new.id,new.receipt_id,new.receipt_line_id,new.delivery_id,new.custody_outcome,
      new.qty_attempted_pcs,new.reason,new.created_by,new.created_at
    ) is distinct from row(
      old.id,old.receipt_id,old.receipt_line_id,old.delivery_id,old.custody_outcome,
      old.qty_attempted_pcs,old.reason,old.created_by,old.created_at
    ) then
    raise exception using errcode='42501',message='FAILED_WASH_FACT_IMMUTABLE';
  end if;
  if new.custody_outcome='RETRY_AT_VENDOR' and new.return_wip_event_id is not null then
    raise exception 'Retry-at-vendor must not manufacture a physical WIP return';
  end if;
  return new;
end
$function$;

create function erp.guard_cp6_failed_wash_size_v2620()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_receipt_status text;
  v_delivery_id uuid;
  v_source_delivery uuid;
  v_source_size uuid;
  v_source_qty integer;
begin
  if tg_op<>'INSERT' then
    raise exception using errcode='42501',message='FAILED_WASH_SIZE_HISTORY_IMMUTABLE';
  end if;
  if not exists(
    select 1 from erp.cp6_laundry_qc_execution_context c
    where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key()
      and c.action='POST_FAILED_WASH'
      and c.permission_key='production.laundry.post'
      and erp.has_permission(c.permission_key)
  ) then
    raise exception using errcode='42501',message='FAILED_WASH_FACTS_REQUIRE_AUTHORITATIVE_FACADE';
  end if;
  select r.status,a.delivery_id into v_receipt_status,v_delivery_id
  from erp.laundry_failed_wash_attempts a
  join erp.laundry_receipts r on r.id=a.receipt_id
  where a.id=new.attempt_id;
  select dl.delivery_id,s.size_id,s.qty_sent_pcs
    into v_source_delivery,v_source_size,v_source_qty
  from erp.laundry_delivery_batch_size_lines s
  join erp.laundry_delivery_lines dl on dl.id=s.delivery_line_id
  where s.id=new.delivery_batch_size_line_id for update of s;
  if v_receipt_status is distinct from 'DRAFT'
     or v_source_delivery is distinct from v_delivery_id
     or v_source_size is distinct from new.size_id
     or new.qty_attempted_pcs>coalesce(v_source_qty,0)
     or new.created_by is distinct from erp.current_app_user_id() then
    raise exception 'Failed-wash size must be a positive exact size from its active delivery';
  end if;
  return new;
end
$function$;

create function erp.guard_cp6_laundry_lineage_on_post_v2620()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare
  r record;
  v_line_count integer;
  v_batch_count integer;
  v_allocated bigint;
  v_prior bigint;
begin
  if not(old.status='DRAFT' and new.status='SENT') then return new; end if;
  if not exists(
    select 1 from erp.laundry_delivery_batch_size_lines x
    join erp.laundry_delivery_lines l on l.id=x.delivery_line_id
    where l.delivery_id=new.id
  ) then
    raise exception 'CP6 posted Laundry delivery requires immutable distribution batch/size lineage';
  end if;

  select count(*) into v_line_count
  from erp.laundry_delivery_lines where delivery_id=new.id;
  if v_line_count<>1 then
    raise exception 'CP6 Laundry delivery must contain exactly one authoritative Potongan line';
  end if;
  select count(distinct x.distribution_batch_id) into v_batch_count
  from erp.laundry_delivery_batch_size_lines x
  join erp.laundry_delivery_lines l on l.id=x.delivery_line_id
  where l.delivery_id=new.id;
  if v_batch_count<>1 then
    raise exception 'CP6 Laundry delivery must contain exactly one authoritative distribution batch';
  end if;
  for r in
    select l.id delivery_line_id,l.qty_sent_pcs,x.distribution_batch_id,x.size_id,
           sum(x.qty_sent_pcs)::bigint child_qty
    from erp.laundry_delivery_lines l
    join erp.laundry_delivery_batch_size_lines x on x.delivery_line_id=l.id
    where l.delivery_id=new.id
    group by l.id,l.qty_sent_pcs,x.distribution_batch_id,x.size_id
    order by x.distribution_batch_id,x.size_id
  loop
    perform 1 from erp.cutting_distribution_batches b
    where b.id=r.distribution_batch_id for update;
    select coalesce(sum(a.qty_pcs),0)::bigint into v_allocated
    from erp.cutting_distribution_allocations a
    join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
    join erp.cutting_group_size_slots s on s.id=y.size_slot_id
    where a.batch_id=r.distribution_batch_id and s.size_id=r.size_id;
    select coalesce(sum(x.qty_sent_pcs),0)::bigint into v_prior
    from erp.laundry_delivery_batch_size_lines x
    join erp.laundry_delivery_lines l on l.id=x.delivery_line_id
    join erp.laundry_deliveries d on d.id=l.delivery_id
    where x.distribution_batch_id=r.distribution_batch_id
      and x.size_id=r.size_id and d.id<>new.id
      and d.status not in('DRAFT','REVERSED');
    if v_prior+r.child_qty>v_allocated then
      raise exception 'Laundry batch/size quantity exceeds distributed capacity. Allocated %, prior active %, this delivery %',
        v_allocated,v_prior,r.child_qty;
    end if;
  end loop;
  if exists(
    select 1 from erp.laundry_delivery_lines l
    left join(
      select delivery_line_id,sum(qty_sent_pcs)::bigint qty
      from erp.laundry_delivery_batch_size_lines group by delivery_line_id
    ) x on x.delivery_line_id=l.id
    where l.delivery_id=new.id and l.qty_sent_pcs is distinct from coalesce(x.qty,0)
  ) then raise exception 'Laundry delivery header/size lineage quantity mismatch'; end if;
  return new;
end
$function$;

create function erp.guard_cp6_laundry_receipt_lineage_on_post_v2620()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare
  r record;
  v_prior bigint;
  v_line_count integer;
begin
  if not(old.status='DRAFT' and new.status='POSTED') then return new; end if;
  if exists(select 1 from erp.laundry_failed_wash_attempts a where a.receipt_id=new.id) then
    select a.* into r
    from erp.laundry_failed_wash_attempts a where a.receipt_id=new.id;
    if (select count(*) from erp.laundry_receipt_lines l where l.receipt_id=new.id)<>1
       or exists(
         select 1 from erp.laundry_receipt_batch_size_lines x
         join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
         where l.receipt_id=new.id
       )
       or exists(
         select 1 from erp.laundry_receipt_lines l
         where l.receipt_id=new.id and(
           l.id<>r.receipt_line_id or l.qty_good_received<>0 or l.qty_bs_laundry<>0
           or l.qty_stuck<>0 or l.qty_missing<>0
           or l.actual_wash_process_id is null
           or l.actual_rate_snapshot is null or l.actual_rate_snapshot<0
           or l.actual_cost_status<>'ESTIMATED'
           or l.actual_cost is distinct from round(r.qty_attempted_pcs*l.actual_rate_snapshot,2)
         )
       )
       or (select coalesce(sum(x.qty_attempted_pcs),0)
           from erp.laundry_failed_wash_batch_size_lines x
           where x.attempt_id=r.id)<>r.qty_attempted_pcs
       or exists(
         select 1
         from erp.laundry_failed_wash_batch_size_lines x
         join erp.laundry_delivery_batch_size_lines s
           on s.id=x.delivery_batch_size_line_id
         join erp.laundry_delivery_lines dl on dl.id=s.delivery_line_id
         where x.attempt_id=r.id and(
           dl.delivery_id<>r.delivery_id or x.size_id<>s.size_id
           or x.qty_attempted_pcs>s.qty_sent_pcs
         )
       ) then
      raise exception 'Failed-wash receipt must contain one zero-output cost line and exact attempted batch/size facts';
    end if;
    if r.custody_outcome='RETRY_AT_VENDOR' then
      if r.return_wip_event_id is not null
         or not exists(select 1 from erp.laundry_deliveries d
           where d.id=r.delivery_id and d.status in('SENT','PARTIAL_RETURN')) then
        raise exception 'Retry-at-vendor must preserve active Laundry custody without a WIP return';
      end if;
    else
      if r.return_wip_event_id is null
         or not exists(
           select 1
           from erp.wip_stage_events rv
           join erp.wip_stage_events src
             on src.id=rv.source_id and src.source_type='LAUNDRY_DELIVERY_LINE'
           join erp.laundry_delivery_lines dl
             on dl.id=src.source_id and dl.delivery_id=r.delivery_id
           join erp.laundry_deliveries d on d.id=dl.delivery_id
           where rv.id=r.return_wip_event_id
             and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
             and rv.po_id=d.po_id and rv.cutting_group_id=dl.cutting_group_id
             and rv.stage_from='LAUNDRY' and rv.stage_to='SEWING'
             and rv.qty_pcs=r.qty_attempted_pcs
             and d.status='REVERSED'
         )
         or (select count(*) from erp.laundry_failed_wash_batch_size_lines x
             where x.attempt_id=r.id)<>
            (select count(*) from erp.laundry_delivery_batch_size_lines s
             join erp.laundry_delivery_lines dl on dl.id=s.delivery_line_id
             where dl.delivery_id=r.delivery_id)
         or exists(
           select 1 from erp.laundry_delivery_batch_size_lines s
           join erp.laundry_delivery_lines dl on dl.id=s.delivery_line_id
           left join erp.laundry_failed_wash_batch_size_lines x
             on x.attempt_id=r.id and x.delivery_batch_size_line_id=s.id
           where dl.delivery_id=r.delivery_id
             and x.qty_attempted_pcs is distinct from s.qty_sent_pcs
         ) then
        raise exception 'Return-unprocessed must return the entire exact delivery and bind one immutable WIP inverse';
      end if;
    end if;
    return new;
  end if;
  if not exists(
    select 1 from erp.laundry_receipt_batch_size_lines x
    join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
    where l.receipt_id=new.id
  ) then
    raise exception 'CP6 posted Laundry receipt requires immutable delivery batch/size lineage';
  end if;
  select count(*) into v_line_count
  from erp.laundry_receipt_lines where receipt_id=new.id;
  if v_line_count<>1 then
    raise exception 'CP6 Laundry receipt must contain exactly one authoritative delivery line';
  end if;
  if exists(
    select 1 from erp.laundry_receipt_lines l
    left join(
      select receipt_line_id,
        sum(qty_good_received)::bigint good_qty,
        sum(qty_bs_laundry)::bigint bs_qty
      from erp.laundry_receipt_batch_size_lines group by receipt_line_id
    ) x on x.receipt_line_id=l.id
    where l.receipt_id=new.id and(
      l.qty_good_received is distinct from coalesce(x.good_qty,0)
      or l.qty_bs_laundry is distinct from coalesce(x.bs_qty,0)
      or l.qty_stuck<>0 or l.qty_missing<>0
    )
  ) then
    raise exception 'CP6 receipt aggregate must equal immutable size facts; Stuck is derived from outstanding, never posted repeatedly';
  end if;
  for r in
    select x.delivery_batch_size_line_id,
      sum(x.qty_good_received+x.qty_bs_laundry)::bigint current_qty,
      max(s.qty_sent_pcs)::bigint sent_qty
    from erp.laundry_receipt_batch_size_lines x
    join erp.laundry_delivery_batch_size_lines s on s.id=x.delivery_batch_size_line_id
    join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
    where l.receipt_id=new.id
    group by x.delivery_batch_size_line_id
    order by x.delivery_batch_size_line_id
  loop
    perform 1 from erp.laundry_delivery_batch_size_lines s
    where s.id=r.delivery_batch_size_line_id for update;
    select coalesce(sum(x.qty_good_received+x.qty_bs_laundry),0)::bigint into v_prior
    from erp.laundry_receipt_batch_size_lines x
    join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
    join erp.laundry_receipts h on h.id=l.receipt_id
    where x.delivery_batch_size_line_id=r.delivery_batch_size_line_id
      and h.id<>new.id and h.status='POSTED';
    if v_prior+r.current_qty>r.sent_qty then
      raise exception 'Laundry physical return exceeds immutable batch/size sent quantity. Sent %, prior %, this receipt %',
        r.sent_qty,v_prior,r.current_qty;
    end if;
  end loop;
  return new;
end
$function$;

-- The legacy invoice lifecycle changes the authoritative cost on receipt lines
-- before it posts/reverses AP and rebuilds HPP.  It historically did not retain
-- a lock on the receipt header.  Serialize both DRAFT -> POSTED and
-- POSTED -> REVERSED against receipt reversal and Final-SKU, then re-check the
-- source while the lock is held.  An exception here rolls back the entire
-- invoice transaction, including receipt-cost, journal, HPP, and AP changes.
create function erp.guard_cp6_vendor_invoice_receipt_on_post_v2620()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
begin
  if not(
    (old.status='DRAFT' and new.status='POSTED')
    or (old.status='POSTED' and new.status='REVERSED')
  ) then return new; end if;
  if not exists(
    select 1 from erp.vendor_invoice_items i where i.invoice_id=new.id
  ) then
    raise exception 'Vendor invoice cannot be posted without Laundry receipt items';
  end if;
  if exists(
    select 1 from erp.vendor_invoice_items i
    where i.invoice_id=new.id group by i.receipt_line_id having count(*)<>1
  ) then
    raise exception 'One Laundry receipt line may appear only once in one vendor invoice';
  end if;

  perform 1
  from erp.laundry_receipts r
  where r.id in(
    select distinct rl.receipt_id
    from erp.vendor_invoice_items i
    join erp.laundry_receipt_lines rl on rl.id=i.receipt_line_id
    where i.invoice_id=new.id
  )
  order by r.id
  for update;

  if exists(
    select 1
    from erp.vendor_invoice_items i
    join erp.laundry_receipt_lines rl on rl.id=i.receipt_line_id
    join erp.laundry_receipts r on r.id=rl.receipt_id
    where i.invoice_id=new.id and r.status<>'POSTED'
  ) then
    raise exception 'Vendor invoice lifecycle lost its authoritative POSTED Laundry receipt; retry only after reconciliation';
  end if;
  if exists(
    select 1
    from erp.vendor_invoice_items i
    join erp.laundry_receipt_lines rl on rl.id=i.receipt_line_id
    left join erp.laundry_failed_wash_attempts a on a.receipt_line_id=rl.id
    where i.invoice_id=new.id and(
      i.qty_pcs is null or i.qty_pcs<=0
      or i.actual_rate is null or i.actual_rate<0
      or i.actual_amount is distinct from round(i.qty_pcs*i.actual_rate,2)
      or i.qty_pcs is distinct from coalesce(a.qty_attempted_pcs,
        rl.qty_good_received+rl.qty_bs_laundry)
    )
  ) then
    raise exception 'Vendor invoice Laundry quantity/rate/amount must equal the authoritative physical receipt or failed-wash attempt';
  end if;
  return new;
end
$function$;

create trigger trg_guard_cp6_delivery_batch_size_v2620
before insert or update or delete on erp.laundry_delivery_batch_size_lines
for each row execute function erp.guard_cp6_laundry_delivery_batch_size_v2620();
create trigger trg_guard_cp6_receipt_batch_size_v2620
before insert or update or delete on erp.laundry_receipt_batch_size_lines
for each row execute function erp.guard_cp6_laundry_receipt_batch_size_v2620();
create trigger trg_guard_cp6_failed_wash_attempt_v2620
before insert or update or delete on erp.laundry_failed_wash_attempts
for each row execute function erp.guard_cp6_failed_wash_attempt_v2620();
create trigger trg_guard_cp6_failed_wash_size_v2620
before insert or update or delete on erp.laundry_failed_wash_batch_size_lines
for each row execute function erp.guard_cp6_failed_wash_size_v2620();
create trigger trg_audit_cp6_delivery_batch_size_v2620
after insert or update or delete on erp.laundry_delivery_batch_size_lines
for each row execute function erp.audit_row_change();
create trigger trg_audit_cp6_receipt_batch_size_v2620
after insert or update or delete on erp.laundry_receipt_batch_size_lines
for each row execute function erp.audit_row_change();
create trigger trg_audit_cp6_failed_wash_attempt_v2620
after insert or update or delete on erp.laundry_failed_wash_attempts
for each row execute function erp.audit_row_change();
create trigger trg_audit_cp6_failed_wash_size_v2620
after insert or update or delete on erp.laundry_failed_wash_batch_size_lines
for each row execute function erp.audit_row_change();
create trigger trg_guard_cp6_delivery_lineage_on_post_v2620
before update of status on erp.laundry_deliveries
for each row execute function erp.guard_cp6_laundry_lineage_on_post_v2620();
create trigger trg_guard_cp6_receipt_lineage_on_post_v2620
before update of status on erp.laundry_receipts
for each row execute function erp.guard_cp6_laundry_receipt_lineage_on_post_v2620();
create trigger trg_guard_cp6_vendor_invoice_receipt_on_post_v2620
before update of status on erp.vendor_invoices
for each row execute function erp.guard_cp6_vendor_invoice_receipt_on_post_v2620();

alter function erp.guard_cp6_laundry_delivery_batch_size_v2620() owner to postgres;
alter function erp.guard_cp6_laundry_receipt_batch_size_v2620() owner to postgres;
alter function erp.guard_cp6_failed_wash_attempt_v2620() owner to postgres;
alter function erp.guard_cp6_failed_wash_size_v2620() owner to postgres;
alter function erp.guard_cp6_laundry_lineage_on_post_v2620() owner to postgres;
alter function erp.guard_cp6_laundry_receipt_lineage_on_post_v2620() owner to postgres;
alter function erp.guard_cp6_vendor_invoice_receipt_on_post_v2620() owner to postgres;
revoke all on function
  erp.guard_cp6_laundry_delivery_batch_size_v2620(),
  erp.guard_cp6_laundry_receipt_batch_size_v2620(),
  erp.guard_cp6_failed_wash_attempt_v2620(),
  erp.guard_cp6_failed_wash_size_v2620(),
  erp.guard_cp6_laundry_lineage_on_post_v2620(),
  erp.guard_cp6_laundry_receipt_lineage_on_post_v2620(),
  erp.guard_cp6_vendor_invoice_receipt_on_post_v2620()
from public,anon,authenticated,service_role;

create function public.erp_get_laundry_qc_workspace_v1(
  p_scope text default 'LAUNDRY',p_query text default null
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
begin
  return erp.get_laundry_qc_workspace_v1(p_scope,p_query);
end
$function$;

create function public.erp_save_laundry_qc_action_v1(
  p_action text,p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
begin
  return erp.save_laundry_qc_action_v1(
    p_action,p_payload,p_client_request_id,p_expected_version
  );
end
$function$;

-- Preserve the established public signature while routing it through the new
-- context, UUID idempotency envelope, and exact receipt batch/size guard.
create or replace function public.erp_post_final_sku_allocation_v1(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
begin
  return erp.save_laundry_qc_action_v1(
    'POST_FINAL_SKU',p_payload,p_client_request_id,p_expected_version
  );
end
$function$;

alter function public.erp_get_laundry_qc_workspace_v1(text,text) owner to postgres;
alter function public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint) owner to postgres;
alter function public.erp_post_final_sku_allocation_v1(jsonb,uuid,bigint) owner to postgres;
revoke all on function
  public.erp_get_laundry_qc_workspace_v1(text,text),
  public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint),
  public.erp_post_final_sku_allocation_v1(jsonb,uuid,bigint)
from public,anon,authenticated,service_role;
grant execute on function
  public.erp_get_laundry_qc_workspace_v1(text,text),
  public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint),
  public.erp_post_final_sku_allocation_v1(jsonb,uuid,bigint)
to authenticated,service_role;

comment on table erp.laundry_delivery_batch_size_lines is
  'CP6 immutable physical lineage from posted contractor distribution batch/size into a Laundry delivery.';
comment on table erp.laundry_receipt_batch_size_lines is
  'CP6 immutable physical return by delivery batch/size. Only Good is QC capacity; Laundry BS is terminal and product-bound.';
comment on table erp.laundry_failed_wash_attempts is
  'CP6 immutable paid failed-wash service fact. It records cost and custody outcome without manufacturing Good, BS, QC, or FG.';
comment on table erp.laundry_failed_wash_batch_size_lines is
  'CP6 immutable exact batch-size quantity charged for one failed-wash attempt.';
comment on function public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint) is
  'CP6 authoritative atomic writer. UUID idempotency, row versions, source conservation, reversal-only correction, and server-owned finance/stock/HPP effects.';

update erp.cp6_v2620_rollback_capsule c
set installed_definition_sha256=case
  when c.object_kind='FUNCTION' then encode(extensions.digest(convert_to(
    pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
  ),'sha256'),'hex')
  else encode(extensions.digest(convert_to(
    pg_get_viewdef(to_regclass(c.object_regidentity),true),'UTF8'
  ),'sha256'),'hex')
end;

do $post_guard$
declare
  v_public record;
  v_fg_progress_def text;
begin
  if (select count(*) from erp.cp6_v2620_rollback_capsule)<>11
     or (select count(*) from erp.cp6_v2620_acl_capsule)<>13
     or exists(
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
     ) then raise exception 'ERP v2.6.20 post guard: rollback capsule drift'; end if;

  if not exists(select 1 from information_schema.columns
      where table_schema='erp' and table_name='laundry_deliveries'
        and column_name='row_version' and is_nullable='NO')
     or not exists(select 1 from information_schema.columns
      where table_schema='erp' and table_name='qc_inspections'
        and column_name='row_version' and is_nullable='NO')
     or not exists(select 1 from information_schema.columns
      where table_schema='erp' and table_name='qc_inspection_items'
        and column_name='source_laundry_receipt_batch_size_line_id') then
    raise exception 'ERP v2.6.20 post guard: version or exact-source column missing';
  end if;
  if exists(
    select 1 from(
      values
        ('erp.laundry_delivery_batch_size_lines'::regclass),
        ('erp.laundry_receipt_batch_size_lines'::regclass),
        ('erp.laundry_failed_wash_attempts'::regclass),
        ('erp.laundry_failed_wash_batch_size_lines'::regclass),
        ('erp.cp6_laundry_qc_execution_context'::regclass),
        ('erp.cp6_v2620_rollback_capsule'::regclass),
        ('erp.cp6_v2620_acl_capsule'::regclass)
    ) x(rel)
    where not coalesce((select c.relrowsecurity from pg_class c where c.oid=x.rel),false)
      or has_table_privilege('anon',x.rel,'SELECT,INSERT,UPDATE,DELETE')
      or has_table_privilege('authenticated',x.rel,'SELECT,INSERT,UPDATE,DELETE')
      or has_table_privilege('service_role',x.rel,'SELECT,INSERT,UPDATE,DELETE')
  ) then raise exception 'ERP v2.6.20 post guard: private table RLS/ACL failed'; end if;
  if to_regclass('erp.idx_products_brand_sku_effective_v2620') is null
     or pg_get_functiondef('erp.validate_product_identity_period()'::regprocedure)
       not like '%BRANDSKU:%new.brand_id%'
     or pg_get_functiondef('erp.validate_product_identity_period()'::regprocedure)
       not like '%SKUROOT:%new.identity_root_id%'
     or pg_get_functiondef('erp.validate_product_identity_period()'::regprocedure)
       not like '%Satu versi SKU tidak boleh memiliki lebih dari satu successor%'
     or pg_get_functiondef('erp.validate_product_identity_period()'::regprocedure)
       not like '%Identitas dan periode SKU immutable setelah row dibuat%'
     or replace(pg_get_functiondef(
       'erp.validate_product_identity_period()'::regprocedure),' ','')
       not like '%p.brand_id=new.brand_id%p.size_id=new.size_id%'
     or pg_get_functiondef('erp.validate_product_identity_period()'::regprocedure)
       not like '%Varian size untuk merek + nomor SKU yang sama%'
     or replace(pg_get_functiondef(
       'erp.run_v259_integrity_checks()'::regprocedure),' ','')
       not like '%PRODUCT_IDENTITY_BRAND_SKU_VARIANT_MISMATCH%'
     or pg_get_functiondef('erp.run_v259_integrity_checks()'::regprocedure)
       not like '%PRODUCT_SUCCESSOR_BRANCH%'
     or replace(pg_get_functiondef(
       'erp.apply_migration_master_rows(uuid)'::regprocedure),' ','')
       not like '%p.brand_id=v_brand%p.size_id=v_size%' then
    raise exception 'ERP v2.6.20 post guard: Brand + SKU + exact-size identity boundary failed';
  end if;
  if exists(
    select 1 from(
      values
        ('erp.laundry_deliveries'::regclass),
        ('erp.laundry_delivery_lines'::regclass),
        ('erp.qc_inspections'::regclass),
        ('erp.qc_inspection_items'::regclass)
    ) x(rel)
    where has_table_privilege('authenticated',x.rel,'INSERT')
       or has_table_privilege('authenticated',x.rel,'UPDATE')
       or has_table_privilege('authenticated',x.rel,'DELETE')
  ) or exists(
    select 1 from(
      values
        ('erp.apply_cutting_correction_and_post_laundry(uuid,uuid,text,text,text,jsonb,timestamp with time zone)'),
        ('erp.post_laundry_delivery(uuid)'),
        ('erp.post_laundry_receipt_v2(uuid,uuid,bigint,text)'),
        ('erp.save_laundry_receipt_draft_v2(jsonb,uuid,bigint)'),
        ('erp.reverse_laundry_delivery(uuid,text)'),
        ('erp.reverse_laundry_receipt(uuid,text)'),
        ('erp.post_qc(uuid)'),
        ('erp.reverse_qc(uuid,text)'),
        ('erp.post_fg_partial_completion_v2(jsonb,uuid,bigint)')
    ) x(sig)
    where has_function_privilege('authenticated',x.sig,'EXECUTE')
  ) then
    raise exception 'ERP v2.6.20 post guard: predecessor browser writer side door remains open';
  end if;
  if to_regclass('erp.uq_cp6_wip_reversal_source_v2620') is null
     or not exists(
       select 1
       from pg_trigger t join pg_class c on c.oid=t.tgrelid
       join pg_namespace n on n.oid=c.relnamespace
       where not t.tgisinternal
         and t.tgname='trg_append_cp6_laundry_wip_reversal_v2620'
         and n.nspname='erp' and c.relname='laundry_receipts'
     )
     or not exists(
       select 1
       from pg_trigger t join pg_class c on c.oid=t.tgrelid
       join pg_namespace n on n.oid=c.relnamespace
       where not t.tgisinternal
         and t.tgname='trg_append_cp6_laundry_wip_reversal_v2620'
         and n.nspname='erp' and c.relname='laundry_deliveries'
     )
     or has_function_privilege(
       'authenticated','erp.append_cp6_laundry_wip_reversal_v2620()','EXECUTE'
     ) then
    raise exception 'ERP v2.6.20 post guard: append-only WIP reversal boundary failed';
  end if;
  if to_regclass('erp.idx_failed_wash_source_size_v2620') is null
     or not exists(select 1 from pg_trigger
       where tgrelid='erp.laundry_failed_wash_attempts'::regclass
         and tgname='trg_guard_cp6_failed_wash_attempt_v2620'
         and tgenabled<>'D' and not tgisinternal)
     or not exists(select 1 from pg_trigger
       where tgrelid='erp.laundry_failed_wash_batch_size_lines'::regclass
         and tgname='trg_guard_cp6_failed_wash_size_v2620'
         and tgenabled<>'D' and not tgisinternal)
     or has_function_privilege(
       'authenticated','erp.guard_cp6_failed_wash_attempt_v2620()','EXECUTE'
     ) or has_function_privilege(
       'authenticated','erp.guard_cp6_failed_wash_size_v2620()','EXECUTE'
     ) then
    raise exception 'ERP v2.6.20 post guard: immutable paid failed-wash boundary failed';
  end if;
  if not exists(
       select 1 from pg_trigger t
       where t.tgrelid='erp.vendor_invoices'::regclass
         and t.tgname='trg_guard_cp6_vendor_invoice_receipt_on_post_v2620'
         and t.tgenabled<>'D' and not t.tgisinternal
     ) or replace(pg_get_functiondef(
       'erp.guard_cp6_vendor_invoice_receipt_on_post_v2620()'::regprocedure),' ','')
         not like '%orderbyr.id%forupdate%r.status<>''POSTED''%'
     or replace(pg_get_functiondef(
       'erp.guard_cp6_vendor_invoice_receipt_on_post_v2620()'::regprocedure),' ','')
         not like '%old.status=''POSTED''andnew.status=''REVERSED''%'
     or has_function_privilege(
       'authenticated','erp.guard_cp6_vendor_invoice_receipt_on_post_v2620()','EXECUTE'
     ) then
    raise exception 'ERP v2.6.20 post guard: vendor-invoice/receipt/Final-SKU serialization failed';
  end if;
  if has_function_privilege('anon','public.erp_get_laundry_qc_workspace_v1(text,text)','EXECUTE')
     or has_function_privilege('anon','public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_get_laundry_qc_workspace_v1(text,text)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.get_laundry_qc_workspace_v1(text,text)','EXECUTE')
     or has_function_privilege('authenticated','erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('anon','erp.desired_laundry_accrual(uuid)','EXECUTE')
     or has_function_privilege('authenticated','erp.desired_laundry_accrual(uuid)','EXECUTE')
     or has_function_privilege('service_role','erp.desired_laundry_accrual(uuid)','EXECUTE') then
    raise exception 'ERP v2.6.20 post guard: facade/private ACL boundary failed';
  end if;
  if replace(pg_get_functiondef(
       'erp.sync_laundry_accrual(uuid,date)'::regprocedure),' ','')
       not like '%pg_advisory_xact_lock(hashtextextended(''PO_HPP:''||p_po_id::text,0))%fromerp.laundry_cost_accrual_state%forupdate%' then
    raise exception 'ERP v2.6.20 post guard: first-row Laundry accrual serialization is absent';
  end if;
  for v_public in
    select p.oid::regprocedure sig,p.prosecdef,p.proowner,p.proconfig
    from pg_proc p where p.oid in(
      'public.erp_get_laundry_qc_workspace_v1(text,text)'::regprocedure,
      'public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure,
      'public.erp_post_final_sku_allocation_v1(jsonb,uuid,bigint)'::regprocedure
    )
  loop
    if not v_public.prosecdef or pg_get_userbyid(v_public.proowner)<>'postgres'
       or not coalesce(v_public.proconfig,array[]::text[])@>array['search_path=""']::text[] then
      raise exception 'ERP v2.6.20 post guard: insecure public facade %',v_public.sig;
    end if;
  end loop;
  v_fg_progress_def:=lower(regexp_replace(
    pg_get_viewdef('erp.v_fg_partial_completion_progress'::regclass,true),
    '[[:space:]]+','','g'
  ));
  if pg_get_functiondef('erp.require_internal()'::regprocedure)
       not like '%cp6_laundry_qc_execution_context%'
     or pg_get_functiondef('erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure)
       not like '%browser_formula_used%false%'
     or md5(pg_get_functiondef(
       'erp.post_fg_partial_completion_v2_legacy_v2610(jsonb,uuid,bigint)'::regprocedure
       )) is distinct from '38d2795520b05cd70fd7bee2c69d3afa'
     or v_fg_progress_def !~
       'coalesce\(lr\.laundry_good_returned_qty_pcs,[^)]*\)-coalesce\(q\.laundry_qc_accounted_qty_pcs,[^)]*\)'
     or v_fg_progress_def ~
       'coalesce\(lr\.laundry_returned_qty_pcs,[^)]*\)-coalesce\(q\.laundry_qc_accounted_qty_pcs,[^)]*\)' then
    raise exception 'ERP v2.6.20 post guard: internal bridge or no-double-QC contract failed';
  end if;
  if pg_get_viewdef('erp.v_wip_control_status_v1'::regclass,true)
       not like '%active_issue_qty_pcs%resolved_issue_qty_pcs%'
     or lower(pg_get_viewdef('erp.v_wip_control_status_v1'::regclass,true))
       not like '%greatest(coalesce(rr.laundry_stuck_qty_pcs%'
     or pg_get_viewdef('erp.v_fg_partial_completion_progress'::regclass,true)
       not like '%resolved_claim_qty_pcs%' then
    raise exception 'ERP v2.6.20 post guard: claim/WIP/terminal-loss reconciliation is absent';
  end if;
  if exists(
    select 1 from erp.laundry_delivery_batch_size_lines x
    join erp.laundry_delivery_lines l on l.id=x.delivery_line_id
    join erp.laundry_deliveries d on d.id=l.delivery_id
    where d.status<>'DRAFT'
    group by l.id,l.qty_sent_pcs
    having count(distinct x.distribution_batch_id)<>1
      or sum(x.qty_sent_pcs)<>l.qty_sent_pcs
  ) or exists(
    select 1 from erp.laundry_receipt_batch_size_lines x
    join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
    join erp.laundry_receipts r on r.id=l.receipt_id
    where r.status='POSTED'
    group by l.id,l.qty_good_received,l.qty_bs_laundry
    having sum(x.qty_good_received)<>l.qty_good_received
      or sum(x.qty_bs_laundry)<>l.qty_bs_laundry
  ) or exists(
    select 1
    from erp.laundry_failed_wash_attempts a
    join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
    join erp.laundry_receipts rh on rh.id=a.receipt_id
    join erp.laundry_deliveries d on d.id=a.delivery_id
    left join lateral(
      select count(*) line_count,coalesce(sum(x.qty_attempted_pcs),0)::bigint qty_attempted_pcs
      from erp.laundry_failed_wash_batch_size_lines x where x.attempt_id=a.id
    ) sx on true
    where rh.status='POSTED' and(
      rl.receipt_id<>a.receipt_id or rh.delivery_id<>a.delivery_id
      or line_count=0 or sx.qty_attempted_pcs<>a.qty_attempted_pcs
      or rl.qty_good_received+rl.qty_bs_laundry+rl.qty_stuck+rl.qty_missing<>0
      or rl.actual_cost is distinct from round(a.qty_attempted_pcs*rl.actual_rate_snapshot,2)
      or (a.custody_outcome='RETRY_AT_VENDOR' and a.return_wip_event_id is not null)
      or (a.custody_outcome='RETURN_UNPROCESSED' and(
        d.status<>'REVERSED' or a.return_wip_event_id is null
      ))
    )
  ) then raise exception 'ERP v2.6.20 post guard: aggregate/lineage mismatch exists'; end if;
  if not exists(select 1 from pg_trigger where tgrelid='erp.laundry_deliveries'::regclass
      and tgname='trg_00_bump_row_version_v2620' and tgenabled<>'D' and not tgisinternal)
     or not exists(select 1 from pg_trigger where tgrelid='erp.qc_inspections'::regclass
      and tgname='trg_00_bump_row_version_v2620' and tgenabled<>'D' and not tgisinternal)
     or not exists(select 1 from pg_trigger where tgrelid='erp.qc_inspection_items'::regclass
      and tgname='trg_01_guard_cp6_qc_batch_size_source_v2620' and tgenabled<>'D' and not tgisinternal) then
    raise exception 'ERP v2.6.20 post guard: lifecycle trigger missing';
  end if;
  if replace(pg_get_functiondef(
       'erp.guard_cp6_laundry_lineage_on_post_v2620()'::regprocedure),' ','')
       not like '%count(distinctx.distribution_batch_id)%v_batch_count<>1%'
     or replace(pg_get_functiondef(
       'erp.guard_cp6_laundry_receipt_batch_size_v2620()'::regprocedure),' ','')
       not like '%forshareofp,m,b,s%'
     or replace(pg_get_functiondef(
       'erp.guard_cp6_qc_batch_size_source_v2620()'::regprocedure),' ','')
       not like '%forshareofp,m,b,s%' then
    raise exception 'ERP v2.6.20 post guard: one-batch lineage or product serialization is absent';
  end if;
end
$post_guard$;

insert into erp.schema_migrations(version,description)
values(
  'v2.6.20',
  'CP6 authoritative Laundry/QC/Final-SKU bridge: immutable distribution batch-size lineage, atomic writers, exact Good-to-QC conservation, reversal-only correction, and server-owned finance/stock/HPP effects'
);

select pg_notify('pgrst','reload schema');
commit;
