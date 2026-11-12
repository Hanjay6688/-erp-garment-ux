# Konsistensi pembacaan transfer supplier OW06

Perbaikan jumlah dan isi halaman saja masih bisa menghasilkan token review sebelum pembalikan dengan detail transfer sesudah pembalikan. Dua sesi PostgreSQL 17.6 mereproduksinya dari definisi asli E4EA. Perbaikan membuat satu pembacaan data STABLE untuk token, pilihan transfer dan halaman. Batas workspace tetap VOLATILE dengan pemeriksaan izin sebelum dan sesudah pembacaan.

Dalam fixture, respons yang sedang berjalan tetap menunjukkan status dan token awal. Permintaan berikutnya melihat hasil commit. Halaman kedua mempertahankan total 25 dan isi kosong saat transfer ke-26 masuk, lalu menampilkan T-26 pada permintaan berikutnya. Pembatalan transaksi mempertahankan hasil awal. Perubahan izin di tengah pembacaan ditolak dengan SQLSTATE 42501.

SQL preview 12.144 byte dipasang utuh. Seluruh 19 kolom katalog dan ACL fungsi awal cocok. Hanya definisi dan volatilitas yang dinyatakan berubah. Helper baru menggunakan hak pemanggil, bersifat STABLE, dan hanya pemilik dapat mengeksekusi. Rollback memulihkan 22 kelompok katalog dan data fixture. Uji ini memakai AP dan izin fixture. Penerapan pada paket penutupan masih memerlukan basis setelah Global dan pembuktian Auth aktual. SQL dan hasil uji tersimpan pada cabang review OW06.
