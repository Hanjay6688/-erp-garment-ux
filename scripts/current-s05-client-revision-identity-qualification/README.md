# Native revision identities in the S05 client

The exact successful Native10 run at 519d returned a UUID revision identity
after a late invoice changed accessory cost. The client wrongly required a
decimal bigint string for this field; the original local test repeated that
wrong assumption. Actual retained PostgreSQL catalogue rows also identify
erp.fg_accessory_cost_revisions.id as UUID with gen_random_uuid() default.

This successor changes only that validator and its regression input. Audit
bigint identities remain exact decimal strings. No money, quantity, source,
history, report SQL, Native function, API, permission or prior manifest changes.
The prior source/qualification remains bound to its original 519d bytes.

replay.mjs requires the exact original Native10 CASE bytes, reproduces the old
21-success/one-refusal outcome and requires all22 successful responses through
the successor. Every financial/source field remains equal to the original;
all21 previously accepted responses remain equal to their old parser results.
The four actual access refusals remain42501. Local unit cases reject malformed,
missing and numeric revision IDs while retaining large audit IDs exactly.

This is client-contract evidence only. No new Native, Auth, HTTP or browser
execution is claimed. S05 UI mounting, live desktop/mobile/current-rights
journeys and final composition remain separate. Production remains closed.
