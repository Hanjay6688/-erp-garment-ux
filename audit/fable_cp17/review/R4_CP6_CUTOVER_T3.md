# R4 — CP6 families AC..BF on the final code: cutover/opening, advances, tutup buku, dated HPP, T3 package + rollback

Reviewer: read-only source reviewer for Fable (round cp17-20261014). Candidate: commit `0b7049d9` at
`scratchpad/frozen` (read-only). Method: static source reading of `supabase/release/cp6-t3/*` (30 files, the installed
text), `supabase/release/cp6-t3-rollbacks/*`, the fixture baseline `supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz`
(decompressed to scratchpad `fable7/fixture.sql`, line numbers below prefixed `FIXTURE:`), `supabase/migrations/*`,
workflows, and the docs named in the task. Paths below are relative to `frozen/`; `R/20xx` = `supabase/release/cp6-t3/<stamp>_erp_v2_6_20xx_*.sql`,
`RB/20xx` = `supabase/release/cp6-t3-rollbacks/<stamp>_erp_v2_6_20xx_*.rollback.sql`, `M/…` = `supabase/migrations/…`.
No database was run; every "would" statement is a prediction from source and is labelled UNCONFIRMED unless the text itself is the proof.

Scope rule applied: the **final body** of a function is the last `CREATE OR REPLACE` in the order fixture → migrations (stamps not
re-shipped by the package) → release AC..BF (stamp order), plus the dynamic `pg_get_functiondef … execute replace(...)` patches in
M/20t, M/20u, M/20ab (these rewrite a body without a `CREATE` statement; see C.4).

---

## A) CP6_HOLD findings → status in the final code

Sources: `docs/cp6-final-audit-checkpoint.md` (16 Sep, "Blocker" table) and `docs/cp6-final-successor-independent.md`
(successor, "Temuan dan batas penerimaan" + "Aturan tanggal dan CSV yang tetap terbuka"). Decision ids: addendum
`docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md` (D01–D06), annex C6 rev4 (`…_LAMPIRAN_C6.md`), D11 table
`docs/cp6-d11-kebijakan-dan-gbd03.md`, master M (quoted in `docs/cp6-pr32-acceptance-and-r10-scope-20260929.md`).

| # | CP6_HOLD finding (doc) | Status on 0b7049d9 | Evidence (file:line) / decision id |
|---|---|---|---|
| H1 | UI asli + layanan disposable: `src/config/runtime.ts` only accepts UAT hostnames; localhost refused (`UAT_URL_INVALID`, `UAT_PROJECT_REF_MISMATCH`) — checkpoint 1 | **RESOLVED by an explicit third mode, not by loosening.** `RuntimeMode` now has `'DISPOSABLE_TEST'` (`src/config/runtime.ts:4`, type `:41-46`); a disposable build is accepted only from the loopback page origin `http://127.0.0.1:4176` (`:193-196`, `DISPOSABLE_BUILD_REQUIRED`) and only against `http://127.0.0.1:<port>` with a port in 32768–65535 excluding the Supabase defaults (`:209-214`, `DISPOSABLE_TARGET_FORBIDDEN`). UAT errors at `:126`, `:138`, `:153` unchanged. Owner path recorded in `docs/cp6-au-r1-handoff.md:1954`. | design decision in handoff §22.6/§1954; browser flows run on it: `.github/workflows/cp6-t3-release-package.yml:84-88` (`browser` matrix key) and `scripts/cp6_t3_browser.py` |
| H2 | Browser spec `tests/browser/cp6-laundry-qc.spec.ts` intercepts backend responses (mock) — checkpoint 1 | **PARTIALLY RESOLVED.** The mock spec still exists (15 `route/fulfill/intercept` hits in `tests/browser/cp6-laundry-qc.spec.ts`). Real-service browser evidence now exists separately: AU/BF browser flows in the T3 package workflow (`cp6-t3-release-package.yml:84-88`), `scripts/cp6_bb_browser.mjs`, `cp6_bc_browser.mjs`, `cp6_bd_browser.mjs`, `cp6_bd_completion_browser.mjs`, `cp6_be_browser.mjs`, `cp6_bf_browser.mjs`. The mock spec is contract evidence only. | — (no owner decision needed; the HOLD asked for real-service evidence, which exists in CI scripts; not re-run here) |
| H3 | CSV/import transport: producer/parser/upload of the real app unproven — both checkpoints | **CODE EXISTS; acceptance outside this static review.** `src/ConnectedInitialImportPage.tsx:333-334` produces CSV templates (`text/csv;charset=utf-8`), `:369-370` upload help ("Simpan dari Excel sebagai CSV UTF-8"). Backend: `erp.save_initial_import_action_v1` (R/20ar:…, replaced by later families), validation `erp._validate_migration_batch_base` final at R/20be:6332. | Annex C6 §0 item 2 (ALL 22 is a CP6 obligation; `22-state mapping: UNVERIFIED` is the auditor's job). Prior Fable r13 verdict: "CP6 CLOSED claim VERIFIED for contract scope" with `not_tested_by_fable: F3/D08 browser` (gptaudit `CP6_COMBINED_INDEX.json` → `fable_round13_closure_verification`). |
| H4 | Role coverage: 95 HTTP checks covered six role classes on CP6 facades only | **PARTIALLY RESOLVED.** Each later family ships an Auth/HTTP matrix in its probe (`scripts/cp6_bb_probe.py`…`cp6_bf_probe.py`; writer handoff `docs/cp6-combined-release-writer-handoff-20260928.md:77` "8 Auth/HTTP"). Not a full role × module × action matrix. | annex C6 ACC-D06 / LAU-T33 rows (BASELINE: existing rights inventory) |
| H5 | Sales/Finance/payroll pages use local state (`src/SalesPages.tsx`, `src/FinancePages.tsx`); no owner contract deferring them found | **ACCEPTED BY CONTRACT (deferred to CP7), and CP7 code now exists.** `docs/cp6-pr32-acceptance-and-r10-scope-20260929.md` quotes master M:1728 (AUD-G04 → "CP7 full dummy sales") and M:6289/6301. `src/SalesPages.tsx:8,30,92,128-129` is still the simulation page ("SIMULASI UX · Belum menulis backend"), but CP7 connected pages exist: `src/ConnectedSalesPage.tsx`, `SalesDraftPanel.tsx`, `SalesPaymentPanel.tsx`, `SalesReturnPanel.tsx`, `SalesChainReversalPanel.tsx` (+ `.dom.test.tsx`) and workflow `.github/workflows/cp7-p11-sales.yml`. | M:1728 (owner master, hash `f21ac703…` identical to addendum §1) |
| H6 | Nota FG legacy: `src/ConnectedFgHandoffBoundary.tsx` deliberately read-only | **UNCHANGED BY DESIGN.** File still present (`src/ConnectedFgHandoffBoundary.tsx`); Final SKU goes through QC facade `erp_post_final_sku_allocation_v1` (annex C6 §5 row L1). | annex C6 §5 L1 (BASELINE) |
| H7 | **CP6-IMPORT-REFERENCE-PREVIEW-01** (P3): `validate_migration_batch` marks an opening MATERIAL row VALID although `location_code` is unknown; prepare then fails P0001 | **RESOLVED (main case), residual in D) R4-04.** Final `erp._validate_migration_batch_base` (R/20be:6332-6595) has a reference table at `:6540-6556` with `('location_code','locations','location_code','LOCATION',array['MATERIAL_ROLL','OPENING_BALANCE_ITEM'])` (`:6544`); an unknown code that is neither in `erp.locations` nor a VALID staged `LOCATION` row yields the row error `'Unknown or invalid staged reference: location_code = …'` (`:6552-6556`). MATERIAL_ROLL additionally requires an active `RAW_MATERIAL_WAREHOUSE` (`:6497-6501`). | — |
| H8 | **Tanggal laporan HOLD** (12 historical-date observations; recost/queue posted on the process day; `HISTORICAL_READY` controls) | **ACCEPTED BY OWNER DECISION D01 and implemented in AY/AZ/AW.** D01 §3 (addendum lines "## 3. D01"): open period → correction travels with the unit, dated `max(E, movement date)`; closed E → one journal per part with economic date E posted on the recognition day (§3.4). Code: `erp.sync_po_hpp_to_gl` R/20ay:703-716 (comment and cap logic), per-date legs `:749-760`, `:1006-1013` (COGS from the sale date); material side R/20az header `:1` and marker `:1278` ("WIP from the cutting day, material until then"); report confidence from the close engine `erp.period_readiness_v1` R/20aw:687, snapshot `erp.get_owner_financial_snapshot_v2` R/20aw:947-1000. The original 12 HOLD observations are preserved as frozen history (`docs/cp6-au-r1-handoff.md` §23.6; gptaudit index CP6-13 `NEW_C0_MONETARY_DATE_25_PASS_FROZEN_HISTORY_PRESERVED`). | **D01** (ratified 25 Sep, addendum §9) |
| H9 | Open-period book-date policy for the whole correction family not chosen; "jangan hanya menambal UI" | **ACCEPTED BY OWNER DECISION D01 §3.2–3.5** (max(E, movement date); ADJUSTMENT_DATE rule §3.3; closed boundary §3.4; cross-period presentation §3.5). Capacity-by-date for advances is **D02** (R/20ba:738 `BA_ADVANCE_DATED_CAPACITY`, `erp.initial_prepayment_dated_floor_v1`, `erp.manage_initial_prepayment_v1`). | **D01, D02** |
| H10 | Nominal/recovery path — independent PASS limited; "bukan bukti UI invoice/sales sudah tersambung" | **UNCHANGED SCOPE** (sales UI = CP7, see H5). Invoice/recost backend is in AO/AZ (`erp.post_material_supplier_invoice`, `erp.post_material_purchase_cost_correction` R/20az:1192). | M:1728 |
| H11 | Checkpoint-1 "Pemeriksaan native/Reuse 460" items (REUSED_EVIDENCE caveats) | Evidence-process items, not code. The final package evidence is the T3 workflow (`cp6-t3-release-package.yml`) + rollback cycle (`cp6-t3-rollback.yml`). Not re-run here. | — |

