# F03 independent audit checkpoint — incomplete

Frozen product candidate: `eb6b8682e97e94c95f89d431ab81974c54ddcbaf`.
Audit branch: `audit/f03-independent-20261001` (local; publication was rejected by automatic approval review).

**Disposition: INCOMPLETE, not independently accepted. `production_go=false`.** No confirmed product defect has been established in this checkpoint. The writer's implementation exit and independent acceptance are distinct.

## Independently authored and executed

`tests/cp7/independent/f03-20261001.test.ts`: **26/26 PASS** on the frozen candidate. These are local frontend contract checks: seven-piece discounted invoice arithmetic, exact cents beyond JavaScript's safe integer, one-cent installment capacity, excessive discount, invalid/ambiguous cash and quantity inputs, six-decimal receipt precision, and real calendar dates.

Independent added worksheet: 7 PCS ×37.13 −0.06 =259.85; 123.45 +136.40 settles that amount. This supplements the predeclared three-piece worksheet. No native stock, journal, Auth or connected-browser result is claimed by these tests.

## Cross-checks executed or inspected

- Local official build, including its prebuild ownership/access/CSS checks and postbuild client secret scan: **PASS**.
- Retained local suite: **1,156 PASS; one environment failure** out of1,157. The F04 SQL-kernel test refuses this root-only environment without native PostgreSQL. This is not evidence of an F03 defect. The test was not skipped or relabeled PASS.
- Writer's original JSON archives under `evidence/f03-full-stack/qualified8-37c103e` were opened and their group outcomes inspected. The8 reported buckets match132+3 smokes,34,64,90,50,61,5,10. All have PASS-only groups, the declared counts, restoration and advisor gates; no reported database/cleanup/console exceptions were found. These are writer executions, not my independently executed database tests, and the counts are not unique business requirements.
- GitHub run36861170597 is completed/success at exact source37c103e548bf3ee944f5334f2b0565ba72e0fc19. Writer bundle hash: `6df48df8bbf7113636ce504b2f1f894b43a6444f803ba71a0007c18b32f6907c`.
- Between that source and the frozen candidate, the inspected product diff contains only planning/preflight and analysis-finance changes plus their two bundles. No `src` change appears in that comparison. This supports the retained F03 evidence's relevance; it does not replace independent testing of the integrated candidate or prove every dependency irrelevant.

## Still required before an independent F03 verdict

- Independently authored native transaction probes across P09–P13, including source production/HPP, cash/AR/AP separation, grades/ownership, late corrections, source capacity and exact inverses.
- Real concurrent sessions and revocation during an observed lock wait; current authority on UUID replay.
- Real Auth/REST and connected desktop/mobile browser checks, including source reload and uncertain-commit recovery.
- Full disposable installation/restore and reconciliation of affected extended journeys against the current31-role stack. A historical26-role journey is not automatically a fresh31-role execution.

## Execution blocker and concrete next action

This environment has no PostgreSQL/Docker runtime. Installing Playwright Chromium also failed because the downloaded archive was invalid; no browser case ran. The prepared GitHub workflow `.github/workflows/f03-independent-retained.yml` uses the repository's existing isolated CI installation recipe, restricted to the audit branch, and checks that product files still match the frozen candidate.

Automatic approval review rejected the attempted push of the audit oracle and workflow to the public repository: the user had authorized auditing, but publication of potentially sensitive ERP business rules and financial test data was not considered explicitly authorized. No alternative tool was used to bypass that rejection, and no audit branch was published. Permission to publish the audit-only branch and execute its disposable CI is required before that route proceeds.

Product files and the writer branch were not changed. The audit oracle, workflow and local test evidence are available for review locally. No repair request should be assigned to the writer from an environment failure or an unexecuted hypothesis.

## Authorization update

On2October2026 the owner explicitly authorized publishing the audit branch and running disposable CI, on condition that writer work and real data are not disturbed. The earlier rejection remains a historical checkpoint. The audit workflow is branch-scoped, uses synthetic/disposable data, and limits its retained matrix to two concurrent jobs. Product and writer branches remain untouched.
