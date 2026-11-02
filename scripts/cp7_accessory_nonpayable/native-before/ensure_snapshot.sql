CREATE OR REPLACE FUNCTION erp.ensure_fg_accessory_cost_snapshot(p_lot_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  l erp.fg_lots%rowtype;
  p erp.production_orders%rowtype;
  v_bom uuid;
  r record;
  v_category_avg numeric(18,6);
  v_hpp_factor numeric(18,6);
  v_reimburse_factor numeric(18,6);
  v_hpp_base numeric(18,6);
  v_reimburse_base numeric(18,6);
  v_snapshot uuid;
  v_commit_at timestamptz;
  v_rework uuid;
  v_decision uuid;
  v_recipient uuid;
  v_selected_count integer;
  v_snapshot_count integer;
begin
  perform erp.require_internal();
  select * into l from erp.fg_lots where id=p_lot_id for update;
  if l.id is null or l.lot_origin<>'PRODUCTION' then return; end if;
  select * into p from erp.production_orders where id=l.po_id;
  if p.id is null then return; end if;

  select ro.id,d.id,d.bom_version_id,d.reimbursement_contractor_id,d.selected_item_count
  into v_rework,v_decision,v_bom,v_recipient,v_selected_count
  from erp.rework_orders ro
  join erp.rework_accessory_decisions d on d.rework_order_id=ro.id
  where ro.good_fg_lot_id=l.id;

  if v_rework is not null then
    select count(*) into v_snapshot_count
    from erp.fg_accessory_cost_snapshots s where s.lot_id=l.id;
    if v_snapshot_count>0 then
      if v_snapshot_count<>v_selected_count
         or exists(
           select 1 from erp.fg_accessory_cost_snapshots s
           left join erp.rework_accessory_selection_lines sl
             on sl.decision_id=v_decision and sl.bom_item_id=s.bom_item_id
           where s.lot_id=l.id and sl.id is null
         ) then
        raise exception 'Rework accessory snapshot set diverges from immutable selection lineage';
      end if;
      return;
    end if;
    if v_selected_count=0 then return; end if;
    if v_bom is null then raise exception 'Selected rework accessory lineage has no BOM version'; end if;
    if not exists(
      select 1 from erp.po_accessory_bom_commitments c
      where c.po_id=l.po_id and c.product_id=l.product_id and c.bom_version_id=v_bom
    ) then raise exception 'Rework accessory BOM commitment is missing or changed'; end if;

    for r in
      select sl.*,c.category_code
      from erp.rework_accessory_selection_lines sl
      join erp.accessory_categories c on c.id=sl.category_id
      where sl.decision_id=v_decision
      order by c.category_code,sl.id
    loop
      v_category_avg:=erp.accessory_category_weighted_avg_cost_at(r.category_id,l.produced_at);
      if r.hpp_method_snapshot='CATEGORY_MOVING_AVG' then
        if v_category_avg is null then
          raise exception 'Cannot snapshot HPP: accessory category % has no moving-average valuation history at %',r.category_id,l.produced_at;
        end if;
        v_hpp_base:=v_category_avg;
      else
        v_hpp_base:=r.hpp_standard_unit_cost_base_snapshot;
      end if;
      v_reimburse_base:=r.reimbursement_unit_rate_base_snapshot;
      insert into erp.fg_accessory_cost_snapshots(
        lot_id,po_id,product_id,bom_version_id,bom_item_id,category_id,
        good_qty_pcs,qty_per_good_fg_base,hpp_method,
        category_avg_cost_base_snapshot,hpp_unit_cost_base_snapshot,
        reimbursement_unit_rate_base_snapshot,costing_basis_at,costing_basis_source
      ) values(
        l.id,l.po_id,l.product_id,v_bom,r.bom_item_id,r.category_id,
        l.initial_qty_pcs,r.qty_per_good_fg_base_snapshot,r.hpp_method_snapshot,
        v_category_avg,v_hpp_base,v_reimburse_base,l.produced_at,'FG_ACCEPTANCE'
      ) returning id into v_snapshot;
      if v_recipient is null and v_reimburse_base>0 then
        raise exception 'Selected rework accessory reimbursement has no authoritative Mandor';
      end if;
      if v_recipient is not null and v_reimburse_base>0 then
        insert into erp.contractor_accessory_reimbursement_entitlements(
          snapshot_id,contractor_id,po_id,lot_id,product_id,category_id,physical_at,amount
        ) select
          v_snapshot,v_recipient,l.po_id,l.id,l.product_id,r.category_id,
          l.produced_at,total_reimbursement
        from erp.fg_accessory_cost_snapshots where id=v_snapshot;
      end if;
    end loop;
    return;
  end if;

  if exists(select 1 from erp.initial_import_wip_outputs o join erp.initial_import_production_sources s on s.opening_item_id=o.opening_item_id where o.lot_id=l.id and s.accessory_cost_included) then return;end if;
  if exists(select 1 from erp.fg_accessory_cost_snapshots where lot_id=l.id) then return; end if;
  v_bom:=erp.commit_accessory_bom_for_lot(l.id);
  if v_bom is null then return; end if;
  select committed_at into v_commit_at
  from erp.po_accessory_bom_commitments
  where po_id=l.po_id and product_id=l.product_id;
  for r in
    select i.*,c.base_uom_code
    from erp.accessory_bom_items i
    join erp.accessory_categories c on c.id=i.category_id
    where i.bom_version_id=v_bom order by c.category_code
  loop
    v_category_avg:=erp.accessory_category_weighted_avg_cost_at(r.category_id,l.produced_at);
    if r.hpp_method='CATEGORY_MOVING_AVG' then
      if v_category_avg is null then
        raise exception 'Cannot snapshot HPP: accessory category % has no moving-average valuation history at %',r.category_id,l.produced_at;
      end if;
      v_hpp_base:=v_category_avg;
    else
      v_hpp_factor:=erp.accessory_uom_factor(r.category_id,r.hpp_uom_code,l.produced_at);
      v_hpp_base:=r.hpp_standard_rate/v_hpp_factor;
    end if;
    v_reimburse_factor:=erp.accessory_uom_factor(
      r.category_id,r.reimbursement_uom_code,l.produced_at
    );
    v_reimburse_base:=r.reimbursement_rate/v_reimburse_factor;
    insert into erp.fg_accessory_cost_snapshots(
      lot_id,po_id,product_id,bom_version_id,bom_item_id,category_id,
      good_qty_pcs,qty_per_good_fg_base,hpp_method,
      category_avg_cost_base_snapshot,hpp_unit_cost_base_snapshot,
      reimbursement_unit_rate_base_snapshot,costing_basis_at,costing_basis_source
    ) values(
      l.id,l.po_id,l.product_id,v_bom,r.id,r.category_id,l.initial_qty_pcs,
      r.qty_per_good_fg_base,r.hpp_method,v_category_avg,v_hpp_base,
      v_reimburse_base,l.produced_at,
      case when v_commit_at=l.produced_at then 'FIRST_FINANCIAL_USE' else 'FG_ACCEPTANCE' end
    ) returning id into v_snapshot;
    if p.contractor_id is null and v_reimburse_base>0 then
      raise exception 'PO % has accessory reimbursement BOM but no mandor/contractor',p.po_number;
    end if;
    if p.contractor_id is not null and v_reimburse_base>0 then
      insert into erp.contractor_accessory_reimbursement_entitlements(
        snapshot_id,contractor_id,po_id,lot_id,product_id,category_id,physical_at,amount
      ) select
        v_snapshot,p.contractor_id,l.po_id,l.id,l.product_id,r.category_id,
        l.produced_at,total_reimbursement
      from erp.fg_accessory_cost_snapshots where id=v_snapshot;
    end if;
  end loop;
end
$function$
