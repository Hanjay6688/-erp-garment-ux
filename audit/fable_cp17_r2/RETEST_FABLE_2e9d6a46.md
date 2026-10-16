# UJI ULANG FABLE r2 — kandidat 2e9d6a468c110684c278d585418eb404250d1150, tree 5e50d224 — 2026-10-16

Auditor: Fable, independen, baca-saja terhadap produk. Dasar: laporan Fable terkunci atas dfab13bf (ccafdb18) dan
keputusan owner yang saya catat beserta oracle uji ulangnya sebelum perbaikan dibuat (8677a399,
`audit/fable_cp17_combined/OWNER_DECISIONS_TO_AUDITOR_20261016.md`). Kepala penulis saat run: `b388a4b7`; beda dari
kandidat hanya 8 berkas `docs/` (pohon produk sama). Status per kasus dibaca dari baris JSON log, bukan warna job. Rincian:
`WORKLOG.md`, `MANIFEST.md`. `production_go: false`.

## Ringkasan

Dari 8 temuan saya yang masih terbuka atau baru di putaran gabungan: **6 DITUTUP**, **2 MASIH TERBUKA** (FABLE-012 ditunda ke
CP7C oleh keputusan D14-9; FABLE-016 tinggal dua langkah yang belum diuji lewat layar). **1 temuan BARU** tingkat S3, yaitu
alat uji penulis, bukan produk. Skenario kas saya yang dulu membuktikan saldo −500 dijalankan ulang tanpa perubahan dan
sekarang ditolak. Uji baru saya untuk D15-1 (pembalikan, koreksi, detektor) lulus semua. 13 workflow penulis yang saya
jalankan ulang lulus per kasus, kecuali satu kasus INCOMPLETE karena alat ujinya. Tidak ada kemunduran pada jumlah kasus
yang bisa dibandingkan dengan putaran gabungan.

## Status per temuan

