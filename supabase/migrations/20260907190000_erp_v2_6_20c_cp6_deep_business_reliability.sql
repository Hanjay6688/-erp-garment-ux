-- ERP Garment v2.6.20c / CP6 deep-business reliability repair.
--
-- Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.
-- Forward-only: recorded predecessor bytes and posted business history are never edited.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';

lock table erp.schema_migrations,
  supabase_migrations.schema_migrations,
  erp.audit_logs,
  erp.fg_lots,
  erp.fg_stock_movements,
  erp.hpp_versions,
  erp.hpp_version_components,
  erp.po_hpp_gl_state,
  erp.sales_headers,
  erp.sales_items,
  erp.sale_stock_allocations,
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

do $guard$
declare
  v_actual text;
  v_platform_match_count integer;
  r record;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20b') then
    raise exception 'ERP v2.6.20c requires immutable v2.6.20b first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20c') then
    raise exception 'ERP v2.6.20c is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.cp6_v2620c_rollback_capsule') is not null
     or to_regprocedure('erp.cp6_lot_work_cost_v2620c(uuid,text)') is not null
     or to_regprocedure('erp.cp6_lot_attendance_cost_v2620c(uuid)') is not null
     or to_regprocedure('erp.cp6_lot_failed_wash_cost_v2620c(uuid)') is not null
     or to_regprocedure('erp.cp6_lot_rework_cost_v2620c(uuid)') is not null
     or to_regprocedure('erp.cp6_po_source_qty_v2620c(uuid)') is not null
     or to_regprocedure('erp.search_laundry_bs_products_v2620c(uuid,timestamp with time zone,text,text,integer)') is not null
     or to_regprocedure('public.erp_search_laundry_bs_products_v1(uuid,timestamp with time zone,text,text,integer)') is not null then
    raise exception 'ERP v2.6.20c target guard: prior repair residue exists';
  end if;
  if exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'ERP v2.6.20c refuses installation while a CP6 execution context exists';
  end if;

  select count(*) into v_platform_match_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20b_cp6_reaudit_reliability_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'fedd509515694fb8f03d90ebccfcc260c8e13f0784d589d04f61b9ece8d2ed25',
      '67c2b8eeb4a473c20a6ac312b863ef8f3b7eccf2a6d8805e921b3996e9eca406'
    );
  if v_platform_match_count<>1 then
    raise exception 'ERP v2.6.20c requires one exact v2.6.20b platform-ledger row; found %',
      v_platform_match_count;
  end if;

  for r in select * from (values
    ('erp._release_sale_draft_reservations(uuid,text)','f76c65655360dd1f90986b8ba3df082362e9d3653bee5ecd4df744c52f8c19a7'),
    ('erp._reserve_sale_draft(uuid)','bc78c9734e0421ee8cda23b158e14c5c1344142b7b39a11becadb3cc95252a36'),
    ('erp.save_sale_draft_v2(jsonb,uuid,bigint)','53343ef8eac4bebfdaa73cefd42cecd42998e4c17f74e643a2d039e428ae78a6'),
    ('erp.cancel_sale_draft_v2(uuid,text,uuid,bigint)','5e73ea052aaf59c222eb45a3be99b89e76bb60c9c191a3637b21b07d67907a0e'),
    ('erp.compute_po_hpp_gl_targets(uuid)','5fd2261072c18dfc8e6da63902320672b89d28caeb52e5c83b562626277845c9'),
    ('erp.get_owner_financial_snapshot_v2(date,date,date)','7bc51c721e14552ee690eb23388d1a3ced04fbc3137d989d6a7115eedfb6ff37'),
    ('erp.post_sale(uuid)','9b1cbb28a7c22677e96cf58001b3b903321f53562083fd09805ece98fa37f7aa'),
    ('erp.post_sale_v2(uuid,uuid,bigint)','646321185c214fe26b7f843c76702b25d74425c0807f87b80ea80dd7990d09bb'),
    ('erp.post_vendor_payment(uuid)','1a153ba0dcfb3cbeec1ee52c977c855c375fe26b2f22aed58f3e986cebf1ec63'),
    ('erp.rebuild_po_hpp(uuid,text)','488a682df22fe4be03dca7d8b251e95716e6a5312ed63e15d1d079ff008407b2'),
    ('erp.refresh_po_hpp_gl_baseline(uuid)','c91f70fb7ef8102b38ec2707e72eb6940a17f0ad6b34780f992e95152ec72d52'),
    ('erp.reverse_sale(uuid,text)','9c2dfee8fd50ba433b890bbd778ac2efdff1be0b0e750bbc4924e1e30fb83eef'),
    ('erp.reverse_vendor_payment(uuid,text)','95d55907ace413137a0082efeeb39d2add38862b726330f1e2ed8b5918d4683f'),
    ('erp.run_v268_financial_report_checks()','4a3149d78a0f6f3f9f1645d867de9f8ed8386cac4fb64bd139c22f24a0e0c264'),
    ('erp.sync_po_hpp_to_gl(uuid,date)','7a1d80d1e1f45d3812ce8ebef8b61c1704241ffc44e87793c28a0f83675ca327')
  ) expected(object_identity,sha256)
  loop
    if to_regprocedure(r.object_identity) is null then
      raise exception 'ERP v2.6.20c predecessor function is missing: %',r.object_identity;
    end if;
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.object_identity)),'UTF8'
    ),'sha256'),'hex') into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: % changed (%)',r.object_identity,v_actual;
    end if;
  end loop;
end
$guard$;

