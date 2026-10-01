# Fable — Putaran 13: verifikasi klaim "CP6 CLOSED" (auditor pengganti, 29 Sep)

Tanggal: 2026-10-01 (UTC). Status dokumen: **FINAL** (semua run selesai dan dibaca per kasus). Tidak ada relabel; run gagal dicatat apa adanya.

## 0. Apa yang diuji dan kenapa

Owner memilih opsi **(a)**: Fable menguji sendiri klaim penutupan CP6 yang ditulis auditor pengganti
(`audit/cp6-cp7-acceptance-20260929`, "CP6 CLOSED — independently accepted for contract scope; production_go=false").
Klaim itu bersandar pada run penulis untuk D07, D09, F3. Putaran ini mengulang gerbang dan skenario milik Fable sendiri
pada kandidat yang sama, lalu menambah kontrol D07.

Kandidat yang diuji (dipin oleh `audit/runs_fable/r13/pin_head.sh`):

| Hal | Nilai |
|---|---|
| Head cabang penulis | `10a834712e515af86c6d8baa89bbe40cff9793e3` (29 Sep) |
| Produk (src, paket rilis, migrasi) identik dengan | `434b182` (`git diff --quiet 434b182 10a8347 -- src supabase/release supabase/migrations` = kosong) |
| Paket T3 | 30 berkas `.sql` + `MANIFEST.json`; sha256 gabungan `e766fcbd…b27b` |
| Inti runtime auditor (runner/modes/probe) | tidak berubah sejak `95353aa` |
| Driver skenario + workflow | tidak berubah sejak `10a8347` |
| Perbaikan yang diklaim ada di produk | D07 retune `af00dd1` (26 Sep), F3/D08 `21dd3d7`, D09/D10/D11 `72d3544`, BD selesai `30fd82f`, BE, BF |

Oracle tetap: M/P/A, C0 §1–8, C6 rev4, dan keputusan owner di `OWNER_DECISIONS_CP6_DRAFT.md`.

## 1. Gerbang (dispatch API, ref = cabang penulis, head 10a8347) — INDEPENDENT_NATIVE_RERUN

| Gerbang | Run | Hasil | Catatan |
|---|---|---|---|
| T2 regresi gabungan | 36802914343 | **success** (3 job: AT16+AU15 & races; 326+AS34; AR174 & races) | `ACCESSORY_CONNECTED_ZERO` tetap EXPECTED_CHANGE (kasus pengganti penulis); tidak ada kasus beku yang direlabel |
| T3 paket rilis (30 berkas) | 36802922323 | **success** (3 job: paket+browser AU/BF; AC..BF+advisors+restore drill; pins dibanding ulang) | paket yang dipasang = yang di-commit |
| T3 rollback AC..BF | 36802929871 | **success** | siklus pasang–copot pada baseline hosted-faithful |
| CodeQL (js/ts, python, c-cpp, actions) | 36802937437 | **success** | |

## 2. Regresi skenario Fable (fase `after`, head 10a8347) — INDEPENDENT_NATIVE_RERUN

| Skenario | Run | r13 | r12 (pembanding) | Putusan |
|---|---|---|---|---|
| xa1 | 36802945018 | 6 PASS | 6 PASS | sama |
| xa2 | 36802952298 | 7 PASS | 7 PASS | sama |
| xa7 | 36802959475 | 14 PASS | 14 PASS | sama |
| xa8 | 36802968654 | 14 PASS + **2 COUNTEREXAMPLE** (`W8_THREE_RECEIPTS_INVOICE_UP`, `W8_THREE_RECEIPTS_DIRECT_DOWN`) | sama 2 CE | **beku** sejak r11/r12: sen dokumen per-PO, owner T3 = A (bukan cacat). Tidak direlabel. |
| xa9 | 36802978021 | 5 PASS | 5 PASS | sama |
| open_1 | 36802987554 | 15 PASS | 15 PASS | sama |
| C0 | 36802996229 | 26 PASS + **1 INCOMPLETE** (`G8C0:AS:ADJUSTMENT_DATE:False`: `permission denied for schema erp` saat memanggil `erp.get_owner_financial_snapshot_v2`) | sama 26+1 | **cacat skenario auditor** (peran sesi salah saat observasi), bukan produk; sudah tercatat sejak r12; dibiarkan apa adanya |
| xaudit_12_f1f2 rev5 | 36803005576 | 9 PASS + **1 FAIL** (`XA12:BC_ABSENT`) | 6 PASS + 1 FAIL + 3 CE | lihat §3 |
| xaudit_12_f4 | 36803013529 | 5 PASS | 5 PASS | F4 tetap terperbaiki |

