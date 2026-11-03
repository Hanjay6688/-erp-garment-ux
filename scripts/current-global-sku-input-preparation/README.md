# Persiapan pengamatan global untuk SKU moving average

Sumber terpisah di atas kandidat Mandor `c19211e`. Tidak ada installer,
workflow keuangan, perubahan izin produk, atau adopsi parent final di sini.
Gate unified pada parent sengaja tetap membatasi namespace lama. Persiapan ini
memiliki fence sendiri; integrasi final wajib mengikat ulang sumber dan bukti.

SKU `d31245e` mengubah dua fungsi HPP yang dirujuk pemeriksa global. `routes.py`
menurunkan kedua definisi dari enam definisi asli lengkap yang berasal dari
Original SKU27 diterima, lalu mengikat sumber SKU yang persis. Semua 19 atribut
masing-masing fungsi tetap dibandingkan. Ini ekspektasi sumber yang belum
lulus Native, bukan bukti parent aktual. Dua puluh dua nama grup katalog dan
metadata view juga harus tetap lengkap.

Lima perubahan sumber yang bisa dibalik menghasilkan empat helper: dua
literal authority, seed penjualan, 31 hubungan identitas ekonomi, dan 12
rowset lengkap. Empat file SQL asli tetap persis. `inspect.sql` dan seluruh
penolakannya tidak diubah. Hubungan mencakup pembalikan dan riwayat superseded;
lokasi, akun dan kategori tidak menjadi simpul penghubung. Pengamatan mencakup
seluruh kolom dan mempertahankan multiplicity, dengan urutan JSON yang stabil.

Pemeriksaan baru membuktikan bentuk 44 tabel/463 kolom, ketidakbertumpukan 13
adapter Mandor dengan fungsi global, penolakan owner/ACL/konfigurasi/authority
yang berubah, serta sintaks dan sifat read-only. Model PostgreSQL17 membuktikan
pemisahan relevant/outside, riwayat immutable, dan deteksi perubahan pada
masing-masing 12 rowset yang sebelumnya tidak diamati. Semuanya lolos pada
eksekusi model pertama. Kolom lama berasal dari Original aktual, kolom SKU
baru berasal dari DDL kandidat; constraints, owners, RLS, callbacks, Auth dan
transaksi bisnis **bukan** bagian yang diuji oleh model ini. Kasus Native = 0.

Jalankan `preflight.py` dengan `--original` menunjuk Original SKU27 yang hash-nya
dipin, `--parser-path` menunjuk pglast, serta tujuan `--report` dan `--model-input`.
Jalankan model dengan `CP7_PGLITE_MODULE`, `CP7_GRAPH_INPUT`, `CP7_GRAPH_REPORT`.
`check_source.py` hanya memeriksa sumber dan bukti, tanpa menjalankan ulang model.

Masih wajib sebelum pemasangan: Original Afui/SKU yang berhasil dan diterima;
parent gabungan aktual; review lengkap sumber, pemanggilan, trigger, FK, RLS,
izin dan writer; profil semua input aktual termasuk lingkup PO yang diperluas
oleh SKU; integrasi exact-route ke installer; transaksi Native D1/E dengan SKU
tersimpan, inverse, dirty/stale/permission/race; keseluruhan paket dan restorasi.
Daftar 12 tabel baru atau minimum 42 tabel lama bukan bukti cakupan lengkap.
Tidak ada production GO atau klaim pemeriksaan independen.
