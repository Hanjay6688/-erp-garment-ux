# AUDIT AKHIR FABLE — kandidat gabungan dfab13bf62398a69a02bf6221c06d29075e5e40b, tree 886f8331 — 2026-10-15 (bagian B paket D14-16, D14-13)

Auditor: Fable, independen. Uji ulang temuan lama ada di `RETEST_FABLE_dfab13bf.md`; catatan run per kasus di
`WORKLOG.md`; temuan dalam bentuk mesin di `FINDINGS.json`. `production_go: false`.

## Ringkasan

Di mode uji (`DISPOSABLE_TEST`), semua 20 rantai punya layar yang tersambung ke database (21 baris; B9 dipecah). 15 baris
teruji lewat aplikasi (browser, atau HTTP dengan login sungguhan). 6 baris punya langkah yang hanya diuji lewat SQL
langsung: posting Bagi Potongan, posting QC & Final SKU, posting Ganti Merek, BS & rework, potongan Nota Ambil Aksesori ke
payroll, dan upah rework. Di mode Enteng (`UAT_AUTH_SIMULATION`), separuh uang dari aplikasi belum tersambung: penjualan, kas & bank,
piutang, jurnal, laporan, payroll dan absensi masih menampilkan angka contoh. Rantai produksi → penjualan → kas putus di
batas barang jadi, dan dua layar keuangan menampilkan angka contoh tanpa label simulasi (FABLE-015). Di kedua mode, data
master (pelanggan, supplier, mandor, lokasi, tarif upah mandor) tidak bisa dibuat dari aplikasi, sehingga jahit selesai
untuk model baru berhenti di "tarif belum ada" (FABLE-017).
Penjaga kas D14-3 bekerja di semua kasus penulis, tetapi laporan kas pemilik masih bisa menunjukkan saldo minus pada satu
tanggal tanpa terdeteksi (FABLE-013, terbukti). Semua 20 job (16 run) penulis yang saya jalankan ulang lulus per kasus; run ke-17 (T2) tidak bisa jalan dan tidak menguji
kandidat. Tidak ada
regresi pada uji ulang dan skenario lama saya.

## Temuan baru (per akar masalah)

### FABLE-013 (S2, terbukti) — Penjaga kas D14-3 menghitung saldo per tanggal ekonomi, laporan kas pemilik per tanggal buku; kas bisa tampil minus tanpa terdeteksi
- **Akar:** `cp7_guard.min_debit_balance_from` dan `cp7_guard.findings()` (`scripts/cp7-src/finance/dated-guards.sql`) menjumlah
  `journal_entries.economic_date`. `erp.post_journal` mencatat `account_daily_balances` pada `transaction_date`. Dokumen
  bertanggal di periode tertutup diakui hari ini (`erp.resolve_accounting_transaction_date`). Pembaca kas pemilik
  `erp_cp7_get_finance_analysis_v1` menyatakan dasar `GL_TRANSACTION_DATE_ALL_CONFIGURED_CASH_COA`.
- **Bukti (FABLE, run 38786227211, kasus `FABLE_CP17C:CASH_BASIS_MISMATCH`, oracle ditulis sebelum run):** tutup buku
  sampai 13 Okt, Kas Utama berisi 1.000,00 sejak 14 Okt. Lewat layar Transaksi Lain-lain (`erp_cp7_save_misc_finance_v1`):
  pemasukan 2.000,00 bertanggal 11 Okt (diakui 16 Okt, `period_shifted`), lalu pengeluaran 1.500,00 bertanggal 15 Okt
  **diterima**. Saldo Kas Utama per tanggal buku: 14 Okt 1.000,00, **15 Okt −500,00**, 16 Okt 1.500,00. Pembaca kas pemilik
  untuk 15 Okt: closing **−500,00**, `reconciled: true`. `cp7_guard.findings()` tidak melaporkan apa pun.
- **Dampak:** aturan owner D14-3 ("ditolak kalau membuat saldo kas/bank minus pada tanggal mana pun") dilanggar menurut
  laporan yang dilihat owner. Total uang tetap benar; yang salah adalah saldo harian di laporan, dan alarmnya diam.
