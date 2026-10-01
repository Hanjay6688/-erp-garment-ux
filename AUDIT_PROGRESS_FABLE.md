# Log progres auditor Fable (per auditor sejak 2026-09-25T15:57:22Z; riwayat sebelumnya di AUDIT_PROGRESS.md yang dibekukan)

## 2026-09-25T15:57:22Z — putaran 11 selesai; keputusan owner D06 + T3; handoff putaran 11
- BB final 4c61aca CONFIRMED (T1 57/57, runtime 14/14, T2, T3 26, rollback 131, T4 PASS, regresi bersih). Cek silang GPT BB round 10: konvergen.
- Owner: D06 disahkan (lampiran rev4 @4c61acad, sha 42e04815…), T3 = A. Dicatat di OWNER_DECISIONS_CP6_DRAFT.md dan indeks.
- Handoff tempel writer: WRITER_HANDOFF_R11_PASTE_20260925.md (D06 dicatat di addendum, kalimat T3 diperbaiki, tidak ada cacat produk BB, catatan sebelum BC).
- Opsi 1 disepakati GPT: log progres dipisah per auditor mulai sekarang.

## 2026-09-25 17:15Z — round 12 pre-BC: writer's "pre-existing" F1/F2 reproduced independently (run dispatched)
- Writer head moved 4c61aca → 7c9d00a (BC probe 32 cases, local PG16 only) → 4b1bd66 (six BA-era ALL-state probes = handoff 3b). BC still has no
  handoff section and no CI run: NOT FINAL, BC audit not started.
- Release package byte-identical 4c61aca..4b1bd66 (only supabase/dev BC file, scripts/cp6_bc_*, src/initialImportCatalogBC.json, docs changed).
  Dispatcher re-pinned to 4b1bd66 for pre-BC scenario runs.
- Writer commit 7c9d00a names two PRE-EXISTING findings and EXCLUDES one from its own probe delta:
  F2 `run_v255_material_cost_integrity_checks:MATERIAL_RECOST_GL_STATE_DRIFT` ("stale per-movement recost check reports drift on exact books");
  F1 `run_v265_gudang_write_integrity_checks:contractor_issue_price_provenance_gap` CRITICAL on a manual-price note line (BC redefines this detector).
- Own scenario `audit/scenarios/round12_fable/xaudit_12_f1f2.py` sha256 2ce03444…: BC_ABSENT guard, detector source dump from pg_proc, F2 via
  (a) late invoice only (control), (b) native adjustment + late invoice ×2, (c) stacked receipts n=3 / n=10 pooled + late invoices; F1 via the AP
  issue facade with mode MANUAL. Oracle: books exact (M:6632/M:835/T3-A) — detector on exact books = detector defect; silent+exact = PASS.
- Dispatched run 36165571453 (phase after, head 4b1bd66). INDEPENDENT_NATIVE_RERUN; waiting.
- Reviewed ab4ea6d docs: D06 recorded verbatim (sha 42e04815…, OWNER_CONFIRMED_TO_AUDITOR), T3 question rewritten per owner, old "1 sen per PO"
  sentence marked wrong in history — CONFIRMED consistent with OWNER_DECISIONS_CP6_DRAFT.md.

## 2026-09-25 17:36Z — round 12 pre-BC F1/F2: runs so far (all INDEPENDENT_NATIVE_RERUN, phase after/pre_bc = product before BC)
- 36165571453 rev1 (4b1bd66): red — auditor tool defect (cases() returned a dict; runner wants [(id, callable)]). Not product evidence.
- 36166046560 rev2 (4b1bd66, after = pre-BC, BC_ABSENT PASS): F2 CONTROL PASS; ADJUST+INVOICE(10.005) COUNTEREXAMPLE (GL 70.03 vs qty×avg 70.04,
  detector +1); ADJUST+INVOICE(2.10) COUNTEREXAMPLE (books exact 14.70, detector +1); STACKED N3 PASS (silent); STACKED N10 COUNTEREXAMPLE
  (books exact: WIP 100.10, inventory 0, detector +1); F1 INCOMPLETE (my error path had no savepoint).
- 36166784262 rev3 (4b1bd66): detail run — per-account deltas, detector inner rows, revaluation events. Obligation (account 2010) = documents
  rounded in EVERY case (100.05 / 100.05 / 21.00 / 30.03 / 100.10). My `obligation_equals_documents_rounded` check keyed by mapping name instead
  of account code → always false → rev3 statuses contaminated (auditor tool defect); rev2 statuses stand. Detector rows: N10 one cut movement
  applied −0.05 vs per-movement target −0.01 (document cent carry, T3-A); adjustment movements have NO material_cost_revaluation_state row
  (applied None) while the journal carried the recost (5900 +30.02 / +6.30) → detector compares against a table the v2.6.20t document-level
  engine does not write. F1 facade refused my timestamp (WIB format) → fallback direct DRAFT line: detector counts it (predicate confirmed).
