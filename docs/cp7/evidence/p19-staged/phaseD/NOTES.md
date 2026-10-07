# P19 phase D — reading a 5,000-target staged run by target range

Clone `/tmp/p19bench/s5kD/repo`, branch `phaseD`, commit `19b2028f` on `842df901` (local only; nothing pushed, no remote touched, no hosted DB).
Patch: `/tmp/p19bench/s5kD/out/phaseD.patch` (= `git diff 842df901`). Logs: `/tmp/p19bench/s5kD/logs/01…13` (failures kept). Outputs: `/tmp/p19bench/s5kD/out/`.

Labels. `LOCAL_PG16_DEV` = this machine, disposable PostgreSQL 16, kernel stand-ins, shared/noisy host: **not evidence**. `RETAINED_NATIVE` = real Native Originals retained in the repo by the P19 load suite (source `8f326d87`), bytes only. `CI 37632330032` = figures handed over by the coordinator (FULL_APPLICATION_NATIVE, p19-scale5), quoted, not re-measured. No cap was raised, no test/oracle loosened, single-run transport unchanged byte for byte.

## 1. Measurements: where the bytes of an Original are

Scripts: `scripts/cp7_p19_original_bytes.mjs` (→ `out/P19_ORIGINAL_BYTES.json`, log 07), `scripts/cp7_p19_result_storage.mjs` (→ `out/P19_RESULT_STORAGE.json`, log 13). "paged arrays" = the eight per-target arrays a staged run pages (recommendations, timeline, actions, demand_models, material_needs, metrics, assumptions, generation_warnings).

### 1.1 Real Native Originals (RETAINED_NATIVE, bytes only) and CI 37632330032

| Original | targets | bytes | per target (paged arrays) | timeline items/target × bytes/item | 5,000-target extrapolation |
|---|---|---|---|---|---|
| retained `P19_LOAD_PROFILE_1` | 3 | 170,003 | 49,753 | 10.3 × 3,265 | 248.8 MB |
| retained `P19_LOAD_PROFILE_4` | 6 | 307,071 | 46,928 | 10.7 × 3,242 | 234.7 MB |
| retained `P19_LOAD_PROFILE_12` | 14 | 673,122 | 45,352 | 10.9 × 3,232 | 226.8 MB |
| CI 37632330032 (coordinator) | 100 | ≈4.2 MB | ≈42,045 incl. fixed | 10.0 × 3,269 | ≈210 MB |

Per-target composition (retained 14 targets ≈ CI 100 targets): **timeline 35.1 KB (77–78 %)**, recommendations 3.1 KB (1 × 3,138 B), material_needs 2.9 KB (2 × 1,445 B), metrics ≈0.9–1.2 KB (1 × 931 B per target + 24 global NATIVE_FINANCE metrics), demand_models 0.81 KB, actions 0.66 KB, assumptions 0.2 KB. Top level: `analysis` 99 %, `financial_source` ≈11 KB fixed, `product_labels` 162 B/target. refs/event_refs/source_links = 47 % of the analysis bytes. Key names: the real `material_needs`/`demand_models`/`generation_warnings` are the prototype's fragment fields `materials`/`models`/`warnings` (mapped by `cp7_analysis_stage.page_field`).

### 1.2 Kernel fixtures (LOCAL_PG16_DEV)

| fixture | targets | Original bytes | paged bytes/target | timeline items/target × bytes/item | refs share | 5,000 extrapolated |
|---|---|---|---|---|---|---|
| assembly (`assemblyInput(n,2)`) | 100 / 300 / 1,000 | 612,554 / 1,805,665 / 5,969,265 | 5,899 / 5,849 / 5,820 | 1.0 × 2,615 | 35 % | 29.3 MB |
| staged (`stagedInput`, 100 positions) | 100 / 300 / 1,000 / 5,000 | 1,457,079 / 4,143,481 / 12,961,060 / 65,444,725 | 13,602 / 13,439 / 12,801 / 12,999 | 5.2 × 1,806 | 31 % | 65.4 MB (measured) |

