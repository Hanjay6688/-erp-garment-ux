-- ERP Garment v2.6.16 / CP4 R1
-- Persistent attendance-HPP route integration and least-privilege Data API boundary.
--
-- This migration intentionally:
--   * requires the exact reviewed CP3 R5 lifecycle through v2.6.14d;
--   * adds ACTIVE attendance allocations to the existing lot-HPP calculation;
--   * recalculates HPP and GL inside the owning pool activation/cancellation transaction;
--   * exposes only owner/admin lifecycle wrappers to authenticated/service_role;
--   * keeps CP3 tables, inner functions, journal reversal primitives, and erp schema private;
--   * stores exact pre-CP4 function bytes for a fail-closed rollback.

begin;
set local lock_timeout='10s';
set local statement_timeout='120s';

do $guard$
declare
  v_rebuild_md5 text;
  v_owner_guard_md5 text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.14d') then
    raise exception 'ERP v2.6.16 requires the independently reviewed v2.6.14d candidate first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.16') then
    raise exception 'ERP v2.6.16 is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regprocedure('erp.rebuild_po_hpp(uuid,text)') is null
     or to_regprocedure('erp.propagate_conversion_hpp_for_po(uuid)') is null
     or to_regprocedure('erp.sync_po_hpp_to_gl(uuid,date)') is null
     or to_regprocedure('erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)') is null
     or to_regprocedure('erp.cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint)') is null
     or to_regprocedure('erp.require_owner_admin()') is null
     or to_regclass('erp.attendance_hpp_pools') is null
     or to_regclass('erp.attendance_hpp_pool_allocations') is null
     or to_regclass('public.v_erp_my_profile') is null then
    raise exception 'ERP v2.6.16 target guard: exact CP3/current-main contract is missing';
  end if;
  if to_regclass('erp.cp4_v2616_rollback_capsule') is not null
     or to_regclass('erp.v_attendance_hpp_active_allocation_by_po_group') is not null then
    raise exception 'ERP v2.6.16 target guard: prior CP4 residue exists';
  end if;
  if exists(
    select 1
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public'
      and p.proname in (
        'erp_set_contractor_hpp_policy_v1',
        'erp_record_sewing_terminal_v1',
        'erp_reverse_sewing_terminal_v1',
        'erp_preview_attendance_hpp_pool_v1',
        'erp_create_attendance_hpp_pool_v1',
        'erp_activate_attendance_hpp_pool_v1',
        'erp_cancel_attendance_hpp_pool_v1'
      )
  ) then
    raise exception 'ERP v2.6.16 target guard: public CP4 RPC name collision';
  end if;

  select md5(pg_get_functiondef('erp.rebuild_po_hpp(uuid,text)'::regprocedure))
  into v_rebuild_md5;
  if v_rebuild_md5 is distinct from 'cfa7eb941c9cb717078b0dd751ceeb86' then
    raise exception 'CONCURRENT_WRITER_DETECTED: rebuild_po_hpp changed after the reviewed UAT fingerprint (observed %)',v_rebuild_md5;
  end if;
  select md5(pg_get_functiondef('erp.require_owner_admin()'::regprocedure))
  into v_owner_guard_md5;
  if v_owner_guard_md5 is distinct from '8c22fb34fb8adf2085ca5703e32d38a5' then
    raise exception 'CONCURRENT_WRITER_DETECTED: require_owner_admin changed after the reviewed UAT fingerprint (observed %)',v_owner_guard_md5;
  end if;
  if has_function_privilege('public','erp.require_owner_admin()','EXECUTE')
     or has_function_privilege('anon','erp.require_owner_admin()','EXECUTE')
     or has_function_privilege('authenticated','erp.require_owner_admin()','EXECUTE')
     or not has_function_privilege('service_role','erp.require_owner_admin()','EXECUTE') then
    raise exception 'CONCURRENT_WRITER_DETECTED: require_owner_admin ACL differs from the reviewed UAT boundary';
  end if;
end
$guard$;

