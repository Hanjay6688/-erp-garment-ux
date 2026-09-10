-- ERP Garment v2.6.20f / CP6 final-runtime reliability closure.
--
-- VENI. VIDI. VICI. ERP. -- I CONQUERED ERP.
-- Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.
-- Forward-only: preserve every posted fact; correction is append-only and auditable.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';

lock table erp.schema_migrations,
  supabase_migrations.schema_migrations,
  erp.audit_logs,
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

do $guard_v2620f$
declare
  r record;
  v_actual text;
  v_platform_match_count integer;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20e') then
    raise exception 'ERP v2.6.20f requires immutable v2.6.20e first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20f') then
    raise exception 'ERP v2.6.20f is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.cp6_v2620f_rollback_capsule') is not null
     or to_regclass('erp.non_po_hpp_gl_sync_events_v2620f') is not null
     or to_regprocedure('erp.compute_non_po_product_hpp_targets_v2620f(uuid)') is not null
     or to_regprocedure('erp.compute_non_po_product_hpp_book_v2620f(uuid)') is not null
     or to_regprocedure('erp.assert_non_po_product_hpp_target_book_v2620f(uuid)') is not null
     or to_regprocedure('erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)') is not null then
    raise exception 'ERP v2.6.20f target guard: prior repair residue exists';
  end if;
  if exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'ERP v2.6.20f refuses installation while a CP6 execution context exists';
  end if;

  select count(*) into v_platform_match_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20e_cp6_counterexample_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      '8afd32e941cca025be6d68b70e1a483d98984d697b7d1da0e3d6722c423ecfdc',
      '7937cde99aa9d77e5e3d987a803fd9c11f9a4aedc61e16fdd8307849c4fe3ad2'
    );
  if v_platform_match_count<>1 then
    raise exception 'ERP v2.6.20f requires one exact v2.6.20e platform-ledger row; found %',
      v_platform_match_count;
  end if;

  for r in select * from (values
    ('erp.compute_po_hpp_gl_targets_v2620d(uuid)','77b5b531d484bcb4c1532e529e8b5269f1afab438ca16d0b1dc7f0f143efc53e'),
    ('erp.propagate_conversion_hpp_for_po(uuid)','15d8d2a4fceafe70105aa1a4f97dc08ce67571001c965dbc50f0c39310e37296'),
    ('erp.post_product_conversion(uuid)','c80f9ff4a047c7232a3bb224cccdfd9e947d38ffe8ef46b9ef9457fa43fb0e4d'),
    ('erp.post_sale(uuid)','96e5eec137b2eee4b16dd3df6aad69c084935521dfa851bf106ef0bab2239ca4'),
    ('erp.post_sales_return(uuid)','d83e9f58406528fd3777b348cf71fc7521de853c6c31c1ed668f7f3e46c2d755'),
    ('erp.reverse_sale(uuid,text)','ec522f0eeabac729590e45360752db6d0fa021e51716289a59be65856adb6cfd'),
    ('erp.reverse_sales_return(uuid,text)','8678a986758185dd489379321f4e2525187252d0108cd7fc2930121da8324175'),
    ('erp.run_v268_financial_report_checks()','5d06a5d87aecd59f6a069a2d2ad3663859787dfe5b9e4ecd4922e1f7b2e28c6e')
  ) expected(object_identity,sha256)
  loop
    if to_regprocedure(r.object_identity) is null then
      raise exception 'ERP v2.6.20f predecessor function is missing: %',r.object_identity;
    end if;
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.object_identity)),'UTF8'
    ),'sha256'),'hex') into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: % changed (%)',
        r.object_identity,v_actual;
    end if;
  end loop;
end
$guard_v2620f$;

create table erp.cp6_v2620f_rollback_capsule(
  object_identity text primary key,
  object_regidentity text not null unique,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.cp6_v2620f_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620f_rollback_capsule
  from public,anon,authenticated,service_role;

insert into erp.cp6_v2620f_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot
)
select
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(
    select a::text from unnest(p.proacl) a order by a::text
  ) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp.compute_po_hpp_gl_targets_v2620d(uuid)'::regprocedure,
  'erp.propagate_conversion_hpp_for_po(uuid)'::regprocedure,
  'erp.post_product_conversion(uuid)'::regprocedure,
  'erp.post_sale(uuid)'::regprocedure,
  'erp.post_sales_return(uuid)'::regprocedure,
  'erp.reverse_sale(uuid,text)'::regprocedure,
  'erp.reverse_sales_return(uuid,text)'::regprocedure,
  'erp.run_v268_financial_report_checks()'::regprocedure
);

do $capsule_guard_v2620f$
begin
  if (select count(*) from erp.cp6_v2620f_rollback_capsule)<>8
     or exists(
       select 1 from erp.cp6_v2620f_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
     ) then
    raise exception 'ERP v2.6.20f exact rollback capsule is incomplete or corrupt';
  end if;
end
$capsule_guard_v2620f$;

-- Explicit append-only correction evidence for any cumulative non-PO
-- redistribution that cannot be represented by reversing one old document.
create table erp.non_po_hpp_gl_sync_events_v2620f(
  id uuid primary key,
  product_id uuid not null references erp.products(id) on delete restrict,
  trigger_source_type text not null,
  trigger_source_id uuid,
  effective_date date not null,
  old_fg_value numeric(20,2) not null,
  new_fg_value numeric(20,2) not null,
  fg_delta numeric(20,2) not null,
  old_cogs_value numeric(20,2) not null,
  new_cogs_value numeric(20,2) not null,
  cogs_delta numeric(20,2) not null,
  old_other_out_value numeric(20,2) not null,
  new_other_out_value numeric(20,2) not null,
  other_delta numeric(20,2) not null,
  journal_entry_id uuid not null unique
    references erp.journal_entries(id) on delete restrict,
  reason text not null check(length(btrim(reason))>=4),
  created_by uuid references erp.app_users(id) on delete restrict,
  created_at timestamptz not null default clock_timestamp(),
  check(new_fg_value=old_fg_value+fg_delta),
  check(new_cogs_value=old_cogs_value+cogs_delta),
  check(new_other_out_value=old_other_out_value+other_delta),
  check(fg_delta+cogs_delta+other_delta=0)
);
create index idx_non_po_hpp_sync_product_v2620f
  on erp.non_po_hpp_gl_sync_events_v2620f(product_id,created_at,id);
alter table erp.non_po_hpp_gl_sync_events_v2620f enable row level security;
revoke all on table erp.non_po_hpp_gl_sync_events_v2620f
  from public,anon,authenticated,service_role;

create function erp.guard_non_po_hpp_gl_sync_event_v2620f()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
begin
  if tg_op<>'INSERT' then
    raise exception using errcode='42501',
      message='NON_PO_HPP_GL_SYNC_EVENT_IS_APPEND_ONLY';
  end if;
  return new;
