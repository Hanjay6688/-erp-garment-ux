CREATE OR REPLACE FUNCTION erp.reverse_qc(p_qc_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.qc_inspections%rowtype;
  r record; l record; b record;
  v_journal uuid;
  v_po_status text;
begin
  perform erp.require_internal();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal QC wajib diisi'; end if;
  select * into h from erp.qc_inspections where id=p_qc_id for update;
  if h.id is null then raise exception 'QC tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception using message='Hanya QC POSTED yang dapat direverse. QC '||coalesce(h.inspection_number,'')||' berstatus '||h.status||'.'; end if;
  select status into v_po_status from erp.production_orders where id=h.po_id for update;
  if v_po_status='FINISHED' then raise exception using message='PO sudah FINISHED. Reopen/koreksi downstream terlebih dahulu sebelum reversal QC.'||cp7_fg_correction_source.qc_blocker_text_v1(h.id),detail=cp7_fg_correction_source.qc_blockers_v1(h.id)::text; end if;

  for b in select bc.* from erp.bs_cases bc where bc.qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id) and bc.status<>'CANCELLED' for update loop
    if exists(select 1 from erp.rework_orders where bs_case_id=b.id and status<>'CANCELLED')
       or exists(select 1 from erp.bs_resolutions where bs_case_id=b.id) then
      raise exception using message='BS hasil QC ini sudah diproses/rework. Batalkan downstream BS terlebih dahulu.'||cp7_fg_correction_source.qc_blocker_text_v1(h.id),detail=cp7_fg_correction_source.qc_blockers_v1(h.id)::text;
    end if;
  end loop;

  for l in
    select fl.* from erp.fg_lots fl
    where fl.qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id)
      and fl.lot_origin='PRODUCTION'
    for update
  loop
    if erp.fg_lot_has_active_downstream(l.id,'QC_GOOD','QC_ITEM',l.qc_item_id) then
      raise exception using message='FG hasil QC masih dipakai transaksi downstream aktif. Reverse transaksi downstream terlebih dahulu.'||cp7_fg_correction_source.qc_blocker_text_v1(h.id),detail=cp7_fg_correction_source.qc_blockers_v1(h.id)::text;
    end if;
    if exists(select 1 from erp.contractor_accessory_reimbursement_entitlements e where e.lot_id=l.id and e.payroll_status<>'UNALLOCATED') then
      raise exception using message='Hak reimbursement aksesori dari QC ini sudah masuk payroll. Cancel/reverse payroll terlebih dahulu.'||cp7_fg_correction_source.qc_blocker_text_v1(h.id),detail=cp7_fg_correction_source.qc_blockers_v1(h.id)::text;
    end if;
  end loop;

  for l in
    select fl.* from erp.fg_lots fl
    where fl.qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id) and fl.lot_origin='PRODUCTION'
    for update
  loop
    select id into v_journal from erp.journal_entries
    where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=l.id and status='POSTED'
    order by posting_at desc,id desc limit 1;
    if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
    -- AZ rev2: the lot's accessory HPP recost journals go with its accrual.
    for v_journal in select je.id from erp.journal_entries je join erp.fg_accessory_cost_revisions rv on rv.id=je.source_id
      join erp.fg_accessory_cost_snapshots sn on sn.id=rv.snapshot_id
      where je.source_type='ACCESSORY_HPP_RECOST' and je.status='POSTED' and sn.lot_id=l.id order by je.posting_at,je.id
    loop perform erp.reverse_journal(v_journal,p_reason); end loop;
    update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=l.id and payroll_status='UNALLOCATED';
    for r in select fm.id from erp.fg_stock_movements fm where fm.lot_id=l.id and fm.movement_type='QC_GOOD' and fm.source_type='QC_ITEM' and fm.source_id=l.qc_item_id and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id) loop
      perform erp.reverse_fg_movement(r.id,p_reason);
    end loop;
    update erp.fg_lots set lot_origin='VOIDED_PRODUCTION',is_open=false where id=l.id;
  end loop;

  update erp.bs_cases set status='CANCELLED',notes=concat_ws(E'\n',notes,'CANCELLED karena source QC direverse: '||p_reason),updated_at=statement_timestamp()
  where qc_item_id in (select id from erp.qc_inspection_items where inspection_id=h.id) and status<>'CANCELLED';
  update erp.qc_inspections set status='REVERSED',updated_at=statement_timestamp() where id=h.id;

  if v_po_status not in ('ON_HOLD','CANCELLED') then
    if exists(select 1 from erp.qc_inspections where po_id=h.po_id and status='POSTED')
       or exists(select 1 from erp.laundry_receipts lr join erp.laundry_deliveries ld on ld.id=lr.delivery_id where ld.po_id=h.po_id and lr.status='POSTED' and ld.status<>'REVERSED') then
      update erp.production_orders set status='QC',current_stage='QC',updated_at=statement_timestamp() where id=h.po_id;
    elsif exists(select 1 from erp.laundry_deliveries where po_id=h.po_id and status not in('DRAFT','REVERSED')) then
      update erp.production_orders set status='LAUNDRY',current_stage='LAUNDRY',updated_at=statement_timestamp() where id=h.po_id;
    elsif exists(select 1 from erp.cutting_groups where po_id=h.po_id and picked_up_at is not null) then
      update erp.production_orders set status='SEWING',current_stage='SEWING',updated_at=statement_timestamp() where id=h.po_id;
    else
      update erp.production_orders set status='CUTTING',current_stage='CUTTING',updated_at=statement_timestamp() where id=h.po_id;
    end if;
  end if;

  perform erp.sync_laundry_accrual(h.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  perform erp.rebuild_po_hpp(h.po_id,'QC reversed: '||p_reason);
  perform erp.propagate_conversion_hpp_for_po(h.po_id);
  perform erp.sync_po_hpp_to_gl(h.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('qc_inspections',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$
