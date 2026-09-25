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