end
$function$;
alter function erp.guard_non_po_hpp_gl_sync_event_v2620f() owner to postgres;
revoke all on function erp.guard_non_po_hpp_gl_sync_event_v2620f()
  from public,anon,authenticated,service_role;
create trigger trg_guard_non_po_hpp_gl_sync_event_v2620f
before update or delete on erp.non_po_hpp_gl_sync_events_v2620f
for each row execute function erp.guard_non_po_hpp_gl_sync_event_v2620f();

-- Source value comes only from original PRODUCTION lots.  Physical ownership
-- and disposition include every current conversion descendant, so an ancestor
-- and its descendant are never capitalized twice.
create or replace function erp.compute_po_hpp_gl_targets_v2620d(p_po_id uuid)
returns table(
  base_output_qty integer,hpp_total_cost numeric,fg_value numeric,
  cogs_value numeric,other_out_value numeric
)
language sql
stable
security definer
set search_path=''
as $function$
with base as(
  select coalesce(sum(fl.initial_qty_pcs),0)::integer qty,
    coalesce(sum(hv.total_cost),0)::numeric raw_total
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
  where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
), lot_hpp as(
  select fl.id lot_id,
    case when coalesce(hv.qty_basis_pcs,0)>0
      then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric hpp_per_pcs
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
  where fl.po_id=p_po_id
    and fl.lot_origin in('PRODUCTION','CONVERSION')
), lot_balance as(
  select lh.lot_id,lh.hpp_per_pcs,
    (coalesce(sum(fm.qty_signed),0)+coalesce(sum(abs(fm.qty_signed)) filter(
      where fm.movement_type='SALE_RESERVE'
        and not exists(select 1 from erp.fg_stock_movements rv
          where rv.reversal_of_id=fm.id)
    ),0))::numeric owned_qty
  from lot_hpp lh
  left join erp.fg_stock_movements fm on fm.lot_id=lh.lot_id
  group by lh.lot_id,lh.hpp_per_pcs
), sold as(
  select a.lot_id,coalesce(sum(a.qty_pcs),0)::numeric qty
  from erp.sale_stock_allocations a
  join erp.sales_items i on i.id=a.sale_item_id
  join erp.sales_headers h on h.id=i.sale_id
  join erp.fg_lots fl on fl.id=a.lot_id
  where fl.po_id=p_po_id and h.status in('POSTED','PARTIAL_PAID','PAID')
  group by a.lot_id
), returned as(
  select i.lot_id,coalesce(sum(i.qty_pcs),0)::numeric qty
  from erp.sales_return_items i
  join erp.sales_returns h on h.id=i.return_id
  join erp.fg_lots fl on fl.id=i.lot_id
  where fl.po_id=p_po_id and h.status='POSTED'
  group by i.lot_id
), raw_values as(
  select b.qty,b.raw_total,
    coalesce(sum(greatest(lb.owned_qty,0)*lb.hpp_per_pcs),0)::numeric raw_owned,
    coalesce(sum(greatest(coalesce(s.qty,0)-coalesce(r.qty,0),0)
      *lb.hpp_per_pcs),0)::numeric raw_cogs
  from base b left join lot_balance lb on true
  left join sold s on s.lot_id=lb.lot_id
  left join returned r on r.lot_id=lb.lot_id
  group by b.qty,b.raw_total
), cents as(
  select qty,round(raw_total,2)::numeric hpp,
    round(raw_total-raw_owned,2)::numeric total_out,
    round(raw_cogs,2)::numeric cogs
  from raw_values
)
select qty,hpp,(hpp-total_out)::numeric,cogs,(total_out-cogs)::numeric
from cents
$function$;
alter function erp.compute_po_hpp_gl_targets_v2620d(uuid) owner to postgres;
revoke all on function erp.compute_po_hpp_gl_targets_v2620d(uuid)
  from public,anon,authenticated,service_role;

-- Revalue conversion descendants in deterministic root-to-leaf order.  A
-- late source invoice therefore reaches every descendant level before the GL
-- target is read.
create or replace function erp.propagate_conversion_hpp_for_po(p_po_id uuid)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  r record;
  v_source_hpp numeric(18,6);
  v_desired numeric(18,6);
  v_current numeric(18,6);
  v_old_id uuid;
  v_new_id uuid;
  v_ver integer;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform 1 from erp.fg_lots
  where po_id=p_po_id and lot_origin in('PRODUCTION','CONVERSION')
  order by id for update;

  for r in
    with recursive rooted(lot_id,depth,path) as(
      select fl.id,0,array[fl.id]
      from erp.fg_lots fl
      where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
      union all
      select a.destination_lot_id,x.depth+1,x.path||a.destination_lot_id
      from rooted x
      join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
      join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
      where a.destination_lot_id is not null
        and not a.destination_lot_id=any(x.path)
        and x.depth<128
    )
    select a.*,x.depth source_depth
    from rooted x
    join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    where a.destination_lot_id is not null
    order by x.depth,a.id
  loop
    select hpp_per_pcs into v_source_hpp
    from erp.v_current_hpp where lot_id=r.source_lot_id;
    if v_source_hpp is null or r.qty_pcs<=0 then continue; end if;
    v_desired:=v_source_hpp+(r.conversion_cost_allocated/r.qty_pcs);
    select hpp_version_id,hpp_per_pcs into v_old_id,v_current
    from erp.v_current_hpp where lot_id=r.destination_lot_id;
    if v_old_id is null or abs(coalesce(v_current,0)-v_desired)>0.000001 then
      select coalesce(max(version_no),0)+1 into v_ver
      from erp.hpp_versions where lot_id=r.destination_lot_id;
      update erp.hpp_versions set is_current=false
      where lot_id=r.destination_lot_id and is_current;
      insert into erp.hpp_versions(
        lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,
        supersedes_id,calculation_reason,created_by
      ) values(
        r.destination_lot_id,v_ver,'ADJUSTED',r.qty_pcs,r.qty_pcs*v_desired,
        true,v_old_id,'Root-to-leaf propagated source HPP through SKU conversion',
        erp.current_app_user_id()
      ) returning id into v_new_id;
      insert into erp.hpp_version_components(
        hpp_version_id,component_type,description,qty_basis,unit_cost,total_cost,
        source_type,source_id
      ) values
        (v_new_id,'OTHER','Latest source lot HPP carry-forward',r.qty_pcs,
          v_source_hpp,r.qty_pcs*v_source_hpp,'FG_LOT',r.source_lot_id),
        (v_new_id,'CONVERSION','Conversion/relabel cost',r.qty_pcs,
          r.conversion_cost_allocated/r.qty_pcs,r.conversion_cost_allocated,
          'PRODUCT_CONVERSION_ALLOCATION',r.id);
    end if;
  end loop;

  if exists(
    with recursive reachable(lot_id,path,depth) as(
      select fl.id,array[fl.id],0
      from erp.fg_lots fl
      where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
      union all
      select a.destination_lot_id,x.path||a.destination_lot_id,x.depth+1
      from reachable x
      join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
      join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
      where a.destination_lot_id is not null
        and not a.destination_lot_id=any(x.path) and x.depth<128
    )
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id and s.po_id=p_po_id
    join erp.fg_lots d on d.id=a.destination_lot_id
    where not exists(select 1 from reachable x where x.lot_id=a.destination_lot_id)
       or s.po_id is null or d.po_id is distinct from s.po_id
       or d.lot_origin<>'CONVERSION' or d.source_lot_id is distinct from s.id
       or a.qty_pcs<=0
  ) then
    raise exception 'CONVERSION_LINEAGE_ORPHAN_OR_CYCLE: PO % conversion graph is not rooted and acyclic',p_po_id;
  end if;
