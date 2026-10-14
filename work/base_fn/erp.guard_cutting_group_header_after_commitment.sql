-- bootstrap lines 9232-9294
CREATE OR REPLACE FUNCTION erp.guard_cutting_group_header_after_commitment()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_committed boolean := false;
  v_has_downstream boolean := false;
  v_earliest timestamptz;
  v_status_allowed boolean := false;
begin
  if current_user in ('postgres','service_role','supabase_admin') then return new; end if;

  v_has_downstream :=
       exists(select 1 from erp.laundry_delivery_lines ldl join erp.laundry_deliveries ld on ld.id=ldl.delivery_id where ldl.cutting_group_id=old.id and ld.status not in('DRAFT','REVERSED'))
    or exists(select 1 from erp.work_completion_events w where w.cutting_group_id=old.id and w.status<>'DRAFT')
    or exists(select 1 from erp.qc_inspection_items q join erp.qc_inspections qi on qi.id=q.inspection_id where q.cutting_group_id=old.id and qi.status<>'DRAFT')
    or exists(select 1 from erp.fg_lots f where f.cutting_group_id=old.id and f.lot_origin<>'VOIDED_PRODUCTION')
    or exists(select 1 from erp.bs_cases b where b.cutting_group_id=old.id and b.status<>'CANCELLED')
    or exists(select 1 from erp.scrap_batches s where s.source_cutting_group_id=old.id);

  v_committed := not erp.is_cutting_group_presewing_reversible(old.id);
  if v_committed and (
       new.po_id is distinct from old.po_id
    or new.cutting_batch_id is distinct from old.cutting_batch_id
    or new.group_number is distinct from old.group_number
    or new.cut_at is distinct from old.cut_at
  ) then
    raise exception 'Potongan sudah dijahit/dipakai operasional. Identitas dan batch tidak boleh diganti langsung.';
  end if;

  if new.status is distinct from old.status then
    v_status_allowed :=
      (old.status='CUT' and new.status='PICKED_UP' and old.picked_up_at is null and new.picked_up_at is not null)
      or
      (old.status='PICKED_UP' and new.status='CUT' and old.picked_up_at is not null and new.picked_up_at is null and not v_committed);
    if not v_status_allowed then
      raise exception 'Status Potongan mengikuti pickup/posting fisik dan tidak boleh diganti manual.';
    end if;
  end if;

  if old.picked_up_at is not null
     and new.picked_up_at is distinct from old.picked_up_at
     and new.picked_up_at is not null then
    select min(x.ts) into v_earliest from (
      select ld.physical_at ts from erp.laundry_delivery_lines ldl join erp.laundry_deliveries ld on ld.id=ldl.delivery_id where ldl.cutting_group_id=old.id and ld.status not in('DRAFT','REVERSED')
      union all
      select w.physical_at from erp.work_completion_events w where w.cutting_group_id=old.id and w.status<>'DRAFT'
      union all
      select q.physical_at from erp.qc_inspection_items qi join erp.qc_inspections q on q.id=qi.inspection_id where qi.cutting_group_id=old.id and q.status<>'DRAFT'
      union all
      select f.produced_at from erp.fg_lots f where f.cutting_group_id=old.id and f.lot_origin<>'VOIDED_PRODUCTION'
    ) x where x.ts is not null;
    if v_earliest is not null and new.picked_up_at > v_earliest then
      raise exception 'Tanggal pickup baru melewati transaksi downstream paling awal %', v_earliest;
    end if;
  end if;
  return new;
end;
$function$;

alter function "erp"."guard_cutting_group_header_after_commitment"() owner to "postgres";
