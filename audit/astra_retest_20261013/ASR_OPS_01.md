# ASR-OPS-01 — identitas scratch backup dapat basi sebelum penghapusan

Status: **OPEN, terbukti pada `7a0b4a90`**. Keluarga akar masalah: perlindungan kepemilikan scratch, beririsan dengan F-OPS-01. Kasus lama yang menolak database asing sejak awal sudah lulus; ini satu variasi tambahan, bukan pengulangan temuan lama sebagai temuan baru.

Asal bukti: `INDEPENDENT_NATIVE_RERUN`, oracle `ASTRA_CONTRACT`, fixture `ASTRA_OWN_CANARY_DATABASES`. [Run pertama](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38354577233), job `115154354639`, kasus `ASD-B05-REPLACED_LEFTOVER`. Seluruh operasi berlangsung di PostgreSQL sekali pakai. Kode produk, jam produk, dan oracle tidak diubah.

**Keparahan: S0 bersyarat menurut §8 panduan (penghapusan permanen data tanpa penolakan).** Prasyaratnya sempit dan memerlukan aktor lain yang memiliki hak administrasi database: scratch bertanda milik alat sudah ada, kemudian diganti database berbeda dengan nama yang sama selama backup berjalan. Ini bukan akses pengguna ERP biasa, bukan bukti penyerang tanpa izin dapat menghapus database, dan bukan bukti nilai uang/stok/HPP sumber ERP berubah.

## Reproduksi

1. Buat dua database canary milik auditor dari `template0` di cluster sekali pakai: sumber dengan satu baris `SOURCE_ORIGINAL`, dan scratch lama bertanda `SCRATCH_MARK` dari alat.
2. Jalankan `cp7_nightly_backup.backup`. Alat membaca `scratch_before=OURS`, lalu menjalankan `pg_dump` asli dengan snapshot ekspor asli.
3. Di batas sesudah `pg_dump` selesai dan sebelum alat melanjutkan, fixture admin menghapus scratch lama dan membuat database lain dengan nama sama. Database baru tidak bertanda milik alat dan memuat `FOREIGN_REPLACEMENT`.
4. Catat sebelum alat dilanjutkan: `scratch_state=FOREIGN`, baris `FOREIGN_REPLACEMENT` benar-benar ada.
5. Lanjutkan metode `dump` dengan hasil asli. Tidak ada cabang, guard, return value, atau perbandingan produk yang diganti.

Harapan oracle: database pengganti tetap ada; operasi menolak pemakaian/penghapusan, tidak mengklaim verifikasi berhasil untuk operasi yang merusak database lain, dan tidak memangkas backup lama.

Hasil asli: `foreign_canary_after=null`, `scratch_after=ABSENT`, `restore_verified=true`, `error` tidak ada. Sumber tetap berisi satu baris `SOURCE_ORIGINAL`. Database pengganti benar-benar hilang. Receipt menunjukkan verifikasi isi dump berhasil; verifikasi itu tidak mendeteksi bahwa database lain telah dipakai sebagai korban pembuatan scratch.

## Akar yang ditunjuk bukti

`scripts/cp7_nightly_backup.py`, fungsi `backup`: nilai `state` dibaca sebelum dump dan dipakai sesudah dump untuk `tools.drop(scratch)` bila nilai awalnya `OURS`. Pemeriksaan awal tidak lagi menjelaskan identitas database pada waktu penghapusan. `finally` juga memakai boolean `ours` sebagai salah satu syarat penghapusan; jalur kedua ini ditemukan dari kode, **belum direproduksi terpisah** dan tidak dihitung menjadi temuan kedua.

Kontrol pembanding pada run sama:

- Database asing yang sudah ada sebelum backup: ditolak dan tetap utuh.
- Database asing yang muncul sesudah pemeriksaan awal `ABSENT`: `createdb` menolak dan database tetap utuh.
- Scratch lama bertanda, tanpa penggantian: backup berhasil dan scratch dibersihkan.
- Penulisan sumber setelah snapshot: backup memverifikasi satu baris snapshot; sumber berisi dua baris. Jalur verifikasi snapshot lulus.

## Handoff writer dan kriteria retest

Pertahankan empat kontrol pembanding yang sudah lulus. Perbaiki keputusan penghapusan agar tidak mengandalkan nama dan status kepemilikan lama saja. Identitas scratch per percobaan serta kebijakan menangani sisa percobaan lama perlu jelas; jangan menganggap cek marker sekali sebagai jaminan seluruh siklus. Penghapusan akhir juga harus terikat pada scratch yang dimiliki percobaan tersebut. Ini saran desain, bukan perubahan kode dari auditor.

Kriteria penutupan: kasus penggantian di atas mempertahankan canary asing dan menolak dengan receipt yang jujur, kontrol lama tetap lulus, sumber tetap utuh, serta tidak ada pemangkasan akibat operasi yang gagal. Jika batas operasional sengaja mengecualikan DDL admin bersamaan, batas tersebut harus dinyatakan dan diputuskan secara eksplisit; auditor tidak menganggap pengecualian itu sudah disetujui.

Jangan mengubah produk hanya untuk membuat label hasil tes menjadi hijau. Log gagal pertama dan Original JSON tetap disimpan. `production_go:false`.