end
$function$;
alter function erp.propagate_conversion_hpp_for_po(uuid) owner to postgres;

-- Conversion is a value-preserving change of SKU.  It may consume only
-- PO-sourced lots until a separate non-PO source-accounting workflow exists.
create or replace function erp.post_product_conversion(p_conversion_id uuid)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  h erp.product_conversions%rowtype;
  r record;
  v_need integer;
  v_take integer;
  v_source_hpp numeric(18,6);
  v_dest_hpp numeric(18,6);
  v_dest_lot uuid;
  v_dest_lot_no text;
  v_source_value numeric(24,6):=0;
  v_lock_product uuid;
  v_po uuid;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into h from erp.product_conversions
  where id=p_conversion_id for update;
  if h.id is null or h.status<>'DRAFT' then
    raise exception 'Product conversion must be DRAFT';
  end if;
  if coalesce(h.conversion_cost_total,0)<>0 then
    raise exception 'Non-zero conversion cost requires a sourced accounting workflow; unsafe unsourced HPP capitalization is blocked';
  end if;

  perform erp.assert_product_identity_time(
    h.from_product_id,h.physical_at,'EXISTING_STOCK');
  perform erp.assert_product_identity_time(
    h.to_product_id,h.physical_at,'NEW_STOCK');

  -- Fail before the first new fact.  A mixed PO/non-PO FIFO pool is also
  -- rejected rather than silently attributing only part of the conversion.
  if exists(
    select 1
    from erp.fg_lots fl
    join erp.fg_stock_movements fm on fm.lot_id=fl.id
    where fl.product_id=h.from_product_id and fl.po_id is null
      and fm.location_id=h.location_id and fm.quality_grade='GRADE_A'
    group by fl.id
    having sum(fm.qty_signed)>0
  ) then
    raise exception 'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW';
  end if;

  insert into erp.fg_inventory_balances(
    product_id,location_id,quality_grade,cached_qty_pcs
  ) values(h.from_product_id,h.location_id,'GRADE_A',0)
  on conflict(product_id,location_id,quality_grade) do nothing;
  insert into erp.fg_inventory_balances(
    product_id,location_id,quality_grade,cached_qty_pcs
  ) values(h.to_product_id,h.location_id,'GRADE_A',0)
  on conflict(product_id,location_id,quality_grade) do nothing;
  for v_lock_product in
    select x from (values(h.from_product_id),(h.to_product_id)) v(x)
    group by x order by x
  loop
    perform 1 from erp.fg_inventory_balances
    where product_id=v_lock_product and location_id=h.location_id
      and quality_grade='GRADE_A' for update;
  end loop;

  v_need:=h.qty_pcs;
  delete from erp.product_conversion_allocations where conversion_id=h.id;
  for r in
    select fl.id,fl.po_id,fl.produced_at,
      sum(fm.qty_signed)::integer location_qty
    from erp.fg_lots fl
    join erp.fg_stock_movements fm on fm.lot_id=fl.id
    where fl.product_id=h.from_product_id and fl.po_id is not null
      and fm.location_id=h.location_id and fm.quality_grade='GRADE_A'
    group by fl.id,fl.po_id,fl.produced_at
    having sum(fm.qty_signed)>0
    order by fl.produced_at,fl.id
  loop
    exit when v_need<=0;
    v_take:=least(v_need,r.location_qty);
    perform 1 from erp.fg_lots where id=r.id for update;
    v_source_hpp:=coalesce(erp.lock_current_hpp_per_pcs(r.id),0);
    v_dest_hpp:=v_source_hpp;
    v_dest_lot_no:=h.conversion_number||'-'||substr(r.id::text,1,8)
      ||'-'||substr(gen_random_uuid()::text,1,6);
    insert into erp.fg_lots(
      lot_number,po_id,qc_item_id,product_id,initial_qty_pcs,cached_qty_pcs,
      produced_at,is_open,lot_origin,source_lot_id
    ) values(
      v_dest_lot_no,r.po_id,null,h.to_product_id,v_take,0,h.physical_at,
      true,'CONVERSION',r.id
    ) returning id into v_dest_lot;
    insert into erp.hpp_versions(
      lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,
      calculation_reason,created_by
    ) values(
      v_dest_lot,1,'ADJUSTED',v_take,v_take*v_dest_hpp,true,
      'SKU conversion/rebrand carry-forward',erp.current_app_user_id()
    );
    insert into erp.hpp_version_components(
      hpp_version_id,component_type,description,qty_basis,unit_cost,
      total_cost,source_type,source_id
    )
    select hv.id,'OTHER','HPP carried from source lot',v_take,
      v_source_hpp,v_take*v_source_hpp,'FG_LOT',r.id
    from erp.hpp_versions hv
    where hv.lot_id=v_dest_lot and hv.version_no=1;
    perform erp.post_fg_movement(
      h.from_product_id,r.id,h.location_id,'GRADE_A','REBRAND_OUT',-v_take,
      v_source_hpp,null,'PRODUCT_CONVERSION',h.id,h.physical_at,
      'SKU conversion OUT',false
    );
    perform erp.post_fg_movement(
      h.to_product_id,v_dest_lot,h.location_id,'GRADE_A','REBRAND_IN',v_take,
      v_dest_hpp,null,'PRODUCT_CONVERSION',h.id,h.physical_at,
      'SKU conversion IN',false
    );
    insert into erp.product_conversion_allocations(
      conversion_id,source_lot_id,destination_lot_id,qty_pcs,
      original_hpp_per_pcs,conversion_cost_allocated
    ) values(h.id,r.id,v_dest_lot,v_take,v_source_hpp,0);
    v_source_value:=v_source_value+(v_take*v_source_hpp);
    v_need:=v_need-v_take;
  end loop;
  if v_need>0 then
    raise exception 'Insufficient source stock for conversion; short % pcs',v_need;
  end if;

  update erp.product_conversions set status='POSTED' where id=h.id;
  if round(v_source_value,2)>0.005 then
    perform erp.post_journal(
      'PRODUCT_CONVERSION',h.id,h.physical_at::date,'SKU conversion/rebrand',
      jsonb_build_array(
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',
          round(v_source_value,2),'credit',0,'product_id',h.to_product_id),
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',
          round(v_source_value,2),'product_id',h.from_product_id)
      )
    );
  end if;

  for v_po in
    select distinct fl.po_id
    from erp.product_conversion_allocations a
    join erp.fg_lots fl on fl.id=a.source_lot_id
    where a.conversion_id=h.id order by fl.po_id
  loop
    perform erp.propagate_conversion_hpp_for_po(v_po);
    perform erp.refresh_po_hpp_gl_baseline(v_po);
    perform erp.assert_po_hpp_target_book_v2620e(v_po);
  end loop;
