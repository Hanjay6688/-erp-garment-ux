# ERP Garment — Checkpoint 1 Independent Revalidation Addendum

**Record type:** forward addendum; the historical Checkpoint 1 evidence is unchanged  
**Revalidated:** 2026-09-01 01:45 UTC  
**Algorithm:** `CP1_REVALIDATION_V1`  
**Result:** **PASS — TAKEOVER READY**  
**Production GO:** **NO**

## What this addendum resolves

This addendum closes five documentation ambiguities without rewriting the original evidence:

1. It persists the exact read-only fingerprint algorithm in `scripts/cp1_fingerprint.sql`.
2. It defines object and column scope explicitly.
3. It separates the Cloudflare production Worker version from an evidence-branch preview version.
4. It records the writer-lock scope and confirms that no database, Auth, deployment, or `main` mutation occurred.
5. It marks Checkpoint 2 only as **REPORTED PASS / AWAITING INDEPENDENT VALIDATION**.

## Writer lock

| Field | Locked value |
|---|---|
| Writer | `Codex /root` |
| Mutation scope | Documentation and evidence only |
| Base branch | `evidence/checkpoints-1-2-20260901` |
| Base commit | `c00500f2a681310ab7d64d177f7d84dea873088b` |
| Base tree | `b33e7cb5bb6217b95e8d2974581c2a158417f9c2` |
| `main` commit | `bf3ce8e2821f120d8abd8788daf07f6da7c15459` |
| `main` tree | `e4377d85b612f5183b4831751de6a735d98a8b6f` |
| Concurrent writer detected | No |
| Persistent UAT write | None |
| Canonical legacy write | None; read-only only |
| Auth/user write | None |
| Cloudflare deploy | None |
| `main` write | None |

The lock is an operational single-writer lease for this evidence revision, not a database advisory lock. Branch heads, migration ledgers, schema counts/hashes, and other non-idle client sessions were checked before the evidence write. Any later unexpected drift still requires `CONCURRENT_WRITER_DETECTED` and a fresh fingerprint.

## Reproducible algorithm and scope

The SQL is a single read-only `SELECT` composed from CTEs. For every component it serializes explicit catalog fields, sorts records with `COLLATE "C"`, joins them with LF, and applies PostgreSQL `md5`. The final fingerprint is the MD5 of the ten component hashes joined with `|`.

- Catalog schemas: `erp`, `public`.
- ERP table/RLS counts: `erp` only.
- Columns: non-dropped user columns on tables, partitioned tables, views, materialized views, and foreign tables in `erp`/`public`; system columns and every other schema are excluded.
- Functions: ordinary functions and procedures in `erp`/`public`.
- Grants: `information_schema.role_table_grants` plus `role_routine_grants` in `erp`/`public`.
- Runtime observations: Auth/app users, RLS, Storage, cron, migration ledger, and other non-idle client sessions.

Script SHA-256: `943bf1180e39a898e38aea359a14f1a3459a1e7ad8dde7f35657ced672376509`.

The historical evidence preserved hash values but not its exact serialization query. Therefore `CP1_REVALIDATION_V1` is a new reproducible baseline; its hashes must not be compared byte-for-byte with the historical hashes.

## Independent results

The exact script was executed twice against each project. Component hashes, counts, runtime invariants, and migration ledgers were stable across both runs.

| Observation | ERP Enteng UAT | ERP-Garment canonical |
|---|---:|---:|
| Project ref | `siimvrusnzxexizpyoib` | `vlxdhpkjeevubjxexnfo` |
| Policy during test | Read-only revalidation | Canonical read-only |
| ERP tables | 142 | 136 |
| Scoped relations | 194 | 186 |
| Scoped columns | 2,233 | 2,102 |
| Views | 48 | 46 |
| Functions/procedures | 436 | 398 |
| Triggers | 383 | 363 |
| Indexes | 419 | 399 |
| Constraints | 944 | 864 |
| Policies | 190 | 184 |
| Table + routine grants | 3,472 | 3,300 |
| RLS enabled/disabled | 142 / 0 | 136 / 0 |
| Auth users / app users | 0 / 0 | 0 / 0 |
| Storage buckets / objects | 1 / 1 | 1 / 1 |
| Cron active / total | 1 / 1 | 1 / 1 |
| Other non-idle client sessions | 0 | 0 |
| Platform migrations | 55 | 272 |
| `schema_fingerprint_v1` | `caf4560c036608927ffa4bec093dcbb1` | `178db1a1feef13fa055bd0493c33a9ac` |

Latest ledgers remain:

- UAT: `20260831032949_erp_v2_6_13b_auth_profile_facade_tracking`.
- Canonical: `20260829204756_erp_v2_6_11_operational_reservations_and_completion_scope`.

The machine-readable addendum records all ten component hashes and both repeat-run timestamps.

## Column-count reconciliation

The original report recorded 2,870 UAT columns and 2,701 canonical columns. Its query and scope were not preserved. V1 deliberately counts only non-dropped columns on user relations in `erp` and `public`, producing 2,233 and 2,102.

This is a **scope difference, not proven schema drift**. The old and new column totals cannot be treated as like-for-like. The table, view, function, trigger, index, constraint, policy, grant, RLS, runtime, and migration-ledger counts independently matched the recorded state.

## Cloudflare version clarification

| Target | Version | Meaning |
|---|---|---|
| Production Worker | `593b5d6f-748a-498b-bf58-a6c7d2263294` | Live demo Worker for `main` commit `bf3ce8e…`; business backend remains disabled |
| Existing evidence-branch preview | `ee4a830d-552b-4157-9f33-b260b5c2c465` | Preview build only; not production |

The production root and its version-specific preview matched byte-for-byte at verification time:

- HTML SHA-256: `f14a36d20b7e751ad81eea9762b35f0d9200400bcb8869dd20e67081257fdad0`
- JavaScript SHA-256: `323798fee530edc5cc94d2cf9168386539c9bf76985357c3f0bd12100d44589b`
- CSS SHA-256: `c279db52b256e9d6ac839881c5099d12111f566d47e2a283cb5752593dda2952`

The evidence preview `ee4a830d…` must never be cited as the live production version.

## Verdict and next gate

Checkpoint 1 remains **PASS**. No unknown source, catalog, migration-ledger, Auth-user, Storage, cron, or live-version drift was found within the now-explicit scope. This revalidation made no persistent database change and did not connect the frontend to the backend.

Checkpoint 2 has an existing evidence claim of PASS, but it has not yet been independently revalidated in this workstream. Its correct handoff status is **REPORTED PASS / AWAITING INDEPENDENT VALIDATION**. That independent restore-evidence validation is the next action before any persistent UAT mutation.