create table erp.cp6_v2620c_rollback_capsule(
  object_identity text primary key,
  object_regidentity text not null unique,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.cp6_v2620c_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620c_rollback_capsule
  from public,anon,authenticated,service_role;

insert into erp.cp6_v2620c_rollback_capsule(
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
  'erp._release_sale_draft_reservations(uuid,text)'::regprocedure,
  'erp._reserve_sale_draft(uuid)'::regprocedure,
  'erp.save_sale_draft_v2(jsonb,uuid,bigint)'::regprocedure,
  'erp.cancel_sale_draft_v2(uuid,text,uuid,bigint)'::regprocedure,
  'erp.compute_po_hpp_gl_targets(uuid)'::regprocedure,
  'erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure,
  'erp.post_sale(uuid)'::regprocedure,
  'erp.post_sale_v2(uuid,uuid,bigint)'::regprocedure,
  'erp.post_vendor_payment(uuid)'::regprocedure,
  'erp.rebuild_po_hpp(uuid,text)'::regprocedure,
  'erp.refresh_po_hpp_gl_baseline(uuid)'::regprocedure,
  'erp.reverse_sale(uuid,text)'::regprocedure,
  'erp.reverse_vendor_payment(uuid,text)'::regprocedure,
  'erp.run_v268_financial_report_checks()'::regprocedure,
  'erp.sync_po_hpp_to_gl(uuid,date)'::regprocedure
);

do $capsule_guard$
begin
  if (select count(*) from erp.cp6_v2620c_rollback_capsule)<>15
     or exists(
       select 1 from erp.cp6_v2620c_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
     ) then
    raise exception 'ERP v2.6.20c exact rollback capsule is incomplete or corrupt';
  end if;
end
$capsule_guard$;

-- Four older capsules were already private by ACL. RLS now makes that
-- deny-by-default boundary explicit as well; no browser/service policies exist.
alter table erp.cp3_r4_rollback_capsule enable row level security;
alter table erp.cp4_v2616_rollback_capsule enable row level security;
alter table erp.cp45_v2617_rollback_capsule enable row level security;
alter table erp.cp45_v2617a_rollback_capsule enable row level security;
revoke all on table erp.cp3_r4_rollback_capsule,
  erp.cp4_v2616_rollback_capsule,
  erp.cp45_v2617_rollback_capsule,
  erp.cp45_v2617a_rollback_capsule
from public,anon,authenticated,service_role;

create function erp.cp6_po_source_qty_v2620c(p_po_id uuid)
returns numeric
language sql
stable
security definer
set search_path=''
as $function$
  select greatest(
    coalesce((select po.target_qty_pcs::numeric from erp.production_orders po where po.id=p_po_id),0),
    coalesce((select sum(v.total_pcs)::numeric
      from erp.v_cutting_group_totals v
      join erp.cutting_groups g on g.id=v.cutting_group_id
      where g.po_id=p_po_id),0),
    coalesce((select sum(fl.initial_qty_pcs)::numeric
      from erp.fg_lots fl
      where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'),0)
  )
$function$;
alter function erp.cp6_po_source_qty_v2620c(uuid) owner to postgres;
revoke all on function erp.cp6_po_source_qty_v2620c(uuid)
  from public,anon,authenticated,service_role;

create function erp.cp6_lot_work_cost_v2620c(p_lot_id uuid,p_category text)
returns numeric
language sql
stable
security definer
set search_path=''
as $function$
with target as(
  select fl.id,fl.po_id,coalesce(fl.cutting_group_id,qi.cutting_group_id) group_id,
    fl.initial_qty_pcs::numeric lot_qty,fl.produced_at
  from erp.fg_lots fl
  left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
  where fl.id=p_lot_id and fl.lot_origin='PRODUCTION'
), position as(
  select t.*,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      left join erp.qc_inspection_items xqi on xqi.id=x.qc_item_id
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and coalesce(x.cutting_group_id,xqi.cutting_group_id)=t.group_id
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) group_start,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) po_start
  from target t
), source_lines as(
  select wce.cutting_group_id,wc.component_category,wcl.qty_completed::numeric source_qty,
    wcl.amount_payable::numeric source_cost,
    coalesce(sum(wcl.qty_completed) over(
      partition by wce.po_id,wce.cutting_group_id,wcl.work_component_id
      order by wce.physical_at,wce.id,wcl.id rows between unbounded preceding and 1 preceding
    ),0)::numeric source_start
  from position p
  join erp.work_completion_events wce on wce.po_id=p.po_id and wce.status='POSTED'
  join erp.work_completion_lines wcl on wcl.completion_id=wce.id
  join erp.work_components wc on wc.id=wcl.work_component_id
  where wc.component_category=case when upper(p_category)='COMMISSION' then 'COMMISSION' else wc.component_category end
    and (upper(p_category)='COMMISSION' or wc.component_category<>'COMMISSION')
    and (wce.cutting_group_id=p.group_id or wce.cutting_group_id is null)
)
select coalesce(sum(
  greatest(least(
    case when s.cutting_group_id is null then p.po_start+p.lot_qty else p.group_start+p.lot_qty end,
    s.source_start+s.source_qty
  )-greatest(
    case when s.cutting_group_id is null then p.po_start else p.group_start end,
    s.source_start
  ),0)*s.source_cost/nullif(s.source_qty,0)
),0)::numeric
from position p left join source_lines s on true
$function$;
alter function erp.cp6_lot_work_cost_v2620c(uuid,text) owner to postgres;
revoke all on function erp.cp6_lot_work_cost_v2620c(uuid,text)
  from public,anon,authenticated,service_role;

create function erp.cp6_lot_attendance_cost_v2620c(p_lot_id uuid)
returns numeric
language sql
stable
security definer
set search_path=''
as $function$
with target as(
  select fl.id,fl.po_id,coalesce(fl.cutting_group_id,qi.cutting_group_id) group_id,
    fl.initial_qty_pcs::numeric lot_qty,fl.produced_at
  from erp.fg_lots fl
  left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
  where fl.id=p_lot_id and fl.lot_origin='PRODUCTION'
), position as(
  select t.*,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      left join erp.qc_inspection_items xqi on xqi.id=x.qc_item_id
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and coalesce(x.cutting_group_id,xqi.cutting_group_id)=t.group_id
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) group_start,
    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x
      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'
        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) po_start
  from target t
), terminal as(
  select e.id,e.po_id,e.cutting_group_id,e.qty_signed::numeric event_qty,
    coalesce(sum(e.qty_signed) over(
      partition by e.po_id,e.cutting_group_id
      order by e.physical_at,e.id rows between unbounded preceding and 1 preceding
    ),0)::numeric group_start,
    coalesce(sum(e.qty_signed) over(
      partition by e.po_id
      order by e.physical_at,e.id rows between unbounded preceding and 1 preceding
    ),0)::numeric po_start
  from erp.sewing_terminal_events e join position p on p.po_id=e.po_id
  where e.event_kind='SELESAI_DIJAHIT' and e.qty_signed>0
    and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id)
), alloc as(
  select a.cutting_group_id,a.sewing_qty::numeric source_qty,a.allocated_amount::numeric source_cost,
    case when a.cutting_group_id is null then t.po_start else t.group_start end source_start
  from position p
  join erp.attendance_hpp_pool_allocations a on a.po_id=p.po_id
    and (a.cutting_group_id=p.group_id or a.cutting_group_id is null)
  join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
  join terminal t on t.id=a.sewing_terminal_event_id
)
select coalesce(sum(
  greatest(least(
    case when a.cutting_group_id is null then p.po_start+p.lot_qty else p.group_start+p.lot_qty end,
    a.source_start+a.source_qty
  )-greatest(
    case when a.cutting_group_id is null then p.po_start else p.group_start end,
    a.source_start
  ),0)*a.source_cost/nullif(a.source_qty,0)
),0)::numeric
from position p left join alloc a on true
$function$;
alter function erp.cp6_lot_attendance_cost_v2620c(uuid) owner to postgres;
revoke all on function erp.cp6_lot_attendance_cost_v2620c(uuid)
  from public,anon,authenticated,service_role;

create function erp.cp6_lot_failed_wash_cost_v2620c(p_lot_id uuid)
returns numeric
language sql
stable
security definer
set search_path=''
as $function$
with lot_source as(
  select fl.initial_qty_pcs::numeric lot_qty,rx.id receipt_batch_size_id,
    rx.delivery_batch_size_line_id,rx.qty_good_received::numeric+rx.qty_bs_laundry::numeric receipt_qty,
    rh.physical_at receipt_at,rh.id receipt_id
  from erp.fg_lots fl
  join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
  join erp.laundry_receipt_batch_size_lines rx on rx.id=qi.source_laundry_receipt_batch_size_line_id
  join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
    and rl.id=qi.source_laundry_receipt_line_id
  join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
  where fl.id=p_lot_id and fl.lot_origin='PRODUCTION'
), receipt_interval as(
  select s.*,coalesce((
    select sum(px.qty_good_received+px.qty_bs_laundry)::numeric
    from erp.laundry_receipt_batch_size_lines px
    join erp.laundry_receipt_lines pl on pl.id=px.receipt_line_id
    join erp.laundry_receipts ph on ph.id=pl.receipt_id and ph.status='POSTED'
    where px.delivery_batch_size_line_id=s.delivery_batch_size_line_id
      and (ph.physical_at,ph.id,px.id)<(s.receipt_at,s.receipt_id,s.receipt_batch_size_id)
  ),0) receipt_start
  from lot_source s
), attempts as(
  select ax.delivery_batch_size_line_id,ax.qty_attempted_pcs::numeric attempt_qty,
    coalesce(rl.actual_cost,a.qty_attempted_pcs*coalesce(rl.actual_rate_snapshot,0))
      *(ax.qty_attempted_pcs::numeric/nullif(a.qty_attempted_pcs,0)) size_cost,
    coalesce((
      select sum(px.qty_good_received+px.qty_bs_laundry)::numeric
      from erp.laundry_receipt_batch_size_lines px
      join erp.laundry_receipt_lines pl on pl.id=px.receipt_line_id
      join erp.laundry_receipts ph on ph.id=pl.receipt_id and ph.status='POSTED'
      where px.delivery_batch_size_line_id=ax.delivery_batch_size_line_id
        and (ph.physical_at,ph.id)<(ah.physical_at,ah.id)
    ),0) attempt_start
  from receipt_interval s
  join erp.laundry_failed_wash_batch_size_lines ax
    on ax.delivery_batch_size_line_id=s.delivery_batch_size_line_id
  join erp.laundry_failed_wash_attempts a on a.id=ax.attempt_id
  join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
    and rl.actual_cost_status in('ESTIMATED','FINAL')
  join erp.laundry_receipts ah on ah.id=a.receipt_id and ah.status='POSTED'
)
select coalesce(sum(
  greatest(least(s.receipt_start+s.receipt_qty,a.attempt_start+a.attempt_qty)
    -greatest(s.receipt_start,a.attempt_start),0)
  *a.size_cost/nullif(a.attempt_qty,0)
  *s.lot_qty/nullif(s.receipt_qty,0)
),0)::numeric
from receipt_interval s left join attempts a on true
$function$;
alter function erp.cp6_lot_failed_wash_cost_v2620c(uuid) owner to postgres;
revoke all on function erp.cp6_lot_failed_wash_cost_v2620c(uuid)
  from public,anon,authenticated,service_role;

create function erp.cp6_lot_rework_cost_v2620c(p_lot_id uuid)
returns numeric
language sql
stable
security definer
set search_path=''
as $function$
  select coalesce(sum(rcl.amount_payable::numeric*fl.initial_qty_pcs/nullif(ro.qty_sent,0)),0)::numeric
  from erp.fg_lots fl
  join erp.rework_orders ro on ro.good_fg_lot_id=fl.id
    and ro.status<>'CANCELLED' and ro.cost_posted=true
  join erp.rework_component_lines rcl on rcl.rework_order_id=ro.id
  where fl.id=p_lot_id and fl.lot_origin='PRODUCTION'
$function$;
alter function erp.cp6_lot_rework_cost_v2620c(uuid) owner to postgres;
revoke all on function erp.cp6_lot_rework_cost_v2620c(uuid)
  from public,anon,authenticated,service_role;

