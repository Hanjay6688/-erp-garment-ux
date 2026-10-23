# OW-15 — rencana rantai tahap linear (penulis A, penggabung)

Ringkas untuk owner: semua perubahan uang/stok dibuat sebagai "tahap" di atas SQL dasar yang dibekukan. Untuk paket auditor,
tahap-tahap itu dipasang berurutan dalam satu rantai, lalu satu uji pemulihan database terpakai (P21) memasang ujung rantai.
Perkiraan 20–25 run CI berurutan (sekitar 1,5–2 hari), lalu kualifikasi penuh. Tidak ada keputusan bisnis baru yang
dibutuhkan; yang dibutuhkan adalah Astra memindahkan perubahan SQL dasarnya ke tahap (lihat temuan 1).

Disusun 23 Okt 2026 dari kode di `fb3ab58f` (sesudah pembatalan OW-09 `43452c27`), hanya membaca.

## 0. Temuan yang menentukan rencana

1. **SQL dasar dibekukan; cabang B juga melanggarnya.** `scripts/cp7_full_owning_install.py:31` mengunci
   `PREDECESSOR_SQL_SHA256=e7701eaa…`, `:53-54` menolak dengan `CP7_FULL_PREDECESSOR_SQL_SOURCE_CHANGED` (terbukti: run
   39848501244 dan 39848539599 di `3c3dea91`). Gerbang sebelum setiap penggabungan harian (tanpa database):
   `PYTHONPATH=scripts python3 -B -c "import json,cp7_payment_source_owning_install as p; assert p.sources()==json.load(open('scripts/ow04-consumer-closure-qualification/SOURCE.json'))['product_sources']"`.
   `origin/astra/d17-14-produksi` (`f3a0d34d`) mengedit 9 berkas `scripts/cp7-src` yang terkunci: `alerts/alerts.sql`,
   `baseline/target.sql`, `plan-native/history-yield.sql`, `planning/{analysis-stages,baseline-source,netting,supply-source}.sql`,
   `stock-formula/{formula,materials}.sql`; semuanya masuk `predecessor_extension()`. Menggabung B apa adanya mematahkan semua
   tahap A. Hasil B sejauh ini (OW10 `b6c0411`/`4d881bf`, OW13b `efe7112`, OW16 `3f0e545`, OW14a `245b595`) dibuat di jalur
   bundle yang diedit dan tidak terbawa ke rantai.
2. **Hanya dua fungsi diubah lebih dari satu tahap, dan urutannya sudah tetap** (bagian 2).
3. **OW07 di rantai bawaan kemungkinan menggagalkan cek E01 READY di P21.** `erp.get_owner_financial_snapshot_v2` mengambil
   keyakinan data dari `erp.period_readiness_v1` (memakai `period_blockers_v1`); salinan data sudah punya periode absensi
   yang belum dibagi ke pool (`ow07/native7-70c8e91d-first-case-failure.json`: `ATTENDANCE_POOL_NOT_ACTIVE` x5).
   `cp7_p18_e01_bridge_cases.py:62,188` menuntut READY. Perbaikan di data (bagikan periode itu lewat facade Native dengan
   kebijakan fixture yang diberi label fixture), bukan melonggarkan cek.
4. **Tahap fgqc (2.21) belum mengunci pendahulu langsungnya** (kasbon); kasbon Native4 sudah lulus (`6c8be6f6`, run
   39847032024). Catat artifaknya dan kunci sebelum requalifikasi fgqc (pengetatan).
5. **Artifak pendahulu kedaluwarsa 21 Nov 2026**: Native32 `12407224140`, Native28 `12429866259`, OW06 Native10
   `12440350206` (E21). Selesaikan dan pasang ulang sebelum itu, atau simpan salinan xz di repo.

## 1. Inventaris tahap

