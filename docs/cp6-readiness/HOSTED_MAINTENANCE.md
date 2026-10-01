# Pemasangan pertama CP6 di hosted: paket untuk persetujuan

Target historis paket: **ERP Enteng (`siimvrusnzxexizpyoib`)**, baseline G-01. Pemeriksaan ledger baca saja 1 Oktober menunjukkan hosted masih `v2.6.20`: A–AB belum dipasang. ERP-Garment (`vlxdhpkjeevubjxexnfo`) adalah proyek berbeda; tidak dianggap otomatis cocok atau target pemasangan. Jalur lengkap membutuhkan **28 predecessor A–AB** pada `PREDECESSOR_MANIFEST.json`, lalu **30 SQL AC–BF** pada `supabase/release/cp6-t3/MANIFEST.json`. Semua memakai byte asli yang dipin; cabang CP7 tidak dipasang.

## Sebelum menjadwalkan

1. Periksa receipt Native/Shell terbaru, identitas source, 30 hash paket, hasil advisor dan pemulihan. Tidak ada langkah dengan FAIL/INCOMPLETE yang diterima.
2. Owner/keuangan meninjau delapan isian nyata pada README. Catat akun/kategori yang dipilih, unsur vendor yang dipakai, serta yang sengaja tidak digunakan. Empat keputusan tertulis boleh disiapkan sebagai formulir; pemasangan schema tidak berarti pengaturannya sudah SET.
3. Tentukan tanggal, durasi, pelaksana dan batas berhenti. Persetujuan harus menyebut **ERP Enteng** serta penghentian transaksi sementara. Persetujuan perbaikan kode tidak dipakai sebagai persetujuan maintenance.
4. Jalankan preflight melalui koneksi yang benar. Mode penuh mensyaratkan baseline `v2.6.20`, katalog/config G-01 yang sesuai dan belum ada berkas A–BF yang diterapkan. Mode AC–BF saja mensyaratkan AB sudah ada dan AC–BF belum dipasang. Periksa ledger, kapsul historis serta ACL. Bila beda, berhenti; jangan melemahkan guard atau menyesuaikan pin berdasarkan tebakan. Perbedaan platform ledger pada bootstrap CI tercatat historis; guard tiap SQL tetap otoritas pada pemasangan aktual.
5. Pastikan tersedia akses pemulihan di luar database sasaran. Ketersediaan backup hosted atau PITR bukan dianggap bukti backup telah dipulihkan.

## Jalur pemilik database dan pemeriksaan kemampuan

Pemeriksaan hosted baca saja menemukan akun yang dipakai bukan superuser, memiliki database sasaran, mempunyai hak koneksi ke `template1`, membaca semua sesi, dan membaca identitas cluster. Koneksi direct aktual masih harus diperiksa driver. Role superuser maintenance milik CI tidak tersedia di hosted. Applier lama menolak selain database CI; tidak boleh disebut pemasang hosted yang siap pakai.

Jalur baru adalah `scripts/cp6_readiness_owner_install.py`. Ia memakai koneksi kerja `postgres` ke database `postgres` dan koneksi pemilik `postgres` ke `template1`, pada **endpoint direct ERP Enteng yang sama**, port 5432. Tidak ada role baru yang dibuat di hosted. Sertifikat server wajib diverifikasi dengan `verify-full`; pooler ditolak. Simpan koneksi dan sertifikat melalui environment operator, tanpa menaruh password dalam dokumen atau log:

```sh
python scripts/cp6_readiness_owner_install.py --report /path/to/CP6_OWNER_PLAN.json
```

Mode bawaan hanya membaca metadata dan memakai `FULL_FROM_V2620`: 28 predecessor ditambah 30 berkas paket, **58 berkas**. Periksa status `READ_ONLY_PLAN_COMPLETE`, baseline yang sesuai, identitas cluster yang sama, kepemilikan sasaran, kemampuan melihat sesi, dan seluruh hash. Ia tidak menutup admission atau memasang SQL. `--install-mode AC_BF_FROM_AB` hanya untuk sasaran yang benar-benar telah sampai AB; mode itu wajib menolak hosted v2.6.20 sebelum admission berubah. Dependency Python mengikuti CI (`psycopg[binary]==3.2.10`).

Uji CI jalur baru wajib membuktikan pemilik/controller dan akun kerja `postgres` **keduanya tanpa superuser**, mulai dari salinan G-01 v2.6.20 dan memasang 58 berkas dengan seluruh guard asli. Keduanya memakai role postgres seperti hosted; pemilik database tidak dipindah ke role controller berbeda saat pemasangan. Akun admin CI hanya dipakai menyiapkan kasus penolakan dan membersihkannya, tidak menjalankan driver pemasangan. Kemampuan kedua akun dicatat dalam receipt. Keberhasilan CI masih belum membuktikan baseline, koneksi direct dan privilege aktual hosted; pemasangan pertama tetap sebuah gate tersendiri. Receipt CI terbaru harus lulus sebelum operator memakai jalur ini.