## 3. Temuan lama: status di kandidat penutupan

| Temuan | Bukti r13 | Status |
|---|---|---|
| **F1** (catatan harga manual ditandai detektor) | `XA12:F1_MANUAL_PRICE_NOTE_LINE` PASS (lewat fasad BC) | **TERPERBAIKI, dikonfirmasi natively** (sama seperti r12) |
| **F2** (detektor `MATERIAL_RECOST_GL_STATE_DRIFT` basi) | r12: 3 COUNTEREXAMPLE (`F2_ADJUST_THEN_LATE_INVOICE`, `_EVEN`, `F2_STACKED_INVOICE_N10`). r13 (dengan D07 `af00dd1`): **semua 5 jalur F2 PASS**, detektor diam pada buku yang tepat | **TERPERBAIKI per D07, dikonfirmasi natively** |
| **D07 kontrol** (alarm diretune, bukan dimatikan) | run 36803212344: `D07_SILENT_ON_EXACT` PASS (drift 0 pada n=3 bertumpuk dan penyesuaian+invoice telat); `D07_NEG_STATE_TAMPER` PASS (+0.05 pada `applied_inventory_delta` → drift **+1** selama savepoint, **0** setelah rollback); `D07_NEG_FACT_TAMPER` **INCOMPLETE**: tabel `material_adjustment_revaluation_facts` menolak UPDATE (`42501 MATERIAL_ADJUSTMENT_REVALUATION_FACT_APPEND_ONLY`), 0 baris diubah, drift tetap 0 | Alarm **masih hidup** (kontrol negatif via state +1). Kontrol via fakta **tidak bisa dijalankan** karena fakta append-only — ini bukan cacat; justru bukti fakta tak bisa diubah. Dicatat INCOMPLETE apa adanya, sesuai docstring skenario. |
| `XA12:BC_ABSENT` FAIL | penjaga rev5: FAIL **sesuai desain** bila BC terpasang (BC memang ada di paket) | bukan temuan |
| **F4** (BB: pelunasan dari uang muka `reversible` NULL) | 3 kasus PASS | **TERPERBAIKI** (coalesce di BC) |
| **F3 / D08** (regex UUID ketat) | sumber `src/accessoryIssue.ts`, `src/laundryQcModel.ts` di 10a8347 = regex kanonik (dibaca ulang putaran 12b, `21dd3d7`) | INDEPENDENT_SOURCE_REVIEW; tidak ada uji browser khusus r13 |
| **D09** (ACC-C12 kunci custody baru → identitas sumber) | probe BD penulis dijalankan di workflow pin Fable: run 36803064486 `after` **41/41 PASS**, `before` success, mismatch {} | INDEPENDENT_NATIVE_RERUN (PLAN penulis, workflow + ref auditor dipin) |

## 4. Probe keluarga (PLAN penulis dijalankan ulang pada workflow pin Fable, ref auditor 10a8347)

| Keluarga | Run | before | after | Catatan |
|---|---|---|---|---|
| BD | 36803064486 | success | success, **41/41 PASS** (termasuk `D09:ACC_C12_SOURCE_IDENTITY`, `D10:VARIANCE_BY_BILLING_SOURCE`) | `bd_after.json` |
| BE | 36803064466 | **failure** (rev1) → rerun job gagal: **success, 16 NO_ROUTE** (mismatch {}) | success: **16/16 PASS** (mismatch {}) | rev1 `before` jatuh **sebelum satu kasus pun jalan**: `install_at → install_as → aq.change('install')` ditolak paket AS: `PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE` (penjaga "DB harus tertutup & kosong sesi"). Rantai pasang yang sama lolos di BD before/after dan BE after → **balapan sesi sisa saat pemasangan, bukan produk**. Satu rerun (jatah tunggal) dipakai. |
| BC | 36803064370 (rev1) **failure – cacat alat auditor** (re-pin mengganti semua sha 40-hex termasuk `supabase/setup-cli@…`); dibangun ulang `96bd871` → run 36803602974 | success: 9 PASS + 38 NO_ROUTE + 3 COUNTEREXAMPLE (persis PLAN pra-BC, `expectation_mismatch` {}) | success: **50/50 PASS** (45 PLAN penulis + 5 kasus FAB Fable: fill-sebelum-terima ditolak, use>post ditolak, bentuk qty tak sah ditolak, reverse ganda ditolak, sidik jari badan v265/v255) | `bcpin_before.json`, `bcpin_after.json` |