create table erp.cp4_v2616_rollback_capsule(
  function_identity text primary key,
  function_definition text not null,
  definition_sha256 text not null,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
revoke all on table erp.cp4_v2616_rollback_capsule from public, anon, authenticated, service_role;

insert into erp.cp4_v2616_rollback_capsule(
  function_identity,function_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end,
  pg_get_userbyid(p.proowner)
from pg_proc p
join pg_namespace n on n.oid=p.pronamespace
where n.nspname='erp'
  and p.proname in (
    'rebuild_po_hpp',
    'activate_attendance_hpp_pool_v1',
    'cancel_attendance_hpp_pool_v1',
    'require_owner_admin'
  );

do $capsule_guard$
declare v_count integer;v_invalid integer;
begin
  select count(*) into v_count from erp.cp4_v2616_rollback_capsule;
  if v_count<>4 then
    raise exception 'ERP v2.6.16 rollback capsule expected four exact functions, found %',v_count;
  end if;
  select count(*) into v_invalid
  from erp.cp4_v2616_rollback_capsule
  where definition_sha256 is distinct from
        encode(extensions.digest(convert_to(function_definition,'UTF8'),'sha256'),'hex');
  if v_invalid<>0 then
    raise exception 'ERP v2.6.16 rollback capsule digest mismatch';
  end if;
end
$capsule_guard$;

-- The pre-CP4 guard used NULL NOT IN (...), whose result is NULL. PL/pgSQL
-- therefore skipped rejection for inactive or unmapped JWT users. Preserve
-- service-role/internal compatibility, but fail closed for a missing app role.
create or replace function erp.require_owner_admin()
returns void
language plpgsql
stable
security definer
set search_path=''
as $function$
declare v_jwt_role text;
begin
  if session_user in ('postgres','supabase_admin') then return; end if;
  begin
    v_jwt_role:=coalesce(auth.jwt()->>'role','');
  exception when others then
    v_jwt_role:='';
  end;
  if v_jwt_role='service_role' then return; end if;
  if coalesce(erp.current_app_role(),'') not in ('OWNER','ADMIN') then
    raise exception 'OWNER or ADMIN access required';
  end if;
end
$function$;
revoke all on function erp.require_owner_admin() from public, anon, authenticated, service_role;
grant execute on function erp.require_owner_admin() to service_role;

create or replace view erp.v_attendance_hpp_active_allocation_by_po_group
with (security_invoker=true)
as
select
  p.id pool_id,
  p.period_start,
  p.period_end,
  a.po_id,
  a.cutting_group_id,
  sum(a.sewing_qty)::bigint sewing_qty,
  sum(a.allocated_amount)::numeric(20,2) attendance_hpp_amount
from erp.attendance_hpp_pools p
join erp.attendance_hpp_pool_allocations a on a.pool_id=p.id
where p.status='ACTIVE'
group by p.id,p.period_start,p.period_end,a.po_id,a.cutting_group_id;
revoke all on table erp.v_attendance_hpp_active_allocation_by_po_group from public, anon, authenticated, service_role;

create function pg_temp.cp4_replace_function(
  p_proname text,
  p_old text,
  p_new text,
  p_expected_functions integer,
  p_expected_occurrences_per_function integer
)
returns void
language plpgsql
as $function$
declare r record;v_count integer;v_seen integer:=0;v_new_def text;
begin
  for r in
    select p.oid,pg_get_functiondef(p.oid) def
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='erp' and p.proname=p_proname
    order by p.oid
  loop
    v_seen:=v_seen+1;
    v_count:=(length(r.def)-length(replace(r.def,p_old,'')))/nullif(length(p_old),0);
    if v_count<>p_expected_occurrences_per_function then
      raise exception 'CP4 patch % expected % anchor occurrence(s), found %',p_proname,p_expected_occurrences_per_function,v_count;
    end if;
    v_new_def:=replace(r.def,p_old,p_new);
    execute v_new_def;
  end loop;
  if v_seen<>p_expected_functions then
    raise exception 'CP4 patch % expected % overload(s), found %',p_proname,p_expected_functions,v_seen;
  end if;
end
$function$;

-- Add ACTIVE attendance-pool cost as a separate LABOR component. Group-bound
-- cost stays with its immutable sewing lineage; only explicit null-group cost is
-- PO-shared. A group with no FG remains in WIP instead of leaking into another
-- group's HPP.
select pg_temp.cp4_replace_function(
  'rebuild_po_hpp',
  $old$  v_other numeric(24,6):=0;
  v_shared_labor numeric(24,6):=0;$old$,
  $new$  v_other numeric(24,6):=0;
  v_attendance_hpp numeric(24,6):=0;
  v_shared_attendance_hpp numeric(24,6):=0;
  v_shared_labor numeric(24,6):=0;$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'rebuild_po_hpp',
  $old$  v_group_rework numeric(24,6);
  v_lot_labor numeric(24,6);$old$,
  $new$  v_group_rework numeric(24,6);
  v_group_attendance_hpp numeric(24,6);
  v_lot_attendance_hpp numeric(24,6);
  v_lot_labor numeric(24,6);$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'rebuild_po_hpp',
  $old$  select coalesce(sum(adjustment_amount),0),coalesce(sum(case when lot_id is null then adjustment_amount else 0 end),0)
  into v_other,v_shared_other
  from erp.cost_adjustments
  where po_id=p_po_id and component_type='OTHER';$old$,
  $new$  select coalesce(sum(adjustment_amount),0),coalesce(sum(case when lot_id is null then adjustment_amount else 0 end),0)
  into v_other,v_shared_other
  from erp.cost_adjustments
  where po_id=p_po_id and component_type='OTHER';

  select
    coalesce(sum(a.allocated_amount),0),
    coalesce(sum(case when a.cutting_group_id is null then a.allocated_amount else 0 end),0)
  into v_attendance_hpp,v_shared_attendance_hpp
  from erp.attendance_hpp_pool_allocations a
  join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
  where a.po_id=p_po_id;$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'rebuild_po_hpp',
  $old$    v_group_fg_qty:=0;v_group_labor:=0;v_group_commission:=0;v_group_laundry:=0;v_group_rework:=0;$old$,
  $new$    v_group_fg_qty:=0;v_group_labor:=0;v_group_commission:=0;v_group_laundry:=0;v_group_rework:=0;v_group_attendance_hpp:=0;$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'rebuild_po_hpp',
  $old$      select coalesce(sum(rcl.amount_payable),0) into v_group_rework
      from erp.rework_component_lines rcl
      join erp.rework_orders ro on ro.id=rcl.rework_order_id
      join erp.bs_cases bc on bc.id=ro.bs_case_id
      where bc.po_id=p_po_id and bc.cutting_group_id=r.lineage_group_id and ro.status<>'CANCELLED' and coalesce(ro.cost_posted,false)=true;$old$,
  $new$      select coalesce(sum(rcl.amount_payable),0) into v_group_rework
      from erp.rework_component_lines rcl
      join erp.rework_orders ro on ro.id=rcl.rework_order_id
      join erp.bs_cases bc on bc.id=ro.bs_case_id
      where bc.po_id=p_po_id and bc.cutting_group_id=r.lineage_group_id and ro.status<>'CANCELLED' and coalesce(ro.cost_posted,false)=true;

      select coalesce(sum(a.allocated_amount),0) into v_group_attendance_hpp
      from erp.attendance_hpp_pool_allocations a
      join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
      where a.po_id=p_po_id and a.cutting_group_id=r.lineage_group_id;$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'rebuild_po_hpp',
  $old$    if coalesce(v_group_fg_qty,0)>0 then
      v_lot_labor:=v_group_labor*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_labor*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_commission:=v_group_commission*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_commission*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_laundry:=v_group_laundry*(r.initial_qty_pcs::numeric/v_group_fg_qty);
      v_lot_rework:=v_group_rework*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_rework*(r.initial_qty_pcs::numeric/v_total_qty);
    else
      v_lot_labor:=v_labor*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_commission:=v_commission*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_laundry:=v_laundry*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_rework:=v_rework*(r.initial_qty_pcs::numeric/v_total_qty);
    end if;$old$,
  $new$    if coalesce(v_group_fg_qty,0)>0 then
      v_lot_labor:=v_group_labor*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_labor*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_commission:=v_group_commission*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_commission*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_laundry:=v_group_laundry*(r.initial_qty_pcs::numeric/v_group_fg_qty);
      v_lot_rework:=v_group_rework*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_rework*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_attendance_hpp:=v_group_attendance_hpp*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_attendance_hpp*(r.initial_qty_pcs::numeric/v_total_qty);
    else
      v_lot_labor:=v_labor*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_commission:=v_commission*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_laundry:=v_laundry*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_rework:=v_rework*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_attendance_hpp:=v_shared_attendance_hpp*(r.initial_qty_pcs::numeric/v_total_qty);
    end if;$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'rebuild_po_hpp',
  $old$    v_lot_cost:=v_lot_material+v_lot_labor+v_lot_commission+v_lot_laundry+v_lot_rework+v_lot_other+v_lot_accessory;$old$,
  $new$    v_lot_cost:=v_lot_material+v_lot_labor+v_lot_commission+v_lot_laundry+v_lot_rework+v_lot_attendance_hpp+v_lot_other+v_lot_accessory;$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'rebuild_po_hpp',
  $old$      (v_new_id,'REWORK','Rework allocation from same cutting group + legacy shared fallback',v_lot_rework,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'OTHER','Other/adjustment allocation',v_lot_other,'PO',p_po_id);$old$,
  $new$      (v_new_id,'REWORK','Rework allocation from same cutting group + legacy shared fallback',v_lot_rework,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'LABOR','Attendance HPP: ACTIVE pool allocation by immutable sewing lineage',v_lot_attendance_hpp,'ATTENDANCE_HPP_ACTIVE_ALLOCATION',coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'OTHER','Other/adjustment allocation',v_lot_other,'PO',p_po_id);$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'rebuild_po_hpp',
  $old$    'accessory',v_accessory,'labor',v_labor,'commission',v_commission,'laundry',v_laundry,'rework',v_rework,'other',v_other,$old$,
  $new$    'accessory',v_accessory,'labor',v_labor,'attendance_hpp',v_attendance_hpp,'commission',v_commission,'laundry',v_laundry,'rework',v_rework,'other',v_other,$new$,
  1,1
);

-- The pool journal, HPP versions, conversion descendants, and GL targets are
-- one transaction. The journal's actual transaction_date is reused so a closed
-- accounting period shift cannot split the lifecycle across dates.
select pg_temp.cp4_replace_function(
  'activate_attendance_hpp_pool_v1',
  $old$  v_journal_id uuid;
  v_line record;$old$,
  $new$  v_journal_id uuid;
  v_effective_date date;
  v_line record;$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'activate_attendance_hpp_pool_v1',
  $old$  v_journal_id := erp.post_journal(
    'ATTENDANCE_HPP_POOL', v_pool.id, v_pool.period_end,
    'Allocate normal-Mandor attendance cost by immutable SELESAI_DIJAHIT',
    v_lines
  );$old$,
  $new$  v_journal_id := erp.post_journal(
    'ATTENDANCE_HPP_POOL', v_pool.id, v_pool.period_end,
    'Allocate normal-Mandor attendance cost by immutable SELESAI_DIJAHIT',
    v_lines
  );
  select transaction_date into v_effective_date
  from erp.journal_entries where id=v_journal_id;$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'activate_attendance_hpp_pool_v1',
  $old$  perform erp.validate_attendance_hpp_pool_v1(v_pool.id);

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)$old$,
  $new$  perform erp.validate_attendance_hpp_pool_v1(v_pool.id);

  for v_line in
    select distinct a.po_id
    from erp.attendance_hpp_pool_allocations a
    where a.pool_id=v_pool.id
    order by a.po_id
  loop
    perform erp.rebuild_po_hpp(v_line.po_id,'Attendance HPP pool activation '||v_pool.id::text);
    perform erp.propagate_conversion_hpp_for_po(v_line.po_id);
    perform erp.sync_po_hpp_to_gl(v_line.po_id,v_effective_date);
  end loop;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'cancel_attendance_hpp_pool_v1',
  $old$  v_reversal_journal_id uuid;
  v_response jsonb;$old$,
  $new$  v_reversal_journal_id uuid;
  v_effective_date date;
  v_po_id uuid;
  v_response jsonb;$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'cancel_attendance_hpp_pool_v1',
  $old$  v_reversal_journal_id := erp._cp3_r4_reverse_journal_internal(v_pool.post_journal_entry_id, btrim(p_reason));$old$,
  $new$  v_reversal_journal_id := erp._cp3_r4_reverse_journal_internal(v_pool.post_journal_entry_id, btrim(p_reason));
  select transaction_date into v_effective_date
  from erp.journal_entries where id=v_reversal_journal_id;$new$,
  1,1
);

select pg_temp.cp4_replace_function(
  'cancel_attendance_hpp_pool_v1',
  $old$  where id = v_pool.id
  returning * into v_pool;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)$old$,
  $new$  where id = v_pool.id
  returning * into v_pool;

  for v_po_id in
    select distinct a.po_id
    from erp.attendance_hpp_pool_allocations a
    where a.pool_id=v_pool.id
    order by a.po_id
  loop
    perform erp.rebuild_po_hpp(v_po_id,'Attendance HPP pool cancellation '||v_pool.id::text);
    perform erp.propagate_conversion_hpp_for_po(v_po_id);
    perform erp.sync_po_hpp_to_gl(v_po_id,v_effective_date);
  end loop;

  insert into erp.audit_logs(entity_type, entity_id, action, new_data, changed_by, change_reason)$new$,
  1,1
);