| Folder tahap | Butir | Pendahulu | Fungsi yang diubah (jumlah jangkar) | Objek baru | Workflow | CI terakhir |
|---|---|---|---|---|---|---|
| `cp7_payment_source_owning_install.py` (dasar) | OW04 | `cp7_consumer_owning_install` | — | — | `cp7-ow04-consumer-closure.yml` | Native32 PASS (12407224140) |
| `cp7_contractor_correction` | OW05 | dasar | `erp.save_cutting_pickup_v1` (1); `cp7_cutting_correction.sewing_revision` (3); ALTER `rate_revisions` | skema + 2 RPC publik | `cp7-ow05-native.yml` | Native28 PASS; P21 `9dde276f`; Auth4 `347a1baf`; Browser2 `5e4b4c1c` |
| `cp7_contractor_guidance` | OW05b | OW05 | `blockers_v1`, `workspace_v1` | skema + 4 pembaca | `cp7-ow05b-native.yml` | Native6 PASS `176dcf38`; browser `eda58db5` |
| `cp7_supplier_transfer` | OW06 | OW05 | `post_supplier_payment`, `reverse_supplier_payment`, `reverse_journal`, `cp7_invoice.payment_detail`, `reverse_payment_locked`, `cp7_supplier_payment_correction.apply`, `run_v267_financial_truth_checks` (3), `cp7_receipt_fix.blockers`, `cp7_transaction_source.resolve` | skema 5 tabel + 2 RPC | `cp7-ow06-native.yml` | Native10 PASS `f764c508`; Auth4 `b9456b5a`; Browser2 belum |
| `cp7_kasbon_source` | 2.18 | OW06 | `resolve` (5) | `document_v1` | `cp7-ow08b-kasbon-native.yml` | Native4 PASS `6c8be6f6` |
| `cp7_fg_correction_source` | 2.21 | kasbon | `resolve` (2), `erp.reverse_qc` (5), `get_laundry_qc_workspace_v1` (4) | 2 pembaca | `cp7-ow08b-fg-correction-native.yml` | Native9 sedang jalan `2927dd25` |
| `cp7_hpp_close` | OW07 | OW05 | `period_blockers_v1`, `activate/cancel_attendance_hpp_pool_v1` | `blockers_v1` | `cp7-ow07-native.yml` | Native7 PASS `3a044782` |
| `cp7_laundry_unknown_wash` | 2.20 | OW07 | 9 fungsi `erp.` laundry/BD/HPP + `period_blockers_v1` | `prices_v1` + pemicu + 6 fungsi | `cp7-ow08b-wash-native.yml` | belum ada kasus jalan (registry image) |
| `cp7_report_credit` | OW08a | OW05 | `run_v268_financial_report_checks` (4), `_v268_…_pre_scope` (2) | `adjustment_v1` | `cp7-ow08a-native.yml` | Native6 PASS `d38f6ee6` |
| `cp7_finance_capture` | OW12a | OW05 | `report_run_unit`, `report_step`, `report_status`, `report_summary_text`, `cp7_background.run_next` | skema capture + compare | `cp7-ow12a-finance-native.yml` | 2 gagal pasang (diperbaiki), 1 registry image |
| `cp7_credit_followups` (cabang `claude/d17-14-ow04b`) | OW04b | OW05 | `cp7_credit.*` (3) | skema | `cp7-ow04b-native.yml` | belum |
| tahap daftar OW-09 (direncanakan) | OW-09 | — | 7 pembaca CP7 + `erp.get_accessory_issue_workspace_v1` | — | baru | — |
| B (9 berkas cp7-src + `cp7_ow16_status_install.py`) | OW16, OW10, OW13b, OW14a/b | bukan tahap rantai | edit badan fungsi; OW14b menambah kolom | OW16: skema `cp7_cutting_status` | `cp7-ow10/13b/14/16-*.yml` | lulus hanya di jalur bundle yang diedit |

## 2. Fungsi yang dipakai bersama

| Fungsi | Urutan wajib | Tersusun? |
|---|---|---|
| `erp.period_blockers_v1(date,date)` | OW07 → wash | Ya, hanya dengan urutan itu (wash menolak tanpa penanda OW07) |
| `cp7_transaction_source.resolve(jsonb)` | OW06 → kasbon → fgqc | Ya; OW06→kasbon terbukti Native4, kasbon→fgqc menunggu Native9 |

