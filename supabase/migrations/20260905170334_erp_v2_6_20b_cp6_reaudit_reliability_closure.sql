-- ERP Garment v2.6.20b / CP6 independent re-audit reliability closure.
--
-- VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
-- Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.
-- This forward-only patch never edits recorded v2.6.20/v2.6.20a bytes and
-- never deletes or rewrites posted business history.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

lock table erp.schema_migrations,
  supabase_migrations.schema_migrations,
  erp.cp6_laundry_qc_execution_context,
  erp.laundry_deliveries,
  erp.laundry_delivery_lines,
  erp.laundry_delivery_batch_size_lines,
  erp.laundry_receipts,
  erp.laundry_receipt_lines,
  erp.laundry_receipt_batch_size_lines,
  erp.laundry_failed_wash_attempts,
  erp.laundry_failed_wash_batch_size_lines,
  erp.qc_inspections,
  erp.qc_inspection_items,
  erp.fg_lots,
  erp.hpp_versions,
  erp.hpp_version_components
in share row exclusive mode;

do $guard$
declare
  v_actual text;
  v_platform_match_count integer;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20a') then
    raise exception 'ERP v2.6.20b requires immutable v2.6.20a first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20b') then
    raise exception 'ERP v2.6.20b is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.cp6_v2620b_rollback_capsule') is not null
     or to_regclass('erp.idx_products_qc_model_size_effective_v2620b') is not null
     or to_regclass('erp.idx_sewing_terminal_group_timeline_v2620b') is not null
     or to_regclass('erp.idx_wip_delivery_source_timeline_v2620b') is not null
     or to_regprocedure('erp.assert_cp6_dispatch_timeline_v2620b(uuid,uuid,timestamp with time zone,jsonb)') is not null
     or to_regprocedure('erp.search_final_sku_products_v2620b(uuid,timestamp with time zone,text,text,integer)') is not null
     or to_regprocedure('public.erp_search_final_sku_products_v1(uuid,timestamp with time zone,text,text,integer)') is not null then
    raise exception 'ERP v2.6.20b target guard: prior re-audit patch residue exists';
  end if;
  if exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'ERP v2.6.20b refuses installation while a CP6 execution context exists';
  end if;

  select count(*) into v_platform_match_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20a_cp6_audit_reliability_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      '1b1b821d0a2d69a653a894c3bb407974c97bef1897d2a0f568d0264270542298',
      '03e0dcaaafecb9107d08d0c44e55b719fbaed63cd8881872423a0e9457a429cd'
    );
  if v_platform_match_count<>1 then
    raise exception 'ERP v2.6.20b requires one exact v2.6.20a platform-ledger row; found %',
      v_platform_match_count;
  end if;

  select encode(extensions.digest(convert_to(pg_get_functiondef(
    'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure
  ),'UTF8'),'sha256'),'hex') into v_actual;
  if v_actual is distinct from '95f42232c0157356f9347b75325a0c4dbf7adb416e5dfb76258dc20ac0a2e641' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: CP6 writer changed (%)',v_actual;
  end if;
  select encode(extensions.digest(convert_to(pg_get_functiondef(
    'erp.get_laundry_qc_workspace_v1(text,text)'::regprocedure
  ),'UTF8'),'sha256'),'hex') into v_actual;
  if v_actual is distinct from '61c675b770762fcfcb153256983d33fc670e812d2b4cdabef090c576b6101f79' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: CP6 workspace changed (%)',v_actual;
  end if;
  select encode(extensions.digest(convert_to(pg_get_functiondef(
    'erp.rebuild_po_hpp(uuid,text)'::regprocedure
  ),'UTF8'),'sha256'),'hex') into v_actual;
  if v_actual is distinct from '63914074822bdf7a8ed7728fc26034ff13f99b73ed9266a66972ca9ffa532d6c' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP rebuild changed (%)',v_actual;
  end if;
  select encode(extensions.digest(convert_to(pg_get_functiondef(
    'erp.require_internal()'::regprocedure
  ),'UTF8'),'sha256'),'hex') into v_actual;
  if v_actual is distinct from '3c1ed361e68b60beb55ec5905b57111efb5c402bf0eb3d1725323403e6434d96' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: internal authorization changed (%)',v_actual;
  end if;
