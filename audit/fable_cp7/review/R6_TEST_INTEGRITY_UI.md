# R6 — Test integrity (F04/F05 tooling) and UI static review — candidate d0b9e9c2

Reviewer: sub-reviewer for auditor Fable. Read-only; checkout `scratchpad/cand` detached at d0b9e9c2; docs-only reads of
`origin/claude/new-session-deapao` where noted. No database, no app run. CI job logs fetched read-only via GitHub API (6 jobs).
Paths below are relative to the checkout root unless absolute.

## Part A — test integrity

### A1. `scripts/cp7_f05_analysis_probe.py` — what the gate reads vs what the SQL can emit

Gate (probe:351): `status='PASS'` iff no `error`, `cp6_restored`, `advisor_gate`, `observed_case_count==expected`,
`required_case_counts_pass` (every group `counts=={'PASS':n}`), `required_case_ids_pass`, and for every group
`status in ('PASS','RUN_COMPLETE') and set(counts)=={'PASS'} and database_remaining==0`. The probe never reads an analysis
flag itself; flag coverage is delegated to the case providers (`cp7_*_cases.py`) whose rows carry PASS/FAIL/COUNTEREXAMPLE/
INCOMPLETE. A group with empty counts fails (set()!={'PASS'}). Summary print (probe:352) prints label/status/source_sha256/
observed_case_count/cp6_restored/advisor_gate/error/traceback only.

Flag inventory from `scripts/cp7-src/planning/analysis*.sql`:
- status vocab: UNKNOWN / ASSUMED / COMPLETE / PARTIAL / BLOCKED (analysis.sql, analysis-stages.sql, analysis-finance.sql), LIMITED
  (analysis-finance.sql:91 readiness), `completeness`, `generation_warnings`/`warnings`, `errors` (HIST_VALIDATE, stages:1594).
- completeness booleans: `history_complete`, `complete_scope`, `wip_complete` (stages:590,638), `supplies_complete` (stages:584-640),
  `capture_complete`, `page_complete` (archive), `demand_unknown` (stages:1024-1258), `identity_unknown` (stages:1164,1259,1785),
  `unknown_days` (stages:309,1073; analysis.sql:149), `unresolved`/`unresolved_qty`/`unresolved_pcs`.
- reasons: SHARED_CAPACITY_UNKNOWN (stages:840), NATIVE_QUANTITY_CAPTURE_INCOMPLETE (591), TIME_UNKNOWN (966), ETA_OR_YIELD_UNKNOWN (974),
  EXISTING_SUPPLY_YIELD_OR_SHARED_ETA_UNKNOWN (723), SELECTED_CALENDAR_EXPIRED (519,542), MATERIAL_FEASIBILITY_NOT_PROVEN (`reason_codes`, 1068).
- job/runner: states RUNNING/DONE/FAILED, retention KEPT/EXPIRED (stages:1410-1417,2227), ARCHIVED_STALE, STALE_VERIFIED (stage-snapshot);
  runner outcomes IDLE/UNIT_STORED/UNIT_RETRY/JOB_DONE/JOB_FAILED/ACCESS_CHANGED_DURING_UNIT (stages:2437-2441); `denied` access object
  (stages:2427,2431) -> step() p_access distinct from access_at_capture -> job FAILED CP7_ANALYSIS_ACCESS_CHANGED (stages:2001-2004);
  `statement_timeout(_ms)`, CP7_RUNNER_STATEMENT_LIMIT_REQUIRED (2405).
- `stale`: `jsonb_build_object('is_stale',false,'reasons','[]')` hardcoded (analysis.sql:285; analysis-stages.sql:1264) — can never be true.

