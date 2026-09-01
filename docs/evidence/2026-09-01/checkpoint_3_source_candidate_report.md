# ERP Garment — Checkpoint 3 Source Candidate Validation

**Verdict:** SOURCE VALIDATION PASS · INDEPENDENT DELTA AUDIT PENDING  
**Production GO:** NO  
**UAT apply:** FORBIDDEN UNTIL WORK SOL MAX PASS  
**Draft PR:** #14

## Scope completed

The missing attendance-HPP candidate was reconstructed from clean `main` `bf3ce8e2821f120d8abd8788daf07f6da7c15459`. The candidate replaces the stale QC-GOOD denominator with an explicit immutable `SELESAI_DIJAHIT` event and keeps the route source-only, private, and inactive.

The candidate includes:

- effective-dated explicit normal-Mandor policy;
- Special independent from `attendance_required` and never inferred from names;
- authoritative `SELESAI_DIJAHIT` record/reversal contract;
- attendance HPP pool preview, create, validate, activate, and ACTIVE cancel lifecycle;
- exact original payroll debit journal-line lineage;
- epoch-microsecond deterministic manifest hashing;
- closed JSON contracts with missing/null/type rejection;
- set-based bounded validation without deferred row triggers;
- exact-byte rollback renderer with digest, byte-count, single terminal `COMMIT`, and ledger-marker guards;
- real two-connection concurrency harness.

## Reproducible proof

| Gate | Result | Evidence |
|---|---|---|
| CP3 candidate workflow | PASS | run `33482192065`, job `99774076749` |
| Frontend/build/security regression | PASS | run `33482195996`, job `99774088548` |
| Proof artifact | PASS | ID `9790364683`, digest `sha256:fd0aecc122275f7145dfe7d320b84bc956e01d7f375d3f5f31daa18d0888119a` |
| Source boundary | PASS | source-only, no hook, no public/service grant, no QC GOOD reference |
| Renderer adversarial tests | PASS | exact source digest/bytes and terminal transaction bound |
| Rendered migration rollback | PASS | schema/ledger residue 0 |
| Behavior/negative/idempotency/reversal fixture | PASS | fixture residue 0 |
| Timezone determinism | PASS | same canonical manifest/hash across tested timezones |
| Special and attendance exclusion | PASS | explicit policy snapshots; no name inference |
| Original debit-line credit lineage | PASS | source credit per exact debit journal line |
| Active pool cancellation | PASS | owning atomic journal reversal; no manual pre-reversal |
| Validator benchmark | PASS | 2,000 destinations, 2 validator calls, 0 deferred row triggers, 96.984 ms |
| Real concurrency | PASS | activate/activate, cancel/cancel, activate/cancel serialized with one valid terminal transition |
| ACL/reconciliation | PASS | 6 private tables, 0 non-internal triggers, no authenticated/service direct access, fixture rows 0 |

## Candidate hashes

| File | SHA-256 |
|---|---|
| `20260901023000_erp_v2_6_14_attendance_hpp_sewing_terminal_foundation.sql` | `68e5a8f81ac364be6a8ec01c5bffdfe4ec587f91d61a03dc9f44a4670cadb821` |
| `20260901023100_erp_v2_6_14b_attendance_hpp_candidate_hardening.sql` | `08b2a035af453ee73668d6d7cfa9e7a58310a85be75b9883647ee68cb413a56c` |
| `attendance_hpp_sewing_terminal_rollback.sql` | `4df2f26cba61bfdfb2dae2fc9c714eeb333d02fe1539fa56492b5475ac6713bd` |
| `attendance_hpp_validator_benchmark_rollback.sql` | `6ec663c92a6b20a7b95b149c51941f230d477cb50222cd48b317bcb7a85cd4f9` |
| `cp3_attendance_hpp_minimal_baseline.sql` | `936f923d76c9ff9b66c350c57d26a4b90131326676b86889f27569aa2b260586` |
| `cp3_render_reviewed_rollback.py` | `a425cfe1bc4ac8740680a9f6e0d0234926bb365f5c503a6acfd840a79f3bf49f` |
| `test_cp3_render_reviewed_rollback.py` | `e84ff683b59bd3d9bd0b2e38fa834886aedb373fcc68a4d05cce5f42604f2139` |
| `cp3_attendance_hpp_concurrency.py` | `a69fd46339fcc9cce9d10e1f963e70765af1e11f3324e1b2963488dd87e3c491` |

## Truth by layer

| Layer | Status |
|---|---|
| SOURCE | PASS — candidate only |
| UAT | NOT APPLIED |
| LIVE | unchanged demo/simulation |
| BACKEND-CONNECTED | NO |
| AUTH/RLS E2E | NOT EXECUTED |
| ERP-Garment legacy | read-only; not mutated |
| PRODUCTION GO | NO |

## Remaining gate

This is not a self-certified CP3 completion. Work Sol Max must independently delta-audit draft PR #14 against the original P0/P1 register and the exact hashes above. Any source change after this evidence invalidates the hashes and requires a fresh proof run.

Only after independent PASS may the owner decide whether Chat Sol Pro resumes as writer for the persistent ERP Enteng UAT phase. No migration, hook, grant, Auth user, Cloudflare deploy, or frontend connection is authorized by this report.