| Temuan | Status | Bukti (label) |
|---|---|---|
| FABLE-013 (S2) penjaga kas hanya tanggal ekonomi | **DITUTUP** | `fable_cp17c_cash_basis.py` tanpa perubahan (run 38928539078): pengeluaran 1.500,00 tgl 15 Okt sesudah pemasukan periode tertutup kini ditolak `CP7_CASH_NEGATIVE ... minus -500.00 pada tanggal buku 2026-10-15 (laporan kas harian)` (FABLE). Oracle D15-1 saya (`fable_r2_cash_both.py`, run 38928553056): pembalikan pemasukan ditolak (tanggal ekonomi), koreksi ke 0,01 ditolak, koreksi wajar −100 diterima (penjaga tidak menolak membabi buta), tidak ada hari minus di kedua dasar sesudah langkah yang diterima, `closed_through` tidak berubah; detektor melaporkan `CASH_NEGATIVE_BOOK_DATE 2026-10-15 −500.00` dan tidak `CASH_NEGATIVE` (FABLE). Sumber: `check_cash` menilai kedua tanggal; koreksi misc/nota/pembayaran pelanggan dinilai pada keadaan akhirnya lewat compound scope (INDEPENDENT_SOURCE_REVIEW). `CP17_R2_CASH_BOOK_DATE_REFUSED`, `CP17_R2_DETECTOR_BOOK_DATE_LISTED` PASS (run 38928586290, INDEPENDENT_NATIVE_RERUN) |
| FABLE-014 (S3) PO selesai satu arah; komentar keliru | **DITUTUP** | `po-reopen.sql` lewat Native `erp.reopen_production_order`, penghalang NOT_FINISHED / FG_USED / PERIOD_CLOSED, token, alasan, idempoten, riwayat tetap; komentar `finish.sql` dibetulkan (INDEPENDENT_SOURCE_REVIEW). `CP17_R2_PO_REOPEN_THEN_FINISH_SAME_HPP`, `_BLOCKERS_UNCHANGED`, race dua tab, HTTP, browser desktop dan HP: semua PASS (run 38928586290) |
| FABLE-015 (S1 untuk Enteng) angka contoh di mode Enteng | **DITUTUP** | `src/screenActivation.ts`: di Enteng 29 layar tersambung, 17 tersembunyi, 1 layar batas (Susun Nota FG), 1 pemberitahuan (Dashboard); rute langsung ke layar tersembunyi merender layar batas "belum tersambung" tanpa angka (`App.tsx` 632/779). Label "SIMULASI UX · semua angka di halaman ini contoh" kini juga tampil bila kepala halaman punya tombol (`FinancePages.tsx`). Unit test `screenActivation.test.ts` + `OwnerDashboard.dom.test.tsx` 8/8 lulus, saya jalankan lokal (FABLE). Sesuai D15-2 |
| FABLE-016 (S3) langkah rantai tanpa uji lewat aplikasi | **MASIH TERBUKA (sebagian)** | Kini diuji lewat layar: posting Bagi Potongan ("Catat pickup & masuk Sewing", `cp7_master_browser.mjs`), posting Ganti Merek ("Catat konversi fisik"), BS → klasifikasi → order rework → hasil, upah rework → Nota → payroll → dibayar, impor → jual → bayar → tutup buku (`cp7_r207_chain_browser.mjs`); `CP17_BROWSER_R2_07_*` dan `CP17_BROWSER_R2_FABLE_D15_3_SCREEN_CHAIN_DESKTOP` PASS (run 38928586290). **Belum:** posting QC & Final SKU (B7) dan potongan Nota Ambil Aksesori ke payroll (S4) masih hanya SQL langsung atau UI CP6 beku; uji browser kandidat untuk QC hanya memeriksa tombol nonaktif |
| FABLE-017 (S2) data master dan tarif mandor tanpa penulis | **DITUTUP** | `master.sql`, `rates.sql`, enam layar Master Data tersambung di mode uji dan Enteng (sensus run 38928569907: enam layar master berubah dari demo menjadi tersambung). Tidak ada hapus, hanya nonaktif/aktif; ubah kode, jenis, satuan, kategori ditolak bila sudah dipakai (INDEPENDENT_SOURCE_REVIEW). Oracle D15-3 saya: rantai mandor + tarif baru → Bagi Potongan → jahit selesai dengan tarif pada tanggal jahit, ubah tarif sesudahnya tidak mengubah upah tercatat (`CP17_R2_FABLE_D15_3_SCREEN_CHAIN_WAGE_AT_SEWING_DATE` + browser desktop PASS); tiap layar master punya browser desktop + HP + race, HTTP master dan tarif (semua PASS, run 38928586290) |
| FABLE-011 (dugaan) tanpa lantai tanggal cutover | **DITUTUP** | D15-5 `cutover/cutover.sql`: trigger BEFORE INSERT pada jurnal (tanggal ekonomi) dan mutasi stok bahan/barang jadi (tanggal WIB), pengecualian jalur saldo awal dan pembalik, riwayat tetap, tidak boleh sesudah transaksi operasional pertama atau cutover batch impor (INDEPENDENT_SOURCE_REVIEW). `CP17_R2_D15_5_*` 5 kasus + 2 race + HTTP + browser desktop/HP PASS. Penjaga baru aktif sesudah owner mengesahkan tanggal resmi di aplikasi |
| FABLE-005 (S3) pemetaan 75 C6 + 22 ALL di luar pohon | **DITUTUP** | `docs/evidence/c6-all-crosswalk/` identik byte demi byte dengan cabang Astra `audit/astra-cp1-7-0b7049d9-20261014` commit d4a83b42 (14 Okt 23:11 WIB, sebelum putaran gabungan): blob json e38a6325 (sha256 b654e674…), md 1634f067 (sha256 79f38ac6…). Isinya tidak saya nilai; menurut README-nya itu indeks disposisi, bukan penerimaan tiap klausul |
| FABLE-012 (dugaan S2) EXECUTE `authenticated` ke penulis `erp` | **MASIH TERBUKA (ditunda D14-9)** | Tidak berubah. `CP17_FABLE012_EXPOSURE_GATE_REVOKE_FIRST` dan `CP17_HTTP_ERP_WRITERS_NOT_REACHABLE` PASS (run 38928586290). Pencabutan dijadwalkan di CP7C, sebelum `erp` pernah terbuka ke Data API |

Temuan lama yang sudah ditutup di putaran gabungan (FABLE-001..004, 006..010) tidak dibuka ulang. Skenario FABLE-001 dan
penjaga D14-2 tetap lulus lewat P12 payroll (64/81/43 PASS) dan `CP17` (146/146).

## Temuan baru

### FABLE-018 (S3, alat uji penulis) — helper browser `laundryRead` membaca teks alert yang bisa sudah hilang; kasus lulus berubah jadi INCOMPLETE
- `scripts/cp6_bd_browser.mjs` baris 62–65 menghitung `.clq-alert.error` lalu meminta `innerText` tanpa menunggu. Bila alert
  hanya tampil sesaat, permintaan teks menunggu 20 detik lalu gagal.
