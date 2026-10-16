# Audit silang hasil Fable, Astra, Sol atas kandidat gabungan dfab13bf (16 Okt 2026)

Disusun penulis Claude sesudah ketiga laporan dikunci. Ini bukan audit independen; isinya: (1) menyatukan temuan ketiga
auditor per akar masalah, (2) memeriksa setiap klaim ke kode atau dengan reproduksi sendiri, (3) mencatat perbedaan
pendapat antar-auditor dan mana yang benar, (4) rencana perbaikan putaran r2. Pelajaran umum dipindah ke
`docs/ERP_BEST_PRACTICES.md`. `production_go:false`.

## 1. Sumber yang dibaca

| Auditor | Cabang (kepala) | Berkas utama | Vonis |
|---|---|---|---|
| Fable | `audit/fable-cp1-7-combined-dfab13bf-20261015` (`8677a399`; kunci `ccafdb18`) | `audit/fable_cp17_combined/RETEST_FABLE_dfab13bf.md`, `FINAL_FABLE.md`, `FINDINGS.json`, `OWNER_DECISIONS_TO_AUDITOR_20261016.md` | jangan pasang ke Enteng sebelum FABLE-013/015/017 beres |
| Astra | `audit/astra-cp1-7-combined-dfab13bf-20261016` (`5a5beeb2`; kunci `3a3da9ef`, lanjutan terkunci) | `audit/astra_cp17_combined/FINAL_ASTRA.md`, `RETEST_ASTRA_dfab13bf.md`, `FINDINGS.json`; `audit/astra_cp17_completion/FINAL_ADDENDUM_ASTRA.md`, `CHAIN_CLOSURE.md` | TAHAN |
| Sol | `audit/sol-cp1-7-combined-dfab13bf-20261016` (`278a95ce`) | `audit/sol_cp17_combined/FINAL_SOL.md`, `RETEST_SOL_dfab13bf.md`, `FINDINGS.json`, `WRITER_HANDOFF.md`, `OPEN_BOUNDARIES.json` | HOLD |

Ketiganya menyatakan tidak membaca hasil auditor lain sebelum mengunci (§16.7). Tidak ada auditor yang menemukan data
Native rusak tanpa terdeteksi; semua cacat baru berupa penjaga yang salah dasar, alur yang tidak ada di aplikasi, atau
tampilan yang menyesatkan.

## 2. Uji ulang temuan lama: sepakat

| Temuan lama | Fable | Astra | Sol | Kesimpulan |
|---|---|---|---|---|
| Bayar upah sebelum akrual (FABLE-001 / FIN01) | DITUTUP | DITUTUP | — | Tutup |
| Klaim laundry sebelum sumber/AP (FABLE-008 / FIN02) | DITUTUP | DITUTUP | — | Tutup |
| Kas kosong bisa bayar (SOL-001, D14-3) | lulus kasus penulis, tapi lihat FABLE-013 | — | DITUTUP untuk pengeluaran biasa, tapi lihat SOL-R1-001 | Tutup untuk pengeluaran tunggal; akar penjaga dibuka lagi di R2-01 |
| Rework/SCRAP (FABLE-006 / RWK01), pool HPP (HPP01), kartu stok (STK01) | DITUTUP | DITUTUP | — | Tutup |
| Pickup POSTED (FABLE-009 / SG-01), sisa kain (FABLE-010 / SG-02), rewash (SG-03) | DITUTUP | DITUTUP (dalam batas keputusan) | lulus | Tutup |
| Payroll bertumpuk (FABLE-007) | dugaan salah | tidak dibuka | — | Tutup |
| SOL-002 artefak BE, SOL-003 diagnosis | — | mitigasi terverifikasi | DITUTUP (akar AZ lama tetap tidak diketahui) | Tutup |
| FABLE-002/003/004 (dokumen) | DITUTUP (003 dengan catatan) | DITUTUP | — | Tutup |
| FABLE-005 pemetaan 75 C6 + 22 ALL | MASIH TERBUKA: pemetaan hanya di cabang Astra | — | — | **Ditutup penulis di r2:** pemetaan disalin byte demi byte ke `docs/evidence/c6-all-crosswalk/` (syarat Fable sendiri) |
| FABLE-011 lantai tanggal cutover | MASIH TERBUKA (keputusan owner) | belum aturan | item lama | **Perlu keputusan owner** (pertanyaan di laporan penulis) |
| FABLE-012 hak EXECUTE `erp` | ditunda D14-9 | ditunda D14-9 | ditunda D14-9 | Tetap ditunda ke CP7C |

