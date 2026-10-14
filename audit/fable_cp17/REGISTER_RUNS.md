# Register run Fable — putaran cp17-20261014 (§16.7)

Semua run di bawah didispatch oleh Fable lewat REST (`dispatch_any.py`), catatan `FABLE_CP17 …`. Ledger lengkap (run id,
head_sha, waktu) disalin dari `dispatch_ledger.jsonl` ke `runs/cp17/dispatch_ledger_cp17.jsonl` saat laporan dikunci.
Ref writer: `claude/new-session-deapao` @ `00b0eb24` (= kandidat `0b7049d9` + docs). Ref Fable: `audit/fable-cp1-7-0b7049d9-20261014`
dengan `product_ref=0b7049d9`. Tidak ada run/artifact milik peserta lain yang dibuka.

## B1 — Regresi CP6 (T2/T3/qualification/probe) di ref writer `00b0eb24` (produk = 0b7049d9)

Status dibaca per kasus dari baris JSON log (bukan warna job). Pembanding = run putaran XC1 (ae0214ad, job 11453451xxxx) yang pada XC2 sudah dinyatakan identik dengan multiset beku r16. Rerun: tidak ada.

| Run / job | Workflow / job | Hasil per kasus | Pembanding | Label |
|---|---|---|---|---|
| 38522008302 / 115713634390 | cp6-t2-regression / AR 174 + races | AR_SEQUENTIAL PASS 145 + INCOMPLETE 1 (`ACCESSORY_CONNECTED_ZERO`: `BC_FREE_REQUIRES_POLICY` ERP-DEC02), AR_SUPERSEDING PASS 1, AR_CONCURRENCY PASS 28 | multiset per-kasus **identik** (176 = 176, 0 selisih) | INDEPENDENT_NATIVE_RERUN; INCOMPLETE = SUPERSEDED_BY_OWNER_RULE (D11) |
| 38522008302 / 115713634650 | cp6-t2-regression / Original 326 + AS 34 | BUSINESS PASS 179 + CONTROL_PASS 39 + DATE_POLICY_REVIEW_REQUIRED 12; IMPORTS 31; VALUES 65; NEW_CASES PASS 25 + COUNTEREXAMPLE 8 + INCOMPLETE 1; T2_APPROVED_ORACLE MATCH 8; T2_CALENDAR_POLICY COUNTEREXAMPLE 12; AO_TRIAL PASS 8 + INCOMPLETE 4; APPROVED_ORACLE_B 5; T2_C0_ORACLE 25 | **identik** (428 = 428, 0 selisih) | INDEPENDENT_NATIVE_RERUN; COUNTEREXAMPLE/INCOMPLETE = FROZEN_CP6_DISPOSITION (r16, D11) |
| 38522008302 / 115713634794 | cp6-t2-regression / AT 16 + AU 15 + races | AT 16 PASS, AT races 4, AU 15, AU races 6 | **identik** (41 = 41) | INDEPENDENT_NATIVE_RERUN |
| 38522017994 / 115713662953 | cp6-t3-release-package / committed package | T3 `ALL_STAGES_INSTALLED`; gate installed/primary_unchanged/backup_restore_drill/security_advisors/writer_runtime semua true; WRITER_PACKAGE_BF_NATIVE 104 PASS; AUDITOR_RACES_PACKAGE 26 PASS; AUDITOR_HTTP_PACKAGE 9 PASS | sama dengan XC1 | INDEPENDENT_NATIVE_RERUN |
| 38522017994 / 115713663162 | cp6-t3-release-package / pins captured | T3 `ALL_STAGES_INSTALLED`, gate 4/4 true, primary_unchanged true | — | INDEPENDENT_NATIVE_RERUN |
| 38522017994 / 115713663119 | cp6-t3-release-package / browser | 27 PASS + 4 INCOMPLETE (READINESS ×2 = F-UI-02 legacy; SALES_MANUAL_13 ×2 retired D13-9c) — lihat RED_CLASSIFICATION | sama dengan XC1/XC2 | ACCEPTED_BY_DECISION |
| 38522026931 / 115713691756 | cp6-t3-rollback | 152 objek; semua `status: PASS` (penolakan negatif = PASS yang diharapkan: `*_ROLLBACK_PLATFORM_OR_SUCCESSOR`, `*_POST_USE_ROLLBACK_REFUSED` AC..BF, `PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE`); alignment `ALIGNED_PER_OBJECT`, `PASS_ALIGNED_CHAIN_TO_AB` | setelah normalisasi uuid/sha/tanggal: **identik** kecuali `run_identity` | INDEPENDENT_NATIVE_RERUN |
| 38522044340 / 115713748861 | cp6-auditor-scenario / self-test B1 | `SELFTEST_PASS`: 6 pelanggaran yang disuntik (status di luar kosakata, hasil bukan dict, commit di koneksi kedua public/erp, advisory lock tertinggal, sesi kedua terbuka) **terdeteksi** sebagai INCOMPLETE; duplicate id ditolak; commit dalam grup → `AUDITOR_CASE_ENDED_GROUP_TRANSACTION` | — | AUDITOR_TOOL (runtime auditor bekerja) |
| 38522044340 / 115713749452 | cp6-auditor-scenario / scenario | `RUN_COMPLETE`: cases 1, races 1, http 1, browser 2 — semua PASS | — | INDEPENDENT_NATIVE_RERUN (sampel) |
| 38522054629 / 115713780247 | cp6-g01-baseline | `ALIGNED_PER_OBJECT`; constraints/views/sequences/schema/capsules equal = true | — | INDEPENDENT_NATIVE_RERUN (baseline hosted-faithful; hanya baca metadata hosted yang sudah tersimpan, tidak menyentuh hosted) |
| 38522195974 / 115714225280 | cp6-s06-close-probe | Probe historis **AUD-S06 di AU beku** (checkout dipin ca7f0955/c6b0e4fb/25fa4736/1bdca376; runtime 690 objek era AN, bukan 0b7049d9): AS_IS CONTROL_PASS; PENDING/RUNNING/FAILED_RETRYABLE/FAILED_EXHAUSTED → COUNTEREXAMPLE (close `CLOSED` saat laporan `RECALC_PENDING`), `REVIEW_COMPLETE` | sama dengan observasi AUD-S06 asli (`docs/cp6-au-r1-handoff.md` §AUD-S06) yang kemudian ditutup oleh AW (close readiness engine, `docs/cp6-aw-design.md`) | LEGACY_RUNTIME_OBSERVATION_ONLY — bukan temuan 0b7049d9; penutupannya diuji di AW after (baris berikut) |
| 38522248192 / 115714394244 | cp6-av-qualification / Original 326 + AS 34 | BUSINESS PASS 179 + CONTROL 39 + DPRR 12; IMPORTS 31; VALUES 65; NEW_CASES PASS 34 | konsisten dengan T2 | INDEPENDENT_NATIVE_RERUN |
| 38522248192 / 115714394528 | cp6-av-qualification / AV rev2 probe before (AU beku) | AV_CASES_BEFORE COUNTEREXAMPLE 8 + CONTROL 8 + N/A 18; RACES_BEFORE 3 PASS + 1 CE; FOUND_RACES_BEFORE 2 PASS + 2 CE; AU 15, AT 16 PASS | before = demonstrasi cacat pada predecessor, sesuai desain probe | GUARD_BY_DESIGN (before) |
| 38522248192 / 115714394617 | cp6-av-qualification / AV rev2 probe after | AV_CASES_AFTER PASS 23 + CONTROL 11; AU 15; AT 16; RACES 4; FOUND_RACES 4 — semua PASS | — | INDEPENDENT_NATIVE_RERUN |
| 38522248192 / 115714394562, 115714394619 | cp6-av-qualification / AR 174 + AV cycles; AT+AU | AR_SEQUENTIAL 146 + AR_CONCURRENCY 28 PASS; AT 16+4, AU 15+6 PASS | — | INDEPENDENT_NATIVE_RERUN |
| 38522090695..38522171091 (9 run × 2 job) | cp6-{aw,ax,ay,az,ba,bb,bc,bd,be}-t1-probe | **after**: AW 13 PASS + 3 CONTROL + 1 OBSERVED (`DISCOVERY:SEED`) + 8 races PASS; AX 20 PASS + 1 OBSERVED (`AX:BACKDATED_OBSERVATION`, catatan penulis: tanggal fisik tertutup dicakup iterasi berikut) + 12 races; AY 8; AZ 29; BA 61; BB 52; BC 45; BD 41; BE 16 — **0 FAIL/COUNTEREXAMPLE/INCOMPLETE pada after**. **before**: AW CE 4 (P01 reverse-after-close, S06 ×3) + N/A 10 + OBSERVED 2 + CONTROL 1; AX N/A 21; AY CE 4 + PASS 4; AZ CE 29; BA CE/NO_ROUTE (lihat file); BB NO_ROUTE 48 + CE 2 + PASS 2; BC NO_ROUTE 34 + CE 3 + PASS 8; BD NO_ROUTE 39 + CE 2; BE NO_ROUTE 16 | before = cacat pada predecessor (diharapkan); after = perbaikan terpasang | INDEPENDENT_NATIVE_RERUN (after); GUARD_BY_DESIGN (before) |
| 38522063143 / 115713817825 | cp6-full-schema-validation / audit-scope | gate `RERUN_REQUIRED: change outside the pinned audit/AD boundary` → `full=false`, job lanjutan **dilewati** | — | NOT_APPLICABLE (gate identitas historis; tidak menguji 0b7049d9) |
| 38522275401, 38522284999, 38522293993, 38522302446 | cp6-{ag,ah,ai,ad} review-scope | semua skrip scope (`cp6_*_scope.py`) assert gagal (merge-base/merges) → output false → job lanjutan dilewati | — | NOT_APPLICABLE (gate identitas historis) |
| 38522428512 / 115714981499 | AUDIT/fable/cp7-native / fable_cp7_smoke @ product_ref 0b7049d9 | native 5 PASS, races 1, http 2, browser 3 — PASS; `cp6_restored: true` | sama dengan XC2 | FABLE |

