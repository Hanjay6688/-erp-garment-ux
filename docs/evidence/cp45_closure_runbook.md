# CP4.5 closure runbook

Order is mandatory; do not parallelize database writers.

1. Freeze candidate bytes and run frontend, source, access, CSS, backend ownership, and build gates.
2. Push the single CP4.5 branch and require exact-head Build UX plus full-schema validation success.
3. Re-gate ERP Enteng UAT and legacy ERP Garment read-only; stop if a writer, lock, drift, or target mismatch appears.
4. If base v2.6.17 is absent, apply its exact CI-reviewed migration once to ERP Enteng UAT only, record its platform ledger once, and verify replay rejection. Never replay it when already recorded.
5. Apply the exact CI-reviewed forward-only v2.6.17a correction once, record platform ledger `20260902180726` once, and verify replay rejection. Do not edit migration `20260902104937`.
6. Run immutable-assignment SQL acceptance, both real two-connection races, and frozen CP4/affected CP3 regression on the corrected runtime.
7. Run manual hosted-UAT Auth/JWT permission E2E with temporary OWNER, custom-role, view-only, inactive, and unmapped identities, including initial assignment, second-assignment rejection, and downstream rejection. Classify this as `MANUAL_HOSTED_UAT_VERIFIED`, never CI.
8. Delete temporary sessions, app mappings, identities, users, roles, patterns, assignment facts, and audit/idempotency rows; prove exact zero synthetic residue.
9. Re-gate UAT and legacy read-only, attach non-secret proof, freeze closure bytes, and run exact-head closure CI.

Stop conditions: unexpected writer, wrong project ref, migration hash mismatch, non-zero synthetic residue, failed rollback proof, failed permission case, or frozen CP3/CP4 byte drift. Production deploy and real-owner invite are explicitly out of scope.
