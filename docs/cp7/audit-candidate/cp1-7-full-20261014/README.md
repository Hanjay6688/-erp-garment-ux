# Kandidat audit penuh CP1–CP7 — 14 Okt 2026

Owner 14 Okt: "ya bikinin handoff sekalian tempel audit pro max ya buat astra fable". Ini langkah kedua dari urutan
owner 11 Okt (audit penuh CP7 → **audit penuh CP1–CP7** → CP7.5 → CP7C → CP8). Paket ini adalah **satu kandidat untuk
dua audit penuh independen** (Astra dan Fable) atas seluruh ERP CP1–CP7 pada versi beku final CP7. Semua kandidat lama
dan bukti kegagalan tetap disimpan dan tidak diubah. `production_go:false`.

| Berkas | Untuk |
|---|---|
| `README.md` | Identitas kandidat, cakupan, riwayat audit per tahap, bukti writer, butir terbuka |
| `HANDOFF_ASTRA.md` | Kotak teks yang disalin owner ke sesi Astra (instruksi + Panduan Audit Pro Max utuh) |
| `HANDOFF_FABLE.md` | Kotak teks yang disalin owner ke sesi Fable (instruksi + Panduan Audit Pro Max utuh) |

## Identitas kandidat

- **Commit: `0b7049d9203bac52b47a4c89f3e0d75646067a8f`**, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`, cabang
  `claude/new-session-deapao`. Ini commit pembekuan final CP7 (D13-13, `../../FREEZE_CP7_FINAL_20261014.md`).
- Commit sesudahnya hanya dokumen: `git diff --name-only 0b7049d9 <head cabang>` semuanya di bawah `docs/`.
- Tree produk pada commit itu (Pro Max §2.8):

| Direktori | Tree |
|---|---|
| `src` | `d6553972f94a4ad4e9170e8a946b30cdac9712fd` |
| `supabase/migrations` | `8f6053bbd0bda80da18065418ad43371cdfd9461` |
| `supabase/release` | `be1e91c172ffb5c05b694a3a54c69562700c6d5e` |
| `supabase/dev` | `88759f4fc51864a1ec9e224fcb4f236204b5c853` |
| `supabase/rollbacks` | `9e216e7bcca6b583341d9ea78cbc0414134ecee2` |
| `scripts/cp7-src` | `7bcf45e174499f3712c67ee08788a90a8c5f7881` |
| `supabase` (seluruhnya) | `5d040436db384b4e574785376367b360a084acb7` |
| `scripts` (seluruhnya) | `b67664091c4394b0ff6a187409d9e9b32213a0e0` |
| `.github/workflows` (139 berkas) | `4d7712279bfdfb6aec10dca4a216dd927875f483` |

- Panduan yang berlaku: `docs/AUDIT_PANDUAN_PRO_MAX.md` pada commit itu, blob `5df759c38e1ea98831a4dfdda3cfd1a2b8bb398b`,
  63.005 byte, SHA-256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`. Isinya sama dengan head
  cabang saat paket ini dibuat. Salinan utuh ada di kedua kotak handoff; bila ada beda, berkas di repo yang berlaku.
- Register keputusan owner: `docs/cp7/OWNER_DECISIONS_20261008.md` (sampai D13-13; sesudah `0b7049d9` hanya baris status
  pembekuan yang ditambah), `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25*.md`,
  `docs/cp6-d11-kebijakan-dan-gbd03.md`.

## Cakupan

Seluruh ERP CP1–CP7 pada kode final, bukan hanya delta CP7. Fokus yang belum pernah diaudit sebagai satu kesatuan:
**sambungan antartahap pada satu kode final** (Pro Max SKN-22): saldo awal cutover (CP6) → pembelian, potong, WIP
(CP3–5) → aksesori, laundry, konversi (CP6 BC..BF) → penjualan, retur, pembayaran (CP7 P11–P13) → payroll → laporan,
rekomendasi dan pengingat (CP7 F04/F05, v2) → koreksi di awal rantai → semua cek integritas nol.