## 3. Temuan baru, disatukan per akar masalah

Kolom "Periksa penulis" = hasil penulis membaca kode atau mereproduksi sendiri pada `dfab13bf`.

### R2-01 Penjaga kas: dasar tanggal dan keadaan setengah jalan — FABLE-013 (S2) + SOL-R1-001 (S1)

- **Dua auditor, satu komponen, arah berlawanan.** Fable: penjaga terlalu longgar (hanya tanggal ekonomi; laporan kas
  owner memakai tanggal buku, jadi saldo harian bisa tampil −500 tanpa ditolak dan detektor diam). Sol: penjaga terlalu
  ketat (koreksi pemasukan yang sudah terpakai ditolak walau saldo akhir masih positif, termasuk koreksi catatan saja).
- **Periksa penulis:** benar keduanya. `scripts/cp7-src/finance/dated-guards.sql`:
  `cp7_guard.min_debit_balance_from` dan `findings()` hanya menjumlah `journal_entries.economic_date`; trigger
  `cp7_guard_cash_not_negative` adalah `AFTER INSERT ... FOR EACH ROW` biasa, jadi dinilai di tengah perintah majemuk
  (balik dulu, baru pengganti) sebelum pengganti sempat diposting.
- **Keputusan owner:** D15-1 (dua dasar tanggal; juga detektor dan koreksi/pembalikan; tanggal asli tidak diubah).
- **Arah perbaikan:** kunci rekening tetap diambil saat baris ditulis (urutan sama seperti sekarang); penilaian saldo
  dipindah ke akhir transaksi (constraint trigger tertunda) dan memeriksa tanggal ekonomi **dan** tanggal buku untuk
  setiap rekening yang tersentuh; detektor memeriksa kedua dasar. Tidak ada overdraft, modal tambahan di fixture, atau
  penjaga yang dimatikan.
- **Uji penerimaan:** skenario Fable `fable_cp17c_cash_basis.py` tanpa perubahan harus ditolak; tiga contoh-penyangkal
  Sol (koreksi 30,01→25,01 sesudah terpakai 20; catatan saja; Native) harus lulus, dua kontrol Sol tetap; `CP17_CASH_*`
  tetap lulus; jalur majemuk lain (`finance/misc-correction.sql`, koreksi nota) ikut diuji.

### R2-02 Mode Enteng menampilkan angka contoh — FABLE-015 (S1 untuk Enteng) + ASTRA-C17-03 (S1) + KNOWN-UI-MODE Sol (S0)

- **Ketiganya sepakat, tingkat berbeda.** Penulis memakai tingkat tertinggi (S0) untuk dua layar uang tanpa label
  (Ringkasan Keuangan, Payroll & Kasbon). Penulis sudah mengungkapnya di `SCREEN_MAP.md` §2; pengungkapan tidak
  menurunkan tingkat.
- **Periksa penulis:** benar. `src/App.tsx` menyalakan penjualan, 6 layar keuangan dan absensi hanya bila mode
  `DISPOSABLE_TEST`; `FinanceHero` hanya menampilkan "SIMULASI UX" bila kepala halaman tanpa tombol.
- **Keputusan owner:** D15-2. Menyambungkan ke Enteng butuh CP7 terpasang di Enteng (CP7C, ditahan), jadi di Enteng
  layar uang/absensi disembunyikan sampai itu terjadi.
- **Arah perbaikan:** satu tabel aktivasi per menu per mode; di Enteng, menu uang/absensi yang belum aktif tidak tampil
  dan rute langsungnya menampilkan layar batas tanpa angka; label contoh dipasang di tingkat halaman, tidak bergantung
  pada tombol; pemberitahuan Dashboard tidak menunjuk menu yang masih contoh.
- **Uji penerimaan:** oracle Fable D15-2 (build Enteng: tidak ada angka contoh tanpa label; tiap layar uang tersambung
  atau tidak tampil), inventaris 48 menu × 3 mode × desktop/HP.

