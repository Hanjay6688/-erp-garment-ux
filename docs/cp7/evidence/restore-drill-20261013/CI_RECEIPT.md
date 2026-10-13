# Uji pemulihan ke Supabase lokal (D13-8b) — tanda terima CI writer

Bukan penerimaan auditor. Alat: `scripts/cp7_supabase_restore_drill.py`. Workflow: `CP7 Supabase Restore Drill`
(`.github/workflows/cp7-supabase-restore-drill.yml`). Alat backup `scripts/cp7_offsite_backup.py` sama dengan kandidat
`5db7c876` (tidak berubah).

## Susunan uji

- Sumber: salinan database ERP CP6 di CI (`cp6_rollback`, PostgreSQL 17.6, Supabase lokal pertama), ditambah dua akun
  login buatan (`drill-one/two@example.invalid`) supaya pemulihan tabel login ikut teruji.
- Satu malam dibuat oleh alat backup ke folder lokal, dengan enkripsi, ambil-ulang, cek hash, dan pemeriksaan
  pemulihannya sendiri.
- Target: **Supabase lokal kedua yang baru** di mesin yang sama (`supabase start`, image dan CLI sama, proyek
  `cp7-drill-target`). Pemulihan berjalan sebagai peran `postgres` target, yang **bukan admin penuh**, seperti di
  hosted.

## Hasil

| Run / job | Commit | Hasil |
|---|---|---|
| 38395295951 / 115288852862 | `a3e3463a` | **GAGAL** `DRILL_STRUCTURE_DIFFERS`: data sama, 0 galat pemulihan, tetapi 41 fungsi `public` ERP bisa dijalankan `anon` dan 1 view terbuka untuk `anon`. Log: `first_failure_a3e3463a_run38395295951_job115288852862.log`. |
| 38395427722 / 115289298577 | `06367091` | GAGAL di langkah uji pemulihan yang sama. Commit ini belum memuat perbaikan hak bawaan; lognya tidak dibaca terpisah. |
| 38397645331 / 115296855968 | `bebf2dc5` | **LULUS** `restore_verified: true`, 3/3 kasus tolak lulus |
| 38397645440 / 115296855969 | `bebf2dc5` | **LULUS** (run kembar dari push yang sama), 3/3 kasus tolak lulus |

Angka run 38397645331:

- Malam: `erp-20261013-193309-WIB-5a1536e1abfe`. Hash file terkunci dan dump sama dengan tanda terima.
- Target: `postgres`, bukan admin penuh, PostgreSQL 17.6, 11 skema bawaan.
- Daftar isi dump: 4.433 entri. 3.829 dipulihkan: 3.592 belum ada di target, 224 data, dan 13 hak akses yang diulang.
  Dibiarkan seperti buatan Supabase: 537 sudah ada di target, 48 data tabel Supabase, dan 19 pg_cron.
- Skema aplikasi: `erp`, `public`, `supabase_migrations`. Di luar skema itu yang ikut dipulihkan ada 10 entri,
  antara lain pemicu `trg_cp45_guard_last_owner_auth_delete` di `auth.users`.
- Hak bawaan peran `postgres` di target yang dikosongkan sebelum pemulihan: 6.
- Galat pemulihan: **0**.
- Data: 218 tabel, 955 baris, 6 nomor urut, **semuanya sama**. Login: `auth.users` 2, `auth.identities` 2. Tabel
  Supabase yang jumlah barisnya berbeda dari sumber: 0.
- Struktur seluruh database (semua skema, pemilik, hak akses): `differ` **{}**, `explained` {}. Perbedaan asli
  sebelum penyeragaman tetap tercatat: constraints 56, functions 16, indexes 2, relations 168, views 14.

Kasus tolak (target yang sama sesudah pemulihan):

| Kasus | Kode yang diharapkan | Hasil |
|---|---|---|
| `DRILL_REFUSES_USED_TARGET`: target sudah berisi | `DRILL_TARGET_NOT_FRESH` | PASS |
| `DRILL_REFUSES_ALTERED_COPY`: satu bit file backup diubah | `DRILL_REMOTE_COPY_DIFFERS` | PASS |
| `DRILL_REFUSES_SUPERUSER_POSTGRES`: `postgres` dijadikan admin penuh | `DRILL_TARGET_ROLE_NOT_HOSTED_LIKE` | PASS |

## Temuan dari run gagal pertama

Proyek Supabase baru sudah punya hak bawaan untuk `postgres` di skema `public`: setiap objek baru otomatis bisa
dipakai `anon`, `authenticated` dan `service_role`. Saat pemulihan, setiap objek dibuat ulang oleh `postgres`, jadi ikut
mendapat hak itu. Daftar hak akses di dump hanya mencatat beda dari bawaan PostgreSQL, sehingga tidak pernah mencabut
`anon`. Akibatnya, tanpa langkah tambahan, pemulihan ke proyek Supabase baru membuka fungsi ERP untuk pengguna yang
belum login.

Perbaikan di prosedur pemulihan, bukan di pembanding: hak bawaan peran `postgres` di target dikosongkan dulu
(jumlahnya dicatat), lalu hak bawaan milik malam itu dipulihkan paling akhir, sama seperti di sumber. Masalah ini
sudah direproduksi di salinan lokal (PG16) dan perbaikannya diperiksa di sana sebelum CI.

## Batas

- Lulus di Supabase lokal **belum otomatis membuktikan pemulihan ke Supabase hosted** (D13-8b). Versi Postgres,
  ekstensi dan batas hak akses `postgres` sama. Pengaturan proyek hosted (kunci API, pengaturan Auth di dashboard,
  domain) tidak ada di dump dan tidak diuji di sini.
- Pembandingnya database sumber yang masih ada (di CI). Untuk pemulihan sungguhan saat Enteng sudah tidak ada,
  pembanding harus disimpan di rincian terkunci setiap malam. Itu belum dibuat (lihat `docs/cp7/OFFSITE_BACKUP.md`).
- pg_cron tidak ikut dipulihkan, sama seperti pemeriksaan malam. Jadwal CP7C dipasang dengan pemasangnya sendiri.
- Data tabel Supabase selain login (sesi, token, log audit Auth) tidak dipulihkan. Bedanya dihitung (`left_behind`);
  di run ini 0.