**Gap to the real 42 KB/target, explained:** (1) the timeline has one DEMAND event per day of the target's horizon (`lead_days+review_days`, `cp7_netting_native.timeline`); real profiles give 10–11 items/target (scale case: 3+7 days), the staged fixture 2–9 days (5.2 items), the assembly fixture 0–3 events; (2) each timeline item carries 8 facts with the row's refs; real refs are UUID ids + UUID/64-hex revisions (~150 B each) and real target keys are `uuid:uuid` (75 B), so a real timeline item is 3.2 KB vs 1.8 KB (staged) / 2.6 KB (assembly); (3) real material_needs are 2 items/target × 1.4 KB (fixture 0.7 × 0.2 KB). Timeline alone: 10.9 × 3.2 KB = 35 KB of the 45 KB.

### 1.3 Staged job with page units, 5,000 targets (LOCAL_PG16_DEV, each unit its own psql session, `statement_timeout=8s`)
67 units (55 before + PAGE_HEADER, 10 PAGES, PAGE_INDEX), wall 77.2 s, job DONE. New units: PAGE_HEADER 89 ms, PAGES 10 × ≤ 594 ms (6.2–6.7 MB per page of 500 targets), PAGE_INDEX 16 ms; header 648,635 B. (Same run: ANA_TEXT 3.0 s, RUN_INSERT 3.5 s, DOC_RENDER 1.9 s — slower than the phase-A log on this noisy host.)

### 1.4 One jsonb `runs.result` at real scale (real-shaped: retained per-target items repeated; LOCAL_PG16_DEV, one session, no statement limit)

| targets | analysis text | jsonb datum (×1.087) | parse (1st / 2nd) | insert jsonb | render ::text | sha256 | one-key read of stored jsonb |
|---|---|---|---|---|---|---|---|
| 994 | 43.6 MB | 47.4 MB | 0.70 / 0.66 s | 0.45 s | 0.37 s | 0.23 s | 28 ms |
| 2,506 | 109.8 MB | 119.3 MB | 6.2 / 3.0 s | 1.38 s | 1.44 s | 0.84 s | 134 ms |
| 4,648 (≈210 MB) | 203.5 MB | 221.3 MB | 11.3 / 6.3 s | 2.21 s | 2.23 s | 1.36 s | 165 ms |
| 4,998 | 218.9 MB | **237.9 MB** | 6.9 / 5.4 s | 2.42 s | 2.32 s | 1.35 s | 224 ms |
| synthetic 251 MB text (log 07) | 251.3 MB | — | **refused 54000 "total size of jsonb object elements exceeds the maximum of 268435455 bytes"** | | | | |

(Stored sizes in the JSON are not meaningful: repeated items compress ~25×.) Reading: the real 5,000-target analysis still fits the jsonb container limit, at 88.6 % of it (≈11 % headroom: ~5,600 targets, or ≥49 KB/target at 5,000, is a hard PostgreSQL error, not a declared cap). RUN_INSERT (parse + insert) ≈ 7.8–13.5 s locally at 4,650–5,000 targets; scaled by the coordinator's CI ratio (RUN_INSERT 1.26 s CI vs 1.93 s local at 65 MB ⇒ ×0.65) ≈ 5–9 s on CI-class hardware — inside 8 s only on the favourable side and far above the 25 %-of-8 s margin used elsewhere; ANA_TEXT and DOC_RENDER scale the same way (≈3.4× the 65 MB cost). Every reader that touches one key of the stored jsonb detoasts all of it (224 ms here with ~25× compressible content; real content compresses far less).

## 2. Inventory: readers of `cp7_analysis_native.runs.result` / the Original, at a 5,000-target staged run

Without the guard below, every whole reader builds or embeds ≈210–220 MB (≈238 MB as jsonb): over the 8 MB single-body bound, the 64 MB client document cap and, in practice, 8 s. With the prototype guard (`refuse_paged` placed after the actor check of `serve()`/`manifest()`), they refuse fast and by name.