end
$guard$;

-- Preserve exact predecessor bytes, owners, and ACLs. Rollback restores only
-- these captured functions and refuses after any new CP6 business use.
create table erp.cp6_v2620b_rollback_capsule(
  object_identity text primary key,
  object_regidentity text not null unique,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.cp6_v2620b_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620b_rollback_capsule
  from public,anon,authenticated,service_role;

insert into erp.cp6_v2620b_rollback_capsule(
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
  'erp.require_internal()'::regprocedure,
  'erp.rebuild_po_hpp(uuid,text)'::regprocedure,
  'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure,
  'erp.get_laundry_qc_workspace_v1(text,text)'::regprocedure,
  'erp.reverse_laundry_delivery(uuid,text)'::regprocedure,
  'erp.reverse_laundry_receipt(uuid,text)'::regprocedure,
  'erp.reverse_qc(uuid,text)'::regprocedure
);

do $capsule_guard$
begin
  if (select count(*) from erp.cp6_v2620b_rollback_capsule)<>7
     or exists(
       select 1 from erp.cp6_v2620b_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
     ) then
    raise exception 'ERP v2.6.20b exact rollback capsule is incomplete or corrupt';
  end if;
end
$capsule_guard$;

-- Reverse actions already require the public granular permission, but the
-- private dependency also needs a same-backend, same-transaction context.
-- Expand the transient context vocabulary without exposing the table.
alter table erp.cp6_laundry_qc_execution_context
  drop constraint cp6_laundry_qc_execution_context_action_check;
alter table erp.cp6_laundry_qc_execution_context
  add constraint cp6_laundry_qc_execution_context_action_check check(action in(
    'POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','POST_FINAL_SKU',
    'REVERSE_DELIVERY','REVERSE_RECEIPT','REVERSE_FINAL_SKU'
  ));

do $patch_reverse_authorization$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
  v_regprocedure regprocedure;
begin
  select pg_get_functiondef('erp.require_internal()'::regprocedure)
    into v_definition;
  v_anchor:=$anchor$        or(c.action='POST_FINAL_SKU'
          and c.permission_key='production.final_sku.post')
      )$anchor$;
  v_replacement:=$replacement$        or(c.action='POST_FINAL_SKU'
          and c.permission_key='production.final_sku.post')
        or(c.action in('REVERSE_DELIVERY','REVERSE_RECEIPT')
          and c.permission_key='production.laundry.reverse')
        or(c.action='REVERSE_FINAL_SKU'
          and c.permission_key='production.final_sku.reverse')
      )$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: reverse internal-context anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);
  execute v_definition;

  for v_regprocedure in
    select x::regprocedure from unnest(array[
      'erp.reverse_laundry_delivery(uuid,text)',
      'erp.reverse_laundry_receipt(uuid,text)',
      'erp.reverse_qc(uuid,text)'
    ]) x order by x
  loop
    select pg_get_functiondef(v_regprocedure) into v_definition;
    v_anchor:='  perform erp.require_owner_admin();';
    v_replacement:='  perform erp.require_internal();';
    if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: owner-only reverse anchor is not exact for %',
        v_regprocedure;
    end if;
    v_definition:=replace(v_definition,v_anchor,v_replacement);
    execute v_definition;
  end loop;
end
$patch_reverse_authorization$;

create index idx_products_qc_model_size_effective_v2620b
  on erp.products(model_id,size_id,effective_from,id)
  include(brand_id,sku,product_name,color_name,effective_to)
  where is_active and is_portal_visible;
