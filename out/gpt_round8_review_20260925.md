# GPT cross-audit — CP6 round 8

Started 2026-09-25T04:54:39.682Z.

## Identity and scope
Audit parent 8d3ee4c050c969e11d5f78c287d63389d48fe69c; writer tool head 9dd7bc2b9309d008e8a2e50d81876d831f3e5ea7; claimed product a095a9d804d29643721e18635c2c3e26adcd56ea. Repository refs independently retrieved. Writer branch is read-only. No product changes, hosted SQL or deployment authorized here.

## Reading ledger
1. Read AUDIT_PROGRESS.md and AUDIT_WRITER_HANDOFF_CP6.md at audit parent. Prior findings and post-lock permission retained. Current writer claims have not yet been accepted.
2. Contract authority to verify: original M/P/BR plus newly signed C0 as reported by owner; C6 remains draft. Do not apply recommendations/memory as oracle.

## Results
BELUM: C0 hash/ratification comparison; C6 mapping; product separation; A4/A7/A8; run logs; new scenario execution.
No new finding or runtime result claimed. Existing gate dispositions remain HOLD/UNVERIFIED.

## LANGKAH BERIKUTNYA
Follow active checklist at the top of AUDIT_PROGRESS.md. Append each completed source section and actual native observation here; save scenario hashes/run/job IDs in the repository before handoff.

## Contract and scope review (completed source sections, 25 Sep 2026)
- Recovered original M/P/BR; all three SHA256 digests match the prior blind lock. No oracle drawn from writer evidence files.
- C0 current SHA256 e83d56e66812011c9a7a4057bf29987d0bcf62aabc17ad23ab422170abb00c99 matches. Approved precursor at 5d54472 SHA256 d39762da0520f30268a73244e7471b7d990138e3cbe36475d639c7cfca8e926d matches. Sections 1–8 are byte-identical. Diff is only opening status and section 9.
- Section 9 records the proposal “D01–D05 sah seperti tertulis, termasuk 3.4 dan 5.3. D06 menunggu tinjauan auditor atas lampiran C6.” and owner response “sah bos”. This matches the handoff supplied by the user; GPT has not accessed the external writer-chat transcript. Source-integrity ACCEPT, not independent authentication of that separate chat and not business gate ACCEPT. Use D01–D05 as the owner's supplied ratified addendum; D06 remains pending.
- Compared a095a9d..9dd7bc2: 4 commits, 13 paths; only docs and three scripts (auditor_modes, auditor_browser_host, codeql_artifact_gate). No src, migrations, dev or release-product changes in that interval.
- Read all 11 C6 rows against M1691–1699,1753–1757,4448–4479, then requirement/test ID sections M4021–4044,4329–4374,5254–5307. C6 hash 72621c8a978573506b8c829a2a8790de948f6cb10e83ecd14dfddf35d495bc0d matches.
- **P2 documentation/qualification gap R8-C6-01:** C6 uses new ACC-01..04/LAU-01..07 group labels but lacks the original 39 ACC acceptance / 36 LAU test crosswalk and does not establish which CR is already in the candidate. Mixed LAU-07 cannot make already-decided vendor master/pending/unknown guarantees discretionary; ACC-04/LAU-05 deferral must exclude existing baseline behavior. Oracle M1697,1757,4329,4448,4479 and C0§8. Not a new proved product bug. GATE-16 HOLD. Detailed row review in out/gpt_round8_c6_review.md.
- A7=CP6-25 safe refusal wording; A8=CP6-19 direct-SQL prepared-edit residue. Handoff classifies both optional P3. Native/permission cross-check still pending; no new product repair requested solely from that classification.
- Browser GitHub authenticated and workflow visible, but no Run workflow control; menu only badge/pin/disable. Connector has rerun but no dispatch operation. Plan: a single audit-owned push workflow, pin tool9dd7bc2, run independent cases on disposable local stack; no writer/main/competition change. No dispatch performed yet.

