# Jembatan privat keuangan resmi pada frozen units — persiapan A

Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.

Ini kandidat A-only di cabang terpisah dari dua kandidat yang sedang diuji.
Sumber B dan pemasang A lama tidak diedit. Belum ada fasad publik, perubahan
pemasang bawaan atau izin produksi. Native40 pendahulu harus lulus aktual
sebelum deklarasi pengujian kandidat ini diikat/dijalankan.

Dua fungsi privat baru berada di cp7_current_frozen_finance: source dan
request_finance. Mode STAGED wajib eksplisit. Flag mode ditambahkan pada dasar
sumber sebelum reference/seal pertama; capsule hanya disegel sekali. Seluruh
perhitungan serta capture/status/proses server tetap memakai sumber laporan
resmi cp7_finance_capture. Tidak ada rumus keuangan baru, perubahan uang,
stok/HPP, nomor urut atau tabel.

Dua penggantian fungsi privat B dideklarasikan pada berkas delta A: request
operasional menolak UUID yang sudah menjadi permintaan keuangan; producer_hash
juga mengikat definisi fungsi A baru. Tidak ada berkas asli B yang diganti.
Permintaan keuangan menolak replay operasional/v1 dan query/mode berbeda;
mengecek izin keuangan sebelum lock, sesudah lock, saat replay, sesudah capture,
dan sesudah finance.start. Penolakan membatalkan seluruh efek.

Delta membuktikan seluruh22kelompok katalog dengan hanya satu schema, dua
fungsi privat baru dan dua penggantian privat yang otoritasnya tetap. Composer
memeriksa pendahulu sebenarnya sebelum delta. Inverse memeriksa seluruh baris
serta sequence sebelum DDL pertama, kemudian memulihkan definisi pendahulu dan
keadaan sebelum pemasangan secara utuh; sesudah dipakai wajib backup penuh.

Pemeriksaan lokal10pernyataan SQL, tiga tubuh PL/pgSQL, kontrak urutan seal/izin,
serta10kontrol negatif lulus. Uji itu bukan pengujian perilaku database. Satu
kontrol awal salah menganggap tambahan whitespace JSON sebagai perubahan
semantik; kegagalannya disimpan, kontrol dibetulkan dengan finance_mode yang
salah, dan penjaga produk tidak diubah demi tes itu.

Masih terbuka: Native dengan capture/halaman/24metrik laporan resmi, penolakan
sumber berubah, izin yang dicabut setelah menunggu, replay lintas mode, race,
AuthHTTP/browser, pemulihan penuh, cron asli dan pabrik1200SKU×3ukuran.
Mode/private route ini belum diadopsi ke aplikasi. production_go=false.
