# Fable — audit penuh CP7 kandidat `d0b9e9c2` (mulai 11 Okt 2026, UTC)

Cabang audit: `audit/fable-cp7-full-d0b9e9c2-20261011` (hanya berkas audit). Tidak ada push ke cabang penulis.
Panduan yang berlaku: `docs/AUDIT_PANDUAN_PRO_MAX.md` versi PR #42 (perintah owner 6 Okt: "PR42 belum merged, jadi gunakan
panduan dari PR tersebut"); versi di cabang kandidat (`5548ff18`) adalah versi 31ee23f0 + nama Sol, TANPA §1.7–1.9,
§2.8–2.12, §5.D, INV-K07/C06/POL04-05/M04-05, POLA-16..22, SKN-19..29, §16 (dicatat sebagai temuan kebersihan dokumen).

## Identitas produk (dipin 11 Okt 17:3x UTC)
- commit `d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0`, tree `4bd5e1acf55f0b441d9c8f67949ee5b070eb9c41`
- head cabang `claude/new-session-deapao` = `5548ff18dedf3a2b77e50e5d2afc0e35fac56e26`; `git diff --name-only d0b9e9c2 5548ff18` = 10 berkas, semua `docs/`
- tree: src `fa7f62e2f59a…`, supabase/release `be1e91c172ff…`, supabase/migrations `8f6053bbd0bd…`, supabase/dev `88759f4fc518…`, scripts/cp7-src `e396ea69049a…`, scripts `d98ef8002750…`, .github/workflows `508e071c3436…` (135 workflow)
- paket CP6 T3 (30 berkas, MANIFEST sha256 e766fcbd…) tidak berubah sejak 10a8347

## Perubahan runtime auditor di kandidat (INDEPENDENT_SOURCE_REVIEW, 11 Okt)
`scripts/cp6_auditor_business_day.py` (+81), `cp6_auditor_modes.py` (+41/−7), `cp6_auditor_runner.py` (+14/−1), host browser `.mjs`.
- PASS → INCOMPLETE bila tanggal WIB rencana/sebelum/sesudah berbeda (lebih ketat). FAIL/COUNTEREXAMPLE/INCOMPLETE tidak diubah.
- `with_retry`: kelompok diulang SEKALI dari salinan baru bila setiap baris non-PASS berlabel rollover dan bukan cek harness
  (`harness_check_failed`), bukan hasil rusak. **Catatan auditor:** sebuah FAIL produk yang kebetulan terjadi saat ganti hari
  memenuhi `explained()` → kelompok diulang dan status akhir laporan memakai percobaan kedua. Percobaan pertama tetap
  tersimpan (`business_day_first_attempt`, berkas `<nama>_BUSINESS_DAY_FIRST_ATTEMPT`). Konsekuensi: auditor WAJIB membaca
  `business_day_retried`/percobaan pertama di setiap run; bug yang hanya muncul lintas tengah malam bisa tersembunyi di
  status akhir. Dicatat sebagai temuan alat uji (minor) + syarat pembacaan bukti. Oracle/jam produk tidak diubah (benar).
- `wib_day()` di modes membuka koneksi ke PRIMARY (bukan salinan) → tidak mengganggu `session_leaks`. `statement_timestamp()`
  dipakai (bukan `now()`), benar di dalam transaksi kelompok.

## Run independen (INDEPENDENT_NATIVE_RERUN) — dispatch REST 17:47–17:50 UTC pada ref `claude/new-session-deapao` head `5548ff18`
Ledger: `scratchpad/out/dispatch_ledger.jsonl` (disalin ke `runs/dispatch_ledger_cp7.jsonl`). 24 workflow penulis + 1 auditor-scenario (BF regresi).
Dibaca per kasus dari log, bukan warna job. Hasil: `runs/`.

### Merah pertama (disimpan apa adanya)
- `astra-cp7-timeline-reuse.yml` run 38161262099 job 114534491610 GAGAL sebelum satu kasus pun: `scripts/cp7_astra_timeline_reuse_probe.mjs:19`
  `deepStrictEqual` daftar fungsi `cp7_netting_native` — aktual memuat `source_within` dan `matching_models_within` (K7a) yang
  tidak ada di daftar harapan. Klasifikasi: STALE_TEST_SELECTOR (alat uji Astra/PR44, bukan produk). Dampak: paritas PR44
  tidak punya bukti berjalan pada kandidat ini dari workflow itu; harus ditutup lewat bukti lain (job `netting` di
  `claude-pl-native.yml`) atau penulis memperbarui daftar. Bukan bagian 15 workflow receipt penulis.

## Runtime Fable untuk kasus CP7 sendiri
`.github/workflows/fable-cp7-native.yml` (cabang audit): langkah salinan dari `claude-p19-transport.yml` d0b9e9c2, checkout produk
dipin `d0b9e9c2` + asersi tree; `audit/fable_cp7/scenarios/fable_cp7_probe.py` memasang komposisi penuh lewat pemasang kandidat
(F03+planning+baseline+supply+schedule+analysis+reminders v2), lalu menjalankan modul skenario Fable lewat runner ketat beku.
