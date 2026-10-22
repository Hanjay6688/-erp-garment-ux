# Koreksi mandor sesudah jahit — OW-05

Belum selesai. Jalur pengganti per PO sudah ditulis; kualifikasi Native10, dua penulis, Auth nyata, layar dan pemulihan masih harus dibuktikan.

Dasar: keputusan owner D17-14 butir4 dan arahan22 Oktober; urutan tetap OW-05→OW-06→OW-07/08.

Jalur yang sedang dikerjakan:

1. Tampilkan semua dokumen yang mengunci mandor dan langkah pembalikan: nota/payroll, pool HPP, barang jadi/QC, laundry, hasil jahit/upah, nota aksesori, bahan mandor dan rework.
2. Pengguna membalik melalui penulis Native yang sudah ada. Tidak ada pemindahan upah atau nota lama ke orang baru.
3. Sesudah seluruh pemakaian aktif ditutup, satu perintah mengganti seluruh pembagian PO dengan pembagian baru, tanggal/jumlah yang sama. Pembagian lama menjadi REVERSED; alokasi, upah, jurnal dan snapshot tarif lama tetap tersimpan.
4. Catat ulang jahitan melalui layar WIP & Jahit dengan pilihan tarif OLD/NEW yang sudah disetujui D16-2/3/4; sesudah diperiksa, susun ulang nota mandor yang benar.

Sumber baru terpisah di `scripts/cp7_contractor_correction/`, di atas pemilik pemasangan OW-04 yang tetap utuh. Satu perubahan Native yang dinyatakan: penulis pickup menerima kelompok dengan riwayat lama hanya di transaksi koreksi privat, setelah seluruh pengunci ditutup. Seluruh pemeriksaan sumber/jumlah/mandor Native lainnya tetap.

Katalog22 kelompok diperiksa penuh; pembatalan pemasangan sesudah dipakai harus melalui backup, tidak menghapus sejarah. Perintah wajib UUID, ulasan sumber terkini, hak setelah menunggu, kunci bersama, seluruh perubahan atomik, dan kesamaan uang/stok/HPP sebelum/sesudah pergantian pembagian.

[Pemeriksaan lokal](local-compile-controls.json) lulus parse/kompilasi8 fungsi privat,2 fasad publik dan satu perubahan Native; tujuh kontrol pasangan WIP lulus. Ini pemeriksaan PGlite dengan tipe kolom Native, bukan pemasangan atau eksekusi penulis keuangan Native.

Sepuluh kasus Native awal mencakup upah aktif ditolak dengan petunjuk, pembalikan→pengganti→catat ulang pada tarif16,00/24,00, replay, UUID berubah, ulasan basi, mandor tidak aktif, kegagalan posting terakhir, kapabilitas privat dan sejarah immutable. Belum ada klaim kasus Native ini lulus.

Masih harus dituntaskan: uji nota/payroll dibayar dan belum dibayar, pool/nota aksesori, riwayat laundry/FG, beberapa potongan satu PO, pergantian berulang, hak dan dua penulis, Auth/layar komputer/HP, pemasangan/pemulihan bawaan serta integrasi pemasangan akhir.

Tidak mengubah main, kandidat audit55c885d1, Enteng, database hosted/produksi atau WA nyata; CP7C formal belum dimulai.
