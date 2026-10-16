# Fable r2 work log (kandidat 2e9d6a46, tree 5e50d224)

## CP2 — tinjauan sumber (INDEPENDENT_SOURCE_REVIEW)

| Bagian | Berkas | Hasil |
|---|---|---|
| R2-01 / D15-1 kas dua tanggal | `finance/dated-guards.sql` | `check_cash` memanggil `min_debit_balance_from` (tanggal ekonomi) **dan** `min_debit_balance_by_book_from` (tanggal buku) untuk setiap baris kredit akun kas; pesan menyebut dasar tanggalnya. Koreksi (misc, nota penjualan, pembayaran pelanggan) membuka "compound scope": baris kredit dicatat, lalu `end_compound` menilai setiap akun yang tersentuh pada kedua tanggal mulai hari tersentuh paling awal. Scope yang masih terbuka saat commit membatalkan transaksi (constraint trigger tertunda). Detektor `findings()` punya `CASH_NEGATIVE` dan `CASH_NEGATIVE_BOOK_DATE`. Penjaga dipicu hanya oleh baris kredit; jurnal tidak bisa diubah sesudah dibuat, jadi tidak ada jalan lain menurunkan saldo |
| R2-05 / D15-4 buka ulang PO | `cutting-correction/po-reopen.sql`, `finish.sql` | Lewat Native `erp.reopen_production_order`; penghalang NOT_FINISHED, FG_USED, PERIOD_CLOSED dihitung di bawah kunci PO; token tinjauan, alasan, idempoten, riwayat tetap; pascasyarat WIP naik tepat sebesar residu yang dibalik. Komentar "no Native inverse" diganti |
| R2-02 / D15-2 layar Enteng | `src/screenActivation.ts`, `src/App.tsx` | Tabel 48 halaman × (enteng, test). Di Enteng menu HIDDEN tidak ada di sidebar, dan rute langsung merender layar batas "belum tersambung" (App.tsx 632, 779). Layar master merender komponen tersambung di semua mode bukan demo. Dashboard tidak ada di tabel → tersembunyi di Enteng. Unit test penulis `screenActivation.test.ts` + `OwnerDashboard.dom.test.tsx`: 8/8 lulus saya jalankan lokal (FABLE) |
| R2-03 / D15-3 master + tarif | `master/master.sql`, `master/rates.sql` | Tarif per mandor × model × komponen dengan versi tanggal berlaku; versi yang sudah dipakai upah tidak bisa diubah (Native `guard_used_contractor_work_rate`); BOM kerja pertama ditulis fasad, perubahan sesudahnya lewat Native `save_work_bom_edit`. **Aturan Native yang perlu diketahui owner:** tarif terkunci per PO sejak upah pertama (`po_work_component_snapshots`); kenaikan tarif di tengah PO tidak berlaku untuk sisa PO itu |
| D15-5 cutover | `cutover/cutover.sql` | Trigger BEFORE INSERT pada `journal_entries` (tanggal ekonomi), `material_stock_movements` dan `fg_stock_movements` (tanggal WIB `physical_at`); pengecualian jalur saldo awal dan pembalik; tanggal resmi tidak boleh sesudah transaksi operasional pertama atau tanggal cutover batch impor; riwayat tidak bisa diubah; sebelum disahkan tidak menolak apa pun |
| R2-04 / D15-6 PO otomatis | `cutting-correction/auto-po.sql` | Satu transaksi: buat PO (DRAFT/CUTTING) → posting Native `erp_save_cutting_group_before_sewing_v2` → PO ke CUTTING; draf hanya di skema CP7. Catatan: fasad pertama yang menyisipkan baris `erp.production_orders` sendiri (tidak ada penulis Native operasional) |
| R2-10 jahit per SKU | `cutting-correction/sewing.sql` | Satu completion dan satu SELESAI_DIJAHIT per SKU dalam satu permintaan; tarif per SKU dibaca dengan aturan snapshot Native; `complete=false` tepat di tempat snapshot Native menolak |
| FABLE-005 | `docs/evidence/c6-all-crosswalk/` | Blob kedua berkas identik dengan cabang Astra `audit/astra-cp1-7-0b7049d9-20261014` commit d4a83b425b91 (14 Okt 23:11 WIB, sebelum putaran gabungan): json e38a6325 / sha256 b654e674…, md 1634f067 / sha256 79f38ac6…. Isi tidak dibaca |

