# CP7 P19 — phase B: real staged SCENARIO units (history, baseline, supply/WIP, schedule, fabric/accessory)

Clone: `/tmp/p19bench/s5kB/repo`, branch `phaseB` from `842df901`. Patch: `/tmp/p19bench/s5kB/out/phaseB.patch` (= `git diff 842df901`). Logs: `/tmp/p19bench/s5kB/logs` (numbered, failing ones kept). Benchmark JSON: `/tmp/p19bench/s5kB/out/` (`P19_STAGED_SCENARIO_KERNEL.short_horizon.json`, `.default_horizon.json`, `.1000_positions.json`; `P19_STAGED_SCENARIO_KERNEL.json` and `bench_try*.json` are the earlier runs of logs 08–10, before the bound/HIST_STOCK/HIST_VALIDATE/ANA_TARGETS fixes). Local commit `07aa2ecd` on `phaseB` (not pushed).

Every timing below is **LOCAL_PG16_DEV** (PostgreSQL 16, disposable kernel runtime from `tests/cp7/families/f04/runtime.mjs`, 4-core shared machine with other Postgres instances running, generated captures). None of it is CI, Native, Auth, HTTP or browser evidence. No owner latency target is met or claimed met.

## 1. What is done

- **No product change.** Nothing under `scripts/cp7-src/**` changed; the single path (`cp7_analysis_native.build` → netting → schedule → supply → baseline → `history_build` → `cp7_demand.history`) and all its caps are byte-for-byte the files at `842df901`. Hence no predecessor-parity test was needed for product code.
- The test prototype `tests/cp7/families/f04/staged-analysis.prototype.sql` (still a TEST prototype, not installed) now computes the SCENARIO with real units instead of `cp7_schedule_native.build(c,q)`:
  `HIST_PREP → HIST_EVENTS×k → HIST_VALIDATE → HIST_ROWS×k → HIST_STOCK×k → BASE_ROWS×k → SUPPLY → SCENARIO` → (phase-A units) `NET_PREP …`.
  The plan grows twice: `HIST_PREP` fixes the units up to `NET_PREP`, `NET_PREP` fixes the rest (as before).
