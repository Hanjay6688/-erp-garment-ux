# Gladi pemasangan jadwal di salinan sekali pakai CI

Permintaan owner, 13 Okt 2026 (instruksi ke penulis no. 2): "Gladi jadwal di salinan sekali pakai CI dengan deklarasi
01:00 WIB, cocokkan `schedules()` dengan K3, lalu uninstall dan buktikan pemulihannya. Hosted tetap tidak disentuh."

**Hasil: PASS.** Kasus `K3C_RACE_SCHEDULE_INSTALLER_REHEARSAL` di suite `k3-cleanup-23`.

| Hal | Nilai |
|---|---|
| Workflow / run / job | `CP7 P19 Analysis Job Transport`, run 38355904844, job 115158614355 (`k3-cleanup-23`), 06:46:59–06:59:34 UTC |
| Commit / tree | `a09b692265699db198e7a1c29e1ea007cfcf8cc4` / `9369d631` |
| Suite | `CP7_K3_CLEANUP` PASS, 23 dari 23 kasus, `cp6_restored: true`, `advisor_gate: true` |
| Database salinan | `cp6_auditor_race`, salinan sekali pakai di container `supabase_db_cp5-local` (127.0.0.1:54322) milik runner |
| Database pg_cron | `postgres` di container yang sama |
| Koneksi hosted | Tidak ada. Kasus menolak alamat database selain mesin runner sendiri (`127.0.0.1`, `localhost` atau soket lokal; `K3C_REHEARSAL_DISPOSABLE_ONLY`). Log job tidak memuat ID proyek Enteng maupun ERP-Garment lama. |
| Log | baris kasus: `08_k3_cleanup_23_a09b6922_run38355904844_job115158614355.log` |

## Urutan dan bukti

Pemasang yang dipakai sama dengan yang akan dipakai saat pemasangan sungguhan: `scripts/cp7_schedule.py`, dijalankan
sebagai proses terpisah dengan jadwal asli. Tidak ada `TEST_SCHEDULE_OVERRIDE`.

1. **`cron.job` sebelum:** 0 baris. Data salinan dicatat per tabel (559 tabel).
2. **Penolakan, tanpa mengubah `cron.job`:**
   - pasang tanpa izin → `CP7_SCHEDULE_INSTALL_NOT_APPROVED`;
   - pasang dengan `--database cp6_auditor_race_other` → `CP7_SCHEDULE_DATABASE_MISMATCH` (nama database harus sama
     dengan database yang tersambung, temuan Fable F-OPS-04).
3. **Pasang** dengan `--installation-approved`. Hasilnya empat jadwal, dengan id 14–17:

   | Nama | Jadwal (UTC) | Arti | Database | Pengguna | Aktif |
   |---|---|---|---|---|---|
   | `cp7-staged-cleanup@cp6_auditor_race` | `*/5 * * * *` | tiap 5 menit | `cp6_auditor_race` | `postgres` | ya |
   | `cp7-staged-retention@cp6_auditor_race` | `30 19 * * *` | 02:30 WIB | `cp6_auditor_race` | `postgres` | ya |
   | `cp7-staged-runner@cp6_auditor_race` | `* * * * *` | tiap menit | `cp6_auditor_race` | `postgres` | ya |
   | `cp7-proof-runner@cp6_auditor_race` | `*/10 * * * *` | tiap 10 menit | `cp6_auditor_race` | `postgres` | ya |

4. **Pasang ulang:** id tetap sama (tidak ada jadwal ganda). **Verifikasi:** `matches: true`.
5. **`schedules()` vs K3:** definisi di database = `schedules` di `docs/cp7/k3/K3_CLEANUP.json` = deklarasi di
   alat uji. Keempat baris `cron.job` (nama, jadwal, perintah, database, pengguna, aktif) sama persis dengan deklarasi.
6. **Backup malam 01:00 WIB:** deklarasi K3 = `nightly.SCHEDULE` = `0 18 * * *` UTC (01:00 WIB). Workflow
   `.github/workflows/cp7-nightly-backup.yml` memuat baris itu tetapi masih dikomentari. Backup berjalan di luar
   database, jadi tidak ada di `cron.job`.
7. **Lepas tanpa izin** → `CP7_SCHEDULE_UNINSTALL_NOT_APPROVED`. **Lepas** dengan `--removal-approved`: keempat nama
   dilepas.
8. **Sesudah:** `cron.job` 0 baris, sama persis dengan sebelum. Tidak ada jadwal yang sempat jalan
   (`cron.job_run_details` sejak pemasangan kosong). Pemasangan dilakukan di antara detik 3–35 dan dilepas beberapa
   detik kemudian. Data 559 tabel salinan sama persis dengan sebelum.

## Batas

- Ini gladi di salinan CI, bukan pemasangan. Hosted, `main`, Cloudflare dan produksi tidak disentuh.
  `production_go:false`.
- Pemasangan sungguhan tetap menunggu izin owner (D13-3) setelah database tujuan dan lokasi backup dipilih
  (`docs/cp7/BACKUP_DESTINATION_PROPOSAL_20261013.md`).
- Di Supabase hosted, pg_cron dan database aplikasi sama-sama bernama `postgres`, jadi nama jadwal di sana menjadi
  `nama@postgres`.
