# AR combined successor qualification

This is a writer regression gate on the unchanged AR product at
`0d53bd46d7da7f7c937263f2a2ab8a45e059b9fc` (runtime qualified at
`8f1a6ecceda40cb2b7b551d307bd6425b4899a24`). It adds only six harness,
workflow, pin and documentation files. No admitted migration, historical
runtime verifier, old workflow, business oracle or application source changes.

The old full-schema workflow remains an AC contract. Its rejection
`AC_ONLY_EXACT_SUCCESSOR_REPAIR_ALLOWED` is retained, not converted into a
PASS. The new gate binds the complete AR product tree and verifies the old AR
source gate in a separate checkout of its own frozen commit. It verifies all
648 functions and 7,148 runtime objects on AR before and after each new group.
Success is bounded regression evidence, not closure of the historical workflow.

The disposable workflow builds the same pinned AC→AN predecessor as the AR
qualification. It first executes the unchanged AR runner (174 cases, two
pre-use rollback cycles, concurrency, advisors, post-use refusal and cleanup).
It then creates a new disposable AN clone, installs the exact AO/AP/AQ/AR
packages under closed admission, and runs these original case declarations:

| Group | Cases | Oracle |
| --- | ---: | --- |
| Business and linked accounting/stock/HPP | 230 | Unchanged AL business oracle previously run on AM |
| Native import, draft edits and reference validation | 31 | Unchanged AL import oracle |
| Typed values, journals and opening quantities | 65 | Unchanged AL value oracle, including 27 original AK declarations |

Declarations are extracted as exact contiguous AST slices from hash-pinned
files. Every case ID and expected count is explicit. Historical runtime runners
are not invoked on a different catalog; their guards remain untouched. This
runner uses the full AR verifier. Existing narrow historical oracle adapters
remain as recorded in their original files; no new result or runtime monkeypatch
is applied by the successor harness.

All 326 cases use real database functions. Each case must restore every ERP
table, Auth rows, migration history and schema ACLs. Temporary schema usage is
limited to the old native fixture transaction and rolled back. Function bodies,
owners and execute ACLs remain unchanged. Public HTTP/CSV/browser transport is
not established by these native tests. The primary AN database must remain
unchanged and the test clone must be removed.

The historical 12 open-period calendar records remain
`DATE_POLICY_REVIEW_REQUIRED`. Owner date policy was already decided; these
records are retained pending a separate policy-specific proof, not a request
to ask the owner again. The new gate must collect all 500 records, preserve the
12 exact HOLD IDs, and produce no new bugs, gaps or incomplete cases. An Actions
success therefore means `REGRESSION_COMPLETE_WITH_12_HISTORICAL_HOLD`, never
500 PASS or independent acceptance.

First native run `35775713029` completed the unchanged AR stage, then stopped
before all 326 additional cases: the primary snapshot connected as `postgres`
although the fixture reset requires the existing `supabase_admin` session.
The successor harness now uses that administrator only on the disposable local
primary, grants no new privilege, and includes initial snapshot failures within
its cleanup/reporting boundary. This is a harness repair, not a product change.
The failed evidence remains a failure; a complete successor result is pending.

Follow-up work is policy-specific
date proof, fresh affected Auth/browser coverage, and independent review of the
unchanged AR repair plus residual risks. CP6 stays HOLD; CP7, main, hosted
migration and production are outside this gate. `production_go: false`,
`hosted_migration_installed: false`, `independent_acceptance: false`.