- **Saran:** penjaga dan detektor juga memeriksa saldo per `transaction_date` (dasar laporan), atau owner menetapkan satu
  dasar tanggal untuk D14-3 dan laporan diberi tanda bila saldo harian minus karena pengakuan terlambat. Jangan
  melonggarkan penjaga yang sekarang.

### FABLE-014 (S3) — "Selesaikan PO" (G2) satu arah dari aplikasi; komentar sumber menyatakan tidak ada kebalikan Native padahal ada
- `scripts/cp7-src/cutting-correction/finish.sql` baris 8: "Finishing cannot be undone from the app (no Native inverse
  exists)". Database punya `erp.reopen_production_order(p_po_id uuid, p_reason text)` (migrasi v2_6_20ac, hanya untuk PO
  FINISHED). Tidak ada layar atau RPC `public` yang memanggilnya (`grep` atas `src/` dan `scripts/cp7-src`: nol).
- **Dampak:** PO yang terlanjur diselesaikan (WIP sisa ditutup ke beban hari itu) hanya bisa dibuka lewat database.
- **Saran:** betulkan komentar; owner memutuskan apakah buka-ulang PO perlu tombol, dengan penghalang seperti fitur lain.

### FABLE-015 (S1 untuk pemasangan Enteng) — Mode Enteng mencampur data asli dengan angka contoh di 11 layar uang; dua tanpa label simulasi
- **Akar:** `src/App.tsx` menyalakan layar tersambung penjualan (4), keuangan (6: Ringkasan, Kas & Bank, Piutang,
  Payroll & Kasbon, Jurnal, Laporan) dan Absensi hanya bila `runtime.mode === 'DISPOSABLE_TEST'`. Layar gudang dan
  produksi memakai `!== 'DEMO_SIMULATION'`. Tidak ada spanduk "data contoh" global (`businessDataMode` tidak dipakai di
  `src/`). `FinanceHero` hanya menampilkan "SIMULASI UX" bila kepala halaman tanpa tombol; Ringkasan Keuangan dan Payroll &
  Kasbon punya tombol, jadi angka contohnya (termasuk kas, hutang, grafik 6 bulan) tampil tanpa tanda. Sensus demo saya
  (`runs/SCREENS_DEMO_dfab13bf.json`) mencatat `sample_label: false` pada kedua layar itu.
- **Dampak:** owner yang membuka aplikasi dengan data Enteng melihat stok dan produksi asli berdampingan dengan kas,
  piutang, penjualan dan payroll palsu, dan pada dua layar tidak ada tanda bahwa angkanya contoh. Rantai B10–B13 dan S3
  tidak tersambung di Enteng. Penulis sudah menulis ini di `SCREEN_MAP.md` §2. Pengungkapan tidak mengubah tingkatnya.
- **Saran:** sebelum Enteng, pilih salah satu untuk setiap layar uang: sambungkan (sesudah lapisan database CP7 terpasang
  di Enteng), atau ganti dengan layar batas tanpa angka seperti Susun Nota FG. Jangan pernah menampilkan angka contoh
  tanpa label.

### FABLE-016 (S3) — Langkah rantai yang tersambung tetapi belum pernah diuji lewat aplikasi di kandidat
Posting Bagi Potongan (B3), posting QC & Final SKU (B7), posting Ganti Merek (B9b), BS & rework (S5), potongan Nota Ambil
Aksesori ke payroll (S4), dan upah rework (S3) hanya diuji dengan SQL langsung (klaim JWT buatan). Uji browser yang
menekan tombolnya berjalan di UI CP6 beku (`cp6_*`), bukan di UI kandidat. Uji browser QC kandidat hanya memeriksa tombol
`Post QC + Final SKU atomic` dalam keadaan nonaktif (`cp7_transaction_source_browser.mjs` baris 190).

### FABLE-017 (S2) — Data master tidak bisa dibuat atau diubah dari aplikasi tersambung di mode mana pun, termasuk tarif upah mandor yang dibutuhkan jahit selesai
- **Akar:** menu Kain & Benchmark, Aksesori & Harga Mandor, Pelanggan, Supplier & Vendor, Mandor, dan Gudang & Lokasi
  menampilkan komponen demo di kedua mode tersambung (sensus: sama persis dengan demo, berlabel simulasi). `src/` tidak
  memanggil RPC apa pun yang membuat pelanggan, supplier/vendor, mandor, lokasi, master bahan, atau tarif kerja. Tabel
  `erp.contractor_work_rates` tidak punya penulis di migrasi kandidat maupun di layar. Impor data awal tidak punya entitas
  tarif (`OPENING_*`, `UNINVOICED_RECEIPT` saja). Produk & SKU tersambung hanya bisa "Buat SKU dari ukuran". Semua uji CI
  membuat data master lewat SQL (mis. `cp7_f03_e01_cases.py` baris 103 menyisipkan `contractor_work_rates`).
