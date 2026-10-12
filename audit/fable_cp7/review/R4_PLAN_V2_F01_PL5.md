# R4 — Plan v1/v2 (F01), Business Report v2, Reminders v2, AI v2, PL-5 B — source review notes

Candidate: `d0b9e9c2` (detached checkout `scratchpad/cand`). Read-only review of `scripts/cp7-src/**/*.sql`,
`src/NativeStagedAiPanel.tsx`, `src/nativeStagedAi.ts`, declarations `docs/cp7/p19/P19_*_V2.json`,
`docs/cp7/pl5/PL5_HISTORY_YIELD.json`, oracles `docs/cp7/p19/P19_STAGED_SNAPSHOT_V2.md`,
`docs/cp7/OWNER_DECISIONS_20261008.md`, `docs/cp7/PL5_YIELD_POLICY_PROPOSAL_20261007.md`,
`docs/cp7/framework-v2/01_KONTRAK_DAN_INTEGRASI.md` §3–§6, `04_BUKTI_DAN_ORACLE.md`, `06_RUSUK_KEBUTUHAN_OWNER.md`.
Writer tests used only for fixture names. No database was contacted. All line numbers are in the candidate checkout.

Abbreviations: C = `scripts/cp7-src/plan-native/commands.sql`, S = `scripts/cp7-src/plan-native/staged.sql`,
P = `scripts/cp7-src/plan-native/preflight.sql`, H = `scripts/cp7-src/plan-native/history-yield.sql`,
R = `scripts/cp7-src/planning/report-staged.sql`, M = `scripts/cp7-src/reminders/staged-reminders.sql`,
A = `scripts/cp7-src/planning/ai-staged.sql`.

---

## 1. F01 — one capacity lock for v1 and v2 ratification

### 1.1 Lock identity
- v1 apply (`cp7_plan_native.apply`, C:41-116): `pg_advisory_xact_lock(hashtextextended('CP7:PLAN_CAPACITY',0))` at C:65.
- v2 apply (`cp7_plan_native.apply_v2`, S:425-470): same key, same call, S:445.
- It is a **transaction-scoped advisory lock on one global constant key**, not a row lock; there is one capacity
  centre in the design ("satu kunci kapasitas", "one shared centre"), so every actor, run, draft and target
  serialises on it. Only these two places take it (grep over `scripts/`: C:65, S:445).

### 1.2 Lock order (identical in both versions; no cycle possible)
`CP7:PLAN_APPLY_REQUEST:<actor>:<request>` (C:49 / S:429) → `CP7:PLAN_MATERIAL_POOL:<roll>` sorted (C:57-59 /
S:441-443) → `CP7:PLAN_CAPACITY` (C:65 / S:445) → `CP7:PLAN_TARGET:<target_key>` (C:69 / S:447) →
`CP7:PLAN_VERSION:<plan_id>` (C:70 / S:448). `save`/`save_v2` take `CP7:PLAN_SAVE` then `CP7:PLAN_VERSION`
(C:6,17 / S:349,367) and acquire nothing after VERSION, so save cannot form a cycle with apply.
The Native writer (`erp_save_cutting_group_before_sewing_v2`) takes row locks after all advisory locks (C:90 / S:455).

### 1.3 Capacity check is after the lock, inside the same transaction, twice
- v1: `preflight` re-read at C:76 (after lock, re-reads the Original and refuses `CP7_PLAN_SOURCE_CHANGED` 40001 if the
  Original is no longer UNCHANGED, P:44-45). `used` = Σ `qty_pcs` of every *other* intent whose Native group is still
  unposted (C:83-86); refuse `CP7_PLAN_CAPACITY_USED` 40001 with DETAIL numbers when
  `selected_new_pcs > free_capacity_pcs − used` (C:87-89). Native draft written (C:90), then the **same check again**
  (C:98-109) after the writer's possible row-lock wait; intent inserted only after that (C:110-111). Any refusal rolls the
  Native draft back with the transaction.
- v2: `preflight_v2(...,'APPLY',r.id)` at S:452 (after all locks). `used` = Σ `qty_pcs` of every other intent that is
  (a) still an unposted Native draft, or (b) posted outside the snapshot's production scope, or (c) recorded after the
  snapshot boundary (S:264-268, `after_snapshot` S:113-121 uses `recorded_at >= data_as_of` OR xmin not visible in the
  capture `pg_snapshot`). `capacity_now = capacity_snapshot − used` (S:269); `CP7_PLAN_V2_CAPACITY_EXPIRED` when the
  selected calendar `through_at <= checked_at`, `CP7_PLAN_V2_CAPACITY_USED` when `total > capacity_now` (S:270-271);
  APPLY raises 40001 with the numbers in DETAIL (S:277-282). Native draft S:455, **recheck again** S:459, intent S:462.
