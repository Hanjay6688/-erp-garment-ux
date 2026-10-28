# Penerus pemeriksaan sumber alat OW10

Perbaikan B sudah diterima A dengan empat tes filesystem dan CodeQL aktual.
Satu berkas alat historis berubah, sedangkan manifest lama tetap menyatakan
berkas yang diuji dahulu. Pemeriksa baru menyatakan penggantian itu secara
eksplisit: 4.314 sumber tetap persis, satu alat memakai sumber penerus teruji,
dan dua helper baru cocok dengan sumber B serta kandidat pemeriksaan A.

Ini meneruskan pemeriksa sumber yang ada. Semua pemeriksaan lainnya tetap
persis, termasuk fixture, sumber B, konfigurasi aplikasi dan oracle. Tidak ada
penggantian manifest lama, pengembalian writer yang rentan, penghapusan query
CodeQL, atau klaim bahwa bukti historis menguji kode alat baru.

Hasilnya hanya pemeriksaan sumber. Tidak membuka prasyarat backend atau browser,
tidak menggantikan actual all7, dan tidak memberi independent_acceptance maupun
production_go. Kandidat backend dan sumber yang diuji tetap dinyatakan terpisah
secara tepat dalam paket integrasi. Tidak ada perubahan produk atau tes browser B.
