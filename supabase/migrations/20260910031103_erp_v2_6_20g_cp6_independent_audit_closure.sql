-- ERP Garment v2.6.20g / independent CP6 N01-N03 closure.
-- VENI. VIDI. VICI. ERP. -- I CONQUERED ERP.
-- Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.
-- Existing posted journals/movements remain immutable. Residual value changes
-- use the existing append-only F synchronizer and retain their trigger source.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';

lock table erp.schema_migrations,supabase_migrations.schema_migrations
in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.journal_entries in share row exclusive mode;
lock table erp.audit_logs,erp.journal_lines,
  erp.fg_adjustments,erp.fg_adjustment_items,
  erp.opening_balance_headers,erp.opening_balance_items,
  erp.opening_hpp_corrections,erp.material_stock_movements,
  erp.fg_lots,erp.fg_stock_movements,erp.fg_inventory_balances,
  erp.hpp_versions,erp.opening_lot_hpp_gl_state,
  erp.non_po_hpp_gl_sync_events_v2620f,
  erp.sales_headers,erp.sales_items,erp.sale_stock_allocations,
  erp.sales_returns,erp.sales_return_items,
  erp.laundry_deliveries,erp.laundry_delivery_lines,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events
in share row exclusive mode;

do $guard_v2620g$
declare r record; v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20f') then
    raise exception 'ERP v2.6.20g requires exact v2.6.20f first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20g')
     or to_regclass('erp.cp6_v2620g_rollback_capsule') is not null then
    raise exception 'ERP v2.6.20g already recorded or prior repair residue exists; never replay';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations m
      where m.name='erp_v2_6_20f_cp6_final_runtime_reliability'
        and encode(extensions.digest(convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'),'hex')
          in('48f0431ca57abc99906d3f578b53ef59f9072fef3fc3e11c0b50a5c3a581279c',
             '5ffdf1e5c12ccc964cf41820a78a790f33b10bbe087397d41b62f6e315c928ae'))<>1 then
    raise exception 'ERP v2.6.20g requires one exact F platform-ledger row';
  end if;
  if exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'ERP v2.6.20g refuses an active CP6 execution context';
  end if;
  for r in select * from(values
    ('erp.post_fg_adjustment(uuid)','a8d3fcccacd5017e54e5f48f042bc8ec57224bce2623fbdbc1cbe1f70824316c'),
    ('erp.reverse_fg_adjustment(uuid,text)','22d7a3ac32c06397b1e6f1659d4c4de0b49367c75a8872e7313ea850b1e185e9'),
    ('erp.post_opening_balance(uuid)','eee35b03c775861208d64873acfd010d51d28da4b377dced1d815ae5ec88c720'),
    ('erp.post_opening_hpp_correction(uuid,numeric,text,date)','c3bd668af920187afe2781cbe5b87cca7995bcbfff2cee684a38a9d0d0b4fcac'),
    ('erp.reverse_opening_hpp_correction(uuid,text)','b5931900f8c23ec8b24663165859754f496c93d25caf95ab9fe1adb510628b0c'),
    ('erp.sync_opening_lot_hpp_to_gl(uuid,date)','217b1b364852601e7dd05da766219290083574a9c64684abdd0a5a5a009a8040'),
    ('erp.run_v268_financial_report_checks()','dc535f21e23d53af97a98a37da99f5109a8130833fd8bceb518196119cf993ed')
  ) expected(identity,sha256)
  loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: G predecessor % (%)',r.identity,v_actual;
    end if;
  end loop;
end
$guard_v2620g$;

create table erp.cp6_v2620g_rollback_capsule(
  object_identity text primary key,
  object_regidentity text not null unique,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp(),
  boundary_snapshot jsonb
);
alter table erp.cp6_v2620g_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620g_rollback_capsule from public,anon,authenticated,service_role;

insert into erp.cp6_v2620g_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a order by a::text) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in('erp.post_fg_adjustment(uuid)'::regprocedure,
  'erp.reverse_fg_adjustment(uuid,text)'::regprocedure,
  'erp.post_opening_balance(uuid)'::regprocedure,
  'erp.post_opening_hpp_correction(uuid,numeric,text,date)'::regprocedure,
  'erp.reverse_opening_hpp_correction(uuid,text)'::regprocedure,
  'erp.sync_opening_lot_hpp_to_gl(uuid,date)'::regprocedure,
  'erp.run_v268_financial_report_checks()'::regprocedure);