end
$function$;
alter function erp.post_product_conversion(uuid) owner to postgres;

-- Non-PO HPP is targeted cumulatively per immutable source lot.  Each lot's
-- rounded source value is conserved while FG/COGS/disposition are redistributed
-- from the complete active sale/return lifecycle, independent of document cuts.
create function erp.compute_non_po_product_hpp_targets_v2620f(p_product_id uuid)
returns table(
  hpp_total_cost numeric,fg_value numeric,cogs_value numeric,
  other_out_value numeric
)
language sql
stable
security definer
set search_path=''
as $function$
with lots as(
  select fl.id,
    coalesce(hv.total_cost,0)::numeric raw_total,
    case when coalesce(hv.qty_basis_pcs,0)>0
      then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric hpp_per_pcs
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
  where fl.product_id=p_product_id and fl.po_id is null
    and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
), balances as(
  select l.id,l.raw_total,l.hpp_per_pcs,
    (coalesce(sum(m.qty_signed),0)+coalesce(sum(abs(m.qty_signed)) filter(
      where m.movement_type='SALE_RESERVE' and not exists(
        select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id
      )),0))::numeric owned_qty
  from lots l
  left join erp.fg_stock_movements m on m.lot_id=l.id
  group by l.id,l.raw_total,l.hpp_per_pcs
), sold as(
  select a.lot_id,coalesce(sum(a.qty_pcs),0)::numeric qty
  from erp.sale_stock_allocations a
  join erp.sales_items i on i.id=a.sale_item_id
  join erp.sales_headers h on h.id=i.sale_id
  join lots l on l.id=a.lot_id
  where h.status in('POSTED','PARTIAL_PAID','PAID')
  group by a.lot_id
), returned as(
  select i.lot_id,coalesce(sum(i.qty_pcs),0)::numeric qty
  from erp.sales_return_items i
  join erp.sales_returns h on h.id=i.return_id
  join lots l on l.id=i.lot_id
  where h.status='POSTED'
  group by i.lot_id
), per_lot as(
  select b.id,round(b.raw_total,2)::numeric hpp,
    round(b.raw_total-greatest(b.owned_qty,0)*b.hpp_per_pcs,2)::numeric total_out,
    round(greatest(coalesce(s.qty,0)-coalesce(r.qty,0),0)
      *b.hpp_per_pcs,2)::numeric cogs
  from balances b
  left join sold s on s.lot_id=b.id
  left join returned r on r.lot_id=b.id
)
select coalesce(sum(hpp),0)::numeric,
  coalesce(sum(hpp-total_out),0)::numeric,
  coalesce(sum(cogs),0)::numeric,
  coalesce(sum(total_out-cogs),0)::numeric
from per_lot
$function$;
alter function erp.compute_non_po_product_hpp_targets_v2620f(uuid)
  owner to postgres;
revoke all on function erp.compute_non_po_product_hpp_targets_v2620f(uuid)
  from public,anon,authenticated,service_role;

create function erp.compute_non_po_product_hpp_book_v2620f(p_product_id uuid)
returns table(
  hpp_total_cost numeric,fg_value numeric,cogs_value numeric,
  other_out_value numeric
)
language sql
stable
security definer
set search_path=''
as $function$
with book as(
  select
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=erp.account_id('FG_INVENTORY')),0)::numeric fg,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=erp.account_id('COGS')),0)::numeric cogs,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id in(
        erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
      )),0)::numeric other_out
  from erp.journal_lines l
  join erp.journal_entries e on e.id=l.journal_entry_id
    and e.status in('POSTED','REVERSED')
  left join erp.journal_entries o on o.id=e.reversal_of_id
  where l.po_id is null and l.product_id=p_product_id
    and e.source_type<>'PRODUCT_CONVERSION'
    and not(e.source_type='JOURNAL_REVERSAL'
      and o.source_type='PRODUCT_CONVERSION')
)
select (fg+cogs+other_out)::numeric,fg,cogs,other_out from book
$function$;
alter function erp.compute_non_po_product_hpp_book_v2620f(uuid)
  owner to postgres;
revoke all on function erp.compute_non_po_product_hpp_book_v2620f(uuid)
  from public,anon,authenticated,service_role;

create function erp.assert_non_po_product_hpp_target_book_v2620f(
  p_product_id uuid
)
returns void
language plpgsql
stable
security definer
set search_path to 'erp','public'
as $function$
declare
  t record;
  b record;
begin
  perform erp.require_internal();
  if exists(
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id
    join erp.fg_lots d on d.id=a.destination_lot_id
    where(s.po_id is null or d.po_id is null)
      and(s.product_id=p_product_id or d.product_id=p_product_id)
  ) then
    raise exception 'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW';
  end if;
  select * into t
  from erp.compute_non_po_product_hpp_targets_v2620f(p_product_id);
  select * into b
  from erp.compute_non_po_product_hpp_book_v2620f(p_product_id);
  if abs(t.hpp_total_cost-b.hpp_total_cost)>0.005
     or abs(t.fg_value-b.fg_value)>0.005
     or abs(t.cogs_value-b.cogs_value)>0.005
     or abs(t.other_out_value-b.other_out_value)>0.005 then
    raise exception 'NON_PO_HPP_TARGET_BOOK_MISMATCH: product %, target hpp/fg/cogs/other %/%/%/%, book %/%/%/%',
      p_product_id,t.hpp_total_cost,t.fg_value,t.cogs_value,t.other_out_value,
      b.hpp_total_cost,b.fg_value,b.cogs_value,b.other_out_value;
  end if;
end
$function$;
alter function erp.assert_non_po_product_hpp_target_book_v2620f(uuid)
  owner to postgres;
revoke all on function erp.assert_non_po_product_hpp_target_book_v2620f(uuid)
  from public,anon,authenticated,service_role;