create index idx_sewing_terminal_group_timeline_v2620b
  on erp.sewing_terminal_events(cutting_group_id,physical_at,id)
  include(qty_signed)
  where cutting_group_id is not null;
create index idx_wip_delivery_source_timeline_v2620b
  on erp.wip_stage_events(source_id,physical_at,id)
  include(cutting_group_id,qty_pcs,stage_from,stage_to)
  where source_type='LAUNDRY_DELIVERY_LINE';

-- Validate the complete future history affected by a proposed backdated
-- dispatch. At each physical timestamp, all same-time deltas are aggregated;
-- no arbitrary UUID/system insertion order is allowed to invent stock.
create function erp.assert_cp6_dispatch_timeline_v2620b(
  p_distribution_batch_id uuid,
  p_cutting_group_id uuid,
  p_physical_at timestamptz,
  p_lines jsonb
)
returns void
language plpgsql
security definer
set search_path=''
as $function$
begin
  if p_distribution_batch_id is null or p_cutting_group_id is null
     or p_physical_at is null or jsonb_typeof(p_lines)<>'array'
     or jsonb_array_length(p_lines)=0 then
    raise exception 'CP6 timeline validation requires batch, Potongan, physical time, and size lines';
  end if;

  if exists(
    select 1
    from erp.laundry_delivery_lines dl
    join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'DRAFT'
    left join erp.wip_stage_events src
      on src.source_type='LAUNDRY_DELIVERY_LINE' and src.source_id=dl.id
    left join erp.wip_stage_events rv
      on rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL' and rv.source_id=src.id
    where dl.cutting_group_id=p_cutting_group_id
    group by dl.id,d.status
    having count(distinct src.id)<>1
       or (d.status='REVERSED' and count(distinct rv.id)<>1)
       or (d.status<>'REVERSED' and count(distinct rv.id)<>0)
  ) then
    raise exception 'CP6 dispatch timeline cannot be proven because existing WIP lineage is incomplete';
  end if;

  if exists(
    with proposed as(
      select x.size_id,sum(x.qty_sent_pcs)::bigint qty_sent_pcs
      from jsonb_to_recordset(p_lines) x(size_id uuid,qty_sent_pcs integer)
      group by x.size_id
    ), capacity as(
      select p.size_id,
        coalesce(sum(a.qty_pcs) filter(where s.id is not null),0)::bigint capacity_qty
      from proposed p
      left join erp.cutting_distribution_allocations a
        on a.batch_id=p_distribution_batch_id
      left join erp.cutting_roll_yields y
        on y.id=a.cutting_roll_yield_id
      left join erp.cutting_group_size_slots s
        on s.id=y.size_slot_id and s.size_id=p.size_id
      group by p.size_id
    ), raw_events as(
      select sx.size_id,d.physical_at event_at,-sx.qty_sent_pcs::bigint delta_qty
      from erp.laundry_delivery_batch_size_lines sx
      join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
      join erp.laundry_deliveries d on d.id=dl.delivery_id
      join proposed p on p.size_id=sx.size_id
      where sx.distribution_batch_id=p_distribution_batch_id and d.status<>'DRAFT'
      union all
      select sx.size_id,rv.physical_at,sx.qty_sent_pcs::bigint
      from erp.laundry_delivery_batch_size_lines sx
      join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
      join erp.wip_stage_events src
        on src.source_type='LAUNDRY_DELIVERY_LINE' and src.source_id=dl.id
      join erp.wip_stage_events rv
        on rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL' and rv.source_id=src.id
      join proposed p on p.size_id=sx.size_id
      where sx.distribution_batch_id=p_distribution_batch_id
      union all
      select p.size_id,p_physical_at,-p.qty_sent_pcs from proposed p
    ), events as(
      select size_id,event_at,sum(delta_qty)::bigint delta_qty
      from raw_events group by size_id,event_at
    ), prefixes as(
      select e.size_id,e.event_at,
        c.capacity_qty+sum(e.delta_qty) over(
          partition by e.size_id order by e.event_at rows unbounded preceding
        ) remaining_qty
      from events e join capacity c on c.size_id=e.size_id
    )
    select 1 from prefixes
    where event_at>=p_physical_at and remaining_qty<0
  ) then
    raise exception 'Laundry dispatch would make a future distribution batch/size history negative';
  end if;

  if exists(
    with raw_events as(
      select e.physical_at event_at,e.qty_signed::bigint delta_qty
      from erp.sewing_terminal_events e
      where e.cutting_group_id=p_cutting_group_id
      union all
      select d.physical_at,-dl.qty_sent_pcs::bigint
      from erp.laundry_delivery_lines dl
      join erp.laundry_deliveries d on d.id=dl.delivery_id
      where dl.cutting_group_id=p_cutting_group_id and d.status<>'DRAFT'
      union all
      select rv.physical_at,rv.qty_pcs::bigint
      from erp.wip_stage_events rv
      join erp.wip_stage_events src
        on src.id=rv.source_id and src.source_type='LAUNDRY_DELIVERY_LINE'
      where rv.cutting_group_id=p_cutting_group_id
        and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
      union all
      select q.physical_at,-sum(i.qty_good_pcs+i.qty_bs_pcs)::bigint
      from erp.qc_inspections q
      join erp.qc_inspection_items i on i.inspection_id=q.id
      where i.cutting_group_id=p_cutting_group_id
        and i.source_laundry_receipt_line_id is null
        and q.status<>'DRAFT'
      group by q.id,q.physical_at
      union all
      select a.event_at,sum(i.qty_good_pcs+i.qty_bs_pcs)::bigint
      from erp.qc_inspections q
      join erp.qc_inspection_items i on i.inspection_id=q.id
      join lateral(
        select min(x.changed_at) event_at
        from erp.audit_logs x
        where x.entity_type='qc_inspections' and x.entity_id=q.id
          and x.action='REVERSE'
      ) a on a.event_at is not null
      where i.cutting_group_id=p_cutting_group_id
        and i.source_laundry_receipt_line_id is null and q.status='REVERSED'
      group by q.id,a.event_at
      union all
      select p_physical_at,-sum(x.qty_sent_pcs)::bigint
      from jsonb_to_recordset(p_lines) x(size_id uuid,qty_sent_pcs integer)
    ), events as(
      select event_at,sum(delta_qty)::bigint delta_qty
      from raw_events group by event_at
    ), prefixes as(
      select event_at,sum(delta_qty) over(order by event_at rows unbounded preceding) ready_qty
      from events
    )
    select 1 from prefixes
    where event_at>=p_physical_at and ready_qty<0
  ) then
    raise exception 'Laundry dispatch would make a future Potongan WIP history negative';
  end if;