### R2-03 Data master harian tidak bisa dibuat dari aplikasi — FABLE-017 (S2) + ASTRA-C17-04 (S1) + KNOWN-DAILY-MASTER Sol (S1)

- **Ketiganya sepakat.** Fable menambah tarif upah mandor (dibutuhkan G1 untuk model/mandor baru).
- **Periksa penulis:** benar, dengan satu koreksi atas Fable: Native **punya** `erp.apply_bulk_rate_change` yang mengubah
  tarif mandor yang sudah ada (versi baru berlaku mulai sekarang), tetapi tidak bisa membuat tarif untuk mandor/model/
  komponen baru, dan tidak ada pembungkus `public` atau layarnya. Penulis pelanggan/supplier/mandor/bahan yang ada hanya
  lewat impor saldo awal (`erp.apply_migration_*`, bertanda migrasi).
- **Keputusan owner:** D15-3 (layar tingkat menengah, riwayat, hak akses).
- **Arah perbaikan:** fasad master CP7 (buat, ubah, nonaktifkan; riwayat yang tidak bisa diubah; token tinjauan;
  idempotensi; data yang sudah dipakai transaksi tidak bisa dihapus) untuk pelanggan, supplier/vendor, mandor,
  gudang/lokasi, kain, aksesori, tarif mandor (model × komponen × mandor, tanggal berlaku), memakai penulis Native bila
  ada. Pesan `NO_WORK_RATE` di G1 menunjuk layar tarif.
- **Uji penerimaan:** oracle Fable D15-3 (rantai dari layar saja: mandor + tarif baru → Bagi Potongan → jahit selesai
  dengan upah sesuai tarif pada tanggal jahit; pelanggan/supplier baru langsung dipakai), browser desktop/HP, HTTP,
  dua tab.

### R2-04 PO produksi harian tidak bisa dibuat — SOL-R1-002 (S1)

- **Hanya Sol.** Astra memakai PO dari fixture di perjalanan CUT_TO_FG; Fable tidak memeriksa pembuatan PO.
- **Periksa penulis:** benar. Satu-satunya `INSERT` ke `erp.production_orders` ada di `erp.apply_migration_open_pos`
  (impor saldo awal, bertanda legacy). Layar Buat Potongan hanya memilih PO yang sudah ada. Demo tidak punya langkah PO
  terpisah; nomor PO hanya muncul sebagai referensi.
- **Arah perbaikan:** jalur PO harian dari aplikasi (lihat pertanyaan untuk owner di laporan penulis tentang bentuknya).
- **Uji penerimaan:** penerimaan Sol (mulai tanpa PO aktif, buat PO lewat layar, lanjut sampai G2; nomor ganda, izin,
  replay, tidak ada stok/jurnal sebelum tahap yang memosting).

### R2-05 Selesaikan PO (G2): satu arah dan tampilan tidak jujur — FABLE-014 (S3) + ASTRA-C17-05 (S2)

- **Dua sisi berbeda dari satu panel.** Fable: tidak bisa dibuka ulang dari aplikasi, dan komentar sumber "no Native
  inverse exists" salah. Astra: panel tetap menyebut "HPP final" walau server `BELUM_LENGKAP/ESTIMATED`, dan
  `eligible=true` padahal Native menolak (6 pcs belum dijahit/dikirim; Native benar, stok aman).
- **Periksa penulis:** benar. `finish.sql` baris 8; `erp.reopen_production_order(uuid,text)` ada (migrasi v2_6_20ac);
  `src/PoFinishPanel.tsx` baris 76, 89–90, 130 berteks "final"; pemeriksaan ruang kerja tidak memasukkan predikat
  `erp.guard_finished_po_source_accounting`.
- **Keputusan owner:** D15-4 (tombol buka ulang dengan penghalang).
- **Arah perbaikan:** teks dari `display_status`; ruang kerja memakai predikat yang sama dengan penjaga Native; fasad dan
  tombol buka ulang; komentar dibetulkan. Penjaga Native tidak diubah.
- **Uji penerimaan:** oracle Fable D15-4; tiga kasus Astra (`ASTRA_G2_UNSEWN_SIX_MUST_NOT_FINISH`,
  `ASTRA_G2_SEWN_UNSENT_SIX_MUST_NOT_FINISH`: ruang kerja harus menyebut penghalang; status final mengikuti server).