-- Public Data API wrappers. Inner functions and tables remain private. Every
-- wrapper repeats the owner/admin check so STAFF/unmapped/inactive users fail
-- before any business mutation. service_role remains an explicit server-only
-- operational caller; the browser artifact scanner forbids that key client-side.
create function public.erp_set_contractor_hpp_policy_v1(
  p_payload jsonb,
  p_client_request_id uuid,
  p_expected_current_policy_id uuid default null
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
begin
  perform erp.require_owner_admin();
  return erp.set_contractor_hpp_policy_v1(p_payload,p_client_request_id,p_expected_current_policy_id);
end
$function$;

create function public.erp_record_sewing_terminal_v1(p_payload jsonb,p_client_request_id uuid)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
begin
  perform erp.require_owner_admin();
  return erp.record_sewing_terminal_v1(p_payload,p_client_request_id);
end
$function$;

create function public.erp_reverse_sewing_terminal_v1(
  p_event_id uuid,
  p_reason text,
  p_client_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
begin
  perform erp.require_owner_admin();
  return erp.reverse_sewing_terminal_v1(p_event_id,p_reason,p_client_request_id);
end
$function$;

create function public.erp_preview_attendance_hpp_pool_v1(p_period_start date,p_period_end date)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
begin
  perform erp.require_owner_admin();
  return erp.preview_attendance_hpp_pool_v1(p_period_start,p_period_end);
end
$function$;

create function public.erp_create_attendance_hpp_pool_v1(p_payload jsonb,p_client_request_id uuid)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
begin
  perform erp.require_owner_admin();
  return erp.create_attendance_hpp_pool_v1(p_payload,p_client_request_id);
end
$function$;

create function public.erp_activate_attendance_hpp_pool_v1(
  p_pool_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
begin
  perform erp.require_owner_admin();
  return erp.activate_attendance_hpp_pool_v1(p_pool_id,p_reason,p_client_request_id,p_expected_version);
end
$function$;

create function public.erp_cancel_attendance_hpp_pool_v1(
  p_pool_id uuid,
  p_reason text,
  p_client_request_id uuid,
  p_expected_version bigint
)
returns jsonb
language plpgsql
security definer
set search_path=''
as $function$
begin
  perform erp.require_owner_admin();
  return erp.cancel_attendance_hpp_pool_v1(p_pool_id,p_reason,p_client_request_id,p_expected_version);
end
$function$;

revoke all on function public.erp_set_contractor_hpp_policy_v1(jsonb,uuid,uuid) from public, anon, authenticated, service_role;
revoke all on function public.erp_record_sewing_terminal_v1(jsonb,uuid) from public, anon, authenticated, service_role;
revoke all on function public.erp_reverse_sewing_terminal_v1(uuid,text,uuid) from public, anon, authenticated, service_role;
revoke all on function public.erp_preview_attendance_hpp_pool_v1(date,date) from public, anon, authenticated, service_role;
revoke all on function public.erp_create_attendance_hpp_pool_v1(jsonb,uuid) from public, anon, authenticated, service_role;
revoke all on function public.erp_activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint) from public, anon, authenticated, service_role;
revoke all on function public.erp_cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint) from public, anon, authenticated, service_role;

grant execute on function public.erp_set_contractor_hpp_policy_v1(jsonb,uuid,uuid) to authenticated, service_role;
grant execute on function public.erp_record_sewing_terminal_v1(jsonb,uuid) to authenticated, service_role;
grant execute on function public.erp_reverse_sewing_terminal_v1(uuid,text,uuid) to authenticated, service_role;
grant execute on function public.erp_preview_attendance_hpp_pool_v1(date,date) to authenticated, service_role;
grant execute on function public.erp_create_attendance_hpp_pool_v1(jsonb,uuid) to authenticated, service_role;
grant execute on function public.erp_activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint) to authenticated, service_role;
grant execute on function public.erp_cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint) to authenticated, service_role;

