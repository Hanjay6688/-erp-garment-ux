# First failures — append only

## 37877038138, independent staged attempt1

- Product:2e605bb7; audit:ea858258.
- Error: `dict() got multiple values for keyword argument case`.
- Classification: AUDITOR_HARNESS, not a product finding.
- Cause: our result dict included `case`; the unchanged strict runner adds `case` when logging.
- First individual result was saved before the logger failed; remaining seven did not run.
- Source restoration: boundary/public/function hashes all true. Package30files, security and backup/restore gates passed.
- Fix: rename our metadata field to `audit_case_id`; no assertion/oracle/product changes.
- Preserve original run/artifacts11592801959(JSON),11593156018(raw), not overwritten.
- Corrected run must retain all first outcomes; no claim that first attempt passed.

## 37877343411, business attempt1

- Same AUDITOR_HARNESS result-key collision as37877038138.
- Independent full-flow case completed PASS; complete first verdict sha2567b6227b42193fbc6b752a6178d7096cff5facf356d64d01d668ebb07d17f4250 retained in evidence/projection-first-1.json.
- Three remaining cases were never reached; continuation executes only those three after metadata fix.
- Full composition restore boundary/public/functions true; package restore/security gates passed.

## 37877802981 and37877803025, retained-row comparison

- First hashes differ only in tables containing typed timestamptz (jobs/page_sets); immutable body/page hashes identical.
- Suspected AUDITOR_COMPARATOR: to_jsonb timestamptz text depends on session TimeZone. No field is excluded.
- Correct comparator setsUTC for serialization and restores callerTimeZone. Dedicated validation must prove time-zone invariance and preserve raw before/after differences.
- Original COUNTEREXAMPLE outputs preserved in evidence/log-verdicts-113650280731.json and113650279827.json. Not attributed to product until adjudicated.

## 37878142700, AS20-32 first setup

- `CP7_PLAN_ASSUMPTIONS_NOT_REVIEWED` at v1 SAVE before either racing action.
- AUDITOR_FIXTURE: payload reused v2 assumption IDs while v1 capture has its own IDs. Positive guard rejection, not product failure.
- Correct only reviewed_assumption_ids using the actually read v1 option list. Capacity inputs/oracle unchanged. Continue only the unreached race; preserve all five PASS cases.

## 37878640217, precise source amount and receipt actor

- AS20-07_LARGE_INVOICE PASS on all three actual amounts. No rerun required.
- AS20-04_08_PRECISION raw `material_purchase_final_ap_total` returned exact61.648683507697. Original expectation incorrectly imposed cents at an intermediate function. Framework02 says rate/amount scales differ and round only at a valid boundary. Classification pending runtime public payment check; do not assign this intermediate mismatch as a product bug.
- Followup preserves exact-operand equality, verifies public payable61.65 and actually pays61.65 to test zero residual. First output retained.
- AS20-01_RECEIPT_REPLAY setup refused `CP7_PROCUREMENT_VALUE_DENIED`: our actor could post but lacked `finance.ap.view` for the explicit price. Add value permission only to initial positive setup; still revoke posting before replay. No guard changed.

## 37878853771, unchanged candidate shell gate

- `scripts/cp7_probe_evidence_test.py` fails `NameError: p19_plan_v2 is not defined` at actual finalizer execution.
- WRITER_HARNESS_DEFECT, independently reproduced at exact candidate; not an application monetary defect.
- Remaining shell/build/browser steps were skipped. Run them separately unchanged, while keeping original shell gate FAILED. Never remove this failure from final assessment.

## Adjudications after independent controls

- Retained row comparison: AS20-38_COMPARATOR_CONTROL plus preservation and two cleaners all PASS in37878853657. Canonical UTC changes no stored field. Original mismatches are AUDITOR_COMPARATOR, withdrawn from product findings.
- Money precision:37879768225 proves public payable61.65, actual payment61.65, zero residual; exact intermediate remains61.648683507697. Original intermediate cents assertion is AUDITOR_ORACLE_BOUNDARY, withdrawn. Receipt permission fixture corrected; revoked posting replay now PASS.
- 5000 scale37878853657 completed all pages, size measurement and cleanup. 5001 honestly FAILED before result (units_done0, run_idnull, CP7_PLANNING_CAPTURE_INCOMPLETE). Only the auditor's over-specific TARGET_LIMIT text assertion failed; the pre-registered no-truncation/refusal oracle is satisfied. Keep original counterexample; no expensive rerun or product fix needed.
- Browser37879134928 initially marked48 desktop +48 mobile route smoke PASS. Code review found the generic loading regex could miss the multiline lazy workspace placeholder. Treat initial route readiness proof as PARTIAL. Continue with an explicit placeholder disappearance check; no product changes.
- Edges37879580253:6/7 independent cases PASS. Matching positive setup refused CP7_WIP_MATCH_BINDING because our synthetic source refs did not equal reconciled position refs. This is AUDITOR_FIXTURE, not an app failure. Use actual immutable position refs in the positive control, retaining own137PCS/red-color oracle; continue only that unreached case.

