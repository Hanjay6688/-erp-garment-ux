# D17-18 — komposisi persiapan pilihan dan keuangan

Status: PREPARED, belum ada hasil runtime. SOURCE baru boleh diikat ke
Original Progress Native5 yang benar-benar PASS dan persis sesuai sumber.

Enam kasus terfokus menjalankan pemasang A lengkap, lima endpoint baru B,
antrean K4 yang tetap memuat keuangan resmi, retensi, pemeriksaan 22 kelompok
katalog, penolakan inverse setelah dipakai, dan pemulihan seluruh basis CP6.
Tiga helper fixture B berasal byte-exact dari commit yang ada di
B_FIXTURE_SOURCE.json. Jalur Native6/factory asli B tidak diganti.

Kasus membuktikan sumber dingin menunggu persiapan; permintaan ulang memakai
identitas yang sama; pemeriksaan izin dan sumber saat SAVE; kegagalan simpan
atomik; payload kedaluwarsa dibersihkan tanpa menghapus identitas/receipt;
pembatalan dapat dipulihkan; error tak dikenal tetap gagal; runner lama
menyelesaikan persiapan dan angka resmi tanpa mengubah uang, stok, atau HPP.

Setiap statement kecil tetap dibatasi 8 detik. Waktu seluruh kasus dicatat,
tanpa syarat total 8 detik dan tanpa menjadikannya ukuran satu operasi pengguna.
Pembatalan 57014 disuntikkan untuk menguji pemulihan; itu bukan pengukuran
timeout nyata. Pemanggilan K4 dari SQL bukan bukti pemicu cron per menit.

Belum membuktikan Auth/HTTP, browser, dua sesi, data pabrik penuh, penerimaan
gabungan atau produksi. Kegagalan lama tetap INCOMPLETE. production_go=false.

Alur: bind_sources.py memeriksa proof aktual dan mengikat semua berkas;
admission.py mengulang penerimaan sumber lama dan memeriksa Original induk;
probe.py menjalankan kasus, inverse dan pemulihan penuh. Fetch Original dan
admission selalu berada pada langkah workflow yang berbeda.