-- Laundry-BS gets the same source-bound, effective-time, keyset-paged resolver
-- that Final-SKU already has. The exact delivery-size line is the authority.
create function erp.search_laundry_bs_products_v2620c(
  p_delivery_batch_size_line_id uuid,
  p_physical_at timestamptz,
  p_query text default null,
  p_after_sort_key text default null,
  p_limit integer default 50
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
declare
  v_query text:=lower(nullif(btrim(p_query),''));
  v_model_id uuid;
  v_size_id uuid;
  v_rows jsonb;
  v_has_more boolean:=false;
  v_next_cursor text;
begin
  perform erp.require_permission('production.laundry.view');
  if p_delivery_batch_size_line_id is null or p_physical_at is null then
    raise exception 'Exact Laundry delivery-size source and timezone-qualified physical time are required';
  end if;
  if p_limit is null or p_limit<1 or p_limit>100 then
    raise exception 'Laundry-BS product search page limit must be between 1 and 100';
  end if;
  if p_physical_at>statement_timestamp()+interval '5 minutes' then
    raise exception 'Laundry-BS product search time cannot be more than five minutes in the future';
  end if;

  select po.model_id,sx.size_id into v_model_id,v_size_id
  from erp.laundry_delivery_batch_size_lines sx
  join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
  join erp.laundry_deliveries d on d.id=dl.delivery_id
    and d.status in('SENT','PARTIAL_RETURN') and d.physical_at<=p_physical_at
  join erp.cutting_groups g on g.id=dl.cutting_group_id and g.po_id=d.po_id
  join erp.production_orders po on po.id=g.po_id
  where sx.id=p_delivery_batch_size_line_id
    and sx.qty_sent_pcs>coalesce((
      select sum(rx.qty_good_received+rx.qty_bs_laundry)
      from erp.laundry_receipt_batch_size_lines rx
      join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
      join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
      where rx.delivery_batch_size_line_id=sx.id
    ),0);
  if v_model_id is null or v_size_id is null then
    raise exception 'Laundry-BS product search source is no longer an authoritative outstanding delivery-size row';
  end if;

  with candidates as(
    select p.id,p.sku,p.product_name name,p.model_id,
      m.model_code,m.model_name,p.brand_id,b.brand_code,b.brand_name,
      p.size_id,s.size_code,s.sort_order size_sort,p.color_name color,
      p.effective_from,p.effective_to,
      lower(b.brand_name)||E'\x1f'||lower(p.sku)||E'\x1f'||
        lower(m.model_name)||E'\x1f'||lower(p.color_name)||E'\x1f'||
        lpad(s.sort_order::text,10,'0')||E'\x1f'||p.id::text sort_key
    from erp.products p
    join erp.product_models m on m.id=p.model_id and m.is_active
    join erp.brands b on b.id=p.brand_id and b.is_active
    join erp.sizes s on s.id=p.size_id and s.is_active
    where p.is_active and p.is_portal_visible
      and p.model_id=v_model_id and p.size_id=v_size_id
      and p.effective_from<=p_physical_at
      and(p.effective_to is null or p.effective_to>p_physical_at)
      and(v_query is null or lower(concat_ws(' ',
        b.brand_code,b.brand_name,p.sku,p.product_name,m.model_code,
        m.model_name,p.color_name,s.size_code
      )) like '%'||v_query||'%')
  ), page as(
    select * from candidates
    where p_after_sort_key is null or sort_key>p_after_sort_key
    order by sort_key limit p_limit+1
  ), numbered as(
    select page.*,row_number() over(order by sort_key) row_no from page
  )
  select coalesce(jsonb_agg(to_jsonb(numbered)-'size_sort'-'sort_key'-'row_no'
           order by sort_key) filter(where row_no<=p_limit),'[]'::jsonb),
         count(*)>p_limit,
         max(sort_key) filter(where row_no<=p_limit)
  into v_rows,v_has_more,v_next_cursor
  from numbered;

  return jsonb_build_object(
    'contract_version','CP6_LAUNDRY_BS_PRODUCT_SEARCH_V2620C',
    'source_delivery_batch_size_line_id',p_delivery_batch_size_line_id,
    'physical_at',p_physical_at,'query',v_query,'page_limit',p_limit,
    'products',v_rows,'has_more',v_has_more,
    'next_cursor',case when v_has_more then v_next_cursor else null end
  );
end
$function$;
alter function erp.search_laundry_bs_products_v2620c(uuid,timestamptz,text,text,integer)
  owner to postgres;
revoke all on function erp.search_laundry_bs_products_v2620c(uuid,timestamptz,text,text,integer)
  from public,anon,authenticated,service_role;

create function public.erp_search_laundry_bs_products_v1(
  p_delivery_batch_size_line_id uuid,
  p_physical_at timestamptz,
  p_query text default null,
  p_after_sort_key text default null,
  p_limit integer default 50
)
returns jsonb
language plpgsql
stable
security definer
set search_path=''
as $function$
begin
  return erp.search_laundry_bs_products_v2620c(
    p_delivery_batch_size_line_id,p_physical_at,p_query,p_after_sort_key,p_limit
  );
end
$function$;
alter function public.erp_search_laundry_bs_products_v1(uuid,timestamptz,text,text,integer)
  owner to postgres;
revoke all on function public.erp_search_laundry_bs_products_v1(uuid,timestamptz,text,text,integer)
  from public,anon,authenticated,service_role;
grant execute on function public.erp_search_laundry_bs_products_v1(uuid,timestamptz,text,text,integer)
  to authenticated,service_role;

-- Rebuild keeps the predecessor transaction/append-only mechanics, but
-- replaces every current-FG denominator with immutable physical source
-- intervals. Unfinished source cost therefore stays in WIP.
do $patch_hpp_source_ownership$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.rebuild_po_hpp(uuid,text)'::regprocedure)
    into v_definition;

  v_anchor:=$anchor$  v_laundry_allocated numeric(24,6):=0;$anchor$;
  v_replacement:=$replacement$  v_laundry_allocated numeric(24,6):=0;
  v_labor_allocated numeric(24,6):=0;
  v_commission_allocated numeric(24,6):=0;
  v_rework_allocated numeric(24,6):=0;
  v_attendance_allocated numeric(24,6):=0;
  v_po_source_qty numeric(24,6):=0;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP allocation declaration anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  perform erp.require_internal();
  -- Serialize all HPP rebuilds for the same PO (cron recost, late invoice, QC, reversal).
  perform pg_advisory_xact_lock(hashtextextended('PO_HPP:'||p_po_id::text,0));$anchor$;
  v_replacement:=$replacement$  perform erp.require_internal();
  -- One lock order covers Draft reservation, post/reversal, late recost, and GL sync.
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform pg_advisory_xact_lock(hashtextextended('PO_HPP:'||p_po_id::text,0));$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP lock anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  select coalesce(sum(initial_qty_pcs),0) into v_total_qty
  from erp.fg_lots where po_id=p_po_id and lot_origin='PRODUCTION';
  if v_total_qty<=0 then return; end if;$anchor$;
  v_replacement:=$replacement$  select coalesce(sum(initial_qty_pcs),0) into v_total_qty
  from erp.fg_lots where po_id=p_po_id and lot_origin='PRODUCTION';
  if v_total_qty<=0 then return; end if;
  v_po_source_qty:=erp.cp6_po_source_qty_v2620c(p_po_id);
  if coalesce(v_po_source_qty,0)<=0 then
    raise exception 'PO source quantity is required before HPP can be allocated';
  end if;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP source-quantity anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$      with lot_source as(
        select sx.distribution_batch_id,rx.size_id
        from erp.qc_inspection_items qi
        join erp.laundry_receipt_batch_size_lines rx
          on rx.id=qi.source_laundry_receipt_batch_size_line_id
        join erp.laundry_delivery_batch_size_lines sx
          on sx.id=rx.delivery_batch_size_line_id
        where qi.id=r.qc_item_id
      ), attempt_size_cost as(
        select a.id,sx.distribution_batch_id,ax.size_id,
          coalesce(rl.actual_cost,a.qty_attempted_pcs*coalesce(rl.actual_rate_snapshot,0))
            *(ax.qty_attempted_pcs::numeric/nullif(a.qty_attempted_pcs,0)) size_cost
        from erp.laundry_failed_wash_attempts a
        join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
        join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
          and rl.actual_cost_status in('ESTIMATED','FINAL')
        join erp.laundry_failed_wash_batch_size_lines ax on ax.attempt_id=a.id
        join erp.laundry_delivery_batch_size_lines sx
          on sx.id=ax.delivery_batch_size_line_id
      ), applicable as(
        select ac.id,ac.size_cost,ls.distribution_batch_id,ls.size_id
        from lot_source ls
        join attempt_size_cost ac
          on ac.distribution_batch_id=ls.distribution_batch_id and ac.size_id=ls.size_id
      ), capacity as(
        select ap.id,ap.size_cost,coalesce(sum(a.qty_pcs),0)::numeric capacity_qty
        from applicable ap
        join erp.cutting_distribution_allocations a
          on a.batch_id=ap.distribution_batch_id
        join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
        join erp.cutting_group_size_slots s
          on s.id=y.size_slot_id and s.size_id=ap.size_id
        group by ap.id,ap.size_cost
      )
      select coalesce(sum(cp6_capacity.size_cost*r.initial_qty_pcs/nullif(cp6_capacity.capacity_qty,0)),0)
      into v_lot_cp6_attempt_laundry from capacity cp6_capacity;$anchor$;
  v_replacement:=$replacement$      select erp.cp6_lot_failed_wash_cost_v2620c(r.id)
      into v_lot_cp6_attempt_laundry;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: failed-wash allocation anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    v_lot_material:=v_lot_material+v_contractor_material*(r.initial_qty_pcs::numeric/v_total_qty::numeric);$anchor$;
  v_replacement:=$replacement$    v_lot_material:=v_lot_material+v_contractor_material*(r.initial_qty_pcs::numeric/v_po_source_qty);$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: contractor-material allocation anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    if coalesce(v_group_fg_qty,0)>0 then
      v_lot_labor:=v_group_labor*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_labor*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_commission:=v_group_commission*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_commission*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_laundry:=case when v_cp6_lineage
        then v_lot_cp6_receipt_laundry+v_lot_cp6_attempt_laundry
        else v_group_laundry*(r.initial_qty_pcs::numeric/v_group_fg_qty) end;
      v_lot_rework:=v_group_rework*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_rework*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_attendance_hpp:=v_group_attendance_hpp*(r.initial_qty_pcs::numeric/v_group_fg_qty)+v_shared_attendance_hpp*(r.initial_qty_pcs::numeric/v_total_qty);
    else
      v_lot_labor:=v_labor*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_commission:=v_commission*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_laundry:=v_laundry*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_rework:=v_rework*(r.initial_qty_pcs::numeric/v_total_qty);
      v_lot_attendance_hpp:=v_shared_attendance_hpp*(r.initial_qty_pcs::numeric/v_total_qty);
    end if;$anchor$;
  v_replacement:=$replacement$    v_lot_labor:=erp.cp6_lot_work_cost_v2620c(r.id,'LABOR');
    v_lot_commission:=erp.cp6_lot_work_cost_v2620c(r.id,'COMMISSION');
    v_lot_laundry:=case when v_cp6_lineage
      then v_lot_cp6_receipt_laundry+v_lot_cp6_attempt_laundry
      when r.lineage_group_id is not null then v_group_laundry*(r.initial_qty_pcs::numeric/nullif(
        coalesce((select total_pcs::numeric from erp.v_cutting_group_totals
          where cutting_group_id=r.lineage_group_id),v_po_source_qty),0))
      else v_laundry*(r.initial_qty_pcs::numeric/v_po_source_qty) end;
    v_lot_rework:=erp.cp6_lot_rework_cost_v2620c(r.id);
    v_lot_attendance_hpp:=erp.cp6_lot_attendance_cost_v2620c(r.id);$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: nonmaterial allocation anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    v_lot_other:=v_lot_other+v_shared_other*(r.initial_qty_pcs::numeric/v_total_qty);
    v_laundry_allocated:=v_laundry_allocated+v_lot_laundry;$anchor$;
  v_replacement:=$replacement$    v_lot_other:=v_lot_other+v_shared_other*(r.initial_qty_pcs::numeric/v_po_source_qty);
    v_laundry_allocated:=v_laundry_allocated+v_lot_laundry;
    v_labor_allocated:=v_labor_allocated+v_lot_labor;
    v_commission_allocated:=v_commission_allocated+v_lot_commission;
    v_rework_allocated:=v_rework_allocated+v_lot_rework;
    v_attendance_allocated:=v_attendance_allocated+v_lot_attendance_hpp;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: shared-cost conservation anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  if v_laundry_allocated < -0.005 or v_laundry_allocated > v_laundry+0.005 then$anchor$;
  v_replacement:=$replacement$  if v_labor_allocated < -0.005 or v_labor_allocated > v_labor+0.005
     or v_commission_allocated < -0.005 or v_commission_allocated > v_commission+0.005
     or v_rework_allocated < -0.005 or v_rework_allocated > v_rework+0.005
     or v_attendance_allocated < -0.005 or v_attendance_allocated > v_attendance_hpp+0.005 then
    raise exception 'CP6 source-owned HPP allocation violates cost conservation: labor %/%, commission %/%, rework %/%, attendance %/%',
      v_labor_allocated,v_labor,v_commission_allocated,v_commission,
      v_rework_allocated,v_rework,v_attendance_allocated,v_attendance_hpp;
  end if;

  if v_laundry_allocated < -0.005 or v_laundry_allocated > v_laundry+0.005 then$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP conservation guard anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    'laundry_remaining_in_wip',v_laundry-v_laundry_allocated,
    'laundry_basis','CP6_EXACT_RECEIPT_BATCH_SIZE_LINEAGE_WITH_LEGACY_FALLBACK',$anchor$;
  v_replacement:=$replacement$    'laundry_remaining_in_wip',v_laundry-v_laundry_allocated,
    'labor_allocated_to_fg',v_labor_allocated,'labor_remaining_in_wip',v_labor-v_labor_allocated,
    'commission_allocated_to_fg',v_commission_allocated,'commission_remaining_in_wip',v_commission-v_commission_allocated,
    'rework_allocated_to_fg',v_rework_allocated,'rework_remaining_in_wip',v_rework-v_rework_allocated,
    'attendance_allocated_to_fg',v_attendance_allocated,'attendance_remaining_in_wip',v_attendance_hpp-v_attendance_allocated,
    'po_physical_source_qty',v_po_source_qty,
    'laundry_basis','CP6_EXACT_DELIVERY_SIZE_CUSTODY_INTERVAL_V2620C',$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP audit evidence anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_definition:=replace(v_definition,
    'Labor allocation: same cutting group + PO-shared fallback',
    'Labor allocation: immutable component completion intervals; unfinished remains WIP');
  v_definition:=replace(v_definition,
    'Commission allocation: same cutting group + PO-shared fallback',
    'Commission allocation: immutable component completion intervals; unfinished remains WIP');
  v_definition:=replace(v_definition,
    'Rework allocation from same cutting group + legacy shared fallback',
    'Rework allocation: exact good rework lot and qty-sent source');
  v_definition:=replace(v_definition,
    'Attendance HPP: ACTIVE pool allocation by immutable sewing lineage',
    'Attendance HPP: ACTIVE source sewing intervals; unfinished remains WIP');
  execute v_definition;
end
$patch_hpp_source_ownership$;

create or replace function erp.compute_po_hpp_gl_targets(p_po_id uuid)
returns table(base_output_qty integer,hpp_total_cost numeric,fg_value numeric,cogs_value numeric,other_out_value numeric)
language sql
stable
security definer
set search_path to 'erp','public'
as $function$
with base as(
  select coalesce(sum(fl.initial_qty_pcs),0)::integer qty,
         coalesce(sum(hv.total_cost),0)::numeric total
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current=true
  where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
), lot_hpp as(
  select fl.id lot_id,
    case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric hpp_per_pcs
  from erp.fg_lots fl
  left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current=true
  where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
), lot_balance as(
  select lh.lot_id,lh.hpp_per_pcs,
    (coalesce(sum(fm.qty_signed),0)+coalesce(sum(abs(fm.qty_signed)) filter(
      where fm.movement_type='SALE_RESERVE'
        and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)
    ),0))::numeric qty
  from lot_hpp lh left join erp.fg_stock_movements fm on fm.lot_id=lh.lot_id
  group by lh.lot_id,lh.hpp_per_pcs
), sold as(
  select a.lot_id,coalesce(sum(a.qty_pcs),0)::numeric qty
  from erp.sale_stock_allocations a
  join erp.sales_items si on si.id=a.sale_item_id
  join erp.sales_headers sh on sh.id=si.sale_id
  join erp.fg_lots fl on fl.id=a.lot_id
  where fl.po_id=p_po_id and sh.status in('POSTED','PARTIAL_PAID','PAID')
  group by a.lot_id
), returned as(
  select sri.lot_id,coalesce(sum(sri.qty_pcs),0)::numeric qty
  from erp.sales_return_items sri
  join erp.sales_returns sr on sr.id=sri.return_id
  join erp.fg_lots fl on fl.id=sri.lot_id
  where fl.po_id=p_po_id and sr.status='POSTED'
  group by sri.lot_id
), vals as(
  select
    coalesce((select sum(greatest(lb.qty,0)*lb.hpp_per_pcs) from lot_balance lb),0)::numeric fg_val,
    coalesce((select sum(greatest(coalesce(s.qty,0)-coalesce(r.qty,0),0)*lh.hpp_per_pcs)
      from lot_hpp lh left join sold s on s.lot_id=lh.lot_id
      left join returned r on r.lot_id=lh.lot_id),0)::numeric cogs_val
)
select base.qty,base.total,vals.fg_val,vals.cogs_val,
  (base.total-vals.fg_val-vals.cogs_val)::numeric
