-- bootstrap lines 12093-12130
CREATE OR REPLACE FUNCTION erp.normalize_cutting_group_pickup()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare v_contractor uuid;
begin
  if new.picked_up_at is not null then
    if new.picked_up_at<new.cut_at then
      raise exception 'Tanggal/jam diambil mandor tidak boleh lebih awal dari tanggal/jam potong';
    end if;
    if new.picked_up_at>clock_timestamp()+interval '5 minutes' then
      raise exception 'Tanggal/jam diambil mandor berada di masa depan';
    end if;
    select contractor_id into v_contractor from erp.production_orders where id=new.po_id;
    if v_contractor is null then raise exception 'Assign a mandor to the PO before marking cutting group as picked up'; end if;
    if new.status='CUT' then new.status:='PICKED_UP'; end if;
  end if;

  if tg_op='UPDATE' and old.picked_up_at is not null and new.picked_up_at is null then
    if old.material_issue_posted
       or exists(select 1 from erp.laundry_delivery_lines ldl join erp.laundry_deliveries ld on ld.id=ldl.delivery_id where ldl.cutting_group_id=old.id and ld.status not in('DRAFT','REVERSED'))
       or exists(select 1 from erp.work_completion_events w where w.cutting_group_id=old.id and w.status='POSTED')
       or exists(select 1 from erp.fg_lots fl where fl.cutting_group_id=old.id and fl.lot_origin<>'VOIDED_PRODUCTION') then
      raise exception 'Pickup date cannot be cleared after downstream use';
    end if;
    new.status:='CUT';
  end if;

  if new.picked_up_at is not null and tg_op='UPDATE' and old.picked_up_at is not null and new.status='CUT' then
    raise exception 'Picked-up cutting group cannot return to CUT status directly';
  end if;
  return new;
end;
$function$;

alter function "erp"."normalize_cutting_group_pickup"() owner to "postgres";
