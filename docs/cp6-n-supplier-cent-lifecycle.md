# CP6 N: supplier cents through the complete document lifecycle

Incoming M is `8105b470c424717666f3a991c6f2fb461316a52d`, tree
`72eec8699b6855e807bcb14fe8d577da907bf5e2`. Its existing native suites pass.
New counterexamples expose disagreement between rounded source balances and
separately rounded corrections, invoice allocations, and supplier returns.

N journals the change between rounded balances **per purchase**, under the
existing purchase locks. Inventory carrying value retains original return cost
so the separate material cost revaluation ledger is not counted twice.
Existing physical movements, cost history, authorization, and document guards
remain in their owning posting functions. Seven function replacements call
three private helpers; no public RPC or UI route is introduced.

`supplier_cent_posting_facts` records each posting or inverse, including an
explicit zero-cent event without a journal. Facts reject updates, deletes and
truncate, have RLS, and grant no application role access. Non-FIFO reversals
preserve the exact original inverse and add a linked cent adjustment atomically
when the current cumulative balance requires it. V267 reconciles each fact's
account vector to its journals, including an injected offsetting-journal fault.

The migration refuses pre-existing critical supplier inconsistencies without
rewriting history. Pre-use rollback verifies the exact M capsule, N source and
installed definitions, helper and inherited trigger ownership/ACL, fact guards,
and the unchanged 64-table boundary. It restores seven M definitions and
removes only the unused N objects. The maintenance controller checks the new
objects before closing admission; existing F–M admission behavior is retained.

The shared SQL oracle runs five counterexamples before N and fourteen groups
after N. Existing M groups, Auth, races, frontend and security gates remain.
The native workflow qualifies nine generations through 180 schedules with
45 actual backend body entries, exercises direct and pre-admission fault
guards, restores the full migration ladder, and hashes all proof payloads.
PGlite is sequential SQL verification only. Native CI is the concurrency/Auth
authority; passing writer verification still requires independent re-audit.

DO NOT MERGE. `production_go:false`. Main, PR24/25, hosted UAT and legacy are
outside this revision's mutation scope. CP7 rev3 → CP7.5 → CP7C → CP8 remains
the roadmap after independent CP6 closure.
