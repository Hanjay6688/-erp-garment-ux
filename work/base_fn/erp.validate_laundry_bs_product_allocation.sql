-- bootstrap lines 25373-25415
CREATE OR REPLACE FUNCTION erp.validate_laundry_bs_product_allocation()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_status text;
  v_physical_at timestamptz;
  v_po_model uuid;
  v_product_model uuid;
  v_product_size uuid;
  v_group uuid;
begin
  select lr.status,lr.physical_at,po.model_id,p.model_id,p.size_id,ldl.cutting_group_id
  into v_status,v_physical_at,v_po_model,v_product_model,v_product_size,v_group
  from erp.laundry_receipt_lines lrl
  join erp.laundry_receipts lr on lr.id=lrl.receipt_id
  join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  join erp.production_orders po on po.id=ld.po_id
  join erp.products p on p.id=new.product_id
  where lrl.id=new.receipt_line_id;

  if v_status is null then raise exception 'Laundry receipt line/product not found'; end if;
  if v_status<>'DRAFT' then raise exception 'Laundry BS product allocation is editable only while receipt is DRAFT'; end if;
  if v_product_model is distinct from v_po_model then
    raise exception 'Laundry BS product model does not match the production order model';
  end if;
  if not exists(
    select 1 from erp.cutting_group_size_slots s
    where s.cutting_group_id=v_group and s.size_id=v_product_size
  ) then
    raise exception 'Laundry BS product size is not present in the source Potongan';
  end if;
  perform erp.assert_product_identity_time(new.product_id,v_physical_at,'NEW_STOCK');
  new.created_by:=coalesce(new.created_by,erp.current_app_user_id());
  return new;
end;
$function$;

alter function "erp"."validate_laundry_bs_product_allocation"() owner to "postgres";
