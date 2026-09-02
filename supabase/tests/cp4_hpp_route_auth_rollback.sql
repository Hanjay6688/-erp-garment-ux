-- CP4 R1 persistent HPP route, atomic lifecycle, ACL, and rollback-safe acceptance.
-- Every synthetic business row and injected failure is contained by this transaction.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local datestyle='ISO, MDY';
set local lock_timeout='8s';
set local statement_timeout='120s';

\ir cp3_r4_full_schema_seed.sql

create temp table cp4_ids(key text primary key,value jsonb) on commit drop;
create temp table cp4_saved_functions(function_identity text primary key,function_definition text not null) on commit drop;

insert into erp.brands(id,brand_code,brand_name)
values('b1000000-0000-0000-0000-000000000001','CP4-R1','CP4 R1 Brand');

insert into erp.locations(id,location_code,location_name,location_type)
values('b1100000-0000-0000-0000-000000000001','CP4-FG','CP4 FG Warehouse','FG_WAREHOUSE');

insert into erp.products(
  id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from
) values (
  'b2000000-0000-0000-0000-000000000001','CP4-R1-SKU',
  'a2000000-0000-0000-0000-000000000001','b1000000-0000-0000-0000-000000000001',
  'TEST','a2100000-0000-0000-0000-000000000001','CP4 R1 Product',
  'b2000000-0000-0000-0000-000000000001','2026-01-01 00:00:00+00'
);

-- Explicit empty BOM: this fixture intentionally has no accessory cost. The
-- runtime must keep failing closed when neither a real BOM nor this explicit
-- NO ACCESSORY declaration exists.
insert into erp.accessory_bom_versions(
  product_id,version_label,effective_from,is_active,notes
) values (
  'b2000000-0000-0000-0000-000000000001','CP4-NO-ACCESSORY',
  '2026-01-01 00:00:00+00',true,'Empty BOM declaration for CP4 rollback-only acceptance'
);

insert into erp.fg_lots(
  id,lot_number,po_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,cutting_group_id
) values
 ('b3000000-0000-0000-0000-000000000001','CP4-R1-LOT-A','a3000000-0000-0000-0000-000000000001','b2000000-0000-0000-0000-000000000001',60,60,'2026-01-01 14:00:00+07','a3200000-0000-0000-0000-000000000001'),
 ('b3000000-0000-0000-0000-000000000002','CP4-R1-LOT-B','a3000000-0000-0000-0000-000000000002','b2000000-0000-0000-0000-000000000001',40,40,'2026-01-01 14:00:00+07','a3200000-0000-0000-0000-000000000002');

insert into erp.fg_stock_movements(
  id,product_id,lot_id,location_id,movement_type,qty_signed,source_type,source_id,physical_at,unit_hpp_snapshot,notes
) values
 ('b3100000-0000-0000-0000-000000000001','b2000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000001','b1100000-0000-0000-0000-000000000001','QC_GOOD',60,'CP4_ACCEPTANCE','b3000000-0000-0000-0000-000000000001','2026-01-01 14:00:00+07',0,'CP4 synthetic FG A'),
 ('b3100000-0000-0000-0000-000000000002','b2000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000002','b1100000-0000-0000-0000-000000000001','QC_GOOD',40,'CP4_ACCEPTANCE','b3000000-0000-0000-0000-000000000002','2026-01-01 14:00:00+07',0,'CP4 synthetic FG B');

select erp.rebuild_po_hpp('a3000000-0000-0000-0000-000000000001','CP4 pre-activation baseline');
select erp.rebuild_po_hpp('a3000000-0000-0000-0000-000000000002','CP4 pre-activation baseline');
select erp.sync_po_hpp_to_gl('a3000000-0000-0000-0000-000000000001','2026-01-01');
select erp.sync_po_hpp_to_gl('a3000000-0000-0000-0000-000000000002','2026-01-01');

