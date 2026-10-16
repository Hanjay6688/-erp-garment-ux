# Peta layar sesudah r2: 48 menu × 3 mode (D15-2)

Disusun penulis dari `src/screenActivation.ts` pada kandidat r2. Ini titik awal untuk auditor, bukan bukti lulus.
Peta sebelumnya (kandidat `dfab13bf`, beserta uji browser lama per layar): `../cp1-7-final-integration-20261015/SCREEN_MAP.md`.

## Cara aplikasi memilih layar sekarang

- Satu tabel, `src/screenActivation.ts` (`SCREEN_ACTIVATION`), menyatakan untuk setiap menu bagaimana ia tampil di mode
  Enteng (`UAT_AUTH_SIMULATION`) dan mode uji (`DISPOSABLE_TEST`). Mode demo (`DEMO_SIMULATION`) selalu data contoh.
- Di mode Enteng, menu bertanda **HIDDEN** tidak ada di sidebar; rute langsungnya menampilkan layar batas tanpa angka;
  halaman pertama melewatinya; pemberitahuan Dashboard hanya menyebut bagian yang punya layar tersambung. Menu itu
  muncul begitu barisnya diubah menjadi CONNECTED (owner D15-2: "sembunyikan begitu terhubung langsung muncul").
- Label SIMULASI UX di halaman keuangan contoh tidak lagi bergantung pada ada-tidaknya tombol di kepala halaman.
- Uji: `src/screenActivation.test.ts` memindai kode routing (setiap layar yang hanya tersambung di build uji harus
  HIDDEN di Enteng; tidak ada menu Enteng yang berupa data contoh) dan `src/OwnerDashboard.dom.test.tsx`.

Kode: **C** = tersambung (CONNECTED), **S** = data contoh (SAMPLE), **H** = disembunyikan (HIDDEN), **B** = layar batas,
**N** = pemberitahuan tanpa angka.

## 1. Semua 48 menu

