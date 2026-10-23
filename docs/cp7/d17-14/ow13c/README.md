# OW13c — checkpoint Native31 lulus; fitur penuh masih terbuka

**Native31 PASS31/31 padaa15054c2**, run39996465132/job120561154474:
15 Native/8 race/4 Auth/4 browser.160 uji klien/12 berkas, TypeScript,
28 source hash,8 invers22,10 authority, restore/advisor/lima gate paket
tepat. Volume2000/202000 4728/1799/1743ms, batas8s/3s tetap.
[Receipt PASS](a15054c-native31-pass.json), [riwayat lengkap](NATIVE31_README.md).
Pesan source berubah dan pemulihan HP lulus; tiga contoh stok yang tadinya
08:00 masih masa depan pada uji tengah malam diperbaiki ke00:00 pada hari
yang sama, tanpa perubahan penjaga Native/jumlah/oracle. Parent tetap5/16;
ini bukti komponen, belum fullOW13c/komposisi A/audit/production_go.

**Riwayat implementasi awal:**
Run Native25 pertama bf98947e membuktikan6 kasus baru (4 Native/2 Auth) PASS,
tetapi satu volume ROP lama timeout8detik:24/25, paket INCOMPLETE. Bukti di
[receipt pertama](bf98947-first-native25-24.json).11 SQL lokal,91 klien/DOM pada8 berkas, TypeScript serta
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
registry bersama. [Patch satu pasangan](SHARED_REGISTRY.patch) disiapkan;
`git apply --check` lulus pada B. Tujuh pasangan lama memakai patch OW13a,
bukan ditumpuk dengan patch enam pasangan OW16. Pemeriksa sumber yang sama
pada salinan sementara dengan tepat8 entri tambahan lulus360 berkas/303 jalur;
[receipt](SHARED_REGISTRY_CHECK.json). Pemeriksa bersama di repo tetap gagal8
pasangan sampai A mengintegrasikannya; ini bukan gerbang rantai A yang lulus. Sembilan SQL
dasar dan pemeriksa owning sumber tetap tepat; A saja penggabung.

## Bukti yang ada dan yang masih wajib

Native31 membuktikan fresh SAVE/UUID replay/0 efek stok-uang-fisik, sumber
stok berubah ditolak, UUID lama tidak dilabel ulang, used-receipt menahan
invers sebelum DDL;4 race checked-save (UUID/revisi/stok/akses setelah wait),
Auth asli dan2 perjalanan checked desktop/HP.19 kontrol caller lama juga
lulus. Lihat receipt untuk31 ID tepat; bukti ini tidak mencakup seluruh
kualifikasi aplikasi dari awal sampai akhir.

Yang masih terbuka sesuai daftar awal:

- Penolakan kelayakan tambahan pada jalur checked: produk/policy berubah,
  WIP unknown, bahan/kapasitas tidak cukup; nilai tidak menjadi0/100% dan
  tidak ada efek draf/receipt yatim. Kontrak preview/apply lama tetap.
- Waktu SAVE aktual dengan2000 produk di bawah8detik termasuk kedua
  pemeriksaan sumber penuh; volume caller2000 yang sudah lulus bukan ini.
- Backup/restore caller/receipt yang sudah dipakai, dengan UUID/history,
  data/owner/ACL/katalog tetap; base package restore bukan after-use proof.
- Komposisi A/default installer, global use census, source registry/generated
  types dan rantai gabungan. Patch/receipt registry sudah tersedia di atas.
- Factory3600/angka keuangan resmi tetap OW12b, terpisah dari proof ini.

FullOW13c/CP7C/audit independen/production_go dan kenaikan parent5/16 tidak
diberikan oleh checkpoint31. Jangan mengulang19/25/31 lama demi angka hijau.
