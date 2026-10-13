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

## Hasil baca per kasus run writer yang saya dispatch ulang (12 Okt 02:xx UTC) — `runs/SUMMARY.md`
56 job dibaca per kasus (log, bukan warna job): 2.585 baris kasus: PASS 2.493, CONTROL_PASS 39, COUNTEREXAMPLE 20, INCOMPLETE 12,
DATE_POLICY_REVIEW_REQUIRED 12, MATCH 8, FAIL 1. Tidak ada `business_day_rollover`/`RERUN_FROM_FRESH_COPY` di satu pun log
(kontrol pergantian hari tidak terpicu; percobaan pertama = percobaan akhir).
- 15 workflow kualifikasi penulis + f03-full + prefreeze-ui: semua kelompok PASS penuh, hitungan sama dengan deklarasi
  (K4 17, K6 10, K3 19, K2 10, PL5 20, plan v2 22, report v2 20, reminder v2 16, AI v2 9, staged 14, transport 15, scale 5,
  attention 286 [181/40/29/36 + 3 admisi], plan39 43, netting 83, supply 53, schedule 71, model 32, P13 12, nota 40, penerimaan 43,
  payroll P12 3 job, fabric-physical 21, fabric-recipe 13, fabric-rule 11, rule-lifecycle 16, e01 9, P18 full cycle 2, P21 gladi 2 job,
  supplier payment create 10 / correction 23, f03-full p09 132, p10 34, p11 64, p12 90, p13 50, customer_refund 10, cash_installments 61,
  supplier_credit 5, prefreeze_ui 31 + 2 INCOMPLETE diagnostik legacy (LEGACY_RUNTIME_OBSERVATION_ONLY, sama dengan 2 Okt).
- Regresi CP6 pada kandidat: T2 326+AS34 multiset status IDENTIK dengan beku r16 (CONTROL_PASS 39, DPRR 12, MATCH 8, COUNTEREXAMPLE 20,
  INCOMPLETE 5 di AO_TRIAL/NEW_CASES); AR 174 + ACCESSORY_CONNECTED_ZERO INCOMPLETE (BC_FREE_REQUIRES_POLICY, SUPERSEDED_BY_OWNER_RULE D11)
  sama; AT 16/AU 15 + balapan PASS; T3 rollback cycle PASS (30 berkas, penolakan urutan, siklus BF/BE/BD); T3 package capture pins sama;
  auditor-scenario BF (xaudit_14_bf) 4/4 + browser 2/2; CodeQL hijau.
- Merah yang BUKAN temuan produk:
  1. `astra-cp7-timeline-reuse` — STALE_TEST_SELECTOR (daftar fungsi probe Astra basi: K7a `*_within`). Paritas PR44 tanpa bukti di kandidat ini dari workflow itu.
  2. `cp6-release-readiness` 3 job — penjaga `READINESS_SCOPE` menolak cabang ini (workflow terikat cakupan berkas lama) — NOT_APPLICABLE.
  3. `cp6-final-boundary-audit` — `assert not git rev-list --merges BASE..HEAD` (cabang memiliki merge commit) — NOT_APPLICABLE.
  4. `cp6-t3-release-package` job runtime: WRITER_PACKAGE_BF_NATIVE 103/104; FAIL `VENDOR_REG:D12:CLAIM_CREDIT_DAILY_OLDER_INVOICE`
     hanya pada cek `reject_after_invoice = july>june and june_end<july` — fixture `today-100 hari` (cp6_bd_probe.py:1411-1416,1458):
     pada 11 Okt 2026 `june`=1 Jul, `june_end`=31 Jul, `july`=31 Jul → cek palsu. 12 cek bisnis lain PASS. POLA-21 (fixture jam dinding), temuan alat uji penulis (minor).
  5. `cp6-t3-release-package` job browser: 4 INCOMPLETE lama (READINESS finance note ×2: UI memanggil `erp_cp7_get_recost_queue_v1` yang tidak ada di paket CP6 saja; SALES_MANUAL_13 ×2 selector basi/PRE-05). Implikasi nyata: UI kandidat tidak boleh dipasang di atas paket CP6 saja tanpa CP7.

## Run Fable sendiri (12 Okt UTC) — semua dibaca per kasus
- smoke 38162239881 (push) 8/8 PASS; ulang 38195346649 8/8 PASS (job merah = alat: ringkasan driver; diperbaiki).
- core 38196137312: native 4 PASS + 1 INCOMPLETE (alat, AI reset read-only), balapan: F01 v1→v2 PASS, F01 v2→v1 PASS, BACKUP_VERIFY_UNDER_LIVE_WRITES PASS (IDLE ticks), BACKUP_SCRATCH_DROPS_FOREIGN_DB **FAIL** (F-OPS-01), CLEANUP_LOCK_VS_RUNNING_STEP **FAIL** (F-OPS-02, step 8,01 s, unit_attempts 1).
- core ulang native 38196731514: 5/5 PASS termasuk AI_BRIEF_RUNS_READ_ONLY; job hijau; cp6_restored true.
- ui browser 38196797717: LANDING_NO_FABRICATED_FIGURES desktop/mobile **FAIL** (F-UI-01, 7 angka karangan), GUDANG_SEES_NO_FINANCE_NAV PASS.
Laporan: `AUDIT_FABLE_d0b9e9c2.md` v1.0 — vonis HOLD dengan syarat §2.

## Uji ulang 7a0b4a90 (12–13 Okt UTC) — selesai
- Kasus Fable tidak diubah: core 38330288917 (5 native + 5 balapan + 1 HTTP baru PL-5 owner-only) 11/11 PASS; smoke+UI 38330296574 11/11 PASS
  (termasuk LANDING_NO_FABRICATED_FIGURES desktop/mobile). F-OPS-01/02 dan F-UI-01 DITUTUP dengan oracle sendiri.
- 17 workflow penulis didispatch pada head 5656f072 (tree 7a0b4a90): 50 job dibaca per kasus, 1.806 baris: 1.804 PASS, 2 INCOMPLETE legacy prefreeze
  (sama dengan sebelumnya), 0 FAIL/COUNTEREXAMPLE, 0 pengulangan hari bisnis. p19-scale5 5/5 PASS (selesai 02:16 UTC).
- Supplier Payment Create (115079091992): 10/10 kasus PASS, label grup INCOMPLETE karena `complete_boundary_restored=false` di akhir grup harness;
  probe Fable 38332667386 (kasus penulis diapit capture/compare) → boundary_equal & public_equal true. Klasifikasi AUDITOR_TOOL belum terjelaskan; syarat §3.1.
- PR44: probe Astra pada tree 7a0b4a90 (38330587114) PARITY_PASS 595/595, mutations_caught 2, benchmark 13–42 %; netting 83/83; review sumber probe → DITERIMA oleh Fable.
- F-PAY-01 ditarik (salah kutip versi fungsi; v2.6.20ac/ap sudah WIB). F-DOC-01: panduan 7a0b4a90 = PR #42 + 9 baris tambahan, tidak ada yang hilang.
- Laporan: `AUDIT_FABLE_7a0b4a90_RETEST.md` v1.0 — LULUS DENGAN SYARAT (§3). Bukti: `runs/retest_7a0b4a90/`.
- 2026-10-13T05:53:51Z: owner menegaskan keputusan 12 Okt dan menerima vonis bersyarat; keputusan D13-1..3 dicatat di OWNER_DECISIONS_TO_AUDITOR_20261013.md.
  Menunggu hasil penulis (diagnosis selisih + 3 run bayar supplier; gladi jadwal) untuk laporan v1.1. Tidak ada run ulang audit.

## Putaran silang 1 (13 Okt, 14:30 UTC) — kandidat ae0214ad (produk = 7a0b4a90; 12 berkas alat berubah)
- Identitas diperiksa (commit, tree, diff produk kosong, 12 berkas). Review sumber A1 (backup OID), A2 (diagnosis), A3 (gladi), A6, A7, A8 selesai → draft v1.1.
- Dispatch 14:33–14:36 UTC: penulis p19-transport 38414371682, supplier-payment-create ×3 (38414385732/38414401092/38414415980), p08-shell 38414431084,
  pl-native 38414446165 (head 856833dc, alat identik ae0214ad); Fable xc1 38414814884, core 38414828309, smoke+ui 38414843823 (product_ref=ae0214ad).
- Kasus Fable baru: scenarios/fable_cp7_xc1.py (4 balapan + 1 native). Temuan minor baru F-OPS-05 (tanda polos bisa disalin) menunggu bukti.
