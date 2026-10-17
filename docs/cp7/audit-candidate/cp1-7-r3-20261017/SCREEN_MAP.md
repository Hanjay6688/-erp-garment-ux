# Peta layar sesudah r3: 47 menu × 3 mode (D16-1, D16-5)

Disusun penulis dari `src/screenActivation.ts` pada kandidat r3. Ini titik awal untuk auditor, bukan bukti lulus.
Peta sebelumnya (kandidat r2): `../cp1-7-r2-20261016/SCREEN_MAP.md`.

## Yang berubah dari r2

- **D16-1** ("selesain biar gausa sembunyiin"): tidak ada lagi menu HIDDEN di mode Enteng. Sebelas menu yang sudah
  tersambung di mode uji kini juga tersambung di Enteng dengan komponen yang sama; Susun Nota FG tidak lagi layar batas;
  lima layar yang dulu data contoh sekarang membaca data nyata (Ringkasan Gudang, Riwayat Pelanggan, Reminder,
  Pengaturan ERP, Audit Trail).
- **D16-5**: menu "Tutup Periode" dihapus; penutupan buku menjadi tab "Tutup Buku" di "Laporan & Tutup Buku" (hak lihat
  laporan dan hak tutup buku tetap terpisah; tautan lama `admin-period-close` membuka tab itu). Jumlah menu 48 → 47.
- **Uji browser di build Enteng**: setiap kasus browser CP17 berjalan dua kali, di build uji dan di build mode Enteng
  (`AUDITOR_UI_MODE=ENTENG`, id berakhiran `_ENTENG`), keduanya terhadap salinan database sekali pakai. Alamat proyek
  Enteng di build itu diarahkan ke API lokal; tidak ada permintaan yang keluar ke hosted.
- `src/screenActivation.test.ts` kini menuntut tidak ada menu HIDDEN dan tidak ada data contoh di Enteng.

Kode: **C** = tersambung, **S** = data contoh, **N** = pemberitahuan tanpa angka.

## 1. Semua 47 menu

