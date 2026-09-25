# Fable — putaran 12 (pra-BC): reproduksi independen temuan "pre-existing" F1/F2 dari writer

Tanggal: 2026-09-25 17:15–17:45Z. Label: INDEPENDENT_NATIVE_RERUN (skenario sendiri, runtime `cp6-auditor-scenario.yml`, ref = cabang writer).
Oracle hanya dari kontrak (M:485 pembulatan, M:835 pembulatan kewajiban per dokumen, M:1066 ACC-DEC02 harga eceran manual, M:6632 total/per tanggal/jejak sumber)
dan keputusan owner T3 = opsi A (OWNER_CONFIRMED_TO_AUDITOR). CP6 tetap HOLD; `production_go=false`.

## 0. Konteks
- Head writer bergerak 4c61aca → 7c9d00a (probe BC 32 kasus, lokal saja) → 4b1bd66 (probe enam state ALL era BA = butir 3b handoff) → 95353aa
  (halaman BC, races/HTTP/browser BC, workflow CI BC, workflow auditor: fase `after` kini memasang BC, fase baru `pre_bc`).
- **BC belum final**: belum ada bagian handoff, belum ada tabel kasus di docs, belum ada run CI BC yang saya baca. Audit BC belum dimulai.
- Paket rilis DB (`supabase/migrations`, `supabase/release`, `supabase/rollbacks`) **identik byte** 4c61aca..95353aa. Perubahan hanya `supabase/dev/cp6_bc_t1_family.sql`,
  `scripts/cp6_bc_*`, berkas `src` BC, dua workflow. Jadi fase `after` pada 4b1bd66 dan fase `pre_bc` pada 95353aa = produk sebelum BC (dijaga kasus `XA12:BC_ABSENT`).
- Commit writer 7c9d00a menyebut dua temuan **pre-existing** dan **mengecualikan** salah satunya dari delta probe BC-nya sendiri (`STALE_F2` di `scripts/cp6_bc_probe.py`).
  Itu klaim writer (WRITER_EXPLANATION). Putaran ini mengujinya sendiri sebelum BC.

## 1. Skenario dan run
Skenario: `audit/scenarios/round12_fable/xaudit_12_f1f2.py` (rev5 sha256 `7ce9d35eab9657fc36aa3f8d7cc239d0457b1e74d523eb1018eca03aad11aafd`).
Kasus: `BC_ABSENT` (penjaga), `DETECTOR_SOURCE_AND_BASELINE` (teks fungsi dari `pg_proc`, baseline bersih), F2 lima jalur, F1 satu jalur lewat fasad nota AP.

| Run | Rev | Head | Fase | Hasil | Catatan |
|---|---|---|---|---|---|
| 36165571453 | 1 | 4b1bd66 | after | merah | cacat alat auditor: `cases()` mengembalikan dict, runner minta `[(id, callable)]`. Bukan bukti produk. |
| 36166046560 | 2 | 4b1bd66 | after | 4 PASS / 3 CE / 1 INCOMPLETE | status F2 sah; F1 INCOMPLETE karena jalur error saya tanpa savepoint. |
| 36166784262 | 3 | 4b1bd66 | after | 2 PASS / 6 CE | run detail; cek kewajiban saya salah kunci (nama mapping vs kode akun) → status rev3 tercemar; angka `accounts_delta` tetap sah. |
| 36167400464 | 4 | 4b1bd66 | after | 2 PASS / 5 INCOMPLETE / 1 CE | F1 lewat fasad asli **terbukti**; F2 gagal pada salah nama kolom saya (`triggering_material_id`). |
| **36168041413** | **5** | **95353aa** | **pre_bc** | **4 PASS / 4 COUNTEREXAMPLE, 0 INCOMPLETE** | **run beku putaran ini.** Semua run tercatat apa adanya; tidak ada relabel. |

Setup rev5: au/av/ay/az/ba/bb PASS, `bc_install` tidak ada (pre_bc). `BC_ABSENT`: marker v2.6.20bc tidak ada, fasad service BC tidak ada, fasad nota AP ada.

## 2. F2 — detektor `run_v255_material_cost_integrity_checks:MATERIAL_RECOST_GL_STATE_DRIFT` (ERROR)
Teks baseline (dari `pg_proc`): baris ini menandai setiap gerakan konsumsi (CUTTING_GROUP, MATERIAL_ADJUSTMENT_ITEM, …) yang
`|round(qty × (unit_cost − original_cost), 2) − material_cost_revaluation_state.applied_inventory_delta| > 0.01`, dengan `coalesce(applied, 0)` bila baris state tidak ada.

| Kasus (rev5) | Buku (oracle kontrak) | Detektor | Status | Mekanisme |
|---|---|---|---|---|
| CONTROL: terima 10 @10.00 (estimasi), invoice 10.005 | kewajiban −100.05 = 10×10.005 dibulatkan per dokumen ✓; persediaan 100.05 ✓ | diam | PASS | tidak ada gerakan konsumsi |
| ADJUST −3 lalu invoice 10.005 | kewajiban −100.05 ✓; persediaan 70.03 (7×10.005=70.035, selisih 1 sen dari qty×rata2, pembulatan M:485), beban 5900 +30.02; fakta v2.6.20t ada, jurnalnya cocok (V2620T_* = 0) | **+1** | COUNTEREXAMPLE | gerakan penyesuaian **tidak punya baris `material_cost_revaluation_state`** (`applied = NULL`); recost-nya dicatat mesin dokumen v2.6.20t (`material_adjustment_revaluation_facts`, target 0.02/−0.02) — detektor lama membaca tabel yang tidak ditulis mesin baru |
| ADJUST −3 lalu invoice 2.10 | kewajiban −21.00 ✓; persediaan 14.70 = 7×2.10 **tepat**; beban 6.30 = 3×2.10 tepat; fakta v2.6.20t −23.70/+23.70, V2620T_* = 0 | **+1** | COUNTEREXAMPLE | sama: `applied = NULL` vs target 23.70 |
| STACKED n=3 (pool, potong, invoice 10.005) | WIP 30.03 = 3×10.01 ✓; persediaan 0 ✓; kewajiban −30.03 ✓ | diam | PASS | applied per gerakan −0.02/0.00/−0.01 vs target −0.01: dalam batas 0.01 |
| STACKED n=10 | WIP 100.10 = 10×10.01 ✓; persediaan 0 ✓; kewajiban −100.10 ✓; 38 event revaluasi | **+1** | COUNTEREXAMPLE | satu gerakan potong `applied −0.05` vs target −0.01: **sen dokumen terkumpul di satu PO** (persis fenomena T3; owner memilih A: tidak ada batas per PO) |

