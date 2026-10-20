# Jalur uang, HPP dan koreksi — pekerjaan berikutnya

Sumber: counter-review internal empat GPT-6.1 Sol Max pada `5e455424` (tree `d102d7fa`).
Semua kesimpulan di bawah **INTERNAL_WRITER_SOURCE_REVIEW**. Tidak ada Native runtime baru;
angka contoh adalah expected fixture, bukan observed yang diklaim telah terjadi.

## OW-07 — pool HPP dan tutup buku

1. Native aktivasi/cancel aktif: `supabase/migrations/20260902043000_erp_v2_6_16_cp4_hpp_route_auth_boundary.sql`
   sekitar 358–376/400–420, dipanggil `scripts/cp7-src/hpp-pool/pool.sql:300/305`.
   Setelah sync_po_hpp_to_gl belum ada sync_finished_po_wip_residual. Jalur pocket mempunyai contoh
   FINISHED di release `20be` sekitar 6975–6979. Jangan mengedit byte rilis CP6 yang diterima.
2. Buat delta dua fungsi terdaftar dengan capture/expected_definitions/verify/restoration, mengikuti
   `scripts/cp7_hpp_policy_guard_bundle.py`. Integrasi melalui note_report/f03 dan probe verifiers.
   Tambah residual setelah GL pada FINISHED, memakai tanggal efektif dan alasan tertaut pool.
   Jalur draft VOIDED yang kembali lebih awal tidak diubah.
3. Fixture nyata: helper `cp7_r3_hpp_pool_cases` + `cp7_cp17_fix_cases` + `cp6_bd_probe`.
   Mandor normal, kebijakan eksplisit, two_size_fixture satu size 10 PCS, terminal sewn 10;
   attendance payroll disetujui Rp1.000. Laundry 10, Final SKU 8 Good + 2 BS, dispose BS lewat writer,
   invoice laundry Rp20 bila dibutuhkan, finish via finish_command. Jangan all-BS: Native finish butuh Good FG.
   Sebelum pool: FINISHED dan WIP per PO nol. Late ACTIVATE expected tambahan Rp800 FG/Rp200 OTHER_EXPENSE,
   WIP per PO tetap nol. Prediksi kode lama +Rp200 belum dijalankan.
4. Fixture cancel terpisah: ACTIVATE→finish→CANCEL, expected WIP per PO nol (prediksi lama −Rp200).
   Cek juga replace/replay, PO masih berjalan, 10/10 Good tanpa residual palsu, rollback langkah akhir,
   race finish/activate dengan lock teramati. Global WIP nol saja bukan oracle: cek per PO, jurnal,
   komponen HPP, source redistribution dan seluruh detektor secara terpisah.
5. Close: `finance/period.sql`→accounting_close_preflight_v1 / close_accounting_through→AW readiness→BF
   period_blockers_v1 (2102–2480). BF belum mempunyai cakupan sumber absen/pocket belum dialokasikan.
   Pocket checks melalui v267 hanya memeriksa alokasi yang ada; attendance conservation v268 dapat
   menerima residual yang diprediksi. FINISHED_PO_WIP_RESIDUAL AC lama tidak ada di checker BC terakhir.
   Tambah pemeriksaan dari anggota sumber eligible, bukan sekadar keberadaan/tanggal pool; kebijakan
   HPP kosong jangan menjadi celah pengecualian.
6. Seed tutup seluruh periode pakai `cp7_period_cases.ready`/`cp6_aw_probe.quiet_seed`, bukan satu hari.
   Pocket fixture `cp6_pocket_period_trial.fixture` memposting usage 11,25 + 10 sewn tanpa alokasi.
   Expected close tertahan→POST_PERIOD/alokasi→review baru boleh close; cancel alokasi harus memblokir lagi
   setelah explicit reopen bila sudah close. Oracle lama lifecycle yang close sebelum alokasi perlu disposisi
   SUPERSEDED_BY_OWNER_RULE dan pengganti, bukan pengaman produk dilonggarkan.

## OW-04 — retur penjualan yang sudah dibayar

- Release `20ah` post_sales_return 310–321 menolak pembayaran melebihi net setelah retur;
  jurnal hanya Dr pendapatan/Cr piutang. Kredit `20bb` 199–223/1003–1071 khusus batch migrasi/retur lama.
  `sales/read.sql:33–52`, customer-history:40–54 dan detektor BB 5643–5685 masih pembayaran mentah.
  `SalesReturnPanel.tsx:60–73` belum menyediakan pilihan refund/kredit.
