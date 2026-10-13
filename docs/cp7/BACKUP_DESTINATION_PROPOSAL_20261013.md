# Usulan database tujuan, lokasi backup, dan cara pemulihan (untuk dipilih owner)

Dasar: keputusan owner D13-3 (13 Okt 2026): "tunda izin pemasangan jadwal dan backup malam sampai nama database
tujuan yang persis serta lokasi dump di luar mesin database ditetapkan. Penulis siapkan usulan lokasi dan cara
pemulihannya untuk saya pilih." Dokumen ini hanya usulan. Belum ada yang dipasang atau dibuat. Hosted tidak disentuh,
dan `production_go:false`.

## 1. Database tujuan

Di Supabase, setiap proyek punya satu database aplikasi dan namanya selalu `postgres`. Jadi yang perlu dipilih
adalah proyeknya. Nama databasenya pasti `postgres`.

| Pilihan | Proyek | Nama database yang dipakai alat | Catatan |
|---|---|---|---|
| **A (usulan)** | ERP Enteng `siimvrusnzxexizpyoib` | `postgres` | Semua uji pemasangan CP6/CP7 diselaraskan dengan riwayat database proyek ini. Sekarang statusnya UAT. Jadwal dan backup dipasang di sini hanya kalau proyek ini memang yang dipakai untuk live. |
| B | Proyek Supabase baru khusus produksi | `postgres` | ID proyek baru diketahui setelah dibuat. Proyek baru harus diselaraskan dan diuji ulang dulu sebelum jadwal/backup dipasang. |

Proyek ERP-Garment lama (`vlxdhpkjeevubjxexnfo`) tidak bisa dipilih karena hanya boleh dibaca.

Saat pemasangan, alat jadwal (`scripts/cp7_schedule.py`) memakai `--database postgres`. Alat menolak kalau nama itu
tidak sama dengan database tempat ia tersambung. Keempat jadwal tercatat sebagai `nama@postgres`. Backup malam memakai
`--source postgres`.

## 2. Lokasi file backup di luar mesin database

Backup dibuat setiap malam pukul 01:00 WIB oleh GitHub Actions, jadi bukan di mesin database. Masalahnya, file di mesin
GitHub hilang begitu job selesai. Karena itu file perlu disalin ke tempat penyimpanan tetap.

| Pilihan | Tempat | Kelebihan | Kekurangan |
|---|---|---|---|
| **L1 (usulan)** | Bucket privat Cloudflare R2 di akun Cloudflare Bos, misalnya `erp-garment-backup` | Akun Cloudflare sudah dipakai. Gratis sampai sekitar 10 GB, dan download tidak dikenai biaya. Kunci akses bisa dibatasi ke satu bucket. Penghapusan backup lama bisa diatur otomatis. | Bucket dan kuncinya harus dibuat dulu. Bos yang menyimpan kunci itu di pengaturan rahasia GitHub, bukan lewat chat. |
| L2 | Google Drive milik Bos (lewat rclone) | Mudah dibuka sendiri dari HP/laptop | Izin Google bisa kedaluwarsa sehingga backup malam gagal diam-diam. Kuota Drive ikut terpakai. |
| L3 | Artifact GitHub Actions | Tanpa akun tambahan | **Tidak diusulkan.** Semua orang yang punya akses repo, termasuk sesi auditor, bisa mengunduh data keuangan dan karyawan. File hilang paling lama dalam 90 hari, dan kuota penyimpanannya kecil. |

Backup bawaan Supabase (paket Pro) boleh tetap aktif sebagai lapisan tambahan. Fungsinya bukan pengganti. Pemulihan
bawaan itu menimpa proyek, masa simpannya pendek, dan tidak diperiksa oleh alat kita.

Tambahan untuk L1 dan L2: aturan "simpan 14 malam terakhir yang lolos pemeriksaan" harus berjalan di tempat
penyimpanan itu. Alasannya, folder kerja di mesin GitHub selalu kosong setiap malam. Langkah salin dan penghapusan
ditambahkan ke workflow saat pemasangan, sesuai tempat yang dipilih.

## 3. Cara memulihkan (restore)

Prinsipnya, pemulihan dilakukan ke database baru dan database lama tidak ditimpa.

1. Pilih malam yang tanda terimanya (`*.receipt.json`) bertuliskan `restore_verified: true`.
2. Unduh file backup beserta tanda terimanya. Pastikan sidik jari file (SHA-256) sama dengan yang tertulis di tanda
   terima. Kalau beda, file tidak dipakai.
3. Pulihkan ke proyek atau database baru (`pg_restore --no-owner`), bukan ke database yang sedang dipakai.
4. Cocokkan jumlah tabel dan jumlah baris dengan tanda terima. Pemeriksaan malam sudah membandingkan isi setiap tabel
   dengan sumbernya. Langkah ini mengulanginya sekali lagi sesudah pemulihan.
5. Setelah cocok, aplikasi diarahkan ke database hasil pemulihan. Database lama dibiarkan sebagai bukti sampai Bos
   memutuskan dihapus.
6. Usul latihan: sekali sebulan, satu backup dipulihkan ke database uji untuk membuktikan file benar-benar bisa
   dipakai.

## 4. Satu risiko yang perlu diketahui sebelum memilih

Setiap malam alat memeriksa backup dengan memulihkannya ke database sementara (`cp7_backup_verify`) di server yang
sama dengan sumbernya. Ini sudah diuji di salinan CI sebagai pengguna admin penuh. Di Supabase hosted, peran `postgres`
bukan admin penuh. Akibatnya, pemulihan ke database sementara di server hosted bisa memunculkan galat izin yang bukan
galat jadwal (pg_cron) yang sudah dikenal alat. Kalau itu terjadi, setiap malam tercatat "belum terverifikasi"
walaupun file backupnya baik. Pemulihan itu juga sementara memakan ruang disk dan tenaga mesin database.

Usulan penulis: pemeriksaan pemulihan dijalankan di mesin GitHub (database Postgres sementara dengan versi yang sama
dengan hosted), bukan di server hosted. Ini butuh perubahan kecil pada alat backup dan uji ulang di CI. Perubahan itu
baru dikerjakan kalau Bos setuju.

## 5. Yang perlu Bos putuskan

1. Database tujuan: **A** (Enteng `siimvrusnzxexizpyoib`, database `postgres`) atau **B** (proyek produksi baru)?
2. Lokasi backup: **L1** (Cloudflare R2, usulan) atau **L2** (Google Drive)?
3. Pemeriksaan pemulihan dipindah ke mesin GitHub (bagian 4): ya atau tidak?

Setelah dipilih, Fable menyusun daftar periksa pemasangan dan backup pertama (register auditor 13 Okt). Pemasangan
tetap menunggu izin pemasangan dari Bos.
