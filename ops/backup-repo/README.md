# Perlengkapan repo backup privat (keputusan owner D13-8, 13 Okt 2026)

**Ditahan sampai tahap CP7C (keputusan owner D13-9a, 13 Okt 2026). Langkah di bawah belum perlu dikerjakan.**

Folder ini berisi semua yang perlu dipindah ke repo GitHub **privat** untuk backup produksi. Kode alatnya tidak
disalin: workflow mengambil alat dari repo ini pada satu commit yang dikunci, yaitu
`5db7c8763a651304b2fd37b8eadb9616d0afe151`. Dengan begitu, yang dijalankan sama persis dengan yang diaudit. Kalau
alatnya berubah, commit kunci itu ikut diganti dan diaudit ulang.

| Berkas | Fungsi |
|---|---|
| `workflows/drive-proof.yml` | Uji jalur Google Drive sungguhan pada data **buatan**: unggah, unduh kembali, cek hash, pulihkan, cocokkan data, struktur dan hak akses, penyimpanan 14 malam, dan penolakan. Folder uji di Drive dikosongkan lagi sesudahnya. Tidak membaca Enteng. |
| `workflows/nightly-backup.yml` | Backup Enteng ke Drive. Pertama dijalankan manual sebagai **backup awal**. Jadwal 01:00 WIB masih dimatikan sampai Bos menyalakannya. Workflow ini hanya membaca Enteng, tidak mengubahnya. |
| `proof.sh`, `proof_seed.sql` | Dipakai `drive-proof.yml`, diambil dari repo ini pada commit yang dikunci. |

## Biaya: Rp0

- Repo privat gratis mendapat 2.000 menit GitHub Actions per bulan. Perkiraan pemakaian: backup malam sekitar 10
  menit × 31 malam ≈ 310 menit, ditambah beberapa kali uji.
- **Jangan daftarkan kartu atau PayPal di GitHub.** Tanpa metode pembayaran, GitHub menghentikan job kalau kuota habis,
  tidak menagih. Kalau di akun sudah ada kartu, buka *Settings → Billing and licensing → Budgets and alerts* dan pasang
  batas Actions **$0** dengan pilihan menghentikan pemakaian.
- Workflow memakai runner standar `ubuntu-24.04` dan batas waktu 40–45 menit. Hanya satu job jalan dalam satu waktu.
  Tidak ada cache dan tidak ada artifact.
- Google Drive gratis 15 GB, dipakai bersama Gmail dan Foto. Tanda terima mencatat sisa ruang Drive dan memberi
  peringatan `BACKUP_REMOTE_SPACE_LOW` kalau hampir penuh. Backup lama yang baik **tidak** dihapus untuk memberi ruang.
  Backup yang dihapus otomatis masuk Sampah Drive dan baru hilang sesudah 30 hari.

## Langkah Bos (sekali saja)

**A. Repo privat**

1. Di GitHub: *New repository* → nama bebas, misalnya `erp-garment-backup` → **Private** → *Create repository*.
2. Di repo baru: *Add file → Create new file*. Ketik nama `.github/workflows/drive-proof.yml`, tempel isi
   `workflows/drive-proof.yml` dari folder ini, lalu *Commit*. Ulangi untuk `.github/workflows/nightly-backup.yml`.

**B. Izin Google Drive (di laptop Bos, gratis)**

3. Pasang rclone dari situs resminya, rclone.org (bagian Downloads).
4. Buka Terminal/Command Prompt, ketik `rclone config`, lalu jawab:
   - `n` (remote baru), nama: `erpbackup`;
   - jenis penyimpanan: **Google Drive** (`drive`);
   - `client_id` dan `client_secret` dikosongkan;
   - scope: pilih yang aksesnya **hanya file yang dibuat rclone** (`drive.file`);
   - pertanyaan lain dibiarkan bawaan, dan "auto config" dijawab **yes**.

   Browser akan terbuka. Login dengan akun Google Bos, lalu izinkan.
5. Ketik `rclone mkdir erpbackup:erp-garment-backup` untuk membuat folder backup.
6. Ketik `rclone config show erpbackup`. Salin seluruh teks yang muncul, mulai dari `[erpbackup]`. **Teks ini kunci
   folder backup. Jangan kirim lewat chat ke siapa pun**, cukup tempel di langkah 7.

**C. Rahasia di repo privat** (*Settings → Secrets and variables → Actions*)

7. *Secrets → New repository secret*:
   - `CP7_BACKUP_RCLONE_CONFIG`: teks dari langkah 6.
   - `CP7_BACKUP_PASSPHRASE`: kalimat acak yang panjang (misalnya 6–8 kata acak). **Tulis juga di kertas atau
     pengelola kata sandi.** Tanpa kalimat ini, tidak satu pun backup bisa dibuka.
8. *Variables → New repository variable*:
   - `CP7_BACKUP_DRIVE_ROOT` = `erpbackup:erp-garment-backup`
   - `CP7_BACKUP_SCRATCH_IMAGE` = `public.ecr.aws/supabase/postgres:<versi>`. Versinya **sama persis** dengan Postgres
     Enteng, terlihat di Supabase Dashboard → *Project Settings → Infrastructure* (contoh: `17.6.1.165`).

**D. Uji Google Drive (wajib sebelum alat dipakai)**

9. Di repo privat: *Actions → Drive proof → Run workflow*. Tunggu sekitar 10–20 menit.
10. Hijau berarti jalur Drive terbukti. Kirim tautan run itu ke penulis. Tautannya tidak memuat rahasia.

**E. Backup awal Enteng (sesudah langkah 10 hijau dan Bos setuju)**

11. Tambah secret `CP7_BACKUP_SOURCE_URL`: alamat koneksi Enteng dari Supabase Dashboard → *Connect* → **Session
    pooler** (URI, sudah termasuk kata sandi database).
12. *Actions → ERP nightly backup → Run workflow*. Hijau dan `restore_verified: true` di tanda terima Drive berarti
    backup awal berhasil dan terverifikasi. Baru sesudah itu Enteng boleh diubah (D13-8f).
13. Jadwal 01:00 WIB dinyalakan belakangan, dengan mengubah satu baris di `nightly-backup.yml` atas izin Bos.

## Batas pembuktian

- Uji Drive memakai data buatan, bukan data Enteng. Yang dibuktikan adalah jalurnya: Drive, kunci, hash, pemulihan,
  dan pencocokan.
- Pemeriksaan pemulihan berjalan di Supabase Postgres sementara di mesin GitHub, dengan versi yang sama. Lulus di sana
  **belum otomatis membuktikan** pemulihan ke Supabase hosted (D13-8b).
- Backup awal adalah pertama kalinya Enteng dibaca alat ini. Kalau ada tabel yang tidak boleh dibaca peran `postgres`
  di hosted, malam itu gagal dengan kode yang jelas, tidak diam-diam.