-- CP3's full-schema fixture already carries legitimate non-attendance work
-- cost. Bind every CP4 assertion to that exact baseline so this test proves
-- the attendance delta without pretending the existing HPP is zero.
insert into cp4_ids(key,value)
select 'baseline',jsonb_build_object(
  'hpp_total',(select round(coalesce(sum(h.total_cost),0),2)
    from erp.hpp_versions h
    where h.is_current and h.lot_id in('b3000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000002')),
  'gl_hpp',(select round(coalesce(sum(s.hpp_total_cost),0),2)
    from erp.po_hpp_gl_state s
    where s.po_id in('a3000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000002')),
  'lot_a',(select round(total_cost,2) from erp.hpp_versions
    where lot_id='b3000000-0000-0000-0000-000000000001' and is_current),
  'lot_b',(select round(total_cost,2) from erp.hpp_versions
    where lot_id='b3000000-0000-0000-0000-000000000002' and is_current),
  'fg_net',(select round(coalesce(sum(case when jl.account_id=erp.account_id('FG_INVENTORY') then jl.debit-jl.credit else 0 end),0),2)
    from erp.journal_entries je join erp.po_hpp_gl_events e on e.id=je.source_id
    join erp.journal_lines jl on jl.journal_entry_id=je.id
    where je.source_type='PO_HPP_GL_SYNC'
      and e.po_id in('a3000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000002')),
  'wip_net',(select round(coalesce(sum(case when jl.account_id=erp.account_id('WIP') then jl.credit-jl.debit else 0 end),0),2)
    from erp.journal_entries je join erp.po_hpp_gl_events e on e.id=je.source_id
    join erp.journal_lines jl on jl.journal_entry_id=je.id
    where je.source_type='PO_HPP_GL_SYNC'
      and e.po_id in('a3000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000002'))
);

insert into cp4_ids(key,value)
values('pool',public.erp_create_attendance_hpp_pool_v1(
  jsonb_build_object('period_start','2026-01-01','period_end','2026-01-01','reason','CP4 persistent HPP route'),
  'b4000000-0000-4000-8000-000000000001'
));

do $test$
declare v_pool uuid:=(select (value->>'pool_id')::uuid from cp4_ids where key='pool');
begin
  if (select value->>'status' from cp4_ids where key='pool') is distinct from 'DRAFT'
     or (select (value->>'numerator_amount')::numeric from cp4_ids where key='pool') is distinct from 150.00
     or (select (value->>'denominator_qty')::bigint from cp4_ids where key='pool')<>100 then
    raise exception 'CP4 DRAFT pool basis mismatch: %',(select value from cp4_ids where key='pool');
  end if;
  if (select round(sum(allocated_amount),2) from erp.attendance_hpp_pool_allocations where pool_id=v_pool) is distinct from 150.00 then
    raise exception 'CP4 DRAFT allocation did not reconcile to 150.00';
  end if;
end
$test$;

-- Inject a failure at the last HPP/GL stage. The owning activation must roll
-- back its pool journal, status, HPP versions, GL state, and idempotency row.
insert into cp4_saved_functions(function_identity,function_definition)
select 'erp.sync_po_hpp_to_gl(uuid,date)',pg_get_functiondef('erp.sync_po_hpp_to_gl(uuid,date)'::regprocedure);

create or replace function erp.sync_po_hpp_to_gl(p_po_id uuid,p_effective_date date default current_date)
returns void
language plpgsql
security definer
set search_path=erp,public
as $injected$
begin
  raise exception 'CP4_INJECTED_HPP_FAILURE';
end
$injected$;

do $test$
declare
  v_pool uuid:=(select (value->>'pool_id')::uuid from cp4_ids where key='pool');
  v_hpp_count bigint:=(select count(*) from erp.hpp_versions where lot_id in('b3000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000002'));