from base,vals
$function$;
alter function erp.compute_po_hpp_gl_targets(uuid) owner to postgres;

-- Every path that can classify or reserve FG uses one advisory lock order.
-- This closes the native race between a late HPP rebuild and sale post/cancel.
do $patch_sales_lock_order$
declare
  r record;
  v_definition text;
  v_anchor text:=$anchor$  perform erp.require_internal();$anchor$;
  v_replacement text:=$replacement$  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));$replacement$;
begin
  for r in select unnest(array[
    'erp._release_sale_draft_reservations(uuid,text)',
    'erp._reserve_sale_draft(uuid)',
    'erp.save_sale_draft_v2(jsonb,uuid,bigint)',
    'erp.cancel_sale_draft_v2(uuid,text,uuid,bigint)',
    'erp.post_sale_v2(uuid,uuid,bigint)'
  ]) object_identity
  loop
    select pg_get_functiondef(to_regprocedure(r.object_identity)) into v_definition;
    if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: sale lock anchor is not exact for %',r.object_identity;
    end if;
    execute replace(v_definition,v_anchor,v_replacement);
  end loop;

  select pg_get_functiondef('erp.reverse_sale(uuid,text)'::regprocedure) into v_definition;
  v_anchor:=$anchor$  perform erp.require_owner_admin();$anchor$;
  v_replacement:=$replacement$  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: sale reversal lock anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);
  v_anchor:=$anchor$    select coalesce(sum(a.qty_pcs*a.unit_hpp_snapshot),0)
    into v_reversal_hpp$anchor$;
  v_replacement:=$replacement$    select round(coalesce(sum(a.qty_pcs*a.unit_hpp_snapshot),0),2)
    into v_reversal_hpp$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: sale reversal minor-unit anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_sales_lock_order$;