-- Capture content, not transaction timestamps: a transaction can have begun
-- before installation and write later. Any changed business fact (including
-- a forward-reconciliation journal produced by this install) blocks rollback.
do $capture_boundary_v2620g$
declare v_table text; v_hash text; v_snapshot jsonb:='{}';
begin
  foreach v_table in array array['app_users','idempotency_requests','products','audit_logs','journal_entries','journal_lines','fg_adjustments','fg_adjustment_items','opening_balance_headers','opening_balance_items','opening_hpp_corrections','material_stock_movements','fg_lots','fg_stock_movements','fg_inventory_balances','hpp_versions','opening_lot_hpp_gl_state','non_po_hpp_gl_sync_events_v2620f','sales_headers','sales_items','sale_stock_allocations','sales_returns','sales_return_items','laundry_deliveries','laundry_delivery_lines','laundry_failed_wash_attempts','wip_stage_events']
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  update erp.cp6_v2620g_rollback_capsule set boundary_snapshot=v_snapshot;
end
$capture_boundary_v2620g$;

-- N01: every adjustment consumer participates in the same serialized lifecycle
-- as sale/return. Preserve original document journals and append only the
-- cumulative minor-unit residual. A pre-existing mismatch cannot be hidden by
-- an unrelated subsequent transaction.
do $patch_adjustments_v2620g$
declare v_definition text; v_identity text; v_anchor text; v_replacement text;
begin
  foreach v_identity in array array['erp.post_fg_adjustment(uuid)','erp.reverse_fg_adjustment(uuid,text)']
  loop
    select pg_get_functiondef(to_regprocedure(v_identity)) into v_definition;
    v_anchor:='  perform erp.require_owner_admin();';
    if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: G adjustment auth anchor %',v_identity;
    end if;
    v_definition:=replace(v_definition,v_anchor,v_anchor||E'\n  perform pg_advisory_xact_lock(hashtextextended(''FG_HPP_SALES_V2620C'',0));');
    if v_identity='erp.post_fg_adjustment(uuid)' then
      v_anchor:='  update erp.fg_adjustment_items set qty_signed=qty_signed where adjustment_id=h.id;';
    else
      v_anchor:=$anchor$  for r in
    select fm.id$anchor$;
    end if;
    v_replacement:=$replacement$  for r in
    select distinct fl.product_id
    from erp.fg_adjustment_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.adjustment_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

$replacement$||v_anchor;
    if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: G adjustment pre-assert anchor %',v_identity;
    end if;
    v_definition:=replace(v_definition,v_anchor,v_replacement);
    v_anchor:='  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)';
    v_replacement:=$replacement$  for r in
    select distinct fl.product_id
    from erp.fg_adjustment_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.adjustment_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.sync_non_po_product_hpp_to_gl_v2620f(
      r.product_id,case when h.status='DRAFT' then h.physical_at::date else current_date end,
      case when h.status='DRAFT' then 'FG_ADJUSTMENT' else 'FG_ADJUSTMENT_REVERSAL' end,
      h.id,'Cumulative adjustment lifecycle: '||h.reason
    );
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

$replacement$||v_anchor;
    if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: G adjustment post-sync anchor %',v_identity;
    end if;
    execute replace(v_definition,v_anchor,v_replacement);
  end loop;
end
$patch_adjustments_v2620g$;

-- N02: preserve F's independently rounded source-lot basis. Equity is the
-- sum of the same posted line amounts, never round(sum(raw line costs)).
-- Raw unit cost and HPP versions retain their original precision/lineage.
do $patch_opening_v2620g$
declare v_definition text; v_anchor text;
begin
  select pg_get_functiondef('erp.post_opening_balance(uuid)'::regprocedure) into v_definition;
  v_anchor:='  perform erp.require_owner_admin();';
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: G opening auth anchor';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_anchor||E'\n  perform pg_advisory_xact_lock(hashtextextended(''FG_HPP_SALES_V2620C'',0));');
  if (length(v_definition)-length(replace(v_definition,'v_debits:=v_debits+v_value;','')))
       /length('v_debits:=v_debits+v_value;')<>6
     or (length(v_definition)-length(replace(v_definition,'v_credits:=v_credits+v_value;','')))
       /length('v_credits:=v_credits+v_value;')<>3
     or (length(v_definition)-length(replace(v_definition,'if v_value>0 then','')))
       /length('if v_value>0 then')<>3 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: G opening minor-unit anchors';
  end if;
  v_definition:=replace(v_definition,'v_debits:=v_debits+v_value;','v_debits:=v_debits+round(v_value,2);');
  v_definition:=replace(v_definition,'v_credits:=v_credits+v_value;','v_credits:=v_credits+round(v_value,2);');
  v_definition:=replace(v_definition,'if v_value>0 then','if round(v_value,2)>0 then');
  execute v_definition;