Kesimpulan F2: **klaim writer CONFIRMED** — buku memenuhi oracle kontrak di kelima jalur, jejak penyesuaian ada di tabel fakta v2.6.20t dan lolos V2620T_*, tetapi detektor
v2.5.5 melapor ERROR pada dua mekanisme yang keduanya sah setelah v2.6.20t / BA W8 / T3-A. Ini **cacat detektor (pre-existing), bukan cacat buku**. Catatan penting:
1. Dampak: `run_v255_…` tidak dipanggil dari UI (`src`) dan tidak digate T2/T3 (T2 hanya membaca V2620T_* dari v267). Jadi dampaknya pada pemeriksaan operator/DB dan pada probe
   keluarga; bukan pada laporan pengguna. Tetap: sebuah guard ERROR yang salah positif harus **didisposisi tertulis**, bukan dikecualikan diam-diam di probe.
2. Aturan "≤ 0,01 per gerakan" di detektor lama **bertentangan** dengan keputusan owner T3-A (sen beberapa nota boleh terkumpul di satu PO). Penyelarasan/pensiun
   detektor ini perlu CR kecil atau catatan owner; auditor tidak menetapkan solusinya.
3. Pengecualian `STALE_F2` di probe BC writer harus dinyatakan di handoff BC sebagai temuan terbuka dengan disposisi, dan setiap kasus BC yang recost tetap mengunci
   `books = subledger` (writer sudah melakukannya) **dan** V2620T_* = 0.
4. Sub-catatan (bukan temuan): pada ADJUST+10.005 produk mengalokasikan sen dokumen 0.05 → beban 0.02 (3×0.005=0.015 dibulatkan) dan persediaan 0.03; nilai persediaan 70.03 vs
   70.035 tidak punya representasi sen; sesuai M:835 + carry BA W8. Detektor produk `MATERIAL_GL_VALUATION_MISMATCH` (toleransi 0.05) diam.

## 3. F1 — `run_v265_gudang_write_integrity_checks:contractor_issue_price_provenance_gap` (CRITICAL)
Rev5, jalur asli: fasad `public.erp_save_accessory_issue_action_v1` POST, mode MANUAL, `manual_price 3.00`, `physical_at` WIB. Baris nota terposting:
`manual_retail_unit_price 3.00`, `accessory_price_version_id NULL`, `unit_sale_price_snapshot 3.0000`. Detektor **+1 CRITICAL**.
Predikat baseline (dari `pg_proc`): `(ACCESSORY and accessory_price_version_id is null) or (bukan ACCESSORY and material_price_version_id is null)` — tidak mengenal
`manual_retail_unit_price`. M:1066 ACC-DEC02 memutuskan harga eceran manual sah. **Klaim writer CONFIRMED (pre-existing).**
Perbaikan writer di BC (`supabase/dev/cp6_bc_t1_family.sql` ~3946: menambah `and i.manual_retail_unit_price is null` pada cabang ACCESSORY) konsisten kontrak dan sempit;
baris tanpa keduanya tetap ditandai. **Diverifikasi di putaran BC**: seluruh badan fungsi v265 BC harus berbeda dari baseline hanya pada predikat itu (saya akan
mengekspor `prosrc` pre/post dan membandingkannya).

## 4. Cacat alat auditor (dicatat, tidak disembunyikan)
rev1 bentuk `cases()`; rev2 F1 tanpa savepoint; rev3 kunci kewajiban; rev4 nama kolom tabel fakta. Semua run tetap di ledger dan `audit/runs_fable/r12/`.

## 5. Yang sudah dicek dari commit writer (SOURCE_REVIEW)
- ab4ea6d: D06 dicatat verbatim (sha lampiran 42e04815…, OWNER_CONFIRMED_TO_AUDITOR), pertanyaan T3 ditulis ulang sesuai owner, kalimat lama "1 sen per PO" ditandai keliru. CONFIRMED.
- 4b1bd66: enam state ALL era BA (P01, A01 ×3, A02, W01, W03, C01 ×2) kini punya probe di `cp6_bc_probe.py` (butir 3b handoff). Baru teks; akan diuji di CI BC.
- 95353aa: workflow auditor berubah 4 baris (opsi `pre_bc`, deskripsi) + driver `cp6_auditor_scenario.py` memasang BC pada `after`. Runner/modes B1 tidak berubah.

## 6. Status
CP6 HOLD. Belum ada cacat produk baru di paket rilis; dua temuan pre-existing writer terkonfirmasi independen: F1 (diperbaiki di BC, verifikasi menyusul) dan F2 (cacat detektor
lama, butuh disposisi tertulis, belum diperbaiki). Menunggu head final BC + tabel kasus + run CI dari writer untuk putaran 12 penuh.
