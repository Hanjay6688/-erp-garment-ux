-- bootstrap lines 25416-25471
CREATE OR REPLACE FUNCTION erp.validate_laundry_claim_lineage()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_delivery_vendor uuid;
  v_line_delivery uuid;
  v_bs integer;
  v_sent integer;
  v_returned integer;
  v_other_claimed integer;
begin
  if new.delivery_id is null then
    if new.receipt_line_id is null then raise exception 'Laundry claim requires delivery or receipt line'; end if;
    select lr.delivery_id into new.delivery_id
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lrl.id=new.receipt_line_id;
  end if;

  perform 1 from erp.laundry_deliveries where id=new.delivery_id for update;
  select vendor_id into v_delivery_vendor from erp.laundry_deliveries where id=new.delivery_id;
  if v_delivery_vendor is null then raise exception 'Laundry delivery not found'; end if;
  if new.vendor_id is distinct from v_delivery_vendor then raise exception 'Laundry claim vendor must match delivery vendor'; end if;

  if new.receipt_line_id is not null then
    perform 1 from erp.laundry_receipt_lines where id=new.receipt_line_id for update;
    select lr.delivery_id,lrl.qty_bs_laundry into v_line_delivery,v_bs
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lrl.id=new.receipt_line_id;
    if v_line_delivery is distinct from new.delivery_id then raise exception 'Laundry claim receipt line does not belong to delivery'; end if;
  end if;

  if new.claim_type in ('MISSING','STUCK') then
    select coalesce(sum(ldl.qty_sent_pcs),0) into v_sent from erp.laundry_delivery_lines ldl where ldl.delivery_id=new.delivery_id;
    select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0) into v_returned
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lr.delivery_id=new.delivery_id and lr.status='POSTED';
    select coalesce(sum(lc.qty_claimed),0) into v_other_claimed
    from erp.laundry_claims lc
    where lc.delivery_id=new.delivery_id and lc.id<>new.id and lc.claim_type in ('MISSING','STUCK') and lc.status not in ('REJECTED');
    if v_other_claimed+new.qty_claimed>greatest(v_sent-v_returned,0) then
      raise exception 'Laundry missing/stuck claims exceed currently unreturned quantity. Outstanding %, other claims %, requested %',greatest(v_sent-v_returned,0),v_other_claimed,new.qty_claimed;
    end if;
  elsif new.claim_type='DAMAGE' then
    if new.receipt_line_id is null then raise exception 'Laundry DAMAGE claim must reference the receipt line where damaged/BS pieces returned'; end if;
    select coalesce(sum(lc.qty_claimed),0) into v_other_claimed from erp.laundry_claims lc
    where lc.receipt_line_id=new.receipt_line_id and lc.id<>new.id and lc.claim_type='DAMAGE' and lc.status<>'REJECTED';
    if v_other_claimed+new.qty_claimed>coalesce(v_bs,0) then raise exception 'Laundry DAMAGE claim exceeds BS quantity on receipt line'; end if;
  end if;
  return new;
end;
$function$;

alter function "erp"."validate_laundry_claim_lineage"() owner to "postgres";