- **Dampak:** jahit selesai (G1) untuk model atau mandor baru ditolak dengan pesan "Tarif kerja (BOM kerja) untuk model PO
  ini belum ada", dan pesan itu menunjuk ke layar yang tidak ada. Pelanggan, supplier, atau mandor baru juga tidak bisa
  ditambahkan dari aplikasi. Rantai B1, B4, B10 dan S3 hanya jalan untuk data master yang sudah ada di database. Penjaga
  menolak dengan aman, jadi tidak ada angka salah, tetapi pekerjaan harian berhenti.
- **Belum diketahui:** apakah data Enteng sudah berisi data master dan tarif yang cukup. Akses baca hosted ditolak
  konektor pada 15 Okt.
- **Saran:** sebelum Enteng, sambungkan layar master minimal (pelanggan, supplier/vendor, mandor, tarif kerja per model ×
  komponen × mandor), atau tetapkan prosedur admin tertulis yang diaudit. Pesan G1 sebaiknya menyebut jalan keluarnya.

## Vonis rantai (B1–B13, S1–S7)

Aturan vonis, ditetapkan sebelum membaca hasil: **TERSAMBUNG DAN TERUJI** = ada layar kandidat yang memanggil RPC langkah
itu, dan ada uji di kandidat yang lulus lewat aplikasi (klik browser, atau HTTP dengan login Auth sungguhan sebagai
pengguna). **TERSAMBUNG TANPA UJI APLIKASI** = layarnya ada, tetapi buktinya di kandidat hanya SQL langsung atau UI CP6
beku. **TIDAK TERSAMBUNG** = tidak ada layar kandidat untuk langkah itu di mode tersebut. Vonis untuk mode uji
(`DISPOSABLE_TEST`); kolom Enteng dari kode routing.

