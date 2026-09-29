# F02 independent findings — repair candidate

29 September 2026. **F02 HOLD; native retest pending. `production_go=false`.** This is a writer repair/retest handoff, not independent acceptance. The historical F01 limited checks, 18 independent passes, 54 writer reruns, and mixed-origin evidence remain preserved at their original sources.

Accepted findings: [combined independent handoff at 0999002](https://github.com/Hanjay6688/-erp-garment-ux/blob/09990020355fb7329fbc7b8710692bf1357d2401/audits/cp7_f02_20260929/HANDOFF.md). F02-01 is the auditor's current WIP cancellation defect. F02-02/X06 originated in [peer PR34](https://github.com/Hanjay6688/-erp-garment-ux/pull/34), then was independently reproduced by the second auditor. Their origin and runtime scopes remain separate.

## F02-01 cancellation projection

Ordinary QC or laundry receipt reversal retains a CANCELLED BS case. The cutting capture retains that row and its dependencies for immutable archive/staleness checks. The active graph now omits the cancelled physical slice after validating that its linked source was reversed. A cancelled case pointing to an active/missing source remains a conflict/unknown; active orphans and active children without a physical case remain refused. Historical holds attached to a cancelled case do not reserve current WIP. Source arrays, completeness limits, authorization and negative-prefix conservation are unchanged. No business writer or ERP data is edited by this reader.

`scripts/cp7_f02_audit_replay.py` packages five unmodified auditor case bodies: QC with BS reversal, GOOD-only QC/receipt control, laundry with BS reversal, rework-completion reversal control and 50/51-scope plus 2000/2001-source bounds. Its module records the exact upstream probe hash. A writer executing these cases is explicitly a replay, not a new independent audit.

Additional writer cases cover a new valid QC/BS after cancellation; a new laundry receipt/BS with cancelled history in a mixed opening+cutting scope; retained HOLD history; active orphan, inconsistent cancellation, negative prefix and active-child failures. Current Auth/HTTP capture after reversal must return `[100,100,0,0,0,0]`, replay the identical request and deny access after current revocation. Both public WIP readers and immutable archives are covered.

## F02-02/X06 private matching boundary

`check_allocations` recomputes `match_target` from explicit source and target facts. A label-only legacy call returns UNKNOWN/MATCHING_FACTS_REQUIRED. The source snapshot must match the positions; source keys/sizes/version references must bind the actual position; reviewed edge refs must contain both source and target refs. Duplicate/missing facts fail closed. A positive label cannot override INCOMPATIBLE, NEEDS_CHECK or UNKNOWN, and a stale reviewed match is refused. Shared capacity, exact rational yield and scenario separation remain unchanged.

Private-kernel regression uses the auditor's 17 PCS, XS, 2/3 yield (11 projected GOOD), RED FACT source and same-key RED→BLUE target. It checks compatible control, forged CANDIDATE_MATCH and CONFIRMED_TARGET, missing required proof, target revision/constraint changes, stale source snapshot and source version, explicit confirmation and ambiguous/missing target facts. Prior capacity-only writer fixtures now provide explicit compatible empty-constraint facts; expected capacity/yield numbers are unchanged.

**Remaining integration obligation:** the kernel remains private and its JSON facts are trusted server-composed input, not authorization proof. P06/P07 must obtain source/target/policy/identity facts from the authoritative capture and enforce current versions at the composed boundary. Public planner Auth/HTTP bypass and stale-preview transaction tests remain OPEN until that route exists. This candidate does not claim a live transaction exploit or that full X06 acceptance is closed.

## Verification plan

The P04 native workflow reruns all 39 prior writer cases, one separate smoke, five auditor replay cases, eight new native regressions and one real Auth/HTTP regression: target **53 cases plus one smoke**. Actual run results and hashes must be appended before this candidate is described as qualified. Accepted CP6 install/restore, advisors and current private ACL gates remain required. P09 has separately qualified 121 cases plus three smokes on source `a499f39`; that is not evidence for this newer F02 candidate.

F03/P10 preparation can continue independently, but no planner joins are promoted through this seam while independent F02 acceptance remains HOLD. R10/P11, failed-wash unknown-rate/P13 and the complete CP7 release remain open.

## Initial repair run retained

Candidate `58a4977f413cfa3d5adfabf99fe8cb0e3fed4112`, [run 36557753382](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36557753382): **45 PASS, 8 INCOMPLETE, plus one separate passing smoke**. All five unmodified auditor replay cases passed, including both BS cancellation counterexamples. New QC/receipt coexistence, mixed replay, active-lineage refusal and real Auth/HTTP reversal also passed. CP6 restoration and advisor gate passed.

Seven allocation cases were incomplete because the new JSONB containment operands lacked parentheses around `->`; PostgreSQL consequently attempted a boolean JSON lookup. The follow-up changes only those operator groupings. One writer-only HOLD test attempted source reversal before RELEASE_HOLD; the accepted lifecycle correctly refused it. The follow-up explicitly asserts that refusal, releases HOLD using the ordinary action, and then reverses the source. Neither the native guard nor the auditor's original expectations are weakened. Initial raw failures remain recorded in `evidence/f02-fix/RUN_1.json` and its compressed report. The next qualification remains pending.