| Bagian | Menu | Demo | Enteng | Uji | Uji browser CP17 (masing-masing juga `_ENTENG`) |
|---|---|---|---|---|---|
| Dashboard | Dashboard | S | N | N | — |
| Produksi | Buat Potongan | S | C | C | `R2_D15_6_AUTO_PO_*` |
| Produksi | Bagi Potongan | S | C | C | `SG01_PICKUP_REVERSAL_DESKTOP`, `SG02_*`, rantai D15-3 |
| Produksi | WIP & Sewing | S | C | C | `G1_SEWING_*`, `R2_10_WAVE_SEWING_*`, `R3_09_RATE_CHOICE_*`, `R3_03_CHAIN_SEWING_TO_CLOSE` |
| Produksi | Laundry | S | C | C | — |
| Produksi | QC & Final SKU | S | C | C | `R3_05_QC_FINAL_SKU_DESKTOP/_MOBILE` (peran lihat saja + OWNER posting, kirim ulang) |
| Produksi | Susun Nota FG | S | C | C | rantai R2-07 kedua, `R3_03_CHAIN_SEWING_TO_CLOSE` |
| Produksi | Barang BS & Rework | S | C | C | rantai R2-07 kedua |
| Gudang | Ringkasan Gudang | S | C | C | `R3_03_WAREHOUSE_SUMMARY_DESKTOP/_MOBILE` (OWNER dan GUDANG) |
| Gudang | Pembelian & Penerimaan | S | C | C | — |
| Gudang | Bahan & Roll | S | C | C | lewat tautan dari Ringkasan Gudang |
| Gudang | Kain kantong | S | C | C | — |
| Gudang | Aksesori | S | C | C | — |
| Gudang | Ringkasan Barang Jadi | S | C | C | — |
| Gudang | Mutasi Barang Jadi · Vivo | S | C | C | — |
| Gudang | Mutasi Barang Jadi · Widie | S | C | C | — |
| Gudang | Kartu Stok FG | S | C | C | — |
| Gudang | Stock Adjustment | S | C | C | — |
| Gudang | Ganti Merek | S | C | C | rantai R2-07 pertama |
| Penjualan | Penjualan & Invoice | S | C | C | `D14_5_SERIES_DOZENS_*`, rantai R2-07 pertama, `R3_03_CHAIN_FG_TO_AR_ZERO` |
| Penjualan | Semua Invoice | S | C | C | — |
| Penjualan | Retur Penjualan | S | C | C | — |
| Penjualan | Pembayaran Pelanggan | S | C | C | `R3_03_CHAIN_FG_TO_AR_ZERO` |
| Penjualan | Riwayat Pelanggan | S | C | C | `R3_03_HISTORY_DESKTOP/_MOBILE` |
| Keuangan | Ringkasan Keuangan | S | C | C | — |
| Keuangan | Kas & Bank | S | C | C | `R3_03_CHAIN_SEWING_TO_CLOSE`, `R3_03_CHAIN_FG_TO_AR_ZERO` |
| Keuangan | Hutang Supplier & Vendor | S | C | C | — |
| Keuangan | Piutang Pelanggan | S | C | C | `R3_03_CHAIN_FG_TO_AR_ZERO` (Lunas, sisa Rp0) |
| Keuangan | Payroll & Kasbon | S | C | C | `KASBON_GIVE_DEDUCT_DESKTOP`, rantai R2-07 kedua, `R3_05_ACCESSORY_NOTE_TO_PAYROLL_DESKTOP`, `R3_03_CHAIN_SEWING_TO_CLOSE`, `R3_03_GUARDS_REFUSE` |
| Keuangan | Absensi & Rate Harian | S | C | C | — |
| Keuangan | Nota Ambil Aksesori | S | C | C | `R3_05_ACCESSORY_NOTE_TO_PAYROLL_DESKTOP` |
| Keuangan | HPP & Rekalkulasi | S | C | C | `G2_FINISH_*`, `R2_PO_REOPEN_*` |
| Keuangan | Jurnal & Transaksi Lain | S | C | C | `R3_03_GUARDS_REFUSE` (D15-5) |
| Keuangan | Laporan & Tutup Buku | S | C | C | `R3_03_PERIOD_TAB_DESKTOP/_MOBILE` (dua tab, riwayat, ADMIN tanpa tab), rantai R2-07 pertama, `R3_03_CHAIN_SEWING_TO_CLOSE` |
| Master Data | Kain & Benchmark | S | C | C | `R2_MASTER_FABRIC_*` |
| Master Data | Aksesori & Harga Mandor | S | C | C | `R2_MASTER_ACCESSORY_*` |
| Master Data | Produk & SKU | S | C | C | rantai R2-07 kedua |
| Master Data | Pelanggan | S | C | C | `R2_MASTER_CUSTOMERS_*` |
| Master Data | Supplier & Vendor | S | C | C | `R2_MASTER_PARTNERS_*` |
| Master Data | Mandor | S | C | C | `R2_MASTER_WORKFORCE_RATES_*`, rantai D15-3 |
| Master Data | Gudang & Lokasi | S | C | C | `R2_MASTER_LOCATIONS_*` |
| Master Data | Pola | S | C | C | — |
| Pengaturan & Audit | Reminder | S | C | C | `R3_03_REMINDERS_DESKTOP/_MOBILE` |
| Pengaturan & Audit | Pengguna & Hak Akses | S | C | C | — |
| Pengaturan & Audit | Pengaturan ERP | S | C | C | `R3_03_ERP_SETTINGS_DESKTOP/_MOBILE` |
| Pengaturan & Audit | Impor data awal | S | C | C | `R2_D15_5_CUTOVER_*`, kedua rantai R2-07 |
| Pengaturan & Audit | Audit Trail | S | C | C | `R3_03_AUDIT_DESKTOP/_MOBILE` |

Semua id di kolom terakhir berawalan `CP17_BROWSER_`. Jumlah: mode **Enteng** 46 tersambung, 1 pemberitahuan
(Dashboard), **0 disembunyikan, 0 data contoh**. Mode **uji** sama. Mode **demo** 47 data contoh.
Sebelum r3 (kandidat r2): Enteng 29 tersambung, 17 disembunyikan, 1 layar batas, 1 pemberitahuan.

## 2. Hal yang sudah terlihat penulis (untuk diperiksa)

1. **Tersambung di Enteng butuh lapisan CP7 terpasang.** Layar baru r3 memanggil RPC `erp_cp7_*` yang belum ada di
   database Enteng (CP7C ditahan, D13-9a). Pemeriksaan yang hanya bisa dilakukan di database Enteng saat pemasangan:
   `../../cp17/R3_INSTALL_TIME_CHECKS.md`.
2. **Build Enteng diuji terhadap salinan sekali pakai**, bukan terhadap hosted. Kunci publik di build itu adalah kunci
   pengganti; host proyek Enteng dipetakan ke API lokal di mesin CI.
3. **Pool HPP absensi** (R3-04) dipasang di halaman HPP & Rekalkulasi, tidak sebagai menu baru; status dan kasusnya
   ditulis di `CROSS_AUDIT.md` dan `docs/cp7/cp17/CP17_FIXES.json`.
4. Menu bertanda "—" tidak punya uji browser baru di r3; uji lama per layar ada di peta-peta sebelumnya. Sensus lebar
   HP 390 px untuk semua menu berjalan di build demo; layar tersambung diperiksa lebar HP-nya hanya pada layar yang
   dilewati uji browser HP.
