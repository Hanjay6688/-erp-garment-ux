# Astra CP1–CP7 independent audit · IN PROGRESS

Candidate **0b7049d9203bac52b47a4c89f3e0d75646067a8f**, tree **ce6aed0a0af920e8aa80248f3cabcd293688df18**. No product file is changed by this branch. `production_go:false`; CP7C/Drive remains on hold. A GitHub success badge is not this audit's verdict.

Current canonical downloaded-case ledger: **844 executions / 698 unique case names: 841 PASS, three raw COUNTEREXAMPLE**. This is a partial inventory of 18 completed writer suites, nine frozen-Astra groups and five new payroll probes; it excludes legacy-baseline runs and unfinished suites. Repeated case names across groups remain separate executions. `CASE_LEDGER_PARTIAL.json` has no missing/planned-count discrepancy after explicitly counting declared smoke cases.

The three raw counterexamples are the previously accepted staged-validator boundary (`AS20-39_VALIDATION_NEGATIVE`) and two new early payroll-date observations (`CP17-ASTRA-PAY-04/05`). The new public-RPC probes accept ordinary full/installment payment before attendance accrual. The separate dated-partial probe will quantify the cutoff impact. Duplicate attendance through a second Nota was refused for both APPROVED and PAID first payrolls; that forwarded suspicion is not confirmed on those paths.

Owner explicitly permitted reading Fable on 14 October 2026 at 06:50:45Z. `FABLE_EXPOSURE_REGISTER.md` records the override. Only three specific static leads and Fable's new manifest/run register were accessible; the full twelve suspected defects were not supplied. New lead-driven findings will retain that attribution.

`CP1_CP2_EVIDENCE_REVIEW.md` corrects the historical evidence inventory: CP1 has a new measured reconstruction and 19 independently matched SQL files. CP2 has a writer receipt of successful archival decryption/149-member checks, but no independently demonstrated database restore in this session. CP2 is not PASS.

The complete first outcomes remain intact. `HARNESS_QUALIFICATIONS.md` documents the pre-case YAML failure, original temporal committed-fixture limitation, regression logger collision after 76 PASS, and obsolete AR verifier before races. Continuation runs execute only not-yet-run cases, with the original 76 explicitly carried and never rerun.

Active runs: native **38522545215** (31 suites); baseline continuation **38526619037** (remaining regression and 28 AR races); new integration **38527771239** (SKN22, dated payroll, overlapping HPP source). Final seven-stage verdicts are not locked while these results are pending.

`ARCHIVE_INDEX.json` points to complete Original ZIPs preserved in Git, with Git blob and SHA-256 identities. First failed baseline AR/temporal ZIP preservation is still being completed; no successful continuation will replace an earlier red result.

Scope receipt: all DB operations were in disposable localhost CI. Existing repository integration automatically ran **Cloudflare Workers Builds** when the audit branch was pushed; its check reports a branch preview URL/version. Astra did not invoke deployment, visit the preview, or modify Cloudflare configuration. This is an observed automatic repository hook, not evidence of a production cutover.
