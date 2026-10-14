-- bootstrap lines 25847-25885
CREATE OR REPLACE FUNCTION erp.validate_qc_source_quantity()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_qc_po uuid;v_qc_at timestamptz;v_group_po uuid;v_group_cut_at timestamptz;v_group_pickup timestamptz;
  v_source_po uuid;v_source_good integer;v_already integer;v_receipt_status text;v_receipt_at timestamptz;
begin
  select po_id,physical_at into v_qc_po,v_qc_at from erp.qc_inspections where id=new.inspection_id;
  if v_qc_po is null then raise exception 'QC inspection not found'; end if;
  if new.qty_good_pcs+new.qty_bs_pcs<=0 then raise exception 'QC item must account for at least 1 piece'; end if;
  if new.cutting_group_id is not null then
    select po_id,cut_at,picked_up_at into v_group_po,v_group_cut_at,v_group_pickup from erp.cutting_groups where id=new.cutting_group_id;
    if v_group_po is distinct from v_qc_po then raise exception 'QC cutting group does not belong to QC PO'; end if;
    if v_qc_at<v_group_cut_at then raise exception 'Tanggal/jam QC tidak boleh lebih awal dari tanggal/jam potong'; end if;
    if v_group_pickup is not null and v_qc_at<v_group_pickup then raise exception 'Tanggal/jam QC tidak boleh lebih awal dari tanggal/jam potongan diambil mandor'; end if;
  end if;
  if new.source_laundry_receipt_line_id is not null then
    select ld.po_id,lrl.qty_good_received,lr.status,lr.physical_at
      into v_source_po,v_source_good,v_receipt_status,v_receipt_at
    from erp.laundry_receipt_lines lrl
    join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    where lrl.id=new.source_laundry_receipt_line_id;
    if v_source_po is distinct from v_qc_po or v_receipt_status<>'POSTED' then raise exception 'QC laundry source must be a POSTED receipt from the same PO'; end if;
    if v_qc_at<v_receipt_at then raise exception 'Tanggal/jam QC tidak boleh lebih awal dari barang diterima kembali dari laundry'; end if;
    select coalesce(sum(qii.qty_good_pcs+qii.qty_bs_pcs),0) into v_already
    from erp.qc_inspection_items qii join erp.qc_inspections qi on qi.id=qii.inspection_id
    where qii.source_laundry_receipt_line_id=new.source_laundry_receipt_line_id and qii.id<>new.id and qi.status<>'REVERSED';
    if v_already+new.qty_good_pcs+new.qty_bs_pcs>coalesce(v_source_good,0) then raise exception 'QC accounted quantity exceeds GOOD quantity physically returned from laundry'; end if;
  end if;
  return new;
end;
$function$;

alter function "erp"."validate_qc_source_quantity"() owner to "postgres";
