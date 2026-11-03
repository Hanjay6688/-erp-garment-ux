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

## Sumber PO yang ikut dijangkau SKU

Review tambahan memakai metadata full25 asli dari pemeriksaan pemasangan Global
`0f93f50`, bukan katalog SKU27 yang mendahului DE30. Sumber kandidat SKU dan
helper global diterapkan hanya sebagai ekspektasi yang belum diterima. Parser
asli menelusuri 277 fungsi, trigger, FK, RLS, default, check, view, domain,
operator, cast dan 13 kueri dinamis yang batas literalnya sudah dipin. Pada
perluasan PO terakhir, 275 hasil pembacaan sumber dipakai kembali karena definisi
dan bahasa masih persis; hanya dua helper baru diparse. Hasilnya memuat 197
kandidat relasi fisik dan 21 relasi yang mungkin ditulis. Jalur sumber tidak
menyisakan target tak dikenal; daftar ini belum menjadi profil input aktual.

`po_routes.py` menambahkan lima perubahan sumber yang bisa dibalik atas helper
SKU sebelumnya. Tiga hubungan identitas mengikat PO, keadaan lot, peristiwa HPP
dan jurnalnya meski dimensi jurnal kosong. Pengamatan memakai identitas PO
langsung, lalu menambahkan 31 rowset lengkap untuk sumber dan hasil PO. Cakupan
meliputi batch potong bersama, bahan dan pembalikannya, sumber kantong historis,
rekalkulasi biaya, jurnal beserta pembalikan, akun dan konteks tanggal invoice.
Bahan, lokasi dan akun tidak menghubungkan identitas PO yang terpisah. Seluruh
kolom, cap waktu, status historis dan multiplicity dipertahankan.

Pemeriksaan baru memakai 71 tabel/733 tipe kolom dari metadata asli dan DDL SKU.
41 kasus model lolos, termasuk tiga perubahan cap waktu yang tidak terlihat
oleh pengamat lama, PO tanpa lot tersisa, dan riwayat pembalikan. Kegagalan
pertama berupa teks fixture yang melewati batas varchar(10) disimpan; fixture
diperpendek dan validasi panjang ditambahkan. Tidak ada transaksi Native,
Auth, RLS atau race yang diklaim dari model ini. Pemeriksa lama, penolakannya,
Native sync dan seluruh sumber parent tetap persis. Sync PO memang dapat
memperbarui cap waktu meski uang tetap; bukti outside wajib menangkap dan
menolak perubahan itu, bukan menghapus cap waktunya.

Gunakan `prepare_po.py` dengan full25 asli yang dipin dan jalankan
`test_po_model.mjs` memakai input yang dihasilkannya. Hasil lengkap dan kegagalan
pertama tersimpan sebagai bukti terpisah; `INPUT_REVIEW_CONTROLS.json` memuat
pin dan ringkasan yang tidak membuka admission. Perbaikan planner SKU setelah
`fdabda` mengubah satu fungsi finalisasi di luar 277 fungsi yang dijangkau;
profil final tetap harus diambil ulang dari parent gabungan yang diterima.

## Penghubung pemasangan yang tetap tertutup

`install_routes.py` menurunkan satu modul installer terisolasi melalui tujuh
penggantian sumber yang dapat dibalik. Sumber installer asli tidak diubah dan
modul yang sudah diimpor tidak diganti. Penyedia SQL memakai empat helper SKU/PO,
pemeriksaan referensi tetap membandingkan seluruh 19 atribut dari 19 fungsi,
dan segel mengikat manifest asli serta manifest tambahan. Satu rencana baru
dipakai oleh pemeriksaan sumber, pemasangan dan segel; parser pembuat rencana
asli tetap persis. Hanya hash tiga body helper berubah. Semua 16 fungsi,
tiga tabel, constraints, trigger, ACL/owner dan delapan adapter Native tetap.

Tujuh pemeriksaan baru lolos, termasuk kegagalan sebelum akses cursor ketika
parent belum diterima, penolakan promosi gate secara diam-diam, penolakan
perubahan byte rencana walau JSON bermakna sama, dan tidak berubahnya seluruh
fungsi transaksi/metadata/rollback asli. Belum ada pemasangan atau pengujian
keuangan global. `load_prepared()` sengaja menolak bila konstanta admission
diubah; adopsi final memerlukan integrasi terpisah setelah bukti parent lengkap.