do $post_guard$
declare v_bad text;v_wrapper_count integer;
begin
  select count(*) into v_wrapper_count
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public'
    and p.proname in (
      'erp_set_contractor_hpp_policy_v1','erp_record_sewing_terminal_v1',
      'erp_reverse_sewing_terminal_v1','erp_preview_attendance_hpp_pool_v1',
      'erp_create_attendance_hpp_pool_v1','erp_activate_attendance_hpp_pool_v1',
      'erp_cancel_attendance_hpp_pool_v1'
    );
  if v_wrapper_count<>7 then
    raise exception 'ERP v2.6.16 expected seven exact public wrappers, found %',v_wrapper_count;
  end if;

  select string_agg(p.proname,',' order by p.proname) into v_bad
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public'
    and p.proname like 'erp\_%' escape '\'
    and p.proname in (
      'erp_set_contractor_hpp_policy_v1','erp_record_sewing_terminal_v1',
      'erp_reverse_sewing_terminal_v1','erp_preview_attendance_hpp_pool_v1',
      'erp_create_attendance_hpp_pool_v1','erp_activate_attendance_hpp_pool_v1',
      'erp_cancel_attendance_hpp_pool_v1'
    )
    and (
      has_function_privilege('anon',p.oid,'EXECUTE')
      or not has_function_privilege('authenticated',p.oid,'EXECUTE')
      or not has_function_privilege('service_role',p.oid,'EXECUTE')
      or p.prosecdef is distinct from true
      or pg_get_functiondef(p.oid) not like '%SET search_path TO ''''%'
    );
  if v_bad is not null then
    raise exception 'ERP v2.6.16 public wrapper ACL/search_path contract failed: %',v_bad;
  end if;

  if has_function_privilege('anon','erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)','EXECUTE')
     or has_function_privilege('service_role','erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)','EXECUTE')
     or has_table_privilege('authenticated','erp.attendance_hpp_pools','SELECT')
     or has_table_privilege('service_role','erp.attendance_hpp_pools','SELECT') then
    raise exception 'ERP v2.6.16 private CP3 boundary was accidentally exposed';
  end if;

  if has_function_privilege('public','erp.require_owner_admin()','EXECUTE')
     or has_function_privilege('anon','erp.require_owner_admin()','EXECUTE')
     or has_function_privilege('authenticated','erp.require_owner_admin()','EXECUTE')
     or not has_function_privilege('service_role','erp.require_owner_admin()','EXECUTE')
     or pg_get_functiondef('erp.require_owner_admin()'::regprocedure) not like '%SET search_path TO ''''%' then
    raise exception 'ERP v2.6.16 null-safe owner/admin guard ACL or search_path mismatch';
  end if;
end
$post_guard$;

insert into erp.schema_migrations(version,description)
values('v2.6.16','CP4 persistent attendance-HPP lot/GL route and null-safe least-privilege owner/admin Data API boundary');

select pg_notify('pgrst','reload schema');
commit;