Rujukan kemampuan: [ALTER DATABASE PostgreSQL 17](https://www.postgresql.org/docs/17/sql-alterdatabase.html), [role postgres Supabase](https://supabase.com/docs/guides/database/postgres/roles-superuser), [koneksi direct dan sertifikat](https://supabase.com/docs/guides/database/connecting-to-postgres).

## Dalam jendela yang disetujui

1. Aktifkan maintenance aplikasi dan hentikan writer, integrasi, scheduler serta koneksi layanan ke sasaran. Biarkan koneksi operator tersedia untuk backup dan pemeriksaan awal. Jangan menyamakan maintenance aplikasi dengan admission database yang tertutup.
2. Ambil backup konsisten **sebelum** pemasangan, record katalog/ACL/ledger, hash isi dan jumlah baris sumber. Pulihkan backup ke lingkungan terpisah; periksa hasil dan pembacaan mesin. Receipt backup harus menyebut `project_ref: siimvrusnzxexizpyoib`, `database: postgres`, `restore_verified: true`, `install_mode: FULL_FROM_V2620`, `manifest_sha256: 8368df52bdf6d026620dd8d301d8c48b16ccb25c04f5c230df83d97d9c8432e5`, dan `verified_at` dengan zona waktu. Driver menolak receipt lebih tua dari satu jam. Mode AC–BF memakai hash manifest 30 berkas dan mode yang sesuai; receipt antar-mode tidak dapat ditukar. Jangan membuat receipt sukses bila pemulihan belum dilakukan.
3. Isi `CP6_APPROVED_MAINTENANCE_WINDOW` dengan referensi persetujuan dan `CP6_VERIFIED_BACKUP_RECEIPT` dengan path receipt yang diperiksa. Jalankan driver dengan `--apply`. Ia mengambil lock maintenance tanpa menunggu lock yang sibuk, menutup admission satu kali untuk keseluruhan paket, dan menunggu sesi lain berhenti alami. Bila sesi masih ada setelah batas tunggu, ia menolak tanpa memasang berkas atau membunuh sesi, lalu mengembalikan admission. Setiap SQL dan ledger disimpan dalam satu transaksi per berkas. Seluruh guard asli tetap berlaku. Bila satu berkas sudah dicoba dan proses gagal, admission tetap tertutup untuk pemeriksaan; jangan lompat berkas atau menjalankan ulang secara buta.
4. Keberhasilan mode penuh adalah `ALL_FILES_INSTALLED`, **58** receipt berkas PASS, Native `BE_PLUS_BF_T1` terverifikasi, hash katalog tercatat, dan admission **tetap tertutup**. Mode AC–BF memerlukan 30. Driver membaca katalog lewat sesi kerja yang dipertahankan sebelum sesi itu ditutup; operator meninjau receipt. Setelah pemeriksaan disetujui pelaksana, buka admission dari koneksi pemilik di `template1` dengan `ALTER DATABASE postgres WITH ALLOW_CONNECTIONS true;`, sementara maintenance aplikasi dan penghentian writer umum tetap berlaku. Periksa kembali ledger dan Native melalui koneksi sasaran yang kini dapat dibuka. Ini memungkinkan login owner, bukan go produksi. Baca versi pengaturan dan simpan nilai yang disetujui lewat RPC Native, dengan expected version, alasan dan request ID. Simpan receipt pengaturan. Jangan menyalin akun/angka fixture CI atau mengisi tabel policy secara langsung.
5. Jalankan canary yang telah disepakati: tarif vendor, satu kiriman/penerimaan ukuran nyata, satu invoice, satu kredit retur bila fitur digunakan, serta pembacaan HPP/utang/jejak dokumen. Canary menyebut sumber dan tanggalnya; setiap kebalikan memakai alur dokumen Native, tanpa delete/update data manual. Bila memakai data nyata, gunakan transaksi dan dokumen bisnis yang memang disetujui owner.
6. Bandingkan advisor sebelum/sesudah. Kelas INFO `rls_enabled_no_policy` pada tabel privat ERP hanya boleh diterima sesuai keputusan historis dan ACL/fasadnya; temuan baru lain harus dijelaskan atau menjadi HOLD. Periksa akses lintas peran, ledger, uang, stok, HPP dan hash data historis.
7. Buka aplikasi dan writer umum hanya setelah semua gate disetujui pelaksana dan owner. Pantau transaksi pertama dan pesan pengaturan yang belum siap; simpan hasil sebagai **pemasangan hosted pertama**, tidak digabung dengan receipt CI. Driver tidak memberi go produksi otomatis.

## Bila harus berhenti atau pulih

- Paket rollback hanya untuk komponen yang belum dipakai, dengan guard identitas dan admission yang sama. Jika ada pemakaian, rollback harus menolak; jangan memaksa penghapusan.
- Bila database belum pernah dipakai sesudah backup, restore backup melalui jalur pemulihan yang telah diuji, lalu periksa katalog, isi, ledger dan pembacaan mesin.
- Bila sudah ada transaksi baru, tetap maintenance. Owner dan pelaksana menilai konsekuensi pemulihan terhadap transaksi tersebut; jangan diam-diam menghilangkan transaksi. Catat batas data yang dipulihkan dan rekonsiliasi yang diperlukan sebelum membuka kembali.

Status paket ini: **siap ditinjau, belum dijalankan di hosted**. Durasi/jadwal dan isian nyata belum diisi karena tidak terdapat keputusan terbaru yang menyebutnya.