- FABRIC_PLAN / ANA_TARGETS run the **real** `cp7_fabric_native.plan/needs` and `cp7_analysis_native.material_needs` in the new fixture (no stand-in). The phase-A 4-field netting projection is kept and proven against the real plan (`fabric_plan_same` per case, and the whole analysis incl. `material_needs`).
- The stub-scenario corpus of phase A (`f05-staged-analysis.test.ts`, netting faults planted inside `c->'stub_scenario'`) is unchanged and still runs: its fixture sets `cp7_analysis_stage.scenario_stand_in()` to true, so its jobs keep the one-unit SCENARIO stand-in (only meaningful with a stub schedule).
- New fixture `tests/cp7/families/f04/staged-scenario-fixture.mjs`: installs the whole real chain (wip graph/normalize/bs/rewash/other/yield/production, planning utc/history_events/history_availability/history_build, baseline/supply/schedule builds, netting, fabric, material, analysis, finance, job store) unchanged from the working tree, plus a full-capture generator (`scenarioCapture`) and `ss_complete` (the selected schedule over the capture's own normalized WIP, bound to `cp7_supply_native.fingerprint(c)`).
- New test `tests/cp7/families/f05-staged-scenario.test.ts` (parity corpus, cap/bound cases, mutants) and benchmark `scripts/cp7_p19_staged_scenario_benchmark.mjs`.
- Job failure now also records `failure_message` (SQLERRM) so refusals are compared on SQLSTATE **and** message, not only the CP7 code.

## 2. The units and why each is exact

Each unit runs copies of the single path's own statements (verbatim where order, ties or errors matter) over a part of the input, in the single path's order. A part is cut only where the result provably depends on that part alone.

| Unit | Scope / chunk (default bound) | What it runs | Exactness argument |
|---|---|---|---|
| HIST_PREP | global, linear | `history_build` up to the demand kernel: status check; the single call's grid **expression** (same casts → same errors) compared with job bounds; facts hash; `targets` (same statement); clean-source checks; `cp7_demand.history` head (fields, context, instants, days rule, policy, targets bound); history_build's stock-loop order (same `for … order by root_id` query, so ties come out identically); sale-id cut; baseline hash | identical statements; job bounds only where the single call has a cap |
| HIST_EVENTS×k | sale-id range, 2,500 sales | `cp7_planning.history_events` (product function, unchanged) on the range's sales + their headers' journals + inverses (by `reversal_of_id`) + their returns/return journals/inverses; then the demand kernel's events check (verbatim: flags, fast path, row loop), selected events, group events | a lineage (= sale item) is never cut; every event, flag and check reads only its own lineage, the clock and the targets; result order is (lineage, revision) and ids are cut in the same collation. The chunk does **not** raise: it returns its first refusal (SQLSTATE, message) |
| HIST_VALIDATE | global, tiny | events count check (kernel cap 50,000 kept), targets loop (verbatim), then re-raises the first chunk refusal in chunk order | the kernel checks events count and targets *before* events; first refusal of the first failing chunk = kernel's first events refusal |
| HIST_ROWS×k | target-key range, ≤ 12,500 cells (targets×days) | `history_availability` (product function) on the range's products + their roots' stock rows; the kernel's history-rows statement (verbatim) over the range's targets, their selected events and availability | each root's grid uses only its own stock rows; each history row aggregates only its own target's days/events; rows are in key order (unique keys) |
| HIST_STOCK×k | root-order range, 1,000 products | history_build's per-root sums and draft lists, then its stock loop (verbatim) | loop order taken from HIST_PREP (same query); sums are exact numerics; see note on the reserve set lookup below |
| BASE_ROWS×k | key range, 250 rows | `cp7_baseline_native.build` row loop (verbatim), maps built at the chunk's first row exactly as at the single loop's first row | rows independent; map-building errors happen at the first row of the first chunk, as in the single loop |
| SUPPLY | global over positions | `normalize_production` + supply fingerprint (verbatim) | — |
| SCENARIO | global over positions | `cp7_schedule_native.build` after its supply call (verbatim) | — |
| FABRIC_PLAN | global | real `cp7_fabric_native.plan(c, {rows: 4-field projection, match_results: unresolved})` | plan reads exactly `target_key`, `production_policy.policy.state`, `conditional_gap_pcs`, `net.inputs.deadline` of each row and only the UNKNOWN/NEEDS_CHECK target keys; same row order |
| ANA_TARGETS×k | 250 targets | phase-A copy, now with real fabric/accessory needs; `material_needs` gets the capture clock + the accessory rows reachable from the chunk's roots (array order kept) | `material_needs` takes the first selected row of a root, the first version of its id, that version's items (sorted by id from the same filtered input) and the first category of each item id — same rows first; a source whose parts are not all arrays is passed whole (same error) |

**Clean source / fallback.** Cutting `history_events` and `history_availability` is exact only when no cast they make can fail and nothing can tie: `events_clean` = every sales/journal/return/return-journal element is an object with a unique string id, all timestamps/dates/numerics they cast are castable, DRAFT/CANCELLED revisions castable, ≤ 1 original journal per sale header, ≤ 1 inverse per journal; `availability_clean` = stock array (or absent), GRADE_A/B rows' `physical_at`/`book_order`/`qty_signed` castable and ids unique and non-null, products' `established_at` castable, query dates castable. If not clean, HIST_PREP calls the single path's **whole** `history_events(c)` / `history_availability(c,q)` (exact, including which bad value a refusal names) and the chunks read that result. This fallback is bounded only by the statement limit: at 5,000 targets the whole calls cost 11.8 s / 16.2 s (log 02), so a *non-clean* capture of that size stops with `CP7_ANALYSIS_STAGE_STOPPED` (loud, never a wrong result). Captures read from the ERP have PK ids and typed columns, i.e. are clean; the fallback exists for planted defects and exactness.

**Availability rows need no check in the chunks.** Every availability row `history_build` makes for a product has that product's key, refs and the capture clock; once the targets check passed (unique, valid keys/refs; it runs first) every such row is valid and conflict-free. HIST_ROWS asserts this invariant and would raise `CP7_ANALYSIS_STAGE_INVARIANT` (unreachable by the argument; never seen).

**One rewritten statement (HIST_STOCK).** history_build's `physical_by_root` uses a NOT EXISTS anti-join on the reserve ids. Inside PL/pgSQL with a jsonb parameter this took 6.7 s per call over 36,000 stock rows (plain SQL 0.33 s; logs 11–12), and every HIST_STOCK unit needs it. The prototype keeps history_build's first sum statement verbatim (its casts and therefore its first error are unchanged) and computes `physical_by_root` with the reserve ids as a jsonb key set: the same rows (`not coalesce(set ? reversal_of_id,false)` ≡ NOT EXISTS, null ids excluded as the join excludes them), summed exactly as numerics; it casts a subset of the first statement's rows, so it cannot fail first. 7.3 s → 1.2 s per 1,000-product unit (log 13). The single path still has the slow statement (under its 1,000-target cap it costs ~0.5 s).

## 3. Bounds (declared in `cp7_analysis_stage.bounds()`)

Per unit: `targets_per_chunk` 250 (was 500 in phase A; real timelines make ~60 KB of analysis per target, 500 took 4.6 s per ANA_TARGETS unit, log 08), `pairs_per_chunk` 25,000 (was 100,000; 6.5 s at 100,000 real pairs, log 08), `history_cells_per_unit` 12,500, `sales_per_events_unit` 2,500, `targets_per_stock_unit` 1,000, allocation 1,000 targets / 100,000 visits per step (unchanged).
Per job: `job_targets` 5,000 (`CP7_ANALYSIS_STAGED_TARGET_LIMIT`, now refused in the first unit HIST_PREP), `job_history_cells` 500,000 = 5,000×100 days (refuses `CP7_PLANNING_HISTORY_GRID_LIMIT` in HIST_PREP), demand events 50,000 (the kernel's own cap, same code), 3,660-day rule kept, `job_pairs` 1,000,000, `job_matching_products` 10,000, positions 1,000 (unchanged from phase A).
Single-call caps are untouched. Intended differences (asserted in the test): 1,001 targets × 1 day — single `CP7_F04_ARRAY_LIMIT`, job DONE; 40 targets × 2,600 days = 104,000 cells — single `CP7_PLANNING_HISTORY_GRID_LIMIT`, job DONE; both complete (every target has its history and netting row). Above the job bounds the job refuses in HIST_PREP (5,001 targets; 200 × 2,600 = 520,000 cells).

## 4. Parity proof (`tests/cp7/families/f05-staged-scenario.test.ts`, LOCAL)

Final run: log 21 (3/3 pass, 585 s); the phase-A stand-in file: log 22 (4/4 pass, 106 s, same statistics as phase A: 714 allocation inputs × 3 step sizes, 1,890 check_allocations comparisons, 162 stub captures with 80 complete and the 3 intended MATCH_LIMIT differences).

**Test 1 — corpus (SMALL bounds: 7 targets per chunk, 37 history cells, 7 sales, 5 stock products, 45 pairs, 4 targets per allocation step, so chunk edges fall everywhere).** 219 generated captures over four shapes (9–30 targets, 1/3/6/9 history days, 3–6 cutting groups plus opening WIP, half with every target reviewed): 3 seeds × 57 planted defects (history 25, baseline 7, supply/WIP 7, schedule 11, netting 3, fabric/accessory 4; incl. 4 non-clean sources of which 2 legal, 3 double bad values placed so that the first value read by the whole statement lies in the last chunk, and 1 combined target+event defect) + 48 clean captures. For every case the staged job and the single chain run on the same capture in one call:
- **101 complete**: equal, as text, to the single build: `runs.result` (jsonb and analysis text), the Original document (segments joined = `original(run)::text`), the assembled scenario = `cp7_schedule_native.build(c,q)::text`, netting rows, match results, allocation, and the FABRIC_PLAN output = real `cp7_fabric_native.plan(c, single netting)`. 23 with the global allocation run (11 edges), 218 CONFIRMED_TARGET and 179 CANDIDATE_MATCH results, 32 fabric rows with a computed external need, 2,289 accessory rows, 3 completions through each non-clean fallback (whole events / whole availability). Cases with >1 unit of a kind: HIST_EVENTS 98, HIST_ROWS 77, HIST_STOCK 101, BASE_ROWS 101, NET_TARGETS/NET_PAIRS/NET_ROWS/ANA_TARGETS 93, ALLOC_STEP 36.
- **118 refused**: the job FAILED with the single path's first refusal, same SQLSTATE **and** message, and where the schedule build itself refuses, the same as it. 35 distinct refusals, by the unit that raised them: HIST_PREP 10 (`CP7_PLANNING_CAPTURE_INCOMPLETE`, `CP7_F04_INSTANT_UTC`, `CP7_DEMAND_COMPLETE_DAYS_REQUIRED`, `CP7_DEMAND_POLICY`, and 6 cast errors whose message names the value the single statement reads first, e.g. 22007 `"not-a-time"`, 22P02 `"1x"`, 22008 `"2026-13-01T00:00:00Z"`); HIST_VALIDATE 5 (`CP7_DEMAND_DUPLICATE_TARGET`, `CP7_WIP_KEY`, `CP7_DEMAND_REVISION_CONFLICT`, `CP7_DEMAND_TARGET_SIZE`, `CP7_DEMAND_LIFECYCLE`); HIST_STOCK 2 (`CP7_PLANNING_NATIVE_RESERVATION_MISMATCH`, `CP7_WIP_PCS`); BASE_ROWS 5 (21000, 22023 scalar/object, `CP7_F04_DECIMAL`, `CP7_DEMAND_MINIMUM_DAYS`); SUPPLY 4 (`CP7_WIP_TRANSITION_QUANTITY`, 22023 object, `CP7_WIP_KEY`, 22007); SCENARIO 3 (21000, `CP7_WIP_YIELD_POLICY`, `CP7_F04_INSTANT_UTC`); NET_PREP 3; FABRIC_PLAN 1 (22P02 `"1,5"`); ANA_TARGETS 2.
- No divergence.

**Test 2 — caps and job bounds** (realistic bounds): the two intended differences (1,001 × 1 and 40 × 2,600 days: single refuses at its cap, job DONE with every history and netting row), and the job's own bounds refusing in HIST_PREP (5,001 targets → `CP7_ANALYSIS_STAGED_TARGET_LIMIT`; 520,000 cells → `CP7_PLANNING_HISTORY_GRID_LIMIT`).

**Test 3 — mutants** (22 captures: 10 clean, 12 defect cases; each mutant one text replacement in one prototype function, applied, run, restored; the restored prototype agrees again). Divergent cases per mutant: EVENTS_NO_INVERSE (an inverse journal without the header id dropped from the chunk) 7, EVENTS_CUT_EDGE (first sale of each chunk lost) 12, AVAILABILITY_NOT_CHECKED (uncastable stock quantity no longer forces the whole call → the chunk names the other bad value) 2, EVENTS_NOT_CHECKED (same for sale dates) 2, ROWS_EDGE (last history row of each chunk lost) 12, ROWS_DRAFTS (drafts read as cancelled) 12, BASE_POLICY_LAST (last policy wins) 2, VALIDATE_NO_CONFLICT 4, VALIDATE_EVENTS_FIRST (chunk events refusal raised before the targets check) 2, SCHEDULE_NO_YIELD 12, FABRIC_NO_GAP (projection without the conditional gap) 7. All 11 caught.

Earlier sweeps with the same comparison (scratch driver, 2 seeds per defect): logs 03/04 and 14 (114 cases, 0 divergent after the events-check restructuring), 23 (14 cases, after the final comment-only header edit).

## 5. Timings (LOCAL_PG16_DEV, `scripts/cp7_p19_staged_scenario_benchmark.mjs`)

Every unit in its own psql session under `statement_timeout='8s'`; "n × max" = units of that kind × slowest unit (server ms). Generated captures (`reviewed: true`, 3 sales + 3 stock receipts per target, 8 cutting groups + 20 opening origins ≈ 75–86 WIP positions). Single call = `cp7_analysis_native.build` in ONE call without a statement limit (measurement only).

### 5.1 Short planning horizon (lead ≤ 3, review ≤ 2 days; ≈ 21 KB analysis per target) — log 16, `out/P19_STAGED_SCENARIO_KERNEL.short_horizon.json`

| stage | 1000×1 | 1000×100 | 5000×1 | 5000×100 |
|---|---|---|---|---|
| **HIST_PREP** | 1 × 498 | 1 × 370 | 1 × 2,059 | 1 × 2,163 |
| **HIST_EVENTS** | 2 × 932 | 2 × 798 | 6 × 1,125 | 6 × 1,130 |
| **HIST_VALIDATE** | 1 × 139 | 1 × 100 | 1 × 482 | 1 × 549 |
| **HIST_ROWS** | 1 × 389 | 8 × 796 | 1 × 1,807 | 40 × 1,259 |
| **HIST_STOCK** | 1 × 314 | 1 × 293 | 5 × 1,213 | 5 × 1,202 |
| **BASE_ROWS** | 4 × 260 | 4 × 380 | 20 × 959 | 20 × 1,130 |
| **SUPPLY** | 1 × 274 | 1 × 237 | 1 × 864 | 1 × 884 |
| **SCENARIO** | 1 × 393 | 1 × 286 | 1 × 1,470 | 1 × 1,491 |
| NET_PREP | 1 × 357 | 1 × 388 | 1 × 2,182 | 1 × 2,124 |
| NET_TARGETS | 4 × 417 | 4 × 526 | 20 × 618 | 20 × 621 |
| NET_PAIRS | 2 × 1,678 | 2 × 1,466 | 11 × 2,746 | 9 × 3,159 |
| NET_PLAN | 1 × 90 | 1 × 97 | 1 × 540 | 1 × 633 |
| ALLOC_PREP | 1 × 358 | 1 × 42 | 1 × 1,714 | 1 × 260 |
| ALLOC_STEP | 1 × 110 | 1 × 44 | 5 × 403 | 5 × 230 |
| ALLOC_FINAL | 1 × 82 | 1 × 44 | 1 × 638 | 1 × 192 |
| NET_ROWS | 4 × 520 | 4 × 511 | 20 × 808 | 20 × 766 |
| FABRIC_PLAN | 1 × 285 | 1 × 249 | 1 × 1,198 | 1 × 850 |
| ANA_TARGETS | 4 × 921 | 4 × 1,062 | 20 × 1,619 | 20 × 1,685 |
| ANA_META | 1 × 590 | 1 × 672 | 1 × 3,324 | 1 × 3,042 |
| ANA_TEXT | 1 × 620 | 1 × 654 | 1 × 4,666 | 1 × 3,885 |
| RUN_INSERT | 1 × 529 | 1 × 569 | 1 × 2,999 | 1 × 2,832 |
| DOC_RENDER | 1 × 619 | 1 × 629 | 1 × 3,903 | 1 × 3,312 |
| DOC_SEGMENTS | 1 × 541 | 1 × 522 | 5 × 2,245 | 5 × 2,142 |
| units / slowest finished unit / wall | 37 / 1,678 ms / 19 s | 44 / 1,466 ms / 24 s | 126 / 4,666 ms / 141 s | 163 / 3,885 ms / 178 s |
| job state | DONE | DONE | DONE | DONE |
| analysis / Original | 20.8 / 20.9 MB, 11 segments | 20.7 / 20.8 MB, 11 segments | 104.7 / 105.4 MB, 53 segments | 102.3 / 103.0 MB, 52 segments |
| complete (history / baseline / netting rows, keys covered) | 1000 / 1000 / 1000, 1000 | 1000 / 1000 / 1000, 1000 | 5000 / 5000 / 5000, 5000 | 5000 / 5000 / 5000, 5000 |
| single call, one statement, no limit | DONE in 14.3 s, **byte-identical** | DONE in 24.4 s, **byte-identical** | refused `CP7_F04_ARRAY_LIMIT` | refused `CP7_PLANNING_HISTORY_GRID_LIMIT` |
| capture | 9 MB; 3000 sales; 7208 stock rows | 9 MB; 3000 sales; 7175 stock rows | 45 MB; 15000 sales; 36001 stock rows | 45 MB; 15000 sales; 36104 stock rows |

### 5.2 Generator default horizon (lead ≤ 20, review ≤ 10 days; ≈ 60 KB analysis per target) — log 15, `out/P19_STAGED_SCENARIO_KERNEL.default_horizon.json`

| stage | 1000×1 | 1000×100 | 5000×1 | 5000×100 |
|---|---|---|---|---|
| **HIST_PREP** | 1 × 426 | 1 × 473 | 1 × 2,193 | 1 × 2,148 |
| **HIST_EVENTS** | 2 × 764 | 2 × 1,083 | 6 × 1,009 | 6 × 1,143 |
| **HIST_VALIDATE** | 1 × 103 | 1 × 121 | 1 × 530 | 1 × 579 |
| **HIST_ROWS** | 1 × 424 | 8 × 702 | 1 × 1,695 | 40 × 1,159 |
| **HIST_STOCK** | 1 × 344 | 1 × 275 | 5 × 1,111 | 5 × 1,189 |
| **BASE_ROWS** | 4 × 260 | 4 × 361 | 20 × 1,000 | 20 × 1,131 |
| **SUPPLY** | 1 × 226 | 1 × 328 | 1 × 885 | 1 × 816 |
| **SCENARIO** | 1 × 311 | 1 × 358 | 1 × 1,466 | 1 × 1,445 |
| NET_PREP | 1 × 379 | 1 × 450 | 1 × 2,319 | 1 × 2,008 |
| NET_TARGETS | 4 × 1,225 | 4 × 1,300 | 20 × 1,513 | 20 × 1,537 |
| NET_PAIRS | 2 × 1,519 | 2 × 1,596 | 11 × 2,561 | 9 × 2,693 |
| NET_PLAN | 1 × 97 | 1 × 122 | 1 × 565 | 1 × 580 |
| ALLOC_PREP | 1 × 344 | 1 × 40 | 1 × 1,677 | 1 × 254 |
| ALLOC_STEP | 1 × 230 | 1 × 34 | 5 × 518 | 5 × 210 |
| ALLOC_FINAL | 1 × 151 | 1 × 44 | 1 × 750 | 1 × 192 |
| NET_ROWS | 4 × 565 | 4 × 638 | 20 × 907 | 20 × 933 |
| FABRIC_PLAN | 1 × 245 | 1 × 252 | 1 × 1,106 | 1 × 878 |
| ANA_TARGETS | 4 × 2,037 | 4 × 2,808 | 20 × 3,046 | 20 × 3,345 |
| ANA_META | 1 × 608 | 1 × 583 | 1 × 3,202 | 1 × 3,162 |
| ANA_TEXT | 1 × 1,718 | 1 × 1,770 | 1 × stopped at 8 s (3×) | 1 × stopped at 8 s (3×) |
| RUN_INSERT | 1 × 1,373 | 1 × 1,435 | 1 × not reached | 1 × not reached |
| DOC_RENDER | 1 × 1,629 | 1 × 1,698 | 1 × not reached | 1 × not reached |
| DOC_SEGMENTS | 1 × 2,262 | 1 × 2,361 | 5 × not reached | 5 × not reached |
| units / slowest finished unit / wall | 37 / 2,262 ms / 31 s | 44 / 2,808 ms / 40 s | 126 / 3,202 ms / 190 s | 163 / 3,345 ms / 228 s |
| job state | DONE | DONE | FAILED (unit 118 ANA_TEXT, CP7_ANALYSIS_STAGE_STOPPED) | FAILED (unit 155 ANA_TEXT, CP7_ANALYSIS_STAGE_STOPPED) |
| analysis / Original | 59.6 / 59.7 MB, 30 segments | 59.2 / 59.4 MB, 30 segments | — | — |
| complete (history / baseline / netting rows, keys covered) | 1000 / 1000 / 1000, 1000 | 1000 / 1000 / 1000, 1000 | — | — |
| single call, one statement, no limit | DONE in 26.7 s, **byte-identical** | DONE in 41.0 s, **byte-identical** | not run (job stopped) | not run (job stopped) |
| capture | 9 MB; 3000 sales; 7208 stock rows | 9 MB; 3000 sales; 7175 stock rows | 45 MB; 15000 sales; 36001 stock rows | 45 MB; 15000 sales; 36104 stock rows |

At 5,000 targets with this horizon the analysis is ≈ 300 MB; ANA_TEXT (one sha256/text over the whole analysis) was stopped three times by the 8 s limit and the job FAILED loudly with `CP7_ANALYSIS_STAGE_STOPPED` (unit ANA_TEXT; RUN_INSERT/DOC_* not reached). Every scenario unit and every netting/analysis unit before it stayed ≤ 3.4 s.

### 5.3 Supply/schedule at the position cap — log 18, `out/P19_STAGED_SCENARIO_KERNEL.1000_positions.json`

1,000 targets × 1 day with 990 WIP positions (110 groups + 250 origins; 990,000 pairs ≤ job 1,000,000): SUPPLY 1 × 1,479 ms, SCENARIO 1 × 693 ms, NET_PAIRS 23 × 2,620 ms, max unit 3,053 ms (ANA_TARGETS), DONE, 1000/1000 rows; single refused `CP7_NETTING_WORK_LIMIT`.

### 5.4 Fabric plan at the P19_FABRIC_SCALE heavy point — log 17

Real `cp7_fabric_native.plan` as the one FABRIC_PLAN unit, 5,000 targets / 300 materials / 20,000 rolls / 1,000 drafts / 10,000 open PO lines, fed the 4-field projection: 2.7 / 2.6 / 2.4 s (3 runs). One global unit fits locally; ≈ 5 s on a 2× slower runner.

### 5.5 Pieces measured before the design (log 02, 5,000 targets × 100 days, 15,000 sales, 36,000 stock rows)

`history_events` whole 11.8 s (it plans a nested loop over sales × journals; per 2,500-sale chunk ≈ 0.7–1.1 s), `history_availability` whole 16.2 s (250 roots: 1.2 s), `normalize_production` 0.67 s (424 positions), supply fingerprint 0.62 s.

## 6. NOT done / open (in order of risk)

1. **The 5,000-target job does not finish with realistic horizons**: ANA_TEXT/RUN_INSERT/DOC_RENDER are proportional to the analysis bytes (≈ 60 KB/target with the generator's 1–30-day horizons → ≈ 300 MB at 5,000; ANA_TEXT > 8 s locally). With a short horizon (≈ 100 MB) they take 3.0–4.7 s locally (≈ 6–9 s on a 2× runner). This is phase A/D's open item (frozen single `semantic_hash`, `runs.result` as one jsonb, 64 MB client cap) — a contract decision, not solvable by more units.
2. **Byte-proportional over the capture** (linear, not superlinear): HIST_PREP (two sha256 over the facts), NET_PREP / SCENARIO / ANA_META (fingerprints over the facts) take 2.0–3.3 s at a 45 MB capture. Larger real captures (capture caps allow ≈ 50,000 rows per fact array) would push ANA_META toward 4–5 s locally. Can be split (dependency hashes in their own unit) if CI shows it is needed; not done.
3. **Non-clean sources at 5,000** fall back to the whole `history_events`/`history_availability` (11.8 s / 16.2 s) and stop the job (`CP7_ANALYSIS_STAGE_STOPPED`). Exact but not completing; real ERP captures are clean by construction (PK ids, typed columns). An exact chunked replay of plan-dependent error order is not possible without running the same statement over the same rows.
4. **Not covered by the corpus**: the 50,000-event cap (needs a 50,001-event capture; whole `history_events` would take minutes); `CP7_DEMAND_UNPOSTED_RETURN` / `CP7_DEMAND_POSTED_AT` / `CP7_DEMAND_LINEAGE_IDENTITY` (history_events cannot produce such events from a capture — checked, the planted twin trips another refusal identically on both paths). The checks are verbatim copies.
5. **Two code paths** remain (prototype copies of history_build, the demand kernel's events/rows statements, the baseline loop, supply and schedule tails). Production should make the single call run the same stage functions over one range; not done (would be a product refactor with predecessor-parity tests).
6. **Tie order on duplicate netting keys in FABRIC_PLAN**: the plan sorts rows by target key; with duplicate keys an in-memory sort of the projection and an external sort of the full rows could order ties differently. The real chain cannot produce duplicate keys (one baseline row per validated, unique history target); only the stub corpus can, and it is small (in-memory both ways).
7. Capture at 5,000 (one statement vs parts), job RPCs / driver / access re-check per unit, expiry, freshness — phase C, untouched.
8. CI: the new test file (≈ 8 min locally) and the benchmark (≈ 10 min locally for 4 vectors) are **not wired** into `.github/workflows/claude-p08-shell.yml` (`p19-assembly` has a 30-minute budget already used by 16 test files + 11 benchmarks). Integrator decision: own job, or a reduced corpus in `p19-assembly`.
9. The design doc `docs/cp7/p19/P19_STAGED_5000_20261007.md` is not updated (its phase-B row, §2 table and §7 bounds now differ from the prototype: 250 targets / 25,000 pairs per unit).

## 7. Files (all under the clone)

- `tests/cp7/families/f04/staged-analysis.prototype.sql` — scenario units (`castable`, `events_clean`, `availability_clean`, `history_prep`, `event_facts`, `events_validate`, `history_validate`, `history_rows`, `history_stock`, `baseline_rows`, `supply`, `schedule`, `material_scope`, `run_scenario_unit`, `scenario_result`, `scenario_stand_in`), new bounds, `failure_message`, plan from HIST_PREP.
- `tests/cp7/families/f04/staged-scenario-fixture.mjs` (new) — real chain install, `scenarioCapture`, `ss_complete`, `ss_case`, mutants helper.
- `tests/cp7/families/f04/staged-analysis-fixture.mjs` — stub corpus keeps the SCENARIO stand-in (`scenario_stand_in()` → true).
- `tests/cp7/families/f05-staged-scenario.test.ts` (new); `scripts/cp7_p19_staged_scenario_benchmark.mjs` (new).
- Unchanged: `tests/cp7/families/f05-staged-analysis.test.ts`, `scripts/cp7_p19_staged_benchmark.mjs` (stand-in benchmark, still in CI), every `scripts/cp7-src/**` file.

## 8. Logs

01 baseline `f05-staged-analysis` at `842df901` (4/4) · 02 pieces at 5,000×100 · 03/04 first defect sweeps · 05/06/07 first test runs (FAILED: corpus threshold too high, a mutant typo, two mutants not caught until the planted defects put the first-read bad value in the last chunk — kept) · 08/09 benchmark trials (bounds too large for real data) · 10 full benchmark v1 (HIST_STOCK 7.5 s/unit, HIST_VALIDATE 3.6 s — fixed) · 11–13 HIST_STOCK profile and fix · 14 defect sweep after restructuring the events check (114 cases, 0 divergent) · 15 benchmark default horizon · 16 benchmark short horizon (COMPLETE) · 17 fabric plan heavy point · 18 990 positions · 19 test run FAILED (a mutant still pointed at the moved conflict check — kept) · 20 test run PASS (3/3, before the verbose reporter) · 21 final test run, verbose (3/3) · 22 phase-A stand-in file (4/4) · 23 sanity after the comment-only header edit (14/14).
