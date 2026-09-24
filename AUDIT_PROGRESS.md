# CP6 audit — GPT recovery checkpoint
Date: 2026-09-24 UTC.
Status: **IN_PROGRESS; full CP6 acceptance audit is NOT COMPLETE. Recommendation HOLD. production_go=false.**

## Identity and authority
- Repository: Hanjay6688/-erp-garment-ux.
- Product candidate: `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc`; tree `5d5f833b2e75e23184c643d5ac469781f1c3ce5e`.
- Baseline comparison: `ca7f09556397801c50a2277bdb65b1bf019f9a05`.
- This recovery branch: `audit/cp6-final-20260924-gpt-a0bcadf`, created directly from the frozen candidate. It is distinct from the other auditor's branch. Only audit documentation is written here.
- No product code, main, competition branch, writer branch, hosted/legacy/production database, deployment, or person-directed message was changed by this recovery action.

Only the three supplied contracts define gates/oracles:
- M = ERP_V3_2_Master_Pulih_20260923.md; SHA256 f21ac70360915a1f1021b42a3918e862ca7d11cf88c1b90c5627b4490c69af07.
- P = ERP_V3_2_Perubahan_Pulih_20260923.md; SHA256 92966cd6ed27e64123be6c52e2263bfbdb3db91c97f2e441c3bdc98589397676.
- BR = ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md; SHA256 4566ab6f1c8e53bc21c70c0c777f780b526305815e04d5913a5c858dfaa85886; CP6/CP7 boundary only.
General ERP context, writer comments/assertions and unrelated memory are not normative evidence.

## Scope correction and phase boundary
The original handoff requests **all CP6**, not merely selected findings. The first report was stopped too early. It is a partial checkpoint, not completion.
The full obligation map now has132 rows across27 families:80 core CP6,32 accepted CP6 extensions,13 scope-dependent accessory/laundry CR rows,7 later-stage/optional boundaries. These are audit subdivisions, not132 new gates or132 PASS results.105 stable contract test IDs are cross-referenced.

Phase1 findings were locked before writer evidence was opened:
- PHASE1_FINDINGS_LOCK.md SHA256 cbca0c6cb3150f0005bbea877d1a6b0371afa6103d9907c21899b1e235e46156.
- PHASE1_SHA256SUMS SHA256 50ba9228c863d4c483404bd425d8d64aac3073c3cd6726e35d9ca840d653438a.
- Last successful local recheck confirmed both unchanged.
Phase2 read selected writer handoff/evidence only after this lock. Continuation findings are explicitly post-lock, not retroactive blind findings.
Contamination disclosure remains: earlier audit memory, forbidden filenames/one commit-title snippet, and competitor leads were visible; they were excluded as oracle. Duplicate-ID was independently reproduced before the competitor leak. Advisory-lock and second-connection claims were not promoted to our native results.

## Gate dispositions
C6-01..10 are audit groupings. ACCEPT for a narrow operation does not accept the entire gate.