Prior Fable disposition of the CP6 finding register (gptaudit `CP6_COMBINED_INDEX.json`): CP6-07 (advance capacity, D02) CLOSED on a095a9d; CP6-18 (WIP product binding, D03) CLOSED (`BA_WIP_OUTPUT_PRODUCT_BOUND` R/20ba:593, `BA_WIP_OUTPUT_SOURCE_MISMATCH` R/20ba:601; re-shipped R/20bb:4793/4801, R/20bd:6528/6536); CP6-09 (opening overlap identity) CLOSED on a095a9d; CP6-24 (double filing on the same close date) CLOSED — final `erp.close_accounting_through` R/20ba:1019-1021 raises `CLOSE_ALREADY_CLOSED`; CP6-12 rollback qualification `VERIFIED_TECHNICAL_AC_BA_ROLLBACK_T3_PREP`; CP6-17 (ALL 22) `CONTRACT_DECIDED_COVERAGE_OPEN`; r13 verdict "CP6 CLOSED claim VERIFIED for contract scope on product 434b182; production_go=false"; r14 "BF accepted on Fable oracles".

---

## B) T3 MANIFEST vs files vs rollbacks

### B.1 Counts and hashes (computed in this review, `python3 -I`, sha256 of the bytes on disk)

| Check | Result |
|---|---|
| `supabase/release/cp6-t3/MANIFEST.json` `files[]` | **30** entries, keys AC..BF; `format` `CP6_T3_RELEASE_PACKAGE_V1`, `label` `T3_PREP`, `production_go:false`, `release_evidence:false`, **`rollbacks: "NOT_TESTED"`**, `pins.file docs/evidence/cp6-t3/release_pins.json` sha `01790c42…` |
| `.sql` files in `supabase/release/cp6-t3/` | **30**; set difference manifest↔directory in both directions = ∅ |
| `package_sha256` of each of the 30 files | **30/30 match** the bytes on disk |
| `source_sha256` of each listed source (`supabase/migrations/*` for AC..AV; `supabase/release/cp6-t3-src/*` for AW..BF) | **30/30 match** |
| `docs/evidence/cp6-t3/release_pins.json` | 130 872 bytes, sha256 `01790c42…` = manifest pin; `status: CAPTURED_AND_INSTALLED`; 30 entries, each with `source_sha256`, `package_sha256`, `subs` count and `status: PASS`; AW..BF sources are `supabase/release/cp6-t3-src/*` |
| `supabase/release/cp6-t3-rollbacks/ROLLBACKS.json` | `format CP6_T3_ROLLBACKS_V1`, **30** rollback entries (AC..AV `RELEASE_VARIANT` from `supabase/rollbacks/*`, AW..BF `FROM_CAPTURE`), order `BF,BE,…,AC`; **30/30 `sha256` match**, 20/20 `source_sha256` match, 30/30 `package_sha256` match the forward files; `capture.blob_sha256` matches `docs/evidence/cp6-t3/rollback_capture.json` |
| `.rollback.sql` files in `cp6-t3-rollbacks/` | 30 (+ `ROLLBACKS.json` = 31 entries in the directory) |
| Build provenance | forward AW..BF built by `scripts/cp6_t3_awx_release.py` from `supabase/dev/cp6_*_t1_family.sql` (header R/20ay:3); rollbacks by `scripts/cp6_t3_rollback.py` from the forward file + `rollback_capture.json` (header RB/20ay:3) |

