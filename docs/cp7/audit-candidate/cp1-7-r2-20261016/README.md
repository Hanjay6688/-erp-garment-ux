# Paket uji ulang r2 CP1–CP7 (perbaikan atas audit gabungan `dfab13bf`)

**Status: DRAF — kualifikasi satu commit belum selesai. Jangan dikirim.**

Fable, Astra dan Sol mengaudit kandidat gabungan `dfab13bf` (paket D14-16). Penulis menyatukan ketiga laporan per akar
masalah di `CROSS_AUDIT.md` (R2-01 sampai R2-10), lalu memperbaiki semuanya di cabang `claude/r2-fixes-20261016`
bersama keputusan owner D15-1 sampai D15-6 (`docs/cp7/OWNER_DECISIONS_20261008.md`). Paket ini satu kandidat untuk
ketiga auditor. Owner yang mengirim: salin kotak di `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md` dan `HANDOFF_SOL.md` ke sesi
masing-masing auditor. Penulis tidak mengirim apa pun.

| Berkas | Isi |
|---|---|
| `README.md` | Status, kandidat, perbaikan per akar, butir yang sudah diketahui |
| `CROSS_AUDIT.md` | Audit silang ketiga laporan `dfab13bf` dan rencana r2 (ditulis sebelum perbaikan; status di §7) |
| `SCREEN_MAP.md` | 48 menu × 3 mode sesudah D15-2, uji browser per layar |
| `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md`, `HANDOFF_SOL.md` | Kotak yang disalin owner ke sesi masing-masing auditor |
| `CI_RECEIPT.json` | Semua run workflow dan job pada kandidat (`scripts/cp7_ci_receipt.py`) |
| `WRITER_HANDOFF.md` | Serah-terima untuk penulis cadangan (bukan untuk auditor) |

## Kandidat

(diisi sesudah kualifikasi)

## Perbaikan per akar

Kasus CP17 dideklarasikan sebelum dijalankan di `docs/cp7/cp17/CP17_FIXES.json` (bagian `findings` menjelaskan tiap akar
dalam bahasa Inggris) dan dijalankan workflow "CP7 CP17 Fixes". Kasus gagal auditor dipakai dengan angka dan hasil yang
diharapkan auditor sendiri; penjaga lama tidak dilonggarkan.