Mode balapan + HTTP + browser penulis (`cp6_{bc,bd,be}_modes.py` + `.mjs`) dijalankan ulang oleh auditor lewat `cp6-auditor-scenario.yml` (fase after) — INDEPENDENT_NATIVE_RERUN atas skenario penulis:

| Keluarga | Run | Hasil |
|---|---|---|
| BC | 36803221110 | **18/18 PASS** (11 races, 2 HTTP, 5 browser) |
| BD | 36803230431 | **20/20 PASS** (9 races, 3 HTTP, 8 browser) |
| BE | 36803238529 | **17/17 PASS** (9 races, 2 HTTP, 6 browser) |

## 5. Putusan Fable atas klaim "CP6 CLOSED"

**Klaim auditor pengganti (29 Sep) TERVERIFIKASI untuk lingkup kontrak CP6 pada produk `434b182` (head alat `10a8347`)**, dengan catatan di bawah.
`production_go` tetap **false** (bukan wewenang auditor; paket belum dipasang ke hosted).

Yang kini berdiri di atas bukti **Fable sendiri** (bukan lagi hanya run penulis):

1. Empat gerbang (T2, T3 30-berkas, rollback, CodeQL) hijau pada head yang sama.
2. Sembilan skenario regresi Fable identik dengan putaran 12; tidak ada hasil beku yang berubah atau direlabel.
3. F1, F2 (via D07), F4: terperbaiki dan dikonfirmasi natively. Alarm D07 hidup (kontrol negatif +1), dan tabel fakta recost terbukti append-only.
4. D09/D10 (BD 41/41), BC 50/50 (termasuk 5 kasus Fable), BE 16/16 — PLAN penulis dijalankan pada workflow dan ref auditor yang dipin, bukan run penulis.
5. Mode balapan/HTTP/browser penulis BC/BD/BE: 55/55 lewat runtime auditor.

Yang **tidak** diuji Fable di putaran ini (dinyatakan apa adanya):

- F3/D08: hanya tinjauan sumber (regex kanonik di 10a8347); tidak ada uji browser khusus. Risiko rendah (validasi format, bukan keamanan akses — per owner D08).
- BF (rentang SKU komersial, kredit vendor, riwayat konversi) dan CP7: di luar lingkup gerbang kontrak CP6 yang Fable pegang; hanya tercakup oleh gerbang T3 (job "AU and BF browser flows" success) dan oleh retest auditor pengganti. Tidak ada skenario Fable untuk BF.
- D11 (nilai kebijakan) dan GBD-03 (representasi klaim laundry lama): masih **terbuka di sisi owner**, bukan cacat produk.

Hasil non-PASS yang dibiarkan apa adanya (tidak satu pun cacat produk baru):

| Hasil | Klasifikasi |
|---|---|
| xa8 2 COUNTEREXAMPLE (W8 tiga nota) | beku; owner T3 = A |
| C0 1 INCOMPLETE (`permission denied for schema erp`) | cacat skenario auditor, sejak r12 |
| f1f2 `BC_ABSENT` FAIL | penjaga, sesuai desain |
| d07 `D07_NEG_FACT_TAMPER` INCOMPLETE | fakta append-only; kontrol tak bisa dijalankan |
| BE pin rev1 `before` failure | balapan sesi saat pemasangan AS; rerun tunggal lolos |
| BC pin rev1 failure | cacat alat auditor (re-pin sha); dibangun ulang |

Label: semua baris §1, §2, §4 = INDEPENDENT_NATIVE_RERUN; F3 = INDEPENDENT_SOURCE_REVIEW; D07–D11/UI-01 = OWNER_CONFIRMED_TO_AUDITOR (tertulis di `OWNER_DECISIONS_CP6_DRAFT.md`).