"Exactly the objects installed": the MANIFEST enumerates **files and hashes, not objects**. The object inventory lives in the
rollback side: each forward file creates `erp.cp6_v2620xx_rollback_capsule` with the pre-image of every function it replaces
(R/20ay:144 `create table erp.cp6_v2620ay_rollback_capsule(like erp.cp6_v2620an_rollback_capsule including all)`), and each rollback
verifies cardinality and sha/ACL/owner of the restored set (RB/20ay:185-192). My regex inventory of the forward text (functions /
tables / views / triggers / indexes) agrees with those capsule cardinalities for the five spot-checked pairs (B.3). Mismatches found:
**none in content**; **two stale metadata items**: (i) `MANIFEST.json.rollbacks = "NOT_TESTED"` is a literal in
`scripts/cp6_t3_release_package.py:337` (and its docstring `:28`) and is never updated although `ROLLBACKS.json` exists and the writer
reports a 147/147 rollback cycle (`docs/cp6-combined-release-writer-handoff-20260928.md:84`); (ii) workflow comments still say
"24 files" and "29-file package" (`.github/workflows/cp6-t3-release-package.yml:74,84`; `cp6-release-readiness.yml:79,89`) while the
step labels say 30. See D) R4-01.

### B.2 What a forward file and its rollback guarantee (common skeleton, cited on AY)

Forward (R/20ay): closed-admission guard `:7-14` (`PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE`: session must be postgres/supabase_admin,
`datallowconn=false`, no other backend); locks `erp.schema_migrations`, `supabase_migrations.schema_migrations` and every `erp` table
`:15-21`; refuses if its marker/capsule/tables already exist `:22-26` (`AY_EXACT_PREDECESSOR_WITHOUT_SUCCESSOR_REQUIRED`), if any later
stamp exists `:27-30`, if any prior AC..AX ledger row sha differs `:31-43` (`AY_PRIOR_PLATFORM_DRIFT`), catalog fingerprint guard `:44+`.
Rollback (RB/20ay): same admission `:6-14`; marker + ledger-row sha of its own file `:22-29` (`AY_ROLLBACK_PLATFORM_OR_SUCCESSOR`,
refuses if any stamp > own exists → only the last file may be rolled back); prior platform drift `:30-41`; catalog guard `:42-108`;
**pre-use check** `:172-184`: per-table row-hash of every `erp` table must equal the capsule's `after` snapshot, and both ledgers'
hashes must equal `platform_before`/`markers_before`, else `AY_POST_USE_ROLLBACK_REFUSED` / `AY_PRIOR_HISTORY_DRIFT`; **function restore**
`:185-193` from the capsule with sha/ACL/owner equality and exact count (`<>2 → AY_FUNCTION_RESTORE_MISMATCH`); drops `:194-198`; ledger
deletes `:199-200`; post-catalog guard `:201-267`; **restored-data check** `:268-280` (`AY_EXACT_RESTORE_FAILED` if any table hash or
ledger hash differs from `before`). This satisfies Pro Max §16.6 "rollback refuses after transactions" by construction (any committed
row changes the table hash), and the cycle script tests it (`scripts/cp6_t3_rollback.py:22-28,521-553,632-639`: one committed business
transaction — customer-receivable opening posted — then `POST_USE_<k>_ROLLBACK_REFUSED` expected for each file).

### B.3 Five pair spot-checks (forward DDL vs rollback statements)

| Pair | Forward creates (R/) | Forward replaces (functions pre-imaged in capsule) | Rollback (RB/) | Verdict |
|---|---|---|---|---|
| **AW** close engine | tables `erp.accounting_close_filings_v1` `:177`, `erp.laundry_rate_owner_estimates_v1` `:189` (+capsule `:144`); triggers `:1071,1073,1075,1077`; 11 new fns (`period_blockers_v1` `:340`, `period_readiness_v1` `:687`, `period_completeness_from_v1` `:705`, `accounting_close_preflight_v1` `:725`, public `erp_accounting_close_preflight_v1` `:1039`, `erp_close_accounting_through_v1` `:1047`, …) | 2: `erp.close_accounting_through` `:782`, `erp.get_owner_financial_snapshot_v2` | drops 4 triggers `:194-197`, 11 fns `:198-208`, 2 tables + capsule `:209-211`, ledger rows `:212-213`; restore count `<>2` `:185-192` | **exact inverse** (2 restored = 13−11) |
| **AY** dated HPP | tables `po_hpp_gl_lot_state_v1` `:174`, `po_hpp_gl_material_state_v1` `:183` (+capsule); new fns `po_hpp_gl_leg_add_v1` `:192`, `po_hpp_gl_pocket_by_pool_v1` | 2: `erp.rebuild_po_hpp`, `erp.sync_po_hpp_to_gl` | drops 2 fns `:194-195`, 2 tables + capsule `:196-198`, ledger `:199-200`; restore count `<>2` | **exact inverse** |
| **BA** audit closure | table `initial_import_wip_output_identity_v1` `:174` (+capsule); new fn `initial_prepayment_dated_floor_v1` | 10 (incl. `close_accounting_through` `:1002`, `complete_initial_import_wip_v1`, `manage_initial_prepayment_v1`, `post_opening_balance` `:215`, `save_laundry_qc_action_v1`, `sync_material_cost_revaluation`, `assert_new_stock_cutoff_coverage_v1` `:2521`, …) | drops 1 fn `:194`, table + capsule `:195-196`, ledger `:197-198`; restore count `<>10` | **exact inverse** (10 = 11−1) |
| **BB** open cutover states | 18 tables (`bb_legacy_documents_v1` `:180`, `bb_customer_credits_v1` `:199`, … `bb_wip_pickups_v1` `:2023`) + capsule; 16 indexes; 12 triggers (incl. on existing tables: `initial_import_financial_sources` `:805`, `payroll_reimbursements` `:854,1768`, `opening_subledger_balances` `:870`, `material_purchase_headers` `:1459`, `sales_headers` `:2788`); `alter table … add column` on `payroll_reimbursements` `:312,1712-1713`, check constraints `:314-316,1715-1717,2020`; 81 new fns | 30 (incl. `_validate_migration_batch_base`, `approve_payroll`, `finalize_migration_batch`, `complete_initial_import_wip_v1`, `post_work_completion` `:6186`, …) | drops 6 triggers on existing tables `:194-199`, FK/check constraints `:200-205`, 3 indexes `:206-208`, 4 added columns `:209-212`, **re-adds the original** `initial_import_production_sources_stage_check` and `payroll_reimbursements_source_type_check` definitions `:213-216`, 5 triggers on new tables `:217-222`, 81 fns `:223-303`, FK `:304`, 18 tables + capsule `:305-323`, ledger `:324-325`; restore count `<>30` | **exact inverse** incl. constraint text restoration |
| **BF** commercial ranges + vendor credit | 10 tables (`bf_rollback_v1` `:171`, `bf_skus_v1` `:178`, … `bf_supplier_credit_moves_v1` `:815`) + capsule; added columns `po_work_component_snapshots.bf_sku_version_id` `:202`, `rework_component_lines.bf_sku_version_id` `:490`, `bd_laundry_charge_lines_v1.bf_sku_version_id` `:616`; unique index replacing the old unique constraint `:204`; 8 triggers `:244-246,396-397,909-913`; 40 new fns + 6 public facades | 33 | drops 7 triggers on existing tables `:194-200`, 3 FKs `:201-203`, index `:204`, 3 columns `:205-207`, restores `rework_component_lines_rate_basis_check` `:208-209` and the original unique constraint `po_work_component_snapshots_po_id_work_component_id_key` `:210`, trigger on new table `:211`, 34 fns + 6 facades `:212-251`, 10 tables + capsule `:252-262`, ledger `:263-264`; restore count `<>33` | **exact inverse** |