| Akar | Temuan | Keputusan owner | Yang berubah | Uji |
|---|---|---|---|---|
| R2-01 penjaga kas | FABLE-013, SOL-R1-001 | D15-1 | Penjaga kas menilai tanggal ekonomi **dan** tanggal buku; koreksi pembayaran pelanggan, koreksi transaksi lain-lain dan koreksi nota penjualan dinilai pada keadaan akhirnya (bukan setengah jalan); detektor memeriksa kedua tanggal. `scripts/cp7-src/finance/dated-guards.sql`, `misc-correction.sql`, `sales/correction.sql`, `sales/payment-correction.sql` | `CP17_R2_CASH_BOOK_DATE_REFUSED` (skenario Fable), `CP17_R2_SPENT_INCOME_*` dan `CP17_R2_MISC_/NOTE_CORRECTION_*` (contoh Sol dengan angkanya), `CP17_R2_COMPOUND_SCOPE_PRIVATE_AND_CLOSED`, `CP17_R2_DETECTOR_BOOK_DATE_LISTED`, `CP17_RACE_R2_CORRECTION_AND_PAYMENT_ONE_BANK`, `CP17_HTTP_R2_SPENT_INCOME_*`; juga workflow koreksi lama (Misc, Payment, Note Correction) |
| R2-02 mode Enteng | FABLE-015, ASTRA-C17-03, Sol KNOWN-UI-MODE | D15-2 | Satu tabel aktivasi per menu per mode (`src/screenActivation.ts`). Di build Enteng menu tanpa layar tersambung tidak tampil dan rutenya menampilkan layar batas tanpa angka; label SIMULASI UX tetap ada walau kepala halaman punya tombol; pemberitahuan Dashboard hanya menyebut bagian yang tersambung | `src/screenActivation.test.ts`, `src/OwnerDashboard.dom.test.tsx` (`npm test` di workflow Build UX dan CP7 Shell S0) |
| R2-03 data master + tarif mandor | FABLE-017, ASTRA-C17-04, Sol KNOWN-DAILY-MASTER | D15-3 | Layar tersambung Pelanggan, Supplier & Vendor, Mandor (+ tarif upah per model × komponen, berlaku mulai tanggal), Gudang & Lokasi, Kain & Benchmark, Aksesori & Harga Mandor. `scripts/cp7-src/master/master.sql`, `rates.sql`; layar jahit menampilkan tarif yang berlaku pada tanggal jahit | `CP17_R2_MASTER_*`, `CP17_RACE_R2_MASTER_*`, `CP17_HTTP_R2_MASTER`, `CP17_HTTP_R2_WORK_RATE`, browser desktop + HP per layar, rantai `CP17_BROWSER_R2_FABLE_D15_3_SCREEN_CHAIN_DESKTOP` |
| R2-04 PO harian | SOL-R1-002 | D15-6 | Buat Potongan membuat PO otomatis saat disahkan, satu transaksi dengan posting potongan; UUID sama = jawaban sama; draf tanpa efek. `scripts/cp7-src/cutting-correction/auto-po.sql`. Sesudah simpan di mode "PO yang sudah ada" layar memuat ulang data kedua mode, tidak lagi terkunci (temuan penulis saat kualifikasi, `3b7cf370`) | `CP17_R2_D15_6_*`, dua race, HTTP, browser desktop + HP; dua kasus DOM di `src/ConnectedProductionRecovery.dom.test.tsx`; uji browser potong F04 lama |
| R2-05 selesai PO + buka ulang | FABLE-014, ASTRA-C17-05 | D15-4 | Ruang kerja memakai predikat penjaga Native; teks HPP dari status server; tombol buka ulang PO dengan penghalang. `finish.sql`, `po-reopen.sql`, `src/PoFinishPanel.tsx` | Tiga perjalanan Astra (`CP17_R2_ASTRA_G1_G2_*`, `CP17_R2_ASTRA_G2_*`) dengan hitungannya sendiri, `CP17_R2_PO_REOPEN_*`, race, HTTP, browser desktop + HP |
| R2-06 seri lusin penjualan | ASTRA-C17-01, ASTRA-C17-02 | — | Seri = merek + SKU dari server; simpan diblokir dan centang tinjauan dihapus selama ukuran dimuat. `src/SalesDraftPanel.tsx` | Kasus DOM ASTRA-C17-01 dan -02 (`src/SalesDraftPanel.dom.test.tsx`); browser D14-5 dengan merek kedua yang SKU-nya sama |
| R2-07 bukti alur lewat aplikasi | FABLE-016, ASTRA-C17-07, Sol BROWSER-CHAIN | — | Dua rantai browser yang hanya memakai layar, mulai dari Impor data awal: (1) WIP → barang jadi merek A → Ganti Merek ke B → tutup buku di tengah rantai → jual → pembayaran ke bank → buka buku; buku yang ditutup tetap sama; (2) komponen kerja dan tarif mandor di Master Data → WIP dipisah sebagai BS → resep aksesori produk impor ditetapkan (tanpa aksesori) di Produk & SKU → BS diklasifikasi dengan komponen itu → order rework ke mandor → hasil → upah rework masuk Nota → payroll dihitung, disetujui, dibayar dari bank | `CP17_BROWSER_R2_07_IMPORT_WIP_BRAND_SALE_CASH_CLOSE`, `CP17_BROWSER_R2_07_BS_REWORK_NOTA_PAYROLL_PAY` |
| R2-08 alat uji arsip CI | ASTRA-C17-06, SOL-R1-003, catatan Fable T2 | — | Daftar "sebelum U" sadar titik berhenti; G01, T2 dan 37 workflow CP6 lama memanggil bootstrap dari checkout cabang sekarang dan tetap jalan walau arsip AC sudah terhapus. Langkah X dan oracle tidak diubah | 36 dari 37 workflow CP6 lama dijalankan di kandidat (satu tidak punya pemicu manual); hasil per workflow di bagian Kandidat dan `CI_RECEIPT.json` |
| R2-09 layar demo melebar di HP | SOL-R1-004, SOL-R1-005 | — | Tata letak QC & Final SKU dan HPP & Rekalkulasi di HP 390 px (tanpa menyembunyikan isi yang keluar) | Workflow "UI phone width census": 48 menu build demo pada 390 px, `scrollWidth <= innerWidth` |
| R2-10 jahit selesai wave BF | Sol KNOWN-BF-WAVE | — | Selesai jahit per SKU untuk potongan wave dengan tarif snapshot per SKU; jalur dasar menolak potongan wave. `sewing.sql`, `src/SewingCompletionPanel.tsx` | `CP17_R2_10_*`, race, HTTP, browser desktop + HP |
| D15-5 lantai tanggal cutover | FABLE-011 | D15-5 | Tanggal cutover resmi (WIB) disahkan di aplikasi pada layar Impor data awal; server menolak jurnal dan gerakan stok operasional baru bertanggal sebelumnya; jalur saldo awal/migrasi dan pembalik tetap lewat jalurnya. `scripts/cp7-src/cutover/cutover.sql` | `CP17_R2_D15_5_*` (batas 00:00 vs 23:59:59 WIB, jalur saldo awal, gagal di tengah, kirim ulang), dua race, HTTP, browser desktop + HP |

