# Pengamatan Global untuk SKU otomatis

Tambahan ini mempertahankan seluruh kandidat Global15fbb65 dan mengikat
44 berkas uang yang sama serta20 tambahan otomatis dari9b1b0fc. Dua tabel
private—konteks transaksi dan bukti admission POST/REVERSE—sebelumnya belum
masuk snapshot pengamat uang. Delapan hubungan identitas bertipe dan dua
snapshot baris lengkap sekarang disiapkan. Akun, gudang, backend PID dan
nomor transaksi tidak dipakai sebagai penghubung komponen.

Seluruh kolom, waktu, fase, JSON dan baris ganda dipertahankan. Kedua perubahan
SQL dapat dibalik persis;19 referensi authority lama dan inspector tidak
berubah. Pemeriksaan sumber membandingkan19 atribut dari19 fungsi otomatis
baru/terganti, serta metadata lengkap dua tabel. Semua361 perubahan atribut
fungsi dan penghilangan setiap objek metadata menolak. Model PG17 memakai
82 tabel/835 tipe kolom dan33 kontrol pengamatan. Model ini tidak menjalankan
transaksi ERP, constraints bisnis, RLS atau Auth.

Installer memakai kode penuntasan lama yang persis dengan provider privat
untuk sumber, rencana dan pemeriksaan baru. Rencana tetap16 fungsi/tiga tabel
dan delapan adapter Native; hanya dua hash body pengamat berubah. Seluruh
gate tetap kosong. Batas relasi246 hanya batas bawah, bukan profil lengkap
atau izin mengadopsi parent. Katalog gabungan aktual, semua writer/callback,
izin, advisory dan seluruh pemulihan tetap wajib direview setelah parent
Afui–Mandor–SKU aktual diterima. Tidak ada workflow atau ERP yang diaktifkan.

Bukti historis40 model uang dan244 relasi tetap historis; tidak dihitung
sebagai pengujian baru. Profil otomatis juga merupakan ekspektasi sumber
yang belum diterima. Sensus penuh aktual tidak dapat digantikan oleh model.

Review sumber kini menelusuri 374 fungsi: 299 hasil parse dipakai kembali hanya
saat body dan bahasanya persis, 75 body lain diparse. Sembilan belas fungsi
SKU otomatis dimasukkan secara eksplisit. Satu trigger SQL dinamis mempunyai
21 binding argumen katalog yang persis, menghasilkan 18 SELECT parent yang
berbeda. Seluruh metadata trigger dan full19 fungsi asli dipertahankan;
identitas parent berasal dari argumen katalog, bukan masukan pengguna.

Calon tabel fisik bertambah menjadi 264. Review callback Afui/Mandor yang
sama kemudian menambahkan 12 tabel, empat trigger, empat FK parent, dan enam
callback tanpa target baru yang belum dikenali. Batas bawah installer kini
276 tabel. Daftar lama 246 ditolak; semua 32 tabel di luar batas lama 244 wajib
ada. Ini tetap batas bawah sumber, bukan katalog gabungan aktual yang lengkap.
Pemeriksaan seluruh writer dan otoritas pada parent yang diterima masih wajib.

Percobaan awal review dipertahankan: dua kesalahan driver lokal sebelum parse
(lacak asal fungsi baru dan bentuk CREATE/OWNER/ACL), lalu hasil pertama yang
secara jujur melaporkan trigger dinamis belum terikat. Binding trigger pertama
belum menyediakan satu field pelaporan milik parser lama dan ditolak sebelum
hasil ditulis; field itu kemudian dilengkapi. Tidak ada transaksi ERP yang
dijalankan dalam percobaan ini dan hasil awal tidak dilabeli PASS.