- Jangan menghapus guard atau membuat batch migrasi palsu. Tambah fakta settlement Native append-only,
  tertaut retur/pelanggan/nilai/tanggal/jurnal/UUID. `K=max(nilai_retur−piutang_sebelum_retur,0)`.
  Dalam transaksi retur sama, Dr piutang/Cr kredit pelanggan K; pilihan refund menambah Dr kredit/Cr kas K.
  Lunas 1.000→retur 200: AR0; kredit200/kas tetap, atau kredit0/kas turun200. Pembayaran asal tetap1.000.
  Dibayar900, AR100, retur200: hanya100 menjadi kredit/refund. Belum dibayar: tidak ada hak refund.
- Satu pembaca saldo canonical: pembayaran efektif=kas dibayar+kredit dipakai−kredit retur diterbitkan;
  status invoice, pembayaran, inverse/koreksi, laporan, reminder dan detektor memakai sumber yang sama.
  Tidak mengarang akun kewajiban/expiry; konfigurasi yang belum sah adalah blocker.
- Dependency: penggunaan kredit/refund→settlement/retur→pembayaran sumber→sale. Koreksi pembayaran tidak
  boleh meninggalkan kredit dari pembayaran lama. Chain-reversal:156–173 sekarang payments→returns→sale;
  ajarkan urutan baru, tampilkan nomor pemakaian dan jalur undo. Koreksi/retur berulang harus tetap efektif satu.
- Kunci mengikuti `sales/commands.sql:73–86`, return-correction:316–333, FG_HPP_SALES, invoice asal/tujuan,
  payment/return/items/alokasi/fakta kredit berurut. Refund tetap memakai CP7_CASH dan saldo akhir kedua dasar
  tanggal (dated-guards.sql:56–70/126–143); izin/token diperiksa setelah menunggu.
- Uji positif/negatif: full/partial/unpaid, kredit dipakai/refund parsial, pelanggan lain, kredit terpakai
  sebelum koreksi, reverse/replay, dua sesi, UUID payload berubah, reply loss, kas kosong, akses dicabut,
  tanggal/periode tertutup, 0→+1→0 detektor; UI desktop/HP sampai refetch dampak stok/HPP/AR/kas.

## OW-05 — salah mandor sesudah sewing

- `cutting-correction/pickup.sql:102–119/140–154` menganggap histori work/sewing/WIP/pool blocker,
  bahkan sudah dibalik. Native pickup POST (`20260903022604...v2_6_18...sql:1081–1106`) juga memakai
  helper downstream; melonggarkan layar saja tidak membuat koreksi berhasil.
- Mandor terikat seluruh PO. Review seluruh grup; jangan pindahkan grup lain diam-diam.
  Tambah generation koreksi/lineage immutable untuk assignment, pickup, snapshot tarif dan work/sewing pengganti.
  Pilihan tarif target berversi wajib mengikuti D16. Registry rate_revisions `(original_snapshot_id,basis_at)`
  belum membedakan generation; sekadar ganti contractor_id dapat memakai tarif A atau bentrok revisi B.
- Dependency graph: penggunaan FG/BS/draft aktif→explicit reopen PO bila FINISHED; pool absen aktif sebelum
  payroll/sewing dibalik; payroll/Nota/reimbursement/kasbon yang berkaitan; QC, invoice/claim, receipt, delivery
  sesuai graf Native; SELESAI_DIJAHIT→work→assignment. Nota POSTED tidak di-VOID; pertahankan dan beri successor.
  Native inverse claim tertentu dapat reopen PO sendiri; side effect harus masuk review, buku tidak auto-open.
- Inverse jurnal biasa memakai CURRENT_DATE. Koreksi tanggal asal perlu derived inverse/restatement source-bound,
  seperti return-correction.sql; bukan edit jurnal posted atau klaim koreksi dari pembatalan biasa.
- CP6FLOW berurut grup→group→PO→pickup harus bertemu lock payroll→mandor→workline→PAYWORK;
  semua pagar diperlukan, deadlock/race belum terbukti dari source.
- Fixture expected 10PCS A@100→B@150: PCS10, hak A0/B1.500, HPP/upah +500 bersih di tanggal benar;
  histori lengkap. Uji setelah undo benar-benar bisa koreksi, active usage tetap menolak; multi-grup, BF perSKU,
  rate revision waktu sama, A→B→A, payroll paid/approved/kasbon/baris tak terkait, pool cancel/replace,
  cutoff/mikrodetik, race payroll/sewing/laundry/pool/rate, last-step failure, UUID/reply loss/revoke,
  UI desktop/HP sampai refetch semua dampak. Jangan menghitung aman-menolak sebagai alur selesai.

Belum ada patch produk OW-04/05/07 pada checkpoint ini; semua masih backlog. `production_go:false`.
