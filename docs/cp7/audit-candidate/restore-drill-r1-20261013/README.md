# Paket uji silang: uji pemulihan ke Supabase lokal (D13-8b) — 13 Okt 2026

Dasar: keputusan owner D13-8b. Uji pemulihan sebelum produksi tidak menimpa Enteng. Uji dilakukan di Supabase
lokal/container sekali pakai di mesin GitHub, dengan versi, ekstensi dan batas hak akses seperti hosted. Batasnya
wajib dicatat: lulus di lokal belum otomatis membuktikan pemulihan hosted.

Paket ini menyambung paket alat backup v2 (`../offsite-backup-r1-20261013/`, kandidat `5db7c876`). Alat backup tidak
berubah: `git diff 5db7c876 bebf2dc5 -- scripts/cp7_offsite_backup.py scripts/cp7_nightly_backup.py` kosong. Kedua
paket boleh dikirim bersamaan. Astra dan Fable menerima **paket yang sama**. `production_go:false`. Enteng, Google
Drive dan hosted tidak disentuh.

## Identitas

- **Kandidat: `bebf2dc5c7c4924c3578e62f3a1788e5a65b8fd7`**, cabang `claude/new-session-deapao`.
- Berkas: `scripts/cp7_supabase_restore_drill.py`, `.github/workflows/cp7-supabase-restore-drill.yml`.
- Kode produk ERP (`supabase/`, `src/`, `scripts/cp7-src/`) tidak berubah sejak `ae0214ad`.

## Cara kerja (ringkas; lengkapnya di docstring alat)

1. Satu malam diambil dari penyimpanan. SHA-256 file terkunci dan dump dicocokkan dengan tanda terima.
2. Target harus baru. Syaratnya: peran `postgres` dan bukan superuser, `auth.users`/`auth.identities` kosong, dan
   `public` tanpa objek. Kalau tidak, muncul `DRILL_TARGET_NOT_FRESH` atau `DRILL_TARGET_ROLE_NOT_HOSTED_LIKE`.
3. Isi target didaftar dengan `pg_dump --schema-only` sebagai `postgres`, lalu `pg_restore -l`. Entri malam yang sama
   persis (jenis, skema, nama, pemilik) dengan yang sudah ada di target adalah milik Supabase dan dibiarkan. Yang
   dipulihkan:
   - definisi yang belum ada di target, termasuk tambahan aplikasi di skema Supabase;
   - hak akses, komentar dan hak bawaan yang pemiliknya bisa diperankan `postgres`;
   - data skema aplikasi dan data login (`auth.users` lalu `auth.identities`);
   - peran yang belum ada, dibuat NOLOGIN.

   pg_cron dan entri tingkat database tidak dipulihkan. Jenis entri yang tidak dikenal menghentikan uji
   (`DRILL_TOC_UNKNOWN`).
4. **Hak bawaan `postgres` di target dikosongkan sebelum pemulihan** (`clear_default_privileges`). Hak bawaan milik
   malam itu dipulihkan paling akhir.
5. Pembanding (tidak diubah dari alat backup):
   - data: md5 dan jumlah baris setiap tabel skema aplikasi dan tabel login;
   - nomor urut;
   - struktur seluruh database dengan `off.structure`, termasuk semua skema, pemilik dan hak akses, dibandingkan lewat
     `off.compare_structure`;
   - struktur mentah, yang setiap bedanya dicatat.

   Tabel Supabase yang tidak dipulihkan dan jumlah barisnya beda dari sumber dihitung (`left_behind`).

## Hasil CI writer

Lihat `../../evidence/restore-drill-20261013/CI_RECEIPT.md`. Ringkasnya:

- Run 38395295951 (`a3e3463a`) gagal pertama: 41 fungsi `public` dan 1 view terbuka untuk `anon` sesudah pemulihan.
  Lognya disimpan.
- Run 38397645331 dan 38397645440 (`bebf2dc5`) lulus:
  - 0 galat;
  - 218 tabel / 955 baris sama, termasuk 2 login;
  - struktur `differ` {};
  - 3/3 kasus tolak.

## Batas yang dinyatakan

- Lulus di Supabase lokal belum otomatis membuktikan pemulihan ke Supabase hosted (D13-8b).
- Pembandingnya database sumber yang masih hidup. Mode pemulihan sungguhan tanpa sumber belum ada. Usulannya ada di
  `docs/cp7/OFFSITE_BACKUP.md`.
- pg_cron, data Supabase selain login, dan pengaturan proyek hosted (kunci, pengaturan Auth di dashboard) tidak
  dipulihkan.
- Kasus tolak berjalan di target yang sama sesudah pemulihan. Uji "tanpa pengosongan hak bawaan pasti gagal" tidak
  diulang di CI; buktinya run gagal pertama dan reproduksi lokal.
