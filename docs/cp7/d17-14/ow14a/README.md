# OW14a — kain berumus di Ringkasan Gudang

23 Oktober2026 WIB. Implementasi layar tersedia; belum dinyatakan selesai sebelum hasil browser nyata.

Ringkasan Gudang menyediakan bagian singkat yang dapat dibuka. Bagian ini memakai `MaterialReorderPanel` dalam mode
baca saja dan pembaca lama `erp_cp7_get_material_reorder_v1`: satu tabel evaluasi dengan panel kain dan sumber
Pengingat/WA, tanpa perhitungan angka kedua. Daftar mencakup seluruh gudang; pencarian lokasi pada ringkasan stok
tidak menyaring daftar kain. Pencarian, saringan dan perpindahan halaman tetap memakai pembaca server yang sama.

Stok fisik saat perhitungan, pesanan belum diterima dan titik pesan ulang terlihat terpisah. Titik pesan ulang adalah
ambang pengingat, bukan stok atau jumlah pembelian. Waktu hitung terlihat; angka cache tidak disebut stok langsung
pada waktu baca. Setiap kain menyebut aturan yang aktif. Mode ringkasan tidak menawarkan refresh perhitungan atau
penulisan konfigurasi; membuka bagian ini hanya membaca, dan saat tertutup tidak meminta daftar kain.

Ini belum menutup OW14b: minimum Kain & Benchmark yang masih aktif belum diubah menjadi referensi konfigurasi lama
dengan pilihan aturan baru. Tidak ada perubahan aturan lama, data Enteng, angka owner atau mekanisme pengiriman WA.

Validasi lokal:20/20 uji DOM pada panel kain dan Ringkasan Gudang, TypeScript dan CSS ownership lulus. Dua kontrol baru
memeriksa pembacaan saat dibuka, pemisahan angka, tidak ada tombol penulis, dan penghapusan angka saat hak hilang.
Skenario browser material yang sudah ada diperluas ke Ringkasan Gudang pada desktop/HP: angka sama dengan oracle
transaksi Native, tidak ada tombol konfigurasi, dan lebar halaman tidak melampaui viewport. Semua99 kontrol WA
tetap pada deklarasi lama, dijalankan workflow `cp7-ow14-warehouse.yml` di database sekali pakai dengan provider palsu.
Hasil server belum tersedia saat catatan implementasi ini ditulis; jangan menganggap lokal sebagai bukti browser.