| reader (file) | what it reads | at 5,000 staged |
|---|---|---|
| `cp7_analysis_native.serve` / `erp_cp7_read_analysis_v1`, `capture` return (analysis.sql) | whole `r.result` + product labels + live fingerprint | whole body ≈210 MB+: must refuse → **CP7_ANALYSIS_RUN_PAGED** (proposed guard; prototype tests it on `manifest`). Live `source_for`+`fingerprint` at 5,000 is itself over budget (P19 §8.7, open) |
| `cp7_analysis_jobs.original/store/manifest/segment` (analysis-jobs.sql) | `original(r)::text`, document + segments | staged DOC_RENDER/DOC_SEGMENTS write them (linear); manifest's document > 64 MB is refused by the client ⇒ manifest refuses paged runs (guard); **segments stay served** (audit/download) |
| `cp7_analysis_native.archives` (analysis-archive.sql) | `r.result->'snapshot'…`, `->>'semantic_hash'` per visible run | detoasts each staged result per listing (0.2 s+ each, ×runs) ⇒ must read the identity from the header (`page_sets`/a column) |
| `cp7_reminder_native.access_now` (attention.sql) → attention workspace/command, receivables, payables, obligation episodes/report/history, rule policy/history, local sink | **embeds `erp_cp7_read_analysis_v1`** (the whole Original) in every response | all refuse (guard) — reminders/attention/conditions **unavailable for staged runs** until they read header + per-target lookups |
| `cp7_reminder_native.original_authority` (attention.sql) → rule conditions, rule episodes, obligation report | `r.result` snapshot/semantic hash + all 5,000 recommendation keys | full detoast of `result` (~0.2–2 s) + 5,000 keys; needs header + a target-key index |
| `rule-condition-source.condition_rows` | every recommendation and material need | 5,000 targets × conditions in one call: over budget; would need paging by target range server-side |
| `report-publication.sql` (publish/read/compare, `report_document`) | serve() + a text report line per target/metric/material | report text ≫ 8 MB; unavailable for staged runs (open: paged reports) |
| `fabric-commands.sql` (fabric workspace/save) | serve() then one recommendation by key | needs one target: page lookup by target key (open; needs a key→page index) |
| `plan-native/source.sql`, `actual.sql` (plan draft/actual) | `r.result` whole + serve() for authority | one target needed: same key→page lookup (open) |
| frontend `NativeAnalysisPanel` (capture/read/job/manifest/segments) | whole Original | **staged: header + pages (new, this phase)** |
| frontend `nativeAnalysisAttention`, `nativeReceivableConditions`, `nativePayableConditions`, `nativeObligationEpisodes`, `nativeRuleSource`, `nativeReminderPolicy`, `nativeAnalysisReports`, `nativeFabricRecipe`, `NativePlanDraftPanel`, `NativeStockAnalysisView`, `NativeMaterialNeedsView`, `analysisReport`/`analysisPrompt` (AI) | an embedded whole Original (8 MB single-body bound) | not offered for a staged run (their `context` stays null; the staged view says so); server side would refuse anyway |

## 3. Design: pages bound to the run (prototype, test runtime only)

Files: `tests/cp7/families/f04/staged-pages.prototype.sql` (NEW, loaded by `staged-analysis-fixture.mjs` right after `staged-analysis.prototype.sql`). **No existing unit body changed.** The one change to existing prototype objects: `cp7_analysis_stage.run_unit` is **renamed** `run_unit_core` and wrapped by a new `run_unit` (step() resolves it by name, unchanged) that (a) after NET_PREP appends `PAGE_HEADER → PAGES×k → PAGE_INDEX` to the fixed plan after DOC_SEGMENTS, (b) runs those units. SCENARIO/FABRIC are untouched.