Regex caveat: my forward inventory counts `CREATE OR REPLACE FUNCTION` of names already present as "replaced"; the capsule
cardinalities above (2/2/10/30/33) equal (forward functions − rollback drops) for all five pairs, which is the strongest static check
available without a database. Two AC-family rollbacks (AC..AV) are `RELEASE_VARIANT`s with `STATEMENTS_PAIR` substitutions of the
ledger-row sha (ROLLBACKS.json AC entry) — reviewed for AC only (`RB/20ac` 1269 lines; it also re-creates `erp.v_payroll_nota_browser`
from a pinned statement, substitution kind `AC_VIEW`).

### B.4 Workflows

- `cp6-t3-release-package.yml`: three jobs (`install`, `capture`, `browser`), hosted-faithful baseline rebuilt to AB via
  `scripts/cp6_t3_aligned_chain.py --stop-after-ab` (`:196-199`), isolated rollback authority role (`:208-222`), clone, then
  `scripts/cp6_t3_package_run.py <key>` (`:243`). `cp6_t3_package_run.py:169-186` compares re-captured `package_sha256` per key with the
  committed `MANIFEST.json` (determinism check). Pinned refs: writer `ca7f0955`, harness `c6b0e4fb`, candidate `25fa4736`, base `1bdca376`
  (`:113-131`). Branch trigger is `claude/new-session-deapao` (`:4-5`) — stale for this frozen candidate; `workflow_dispatch` present.
- `cp6-t3-rollback.yml`: modes `capture`/`cycle` (`:16-22`), auto-mode chooses cycle once all 30 rollback files exist
  (`scripts/cp6_t3_rollback.py:676-682`); cycle = refusals (out of order, open admission, original test-chain file on release chain),
  two full BF→AC cycles with exact state comparison, reinstall equality, and the post-use matrix (`cp6_t3_rollback.py:557-645`).
- `cp6-release-readiness.yml`: adds an `owner` job installing the 58 frozen files with a non-superuser owner account
  (`:84-86`, `scripts/cp6_readiness_owner_aligned.py`, `cp6_readiness_owner_test.py`) — this is the INV-M04 "from hosted v2.6.20, 28
  predecessors + 30" path; branch trigger `cp6/release-readiness`.
- `cp6-t2-regression.yml`: AR 174 cases + races, AT 16/AU 15 temporal, "original 326 + AS 34" regression on the combined candidate,
  built on the exact AC..AN chain via harness review scripts (`:181-302`); explicitly "not release evidence (T3 is)" (`:18-19`).

---

## C) Invariants → enforcing code or NOT ENFORCED

### C.1 Opening rows immutable after first transaction?

- Opening headers/items: `trg_posted_guard_opening_balance_headers` → `erp.guard_posted_document()` (`FIXTURE:30681`; function
  `FIXTURE` "guard_posted_document": non-DRAFT rows cannot be edited/deleted/status-changed by table access, bypass only for
  `postgres/service_role/supabase_admin`); items via `trg_parent_status_guard_opening_balance_items` → `guard_child_by_parent_status`
  (`FIXTURE:30685`); `trg_guard_opening_balance_post_date` refuses posting with a future `opening_date` (`FIXTURE:30679`, fn body shown in
  this review). Staging/batches/subledger openings are system-managed (`guard_system_managed_table`, `FIXTURE:30661,30663,30693`).
- Opening prepayments (uang muka awal) immutable rows: `initial_prepayment_immutable` triggers on `initial_import_prepayments`,
  `_payments`, `_events` (`FIXTURE:108500-108502` in the concatenated stream = R/20ap/R/20ba text).
- Opening payables reserved by payroll: `erp.bb_guard_opening_balance_reserved_v1` R/20bb:858-871 (`BB_OSS_EXCEEDS_AVAILABLE`).
- Invoiced part of pre-cutover receipts: `BB_RECEIPT_INVOICED_PART_IMMUTABLE` R/20bb:1281, trigger `:1283`.
- Opening FG HPP may be **corrected** (not edited) via `erp.post_opening_hpp_correction` R/20ac:4606-4637: only `lot_origin='OPENING'`
  (`:4619`), refused once the lot was used by conversion/rebrand (`:4621`), dated correction. No `reverse_opening_balance` function exists
  (searched: none). Batch-level optimistic lock: `erp.initial_import_revision_v1` R/20bb:3383-3413 hashes batch+rows+opening+BB parts,
  used by `get_initial_import_workspace_v1` R/20bb:3423 as `revision`.
- **Verdict: ENFORCED** for direct edits/deletes and for status changes; corrections only via dated, linked documents. Not re-verified at
  runtime.

### C.2 Cutover date respected by every writer (no posting before cutover)?