Named in at least one case provider (grep over scripts/cp7_*_cases.py): UNKNOWN, ASSUMED, COMPLETE, PARTIAL, BLOCKED, LIMITED, completeness,
generation_warnings, history_complete, complete_scope, capture_complete, page_complete, unresolved*, statement_timeout, ARCHIVED_STALE,
STALE_VERIFIED, EXPIRED, FAILED, capacity_state, primary_reason; K4 provider covers all six runner outcomes and `denied`
(cp7_k4_runner_cases.py:32-47, grep counts UNIT_STORED 11, JOB_FAILED 6, UNIT_RETRY 5, ACCESS_CHANGED_DURING_UNIT 3, denied 6).
NEVER named in any case provider, probe or browser module: demand_unknown, wip_complete, supplies_complete, unknown_days, identity_unknown,
'warnings' (as such), is_stale, SHARED_CAPACITY_UNKNOWN, NATIVE_QUANTITY_CAPTURE_INCOMPLETE, TIME_UNKNOWN, ETA_OR_YIELD_UNKNOWN,
SELECTED_CALENDAR_EXPIRED, reason_codes, 'errors'. Their only coverage is whole-output equality staged-vs-single on the same reference
(cp7_p19_staged_cases.py:260-262, `P19G_STAGED_ANALYSIS_DIFFERS_FROM_SINGLE_ON_SAME_REFERENCE`) — an equivalence oracle, not a
correctness oracle: a flag that is wrong the same way in both compilers passes. Suspected defects: (a) dead `is_stale` flag; (b) no case
asserts the UNKNOWN reasons above are produced when their trigger holds (fixture inspection needed to confirm whether they fire at all).

### A2. Business-day control in the browser host (.mjs) vs Python

Files: scripts/cp6_auditor_business_day.mjs (15 lines, guard only), scripts/cp6_auditor_browser_host.mjs (host),
scripts/cp6_auditor_business_day.py (guard, explained, retry_allowed, with_retry), scripts/cp6_auditor_modes.py (run_browser:343-385),
scripts/cp6_auditor_runner.py (strict_group:89-95, per-case checks 139-146).

Can the .mjs path turn FAIL/COUNTEREXAMPLE into PASS or INCOMPLETE? No. guard() only rewrites `status==='PASS'` to INCOMPLETE
(business_day.mjs:10-13); all other statuses untouched. The host never decides a retry; it only records rows. Retry is decided in Python
(`modes.run_browser` -> `business_day.with_retry(..., lambda r: r['cases'])`, modes:346) over the host's rows.

Retry exclusions on the browser path (all confirmed in source):
- timeout -> row INCOMPLETE `AUDITOR_BROWSER_CASE_TIMEOUT`, `report.error` set, run ends (host:176-188) -> Python `report['error']`
  (modes:371) -> `retry_allowed` False (business_day.py:58).
- malformed result -> `AUDITOR_CASE_RESULT_NOT_AN_OBJECT` (host:178) -> in SCENARIO_ERRORS -> `explained()` False (py:45-52).
- status outside vocabulary -> `status_outside_vocabulary` (host:183) -> `explained()` False.
- duplicate ids -> report.error (host:171). Host status != RUN_COMPLETE -> error (modes:371). Session left open on the copy ->
  `AUDITOR_BROWSER_SESSION_LEFT_OPEN` error (modes:372-373). Auth counts not restored / auth_cleanup_failures -> cleanup_failures
  (modes:382-383) -> no retry. database_remaining (modes:380) -> no retry.
- Browser host has NO per-case harness checks (no boundary/public-schema/leak check per case), so `harness_check_failed` is never set
  on a browser row; group-level checks above are the only harness exclusions.

DEFECT (design, medium): `explained()` treats a rolled-over FAIL or COUNTEREXAMPLE row as explained (business_day.py:48-52: only
rollover + not harness + not outside-vocab + not scenario error), and `retry_allowed` therefore reruns a group whose only non-PASS row is
a genuine FAIL that happened to straddle WIB midnight. The writer's own test asserts this is intended:
scripts/cp6_auditor_business_day_test.py:73 `self.assertTrue(bd.retry_allowed({}, {'A': self.rolled('FAIL')}))`. Consequence: group
verdict FAIL/COUNTEREXAMPLE (first attempt) -> PASS (second attempt) with `business_day_retried=true`; the FAIL survives only inside
`business_day_first_attempt`. This contradicts the module docstring/README wording "FAIL ... never changed" at the group-verdict level.
Probability low (needs a real FAIL in a case that crosses midnight) but it is exactly the class of masking the audit question asks about.
Mitigation depends on A5 (visibility of `business_day_retried`), which is weak.

