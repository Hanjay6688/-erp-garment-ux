# Pemasangan pertama CP6 di hosted: paket untuk persetujuan

Target historis paket: **ERP Enteng (`siimvrusnzxexizpyoib`)**, baseline G-01 yang sudah dicocokkan secara baca saja. ERP-Garment (`vlxdhpkjeevubjxexnfo`) adalah proyek berbeda; tidak dianggap otomatis cocok atau target pemasangan. Paket yang dipakai hanya `supabase/release/cp6-t3/MANIFEST.json`, 30 SQL AC–BF sesuai urutan manifest, dari source CP6 yang diterima. Cabang CP7 tidak dipasang.

## Sebelum menjadwalkan

1. Periksa receipt Native/Shell terbaru, identitas source, 30 hash paket, hasil advisor dan pemulihan. Tidak ada langkah dengan FAIL/INCOMPLETE yang diterima.
2. Owner/keuangan meninjau delapan isian nyata pada README. Catat akun/kategori yang dipilih, unsur vendor yang dipakai, serta yang sengaja tidak digunakan. Empat keputusan tertulis boleh disiapkan sebagai formulir; pemasangan schema tidak berarti pengaturannya sudah SET.
3. Tentukan tanggal, durasi, pelaksana dan batas berhenti. Persetujuan harus menyebut **ERP Enteng** serta penghentian transaksi sementara. Persetujuan perbaikan kode tidak dipakai sebagai persetujuan maintenance.
4. Jalankan `scripts/cp6_readiness_hosted_preflight.sql` melalui koneksi yang benar. Periksa versi Postgres, ledger dan katalog terhadap predecessor AB, kapsul historis dan ACL yang dipin paket. Bila beda, berhenti; jangan melemahkan guard atau menyesuaikan pin berdasarkan tebakan.
5. Pastikan tersedia akses pemulihan di luar database sasaran. Ketersediaan backup hosted atau PITR bukan dianggap bukti backup telah dipulihkan.

## Jalur pemilik database dan pemeriksaan kemampuan

Pemeriksaan hosted baca saja menemukan akun yang dipakai bukan superuser, memiliki database sasaran, dapat terhubung ke `template1`, membaca semua sesi, dan membaca identitas cluster. Role superuser maintenance milik CI tidak tersedia di hosted. Applier lama menolak selain database CI; tidak boleh disebut pemasang hosted yang siap pakai.

Jalur baru adalah `scripts/cp6_readiness_owner_install.py`. Ia memakai koneksi kerja `postgres` ke database `postgres` dan koneksi pemilik `postgres` ke `template1`, pada **endpoint direct ERP Enteng yang sama**, port 5432. Tidak ada role baru yang dibuat di hosted. Sertifikat server wajib diverifikasi dengan `verify-full`; pooler ditolak. Simpan koneksi dan sertifikat melalui environment operator, tanpa menaruh password dalam dokumen atau log:

```sh
python scripts/cp6_readiness_owner_install.py --report /path/to/CP6_OWNER_PLAN.json
```

Mode bawaan hanya membaca metadata. Periksa status `READ_ONLY_PLAN_COMPLETE`, identitas cluster yang sama, kepemilikan sasaran, kemampuan melihat sesi, dan 30 hash paket. Ia tidak menutup admission atau memasang SQL. Dependency Python mengikuti CI (`psycopg[binary]==3.2.10`).

Uji CI jalur baru wajib membuktikan pemilik/controller dan akun kerja `postgres` **keduanya tanpa superuser**, lalu memasang 30 berkas dengan seluruh guard asli. Akun admin CI hanya dipakai menyiapkan dan membersihkan fixture kepemilikan salinan sekali pakai, tidak menjalankan driver pemasangan. Kemampuan kedua akun dicatat dalam receipt. Keberhasilan CI masih belum membuktikan baseline, koneksi direct dan privilege aktual hosted; pemasangan pertama tetap sebuah gate tersendiri. Receipt CI terbaru harus lulus sebelum operator memakai jalur ini.

