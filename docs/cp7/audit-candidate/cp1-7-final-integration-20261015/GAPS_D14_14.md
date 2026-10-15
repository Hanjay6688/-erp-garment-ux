# Tiga celah sebelum audit akhir (D14-14) — G1, G2, G3

Owner D14-14 (15 Okt 2026): "ya yg jelas lu beresin lah". D14-15: dikerjakan di cabang `claude/final-gaps-20261015`.
D14-16: auditor belum diberi apa-apa; sesudah tiga celah ini selesai, penulis menyiapkan **satu paket gabungan**
(uji ulang r1 + audit akhir) pada satu kandidat.

Dokumen ini penjelasan penulis, bukan bukti lulus. Bukti adalah run CI yang dicatat di bagian 4.

## 1. G1 — "Selesai dijahit" dan upah borongan dari layar WIP & Sewing

**Sebelumnya:** jumlah "siap kirim laundry" dihitung dari catatan jahit selesai (`erp.sewing_terminal_events`), tetapi
tidak ada layar yang bisa membuatnya; uji membuatnya lewat SQL. Upah borongan (`erp.post_work_completion`, jurnal
`WORK_COMPLETION`) juga tidak punya jalan dari aplikasi (CHAIN_MAP §3 butir 1 dan 2, B4).

**Sekarang:** kartu potongan di WIP & Sewing punya bagian "Selesai jahit" (seperti kartu demo "SELESAI DIJAHIT __ / N
pcs"). Owner/Admin dengan `production.wip.view` + `production.wip.post` mengisi jumlah, waktu (WIB) dan catatan, lalu
mencentang "sudah diperiksa". Satu perintah server (`scripts/cp7-src/cutting-correction/sewing.sql`) dalam satu
transaksi, hanya lewat penulis Native yang sudah ada:

1. `erp.ensure_po_work_component_snapshots_v2` mengunci tarif PO (BOM kerja + tarif mandor) pada waktu jahit;
2. satu `erp.work_completion_events` DRAFT dengan satu baris per komponen tarif dasar, di-POST oleh
   `erp.post_work_completion` (jurnal Dr WIP / Cr hutang mandor; baris ini yang dibaca Nota/payroll);
3. `erp.record_sewing_terminal_v1` (SELESAI_DIJAHIT) untuk catatan itu — inilah yang dihitung laundry sebagai siap kirim.

Batal: hanya selama potongannya masih di mandor, upahnya belum masuk payroll, dan tidak dipakai pool HPP absensi yang
aktif; lewat pembalik Native (`erp.reverse_sewing_terminal_v1`, lalu `erp.reverse_work_completion`).

Sebelum catatan pertama, layar menampilkan **perkiraan** upah per pcs dari tarif yang akan dikunci (tarif mandor untuk
model dan komponen itu, kalau tidak ada pakai tarif bawaan BOM kerja). Tarif yang benar-benar dikunci adalah yang berlaku
pada waktu jahit yang diisi; hasil simpan menyebut upah yang benar-benar dicatat.

**Batas yang diketahui (ditolak dengan alasan, bukan diam-diam):**
- `WAVE_SKU_RATES`: potongan yang memakai tarif per SKU/ukuran (wave BF) tidak bisa dicatat di layar ini, karena layar
  mencatat satu jumlah untuk seluruh potongan.
- `NO_WORK_RATE`: model PO tanpa BOM kerja aktif (atau komponen tanpa tarif sama sekali) — BOM kerja diisi di aplikasi
  saat dipakai.
- `CONTRACTOR_MISMATCH` / `CONTRACTOR_NOT_MANDOR` / `PO_STATE` / `NO_POSTED_PICKUP` / `NOTHING_TO_SEW`.
- `erp.post_work_completion` masih bisa dieksekusi peran `authenticated` lewat SQL (FABLE-012; pencabutan ditunda ke
  CP7C, D14-9). Lewat Data API tidak terjangkau: `CP17_HTTP_ERP_WRITERS_NOT_REACHABLE`.

## 2. G2 — Selesaikan PO dan kunci HPP final dari layar HPP & Rekalkulasi

**Sebelumnya:** `erp.finish_production_order` (yang membuat HPP final) tidak punya pembungkus `public`; dari aplikasi
hanya ada hitung ulang antrean (CHAIN_MAP §3 butir 2, B8).

**Sekarang:** halaman HPP & Rekalkulasi punya bagian "Selesaikan PO · HPP final" (sesuai baris checklist demo
"Produksi sudah selesai · PO berstatus FINISHED"). Owner/Admin dengan `finance.hpp.view` + `finance.hpp.manage` mencari
PO, lalu melihat fakta yang sama dengan yang diperiksa Native sebelum menyelesaikan PO: laundry kembali atau klaimnya
selesai, barang GOOD dari laundry sudah lewat QC, tidak ada BS terbuka, sudah ada barang jadi; ditambah saldo WIP PO
dan daftar kelengkapan HPP Native (`erp.get_hpp_completeness`). Perintah server
(`scripts/cp7-src/cutting-correction/finish.sql`) hanya memanggil `erp.finish_production_order` (bangun ulang HPP,
HPP konversi, HPP ke buku besar, sisa WIP ditutup ke biaya lain-lain pada tanggal hari ini WIB) dan menolak kecuali
PO berakhir FINISHED dengan saldo WIP nol.

**Batas yang diketahui:**
- Tidak ada pembalik Native untuk PO yang sudah selesai; layar menyebutnya sebelum disimpan.
- Tanggal selesai selalu hari ini (WIB), karena Native memakai waktu server.
- Sesudah selesai, HPP bisa masih "Final, tetapi belum lengkap" (misalnya tagihan laundry belum final atau antrean
  hitung ulang masih ada); alasannya ditampilkan dari daftar Native, dan hitung ulang tetap lewat panel yang sudah ada.

## 3. G3 — Menjalankan ulang 51 workflow `cp7-*` yang basi

Commit `2e16fcb4` menambah tombol jalankan manual ke 51 workflow yang sebelumnya hanya berjalan saat push ke
`cp7/integration` (hasil terakhir 8 Okt, sebelum penjaga D14-2/D14-3/FIN02). Semua dijalankan pada `2e16fcb4`:
48 hijau pada percobaan pertama, 3 merah. Ketiganya data uji lama yang bertabrakan dengan penjaga baru, bukan
kesalahan produk; penjaga dan pemeriksaan tidak dilonggarkan, log gagal disimpan di run aslinya:

| Workflow | Run gagal | Sebab | Perbaikan |
|---|---|---|---|
| CP7 Native Atomic Misc Correction | 38716103082 | 3 dari 20 kasus membayar biaya setahun lalu / jumlah sangat besar dari bank yang baru diberi modal di hari buka (`CP7_CASH_NEGATIVE`, D14-3) | bank diberi modal pemilik pada hari setahun lalu itu, dan modal cukup untuk jumlah presisi, lewat `cp7_cash_funding` |
| CP7 Native Transaction Source Navigation | 38716165562 | 11 kasus pembayaran supplier dari bank kosong (`CP7_CASH_NEGATIVE`) | bank uji diberi modal sebesar total pembayarannya pada hari penerimaan; `cash_before` dibaca sesudahnya |
| CP7 F03 Supplier Current Authority | 38716162817 | manifest pengganti masih 34 peran; tumpukan peran sekarang 37 (`cp7_guard`, `cp7_kasbon_*`) | daftar peran disamakan dengan `cp7_f03_full_manifest.json` beserta catatan tinjauan |

## 3a. Arsip CI yang kedaluwarsa (D14-17)

Arsip `10392910720` (run 34956212157, 15 Sep 2026) adalah sumber daftar tabel "sebelum U" yang dibaca langkah beku X
(`Apply v2.6.20x ...` di workflow beku `1bdca376`) saat rantai uji dibangun ulang. Workflow pembuatnya menyimpan
arsip 30 hari (`retention-days: 30`), jadi arsip itu terhapus otomatis 15 Okt 2026; lima run pada `191ee9ff` berhenti
di langkah pertama dengan HTTP 410 (38721795013, 38721797914, 38721801271, 38721804060, 38721806508). Arsip itu tidak
bisa dibuat ulang persis: pembuatnya butuh arsip `10320611163` yang juga sudah terhapus.

- 14 arsip lain yang dikunci workflow dan masih hidup disalin utuh ke artifact `11967162735` (run 38723163085,
  sampai 13 Jan 2027, daftar ukuran dan SHA-256 di dalamnya). Belum ada workflow yang dipindah ke salinan itu.
- Owner D14-17 ("ya"): bila arsip tidak ada, `scripts/cp6_pre_u_inventory.py` menjalankan fungsi beku yang sama yang
  dulu membuat file itu (`scripts/cp6_v2620u_install_diagnostic.snapshot` dari checkout `1bdca376`) tepat sebelum
  langkah beku U, dan menulis file dengan bentuk yang dibaca langkah X. Langkah X tidak diubah dan tetap memutuskan.
  Tambahan sebelum U: jumlah wajib 208 tabel (207 `erp`, 1 `supabase_migrations`), dan SHA-256 daftar nama dikunci
  sesudah pengambilan pertama. Bila arsip ada, jalur lama yang dikunci SHA-256 dipakai tanpa perubahan.
- 80 workflow tidak lagi berhenti bila unduhan arsip gagal (78 yang memakai `cp6_t3_aligned_chain.py`, ditambah
  `cp6-av-qualification` dan `cp6-be-t1-probe` yang sekarang menjalankan `cp6_ac_audit_bootstrap.py` dari checkout
  auditor; isinya sama dengan salinan `25fa4736`, ditambah jalur pengganti ini).
- **Batas:** tidak bisa lagi dibuktikan bahwa daftar "sebelum U" hari ini sama persis dengan daftar 15 Sep; yang
  terbukti hanya jumlah, fungsi pembuat, titik pengambilan, dan kesamaan antar-run sesudah dikunci. 37 workflow CP6
  lama yang memanggil bootstrap dari checkout kandidat beku tetap tidak bisa berjalan (di luar Q25). Pin SHA-256
  `scripts/cp6_ac_audit_bootstrap.py` di `scripts/cp6_ai_audit_router.py` (workflow CP6 AI lama) tidak lagi cocok.

## 4. Bukti CI

Diisi sesudah run selesai (lihat bagian berikut yang ditambahkan dengan tanggal).