begin
  begin
    perform public.erp_activate_attendance_hpp_pool_v1(
      v_pool,'CP4 injected activation failure','b4000000-0000-4000-8000-000000000002',1
    );
    raise exception 'CP4 expected injected activation failure was not raised';
  exception when others then
    if sqlerrm not like '%CP4_INJECTED_HPP_FAILURE%' then raise; end if;
  end;

  if (select status from erp.attendance_hpp_pools where id=v_pool) is distinct from 'DRAFT'
     or (select row_version from erp.attendance_hpp_pools where id=v_pool)<>1
     or (select post_journal_entry_id from erp.attendance_hpp_pools where id=v_pool) is not null
     or exists(select 1 from erp.journal_entries where source_type='ATTENDANCE_HPP_POOL' and source_id=v_pool)
     or (select count(*) from erp.hpp_versions where lot_id in('b3000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000002'))<>v_hpp_count then
    raise exception 'CP4 failed activation left partial residue';
  end if;
end
$test$;

do $restore$
declare v_definition text;
begin
  select function_definition into v_definition from cp4_saved_functions where function_identity='erp.sync_po_hpp_to_gl(uuid,date)';
  execute v_definition;
end
$restore$;

insert into cp4_ids(key,value)
values('activated',public.erp_activate_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp4_ids where key='pool'),
  'CP4 activate persistent HPP','b4000000-0000-4000-8000-000000000003',1
));

do $test$
declare
  v_pool uuid:=(select (value->>'pool_id')::uuid from cp4_ids where key='pool');
  v_attendance numeric;
  v_hpp_total numeric;
  v_gl_hpp numeric;
  v_pool_debit numeric;
  v_pool_credit numeric;
  v_fg_net numeric;
  v_wip_net numeric;
  v_attendance_a numeric;
  v_attendance_b numeric;
  v_base_hpp numeric:=(select (value->>'hpp_total')::numeric from cp4_ids where key='baseline');
  v_base_gl numeric:=(select (value->>'gl_hpp')::numeric from cp4_ids where key='baseline');
  v_base_lot_a numeric:=(select (value->>'lot_a')::numeric from cp4_ids where key='baseline');
  v_base_lot_b numeric:=(select (value->>'lot_b')::numeric from cp4_ids where key='baseline');
  v_base_fg_net numeric:=(select (value->>'fg_net')::numeric from cp4_ids where key='baseline');
  v_base_wip_net numeric:=(select (value->>'wip_net')::numeric from cp4_ids where key='baseline');
