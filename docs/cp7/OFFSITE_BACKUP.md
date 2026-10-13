# Backup malam ke penyimpanan luar (alat versi 2)

Dasar: keputusan owner 13 Okt 2026. D13-5 menetapkan penyimpanan privat di luar database, terenkripsi, dengan 14 malam
terverifikasi. D13-6 menetapkan pemeriksaan pemulihan di mesin GitHub dan pengambilan kembali file dari penyimpanan.
D13-7 menetapkan produksi = Enteng dan backup ke Drive dulu. Batas biaya: tanpa biaya.

**Status:** alat sudah dibuat dan diuji di server sekali pakai. **Belum dipasang.** Hosted, Drive dan R2 tidak
disentuh. `production_go:false`. Alat ini bukan bagian dari putaran silang 1 (kandidat `ae0214ad`) dan akan diaudit
terpisah.

## Yang dikerjakan alat setiap malam

Alat: `scripts/cp7_offsite_backup.py`. Workflow: `.github/workflows/cp7-nightly-backup.yml`, masih nonaktif.

1. Database dibaca dalam satu potret waktu. Hasilnya: file dump, sidik isi setiap tabel, nilai setiap nomor urut, dan
   sidik struktur (tabel, kolom, aturan, indeks, fungsi, hak akses, pemilik, kebijakan RLS, dan lain-lain).
2. Dump dikunci (enkripsi AES-256) dengan kata sandi backup. Dump yang belum dikunci langsung dihapus.
3. File terkunci disalin ke penyimpanan luar (Google Drive atau R2). Kalau nama yang sama sudah ada, salinan ditolak.
4. File **diambil kembali** dari penyimpanan, dicek sama persis dengan yang diunggah, lalu dibuka kuncinya.
5. File hasil ambil-ulang itu dipulihkan ke database sementara di mesin GitHub (PostgreSQL versi sama), bukan di
   server produksi.
6. Isi, struktur, pemilik dan hak akses hasil pemulihan dibandingkan dengan potret di langkah 1. Hanya hasil yang
   sama persis yang dicatat **terverifikasi**.
7. Tanda terima disimpan di penyimpanan:
   - tanda terima biasa: hanya angka dan kode, tanpa nama tabel dan tanpa isi;
   - rincian terkunci.
8. Disimpan 14 malam terverifikasi terbaru. Yang lebih lama baru dihapus sesudah malam ini terverifikasi. Malam yang
   gagal tidak menghapus apa pun.

Log GitHub hanya memuat satu baris kode dan angka. Isi database tidak masuk log, artifact atau repo.

## Bukti uji (server sekali pakai)

Workflow `CP7 Offsite Backup` menjalankan 11 kasus dua kali: sekali ke penyimpanan S3 (peniru S3 di mesin uji, jalur
yang sama dengan R2) dan sekali ke folder biasa.

- Sumber: salinan database ERP CP6 di CI (`cp6_rollback`, PostgreSQL 17.6).
- Server pemulihan: kontainer kedua dengan image Supabase yang sama (`ghcr.io/supabase/postgres:17.6.1.165`).

**Hasil: lulus 11/11 di kedua penyimpanan.** Run 38385679082, job 115256750708, commit `a70523ce`. Baris kasus:
`../evidence/offsite-backup-20261013/offsite_backup_11_a70523ce_run38385679082_job115256750708.log`.

- **Data:** 265 tabel dan 10 nomor urut hasil pemulihan sama persis dengan sumbernya. Struktur, pemilik dan hak akses
  juga sama.
- **Galat pemulihan:** ada 19, semuanya pg_cron. Pemulihan dilakukan ke database selain `postgres`, sedangkan pg_cron
  hanya bisa dipasang di database `postgres`. Jadwalnya dipasang terpisah oleh `cp7_schedule.py`.