### R2-06 Seri lusin penjualan — ASTRA-C17-01 (S1) + ASTRA-C17-02 (S2)

- **Hanya Astra.** Fable dan Sol menguji D14-5 pada fixture satu merek, jadi tidak bisa menemukannya.
- **Periksa penulis:** benar. `src/SalesDraftPanel.tsx`: kunci seri `series=p.commercial_sku` tanpa merek; pencarian
  ukuran memakai teks SKU sehingga Vivo dan Widie dengan nomor sama tercampur; `valid`/`save()` tidak memeriksa
  `seriesBusy`, dan centang "sudah diperiksa" tidak dihapus saat memilih seri baru.
- **Arah perbaikan:** identitas seri = merek + SKU (dari server, bukan teks tampilan); ukuran yang dimuat dibatasi ke
  merek yang sama; simpan diblokir dan tinjauan dihapus selama ukuran dimuat.
- **Uji penerimaan:** dua kasus DOM Astra tanpa perubahan + browser lintas merek desktop/HP + baca ulang server.

### R2-07 Bukti alur lewat aplikasi belum lengkap — FABLE-016 (S3) + ASTRA-C17-07 (S2) + batas BROWSER-CHAIN Sol

- **Sebagian sudah ditutup Astra sendiri** (perjalanan browser terkunci di addendum): posting Buat Potongan, Bagi
  Potongan, QC & Final SKU dalam satu PO (CUT_TO_FG), dan Nota Ambil Aksesori → potongan payroll → kas. Jadi FABLE-016
  untuk B3 dan B7 dan S4 sudah punya saksi aplikasi independen.
- **Sisa:** posting Ganti Merek lewat aplikasi; BS → rework → Nota → bayar dalam satu perjalanan; upah rework lewat
  aplikasi; impor WIP → produksi → jual → kas; siklus pool HPP absensi di layar; tutup periode di tengah rantai.
- **Arah perbaikan:** tambah kasus browser penulis untuk sisa itu, mulai dari master dan PO yang dibuat lewat layar
  (sesudah R2-03 dan R2-04), bukan dari SQL fixture.

### R2-08 Alat uji arsip CI kedaluwarsa belum menyeluruh — ASTRA-C17-06 (S2) + SOL-R1-003 (S3) + catatan Fable (T2)

- **Periksa penulis:** benar. `cp6-g01-baseline.yml` dan `cp6-t2-regression.yml` masih mengunduh arsip tanpa jalur
  pengganti, dan T2 memanggil bootstrap dari checkout kandidat beku; `cp6_t3_aligned_chain.py` memanggil
  `pre_u.finished()` walau rantai sengaja berhenti sebelum U. Penulis sudah menulis batas "37 workflow CP6 lama tidak
  bisa berjalan" di `GAPS_D14_14.md` §3a; Astra benar bahwa itu harus dibetulkan, bukan hanya dicatat.
- **Arah perbaikan:** `finished()` sadar titik berhenti (sebelum U: tidak berlaku, dicatat; sesudah U: tetap wajib);
  G01, T2 dan workflow CP6 lama lain memanggil bootstrap dari checkout auditor seperti `cp6-av-qualification`. Langkah X
  dan oracle tidak diubah; log gagal pertama disimpan.

### R2-09 Layar demo QC dan HPP melebar di HP — SOL-R1-004 (S2) + SOL-R1-005 (S2)

- **Pertentangan antar-auditor:** Astra mencatat "nol overflow horizontal" pada 288 pengamatan (termasuk demo HP); Sol
  mengukur QC 669 px dan HPP 627 px pada layar 390 px.
- **Periksa penulis (Chromium lokal, build demo `dfab13bf`, viewport 390×844):** `documentElement.scrollWidth` QC = **669**,
  HPP = **627**; elemen yang keluar: `span.result` (QC), `div.hpp-size-summary` (HPP). Pada 1440 px tidak melebar.
  **Sol benar; klaim Astra "nol overflow" keliru untuk dua layar ini.** Kemungkinan cara ukur berbeda (Astra tidak
  menyebut rumusnya).
- **Arah perbaikan:** tata letak kedua layar (bukan `overflow:hidden`); pemeriksaan otomatis `scrollWidth <= innerWidth`
  untuk 48 menu × 3 mode × HP di CI dengan rumus yang ditulis.