| # | Rantai | Vonis (DISPOSABLE_TEST) | Di mode Enteng | Bukti utama (label) |
|---|---|---|---|---|
| B1 | Penerimaan supplier → stok bahan | TERSAMBUNG DAN TERUJI | tersambung | Receipt correction 43 kasus PASS (38784428651), supplier payment create/correction (INDEPENDENT_NATIVE_RERUN) |
| B2 | Bahan → Buat Potongan → WIP | TERSAMBUNG DAN TERUJI | tersambung | Klik "Post ke WIP Potongan" di `cp7_cutting_input/yield_browser` (F04, di CI_RECEIPT; REUSED_WRITER_EVIDENCE); buka ulang potongan 19 kasus termasuk browser 2 PASS (38784501713); kain kembali SG02 browser PASS |
| B3 | Potongan → Bagi Potongan | **TERSAMBUNG TANPA UJI APLIKASI** (posting); pembatalan teruji | tersambung | Posting hanya SQL (`cp7_*_cases.py`) dan UI CP6; `CP17_BROWSER_SG01_PICKUP_REVERSAL_DESKTOP` PASS |
| B4 | Bagi Potongan → jahit selesai → siap laundry | TERSAMBUNG DAN TERUJI | tersambung | `CP17_G1_*`, race, HTTP, browser desktop/HP PASS (38784255332) |
| B5 | Jahit → kirim/terima laundry (+klaim, cuci ulang) | TERSAMBUNG DAN TERUJI | tersambung | Posting lewat RPC sebagai pengguna login + layar diperiksa (`BD_BROWSER:*`, pre-freeze 31 kasus PASS, 38784556107) |
| B6 | Invoice/klaim laundry → hutang vendor → kas | TERSAMBUNG DAN TERUJI | tersambung | `BD_BROWSER:D12_*` bayar dokumen vendor; penjaga FIN02 hanya SQL (`CP17_FIN02_*`) |
| B7 | Terima laundry → QC & Final SKU → lot FG | **TERSAMBUNG TANPA UJI APLIKASI** | tersambung | Posting QC hanya SQL di kandidat; browser kandidat hanya memeriksa tombol nonaktif |
| B8 | Barang jadi → HPP final | TERSAMBUNG DAN TERUJI | tersambung | `CP17_G2_*`, race, HTTP, browser PASS; satu arah (FABLE-014) |
| B9a | Buku Vivo/Widie, penyesuaian | TERSAMBUNG DAN TERUJI | tersambung | Note correction 43 kasus PASS (38784408935); F03 Full p10 (REUSED) |
| B9b | Ganti Merek | **TERSAMBUNG TANPA UJI APLIKASI** (posting) | tersambung | Browser kandidat hanya `SET_REDYE_PRICE` (`cp7_f03_redye_browser.mjs` baris 31) |
| B10 | Barang jadi → draf/invoice penjualan | TERSAMBUNG DAN TERUJI | **TIDAK TERSAMBUNG** (data contoh) | F03 Full p11, `CP17_BROWSER_D14_5_*` PASS |
| B11 | Penjualan → piutang → bayar → kas | TERSAMBUNG DAN TERUJI | **TIDAK TERSAMBUNG** | Payment correction 23 kasus PASS (38784519618), note correction |
| B12 | Retur penjualan → stok FG + kredit | TERSAMBUNG DAN TERUJI | **TIDAK TERSAMBUNG** | F03 Full p11 returns, sales return correction (REUSED) |
| B13 | Uang → kas/bank → buku besar → laporan/tutup periode | TERSAMBUNG DAN TERUJI, **dengan cacat FABLE-013** | **TIDAK TERSAMBUNG** (kas, jurnal, laporan) | F03 cash reader 21 kasus PASS (38784537309), P13 period 25 kasus PASS (38784483635), `CP17_CASH_*`; FABLE-013 |
| S1 | Hutang supplier → bayar → kas | TERSAMBUNG DAN TERUJI | tersambung | Supplier payment create 10 PASS (38784464552), correction 23 PASS (38784446800) |
| S2 | Retur/kredit supplier | TERSAMBUNG DAN TERUJI | tersambung | F03 Full p09, supplier credit (REUSED_WRITER_EVIDENCE) |
| S3 | Payroll: absensi, Nota, rework, kasbon → kas | TERSAMBUNG DAN TERUJI; upah rework **tanpa uji aplikasi** | **TIDAK TERSAMBUNG** (Payroll, Absensi data contoh; Nota diblok) | P12 payroll 3 job PASS, E05 26 PASS, `CP17_BROWSER_KASBON_*` PASS |
| S4 | Nota Ambil Aksesori → potongan payroll | **TERSAMBUNG TANPA UJI APLIKASI** (potongan ke payroll) | layar tersambung, ujung payroll tidak | Browser E24 untuk nota (REUSED); potongan ke payroll hanya SQL |
| S5 | BS dan rework | **TERSAMBUNG TANPA UJI APLIKASI** | tersambung | Browser kandidat hanya navigasi asal transaksi; posting diuji di UI CP6 |
| S6 | Hitung fisik / penyesuaian | TERSAMBUNG DAN TERUJI | tersambung | F03 Full p09/p10 (REUSED) |
| S7 | Impor saldo awal → tahap berikutnya | TERSAMBUNG DAN TERUJI | tersambung (Impor) | `AUDITOR_BROWSER_CP7_P12_OPENING_PAYROLL` 2 PASS (38784369800) |

## Vonis layar (48 menu × 2 mode)

**Cara:** modul `fable_cp17c_screens.mjs` membuka ke-48 menu sebagai OWNER dan mencatat judul, tombol, tab, kepala tabel,
label simulasi, jumlah angka rupiah, dan luapan horizontal (desktop 1440 px). Versi demo dijalankan lokal
(`DEMO_SIMULATION`, `runs/SCREENS_DEMO_dfab13bf.json`). Versi tersambung dijalankan di CI pada build `DISPOSABLE_TEST`
dengan Auth sungguhan (run 38791073836, 7/7 kelompok PASS, 48/48 menu terbuka, `runs/SCREENS_CONNECTED_dfab13bf.json`).
Mode Enteng tidak boleh dijalankan (hosted), jadi kolom Enteng dinilai dari kode routing `src/App.tsx` dan
`src/config/runtime.ts`.
**Aturan vonis:** SAMA = komponen layar yang sama dengan demo, datanya dari database. BEDA = layar tersambung yang
didesain lain dari demo. "Tugas utama" menyatakan apakah pekerjaan inti demo bisa dilakukan. TIDAK ADA LAYAR TERSAMBUNG =
menu menampilkan data contoh, layar batas, atau pemberitahuan saja. Tidak ada luapan horizontal di desktop pada 48 menu
kedua build.