Python vs JS differences (table):
| Aspect | Python (runner/modes) | JS host | Effect |
|---|---|---|---|
| guard semantics | guard(): PASS->INCOMPLETE, error setdefault | identical (`!('error' in row)`) | parity (test.mjs 7 vectors) |
| per-case harness checks | boundary, public schema, leaks -> harness_check_failed (runner:141-145; modes:158-159) | none per case | browser rows can never be "unexplained by harness" |
| keep_first | strict_group saves `<name>_BUSINESS_DAY_FIRST_ATTEMPT` via r1.save (runner:92-94) | n/a; run_browser/run_races/run_http pass no keep_first (modes:176,310,346) | first attempt only nested in the group JSON |
| `today` source | clone read at setup (runner:106) | env AUDITOR_BROWSER_TODAY = setup['today'] (modes:364); before/after via psql on the copy (host:174,184) | same server clock; different connection |
| date read failure | psycopg error inside group -> report error | execFileSync throw outside try (host:174/184) -> main throws -> report.error, failed_stage=CASES, current row not recorded | INCOMPLETE either way; browser loses the row |
| retry decision | with_retry over rows | none | single decision point in Python |
| second rollover during rerun | stays INCOMPLETE (with_retry runs at most twice) | n/a | ok |

What the tests do NOT cover: test.mjs only checks guard parity on 7 vectors and two regexes on the host source (test.mjs:31-33) — not the
host loop (timeout, NOT_AN_OBJECT, outside-vocabulary, duplicate ids, psql failure). test.py Wiring replaces `_run_browser_once` with a fake
(test.py:294-313), so the mapping of host output (status/error/missing/cleanup) into the Python report is untested; FAIL+rollover rerun is
asserted as allowed, never flagged; absence of keep_first for browser/races/http untested; AUDITOR_BROWSER_TODAY == copy WIB date untested;
no test of receipt/summary visibility of `business_day_retried`.

### A3. Browser case timeout and the K4 60 s bounds

Host: `caseTimeoutMs` default 45 min (host:44-45); `Promise.race([operation(), limit])` (host:176-177); on timeout the row is
`{status:'INCOMPLETE', error:'AUDITOR_BROWSER_CASE_TIMEOUT', timeout_ms}`, guard still applied, row saved, then `report.error`,
`report.timed_out_case`, loop exits (host:180-188); later cases are `missing`; status INCOMPLETE; exit 1 (host:194-196,219). The pending
`operation()` promise has its rejection handled by `Promise.race`; browser.close bounded to 60 s (host:204). Python: host status !=
RUN_COMPLETE -> error -> INCOMPLETE without `finish()` (modes:371,384). Probe gate needs group status PASS/RUN_COMPLETE and counts=={'PASS'}
-> a timeout can never be PASS on any path. No assertion/oracle is touched by the timeout.
K4 module (scripts/cp7_k4_runner_browser.mjs): `bounded()` (line 20) wraps response-body reads (27, K4R_RESPONSE_BODY_NOT_READ) and
context.close in `finally` (76, K4R_CONTEXT_CLOSE_TIMEOUT); `expect.poll` timeouts 60 s/240 s/90 s. All reject -> thrown -> host INCOMPLETE.
Notes: (i) a thrown Playwright/assert failure (incl. the no-horizontal-scroll oracle in `shot()`, line 16) is INCOMPLETE, not FAIL — never
PASS, but FAIL/INCOMPLETE are blurred; (ii) a close timeout in `finally` replaces the original error text (K4R_*_FAILURE.json is written
first, line 75); (iii) `no_horizontal_scroll:true` in the PASS row is a constant that is only true because `shot()` did not throw.
Workflow: k4-runner-17 job timeout 180 min (.github/workflows/claude-p19-transport.yml:120-122); AUDITOR_BROWSER_CASE_TIMEOUT_MS is set in no
workflow (default 45 min applies; two timed-out browser cases = 90 min < 180).

### A4. Evidence logs vs CI logs

