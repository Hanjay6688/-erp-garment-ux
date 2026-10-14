-- bootstrap lines 14887-14951
CREATE OR REPLACE FUNCTION erp.post_qc(p_qc_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.qc_inspections%rowtype;
  r record;
  v_lot_id uuid;
  v_lot_number text;
begin
  perform erp.require_internal();
  select * into h from erp.qc_inspections where id=p_qc_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'QC must be DRAFT'; end if;
  if h.destination_location_id is null then raise exception 'QC destination FG location is required'; end if;
  if not exists(select 1 from erp.qc_inspection_items where inspection_id=h.id) then raise exception 'QC has no items'; end if;

  -- Validate all SKU identities before creating any FG/BS side effect.
  for r in
    select qi.*,p.sku
    from erp.qc_inspection_items qi
    join erp.products p on p.id=qi.final_product_id
    where qi.inspection_id=h.id
    order by qi.id
  loop
    perform erp.assert_product_identity_time(r.final_product_id,h.physical_at,'NEW_STOCK');
  end loop;

  for r in
    select qi.*,p.sku
    from erp.qc_inspection_items qi
    join erp.products p on p.id=qi.final_product_id
    where qi.inspection_id=h.id
    order by qi.id
  loop
    if r.qty_good_pcs>0 then
      v_lot_number:=h.inspection_number||'-'||regexp_replace(r.sku,'[^A-Za-z0-9]+','','g')||'-'||substr(r.id::text,1,8);
      insert into erp.fg_lots(
        lot_number,po_id,qc_item_id,cutting_group_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,lot_origin
      ) values(
        v_lot_number,h.po_id,r.id,r.cutting_group_id,r.final_product_id,r.qty_good_pcs,0,h.physical_at,'PRODUCTION'
      ) returning id into v_lot_id;
      perform erp.post_fg_movement(r.final_product_id,v_lot_id,h.destination_location_id,'GRADE_A','QC_GOOD',r.qty_good_pcs,0,null,'QC_ITEM',r.id,h.physical_at,'QC good output',false);
      perform erp.ensure_fg_accessory_cost_snapshot(v_lot_id);
      perform erp.post_accessory_reimbursement_accrual(v_lot_id);
    end if;

    if r.qty_bs_pcs>0 then
      insert into erp.bs_cases(bs_number,po_id,cutting_group_id,qc_item_id,product_id,detected_at_stage,cause_source,qty_pcs,status,physical_at,notes)
      values('BS-QC-'||h.inspection_number||'-'||substr(r.id::text,1,8),h.po_id,r.cutting_group_id,r.id,r.final_product_id,'QC','UNKNOWN',r.qty_bs_pcs,'OPEN',h.physical_at,'Detected at QC; classify cause when known')
      on conflict(bs_number) do nothing;
    end if;
  end loop;

  update erp.qc_inspections set status='POSTED',updated_at=now() where id=h.id;
  update erp.production_orders set status='QC',current_stage='QC',updated_at=now() where id=h.po_id;
  perform erp.sync_laundry_accrual(h.po_id,h.physical_at::date);
  perform erp.rebuild_po_hpp(h.po_id,'QC posted / batch-lineage HPP snapshot / output lot created');
  perform erp.propagate_conversion_hpp_for_po(h.po_id);
  perform erp.sync_po_hpp_to_gl(h.po_id,h.physical_at::date);
end$function$;

alter function "erp"."post_qc"(p_qc_id uuid) owner to "postgres";
