-- bootstrap lines 9489-9529
CREATE OR REPLACE FUNCTION erp.guard_laundry_claim_capacity_on_resolution()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_sent bigint;
  v_returned bigint;
  v_claimed bigint;
  v_bs bigint;
begin
  if new.status in ('SETTLED','WRITTEN_OFF') and old.status is distinct from new.status then
    if new.claim_type in ('MISSING','STUCK') then
      perform 1 from erp.laundry_deliveries where id=new.delivery_id for update;
      select coalesce(sum(qty_sent_pcs),0) into v_sent from erp.laundry_delivery_lines where delivery_id=new.delivery_id;
      select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0) into v_returned
      from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
      where lr.delivery_id=new.delivery_id and lr.status='POSTED';
      select coalesce(sum(qty_claimed),0) into v_claimed
      from erp.laundry_claims
      where delivery_id=new.delivery_id and claim_type in ('MISSING','STUCK') and status<>'REJECTED';
      if v_claimed>greatest(v_sent-v_returned,0) then
        raise exception 'Laundry claim resolution exceeds physical outstanding quantity. Outstanding %, active claims %. Reject/correct duplicate claim first.',greatest(v_sent-v_returned,0),v_claimed;
      end if;
    elsif new.claim_type='DAMAGE' then
      if new.receipt_line_id is null then raise exception 'Laundry DAMAGE claim must reference a receipt line'; end if;
      select qty_bs_laundry into v_bs from erp.laundry_receipt_lines where id=new.receipt_line_id for update;
      select coalesce(sum(qty_claimed),0) into v_claimed
      from erp.laundry_claims
      where receipt_line_id=new.receipt_line_id and claim_type='DAMAGE' and status<>'REJECTED';
      if v_claimed>coalesce(v_bs,0) then
        raise exception 'Laundry DAMAGE claim resolution exceeds BS quantity on source receipt. BS %, active claims %. Reject/correct duplicate claim first.',coalesce(v_bs,0),v_claimed;
      end if;
    end if;
  end if;
  return new;
end;
$function$;

alter function "erp"."guard_laundry_claim_capacity_on_resolution"() owner to "postgres";
