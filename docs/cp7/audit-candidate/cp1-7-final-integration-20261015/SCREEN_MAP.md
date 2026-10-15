# Peta layar: UX demo vs layar tersambung (fokus 2 audit akhir, D14-13)

Disusun penulis pada 15 Okt 2026 dari kode di `66baa8e8` (hanya membaca kode; tidak ada database hosted yang dibuka).
Ini **titik awal** untuk auditor, bukan bukti lulus. Auditor memeriksa ulang setiap baris dengan kodenya sendiri.

## Cara aplikasi memilih layar

- Menu dan label: `src/App.tsx` baris 276–314 (`nav`, `adminNav`, peta label → id halaman); pemilihan label:
  `chooseSubmenu` baris 561–600; render per halaman: baris 630–762. Hak akses per halaman: `src/auth/accessCatalog.ts`.
- Mode aplikasi (`src/config/runtime.ts`):
  - `DEMO_SIMULATION`: UX demo, data contoh, tanpa database.
  - `UAT_AUTH_SIMULATION`: login dan data **Supabase Enteng** (`siimvrusnzxexizpyoib`), yaitu calon produksi.
  - `DISPOSABLE_TEST`: Supabase lokal sekali pakai, dipakai semua uji browser CI.
  - Bendera per area (potong, bagi potongan, WIP, BS, laundry, QC) bernilai `CONNECTED` di kedua mode tersambung;
    `fgHandoffMode` bernilai `BLOCKED_UNTIL_AUTHORITATIVE`.

Kode: **T** = tersambung (baca/tulis lewat RPC), **D** = data contoh/keadaan lokal, **B** = layar batas ("belum aktif"),
**T−** = tersambung tetapi panel khusus `DISPOSABLE_TEST` disembunyikan, **N** = pemberitahuan saja, tanpa angka.

## 1. Semua 48 menu