begin
  if (select value->>'status' from cp4_ids where key='activated') is distinct from 'ACTIVE'
     or (select (value->>'row_version')::bigint from cp4_ids where key='activated')<>2 then
    raise exception 'CP4 activation response mismatch: %',(select value from cp4_ids where key='activated');
  end if;

  select round(sum(c.total_cost),2) into v_attendance
  from erp.hpp_versions h
  join erp.hpp_version_components c on c.hpp_version_id=h.id
  where h.is_current and h.lot_id in('b3000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000002')
    and c.component_type='LABOR' and c.source_type='ATTENDANCE_HPP_ACTIVE_ALLOCATION';
  select
    round(coalesce(sum(c.total_cost) filter(where h.lot_id='b3000000-0000-0000-0000-000000000001'),0),2),
    round(coalesce(sum(c.total_cost) filter(where h.lot_id='b3000000-0000-0000-0000-000000000002'),0),2)
  into v_attendance_a,v_attendance_b
  from erp.hpp_versions h
  join erp.hpp_version_components c on c.hpp_version_id=h.id
  where h.is_current
    and h.lot_id in('b3000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000002')
    and c.component_type='LABOR' and c.source_type='ATTENDANCE_HPP_ACTIVE_ALLOCATION';
  select round(sum(h.total_cost),2) into v_hpp_total
  from erp.hpp_versions h
  where h.is_current and h.lot_id in('b3000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000002');
  select round(sum(s.hpp_total_cost),2) into v_gl_hpp
  from erp.po_hpp_gl_state s
  where s.po_id in('a3000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000002');

  select round(coalesce(sum(jl.debit),0),2),round(coalesce(sum(jl.credit),0),2)
  into v_pool_debit,v_pool_credit
  from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id
  where je.source_type='ATTENDANCE_HPP_POOL' and je.source_id=v_pool and je.status='POSTED';

  select
    round(coalesce(sum(case when jl.account_id=erp.account_id('FG_INVENTORY') then jl.debit-jl.credit else 0 end),0),2),
    round(coalesce(sum(case when jl.account_id=erp.account_id('WIP') then jl.credit-jl.debit else 0 end),0),2)
  into v_fg_net,v_wip_net
  from erp.journal_entries je join erp.po_hpp_gl_events e on e.id=je.source_id
  join erp.journal_lines jl on jl.journal_entry_id=je.id
  where je.source_type='PO_HPP_GL_SYNC'
    and e.po_id in('a3000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000002')
    and je.status='POSTED';

  if v_attendance is distinct from 150.00
     or v_attendance_a is distinct from 90.00
     or v_attendance_b is distinct from 60.00
     or v_hpp_total is distinct from v_base_hpp+150.00
     or v_gl_hpp is distinct from v_base_gl+150.00
     or v_pool_debit is distinct from 150.00
     or v_pool_credit is distinct from 150.00
     or v_fg_net is distinct from v_base_fg_net+150.00
     or v_wip_net is distinct from v_base_wip_net+150.00 then
    raise exception 'CP4 activation reconciliation mismatch attendance % (%/%), HPP % baseline %, GL % baseline %, pool D/C %/%, FG/WIP net %/% baselines %/%',
      v_attendance,v_attendance_a,v_attendance_b,v_hpp_total,v_base_hpp,v_gl_hpp,v_base_gl,
      v_pool_debit,v_pool_credit,v_fg_net,v_wip_net,v_base_fg_net,v_base_wip_net;
  end if;

  if (select round(total_cost,2) from erp.hpp_versions where lot_id='b3000000-0000-0000-0000-000000000001' and is_current) is distinct from v_base_lot_a+90.00
     or (select round(total_cost,2) from erp.hpp_versions where lot_id='b3000000-0000-0000-0000-000000000002' and is_current) is distinct from v_base_lot_b+60.00 then
    raise exception 'CP4 immutable sewing-lineage allocation did not add lot HPP 90/60 over baseline';
  end if;
end
$test$;

-- Inject the same last-stage failure into cancellation. The ACTIVE pool and
-- its posted journal/HPP must remain untouched until the whole correction works.
create or replace function erp.sync_po_hpp_to_gl(p_po_id uuid,p_effective_date date default current_date)
returns void
language plpgsql
security definer
set search_path=erp,public
as $injected$
begin
  raise exception 'CP4_INJECTED_HPP_FAILURE';
end
$injected$;

do $test$
declare
  v_pool uuid:=(select (value->>'pool_id')::uuid from cp4_ids where key='pool');
  v_post uuid:=(select post_journal_entry_id from erp.attendance_hpp_pools where id=(select (value->>'pool_id')::uuid from cp4_ids where key='pool'));
begin
  begin
    perform public.erp_cancel_attendance_hpp_pool_v1(
      v_pool,'CP4 injected cancellation failure','b4000000-0000-4000-8000-000000000004',2
    );
    raise exception 'CP4 expected injected cancellation failure was not raised';
  exception when others then
    if sqlerrm not like '%CP4_INJECTED_HPP_FAILURE%' then raise; end if;
  end;

  if (select status from erp.attendance_hpp_pools where id=v_pool) is distinct from 'ACTIVE'
     or (select row_version from erp.attendance_hpp_pools where id=v_pool)<>2
     or (select status from erp.journal_entries where id=v_post) is distinct from 'POSTED'
     or exists(select 1 from erp.journal_entries where reversal_of_id=v_post)
     or (select round(sum(h.total_cost),2) from erp.hpp_versions h where h.is_current and h.lot_id in('b3000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000002'))
        is distinct from (select (value->>'hpp_total')::numeric+150.00 from cp4_ids where key='baseline') then
    raise exception 'CP4 failed cancellation left partial residue';
  end if;