- Isolation: both `access_now` entry points require `transaction_isolation = 'read committed'`
  (`plan-native/bootstrap.sql:53`), so each statement after the lock sees the other session's committed intent.
- `intents.draft_id` is `unique` (`plan-native/bootstrap.sql:23`), intents/drafts/commands immutable (bootstrap.sql:33-35).

### 1.4 Other writers of committed plan quantities
`grep -rn "insert into cp7_plan_native.intents" scripts/` → only C:110 and S:462. `erp_save_cutting_group_before_sewing_v2`
is called from cp7-src only in C:90 and S:455 (plus grant in bootstrap). Scenario (`schedule-scenario.sql`), fabric
commands, profiles, AI, report, reminders write no intents and call no Native writer. **No plan ratification path
bypasses the lock.** Residual: a *manual* cutting group posted through the Cutting page is not a plan and never passes
through `CP7:PLAN_CAPACITY`; it consumes real capacity but is not subtracted by either apply (see Defect D1).

### 1.5 Quantification (capacity 60, concurrent 31 (v1) + 30 (v2))
- S1 (v1, 31) acquires `CP7:PLAN_CAPACITY`; S2 (v2, 30) blocks at S:445 (or earlier at a shared roll lock).
- S1: used=0, 31 ≤ 60 → Native draft, intent, commit.
- S2 resumes: `used` sees S1's intent (unposted group, `draft_id is distinct from p_draft`) = 31 → capacity_now 29 →
  30 > 29 → 40001 `CP7_PLAN_V2_CAPACITY_USED`, DETAIL `capacity_used_by_other_plans_pcs=31, capacity_now_pcs=29`.
  Committed total = 31 ≤ 60. **61 cannot be committed.**
