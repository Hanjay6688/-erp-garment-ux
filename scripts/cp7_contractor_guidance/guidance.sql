-- OW-05b. The Mandor correction workspace names the real menus, lists every
-- document to make again after the correction, and shows the stored correction
-- history. Readers only: no table, trigger, grant or business row changes.
create schema cp7_contractor_guidance authorization postgres;
revoke all on schema cp7_contractor_guidance from public,anon,authenticated,service_role;

-- One blocker row from cp7_contractor_correction.blockers_v1 gets the step text of
-- the screen that actually reverses it. 'menu' is null when no screen can do it;
-- the step then says so plainly. 'source' is a reference the existing
-- erp_cp7_resolve_transaction_source_v1 can open, or null.
create function cp7_contractor_guidance.guide_v1(p_item jsonb)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare v_kind text:=p_item->>'kind';v_id uuid:=(p_item->>'id')::uuid;v_status text:=p_item->>'status';
 v_menu text;v_step text;v_source jsonb;v_qc uuid;v_flag boolean;
begin
 case v_kind
 when'PO_STATE'then
  if v_status='FINISHED'then
   v_menu:='Keuangan › HPP & Rekalkulasi';
   v_step:='PO sudah selesai. Buka ulang PO ini di Keuangan › HPP & Rekalkulasi, bagian "Selesaikan atau buka ulang PO" (tombol Buka ulang PO). Barang jadi yang sudah dipakai harus dibalik lebih dulu.';
  else
   v_step:='Status PO ini '||case v_status when'ON_HOLD'then'Ditahan'else'Dibatalkan'end
    ||' dan aplikasi belum punya tombol untuk mengubahnya, jadi koreksi mandor PO ini belum bisa dilakukan dari layar.';
  end if;
 when'PICKUP_SOURCE'then
  v_menu:='Produksi › Bagi Potongan';
  v_step:='Koreksi ini perlu PO yang punya mandor dan pembagian potongan terposting dengan mandor yang sama. Periksa pembagian PO ini di Produksi › Bagi Potongan.';
 when'PAYROLL'then
  v_menu:='Keuangan › Payroll & Kasbon';
  v_step:=case when v_status='PAID'
   then'Nota/gaji ini sudah dibayar. Di Keuangan › Payroll & Kasbon pilih "Batalkan payroll dan pembayaran". Uang yang sudah keluar tidak dipindah ke mandor baru.'
   else'Batalkan nota/gaji ini di Keuangan › Payroll & Kasbon (tombol Batalkan payroll).'end;
  v_source:=jsonb_build_object('source_type','PAYROLL_PAYMENT','source_id',v_id);
 when'ATTENDANCE_POOL'then
  v_menu:='Keuangan › HPP & Rekalkulasi';
  v_step:='Batalkan pool HPP absen ini di Keuangan › HPP & Rekalkulasi (tombol Batalkan pada pool). Pool dibuat dan diaktifkan lagi sesudah koreksi.';
 when'POCKET_POOL'then
  v_menu:='Gudang › Kain kantong';
  v_step:='Batalkan alokasi kain kantong periode yang memakai PO ini di Gudang › Kain kantong (Sahkan pembatalan alokasi). Bagi lagi sesudah koreksi.';
 when'QC'then
  v_menu:='Produksi › QC & Final SKU';
  v_step:='Batalkan finalisasi QC ini di Produksi › QC & Final SKU. Lot barang jadi, kasus BS dan hak tagih aksesori dari QC ini ikut dibatalkan. Bila barang jadinya sudah dipakai, balik pemakaiannya lebih dulu.';
  v_source:=jsonb_build_object('source_type','QC_INSPECTION','source_id',v_id);
 when'FG_LOT'then
  select fl.qc_item_id into v_qc from erp.fg_lots fl where fl.id=v_id;
  if v_qc is not null then
   v_menu:='Produksi › QC & Final SKU';
   v_step:='Lot barang jadi ini ikut batal saat finalisasi QC asalnya dibatalkan di Produksi › QC & Final SKU. Bila barangnya sudah dijual atau dipindah, balik dulu: retur di Penjualan › Retur Penjualan, atau batalkan di Gudang › Stock Adjustment atau Gudang › Ganti Merek.';
   v_source:=jsonb_build_object('source_type','QC_ITEM','source_id',v_qc);
  else
   v_menu:='Produksi › Barang BS & Rework';
   v_step:='Lot barang jadi ini tidak berasal dari QC. Bila dari hasil rework, batalkan hasilnya di Produksi › Barang BS & Rework (Periksa pembatalan hasil); bila barangnya sudah dijual atau dipindah, balik pemakaiannya lebih dulu.';
  end if;
 when'LAUNDRY'then
  v_menu:='Produksi › Laundry';
  v_step:='Di Produksi › Laundry batalkan penerimaannya lebih dulu (Batalkan penerimaan), lalu Batalkan pengiriman.';
  v_source:=jsonb_build_object('source_type','LAUNDRY_DELIVERY','source_id',v_id);
 when'SEWING'then
  v_menu:='Produksi › WIP & Sewing';
  v_step:='Batalkan catatan selesai jahit ini di Produksi › WIP & Sewing (Batalkan catatan selesai jahit). Upah borongannya ikut dibalik.';
 when'WORK','WORK_JOURNAL'then
  if v_kind='WORK_JOURNAL'then select je.source_id into v_id from erp.journal_entries je where je.id=v_id;end if;
  select exists(select 1 from erp.sewing_terminal_events st where st.source_work_completion_id=v_id)into v_flag;
  if v_flag then
   v_menu:='Produksi › WIP & Sewing';
   v_step:=case v_kind when'WORK'then'Hasil kerja/upah ini'else'Jurnal upah ini'end
    ||' ikut dibalik saat catatan selesai jahitnya dibatalkan di Produksi › WIP & Sewing.';
  else
   v_step:=case v_kind when'WORK'then'Hasil kerja/upah ini'else'Jurnal upah ini'end
    ||' tidak berasal dari catatan selesai jahit di aplikasi dan belum punya tombol pembatalan, jadi koreksi mandor PO ini belum bisa dilakukan dari layar.';
  end if;
 when'ACCESSORY_NOTE'then
  select fl.qc_item_id into v_qc from erp.contractor_accessory_reimbursement_entitlements ae
   join erp.fg_lots fl on fl.id=ae.lot_id where ae.id=v_id;
  v_menu:=case when v_qc is not null then'Produksi › QC & Final SKU'else'Produksi › Barang BS & Rework'end;
  v_step:=case when v_status='UNALLOCATED'then''
   else'Hak tagih aksesori ini sudah masuk nota/gaji; batalkan nota/gajinya dulu di Keuangan › Payroll & Kasbon. 'end
   ||case when v_qc is not null
    then'Hak tagih ini ikut batal saat finalisasi QC asalnya dibatalkan di Produksi › QC & Final SKU.'
    else'Hak tagih ini berasal dari lot di luar QC; bila dari hasil rework, batalkan hasilnya di Produksi › Barang BS & Rework.'end;
  if v_qc is not null then v_source:=jsonb_build_object('source_type','QC_ITEM','source_id',v_qc);end if;
 when'MATERIAL_ISSUE'then
  -- The Nota Ambil Aksesori screen owns counted-PCS accessory notes only (the
  -- same rule the transaction-source reader applies).
  select not exists(select 1 from erp.contractor_material_issue_items i
    left join erp.materials m on m.id=i.material_id
    left join erp.uom_definitions u on u.unit_code=m.unit_code
   where i.issue_id=v_id and(m.material_type is distinct from'ACCESSORY'
    or upper(m.unit_code)is distinct from'PCS'or u.dimension is distinct from'COUNT'))into v_flag;
  if v_flag then
   v_menu:='Keuangan › Nota Ambil Aksesori';
   v_step:=case when v_status='DRAFT'then'Hapus draft nota ambil aksesori ini di Keuangan › Nota Ambil Aksesori (Hapus draft).'
    else'Batalkan nota ambil aksesori ini di Keuangan › Nota Ambil Aksesori (Periksa pembatalan). Bila nota sudah masuk gaji, batalkan nota/gajinya dulu di Keuangan › Payroll & Kasbon.'end;
   v_source:=jsonb_build_object('source_type','CONTRACTOR_MATERIAL_RECEIVABLE','source_id',v_id);
  else
   v_step:='Nota pengambilan ini berisi kain atau bahan selain aksesori PCS. Aplikasi belum punya layar untuk membatalkannya, jadi koreksi mandor PO ini belum bisa dilakukan dari layar.';
  end if;
 when'REWORK'then
  v_menu:='Produksi › Barang BS & Rework';
  v_step:='Di Produksi › Barang BS & Rework batalkan hasil rework lebih dulu bila sudah selesai (Periksa pembatalan hasil), lalu Batalkan order.';
  v_source:=jsonb_build_object('source_type','REWORK_ORDER','source_id',v_id);
 when'BS'then
  select bc.qc_item_id into v_qc from erp.bs_cases bc where bc.id=v_id;
  if v_qc is not null then
   v_menu:='Produksi › QC & Final SKU';
   v_step:='Kasus BS ini ikut batal saat finalisasi QC asalnya dibatalkan di Produksi › QC & Final SKU. Balik dulu keputusan dan rework-nya di Produksi › Barang BS & Rework.';
   v_source:=jsonb_build_object('source_type','QC_ITEM','source_id',v_qc);
  else
   v_step:='Kasus BS ini dibuat manual dan aplikasi belum punya tombol untuk membatalkannya, jadi koreksi mandor PO ini belum bisa dilakukan dari layar.';
  end if;
 when'SCRAP'then
  v_step:='Dokumen scrap ini berasal dari data lama dan aplikasi belum punya tombol untuk membatalkannya, jadi koreksi mandor PO ini belum bisa dilakukan dari layar.';
 when'PICKUP_DRAFT'then
  v_menu:='Produksi › Bagi Potongan';
  v_step:='Hapus draft pembagian potongan ini di Produksi › Bagi Potongan (Hapus draft). Koreksi mengganti semua pembagian terposting dalam PO.';
  select jsonb_build_object('source_type','CUTTING_GROUP','source_id',pk.cutting_group_id)into v_source
   from erp.cutting_pickups pk where pk.id=v_id;
 when'GROUP_STATE'then
  v_step:='Potongan ini masih punya proses lanjutan yang aktif. Selesaikan pembalikan dokumen lain di daftar ini; baris ini hilang sendiri setelah potongan kembali ke status sudah diambil.';
 when'WIP_HISTORY'then
  v_step:='Perpindahan WIP PO ini belum semuanya punya pasangan pembalikan. Selesaikan pembalikan dokumen lain di daftar ini; bila baris ini tetap muncul, ada perpindahan WIP yang belum bisa dibalik dari aplikasi.';
 else
  raise exception 'CP7_MANDOR_GUIDANCE_KIND_UNKNOWN: %',v_kind;
 end case;
 return p_item||jsonb_build_object('step',v_step,'menu',v_menu,'source',v_source);