- **Header** (`cp7.native-analysis-header.v1`): the Original's non-analysis fields exactly as `original()` renders them (run/request ids, query, financial_source, product_labels, flags) + `analysis_header` = the ANA_META skeleton with each per-target sentinel removed + the semantic hash, + `paged` = per paged array `{prefix, items}` (where the per-target items sit: sentinel index; how many), `targets_total`, `page_count`, `document_sha256`, `semantic_hash`. Never named or shaped as a whole Original (no `analysis` key, own contract).
- **Pages** (`cp7.native-analysis-page.v1`, one per ANA_TARGETS chunk): run/request ids, index, page_count, target_lo/hi (ordinals in the job's loop order), targets_total, document/semantic/header hashes, per-array `counts`, `offsets` (items before this page), whole-run `totals`, `summary` (recommendations by production state, unreviewed policies), `items` = the chunk's stored fragments parsed (no recompute). Canonical jsonb text, UTF8 size, sha256, ≤ 8,000,000 bytes else `CP7_ANALYSIS_PAGE_BODY_LIMIT` (header: `CP7_ANALYSIS_PAGE_HEADER_LIMIT`).
- **Tables** `cp7_analysis_jobs.page_sets` (written LAST by PAGE_INDEX after checking contiguity/counts; FK to `documents`, so bound to the segments) and `cp7_analysis_jobs.pages`: owner cp7_capture, RLS deny-all, no grants, immutable triggers. A failed or half-paged job is unreadable (readers require the page set).
- **Readers**: `cp7_analysis_jobs.pages_manifest(run)` = manifest-equivalent full check once (fresh read committed, actor-bound run, protected finance still visible, access unchanged at the end) → `cp7.native-analysis-pages.v1` {source_state, access_epoch, document {bytes, chars, sha256, segment_count, segment_characters}, semantic_hash, targets_total, page_count, paged, totals, header {utf8_bytes, sha256, body}, pages [{index, target_lo, target_hi, utf8_bytes, sha256, counts}]}; `cp7_analysis_jobs.page(run, index, access)` = the segment reader's checks (same access epoch, actor's own run) → `cp7.native-analysis-page-read.v1` envelope with the body string. Public `erp_cp7_read_analysis_pages_v1(uuid)`, `erp_cp7_read_analysis_page_v1(uuid,integer,text)`: SECURITY DEFINER, owner cp7_capture, `search_path=''`, execute only `authenticated`. `cp7_analysis_jobs.refuse_paged(run)` = the proposed guard line for `serve()`/`manifest()` (after the actor check; raises `CP7_ANALYSIS_RUN_PAGED`).
- **Proof** `tests/cp7/families/f05-staged-pages.test.ts` (2 tests, both pass, log 11): (1) the staged parity corpus (f05-staged-analysis seeds/shapes/defects, 162 cases) with pages of 7 targets (whole corpus, single build compared) and of 1 and 3 targets (2/3 of the corpus each): an independent SQL verifier checks per page canonical text/size/hash/binding/contiguity/counts/offsets; per paged array the page items in page order == items [prefix, prefix+n) of `runs.result` (text, byte for byte); header analysis == analysis without those items; header other fields == `original()`; the Original rebuilt from header + pages == the segments joined and the analysis text == the stored ANALYSIS text (byte for byte); totals == the analysis; failed jobs expose no page set/page. Result: 191 runs verified, 1,982 pages, 1,812 page edges, 80/80 single builds byte-identical, every paged array kind incl. unreviewed-policy warnings, null material needs (not paged) and zero-target runs; 12 refusal codes (no page set). (2) readers: page/manifest contents vs node sha256, refusals (changed epoch, other actor with its own epoch → RUN_UNAVAILABLE, index out of range, no actor, hidden owner report, run without pages, stale source → ARCHIVED_STALE), guarded manifest refuses `CP7_ANALYSIS_RUN_PAGED` (foreign run stays UNAVAILABLE), unchanged manifest for a run without pages, segments still served, privileges/owner/definer/search_path, immutability.

Existing suites with the fixture change: `f05-staged-analysis` 4/4, `f05-analysis-jobs` 1/1 (log 11).

## 4. Storage proposal for `runs.result` of staged runs