end
$function$;
alter function erp.assert_cp6_dispatch_timeline_v2620b(uuid,uuid,timestamptz,jsonb)
  owner to postgres;
revoke all on function erp.assert_cp6_dispatch_timeline_v2620b(uuid,uuid,timestamptz,jsonb)
  from public,anon,authenticated,service_role;

do $patch_writer$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef(
    'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure
  ) into v_definition;

  v_anchor:=$anchor$  perform set_config('app.change_reason',v_reason,true);

  if v_action='POST_DELIVERY' then$anchor$;
  v_replacement:=$replacement$  perform set_config('app.change_reason',v_reason,true);

  if v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT','REVERSE_FINAL_SKU') then
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      case when v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT')
        then 'production.laundry.reverse' else 'production.final_sku.reverse' end,
      p_client_request_id,p_payload
    );
  end if;

  if v_action='POST_DELIVERY' then$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: reverse context insertion anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    select sum(x.qty_sent_pcs)::bigint into v_total
    from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
    select coalesce(w.unsent_ready_qty_pcs,0)::bigint into v_available$anchor$;
  v_replacement:=$replacement$    select sum(x.qty_sent_pcs)::bigint into v_total
    from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
    perform erp.assert_cp6_dispatch_timeline_v2620b(
      v_batch_id,v_group.id,v_physical_at,v_lines
    );
    select coalesce(w.unsent_ready_qty_pcs,0)::bigint into v_available$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: full dispatch-timeline anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  if exists(
    select 1 from erp.cp6_laundry_qc_execution_context c
    where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
  ) then raise exception 'CP6 execution context leaked after action'; end if;$anchor$;
  v_replacement:=$replacement$  if v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT','REVERSE_FINAL_SKU') then
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current()
      and actor_key=erp._idempotency_actor_key() and action=v_action
      and client_request_id=p_client_request_id;
    if not found then raise exception 'CP6 reverse execution context cleanup failed'; end if;
  end if;
  if exists(
    select 1 from erp.cp6_laundry_qc_execution_context c
    where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
  ) then raise exception 'CP6 execution context leaked after action'; end if;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: reverse context cleanup anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);
  execute v_definition;
