# Addendum A1 laporan cp17 — CP1/CP2 dengan izin owner D14-1 (14 Okt 2026)

Tidak menimpa laporan v1.0 (sha256 di `LOCK.md`). Label: FABLE (query baca-saja Fable ke hosted atas izin D14-1).

## Yang dijalankan
Dua query SELECT katalog ke Supabase ERP Enteng `siimvrusnzxexizpyoib` (PostgreSQL 17.6.1.165) lewat konektor sesi; tidak ada tulis, tidak ada baris data bisnis yang keluar (hanya hash dan jumlah).
1. `runs/cp12/cp1_fingerprint.sql` — algoritma `CP1_REVALIDATION_V1` dari cabang bukti `codex/cp1-revalidation-evidence-20260901` (sha256 943bf118…, sama dengan yang dikutip penulis; 0 perintah tulis). Hasil: `runs/cp12/hosted_cp1_v1_20261014.json`, 2026-10-14T13:18:52Z.
2. `runs/cp12/g01_summary.sql` — query ringkasan G-01 dari pohon beku (sha256 223a9653…, sama dengan `summary_sql_sha256` di `docs/evidence/cp6-g01/hosted_summary.json`). Hasil: `runs/cp12/hosted_g01_20261014.json`.

## Hasil
| Pembanding | Hasil |
|---|---|
| Hosted hari ini vs rekaman G-01 (23 Sep, v2.6.20) | **IDENTIK 16/16 jenis** (function 537, function_owner_acl 537, relation 237, relation_owner_acl 237, view 51, constraint 1184, index 520, trigger 435, policy 190, sequence 6, type/schema/default_acl/extension, app_ledger 55, platform_ledger 70, config_hash 6 — semua md5 sama). Hosted tidak berubah sejak G-01. |
| Hosted hari ini vs revalidasi CP1 (1 Sep, v2.6.13b) | Berbeda seperti seharusnya: fingerprint V1 `caf4560c…` → `24ca84da…`; tabel erp 142 → 180, fungsi 436 → 537, migrasi platform 55 → 70 (terakhir `20260904232442_erp_v2_6_20_cp6_laundry_qc_fg_authoritative`). Selisihnya adalah migrasi v2.6.14..v2.6.20 yang tercatat. |
| Status runtime hosted | `auth_users` 0, `app_users` 0, `other_nonidle_sessions` 0, storage 1 bucket/1 objek, `cron_jobs` 1 aktif — **sama dengan 1 Sep** (job itu sudah ada sejak CP1, bukan pemasangan baru; sesuai D13-3). RLS: 176 tabel erp aktif, **4 tidak aktif** (1 Sep: 142/0). |
| Arsip CP2 | **Tidak dapat diambil**: artefak Actions run 33430989888/33457299164 sudah tidak ada (0 artefak); sesi ini tidak punya konektor Google Drive. Restore independen CP2 belum dilakukan. |

## Dampak pada vonis
- **CP1: LULUS DENGAN SYARAT** (sebelumnya BELUM DIPERIKSA). Alat fingerprint CP1 terverifikasi baca-saja dan hash-nya cocok; target hosted dapat diukur ulang dan identik dengan baseline G-01 yang dipakai semua paket CP6/CP7, jadi rantai baseline CP1 → G-01 → paket rilis tersambung. Syarat: bukti CP1 dibawa ke pohon kandidat (FABLE-004), dan 4 tabel erp tanpa RLS dijelaskan (lihat di bawah).
- **CP2: TETAP BELUM DIPERIKSA — TIDAK DAPAT DIVERIFIKASI DARI SESI INI** sampai arsip + kunci tersedia. Owner sudah mengizinkan Drive (D14-1); yang kurang hanya konektor Drive di sesi.
- **Catatan baru (S3, bukan temuan produk sampai dijelaskan): 4 tabel di skema `erp` hosted tidak memakai RLS** (1 Sep: 0). Nama tabelnya tidak dibaca di putaran ini (query lanjutan tidak dijalankan). Penulis diminta menyebut keempatnya dan alasannya; bila salah satu dapat dijangkau peran publik, naik menjadi temuan INV-A05.

## Yang belum dijalankan
- Nama dan jadwal job cron hosted (query baca-saja metadata `cron.job` ditolak di prompt izin sesi; tidak diulang).
- Restore independen CP2 (butuh konektor Drive).
