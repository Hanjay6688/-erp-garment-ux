-- bootstrap lines 16728-16786
CREATE OR REPLACE FUNCTION erp.reopen_production_order(p_po_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_status text;
  v_stage text;
  r record;
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then
    raise exception 'Alasan reopen PO wajib diisi';
  end if;

  select status into v_status from erp.production_orders where id=p_po_id for update;
  if v_status is null then raise exception 'PO tidak ditemukan'; end if;
  if v_status<>'FINISHED' then
    raise exception 'Hanya PO FINISHED yang dapat direopen. Status saat ini %',v_status;
  end if;

  for r in
    select je.id
    from erp.po_wip_close_events e
    join erp.journal_entries je on je.id=e.journal_entry_id
    where e.po_id=p_po_id and je.source_type='PO_WIP_RESIDUAL_CLOSE' and je.status='POSTED'
    order by je.posting_at desc,je.id desc
  loop
    perform erp.reverse_journal(r.id,'Reopen PO: '||p_reason);
  end loop;

  if exists(select 1 from erp.qc_inspections q where q.po_id=p_po_id and q.status='POSTED')
     or exists(select 1 from erp.laundry_receipts lr join erp.laundry_deliveries ld on ld.id=lr.delivery_id where ld.po_id=p_po_id and lr.status='POSTED' and ld.status<>'REVERSED')
     or exists(select 1 from erp.fg_lots fl where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION') then
    v_stage:='QC';
  elsif exists(select 1 from erp.laundry_deliveries ld where ld.po_id=p_po_id and ld.status not in('DRAFT','REVERSED')) then
    v_stage:='LAUNDRY';
  elsif exists(select 1 from erp.cutting_groups cg where cg.po_id=p_po_id and cg.picked_up_at is not null) then
    v_stage:='SEWING';
  elsif exists(select 1 from erp.cutting_groups cg where cg.po_id=p_po_id) then
    v_stage:='CUTTING';
  else
    v_stage:='DRAFT';
  end if;

  update erp.production_orders
  set status=case when v_stage='DRAFT' then 'DRAFT' else v_stage end,
      current_stage=case when v_stage='DRAFT' then 'CUTTING' else v_stage end,
      updated_at=now()
  where id=p_po_id;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('production_orders',p_po_id,'UPDATE',jsonb_build_object('correction_type','PO_REOPEN','previous_status','FINISHED','restored_stage',v_stage),erp.current_app_user_id(),p_reason);
end;
$function$;

alter function "erp"."reopen_production_order"(p_po_id uuid, p_reason text) owner to "postgres";
