-- bootstrap lines 10750-10844
CREATE OR REPLACE FUNCTION erp.guard_qc_posting_consistency()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  r record;
  v_effective bigint;
  v_prior bigint;
  v_current bigint;
  v_source_good bigint;
  v_source_po uuid;
  v_source_status text;
begin
  if new.status='POSTED' and old.status is distinct from 'POSTED' then
    if new.physical_at>clock_timestamp()+interval '5 minutes' then
      raise exception 'Tanggal/jam QC berada di masa depan. Periksa tanggal/jam sebelum posting.';
    end if;

    if exists(select 1 from erp.qc_inspection_items i where i.inspection_id=new.id and i.cutting_group_id is null) then
      raise exception 'Setiap item QC produksi wajib terkait Potongan agar qty FG, HPP, dan histori dapat divalidasi.';
    end if;

    for r in
      select i.cutting_group_id,sum(i.qty_good_pcs+i.qty_bs_pcs)::bigint current_qty
      from erp.qc_inspection_items i
      where i.inspection_id=new.id
      group by i.cutting_group_id
      order by i.cutting_group_id
    loop
      perform 1 from erp.cutting_groups cg where cg.id=r.cutting_group_id and cg.po_id=new.po_id for update;
      if not found then raise exception 'Potongan item QC tidak belongs to PO QC'; end if;

      select coalesce(v.total_pcs,0) into v_effective
      from erp.v_cutting_group_totals v where v.cutting_group_id=r.cutting_group_id;

      select coalesce(sum(i2.qty_good_pcs+i2.qty_bs_pcs),0)::bigint into v_prior
      from erp.qc_inspection_items i2
      join erp.qc_inspections q2 on q2.id=i2.inspection_id
      where i2.cutting_group_id=r.cutting_group_id
        and q2.status='POSTED'
        and q2.id<>new.id;

      v_current:=coalesce(r.current_qty,0);
      if v_effective<=0 then
        raise exception 'Potongan item QC tidak memiliki qty efektif yang dapat menghasilkan FG/BS.';
      end if;
      if v_prior+v_current>v_effective then
        raise exception 'Qty QC melebihi Potongan efektif. Potongan %, efektif %, QC sebelumnya %, QC ini %. Koreksi qty QC/Potongan sebelum posting.',
          r.cutting_group_id,v_effective,v_prior,v_current;
      end if;
    end loop;

    for r in
      select i.source_laundry_receipt_line_id as source_id,
             sum(i.qty_good_pcs+i.qty_bs_pcs)::bigint as current_qty
      from erp.qc_inspection_items i
      where i.inspection_id=new.id
        and i.source_laundry_receipt_line_id is not null
      group by i.source_laundry_receipt_line_id
      order by i.source_laundry_receipt_line_id
    loop
      select lrl.qty_good_received,ld.po_id,lr.status
        into v_source_good,v_source_po,v_source_status
      from erp.laundry_receipt_lines lrl
      join erp.laundry_receipts lr on lr.id=lrl.receipt_id
      join erp.laundry_delivery_lines ldl on ldl.id=lrl.delivery_line_id
      join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
      where lrl.id=r.source_id
      for update of lrl;

      if v_source_po is distinct from new.po_id or v_source_status<>'POSTED' then
        raise exception 'QC laundry source must still be a POSTED receipt from the same PO at posting time';
      end if;

      select coalesce(sum(i2.qty_good_pcs+i2.qty_bs_pcs),0)::bigint into v_prior
      from erp.qc_inspection_items i2
      join erp.qc_inspections q2 on q2.id=i2.inspection_id
      where i2.source_laundry_receipt_line_id=r.source_id
        and q2.status='POSTED'
        and q2.id<>new.id;

      v_current:=coalesce(r.current_qty,0);
      if v_prior+v_current>coalesce(v_source_good,0) then
        raise exception 'QC accounted quantity exceeds GOOD quantity physically returned from laundry at posting. Received %, already QC %, this QC %',
          coalesce(v_source_good,0),v_prior,v_current;
      end if;
    end loop;
  end if;
  return new;
end;
$function$;

alter function "erp"."guard_qc_posting_consistency"() owner to "postgres";