create function erp.sync_non_po_product_hpp_to_gl_v2620f(
  p_product_id uuid,
  p_effective_date date,
  p_trigger_source_type text,
  p_trigger_source_id uuid,
  p_reason text
)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  t record;
  b record;
  v_df numeric(20,2);
  v_dc numeric(20,2);
  v_do numeric(20,2);
  v_event uuid:=gen_random_uuid();
  v_journal uuid;
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  if nullif(btrim(p_trigger_source_type),'') is null
     or nullif(btrim(p_reason),'') is null then
    raise exception 'Non-PO HPP synchronization requires source and reason';
  end if;
  if exists(
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id
    join erp.fg_lots d on d.id=a.destination_lot_id
    where(s.po_id is null or d.po_id is null)
      and(s.product_id=p_product_id or d.product_id=p_product_id)
  ) then
    raise exception 'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW';
  end if;

  select * into t
  from erp.compute_non_po_product_hpp_targets_v2620f(p_product_id);
  select * into b
  from erp.compute_non_po_product_hpp_book_v2620f(p_product_id);
  if abs(t.hpp_total_cost-b.hpp_total_cost)>0.005 then
    raise exception 'NON_PO_HPP_SOURCE_VALUE_MISMATCH: product %, target total %, book total %',
      p_product_id,t.hpp_total_cost,b.hpp_total_cost;
  end if;

  v_df:=round(t.fg_value-b.fg_value,2);
  v_dc:=round(t.cogs_value-b.cogs_value,2);
  v_do:=round(t.other_out_value-b.other_out_value,2);
  if abs(v_df+v_dc+v_do)>0.005 then
    raise exception 'NON_PO_HPP_DELTA_NOT_CONSERVED: product %, fg %, cogs %, other %',
      p_product_id,v_df,v_dc,v_do;
  end if;
  if abs(v_df)<=0.005 and abs(v_dc)<=0.005 and abs(v_do)<=0.005 then
    return;
  end if;

  if abs(v_df)>0.005 then
    v_lines:=v_lines||jsonb_build_array(case when v_df>0
      then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_df,
        'credit',0,'product_id',p_product_id)
      else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,
        'credit',abs(v_df),'product_id',p_product_id) end);
  end if;
  if abs(v_dc)>0.005 then
    v_lines:=v_lines||jsonb_build_array(case when v_dc>0
      then jsonb_build_object('mapping_key','COGS','debit',v_dc,
        'credit',0,'product_id',p_product_id)
      else jsonb_build_object('mapping_key','COGS','debit',0,
        'credit',abs(v_dc),'product_id',p_product_id) end);
  end if;
  if abs(v_do)>0.005 then
    v_lines:=v_lines||jsonb_build_array(case when v_do>0
      then jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_do,
        'credit',0,'product_id',p_product_id)
      else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,
        'credit',abs(v_do),'product_id',p_product_id) end);
  end if;

  v_journal:=erp.post_journal(
    'NON_PO_HPP_GL_SYNC_V2620F',v_event,p_effective_date,
    'Cumulative non-PO HPP redistribution · '||p_reason,v_lines
  );
  insert into erp.non_po_hpp_gl_sync_events_v2620f(
    id,product_id,trigger_source_type,trigger_source_id,effective_date,
    old_fg_value,new_fg_value,fg_delta,
    old_cogs_value,new_cogs_value,cogs_delta,
    old_other_out_value,new_other_out_value,other_delta,
    journal_entry_id,reason,created_by
  ) values(
    v_event,p_product_id,p_trigger_source_type,p_trigger_source_id,
    p_effective_date,b.fg_value,t.fg_value,v_df,
    b.cogs_value,t.cogs_value,v_dc,
    b.other_out_value,t.other_out_value,v_do,
    v_journal,p_reason,erp.current_app_user_id()
  );
  perform erp.assert_non_po_product_hpp_target_book_v2620f(p_product_id);
end
$function$;
alter function erp.sync_non_po_product_hpp_to_gl_v2620f(
  uuid,date,text,uuid,text
) owner to postgres;
revoke all on function erp.sync_non_po_product_hpp_to_gl_v2620f(
  uuid,date,text,uuid,text
) from public,anon,authenticated,service_role;

-- The document writers still own the commercial journal, but their non-PO
-- HPP lines are now the delta between the global lot-lifecycle target and book.
do $patch_post_sale_v2620f$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.post_sale(uuid)'::regprocedure)
    into v_definition;

  v_anchor:=$anchor$  update erp.sale_stock_allocations a
  set unit_hpp_snapshot=coalesce(erp.lock_current_hpp_per_pcs(a.lot_id),0)$anchor$;
  v_replacement:=$replacement$  for r in
    select distinct fl.product_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  update erp.sale_stock_allocations a
  set unit_hpp_snapshot=coalesce(erp.lock_current_hpp_per_pcs(a.lot_id),0)$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale pre-assert anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  -- Opening and any future non-PO FG origin keeps its frozen transaction HPP.
  -- Cumulative slices conserve the exact rounded total across multiple lots.
  for r in
    with weights as(
      select fl.id lot_id,fl.product_id,
        sum(a.qty_pcs*a.unit_hpp_snapshot)::numeric raw_value
      from erp.sale_stock_allocations a
      join erp.sales_items i on i.id=a.sale_item_id
      join erp.fg_lots fl on fl.id=a.lot_id
      where i.sale_id=h.id and fl.po_id is null
      group by fl.id,fl.product_id
    ), ordered as(
      select w.*,
        sum(raw_value) over(order by lot_id rows unbounded preceding) cumulative_value
      from weights w
    )
    select product_id,
      round(cumulative_value,2)-round(cumulative_value-raw_value,2) hpp_value
    from ordered order by lot_id
  loop
    if abs(r.hpp_value)>0.005 then
      v_lines:=v_lines||jsonb_build_array(
        jsonb_build_object('mapping_key','COGS','debit',r.hpp_value,'credit',0,
          'customer_id',h.customer_id,'product_id',r.product_id),
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',r.hpp_value,
          'customer_id',h.customer_id,'product_id',r.product_id));
    end if;
  end loop;$anchor$;
  v_replacement:=$replacement$  -- One cumulative target per product, composed from per-lot lifecycle truth.
  for r in
    select distinct fl.product_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    select round(t.fg_value-b.fg_value,2),
      round(t.cogs_value-b.cogs_value,2),
      round(t.other_out_value-b.other_out_value,2)
    into v_delta_fg,v_delta_cogs,v_delta_other
    from erp.compute_non_po_product_hpp_targets_v2620f(r.product_id) t
    cross join lateral erp.compute_non_po_product_hpp_book_v2620f(r.product_id) b;
    if abs(v_delta_fg+v_delta_cogs+v_delta_other)>0.005 then
      raise exception 'Sale non-PO HPP delta does not conserve source value for product %: fg %, cogs %, other %',
        r.product_id,v_delta_fg,v_delta_cogs,v_delta_other;
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0
        then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,
          'credit',abs(v_delta_fg),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0
        then jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,
          'credit',abs(v_delta_cogs),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0
        then jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,
          'credit',abs(v_delta_other),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
  end loop;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale non-PO target anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALE',h.id,h.sale_date::date,
      'Sales to customer/toko · cumulative exact HPP target',v_lines);
  end if;

  for r in
    select distinct fl.po_id$anchor$;
  v_replacement:=$replacement$  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALE',h.id,h.sale_date::date,
      'Sales to customer/toko · cumulative exact HPP target',v_lines);
  end if;

  for r in
    select distinct fl.product_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  for r in
    select distinct fl.po_id$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale post-assert anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_post_sale_v2620f$;

