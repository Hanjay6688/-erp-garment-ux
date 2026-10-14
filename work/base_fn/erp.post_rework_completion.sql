-- bootstrap lines 14952-14981
CREATE OR REPLACE FUNCTION erp.post_rework_completion(p_rework_order_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare r erp.rework_orders%rowtype;b erp.bs_cases%rowtype;v_total numeric(20,2):=0;v_location uuid;v_location_count integer:=0;v_lot uuid;v_lot_number text;v_hpp numeric(18,6):=0;v_remaining integer:=0;v_completed_at timestamptz;
begin
  perform erp.require_internal();select * into r from erp.rework_orders where id=p_rework_order_id for update;if r.id is null then raise exception 'Rework order not found';end if;if r.status<>'COMPLETED' then raise exception 'Rework must be COMPLETED before posting';end if;if r.qty_good_returned+r.qty_bs_returned<>r.qty_sent then raise exception 'Rework completion must reconcile exactly: GOOD + BS must equal qty sent';end if;if r.cost_posted then return;end if;
  select * into b from erp.bs_cases where id=r.bs_case_id for update;if b.id is null then raise exception 'BS case not found';end if;v_completed_at:=coalesce(r.completed_at,now());
  if r.qty_good_returned>0 then
    if b.po_id is null or b.product_id is null then raise exception 'GOOD rework return requires native production PO and product lineage';end if;
    if r.return_fg_location_id is not null then select id into v_location from erp.locations where id=r.return_fg_location_id and is_active=true and location_type='FG_WAREHOUSE';if v_location is null then raise exception 'Selected rework return location must be an active FG warehouse';end if;
    else select count(*),(array_agg(id order by id))[1] into v_location_count,v_location from erp.locations where is_active=true and location_type='FG_WAREHOUSE';if v_location_count<>1 then raise exception 'Select return FG warehouse for rework GOOD output; active FG warehouse count is %',v_location_count;end if;end if;
    v_lot_number:='RW-'||r.rework_number||'-'||substr(r.id::text,1,8);
    insert into erp.fg_lots(lot_number,po_id,qc_item_id,cutting_group_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin) values(v_lot_number,b.po_id,b.qc_item_id,b.cutting_group_id,b.product_id,r.qty_good_returned,0,v_completed_at,true,'PRODUCTION') returning id into v_lot;
    perform erp.post_fg_movement(b.product_id,v_lot,v_location,'GRADE_A','REWORK_IN',r.qty_good_returned,0,null,'REWORK_ORDER',r.id,v_completed_at,'GOOD returned from rework',false);
    perform erp.ensure_fg_accessory_cost_snapshot(v_lot);perform erp.post_accessory_reimbursement_accrual(v_lot);
    update erp.rework_orders set good_fg_lot_id=v_lot,return_fg_location_id=v_location,completed_at=v_completed_at where id=r.id;
    insert into erp.bs_resolutions(bs_case_id,resolution_type,qty_pcs,compensation_amount,responsible_contractor_id,responsible_vendor_id,source_rework_order_id,physical_at,notes) values(b.id,case when r.destination_type='CONTRACTOR' then 'REWORK_SEWING' else 'REWORK_LAUNDRY' end,r.qty_good_returned,0,r.contractor_id,r.vendor_id,r.id,v_completed_at,'Recovered to GOOD FG from rework');
  else update erp.rework_orders set completed_at=v_completed_at where id=r.id;end if;
  select greatest(b.qty_pcs-coalesce(sum(br.qty_pcs),0),0)::integer into v_remaining from erp.bs_resolutions br where br.bs_case_id=b.id;
  update erp.bs_cases set status=case when v_remaining=0 then 'RESOLVED' else 'PARTIAL' end,updated_at=now() where id=b.id;
  if r.destination_type='CONTRACTOR' then select coalesce(sum(amount_payable),0) into v_total from erp.rework_component_lines where rework_order_id=r.id;if v_total>0 then perform erp.post_journal('REWORK_COMPLETION',r.id,v_completed_at::date,'Rework labor completion',jsonb_build_array(jsonb_build_object('mapping_key','WIP','debit',round(v_total,2),'credit',0,'contractor_id',r.contractor_id,'po_id',b.po_id),jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',round(v_total,2),'contractor_id',r.contractor_id,'po_id',b.po_id)));end if;end if;
  update erp.rework_orders set cost_posted=true where id=r.id;
  if b.po_id is not null and exists(select 1 from erp.fg_lots where po_id=b.po_id) then perform erp.rebuild_po_hpp(b.po_id,'Rework completion posted with physical GOOD return');perform erp.propagate_conversion_hpp_for_po(b.po_id);perform erp.sync_po_hpp_to_gl(b.po_id,v_completed_at::date);if v_lot is not null then select coalesce(hpp_per_pcs,0) into v_hpp from erp.v_current_hpp where lot_id=v_lot;update erp.fg_stock_movements set unit_hpp_snapshot=v_hpp where lot_id=v_lot and movement_type='REWORK_IN' and source_type='REWORK_ORDER' and source_id=r.id;end if;end if;
end;$function$;

alter function "erp"."post_rework_completion"(p_rework_order_id uuid) owner to "postgres";