| # | Menu | DISPOSABLE_TEST | Enteng (UAT) | Catatan (tugas utama, beda dari demo) |
|---|---|---|---|---|
| 1 | Dashboard | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | Pemberitahuan saja (keputusan F-UI-01). Pemberitahuan menunjuk ke menu yang di Enteng masih data contoh |
| 2 | Buat Potongan | BEDA | BEDA (panel uji disembunyikan) | Tugas utama ada ("Post ke WIP Potongan"). Pola salin baris per roll dari demo tidak ada |
| 3 | Bagi Potongan | BEDA | BEDA | Daftar + detail. "Susun otomatis", "Atur pecahan", "Tarik ke batch" tidak terlihat di layar pertama; posting belum diuji lewat aplikasi (FABLE-016) |
| 4 | WIP & Sewing | BEDA | BEDA | "Catat selesai jahit" ada (G1). Serah langsung ke laundry dari layar ini (demo) tidak ada; lewat menu Laundry. Butuh tarif upah (FABLE-017) |
| 5 | Laundry | BEDA | BEDA | Kirim, terima, cuci gagal, harga & tagihan ada |
| 6 | QC & Final SKU | BEDA | BEDA | Simpan QC ada; belum diuji lewat aplikasi (FABLE-016) |
| 7 | Susun Nota FG | BEDA | **TIDAK ADA LAYAR TERSAMBUNG** (layar batas) | Di Enteng Nota FG diblokir |
| 8 | Barang BS & Rework | BEDA | BEDA | Daftar kasus + klaim laundry + BS legacy; langkah rework bertarif dari demo tidak terlihat di layar pertama |
| 9 | Ringkasan Gudang | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | Data contoh berlabel |
| 10 | Pembelian & Penerimaan | BEDA | BEDA | Penerimaan, bayar supplier, retur supplier ada |
| 11 | Bahan & Roll | BEDA | BEDA | Stok per gudang + transfer. Retur supplier per roll (demo) pindah ke Pembelian |
| 12 | Kain kantong | BEDA | BEDA | Demo hanya pemberitahuan; versi tersambung punya pengesahan pengurangan stok |
| 13 | Aksesori | BEDA | BEDA | Stok, transaksi, barang kembali ada |
| 14 | Ringkasan Barang Jadi | BEDA | BEDA (panel uji disembunyikan) | Penjelajah stok; ringkasan per merek (demo) tidak ada |
| 15 | Mutasi Barang Jadi · Vivo | BEDA | BEDA | Buku ada; "Atur merek" per buku dari demo tidak terlihat |
| 16 | Mutasi Barang Jadi · Widie | BEDA | BEDA | Sama dengan Vivo |
| 17 | Kartu Stok FG | BEDA | BEDA (panel uji disembunyikan) | Penjelajah stok |
| 18 | Stock Adjustment | BEDA | BEDA | Hitung fisik bahan dan barang jadi ada |
| 19 | Ganti Merek | BEDA | BEDA | Pilih lot, tujuan, pratinjau; posting belum diuji lewat aplikasi (FABLE-016) |
| 20 | Penjualan & Invoice | BEDA | **TIDAK ADA LAYAR TERSAMBUNG** | Penjelajah invoice + buat invoice |
| 21 | Semua Invoice | BEDA | **TIDAK ADA LAYAR TERSAMBUNG** | Membuka penjelajah yang sama berjudul "Penjualan & Invoice" |
| 22 | Retur Penjualan | BEDA | **TIDAK ADA LAYAR TERSAMBUNG** | Lewat penjelajah invoice (tombol sama dengan menu 20) |
| 23 | Pembayaran Pelanggan | BEDA | **TIDAK ADA LAYAR TERSAMBUNG** | Lewat penjelajah invoice |
| 24 | Riwayat Pelanggan | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | Data contoh berlabel |
| 25 | Ringkasan Keuangan | BEDA | **TIDAK ADA LAYAR TERSAMBUNG, tanpa label** | FABLE-015 |
| 26 | Kas & Bank | BEDA | **TIDAK ADA LAYAR TERSAMBUNG** | Buku kas tersambung; transaksi lain-lain lewat Jurnal |
| 27 | Hutang Supplier & Vendor | BEDA | BEDA | Utang & kredit retur supplier, tagihan laundry |
| 28 | Piutang Pelanggan | BEDA | **TIDAK ADA LAYAR TERSAMBUNG** | Penjelajah piutang |
| 29 | Payroll & Kasbon | BEDA | **TIDAK ADA LAYAR TERSAMBUNG, tanpa label** | FABLE-015 |
| 30 | Absensi & Rate Harian | BEDA | **TIDAK ADA LAYAR TERSAMBUNG** | "Tandai semua hadir", "Salin minggu sebelumnya" dari demo tidak terlihat di layar pertama |
| 31 | Nota Ambil Aksesori | BEDA | BEDA | Nota baru, simpan draft, pengesahan ada |
| 32 | HPP & Rekalkulasi | BEDA | BEDA | Antrean HPP + proses; komposisi HPP per ukuran/versi (demo) tidak di layar pertama |
| 33 | Jurnal & Transaksi Lain | BEDA | **TIDAK ADA LAYAR TERSAMBUNG** | Penjelajah jurnal + pendapatan/biaya lain |
| 34 | Laporan & Tutup Buku | BEDA | **TIDAK ADA LAYAR TERSAMBUNG** | Laporan + tutup buku dengan arsip. Di Enteng tidak ada tempat tutup buku sama sekali |
| 35 | Kain & Benchmark | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | FABLE-017 |
| 36 | Aksesori & Harga Mandor | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | FABLE-017 (tarif mandor) |
| 37 | Produk & SKU | BEDA | BEDA | Hanya "Buat SKU dari ukuran". Tambah produk, harga massal, tarif kategori, edit BOM (demo) tidak ada |
| 38 | Pelanggan | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | FABLE-017 |
| 39 | Supplier & Vendor | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | FABLE-017 |
| 40 | Mandor | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | FABLE-017 |
| 41 | Gudang & Lokasi | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | FABLE-017 |
| 42 | Pola | SAMA | SAMA | Komponen yang sama, tersambung lewat mode internal |
| 43 | Reminder | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | Data contoh berlabel |
| 44 | Pengguna & Hak Akses | SAMA | SAMA | Komponen yang sama |
| 45 | Pengaturan ERP | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | Data contoh berlabel |
| 46 | Impor data awal | BEDA | BEDA | Demo hanya pemberitahuan; versi tersambung bisa buat draft impor |
| 47 | Tutup Periode | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | "contoh Agustus 2026"; tutup buku sungguhan ada di menu 34 (hanya mode uji) |
| 48 | Audit Trail | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | Data contoh berlabel |