do $patch_post_sales_return_v2620f$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.post_sales_return(uuid)'::regprocedure)
    into v_definition;

  v_anchor:=$anchor$  for r in
    select * from erp.sales_return_items where return_id=h.id
    order by product_id,location_id,quality_grade,lot_id,id
  loop$anchor$;
  v_replacement:=$replacement$  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  for r in
    select * from erp.sales_return_items where return_id=h.id
    order by product_id,location_id,quality_grade,lot_id,id
  loop$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return pre-assert anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  for r in
    with weights as(
      select fl.id lot_id,fl.product_id,
        sum(i.qty_pcs*i.unit_hpp_snapshot)::numeric raw_value
      from erp.sales_return_items i
      join erp.fg_lots fl on fl.id=i.lot_id
      where i.return_id=h.id and fl.po_id is null
      group by fl.id,fl.product_id
    ), ordered as(
      select w.*,
        sum(raw_value) over(order by lot_id rows unbounded preceding) cumulative_value
      from weights w
    )
    select product_id,
      round(cumulative_value,2)-round(cumulative_value-raw_value,2) hpp_value
    from ordered order by lot_id
  loop
    if abs(r.hpp_value)>0.005 then
      v_lines:=v_lines||jsonb_build_array(
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',r.hpp_value,'credit',0,
          'customer_id',h.customer_id,'product_id',r.product_id),
        jsonb_build_object('mapping_key','COGS','debit',0,'credit',r.hpp_value,
          'customer_id',h.customer_id,'product_id',r.product_id));
    end if;
  end loop;$anchor$;
  v_replacement:=$replacement$  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    select round(t.fg_value-b.fg_value,2),
      round(t.cogs_value-b.cogs_value,2),
      round(t.other_out_value-b.other_out_value,2)
    into v_delta_fg,v_delta_cogs,v_delta_other
    from erp.compute_non_po_product_hpp_targets_v2620f(r.product_id) t
    cross join lateral erp.compute_non_po_product_hpp_book_v2620f(r.product_id) b;
    if abs(v_delta_fg+v_delta_cogs+v_delta_other)>0.005 then
      raise exception 'Return non-PO HPP delta does not conserve source value for product %: fg %, cogs %, other %',
        r.product_id,v_delta_fg,v_delta_cogs,v_delta_other;
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0
        then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,
          'credit',abs(v_delta_fg),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0
        then jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,
          'credit',abs(v_delta_cogs),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0
        then jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,
          'credit',abs(v_delta_other),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
  end loop;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return non-PO target anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALES_RETURN',h.id,h.physical_at::date,
      'Sales return from customer · cumulative exact HPP target',v_lines);
  end if;

  update erp.sales_headers$anchor$;
  v_replacement:=$replacement$  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALES_RETURN',h.id,h.physical_at::date,
      'Sales return from customer · cumulative exact HPP target',v_lines);
  end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  update erp.sales_headers$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return post-assert anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_post_sales_return_v2620f$;

-- Reversal first compensates the immutable original document journal, then an
-- explicit sync event resolves the cumulative minor-unit remainder left by the
-- other still-active documents.  Both reversal orders therefore converge.
do $patch_reverse_sale_v2620f$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.reverse_sale(uuid,text)'::regprocedure)
    into v_definition;

  v_anchor:=$anchor$  select round(coalesce((select sum(line_total)
           from erp.sales_items where sale_id=h.id),0),2)
       +round(coalesce((select sum(a.qty_pcs*a.unit_hpp_snapshot)
          from erp.sale_stock_allocations a
          join erp.sales_items i on i.id=a.sale_item_id
          join erp.fg_lots fl on fl.id=a.lot_id
          where i.sale_id=h.id and fl.po_id is null),0),2)
  into v_expected;$anchor$;
  v_replacement:=$replacement$  for r in
    select distinct fl.product_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  -- HPP may legitimately have had zero document delta.  Global target/book
  -- proof above detects missing value; only commercial value requires a SALE journal.
  select round(coalesce((select sum(line_total)
           from erp.sales_items where sale_id=h.id),0),2)
  into v_expected;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale reversal pre-proof anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  update erp.sales_headers set status='REVERSED' where id=h.id;

  for v_po in$anchor$;
  v_replacement:=$replacement$  update erp.sales_headers set status='REVERSED' where id=h.id;

  for r in
    select distinct fl.product_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.sync_non_po_product_hpp_to_gl_v2620f(
      r.product_id,current_date,'SALE_REVERSAL',h.id,
      'Reverse Sale '||h.id::text||': '||p_reason
    );
  end loop;

  for v_po in$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale reversal sync anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_reverse_sale_v2620f$;

do $patch_reverse_sales_return_v2620f$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.reverse_sales_return(uuid,text)'::regprocedure)
    into v_definition;

  v_anchor:=$anchor$  select round(coalesce(sum(i.refund_amount),0),2)
       +round(coalesce(sum(i.qty_pcs*i.unit_hpp_snapshot)
          filter(where fl.po_id is null),0),2)
  into v_expected
  from erp.sales_return_items i
  join erp.fg_lots fl on fl.id=i.lot_id
  where i.return_id=h.id;$anchor$;
  v_replacement:=$replacement$  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  select round(coalesce(sum(i.refund_amount),0),2)
  into v_expected
  from erp.sales_return_items i
  where i.return_id=h.id;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return reversal pre-proof anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  update erp.sales_returns set status='REVERSED' where id=h.id;
  select erp.sale_net_total(s.id)::numeric(20,2) into v_total;$anchor$;
  v_replacement:=$replacement$  update erp.sales_returns set status='REVERSED' where id=h.id;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.sync_non_po_product_hpp_to_gl_v2620f(
      r.product_id,current_date,'SALES_RETURN_REVERSAL',h.id,
      'Reverse Sales return '||h.id::text||': '||p_reason
    );
  end loop;

  select erp.sale_net_total(s.id)::numeric(20,2) into v_total;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return reversal sync anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_reverse_sales_return_v2620f$;