create or replace function erp.post_sale(p_sale_id uuid)
returns void
language plpgsql
security definer
set search_path to 'erp','public','pg_temp'
as $function$
declare
  h erp.sales_headers%rowtype;
  r record;
  v_sales numeric(24,6):=0;
  v_cogs numeric(24,6):=0;
  v_item_qty bigint;
  v_reserved_qty bigint;
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into h from erp.sales_headers where id=p_sale_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Sale must be DRAFT'; end if;
  if h.source_location_id is null then raise exception 'Sale source FG location is required'; end if;
  if not exists(select 1 from erp.sales_items where sale_id=p_sale_id) then raise exception 'Sale has no items'; end if;

  select coalesce(sum(qty_pcs),0),coalesce(sum(line_total),0)
  into v_item_qty,v_sales from erp.sales_items where sale_id=h.id;
  select coalesce(sum(abs(m.qty_signed)),0) into v_reserved_qty
  from erp.fg_stock_movements m
  join erp.sales_items i on i.id=m.source_id
  where i.sale_id=h.id and m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);

  if v_reserved_qty=0 then v_reserved_qty:=erp._reserve_sale_draft(h.id); end if;
  if v_reserved_qty<>v_item_qty then
    raise exception 'Sale Draft reservation mismatch. Items %, active reservation %',v_item_qty,v_reserved_qty;
  end if;
  if exists(
    select 1 from erp.sales_items i
    left join(select sale_item_id,sum(qty_pcs)::bigint qty_pcs
      from erp.sale_stock_allocations group by sale_item_id) a on a.sale_item_id=i.id
    where i.sale_id=h.id and coalesce(a.qty_pcs,0)<>i.qty_pcs
  ) then raise exception 'Sale allocation does not match Draft line quantity'; end if;

  -- A Draft reserves physical sellable quantity, not a historical value.
  -- Freeze the latest authoritative HPP only at POST, in the same lock/transaction.
  update erp.sale_stock_allocations a
  set unit_hpp_snapshot=coalesce(erp.lock_current_hpp_per_pcs(a.lot_id),0)
  from erp.sales_items i
  where i.id=a.sale_item_id and i.sale_id=h.id;

  update erp.fg_stock_movements m
  set unit_hpp_snapshot=a.unit_hpp_snapshot
  from erp.sales_items i
  join erp.sale_stock_allocations a on a.sale_item_id=i.id
  where i.id=m.source_id and i.sale_id=h.id
    and a.lot_id=m.lot_id
    and m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);

  select coalesce(sum(a.qty_pcs*a.unit_hpp_snapshot),0) into v_cogs
  from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
  where i.sale_id=h.id;

  update erp.fg_stock_movements m
  set movement_type='SALE',notes='Sale posted · quantity reserved in Draft; HPP frozen at POST'
  from erp.sales_items i
  where i.id=m.source_id and i.sale_id=h.id
    and m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);

  update erp.sales_headers set status='POSTED' where id=h.id;
  if abs(v_sales)>0.005 then
    v_lines:=v_lines||jsonb_build_array(
      jsonb_build_object('mapping_key','AR_CUSTOMER','debit',round(v_sales,2),'credit',0,'customer_id',h.customer_id),
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',0,'credit',round(v_sales,2),'customer_id',h.customer_id));
  end if;
  for r in
    select fl.po_id,round(sum(a.qty_pcs*a.unit_hpp_snapshot),2) cogs
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id
    group by fl.po_id order by fl.po_id
  loop
    if abs(r.cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(
        jsonb_build_object('mapping_key','COGS','debit',r.cogs,'credit',0,'customer_id',h.customer_id,'po_id',r.po_id),
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',r.cogs,'customer_id',h.customer_id,'po_id',r.po_id));
    end if;
  end loop;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALE',h.id,h.sale_date::date,'Sales to customer/toko',v_lines);
  end if;
end
$function$;
alter function erp.post_sale(uuid) owner to postgres;

create or replace function erp.refresh_po_hpp_gl_baseline(p_po_id uuid)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  t record;
  v_documented_gain numeric(24,6):=0;
  v_hpp numeric(24,6);v_fg numeric(24,6);v_cogs numeric(24,6);v_other numeric(24,6);
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into t from erp.compute_po_hpp_gl_targets(p_po_id);
  if t.base_output_qty is null or t.base_output_qty<=0 then return; end if;

  with lot_hpp as(
    select fl.id lot_id,case when coalesce(hv.qty_basis_pcs,0)>0
      then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric hpp_per_pcs
    from erp.fg_lots fl left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current=true
    where fl.po_id=p_po_id
  ), adj_net as(
    select fm.lot_id,sum(fm.qty_signed)::numeric qty
    from erp.fg_stock_movements fm join erp.fg_lots fl on fl.id=fm.lot_id
    where fl.po_id=p_po_id and(
      (fm.movement_type='ADJUSTMENT' and fm.source_type='FG_ADJUSTMENT_ITEM')
      or(fm.movement_type='REVERSAL' and exists(
        select 1 from erp.fg_stock_movements orig where orig.id=fm.reversal_of_id
          and orig.movement_type='ADJUSTMENT' and orig.source_type='FG_ADJUSTMENT_ITEM')))
    group by fm.lot_id
  )
  select coalesce(sum(greatest(a.qty,0)*lh.hpp_per_pcs),0) into v_documented_gain
  from adj_net a join lot_hpp lh on lh.lot_id=a.lot_id;
  if t.other_out_value < -v_documented_gain-0.01 then
    raise exception 'PO HPP allocation inconsistent: financial FG + net sold exceeds production output without a documented positive FG adjustment';
  end if;

  v_hpp:=round(coalesce(t.hpp_total_cost,0),2);
  v_fg:=round(coalesce(t.fg_value,0),2);
  v_cogs:=round(coalesce(t.cogs_value,0),2);
  v_other:=v_hpp-v_fg-v_cogs;
  insert into erp.po_hpp_gl_state(po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,updated_at)
  values(p_po_id,t.base_output_qty,v_hpp,v_fg,v_cogs,v_other,now())
  on conflict(po_id) do update set base_output_qty=excluded.base_output_qty,
    hpp_total_cost=excluded.hpp_total_cost,fg_value=excluded.fg_value,
    cogs_value=excluded.cogs_value,other_out_value=excluded.other_out_value,updated_at=now();
end
$function$;
alter function erp.refresh_po_hpp_gl_baseline(uuid) owner to postgres;

create or replace function erp.sync_po_hpp_to_gl(p_po_id uuid,p_effective_date date default current_date)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  t record;
  s erp.po_hpp_gl_state%rowtype;
  v_target_qty integer:=0;
  v_target_hpp numeric(24,6):=0;
  v_target_fg numeric(24,6):=0;
  v_target_cogs numeric(24,6):=0;
  v_target_other numeric(24,6):=0;
  v_df numeric(24,6);v_dc numeric(24,6);v_do numeric(24,6);v_sum numeric(24,6);
  v_lines jsonb:='[]'::jsonb;v_event uuid;v_journal uuid;v_documented_gain numeric(24,6):=0;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into t from erp.compute_po_hpp_gl_targets(p_po_id);
  select * into s from erp.po_hpp_gl_state where po_id=p_po_id for update;

  if coalesce(t.base_output_qty,0)>0 then
    v_target_qty:=t.base_output_qty;
    -- Cumulative targets, deltas, journal lines, and saved state all use the
    -- same minor-unit values. The balancing bucket receives the deterministic remainder.
    v_target_hpp:=round(coalesce(t.hpp_total_cost,0),2);
    v_target_fg:=round(coalesce(t.fg_value,0),2);
    v_target_cogs:=round(coalesce(t.cogs_value,0),2);
    v_target_other:=v_target_hpp-v_target_fg-v_target_cogs;

    with lot_hpp as(
      select fl.id lot_id,case when coalesce(hv.qty_basis_pcs,0)>0
        then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric hpp_per_pcs
      from erp.fg_lots fl left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current=true
      where fl.po_id=p_po_id and fl.lot_origin<>'VOIDED_PRODUCTION'
    ), adj_net as(
      select fm.lot_id,sum(fm.qty_signed)::numeric qty
      from erp.fg_stock_movements fm join erp.fg_lots fl on fl.id=fm.lot_id
      where fl.po_id=p_po_id and fl.lot_origin<>'VOIDED_PRODUCTION'
        and((fm.movement_type='ADJUSTMENT' and fm.source_type='FG_ADJUSTMENT_ITEM')
          or(fm.movement_type='REVERSAL' and exists(
            select 1 from erp.fg_stock_movements orig where orig.id=fm.reversal_of_id
              and orig.movement_type='ADJUSTMENT' and orig.source_type='FG_ADJUSTMENT_ITEM')))
      group by fm.lot_id
    )
    select coalesce(sum(greatest(a.qty,0)*lh.hpp_per_pcs),0) into v_documented_gain
    from adj_net a join lot_hpp lh on lh.lot_id=a.lot_id;
    if v_target_other < -v_documented_gain-0.01 then
      raise exception 'PO HPP allocation inconsistent: financial FG + net sold exceeds production output without a matching documented positive FG adjustment';
    end if;
  else
    v_target_qty:=0;v_target_hpp:=0;v_target_fg:=0;v_target_cogs:=0;v_target_other:=0;
    if s.po_id is null then return; end if;
  end if;

  v_df:=v_target_fg-round(coalesce(s.fg_value,0),2);
  v_dc:=v_target_cogs-round(coalesce(s.cogs_value,0),2);
  v_do:=v_target_other-round(coalesce(s.other_out_value,0),2);
  v_sum:=v_df+v_dc+v_do;

  if abs(v_df)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_df>0
    then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_df,'credit',0,'po_id',p_po_id)
    else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(v_df),'po_id',p_po_id) end); end if;
  if abs(v_dc)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_dc>0
    then jsonb_build_object('mapping_key','COGS','debit',v_dc,'credit',0,'po_id',p_po_id)
    else jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_dc),'po_id',p_po_id) end); end if;
  if abs(v_do)>0.005 then
    if v_do>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','OTHER_EXPENSE','debit',v_do,'credit',0,'po_id',p_po_id));
    else v_lines:=v_lines||jsonb_build_array(jsonb_build_object(
      'mapping_key','OTHER_INCOME','debit',0,'credit',abs(v_do),'po_id',p_po_id)); end if;
  end if;
  if abs(v_sum)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_sum>0
    then jsonb_build_object('mapping_key','WIP','debit',0,'credit',v_sum,'po_id',p_po_id)
    else jsonb_build_object('mapping_key','WIP','debit',abs(v_sum),'credit',0,'po_id',p_po_id) end); end if;

  if jsonb_array_length(v_lines)>=2 then
    insert into erp.po_hpp_gl_events(po_id,effective_date,old_hpp_total,new_hpp_total,fg_delta,cogs_delta,other_delta)
    values(p_po_id,p_effective_date,round(coalesce(s.hpp_total_cost,0),2),v_target_hpp,v_df,v_dc,v_do)
    returning id into v_event;
    v_journal:=erp.post_journal('PO_HPP_GL_SYNC',v_event,p_effective_date,
      'Latest corrected HPP allocation · exact minor-unit targets',v_lines);
    update erp.po_hpp_gl_events set journal_entry_id=v_journal where id=v_event;
  end if;

  insert into erp.po_hpp_gl_state(po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,updated_at)
  values(p_po_id,v_target_qty,v_target_hpp,v_target_fg,v_target_cogs,v_target_other,now())
  on conflict(po_id) do update set base_output_qty=excluded.base_output_qty,
    hpp_total_cost=excluded.hpp_total_cost,fg_value=excluded.fg_value,
    cogs_value=excluded.cogs_value,other_out_value=excluded.other_out_value,updated_at=now();