- 36167400464 rev4 (4b1bd66): F1 through the real facade (POST, mode MANUAL, WIB physical_at): posted line manual_retail_unit_price 3.00,
  accessory_price_version_id null → contractor_issue_price_provenance_gap +1 CRITICAL → **F1 CONFIRMED pre-existing** (baseline predicate
  ignores manual_retail_unit_price; M:1066 ACC-DEC02 makes the manual price valid). F2 cases INCOMPLETE on my column typo (triggering_material_id).
- Writer head moved to 95353aa (BC pages, races/HTTP/browser, BC CI workflow, auditor workflow: phase `after` now installs BC, new `pre_bc`).
  DB release package still identical to 4c61aca. Dispatcher re-pinned; rev5 dispatched as 36168041413 phase pre_bc.

## 2026-09-25 17:45Z — round 12 pre-BC FROZEN: run 36168041413 (rev5, pre_bc, 95353aa) 4 PASS / 4 COUNTEREXAMPLE
- F1 CONFIRMED pre-existing (facade route). F2 CONFIRMED pre-existing detector defect (books meet oracle on all 5 paths; adjustment facts v2.6.20t present, V2620T_*=0;
  state row missing for adjustment movements; document cent carry n=10). Written: out/fable_r12_results.md, WRITER_HANDOFF_R12_PASTE_20260925.md, handoff §2a, index key fable_round12_pre_bc.
- Next: cross-check GPT (after this push), then wait for BC final head + case table + CI run.
- 17:55Z: F3 (writer case table d385e7e) CONFIRMED by source review + Node regex test: `src/accessoryIssue.ts:20` strict UUID guard unchanged since 4c61aca; seed
  `a1000000-…-0001` fails; blocks ACC-D09 browser evidence. Sibling `src/laundryQcModel.ts:123`. Writer heads seen: fe226cf (BC = 27th T3 file, T2 covers BC),
  d385e7e (BC case table). Still no BC final declaration / T3 pins. GPT: no new commits since 66cbdc4 → nothing to cross-check.
- 18:20Z: F4 reproduced independently: run 36171335601 (pre_bc, 0746c33) advance-paid opening settlement `reversible` NULL → COUNTEREXAMPLE; run 36171347110 (after)
  `false` → PASS; cash control `true` both phases. Round-11 "BB no product defects" corrected (F4 escaped r11). Writer runs read (status only): BC probe 36168802591
  green both phases, T2 36168125448 green 3/3, auditor modes run 36168808537 red at browser step (writer: script error, fix 792251f). Waiting for BC final.
- 18:25Z: cross-check GPT `out/gpt_bc_20260926_initial_review.md` (REUSED_GPT_LOG_READ of writer CI on 5e1ae83/e21d15b/0746c33): convergent with Fable on F3
  (UI guard, ACC-D09 unproven) and F4 (NULL flag, coalesce fix). New GPT claim GPT-BC-01 (P3 UI: search query carried from Stok tab to Dokumen tab, hides
  documents) — not yet verified by Fable; to check with an own browser case in the BC round. GPT notes ACC-C12 coverage partial (same-goods duplicate not
  tested) — agree; added to my BC-round list. No conflicts. Standing by for the writer's BC final (head + §31 + run numbers).
- 18:35Z: owner direction on F2 recorded as D07 (retune to document level; verbatim + auditor reading in OWNER_DECISIONS_CP6_DRAFT.md); spec for writer in paste R12
  §2.1. GPT BC initial review compiled into paste R12 §2a and handoff §2a (GPT-BC-01, ACC-C12 gap, ACC-D09, browser INCOMPLETE, T3/rollback reads).

## 2026-09-25 19:20Z — round 12 BC started (writer §31 = BC head; product 27e1a05, DB package e21d15b, tool head 23abac1)
- GPT reconciliation done (results §8): GPT-BC-01 valid at 5e1ae83, fixed 27e1a05; GPT-BC-02 rollback comparator narrowing reviewed and accepted; ACC-C12 same-goods
  case added by writer (21ce322), new-custody-key limit = owner policy question; ACC-D09 unproven (writer browser reruns red ×4).
- Own pinned BC probe workflow `.github/workflows/fable-cp6-bc-t1.yml`: run 36178145305 (writer PLAN 44): before 33 NO_ROUTE + 3 CE + 8 PASS, after 44/44 PASS,
  mismatch {}, primary_unchanged. Run 36178552990 (PLAN + 5 Fable cases) in flight.