**Jumlah.** DISPOSABLE_TEST: SAMA 2, BEDA 33, TIDAK ADA LAYAR TERSAMBUNG 13. Enteng: SAMA 2, BEDA 21, TIDAK ADA LAYAR
TERSAMBUNG 25 (11 di antaranya layar uang/absensi yang tersambung di mode uji, 2 tanpa label simulasi, 1 layar batas).
Layar yang BEDA umumnya memakai pola "cari/jelajah lalu panel detail". Sensus hanya mencatat layar pertama, jadi tombol di
panel detail tidak dihitung (lihat "Yang belum saya periksa").

## Yang harus dibetulkan sebelum dipasang ke Enteng

Urut dari yang paling menentukan:
1. **FABLE-015** — tidak boleh ada angka contoh di samping data asli. Sambungkan 11 layar uang/absensi (sesudah lapisan
   database CP7 terpasang di Enteng), atau ganti dengan layar batas tanpa angka. Minimal pasang label pada Ringkasan
   Keuangan dan Payroll & Kasbon.
2. **FABLE-017** — jalur membuat dan mengubah data master dan tarif upah mandor (layar, atau prosedur admin tertulis
   yang diaudit), dan pastikan data Enteng sudah memuatnya.
3. **Urutan pasang:** lapisan database CP7 harus terpasang sebelum UI CP7. Pada database lama, layar kesiapan keuangan
   gagal 404 `erp_cp7_get_recost_queue_v1` (run 38784556107, grup `LEGACY_RUNTIME_GAP`; LEGACY_RUNTIME_OBSERVATION_ONLY).