- **Dicatat terpisah sebagai "dijelaskan":** 2 hak akses skema `graphql` dan `graphql_public` milik Supabase. Supabase
  memasang hak akses itu saat ekstensi pg_graphql dibuat, dan pg_dump tidak membawanya. Keduanya tetap tertulis di
  tanda terima (`structure.explained`), tidak disembunyikan.

Run sebelumnya yang gagal disimpan sebagai riwayat. Semua run berada di commit sesudah kandidat putaran silang, dan
data tidak pernah berbeda.

| Run | Hasil | Sebab | Perbaikan |
|---|---|---|---|
| 38380406480 | Berhenti sebelum kasus | Image MinIO dari quay.io ditolak | Peniru S3 dari PyPI |
| 38381333559 | Semua malam `BACKUP_FAILED` | Di image Supabase, `postgres` bukan admin penuh | Server pemulihan sementara memakai admin khusus yang dibuat di server itu |
| 38382137554 | Struktur beda | (a) PostgreSQL menulis ulang bentuk `IN ('A','B')` pada kolom varchar sesudah pg_dump; (b) alat uji memanggil dirinya sendiri | (a) kedua sisi diseragamkan ke bentuk hasil pulihan, hanya untuk pola itu; (b) diperbaiki |
| 38382979521 | Struktur beda | Sama dengan (a) | Diperbaiki di run berikutnya |
| 38383998201 | Struktur beda | Hak akses eksplisit yang sama dengan bawaan vs bawaan (kosong); urutan peran (`order by 1`, kesalahan alat sendiri) | Hak akses dibandingkan maknanya (`acldefault`) sebagai himpunan; urutan diperbaiki |
| 38384868292 | Struktur beda | Skema `graphql`/`graphql_public` (lihat di atas) | Dicatat terpisah sebagai "dijelaskan" |
| **38385679082** | **11/11 lulus × 2** | | |

Penyeragaman di atas tidak melonggarkan pembanding untuk perubahan sungguhan. Kasus `OFB_STRUCTURE_DIFFERENCE_DETECTED`
mengubah daftar `IN` itu, hak akses dan aturan kolom di hasil pemulihan, dan ketiganya tetap tertangkap.

| Kasus | Yang dibuktikan |
|---|---|
| `OFB_VERIFIED_FROM_FETCHED_COPY` | Pemulihan dari file yang diambil kembali terverifikasi. File di penyimpanan terkunci, kata sandi salah ditolak, sumber tidak berubah, database sementara dan peran tambahan dibersihkan. |
| `OFB_NO_CONTENT_OUTSIDE_THE_REMOTE` | Baris log dan file di penyimpanan tidak memuat isi, nama tabel uji, atau dump yang tidak dikunci. |
| `OFB_TAMPERED_REMOTE_COPY_UNVERIFIED` | File di penyimpanan diubah sesudah diunggah → ditolak (`BACKUP_REMOTE_COPY_DIFFERS`), tidak ada yang dihapus. |
| `OFB_DATA_DIFFERENCE_DETECTED` | Satu baris berbeda di hasil pemulihan → tertangkap. |
| `OFB_STRUCTURE_DIFFERENCE_DETECTED` | Hak akses dan aturan kolom berbeda → tertangkap. |
| `OFB_SEQUENCE_DIFFERENCE_DETECTED` | Nomor urut berbeda → tertangkap. |
| `OFB_VERIFIED_UNDER_WRITES` | Database tetap ditulis selama backup, dan hasilnya tetap terverifikasi terhadap potret waktunya. |
| `OFB_REMOTE_RETENTION_14_VERIFIED` | 14 malam terverifikasi terbaru disimpan. Malam gagal tidak menghapus apa pun. Malam yang tidak terverifikasi atau tanpa tanda terima tetap ada selama lebih baru dari malam tertua yang disimpan. |
| `OFB_NAME_COLLISION_REFUSED` | Nama yang sudah ada ditolak dan file lama tidak berubah. |
| `OFB_SCRATCH_SERVER_GUARDS` | Server pemulihan yang sama dengan sumber, di luar mesin sendiri, atau berbeda versi → ditolak. |
| `OFB_FOREIGN_SCRATCH_NAME_REFUSED` | Database lain bernama sama di server pemulihan → ditolak dan dibiarkan utuh. |