do $patch_financial_checks_v2620f$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure)
    into v_definition;

  -- A commercial journal is mandatory for monetary value.  A sub-cent HPP
  -- document can legitimately have zero delta; the global target/book check
  -- below, rather than document-local rounding, proves its value.
  v_anchor:=$anchor$    and(round(coalesce((select sum(i.line_total) from erp.sales_items i
          where i.sale_id=h.id),0),2)>0.005
      or round(coalesce((select sum(a.qty_pcs*a.unit_hpp_snapshot)
          from erp.sale_stock_allocations a
          join erp.sales_items i on i.id=a.sale_item_id
          join erp.fg_lots fl on fl.id=a.lot_id
          where i.sale_id=h.id and fl.po_id is null),0),2)>0.005)$anchor$;
  v_replacement:=$replacement$    and round(coalesce((select sum(i.line_total) from erp.sales_items i
          where i.sale_id=h.id),0),2)>0.005$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: active Sale journal check anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    and(round(coalesce((select sum(i.refund_amount)
          from erp.sales_return_items i where i.return_id=h.id),0),2)>0.005
      or round(coalesce((select sum(i.qty_pcs*i.unit_hpp_snapshot)
          from erp.sales_return_items i
          join erp.fg_lots fl on fl.id=i.lot_id
          where i.return_id=h.id and fl.po_id is null),0),2)>0.005)$anchor$;
  v_replacement:=$replacement$    and round(coalesce((select sum(i.refund_amount)
          from erp.sales_return_items i where i.return_id=h.id),0),2)>0.005$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: posted return journal check anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  select 'V2620E_NON_PO_SALE_HPP_BOOK_MISMATCH','CRITICAL',count(*)::bigint,
    'Opening/non-PO Sale and return HPP must move the exact frozen rounded amount between FG and COGS'
  from(
    select h.id,
      round(coalesce((select sum(a.qty_pcs*a.unit_hpp_snapshot)
        from erp.sale_stock_allocations a
        join erp.sales_items i on i.id=a.sale_item_id
        join erp.fg_lots fl on fl.id=a.lot_id
        where i.sale_id=h.id and fl.po_id is null),0),2) expected_cogs,
      coalesce((select sum(l.debit-l.credit)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_type='SALE' and j.source_id=h.id and j.status='POSTED'
          and l.account_id=erp.account_id('COGS') and l.po_id is null),0) actual_cogs,
      coalesce((select sum(l.debit-l.credit)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_type='SALE' and j.source_id=h.id and j.status='POSTED'
          and l.account_id=erp.account_id('FG_INVENTORY') and l.po_id is null),0) actual_fg
    from erp.sales_headers h where h.status in('POSTED','PARTIAL_PAID','PAID')
    union all
    select h.id,
      -round(coalesce((select sum(i.qty_pcs*i.unit_hpp_snapshot)
        from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
        where i.return_id=h.id and fl.po_id is null),0),2),
      coalesce((select sum(l.debit-l.credit)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_type='SALES_RETURN' and j.source_id=h.id and j.status='POSTED'
          and l.account_id=erp.account_id('COGS') and l.po_id is null),0),
      coalesce((select sum(l.debit-l.credit)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_type='SALES_RETURN' and j.source_id=h.id and j.status='POSTED'
          and l.account_id=erp.account_id('FG_INVENTORY') and l.po_id is null),0)
    from erp.sales_returns h where h.status='POSTED'
  ) non_po
  where abs(non_po.actual_cogs-non_po.expected_cogs)>0.005
     or abs(non_po.actual_fg+non_po.expected_cogs)>0.005$anchor$;
  v_replacement:=$replacement$  select 'V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH','CRITICAL',count(*)::bigint,
    'Each non-PO product book must equal cumulative per-lot minor-unit HPP targets across every active Sale, return, correction, and reversal'
  from(
    select distinct fl.product_id
    from erp.fg_lots fl
    where fl.po_id is null
      and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
  ) p
  cross join lateral erp.compute_non_po_product_hpp_targets_v2620f(p.product_id) t
  cross join lateral erp.compute_non_po_product_hpp_book_v2620f(p.product_id) b
  where abs(t.hpp_total_cost-b.hpp_total_cost)>0.005
     or abs(t.fg_value-b.fg_value)>0.005
     or abs(t.cogs_value-b.cogs_value)>0.005
     or abs(t.other_out_value-b.other_out_value)>0.005$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: non-PO report target anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  -- Financial reversal of the failed-wash receipt must not erase the separate,
  -- immutable Laundry-to-Sewing custody fact.
  v_anchor:=$anchor$join erp.laundry_receipts fr on fr.id=f.receipt_id and fr.status='POSTED'$anchor$;
  v_replacement:=$replacement$join erp.laundry_receipts fr on fr.id=f.receipt_id
           and fr.status in('POSTED','REVERSED')
         join erp.wip_stage_events rv on rv.id=f.return_wip_event_id
           and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
           and rv.stage_from='LAUNDRY' and rv.stage_to='SEWING'
           and rv.qty_pcs=f.qty_attempted_pcs
         join erp.wip_stage_events src on src.id=rv.source_id
           and src.source_type='LAUNDRY_DELIVERY_LINE'
           and src.source_id=sx.delivery_line_id
         join erp.laundry_delivery_lines fdl on fdl.id=src.source_id
           and fdl.delivery_id=f.delivery_id
           and rv.po_id=sd.po_id
           and rv.cutting_group_id=fdl.cutting_group_id$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>2 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: redispatch custody receipt anchors are not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:='and fr.physical_at<=dd.physical_at';
  v_replacement:='and fr.physical_at<=dd.physical_at and rv.physical_at<=dd.physical_at';
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>2 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: redispatch custody time anchors are not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  union all
  select 'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH','CRITICAL',count(*)::bigint,$anchor$;
  v_replacement:=$replacement$  union all
  select 'V2620F_CONVERSION_VALUE_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Every posted conversion must be PO-sourced, value-preserving, rooted, and represented by exact OUT/IN facts with current descendant HPP'
  from erp.product_conversion_allocations a
  join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
  join erp.fg_lots s on s.id=a.source_lot_id
  left join erp.fg_lots d on d.id=a.destination_lot_id
  left join erp.v_current_hpp sh on sh.lot_id=s.id
  left join erp.v_current_hpp dh on dh.lot_id=d.id
  where s.po_id is null or d.id is null or d.po_id is distinct from s.po_id
     or d.lot_origin<>'CONVERSION' or d.source_lot_id is distinct from s.id
     or d.initial_qty_pcs is distinct from a.qty_pcs or a.qty_pcs<=0
     or sh.hpp_per_pcs is null or dh.hpp_per_pcs is null
     or abs(dh.hpp_per_pcs-(sh.hpp_per_pcs
       +a.conversion_cost_allocated/nullif(a.qty_pcs,0)))>0.000001
     or (select count(*) from erp.fg_stock_movements m
         where m.source_type='PRODUCT_CONVERSION' and m.source_id=c.id
           and m.lot_id=s.id and m.movement_type='REBRAND_OUT'
           and m.qty_signed=-a.qty_pcs)<>1
     or (select count(*) from erp.fg_stock_movements m
         where m.source_type='PRODUCT_CONVERSION' and m.source_id=c.id
           and m.lot_id=d.id and m.movement_type='REBRAND_IN'
           and m.qty_signed=a.qty_pcs)<>1

  union all
  select 'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH','CRITICAL',count(*)::bigint,$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))
       /length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: conversion report insertion anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_financial_checks_v2620f$;

