# Pembekuan final CP7 — 14 Okt 2026

**CP7 dibekukan final pada commit `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree
`ce6aed0a0af920e8aa80248f3cabcd293688df18`.** `production_go:false`.

## Dasar

D13-13 (owner, verbatim di `OWNER_DECISIONS_20261008.md`) menyatakan: "Pembekuan final mengikuti penutupan dua butir
tersebut; A2 tetap tercantum sebagai keterbatasan terbuka." Kedua butir itu (D13-12: R2-A6 dan F-OPS-05) sudah ditutup
oleh kedua auditor pada kandidat yang sama.

| Auditor | Laporan | R2-A6 | F-OPS-05 | Bantahan |
|---|---|---|---|---|
| Astra | `audit/astra_xc2_20261014/REPORT.md`, cabang `audit/astra-cp7-xc2-0b7049d9-20261014`; terkunci `57ac8aab`, pemeriksaan paket final `fb24bd92` | LENGKAP | DITUTUP | — |
| Fable | `audit/fable_cp7/AUDIT_FABLE_XC2_0b7049d9_v1.2.md`, cabang `audit/fable-cp7-full-d0b9e9c2-20261011`; final `46fe722c`, koreksi angka `c17a53b2`, `319e6624` | LENGKAP | DITUTUP | Tidak ada bantahan terhadap Astra |

CI writer pada kandidat: `docs/cp7/audit-candidate/crosscheck-r2-20261014/CI_RECEIPT.json` (20/20 workflow, 57/57 job,
GitHub attempt pertama; empat grup diulang karena pergantian hari WIB, 92 eksekusi, 41 di antaranya ditandai rollover).

## Isi yang dibekukan

- Kode produk (`supabase/`, `src/`, `scripts/cp7-src/`) identik dengan `7a0b4a90` dan `ae0214ad`.
- Alat dan uji pada commit kandidat, termasuk aturan tanda backup ber-OID (F-OPS-05) dan kasus browser P11 helper lusin.
- Register keputusan owner sampai D13-13.
- Pensiun `SALES_MANUAL_13` (desktop dan HP) dari komposisi CP7 sah (D13-9c, kedua auditor menyatakan LENGKAP). Kasus
  aslinya tetap ada di suite CP6 beku.

## Keterbatasan dan catatan yang ikut tercantum

- **A2 MASIH TERBUKA (bukan penghalang, D13-10).** Penyebab dua kegagalan akhir grup bayar supplier (run 38288829388
  dan 38330557862) belum ditemukan. Diagnosis tetap terpasang dan log asli tetap disimpan.
- **Batas operasional A1.** Admin yang mengganti database tepat sebelum koneksi restore bisa membuat restore menulis
  ke database pengganti. Pengganti itu tidak dihapus dan malam tidak diverifikasi. Pemeriksaan pemulihan berjalan di
  database sementara mesin GitHub (D13-6, D13-8b), bukan di cluster bersama.
- Bagi rata 4/4/4 hanya ada di layar simulasi yang tidak tampil di mode tersambung, dan hanya diuji di jsdom. Kasus
  HP adalah emulasi Chromium.

## Yang tidak termasuk pembekuan ini

- Tidak ada pemasangan ke Enteng atau hosted. Jadwal pg_cron dan backup malam belum dipasang.
- Backup ke Google Drive, uji Drive dan repo privat ditahan sampai CP7C (D13-9a). Alat CP7C yang ada di cabang
  (`scripts/cp7_offsite_backup*.py`, `scripts/cp7_supabase_restore_drill.py`, `ops/backup-repo/`) tidak diaudit di
  pembekuan ini, dan perlu dikualifikasi ulang saat CP7C dibuka.
- Urutan berikutnya menurut owner (11 Okt): audit penuh CP1–CP7, lalu CP7.5, lalu CP7C, lalu CP8.