- The cutover is **per import batch** (`erp.migration_batches.cutover_at`, `FIXTURE:1510`; `create_migration_batch` `FIXTURE:7901-7906`),
  materialised as `opening_balance_headers.opening_date = cutover_at::date` (R/20ac:5817, R/20ap:2289, R/20bb:…). There is **no global
  cutover constant** read by general writers.
- Inside the import families every pre-cutover document carries and checks `cutover_date`: `check(document_date<=cutover_date)`
  R/20ap:208, R/20bb:194,1369,1703; `P04_BEFORE_CUTOVER` R/20bb:1443-1444; `BB_OSS_DATE_OUT_OF_RANGE` R/20bb:1120-1121,1621-1622;
  `BB_OPENING_PAYABLE_DATE` R/20bb:890; `Y02_CARRY_BEFORE_CUTOVER` R/20bb:1758; `BB_S02_DATE_BEFORE_CUTOVER` R/20bb:2784; prepayment
  events `v_date<a.cutover_date` R/20ap:1330, R/20ba:683; cash-advance payroll `R/20ap:4913`; supplier return of pre-cutover
  consumption R/20ap:3223.
- General writers do **not** check the opening date: `erp.post_material_purchase_v2` (final `FIXTURE:13882`, 43 lines, no cutover/opening
  reference), `erp.post_sale_v2` (final `M/20260829204632_…:680`, none), `erp.post_material_adjustment_v2` (`FIXTURE:13694`, none),
  `erp.post_fg_unsourced_receipt_v1` (R/20ax:326; only "not more than 5 minutes in the future" `:384` and "not before the BS found"
  `:424`), `erp.save_laundry_qc_action_v1` (R/20bd:3123; relative ordering vs pickup/delivery `:3437,3667`, future `:3355`).
- What *does* stop pre-cutover **outflows** is the chronological non-negativity of history: FG `erp.assert_fg_chronological_nonnegative`
  (`FIXTURE:6702-6739`, running sum ordered by `physical_at,system_created_at,id` per product/location/grade and per lot) called from
  `erp.post_fg_movement` R/20ac:3706; material `AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY` R/20am:485,761, R/20ao:250,
  R/20bc:2368 (inside `_recalculate_material_cost_core`). Pre-cutover **inflows** (a receipt or unsourced FG receipt dated before
  `opening_date`) are not refused by anything found. → **NOT ENFORCED (globally)**; see D) R4-02.
- The "new stock cutoff" family (`erp.assert_new_stock_cutoff_coverage_v1` R/20av:430-480, re-shipped R/20ba:2521, R/20bb:4319,
  R/20bc:4074, R/20be:4015, R/20bf:1574) is about **product-identity** effective dates (every FK to `erp.products` must be classified;
  `latest_new_stock_physical_at_v1` R/20av:401-418), not about the opening date.

### C.3 Per-SKU/size/lot opening = first movement?

- `erp.post_opening_balance` (final R/20ba:215-492): material opening movements at `opening_date` WIB midnight (`:445`), FG at
  `erp.product_opening_physical_at(product_id, opening_date)` (`:452,471`; fn `FIXTURE:15729-15756` = `greatest(day start WIB, product.effective_from)`,
  refuses a SKU version not yet effective on the opening day `:15751-15753`), WIP at `opening_date` midnight (`:467`), journal
  `OPENING_BALANCE` on `opening_date` (`:490`). Products are per size (`PRODUCT` catalog requires `size_code`, R/20bf:3332 catalog text),
  so "per SKU/size" = per `product_id`; lots are per opening item (`lot_origin='OPENING'`).
- Any later FG movement dated before that instant makes the per-product/location/grade **and per-lot** running sum negative →
  refused by `assert_fg_chronological_nonnegative` (`FIXTURE:6714-6736`). Material: same via AM. → **ENFORCED for outflows**; inflows
  see C.2. Cross-batch duplicate opening of the same physical source (prior CP6-09) is handled by AR opening overlap
  (`erp.post_opening_balance` R/20ba:236-… refuses a second batch header for the same source set; detail in `docs/cp6-ar-opening-overlap.md`,
  not re-read here).

### C.4 Period close (tutup buku)

- **What is locked:** a single `erp.accounting_period_control.closed_through` date (`FIXTURE:117-125`, singleton check `:3045`).
  Closing: `erp.close_accounting_through` final R/20ba:1002-1040 — owner/admin only (`require_owner_admin` `:1010`), only dates before
  WIB today (`:1012`), reason required, row locked `for update` (`:1014`), cannot move backwards (`:1015-1017`), `CLOSE_ALREADY_CLOSED`
  (`:1019-1021`), **readiness engine must be READY** (`:1023-1028`, `erp.period_readiness_v1`), then material cost checkpoints are
  refreshed and an immutable filing is written (`accounting_close_filings_v1`, R/20aw:817-823; immutability triggers R/20aw:1071-1073,
  fn `guard_accounting_close_filing_immutable_v1` R/20aw:198). Public facade `public.erp_close_accounting_through_v1` R/20aw:1047-1062,
  granted to `authenticated,service_role` (R/20aw:1089-1090) but gated inside by `require_owner_admin`.
- **Who can reopen:** `erp.reopen_accounting_through(p_new_closed_through, p_reason)` R/20ac:5934-5957 — owner/admin, reason required,
  new date must be earlier than current close or NULL (full reopen), and before today; audit-logged. **No `public.erp_reopen_*` facade
  exists** (searched), so reopening needs a privileged DB session (`erp` schema is not exposed to HTTP).
- **Lock semantics for writers — the lock does not refuse; it re-dates journals.** `erp.post_journal` (`FIXTURE:13391+`) calls
  `erp.resolve_accounting_transaction_date` (`:13466` = body line 76) and stores `economic_date = p_transaction_date`, `transaction_date = v_gl_date`
  (`:13468-13469`), writing an audit row "Late/backdated posting moved to open accounting period" when shifted (`:13481-13483`).
  `resolve_accounting_transaction_date` (`FIXTURE:17066-17081`) returns `greatest(today, closed_through+1)` for an economic date on or
  before the close, and refuses future economic dates. Its clock was rewritten in place: M/20t:335-341 replaced both `current_date`
  with `erp._cp3_business_date(current_timestamp)` (anchor count asserted = 2), and M/20ab:256-266 replaced `current_timestamp` with
  `statement_timestamp()` (hash chain `13fa7b70→92e6c30c→656ac4cd`, pinned at R/20ac:1094). So the final function uses the WIB business
  day — INV-T01 holds here (checked because the fixture text alone would have violated it).