Tidak ada fungsi lain yang dipakai bersama. OW-09 tidak bersentuhan dengan OW12a/OW08a/OW07 (OW12a membaca
`cp7_finance.workspace`, fungsi lain di skema yang sama). OW04 memanggil `cp7_sales.cash_workspace` dengan `payment_limit=1`,
jadi jalur OW-09 tanpa kunci baru harus tetap sama persis (jadikan pembanding 319 panggilan sebagai kasus Native). Ke depan:
OW13a (B) kemungkinan mengubah `cp7_background.run_next()` yang sudah diubah OW12a, dan OW12b juga harus di atas OW12a.

## 3. Urutan rantai dan perubahan minimal per tahap

Aturan keras: himpunan beku tidak pernah berubah (semua yang dijangkau `cp7_payment_source_owning_install.sources()`); setiap
perubahan adalah folder tahap dengan SQL-nya sendiri. Jangan mengedit dokumen/workflow/berkas bersama yang dikunci tahap yang
sudah lulus; hasil baru ditulis di berkas baru. Antarmuka dari fgqc ke atas: setiap modul rantai mengekspor
`catalog, atomic, as_owner, base, function_ddl` supaya re-base cukup satu baris impor.

| # | Tahap | Perubahan | Pin/bukti dibuat ulang |
|---|---|---|---|
| 0–3 | dasar, OW05, OW06, kasbon | tidak ada | — |
| 4 | fgqc | tambah `base=…`; `native_probe.admitted()` mengunci laporan kasbon Native4 | `SOURCE.json` pendahulu → kasbon; pengambil `scripts/ow08b_kasbon_native_original.py`; langkah ambil di workflow |
| 5 | OW05b | `composition.py:12` → `cp7_fg_correction_source`; `:21-23`; `:65`; `native_probe.py:9`, `:26-30` | `SOURCE.json` (termasuk App.tsx); workflow mengambil Native10, kasbon, fgqc |
| 6 | OW04b | bangun di sini (pendahulu `cp7_contractor_guidance`) | Native asli pertamanya |
| 7 | OW08a | `composition.py:11` → `cp7_credit_followups`; `native_probe.py` | `SOURCE.json`; workflow |
| 8 | OW12a | `composition.py:15` → `cp7_report_credit`; `POSTGRES=predecessor.as_owner`; tetap `handover()` | hasil 39847548230 tergantikan |
| 9 | OW-09 | bangun langsung di atas `cp7_finance_capture` (hemat satu requalifikasi) | baru |
| 10 | OW07 | `composition.py:12` → modul OW-09; `native_probe.py` | `SOURCE.json`; workflow |
| 11 | wash | komposisi tetap (impor `cp7_hpp_close`) | `ow07_native_original` dan `ow07_original.py` |
| 12+ | tahap B (status OW16; delta perencanaan OW10/13b/14a; OW14b; OW12b; OW13a) | B mengembalikan 9 berkas cp7-src ke byte beku; editnya menjadi folder tahap di atas ujung rantai | permintaan di `KOORDINASI.md`; A menulis komposisi, B SQL dan kasus |

OW06→kasbon→fgqc di bawah karena hanya awalan itu yang sudah lulus; OW07 di atas supaya penghalang tutup bukunya tidak
mengubah kasus tahap di bawahnya. Tidak ada id kasus, angka uang atau berkas EXPECTED yang berubah; hanya ikatan pendahulu.

Perubahan urutan (keputusan integrator, 23 Okt): OW04b (followups/A/B) pindah ke ujung rantai, sesudah wash; OW08a langsung
di atas OW05b. Alasannya: fungsi yang diubah OW04b tidak beririsan dengan tahap lain, dan OW04b masih dibangun.

## 4. P21 bawaan memasang ujung rantai

