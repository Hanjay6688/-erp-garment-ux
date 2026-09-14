# Independent X audit

Business candidate: `fa3f76c74b169d4869721a203650be60cd866160`, tree
`582436e12e9c96f123485e8b1a062f6992269bbb`. This audit adds no migration or
rollback and requires all business SQL to remain byte-identical to that candidate.
The writer evidence remains native run 34788467189 and CodeQL 34788467150.

`scripts/cp6_x_independent_audit.py` is executed by
`.github/workflows/cp6-full-schema-validation.yml` immediately after X's existing
authorization regression. It is included in that workflow's source manifest,
and its result is bound to the exact audit commit, tree, and frozen business
candidate. The workflow retains the independent report even when the gate fails.
There is no disconnected test entrypoint or replacement of an existing gate.

The audit probes five ordinary opening balance settlement categories in four
session timezones. Opening balances and settlements are created as drafts and
posted by the existing entrypoints under a real `authenticated` session mapped
to OWNER. The physical timestamp is September 3, 2026 at 00:30 in Jakarta;
the independent expected date comes from Python zoneinfo. Draft inertness,
three-cent journal conservation, partial settlement state, report cash by date,
and report confidence are observed. The caller changes timezone before and after
posting, and the call must preserve the caller's setting.

Two additional controls revoke an existing ADMIN user's activity or its role
after a scrap draft has been created. Posting must refuse atomically under the
same subject, and reactivation must permit the same draft. These are sequential
permission controls, not evidence of concurrent revocation behavior. A final
catalog control verifies 30 table privileges across the three private execution
context tables and the anon/authenticated database roles.

Twelve additional cases cover four vendor payments at Jakarta midnight, four
customer sales payments at Jakarta midnight, and four midday sales controls,
each group using the same four caller timezones. Their payment
dates follow the source invoice. Existing fixture helpers prepare legitimate
posted opening-FG/sales or laundry receipt/invoice state as disposable admin;
the tested drafts and payments execute as an authenticated OWNER. Sales payment
facts are captured without modification. This distinguishes a fixed UTC
function setting from timezone-dependent caller behavior.

The 35 cases each restore the complete ERP function/owner/ACL/table snapshot.
The outer transaction restores the unseeded runtime, including any disposable
schema-usage alignment taken from the existing Auth foundation. Role activity
changes and initial fixture loading are explicitly privileged test setup.
Ordinary financial calls run with actual authenticated session authorization.
Synthetic JWT context is not signed-JWT, HTTP, or UI reachability evidence.

Exit 0 means only this bounded audit passed. Exit 1 means a qualified new
counterexample, and exit 2 means incomplete evidence or fixture/oracle failure.
No source-level suspicion is promoted to a business bug without native evidence.
An empty or partial report cannot pass the final proof binder.

Source inspection also identified remaining `CURRENT_DATE` and timestamp-to-date
casts in other financial, stock, and payroll paths. They require type, wrapper,
and native reachability analysis; this audit does not certify all such paths.
Independent final PASS remains pending. `production_go:false`; CP7 is untouched.

Native #172 (34805036582), audit commit
`d9be2f4cddb80f53ffc9b9687ce2acb9518171e3`, failed at step 71 with overall
INCOMPLETE: eight qualified settlement counterexamples, eleven passing controls,
and four CUSTOMER_RECEIVABLE fixture errors (customer code exceeded varchar(30)).
The fixture is now bounded to 24 characters; no business source was patched.
Every case and the entire unseeded runtime restored exactly: 533 ERP functions
with owner/ACL plus 212 ERP/platform tables. Counterexamples recorded three-cent
cash movement on September 2 instead of September 3 while reports stayed READY.
The failed run and both original artifacts remain evidence, not a PASS:

- `cp6-x-independent-audit`, artifact 10332713766, 19,997 bytes,
  SHA-256 `cd1c40e7605234f9c2a375882952c19625021a2fc42c72ee0261005420dc6281`.
- `cp6-r1-v2620x-full-schema-auth-browser-proof`, artifact 10333132490,
  3,048,311 bytes, SHA-256
  `9749c5530f1732d333af0a681c5f0f2008ab19b338b88b32dea2dac5c447af1d`.
