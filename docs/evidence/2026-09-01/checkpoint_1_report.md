# ERP Garment — Checkpoint 1: Writer Lock & Fingerprint

**Captured:** 2026-09-01 WIB  
**Writer:** Chat Sol Pro  
**Evidence branch:** `evidence/checkpoints-1-2-20260901`  
**Production source baseline:** `main` at `bf3ce8e2821f120d8abd8788daf07f6da7c15459`

## Gate result

| Gate | Result |
|---|---|
| Single writer lock | PASS |
| Unknown/concurrent writer | NONE DETECTED |
| Source fingerprint | PASS |
| ERP Enteng UAT fingerprint | PASS WITH KNOWN DRIFT |
| ERP-Garment legacy read-only | PASS |
| Live commit/version match | PASS AS DEMO |
| Business backend connected | NO — intentionally disabled |
| Auth E2E | NOT YET EXECUTED |
| Checkpoint 2 allowed | YES |
| Production GO | NO |

## Source and live

- Repository: `Hanjay6688/-erp-garment-ux`
- Official branch: `main`
- Commit: `bf3ce8e2821f120d8abd8788daf07f6da7c15459`
- Tree: `e4377d85b612f5183b4831751de6a735d98a8b6f`
- Package version: `0.1.2`
- Cloudflare Worker: `erp-garment-ux`
- Cloudflare Version ID: `593b5d6f-748a-498b-bf58-a6c7d2263294`
- GitHub CI: PASS
- Cloudflare build/deploy: PASS
- Runtime: `DEMO_SIMULATION`
- Business data: `SIMULATION`
- Business RPC write: disabled

`main` is intentionally not changed by this evidence package. The evidence lives on a separate branch so the source/live fingerprint stays stable.

## ERP Enteng UAT

- Project ref: `siimvrusnzxexizpyoib`
- Status: `ACTIVE_HEALTHY`
- Database size: 102 MB
- Tables: 142
- Views including public facades: 48
- Functions including public RPCs: 436
- Triggers: 383
- Indexes: 419
- Constraints: 944
- Policies: 190
- Columns: 2,870
- RLS enabled: 142/142 tables
- Auth users: 0
- `erp.app_users`: 0
- Pending HPP recalc: 0
- Other non-idle sessions: 0
- Active Edge Functions: 17
- Schema fingerprint: `a0c59b96b3879edd28f3d8c57d0894a3`
- Latest platform migration: `20260831032949_erp_v2_6_13b_auth_profile_facade_tracking`
- Application marker: `v2.6.11a`

## ERP-Garment legacy baseline

- Project ref: `vlxdhpkjeevubjxexnfo`
- Status: `ACTIVE_HEALTHY`
- Database size: 34 MB
- Tables: 136
- Views: 46
- Functions: 398
- Triggers: 363
- Indexes: 399
- Constraints: 864
- Policies: 184
- Columns: 2,701
- RLS enabled: 136/136 tables
- Auth users: 0
- `erp.app_users`: 0
- Pending HPP recalc: 0
- Other non-idle sessions: 0
- Active Edge Functions: 12
- Schema fingerprint: `f6ccf0a0155664544273fc41ff7d69af`
- Latest platform migration: `20260829204756_erp_v2_6_11_operational_reservations_and_completion_scope`

**Mutation policy:** read-only legacy baseline. It must not be used as the restore target.

## Known drift and findings

1. Release notes still state ERP Enteng and ERP-Garment are runtime-equivalent. That statement is stale and must be corrected through forward release metadata, not by editing migration history.
2. ERP Enteng has later Attendance, Stock Explainability, Manual Reminder, and Auth profile-facade changes.
3. Several old export/install/self-test Edge Functions remain ACTIVE. Inspected examples are retired stubs that return HTTP 410, but all functions must be backed up and reviewed before controlled cleanup.
4. ERP Enteng Security Advisor reports 12 warnings for intentionally exposed authenticated `SECURITY DEFINER` facades. These are not accepted as safe until role guards, fixed `search_path`, anon denial, negative API tests, and Auth E2E are proven.
5. Auth user mappings are verified empty, but dashboard-level Auth settings were not available through the connector and remain to be reverified before OWNER creation.
6. `main` is not protected. This is a pre-production hardening item.
7. Index/catalog counts are large relative to current data. No index is removed based only on zero-scan statistics while the database is nearly empty.

## Takeover contract

- Only one writer may mutate GitHub, ERP Enteng, Cloudflare, Auth, or Storage at a time.
- Work Sol Ultra/Max remains reviewer-only until this document is superseded by a newer `TAKEOVER_READY` package.
- Before any persistent database patch, Checkpoint 2 encrypted backup and end-to-end restore must PASS.
- Any unexpected source/schema/migration/Cloudflare drift is `CONCURRENT_WRITER_DETECTED`; stop all writes and fingerprint again.

The machine-readable record is `checkpoint_1_fingerprint.json` in this folder.