| Menu | id halaman | DEMO | UAT (Enteng) | DISPOSABLE_TEST | Uji browser yang membuka layar tersambung |
|---|---|---|---|---|---|
| Dashboard | dashboard | D | N | N | tidak ada (hanya jsdom `OwnerDashboard.dom.test.tsx`) |
| Buat Potongan | cutting-roll | D | T− | T | `cp7_cutting_yield/_input/_learning`, `cp6_frontend_recovery_ui`, `cp6_v2620an_selectors_ui` |
| Bagi Potongan | mandor-wip | D | T | T | `cp7_cp17_fix`, `cp7_cutting_correction`, `cp6_frontend_recovery_ui` |
| WIP & Sewing | sewing-wip | D | T | T | hanya `cp6_frontend_recovery_ui` (era CP6) |
| Laundry | laundry | D | T | T | `cp6_bd*`, `cp6_be`, `cp6_bf_*`, `cp6_readiness`, `cp6_disposable_ui_e2e`, `cp7_f03_redye`, `cp7_transaction_source` |
| QC & Final SKU | qc | D | T | T | `cp6_bd`, `cp6_disposable_ui_e2e`, `cp6_final_gap_ui`, `cp7_transaction_source` |
| Susun Nota FG | fg-handoff | D | **B** | T (Nota) | `cp7_p12`, `cp7_p12_opening`, `cp7_p12_attendance_write` |
| Barang BS & Rework | bs-rework | D | T | T | `cp6_be`, `cp6_final_gap_ui`, `cp6_frontend_recovery_ui`, `cp7_transaction_source` |
| Ringkasan Gudang | warehouse-dashboard | D | **D** | **D** | tidak ada |
| Pembelian & Penerimaan | procurement | D | T | T | `cp7_p09`, `cp7_receipt_correction`, `cp7_supplier_payment_*`, `cp7_f03_return_documents` |
| Bahan & Roll | materials-rolls | D | T | T | `cp7_p09`, `cp7_receipt_correction`, `cp7_transaction_source` |
| Kain kantong | pocket-fabric | N | T | T | `cp6_ap_flow_ui`, `cp6_be`, `cp6_be_revision` |
| Aksesori | accessories | D | T | T | `cp6_bc`, `cp6_readiness`, `cp7_f03_e03` |
| Ringkasan Barang Jadi | fg-summary | D | T− | T | ±37 skrip `cp7_f04_*`, `cp7_f05_*`, `cp7_p18_*`, `cp7_p19_*`, `cp7_k*`, `cp7_p10` |
| Mutasi Barang Jadi · Vivo / Widie | movements-vivo / -widie | D | T | T | `cp7_p10_book`, `cp7_note_correction` |
| Kartu Stok FG | stock-card | D | T− | T | `cp7_f03_redye`, `cp7_note_correction`, `cp7_transaction_source` |
| Stock Adjustment | stock-adjustment | D | T | T | `cp7_p09`, `cp7_p10_adjustment` |
| Ganti Merek | brand-conversion | D | T | T | hanya `cp6_be` |
| Penjualan & Invoice | sales-invoice | D | **D** | T | `cp7_p11_*`, `cp7_f03_e01`, `cp7_sales_chain`, `cp7_note_correction`, `cp7_cp17_fix` |
| Semua Invoice | sales-allocation | D | **D** | T | tidak ada |
| Retur Penjualan | sales-returns | D | **D** | T | `cp7_f03_e01`, `cp7_p11_returns`, `cp7_sales_return_correction` |
| Pembayaran Pelanggan | sales-payments | D | **D** | T | `cp7_f03_e01`, `cp7_p11_returns`, `cp7_payment_correction` |
| Riwayat Pelanggan | sales-history | D | **D** | **D** | tidak ada (belum ada layar tersambung) |
| Ringkasan Keuangan | finance-overview | D | **D** | T | `cp7_f03_finance_overview`, `cp7_f03_misc` |
| Kas & Bank | finance-cash | D | **D** | T | `cp7_f03_cash`, `cp7_f03_e05`, `cp7_f03_misc` |
| Hutang Supplier & Vendor | finance-ap | D | T | T | `cp6_bf_supplier`, `cp7_f03_supplier_credit`, `cp7_p09` |
| Piutang Pelanggan | finance-ar | D | **D** | T | `cp7_f03_receivables`, `cp7_f03_e01`, `cp7_f03_misc` |
| Payroll & Kasbon | finance-payroll | D | **D** | T | `cp7_p12_*`, `cp7_f03_e05`, `cp7_cp17_fix`, `cp7_transaction_source` |
| Absensi & Rate Harian | operations-attendance | D | **D** | T | `cp7_p12_attendance*`, `cp7_p12_roster` |
| Nota Ambil Aksesori | contractor-issue | D | T | T | `cp6_ap_flow_ui`, `cp6_bc`, `cp7_f03_e24_issue`, `cp7_transaction_source` |
| HPP & Rekalkulasi | hpp | D | T | T | `cp6_bf`, `cp6_readiness`, `cp7_p13_recost` |
| Jurnal & Transaksi Lain | finance-journal | D | **D** | T | `cp7_f03_journal`, `cp7_f03_misc`, `cp7_misc_correction`, `cp7_supplier_payment_correction` |
| Laporan & Tutup Buku | finance-reports | D | **D** | T | `cp7_p13_finance/_analysis/_period`, `cp7_f03_report_dates`, `cp7_f03_misc` |
| Kain & Benchmark | master-fabric | D | **D** | **D** | tidak ada |
| Aksesori & Harga Mandor | master-accessory | D | **D** | **D** | tidak ada |
| Produk & SKU | master-products | D | T | T | `cp6_bf`, `cp6_bf_free` |
| Pelanggan / Supplier & Vendor / Mandor / Gudang & Lokasi | master-customers / -partners / -workforce / -locations | D | **D** | **D** | tidak ada |
| Pola | master-pattern | D | T | T | tidak ada untuk layar tersambung |
| Reminder | admin-reminders | D | **D** | **D** | tidak ada |
| Pengguna & Hak Akses | admin-access | D | T | T | tidak ada untuk layar tersambung |
| Pengaturan ERP / Tutup Periode / Audit Trail | admin-settings / -period-close / -audit | D | **D** | **D** | tidak ada |
| Impor data awal | admin-import | N | T | T | `cp6_ap_flow_ui`, `cp6_at/au_browser_ui`, `cp6_bb/bc/bd/be`, `cp7_f03_refund`, `cp7_p12_opening` |

Jumlah: di **UAT (Enteng)** 23 menu tersambung, **23 menu masih data contoh**, 1 layar batas (Susun Nota FG), 1
pemberitahuan (Dashboard). Di **DISPOSABLE_TEST** 35 tersambung (termasuk Nota), 12 data contoh, 1 pemberitahuan.

## 2. Hal yang sudah terlihat penulis (untuk diperiksa, bukan disimpulkan)

1. **Penjualan, sebagian besar Keuangan dan Absensi hanya tersambung di `DISPOSABLE_TEST`.** Syaratnya ditulis
   `runtime.mode === 'DISPOSABLE_TEST'` (`App.tsx` baris 637, 638, 761), bukan `!== 'DEMO_SIMULATION'` seperti layar
   gudang dan produksi. Akibatnya, aplikasi yang dibuka dengan data Enteng menampilkan 11 layar penjualan/keuangan/absensi
   dengan **angka contoh**. Tidak ada dokumen yang menjelaskan kapan dan bagaimana layar itu dinyalakan di Enteng.
   Yang ada hanya catatan per handoff bahwa layar itu "terbuka di DISPOSABLE_TEST" (mis. `docs/cp7/P12_NOTA_HANDOFF.md`
   baris 49, `docs/cp7/F03_CASH_READER_HANDOFF.md` baris 9) dan aturan "jangan mengganti enum menjadi fully-connected
   sebelum route terbukti" (`docs/cp7/framework-v2/01_KONTRAK_DAN_INTEGRASI.md` baris 65).