end
$patch_opening_v2620g$;

-- N02 lifecycle extension: round(new lot basis)-round(previous lot basis),
-- never round(raw cost difference). The pre-change asserts below prevent a
-- correction from absorbing an unrelated existing target/book discrepancy.
do $patch_opening_corrections_v2620g$
declare v_identity text; v_definition text; v_anchor text;
begin
  foreach v_identity in array array['erp.post_opening_hpp_correction(uuid,numeric,text,date)',
    'erp.reverse_opening_hpp_correction(uuid,text)']
  loop
    select pg_get_functiondef(to_regprocedure(v_identity)) into v_definition;
    v_anchor:='  perform erp.require_owner_admin();';
    if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: G opening correction auth %',v_identity;
    end if;
    v_definition:=replace(v_definition,v_anchor,v_anchor||E'\n  perform pg_advisory_xact_lock(hashtextextended(''FG_HPP_SALES_V2620C'',0));');
    v_anchor:='  select hpp_version_id,hpp_per_pcs into ';
    if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: G opening correction pre-assert %',v_identity;
    end if;
    execute replace(v_definition,v_anchor,
      E'  perform erp.assert_non_po_product_hpp_target_book_v2620f(l.product_id);\n'||v_anchor);
  end loop;
end
$patch_opening_corrections_v2620g$;