| Gate | Status | Contract file/lines | Current basis |
|---|---|---|---|
|C6-01 evidence identity/completeness|HOLD|M1624–1626,1693,1762–1767,4391–4393,4521–4525|Exact SHA/jobs bound; runner duplicate-ID loss; T2 disposition and missing independent cases remain.|
|C6-02 atomicity/immutable facts/exact state|UNVERIFIED|M3816–3826,5048–5052|Broad source review, no complete native lifecycle proof; historical capacity/cent risks remain.|
|C6-03 recovery/input/unknown/selectors|HOLD|M1678–1679,1691,3817–3820,3825–3826,3939|Wrong WIB payloads, unstable request recovery and failed-read zero display reproduced locally; selector tails source-supported.|
|C6-04 ALL initial import|UNVERIFIED|M44–45,359–365,749–755,829–843,934–938,1024–1025,1691; P966–967|Template count is insufficient; semantic open-document continuation mapping being extended.|
|C6-05 dates/recost/HPP/journals/reports|HOLD|M375,377,837,1022,1059–1065,1666,1691,3816,3820,3825|F01 wrong WIB payload; U03 cent risk; full dated financial acceptance absent.|
|C6-06 production/AP/AR/payroll/advances|UNVERIFIED|M359–379,629–648,749–757,3822–3824|Source bodies reviewed with explicit limits; U02 and advance dated-capacity candidate need native results; payroll producer follow-up active.|
|C6-07 accepted accessories/pocket|UNVERIFIED|M44–48,466–472,495,557–561,1023,3900–3902,3951,5192–5199|Positive local controls and source mechanisms; whole lifecycle/races not independently accepted; expanded CR scope separate.|
|C6-08 Auth/permissions/connected UI|UNVERIFIED|M1691,4486,5046–5052,5209,5213–5224|27 public RPCs traced;10 browser cases rerun; full real Auth/action/location/revocation matrix absent.|
|C6-09 concurrency/stale state|UNVERIFIED|M751–755,1025,4165,4486,5048–5052|Existing AR/AT/AU races rerun;20 AR observations independently checked narrowly; own full schedules absent.|
|C6-10 install/compatibility/rollback/cleanup|HOLD|M1767,3826,4306–4314,4486,5192–5209|Install/backup restore scoped positive; whole-candidate rollback/refusal unqualified.|

## Fresh selected native job ledger
GitHub can give inherited completed jobs new IDs on later attempts. The IDs below are actual selected fresh executions; actual starts are tracked. A green job is not an independent business oracle.

| Run ID | Job ID | Actual start UTC | Observed scope/result |
|---|---|---|---|
|36037873682|107772639059|18:23:54|Original326:314 PASS/control,12 date-policy HOLD; NEW34:25PASS/8COUNTEREXAMPLE/1INCOMPLETE; AO12:8PASS/4INCOMPLETE. DISPOSITION_REQUIRED, primary unchanged,clone0. Log2198–2199.|
|36037876338|107772603343|18:23:48|24install stages; restored same meaning318tables/1647rows,5checks; Auth0→0/primary unchanged.54advisorINFO reviewed, not assumed security exposure. Log1301–1330.|
|36037878419|107772676223|18:24:00|CodeQL JavaScript/TypeScript PASS,result_count0. Log2415.|
|36037873682|107792476681|19:15:14|AR146sequential+28race writerPASS. Independent raw-observation checker20scopedPASS/5INCOMPLETE/3UNVERIFIED.|
|36037876338|107792486765|19:15:17|Browser10PASS,console0,REST stopped,Auth0→0,primary unchanged. Opening WIP_OUTPUT flow only. Log1608–1609.|
|36037878419|107792495809|19:15:18|CodeQL Actions PASS,result_count0. Log1331.|
|36037878419|107794260297|19:19:58|CodeQL Python PASS,result_count0. Log1811.|
|36037873682|107795483321|19:23:12|AT16+AU15sequential and4+6races writerPASS. Raw worker results retained; boolean invariants not promoted to full independent proof. Log1739.|
|36037878419|107795615827|19:23:33|CodeQL C++ PASS,result_count0. Log1772.|

All are exact9add57e. T3 pins job107772660584/log1340 equal:true was independently retrieved existing evidence, not a new auditor rerun.
AR20 scoped checks verify selected one-effect header/quantity/value/aggregate debit-credit and exact known refusal observations. They do NOT prove all account/dimension/source lineage, dated prefixes, rollback baseline or exact response replay.5 missing exact refusal details and3 boolean-only cases remain open.
CodeQL zero findings does not prove SQL/business correctness.

## Findings and evidence limits
No P0 demonstrated. Priorities do not assert observed production loss.