-- Reconcile existing immutable facts through the same public writers used at
-- runtime.  No historical journal, movement, allocation, or receipt is edited.
do $reconcile_existing_v2620f$
declare
  r record;
begin
  if exists(
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id
    join erp.fg_lots d on d.id=a.destination_lot_id
    where s.po_id is null or d.po_id is null
  ) then
    raise exception 'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW: migration cannot classify historical non-PO conversion value safely';
  end if;

  for r in
    select distinct s.po_id
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id
    where s.po_id is not null order by s.po_id
  loop
    perform erp.propagate_conversion_hpp_for_po(r.po_id);
    -- E's refresh reads the actual book; sync then moves it to F's target.
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.sync_po_hpp_to_gl(r.po_id,current_date);
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.assert_po_hpp_target_book_v2620e(r.po_id);
  end loop;

  for r in
    select distinct fl.product_id
    from erp.fg_lots fl
    where fl.po_id is null
      and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
    order by fl.product_id
  loop
    perform erp.sync_non_po_product_hpp_to_gl_v2620f(
      r.product_id,current_date,'V2620F_MIGRATION',null,
      'Forward-only reconciliation of cumulative non-PO minor-unit targets'
    );
  end loop;
end
$reconcile_existing_v2620f$;

do $installed_guard_v2620f$
declare
  v_issue_count bigint;
begin
  if not(select c.relrowsecurity from pg_class c
      where c.oid='erp.cp6_v2620f_rollback_capsule'::regclass)
     or not(select c.relrowsecurity from pg_class c
      where c.oid='erp.non_po_hpp_gl_sync_events_v2620f'::regclass)
     or exists(select 1 from pg_policy p where p.polrelid in(
       'erp.cp6_v2620f_rollback_capsule'::regclass,
       'erp.non_po_hpp_gl_sync_events_v2620f'::regclass
     ))
     or exists(
       select 1 from information_schema.role_table_grants g
       where g.table_schema='erp'
         and g.table_name in(
           'cp6_v2620f_rollback_capsule','non_po_hpp_gl_sync_events_v2620f'
         )
         and g.grantee in('PUBLIC','anon','authenticated','service_role')
     )
     or (select count(*) from pg_trigger t
       where not t.tgisinternal
         and t.tgrelid='erp.non_po_hpp_gl_sync_events_v2620f'::regclass
         and t.tgname='trg_guard_non_po_hpp_gl_sync_event_v2620f')<>1
     or position($needle$'CONVERSION'$needle$ in pg_get_functiondef(
       'erp.compute_po_hpp_gl_targets_v2620d(uuid)'::regprocedure))=0
     or position('Root-to-leaf propagated source HPP' in pg_get_functiondef(
       'erp.propagate_conversion_hpp_for_po(uuid)'::regprocedure))=0
     or position('NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW' in
       pg_get_functiondef('erp.post_product_conversion(uuid)'::regprocedure))=0
     or position('compute_non_po_product_hpp_targets_v2620f' in
       pg_get_functiondef('erp.post_sale(uuid)'::regprocedure))=0
     or position('sync_non_po_product_hpp_to_gl_v2620f' in
       pg_get_functiondef('erp.reverse_sale(uuid,text)'::regprocedure))=0
     or position('V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH' in
       pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure))=0
     or position($needle$fr.status in('POSTED','REVERSED')$needle$ in
       pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure))=0
     or exists(
       select 1 from (values
         ('erp.guard_non_po_hpp_gl_sync_event_v2620f()'),
         ('erp.compute_non_po_product_hpp_targets_v2620f(uuid)'),
         ('erp.compute_non_po_product_hpp_book_v2620f(uuid)'),
         ('erp.assert_non_po_product_hpp_target_book_v2620f(uuid)'),
         ('erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)')
       ) f(identity)
       cross join (values('anon'),('authenticated'),('service_role')) r(role_name)
       where has_function_privilege(r.role_name,f.identity,'EXECUTE')
     ) then
    raise exception 'ERP v2.6.20f did not install privately and completely';
  end if;

  select coalesce(sum(c.issue_count),0)::bigint into v_issue_count
  from erp.run_v268_financial_report_checks() c
  where c.check_name in(
    'V2620C_PO_HPP_TARGET_STATE_MISMATCH',
    'V2620C_PO_HPP_BOOK_MISMATCH',
    'V2620C_WIP_SOURCE_CONSERVATION_MISMATCH',
    'V2620C_HPP_COMPONENT_SUM_MISMATCH',
    'V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH',
    'V2620E_SALES_RETURN_VALUE_EXCEEDS_SALE',
    'V2620E_OPENING_HPP_LINEAGE_MISMATCH',
    'V2620E_OPENING_FG_GL_MISMATCH',
    'V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH',
    'V2620E_REDISPATCH_EVENT_MISMATCH',
    'V2620F_CONVERSION_VALUE_LINEAGE_MISMATCH'
  );
  if v_issue_count<>0 then
    raise exception 'ERP v2.6.20f targeted reconciliation still has % issue(s)',
      v_issue_count;
  end if;

  update erp.cp6_v2620f_rollback_capsule c
  set installed_definition_sha256=encode(extensions.digest(convert_to(
    pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
  ),'sha256'),'hex');
  if (select count(*) from erp.cp6_v2620f_rollback_capsule
      where installed_definition_sha256 is not null)<>8 then
    raise exception 'ERP v2.6.20f installed-definition capsule is incomplete';
  end if;
end
$installed_guard_v2620f$;

comment on table erp.non_po_hpp_gl_sync_events_v2620f is
  'Private append-only evidence for cumulative non-PO FG/COGS/disposition minor-unit redistribution after correction or reversal.';
comment on function erp.compute_po_hpp_gl_targets_v2620d(uuid) is
  'PO target: source value from production roots; ownership and disposition include every active conversion descendant.';
comment on function erp.compute_non_po_product_hpp_targets_v2620f(uuid) is
  'Cumulative non-PO HPP target, conserved at minor-unit precision per immutable source lot across split documents.';
comment on function erp.sync_non_po_product_hpp_to_gl_v2620f(
  uuid,date,text,uuid,text
) is
  'Append-only reconciler for non-PO cumulative HPP targets after lifecycle corrections and reversals.';

insert into erp.schema_migrations(version,description)
values(
  'v2.6.20f',
  'CP6 A01-A04 closure: conversion-descendant value, cumulative non-PO minor units, custody-safe financial reversal, and final-runtime proof gate'
);

commit;