FABLE-005 (pemetaan 75 C6 + 22 ALL) ditutup dengan menyalin berkas Astra byte demi byte ke
`docs/evidence/c6-all-crosswalk/` (syarat Fable sendiri). FABLE-012 tetap ditunda ke CP7C (D14-9).

## Butir yang sudah diketahui penulis (bukan temuan auditor; boleh diuji)

- **Pool HPP absensi** tidak punya layar yang menjalankan siklusnya, dan r2 tidak menambahkannya. Ini batas yang dicatat
  penulis, bukan keputusan owner. Konteks: D15-2 menyembunyikan layar absensi di mode Enteng sampai tersambung.
- **Lapisan CP7 belum terpasang di Enteng** (CP7C ditahan, D13-9a). Layar yang tercatat CONNECTED untuk Enteng di
  `src/screenActivation.ts`, termasuk layar master baru, memanggil RPC `erp_cp7_*` yang baru ada sesudah pemasangan itu.
  Semua uji browser memakai build `DISPOSABLE_TEST` di database sekali pakai.
- **Produk dari impor belum punya resep aksesori.** Native menolak QC → barang jadi dan order rework untuk produk itu
  sampai resepnya ditetapkan di layar Produk & SKU (boleh "tanpa aksesori"). Resep dari layar itu berlaku mulai saat
  disimpan (BF_HISTORY menolak awal yang lampau), jadi kejadian yang lebih awal tidak bisa memakainya. Rantai R2-07 kedua
  menjalankan urutan ini (temuan penulis saat menulis rantai itu, run 38875002986).
- **Tanggal cutover resmi** belum berlaku di mana pun sampai disahkan lewat aplikasi; sebelum itu penjaga D15-5 tidak
  menolak apa pun.
- **Sensus lebar HP** memeriksa build demo. Layar tersambung diperiksa per uji browser (`noSideScroll`) hanya pada layar
  yang dilewati uji itu.
- **FABLE-012:** 82 penulis `erp` masih bisa dieksekusi peran `authenticated` lewat SQL; tidak terjangkau lewat Data API.
  Pencabutan ditunda ke CP7C (D14-9).

## Larangan (sama dengan putaran sebelumnya)

Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy
ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only), production. Mode Enteng diuji dengan build lokal + backend sekali pakai
atau HTTP tiruan, bukan ke hosted. Tidak meminta password, token atau kunci di chat. `production_go:false`.
