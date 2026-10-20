# Outer Native scope visibility: first failure and narrow correction

Candidate `a96079dc0f0ee5aadb8bcd07f4fce7a434a12227`, run39483336784,
job118837297372, completed with20 PASS/12 INCOMPLETE. All20 retained controls
passed; every new paid-return case failed at the outer final leak assertion:
`permission denied for table return_native_scope`. Restore and advisor gates
passed. Exact first logs and per-case results are retained in
`CI_A960_FIRST_RUNTIME.log.gz` and `CI_A960_FIRST_FAILURE.json`.

The outer implementation executes as `cp7_credit_write`, which owns its two
new request/scope tables but deliberately cannot read the postgres-owned
Native scope. Giving it SELECT would still hide leaked rows behind default
denial RLS and could turn the assertion into a false success.

The correction preserves the exact predicate and refusal code through a
postgres-owned, SECURITY DEFINER, void-only assertion with fixed empty
search_path. It reads only the current backend/transaction, accepts no caller
identity or table/predicate argument, and receives EXECUTE only for the outer
writer. No table grant, ERP mutation privilege, source permission, monetary
formula, payload, quote, calendar, lock order or final access check changes.
Both source and derived outer wrapper use the same assertion, at the same
position. The existing deferred all-scope closure remains in force.

Expected was declared before execution in `native-scope-fix/DECLARATION.json`.
The actual helper and role/RLS controls pass18/18 locally, including the old
42501 failure, own/current scope leakage, other actor, completed-but-not-cleared
scope, different backend/transaction, outsider execution, direct table denial,
and the unsafe hypothetical SELECT-grant/RLS alternative. This is isolated SQL,
not actual ERP posting, authorization, commit, recovery or browser evidence.

The unchanged32-case Native qualification must run on the next published
candidate. Its original monetary/calendar goldens remain unchanged. The
uncommitted Native EMPTY extension stays disabled and is not part of this fix.
OW-04 remains open; there is no feature/audit/production acceptance.