| Bagian | Menu | Demo | Enteng | Uji | Uji browser baru di r2 (workflow CP7 CP17 Fixes) |
|---|---|---|---|---|---|
| Dashboard | Dashboard | S | N | N | — |
| Produksi | Buat Potongan | S | C | C | `CP17_BROWSER_R2_D15_6_AUTO_PO_DESKTOP/_MOBILE` (PO otomatis) |
| Produksi | Bagi Potongan | S | C | C | rantai D15-3 (`CP17_BROWSER_R2_FABLE_D15_3_SCREEN_CHAIN_DESKTOP`), PO otomatis |
| Produksi | WIP & Sewing | S | C | C | G1 desktop/HP, `CP17_BROWSER_R2_10_WAVE_SEWING_*`, rantai D15-3, PO otomatis |
| Produksi | Laundry | S | C | C | — |
| Produksi | QC & Final SKU | S | C | C | — (tata letak HP: sensus demo) |
| Produksi | Susun Nota FG | S | B | C | rantai R2-07 kedua |
| Produksi | Barang BS & Rework | S | C | C | rantai R2-07 kedua |
| Gudang | Ringkasan Gudang | S | H | S | — |
| Gudang | Pembelian & Penerimaan | S | C | C | — |
| Gudang | Bahan & Roll | S | C | C | — |
| Gudang | Kain kantong | S | C | C | — |
| Gudang | Aksesori | S | C | C | — |
| Gudang | Ringkasan Barang Jadi | S | C | C | — |
| Gudang | Mutasi Barang Jadi · Vivo | S | C | C | — |
| Gudang | Mutasi Barang Jadi · Widie | S | C | C | — |
| Gudang | Kartu Stok FG | S | C | C | — |
| Gudang | Stock Adjustment | S | C | C | — |
| Gudang | Ganti Merek | S | C | C | rantai R2-07 pertama |
| Penjualan | Penjualan & Invoice | S | H | C | D14-5 desktop/HP (merek kedua SKU sama), rantai R2-07 pertama (jual + bayar) |
| Penjualan | Semua Invoice | S | H | C | — |
| Penjualan | Retur Penjualan | S | H | C | — |
| Penjualan | Pembayaran Pelanggan | S | H | C | — |
| Penjualan | Riwayat Pelanggan | S | H | S | — |
| Keuangan | Ringkasan Keuangan | S | H | C | — |
| Keuangan | Kas & Bank | S | H | C | — |
| Keuangan | Hutang Supplier & Vendor | S | C | C | — |
| Keuangan | Piutang Pelanggan | S | H | C | — |
| Keuangan | Payroll & Kasbon | S | H | C | kasbon desktop, rantai R2-07 kedua (hitung, setujui, lunasi) |
| Keuangan | Absensi & Rate Harian | S | H | C | — |
| Keuangan | Nota Ambil Aksesori | S | C | C | — |
| Keuangan | HPP & Rekalkulasi | S | C | C | G2 desktop/HP, `CP17_BROWSER_R2_PO_REOPEN_*` |
| Keuangan | Jurnal & Transaksi Lain | S | H | C | — |
| Keuangan | Laporan & Tutup Buku | S | H | C | rantai R2-07 pertama (tutup lalu buka buku) |
| Master Data | Kain & Benchmark | S | C | C | `CP17_BROWSER_R2_MASTER_FABRIC_*` |
| Master Data | Aksesori & Harga Mandor | S | C | C | `CP17_BROWSER_R2_MASTER_ACCESSORY_*` |
| Master Data | Produk & SKU | S | C | C | rantai R2-07 kedua (resep aksesori produk impor) |
| Master Data | Pelanggan | S | C | C | `CP17_BROWSER_R2_MASTER_CUSTOMERS_*` |
| Master Data | Supplier & Vendor | S | C | C | `CP17_BROWSER_R2_MASTER_PARTNERS_*` |
| Master Data | Mandor | S | C | C | `CP17_BROWSER_R2_MASTER_WORKFORCE_RATES_*`, rantai D15-3, rantai R2-07 kedua (komponen + tarif) |
| Master Data | Gudang & Lokasi | S | C | C | `CP17_BROWSER_R2_MASTER_LOCATIONS_*` |
| Master Data | Pola | S | C | C | — |
| Pengaturan & Audit | Reminder | S | H | S | — |
| Pengaturan & Audit | Pengguna & Hak Akses | S | C | C | — |
| Pengaturan & Audit | Pengaturan ERP | S | H | S | — |
| Pengaturan & Audit | Impor data awal | S | C | C | `CP17_BROWSER_R2_D15_5_CUTOVER_*` (tanggal cutover), kedua rantai R2-07 (CSV, periksa, sahkan, hasil WIP, pisah BS) |
| Pengaturan & Audit | Tutup Periode | S | H | S | — |
| Pengaturan & Audit | Audit Trail | S | H | S | — |

Jumlah: mode **Enteng** 29 tersambung, 17 disembunyikan, 1 layar batas (Susun Nota FG), 1 pemberitahuan (Dashboard),
**0 data contoh**. Mode **uji** 41 tersambung, 6 data contoh, 1 pemberitahuan. Mode **demo** 48 data contoh.
Sebelum r2 (kandidat `dfab13bf`): Enteng 23 tersambung dan 23 data contoh.

## 2. Hal yang sudah terlihat penulis (untuk diperiksa)

1. **Tersambung di Enteng butuh lapisan CP7 terpasang.** Banyak layar C memanggil RPC `erp_cp7_*`, termasuk enam layar
   master baru. Lapisan CP7 belum dipasang di Enteng (CP7C ditahan, D13-9a). Tabel aktivasi menyatakan layar mana yang
   tampil; ia tidak membuktikan bahwa RPC-nya sudah ada di database Enteng.
2. **Semua uji browser memakai build `DISPOSABLE_TEST`.** Mode Enteng diperiksa lewat pemindaian kode routing dan uji
   DOM, bukan uji browser terhadap backend sungguhan (sesuai larangan menyentuh hosted).
3. **Lebar HP.** Sensus 48 menu pada 390 px berjalan di build demo (workflow "UI phone width census"); layar tersambung
   diperiksa hanya pada layar yang dilewati uji browser HP.
4. **Pool HPP absensi** tidak punya layar yang menjalankan siklusnya (batas penulis, bukan keputusan owner).
5. Tidak ada uji browser baru untuk menu yang di tabel bertanda "—"; uji lama per layar ada di peta sebelumnya.