| option | at real 5,000 (LOCAL; CI ≈ ×0.65) | consequences |
|---|---|---|
| A. keep one jsonb (prototype RUN_INSERT today) | 238 MB jsonb = 88.6 % of the hard 268,435,455-byte limit; parse+insert 7.8–13.5 s local (≈5–9 s CI); every one-key read detoasts all | no contract change, but capacity rests on a PostgreSQL limit with ~11 % headroom (hard 54000 error, not a declared cap); RUN_INSERT/ANA_TEXT/DOC_RENDER near or over 8 s; readers still unusable (§2) — **not supportable** |
| B. text-backed result (`result_text`, `result` = NULL or header for staged) | insert text 2.0 s, sha 1.35 s; no jsonb limit | contract change of `runs` (nullable `result` or `result_kind`); every reader in §2 must branch; whole text still unreadable by the client; duplicates the document segments' content |
| **C. header jsonb + pages + segments (recommended)** | header 0.65 MB fixture (real est. 1–4 MB: labels 0.8 MB, sources ≤1.4 MB, edges, finance); pages ≤ 8 MB each; no ≥ 200 MB jsonb anywhere | `runs` gets `result_kind` ('WHOLE'/'PAGED') and, for PAGED, `result` = the header analysis (or NULL); `serve()`/`manifest()` refuse PAGED (`CP7_ANALYSIS_RUN_PAGED`); archives/original_authority read identity/target keys from the header/page set (+ a target-key→page index); reminders, reports, fabric workspace, plan draft read one target or a target range; semantic hash stays one sha256 over the whole analysis text (ANA_TEXT; ≈3× the 65 MB cost — still the largest single unit, open); RUN_INSERT shrinks to the header; DOC_SEGMENTS stays (audit/download); stage tables (fragments, texts ≈ 2× the document) need expiry after DONE |

Contract consequences (any option ≠ A): `runs.result` no longer always a complete `cp7.analysis.v2` (column or kind change; readers must branch or fail closed); `erp_cp7_read_analysis_v1`/manifest can refuse with a new code; new contracts `cp7.native-analysis-pages.v1`, `-header.v1`, `-page.v1`, `-page-read.v1`; archives list must carry/derive identity without detoasting; reminder/attention/condition/report/fabric/plan readers need target-scoped reads; the freshness check (live fingerprint at 5,000) remains open; the semantic hash definition is unchanged. Implemented in the prototype: only what paged reading needs (page tables, units, readers, guard); RUN_INSERT unchanged; single-path contracts unchanged.

**Page size at real scale (open, important):** pages = ANA_TARGETS chunks of 500 targets ⇒ 6.6 MB in the fixture but ≈22.7 MB at the real 45 KB/target ⇒ the page unit refuses (`CP7_ANALYSIS_PAGE_BODY_LIMIT`, no truncation). Options: (i) `targets_per_chunk` ≤ 170 for the per-target stages (≈34 chunks/kind at 5,000, more round trips); (ii) a separate ANA_TARGETS/page chunk bound in the NET_PREP plan (e.g. 150 ⇒ ≤ 7 MB); (iii) byte-adaptive pages: ANA_TARGETS also stores per-target item counts so PAGES can cut at any target boundary by bytes (small change to `analysis_targets` output; not done to avoid touching the unit under concurrent change).

## 5. Frontend (Indonesian UI, single runs unchanged)

