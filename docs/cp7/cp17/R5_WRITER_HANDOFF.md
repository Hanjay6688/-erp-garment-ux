# r5 writer handoff (living checkpoint)

Same mechanism as `R4_WRITER_HANDOFF.md`: commit one piece at a time; updated with every r5 commit on
`claude/r5-fixes-20261019`; the last commit that touches this file is the checkpoint to continue from.

## Rules that stay in force

- Owner reports: plain everyday Indonesian, first sentence says what is done and what is not (CLAUDE.md).
- Follow `docs/ERP_BEST_PRACTICES.md` and its checklist; new general audit lessons go there with their finding IDs.
- Never mutate: main, Cloudflare deployment, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment
  (`vlxdhpkjeevubjxexnfo`, read-only), production. `production_go:false`; D13-9a (the writer does not touch hosted or Drive).
- Do not loosen old oracles/guards to get green; keep failed logs and wrong fixtures. Do not reopen approved decisions.
- No production dump in the repo, public artifacts or logs. No paid services. No messages to other people. No PR.

## Mandate (r5)

Owner D17-2 (19 Okt): "Auditor dl ya, inget lu punya tugas ini di next turn ya" — the auditors went first; the next writer
task is the direct analysis with financial figures (target 3 s). Owner 19 Okt after the r4 retests: "udah semua katanya"
(all three auditors reported). So r5: fix the valid r4 findings, do the D17-2 speed work, qualify on one commit, retest
package for Fable/Astra/Sol.

Basis: candidate r4 `663f6faefcbb9c70f0f99bbc7e78164e03521329` (tree `023f3554`); r5 branches from
`claude/new-session-deapao` at `5eda90e1` (r4 plus docs only).

## r4 audit results (locked reports)

| Auditor | Branch / lock | Verdict |
|---|---|---|
| Fable | `audit/fable-cp1-7-r4-663f6fae-20261019`, lock `ff6045a9` (`audit/fable_cp17_r4/`) | D16-1 oracles 1-5 closed, FABLE-016/018 stay closed, no new product finding; FABLE-012 deferred (D14-9); R4-05 guard matrix 70 cells 0 differences |
| Astra | `audit/astra-cp1-7-r4-663f6fae-20261019`, lock `40238e36` (`audit/astra_cp17_r4/`) | LULUS_UJI_ULANG_DENGAN_BATAS_BUKTI: ASTRA-R3-01, ASTRA-R2-01, ASTRA-R3-02, ASTRA-R3-03 closed; no new product finding; 565 cases PASS |
| Sol | `audit/sol-cp1-7-r4-663f6fae-20261019`, seal `ecb44425` (`audit/sol_cp17_r4/`) | one new S1 (SOL-R4-001), KNOWN-P19-DIRECT-LATENCY open S2 (D17-2) |

| Finding | Severity | Validity check by the writer | r5 item |
|---|---|---|---|
| SOL-R4-001 a valid FG_REPAIR Nota raises two CRITICAL `payroll_work_wrong_contractor` | S1 | Valid by source: `erp.run_v263a_payroll_integrity_checks()` (body of `supabase/migrations/20260901161322_erp_v2_6_15_payroll_component_entitlement.sql:185-202`, same text in the CP4.5a bootstrap, not redefined later) resolves the line's contractor only through PRODUCTION (`work_completion_events`) and REWORK (`rework_orders`); AX (`scripts/cp6_ax_build.py`) taught the eligible-lines view, source CHECK, validator and merge the FG_REPAIR source but not this checker, so every FG_REPAIR line compares the Nota contractor with NULL. Family sweep of the latest CP6 definitions (bootstrap + `supabase/release/cp6-t3/`) and `scripts/cp7-src`: the other payroll source-type branches are source-specific (REWORK cost-post check, production entitlement, rework/work reversal, BS counters) or already know FG_REPAIR (CP7 payment-date floor, source cards) | R5-01 |
| KNOWN-P19-DIRECT-LATENCY (Sol 4.25-4.66 s, Fable 4.6 s SQL / 5.6 s browser, Astra 4.65 s at 100 targets with figures) | S2 known | Valid measurement; D17-2 | R5-02 |

