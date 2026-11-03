# Pengamatan Global untuk biaya SKU terkini

Persiapan ini mengikat sumber SKU `ae480ca43d750a6abe41681fc6f90e6ad81a9135`
dengan tree `84b82de57207948d3e747432d387ce038de55204`. Sumber tersebut telah
melewati pemeriksaan seluruh prasyarat Native19, tetapi 19 transaksi ERP-nya
belum dijalankan. Semua delapan gate Global dan 12 gate produk biaya tetap
kosong. Tidak ada workflow atau pemasangan yang diaktifkan.

Sembilan tabel biaya baru sebelumnya belum masuk pengamatan Global. Empat
perubahan sumber yang dapat dibalik menambahkan 24 hubungan identitas dan
sembilan pengamatan baris lengkap, serta memperbarui dua referensi fungsi HPP.
Seluruh 19 atribut dari 19 fungsi authority tetap dibandingkan. Nilai nol,
cap waktu, status pembalikan, superseded, dan baris ganda tetap diperhitungkan.
Akun dan lokasi tidak menjadi penghubung komponen yang terpisah. Pengamat
lama, seluruh fungsi transaksi Native, izin, dan pemulihan tetap persis.

Pemeriksaan sumber melewati 41 kontrol penolakan. Model PostgreSQL17 memakai
80 tabel dan 813 tipe kolom, dengan empat penyedia baca yang dinyatakan secara
eksplisit; 40 kontrol lolos pada eksekusi model pertama yang benar-benar dimulai.
Model tidak menguji constraints bisnis, RLS, Auth, callback Native, atau transaksi
ERP. Tiga helper berubah dan inspector lama tetap persis.

Review pemanggilan sumber memakai full25 aktual asli dan ekspektasi sumber SKU
secara terpisah. Seluruh 30 replacement-before SKU dibandingkan pada 19 atribut;
274 hasil pembacaan sumber dipakai kembali hanya saat definisi dan bahasa persis,
28 body lain diparse. Hasilnya menjangkau 302 fungsi, 232 calon tabel fisik, dan
21 kemungkinan target tulis tanpa target sumber yang belum dikenali. Review
callback Mandor dijalankan lagi dengan input ini: empat trigger, dua FK, enam
callback, dan 12 tabel tambahan. Tidak ada tabrakan dengan 13 adapter Mandor
atau lima adapter Afui. Batas bawah gabungan menjadi 244 tabel. Ini belum
merupakan profil katalog gabungan yang aktual atau lengkap.

Delapan penggantian sumber installer dapat dibalik ke byte aslinya. Rencana
tetap berisi 16 fungsi dan tiga tabel; hanya tiga hash body pengamat berubah.
Delapan pengujian pemasangan tertutup lolos, termasuk penolakan sebelum cursor
untuk daftar 209/221/232 tabel, penghilangan satu per satu semua 244 tabel,
perubahan byte rencana, dan promosi masing-masing delapan gate. Input tambahan
tetap boleh diwajibkan oleh review aktual berikutnya. Lulus batas bawah ini
tidak mengesahkan parent, izin, transaksi, atau runtime.

Kegagalan persiapan pertama dipertahankan terpisah: perkiraan jumlah kolom
keliru memasukkan 37 kolom indeks sebagai kolom tabel; angka yang benar adalah
813. Percobaan pemanggilan model yang mengikuti kegagalan itu berhenti karena
file input belum ada, sebelum engine dibuat. Sumber SQL tidak diubah untuk
meloloskannya. Bukti ini bukan kegagalan keuangan ERP dan bukan model PASS.

Urutan reproduksi: `preflight.py` dengan `--original`, `--parser-path`,
`--report`, dan `--model-input`; model dengan `CP7_PGLITE_MODULE`,
`CP7_GRAPH_INPUT`, `CP7_GRAPH_REPORT`; review callback dengan input persis
yang dipin; `test_install_routes.py`; lalu `check_source.py` untuk memeriksa
seluruh namespace tambahan dan 14.612 file parent yang tidak berubah.
Parser sumber lengkap dan hasil mentahnya disimpan bersama bukti pemeriksaan.

Masih wajib sebelum pemasangan: hasil Afui diterima; transaksi SKU Native19;
Mandor dan parent gabungan aktual; sensus sumber/input/izin/writer pada parent
itu; pemasangan dan inverse aktual; D1/E positif, dirty, stale, permission,
race, Auth, semua lima gate paket, dan pemulihan penuh. Tidak ada production GO
atau klaim audit independen dari persiapan ini.