end $$;

create function cp7_contractor_guidance.after_step_v1()returns text
language sql immutable set search_path=''as $$
 select'Catat ulang hasil jahit untuk mandor yang benar di Produksi › WIP & Sewing dengan waktu fisik aslinya, lalu buat lagi dokumen lain yang tadi dibalik sesuai daftar di bawah. Nota, upah dan pembayaran lama tetap tersimpan sebagai riwayat.'::text
$$;

-- Every document the operator may have reversed, in the order to make it again.
create function cp7_contractor_guidance.after_steps_v1()returns jsonb
language sql immutable set search_path=''as $$
 select jsonb_build_array(
  jsonb_build_object('menu','Produksi › WIP & Sewing','step','Catat ulang hasil jahit untuk mandor yang benar dengan waktu fisik aslinya; pilih tarif PO lama atau tarif mandor baru.'),
  jsonb_build_object('menu','Keuangan › Nota Ambil Aksesori','step','Bila nota ambil aksesori mandor lama dibatalkan, buat dan sahkan lagi untuk mandor yang benar.'),
  jsonb_build_object('menu','Produksi › Laundry','step','Bila pengiriman atau penerimaan laundry dibatalkan, kirim dan terima lagi.'),
  jsonb_build_object('menu','Produksi › QC & Final SKU','step','Bila QC dibatalkan, QC dan finalisasi lagi. Lot barang jadi, kasus BS dan hak tagih aksesori terbentuk lagi dari QC baru.'),
  jsonb_build_object('menu','Produksi › Barang BS & Rework','step','Bila keputusan BS atau rework dibatalkan, catat lagi dari kasus BS yang terbentuk oleh QC baru.'),
  jsonb_build_object('menu','Penjualan › Penjualan & Invoice','step','Bila barang jadi diretur atau penyesuaiannya dibatalkan agar QC bisa dibuka, catat lagi penjualan atau penyesuaiannya.'),
  jsonb_build_object('menu','Gudang › Kain kantong','step','Bila alokasi kain kantong periode itu dibatalkan, bagi lagi ke HPP.'),
  jsonb_build_object('menu','Keuangan › HPP & Rekalkulasi','step','Bila pool HPP absen dibatalkan, buat dan aktifkan lagi; bila PO dibuka ulang, selesaikan PO lagi.'),
  jsonb_build_object('menu','Keuangan › Payroll & Kasbon','step','Susun lagi nota/gaji untuk mandor yang benar lalu bayar dari sana.'))
$$;

-- Stored corrections of one PO, newest first: who, when, from which Mandor to
-- which, why, and how many posted pickups were replaced.
create function cp7_contractor_guidance.history_v1(p_po uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select coalesce(jsonb_agg(jsonb_build_object('generation_no',h.generation_no,'recorded_at',h.recorded_at,
   'actor_name',(select u.full_name from erp.app_users u where u.auth_user_id=h.actor order by u.id limit 1),
   'old_contractor_id',h.old_contractor_id,'old_contractor_name',o.contractor_name,
   'new_contractor_id',h.new_contractor_id,'new_contractor_name',n.contractor_name,
   'reason',h.reason,'pickup_count',jsonb_array_length(h.result->'replacements'))
  order by h.generation_no desc),'[]')
 from cp7_contractor_correction.history_v1 h
 join erp.contractors o on o.id=h.old_contractor_id
 join erp.contractors n on n.id=h.new_contractor_id
 where h.po_id=p_po
$$;

revoke all on all functions in schema cp7_contractor_guidance from public,anon,authenticated,service_role,cp7_capture;
