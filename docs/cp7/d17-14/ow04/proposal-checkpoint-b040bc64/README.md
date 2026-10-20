# Retur lunas: checkpoint usulan yang belum dipasang

Paket ini menyimpan pekerjaan dan bantahan sebelum integrasi produk. Tidak ada
SQL, TypeScript, atau penulis transaksi dari arsip yang diimpor aplikasi. Kandidat
produk tetap b040bc6492d2184efad0b9a06c1dd4e2a10b9053; perubahan produknya identik
dengan b7fc541c. Retur lunas belum selesai, belum diuji sebagai alur ERP utuh, dan
tidak mendapat izin produksi dari paket ini.

Arsip memuat 144 jalur logis, termasuk tujuh salinan identik yang diwujudkan agar
rujukan hasil lama tetap bisa dibaca. Setiap berkas diperiksa SHA256 sebelum
dikemas dan dibaca kembali dari arsip. `ARCHIVE_PLAN.json` mencatat hash, ukuran,
jenis bukti, kegagalan awal, dan batas pemeriksaan. `CHECKPOINT_RECEIPT.json`
mengikat paket ke kandidat dan hash arsip. Jalankan dari direktori ini:

```sh
python verify_archive.py
```

Untuk melanjutkan di lokasi kerja kosong, ekstrak arsip setelah verifikasi.
Jangan menjalankan berkas SQL sebagai installer. Sebagian usulan sengaja menolak
sebelum DDL karena otoritas, koordinator transaksi, penerapan kredit/refund, dan
penutupan atomik belum lengkap. Skrip lama masih mencatat lokasi runtime kerja
asal; sesuaikan lokasi dependency secara eksplisit sebelum mereproduksi, tanpa
mengubah expected atau menganggap PGlite sebagai PostgreSQL Native.

Bagian yang sudah ada meliputi sumber keuangan dan lineage, hitungan signed
recognition dua tanggal, ordinal keluarga retur, pemecahan journal part yang
tetap eksak, pembaca saldo, usulan admission/request, fixture Native yang belum
dijalankan, serta kontrak UI. Hasil sintetik atau pembacaan sumber tidak membuktikan
izin runtime, race, posting, UI produk, atau pemulihan seluruh fitur.

Keterbatasan penting: receipt UI melaporkan 40 tes sintetik, tetapi log final yang
dipin hanya berisi header RUN. Paket mempertahankan fakta ini. Jangan mengubahnya
menjadi klaim bukti runtime lengkap. Pengulangan terarah berikutnya harus menyimpan
stdout, stderr, exit code, source hash dan seluruh ringkasan tes.

Counter terbuka: `PROVEN_ABSENT` untuk jurnal SALE/RETURN **sebelumnya** berbeda
dari proyeksi retur baru `NO_JOURNAL`. Saldo awal HPP0, penjualan gratis tanpa
jurnal, lalu recost10 dapat menghasilkan retur HPP-only DrFG10/CrCOGS10. Tanggal
kausal tidak boleh dibuat-buat; Native tetap memakai resolver tanggal yang sah.
Jika ada ancestor jurnal HPP-only, tanggalnya tetap floor yang nyata. Riwayat
yang tidak lengkap harus ditolak, bukan dianggap absen.

Native entry harus menyegel prior proof ketika retur sendiri masih DRAFT.
Completed-source reader baru berjalan setelah jurnal atau ketiadaan jurnal yang
terbukti. Scope milik operasi hanya boleh mengecualikan proyeksi dirinya sendiri,
bukan daftar UUID bebas dari caller. UI/admission pada snapshot ini masih memiliki
aturan universal floor yang diketahui terlalu ketat dan sedang diperbaiki di
salinan usulan berikutnya. Jangan memasangnya sebagian.

Ini review internal writer. Audit independen, penerimaan owner, dan pemasangan
produksi tetap mengikuti register keputusan dan paket kandidat yang terpisah.
