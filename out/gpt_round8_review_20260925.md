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


