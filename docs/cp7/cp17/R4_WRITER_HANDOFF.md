# r4 writer handoff (living checkpoint)

Same mechanism as `R3_WRITER_HANDOFF.md` (owner 17 Okt: commit one piece at a time; when close to the limit, the nearest
checkpoint is forwarded to writer Sol). Updated with every r4 commit on `claude/r4-fixes-20261018`; the last commit that
touches this file is the checkpoint to continue from.

## Rules that stay in force

- Owner reports: plain everyday Indonesian, first sentence says what is done and what is not (CLAUDE.md).
- Follow `docs/ERP_BEST_PRACTICES.md` and its checklist; new general audit lessons go there with their finding IDs.
- Never mutate: main, Cloudflare deployment, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment
  (`vlxdhpkjeevubjxexnfo`, read-only), production. `production_go:false`; D13-9a (the writer does not touch hosted or Drive).
- Do not loosen old oracles/guards to get green; keep failed logs and wrong fixtures. Do not reopen approved decisions.
- No production dump in the repo, public artifacts or logs. No paid services. No messages to other people. No PR.

## Mandate (r4)

Owner 18 Okt, after Fable and Astra locked their r3 reports and before Sol's: "mulai aja ntar nyusul, tar tinggal lu cek
temuannya valid apa engga". So: fix the r3 findings now; when Sol's report arrives, check each Sol finding for validity
(reproduce or refute with evidence) and fold the valid ones into r4; then qualify on one commit and prepare the retest
package for Fable/Astra/Sol.

Basis: candidate r3 `b53b5acdf260b03ebac3474e9ae837fcef6f6eb1`; r4 branches from `claude/new-session-deapao` at
`64339905` (r3 plus docs only).

## r3 audit results (locked reports)

| Auditor | Branch / lock | Verdict |
|---|---|---|
| Fable | `audit/fable-cp1-7-r3-b53b5acd-20261017`, lock `2033fdfc` (`audit/fable_cp17_r3/`) | D16-1 oracles 1-5 closed, FABLE-016 and FABLE-018 closed, no new finding; FABLE-012 still deferred (D14-9) |
| Astra | `audit/astra-cp1-7-r3-b53b5acd-20261018`, lock `741ffdf3` (`audit/astra_cp17_r3/`) | HOLD: 2 S1, 2 S2 (below) |
| Sol | `audit/sol-cp1-7-r3-b53b5acd-20261017`, seal `ff6374ad` (`audit/sol_cp17_r3/`) | no new blind product finding; three known open items for the writer (validity in `docs/cp7/cp17/r4-sol/README.md`) |

| Finding | Severity | Validity check by the writer | r4 item |
|---|---|---|---|
| ASTRA-R3-01 public CP4 pool wrappers skip the CP7 closed-period and manage-permission refusal | S1 | Valid by source: `supabase/migrations/20260902043000_erp_v2_6_16_cp4_hpp_route_auth_boundary.sql:470-544` only calls `erp.require_owner_admin()` then the Native writer, granted to `authenticated`; the CP7 app does not call them (`src/` uses `erp_cp7_save_hpp_pool_v1`). Family: 69 public non-CP7 routes the browser role may execute; 40 app routes and 4 reminder routes kept, 25 closed to the Data API (`scripts/cp7_public_routes_bundle.py`). Local (throwaway PG16): 25/25 definitions equal the Python expectation, ACL unchanged, Data API session refused, database session unchanged, restore exact; review case PASS against stubs. Fixed (committed) | R4-01 |
| ASTRA-R2-01 remainder: reopen still blocked after a positive FG adjustment and its inverse | S1 | Valid by source: `po-reopen.sql` counted every negative movement as use minus its own reversals, so the -2 REVERSAL of a +2 inflow was a use. Fixed (committed), CP17 cases added | R4-02 |
| ASTRA-R3-02 Audit Trail paging skips a lower id committed after the first page, no "newer" flag | S2 | Valid: reproduced locally with Astra's schedule on the old `audit.sql` (COUNTEREXAMPLE; harness `scratchpad/r4audit/run.py` of the writer, throwaway PG16); new `audit.sql` PASS. Fixed (committed) | R4-03 |
| ASTRA-R3-03 connected WIP numbers pale on white cards | S2 | Valid by source: `.cwip-kpis article` / `.cwip-list>article` set `background:#fff` and the text inherits `#f4f6fb` (`src/styles.css` root). Same family found by the new readability census on Master Data > Pola. Fixed (committed) | R4-04 |

## Not done yet (in this order)

1. Done: R4-01..R4-04 (+R4-04b), Sol validity (`docs/cp7/cp17/r4-sol/`), R4-05 (owner D17-1).
2. Qualify one commit on `claude/new-session-deapao` (fast-forward from `claude/r4-fixes-20261018`; workflow list = the
   115 of the r3 receipt, `scratchpad/qual_r4_files.json`), receipt with `scripts/cp7_ci_receipt.py`, package
   `docs/cp7/audit-candidate/cp1-7-r4-20261019/`, boxes (`scratchpad/r4pkg/boxes.py`, set SHA/TREE), owner report.
   First candidate `769f2cc3` withdrawn (R4-Q1, see the log); the next candidate is the commit that carries this line.

