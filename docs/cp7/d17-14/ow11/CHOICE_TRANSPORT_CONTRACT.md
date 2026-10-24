# Konfirmasi — sesi bersamaan dan Auth

Tahap berikut Native6, dideklarasikan sebelum run.10 kasus:1 anchor katalog22
yang diulang tanpa kredit baru,6 race dua backend dan3 Auth/PostgREST. Tidak
menjalankan browser dan tidak memakai pilihan untuk forecast.

Enam race menggunakan koneksi PostgreSQL terpisah dengan barrier atau penantian
yang benar-benar terlihat lewat pg_blocking_pids. UUID sama menghasilkan satu
pilihan/satu receipt dengan jawaban identik; UUID berbeda pada revisi yang sama
mempunyai satu pemenang CAS. Hak pengguna dicabut saat menunggu masing-masing
lock envelope, request dan target. Kasus request mengulang receipt yang benar-benar
sudah commit sehingga pemeriksaan akses harus mendahului balasan cache.

Kasus perubahan sumber memegang envelope Native pada sesi penghalang, menjalankan
writer stok sungguhan di sesi yang sama, lalu commit. Writer pilihan yang menunggu
harus bangun dan menolak sumber basi. Sesi ketiga tidak dipakai untuk writer stok
karena akan menunggu envelope yang sengaja ditahan. Semua kasus memeriksa jumlah
kedua tabel dan stok/uang/HPP; hanya perubahan stok fixture yang eksplisit dibolehkan.

Tiga kasus HTTP memakai login Supabase Auth sungguhan dan PostgREST tanpa USAGE ERP
tambahan: baca/konfirmasi/CLEAR/replay; token lama sesudah deaktivasi; serta anon
dan aktor lain dengan epoch miliknya sendiri. Konfigurasi boleh dibaca pengguna
lain yang berhak; snapshot perhitungan tetap privat untuk aktor yang menangkapnya.

Stage pembaca dan pilihan dipasang hanya pada salinan uji. Race mendapat salinan
baru per kasus; HTTP berbagi satu salinan dengan target fixture unik dan menghitung
delta yang sebenarnya. Pemasang utama12 tahap tetap. Cleanup Auth, sesi, salinan,
restore CP6, advisor dan5 gate paket harus diperiksa dari Original lengkap.

Hasil ini tidak menggantikan Native6, uji layar, consumer/fingerprint, pemasangan
default/fullchain/after-use A, atau penilaian independen. production_go=false.