create or replace function erp.sync_opening_lot_hpp_to_gl(
  p_lot_id uuid,p_effective_date date default current_date
)
returns void language plpgsql security definer set search_path='erp','public'
as $function$
declare
  l erp.fg_lots%rowtype; s erp.opening_lot_hpp_gl_state%rowtype;
  h erp.hpp_versions%rowtype; v_baseline numeric; v_source_delta numeric;
  v_expected_delta numeric; v_current_qty numeric; v_base_fg numeric;
  v_net_sold_qty numeric; v_actual_cogs numeric; v_expense numeric; v_income numeric;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into l from erp.fg_lots where id=p_lot_id for update;
  if l.id is null or l.lot_origin<>'OPENING' then return; end if;
  select * into h from erp.hpp_versions where lot_id=l.id and is_current;
  if h.id is null then raise exception 'Opening current HPP is missing'; end if;
  select fm.unit_hpp_snapshot into v_baseline from erp.fg_stock_movements fm
  where fm.lot_id=l.id and fm.movement_type='OPENING'
  order by fm.physical_at,fm.system_created_at,fm.id limit 1;
  if v_baseline is null then raise exception 'Opening lot % has no source movement',l.lot_number; end if;
  if exists(select 1 from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id
    where a.source_lot_id=l.id and c.status='POSTED') then
    raise exception 'Opening HPP conversion requires a sourced descendant correction workflow';
  end if;
  select * into s from erp.opening_lot_hpp_gl_state where lot_id=l.id for update;
  v_expected_delta:=round(h.total_cost,2)
    -round(l.initial_qty_pcs*coalesce(s.current_hpp,v_baseline),2);
  select t.hpp_total_cost-b.hpp_total_cost into v_source_delta
  from erp.compute_non_po_product_hpp_targets_v2620f(l.product_id) t
  cross join lateral erp.compute_non_po_product_hpp_book_v2620f(l.product_id) b;
  if v_source_delta is distinct from v_expected_delta then
    raise exception 'OPENING_SOURCE_CHANGE_NOT_EXACT: product %, pending lot basis %, target/book source delta %',
      l.product_id,v_expected_delta,v_source_delta;
  end if;
  if v_source_delta<>0 then
    perform erp.post_journal('OPENING_HPP_SOURCE_V2620G',h.id,p_effective_date,
      'Source lot basis correction for '||l.lot_number||' / HPP version '||h.id,
      jsonb_build_array(
        jsonb_build_object('mapping_key','FG_INVENTORY',
          'debit',greatest(v_source_delta,0),'credit',greatest(-v_source_delta,0),'product_id',l.product_id),
        jsonb_build_object('mapping_key','OPENING_EQUITY',
          'debit',greatest(-v_source_delta,0),'credit',greatest(v_source_delta,0))
      ));
  end if;
  perform erp.sync_non_po_product_hpp_to_gl_v2620f(l.product_id,p_effective_date,
    'OPENING_HPP_LIFECYCLE_V2620G',h.id,'Exact rounded opening source and cumulative physical lifecycle');
  perform erp.assert_non_po_product_hpp_target_book_v2620f(l.product_id);

  -- Preserve the historical raw revaluation diagnostics and trigger-activation
  -- contract. These projections are not used as monetary posting authority:
  -- actual journals and F's cumulative source/target/book checks are.
  -- DRAFT reservations reduce sellable qty, not company ownership.
  select coalesce(sum(fm.qty_signed),0),coalesce(sum(fm.qty_signed*fm.unit_hpp_snapshot),0)
    into v_current_qty,v_base_fg from erp.fg_stock_movements fm where fm.lot_id=l.id;
  select v_current_qty+coalesce(sum(abs(fm.qty_signed)),0),
    v_base_fg+coalesce(sum(abs(fm.qty_signed)*fm.unit_hpp_snapshot),0)
    into v_current_qty,v_base_fg from erp.fg_stock_movements fm
    where fm.lot_id=l.id and fm.movement_type='SALE_RESERVE'
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id);
  select coalesce(sum(a.qty_pcs),0),coalesce(sum(a.qty_pcs*a.unit_hpp_snapshot),0)
    into v_net_sold_qty,v_actual_cogs from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id join erp.sales_headers sh on sh.id=i.sale_id
    where a.lot_id=l.id and sh.status in('POSTED','PARTIAL_PAID','PAID');
  select v_net_sold_qty-coalesce(sum(i.qty_pcs),0),v_actual_cogs-coalesce(sum(i.qty_pcs*i.unit_hpp_snapshot),0)
    into v_net_sold_qty,v_actual_cogs from erp.sales_return_items i
    join erp.sales_returns rh on rh.id=i.return_id where i.lot_id=l.id and rh.status='POSTED';
  select coalesce(sum(case when i.qty_signed<0 then -i.qty_signed*(h.hpp_per_pcs-i.unit_hpp_snapshot) else 0 end),0),
    coalesce(sum(case when i.qty_signed>0 then i.qty_signed*(h.hpp_per_pcs-i.unit_hpp_snapshot) else 0 end),0)
    into v_expense,v_income from erp.fg_adjustment_items i
    join erp.fg_adjustments a on a.id=i.adjustment_id where i.lot_id=l.id and a.status='POSTED';
  insert into erp.opening_lot_hpp_gl_state(lot_id,current_hpp,fg_revaluation,cogs_revaluation,
    expense_revaluation,income_revaluation,equity_revaluation,updated_at)
  values(l.id,h.hpp_per_pcs,v_current_qty*h.hpp_per_pcs-v_base_fg,
    v_net_sold_qty*h.hpp_per_pcs-v_actual_cogs,v_expense,v_income,
    l.initial_qty_pcs*(h.hpp_per_pcs-v_baseline),now())
  on conflict(lot_id) do update set current_hpp=excluded.current_hpp,
    fg_revaluation=excluded.fg_revaluation,cogs_revaluation=excluded.cogs_revaluation,
    expense_revaluation=excluded.expense_revaluation,income_revaluation=excluded.income_revaluation,
    equity_revaluation=excluded.equity_revaluation,updated_at=now();
end
$function$;