## LANGKAH BERIKUTNYA (supersedes earlier checklist)
1. Finish per-case C0 oracle for 25 T2, preserving old 12 HOLD. Obtain current T2 LOG and exact case IDs.
2. Build/review/hash GPT scenario plus an audit-only workflow (one phase at a time), include positive distinct-source and multi-receipt cent tests; commit before run.
3. Inspect new Actions run identities/jobs/results and cleanup; persist each completed run. Review A7/A8 and B1–B6 with source and native limits.
4. Finish C6 source inventory and draft scoped disposition; D06 needs owner ratification after this review, and baseline evidence must pass before GATE-16 ACCEPT.

## GPT round8 native preparation — 2026-09-25T05:07:35.329Z
- Fable checkpoint 6fcd5784a3bfb070f901eb59de0be072e2026ef0 preserved; his current round8 runs are separate provenance. GPT adds multi-receipt cent oracles and mode-level B1 sentinels plus independent affected-case reruns.
- Scenario `audit/scenarios/round8/gpt_round8.py` SHA256 695faf3e6d4d393705d423940b47012ae2c9b4ccf68dc509fc7f1b7b64bee77b; tool probe `gpt_tool_modes.py` SHA256 0cad838261da653b2fd3b594042148e4ff54d1db6fa04c256add36b195c8df85. All dependencies/hash receipts in MANIFEST.json. NOT_RUN before this commit; run/job IDs pending.
- One workflow `.github/workflows/gpt-cp6-round8.yml`, push only on audit branch, three jobs (business+race+HTTP; invalid-mode sentinel; existing writer selftest). Checkouts pin tool9dd7bc2 and original bootstrap refs; no hosted target, read-only workflow token, no product files changed. Pushed scenario/workflow will trigger disposable execution.
- **R8-B1-01 P2 tool candidate:** race/HTTP loops do not reject duplicates or unknown statuses (cp6_auditor_modes.py99–126,237–267); strict regular/browser guards do not cover them. Native sentinel oracle: duplicate must refuse before calls, invalid status must be INCOMPLETE; first result must not disappear. Tool test intentionally repeats IDs; not product cases.
- A4 oracle: zero remaining qty requires zero inventory value; two receipts/invoices each round independently, and full consumption must conserve the sum of posted document cents (M3818/3820; existing CP6-03). The disclosed 0.01-per-receipt residual is a known limit, not contractual permission to close the finding.
- A8 oracle qualification: prepared-edit refusal proves no stale posting on that path, but does not itself prove editable DRAFT under M3817. GPT variant retains INCOMPLETE for that aspect until reachable ordinary UI/API scope is established; Fable historical result preserved.
- LANGKAH BERIKUTNYA: record new push run ID and job IDs immediately; read all per-case JSON, expected refusals/atomicity and cleanup; commit after completion. Then browser and new T2 oracle phase, full rollback/log review, C6 inventory. CP6 HOLD, audit_complete=false, production_go=false.




## GPT round8 — independent native results (25 September 2026)
**CP6 HOLD · audit_complete=false · production_go=false.** Candidate tool `9dd7bc2`, product `a095a9d`. Historical 12 HOLD unchanged. This section supersedes the earlier IN_FLIGHT entry for run 36097284096 only; it does not relabel old candidates.

Run [36097284096](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36097284096), audit commit `f28a871d`. Full per-case JSON, job IDs, source log line numbers and SHA256: `out/gpt_round8_run_36097284096.json`. Scenario hashes remain in `audit/scenarios/round8/MANIFEST.json`.