- **Coverage list (mandatory).** Final-body call graph (953 functions; writer = `post_/reverse_/save_/finalize_/complete_/apply_/manage_/
  set_…` plus `public.erp_(save|post|reverse|set|manage|complete|finalize|apply|close|reopen|…)`; 316 writers; reach depth 4).
  **Writers that reach the lock** (either read `accounting_period_control` directly or call `post_journal`): 153, including every
  financial poster (`post_sale_v2`, `post_sales_return`, `post_material_purchase_v2`, `post_material_supplier_invoice`,
  `post_material_purchase_cost_correction`, `post_material_adjustment_v2`, `post_material_transfer_v2` — direct read R/20am:444 —,
  `_recalculate_material_cost_core` — direct read R/20ac:1609 used for checkpoint selection `:1613-1622` —, laundry QC/receipt/final SKU,
  work completion, payroll approval/payment, `post_opening_balance`, BC/BD/BE/BF posting entrypoints, `sync_po_hpp_to_gl` — direct read
  R/20ay:713-716 to cap the correction at E when E is closed).
  **Writers that do NOT reach the lock (163; 81 of them touch physical/financial state).** Drafts and master data are expected here;
  the ones that **change dated operational facts without any lock interaction** are:
  - `erp.post_attendance_period_v1` M/20260830140645_…:1299 and `erp.reverse_attendance_period_v1` `:1488` (+ facades `:2193,2209`) —
    attendance facts (feed payroll/HPP later);
  - `erp.reverse_sewing_terminal_v1` M/20260901023200_…:758 (+ facade R/20be:1345);
  - `erp.post_fg_movement` R/20ac:3643 and `erp.reverse_fg_movement` `FIXTURE:18005` (internal; callers post journals);
  - `erp.apply_rework_component_entitlement` `FIXTURE:6601`, `erp.reverse_bs_disposition_v2` `FIXTURE:17504`;
  - `erp.cancel_sale_draft_v2` M/20260829204632_…:559, `erp.save_sale_draft_v2` `:444` (reservations);
  - opening/import mutators: `erp.apply_initial_import_receipts_v1` R/20bb:4612, `erp.bb_manage_opening_wip_v1` R/20bb:2210,
    `erp.bb_manage_payroll_entitlement_v1` R/20bb:1935, `erp.bb_manage_purchase_commitment_v1` R/20bb:1601, `erp.apply_migration_open_pos`
    R/20ak:642, `erp.apply_migration_master_rows` R/20ap:2015, `erp.finalize_migration_batch` R/20be:6596,
    `erp.set_opening_cash_advance_payroll_v1` R/20ap:4936, `erp.set_opening_fg_hpp_percent` `FIXTURE:24268`;
  - BC/BE helpers that write custody/pocket/redye state without journals: `erp.bc_close_custody_v1` R/20bc:1156, `erp.bc_count_post_v1`
    R/20bc:1243, `erp.bc_note_return_issue_movement_v1` R/20bc:1395, `erp.bc_allocate_carry_v1` R/20bc:1570, `erp.be_save_rework_v1`
    R/20be:677, `erp.be_pocket_link_receipt_origin_v1` R/20be:1221, `erp.save_rework_order_v2` R/20be:3652, `erp.save_cutting_batch_v2`
    R/20ac:8309, `erp.save_laundry_claim_v2` R/20ac:8485, `erp.save_worker_roster_v1` R/20ac:10284, `erp.set_worker_daily_rate_v1`
    R/20ac:10681, `erp.set_accessory_uom_conversion_v2` R/20ac:10518, `erp.apply_bulk_rate_change` `FIXTURE:6400`, `erp.save_work_bom_edit`
    `FIXTURE:23316`.
  Full list: scratchpad `fable7/writers_lock.json` (316 rows: name, file, line, reaches_lock, calls_post_journal).
- **Consequence:** INV-T02 ("periode tertutup tidak berubah diam-diam") is satisfied for the **GL** (journals never land on a closed
  `transaction_date`; filings are immutable and the snapshot shows `filing` + `changed_since_filing`, R/20aw:999-1000), and for **value
  corrections** by D01 §3.4. For **physical quantity facts** there is no refusal and no shifting: a stock movement, attendance day or
  work completion dated inside the closed period is stored at that date; as-of stock/WIP reports for the filed period change. The
  readiness engine only flags dated *defects* (negative prefixes etc.), so `changed_since_filing` (= `filing is not null and status<>'READY'`,
  R/20aw:1000) stays **false** for a clean backdate. → **NOT ENFORCED for physical facts; weak change flag.** See D) R4-03.

### C.5 Advances (uang muka) capacity by date — D02

`erp.initial_prepayment_dated_floor_v1` + `erp.manage_initial_prepayment_v1` (R/20ba, raise `BA_ADVANCE_DATED_CAPACITY` R/20ba:738) —
refuse APPLY/REFUND/downward corrections that would make the remaining advance negative on the operation date or any later date
(addendum §4 D02.1). Prepayment events dated before cutover or after today refused R/20ba:683. **ENFORCED** (static); prior Fable
CP6-07 CLOSED on a095a9d.

### C.6 Dated HPP (see also E)

`erp.sync_po_hpp_to_gl` R/20ay:640-1069: per-date legs FG/COGS/other from each piece's physical facts, cap at E when E ≤ closed_through
(`:713-716`), one journal on the caller date outside the late-invoice path (`:716-737`). `erp.invoice_recost_economic_date_v1`
(R/20ao:134) carries the invoice economic date through the recost chain (`:169,458,1218-1221,1258`; R/20ap:6429; R/20as:350-353).
Material side R/20az (`sync_material_cost_revaluation`, `_cp6_sync_material_adjustment_revaluation`, `refresh_accessory_hpp_after_material_recost`
R/20az:721, journal `ACCESSORY_HPP_RECOST` `:776`). **ENFORCED per D01.**

### C.7 Accessories / laundry / pockets / dye / conversion policy gates (D06, D11)

