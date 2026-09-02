# CP4.5 closure runbook

Order is mandatory; do not parallelize database writers.

1. Freeze candidate bytes and run frontend, source, access, CSS, backend ownership, and build gates.
2. Push the single CP4.5 branch and require exact-head Build UX plus full-schema validation success.
3. Re-gate ERP Enteng UAT and legacy ERP Garment read-only; stop if a writer, lock, drift, or target mismatch appears.
4. Apply the exact CI-reviewed migration once to ERP Enteng UAT only, record platform ledger once, and verify replay rejection.
5. Run SQL acceptance and frozen CP4/affected CP3 regression on UAT.
6. Run manual hosted-UAT Auth/JWT permission E2E with temporary OWNER, custom-role, view-only, inactive, and unmapped identities. Classify this as `MANUAL_HOSTED_UAT_VERIFIED`, never CI.
7. Delete temporary sessions, app mappings, identities, users, roles, patterns, and audit rows; prove exact zero synthetic residue.
8. Re-gate UAT and legacy read-only, attach non-secret proof, freeze closure bytes, and run exact-head closure CI.

Stop conditions: unexpected writer, wrong project ref, migration hash mismatch, non-zero synthetic residue, failed rollback proof, failed permission case, or frozen CP3/CP4 byte drift. Production deploy and real-owner invite are explicitly out of scope.
