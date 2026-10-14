-- bootstrap lines 13536-13643
CREATE OR REPLACE FUNCTION erp.post_laundry_receipt(p_receipt_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  h erp.laundry_receipts%rowtype;
  d erp.laundry_deliveries%rowtype;
  r record;
  a record;
  v_sent bigint;
  v_returned bigint;
  v_allocated integer;
  v_bs_number text;
begin
  perform erp.require_internal();
  select * into h from erp.laundry_receipts where id=p_receipt_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Laundry receipt must be DRAFT'; end if;
  select * into d from erp.laundry_deliveries where id=h.delivery_id for update;
  if d.status not in ('SENT','PARTIAL_RETURN') then raise exception 'Laundry delivery must already be sent'; end if;
  if not exists(select 1 from erp.laundry_receipt_lines where receipt_id=h.id) then
    raise exception 'Laundry receipt has no lines';
  end if;

  for r in
    select lrl.*,ldl.cutting_group_id
    from erp.laundry_receipt_lines lrl
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    where lrl.receipt_id=h.id order by lrl.id
  loop
    select coalesce(sum(x.qty_bs),0)::integer into v_allocated
    from erp.laundry_receipt_bs_product_allocations x where x.receipt_line_id=r.id;
    if v_allocated<>r.qty_bs_laundry then
      raise exception 'Laundry BS product allocation % must equal BS qty % for receipt line %',
        v_allocated,r.qty_bs_laundry,r.id;
    end if;

    if r.qty_good_received+r.qty_bs_laundry>0 and exists(
      select 1
      from erp.laundry_claims lc
      left join erp.laundry_receipt_lines prior_line on prior_line.id=lc.receipt_line_id
      where lc.status in ('SETTLED','WRITTEN_OFF')
        and lc.claim_type in ('MISSING','STUCK')
        and (
          prior_line.delivery_line_id=r.delivery_line_id
          or (lc.receipt_line_id is null and lc.delivery_id=d.id)
        )
    ) then
      raise exception 'Late physical return is blocked after a STUCK/MISSING claim is SETTLED/WRITTEN_OFF; reverse the claim resolution first';
    end if;

    if r.qty_good_received+r.qty_bs_laundry>0 then
      insert into erp.wip_stage_events(
        po_id,cutting_group_id,stage_from,stage_to,qty_pcs,
        source_type,source_id,physical_at,created_by,notes
      ) values(
        d.po_id,r.cutting_group_id,'LAUNDRY','QC',r.qty_good_received+r.qty_bs_laundry,
        'LAUNDRY_RECEIPT_LINE',r.id,h.physical_at,erp.current_app_user_id(),
        'Physically returned from laundry'
      );
      update erp.cutting_groups set status='RETURNED' where id=r.cutting_group_id;
    end if;

    for a in
      select * from erp.laundry_receipt_bs_product_allocations
      where receipt_line_id=r.id order by id
    loop
      perform erp.assert_product_identity_time(a.product_id,h.physical_at,'NEW_STOCK');
      v_bs_number:='BS-LAU-'||left(h.receipt_number,28)||'-'||substr(r.id::text,1,8)||'-'||substr(a.id::text,1,6);
      insert into erp.bs_cases(
        bs_number,po_id,cutting_group_id,product_id,
        source_laundry_receipt_line_id,source_laundry_bs_allocation_id,
        detected_at_stage,cause_source,responsible_vendor_id,
        qty_pcs,status,physical_at,notes
      ) values(
        v_bs_number,d.po_id,r.cutting_group_id,a.product_id,r.id,a.id,
        'LAUNDRY','LAUNDRY',d.vendor_id,a.qty_bs,'OPEN',h.physical_at,
        'Auto-created from laundry receipt with product/size lineage'
      ) on conflict(source_laundry_bs_allocation_id) where source_laundry_bs_allocation_id is not null do nothing;
    end loop;
  end loop;

  update erp.laundry_receipts set status='POSTED',updated_at=now() where id=h.id;
  select coalesce(sum(qty_sent_pcs),0) into v_sent
  from erp.laundry_delivery_lines where delivery_id=d.id;
  select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0) into v_returned
  from erp.laundry_receipt_lines lrl
  join erp.laundry_receipts lr on lr.id=lrl.receipt_id
  where lr.delivery_id=d.id and lr.status='POSTED';
  update erp.laundry_deliveries
  set status=case when v_returned>=v_sent then 'RETURNED' else 'PARTIAL_RETURN' end,
      updated_at=now()
  where id=d.id;
  if v_returned>0 then
    update erp.production_orders set status='QC',current_stage='QC',updated_at=now() where id=d.po_id;
  end if;
  perform erp.sync_laundry_accrual(d.po_id,h.physical_at::date);
  if exists(select 1 from erp.fg_lots where po_id=d.po_id) then
    perform erp.rebuild_po_hpp(d.po_id,'Laundry receipt posted/corrected');
    perform erp.propagate_conversion_hpp_for_po(d.po_id);
    perform erp.sync_po_hpp_to_gl(d.po_id,h.physical_at::date);
  end if;
end;
$function$;

alter function "erp"."post_laundry_receipt"(p_receipt_id uuid) owner to "postgres";
