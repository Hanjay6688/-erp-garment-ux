-- bootstrap lines 18201-18324
CREATE OR REPLACE FUNCTION erp.reverse_laundry_receipt(p_receipt_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  h erp.laundry_receipts%rowtype;
  d erp.laundry_deliveries%rowtype;
  r record;
  b record;
  v_sent bigint;
  v_returned bigint;
  v_po_status text;
begin
  perform erp.require_owner_admin();
  if nullif(btrim(p_reason),'') is null then raise exception 'Alasan reversal penerimaan laundry wajib diisi'; end if;
  select * into h from erp.laundry_receipts where id=p_receipt_id for update;
  if h.id is null then raise exception 'Penerimaan laundry tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya penerimaan laundry POSTED yang dapat direverse'; end if;
  select * into d from erp.laundry_deliveries where id=h.delivery_id for update;
  if d.id is null or d.status='REVERSED' then raise exception 'Pengiriman laundry sumber tidak aktif'; end if;
  select status into v_po_status from erp.production_orders where id=d.po_id for update;
  if v_po_status='FINISHED' then
    raise exception 'PO sudah FINISHED. Reopen/koreksi transaksi downstream terlebih dahulu sebelum reversal penerimaan laundry.';
  end if;

  perform erp.assert_laundry_receipt_reversal_payroll_safe(h.id);
  if exists(
    select 1 from erp.qc_inspection_items qi
    join erp.qc_inspections qh on qh.id=qi.inspection_id
    where qi.source_laundry_receipt_line_id in(select id from erp.laundry_receipt_lines where receipt_id=h.id)
      and qh.status<>'REVERSED'
  ) then raise exception 'Penerimaan laundry ini sudah dipakai QC. Reverse QC aktif terlebih dahulu.'; end if;
  if exists(
    select 1 from erp.vendor_invoice_items vii join erp.vendor_invoices vi on vi.id=vii.invoice_id
    where vii.receipt_line_id in(select id from erp.laundry_receipt_lines where receipt_id=h.id)
      and vi.status<>'REVERSED'
  ) then raise exception 'Penerimaan laundry ini sudah masuk invoice vendor. Reverse invoice vendor aktif terlebih dahulu.'; end if;
  if exists(
    select 1 from erp.laundry_claims lc
    where (lc.receipt_line_id in(select id from erp.laundry_receipt_lines where receipt_id=h.id) or lc.delivery_id=d.id)
      and lc.status<>'REJECTED'
  ) then raise exception 'Penerimaan/delivery laundry ini sudah memiliki claim aktif/terselesaikan. Bereskan claim terlebih dahulu.'; end if;

  for r in select * from erp.laundry_receipt_lines where receipt_id=h.id and qty_bs_laundry>0
  loop
    for b in
      select * from erp.bs_cases bc
      where bc.source_laundry_receipt_line_id=r.id
         or bc.bs_number='BS-LAU-'||h.receipt_number||'-'||substr(r.id::text,1,8)
      for update
    loop
      if exists(select 1 from erp.rework_orders where bs_case_id=b.id and status<>'CANCELLED')
         or exists(select 1 from erp.bs_resolutions where bs_case_id=b.id) then
        raise exception 'BS dari penerimaan laundry ini sudah diproses/rework. Batalkan downstream BS terlebih dahulu.';
      end if;
      update erp.bs_cases
      set status='CANCELLED',notes=concat_ws(E'\n',notes,'CANCELLED karena source laundry receipt direverse: '||p_reason),updated_at=now()
      where id=b.id;
    end loop;
  end loop;

  update erp.laundry_receipts set status='REVERSED',updated_at=now() where id=h.id;
  select coalesce(sum(qty_sent_pcs),0) into v_sent from erp.laundry_delivery_lines where delivery_id=d.id;
  select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0) into v_returned
  from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
  where lr.delivery_id=d.id and lr.status='POSTED';
  update erp.laundry_deliveries
  set status=case when v_returned>=v_sent and v_sent>0 then 'RETURNED'
                  when v_returned>0 then 'PARTIAL_RETURN' else 'SENT' end,
      updated_at=now()
  where id=d.id;

  for r in
    select distinct ldl.cutting_group_id
    from erp.laundry_receipt_lines lrl
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    where lrl.receipt_id=h.id
  loop
    if exists(
      select 1 from erp.laundry_receipt_lines x
      join erp.laundry_receipts xr on xr.id=x.receipt_id
      join erp.laundry_delivery_lines xdl on xdl.id=x.delivery_line_id
      where xdl.cutting_group_id=r.cutting_group_id and xr.status='POSTED'
    ) then update erp.cutting_groups set status='RETURNED' where id=r.cutting_group_id;
    elsif exists(
      select 1 from erp.laundry_delivery_lines xdl
      join erp.laundry_deliveries xd on xd.id=xdl.delivery_id
      where xdl.cutting_group_id=r.cutting_group_id and xd.status not in('DRAFT','REVERSED')
    ) then update erp.cutting_groups set status='LAUNDRY' where id=r.cutting_group_id;
    else update erp.cutting_groups
      set status=case when picked_up_at is not null then 'PICKED_UP' else 'CUT' end
      where id=r.cutting_group_id;
    end if;
  end loop;

  if v_po_status not in ('ON_HOLD','CANCELLED') then
    if exists(select 1 from erp.qc_inspections where po_id=d.po_id and status='POSTED')
       or exists(select 1 from erp.laundry_receipts lr join erp.laundry_deliveries ld on ld.id=lr.delivery_id
                 where ld.po_id=d.po_id and lr.status='POSTED' and ld.status<>'REVERSED') then
      update erp.production_orders set status='QC',current_stage='QC',updated_at=now() where id=d.po_id;
    elsif exists(select 1 from erp.laundry_deliveries where po_id=d.po_id and status not in('DRAFT','REVERSED')) then
      update erp.production_orders set status='LAUNDRY',current_stage='LAUNDRY',updated_at=now() where id=d.po_id;
    elsif exists(select 1 from erp.cutting_groups where po_id=d.po_id and picked_up_at is not null) then
      update erp.production_orders set status='SEWING',current_stage='SEWING',updated_at=now() where id=d.po_id;
    else update erp.production_orders set status='CUTTING',current_stage='CUTTING',updated_at=now() where id=d.po_id;
    end if;
  end if;

  perform erp.sync_laundry_accrual(d.po_id,current_date);
  if exists(select 1 from erp.fg_lots where po_id=d.po_id) then
    perform erp.rebuild_po_hpp(d.po_id,'Laundry receipt reversed: '||p_reason);
    perform erp.propagate_conversion_hpp_for_po(d.po_id);
    perform erp.sync_po_hpp_to_gl(d.po_id,current_date);
  end if;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('laundry_receipts',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

alter function "erp"."reverse_laundry_receipt"(p_receipt_id uuid, p_reason text) owner to "postgres";