Fail-closed while a policy value is pending: `BC_POLICY_PENDING` R/20bc:276 (generic) and `:943` (ACC-DEC04 account),
`BC_FREE_REQUIRES_POLICY` R/20bc:3330 (ERP-DEC02), `BC_CARRY_ONCE` R/20bc:1592 (ACC-DEC05 = `CREDIT_THEN_CARRY`), `BD_POLICY_PENDING`
R/20bd:244, LAU-DEC04 value check R/20bd:300-301 and `BD_SALE_LAUNDRY_PRICE_UNKNOWN` in `erp.bd_assert_sale_laundry_known_v1` R/20bd:2391-2400
(only `ALLOW_PENDING` lets the sale through and records it in `bd_pending_price_sales_v1` `:2373,2403`), LAU-DEC06 correction documents
`BD_CORRECTION_EXCEEDS_PAYABLE` R/20bd:2277 (re-shipped R/20be:4502, R/20bf:2025-2029 — "vendor receivable needs its own flow"),
GBD-03 option 1 `BD_W05_COMPENSATION_EXCEEDS_PAYABLE` R/20bd:1630. LAU-T14 (price at delivery) R/20ba:1822. No `PENDING_POLICY_VALUE`
literal is a default in SQL (0 hits for a policy default in R/20bf; values are rows in `erp.bd_policy_settings_v1`/BC equivalents, set by
the owner in the app — `scripts/cp6_bd_browser.mjs:5,445-456` exercises SET and back to pending). **ENFORCED (fail-closed).**

---

## D) Suspected defects

| ID | Sev | Where | Reasoning | Concrete probe | Status |
|---|---|---|---|---|---|
| **R4-01** | P3 (release evidence hygiene; Pro Max §16.6 "arsip bukti … manifest") | `supabase/release/cp6-t3/MANIFEST.json` field `rollbacks: "NOT_TESTED"`; literal at `scripts/cp6_t3_release_package.py:337` (docstring `:28`); stale "24 files"/"29-file" comments `.github/workflows/cp6-t3-release-package.yml:74,84`, `cp6-release-readiness.yml:79,89` | The committed release manifest asserts rollbacks are untested while `ROLLBACKS.json` (30 hashed inverses), `rollback_capture.json` and the writer's 147/147 cycle (`docs/cp6-combined-release-writer-handoff-20260928.md:84`) exist. An operator reading only the MANIFEST at install time gets a false negative; the opposite drift (a future manifest saying tested when files changed) is not guarded either because the field is constant. | Read the field; grep the script; compare with `ROLLBACKS.json` (done). | **CONFIRMED by source** (metadata only; no business impact) |
| **R4-02** | P2 (INV-M01/INV-M03, annex C6 §0.2 "Histori lama tidak boleh dikarang"; M:369/379) | No global cutover floor for **inflow** writers: `erp.post_material_purchase_v2` `FIXTURE:13882`, `erp.post_fg_unsourced_receipt_v1` R/20ax:326 (`:384` future-only), `erp.post_material_adjustment_v2` `FIXTURE:13694`, `erp.post_sale_v2` M/20260829204632:680; cutover checks exist only inside import families (C.2). Outflows are caught by `assert_fg_chronological_nonnegative` `FIXTURE:6702` / AM `:485` only because they would make history negative. | A receipt (material purchase with `physical_at` before `opening_date`, or an AX unsourced FG receipt dated D−3) adds pre-cutover history **on top of** the imported opening balance of the same SKU/material: as-of reports for dates before cutover show stock that the opening document says did not exist in ERP, and the opening balance plus the backdated receipt double count the same physical goods if the receipt was already part of the legacy balance. Nothing in the readiness engine classifies "movement before opening" (detectors are negative-prefix/as-of only, R/20bf:2214,2257,2314). | Disposable DB after a POSTED opening for SKU X (qty 10, lot `OPENING`, `opening_date` D). (1) `erp.post_fg_unsourced_receipt_v1` for X with `physical_at` = D−3 07:00 WIB, qty 5 → **expected (contract)**: refusal naming the opening date; **predicted (code)**: POSTED, `fg_stock_movements` row at D−3, `get_owner_financial_snapshot_v2(p_as_of=D−1)` FG ≠ 0. (2) Same with a material purchase header `physical_at` D−2 and `post_material_purchase_v2` → predicted POSTED, `erp.v_material_grni_aging` and material inventory as-of D−1 non-zero. (3) Control: outflow (sale) dated D−1 → refused by the chronological guard. | **UNCONFIRMED (static)** — needs the native probe; owner may also decide pre-cutover backfill is legitimate, in which case it must be a written rule, not a gap |
| **R4-03** | P3 (INV-T02 presentation; D01 §3.4 "Laporan menandai `changed_since_filing`") | `erp.get_owner_financial_snapshot_v2` R/20aw:999-1000: `changed_since_filing := v_filing is not null and v_readiness->>'status'<>'READY'`; physical writers never consult `closed_through` (C.4 list) | After a close through D and a filing, a stock movement / attendance / work completion dated ≤ D is stored at that date (only its journal is shifted). The as-of quantities and the FG/material value in a re-read of the filed period differ from the filing, but because readiness is still READY, the report says `changed_since_filing=false`. The filing stores only `gl_balances` (R/20aw:817-823), so a quantity-only backdate is not even comparable. | Disposable DB: close through D (READY), file; post `post_material_adjustment_v2` dated D−1 (+2 units, documented) → journal `transaction_date` = today (audit row "moved to open accounting period"), `material_stock_movements.physical_at` = D−1; call `get_owner_financial_snapshot_v2(D−30, D, D)` → predicted `data_confidence.changed_since_filing=false`, `financial_position.material_inventory` unchanged vs filing (GL shifted) while a stock-as-of query for D shows +2. | **CONFIRMED by source for the flag logic**; business impact is presentation (physical history vs filed value), needs native run for exact numbers |
| **R4-04** | P3 (residual of CP6-IMPORT-REFERENCE-PREVIEW-01) | `erp._validate_migration_batch_base` R/20be:6540-6556 checks only existence of the `location_code` in `erp.locations` (`execute format('select exists(select 1 from erp.%I where %I=$1)'…)` `:6549-6550`) for `OPENING_BALANCE_ITEM`; prepare requires an **active raw-material warehouse** (`'location_code: gudang bahan aktif tidak ditemukan'` R/20ap:4419, R/20bb:1502,4584, R/20be:5673) or an active FG warehouse (`'pilih gudang barang jadi aktif'` R/20bd:6543). MATERIAL_ROLL has the stricter validator check (`:6497-6501`); OPENING_BALANCE_ITEM does not. | The successor's finding ("validator says VALID, prepare fails P0001") still reproduces for a location that exists but is inactive or of the wrong type (e.g. a CUTTING_WIP location on a MATERIAL opening row, or an FG warehouse code on a MATERIAL row). Ledger stays intact (prepare is atomic), so this is diagnostics-only, as before. | Stage one `OPENING_BALANCE_ITEM` `balance_type=MATERIAL` with `location_code` of an existing `is_active=false` RAW_MATERIAL_WAREHOUSE; `validate_migration_batch` → predicted VALID/0 errors; `prepare_migration_opening_balance` → predicted P0001 `location_code: gudang bahan aktif tidak ditemukan`. Control: unknown code → row error at validation (fixed path). | **UNCONFIRMED (static)**, high confidence from text |
| R4-05 | INFO | `erp.reopen_accounting_through` R/20ac:5934 has no `public.erp_*` facade | Reopen requires a privileged SQL session; the UI cannot reopen. Fail-closed, consistent with "owner reopen is a controlled event", but there is no in-app audit trail of *who* asked. Not a defect against the contract read here. | — | NOTED |
| R4-06 | INFO | Workflow `on.push.branches` pins (`claude/new-session-deapao`, `cp6/release-readiness`) | The T3/rollback workflows do not trigger on the frozen candidate's branch; evidence must come from `workflow_dispatch` runs whose `product_ref` is asserted by the auditor workflow (Fable manifest). | — | NOTED |

