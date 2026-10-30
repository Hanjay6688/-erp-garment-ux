-- Managed recovery only. Native BC valuation and BE/HPP writers stay intact.
create function cp7_sku_conversion.recovery_managed_v1(p_lot uuid)
returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from erp.bc_return_lots_v1 l
  join erp.be_conversion_returns_v1 r on r.outstanding_id=l.outstanding_id
  join cp7_sku_conversion.members_v1 m on m.conversion_id=r.conversion_id
  where l.id=p_lot)
$$;

create function cp7_sku_conversion.recovery_auth_v1(p_payload jsonb)
returns void language plpgsql volatile security definer set search_path='' as $$
declare v text;
begin
 -- Preserve the old parser/validation order for malformed or unmanaged input.
 if jsonb_typeof(p_payload->'lot_id') is distinct from 'string' then return;end if;
 v:=btrim(p_payload->>'lot_id');
 if v!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then return;end if;
 if not cp7_sku_conversion.recovery_managed_v1(v::uuid) then return;end if;
 perform erp.require_permission('warehouse.accessory.view');
 perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
 perform erp.require_internal();
end $$;

create function cp7_sku_conversion.recovery_graph_v1(p_conversion uuid,p_pending numeric,p_require_normal boolean)
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare v_po uuid;r record;h record;v_map jsonb:='{}'::jsonb;v_entry jsonb;
 v_source numeric(18,6);v_desired numeric(18,6);v_current numeric(18,6);
 v_extra numeric;v_total numeric(24,6);v_stored numeric(18,6);v_visits integer:=0;