2. **Dokumen penulis yang salah.** `docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md` (baris 16–19, 51–52),
   `docs/cp7/FREEZE_CP7_FINAL_20261014.md` baris 35 dan `../cp1-7-full-20261014/README.md` baris 95 menulis bahwa layar
   simulasi penjualan "tidak tampil di mode tersambung". Itu benar hanya untuk `DISPOSABLE_TEST`; di mode Enteng layar
   simulasi itu tampil. Koreksi ditambahkan di berkas pertama (bagian "Koreksi 15 Okt"); teks lama tidak dihapus.
3. **Label "SIMULASI UX" hilang di dua layar keuangan.** Tanda simulasi hanya tampil bila kepala halaman tidak punya
   tombol (`src/FinancePages.tsx` baris 51). Ringkasan Keuangan (baris 120) dan Payroll & Kasbon (baris 229) punya
   tombol, jadi angka contoh (termasuk grafik penjualan/HPP 6 bulan) tampil tanpa tanda di mode Enteng.
4. **Dashboard** di mode tersambung hanya menampilkan pemberitahuan (keputusan owner F-UI-01, 12 Okt). Kalimatnya
   menunjuk ke menu Keuangan, Gudang, Produksi dan Penjualan untuk angka asli, padahal di mode Enteng Penjualan, sebagian
   besar Keuangan dan Ringkasan Gudang masih data contoh.
5. **Layar tersambung butuh fungsi CP7 di server.** Kartu stok, ringkasan barang jadi, mutasi Vivo/Widie, pembelian,
   bahan & roll, stock adjustment (dan panel di bagi potongan, laundry, HPP) memanggil RPC `erp_cp7_*`. Paket CP7 belum
   pernah dipasang di Enteng (`docs/cp7/FREEZE_CP7_FINAL_20261014.md` baris 40); pada database CP6 saja, panel recost
   HPP pernah mendapat HTTP 404 / PGRST202 di uji pra-beku (`docs/cp7/PREFREEZE_RUNTIME_MIGRATION_20261006.md` baris 5).
6. **Tautan ke transaksi asal** hanya aktif di `DISPOSABLE_TEST` (`App.tsx` baris 457, `TransactionSourceNavigation.tsx`
   baris 28).
7. **Tidak ada uji browser** pada 13 menu (Ringkasan Gudang, Semua Invoice, Riwayat Pelanggan, 6 master data, 4 menu
   admin), dan tidak ada uji browser untuk layar tersambung Pola serta Pengguna & Hak Akses.
8. **Semua uji browser CI memakai build `DISPOSABLE_TEST`.** Uji browser build mode Enteng hanya
   `tests/browser/cp5-bs-resolution.spec.ts` dan `cp6-laundry-qc.spec.ts`, dengan HTTP tiruan. Belum ada uji browser
   build mode Enteng terhadap backend sungguhan (sesuai larangan menyentuh hosted).
9. `README.md` di akar repo (baris 29) mendaftar layar tersambung mode Enteng lebih sedikit daripada kodenya.
10. **Data induk harian.** Layar Pelanggan, Supplier & Vendor, Mandor, Gudang & Lokasi, Kain & Benchmark dan
    Aksesori & Harga Mandor masih data contoh di semua mode. Sepanjang yang terlihat penulis, data induk itu di
    database hanya masuk lewat Impor data awal (migrasi `v2_6_20ak`, `v2_6_20ap`) dan beberapa master khusus (mis.
    master vendor laundry BD-1). Auditor memeriksa apakah pemakaian harian (pelanggan baru, mandor baru) punya jalan.
11. **WIP & Sewing tersambung tidak bisa mencatat jahit selesai** (lihat `CHAIN_MAP.md` §3 butir 1). Di UX demo,
    layar ini punya alur kirim ke laundry; di layar tersambung hanya baca dan tanda.

## 3. Yang diminta dari auditor untuk fokus 2

- Untuk setiap menu: bandingkan perilaku UX demo dengan layar tersambungnya (alur, isian, hitungan, pesan tolak,
  tampilan HP). Contoh perilaku demo yang sempat tidak ikut: bagi lusin per seri (D14-5, `src/SalesPages.tsx`).
- Tandai setiap menu: SAMA / BEDA (sebutkan perilaku) / TIDAK ADA LAYAR TERSAMBUNG.
- Nilai butir 1–11 di atas: mana yang harus beres sebelum pemasangan ke Enteng (CP7C/CP8) dan mana yang boleh menyusul.
- Larangan tetap: tidak membuka atau mengubah Supabase hosted Enteng, legacy, production, main, atau deployment
  Cloudflare. Mode Enteng diuji dengan build lokal + backend sekali pakai atau HTTP tiruan.