Refuted while reviewing (recorded so nobody re-opens it): the fixture text of `erp.resolve_accounting_transaction_date` uses
`current_date` (UTC risk, INV-T01) — but the body is rewritten in place by M/20t:335-341 and M/20ab:256-266 to
`erp._cp3_business_date(statement_timestamp())`; the pinned sha `656ac4cd…` at R/20ac:1094 is the rewritten text. **Not a defect.**

---

## E) Seams to CP7

1. **Sales/AR/COGS UI** — CP6 engine (`post_sale_v2`, reservations, `bd_assert_sale_laundry_known_v1` R/20bd:2391) is consumed by the
   CP7 connected sales chain (`src/ConnectedSalesPage.tsx`, `SalesDraftPanel.tsx`, `SalesPaymentPanel.tsx`, `SalesReturnPanel.tsx`,
   `.github/workflows/cp7-p11-sales.yml`). R10/AUD-G04 is gated on CP7 (M:1728). Any CP7 writer that posts FG movements inherits C.2/C.4
   semantics (no cutover floor, journal-shift lock) — R4-02/R4-03 propagate.
2. **Period close UI/finance** — CP7 `cp7-p13-period.yml`, `cp7-p13-recost.yml`, `ConnectedFinanceReportPage.tsx:50` (status label) and
   `ConnectedFinanceOverviewPage.tsx:85` consume `period_readiness_v1`/`get_owner_financial_snapshot_v2`; `changed_since_filing`
   (R4-03) is what the CP7 report shows the owner. Reopen has no facade (R4-05).
3. **Dated HPP** — `po_hpp_gl_lot_state_v1` / `po_hpp_gl_material_state_v1` (R/20ay:174,183) are the per-lot "last posted HPP" memory
   CP7 recost (`cp7-p13-recost.yml`, `cp7-f03-cost-continuation.yml`) must keep in sync; BF commercial SKU ranges add `bf_sku_version_id`
   to work snapshots/rework/laundry charge lines (R/20bf:202,490,616).
4. **Laundry pending price → CP7 sales** — `bd_pending_price_sales_v1` (R/20bd:2373) marks sales with non-final HPP; UI today only in
   `src/LaundryBdPanel.tsx:420-429` ("HPP belum final") plus counts in finance pages; CP7 sales pages should surface `hpp_state`.
5. **Opening/cutover data** — `scripts/cp6_cutover_data_checks.py` (read-only inventory for F3/D08) is still an operator item
   (`docs/cp6-au-r1-handoff.md:2703,2954`); CP7 go-live (CP7C backup kit, D13-9a, out of this scope) depends on it.
6. **Vendor receivable** — `BD_CORRECTION_EXCEEDS_PAYABLE` (R/20bf:2025-2029) deliberately leaves "kelebihan bayar ke vendor" without a
   flow; a CP7/CP7.5 successor must add it before laundry over-payments appear in production.

---

## F) Undetermined / not done here

- No database was executed; every "predicted" outcome in D) is static. Native probes for R4-02, R4-03, R4-04 are specified above.
- The 30 forward files were inventoried by regex; only AW, AY, BA, BB, BF were read statement-by-statement against their rollbacks.
  AC..AV rollbacks are `RELEASE_VARIANT`s of reviewed `supabase/rollbacks/*` files; only AC's substitution kinds were inspected.
- `erp.period_blockers_v1` final text (R/20bf:2102) was not read line by line; D04's registry (`scripts/cp6_aw_integrity_registry.sql`)
  not re-verified.
- Whether the owner has ratified pre-cutover backfill as permitted (R4-02) is unknown; no decision text found in the addendum, annex
  C6, D11 or `docs/cp7/OWNER_DECISIONS_20261008.md` (grep for cutover/saldo awal there not performed exhaustively).
- §34.8 items on the final code: LAU-T36 oracle → done (§34.9, `scripts/cp6_bd_browser.mjs`); policy values 1,2,3,5,7,8,9,10 → still
  owner-in-app (fail-closed code C.7); D07–D12 + `V2620C_WIP_SOURCE_CONSERVATION_MISMATCH` substitution → check present at R/20bd:7020
  and in R/20be (1 hit), absent from R/20bf (0 hits — the BF file does not re-ship that check; whether BE's text is the final body was
  not confirmed); "piutang vendor belum punya alur" → unchanged (R/20bf:2025-2029); "LAU-DEC04 belum diuji di browser" →
  `scripts/cp6_bd_completion_browser.mjs:32-50` now asserts the "HPP belum final" region (not run here); "HPP belum final hanya di
  halaman laundry" → still only `src/LaundryBdPanel.tsx:421-429` as a list, finance pages show counts only; BE → shipped (R/20be);
  UI-01 → owner-scheduled (gptaudit index `owner_decisions.UI-01`), no code claim checked; cutover ID inventory → script exists
  (`scripts/cp6_cutover_data_checks.py`), operator run not evidenced in repo.
- §31.8/§32.9 "75 C6 + 22 ALL" plan: the writer reports the combined run as "90 native + 22 contention + 8 Auth/HTTP + 27 browser BF"
  (`docs/cp6-combined-release-writer-handoff-20260928.md:77-79`), i.e. the 75/22 crosswalk ids are not reported one-to-one; mapping of
  the 75 annex ids (annex C6 §6) to those 90 cases was not reconstructed here and remains UNVERIFIED from this review's side.
- CSV upload transport end-to-end (H3) and role matrix completeness (H4): code located, acceptance not assessed.