end
$patch_writer$;

-- CP6 Laundry cost follows the exact receipt/batch-size lineage of each FG
-- lot. A partial FG handoff cannot absorb cost belonging to Good still in QC,
-- outstanding Laundry custody, Laundry BS, or an unresolved loss.
do $patch_partial_hpp$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.rebuild_po_hpp(uuid,text)'::regprocedure)
    into v_definition;

  v_anchor:=$anchor$  v_lot_rework numeric(24,6);
  v_lot_other numeric(24,6);
begin$anchor$;
  v_replacement:=$replacement$  v_lot_rework numeric(24,6);
  v_lot_other numeric(24,6);
  v_cp6_lineage boolean:=false;
  v_lot_cp6_receipt_laundry numeric(24,6):=0;
  v_lot_cp6_attempt_laundry numeric(24,6):=0;
  v_laundry_allocated numeric(24,6):=0;
begin$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP declaration anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$           bool_or(lr.status='POSTED' and lrl.actual_cost_status='PENDING') as has_pending_receipt$anchor$;
  v_replacement:=$replacement$           bool_or(lr.status='POSTED' and lrl.actual_cost_status in('PENDING','ESTIMATED')) as has_pending_receipt$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP receipt-state anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$         coalesce(bool_or(has_pending_receipt or (qty_sent_pcs>qty_costed_actual and estimated_rate_snapshot is null)),false)
  into v_laundry,v_pending from dl;$anchor$;
  v_replacement:=$replacement$         coalesce(bool_or(has_pending_receipt or qty_sent_pcs>qty_costed_actual),false)
  into v_laundry,v_pending from dl;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP outstanding-state anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  where ld.po_id=p_po_id and rl.actual_cost_status in('ESTIMATED','FINAL');


  select coalesce(sum(rcl.amount_payable),0),$anchor$;
  v_replacement:=$replacement$  where ld.po_id=p_po_id and rl.actual_cost_status in('ESTIMATED','FINAL');

  v_pending:=v_pending or exists(
    select 1
    from erp.laundry_failed_wash_attempts a
    join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
    join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
    join erp.laundry_deliveries ld on ld.id=a.delivery_id
    where ld.po_id=p_po_id and rl.actual_cost_status='ESTIMATED'
  );


  select coalesce(sum(rcl.amount_payable),0),$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: failed-wash HPP state anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    v_group_fg_qty:=0;v_group_labor:=0;v_group_commission:=0;v_group_laundry:=0;v_group_rework:=0;v_group_attendance_hpp:=0;

    if r.lineage_group_id is not null then$anchor$;
  v_replacement:=$replacement$    v_group_fg_qty:=0;v_group_labor:=0;v_group_commission:=0;v_group_laundry:=0;v_group_rework:=0;v_group_attendance_hpp:=0;
    v_cp6_lineage:=false;v_lot_cp6_receipt_laundry:=0;v_lot_cp6_attempt_laundry:=0;

    if r.lineage_group_id is not null then$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP per-lot reset anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    if coalesce(v_pool_qty,0)>0 then v_lot_material:=v_pool_material*(r.initial_qty_pcs::numeric/v_pool_qty);$anchor$;
  v_replacement:=$replacement$    select exists(
      select 1
      from erp.qc_inspection_items qi
      join erp.laundry_receipt_batch_size_lines rx
        on rx.id=qi.source_laundry_receipt_batch_size_line_id
      where qi.id=r.qc_item_id
    ) into v_cp6_lineage;

    if v_cp6_lineage then
      select coalesce((case
          when rl.actual_cost_status in('ESTIMATED','FINAL') and rl.actual_cost is not null
            then rl.actual_cost/nullif(rl.qty_good_received+rl.qty_bs_laundry,0)
          else coalesce(rl.actual_rate_snapshot,dl.estimated_rate_snapshot,0)
        end)*r.initial_qty_pcs,0)
      into v_lot_cp6_receipt_laundry
      from erp.qc_inspection_items qi
      join erp.laundry_receipt_batch_size_lines rx
        on rx.id=qi.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
        and rl.id=qi.source_laundry_receipt_line_id
      join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
      join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
      left join erp.laundry_failed_wash_attempts fa on fa.receipt_line_id=rl.id
      where qi.id=r.qc_item_id and fa.id is null;
      v_lot_cp6_receipt_laundry:=coalesce(v_lot_cp6_receipt_laundry,0);

      with lot_source as(
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
      select coalesce(sum(c.size_cost*r.initial_qty_pcs/nullif(c.capacity_qty,0)),0)
      into v_lot_cp6_attempt_laundry from capacity c;
    end if;

    if coalesce(v_pool_qty,0)>0 then v_lot_material:=v_pool_material*(r.initial_qty_pcs::numeric/v_pool_qty);$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: exact CP6 Laundry lineage anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$      v_lot_laundry:=v_group_laundry*(r.initial_qty_pcs::numeric/v_group_fg_qty);$anchor$;
  v_replacement:=$replacement$      v_lot_laundry:=case when v_cp6_lineage
        then v_lot_cp6_receipt_laundry+v_lot_cp6_attempt_laundry
        else v_group_laundry*(r.initial_qty_pcs::numeric/v_group_fg_qty) end;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: partial Laundry allocation anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    v_lot_other:=v_lot_other+v_shared_other*(r.initial_qty_pcs::numeric/v_total_qty);
    v_lot_cost:=v_lot_material+$anchor$;
  v_replacement:=$replacement$    v_lot_other:=v_lot_other+v_shared_other*(r.initial_qty_pcs::numeric/v_total_qty);
    v_laundry_allocated:=v_laundry_allocated+v_lot_laundry;
    v_lot_cost:=v_lot_material+$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Laundry allocation accumulator anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$      (v_new_id,'LAUNDRY','Laundry allocation from same cutting group; PENDING uses estimate',v_lot_laundry,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),$anchor$;
  v_replacement:=$replacement$      (v_new_id,'LAUNDRY',case when v_cp6_lineage
        then 'CP6 exact receipt/batch-size service lineage; unfinished cost remains WIP'
        else 'Legacy Laundry allocation from same cutting group; PENDING uses estimate' end,
        v_lot_laundry,case when v_cp6_lineage then 'QC_ITEM'
          when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,
        case when v_cp6_lineage then r.qc_item_id else coalesce(r.lineage_group_id,p_po_id) end),$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Laundry HPP component anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values ('production_orders',p_po_id,'RECALCULATE',jsonb_build_object($anchor$;
  v_replacement:=$replacement$  if v_laundry_allocated < -0.005 or v_laundry_allocated > v_laundry+0.005 then
    raise exception 'CP6 Laundry HPP allocation violates cost conservation: accrued %, FG allocated %',
      v_laundry,v_laundry_allocated;
  end if;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values ('production_orders',p_po_id,'RECALCULATE',jsonb_build_object($replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP conservation anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    'accessory',v_accessory,'labor',v_labor,'attendance_hpp',v_attendance_hpp,'commission',v_commission,'laundry',v_laundry,'rework',v_rework,'other',v_other,
    'total_current_fg_cost'$anchor$;
  v_replacement:=$replacement$    'accessory',v_accessory,'labor',v_labor,'attendance_hpp',v_attendance_hpp,'commission',v_commission,'laundry',v_laundry,'rework',v_rework,'other',v_other,
    'laundry_allocated_to_current_fg',v_laundry_allocated,
    'laundry_remaining_in_wip',v_laundry-v_laundry_allocated,
    'laundry_basis','CP6_EXACT_RECEIPT_BATCH_SIZE_LINEAGE_WITH_LEGACY_FALLBACK',
    'total_current_fg_cost'$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP audit basis anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);
  execute v_definition;
end
$patch_partial_hpp$;

-- The source/history query and product query are deliberately different API
-- calls. Product resolution is bound to the exact live receipt batch-size and
-- operator-supplied QC time, with keyset paging beyond the first 500 rows.
create function erp.search_final_sku_products_v2620b(
  p_source_laundry_receipt_batch_size_line_id uuid,
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
  perform erp.require_permission('production.final_sku.view');
  if p_source_laundry_receipt_batch_size_line_id is null or p_physical_at is null then
    raise exception 'Exact QC source and timezone-qualified physical time are required for Final SKU search';
  end if;
  if p_limit is null or p_limit<1 or p_limit>100 then
    raise exception 'Final SKU search page limit must be between 1 and 100';
  end if;
  if p_physical_at>statement_timestamp()+interval '5 minutes' then
    raise exception 'Final SKU search time cannot be more than five minutes in the future';
  end if;

  select po.model_id,rx.size_id into v_model_id,v_size_id
  from erp.laundry_receipt_batch_size_lines rx
  join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
  join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
  join erp.laundry_delivery_batch_size_lines sx on sx.id=rx.delivery_batch_size_line_id
  join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id and dl.id=rl.delivery_line_id
  join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
  join erp.cutting_groups g on g.id=dl.cutting_group_id and g.po_id=d.po_id
  join erp.production_orders po on po.id=g.po_id
  where rx.id=p_source_laundry_receipt_batch_size_line_id
    and rh.physical_at<=p_physical_at
    and rx.qty_good_received>coalesce((
      select sum(qi.qty_good_pcs+qi.qty_bs_pcs)
      from erp.qc_inspection_items qi
      join erp.qc_inspections q on q.id=qi.inspection_id
      where qi.source_laundry_receipt_batch_size_line_id=rx.id
        and q.status<>'REVERSED'
    ),0);
  if v_model_id is null or v_size_id is null then
    raise exception 'Final SKU search source is no longer an authoritative live QC row';
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
    'contract_version','CP6_PRODUCT_SEARCH_V2620B',
    'source_laundry_receipt_batch_size_line_id',p_source_laundry_receipt_batch_size_line_id,
    'physical_at',p_physical_at,'query',v_query,'page_limit',p_limit,
    'products',v_rows,'has_more',v_has_more,
    'next_cursor',case when v_has_more then v_next_cursor else null end
  );
end
$function$;
alter function erp.search_final_sku_products_v2620b(uuid,timestamptz,text,text,integer)
  owner to postgres;
revoke all on function erp.search_final_sku_products_v2620b(uuid,timestamptz,text,text,integer)
  from public,anon,authenticated,service_role;

create function public.erp_search_final_sku_products_v1(
  p_source_laundry_receipt_batch_size_line_id uuid,
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
  return erp.search_final_sku_products_v2620b(
    p_source_laundry_receipt_batch_size_line_id,p_physical_at,
    p_query,p_after_sort_key,p_limit
  );
end
$function$;
alter function public.erp_search_final_sku_products_v1(uuid,timestamptz,text,text,integer)
  owner to postgres;
revoke all on function public.erp_search_final_sku_products_v1(uuid,timestamptz,text,text,integer)
  from public,anon,authenticated,service_role;
grant execute on function public.erp_search_final_sku_products_v1(uuid,timestamptz,text,text,integer)
  to authenticated,service_role;

do $patch_workspace_query_contract$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.get_laundry_qc_workspace_v1(text,text)'::regprocedure)
    into v_definition;
  v_anchor:=$anchor$          and(v_query is null or lower(concat_ws(' ',rh.receipt_number,
            d.delivery_number,po.po_number,g.group_number,m.model_code,
            m.model_name,b.brand_code,b.brand_name,p.sku,p.product_name,
            s.size_code)) like '%'||v_query||'%')
      ))$anchor$;
  v_replacement:=$replacement$      ))$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: workspace product/source coupling anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$      'query_required_for_more',true,
      'products_relevant_to_live_qc',v_scope='QC',$anchor$;
  v_replacement:=$replacement$      'query_required_for_more',true,
      'transaction_query_scope','SOURCE_QUEUE_AND_HISTORY',
      'product_search_contract','CP6_PRODUCT_SEARCH_V2620B',
      'product_query_decoupled',true,
      'products_relevant_to_live_qc',v_scope='QC',$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: workspace query-contract anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);
  execute v_definition;