Dirs (d0b9e9c2): docs/cp7/evidence/business-day-control-20261011/{01_k4_browser_mobile_silent_first_attempt.log,
02_k4_browser_mobile_silent_second.log, CI_RECEIPT.json, README.md, SOURCE_DELTA.json}; sol-p20-k4-20261009/{01_attention284_wib_midnight_first_attempt.log,
README.md}; k3-cleanup-20261009/{01_shell_gitignore_guard.log, 02_k3_cleanup_17_first_run.log, 03_k3_cleanup_17_second_run.log} (no README; headers in logs).
origin/claude/new-session-deapao adds only 3 README lines in business-day-control (job 114435156829 on d0b9e9c2 passed 6/6) plus
docs/cp7/audit-candidate/cp7-full-20261011/*; no evidence log changed.

| Stored log | Cited run / job | CI compare | Result |
|---|---|---|---|
| bd/01 | 38114007484 / 114395165573 | 29/29 stored lines found by timestamp, identical prefix; 16 case ids+statuses equal; 16 business_day rows all 2026-10-11/11/11, no rollover, no RERUN; desktop browser PASS 05:54:16, `##[error]The operation was canceled.` 07:14:58 (= 80 min 42 s) | MATCH |
| bd/02 | 38122987757 / 114421382536 | 29/29 identical; 16 cases equal; desktop PASS 08:35:19, canceled 08:56:20 (= 21 min 01 s) | MATCH |
| sol/01 | 37958882487 / 113916327717 | 13/13 identical; the 6 INCOMPLETE browser rows (`'2' !== '1'`, fixture `CP7_NOTA_AFTER_PERIOD`) and label INCOMPLETE present in CI | MATCH |
| k3/01 | 37853604126 / 113572379308 | assertion text, both SHA-256 values, check-cp6-boundary.mjs:862:8 stack, exit code 1 all present in CI tail | MATCH |
| k3/02 | 37853604176 / 113572379702 | 37/37 stored body lines found verbatim; 17 case statuses equal; two browser INCOMPLETE (locator.click timeout) | MATCH |
| k3/03 | 37859254362 / 113590815313 | 22/22 verbatim; two browser INCOMPLETE (locator.selectOption timeout) | MATCH |
Method: tail 700/400 lines per job (original lengths 2186/2188/2560/1476/2168/2173); lines compared after stripping the stored `NNNN:` prefix,
up to 1400 chars. Comparison script: scratchpad/cp7/review/compare_logs.py, compare_k3.py.

### A5. Is a business-day rerun visible in the receipt?

No receipt builder exists in the repo (grep CI_RECEIPT/ci-receipt only hits docs). CI_RECEIPT.json contracts
(`cp7.business-day-control-ci-receipt.v1`; `cp7.full-audit-ci-receipt.v1` at origin) hold run/job ids, conclusions and
`qualification.all_first_attempt` (GitHub re-run attempts, not business-day reruns); zero `business_day`/`retried` fields.
`business_day_retried`/`business_day_first_attempt` live only in the group report nested in the probe JSON (CP7_K4_RUNNER.json etc.,
uploaded as artifact `auditor/cp6-proof/t3/*.json`, claude-p19-transport.yml:307-319) and as the `RERUN_FROM_FRESH_COPY` job-log line
(business_day.py:74). The probe's printed summary (probe:352) omits it; `scripts/cp7_contract_receipt.py` (framework byte lock) and
`scripts/cp7_checkpoint_evidence_index.py` (artifact hashes) never read it. => In CI_RECEIPT.json a retried group is identical to a clean one.

## Part B — UI (static)

### B6. Routes, guards, mode indicator, refusal
Single-page state router: `type Page` union (App.tsx:79), `PAGE_PERMISSION_BY_ID` 48 ids -> permission (src/auth/accessCatalog.ts:58-106);
`isPageAllowed` false for unknown ids (accessCatalog.ts:137-140); guard App.tsx:628 `!(demoAccess || isPageAllowed(accessBundle,page))` ->
`<AccessDenied permission=... roleName=...>`; redirect effect App.tsx:486-490; nav labels hidden by `canSeeNavLabel` (449).
Refusal text App.tsx:771-772: role="alert" "Tidak punya akses" / "Role <X> tidak memiliki izin untuk membuka halaman ini." + `<code>permission</code>`.
'placeholder' page -> `route.unowned`. demoAccess only when runtime.mode==='DEMO_SIMULATION' (AuthProvider.tsx:50-54; line 73 only when client
null, i.e. not connected) -> no guard bypass in UAT/DISPOSABLE. AuthGate wraps App (main.tsx:72-74). `/cp7-preview` reachable by URL in any
mode (App.tsx:439) but Cp7Shell refuses outside DEMO_SIMULATION (src/cp7/Cp7Shell.tsx:33). Modes: DEMO_SIMULATION | UAT_AUTH_SIMULATION |
DISPOSABLE_TEST (src/config/runtime.ts:4); production host forbidden (PRODUCTION_TARGET_FORBIDDEN). Indicator: RuntimeBadge in topbar
(src/components/RuntimeIdentity.tsx:9-15): 'UJI LOKAL · DATA SINTETIS' / 'UAT · MODUL TERPILIH LIVE' / 'DEMO · DATA SIMULASI'; identity
chip shows 'Owner / Simulasi' when not AUTHORIZED (30-34).
FLAG (medium): Dashboard (App.tsx:629-634, component 775-783) renders in ALL modes with hard-coded figures — "Rp284,6 jt", "Rp418,2 jt",
"Rp176,8 jt", "Rp298,4 jt", "Kamis, 27 Agustus 2026", flow strip pcs — and the component has no simulation label (grep of 775-790 for
simulasi/demo/contoh: none). It is the default landing page for any authorized user with dashboard.view (`firstAllowedPageId`, accessCatalog.ts:149).
Only the topbar badge hints the data is not real. Demo components rendered in connected modes (each carries a "SIMULASI/CONTOH" banner, so
labelled): warehouse-dashboard -> WarehousePages (646; "data simulasi" notes, 243), master-fabric/accessory -> MaterialMasterPages (753),
master-customers/partners/workforce/locations -> MasterDataPages (754; "UX ini simulasi sampai Auth dan RPC domain tersambung", 124),
admin-reminders/settings/period-close/audit -> OperationsAdminPages (759; "DATA CONTOH · UX SIMULASI", 72), master-pattern -> PatternPage (755).
In UAT_AUTH_SIMULATION additionally sales (635), finance (636) and attendance (759) fall back to demo pages (banner "SIMULASI UX",
SalesPages.tsx:92, FinancePages.tsx:51). No route with Native data is reachable without the line-628 guard.

### B7. Zero fallbacks on failed/unauthorised loads
Connected finance/stock pages set an error message and keep or null their data; no zero-fill on catch: ConnectedFinanceOverviewPage.tsx:58,
ConnectedFinanceReportPage.tsx:34, ConnectedCashLedgerPage.tsx:48, ConnectedReceivablesPage.tsx:39, ConnectedJournalPage.tsx:43,
ConnectedFgStockPage.tsx:46, ConnectedSkuHppPage.tsx:39, FinanceAnalysisPanel.tsx:23, NativeAnalysisPanel.tsx:127-179 (FORBIDDEN -> setStaged(null)),
ConnectedSupplierCreditPage.tsx:34, ConnectedPayrollPage.tsx:55,126, ConnectedMaterialsPage.tsx:71 (nulls + error).
`?? 0 / || 0` hits in connected code are pagination offsets or form math: ConnectedCashLedgerPage.tsx:89, ConnectedFgStockPage.tsx:32,66,70,
ConnectedFgBookPage.tsx:36-100, MiscFinancePanel.tsx:14,105,121,130, SupplierPaymentPanel.tsx:61-62, ConnectedSupplierCreditPage.tsx:47 (`??0n`
allocation math). Residual: NativeStagedAnalysisView.tsx:59 `n(t.items.timeline??0)` / `material_needs??0` renders 0 if the totals are absent
(minor; totals are consistency-checked in nativeAnalysisPages.ts:79). nativeAnalysisPages.ts:79,238 use ??0 inside fail-closed checks.
Demo pages use ??0 freely (FinancePages.tsx:213-218, HppPage.tsx:96-98) but are simulation. The substantive "angka palsu" is the Dashboard (B6).

### B8. Horizontal overflow (static only)
Every table/row-grid with min-width >= 560px found sits in an overflow:auto/overflow-x:auto wrapper: .responsive-table (styles.css:127;
used by stock-ledger App.tsx:2154 and Native* panels), .wip-detail-table (cutting-reminders.css:525-537, 1100px), .biz-table/.biz-aging/
.biz-journal-lines (business-pages.css:7,9,17), .biz-all-invoice-table/.biz-sales-timetable (ux-corrections.css:43-48), .hpp-history-table
(hpp.css:13,22), .md-bom-table (master-data-pages.css:13), .mm-history (material-master.css:8), .simatch-lines (supplier-invoice-match.css:6),
.ic-size-transfer (inventory-control.css:10), .qc-size-workbench (finalization-flow.css:2), .ci-lines (contractor-issue.css:4), .cpick-table-wrap,
.ccut-table-wrap, .wh-mini-ledger/.wh-return-history (warehouse.css:10,42), .bsr-size-table (bs-rework.css:16), .supplier-credit-table
(supplier-credit.css:4), .native-demand .responsive-table (native-demand-history.css:13). Other `min-width: N px` hits are @media queries.
Residual risks (unverified): white-space:nowrap-dense files laundry.css (15), procurement.css (14), warehouse.css (12), ux-corrections.css (12),
movement-book.css (9); 4-column grids `.mm-metrics` (material-master.css) without a <500px override (`.md-rate-cards` has 980/500 overrides).
Runtime check exists only for the K4 FG-summary/analysis screens at 390px (k4_runner_browser.mjs:16 scrollWidth<=innerWidth+1).

### B9. PR #45 not in the candidate
`git diff --stat d0b9e9c2 origin/claude/ux-spacing-layout -- src scripts | tail -3` -> 1542 files changed (branches diverged; merge-base 6d4cda11).
`git ls-tree -r --name-only d0b9e9c2 src | grep -i browsepicker|overlayportal` -> empty; present on origin/claude/ux-spacing-layout
(src/components/BrowsePicker.tsx, BrowsePicker.test.tsx, OverlayPortal.tsx, browsePickerDom.test.support.ts). Confirmed absent.

## Probes to run (runtime)
1. `python3 -c "import cp6_auditor_business_day as bd;r={'status':'FAIL'};bd.guard(r,'2026-10-09','2026-10-10','2026-10-10');print(bd.retry_allowed({},{'A':r}))"`
   in scripts/ -> expected True (reproduces the FAIL-rerun design in A2).
2. Host with `AUDITOR_BROWSER_CASE_TIMEOUT_MS=2000` and a module whose first case never resolves -> expected row INCOMPLETE
   AUDITOR_BROWSER_CASE_TIMEOUT, `report.error`, `timed_out_case`, remaining ids in `missing`, exit 1; probe status INCOMPLETE.
3. DISPOSABLE_TEST login with a role holding dashboard.view -> landing Dashboard shows "Rp284,6 jt" etc. with no simulation label (defect B6).
   Role without finance.cash.view -> open Kas & Bank -> alert "Tidak punya akses ... finance.cash.view".
4. 390px viewport on master-fabric, laundry, procurement, movements pages -> `document.documentElement.scrollWidth <= innerWidth`.
5. Download artifact of job 114435156829 (k4-runner-17 on d0b9e9c2) and grep CP7_K4_RUNNER.json for `business_day_retried` (not fetched here).

## Not determined
- Whether the uploaded JSON for job 114435156829 shows a business-day rerun (artifact not fetched; 6-fetch budget spent on the logs above).
- Whether the UNKNOWN reasons never named in cases (A1) are ever produced by current fixtures (needs fixture inspection or a DB run).
- Whether `is_stale:false` is intentional (staleness handled by ARCHIVED_STALE job state) or a dead flag the UI trusts.
- Runtime horizontal overflow on pages without a 390px screenshot oracle.
