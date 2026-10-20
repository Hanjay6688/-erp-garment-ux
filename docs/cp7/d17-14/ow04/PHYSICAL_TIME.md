# Waktu penerimaan barang retur — perbaikan kecil OW-04

Sumber kontrak: `docs/erp-reliability-invariants.md`, Physical time. Barang
yang kembali adalah penerimaan fisik; waktu harus dikonfirmasi operator,
bukan disimpulkan dari saat halaman dibuka. Ini belum penyelesaian kredit/refund.

Expected sebelum perbaikan: input retur baru kosong, penulis tidak dapat
dijalankan tanpa waktu, perubahan waktu membatalkan konfirmasi pemeriksaan,
dan waktu WIB yang diketik menjadi tepat satu instant UTC pada payload.
Timestamp dokumen lama/correction berasal dari sumbernya dan tidak diubah.

Uji baru pada produk878/bb76 gagal: input justru berisi waktu buka halaman
(`local-physical-time-first-failure.log`: 1 gagal, 9 kontrol lulus).
Perbaikan membuang default `new Date()` dari formulir retur baru. Semua
validasi, token sumber, jumlah, HPP dan jalur penulis tetap yang sama.

Dua browser Native P11 desktop/HP diperkuat tanpa mengubah expected bisnis:
input harus kosong; setelah baris lengkap dan review, simpan masih terkunci;
operator mengisi waktu fixture WIB secara eksplisit lalu konfirmasi lagi.
Retur tersimpan harus memiliki instant yang tepat, termasuk replay balasan
hilang. Uji yang sudah ada tidak cukup karena sebelumnya bergantung default.
Jumlah kasus suite P11 tetap64. Workflow diaktifkan pada cabang writer;
checkout auditor memakai commit workflow itu dan merupakan sumber build UI.
Pin paket candidate/penulis/AB/harness tetap. Pemeriksa internal menelusuri
sumber browser dan mengoreksi penjelasan awal yang keliru menyamakan pin
candidate dengan sumber UI; perubahan pin yang tidak diperlukan dibatalkan.

Hasil browser Native perbaikan ini belum tersedia saat expected ditulis.
Tidak ada perubahan rumus uang atau implementasi penyelesaian retur lunas.

Sesudah perbaikan: **32/32 DOM** pada formulir retur, koreksi retur dan
pembayaran lulus (`local-physical-time-fixed.log`); TypeScript, Node syntax,
source/access/CSS ownership dan diff check lulus. Pemeriksa internal Sol Max
menelusuri urutan fixture: waktu retur yang diketik tepat2menit sesudah
waktu penjualan UI, dan sebelum waktu database, termasuk saat melewati
tengah malam WIB dan browser Los Angeles. Ini source review, bukan Native.
