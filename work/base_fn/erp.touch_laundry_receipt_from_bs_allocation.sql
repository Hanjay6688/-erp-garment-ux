-- bootstrap lines 25016-25033
CREATE OR REPLACE FUNCTION erp.touch_laundry_receipt_from_bs_allocation()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare v_line uuid:=case when tg_op='DELETE' then old.receipt_line_id else new.receipt_line_id end;
begin
  update erp.laundry_receipts lr
  set updated_at=now()
  from erp.laundry_receipt_lines lrl
  where lrl.id=v_line and lr.id=lrl.receipt_id and lr.status='DRAFT';
  if tg_op='DELETE' then return old; else return new; end if;
end;
$function$;

alter function "erp"."touch_laundry_receipt_from_bs_allocation"() owner to "postgres";