## 37880663536, two-midnight-sales continuation

- Four independent monetary cases PASS: chosen-invoice supplier credit22.46, paid receipt quantity increase, returned/paid sales correction, and73-unit two-stage late invoice.
- WIB test posted the first23:59:59 sale, then second CREATE refused duplicate sale_number because both own fixture sales reused the same tag. AUDITOR_FIXTURE; unique-document guard worked. Keep quantities/prices/dates/oracles; add date suffix to each synthetic document number and continue only this uncompleted case.
- Corrected matching probe37880366048 PASS; no matcher finding. Corrected ready-screen browser37880365949 PASS:48 desktop+48 mobile navigation and actual finance permission boundary. Earlier readiness evidence stays PARTIAL.

## Final continuations

-37881044694: current payroll82.82 +opening85 +carry7.50 -advance30 =cash145.32. Own case PASS, replay one effect, inverse restores cash/source rights and physical41 unchanged.
-37881215479: distinct-document continuation proves23:59:59 WIB revenue58.11/COGS49.38 and00:00:01 revenue135.59/COGS115.22 in their proper dates. PASS; duplicate-number fixture failure remains preserved.

## Kelanjutan setelah laporan awal — first failures tetap utuh

- Run37892630236: discount, size dan late fullflow PASS. AS20C-04-ACTOR berhenti karena auditor menulis material_purchases, bukan material_purchase_headers. AUDITOR_FIXTURE; hanya kasus itu dilanjutkan di37893419603danPASS.
- Run37892863976: retentionFAILED danUTF8 PASS. Consumer fixture memakai custom role code yang memang bukan internal role untuk reminder. Run37893519004memakaiSTAFF tetapi baseline legacySTAFF sengaja nonaktif, sehingga positive start ditolak. Keduanya AUDITOR_FIXTURE; tidak ada produk diubah. Run37894257418menggunakanADMINaktif dengan4permission, lalu cabutWIP:11endpoint positif dahulu,seluruh11ditolaksetelahrevoke danretainedunchanged.
- Run37893074616:5racePASS. AS20C-15-RACE telah melewati admission/replay tetapi final drain auditor masih PARTIAL_SELECTIONmeski menghabiskan sisa. Produk benar menolak. Mode final control digantiALL_READY; targeted37893987955PASS. Dua input race19+17danoracle30tetap.
- Run37893419603: actor,returncredit,closedperiodPASS. Roster gagal pada duplicate Python keyword helper, sebelumCREATE. Priority mencapaiA11/B6tetapi assertion membandingkan inputecho yang sengaja dipermutasi. Keduanya first failure disimpan. Targeted37894141652membuktikan baris/edges/quantity/refs/verdict identik; hanya order inputecho berbeda. Earlier deadline/unknowncontrolsPASS. ADJUDICATED_PASS, bukan bug produk.
- Roster37894141652: pekerja/amount38.815→38.82/payroll6038.82benar; akun debit aktualWIP dibandingkan auditor denganLABOR_COST. Kontrak CP3 yang diterima menempatkan approvalattendance diWIP sebelum alokasiSELESAI_DIJAHIT;LABOR_COSTuntukmanualreimbursement berbeda. Salah oracle akun auditor diperbaiki secara terbuka, angka/kewajiban/replaytetap. Targeted final roster37894872845PASS dan identity/replaydituntaskan. ADJUDICATED_PASS, bukan alasan meminta writer mengubah kebijakan.

- Browser37894527264: kedua perjalanan sudah menjalankan7command200danfullinverse. Pembanding terakhir auditor membandingkan dictionaryGLsecara struktural; akun yang baru punya jurnal muncul dengan saldo0.00setelahinverse. RawINCOMPLETEtetap. Adjudicate_browser.pymembandingkansemuaIDakun(default0),kontrol+0.01akunlama/baruterdeteksi,danmemeriksa final41FG,raw32/395.84,semuariwayatreversed,jurnalbalance. Bukti runtimelengkaptelahtersimpan,sehinggatidakadaulangruntime. ADJUDICATED_PASSuntukkedualayar.

Semua raw verdict,trace,runIDdanhashartifact tetap berada dalam CONTINUATION_RESULTS.json serta evidence/CONTINUATION_PROJECTED_EVIDENCE.json.gz. Semua pemulihan boundary/public/functions tercatattrue. Tidak ada kasus lulus diulang sekadar untuk menambah hitungan.