- Dispatched on 23abac1: T2 36177884812, T3 package 36177895962, rollback 36177907418, CodeQL 36177919063; regression after-phase: xa1 36177930596, xa2 36177941767,
  xa7 36177953287, xa8 36177965107, xa9 36177978040, open_1 36177989983, C0 36178002278, xaudit_12_f1f2 36178015645.
- T2 disposition written (results §10): ACCESSORY_CONNECTED_ZERO PASS→INCOMPLETE = EXPECTED_CHANGE per ERP-DEC02/M:5023; frozen case stays, writer adds successor.
- 19:30Z: round 12 BC results: gates T2/T3(27)/rollback/CodeQL all success; regression identical to r11 (xa8 2 frozen CE, C0 1 grant INCOMPLETE); F1 fix CONFIRMED
  natively (36178015645); BC PLAN 44/44 after on own workflow (36178145305); Fable adversarial cases product-clean (36178552990; auditor comparator defect → rev2
  triggered by workflow touch). Results §9, paste §2b, index fable_round12_bc. Open: D09/F3, D07, ACC-C12 key policy.
- 19:35Z: BC probe PLAN + Fable rev2 run 36179524130: after 49/49 PASS, before per plan, mismatch {} — FROZEN for BC T1. Round 12 BC closed on the auditor side
  except open items D09/F3, D07, ACC-C12 key policy. Waiting for writer (D09 green, D07, then BD).
- 19:55Z: handover notes written (HANDOVER_AUDITOR_ONBOARDING_20260925.md — state NOT locked, §3 tells how to find the current state; HANDOVER_WRITER_OPUS_TO_GPT_20260925.md).
  In flight: run 36181745737 (Fable BC races ×6 + cross-tab browser ×1, scenario sha 3612a314…, head caeff6f, product 27e1a05). Fable continues until quota ends; every step pushed.
- 20:15Z: Fable BC races ×6 + cross-tab browser: rev1 36181745737 (product correct; 2 FAIL = auditor oracle), rev2 36182433079 **7/7 PASS FROZEN**. GPT correction read
  (GPT has not run own BC scenarios yet; GBC-1–3 oracles frozen) — consistent. Items 1–2 done. Fable continues only while quota lasts; the replacement auditor follows
  HANDOVER_AUDITOR_ONBOARDING_20260925.md §3 to find the current state.
- 2026-09-25 20:10Z (26 Sep 03:10 WIB): GPT BC follow-up run2 36182902112 reconciled (results §14, paste §2c): GBC-1 agree PARTIAL/UNVERIFIED (owner identity policy);
  GBC-2 agree F3, joint severity P3 product / P2 conditional on cutover data (read-only inventory by writer/operator); GBC-3 covered by Fable 36182433079. No conflicts.
- 26 Sep 03:20 WIB: WRITER_HANDOFF_R12_FINAL_PASTE_20260926.md written (single reconciled Fable+GPT paste for Opus: BC clean on tested coverage, 5 ordered tasks, conventions);
  previous paste marked DIGANTIKAN; index writer_handoff_paste_latest updated.
- 26 Sep: D08 recorded (owner direction: F3 fix option b allowed; format validation ≠ access security; writer must show from diff that no role/permission line changes).
  Paste final §2.3 rewritten. Writer status read: BD near-final (28-file T3, T2 covers BD, D07 done in af00dd1, T3 red on af00dd1 pending re-capture), UI gallery ffb5076.
- 26 Sep: owner directions D09 (ACC-C12 option a), D10 (invoice variance split), D11 (policy table), UI-01 recorded verbatim; §32.9 synced (owner vs auditor items);
  combined paste WRITER_HANDOFF_R12B_PASTE_20260926.md (GPT reply + Fable additions + decisions). BD head 2aee623 with §32 = auditable; BD round pending quota.

## 2026-10-01 — Fable back after quota gap (27 Sep → 1 Oct): survey only, nothing verified yet
- Replacement auditor did NOT use this shared branch; its work is on `audit/bd-independent-20260927`, `audit/bd-be-retest-20260928`, `audit/bd-be-sku-delta-handoff-20260928`,
  `audit/cp6-final-independent-20260928`, `audit/cp6-cp7-acceptance-20260929` (branched from the writer branch, folders `audits/…`). On 29 Sep it declared
  "CP6 CLOSED — independently accepted for contract scope; R10 OPEN on CP7; production_go=false" (candidate fab23e7, product/package 434b182, 30-file package incl. BE+BF).
