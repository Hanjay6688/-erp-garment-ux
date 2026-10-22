-- OW-08b (D17-13 2.21; owner D14-10, D15-4). A refused QC reversal names every document that still blocks it and the
-- real menu where each one is undone. Readers only: no table, trigger, grant or business row changes. The refusal
-- conditions of erp.reverse_qc and of the QC workspace stay byte-for-byte; only their sentences get these names.
create schema cp7_fg_correction_source authorization postgres;
revoke all on schema cp7_fg_correction_source from public,anon,authenticated,service_role,cp7_capture;

-- Every blocker of one QC reversal: PO, BS, later use of its goods (latest first), payroll. Each list uses the predicate erp.reverse_qc applies:
-- its PO is FINISHED; a BS case of its items (not CANCELLED) has a rework order that is not CANCELLED or a resolution;
-- a PRODUCTION lot of its items has an active downstream movement (erp.fg_lot_has_active_downstream: any movement of
-- the lot except REVERSAL rows and the lot's own QC_GOOD origin, without an inverse); an accessory right of such a lot
-- is no longer UNALLOCATED. 'menu' is a real sidebar item, or null when no screen can undo it (the step says so);
-- 'source' is a reference erp_cp7_resolve_transaction_source_v1 can open, or null.
create function cp7_fg_correction_source.qc_blockers_v1(p_qc uuid)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare v_out jsonb:='[]';v_seen text[]:='{}';v_key text;v_step text;v_menu text;v_source jsonb;
 v_number text;v_status text;v_extra text;v_id uuid;r record;
begin
 for r in select po.id,po.po_number from erp.qc_inspections q join erp.production_orders po on po.id=q.po_id
  where q.id=p_qc and po.status='FINISHED' loop
  v_out:=v_out||jsonb_build_array(jsonb_build_object('kind','PO_FINISHED','id',r.id,'number',r.po_number,
   'menu','Keuangan › HPP & Rekalkulasi','source',null,
   'step','PO '||r.po_number||' sudah selesai: buka ulang di Keuangan › HPP & Rekalkulasi, bagian "Selesaikan atau buka ulang PO" (tombol Buka ulang PO).'));
 end loop;

 for r in select bc.bs_number,ro.id,ro.rework_number,ro.status from erp.bs_cases bc
  join erp.rework_orders ro on ro.bs_case_id=bc.id and ro.status<>'CANCELLED'
  where bc.qc_item_id in(select i.id from erp.qc_inspection_items i where i.inspection_id=p_qc)and bc.status<>'CANCELLED'
  order by bc.bs_number,bc.id,ro.rework_number,ro.id loop
  v_out:=v_out||jsonb_build_array(jsonb_build_object('kind','REWORK_ORDER','id',r.id,'number',r.rework_number,
   'menu','Produksi › Barang BS & Rework','source',jsonb_build_object('source_type','REWORK_ORDER','source_id',r.id),
   'step',case when r.status='COMPLETED'
    then'Rework '||r.rework_number||' (BS '||r.bs_number||') sudah selesai: di Produksi › Barang BS & Rework batalkan hasilnya dulu (Periksa pembatalan hasil), lalu Batalkan order.'
    else'Rework '||r.rework_number||' (BS '||r.bs_number||') masih aktif: batalkan di Produksi › Barang BS & Rework (Batalkan order).'end));
 end loop;
 for r in select bc.bs_number,br.id,br.resolution_type,br.source_rework_order_id from erp.bs_cases bc
  join erp.bs_resolutions br on br.bs_case_id=bc.id
  where bc.qc_item_id in(select i.id from erp.qc_inspection_items i where i.inspection_id=p_qc)and bc.status<>'CANCELLED'
  order by bc.bs_number,bc.id,br.physical_at,br.id loop
  v_out:=v_out||jsonb_build_array(jsonb_build_object('kind','BS_RESOLUTION','id',r.id,'number',r.bs_number,
   'menu','Produksi › Barang BS & Rework',
   'source',case when r.source_rework_order_id is null then null
    else jsonb_build_object('source_type','REWORK_ORDER','source_id',r.source_rework_order_id)end,
   'step',case when r.source_rework_order_id is null
    then'Keputusan '||replace(r.resolution_type,'_',' ')||' pada BS '||r.bs_number||': batalkan di Produksi › Barang BS & Rework (tombol Reverse pada riwayat kasus, Owner/Admin).'
    else'Keputusan '||replace(r.resolution_type,'_',' ')||' pada BS '||r.bs_number||' berasal dari hasil rework; ikut batal saat hasil rework itu dibatalkan di Produksi › Barang BS & Rework.'end));
 end loop;

 for r in select fl.lot_number,fm.source_type,fm.source_id from erp.fg_lots fl
  join erp.fg_stock_movements fm on fm.lot_id=fl.id
  where fl.qc_item_id in(select i.id from erp.qc_inspection_items i where i.inspection_id=p_qc)and fl.lot_origin='PRODUCTION'
   and fm.movement_type<>'REVERSAL'
   and not(fm.movement_type='QC_GOOD'and fm.source_type='QC_ITEM'and fm.source_id=fl.qc_item_id)
   and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)
  order by fm.physical_at desc,fm.id desc loop
  v_id:=null;v_number:=null;v_status:=null;v_extra:=null;v_menu:=null;v_source:=null;
  case r.source_type
  when'SALE_ITEM'then
   select h.id,h.sale_number,h.status into v_id,v_number,v_status
    from erp.sales_items i join erp.sales_headers h on h.id=i.sale_id where i.id=r.source_id;
   if v_id is not null then
    v_menu:='Penjualan › Penjualan & Invoice';v_source:=jsonb_build_object('source_type','SALE_ITEM','source_id',r.source_id);
    v_step:=case when v_status='DRAFT'
     then'Draft invoice '||v_number||' memesan barang dari lot '||r.lot_number||': di Penjualan › Penjualan & Invoice ubah drafnya atau pilih Batalkan draft invoice.'
     else'Penjualan '||v_number||' memakai barang dari lot '||r.lot_number||': di Penjualan › Penjualan & Invoice pilih Batalkan penjualan tercatat (atau Periksa pembatalan rantai bila sudah ada pembayaran atau retur).'end;
   end if;
  when'SALES_RETURN_ITEM'then
   select sr.id,sr.return_number,h.sale_number into v_id,v_number,v_extra
    from erp.sales_return_items i join erp.sales_returns sr on sr.id=i.return_id join erp.sales_headers h on h.id=sr.sale_id
    where i.id=r.source_id;
   if v_id is not null then
    v_menu:='Penjualan › Retur Penjualan';v_source:=jsonb_build_object('source_type','SALES_RETURN_ITEM','source_id',r.source_id);
    v_step:='Retur '||v_number||' (invoice '||v_extra||') mengembalikan barang ke lot '||r.lot_number
     ||': di Penjualan › Retur Penjualan buka invoice '||v_extra||', pilih Koreksi retur '||v_number||' lalu Batalkan retur tercatat.';
   end if;
  when'FG_ADJUSTMENT_ITEM'then
   select h.id,h.adjustment_number into v_id,v_number
    from erp.fg_adjustment_items i join erp.fg_adjustments h on h.id=i.adjustment_id where i.id=r.source_id;
   if v_id is not null then
    v_menu:='Gudang › Stock Adjustment';v_source:=jsonb_build_object('source_type','FG_ADJUSTMENT_ITEM','source_id',r.source_id);
    v_step:='Penyesuaian barang jadi '||v_number||' mengubah lot '||r.lot_number
     ||': di Gudang › Stock Adjustment, bagian Barang jadi, pilih Batalkan koreksi FG.';
   end if;
  when'PRODUCT_CONVERSION'then
   select c.id,c.conversion_number into v_id,v_number from erp.product_conversions c where c.id=r.source_id;
   if v_id is not null then
    v_menu:='Gudang › Ganti Merek';
    v_step:='Ganti merek '||v_number||' memakai barang dari lot '||r.lot_number
     ||': batalkan di Gudang › Ganti Merek, bagian Riwayat konversi (tombol Batalkan).';
   end if;
  else null;
  end case;
  if v_id is null then
   v_id:=r.source_id;v_number:=r.source_type;
   v_step:='Mutasi barang jadi jenis '||r.source_type||' pada lot '||r.lot_number
    ||' belum punya layar pembatalan, jadi finalisasi QC ini belum bisa dibatalkan dari aplikasi.';
  end if;
  v_key:=r.source_type||':'||coalesce(v_id::text,'');
  if not v_key=any(v_seen)then
   v_seen:=v_seen||v_key;
   v_out:=v_out||jsonb_build_array(jsonb_build_object('kind','FG_DOWNSTREAM','movement_source_type',r.source_type,'id',v_id,
    'number',v_number,'menu',v_menu,'source',v_source,'step',v_step));
  end if;
 end loop;

 for r in select ps.id,ps.payroll_number,ps.status from erp.payroll_settlements ps
  where ps.status<>'REVERSED'and exists(select 1 from erp.fg_lots fl
   join erp.contractor_accessory_reimbursement_entitlements e on e.lot_id=fl.id and e.payroll_status<>'UNALLOCATED'
   join erp.payroll_reimbursements pr on pr.source_type='ACCESSORY_BOM'and pr.source_id=e.id and pr.payroll_id=ps.id
   where fl.qc_item_id in(select i.id from erp.qc_inspection_items i where i.inspection_id=p_qc)and fl.lot_origin='PRODUCTION')
  order by ps.payroll_number,ps.id loop
  v_out:=v_out||jsonb_build_array(jsonb_build_object('kind','PAYROLL','id',r.id,'number',r.payroll_number,
   'menu','Keuangan › Payroll & Kasbon','source',jsonb_build_object('source_type','PAYROLL_PAYMENT','source_id',r.id),
   'step',case when r.status='PAID'
    then'Payroll '||r.payroll_number||' sudah dibayar dan memuat hak tagih aksesori dari QC ini: di Keuangan › Payroll & Kasbon pilih Batalkan payroll dan pembayaran.'
    else'Payroll '||r.payroll_number||' memuat hak tagih aksesori dari QC ini: batalkan di Keuangan › Payroll & Kasbon (Batalkan payroll).'end));
 end loop;
 -- A right that is not UNALLOCATED but sits in no active payroll still blocks; say so plainly.
 for r in select fl.lot_number,e.id,e.payroll_status from erp.fg_lots fl
  join erp.contractor_accessory_reimbursement_entitlements e on e.lot_id=fl.id and e.payroll_status<>'UNALLOCATED'
  where fl.qc_item_id in(select i.id from erp.qc_inspection_items i where i.inspection_id=p_qc)and fl.lot_origin='PRODUCTION'
   and not exists(select 1 from erp.payroll_reimbursements pr join erp.payroll_settlements ps on ps.id=pr.payroll_id
    where pr.source_type='ACCESSORY_BOM'and pr.source_id=e.id and ps.status<>'REVERSED')
  order by fl.lot_number,e.id loop
  v_out:=v_out||jsonb_build_array(jsonb_build_object('kind','ACCESSORY_RIGHT','id',r.id,'number',r.lot_number,
   'menu',null,'source',null,
   'step','Hak tagih aksesori lot '||r.lot_number||' berstatus '||r.payroll_status
    ||' tanpa payroll aktif; aplikasi belum punya tombol untuk mengembalikannya, jadi finalisasi QC ini belum bisa dibatalkan dari aplikasi.'));
 end loop;
 return v_out;
end $$;

-- The same list as plain sentences appended to the refusal: the first eight steps, numbered.
create function cp7_fg_correction_source.qc_blocker_text_v1(p_qc uuid)returns text
language sql stable security definer set search_path=''as $$
 select case when jsonb_array_length(s.b)=0 then''
  else' Yang harus dibetulkan dulu: '
   ||(select string_agg(e.n::text||') '||(e.x->>'step'),' 'order by e.n)from jsonb_array_elements(s.b)with ordinality e(x,n)where e.n<=8)
   ||case when jsonb_array_length(s.b)>8
    then' Masih ada '||(jsonb_array_length(s.b)-8)::text||' dokumen lain; selesaikan yang di atas lalu periksa lagi.'else''end end
 from(select cp7_fg_correction_source.qc_blockers_v1(p_qc)b)s
$$;

revoke all on function cp7_fg_correction_source.qc_blockers_v1(uuid),cp7_fg_correction_source.qc_blocker_text_v1(uuid)
 from public,anon,authenticated,service_role,cp7_capture;
