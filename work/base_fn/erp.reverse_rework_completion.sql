-- bootstrap lines 19307-19379
CREATE OR REPLACE FUNCTION erp.reverse_rework_completion(p_rework_order_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r erp.rework_orders%rowtype;
  b erp.bs_cases%rowtype;
  x record;
  v_journal uuid;
  v_total numeric(24,6):=0;
  v_remaining integer:=0;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal hasil rework wajib diisi'; end if;
  select * into r from erp.rework_orders where id=p_rework_order_id for update;
  if r.id is null then raise exception 'Rework order tidak ditemukan'; end if;
  if r.status='CANCELLED' and r.cost_posted then return; end if;
  if r.status<>'COMPLETED' or not r.cost_posted then raise exception 'Hanya rework COMPLETED yang sudah diposting biayanya yang dapat direverse'; end if;
  select * into b from erp.bs_cases where id=r.bs_case_id for update;

  if exists(
    select 1 from erp.payroll_work_items pwi
    join erp.payroll_settlements ps on ps.id=pwi.payroll_id
    join erp.rework_component_lines rcl on rcl.id=pwi.source_id
    where pwi.source_type='REWORK' and rcl.rework_order_id=r.id and ps.status<>'REVERSED'
  ) then raise exception 'Upah rework ini sudah masuk payroll. Cancel/reverse payroll aktif terlebih dahulu.'; end if;

  if r.good_fg_lot_id is not null then
    if erp.fg_lot_has_active_downstream(r.good_fg_lot_id,'REWORK_IN','REWORK_ORDER',r.id) then
      raise exception 'FG hasil rework masih dipakai transaksi downstream aktif. Reverse transaksi downstream terlebih dahulu.';
    end if;
    if exists(select 1 from erp.contractor_accessory_reimbursement_entitlements e where e.lot_id=r.good_fg_lot_id and e.payroll_status<>'UNALLOCATED') then
      raise exception 'Reimbursement aksesori hasil rework sudah masuk payroll. Cancel/reverse payroll terlebih dahulu.';
    end if;
  end if;

  select coalesce(sum(amount_payable),0) into v_total from erp.rework_component_lines where rework_order_id=r.id;
  select id into v_journal from erp.journal_entries where source_type='REWORK_COMPLETION' and source_id=r.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if r.destination_type='CONTRACTOR' and v_total>0.005 and v_journal is null then raise exception 'Jurnal biaya/upah rework tidak ditemukan; reversal dibatalkan agar hutang mandor/HPP tidak rusak'; end if;

  if r.good_fg_lot_id is not null then
    select id into v_journal from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=r.good_fg_lot_id and status='POSTED' order by posting_at desc,id desc limit 1;
    if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
    update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=r.good_fg_lot_id and payroll_status='UNALLOCATED';
    for x in select fm.id from erp.fg_stock_movements fm where fm.lot_id=r.good_fg_lot_id and fm.movement_type='REWORK_IN' and fm.source_type='REWORK_ORDER' and fm.source_id=r.id and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)
    loop perform erp.reverse_fg_movement(x.id,p_reason); end loop;
    update erp.fg_lots set lot_origin='VOIDED_PRODUCTION',is_open=false where id=r.good_fg_lot_id and lot_origin='PRODUCTION';
  end if;

  select id into v_journal from erp.journal_entries where source_type='REWORK_COMPLETION' and source_id=r.id and status='POSTED' order by posting_at desc,id desc limit 1;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  delete from erp.bs_resolutions where source_rework_order_id=r.id;
  update erp.rework_orders set status='CANCELLED',updated_at=now(),notes=concat_ws(E'\n',notes,'CANCELLED after posted completion reversal: '||p_reason) where id=r.id;

  select greatest(b.qty_pcs-coalesce(sum(br.qty_pcs),0),0)::integer into v_remaining from erp.bs_resolutions br where br.bs_case_id=b.id;
  if v_remaining<=0 then update erp.bs_cases set status='RESOLVED',updated_at=now() where id=b.id;
  elsif exists(select 1 from erp.rework_orders ro where ro.bs_case_id=b.id and ro.id<>r.id and ro.status in ('OPEN','IN_PROGRESS','PARTIAL')) then update erp.bs_cases set status='IN_REWORK',updated_at=now() where id=b.id;
  elsif v_remaining<b.qty_pcs then update erp.bs_cases set status='PARTIAL',updated_at=now() where id=b.id;
  else update erp.bs_cases set status='OPEN',updated_at=now() where id=b.id; end if;

  if b.po_id is not null then
    perform erp.rebuild_po_hpp(b.po_id,'Rework completion reversed: '||p_reason);
    perform erp.propagate_conversion_hpp_for_po(b.po_id);
    perform erp.sync_po_hpp_to_gl(b.po_id,current_date);
  end if;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason) values('rework_orders',r.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;

alter function "erp"."reverse_rework_completion"(p_rework_order_id uuid, p_reason text) owner to "postgres";