- `src/nativeAnalysisPages.ts`: `parseAnalysisPagesManifest` (exact keys, contract, run/request binding, states, document shape, targets ≤ 5,000 declared, pages 0..n-1 contiguous over 1..total, counts summing to `paged`, totals: recommendations by state + unreviewed = targets, actions = targets, page ≤ 8,000,000 B, header ≤ 8,000,000 B), `parseAnalysisHeader` (size + sha256 of the body, contract, ids, query, paged, hashes, frozen schema on `analysis_header`, actor scope, labels, fact refs/global assumptions, sources vs edge inputs, finance via the unchanged `financeSource`), `parseAnalysisPage` (envelope vs manifest entry/header/document hash, body size + sha256, page body fields, counts/offsets/totals/summary recomputed, schema per item, per-page semantics: each target = 1 recommendation or 1 unreviewed policy, exactly 1 action per target, warnings, unique keys, every per-target item belongs to a target of the page, assumptions header ∪ page, material needs via the shared `assertMaterialNeed`, edges' sizes for page targets), `stagedRangeLabel` ("Target 501–1.000 dari 5.000"), `analysisRunPaged`.
- `src/nativeAnalysis.ts`: behaviour-preserving exports only (`assertAnalysisFacts`, `assertMaterialNeed`, `financeSource`, `pcs`, `analysisSchemaMatches`; `assertSemantics` calls them in the same order). `src/nativeAnalysisArchive.ts`: parameter types widened structurally.
- `src/NativeAnalysisPanel.tsx`: a whole read refused with `CP7_ANALYSIS_RUN_PAGED` (manifest after a background job, `erp_cp7_read_analysis_v1` when opening an archive) → `erp_cp7_read_analysis_pages_v1` → header → page 0 via `erp_cp7_read_analysis_page_v1` with the access epoch; generation + page-sequence guards drop stale replies; 42501 on a page drops the staged view; "Periksa sumber analisis" re-reads the page set (same header/document/pages) and the open page with the new epoch. Single runs: no new call, same parse.
- `src/NativeStagedAnalysisView.tsx`: summary first ("Ringkasan seluruh analisis · 5.000 target", every number from the server's totals, stated as such), then "Target 501–1.000 dari 5.000", Halaman k dari n, Target sebelumnya/berikutnya, a range selector, "Mengambil target 501–1.000 dari 5.000…" while loading (no page content shown meanwhile), "Halaman ini hanya memuat target …", no tabs/report/AI/stock/plan for staged runs (explicitly stated). No new CSS.
- RPC registration: `src/types/database.preconnect.ts`, `scripts/check-source-ownership.mjs`, `scripts/check-access-catalog.mjs`.

## 6. Test counts (exact)

| suite | before (842df901) | after | log |
|---|---|---|---|
| `npx vitest run src` (root) | 1,441 passed / 142 files | **1,453 passed** / 144 files (+7 `nativeAnalysisPages.test.ts`, +5 `NativeAnalysisPanel.pages.dom.test.tsx`) | 12 / 08 |
| `f05-staged-pages` (nobody) | — | **2/2** | 11 (first full run log 05: corpus pass, reader test failed on my stale stand-in → fixed, log 06) |
| `f05-staged-analysis` (nobody) | 4/4 | 4/4 | 02 / 11 |
| `f05-analysis-jobs` (nobody) | 1/1 | 1/1 | 01 / 11 |
| `npx tsc -b`, `npm run build` (incl. check:source/access/css, artifact scan) | pass | pass | 09, 10 |

Mutation checks done by hand on the parser (timeline target check, page range continuity, body hash, per-page target count, totals) and the view (totals from page) — each caught; one initially surviving (per-page target invariant) led to the "items shifted across a page edge with consistent hashes" test.

## 7. Done / not done

Done: measurements (real retained, fixtures, real-shaped jsonb limits/costs), reader inventory, page design + prototype (tables, units, readers, RPCs, guard), byte-for-byte proof over the corpus with 1/3/7-target pages, storage proposal, client parser/transport + staged UI + unit/DOM tests, commit. Not done: installing any of it (prototype only); RUN_INSERT/`runs` change; byte-adaptive pages or a per-page chunk bound (§4); guard installed in `serve()`/`manifest()` (tested only on the product manifest in the test runtime); target-key→page lookup for fabric/plan/reminders; paged reports/reminders/AI; freshness at 5,000; stage-table expiry; CI wiring (`f05-staged-pages` is not added to `p19-assembly`; ≈3 min locally); real browser/Native evidence.

## 8. Open decisions (owner/contract)

1. Storage: option C (header + pages + segments; `runs.result_kind`, PAGED runs refuse whole reads) vs B vs keeping A with a declared bytes cap below the jsonb limit.
2. Page granularity at the real 45 KB/target: per-page chunk bound (≈150 targets, ≤ 7 MB) vs byte-adaptive pages (needs per-target counts from ANA_TARGETS).
3. Which features must work on a staged run (reminders/attention, reports, fabric workspace, plan draft, AI handoff) and in which order; each needs a target-range or target-key reader — until then the UI states they are unavailable.
4. Semantic hash over ≥ 200 MB text stays one unit (≈3× today's cost): keep, or a contract change to a hash of hashes.
5. New refusal code `CP7_ANALYSIS_RUN_PAGED` and the four new contracts.