Catatan B1: `cp6-t3-aligned-install` (merah) → `runs/cp17/AC_VIEW_MISMATCH.md`. Job "hijau" kelas gate (audit-scope, review-scope) **tidak** dihitung sebagai bukti lulus. OBSERVED pada AW/AX after adalah kasus observasi berlabel penulis, bukan PASS; dicatat di daftar belum-diperiksa laporan.

## B2 — Regresi CP7 (14 workflow penulis) di ref writer `00b0eb24` (produk = 0b7049d9)

Semua job dibaca per kasus; pembanding = run putaran retest/XC1 (job 1507xxxxxxx / 1535xxxxxxx) yang pada XC2 dinyatakan identik dengan beku. Hasil: **multiset per-kasus identik di 26/26 job berkasus**; 0 FAIL/COUNTEREXAMPLE/INCOMPLETE produk; `cp6_restored: true` dan `advisor_gate: true` di setiap SUMMARY; tidak ada `business_day_retried: true`.

| Run | Workflow / job | Hasil per kasus | Pembanding |
|---|---|---|---|
| 38521746469 | claude-p08-physical: attention284, analysis152, fabric13-successor, fabric-physical21, plan39 | ATTENTION 3+181 PASS, races 40, http 29, browser 36 (289); ANALYSIS 107/20/12/14 (153); FABRIC_RECIPE 8/2/1/2; FABRIC_PHYSICAL 16/2/1/2; PLAN39 (lihat file) — semua PASS | identik |
| 38521756257 | claude-p12-payroll: attendance-write, roster, payroll-review | 81 / 64 / 43 kasus, semua PASS (NOTA_SOURCE 5, NOTA 7, PAYROLL_REVIEW 4, P09 admission, races, http, browser) | identik |
| 38521765759 | claude-p13-finance | REPORT_NATIVE 8, races 1, http 1, browser 2 — PASS | identik |
| 38521775206 | claude-p18-fabric-rule: rule-lifecycle16, p18-e01-9, fabric-rule11 | 16 / 9 / 11 PASS | identik |
| 38521784664 | claude-p18-full-cycle | 2 PASS | identik |
| 38521794910 | claude-p21-rehearsal: full composition; install/pre-use rollback/identical reinstall/use/post-use | SUMMARY PASS keduanya (tanpa kasus JSON; status ringkasan) | identik |
| 38521805103 | claude-pl-native: netting, schedule, supply, model | 83 / 71 / 53 / 32 PASS | identik |
| 38521815079 | claude-note-correction | admission smoke 3, NOTE_CORRECTION 28, races 4, http 3, browser 5 — PASS (43) | identik |
| 38521824295 | cp7-receipt-correction | 37/3/1/2 PASS (43) | identik |
| 38521833888 | claude-supplier-payment-correction | 14/4/3/2 PASS (23) | identik (kegagalan sekali-jalan retest tidak terulang) |
| 38521843429 | claude-supplier-payment-create | 4/3/1/2 PASS (10) | identik |
| 38521853239 | claude-p08-shell: shell, p19-assembly, p19-staged, CodeQL actions, CodeQL js-ts | shell = uji-diri runtime (INCOMPLETE yang disuntik: `deliberate restoration lock failure`, `earlier actual case failure` → terdeteksi; PASS 6); assembly/staged tanpa kasus JSON, job sukses | identik |
| 38521863082 | cp6-candidate-codeql (python, actions, c-cpp, js-ts) | 4 job sukses. **Daftar alert code-scanning tidak dapat dibaca auditor** (`code-scanning/alerts` → 403 "Resource not accessible by integration"); yang dibuktikan hanya "analisis selesai tanpa error", bukan "nol alert" | — (WRITER_CROSSCHECK untuk klaim nol alert) |
| 38521872645 | astra-cp7-timeline-reuse / isolated-kernel-parity (workflow penulis di pohon beku; dijalankan Fable sendiri) | `PARITY_PASS` declared 595 = executed 595, successes 312, refusals 283 (16 distinct), supply_events 448, mutations_caught 2; benchmark 100/300/1000 target: pengurangan 41/42/41 % (0 posisi), 11/23/31 % (100 posisi); status PASS | sama dengan XC2 |

Catatan B2: run pembanding adalah run Fable sendiri pada putaran sebelumnya (bukan artefak penulis). Pembacaan log per kasus dilakukan lokal dari salinan log yang disimpan di sesi (`cp7/runs/*_1157*.json`); salinan tidak dimasukkan ke repo karena ukurannya, ringkasan hitungan di atas adalah hasilnya.