end
$function$;
alter function erp.sync_po_hpp_to_gl(uuid,date) owner to postgres;

create or replace function erp.post_vendor_payment(p_payment_id uuid)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  p erp.vendor_payments%rowtype;h erp.vendor_invoices%rowtype;
  v_cash uuid;v_paid numeric(20,2);
begin
  perform erp.require_internal();
  select * into p from erp.vendor_payments where id=p_payment_id for update;
  if p.id is null or p.status<>'DRAFT' then raise exception 'Vendor payment must be DRAFT'; end if;
  select * into h from erp.vendor_invoices where id=p.vendor_invoice_id for update;
  if h.status not in('POSTED','PARTIAL_PAID') then
    raise exception 'Vendor invoice must be posted and still unpaid';
  end if;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid
  from erp.vendor_payments where vendor_invoice_id=h.id and status='POSTED';
  if v_paid+p.amount>h.total_amount then
    raise exception 'Vendor payment exceeds exact remaining payable. Invoice total %, already paid %, requested %',
      h.total_amount,v_paid,p.amount;
  end if;
  select coa_account_id into v_cash from erp.cash_accounts
  where id=p.cash_account_id and is_active=true;
  if v_cash is null then raise exception 'Active cash/bank account is required'; end if;
  perform erp.post_journal('VENDOR_PAYMENT',p.id,p.payment_date::date,'Laundry vendor payment',jsonb_build_array(
    jsonb_build_object('mapping_key','AP_VENDOR','debit',p.amount,'credit',0,'vendor_id',h.vendor_id),
    jsonb_build_object('account_id',v_cash,'debit',0,'credit',p.amount,'vendor_id',h.vendor_id)));
  update erp.vendor_payments set status='POSTED' where id=p.id;
  v_paid:=v_paid+p.amount;
  update erp.vendor_invoices set status=case when v_paid=total_amount then 'PAID' else 'PARTIAL_PAID' end
  where id=h.id;
end
$function$;
alter function erp.post_vendor_payment(uuid) owner to postgres;

create or replace function erp.reverse_vendor_payment(p_payment_id uuid,p_reason text)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  p erp.vendor_payments%rowtype;h erp.vendor_invoices%rowtype;
  v_journal uuid;v_paid numeric(20,2);
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then
    raise exception 'Alasan reversal pembayaran vendor laundry wajib diisi';
  end if;
  select * into p from erp.vendor_payments where id=p_payment_id for update;
  if p.id is null then raise exception 'Pembayaran vendor laundry tidak ditemukan'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status<>'POSTED' then
    raise exception 'Hanya pembayaran vendor laundry yang sudah POSTED yang dapat direverse';
  end if;
  select * into h from erp.vendor_invoices where id=p.vendor_invoice_id for update;
  if h.id is null then raise exception 'Invoice vendor laundry sumber pembayaran tidak ditemukan'; end if;
  select id into v_journal from erp.journal_entries
  where source_type='VENDOR_PAYMENT' and source_id=p.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_journal is null then
    raise exception 'Jurnal pembayaran vendor laundry tidak ditemukan; reversal dibatalkan agar kas/hutang tidak rusak';
  end if;
  perform erp.reverse_journal(v_journal,p_reason);
  update erp.vendor_payments set status='REVERSED' where id=p.id;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid
  from erp.vendor_payments where vendor_invoice_id=h.id and status='POSTED';
  update erp.vendor_invoices set status=case
    when v_paid=h.total_amount then 'PAID'
    when v_paid>0 then 'PARTIAL_PAID' else 'POSTED' end where id=h.id;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('vendor_payments',p.id,'REVERSE',erp.current_app_user_id(),p_reason);
end
$function$;
alter function erp.reverse_vendor_payment(uuid,text) owner to postgres;