### R2-10 Jahit selesai untuk potongan bertarif wave BF — KNOWN-BF-WAVE Sol (S1)

- **Hanya Sol (batas yang sudah diungkap penulis).** `sewing.sql` menolak `WAVE_SKU_RATES` bila potongan punya
  `erp.bf_wave_skus_v1`.
- **Arah perbaikan:** jalur jahit selesai per SKU/ukuran dengan tarif snapshot wave dan alokasi upah per komponen; jalur
  dasar tidak dipakai untuk melewati penolakan.

## 4. Pertentangan dan koreksi antar-auditor

| Topik | Pendapat | Hasil periksa penulis |
|---|---|---|
| Layar demo melebar di HP | Astra: nol; Sol: QC 669 px, HPP 627 px | Sol benar (diukur ulang penulis). |
| Tarif mandor tanpa penulis | Fable: tidak ada penulis | Sebagian: Native bisa mengubah tarif yang ada (`apply_bulk_rate_change`), tidak bisa membuat yang baru; tanpa layar. |
| Tingkat layar contoh Enteng | Fable S1-untuk-Enteng, Astra S1, Sol S0 | Penulis memakai S0 untuk dua layar uang tanpa label. |
| Bukti aplikasi B3/B7/S4 | Fable: belum ada | Ditutup oleh perjalanan Astra sendiri (CUT_TO_FG, ACCESSORY_NOTA_TO_CASH). |
| "80 uji" di laporan penulis | Astra dan Sol: 80 run workflow / 131 job, bukan 80 kasus | Benar. Laporan penulis berikutnya menyebut run, job dan kasus secara terpisah. |
| 11 COUNTEREXAMPLE dan 16 NO_ROUTE di log penulis | Astra: konteks, bukan regresi | Diperiksa: semuanya di kelompok `*_BEFORE` (potret sebelum perbaikan untuk pembanding); 2 INCOMPLETE adalah celah UI CP7 di atas database lama yang sudah dikenal. Bukan regresi. |
| Kegagalan pertama Offsite Backup (port 54324) | Sol dan Astra: penyebab belum terbukti | Benar; penulis menulisnya sebagai dugaan. |

## 5. Temuan yang hanya ditemukan satu auditor

- Fable: FABLE-013 (dasar tanggal kas), FABLE-014 (G2 satu arah).
- Astra: ASTRA-C17-01/02 (seri lusin), ASTRA-C17-05 (G2 preflight dan label), ASTRA-C17-06 (entry point arsip).
- Sol: SOL-R1-001 (koreksi majemuk), SOL-R1-002 (PO harian), SOL-R1-003 (pre-U berhenti sebelum U), SOL-R1-004/005
  (layar HP).

Tiga akar ditemukan oleh ketiganya (layar contoh Enteng, data master, bukti aplikasi). Auditor independen yang berbeda
cara kerja menemukan cacat yang berbeda; satu auditor saja tidak cukup.

## 6. Rencana perbaikan r2 (urutan)

| Urut | Akar | Alasan urutan |
|---|---|---|
| 1 | R2-01 penjaga kas | Uang; menyentuh semua pengeluaran; keputusan owner sudah ada |
| 2 | R2-06 seri penjualan | S1, barang salah merek bisa terjual |
| 3 | R2-05 selesai PO + buka ulang | Keputusan owner ada; panel sudah ada |
| 4 | R2-02 mode Enteng | S0; perubahan routing dan label |
| 5 | R2-03 data master + tarif | Terbesar; prasyarat R2-04, R2-07 |
| 6 | R2-04 PO harian | Butuh bentuk dari owner |
| 7 | R2-10 wave BF | Sesudah tarif master |
| 8 | R2-07 bukti aplikasi | Sesudah 3–7, mulai dari data yang dibuat di layar |
| 9 | R2-08 alat uji, R2-09 layar HP | Kecil, bisa sejalan |

Setiap akar: kasus gagal auditor dipakai apa adanya (nominal dan expected tidak diganti), kontrol negatif tetap,
penjaga lama tidak dilonggarkan, log gagal disimpan, lalu kualifikasi satu commit dan satu paket uji ulang ke ketiga
auditor.