| Tahap | Isi | Titik masuk baca |
|---|---|---|
| CP1 | Baseline: fingerprint, skema, repo | `docs/cp3-5-code-ownership.md` (riwayat), `docs/evidence/`, `docs/runbooks/` |
| CP2 | Backup terenkripsi dan restore basis pra-v2.6.10 | `docs/cp3-5-code-ownership.md` §Immutable migration history. Set pemulihan CP2 tidak ada di repo |
| CP3 / CP3.5 | Absensi–HPP, hak kerja/payroll, penyebut SELESAI_DIJAHIT; kepemilikan sumber, ledger migrasi | `docs/cp3-5-code-ownership.md`, `docs/evidence/backend_source_ownership.json`, `scripts/check-*-ownership.mjs` |
| CP4 / CP4.5 | Auth/RBAC, identitas, master, pola, WIP | `supabase/migrations/`, workflow `cp4-*`, `cp45-*` |
| CP5 | BS, rework, rewash, klaim; dampak stok/payroll/HPP/jurnal | workflow `cp5-*`, `cutting-bridge-*` |
| CP6 (AC..BF) | Saldo awal, uang muka, tutup buku per tanggal, HPP bertanggal, aksesori, laundry, kantong/celup/konversi; paket rilis T3 + rollback | `docs/cp6-au-r1-handoff.md` (§1–§34.9), `supabase/release/cp6-t3/MANIFEST.json`, `scripts/cp6_layers.py` |
| CP7 | P00–P21, F03–F05, koreksi transaksi, rencana/laporan/pengingat/AI v2, K2–K7, UI tersambung | `docs/cp7/framework-v2/00_MULAI_DI_SINI.md`, `../cp7-full-20261011/AUDITOR_START.md` (tabel cakupan CP7) |

Pro Max §16.5: CP1 dan CP2 dicatat eksplisit, tidak dianggap tercakup hanya karena regresi CP3–5 lolos. Bagian yang
buktinya tidak ada di repo ditulis `TIDAK DAPAT DIVERIFIKASI DARI SESI INI`, bukan lulus.

## Riwayat audit per tahap (masukan, bukan penerimaan audit ini)

| Tahap | Audit sebelumnya | Putusan / status |
|---|---|---|
| CP1–CP2 | Tidak ada laporan audit independen khusus yang ditemukan writer di repo | Belum pernah diaudit independen sebagai tahap sendiri (sepengetahuan writer) |
| CP3–CP5 | Kualifikasi skema penuh historis (workflow `cp3-r4-*`, `cp4-*`, `cp45-*`, `cp5-*`); 22 berkas bukti R5 CP3 dibekukan per byte | Bukti historis pada commit lama; regresi baseline (SKN-23) belum dijalankan ulang di kandidat ini |
| CP6 | Final audit 16 Sep: **CP6_HOLD** (`docs/cp6-final-audit-checkpoint.md`, kandidat `25fa4736`); audit successor: CP6_HOLD (`docs/cp6-final-successor-independent.md`); tinjauan per keluarga (`docs/cp6-*-independent-*.md`, `docs/reviews/ERP_CP6_Audit_757b79a_20260923.md`, cabang `audit/cp6-*`, `audit/bd-*`, `audit/be-*`, `audit/sku-range-*`) | PR32: CP6-FINAL-01 CLOSED (29 Sep, `docs/cp6-pr32-acceptance-and-r10-scope-20260929.md`); kesiapan CP6 diterima independen terbatas (`docs/cp7/evidence/cp6-readiness/INDEPENDENT_AUDIT_LOCK.json`, Fable R15/PR39, `bfb38c54`); status `CLOSED_CONTRACT_SCOPE_HOLD_NO_DEPLOYMENT`, `audit_complete=false` |
| CP7 | Kandidat beku `9d57b7f5` (8 Okt) → P20 Astra `2e605bb7` HOLD → Sol `8cc1b081` dan uji ulang `8116800c` PASS_RETEST → audit penuh CP7 `d0b9e9c2` (Astra `audit/astra-cp7-full-d0b9e9c2-20261012`, Fable `audit/fable-cp7-full-d0b9e9c2-20261011`) HOLD → perbaikan `5f1506f4`, `7a0b4a90`, `85e17168` → putaran silang 1 `ae0214ad` → putaran silang 2 `0b7049d9` | **Beku final** (D13-13): R2-A6 LENGKAP dan F-OPS-05 DITUTUP oleh kedua auditor; A2 terbuka bukan penghalang (D13-10) |

## Bukti writer pada kandidat (untuk diuji ulang, bukan diterima begitu saja)

- `../crosscheck-r2-20261014/CI_RECEIPT.json`: 20/20 workflow, 57/57 job sukses pada `0b7049d9`, semua GitHub attempt
  pertama. Isinya workflow kualifikasi CP7 (termasuk `CP7 Pre-freeze UI Regression` = oracle browser CP6 di tumpukan
  CP7 penuh, `CP7 F03 Full Retained Components`, `CP7 P21 Rehearsal`), Build UX dan CodeQL. Empat grup diulang dari
  salinan baru karena pergantian hari WIB: 92 eksekusi kasus, 41 di antaranya ditandai rollover (rinciannya di
  `../crosscheck-r2-20261014/README.md`).
