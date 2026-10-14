-- bootstrap lines 25886-25923
CREATE OR REPLACE FUNCTION erp.validate_rework_quantity_state()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_bs_qty integer;v_bs_status text;v_bs_at timestamptz;
  v_resolved integer:=0;v_other_active integer:=0;v_available integer:=0;
  v_require_active_source boolean:=false;
begin
  select qty_pcs,status,physical_at into v_bs_qty,v_bs_status,v_bs_at from erp.bs_cases where id=new.bs_case_id;
  if v_bs_qty is null then raise exception 'BS case not found'; end if;
  v_require_active_source := new.status<>'CANCELLED' and (
       tg_op='INSERT' or new.bs_case_id is distinct from old.bs_case_id or new.qty_sent is distinct from old.qty_sent
       or new.physical_sent_at is distinct from old.physical_sent_at or new.status is distinct from old.status);
  if v_require_active_source and v_bs_status not in ('OPEN','IN_REWORK','PARTIAL') then
    raise exception 'BS case status % tidak dapat memulai/diubah menjadi rework aktif',v_bs_status;
  end if;
  if new.physical_sent_at<v_bs_at then raise exception 'Tanggal/jam kirim rework tidak boleh lebih awal dari waktu BS terdeteksi'; end if;
  if new.physical_sent_at>clock_timestamp()+interval '5 minutes' then raise exception 'Tanggal/jam kirim rework berada di masa depan'; end if;
  if new.completed_at is not null and new.completed_at<new.physical_sent_at then raise exception 'Tanggal/jam selesai rework tidak boleh lebih awal dari waktu kirim rework'; end if;
  if new.completed_at is not null and new.completed_at>clock_timestamp()+interval '5 minutes' then raise exception 'Tanggal/jam selesai rework berada di masa depan'; end if;
  if new.qty_sent<=0 or new.qty_good_returned<0 or new.qty_bs_returned<0 then raise exception 'Rework quantities must be positive/non-negative'; end if;
  if new.qty_good_returned+new.qty_bs_returned>new.qty_sent then raise exception 'Returned GOOD + BS cannot exceed qty sent'; end if;
  if new.status='COMPLETED' and new.qty_good_returned+new.qty_bs_returned<>new.qty_sent then raise exception 'Completed rework must reconcile exactly: GOOD + BS must equal qty sent'; end if;
  if new.status='PARTIAL' and (new.qty_good_returned+new.qty_bs_returned<=0 or new.qty_good_returned+new.qty_bs_returned>=new.qty_sent) then raise exception 'PARTIAL rework must have some returned qty but still leave outstanding qty'; end if;
  if (tg_op='INSERT' or new.bs_case_id is distinct from old.bs_case_id or new.qty_sent is distinct from old.qty_sent) and new.status<>'CANCELLED' then
    select coalesce(sum(br.qty_pcs),0) into v_resolved from erp.bs_resolutions br where br.bs_case_id=new.bs_case_id;
    select coalesce(sum(ro.qty_sent),0) into v_other_active from erp.rework_orders ro
    where ro.bs_case_id=new.bs_case_id and ro.id<>new.id and ro.status in ('OPEN','IN_PROGRESS','PARTIAL');
    v_available:=greatest(v_bs_qty-v_resolved-v_other_active,0);
    if new.qty_sent>v_available then raise exception 'Rework qty sent % exceeds currently available unresolved BS qty %',new.qty_sent,v_available; end if;
  end if;
  return new;
end$function$;

alter function "erp"."validate_rework_quantity_state"() owner to "postgres";