## Yang belum dibuktikan (jujur)

- **Google Drive** belum diuji, karena butuh akun Bos. Alatnya memakai jalur rclone yang sama dengan R2/S3.
- Di server pemulihan sementara, pemulihan dijalankan sebagai admin penuh yang dibuat khusus di server itu. Server
  itu hilang bersama mesin GitHub sesudah job selesai.
- **Hosted belum pernah dibaca.** Di Supabase hosted, peran `postgres` bukan admin penuh. Saat pemasangan, baru
  ketahuan apakah ada tabel atau nomor urut yang tidak boleh dibaca. Kalau ada, malam itu gagal dengan kode, tidak
  diam-diam.
- **Pemulihan ke proyek Supabase terpisah** (syarat owner sebelum produksi) belum dilakukan. Pemeriksaan malam membuktikan
  dump bisa dipulihkan ke PostgreSQL versi sama. Itu belum membuktikan pengaturan Supabase (Auth, kunci, Storage)
  ikut pulih. Usulan tanpa biaya ada di register (pertanyaan no. 2, 13 Okt).
- File Supabase Storage tidak ikut. ERP saat ini tidak memakai Storage.

## Yang perlu disiapkan Bos saat pemasangan (tanpa biaya)

Semua disimpan di pengaturan rahasia GitHub, tidak lewat chat.

1. **Penyimpanan.** Untuk Google Drive: pasang rclone di laptop (gratis), jalankan `rclone config`, buat remote bernama
   `erpbackup` dengan jenis Google Drive dan akses "drive.file", lalu login Google. Isi konfigurasinya disimpan sebagai
   rahasia `CP7_BACKUP_RCLONE_CONFIG`. Folder tujuan, misalnya `erpbackup:erp-garment-backup/nightly`, disimpan sebagai
   variabel `CP7_BACKUP_REMOTE`. Untuk R2 caranya sama, dengan jenis S3.
2. **Kata sandi backup.** Kalimat acak yang panjang, disimpan sebagai rahasia `CP7_BACKUP_PASSPHRASE`. Bos juga wajib
   menyimpannya di luar GitHub (pengelola kata sandi atau kertas). Tanpa kata sandi ini, tidak satu pun backup bisa
   dibuka.
3. **Alamat database** Enteng lewat "Session pooler" (IPv4), disimpan sebagai rahasia `CP7_BACKUP_SOURCE_URL`.
4. **Image server pemulihan** dengan versi yang sama dengan Enteng, disimpan sebagai variabel
   `CP7_BACKUP_SCRATCH_IMAGE`.
5. Variabel `CP7_NIGHTLY_BACKUP_INSTALLED=true` dan baris jadwal 01:00 WIB baru diaktifkan sesudah izin pemasangan.
   Sebelum perubahan apa pun di Enteng, workflow dijalankan sekali secara manual sebagai backup pertama (D13-7a).

## Cara memulihkan (kalau dibutuhkan)

1. Pilih malam yang tanda terimanya bertuliskan `restore_verified: true`.
2. Unduh `<malam>.dump.gpg` dan `<malam>.receipt.json`. Cocokkan SHA-256 file dengan `encrypted.sha256` di tanda
   terima.
3. Buka kunci dengan kata sandi backup (`gpg --decrypt`). Cocokkan SHA-256 hasilnya dengan `dump.sha256`.
4. Pulihkan ke database atau proyek **baru**, bukan menimpa yang sedang dipakai. Langkah persis untuk proyek Supabase
   baru ditulis sesudah uji pemulihan ke proyek terpisah.
