-- bootstrap lines 13491-13535
CREATE OR REPLACE FUNCTION erp.post_laundry_delivery(p_delivery_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare h erp.laundry_deliveries%rowtype; r record; v_group_total bigint; v_already_sent bigint; v_rate numeric(18,2); v_pickup timestamptz;
begin
  perform erp.require_internal();
  select * into h from erp.laundry_deliveries where id=p_delivery_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Laundry delivery must be DRAFT'; end if;
  if not exists(select 1 from erp.laundry_delivery_lines where delivery_id=h.id) then raise exception 'Laundry delivery has no lines'; end if;
  for r in select * from erp.laundry_delivery_lines where delivery_id=h.id loop
    if not exists(select 1 from erp.cutting_groups cg where cg.id=r.cutting_group_id and cg.po_id=h.po_id) then raise exception 'Cutting group does not belong to delivery PO'; end if;
    select picked_up_at into v_pickup from erp.cutting_groups where id=r.cutting_group_id;
    if v_pickup is null then raise exception 'Cutting group % has not been picked up by the mandor yet',r.cutting_group_id; end if;
    if h.physical_at<v_pickup then raise exception 'Tanggal/jam kirim laundry tidak boleh lebih awal dari tanggal/jam potongan diambil mandor'; end if;
    select total_pcs into v_group_total from erp.v_cutting_group_totals where cutting_group_id=r.cutting_group_id;
    select coalesce(sum(ldl2.qty_sent_pcs),0) into v_already_sent
    from erp.laundry_delivery_lines ldl2 join erp.laundry_deliveries ld2 on ld2.id=ldl2.delivery_id
    where ldl2.cutting_group_id=r.cutting_group_id and ld2.id<>h.id and ld2.status not in('DRAFT','REVERSED');
    if coalesce(v_group_total,0)<v_already_sent+r.qty_sent_pcs then
      raise exception 'Laundry qty exceeds effective cutting qty for group %. Effective %, already sent %, requested %. Post a local cutting quantity correction instead of reversing sibling groups.',r.cutting_group_id,coalesce(v_group_total,0),v_already_sent,r.qty_sent_pcs;
    end if;
    v_rate:=r.estimated_rate_snapshot;
    if v_rate is null and h.target_wash_process_id is not null then
      perform pg_advisory_xact_lock(hashtextextended('LRATE:'||h.vendor_id::text||':'||h.target_wash_process_id::text,0));
      select rate_per_pcs into v_rate from erp.laundry_vendor_rate_versions
      where vendor_id=h.vendor_id and wash_process_id=h.target_wash_process_id and effective_from<=h.physical_at and (effective_to is null or effective_to>h.physical_at)
      order by effective_from desc,created_at desc limit 1;
      if v_rate is not null then update erp.laundry_delivery_lines set estimated_rate_snapshot=v_rate,estimated_cost_status='ESTIMATED' where id=r.id; end if;
    end if;
    insert into erp.wip_stage_events(po_id,cutting_group_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by,notes)
    select h.po_id,r.cutting_group_id,'SEWING','LAUNDRY',r.qty_sent_pcs,po.contractor_id,'LAUNDRY_DELIVERY_LINE',r.id,h.physical_at,erp.current_app_user_id(),h.target_dyeing_color
    from erp.production_orders po where po.id=h.po_id;
    update erp.cutting_groups set status='LAUNDRY' where id=r.cutting_group_id;
  end loop;
  update erp.laundry_deliveries set status='SENT',updated_at=now() where id=h.id;
  update erp.production_orders set status='LAUNDRY',current_stage='LAUNDRY',updated_at=now() where id=h.po_id;
  perform erp.sync_laundry_accrual(h.po_id,h.physical_at::date);
end;
$function$;

alter function "erp"."post_laundry_delivery"(p_delivery_id uuid) owner to "postgres";
