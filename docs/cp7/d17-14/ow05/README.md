# Koreksi mandor sesudah jahit — OW-05

Belum selesai. Sepuluh uji Native awal lulus dan layar sudah tersambung; nota/payroll lengkap, dua penulis, Auth nyata, browser dan pemulihan masih dituntaskan.

Dasar: keputusan owner D17-14 butir4 dan arahan22 Oktober; urutan tetap OW-05→OW-06→OW-07/08.

Jalur yang sedang dikerjakan:

1. Tampilkan semua dokumen yang mengunci mandor dan langkah pembalikan: nota/payroll, pool HPP, barang jadi/QC, laundry, hasil jahit/upah, nota aksesori, bahan mandor dan rework.
2. Pengguna membalik melalui penulis Native yang sudah ada. Tidak ada pemindahan upah atau nota lama ke orang baru.
3. Sesudah seluruh pemakaian aktif ditutup, satu perintah mengganti seluruh pembagian PO dengan pembagian baru, tanggal/jumlah yang sama. Pembagian lama menjadi REVERSED; alokasi, upah, jurnal dan snapshot tarif lama tetap tersimpan.
4. Catat ulang jahitan melalui layar WIP & Jahit dengan pilihan tarif OLD/NEW yang sudah disetujui D16-2/3/4; sesudah diperiksa, susun ulang nota mandor yang benar.

Sumber baru terpisah di `scripts/cp7_contractor_correction/`, di atas pemilik pemasangan OW-04 yang tetap utuh. Satu perubahan Native yang dinyatakan: penulis pickup menerima kelompok dengan riwayat lama hanya di transaksi koreksi privat, setelah seluruh pengunci ditutup. Seluruh pemeriksaan sumber/jumlah/mandor Native lainnya tetap.

Katalog22 kelompok diperiksa penuh; pembatalan pemasangan sesudah dipakai harus melalui backup, tidak menghapus sejarah. Perintah wajib UUID, ulasan sumber terkini, hak setelah menunggu, kunci bersama, seluruh perubahan atomik, dan kesamaan uang/stok/HPP sebelum/sesudah pergantian pembagian.

[Pemeriksaan lokal](local-compile-controls.json) lulus parse/kompilasi8 fungsi privat,2 fasad publik dan satu perubahan Native; tujuh kontrol pasangan WIP lulus. Ini pemeriksaan PGlite dengan tipe kolom Native, bukan pemasangan atau eksekusi penulis keuangan Native.

Sepuluh kasus Native awal mencakup upah aktif ditolak dengan petunjuk, pembalikan→pengganti→catat ulang pada tarif16,00/24,00, replay, UUID berubah, ulasan basi, mandor tidak aktif, kegagalan posting terakhir, kapabilitas privat dan sejarah immutable. [Native10 sudah lulus](native10-60cbf04d-pass.json), produk60cbf04d, run39765975641/job119781398868. Upah mandor lama0,00; catat ulang empat pcs pada tarif PO menghasilkan16,00 atau tarif mandor baru24,00, dengan WIP/jurnal tepat; CP6 dan advisor pulih sama. Ini belum menyatakan OW-05 selesai.

Masih harus dituntaskan: uji nota/payroll dibayar dan belum dibayar, pool/nota aksesori, riwayat laundry/FG, beberapa potongan satu PO, pergantian berulang, hak dan dua penulis, Auth/layar komputer/HP, pemasangan/pemulihan bawaan serta integrasi pemasangan akhir.

Tidak mengubah main, kandidat audit55c885d1, Enteng, database hosted/produksi atau WA nyata; CP7C formal belum dimulai.

Layar baru tersedia dari WIP & Jahit (termasuk baris riwayat selesai): satu panel per PO, pengunci berurutan, mandor pengganti, alasan, konfirmasi dan petunjuk catat ulang. Pemulihan respons hilang memakai UUID yang sama. [Uji klien75](client75-recovered-pass.json) mencakup6 kasus baru dan69 uji terkait yang lama; ini DOM tiruan, bukan Auth/browser nyata.

Berikutnya14 kasus: sepuluh awal diulang bersama4 kasus baru untuk nota/payroll belum dibayar, dibayar→balik uang→bayar mandor yang benar, serta dua koreksi mandor pada waktu jahit asli dengan pilihan tarif OLD/NEW. Nilai yang dituntut16,00/24,00/32,00 tetap; belum ada klaim empat kasus baru lulus. Produk SQL tidak diubah untuk menjalankan pembanding ini.

Uji14 pertama pada49370790 (run39769236803/job119792291443) menghasilkan12 PASS/2 INCOMPLETE; [kegagalan pertama](native14-49370790-first-failure.json) tetap disimpan. Satu cacat produk: koreksi kedua dengan tarif NEW pada waktu jahit asli bertabrakan dengan kunci revisi milik pergantian mandor sebelumnya. Satu cacat pembanding: penulis pembayaran payroll Native menyelesaikan saldo per mandor, dengan `contractor_id` tanpa `po_id`; uji terakhir keliru menuntut saldo per PO nol. Uji dibetulkan ke saldo seluruh mandor, tetap menuntut kas0,00 dan utang mandor0,00, tanpa mengubah nominal16,00.

Perbaikan produk memberi setiap pergantian mandor urutan privat di bawah kunci bersama. Revisi tarif kini unik menurut snapshot asli, waktu jahit asli dan identitas pergantian mandor; untuk PO lama tanpa pergantian, identitas tetap NULL dan `NULLS NOT DISTINCT` menjaga penolakan duplikasi seperti sebelumnya. Helper revisi diturunkan tepat dari sumber yang diterima: hanya pemilihan/penyimpanan identitas pergantian yang ditambah; pemeriksaan tarif, versi, tanggal dan snapshot lama tetap. Tidak menulis ulang tarif yang sudah dipakai atau mengubah tanggal fisik.

[Pemeriksaan lokal perubahan](generation-local-controls.json) lulus kompilasi empat fungsi dan helper turunan, pemisahan dua pergantian, replay snapshot yang sama, penolakan perubahan tarif dalam pergantian yang sama, serta pemulihan enam kelompok katalog yang terdampak. Ini belum bukti penulis keuangan Native. Uji berikutnya25 kasus:14 alur OW-05 dan11 oracle tarif R3 yang file/hasil wajibnya tidak diubah. Pemeriksaan seluruh22 kelompok dan pencopotan sebelum dipakai tetap wajib; hasilnya belum diklaim lulus.

Acuan sintaks PostgreSQL17: [UNIQUE / NULLS NOT DISTINCT](https://www.postgresql.org/docs/17/ddl-constraints.html), [ALTER TABLE](https://www.postgresql.org/docs/17/sql-altertable.html).

Percobaan25 pada86bfc11 berhenti sebelum kasus (0 tercapai): alat mencoba menyelesaikan nama fungsi privat lewat peran pemasangan yang memang tidak diberi USAGE skema itu. [Kegagalan pertama](native25-86bfc11f-install-first-failure.json) disimpan. Perbaikan mengambil definisi persis dari tangkapan22 kelompok yang sudah diverifikasi, tanpa memberi hak skema baru; seluruh25 oracle tetap sama. Belum diklaim lulus.