## CP3 — run (didispatch 16 Okt; kepala penulis b388a4b7, pohon produk = 2e9d6a46)
Fable (cabang audit, head d93c1b80): 38928539078 cash_basis lama tanpa perubahan; 38928553056 r2_cash_both; 38928569907
sensus layar DISPOSABLE. Penulis (ref claude/new-session-deapao): 38928586290 CP17 Fixes, 38928600597 F03 cash,
38928614932 misc correction, 38928628808 payment correction, 38928642717 note correction, 38928656059 cutting correction,
38928670120 P13 period, 38928683194 prefreeze UI, 38928696198 F04 cutting inputs, 38928710724 supplier payment create,
38928723680 P12 payroll, 38928737621 sales chain, 38928751306 UI phone width census.

## CP3 — hasil per kasus (semua run 16 Okt; status dari baris JSON log)

| Run | Isi | Hasil per kasus | Label |
|---|---|---|---|
| 38928539078 | `fable_cp17c_cash_basis.py` **tanpa perubahan** (run 38786227211 dulu COUNTEREXAMPLE) | PASS: pengeluaran 1.500,00 tgl 15 Okt ditolak `CP7_CASH_NEGATIVE ... minus -500.00 pada tanggal buku 2026-10-15 (laporan kas harian)` | FABLE |
| 38928553056 | `fable_r2_cash_both.py` | 2/2 PASS. Invariant: a diterima; b ditolak (tanggal buku); c diterima; d pembalikan pemasukan ditolak (tanggal ekonomi 16 Okt −500); e koreksi ke 0,01 ditolak (ekonomi 11 Okt −499,99); f koreksi −100 diterima; tidak ada hari minus di kedua dasar sesudah langkah yang diterima; `closed_through` tetap. Detektor: `CASH_NEGATIVE_BOOK_DATE 2026-10-15 −500.00`, tanpa `CASH_NEGATIVE`; trigger kembali aktif | FABLE |
| 38928569907 | sensus layar DISPOSABLE (`fable_cp17c_screens.mjs`) | 7/7 kelompok PASS, 48/48 menu terbuka, 0 luapan. Sama dengan demo: Ringkasan Gudang, Riwayat Pelanggan, Reminder, Pengaturan ERP, Tutup Periode, Audit Trail (berlabel), Pola dan Pengguna (komponen sama, tersambung). Berubah sejak dfab13bf: Buat Potongan, 6 layar master, Impor data awal | FABLE |
| 38928586290 | CP7 CP17 Fixes | 146/146 PASS (145 dideklarasikan + CP6_AUDITOR_PUBLIC_STATE_STABLE_ORDER); 44 kasus terkait oracle Fable semua PASS | INDEPENDENT_NATIVE_RERUN |
| 38928600597 / 614932 / 628808 / 642717 | F03 cash / misc correction / payment correction / note correction | 21 / 20 / 23 / 43 PASS | INDEPENDENT_NATIVE_RERUN |
| 38928656059 / 670120 / 696198 / 710724 | cutting correction / P13 period / F04 cutting inputs / supplier payment create | 19 / 25 / 34 / 10 PASS | INDEPENDENT_NATIVE_RERUN |
| 38928723680 | P12 payroll (3 job) | 64 / 81 / 43 PASS | INDEPENDENT_NATIVE_RERUN |
| 38928737621 | sales chain reversal | 25 PASS | INDEPENDENT_NATIVE_RERUN |
| 38928751306 | UI phone width census (build demo) | `{"menus":48,"failed":[]}` | INDEPENDENT_NATIVE_RERUN |
| 38928683194 | Pre-freeze UI | **merah**: 30 PASS, 3 INCOMPLETE. 2 = `LEGACY_RUNTIME_GAP` yang sama dengan dfab13bf (UI CP7 di atas DB lama, 404 `erp_cp7_get_recost_queue_v1`). 1 baru: `BD_BROWSER:OWNER_POLICY_SET_AND_CLEAR` — kebijakan SET lalu PENDING sudah lulus; helper `laundryRead` (cp6_bd_browser.mjs:62-65) menghitung `.clq-alert.error` lalu meminta teksnya tanpa menunggu, alert sudah hilang → timeout 20 s. Berkas tidak berubah sejak dfab13bf; lulus di run kualifikasi penulis dan di rerun dfab13bf saya. Tidak di-rerun (job tidak mati sebelum kasus) | INDEPENDENT_NATIVE_RERUN |

Semua rantai pre-U: `PRE_U_CAPTURED_IN_THIS_REBUILD`, sidik `eb7f121d…` sama. Jumlah kasus job yang juga saya ulang di dfab13bf
sama persis (F03 cash 21, payment corr 23, note corr 43, cutting 19, P13 25, supplier payment create 10, P12 64/81/43).
