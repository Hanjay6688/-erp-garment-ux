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