- Writer branch: 72 commits since 08065a3 (BE, BF = commercial ranges/vendor credit/conversion history; release package 30 files; writer takeover doc 28 Sep). Handoff doc stops at §34 (BD);
  BE/BF have separate handoff docs. Writer moved to CP7 (branches cp7/*, PRs #31–#38, cp7/integration active 1 Oct). `main` unchanged (557005e, 22 Sep).
- NOT yet verified by Fable: BD/BE/BF audits, the CP6 closure claim, D07 retest, D09 ACC-C12 tests, F3/D08 fix verification, D11 values, GBD-03. Fable's own last frozen state remains r12 (BC).

## 2026-10-01 ~02:00Z — round 13 (owner chose option a): verify the CP6 closure claim on candidate 10a8347 (product 434b182)
- Identity: src + supabase/release + supabase/migrations identical 434b182..10a8347; runtime core (runner/modes/au_r1) unchanged since 95353aa; driver reviewed at 10a8347 (installs BD/BE, phases pre_bd/pre_be, writer push config only on push events).
- Dispatched: gates T2 36802914343 · T3(30) 36802922323 · rollback 36802929871 · CodeQL 36802937437; regression after-phase (AC..BF): xa1 36802945018 · xa2 36802952298 ·
  xa7 36802959475 · xa8 36802968654 · xa9 36802978021 · open_1 36802987554 · C0 36802996229 · xaudit_12_f1f2 36803005576 (D07: F2 rows expected silent) · xaudit_12_f4 36803013529.
- Pinned probe workflows (audit branch be23433): BC (PLAN + 5 FAB) 36803064370 · BD (PLAN 34 incl. D09/D10 cases) 36803064486 · BE (PLAN 13) 36803064466.
- Own D07 negative controls `round13_fable/xaudit_13_d07.py` (sha cee58a1d…): run 36803212344. Writer modes+browser reruns on auditor runtime: BC 36803221110 · BD 36803230431 · BE 36803238529.
- Cross-check read: replacement auditor's acceptance = disclosed retest of BF conversion history + CP7 delta + 30-file package install; D07/D09/F3 relied on writer runs (36463334464 etc.), not re-run.

## 2026-10-01 ~02:30Z — putaran 13 selesai: klaim "CP6 CLOSED" auditor pengganti DIVERIFIKASI pada 10a8347 (produk 434b182)
- Gerbang: T2 36802914343, T3(30) 36802922323, rollback 36802929871, CodeQL 36802937437 — semua success.
- Regresi Fable (after): xa1 6/6, xa2 7/7, xa7 14/14, xa8 14+2 CE beku, xa9 5/5, open_1 15/15, C0 26+1 INCOMPLETE (cacat skenario, sejak r12),
  f1f2 9 PASS + BC_ABSENT FAIL (penjaga) → **F2 diam di semua 5 jalur (D07 af00dd1 bekerja)**, F1 PASS; f4 5/5.
- Kontrol D07 (xaudit_13_d07, run 36803212344): SILENT_ON_EXACT PASS; NEG_STATE_TAMPER PASS (+1 saat tamper, 0 setelah rollback);
  NEG_FACT_TAMPER INCOMPLETE — tabel fakta append-only (42501 MATERIAL_ADJUSTMENT_REVALUATION_FACT_APPEND_ONLY). Bukan cacat.
- Probe pin (workflow + ref auditor): BD 36803064486 after 41/41; BC 36803602974 before = PLAN, after 50/50 (45 penulis + 5 FAB);
  BE 36803064466 rev1 before gagal PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE sebelum kasus apa pun (balapan sesi saat install AS) →
  rerun tunggal: before 16 NO_ROUTE, after 16/16 PASS. BC rev1 36803064370 gagal karena cacat alat auditor (re-pin sha), dibangun ulang 96bd871.
- Mode penulis via runtime auditor: BC 18/18, BD 20/20, BE 17/17.
- Laporan: out/fable_r13_results.md (FINAL). Semua JSON per kasus di audit/runs_fable/r13/.
- Tidak diuji Fable: F3 hanya tinjauan sumber; BF/CP7 di luar lingkup gerbang CP6 Fable. Terbuka owner: D11 nilai kebijakan, GBD-03, arah UI.

## 2026-10-01 ~02:56Z — putaran 14 (finisher CP6) dispatched: BF dengan oracle sendiri + rerun bukti BF penulis di runtime auditor
- Owner: "uji aja yang lu rasa perlu buat finisher cp6, abis tu lanjut cp7". Celah yang saya pilih: BF (belum pernah saya sentuh), F3 (tinjauan sumber saja).
- Sumber: badan BF paket rilis `20260928134500_erp_v2_6_20bf…sql` memuat badan dev `supabase/dev/cp6_bf_t1_family.sql` (sha d5e66d22…)
  utuh kecuali satu baris deskripsi ledger (288279/288316 karakter cocok) — INDEPENDENT_SOURCE_REVIEW. Driver fase `after` memasang BF dari berkas dev
  (`INSTALL_BF=True`), jadi run di bawah menguji badan yang sama dengan paket.
- F3/D08: `src/accessoryIssue.ts:20` dan `src/laundryQcModel.ts:124` = regex UUID kanonik dengan flag `/i` (huruf besar diterima). Tidak ada uji browser; cukup.
- Skenario sendiri `audit/scenarios/round14_fable/xaudit_14_bf.py` (sha 83813915…): RANGE_MOVE_WRITES_NO_PHYSICAL, SKU_AT_TIMELINE_NO_GAP,
  HPP_VALUE_CONSERVED_ACROSS_GROUPING, SUPPLIER_CREDIT_AP_CONSERVED → run 36808105014.
- Rerun bukti penulis lewat `cp6-auditor-scenario.yml` (after, head 10a8347): combined+bf_browser 36808112738; free+free_browser 36808120840;
  vendor+vendor_browser 36808128920; bf_modes+supplier_browser 36808136834.
- Oracle BF yang dikutip penulis dari owner (28 Sep 14:59 WIB: tarif laundry dari vendor; SKU final opsional) = UNVERIFIED_OWNER_DECISION sampai owner konfirmasi.

## 2026-10-01 ~03:45Z — putaran 14 selesai: BF lolos; CP6 selesai dari sisi auditor Fable
- xaudit_14_bf 36808105014: 4/4 PASS (range move tanpa jejak fisik; sku_at kontinu; HPP kekal; Σ AP kekal + penolakan negatif/over).
- Rerun penulis: combined 154/154, vendor 133/133, bf_modes+supplier 67/67; free_modes 116 PASS + 9 INCOMPLETE = skenario basi
  (BF_LAUNDRY_VENDOR_AUTHORITY; aturan owner 28 Sep/R16 ditegakkan produk; jalur FREE/WAIVED sah lulus di master vendor BD) → SUPERSEDED_BY_OWNER_RULE.
- Laporan: out/fable_r14_results.md. JSON per kasus di audit/runs_fable/r14/. Berikutnya: CP7 (menunggu arahan owner).

## 2026-10-01 ~03:50Z — putaran 14 selesai: BF lolos; register dikoreksi; D13 dicatat; CP6 selesai dari sisi auditor Fable
- xaudit_14_bf 36808105014: 4/4 PASS. Rerun penulis: combined 154/154, vendor 133/133, bf_modes+supplier 67/67; free_modes 116 PASS + 9 INCOMPLETE =
  SUPERSEDED_BY_OWNER_RULE (BF_LAUNDRY_VENDOR_AUTHORITY). Laporan out/fable_r14_results.md; JSON di audit/runs_fable/r14/.
- Kesalahan auditor dikoreksi: GBD-03 (opsi 1), D11 (5 diputuskan, 8 isian aplikasi), UI-01 (dijadwalkan owner) sudah dijawab 26 Sep — bukan item terbuka.
- D13 (owner → auditor, 1 Okt): tarif laundry dari vendor; SKU hanya riwayat biaya. Produk sesuai (BF_LAUNDRY_VENDOR_AUTHORITY; erp_get_laundry_history_v1).
- Berikutnya: CP7 atas arahan owner.

## 2026-10-01 ~07:20Z — putaran 15: PR 39 (cp6/release-readiness f378b9e) ditinjau dan dijalankan ulang
- Sumber: paket DB identik 10a8347; 28 pendahulu 28/28 hash cocok; BF free ditulis ulang di vendor (D13); UI hanya penjelasan/prefill; preflight hosted baca saja.
- Run ulang saya di cabang PR: readiness 36824954256 (owner 58 berkas 10/10; native 104 / races 26 / HTTP 9; browser 31, 0 console error);
  auditor-scenario 36824956958 combined+free browser 166/166. Identik dengan klaim penulis.
- Tidak bisa verifikasi "hosted masih v2.6.20" dari sesi ini (baca proyek hosted ditolak) → REUSED_WRITER_EVIDENCE.
- Laporan: out/fable_r15_pr39_review.md. Putusan: PR 39 layak merge ke cabang penulis; go produksi tetap menunggu isian owner, backup pulih, jendela maintenance, advisor hosted, UI vs demo.