| ID | Priority/status | Independent oracle and evidence |
|---|---|---|
|F01|P1/local confirmed|M3820 WIB input2026-09-20T00:30 must serializeSep19T17:30Z on every device. Active Cutting/Pickup/BS serialize via device timezone.34exact-source checks28PASS/6FAIL; actual persisted ledger impact not native-tested.|
|U01|P2/native UNVERIFIED|M1691 complete BS sources. Reader caps100 before claimable filtering; no selector continuation. Valid101-source fixture NOT_RUN.|
|U02|P1/native UNVERIFIED|M3816,3820–3823 immutable dated WIP prefixes. Opening8,complete8D−3,reverseD,complete8D−1 predicts negative historicalWIP. Source-supported; SI02 NOT_RUN.|
|U03|P2/native UNVERIFIED|M1022,3818,3820 endpoint money conservation. Qty1 at10.005→10.014 rounds both receipts10.01; recost rounded delta may move0.01 and leave raw−0.01/WIP10.02. Four cases NOT_RUN; compensation not ruled out natively.|
|R01|P2/local confirmed|M1767,4391–4393 traceable evidence. Duplicate IDs overwrite earlier INCOMPLETE in actual unchanged runner AST with I/O doubles. Raw logs retain both. Current indexed native cases had no duplicate group/ID.|
|R02|P2/qualification gap|M3826,4306–4314,5198–5209. FinalAW–AZ rollback files/qualified downgrade/refusal absent; manifestNOT_TESTED. Successful installed-backup restore is not predecessor rollback.|
|C-AUTH-01|P2/local confirmed,post-lock|M1679,3819 retain exact request envelope. Pattern/Access retries regenerate UUID; quick-create can reuse UUID with changed payload.7local checks4PASS/3FAIL. Server uniqueness/version protections acknowledged; no committed duplicate/data-corruption claim.|
|C-SEL-01|P2/source confirmed,nativeUNVERIFIED|M1691,3826,4486;M495 for pocket cancel. Initial-import latest50 and pocket-period latest50 are sole action selectors; payroll/prepayment targets cap100. One public51draft scenario prepared; other valid fixtures unwritten.|
|C-UNK-01|P2/local confirmed,post-lock|M3825 unknown is not zero. Failed initial Laundry/QC workspace read leaves null but unconditional KPI expressions render0.4local checks2PASS/2FAIL. Error banners and writer locks remain; no financial finality or mutation bypass claim.|
|C-BIZ-01|candidateP1/nativeUNVERIFIED|M629–646 and3816–3820. Opening67.25D−8,correctionto100D−2,refund100D−4 predicts normal advance prefix−32.75 for supplier/vendor/customer while current0. Public route source traced; six cases NOT_RUN. Applying dated-prefix rule to advance monetary capacity is stated inference.|
|C-BIZ-02|unpromoted reachability lead|COUNT transfer/adjustment may admit0.5; no independent ordinary route proof. Runner conditionally grants schemaUSAGE. Four cases excluded from default batch; optional execution remains INCOMPLETE with privilege qualification.|

H01 optional WIP identity policy and H02 alternate prepared-item edit reachability remain unpromoted. Nullable deactivation version and GRNI_ESTIMATE_OPEN policy are residual questions, not native-confirmed security/accounting findings.
Auth findings were counter-reviewed by business peer. Root counter-reviewed advance signs/dates/guards and COUNT reachability. Simple sale double-stock-out and reversed-output pocket-allocation hypotheses were eliminated in final source; this is not whole-family acceptance.

## Prepared scenario receipt
Default combined batch:15 cases, native **NOT_RUN**, run_id:null,job_id:null.
- combined_scenarios.py SHA256 `968cac54ac7fa7fe4e3fc1d666e257b04944faf1beec1f45a209274db00869d1`;25248bytes;33664base64chars.
- work/stock_import_scenario.py:4cases; SHA256 ff92e8d973ebb75c05ba8ac6b47da96565c9b50760c91b247f331a765d18df81.
- work/money_dates_scenario.py:4cases; SHA256 cfa1157b7ea39e6f5162d85a540ed5e22c30d8fef9ddfe840b5a9bf2f631d9ef.
- continuation/business/business_scenarios.py:6default advance cases,4held COUNT cases; SHA256 44b075c763a5d6962322d51e4b4ed0b75360b6e0135575420208ac39152b342b.
- continuation/auth_selector_scenarios.py:1case; SHA256 2276140a28ce27e9cd8e18b03285bdeee9aa33aee4118fe701eca20442bc3bd4.
Syntax, embedded-byte/hash equality, JSON roundtrip and unique factory IDs were checked. Factory enumeration used inert runtime imports. No case lambda/SQL executed.