- **Workflow era CP3–CP6 tidak dijalankan writer pada commit ini**: `cp3-r4-*`, `cp4-*`, `cp45-*`, `cp5-*`,
  `cutting-bridge-*`, `cp6-*-t1-probe`, `CP6 T2 Combined Regression`, `CP6 T3 Release Package`, `CP6 T3 Rollback`,
  `CP6 Release Readiness`, `CP6 Auditor Scenario`. Bukti terakhirnya ada di commit lama. Sebagian (snapshot historis)
  memang terikat commit lamanya; auditor menentukan sendiri mana yang wajib dijalankan ulang di kandidat ini.
- Rencana writer lama "uji gabungan 75 kasus C6 + 22 ALL dari ujung ke ujung pada satu head" (`docs/cp6-au-r1-handoff.md`
  §31.8, §32.9) tidak ditemukan writer sebagai satu run tercatat. Cakupannya mungkin sudah tertutup sebagian oleh paket
  rilis T3 dan alur gabungan 28 Sep (`docs/cp6-combined-release-writer-handoff-20260928.md`); itu belum dibuktikan.

## Butir terbuka yang diketahui (bukan temuan baru; boleh diuji)

- **A2 (D13-10):** penyebab dua kegagalan akhir grup bayar supplier (run 38288829388, 38330557862) belum ditemukan.
  Diagnosis tetap terpasang; log asli disimpan.
- **Batas operasional A1:** admin yang mengganti database tepat sebelum koneksi restore bisa membuat restore menulis ke
  database pengganti; pengganti tidak dihapus dan malam tidak diverifikasi.
- **CP6 lama:** `CP6 Auditor Scenario` merah pada 4 kasus browser CP6 sejak 2 Okt (2 `READINESS` karena layar CP7
  memanggil RPC CP7 yang tidak dipasang di skenario CP6 saja; 2 `SALES_MANUAL_13` dipensiunkan dari komposisi CP7,
  D13-9c, `../../RETIRED_CP6_SALES_MANUAL_13.md`). Oracle browser CP6 yang sama lulus di `CP7 Pre-freeze UI Regression`.
- **CP6 §34.8:** piutang ke vendor belum punya alur; status "HPP belum final" hanya tampil di halaman laundry; nilai
  pengaturan CP6 yang tersisa diisi di aplikasi saat dipakai.
- Bagi rata 4/4/4 hanya di layar simulasi dan diuji di jsdom. Kasus HP adalah emulasi Chromium; HP fisik/Safari belum.
- **K7:** capture 4,4–4,6 dtk diterima sementara sebagai latar (keputusan owner 8 Okt butir 7); 3 dtk belum tercapai.
- **Belum dipasang:** jadwal pembersihan, hapus 7 hari, penjalan K4 dan K6, backup malam (tahap CP7C).
- **Ditahan, tidak diaudit di sini (D13-9a):** alat backup CP7C (`scripts/cp7_offsite_backup*.py`,
  `scripts/cp7_supabase_restore_drill.py`, `ops/backup-repo/`, workflow `cp7-offsite-backup.yml`,
  `cp7-backup-kit-check.yml`, `cp7-supabase-restore-drill.yml`). Dikualifikasi ulang saat CP7C dibuka.
- **Bukan bagian kandidat:** PR #45 (UI demo). Area optimasi timeline PR44 tidak boleh diterima oleh penulisnya (Astra).
- Shadow run data nyata (§12.4) dan pemasangan dari salinan hosted nyata (§12.10, SKN-21) belum pernah dilakukan;
  keduanya butuh izin owner dan bukan bagian audit ini.
- `independent_acceptance=false`, `audit_complete=false`, `production_go=false`.

## Hasil yang diminta dari tiap auditor

Laporan format Pro Max §9 di cabang audit baru miliknya, dikunci dengan commit sebelum membaca laporan auditor lain di
putaran ini (§2.2, §16.7). Isinya: temuan per akar masalah dengan bukti, matriks invarian §5, vonis per tahap CP1–CP7
(LULUS / GAGAL / BELUM DIPERIKSA, dengan alasan), daftar "belum saya periksa", label asal-bukti per klaim, pertanyaan
owner dengan rekomendasi, dan ringkasan owner ≤ 10 kalimat. Sesudah keduanya terkunci: periksa silang seperti putaran
1–2, lalu penyatuan (§10).

## Sesudah audit ini

CP7.5 (kode diringkas, perilaku dibuktikan sama, riwayat lama diarsip), lalu CP7C (backup/restore, jadwal server, uji
beban; repo privat dan Drive), lalu CP8 (audit/gladi akhir, GO owner). Perbaikan atas temuan audit ini menjadi kandidat
baru dan diperiksa ulang.
