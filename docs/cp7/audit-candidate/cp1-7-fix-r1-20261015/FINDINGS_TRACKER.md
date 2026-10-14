# Perbaikan sesudah audit penuh CP1–CP7 — daftar gabungan (penulis)

Kandidat yang diaudit: `0b7049d9203bac52b47a4c89f3e0d75646067a8f` (tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`).
Ketiga laporan sudah dikunci sebelum penulis mulai memperbaiki. Daftar ini disusun penulis per akar masalah, mengikuti
Pro Max §10–§11; ini bukan penyatuan resmi auditor dan bukan penerimaan. `production_go:false`.

| Auditor | Laporan terkunci | Vonis |
|---|---|---|
| Fable | `audit/fable_cp17/AUDIT_FABLE_0b7049d9.md` v1.0 (`746693bf`, koreksi `3b0010e0`) + addendum A1–A3 (`1224901f`, `f24c71b8`, `681dd7a9`), cabang `audit/fable-cp1-7-0b7049d9-20261014` | CP1 dan CP2 lulus dengan syarat (sesudah D14-1), CP3/CP5/CP6 lulus dengan syarat, CP4 lulus dengan syarat, CP7 lulus |
| Astra | `audit/astra_cp17/AUDIT_ASTRA_CP17_0b7049d9.md` (`f70361d5`), lanjutan (`d5dcf4e3`), addendum silang `followup-681dd7a9/` (`d4a83b42`), cabang `audit/astra-cp1-7-0b7049d9-20261014` | TAHAN penerimaan penuh |
| Sol | `audit/sol_cp1_7/AUDIT_REPORT.md`, `FINDINGS.json`, `WRITER_HANDOFF.md` (`10bfe397`), cabang `audit/sol-cp1-7-0b7049d9-20261014` | HOLD |

Keputusan owner yang dipakai: D14-2..D14-7 (`../../OWNER_DECISIONS_20261008.md`, 15 Okt 2026).

## A. Cacat yang terbukti saat dijalankan (wajib diperbaiki)

| ID gabungan | Asal | Keparahan tertinggi | Masalah | Rencana penulis |
|---|---|---|---|---|
| R-FIN01 | Fable FABLE-001, Astra FIN01 | S0 (Astra) | Bayar upah (penuh, cicilan final, cicilan sebagian) boleh bertanggal sebelum utang upahnya diakui; utang per tanggal minus, tidak ada alarm | D14-2: tolak di batas Native pembayaran upah dan perintah CP7 PAY/cicilan bila tanggal bayar mendahului akrual sumber yang dilunasi; kasbon tetap jalur tersendiri. Tambah detektor utang upah per mandor per tanggal < 0. Kasus PAY04/05/06/FIN07 + kontrol same-day/later, replay, pembalikan, periode tertutup, browser |
| R-CASH01 | Sol SOL-001 | S1 | Bank saldo 0 bisa membayar supplier; saldo jadi minus | D14-3: penjaga bersama per akun kas, kronologis (tidak ada tanggal ≥ tanggal bayar dengan saldo < 0), dikunci per akun; semua pengeluaran (supplier, laundry, upah, kas lain, uang muka, refund). Race dua pembayaran, backdate, pembalikan, detektor |
| R-FIN02 | Fable FABLE-008, Astra FIN02 | S0 (Astra) | Penyelesaian klaim laundry bertanggal sebelum sumber klaim dan utang vendor; AP vendor per tanggal minus, laba pindah hari | Kapasitas kompensasi dihitung per tanggal pengakuan dan tidak boleh mendahului tanggal klaim; D12 (kredit lintas tagihan) tetap sah. MISSING/STUCK/DAMAGE, same-day/later, replay, race, periode tertutup, browser |
| R-RWK01 | Fable FABLE-006, Astra RWK01 | S1 | Upah rework yang sudah diakui utang hilang dari Nota bila semua hasil di-SCRAP | Kelayakan Nota mengikuti kerja yang sah diakui, bukan label hasil barang. ALL-BS/SCRAP 60 bisa masuk Nota dan dibayar sekali; GOOD, campuran, WRITE_OFF/HOLD, pembalikan, browser |
| R-STK01 | Astra STK01 | S0 (Astra) | Sesudah REOPEN lalu POST ulang potongan bertanggal lama, kartu stok historis menampilkan saldo −10 | Pembaca kartu stok "restated" tidak menghitung pasangan asli/pembalik yang sudah netral sebagai dua pemakaian aktif; riwayat tetap terlihat. Selaraskan dengan mesin biaya; kasus sampai re-POST, variasi jumlah/tanggal, browser |
| R-HPP01 | Astra HPP01 (petunjuk Fable R1-02) | S1 | Kebijakan HPP baru untuk mandor yang sebelumnya tidak ikut membuat pool ACTIVE basi tanpa ditolak | Perubahan kebijakan yang mengubah himpunan peserta pool ACTIVE ditolak atomik (atau lewat pembatalan → pool pengganti). Kasus asli, kontrol tidak relevan, batas tanggal berlaku, race, detektor |

## B. Alur yang belum ada (dari pembacaan kode; wajib dilengkapi)

| ID | Asal | Masalah | Rencana |
|---|---|---|---|
| R-SG01 | Fable FABLE-009, Astra SG-01 | Bagi Potongan (pickup) yang sudah POSTED tidak punya jalur koreksi | Pembalik/pengganti milik Native untuk pickup produksi, dengan penghalang dependency yang menunjuk jalan keluarnya; pengaman immutabilitas tetap. Uji salah mandor/tanggal/batch sebelum dan sesudah jahit/laundry/QC |
| R-SG02 | Fable FABLE-010, Astra SG-02 | Sisa kain hanya "terlapor", tidak bisa masuk stok lagi | D14-4: langkah "kain kembali ke gudang" per roll/lokasi/waktu memakai `post_cutting_material_returns` yang sudah ada; nilai kembali dan biaya PO turun. Pakai lagi, pembalikan, replay, browser |
| R-SG03 | Astra SG-03 | Rewash berbayar tanpa ganti SKU belum punya sumber tagihan | Sudah diputuskan owner lewat D06 (Lampiran C6 rev4): LAU-06a cuci ulang produk sama **tanpa tagihan vendor**, LAU-T28 meminta fee 0 yang eksplisit dan berversi; fee cuci ulang hanya lewat LAU-05b (tarif vendor) atau LAU-06b (celup ulang ke SKU baru). Penulis membuktikan fee 0 eksplisit itu dengan kasus, tanpa menambah jalur tagihan baru |
| R-KASBON | D14-6 (akibat D14-2) | Kasbon tunai ke mandor sesudah cutover belum bisa dicatat | Pencatatan kasbon tunai (kas keluar → piutang mandor) yang dipotong otomatis di payroll berikutnya, tunduk pada aturan kas D14-3 |
| R-LUSIN | Sol (kebutuhan lama `SALES_MANUAL_13`) | Form penjualan tersambung belum bisa membagi lusin ke satu seri ukuran | D14-5: bagi rata otomatis ke ukuran seri + tampilan balik "x lusin y potong"; bagi tidak rata ditolak dengan pesan jelas. Uji unit, browser desktop/HP, simpan/baca ulang |

## C. Akses

| ID | Asal | Masalah | Rencana |
|---|---|---|---|
| R-ACC01 | Fable FABLE-012; Astra RBAC (2 kasus PASS, 6 penolakan) | Peran `authenticated` punya USAGE skema `erp` dan EXECUTE ke 160 fungsi `erp` (108 bernama penulis). Pemeriksaan peran di dalam fungsi menolak non-owner, tetapi jalur langsung melewati fasad | Inventaris dulu siapa yang memanggil tiap fungsi (fasad SECURITY DEFINER, trigger, pembaca); lalu cabut EXECUTE langsung dari `authenticated` yang tidak dibutuhkan; panggilan langsung → 42501; seluruh suite fasad tetap lulus. Skema yang diekspos API hosted: owner mengizinkan Fable membaca (D14-7), owner yang menyampaikan ke Fable |

## D. Alat bukti dan dokumen

| ID | Asal | Masalah | Rencana |
|---|---|---|---|
| R-EV01 | Sol SOL-002 | Artefak BE hanya 4/16 karena impor AV memindahkan folder keluaran global | Folder keluaran tetap per run; gerbang unggah memeriksa himpunan ID, jumlah dan status akhir |
| R-EV02 | Sol SOL-003, OPEN-AZ-FIRST | Pemasang membuang pesan PostgreSQL saat berhenti di AZ; penyebab kegagalan pertama 51/58 belum diketahui | Simpan pesan/konteks/berkas+hash secara privat; telusuri kegagalan pertama tanpa melonggarkan pengaman |
| R-DOC01 | Fable FABLE-002 | Dua salinan migrasi AC berbeda (`supabase/migrations` vs `supabase/release/cp6-t3`) | Tetapkan salinan paket rilis sebagai kanonik untuk pemasangan baru, tambahkan pemeriksaan/penjelasan perbedaan; berkas lama tidak diubah, pengaman tidak dilonggarkan |
| R-DOC02 | Fable FABLE-003 | Manifest T3 masih `rollbacks: NOT_TESTED`, label T3_PREP, komentar jumlah berkas basi | Rujuk bukti rollback yang sudah lulus; betulkan komentar |
| R-DOC03 | Fable FABLE-004; Astra CP1_CP2_CROSSCHECK | Bukti CP1/CP2 tidak ada di pohon kandidat | Bawa skrip/bukti CP1/CP2 (hash, bukan rahasia) ke pohon; restore CP2 di image Supabase asli menjadi bagian CP7C |
| R-DOC04 | Fable FABLE-005 | Rencana 75 C6 + 22 ALL tanpa pemetaan | Sudah dipetakan Astra (`C6_75_ALL22_CROSSWALK`); penulis menautkan dan menjalankan ulang yang belum terpetakan bila ada |
| R-DOC05 | Fable A1 | 4 tabel `erp` di hosted tanpa RLS | Kode final 0 tabel tanpa RLS (Fable A3). Penulis menyebut keempat tabel dari riwayat migrasi tanpa query hosted |

## E. Tidak dikerjakan sebagai bug (dengan alasan)

| ID | Asal | Alasan |
|---|---|---|
| FABLE-007 | Fable (dugaan absensi dobel) | Dibantah Astra pada rute yang diuji (PAY02/PAY03). Penulis menambah satu kasus regresi saja, tanpa mengubah produk |
| FABLE-011 | Fable (lantai tanggal cutover) | Astra: bergantung kontrak; larangan global tanpa keputusan owner tidak dibuat |
| A2 | CP7 lama | Tetap OPEN, bukan penghalang (D13-10) |
| A6, F-OPS-05 | CP7 putaran 2 | Sudah ditutup; tidak dibuka ulang |

## F. Untuk pemegang backup (owner)

Fable melaporkan 40 dari 64 karakter passphrase CP2 tercetak di log sesinya. Kunci CP2 dianggap terpapar dan tidak
dipakai untuk backup baru. Backup CP7C memakai kunci baru (rancangan CP7C sudah memakai kunci tersendiri).

## G. Status pengerjaan (penulis; bukan penerimaan)

Status per 15 Okt 2026 dini hari (WIB). "PASS" berarti lulus di CI pada commit yang disebut. Kualifikasi semua
workflow pada satu commit dicatat di `README.md` dan `CI_RECEIPT.json`.

Run CP17 terakhir yang lengkap: `e0fb701d`, run 38630670309, **39/39 PASS** (native 31, race 1, HTTP 4, browser 3),
`cp6_restored` dan gerbang advisor PASS, uji langkah tunggu pemasang 6/6 PASS.

| ID | Status | Bukti/kode |
|---|---|---|
| R-FIN01, R-CASH, R-FIN02 | Penjaga terpasang. Kasus FIN01/CASH/FIN02, race dua pembayaran, HTTP, dan detektor data lama **PASS** (run 38630670309) | `cp7_dated_guard_bundle.py`, `dated-guards.sql`, `cp7_cp17_fix_cases.py` |
| R-STK01, R-HPP01, R-RWK01 | Kasus **PASS** (run 38630670309). RWK01: OPEN/PARTIAL tetap belum bisa dibayar sampai owner memutuskan | `cp7_rework_eligibility_bundle.py`, `cp7_hpp_policy_guard_bundle.py` |
| R-SG01 | Tingkat (a) dibangun: batal Bagi Potongan sebelum dijahit, 2 delta Native dideklarasikan. 2 kasus native + browser desktop **PASS**. Run pertama browser gagal karena nama kolom laporan (`group`) bentrok dengan nama milik runner; diganti `cutting_group` | `pickup.sql`, `cp7_pickup_reversal_bundle.py`, `PickupReversalPanel.tsx`, `SG01_PICKUP_REVERSAL.md` |
| R-SG02 | 4 kasus native + browser HP **PASS**. Browser HP pertama gagal: tabel roll membuat halaman 722 piksel di layar 412 piksel; tampilan dibetulkan. **Belum**: pembatalan bila jumlah salah (Native juga belum punya; pertanyaan owner) | `return.sql`, `CuttingFabricReturnPanel.tsx`, `connected-pickup.css`, `SG02_FABRIC_RETURN.md` |
| R-SG03 | Kasus cuci ulang produk sama tanpa tagihan vendor **PASS** | `cp7_cp17_fix_cases.py` (`rewash_free`) |
| Kasbon (D14-6) | 3 kasus native, HTTP, browser desktop **PASS**. Bug layar ditemukan dan dibetulkan: pesan "kasbon tercatat" hilang saat halaman payroll memuat ulang | `kasbon.sql`, `cp7_kasbon_bundle.py`, `PayrollKasbonPanel.tsx`, `KASBON_D14_6.md` |
| R-LUSIN (D14-5) | Dibangun di layar draf penjualan + uji unit/DOM. **Belum**: uji browser khusus (butuh fixture stok 3 ukuran satu SKU). Uji browser helper lusin P11 yang lama tetap jalan di `CP7 Pre-freeze UI Regression` | `src/sales/seriesDozens.ts`, `SalesDraftPanel.tsx` |
| FABLE-007 | Tanpa perubahan produk. Uji pertama (`6553d7c7`, run 38631233950) ditolak saat menyiapkan data oleh penjaga Native `erp.guard_payroll_period_overlap` (skema dasar; tidak ada di migrasi pohon ini, karena itu tidak ditemukan Fable): payroll aktif kedua yang bertumpuk tidak bisa dibuat. Uji diganti `CP17_RACE_OVERLAPPING_PAYROLL_ONE_WINS` (berurutan dan bersamaan) | `cp7_cp17_fix_cases.py` |
| R-ACC01 (FABLE-012) | Inventaris 160 fungsi `erp`; 82 penulis tanpa rujukan dari kode yang berjalan dengan hak pemanggil dibuktikan tidak terjangkau dari Data API (`CP17_HTTP_ERP_WRITERS_NOT_REACHABLE` **PASS**). Pencabutan EXECUTE belum: sekitar 700 pemanggilan langsung di 194 berkas alat uji lama (pertanyaan owner). Setelan hosted dibaca Fable (D14-7) | `cp7_access_inventory.py` |
| R-DOC01, R-DOC02, R-DOC03, R-DOC05 | Selesai di `495821c8`: pemeriksaan salinan paket PASS (30 berkas), komentar basi dibetulkan, bukti CP1/CP2 dibawa ke pohon, 4 tabel tanpa RLS dijelaskan | `cp7_release_copy_check.py`, `docs/evidence/cp1-cp2/`, `DOC_FINDINGS_FABLE_002_003_004_RLS.md` |
| R-DOC04 (FABLE-005) | Pemetaan 75 C6 + 22 ALL sudah dibuat Astra; ditautkan, tanpa kode baru | `audit/astra_cp17/followup-681dd7a9/C6_75_ALL22_CROSSWALK.md` (cabang Astra, `d4a83b42`) |
| A2 (urutan daftar fungsi di pembanding) | Akar masalah ditemukan: `jsonb_agg(... order by 1)` mengurutkan dengan angka tetap 1, jadi urutan ikut rencana query; menunggu izin owner (D13-11) | `cp6_auditor_runner.py:35` |
| T3 browser AU/BF | **PASS** di `6510aaca` (run 38628727700) sesudah perbaikan. Merah sejak 6 Okt (sama persis: 27 PASS, 4 INCOMPLETE; AU 10/10). Penyebab: tampilan cabang ini (CP7) dipasang di atas database yang hanya berisi paket CP6, jadi panel HPP memanggil fungsi CP7 yang tidak ada (404) dan layar simulasi penjualan sudah diganti layar P11 (sudah tercatat di `PREFREEZE_RUNTIME_MIGRATION_20261006.md`, PRE-01/PRE-05). Perbaikan: bagian browser memakai tampilan dan alat CP6 beku `e43e0ed4` yang dulu lulus 31/31 dan 10/10 (run 36828454996); berkas paket dan `package.json` identik byte. Tidak ada assertion yang diubah; oracle CP6 yang sama tetap jalan di tampilan cabang ini dengan stack CP7 penuh (`cp7-prefreeze-ui.yml`) | `cp6-t3-release-package.yml` |
| R-EV01 (SOL-002) | Diperbaiki di `237d6ce1`: folder keluaran tidak lagi dipindah saat impor; gerbang memeriksa himpunan ID, status, dan hasil akhir. BE T1 **PASS** di `237d6ce1` (run 38627665293) | `cp6_av_probe.py`, `cp6_be_probe.py` |
| R-EV02 (SOL-003, OPEN-AZ-FIRST) | Pesan PostgreSQL disimpan di berkas diagnosis terpisah (`237d6ce1`), sekarang juga daftar proses lain di database saat gagal (jenis dan status saja). Penyebab paling mungkin kegagalan pertama di AZ: proses perawatan otomatis PostgreSQL (autovacuum) masuk ke database yang sudah ditutup, dan baris pertama AZ menolak bila ada proses lain. Log Sol tidak menyebut baris mana yang menolak, jadi ini belum terbukti. Pemasang sekarang menunggu proses lain keluar sebelum tiap berkas dan mengulang **hanya** penolakan `PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE` (transaksi berkas itu sudah dibatalkan), seperti pemasang paket T3. Teks pengaman tidak diubah; penolakan lain tetap berhenti. Uji 6 kasus PASS lokal dan di CI (run 38630670309) | `cp6_readiness_owner_install.py`, `cp6_readiness_owner_drain_test.py` |