- Run 38928683194, kasus `BD_BROWSER:OWNER_POLICY_SET_AND_CLEAR`: oracle kasusnya (kebijakan LAU-DEC04 SET lalu kembali
  PENDING) sudah tercapai, tetapi kasus tercatat INCOMPLETE karena helper ini. Berkasnya tidak berubah sejak dfab13bf; kasus
  yang sama lulus di run kualifikasi penulis dan di rerun saya atas dfab13bf. Job tidak mati sebelum kasus, jadi tidak
  saya ulang.
- Yang belum diketahui: isi alert error yang sempat tampil di Laundry → Harga & tagihan sesudah kebijakan dikembalikan.
- Saran: helper mengambil teks dengan cara yang tidak menunggu elemen yang sudah hilang, dan menyimpan teksnya. Ini bukan
  pengunci pemasangan.

## Catatan untuk owner (bukan cacat)
- **Tarif upah terkunci per PO sejak upah pertama** (aturan Native `po_work_component_snapshots`). Kenaikan tarif di tengah
  PO tidak berlaku untuk sisa PO itu; berlaku untuk PO berikutnya.
- **D15-2 di Enteng:** layar penjualan, kas, piutang, jurnal, laporan/tutup buku, payroll dan absensi disembunyikan sampai
  tersambung. Artinya, sampai layar itu tersambung, upah yang tercatat dari jahit selesai menumpuk sebagai utang mandor dan
  belum bisa dibayar atau ditutup bukunya lewat aplikasi Enteng. Pool HPP absensi juga belum punya layar (batas yang dicatat
  penulis).
- **PO otomatis (D15-6)** adalah fasad CP7 pertama yang menyisipkan baris `erp.production_orders` sendiri, karena tidak ada
  penulis Native untuk PO operasional. Lanjutannya ke Bagi Potongan dan jahit diuji penulis dan lulus.

## Yang harus beres sebelum pemasangan ke Enteng
1. Urutan pasang: lapisan database CP7 (termasuk master, tarif, cutover, buka ulang PO) terpasang dan diuji sebelum UI CP7.
   Pada database lama, layar memanggil fungsi yang tidak ada (masih terbukti: `LEGACY_RUNTIME_GAP`, run 38928683194).
2. FABLE-012 / D14-9: cabut EXECUTE 82 penulis `erp` dari `authenticated` sebelum `erp` terbuka ke Data API (CP7C).
3. Sahkan tanggal cutover resmi di aplikasi sebelum transaksi operasional pertama; tanpa itu D15-5 belum menjaga apa pun.
4. Isi data master dan tarif mandor lewat layar baru, dan resep aksesori produk hasil impor (Produk & SKU) sebelum QC atau
   rework produk itu.
5. Rencana operasional untuk upah, penjualan dan kas selama layar uang masih disembunyikan (lihat catatan D15-2).
6. Kunci CP2 yang terpapar tidak dipakai lagi (sudah diakui penulis).

## Yang belum saya periksa
- Data dan setelan Supabase Enteng (master, tarif, Data API): tidak ada akses hosted pada putaran ini.
- Build mode Enteng di browser: dilarang menyentuh hosted; vonis Enteng dari kode dan unit test.
- Posting QC & Final SKU dan potongan Nota Ambil Aksesori ke payroll lewat layar (FABLE-016).
- Isi alert error sesaat di Laundry (FABLE-018).
- Tampilan HP layar tersambung di luar yang dilewati uji browser HP penulis; sensus HP 48 menu hanya build demo.
- Workflow kualifikasi penulis yang tidak saya ulang (receipt: 116 run; saya ulang 13 workflow + 3 run Fable). 35 workflow
  CP6 lama tidak saya ulang (arsip kedaluwarsa dan pemeriksa lingkup historis; tidak menguji kandidat).
- Alat backup CP7C (D13-9a), red team di luar RBAC, pekerjaan auditor lain putaran ini (§16.7).

## Pernyataan paparan
Lihat `MANIFEST.md` §Paparan. Selain dua berkas pemetaan Astra lama yang hanya di-hash (dibuat sebelum putaran gabungan),
tidak ada laporan, cabang, run, artifact atau komentar auditor lain yang dibuka.