4. **FABLE-013** — owner menetapkan dasar tanggal D14-3, lalu penjaga dan detektor kas memeriksa dasar yang dipakai
   laporan. Penjaga yang sekarang tidak dilonggarkan.
5. **FABLE-012 / D14-9** — cabut EXECUTE 82 penulis `erp` dari `authenticated` sebelum `erp` pernah terbuka ke Data API.
   Setelan Data API hosted perlu dibaca ulang karena saya tidak bisa membacanya pada putaran ini.
6. **Kunci CP2** — jangan dipakai untuk backup baru (sudah diakui penulis).
7. Sebaiknya juga: uji lewat aplikasi untuk posting Bagi Potongan, QC & Final SKU, Ganti Merek, BS & rework, dan potongan
   Nota Ambil Aksesori ke payroll (FABLE-016); betulkan komentar dan putuskan tombol buka-ulang PO (FABLE-014).

## Yang belum saya periksa

- Setelan Data API dan isi data master/tarif di Enteng: konektor Supabase menolak `execute_sql` dan `get_project_url`
  ("You do not have permission") pada 15 Okt. Izin D14-7 tidak bisa dipakai.
- Build mode Enteng di browser: dilarang menyentuh hosted. Kolom Enteng berasal dari kode routing, bukan dari layar.
- Tampilan HP per menu: sensus hanya desktop 1440 px (uji HP penulis untuk G1, G2, SG02, D14-5 lulus).
- Panel detail di balik layar daftar: sensus hanya mencatat layar pertama setiap menu.
- 64 dari 80 run di CI_RECEIPT penulis tidak saya jalankan ulang (16 run kandidat, 20 job, saya ulang; ditambah T2 yang tidak
bisa jalan). Contohnya F03 Full,
  F04/F05, E24, X04, kapasitas. Untuk itu saya pakai REUSED_WRITER_EVIDENCE.
- 37 workflow CP6 lama, termasuk T2: tidak bisa jalan (arsip kedaluwarsa) dan dikunci ke commit CP6 beku.
- Pengakuan posting mundur sesudah tutup buku dengan posting yang diterima: chain4 hanya mendapat penolakan karena bank
  fixture kosong. Pengakuan di hari ini terlihat di bukti FABLE-013 (`period_shifted`), tetapi tanda `changed_since_filing`
  tidak diuji ulang di kandidat.
- Alat backup CP7C (di luar ruang lingkup, D13-9a). Uji penyerangan keamanan (red team) di luar RBAC.
- Laporan, cabang dan run auditor lain (aturan §16.7), termasuk pemetaan FABLE-005 di cabang Astra.

## Hasil merah yang bukan temuan

| Run | Kasus | Sebab | Label |
|---|---|---|---|
| 38784599005, 38784617586, 38784635065, 38784653182, 38784671018, 38785788908, rbac2 pertama | semua | Workflow Fable masih mengunduh arsip AC yang kedaluwarsa (HTTP 410) sebelum kasus apa pun; diganti baris pengganti penulis D14-17 | AUDITOR_TOOL |
| 38784274269 | CP6 T2 (3 job) | HTTP 410 sebelum kasus; T2 dikunci ke commit CP6 beku | NOT_APPLICABLE |
| 38786127478 | CLOSE_THEN_BACKDATED, TIMEZONE | Tutup buku sampai hari ini ditolak produk (benar); parameter `set local` psycopg | AUDITOR_TOOL |
| 38786142567 | CLOSED_PERIOD_RECOGNITION | Kolom `created_at` tidak ada (sudah dibetulkan di chain4) | AUDITOR_TOOL |
| 38784556107 | 2 INCOMPLETE `LEGACY_RUNTIME_GAP` | UI CP7 di atas database lama | LEGACY_RUNTIME_OBSERVATION_ONLY |

Merah yang **merupakan** temuan: 38786227211 (COUNTEREXAMPLE FABLE-013).

## Label asal-bukti