| Scope | Evidence | Gate disposition |
|---|---|---|
| A1 duplicates, A3 dated WIP and positive dates, A9 three-party dated capacities + controls, A10 WIP identity + positive controls | 28/33 ordinary cases PASS across these and four single-receipt cent cases, import-51 selector, ordinary edit and replay | ACCEPT for the explicitly listed cases only; complete business gates not closed |
| CP6-03 / A4, multiple receipts, direct + invoice, UP + DOWN | Four COUNTEREXAMPLE, job107952094985 lines1888–1891 | HOLD; existing P2 finding remains open, not a duplicate new finding |
| A6 close race, WIP race quantity safety | 2 PASS, job107952094985 lines1894–1895 | ACCEPT for safety cases; A7 message specificity remains optional P3 |
| A8 prepared edit | Ordinary validate→edit→finalize PASS. Exposed prepare→edit explicitly refused: INCOMPLETE for draft editability | UNVERIFIED reachability/editability; no stale successful post proved via this legitimate edit |
| B1 savepoint strictness | Writer selftest independently executed: SELFTEST_PASS, job107952095105 | ACCEPT for duplicate/status/isolation checks in ordinary mode |
| B1 race and HTTP strictness, R8-B1-01 | Both duplicate IDs erase earlier INCOMPLETE; unknown statuses accepted; job107952095197 still RUN_COMPLETE | HOLD, P2 tool/evidence integrity |
| Real Auth HTTP | Revoked and unmapped users PASS; old H1 dummy arguments produce business validation errors | H1 UNVERIFIED, not a promoted product finding; fix arguments before rerun |
| C6 / GATE-16 | Eleven-row review in out/gpt_round8_c6_review.md; source policy crosswalk incomplete | HOLD; D06 remains unratified |

### Verified residual CP6-03 (P2)
Two separately rounded one-unit receipts of the same material, both fully consumed; physical stock = 0. UP correction 10.00→10.005 makes two document totals 10.01+10.01=20.02. Actual inventory 0.01 and WIP20.01; required inventory0/WIP20.02. DOWN 10.01→10.004 makes totals10.00+10.00=20.00. Actual inventory−0.01 and WIP20.01; required inventory0/WIP20.00. Reproduced through direct correction and supplier invoice. No return or tolerance-policy ambiguity in these fixtures. Writer's disclosed per-receipt limit describes the remaining defect; it does not authorize closing the contract gate. Oracle: Master Pulih M:835 (cent reconciliation principle), M:3818–3820, M:6625/M:6632 (GRNI/AP/stock/HPP reconciliation, sold-out cents, total/per-date value). Likely mechanism: `supabase/dev/cp6_ba_t1_family.sql:670–684` uses rounded aggregate stock endpoints, losing the sum of individually posted receipt cents.

### R8-B1-01 (P2 tool; extension of existing runner-integrity finding)
`gpt_tool_modes.py` returns INCOMPLETE then PASS for the same ID, plus NOT_A_VALID_STATUS, independently in race and HTTP. Both first results disappear from final counts; final RUN_COMPLETE/job success. Source `scripts/cp6_auditor_modes.py:99–126,237–267`: dictionaries overwrite and finish checks only INCOMPLETE/cleanup, not uniqueness/status vocabulary. This does not turn our unique-ID business results into failures; it invalidates a claim that all modes enforce B1. Required oracle: each planned case retained once, duplicate IDs rejected, unknown vocabulary→INCOMPLETE, incomplete cannot become complete by overwrite (Master M:1699/M:4324).
All three jobs: primary unchanged, clones removed; HTTP Auth counts restored. No hosted access.

### HTTP and prepared-draft qualification
H1 OWNER import read uses a random nonexistent batch; viewer accessory write uses an unknown action. Errors therefore cannot establish either access failure or access success for valid actions. Keep raw COUNTEREXAMPLE for provenance, classify the audit conclusion UNVERIFIED and rerun valid calls. A8 explicitly refused edit establishes no stale post, but does not establish editable prepared drafts required by M:1025/M:3817. Review real public reachability before deciding necessity/severity; retain old P3 distinction.

### LANGKAH BERIKUTNYA
1. Write/freeze 25 fresh T2 oracles from C0 D01 (8 AS +12 calendar+4 AO+1 adjustment); preserve historical statuses. Assert amounts and dates by prefix, not only current totals or equality to writer output.
2. Resolve Fable oracle differences explicitly: calendar WIP82.37/FG49.43/COGS32.95 after first partial invoice; inventory remains at E before cutting G; open adjustment recost dated max(E,A), not an early expense at E.
3. Run the next audit-only workflow phase pinned to the same candidate: C0 cases, valid real-Auth HTTP, and browser timezone/actions. Changing the current workflow and new scenario together avoids rerunning the completed business phase.
4. Cross-review T3/rollback/CodeQL actual Actions logs with provenance; finish C6 source crosswalk and A7/A8 recommendation. Commit each run/finding, then update combined report and writer handoff without duplicating CP6-03.