begin
 select l.po_id into v_po from erp.be_conversion_sources_v1 s join erp.fg_lots l on l.id=s.source_lot_id
  where s.conversion_id=p_conversion;
 if not found then raise exception 'CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED: sumber biaya perlu diperiksa kembali';end if;
 -- A Native conversion cost belongs to its one allocation. Ambiguous legacy
 -- multi-parent destinations are not a safe in-memory propagation profile.
 if (select count(*)from erp.product_conversion_allocations where conversion_id=p_conversion)<>1
  or exists(select 1 from erp.product_conversion_allocations a join erp.product_conversions c on c.id=a.conversion_id
    join erp.fg_lots s on s.id=a.source_lot_id where c.status='POSTED'and a.destination_lot_id is not null
    and((v_po is null and s.po_id is null)or s.po_id=v_po)
    group by a.destination_lot_id having count(*)<>1)then
  raise exception 'CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED: alokasi biaya perlu diperiksa kembali';end if;
 -- Native reads only source/destination HPP reached by this cursor. An
 -- unrelated PO or unused VOIDED root must not contaminate this profile.
 for h in
  with recursive rooted(lot_id,depth,path)as(
   select fl.id,0,array[fl.id]from erp.fg_lots fl where
    (v_po is null and fl.po_id is null and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION'))
    or(v_po is not null and fl.po_id=v_po and fl.lot_origin='PRODUCTION')
   union all
   select a.destination_lot_id,x.depth+1,x.path||a.destination_lot_id from rooted x
    join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    where a.destination_lot_id is not null and not a.destination_lot_id=any(x.path)and x.depth<128),
  visited as(select a.source_lot_id,a.destination_lot_id from rooted x
   join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
   join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
   where a.destination_lot_id is not null),
  used_lots as(select source_lot_id lot_id from visited union select destination_lot_id from visited)
  select hv.lot_id,hv.hpp_per_pcs from erp.v_current_hpp hv join used_lots used on used.lot_id=hv.lot_id order by hv.lot_id
 loop
  if h.hpp_per_pcs is null or h.hpp_per_pcs::text in('NaN','Infinity','-Infinity') then
   raise exception 'CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED: HPP sumber belum dapat dipastikan';end if;
  v_map:=jsonb_set(v_map,array[h.lot_id::text],jsonb_build_object('hpp',h.hpp_per_pcs::text),true);
 end loop;
 -- Same root set, depth/path bound, visited allocations and ordering as the
 -- captured Native NONPO/PO propagation. No HPP, journal or sequence is written.
 for r in
  with recursive rooted(lot_id,depth,path)as(
   select fl.id,0,array[fl.id]from erp.fg_lots fl where
    (v_po is null and fl.po_id is null and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION'))
    or(v_po is not null and fl.po_id=v_po and fl.lot_origin='PRODUCTION')
   union all
   select a.destination_lot_id,x.depth+1,x.path||a.destination_lot_id from rooted x
    join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    where a.destination_lot_id is not null and not a.destination_lot_id=any(x.path)and x.depth<128)
  select a.*,x.depth source_depth from rooted x
   join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
   join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
   where a.destination_lot_id is not null order by x.depth,a.id
 loop
  v_visits:=v_visits+1;
  v_source:=(v_map->r.source_lot_id::text->>'hpp')::numeric(18,6);
  if v_source is null then raise exception 'CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED: HPP sumber belum dapat dipastikan';end if;
  if r.qty_pcs<=0 then continue;end if;
  v_extra:=erp.be_allocation_extra_v1(r.id);
  if v_extra is null or v_extra::text in('NaN','Infinity','-Infinity') then
   raise exception 'CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED: biaya konversi perlu diperiksa kembali';end if;
  v_desired:=v_source+((v_extra-case when r.conversion_id=p_conversion then p_pending else 0 end)/r.qty_pcs);
  if v_desired<0 then raise exception 'BE_RECOVERY_EXCEEDS_VALUE: nilai pemulihan melebihi nilai sumber dan biaya sah';end if;
  v_entry:=v_map->r.destination_lot_id::text;v_current:=(v_entry->>'hpp')::numeric(18,6);
  if v_entry is null or abs(coalesce(v_current,0)-v_desired)>0.000001 then
   if p_require_normal then
    raise exception 'CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED: HPP konversi perlu diselaraskan lebih dahulu';end if;
   -- Actual storage ABI: total_cost NUMERIC(24,6), generated HPP NUMERIC(18,6).
   -- There is no cent rounding or new average in this projection.
   v_total:=r.qty_pcs*v_desired;v_stored:=v_total/r.qty_pcs;
   v_map:=jsonb_set(v_map,array[r.destination_lot_id::text],jsonb_build_object('hpp',v_stored::text),true);
  end if;
 end loop;
 -- Same post-traversal orphan predicates, including unrelated visited branches.
 if exists(
  with recursive reachable(lot_id,path,depth)as(
   select fl.id,array[fl.id],0 from erp.fg_lots fl where
    (v_po is null and fl.po_id is null and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION'))
    or(v_po is not null and fl.po_id=v_po and fl.lot_origin='PRODUCTION')
   union all
   select a.destination_lot_id,x.path||a.destination_lot_id,x.depth+1 from reachable x
    join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    where a.destination_lot_id is not null and not a.destination_lot_id=any(x.path)and x.depth<128)
  select 1 from erp.product_conversion_allocations a
   join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
   join erp.fg_lots s on s.id=a.source_lot_id and((v_po is null and s.po_id is null)or s.po_id=v_po)
   join erp.fg_lots d on d.id=a.destination_lot_id
   where not exists(select 1 from reachable x where x.lot_id=a.destination_lot_id)
    or(v_po is null and not erp.be_nonpo_admitted_v1(c.id))
    or(v_po is not null and s.po_id is null)or d.po_id is distinct from s.po_id
    or d.lot_origin<>'CONVERSION'or d.source_lot_id is distinct from s.id or a.qty_pcs<=0)then
  if v_po is null then raise exception 'BE_NON_PO_LINEAGE_ORPHAN_OR_CYCLE';
  else raise exception 'CONVERSION_LINEAGE_ORPHAN_OR_CYCLE: PO % conversion graph is not rooted and acyclic',v_po;end if;
 end if;
 return jsonb_build_object('po_id',v_po,'visited_allocations',v_visits,'current_virtual_hpp',v_map);
end $$;

create function cp7_sku_conversion.recovery_preflight_v1(p_lot uuid,p_qty numeric,p_unit numeric,p_at timestamptz)
returns void language plpgsql volatile security definer set search_path='' as $$
declare v_conversion uuid;v_group uuid;v_material uuid;v_category uuid;v_po uuid;v_count bigint;v_avg numeric(18,6);v_stock numeric(18,6);
 v_pending numeric;v_target numeric;v_before numeric;r record;v_profile jsonb;
begin
 if not cp7_sku_conversion.recovery_managed_v1(p_lot) then return;end if;
 perform cp7_sku_conversion.recovery_auth_v1(jsonb_build_object('lot_id',p_lot::text));
 -- Existing Native BCLOT/material locks may already have waited. Do not add
 -- a blocking FG acquisition in the opposite order used by Native usage.
 if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))then
  raise exception 'CP7_SKU_RECOVERY_BUSY: data biaya sedang berubah; muat ulang lalu coba lagi';end if;
 begin
  -- Freeze Native graph/HPP/cost and append-only material inputs, including
  -- inserts (phantoms). SRE is self-compatible with our later Native writes.
  -- NOWAIT prevents inverse row/table order waits; ordinary readers continue.
  lock table cp7_sku_conversion.groups_v1,cp7_sku_conversion.members_v1,
   erp.bc_adjustment_purposes_v1,erp.bc_documents_v1,erp.bc_lot_events_v1,erp.bc_return_lots_v1,
   erp.be_conversion_cost_events_v1,erp.be_conversion_cost_sources_v1,erp.be_conversion_returns_v1,erp.be_conversion_sources_v1,
   erp.cost_recalc_queue,erp.fg_accessory_cost_snapshots,erp.fg_lots,erp.hpp_version_components,erp.hpp_versions,
   erp.material_adjustment_items,erp.material_adjustment_revaluation_facts,erp.material_adjustments,
   erp.material_cost_checkpoints,erp.material_cost_history,erp.material_cost_revaluation_state,erp.material_stock_movements,
   erp.material_purchase_items,erp.material_supplier_invoice_lines,erp.material_supplier_invoices,erp.materials,
   erp.product_conversion_allocations,erp.product_conversions in share row exclusive mode nowait;
  perform 1 from erp.accounting_period_control where singleton_id=1 for share nowait;
  -- Native propagation visits this whole graph; prelock all future touched
  -- facts in deterministic order so its old FOR UPDATE statements cannot wait.
  perform 1 from erp.product_conversions order by id for update nowait;
  perform 1 from erp.fg_lots order by id for update nowait;
  perform 1 from erp.hpp_versions order by id for update nowait;
  perform 1 from erp.material_stock_movements order by id for update nowait;
  perform 1 from erp.material_cost_history order by movement_id for update nowait;
  perform 1 from erp.material_cost_checkpoints order by material_id for update nowait;
  perform 1 from erp.material_adjustments order by id for update nowait;
  perform 1 from erp.material_adjustment_items order by id for update nowait;
  perform 1 from erp.material_adjustment_revaluation_facts order by id for update nowait;
  perform 1 from erp.material_cost_revaluation_state order by movement_id for update nowait;
  perform 1 from erp.be_conversion_cost_sources_v1 order by document_id for share nowait;
  perform 1 from erp.be_conversion_cost_events_v1 order by id for share nowait;
 exception when lock_not_available then
  raise exception 'CP7_SKU_RECOVERY_BUSY: data biaya sedang berubah; muat ulang lalu coba lagi';
 end;
 perform cp7_sku_conversion.recovery_auth_v1(jsonb_build_object('lot_id',p_lot::text));
 perform erp.resolve_accounting_transaction_date(erp._cp3_business_date(p_at));
 select count(*),min(return_source.conversion_id::text)::uuid,min(m.group_id::text)::uuid,min(l.material_id::text)::uuid
  into v_count,v_conversion,v_group,v_material from erp.bc_return_lots_v1 l
  join erp.be_conversion_returns_v1 return_source on return_source.outstanding_id=l.outstanding_id
  left join cp7_sku_conversion.members_v1 m on m.conversion_id=return_source.conversion_id where l.id=p_lot;
 if v_count<>1 or v_group is null or not exists(select 1 from erp.product_conversions where id=v_conversion and status='POSTED')then
  raise exception 'CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED: sumber pemulihan perlu diperiksa kembali';end if;
 select source_lot.po_id into v_po from erp.be_conversion_sources_v1 source_link
  join erp.fg_lots source_lot on source_lot.id=source_link.source_lot_id where source_link.conversion_id=v_conversion;
 if p_qty is null or p_unit is null or p_qty<=0 or p_unit<0 or p_qty::text in('NaN','Infinity','-Infinity')
   or p_unit::text in('NaN','Infinity','-Infinity')then
  raise exception 'CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED: nilai pemulihan perlu diperiksa kembali';end if;
 -- A repricing or backdated material replay would require another cost engine.
 -- Admit only an append at the unchanged Native moving average, with every
 -- prior cost already reconciled. All other profiles refuse before effects.
 select moving_average_cost,cached_stock_qty,accessory_category_id into v_avg,v_stock,v_category from erp.materials where id=v_material;
 if v_category is not null and not pg_try_advisory_xact_lock(hashtextextended('ACCESSORY_HPP_CATEGORY|'||v_category::text,0))then
  raise exception 'CP7_SKU_RECOVERY_BUSY: data biaya sedang berubah; muat ulang lalu coba lagi';end if;
 perform cp7_sku_conversion.recovery_auth_v1(jsonb_build_object('lot_id',p_lot::text));
 if v_avg is null or v_avg::text in('NaN','Infinity','-Infinity')or v_avg<=0 or p_unit<>v_avg
  or v_stock is null or v_stock<=0 or v_stock::text in('NaN','Infinity','-Infinity')
  or exists(select 1 from erp.material_stock_movements where material_id=v_material
    and(physical_at>=p_at or not is_cost_recalculated or unit_cost_snapshot is distinct from v_avg
      or input_unit_cost is distinct from v_avg or qty_signed<=0 or qty_signed is null or qty_signed::text in('NaN','Infinity','-Infinity')
      or source_type not in('MATERIAL_PURCHASE_ITEM','MATERIAL_ADJUSTMENT_ITEM')or source_type is null
      or reversal_of_id is not null or roll_id is not null))
  or exists(select 1 from erp.material_stock_movements m where m.material_id=v_material and(
    (m.source_type='MATERIAL_PURCHASE_ITEM'and not exists(select 1 from erp.material_purchase_items i
      where i.id=m.source_id and i.material_id=v_material and not exists(select 1 from erp.material_purchase_items other
        where other.purchase_id=i.purchase_id and other.material_id is distinct from v_material)))
    or(m.source_type='MATERIAL_ADJUSTMENT_ITEM'and not exists(select 1 from erp.material_adjustment_items i
      where i.id=m.source_id and i.material_id=v_material and not exists(select 1 from erp.material_adjustment_items other
        where other.adjustment_id=i.adjustment_id and other.material_id is distinct from v_material)))))
  or v_stock is distinct from(select sum(qty_signed)from erp.material_stock_movements where material_id=v_material)
  or exists(select 1 from erp.material_stock_movements m left join erp.material_cost_history h on h.movement_id=m.id
    where m.material_id=v_material and(h.material_id is distinct from m.material_id or h.movement_qty is distinct from m.qty_signed
      or h.movement_unit_cost is distinct from m.unit_cost_snapshot or h.average_after is distinct from v_avg
      or h.physical_at is distinct from m.physical_at
      or h.stock_after is distinct from(select sum(x.qty_signed)from erp.material_stock_movements x where x.material_id=v_material
        and(x.physical_at,x.system_created_at,x.id)<=(m.physical_at,m.system_created_at,m.id))
      or h.stock_before is distinct from h.stock_after-m.qty_signed
      or h.average_before is distinct from case when h.stock_before=0 then 0 else v_avg end))
  or exists(select 1 from erp.material_cost_checkpoints c where c.material_id=v_material and(
    c.stock_qty is distinct from coalesce((select sum(x.qty_signed)from erp.material_stock_movements x where x.material_id=v_material
      and erp._cp3_business_date(x.physical_at)<=c.checkpoint_date),0)
    or c.moving_average_cost is distinct from case when c.stock_qty=0 then 0 else v_avg end
    or c.last_movement_id is distinct from(select x.id from erp.material_stock_movements x where x.material_id=v_material
      and erp._cp3_business_date(x.physical_at)<=c.checkpoint_date order by x.physical_at desc,x.system_created_at desc,x.id desc limit 1)))
  or exists(select 1 from erp.fg_accessory_cost_snapshots where category_id=v_category and hpp_method='CATEGORY_MOVING_AVG')
  or exists(select 1 from erp.cost_recalc_queue where completed_at is null)then
  raise exception 'CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED: biaya material perlu diperiksa kembali sebelum penilaian';end if;
 for r in select s.document_id,s.kind,p.adjustment_id,d.status,cost_lot.po_id,cost_lot.id source_lot_id,cost_conversion.status conversion_status
  from erp.be_conversion_cost_sources_v1 s
  join erp.bc_adjustment_purposes_v1 p on p.document_id=s.document_id
  join erp.bc_documents_v1 d on d.id=p.document_id
  left join erp.be_conversion_sources_v1 cost_source on cost_source.conversion_id=s.conversion_id
  left join erp.fg_lots cost_lot on cost_lot.id=cost_source.source_lot_id
  left join erp.product_conversions cost_conversion on cost_conversion.id=s.conversion_id
  where exists(select 1 from erp.material_adjustment_items i where i.adjustment_id=p.adjustment_id and i.material_id=v_material)
  order by s.document_id,p.adjustment_id loop
  v_profile:=erp._cp6_material_adjustment_revaluation_state(r.adjustment_id);
  v_target:=case when r.status='POSTED'then -(v_profile->>'current_value')::numeric else 0 end;
  select coalesce(sum(target_amount-previous_amount),0)into v_before from erp.be_conversion_cost_events_v1 where adjustment_id=r.adjustment_id;
  if(v_profile->>'incomplete_cost')::bigint is distinct from 0 or r.po_id is distinct from v_po
   or r.source_lot_id is null or r.conversion_status is distinct from 'POSTED'
   or v_target is null or v_target::text in('NaN','Infinity','-Infinity')
   or v_target<>v_before or(r.kind='USAGE'and v_target<0)or(r.kind='RECOVERY'and v_target>0)then
   raise exception 'CP7_SKU_RECOVERY_PROFILE_REVIEW_REQUIRED: sumber biaya terdahulu perlu diselaraskan';end if;
 end loop;
 perform cp7_sku_conversion.recovery_graph_v1(v_conversion,0,true);
 -- Same round(...,2) as Native material-adjustment revaluation current_value.
 v_pending:=round(p_qty*p_unit,2);
 perform cp7_sku_conversion.recovery_graph_v1(v_conversion,v_pending,false);
end $$;