FABLE: skenario `fable_cp17c_cash_basis.py`, `fable_cp17c_screens.mjs`, skenario cp17 lama, sensus demo lokal, cek salinan
paket lokal. INDEPENDENT_NATIVE_RERUN: 17 run penulis yang saya kirim ulang pada `claude/new-session-deapao` (head 65628336,
pohon produk = dfab13bf). INDEPENDENT_SOURCE_REVIEW: `dated-guards.sql`, `payment-date-guard.sql`, `kasbon.sql`,
`pickup.sql`, `return.sql`, `sewing.sql`, `finish.sql`, `materials/read.sql`, `procurement/correction.sql`, `App.tsx`,
`runtime.ts`, `FinancePages.tsx`. REUSED_WRITER_EVIDENCE: run CI_RECEIPT yang tidak saya ulang. ACCEPTED_BY_DECISION:
D14-9 (FABLE-012), D14-11 (RWK01), D14-17 (arsip). WRITER_CROSSCHECK: CHAIN_MAP dan SCREEN_MAP penulis dipakai sebagai
titik awal; setiap baris diperiksa ulang dengan kode atau sensus.

## Pertanyaan untuk owner (dengan rekomendasi)

1. **D14-3, saldo kas "tanggal mana pun" menurut tanggal apa?** Rekomendasi: menurut kedua tanggal. Penjaga juga menolak
   bila laporan kas harian akan minus (FABLE-013).
2. **Layar uang di Enteng:** sambungkan dulu, atau sembunyikan di balik layar batas sampai tersambung? Rekomendasi:
   sembunyikan sekarang, sambungkan sesudah lapisan database CP7 terpasang dan diuji di Enteng (FABLE-015).
3. **Data master dan tarif mandor:** layar baru, atau prosedur admin? Rekomendasi: layar minimal untuk pelanggan,
   supplier, mandor, dan tarif kerja sebelum pemakaian harian (FABLE-017).
4. **Buka ulang PO yang terlanjur selesai:** perlu tombol? Rekomendasi: ya, dengan penghalang seperti fitur koreksi lain
   (FABLE-014).
5. **Lantai tanggal cutover (FABLE-011):** masih menunggu keputusan; rekomendasi tetap seperti v1.0.

## Ringkasan untuk owner (bahasa sehari-hari)

1. Perbaikan atas 12 temuan lama saya sebagian besar berhasil: 9 tertutup, 3 masih terbuka (satu menunggu keputusan Bos,
   satu ditunda sesuai keputusan D14-9, satu buktinya ada di cabang auditor lain).
2. Masalah terbesar dulu, bayar upah sebelum utangnya ada, sekarang ditolak sistem; sudah saya coba sendiri.
3. Semua 20 uji penulis yang saya jalankan ulang lulus, dan uji lama saya tidak menemukan kemunduran di versi baru ini.
4. Di mode uji, alur produksi sampai penjualan dan kas sudah tersambung. Tiga langkah (bagi potongan, QC, ganti merek) baru
   diuji lewat database, belum lewat layar.
5. Di mode Enteng, layar penjualan, kas, piutang, jurnal, laporan, payroll dan absensi masih memakai angka contoh.
6. Dua di antaranya, Ringkasan Keuangan dan Payroll & Kasbon, tidak diberi tanda "contoh", jadi bisa dikira angka asli.
7. Pelanggan, supplier, mandor dan tarif upah mandor belum bisa ditambah dari aplikasi, sehingga jahit selesai untuk model
   baru akan berhenti.
8. Saya menemukan celah kecil di aturan kas tidak boleh minus: laporan kas bisa menunjukkan minus pada satu hari bila ada
   pemasukan lama yang baru dicatat.
9. Saran saya: jangan pasang ke Enteng sebagai aplikasi penuh sebelum butir 5 sampai 8 dibereskan atau diputuskan.
10. Akses baca ke Supabase Enteng ditolak hari ini, jadi isi data Enteng belum saya periksa.

## Register run

Lihat `WORKLOG.md` (semua run beserta hasil per kasus) dan `SP/out/dispatch_ledger.jsonl` (salinan ringkas di bawah saat
penguncian).

## Pernyataan paparan (§16.7)

Lihat `MANIFEST.md` §Paparan beserta koreksinya. Tidak ada laporan, cabang, run, artifact atau komentar auditor lain dari
putaran ini yang dibuka sebelum laporan ini dikunci.