end
$test$;

do $restore$
declare v_definition text;
begin
  select function_definition into v_definition from cp4_saved_functions where function_identity='erp.sync_po_hpp_to_gl(uuid,date)';
  execute v_definition;
end
$restore$;

insert into cp4_ids(key,value)
values('cancelled',public.erp_cancel_attendance_hpp_pool_v1(
  (select (value->>'pool_id')::uuid from cp4_ids where key='pool'),
  'CP4 cancel persistent HPP','b4000000-0000-4000-8000-000000000005',2
));

do $test$
declare
  v_pool uuid:=(select (value->>'pool_id')::uuid from cp4_ids where key='pool');
  v_post uuid:=(select post_journal_entry_id from erp.attendance_hpp_pools where id=(select (value->>'pool_id')::uuid from cp4_ids where key='pool'));
  v_pool_net numeric;
  v_hpp_sync_fg_net numeric;
  v_hpp_sync_wip_net numeric;
  v_base_hpp numeric:=(select (value->>'hpp_total')::numeric from cp4_ids where key='baseline');
  v_base_gl numeric:=(select (value->>'gl_hpp')::numeric from cp4_ids where key='baseline');
  v_base_fg_net numeric:=(select (value->>'fg_net')::numeric from cp4_ids where key='baseline');
  v_base_wip_net numeric:=(select (value->>'wip_net')::numeric from cp4_ids where key='baseline');
begin
  if (select value->>'status' from cp4_ids where key='cancelled') is distinct from 'CANCELLED'
     or (select (value->>'row_version')::bigint from cp4_ids where key='cancelled')<>3
     or (select status from erp.journal_entries where id=v_post) is distinct from 'REVERSED'
     or not exists(select 1 from erp.journal_entries where reversal_of_id=v_post and status='POSTED') then
    raise exception 'CP4 owning cancellation response/journal mismatch: %',(select value from cp4_ids where key='cancelled');
  end if;

  if exists(
    select 1 from erp.hpp_versions h
    join erp.hpp_version_components c on c.hpp_version_id=h.id
    where h.is_current
      and h.lot_id in('b3000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000002')
      and c.source_type='ATTENDANCE_HPP_ACTIVE_ALLOCATION'
      and abs(c.total_cost)>0.005
  )
     or (select round(sum(h.total_cost),2) from erp.hpp_versions h where h.is_current and h.lot_id in('b3000000-0000-0000-0000-000000000001','b3000000-0000-0000-0000-000000000002')) is distinct from v_base_hpp
     or (select round(sum(s.hpp_total_cost),2) from erp.po_hpp_gl_state s where s.po_id in('a3000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000002')) is distinct from v_base_gl
     or exists(select 1 from erp.v_attendance_hpp_active_allocation_by_po_group where pool_id=v_pool) then
    raise exception 'CP4 cancellation left active HPP residue';
  end if;

  select round(coalesce(sum(jl.debit-jl.credit),0),2) into v_pool_net
  from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id
  where je.id=v_post or je.reversal_of_id=v_post;

  select
    round(coalesce(sum(case when jl.account_id=erp.account_id('FG_INVENTORY') then jl.debit-jl.credit else 0 end),0),2),
    round(coalesce(sum(case when jl.account_id=erp.account_id('WIP') then jl.credit-jl.debit else 0 end),0),2)
  into v_hpp_sync_fg_net,v_hpp_sync_wip_net
  from erp.journal_entries je join erp.po_hpp_gl_events e on e.id=je.source_id
  join erp.journal_lines jl on jl.journal_entry_id=je.id
  where je.source_type='PO_HPP_GL_SYNC'
    and e.po_id in('a3000000-0000-0000-0000-000000000001','a3000000-0000-0000-0000-000000000002');

  if v_pool_net is distinct from 0.00
     or v_hpp_sync_fg_net is distinct from v_base_fg_net
     or v_hpp_sync_wip_net is distinct from v_base_wip_net then
    raise exception 'CP4 activation+cancellation did not return to journal baseline: pool %, FG % baseline %, WIP % baseline %',
      v_pool_net,v_hpp_sync_fg_net,v_base_fg_net,v_hpp_sync_wip_net,v_base_wip_net;
  end if;
