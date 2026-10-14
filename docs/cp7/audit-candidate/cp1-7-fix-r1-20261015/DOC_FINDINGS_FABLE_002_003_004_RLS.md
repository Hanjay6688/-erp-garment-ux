# Temuan dokumen: FABLE-002, FABLE-003, FABLE-004, dan 4 tabel tanpa RLS (R-DOC01..03, R-DOC05)

Tidak ada pengaman yang dilonggarkan. Tidak ada berkas migrasi lama atau manifest ber-hash yang diubah.

## R-DOC01 / FABLE-002: dua salinan AC..AV
- **Salinan resmi untuk pemasangan baru** adalah paket rilis `supabase/release/cp6-t3/`, 30 berkas AC..BF, sesuai
  `MANIFEST.json`.
- `supabase/migrations/*_20ac..20av_*` adalah berkas asli. Berkas ini tidak diubah, karena berkas migrasi yang sudah
  terpasang tidak boleh berubah isinya.
- Perbedaannya hanya pin pengaman yang diambil ulang di rantai yang sama dengan hosted (keputusan owner G-01 opsi b). Jenis
  pin yang berubah ada empat:
  - AC_VIEW: teks view `v_payroll_nota_browser` versi hosted;
  - LEDGER: hash pendahulu, menurun berantai;
  - CATALOG: jumlah dan sidik katalog;
  - CAPSULE: hash kapsul rollback.
- AW..BF hanya ada di paket. Sumbernya ada di `supabase/release/cp6-t3-src`.
- **Pemeriksaan baru `scripts/cp7_release_copy_check.py`** (baca-saja, tanpa database). Pemeriksaan ini membangun ulang ke-30
  berkas paket dari sumber dan pin yang dikomit, memakai cara turunan pembangun asli, lalu mewajibkan:
  - sumber tidak berubah sejak dicatat;
  - hasil bangun ulang identik byte dengan berkas paket dan hash manifest;
  - daftar substitusi sama dengan manifest dan hanya memakai empat jenis di atas.

  Hasil di pohon ini: **PASS**, 30 berkas. AC berbeda 8 baris (AC_VIEW). AD..AN masing-masing 2 baris (LEDGER). AO..BF
  8–20 baris (LEDGER/CATALOG/CAPSULE).

## R-DOC02 / FABLE-003: label manifest dan komentar basi
- `MANIFEST.json` tidak diubah, karena sha256-nya dipin oleh `scripts/cp7_p00_catalogue.py`.
  - `rollbacks: NOT_TESTED` dan `label: T3_PREP` adalah nilai saat paket dibangun. Rollback dibangun dan diuji sesudahnya
    oleh `scripts/cp6_t3_rollback.py`.
  - Bukti terakhir: workflow `cp6-t3-rollback.yml` run 38522026931, job 115713691756 (14 Okt 2026, head `00b0eb24`),
    berjudul "committed 30-file package, AC..BF rollback auto", hasil **success**.
  - Sejak `00b0eb24`, paket dan migrasi tidak berubah (diperiksa dengan `git diff`). Alat rollback hanya berubah komentar
    (butir di bawah); perubahan itu memicu cycle rollback lagi di head ini, dan hasilnya dicatat di kualifikasi kandidat.
  - Bukti cycle sebelumnya: 139/139 PASS (run 36222384316, handoff CP6 §34).
- Komentar basi dibetulkan. Hanya komentar; kode tidak berubah:
  - `cp6-t3-release-package.yml`: "24 files" dan "29-file" menjadi 30 berkas AC..BF;
  - `cp6_t3_release_package.py`: AC..AV menjadi AC..BF, dan catatan NOT_TESTED dijelaskan;
  - `cp6_t3_rollback.py`: AC..BD, AW..BA, dan BA..AC menjadi AC..BF, AW..BF, dan BF..AC, sesuai `KEYS` dan
    `reversed(ALL)` di kodenya;
  - `cp6_t3_package_run.py`.

## R-DOC03 / FABLE-004: bukti CP1/CP2 di pohon kandidat
Bukti dan skrip CP1/CP2 sekarang ada di `docs/evidence/cp1-cp2/`.
- Isinya salinan byte-demi-byte. Asal commit dan sha256 tiap berkas dicatat di `MANIFEST.json`.
- Tidak ada kunci, arsip, atau baris data.
- Pemeriksaan independen Fable (A1: CP1, A2: CP2) dan Astra dirujuk di README folder itu.
- Restore CP2 di image Supabase asli tetap menjadi bagian CP7C dan masih ditahan (D13-9a).

## R-DOC05: 4 tabel `erp` di hosted tanpa RLS
Sumbernya riwayat migrasi saja; hosted tidak di-query.
- Rantai yang terpasang di hosted adalah bootstrap CP4.5a ditambah migrasi sampai `20260904232442_erp_v2_6_20`. Rantai itu
  membuat 180 tabel `erp`, 176 di antaranya dengan RLS. Angka ini sama dengan bacaan Fable di hosted (176 aktif, 4 tidak).
- Keempat tabel itu adalah **kapsul rollback rilis lama**, berisi salinan definisi fungsi untuk rollback:
  - `erp.cp3_r4_rollback_capsule`
  - `erp.cp4_v2616_rollback_capsule`
  - `erp.cp45_v2617_rollback_capsule`
  - `erp.cp45_v2617a_rollback_capsule`
- Pemilik keempatnya `postgres`. Bootstrap mencabut semua hak dari `public, anon, authenticated, service_role`, dan tidak
  ada GRANT sesudahnya di migrasi mana pun. Jadi peran publik tidak dapat menjangkaunya; ini bukan temuan INV-A05.
- Kode final menyalakan RLS pada keempatnya: migrasi `20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.sql` baris
  173–176. Hasilnya, 0 tabel tanpa RLS sesudah paket dipasang (Fable A3).
- Cara memeriksa ulang: pindai `create table erp.*` dan `enable row level security` pada bootstrap ditambah migrasi
  ≤ `20260904232442`.