Rujukan kemampuan: [ALTER DATABASE PostgreSQL 17](https://www.postgresql.org/docs/17/sql-alterdatabase.html), [role postgres Supabase](https://supabase.com/docs/guides/database/postgres/roles-superuser), [koneksi direct dan sertifikat](https://supabase.com/docs/guides/database/connecting-to-postgres).

## Dalam jendela yang disetujui

1. Aktifkan maintenance aplikasi dan hentikan writer, integrasi, scheduler serta koneksi layanan ke sasaran. Biarkan koneksi operator tersedia untuk backup dan pemeriksaan awal. Jangan menyamakan maintenance aplikasi dengan admission database yang tertutup.
2. Ambil backup konsisten **sebelum** pemasangan, record katalog/ACL/ledger, hash isi dan jumlah baris sumber. Pulihkan backup ke lingkungan terpisah; periksa hasil dan pembacaan mesin. Receipt backup harus menyebut `project_ref: siimvrusnzxexizpyoib`, `database: postgres`, `restore_verified: true`, `manifest_sha256: 40795c3fce619c5795b427e9aa31836777b687f82eba4ab5654264d57564879f`, dan `verified_at` dengan zona waktu. Driver menolak receipt lebih tua dari satu jam. Jangan membuat receipt sukses bila pemulihan belum dilakukan.
3. Isi `CP6_APPROVED_MAINTENANCE_WINDOW` dengan referensi persetujuan dan `CP6_VERIFIED_BACKUP_RECEIPT` dengan path receipt yang diperiksa. Jalankan driver dengan `--apply`. Ia mengambil lock maintenance tanpa menunggu lock yang sibuk, menutup admission satu kali untuk keseluruhan paket, dan menunggu sesi lain berhenti alami. Bila sesi masih ada setelah batas tunggu, ia menolak tanpa memasang berkas atau membunuh sesi, lalu mengembalikan admission. Setiap SQL dan ledger disimpan dalam satu transaksi per berkas. Seluruh guard asli tetap berlaku. Bila satu berkas sudah dicoba dan proses gagal, admission tetap tertutup untuk pemeriksaan; jangan lompat berkas atau menjalankan ulang secara buta.
4. Keberhasilan pemasangan adalah `ALL_FILES_INSTALLED`, 30 receipt berkas PASS, dan admission **tetap tertutup**. Periksa receipt serta katalog/ledger melalui jalur maintenance. Setelah pemeriksaan disetujui pelaksana, buka admission dari koneksi pemilik di `template1` dengan `ALTER DATABASE postgres WITH ALLOW_CONNECTIONS true;`, sementara maintenance aplikasi dan penghentian writer umum tetap berlaku. Ini memungkinkan login owner, bukan go produksi. Baca versi pengaturan dan simpan nilai yang disetujui lewat RPC Native, dengan expected version, alasan dan request ID. Simpan receipt pengaturan. Jangan menyalin akun/angka fixture CI atau mengisi tabel policy secara langsung.
5. Jalankan canary yang telah disepakati: tarif vendor, satu kiriman/penerimaan ukuran nyata, satu invoice, satu kredit retur bila fitur digunakan, serta pembacaan HPP/utang/jejak dokumen. Canary menyebut sumber dan tanggalnya; setiap kebalikan memakai alur dokumen Native, tanpa delete/update data manual. Bila memakai data nyata, gunakan transaksi dan dokumen bisnis yang memang disetujui owner.
6. Bandingkan advisor sebelum/sesudah. Kelas INFO `rls_enabled_no_policy` pada tabel privat ERP hanya boleh diterima sesuai keputusan historis dan ACL/fasadnya; temuan baru lain harus dijelaskan atau menjadi HOLD. Periksa akses lintas peran, ledger, uang, stok, HPP dan hash data historis.
7. Buka aplikasi dan writer umum hanya setelah semua gate disetujui pelaksana dan owner. Pantau transaksi pertama dan pesan pengaturan yang belum siap; simpan hasil sebagai **pemasangan hosted pertama**, tidak digabung dengan receipt CI. Driver tidak memberi go produksi otomatis.

## Bila harus berhenti atau pulih

- Paket rollback hanya untuk komponen yang belum dipakai, dengan guard identitas dan admission yang sama. Jika ada pemakaian, rollback harus menolak; jangan memaksa penghapusan.
- Bila database belum pernah dipakai sesudah backup, restore backup melalui jalur pemulihan yang telah diuji, lalu periksa katalog, isi, ledger dan pembacaan mesin.
- Bila sudah ada transaksi baru, tetap maintenance. Owner dan pelaksana menilai konsekuensi pemulihan terhadap transaksi tersebut; jangan diam-diam menghilangkan transaksi. Catat batas data yang dipulihkan dan rekonsiliasi yang diperlukan sebelum membuka kembali.

Status paket ini: **siap ditinjau, belum dijalankan di hosted**. Durasi/jadwal dan isian nyata belum diisi karena tidak terdapat keputusan terbaru yang menyebutnya.