The approved scenario runner grants authenticated erp schemaUSAGE before cases when absent. No auditor grant/revoke added. This limits unmodified-ACL proof; it does not authorize widening any production permission.
The session can rerun existing jobs but has no callable arbitrary workflow-dispatch POST or local DB. Approved API endpoint and exact body are in the offline workspace's continuation/dispatch/. Check branch still equals frozenSHA before dispatch. Do not claim the source files/payload have been copied to this branch: only this recovery document is persisted here at this checkpoint.

## Persistence and actual interruption
Last confirmed durable upload before interruption:
- CP6_AUDIT_PROGRESS.md version1.
- CP6_AUDIT_CONTINUATION_CHECKPOINT.zip version1 (1580593bytes).
- Earlier CP6_PHASE1_LOCKED_9add57e.zip, AUDIT_REPORT_CP6.md version0 and CP6_AUDIT_EVIDENCE_9add57e.zip version0 remain partial checkpoints.

Later local files were created/read successfully, but the execution environment then went offline:
`exec-server transport disconnected`, then409 `environment_offline: Environment is not connected`.
Both exec and apply_patch failed; a direct attempted upload of the final coverage document also failed. Therefore the later report/bundle/JSON/scenario files are **not all durably uploaded**, and an updated final evidence ZIP/receipt must not be claimed.

Last known local root: /workspace/scratch/a0bcadfadc7e/cp6_audit.
Final coverage hashes observed before interruption:
- continuation/coverage_completion.md: c5bb9160e0f6005e8d530a826504b0a61348d1bc8ba081278b70182e4c973394.
- continuation/coverage_matrix.json: e5fdcc9fc6fdd165ee701094e2c60e8639b87673ec73bc9b1554c4c11491fd1d.
New follow-up files for semantic ALL mapping and payroll source producers had NOT been written when the workspace disconnected. GitHub exact-candidate read fallback is now being used; any resulting notes need separate persistence here.

## LANGKAH BERIKUTNYA
1. Continue bounded semantic ALL open-document and payroll eligibility/rate/Special source review via exact9add GitHub reads. Persist complete notes on this isolated audit branch; mark unavailable compressed-baseline/source paths precisely.
2. When workspace reconnects, inspect existing files before restoring anything. Verify candidate/tree/clean status and phase1 hashes. Do not overwrite later local work with older version1 ZIP.
3. Recover/verify15-case payload and four member hashes above. If files are missing, restore the latest durable checkpoint and regenerate only missing continuation artifacts; do not pretend reconstructed bytes match an old hash without checking.
4. Complete revised report,132-row matrix consistency,case/run ledger,hash manifest and checkpoint ZIP. Preserve original report as partial; new receipt must say audit_incomplete.
5. Run15cases through the explicitly approved disposable custom-dispatch endpoint once an authorized dispatch-capable environment is available. Verify SHA/head/phase/plannedIDs/each result/restoration/cleanup; unexpected refusals stay INCOMPLETE.
6. Remaining unperformed work is broader than dispatch: valid pocket/payroll/prepayment/BS tail fixtures; real browser timezone/unknown/recovery; complete Auth/action/location; own concurrency schedules; transitive HPP/producers; semantic ALL; rollback/refusal qualification. Do not attribute every gap to tooling or promote a suite count to full CP6 PASS.
7. Owner acceptance/production decision remains withheld. No product repair is performed by this auditor.