- Reverse order (v2 30 first): S1 v1 sees used=30 → 31 > 30 → `CP7_PLAN_CAPACITY_USED` (or `CP7_PLAN_SOURCE_CHANGED`
  first at P:45 because the v2 Native draft changed the v1 Original's fabric source). Total 30.
- S1 rollback: S2 sees used=0 → commits 30. Exact fit: after 31 committed, a 29-piece v2 plan is accepted (60), 30 refused.
- Writer fixture names: `P19P_RACE_V1_HOLDS_V2_REFUSED`, `P19P_RACE_V2_HOLDS_V1_REFUSED`,
  `P19P_RACE_V1_ROLLBACK_FREES_CAPACITY`, `P19P_V1_V2_SHARED_CAPACITY` (`scripts/cp7_p19_plan_v2_cases.py:155-178,
  639-700`: `two()`, `capacity_split()` a = min(need, c−1), b = c−a+1; `cross()`).

---

## 2. Plan v2 — "memeriksa ulang live dalam satu transaksi"

- Live facts are **re-read, not trusted from the snapshot**, by `staged_live` (S:52-110), called at S:221 inside the
  apply transaction (and again after the Native writer): current product rows of the root (S:68-70), production policy
  now (S:71-73), finished stock grade A/B with `physical_at<=clk and system_created_at<=clk` (S:74-75), company WIP of
  model+size from posted groups not proven exhausted at the snapshot, batches of 50, >200 groups or non-COMPLETE
  normalisation → UNKNOWN (S:77-98), linked intents and groups posted outside the snapshot scope (S:99-102).
- Snapshot values stored on the draft (`staged_drafts.snapshot`, S:11-19, immutable S:19) and compared in
  `preflight_v2` live block (S:219-283): PRODUCT (S:222-227), POLICY KNOWN+ACTIVE (S:228-230), TARGET_PLANS after the
  boundary (S:233-237), LINKED_PLANS v1 rule (S:240-246), WIP (S:247-250), NEED
  `need_now = gap − max(0,(fg_now+wip_now) − (fg_snap+wip_snap))`, `total > ceil(need_now·den/num)` or need_now=0 →
  `CP7_PLAN_V2_NEED_CHANGED` (S:255-257), CAPACITY (S:262-271), material/rolls via live `material_pool`
  (`preflight.sql:5-20`, S:188-194), access re-read after every lock (S:430,444,446,449,454,461).
- "Freshness" is compared per item: `since = data_as_of`, `boundary = capture_marks.source_snapshot` (S:222) feed
  `after_snapshot`; the apply does **not** call the freshness RPC and does not require VERIFIED_SAME (by contract §0.5).
  Options/preview/apply all return `data_as_of`; apply outcome includes `live.checked_at` (S:466).
- Refusal: 40001, message = code, DETAIL JSON (S:277-282), no Native draft or intent survives (exception → rollback).
- Save-time static check `total > cut_limit or total > capacity_snapshot` → `CP7_PLAN_QUANTITY_EXCEEDS_NEED_OR_CAPACITY` (S:212).

---

## 3. Business Report v2 — "disegel sekali", finance from authoritative source, rights per call

- Seal = the single `report_publications` row inserted in the SUMMARY unit (R:407-411) under
  `CP7:REPORT_SERIES_V2:<actor>:<series>` (R:394) after checking `prior.revision = j.revision−1` (R:396, 40001
  `CP7_REPORT_REVISION_CHANGED`). `job_id unique` (R:42) → at most one publication per job; `unique(actor,request_id)`
  and `unique(actor,series_id,revision)` (R:52). `report_reads`, `report_sections`, `report_publications` have
  before-update/delete triggers `cp7_private.immutable_run()` (R:63-67; raises 55000 `CP7_RUN_IMMUTABLE`,
  `snapshot/bootstrap.sql:32-34`). `report_jobs` only progress columns may change (R:70-71); `check((state='DONE')=
  (publication_id is not null))` (R:28-29).
- Re-seal / regenerate under same id: `report_step` acts only when `state='RUNNING'` (R:435); a DONE/FAILED job is
  inert. Same request UUID with same payload → status only (R:299-303); different payload → `CP7_REPORT_REQUEST_CHANGED`
  (R:301); UUID known to v1 → refused (R:305-306); lookup of an unknown UUID closes it forever (`CLOSED_UNCOMMITTED`,
  R:331). Revisions get a new publication id in the same series.
- Finance/HPP source: `report_actuals` (R:238-251) reads finished stock in one statement at one clock and, only when
  `finance='INCLUDED'`, `cp7_analysis_native.financial_source(q, p_at)` (R:250) →
  `cp7_finance.workspace(dates)` = the accepted Native owner report for the Jakarta date of the read
  (`planning/analysis-finance.sql:24-55`; book signature over journals/lines/daily balances/cash accounts;
  `source_hash` stored as `financial_source_hash`, R:409). No other calculator.
- Rights (`report_finance_access`: role OWNER/ADMIN and `finance.reports.view`, preflight additionally
  `finance.period_close.manage`, R:85-89): checked at publish (R:316-317), at ACTUALS before the read (R:345-346) and
  for the close preflight (R:349-350), at SUMMARY (R:384-385), at every read: document (R:473-474), section (R:497-498,
  plus `access_epoch` hash, R:491-492), index (R:513-518). Every step compares the live access object with
  `access_at_request` and fails the job on change (R:436-438) → no publication (DONE requires publication_id).
  `financial_source` is security definer owned by `cp7_finance_read` (analysis-finance.sql:59), so the explicit gates
  are the only barrier; they are present on every path found.
- Wording: summary and sections write "Data analisis per … WIB", "bukan angka saat ini" (R:139-140, R:164-166);
  freshness in words (R:92-104); "Keuangan dan HPP tidak dimasukkan … Tidak ada angka pengganti." (R:176).

---

## 4. Reminders v2 — recheck before claim and before finish

- Claim `staged_claim` (M:800-885): locks request (M:814) → binding (M:820) → `CP7:RULE_EPISODES:CURRENT_SOURCE` (M:834);
  snapshot condition must still be the presented hash and ACTIVE at the snapshot (M:829-831); cooldown/quiet refused
  40001 without writing (M:842); **recheck now after the last lock** `staged_verdict` (M:849); `CONDITION_CHANGED`
  (live AR/AP facts differ) → 40001 (M:850); recheck recorded (M:851, `staged_rechecks` immutable M:80); any verdict
  other than STILL_OPEN → result `NOT_SENT` with verdict, no claim (M:853); STILL_OPEN → one claim per
  binding/episode/policy/occurrence (M:862-873).
- Finish `staged_finish` (M:887-937): same locks (M:898,904,905), claim row `for update` + fence (M:906-908),
  **recheck again** (M:913), recorded as phase FINISH (M:915); outcome `SUPPRESSED` when binding changed/disabled
  (M:919), verdict ≠ STILL_OPEN (`RECHECK_<verdict>`, M:920), policy changed (M:921), episode no longer active (M:923),
  cooldown/quiet now (M:924); only then `LOCAL_SINK_CAPTURED` (M:926). Claim rows move once CLAIMED→outcome
  (trigger `guard_staged_claim` M:107-118). So a reminder **cannot be marked done when the obligation changed in
  between**: RESOLVED_NOW/CHANGED_REVIEW_REQUIRED/NOT_FOUND_NOW/CONDITION_CHANGED all suppress.
- Verdict rules (M:528-604): production `need_now = need_snap − max(0, Δ(fg+wip))`, 0 → RESOLVED_NOW (M:548-549);
  product/policy/plan-after-snapshot → CHANGED_REVIEW_REQUIRED (M:550-555); WIP unknown → UNKNOWN_NOW; threshold →
  BELOW_THRESHOLD_NOW; fabric held on need fall or material moves/commitments after the boundary (M:559-565);
  accessory always UNKNOWN_NOW (M:575); AR/AP read live with v1 readers (M:579-594), paid → RESOLVED_NOW.
- Episodes: `staged_episodes` keyed by condition_key, one ACTIVE (unique partial index M:46), opened by a STILL_OPEN
  claim, resolved by a RESOLVED_NOW recheck, ACTIVE→RESOLVED only (trigger M:97-105); `staged_record` M:759-775.
  ACK/snooze exist only in v1 `attention.sql` (per-actor attention states NEW/ACK/SNOOZED/DONE, attention.sql:15-18);
  v2 has no ACK/snooze — cooldown and quiet hours come from `rule_policies` via `policy_timing` (rule-policy.sql).
- Obligations always live (`staged_obligations`, M:502-512, `READ_NOW_NOT_FROM_SNAPSHOT`).

---

## 5. Tanya AI v2

- Bound: `p_targets` array ≤ 20 distinct UUID:UUID keys (A:31-34, `CP7_AI_V2_TARGETS`); priority ≤ 25 (`limit 25`, A:48);
  `bounds {priority:25, selected:20}` in the reply (A:56); values copied from the retained index `plan_targets`, no page read.
- Time label: `data_as_of = jobs.captured_at` (A:55), `freshness` = full freshness contract with `evaluated_at` (A:44,56);
  client prompt (`src/nativeStagedAi.ts:77-87`) writes "Angka analisis adalah keadaan per <WIB> … bukan angka saat ini",
  freshness text, and for finance "dibaca <WIB> untuk tanggal …" or "Keuangan dan HPP tidak disertakan".
- Never writes: `ai_brief` is declared `stable` (A:25) and calls only stable functions: `cp7_schedule_native.access_now`
  (schedule.sql:26-27 stable), `require_kept` (analysis-stages.sql:1412-1413 stable), `freshness`
  (analysis-stage-snapshot.sql:127-128 stable) → `changes_since` (stable, :78-79). A stable PL/pgSQL function cannot
  execute DML (Postgres refuses "… is not allowed in a non-volatile function"). No logging table, no `requests` row:
  grep of A for insert/update/delete → none. The contract permits no AI write; none exists. Server calls no AI (A:10).
- Finance leak: brief carries `'finance','NOT_IN_SNAPSHOT'` (A:57). Client reads finance only via
  `erp_cp7_get_finance_report_v1` (`src/NativeStagedAiPanel.tsx:34`), which is gated server-side by
  `cp7_finance.access_now`: `finance.reports.view` and role OWNER/ADMIN (`finance/read.sql:16-19`), preflight only with
  `finance.period_close.manage` (read.sql:49) — the **same predicate** as `report_finance_access` (R:85-89). The client
  checkbox (`financeAccess.ownerReports`) is cosmetic; a STAFF caller gets 42501 from the RPC. No leak found.

---

## 6. PL-5 B history yield

- Versioned policy: `cp7_yield_policy.policies` (H:15-27): `revision unique`, `state ACTIVE|PAUSED`, `window_days`,
  `min_groups`, `min_cut_pcs`, fixed `confidence='0.90'`, `z='1.2815515655446004'`, `method=WILSON_SCORE_ONE_SIDED_LOWER_BOUND`,
  `rounding=FLOOR_PERMILLE`, `levels={PRODUCT_SIZE,MODEL}`; reason, actor, actor_role OWNER/ADMIN, request_id;
  immutable (H:40-43). Save `apply` (H:85-137): OWNER/ADMIN (H:47-54) + `master.product.manage`
  (`identity/bootstrap.sql:45-58`), request lock + `CP7:YIELD_POLICY` lock (H:94,112), `expected_revision` must equal
  current (40001 `CP7_YIELD_POLICY_REVISION_CHANGED`), confidence must be "0.90" (H:110). `workspace` shows the decided
  package 180/5/200 as `decided_package` and state `PENDING_POLICY_VALUE` until a revision exists (H:66-83).
- Reader `history_source` (H:236-346): no policy → `PENDING_POLICY_VALUE` (H:246-248); PAUSED → `POLICY_PAUSED` (H:252);
  target/model changed → UNKNOWN (H:253-256). Window: `first_day = WIB date − window_days + 1` (H:251); candidates are
  posted groups of **this model only** (`po.model_id = p_model`, H:265-276) with a PL-8 exhaustion proof under the
  current kernel captured in the window; finish date = last physical event ≤ clock (H:191-203); a group counts only if
  `model_id = p_model` and every posted QC went to this model (`qc_models <@ [p_model]`, H:295), every pool spent, and
  finish date ≥ first_day (H:295-297). Level PRODUCT_SIZE: pools of the target's size whose QC roots are exactly the
  target root (H:298-299); level MODEL: all pools of the model's groups; MODEL is `NOT_EVALUATED` once PRODUCT_SIZE is
  sufficient (H:280-281). >200 candidates at a level → UNKNOWN `HISTORY_GROUP_LIMIT` (H:271,276,278-279). Sufficient =
  `groups ≥ min_groups and cut ≥ min_cut_pcs` (H:305). Output numerator = k (permille), denominator 1000 (H:340).
- Wilson lower bound `wilson_permille(x,n)` (H:148-170): floating-point first guess (H:154) then exact integer fix-up
  (H:155-168) for the largest k with `1000·L ≥ k`, L = (2x+z²−z·√(z²+4x(n−x)/n)) / (2(n+z²)). Verified numerically
  (Python Decimal, 60 digits, exhaustive n<400 plus spot checks): **180/200 → 869 (0.869, proposal "±86,9%")**,
  190/200 → 926, 90/100 → 854, 45/50 → 832, 1/1 → 378, 0/200 → 0, 200/200 → 991, 1000/1000 → 998, 10⁶/10⁶ → 999;
  zero mismatches against exact arithmetic. Rounding is down (floor). All-good samples give n/(n+z²) < 1, floored ≤ 999:
  **100% can never be produced.** Plan cut for need 100 at 869‰ = ceil(100·1000/869) = 116 (proposal says 116).
- Plan use: `preflight` (P:55,101-108) and `preflight_v2` (S:162,206-212): history AVAILABLE → `HISTORY_NATIVE`
  numerator/denominator, planner estimate then refused `CP7_PLAN_NEW_START_YIELD_HISTORY_AVAILABLE` (P:62, S:168);
  otherwise estimate A (`PLAN_ESTIMATE_REVIEWED`, must be in `reviewed_assumption_ids`); otherwise UNKNOWN with
  `cut_limit = ceil(need)` and `NEED_CAP_YIELD_UNKNOWN_NOT_ASSUMED_100_PERCENT`, good/unresolved null (P:106-107,130-132).
  History is read live in the apply transaction (P:55 inside preflight at C:76/98; S:162 at S:452/459).

---

## 7. "Yield never 100%" across baseline/netting/schedule/fabric/accessory

- WIP projection: `cp7_wip.project_yield` (`wip/yield.sql:3-50`) requires an explicit selected policy per position
  (basis CONFIRMED_PLAN|HISTORY|ASSUMED, `den>0 and num<=den`); a position without a selected yield is
  `quality UNKNOWN, reason YIELD_NOT_SELECTED` → excluded from allocation as `ETA_OR_YIELD_UNKNOWN`
  (`baseline/allocation.sql:125-126`). No default 1.0 anywhere in these kernels.
- Schedule plan: `yield_numerator/denominator` both null or both set, `den=0 or num>den` refused
  (`planning/schedule.sql:96-100`); equality (100%) is **allowed as an explicit ASSUMED selection** (labelled).
- Netting: allocation UNKNOWN unless `schedule_state=SELECTED_ASSUMPTIONS` (`netting.sql:383-384`).
- New start: PL-5 (section 6); planner estimate A also allows numerator = denominator (P:60, S:166) per the 7 Oct rule
  "bagus ≤ potong" — explicit, reviewed, not assumed.
- Fabric: gross = `conditional_gap_pcs × qty_per_good_pcs` (`fabric-requirements.sql:198`); accessory: gross =
  `conditional_gap_pcs × qty_per_good_fg_base` (`material-requirements.sql:68`). Both are per **good** piece on the
  good-piece gap; no yield (history or estimate) is applied; waste must be inside the recipe/BOM factor. The plan's
  roll `qty_issued` is operator-chosen and only checked against pool availability (P:89-92, S:188-192), never derived
  from a yield.

---

## 8. As-known cutoff — which columns

- Single-path snapshot: FG movements `physical_at<=c.at and system_created_at<=c.at`; sales
  `created_at<=c.at and sale_date<=c.at` (`snapshot/sources.sql:44-45,54`; `planning/history-source.sql:33`) → economic
  **and** recording cutoff. Demand history rows carry `known_at`/`effective_at`, both cut (`demand/history.sql:38-60`;
  `planning/analysis-stages.sql:210-239`).
- Staged capture: `capture_marks.source_snapshot = pg_current_snapshot()` taken in the statement that reads the reference
  (`analysis-stages.sql:2070-2073`); "after the boundary" = recorded later OR written by a transaction not visible in
  that snapshot (`after_snapshot` S:113-121; `changes_since` analysis-stage-snapshot.sql:78-125; reminders M:217-232).
- Policies as-known by recording time: schedule `recorded_at<=p_at` (`schedule.sql:128`), fabric recipes
  `recorded_at<=p_at` (`fabric-requirements.sql:87`), demand profiles `recorded_at<=p_at` (`profile.sql:43`), accessory
  BOM `created_at<=p_at` (`material-requirements.sql:11`), products `created_at<=captured_at` (`netting.sql:21`).
- Production facts use **physical time only**: `cut_at<=`, `picked_up_at<=`, `physical_at<=` (`wip/source.sql:8,23,31,43,
  65,71,82,87,92,116`; `supply-source.sql:294,301,370`); flags by `created_at` (wip/source.sql:121); fabric roll stock
  `physical_at<=p_at` only (`fabric-requirements.sql:139-146`). No `system_created_at` cutoff there.
- Live rechecks (`staged_live` S:74-75) use both columns for FG; v2 reminder material moves use `system_created_at` + xmin (M:224).

---

## 9. Suspected defects / observations

D1 (medium-low) — v2 live capacity recheck subtracts only *plan* intents (S:264-268; `posted_outside_snapshot` joins
`cp7_plan_native.intents`, S:100-102). A manual cutting group of another model posted after the snapshot adds real
WIP load but is not subtracted; `capacity_now` stays at the snapshot value. Contract §3 phrases the rule as "potong
semua rencana lain", so this is by-design wording, but "memeriksa ulang live" is partial for capacity. Direction: can
over-admit versus a fresh analysis (not versus other plans). F01's two-ratification property is unaffected.

D2 (low) — v1 apply has no calendar-expiry check: `free_capacity_pcs` is the Original's `new_start_capacity` (P:52) and
v1 relies only on `source_state=UNCHANGED` (P:45); time passing does not change the source hash, so a v1 plan can be
ratified after the selected calendar's `through_at` has passed. v2 refuses `CP7_PLAN_V2_CAPACITY_EXPIRED` (S:270).
v1 is declared "unchanged" by the contract; recorded as a v1 residual.

D3 (low, design) — PL-5 parameters 180/5/200 are not pinned: any OWNER **or ADMIN** with `master.product.manage` can
store `window_days` 1..3660, `min_groups` 1..1000, `min_cut_pcs` 1..10⁶ (H:18-20, 100-104). Only confidence/method/
rounding/levels are fixed. With 1/1/1 a single 1-piece group yields k=378‰. The owner asked for a versioned policy,
so configurability is intended; the question is whether ADMIN may alter the owner's numbers.

D4 (observation) — Estimate A accepts numerator = denominator (100%) (P:60; S:166) — matches the 7 Oct rule
"bagus ≤ potong"; explicit and reviewed, not assumed.

D5 (observation) — Fabric and accessory needs do not apply any yield (section 7). If recipes/BOM are entered per good
piece without waste, material need is understated by the yield loss; PL-5 history yield never reaches material need.

D6 (observation) — Reminder v2 accessory conditions are never claimable (always `UNKNOWN_NOW`, M:575). Conservative;
matches contract §5 wording "aksesori tidak diketahui".

D7 (observation) — Production-fact readers have no recording-time cutoff (section 8). Stored runs are immutable and
the staged boundary uses a pg_snapshot, so the "temporal non-leakage" oracle holds for stored results; a re-read at
an old `p_at` is not reproducible after a backdated production row.

D8 (observation) — `CP7:PLAN_CAPACITY` is one global key for the whole installation (all actors/runs); correct for one
centre, serialises every apply in the factory.

---

## 10. Runtime probes (expected outcomes from source)

P1 F01 race. Fixture: `two()`/`capacity_split()` in `scripts/cp7_p19_plan_v2_cases.py:155-178`; two targets of the same
run, capacity c (use c=60, a=31, b=30). Session 1: `begin; select public.erp_cp7_apply_plan_action_v1('{"draft_id":"<D1>",
"expected_revision":"1","explicit_review":true,"reason":"r"}'::jsonb,'<U1>'::uuid);` (hold). Session 2:
`select public.erp_cp7_apply_plan_action_v2('{"draft_id":"<D2>","expected_revision":"1","explicit_review":true,
"reason":"r"}'::jsonb,'<U2>'::uuid);` → blocks (`pg_stat_activity.wait_event_type='Lock', wait_event='advisory'`).
Session 1 `commit` → session 2 fails SQLSTATE 40001, message `CP7_PLAN_V2_CAPACITY_USED`, DETAIL
`capacity_used_by_other_plans_pcs=31, capacity_now_pcs=29, selected_new_pcs=30`. Check
`select count(*) from cp7_plan_native.intents` = 1 and Σ qty_pcs over intents' drafts = 31 ≤ 60. Variant rollback →
session 2 succeeds, total 30. Reverse order (v2 holds 30, v1 31) → 40001 `CP7_PLAN_CAPACITY_USED` or
`CP7_PLAN_SOURCE_CHANGED`; total 30. Control: after 31 committed, v2 draft of 29 → `NATIVE_DRAFT_CREATED` (total 60);
30 → refused.

P2 D1 residual. Snapshot capacity C. After the snapshot, post a manual cutting group of another model (Cutting page
writer, posted) with pieces X. `erp_cp7_preview_plan_action_v2(D)` for a draft with total=C → CAPACITY `OK`,
`capacity_now_pcs=C`; apply accepted. A fresh staged analysis shows capacity C' < C. Confirms the documented scope.

P3 Plan v2 live need. Save draft from snapshot with gap g; post FG grade A movement +k for the target root;
`erp_cp7_preview_plan_action_v2(D)` → `live.increase_pcs=k`, `need_now_pcs=g−k`, NEED `REFUSED/CP7_PLAN_V2_NEED_CHANGED`
when total > ceil((g−k)·den/num); `erp_cp7_apply_plan_action_v2` → 40001 same code; `erp.cutting_groups` count and
`cp7_plan_native.intents` unchanged. Policy flip to PAUSED → `CP7_PLAN_V2_POLICY_CHANGED`.

P4 Report seal. `erp_cp7_publish_report_v2(payload,U)` → `RUNNING`, `unit_count=page_count+3`; `erp_cp7_step_report_v2(U)`
repeated → `DONE`, `publication_id` set. As the table owner: `update cp7_analysis_stage.report_publications set title='x'
where id=P` → ERROR 55000 `CP7_RUN_IMMUTABLE`; `delete` same. `erp_cp7_step_report_v2(U)` again → DONE unchanged.
`erp_cp7_publish_report_v2(same payload,U)` → status, no second job; different payload → `CP7_REPORT_REQUEST_CHANGED`.
`select count(*) from cp7_analysis_stage.report_publications where job_id=J` = 1.

P5 Report finance rights. STAFF: `erp_cp7_publish_report_v2({...finance:'INCLUDED'})` → 42501 `CP7_REPORT_V2_FINANCE_ACCESS`.
OWNER INCLUDED job; revoke `finance.reports.view` between steps → next step: job `FAILED`, `failure_code=
CP7_REPORT_ACCESS_CHANGED`, `publication_id` null. Non-entitled actor reading an INCLUDED publication →
42501 `CP7_REPORT_UNAVAILABLE`; `erp_cp7_list_reports_v2` omits it. `financial_source_hash` equals
`cp7_analysis_native.financial_source(period, actuals_read_at)->>'source_hash'` recomputed for the same book.

P6 Reminders. Build set: `erp_cp7_step_reminder_conditions_v2(run)` until `DONE`; pick an ACTIVE `PRODUCTION_GAP:<target>`.
`erp_cp7_claim_reminder_v2({run_id,identity_hash,condition_key,condition_hash,binding_id},U1)` → `outcome=CLAIMED`,
`recheck.phase=CLAIM, verdict=STILL_OPEN`, episode ACTIVE. Post FG covering the need. `erp_cp7_finish_reminder_v2(
{run_id,identity_hash,claim_id,fence,outcome:'LOCAL_CAPTURE'},U2)` → `claim.status=SUPPRESSED`,
`reason=RECHECK_RESOLVED_NOW`, recheck phase FINISH, episode RESOLVED. New claim on the same key → `outcome=NOT_SENT,
verdict=RESOLVED_NOW`. AR: pay the invoice between claim and finish → `SUPPRESSED RECHECK_RESOLVED_NOW`; change its due
facts → `RECHECK_CONDITION_CHANGED`. Race: two sessions claim the same key → one CLAIMED, other 40001
`CP7_LOCAL_AMBIGUOUS_EPISODE_NO_NEW_OCCURRENCE`.

P7 AI. `begin; set transaction read only; select public.erp_cp7_get_staged_ai_brief_v1(run,'["<k>"]');` → succeeds
(a write would raise 25006). `select sum(n_tup_ins+n_tup_upd+n_tup_del) from pg_stat_user_tables where schemaname like
'cp7%'` unchanged before/after. 21 keys → `CP7_AI_V2_TARGETS`; `jsonb_array_length(priority) <= 25`;
`finance='NOT_IN_SNAPSHOT'`; `data_as_of = jobs.captured_at`. STAFF: `erp_cp7_get_finance_report_v1(q)` → 42501
`CP7_FINANCE_ACCESS_DENIED`/`CP7_FINANCE_OWNER_ADMIN_REQUIRED`.

P8 PL-5. (a) No policy: `erp_cp7_get_history_yield_policy_v1()->>'state'='PENDING_POLICY_VALUE'`; preview
`new_start_yield.basis='UNKNOWN'`, `cut_limit_pcs=needed_pcs`, `expected_good_pcs=null`. (b)
`erp_cp7_save_history_yield_policy_v1({expected_revision:'0',state:'ACTIVE',window_days:'180',min_groups:'5',
min_cut_pcs:'200',confidence:'0.90',reason:'...'},U)` as OWNER → revision 1; as STAFF → 42501; confidence '0.95' →
`CP7_YIELD_POLICY_CONFIDENCE_FIXED`; `update cp7_yield_policy.policies …` → 55000. (c) `select
cp7_plan_native.wilson_permille(180,200)`=869, `(200,200)`=991, `(1,1)`=378, `(1000000,1000000)`=999, `(0,200)`=0.
(d) Fixture: 5 proven-exhausted groups of the model, same root+size, Σcut 200, Σfg 180 →
`cp7_plan_native.history_yield(target,model)`: `status=AVAILABLE, level=PRODUCT_SIZE, numerator='869', denominator='1000'`;
preview for need 100 → `cut_limit_pcs='116'`, `cut_limit_basis=NEED_AT_STATED_YIELD`; a payload with `new_start_yield` →
`CP7_PLAN_NEW_START_YIELD_HISTORY_AVAILABLE`. (e) 4 groups → PRODUCT_SIZE `INSUFFICIENT_SAMPLE`, MODEL evaluated;
a group whose PO is another model → not counted (`excluded.unattributed`); finish 181 days ago → `excluded.outside_window`.
(f) policy PAUSED → `status=POLICY_PAUSED`, estimate A accepted. (g) `erp_cp7_get_history_yield_policy_v1()` as a
non-OWNER/ADMIN still readable (view rights), `manage_allowed=false`.

---

## 11. Not determined from source

- `public.erp_save_cutting_group_before_sewing_v2` (Native writer in `supabase/migrations`) was not read; assumed to
  write only a draft group (both applies refuse if `material_issue_posted` is not false, C:91 / S:456).
- `erp.get_my_access_v1()` body not read (assumed JWT-based like `erp.has_permission`, which uses `auth.uid()`,
  `supabase/migrations/20260902104937_…:589-615`); the gates rely on that.
- Whether the staged analysis' `existing_load_minutes` includes unposted drafts (only affects how conservative
  `used` is; direction is safe).
- Actual PostgREST isolation is asserted by code (`read committed` check) but not observed.
- Timing at 5,000 targets (`staged_live` 200-group WIP limit, history 200-candidate limit) not evaluated.
- Frontend "terkini" absence checked only by grep of `src/nativeStagedAi.ts`.
