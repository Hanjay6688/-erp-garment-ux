# OW10 — cache titik, stok selalu baru (23 Oktober2026 WIB)

Tahap privat `cp7_reorder_reader_stage` v1 mempunyai1 schema,2 fungsi dan2 tabel,
0 hook/endpoint/grant Native. Caller v1 kini tersedia terpisah di [REORDER_CALLER_CONTRACT](REORDER_CALLER_CONTRACT.md);
Native caller masih menunggu kualifikasi. A tidak perlu
memasang potongan ini terpisah. Ini infrastruktur untuk caller D17-8/OW10.

`snapshot(server_source)` menerima hanya snapshot dari sumber server privat
dalam pernyataan caller. Tidak ada facade Auth yang menerima DTO ini. Pembaca
memakai lock FG global/read committed; tidak membuat analisis/job/WA. Cache
menyimpan titik/produk/statistik riwayat beserta threshold_hash/waktu asal.
Snapshot sumber baru diperiksa setiap kali, hak tetap kewajiban facade.

Cache miss mengompilasi riwayat/target/titik Native yang sama. Cache hit menjaga
seluruh JSON titik dan waktu perhitungannya; current_stock dihitung lagi dari
snapshot sumber kini dan availability Native. Stok fisik, reservasi dan draft
harus cocok. Perubahan stok hari ini tidak perlu kompilasi ulang riwayat hari
lengkap. Backdate, profil, manual, lead, default, query atau kode mengubah key.
Snapshot membedakan waktu stok diperiksa dari waktu titik dihitung; key threshold
bukan fingerprint alokasi WIP dan tidak mengizinkan memakai WIP lama.

Tabel cache boleh dieviksikan. Tabel use_marks menyimpan penggunaan pertama dan
menolak update/delete; invers setelah pakai menolak sebelum DDL meskipun cache
kosong. Guard/rantai global A tetap wajib mempertimbangkan use_marks. Prainvers
sebelum pemakaian memulihkan22 kelompok persis; input module dibalik setelah
caller/cache dikeluarkan. Tidak menghapus marker/data agar invers diperbolehkan.

28 kelompok SQL lokal/dua API installer22 lulus, termasuk sumber/history/target
aktual dengan profil/identitas fixture,2000 produk/202000 pergerakan. Seluruh
2000 titik dan stok kini dipertahankan. Uji hangat benar membaca cache dan stok
hari ini berubah tanpa kompilasi history. PGlite: dingin11208ms/hangat5612ms;
**bukan Native/Auth/SLA3detik**. Dua instalasi apply/admit/inverse/reapply22 dan
guard setelah pakai sebelum DDL lulus. Tidak ada perubahan bundle/migrasi A.

Kegagalan pertama15/28 disimpan `local-reorder-cache-first-failure.json`:
kurung JSON extraction kurang pada source threshold_hash menyebabkan SQL
unknown-minus-unknown sebelum penggunaan cache. Produk diperbaiki dengan
kurung; angka expected/oracle/guard tidak dilonggarkan. Original/log lengkap
terpisah, hasil28/28 menggantikannya tanpa menghapus kegagalan pertama.

Caller compute/pengingat, binding WIP good/ETA serta facade/label v2 sudah
dibuat dan diuji lokal. Lanjutan: uji Native/dua pengguna/login/layar/pasang-pulih serta
ukuran performa. Komponen suplai Native133 sudah PASS; cache/input di dokumen
ini belum masuk kandidat Native tersebut. Parent5/16; bukan CP7C/production_go.