## How to check locally

As in `R3_WRITER_HANDOFF.md` ("How to check locally").

## Checkpoint log

| Commit subject | State after it |
|---|---|
| fix(r4): PO reopen ignores the inverse of an inflow (R4-02) | `po-reopen.sql` skips a negative movement that reverses a positive one; `scripts/cp7_r4_cases.py` (Astra's case as written + 2 controls + 1 race) wired into `cp7_cp17_fix_cases.py`; declaration 325 (156/35/24/55/55); workflow paths include `scripts/cp7_r4_*`. Local: compile + clash check of po-reopen.sql, py_compile, declaration equal. Not yet run in CI |
| fix(r4): Audit Trail says when a late commit changes the listing (R4-03) | `audit.sql`: listing mark (count-sum inside the cutoff) in `snapshot.listed` and in the keyset cursor `<id>:<mark>`; a differing mark answers `changed`/`newer`; refusals for a stray mark. Screen stops paging and asks for Muat ulang (`src/ConnectedAuditTrailPage.tsx`, `src/auditTrailContract.ts`, DOM test). r3 browser case checks the new cursor. CP17: Astra's schedule as written + 3 control races + 1 Native refusal case; declaration 330 (157/39/24/55/55). Local: compile + clash, DOM 21/21, tsc, old-vs-new harness. CI run 39147330072 (R4-02) still queued |
| fix(r4): light cards set their own dark text; readability census (R4-04) | `src/connected-wip-status.css`, `src/pattern-page.css`; `scripts/cp7_r4_readable_browser.mjs` (2 CP17 browser cases, every menu, desktop+phone, < 2:1 refused, WIP figures >= 4.5:1), also run by `scripts/ui_phone_width_census.mjs` on the demo build (local: 47 menus, 0 unreadable after the fix; before it Pola had 4 texts at 1.08:1). Declaration 334 (157/39/24/57/57). Local: build, census, CSS/source ownership, WIP DOM tests 198/198 |
| fix(r4): older public routes refuse a Data API session (R4-01) | `scripts/cp7_public_routes_bundle.py` (25 routes get a first statement refusing session_user `authenticator` with 42501 CP7_PUBLIC_ROUTE_CLOSED; captured/restored through `note_report` like every F03 predecessor delta; no grant change; `verify()` fails on an unreviewed public route a browser role (authenticated or anon) may execute, or a closed route without its refusal, or one that is not SECURITY DEFINER); role stack 50 (both manifests, `cp7_f03_full_probe.py`). CP17: Astra's two HTTP pool cases as written (last, they leave the period closed and ADMIN without manage), 1 HTTP control (all 25 refused through real Auth by name, nothing written, app routes answer), 2 Native (same call as database vs Data API session; review fails closed). Declaration 339 (159/39/27/57/57). Signature keys must be the search_path-free regprocedure text (`timestamp with time zone`, not `timestamptz`), checked at capture |
| docs(r4): best-practice lessons from the r3 audit | `docs/ERP_BEST_PRACTICES.md`: B8e (ASTRA-R3-02 listing mark), C12c (ASTRA-R2-01 pairing both ways), C12d (ASTRA-R3-01 close every old public route, census), D17a (ASTRA-R3-03 readability); checklist lines added. CI: CP17 39147330072 (f7cd6e3b) running; CP17 + F03 full dispatched on 9cd7da11 (queued behind Sol's audit runs) |
| fix(r4): HPP pool panel and BS RecordTools readable (census found them) | CP17 39147330072 at f7cd6e3b PASS 325/325 (R4-02 incl. Astra's case). CP17 39150359349 at 9cd7da11: 335 PASS, the 4 R4-04 readability cases INCOMPLETE because the new census found real unreadable texts on connected screens with data: BS & Rework RecordTools buttons (light text on browser grey, 1.11), HPP pool period buttons (brown on dark, 1.88) and blockers (1.73). Writer replica with the built CSS reproduced the same ratios plus the same family in the pool preview facts, draft form labels and warning (1.02-1.88) that the census could not see yet; after the fix 0 below 2:1. `src/hpp-pool.css`, `src/connected-bs-resolution.css`; the case now opens the pool preview and draft form (read only) and prints one compact line per family. Failed log kept: `scratchpad/cand-logs/r4/cp17_9cd7da11.json` (writer). F03 full 39150361080 at 9cd7da11 PASS |
| fix(r4): connected Master Data screens readable (census found them) | CP17 39152170681 at 82e515f5: BS and HPP pool fixed (gone from the list); with one line per family the full list showed the same family on every connected Master Data screen (white/grey buttons, list items, tabs, the light form: app light text on light boxes, 1.06-1.08). Writer replica with the built CSS: 19 below 2:1 before (also facts, usage chips, action buttons), 0 after; dark-on-dark notes (2.18-2.79) lifted too. `src/master-connected.css`. Failed log kept: `scratchpad/cand-logs/r4/cp17_82e515f5.json` (writer) |
| docs(r4): Sol r3 validity check; CP7C backup patch prepared, not applied | `docs/cp7/cp17/r4-sol/`: pool entrypoints = R4-01 (done); backup replacement write valid, patch held for CP7C (D13-9a), writer-local 12/12 PASS with it and the new case FAIL without it; P19 direct latency valid measurement of the declared gap, owner timing choice asked |
| docs(r4): record owner D17-1 (do the analysis speed work in r4) | `docs/cp7/OWNER_DECISIONS_20261008.md` D17-1 verbatim. CP17 39154513712 at 1058997e: success (all readability cases PASS) |
| diag(r4): function-time diagnostic of one direct analysis capture per finance mode | `capture_diagnosis` in the scale SQL ladder (100/300 targets, rolled back, labelled not app latency) + dispatch-only `claude-p19-capture-diagnosis.yml` (`P19S_ONLY_SIZES=100,300`; registered by its own push). Run 39157467151: with figures 100 targets 6.3 s server, `erp.require_internal()` 32,150 calls = 3.9 s; owner report read twice (2.6 s each); JIT irrelevant; 300 without figures 3.1 s (compiler), browser 26.5 MB (result sent twice). Details: `docs/cp7/p19/P19_R4_05_DIRECT_LATENCY.md`. Log kept: `scratchpad/p19diag/run1.json` (writer) |
| fix(r4): analysis panel states its WIB start clock at once (R4-05) | `src/NativeAnalysisPanel.tsx`: "Sedang dihitung sejak jam ... WIB" when the request is sent (was after a 3 s timer). Local: tsc, 110 panel/transport tests |
| perf(r4): internal access guard answers the no-context case with one probe (R4-05) | `scripts/cp7_internal_guard_bundle.py` (last F03 delta, hash-checked; f03 `patched_internal` composes it; verify in CP17 and F03 full probes); CP17 Native `CP17_R4_05_INTERNAL_GUARD_SAME_ANSWER` (old/new side by side, 8 callers) and `..._DISPATCH_REVIEWED`; declaration 341 (161/39/27/57/57). Writer-local PG16 stubs: 27 callers equal, both cases PASS; 89-103 -> 29-45 us per call. CI dispatched at 27f04d72: CP17 39159623640, F03 full 39159630980, capture diagnosis 39159625311 |
| test(r4): sales dispatch equivalence knows the declared R4-05 probe; R4-05 results | CP17 39159623640 at 27f04d72: PASS 341 (both R4-05 cases; owner with a sales context row ALLOW/ALLOW). F03 full 39159630980 at 27f04d72: 7 groups success, p11 `P11_COMMAND_PRIVATE_FIELDS` INCOMPLETE (`cp7_p19_sales_dispatch_equivalence.py` rebuilt the predecessor guard from the installed text and found the probe; now the probe is checked and left out of the predecessor; decisions and oracle unchanged); rerun 39160732659 at 188c8966: success 8/8. Capture diagnosis 39159625311: 100 targets with figures 2.30-2.60 s in the browser (before 5.58-7.53 s), guard 121 -> 22 us per call; 300 targets still over 3 s (`docs/cp7/p19/P19_R4_05_DIRECT_LATENCY.md`). Local: vitest 174 files / 1663 tests, source/CSS/access ownership. Failed log kept: `scratchpad/cand-logs/r4/f03full_p11_27f04d72.json` (writer) |
| docs(r4): retest package draft at candidate 769f2cc3 (qualification running) | `docs/cp7/audit-candidate/cp1-7-r4-20261019/` (README, CROSS_AUDIT, three boxes). Qualification of 769f2cc3: 115 runs dispatched; red so far only the r3 known-red set (CP6 AI-R2 etc.) plus one new: CP7 P19 Analysis Job Transport 39161868253, job k6-proof-runner-10, `K6P_RACE_PG_CRON_FINISHES_PASS` INCOMPLETE (R4-Q1) |
| test(r4): read pg_cron runs once each end is written (R4-Q1) | Cause: the run that finished the proof pass (runid 1, started 21:20:51.39) commits the pass before pg_cron writes the run's status; the case read the runs at 21:20:52.2 and saw only `running`. r3 (job 117405683448) passed the same case with cron_runs 1, so the race is old. `scripts/cp7_schedule.py` `wait_recorded` (read-only, at most 60 s, not used by install/verify/uninstall); K6 and K4 pg_cron cases read the runs after uninstall, `quiet` and `wait_recorded`; K4 browser fixture waits before counting. Oracle unchanged. K3 cases already wait for a finished run or expect none. Local: stub `cron.job_run_details` (running -> succeeded after 1.5 s: waited 1.51 s; stuck run: False after 1 s). Best practice E25g. Failed log kept: `scratchpad/cand-logs/r4/k6_proof_runner_769f2cc3.log` (writer). Validation: transport 39168052459 on the r4 branch |