- `scripts/cp7_p21_chain_adapter.py` (bentuk `cp7_p21_ow05_adapter.py`): `owner` = komposisi ujung rantai; `install` mencatat
  katalog sebelum/sesudah dan `seeded_private_rows` semua tabel tahap; `rollback_preuse` dalam `atomic`: verifikasi, kunci
  semua tabel privat cp7_* NOWAIT, penjaga "sudah dipakai" global sebelum DDL apa pun
  (`CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE`), lalu `owner.rollback_preuse`, lalu perbaikan
  `v_customer_receivables` yang sama dengan `cp7_p21_ow05_adapter.py:43-65`.
- `scripts/cp7_chain_restore.py` (salinan `cp7_ow05_restore.py`): `VERSION` baru; telusuri `state['predecessor']` sedalam DEPTH
  tetap sampai `sources == cp7_contractor_correction.composition.sources()`; harapan pulih: 22 kelompok katalog sama, semua baris
  dan sequence sama, hanya GUARD sensus OW04 yang diikat ulang, 5 kontrol penolakan tetap.
- `scripts/cp7_p21_current_chain_rehearsal_probe.py` (salinan probe OW05). Pengetatan: cek AR lama dari 2/3/1 menjadi
  semua `('CRITICAL',0)` dan `CP7_CUSTOMER_CREDIT_REPORT_UNPROVEN`=0; `docs/cp7/d17-14/ow04/p21-36a6b880-readiness-boundary.json`
  tetap sebagai riwayat. `CHAIN_STEPS`: OW06 transfer 400+600 lalu pulih, ulang satu efek, balik seluruhnya; kasbon/fgqc
  `resolve` sama; OW08a 0/0/0; OW12a capture tersegel sama dengan laporan keuangan; wash harga belum diketahui → tutup tertahan
  → harga diisi sekali → tertahan lepas; B pembacaan status sama. Bila temuan 3 benar, persiapan pool absensi sebelum E01.
- Berkas EXPECTED lama tidak berubah; baru: `scripts/chain-p21-qualification/{SOURCE.json,EXPECTED_CHAIN_STEPS.json,README.md}`.
- Workflow `.github/workflows/cp7-chain-p21.yml` (salinan `cp7-ow04-final-p21.yml`, batas waktu 120 menit).
- Urutan run (berurutan, tiap run butuh id artifak pendahulunya): fgqc → OW05b → OW04b → OW08a → OW12a → OW-09 → OW07 → wash →
  tahap B → P21 rantai → browser/Auth yang pinnya berubah → kualifikasi penuh (sekitar 117 workflow + CP6 penuh, dengan 21 gagal
  CP6 dan 4 kasus layar tetap ditampilkan gagal). Perkiraan: tahap A 8–13 run, tahap B 4–8, P21 2–3.

## 5. Risiko

- Lingkup dan jadwal B (terbesar): 9 edit cp7-src harus jadi tahap dan suite B dijalankan ulang di jalur itu; sampai itu, cabang
  B tidak boleh digabung ke integrasi apa adanya.
- OW07 dan E01 READY (temuan 3): mengenai semua suite yang memasang ujung rantai dan menuntut READY. Bila kontraktor seed
  tidak punya kebijakan pool HPP, `ATTENDANCE_POOL_POLICY_MISSING` akan menahan; pakai kebijakan fixture berlabel, bukan angka owner.
- Penjaga rollback wash menghitung baris cuci gagal PENDING/tanpa tarif; pastikan salinan data tidak punya, atau P21 menolak.
- Kedaluwarsa artifak 21 Nov 2026 (E21).
- Pin berkas bersama (App.tsx, `CHECKPOINT.json`, `PROGRESS.md`) patah di penggabungan harian; pin ulang hanya saat tahap itu
  dikualifikasi ulang.
- Memajukan pin dasar: tidak selama D17-14. Hanya lewat langkah "fold" terpisah sesudah P21 rantai dan kualifikasi penuh lulus
  (cp7-src dilipat mekanis dari katalog ujung rantai, bukti `install(folded)==install(base+chain)` di 22 kelompok, pin baru, ulang
  semua suite dengan oracle dan id kasus sama, pin lama tetap sebagai riwayat, audit independen sebelum jadi bawaan).