## Not done yet (in this order)

1. R5-01: F03 delta that teaches the checker FG_REPAIR (capture/restore through `originals`), Sol's case as written
   (2 before, 0 after), negative controls (real wrong contractor, missing wage still counted), F03/CP17 wiring.
2. R5-02: D17-2 speed work (start from `docs/cp7/p19/P19_R4_05_DIRECT_LATENCY.md` "Still open").
3. Qualify one commit (115 workflows as r4 + full writer CP6 scenario), receipt, package `cp1-7-r5-*`, boxes, owner report.

## Checkpoint log

| Commit subject | State after it |
|---|---|
| fix(r5): payroll wrong-contractor checker knows FG_REPAIR (R5-01) | `scripts/cp7_payroll_checks_bundle.py` (forward delta on `erp.run_v263a_payroll_integrity_checks()`: left join of `fg_unsourced_repair_wages_v1` on FG_REPAIR lines, `coalesce(wce, ro, fgw)` contractor; anchor checked; captured in `note_report.capture`, expected in `expected_definitions`, F03 extension before the R4-05 guard delta; verify in CP17 and F03 full probes). `scripts/cp7_r5_cases.py`: Sol's case as written + control (wage of another contractor and a missing wage each count once; guard off only inside a rolled-back savepoint). Declaration 343 (163/39/27/57/57). Writer-local PG16 stubs (`scratchpad/r5/checker_local.py`): real Native body, before 2 -> after 0, other-contractor wage 1, missing wage 1, wrong production line 1, reversed Nota 0, restore text exact, second install refused |
| perf(r5): account lookups once per query in the report readers (R5-02) | `scripts/cp7_report_accounts_bundle.py`: in 11 STABLE readers (owner report, run_v268, its pre-scope, run_v267, the non-PO and PO HPP books, sale lifecycle amount, opening credit account, initial prepayment checks, pocket fabric checks, pocket period book) every literal `erp.account_id('<KEY>')` -> `(select erp.account_id('<KEY>'))` (init plan, once per query). Install: precondition that all 17 keys are core mappings (Native guard refuses delete/rename), then per reader a literal-call-count check and the same regex rewrite in SQL; capture after the note-report and kasbon deltas (owner report and run_v267 compose on top); expected definitions wrap the composed dict. Found while testing locally: an inline STABLE call with constant arguments is also evaluated by the planner while estimating, so the old text refuses a missing key even with no row; an init plan refuses only when a row needs it — closed by the core-mapping precondition. Writer-local PG16 synthetic reader: 66,008 -> 12 account_id calls, same rows, SQL rewrite == Python rewrite, unwrap restores. CP17: `CP17_R5_02_REPORT_READERS_SAME_ANSWER`, `..._REVIEWED`; declaration 345 (165/39/27/57/57) |
| test(r5): R5-02 composes with the note report check; test copies callable as owner | CI at 1eee1e7f: F03 full 39204178773 success 8/8; CP17 39204171233 342 PASS + `CP17_R5_01_VALID_FG_REPAIR_NOTA_ZERO_ALARM_SOL` INCOMPLETE (writer tool: the copy of the old checker sat in a schema the owner role could not use). CI at 9042f7a9: F03 full 39204920099 8 groups, capture diagnosis 39204922149 and CP17 39204918044 INCOMPLETE: `cp7_note_correction_verify.py` required the installed owner report to equal the note delta alone (`NOTE_NATIVE_REPORT_EXACT_READ_DELTA`); now it requires exactly the note delta plus the declared R5-02 rewrite. CP17 there: the same R5-01 tool error and `CP17_R5_02_REPORT_READERS_SAME_ANSWER` (same cause: copies not callable as owner, so every call compared a refusal with rows). Grants on the savepoint-only schemas; the mismatch message now carries both answers. Failed logs kept: `scratchpad/cand-logs/r5/` (writer) |
| test(r5): reader comparison runs both readers as the database owner with the owner's claims | CI at 7ca9554e: F03 full 39207390804 success 8/8; CP17 39207388943 344 PASS (both R5-01 cases PASS: Sol's case baseline 167 detectors all 0, delta none, old checker 0 -> 2; control: other-contractor wage +1, missing wage +1; R5-02 review PASS with five refusals) and `CP17_R5_02_REPORT_READERS_SAME_ANSWER` INCOMPLETE (writer tool: the installed internal reader is not granted to the browser role, so the owner session got 42501 where the copy answered). Capture diagnosis 39207392615 (sizes 100/300; the run is red only because two of four sizes are planned): 100 targets with figures 2.28 s server (r4 qualification 4.56 s on a comparable runner: without figures 1.25 s vs 1.16 s), `erp.require_internal()` 3,652 calls (was 32,150), `erp.account_id` 2,476 (4 per call of the per-product HPP book, 588 calls); browser 2.87-3.32 s (was 4.57-5.92 s); SQL ladder 2.40-2.91 s. 300 targets with figures: browser 10.3-10.8 s for 1 and 30 days (was refused at 8 s), refused at 8 s for 100 days; background job with figures completes in all three windows (5.1-7.9 s). Log: `scratchpad/p19diag/run_r5_7ca9.json` (writer) |
| docs(r5): P19 R5-02 report readers diagnosis and result | `docs/cp7/p19/P19_R5_02_REPORT_READERS.md`: diagnosis (r4 qualification counters), change, the planner-estimation difference and its core-mapping precondition, result at 100 targets with figures (server 4.56 -> 2.28 s; browser 4.57-5.92 -> 2.87-3.32 s), 300 targets, still open (3 s with figures not marked met). CP17 at 3b9817ae dispatched; `CP17_R5_02_REPORT_READERS_SAME_ANSWER` still to confirm |
| test(r5): reader comparison builds the rows the CP17 books lack and fails on a reader compared on nothing | CI at 3b9817ae: CP17 39209921715 success, `CP17_R5_02_REPORT_READERS_SAME_ANSWER` PASS but vacuous for three readers: inputs compared 0 for `bb_opening_credit_account_v1`, `pocket_period_book_v1`, `sale_lifecycle_po_hpp_amount_v2620d` (the CP17 books hold no opening credit, pocket period or sale journal). The case now builds those rows inside its rolled-back savepoint through the BB/BE probe paths (opening import with three allowances and a customer credit applied; production import with its historical pocket period posted; sale of an opening finished good and its return), records per reader inputs/answered/with value, and fails (`CP17_R5_02_READER_NOT_EXERCISED`) when a reader never answers or one of those three never returns a value. Declaration text updated; best practice E25i. Log: `scratchpad/cand-logs/r5/cp17_3b98.log` (writer, last 400 lines) |
| docs(r5): CP17 at b9dad7bd, every reader compared; candidate next | CI at b9dad7bd: CP17 39213380701 job 117931576806 success; cases read from the log (last 3,000 lines): Native 165, race 39, HTTP 27, browser Enteng 57, all PASS. `CP17_R5_02_REPORT_READERS_SAME_ANSWER` PASS with every reader answered and with a value (inputs: opening credit account 4, pocket period book 1, sale lifecycle 4, non-PO HPP 2, PO HPP 9, owner report 3, the five checks 1 each); fixture opening batch, pocket period, sale and return built and rolled back (full boundary restored). Next: fast-forward `claude/new-session-deapao` to this commit and qualify (115 workflows + full writer CP6 scenario). Log: `scratchpad/cand-logs/r5/cp17_b9da.log` (writer) |