end
$patch_workspace_query_contract$;

do $installed_guard$
begin
  if position('assert_cp6_dispatch_timeline_v2620b' in pg_get_functiondef(
       'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure
     ))=0
     or position('REVERSE_FINAL_SKU' in pg_get_constraintdef((
       select oid from pg_constraint
       where conrelid='erp.cp6_laundry_qc_execution_context'::regclass
         and conname='cp6_laundry_qc_execution_context_action_check'
     )))=0
     or position('CP6 exact receipt/batch-size service lineage' in pg_get_functiondef(
       'erp.rebuild_po_hpp(uuid,text)'::regprocedure
     ))=0
     or position('product_query_decoupled' in pg_get_functiondef(
       'erp.get_laundry_qc_workspace_v1(text,text)'::regprocedure
     ))=0
     or has_function_privilege(
       'authenticated','erp.reverse_laundry_delivery(uuid,text)','EXECUTE'
     )
     or has_function_privilege(
       'authenticated','erp.reverse_laundry_receipt(uuid,text)','EXECUTE'
     )
     or has_function_privilege(
       'authenticated','erp.reverse_qc(uuid,text)','EXECUTE'
     )
     or not has_function_privilege(
       'authenticated',
       'public.erp_search_final_sku_products_v1(uuid,timestamp with time zone,text,text,integer)',
       'EXECUTE'
     ) then
    raise exception 'ERP v2.6.20b reliability patch did not install completely';
  end if;

  update erp.cp6_v2620b_rollback_capsule c
  set installed_definition_sha256=encode(extensions.digest(convert_to(
    pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
  ),'sha256'),'hex');
  if (select count(*) from erp.cp6_v2620b_rollback_capsule
      where installed_definition_sha256 is not null)<>7 then
    raise exception 'ERP v2.6.20b installed-definition capsule is incomplete';
  end if;
end
$installed_guard$;

comment on function public.erp_search_final_sku_products_v1(uuid,timestamptz,text,text,integer) is
  'CP6 source-bound Final SKU search with keyset paging; product search never mutates or filters the QC source queue.';

insert into erp.schema_migrations(version,description)
values('v2.6.20b','CP6 re-audit closure: full temporal prefixes, partial Laundry HPP/WIP lineage, granular reversals, independent SKU paging');

commit;