create or replace function erp.run_v268_financial_report_checks()
returns table(check_name text,severity text,issue_count bigint,details text)
language plpgsql
stable
security definer
set search_path to 'erp','public','pg_catalog','information_schema','pg_temp'
as $function$
begin
  perform erp.require_owner_admin();
  return query
  select r.check_name,r.severity,r.issue_count,r.details
  from erp._v268_financial_report_checks_pre_scope() r
  where r.check_name not in(
    'V268_BROWSER_DIRECT_FINANCIAL_WRITE',
    'V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE'
  )

  union all
  select 'V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE','CRITICAL',count(*)::bigint,
    'Browser roles must not directly mutate ledger or supplier-invoice aggregates'
  from information_schema.role_table_grants g
  where g.table_schema='erp'
    and g.table_name in('journal_entries','journal_lines','account_daily_balances',
      'material_supplier_invoices','material_supplier_invoice_lines')
    and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE')

  union all
  select 'V2620C_PO_HPP_TARGET_STATE_MISMATCH','CRITICAL',count(*)::bigint,
    'Saved PO HPP/FG/COGS/other state must equal independently recomputed current minor-unit targets'
  from erp.po_hpp_gl_state s
  cross join lateral erp.compute_po_hpp_gl_targets(s.po_id) t
  where s.base_output_qty is distinct from coalesce(t.base_output_qty,0)
     or s.hpp_total_cost is distinct from round(coalesce(t.hpp_total_cost,0),2)
     or s.fg_value is distinct from round(coalesce(t.fg_value,0),2)
     or s.cogs_value is distinct from round(coalesce(t.cogs_value,0),2)
     or s.other_out_value is distinct from(
       round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2))

  union all
  select 'V2620C_HPP_COMPONENT_SUM_MISMATCH','CRITICAL',count(*)::bigint,
    'Every current HPP version must equal the exact sum of its traceable components'
  from erp.hpp_versions h
  where h.is_current and abs(h.total_cost-coalesce((
    select sum(c.total_cost) from erp.hpp_version_components c where c.hpp_version_id=h.id
  ),0))>0.000001

  union all
  select 'V2620C_PO_HPP_BOOK_MISMATCH','CRITICAL',count(*)::bigint,
    'Per-PO FG, COGS, and HPP-disposition books must equal the saved minor-unit state after every post, recost, cancellation, return, and reversal'
  from erp.po_hpp_gl_state s
  cross join lateral(
    select
      coalesce(sum(jl.debit-jl.credit) filter(
        where jl.account_id=erp.account_id('FG_INVENTORY')),0)::numeric fg_book,
      coalesce(sum(jl.debit-jl.credit) filter(
        where jl.account_id=erp.account_id('COGS')),0)::numeric cogs_book,
      coalesce(sum(jl.debit-jl.credit) filter(
        where jl.account_id in(
          erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
        )),0)::numeric other_book
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
      and je.status in('POSTED','REVERSED')
    where jl.po_id=s.po_id
  ) b
  cross join lateral(
    select coalesce(sum(e.residual_amount),0)::numeric active_wip_close
    from erp.po_wip_close_events e
    join erp.journal_entries je on je.id=e.journal_entry_id
      and je.source_type='PO_WIP_RESIDUAL_CLOSE' and je.status='POSTED'
    where e.po_id=s.po_id
  ) c
  where abs(b.fg_book-s.fg_value)>0.005
     or abs(b.cogs_book-s.cogs_value)>0.005
     or abs((b.other_book-c.active_wip_close)-s.other_out_value)>0.005

  union all
  select 'V2620C_WIP_SOURCE_CONSERVATION_MISMATCH','CRITICAL',count(*)::bigint,
    'Per-PO WIP book must equal independently sourced manufacturing cost not yet transferred into current HPP, net of an active final residual close'
  from erp.po_hpp_gl_state s
  cross join lateral(
    select (
      coalesce((
        select sum(-m.qty_signed*m.unit_cost_snapshot)
        from erp.material_stock_movements m
        where (m.source_type='CUTTING_GROUP' and m.source_id in(
          select g.id from erp.cutting_groups g where g.po_id=s.po_id
        )) or (m.source_type='CUTTING_GROUP_RETURN' and m.source_id in(
          select g.id from erp.cutting_groups g where g.po_id=s.po_id
        ))
      ),0)
      +coalesce((
        select sum(i.qty*i.unit_cost_snapshot)
        from erp.contractor_material_issue_items i
        join erp.contractor_material_issues h on h.id=i.issue_id and h.status='POSTED'
        join erp.materials m on m.id=i.material_id and m.material_type<>'ACCESSORY'
        where h.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(l.amount_payable)
        from erp.work_completion_lines l
        join erp.work_completion_events h on h.id=l.completion_id and h.status='POSTED'
        where h.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(a.allocated_amount)
        from erp.attendance_hpp_pool_allocations a
        join erp.attendance_hpp_pools h on h.id=a.pool_id and h.status='ACTIVE'
        where a.po_id=s.po_id
      ),0)
      +coalesce((
        with delivery_cost as(
          select dl.id,dl.qty_sent_pcs,dl.estimated_rate_snapshot,
            coalesce(sum(case when rh.status='POSTED'
              and rl.actual_cost_status in('ESTIMATED','FINAL')
              then rl.qty_good_received+rl.qty_bs_laundry else 0 end),0) qty_costed,
            coalesce(sum(case when rh.status='POSTED'
              and rl.actual_cost_status in('ESTIMATED','FINAL')
              then coalesce(rl.actual_cost,0) else 0 end),0) actual_cost
          from erp.laundry_delivery_lines dl
          join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
          left join erp.laundry_receipt_lines rl on rl.delivery_line_id=dl.id
          left join erp.laundry_receipts rh on rh.id=rl.receipt_id
          where d.po_id=s.po_id
          group by dl.id,dl.qty_sent_pcs,dl.estimated_rate_snapshot
        )
        select sum(actual_cost+greatest(qty_sent_pcs-qty_costed,0)
          *coalesce(estimated_rate_snapshot,0)) from delivery_cost
      ),0)
      +coalesce((
        select sum(l.amount_payable)
        from erp.rework_component_lines l
        join erp.rework_orders r on r.id=l.rework_order_id
          and r.status<>'CANCELLED' and r.cost_posted=true
        join erp.bs_cases b on b.id=r.bs_case_id
        where b.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(a.adjustment_amount) from erp.cost_adjustments a
        where a.po_id=s.po_id and a.component_type='OTHER'
      ),0)
      +coalesce((
        select sum(a.total_hpp_cost)
        from erp.fg_accessory_cost_snapshots a
        join erp.fg_lots fl on fl.id=a.lot_id
          and fl.lot_origin='PRODUCTION'
        where fl.po_id=s.po_id
      ),0)
    )::numeric source_cost
  ) truth
  cross join lateral(
    select coalesce(sum(jl.debit-jl.credit),0)::numeric wip_book
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
      and je.status in('POSTED','REVERSED')
    where jl.po_id=s.po_id and jl.account_id=erp.account_id('WIP')
  ) w
  cross join lateral(
    select coalesce(sum(e.residual_amount),0)::numeric active_wip_close
    from erp.po_wip_close_events e
    join erp.journal_entries je on je.id=e.journal_entry_id
      and je.source_type='PO_WIP_RESIDUAL_CLOSE' and je.status='POSTED'
    where e.po_id=s.po_id
  ) c
  where abs(w.wip_book-(round(truth.source_cost,2)-s.hpp_total_cost-c.active_wip_close))>0.005

  union all
  select 'V2620C_SALE_REVENUE_REPORT_INPUT_MISMATCH','CRITICAL',count(*)::bigint,
    'Each sale lifecycle must contribute its exact line total to SALES_REVENUE while active and zero after cancellation/reversal'
  from(
    select h.id,h.status,
      case when h.status in('POSTED','PARTIAL_PAID','PAID')
        then coalesce((select sum(i.line_total) from erp.sales_items i where i.sale_id=h.id),0)
        else 0 end::numeric expected_revenue,
      coalesce(sum(jl.credit-jl.debit),0)::numeric booked_revenue
    from erp.sales_headers h
    left join erp.journal_entries origin on origin.source_type='SALE' and origin.source_id=h.id
      and origin.status in('POSTED','REVERSED')
    left join erp.journal_entries je on je.id=origin.id
      or (je.source_type='JOURNAL_REVERSAL' and je.reversal_of_id=origin.id
          and je.status in('POSTED','REVERSED'))
    left join erp.journal_lines jl on jl.journal_entry_id=je.id
      and jl.account_id=erp.account_id('SALES_REVENUE')
    group by h.id,h.status
  ) x
  where abs(x.booked_revenue-x.expected_revenue)>0.005

  union all
  select 'V2620C_SALES_RETURN_REPORT_INPUT_MISMATCH','CRITICAL',count(*)::bigint,
    'Each sales-return lifecycle must reduce SALES_REVENUE by its exact refund while active and contribute zero after reversal'
  from(
    select h.id,h.status,
      case when h.status='POSTED'
        then -coalesce((select sum(i.refund_amount) from erp.sales_return_items i where i.return_id=h.id),0)
        else 0 end::numeric expected_revenue,
      coalesce(sum(jl.credit-jl.debit),0)::numeric booked_revenue
    from erp.sales_returns h
    left join erp.journal_entries origin on origin.source_type='SALES_RETURN' and origin.source_id=h.id
      and origin.status in('POSTED','REVERSED')
    left join erp.journal_entries je on je.id=origin.id
      or (je.source_type='JOURNAL_REVERSAL' and je.reversal_of_id=origin.id
          and je.status in('POSTED','REVERSED'))
    left join erp.journal_lines jl on jl.journal_entry_id=je.id
      and jl.account_id=erp.account_id('SALES_REVENUE')
    group by h.id,h.status
  ) x
  where abs(x.booked_revenue-x.expected_revenue)>0.005

  union all
  select 'V2620C_DRAFT_SALE_VALUE_LEAK','CRITICAL',count(*)::bigint,
    'An active Draft reservation may reduce sellable quantity but may not classify current HPP as COGS/other expense'
  from(
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.sales_headers h on h.id=i.sale_id and h.status='DRAFT'
    join erp.fg_lots fl on fl.id=a.lot_id and fl.po_id is not null
  ) d
  cross join lateral erp.compute_po_hpp_gl_targets(d.po_id) t
  where abs(coalesce(t.other_out_value,0))>0.005

  union all
  select 'V2620C_VENDOR_PAYMENT_EXACT_STATUS_MISMATCH','CRITICAL',count(*)::bigint,
    'Vendor invoice PAID/PARTIAL status must match the exact two-decimal payment subledger'
  from erp.vendor_invoices h
  cross join lateral(
    select coalesce(sum(p.amount),0)::numeric(20,2) paid
    from erp.vendor_payments p where p.vendor_invoice_id=h.id and p.status='POSTED'
  ) x
  where (h.status='PAID' and x.paid<>h.total_amount)
     or (h.status='PARTIAL_PAID' and not(x.paid>0 and x.paid<h.total_amount))
     or (h.status='POSTED' and x.paid<>0)

  union all
  select 'V2620C_HPP_STATE_HAS_SUBCENT','CRITICAL',count(*)::bigint,
    'Cumulative PO HPP GL state must contain exactly the minor-unit amounts that were journaled'
  from erp.po_hpp_gl_state s
  where s.hpp_total_cost<>round(s.hpp_total_cost,2)
     or s.fg_value<>round(s.fg_value,2)
     or s.cogs_value<>round(s.cogs_value,2)
     or s.other_out_value<>round(s.other_out_value,2);
end
$function$;
alter function erp.run_v268_financial_report_checks() owner to postgres;

