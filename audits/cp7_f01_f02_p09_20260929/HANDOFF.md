# F01 / F02 repair / P09 independent audit handoff

**Decision: both reproduced F02 defects are independently resolved on this candidate; implemented P09 increment passes this audit. No new counterexample found. Full P09/F03 and future planner integration remain open. `production_go=false`.**

Candidate: product `ee8699829bc53799e5f840bb5490059e456fa81a`, checkpoint `e3ddcec94c4db2b6fe299cdadc82f50d57781bfc`. Execution branch `audit/cp7-f01-f02-p09-retest-20260929`, initial audit commit `b345d4e4fb50e0142d9e741acccf926863bb5617`, [run36563251161](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36563251161).

## Independent execution

**16/16 own cases PASS:** five unchanged original F02 probes, ten additional native probes, one new real Auth/HTTP flow. **146/146 writer regression cases rerun PASS, plus three separate smokes:** full121case P09 suite and25 focused F02 kernel/repair cases. P09's22 committed races and18 real connected desktop/mobile browser cases are included in that146, not added again. Browser console errors0; Auth cleanup and disposable-copy cleanup pass. First execution passed; there were no fixture corrections or expected-value changes in this retest.

| Finding / additional probe | Actual independent result | Disposition |
| --- | --- | --- |
| F02-01 cancelled BS after QC reversal | Cutting and combined readers both return100 input/100 WIP/0 FG/0 BS. Receipt-BS reversal also returns100 WIP. Prior snapshots remain immutable and stale. | **CLOSED on candidate**; do not ask writer to fix again. |
| Repeated cancel/re-QC |100→80 WIP/15 FG/5 BS→100 WIP→90/7/3→100 WIP→87/11/2; active and cancelled cases coexist correctly. GOOD-only and rework inverse controls pass. | PASS; no new finding. |
| F02-02/X06 private matching bypass | RED→BLUE with both forged positive labels refused; required unknown evidence refused. Label-only call returns UNKNOWN. RED→RED valid17input→11projectedGOOD succeeds. Stale refs/snapshot and missing/duplicate facts refused; yield/capacity caps preserved. | **Reproduced private-kernel defect CLOSED**. Future authoritative public-planner seam remains open below. |
| F01 actor/request/access | Same UUID for two actors produces distinct protected snapshots. Other actor read and deactivated actor replay/read denied. Finance grant does not backfill old capture; revocation immediately redacts captured amounts. | PASS; prior accepted F01 evidence preserved. |
| P09 large invoice | One line1×22,000,000 posts; supplier AP journal22,000,000.00; physical quantity1; inverse restores original ledger and receipt valuation240. | PASS; no overflow in this P09 path. |
| P09 multi-receipt invoice |7×13+11×17=278; source AP91/187, quantities7/11; identical UUID posts once; inverse restores both source ledgers. | PASS. |
| P09 multi-input count | Stocks10/10 counted8/7, deltas−2/−3; inverse restores10/10 and all accounts. A reviewed zero-delta line changing before POST rejects the whole old count. | Public native command PASS; multi-input UI still open. |
| P09 shared request domain | Reusing transfer UUID for count cannot return the transfer as a count or create partial count effects; original transfer outcome remains recoverable. | PASS. |
| F02 repaired public HTTP | After actual QC-BS reversal, combined capture100 WIP; same-key replay stable; another actor and deactivated cached replay denied. | PASS. |

Original prior evidence remains at [0999002](https://github.com/Hanjay6688/-erp-garment-ux/blob/09990020355fb7329fbc7b8710692bf1357d2401/audits/cp7_f02_20260929/HANDOFF.md). That historical HOLD is superseded **for these two defect reproductions on the pinned repaired candidate only**. Preserve the original report rather than rewriting its historical verdict.

The accepted CP6 package installation, original-function/ACL restoration, security-advisor gate and backup/restore all pass. Primary database unchanged. All HTTP/browser Auth counts return0; all temporary case databases removed. No hosted writes. Screenshot spot checks cover the independent run's count desktop and combined-invoice mobile; this is bounded visual inspection, not an accessibility certification.

Audit artifact11030893468 ZIP SHA256:`a922449ea3fa83d4167e996cb288ed519d6a1011d99d328ca1d5739ed8129f0c`. Raw expected/actual and boundary details are preserved in CASES.json and compressed reports under evidence/. CANDIDATE.json and EVIDENCE_MANIFEST.json bind product, probes and artifacts.

## Writer cross-check

- F02 run36558701316: 53 PASS and one smoke. Downloaded ZIP and raw JSON hashes match the handoff. WIP bundle `bde0745490b055586745c19fa50c01caa32ed1687874f5879ef97422247fe829`.
- P09 run36558701532: 121 PASS and three smokes:73 native,22 races,8 HTTP,18 browsers. ZIP/raw hashes match; P09 bundle `d34acae6754a9e6c390c54696b4b8d7acbf44697723243b249bf79c839344450`.
- Both writer package reports pass original-database protection, backup/restore, security and runtime gates. Auth counts return to zero. App evidence:690 unit/DOM +6shell browser, ownership/build/secret gates and CodeQL succeed.

## Scope kept open, not mislabeled bugs

- P04/X06: future P06/P07 integration must capture authoritative source/target facts server-side and prove current versions, stale-preview refusal and direct-client/Auth/HTTP boundaries. Private-kernel matching acceptance alone cannot close this future seam.
- Full P09/F03: material issues; multi-input/zero-history count UI; mixed-receipt and paid-source supplier return work; remaining full exit matrices and family/release gates. Native multi-input success would not prove the missing UI.
- Latest observed writer head `f41e6eb` adds P10 and App routing. This audit is source-bound to the frozen F01/F02/P09 candidate; no P10 acceptance is claimed.
- Existing accepted F01 evidence and CP6 contract closure remain in place. `production_go=false`. No product edit, deployment, merge, or hosted/UAT/production write.

## Writer continuation

Retire F02-01 and the reproduced F02-02 private-kernel bug from the active defect queue. Keep the remaining integration/feature gates above as named work, not as a claim that these repaired cases are still failing. Preserve source/hash links when updating family status. No new product fix is requested by this audit. Full family/release GO requires the outstanding contract scope; this report does not waive it.

Supporting files: CANDIDATE.json, ORACLE.md, REVIEW_NOTES.md, CASES.json, RESULT.json, WRITER_CROSSCHECK.json, EVIDENCE_MANIFEST.json and source-bound compressed raw reports in evidence/.
