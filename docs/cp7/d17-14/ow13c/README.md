# OW13c — saran potong, checkpoint lokal

**Kode server dan layar terhubung di Disposable; belum kualifikasi Native dan
belum OW13c selesai.**11 SQL lokal,91 klien/DOM pada8 berkas, TypeScript serta
API installer/invers22 lokal lulus. Batas penting: SQL lokal memakai badan baru
yang sebenarnya, tetapi source/preflight/writer rencana lama adalah boundary
terkontrol; bukan bukti perilaku Native. Tidak ada pemasangan bawaan/Enteng.

Form Buat Potongan membuka `NativeAnalysisPanel` yang sama, dengan periode
penjualan eksplisit, lalu target SKU/ukuran dipilih dari hasil bertahap. Waktu,
alasan, alokasi, bahan dan jumlah memakai panel rencana yang sama. Tidak ada
mesin ramalan kedua, pengisian jumlah ke seluruh varian atau periode kebijakan
baru buatan penulis. Jumlah rencana dapat diedit sebelum disimpan.

Rencana arsip lama sengaja mengizinkan SAVE dari snapshot bertanggal (8 Okt),
kemudian memeriksa pada preview/apply. Kontrak itu tetap. Jalur form baru memakai
`cutting_save_contract=cp7.cutting-checked-save.v1` dan satu facade tambahan:
`erp_cp7_save_cutting_suggestion_v1(jsonb,uuid)`. Server mendelegasikan ke mesin
plan v2 yang sama dengan source/kelayakan/akses baru sebelum dan sesudah writer.
Sumber berubah atau WIP/kelayakan belum terbukti menolak, bukan dianggap0/100%.
Seluruh penolakan sesudah writer membatalkan draf/versi/receipt bersama.

Urutan lock: request plan yang sama, roll terurut, kapasitas bersama, target,
versi plan. Hak diperiksa kembali setelah menunggu dan sebelum hasil disimpan.
Receipt privat immutable termasuk TRUNCATE menjadi penanda setelah pakai;
UUID sama mengembalikan hasil dan waktu pemeriksaan yang sama, tidak dilabel
sebagai pemeriksaan baru. UUID sama berisi lain serta request lama yang bukan
jalur checked ditolak. Revoke juga menolak replay hasil lama.

Mode jalur disimpan di payload recovery `PLAN_APPLY_STAGED` yang sudah ada,
bukan domain baru yang tidak dikenal pemeriksa global. Jika jawaban hilang dan
halaman rencana biasa dibuka, marker tetap mengarahkan UUID/payload yang sama
ke facade checked. Klien wajib menerima bukti checked-save yang cocok; nominal
success tanpa bukti tidak menghapus recovery. APPLY tetap jalur Native plan
yang ada dan hanya membuat draf Potongan, bukan posting fisik.

## Komposisi A

Modul `scripts/cp7_cutting_checked_save`: schema privat,1 tabel receipt,
2 fungsi privat dan1 facade publik.0 penggantian badan fungsi lama,0 DML ERP,
0 rumus uang/stok/HPP.5 badan dependensi dipin tepat; owner/ACL/GUC tetap.
`install_delta`, `verify`, `admit_catalog`, `rollback_preuse` tidak membuka
koneksi/commit. A wajib menyediakan transaksi/envelope/global use guard,
memasukkan receipt immutable dalam census setelah pakai, serta komposisi sesuai
kontrak. Sebelum dipakai, invers22 lokal tepat; setelah receipt ada, invers
menolak sebelum DDL. DROP menggunakan RESTRICT, bukan menghapus dependen lain.

A menambah pasangan source/RPC `src/nativeCuttingSuggestion.ts` →
`erp_cp7_save_cutting_suggestion_v1` pada registry dan generator tipe. B memakai
tipe facade sempit sementara di berkasnya sendiri; tidak mengubah tipe/bundle/
registry bersama. Gerbang sumber bersama belum dinyatakan lulus. Sembilan SQL
dasar dan pemeriksa owning sumber tetap tepat; A saja penggabung.

## Bukti yang masih wajib

- Native: data/plan/target/quantity dari perjalanan sebenarnya; angka sama
  dengan panel, stale/produk nonaktif/policy/WIP unknown/bahan/kapasitas berubah
  menolak dengan0 efek; rencana arsip lama tetap kontraknya.
- Dua backend: UUID sama, dua revisi bersaing, stok/bahan/kapasitas berubah dan
  revoke setelah lock wait; tidak ada draf/receipt yatim.
- Auth/PostgREST asli, desktop1440/HP390, waktu WIB, period/target eksplisit,
  jumlah yang diedit, hilang jawaban dan buka ulang di halaman rencana biasa.
- Komposisi dependensi terhadap rantai A, installer/invers22 Native dan penolakan
  setelah pakai, backup/restore caller yang sudah dipakai, source gate bersama.
- Waktu satu SAVE aktual di bawah batas8detik, termasuk dua pemeriksaan sumber
  penuh. Belum ada angka Native untuk jalur ini; jangan menaikkan batas agar
  lulus. Pabrik3600 tetap OW12b, terpisah dari Native19 sintetis.

Native19 yang telah lulus tetap kandidat d5997235 tersendiri, bukan bukti untuk
kode OW13c baru ini. Seluruh backlog tetap lingkup; parent5/16, tidak ada
CP7C/production_go/audit independen dari checkpoint ini.