end
$test$;

-- Static boundary proof complements the real HTTP/JWT E2E runner.
do $test$
declare r record;
begin
  for r in
    select p.oid,p.proname,p.prosecdef,pg_get_functiondef(p.oid) definition
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public'
      and p.proname in(
        'erp_set_contractor_hpp_policy_v1','erp_record_sewing_terminal_v1',
        'erp_reverse_sewing_terminal_v1','erp_preview_attendance_hpp_pool_v1',
        'erp_create_attendance_hpp_pool_v1','erp_activate_attendance_hpp_pool_v1',
        'erp_cancel_attendance_hpp_pool_v1'
      )
  loop
    if has_function_privilege('anon',r.oid,'EXECUTE')
       or not has_function_privilege('authenticated',r.oid,'EXECUTE')
       or not has_function_privilege('service_role',r.oid,'EXECUTE')
       or not r.prosecdef
       or r.definition not like '%SET search_path TO ''''%' then
      raise exception 'CP4 public wrapper boundary mismatch: %',r.proname;
    end if;
  end loop;

  if has_function_privilege('public','erp._cp3_r4_reverse_journal_internal(uuid,text)','EXECUTE')
     or has_function_privilege('anon','erp._cp3_r4_reverse_journal_internal(uuid,text)','EXECUTE')
     or has_function_privilege('authenticated','erp._cp3_r4_reverse_journal_internal(uuid,text)','EXECUTE')
     or has_function_privilege('service_role','erp._cp3_r4_reverse_journal_internal(uuid,text)','EXECUTE')
     or has_table_privilege('authenticated','erp.attendance_hpp_pools','SELECT')
     or has_table_privilege('service_role','erp.attendance_hpp_pools','SELECT') then
    raise exception 'CP4 private route or reversal primitive gained exposure';
  end if;

  if has_function_privilege('public','erp.require_owner_admin()','EXECUTE')
     or has_function_privilege('anon','erp.require_owner_admin()','EXECUTE')
     or has_function_privilege('authenticated','erp.require_owner_admin()','EXECUTE')
     or not has_function_privilege('service_role','erp.require_owner_admin()','EXECUTE')
     or pg_get_functiondef('erp.require_owner_admin()'::regprocedure) not like '%SET search_path TO ''''%' then
    raise exception 'CP4 null-safe owner/admin guard ACL or search_path mismatch';
  end if;
end
$test$;

select jsonb_pretty(jsonb_build_object(
  'status','PASS',
  'pool_lifecycle',(select jsonb_build_object('status',status,'row_version',row_version) from erp.attendance_hpp_pools where id=(select (value->>'pool_id')::uuid from cp4_ids where key='pool')),
  'active_allocation_residue',(select count(*) from erp.v_attendance_hpp_active_allocation_by_po_group),
  'current_attendance_hpp',(select coalesce(sum(c.total_cost),0) from erp.hpp_versions h join erp.hpp_version_components c on c.hpp_version_id=h.id where h.is_current and c.source_type='ATTENDANCE_HPP_ACTIVE_ALLOCATION'),
  'private_pool_select_authenticated',has_table_privilege('authenticated','erp.attendance_hpp_pools','SELECT'),
  'private_pool_select_service_role',has_table_privilege('service_role','erp.attendance_hpp_pools','SELECT'),
  'public_preview_authenticated',has_function_privilege('authenticated','public.erp_preview_attendance_hpp_pool_v1(date,date)','EXECUTE'),
  'public_preview_service_role',has_function_privilege('service_role','public.erp_preview_attendance_hpp_pool_v1(date,date)','EXECUTE'),
  'public_preview_anon',has_function_privilege('anon','public.erp_preview_attendance_hpp_pool_v1(date,date)','EXECUTE')
));

rollback;