do $patch_owner_report$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure)
    into v_definition;

  v_anchor:=$anchor$  v_laundry_good numeric:=0;v_laundry_bs numeric:=0;v_laundry_stuck numeric:=0;v_laundry_missing numeric:=0;$anchor$;
  v_replacement:=$replacement$  v_laundry_good numeric:=0;v_laundry_bs numeric:=0;v_laundry_stuck numeric:=0;v_laundry_missing numeric:=0;
  v_laundry_outstanding numeric:=0;
  v_failed_checks jsonb:='[]'::jsonb;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: owner report declaration anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  select coalesce(sum(i.qty_pcs*i.unit_price_snapshot),0),coalesce(sum(i.discount_amount),0)
  into v_gross_sales,v_discounts
  from erp.sales_items i join erp.sales_headers h on h.id=i.sale_id
  where h.status in('POSTED','PARTIAL_PAID','PAID') and h.sale_date::date between p_from and p_to;
  select coalesce(sum(i.refund_amount),0) into v_sales_returns
  from erp.sales_return_items i join erp.sales_returns h on h.id=i.return_id
  where h.status='POSTED' and h.physical_at::date between p_from and p_to;$anchor$;
  v_replacement:=$replacement$  select coalesce(sum(i.qty_pcs*i.unit_price_snapshot),0),coalesce(sum(i.discount_amount),0)
  into v_gross_sales,v_discounts
  from erp.sales_items i join erp.sales_headers h on h.id=i.sale_id
  where exists(
    select 1 from erp.journal_entries original
    where original.source_type='SALE' and original.source_id=h.id
      and original.transaction_date between p_from and p_to
      and not exists(
        select 1 from erp.journal_entries reversal
        where reversal.reversal_of_id=original.id
          and reversal.transaction_date<=p_to and reversal.status='POSTED'
      )
  );
  select coalesce(sum(i.refund_amount),0) into v_sales_returns
  from erp.sales_return_items i join erp.sales_returns h on h.id=i.return_id
  where exists(
    select 1 from erp.journal_entries original
    where original.source_type='SALES_RETURN' and original.source_id=h.id
      and original.transaction_date between p_from and p_to
      and not exists(
        select 1 from erp.journal_entries reversal
        where reversal.reversal_of_id=original.id
          and reversal.transaction_date<=p_to and reversal.status='POSTED'
      )
  );$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: owner report lifecycle anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  select coalesce(sum(i.qty_good_received),0),coalesce(sum(i.qty_bs_laundry),0),
         coalesce(sum(i.qty_stuck),0),coalesce(sum(i.qty_missing),0)
  into v_laundry_good,v_laundry_bs,v_laundry_stuck,v_laundry_missing
  from erp.laundry_receipt_lines i join erp.laundry_receipts h on h.id=i.receipt_id
  where h.status='POSTED' and h.physical_at::date between p_from and p_to;$anchor$;
  v_replacement:=$replacement$  select coalesce(sum(i.qty_good_received),0),coalesce(sum(i.qty_bs_laundry),0),
         coalesce(sum(i.qty_stuck),0),coalesce(sum(i.qty_missing),0)
  into v_laundry_good,v_laundry_bs,v_laundry_stuck,v_laundry_missing
  from erp.laundry_receipt_lines i join erp.laundry_receipts h on h.id=i.receipt_id
  where h.status='POSTED' and h.physical_at::date between p_from and p_to;

  select greatest(coalesce(sum(case
    when w.stage_to='LAUNDRY' then w.qty_pcs
    when w.stage_from='LAUNDRY' then -w.qty_pcs
    else 0 end),0),0)
  into v_laundry_outstanding
  from erp.wip_stage_events w
  where w.physical_at::date<=p_as_of
    and w.source_type in(
      'LAUNDRY_DELIVERY_LINE','LAUNDRY_RECEIPT_LINE',
      'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL',
      'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'
    );$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: owner report Laundry source anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  select coalesce(sum(issue_count) filter(where severity='CRITICAL'),0)::bigint,
         coalesce(sum(issue_count) filter(where severity='WARNING'),0)::bigint
  into v_critical,v_warning from erp.run_v268_financial_report_checks();$anchor$;
  v_replacement:=$replacement$  select coalesce(sum(issue_count) filter(where severity='CRITICAL'),0)::bigint,
         coalesce(sum(issue_count) filter(where severity='WARNING'),0)::bigint
  into v_critical,v_warning from erp.run_v268_financial_report_checks();
  select coalesce(jsonb_agg(jsonb_build_object(
    'check_name',c.check_name,'severity',c.severity,'issue_count',c.issue_count,
    'details',c.details) order by c.severity,c.check_name),'[]'::jsonb)
  into v_failed_checks from erp.run_v268_financial_report_checks() c
  where c.issue_count>0;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: owner report confidence anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$      'supplier_exposure_basis','CURRENT_OPERATIONAL_STATE'$anchor$;
  v_replacement:=$replacement$      'supplier_exposure_basis','CURRENT_OPERATIONAL_STATE',
      'performance_lifecycle_basis','JOURNAL_EVENT_STATE_AS_OF_PERIOD_END',
      'quality_event_basis','CURRENT_OPERATIONAL_STATE_WITH_EVENT_DATE_CUTOFF',
      'laundry_outstanding_basis','IMMUTABLE_WIP_STAGE_EVENT_NET_AS_OF_BALANCE_DATE'$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: owner report basis anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$      'pending_cost_recalc_count',v_pending$anchor$;
  v_replacement:=$replacement$      'pending_cost_recalc_count',v_pending,
      'failed_checks',v_failed_checks$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: owner report failed-check evidence anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$      'laundry_stuck_pcs',v_laundry_stuck,'laundry_missing_pcs',v_laundry_missing$anchor$;
  v_replacement:=$replacement$      'laundry_outstanding_pcs',v_laundry_outstanding,
      'legacy_receipt_stuck_pcs',v_laundry_stuck,
      'legacy_receipt_missing_pcs',v_laundry_missing$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: owner report outstanding label anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_owner_report$;

do $installed_guard$
begin
  if position('FG_HPP_SALES_V2620C' in pg_get_functiondef(
       'erp.rebuild_po_hpp(uuid,text)'::regprocedure))=0
     or position('cp6_lot_failed_wash_cost_v2620c' in pg_get_functiondef(
       'erp.rebuild_po_hpp(uuid,text)'::regprocedure))=0
     or position('SALE_RESERVE' in pg_get_functiondef(
       'erp.compute_po_hpp_gl_targets(uuid)'::regprocedure))=0
     or position('exact minor-unit targets' in pg_get_functiondef(
       'erp.sync_po_hpp_to_gl(uuid,date)'::regprocedure))=0
     or position('HPP frozen at POST' in pg_get_functiondef(
       'erp.post_sale(uuid)'::regprocedure))=0
     or position('JOURNAL_EVENT_STATE_AS_OF_PERIOD_END' in pg_get_functiondef(
       'erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure))=0
     or to_regprocedure('public.erp_search_laundry_bs_products_v1(uuid,timestamp with time zone,text,text,integer)') is null
     or not has_function_privilege('authenticated',
       'public.erp_search_laundry_bs_products_v1(uuid,timestamp with time zone,text,text,integer)','EXECUTE')
     or has_function_privilege('anon',
       'public.erp_search_laundry_bs_products_v1(uuid,timestamp with time zone,text,text,integer)','EXECUTE')
     or exists(
       select 1 from (values
         ('erp.cp6_lot_work_cost_v2620c(uuid,text)'),
         ('erp.cp6_lot_attendance_cost_v2620c(uuid)'),
         ('erp.cp6_lot_failed_wash_cost_v2620c(uuid)'),
         ('erp.cp6_lot_rework_cost_v2620c(uuid)'),
         ('erp.cp6_po_source_qty_v2620c(uuid)'),
         ('erp.search_laundry_bs_products_v2620c(uuid,timestamp with time zone,text,text,integer)')
       ) f(identity)
       cross join (values('anon'),('authenticated'),('service_role')) r(role_name)
       where has_function_privilege(r.role_name,f.identity,'EXECUTE')
     )
     or exists(
       select 1 from (values
         ('erp.cp3_r4_rollback_capsule'),('erp.cp4_v2616_rollback_capsule'),
         ('erp.cp45_v2617_rollback_capsule'),('erp.cp45_v2617a_rollback_capsule')
       ) x(identity)
       join pg_class c on c.oid=to_regclass(x.identity)
       where not c.relrowsecurity
     ) then
    raise exception 'ERP v2.6.20c deep-business repair did not install completely';
  end if;

  update erp.cp6_v2620c_rollback_capsule c
  set installed_definition_sha256=encode(extensions.digest(convert_to(
    pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
  ),'sha256'),'hex');
  if (select count(*) from erp.cp6_v2620c_rollback_capsule
      where installed_definition_sha256 is not null)<>15 then
    raise exception 'ERP v2.6.20c installed-definition capsule is incomplete';
  end if;
end
$installed_guard$;

comment on function public.erp_search_laundry_bs_products_v1(uuid,timestamptz,text,text,integer) is
  'CP6 source-bound Laundry-BS SKU search with effective-time validation and keyset paging beyond the bounded workspace lookup.';
comment on function erp.compute_po_hpp_gl_targets(uuid) is
  'Financial HPP classification: active Sale Draft reservations remain FG until POST; COGS uses current lot HPP.';
comment on function erp.sync_po_hpp_to_gl(uuid,date) is
  'Posts and stores identical minor-unit cumulative targets; deterministic remainder balances to WIP.';

insert into erp.schema_migrations(version,description)
values('v2.6.20c','CP6 deep-business repair: source-owned HPP, sale valuation order, exact money, historical report basis, Laundry-BS paging, capsule RLS');

commit;
