# Astra P20 independent audit — 9 October 2026

Status: IN PROGRESS. No acceptance yet. production_go: false.

Product commit: `2e605bb7d9b6b7903919b8df2be1443f1740140b`.
Product tree: `51935efb12c035496848e2a85590aa18a3ed3d76`.
Frozen predecessor: `9d57b7f5` (tree `64e7dbfd1dadb36f00f88fa3397faf14833e7f0d`).
Documentation head read: `a7f37aec69abfd24226abb77b8ad2f24973525f4`.
The diff from product to that documentation head contains only paths under docs/.
This is one audit of the whole CP7 composition, not acceptance inherited from an earlier audit.

## Authority and boundaries

Owner's current audit instruction, approved owner decisions, then contracts take precedence.
Read AUDIT_PANDUAN_PRO_MAX.md completely at the product commit (415 lines), package README and AUDITOR_START_P20
at the documentation head, OWNER_DECISIONS_20261008 including 9 October, framework contract/oracle/owner ribs,
P19 staged/snapshot v2 contracts, K2/K3 declarations, and CP6 owner addenda relevant to dependent operations.
The guide at this candidate is the original version; historical chat clarifications about evidence origin and
runtime claims remain mandatory. Static review never closes a runtime claim.

No hosted SQL, production, deployments, main, integration or writer-branch changes. Schedules and backups only
inside the disposable CI runtime. No messages, external reminder delivery or credential requests. No product fixes,
weakened assertions or oracle changes to make a failing case pass. First attempt and first failure are retained.
Database URLs must be loopback, and every runtime records candidate SHA/tree plus audit/harness versions.

## Independence and conflict disclosure

Astra authored the earlier timeline optimization PR44. Its behavior is covered by tests here but its final
independent acceptance requires another auditor. Results here must not conceal that conflict.
No same-round peer audit reports or peer Actions logs are read. Writer setup helpers may be reused as fixtures;
every result records fixture_origin, oracle_origin and evidence_origin separately.

- INDEPENDENT_NATIVE_CASE: independently designed case and oracle executed by this auditor in native CI.
- INDEPENDENT_NATIVE_RERUN: existing writer case re-executed by this auditor unchanged; writer oracle identified.
- INDEPENDENT_SOURCE_REVIEW: static claims only.
- WRITER_CROSSCHECK: writer receipts or reports, never independent PASS.

A green workflow is insufficient: count expected IDs and every case verdict, verify restoration and authorization
gates, retain complete JSON and first logs. Missing cases are INCOMPLETE, not PASS. An infrastructure or harness
failure is diagnosed separately from product failure. Never blanket rerun after a case started.

## Test order and outcomes

The case matrix is registered before implementation of independent probes. Additions are append-only with a reason.
Use independent decimal arithmetic, physical conservation, authorization and transaction boundaries rather than
implementation error strings as primary oracles. Negative controls must prove the test would notice the defect.
Run existing regression suites unchanged as supplementary breadth, plus new contract-derived native/HTTP/race/
browser cases. Source hashes before and after establish the product was not altered.

All 19 required areas receive PASS / FAIL / INCOMPLETE / BLOCKED_BY_TOOLING with exact evidence and bounds.
The final report separates our cases from reruns and writer crosschecks, includes one consolidated writer handoff,
and distinguishes software findings from pending owner installation settings or deliberately deferred K4.