-- N03: independent authoritative delivery -> source-event -> inverse-event
-- reconciliation. Financial failed-wash reversal does not erase custody.
-- This detects corruption; it does not rewrite or conceal a corrupted fact.
do $patch_report_v2620g$
declare v_definition text; v_anchor text; v_replacement text;
begin
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure) into v_definition;
  v_anchor:=$anchor$  union all
  select 'V2620E_REDISPATCH_EVENT_MISMATCH','CRITICAL',count(*)::bigint,$anchor$;
  v_replacement:=$replacement$  union all
  select 'V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH','CRITICAL',count(*)::bigint,
    'Laundry source and inverse events must match authoritative delivery quantity, dimensions, direction, chronology and net physical custody'
  from(
    select dl.id
    from erp.laundry_delivery_lines dl
    join erp.laundry_deliveries d on d.id=dl.delivery_id
    join erp.production_orders po on po.id=d.po_id
    left join lateral(
      select count(*) total_sources,
        count(*) filter(where s.po_id=d.po_id
          and s.cutting_group_id is not distinct from dl.cutting_group_id
          and s.contractor_id is not distinct from po.contractor_id
          and s.stage_from='SEWING' and s.stage_to='LAUNDRY'
          and s.qty_pcs=dl.qty_sent_pcs and s.physical_at=d.physical_at) valid_sources,
        coalesce(sum(s.qty_pcs),0) source_qty
      from erp.wip_stage_events s
      where s.source_type='LAUNDRY_DELIVERY_LINE' and s.source_id=dl.id
    ) source on true
    left join lateral(
      select count(*) total_inverses,
        count(*) filter(where r.po_id=s.po_id
          and r.cutting_group_id is not distinct from s.cutting_group_id
          and r.contractor_id is not distinct from s.contractor_id
          and r.stage_from='LAUNDRY' and r.stage_to='SEWING'
          and r.qty_pcs=dl.qty_sent_pcs and r.qty_pcs=s.qty_pcs
          and r.physical_at>=s.physical_at) valid_inverses,
        coalesce(sum(r.qty_pcs),0) inverse_qty
      from erp.wip_stage_events s
      join erp.wip_stage_events r on r.source_id=s.id
        and r.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
      where s.source_type='LAUNDRY_DELIVERY_LINE' and s.source_id=dl.id
    ) inverse on true
    where d.status<>'DRAFT' and(
      source.total_sources<>1 or source.valid_sources<>1
      or inverse.total_inverses<>case when d.status='REVERSED' then 1 else 0 end
      or inverse.valid_inverses<>inverse.total_inverses
      or source.source_qty-inverse.inverse_qty<>
        case when d.status='REVERSED' then 0 else dl.qty_sent_pcs end
    )
    union all
    select s.id from erp.wip_stage_events s
    left join erp.laundry_delivery_lines dl on dl.id=s.source_id
    left join erp.laundry_deliveries d on d.id=dl.delivery_id
    where s.source_type='LAUNDRY_DELIVERY_LINE'
      and(dl.id is null or d.id is null or d.status='DRAFT')
    union all
    select r.id from erp.wip_stage_events r
    left join erp.wip_stage_events s on s.id=r.source_id
      and s.source_type='LAUNDRY_DELIVERY_LINE'
    where r.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL' and s.id is null
  ) bad_custody

  union all
  select 'V2620E_REDISPATCH_EVENT_MISMATCH','CRITICAL',count(*)::bigint,$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: G report insertion anchor';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_report_v2620g$;

-- Existing F split adjustments can already have the exact N01 residual. Use
-- the source-value-conserving F reconciler, retain a migration trigger source,
-- and let any unrelated source-value mismatch refuse the whole installation.
do $reconcile_v2620g$
declare r record;
begin
  for r in select distinct product_id from erp.fg_lots
    where po_id is null and lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
    order by product_id
  loop
    perform erp.sync_non_po_product_hpp_to_gl_v2620f(
      r.product_id,current_date,'MIGRATION_V2620G',null,
      'Independent audit N01: append-only cumulative non-PO adjustment reconciliation'
    );
  end loop;
end
$reconcile_v2620g$;

do $installed_guard_v2620g$
declare r record; v_count bigint;
begin
  if (select count(*) from erp.cp6_v2620g_rollback_capsule)<>7 then
    raise exception 'ERP v2.6.20g incomplete rollback capsule';
  end if;
  for r in select c.*,p.proowner,p.proacl
    from erp.cp6_v2620g_rollback_capsule c join pg_proc p on p.oid=to_regprocedure(c.object_regidentity)
  loop
    if pg_get_userbyid(r.proowner) is distinct from r.owner_snapshot
       or (case when r.proacl is null then null else array(select a::text from unnest(r.proacl) a order by a::text) end)
          is distinct from r.acl_snapshot then
      raise exception 'ERP v2.6.20g changed owner/ACL for %',r.object_regidentity;
    end if;
  end loop;
  select coalesce(sum(issue_count),0) into v_count from erp.run_v268_financial_report_checks()
  where check_name in('V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH',
    'V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH','V2620E_OPENING_FG_GL_MISMATCH');
  if v_count<>0 then raise exception 'ERP v2.6.20g targeted reconciliation failed: % issue(s)',v_count; end if;
  update erp.cp6_v2620g_rollback_capsule c set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'),'sha256'),'hex');
end
$installed_guard_v2620g$;

insert into erp.schema_migrations(version,description) values(
  'v2.6.20g','CP6 independent N01-N03: cumulative adjustment/reversal cents, line-consistent opening equity, and authoritative WIP custody detector'
);
commit;
