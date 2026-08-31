# ERP Garment — Checkpoint 2: Encrypted Backup & Restore Gate

**Status:** BACKUP PASS · RESTORE DRILL PENDING  
**Captured:** 2026-09-01 WIB  
**Source baseline:** `main` at `bf3ce8e2821f120d8abd8788daf07f6da7c15459`  
**UAT source:** ERP Enteng `siimvrusnzxexizpyoib`  
**Forbidden restore target:** ERP-Garment legacy `vlxdhpkjeevubjxexnfo`

## Backup result

A fresh logical recovery package was exported from ERP Enteng, encrypted before artifact storage, decrypted again, byte-compared against the original archive, and independently decrypted/verified a second time outside the workflow.

| Check | Result |
|---|---|
| Fresh ERP Enteng export | PASS |
| Required bundle files present | PASS |
| Internal SHA-256 validation | PASS — 148 files |
| AES-256-CBC encryption | PASS |
| PBKDF2-HMAC-SHA256 | 600,000 iterations |
| Workflow decrypt/byte compare | PASS |
| Independent local decrypt | PASS |
| Raw archive SHA-256 match | PASS |
| ZIP integrity | PASS |
| Plaintext uploaded as artifact | NO |
| Restore into disposable DB | PENDING |

## Recovery files

- Encrypted backup: `ERP_ENTENG_CP2_BACKUP_20260831T193529Z.zip.enc`
- Encrypted SHA-256: `f4a7e060b3d9d60b9e04ed6bf2afd3f15e6b8af74f030fb4c11914d070ed75a1`
- Recovery key file: `ERP_ENTENG_CP2_RECOVERY_KEY_20260831T193529Z.txt`
- Recovery key file SHA-256: `6ed0dd8cd8296cf6f6080ac3a0db3b12a70351789bff60b05730cb4c7f9526e3`
- Raw archive SHA-256 after decrypt: `e176cac94d78915cb5fd73a065f58150184ee0b37801e6eb70fbc8fcfa29ef53`

The encrypted backup and recovery key must be stored in separate Google Drive locations. GitHub artifacts are temporary transport only.

## Captured scope

- 142 ERP table payloads
- 104 current ERP rows
- 55 Supabase platform migrations
- 41 application migration markers
- complete ERP/public facade catalog for tables, columns, types, sequences, constraints, indexes, function definitions, view definitions/dependencies, triggers, policies, table/routine grants, cron, release metadata, and migration ledgers
- generated `ERP_ENTENG_BEFORE_REBUILD.sql`
- generated `ERP_ENTENG_DATA_RESTORE.sql`
- one actual Storage object, 1,084,146 bytes, plus bucket/object metadata and checksum
- empty Auth-state manifest: 0 `auth.users`, 0 `auth.identities`, 0 `erp.app_users`; no password hash was copied

## Evidence

- Successful workflow run: `33430989888`
- Successful job attempt: `99617105226`
- Encrypted backup artifact ID: `9772713622`
- Recovery-key artifact ID: `9772714077`
- Machine-readable manifest: `checkpoint_2_backup_manifest.json`

## Restore gate and cost

A disposable Supabase branch is the next restore target. Supabase quoted:

> **USD 0.01344 per hour** while the branch exists.

The branch has not been created because the platform requires the owner to explicitly confirm the quoted recurring hourly cost. After confirmation, the restore drill must:

1. Create a disposable branch from ERP Enteng migrations.
2. Verify migration replay and schema fingerprint.
3. Decrypt the backup only in the controlled restore runner.
4. Restore ERP data and the Storage object.
5. Compare row counts, checksums, migration ledgers, RLS, grants, functions, triggers, cron, and release metadata.
6. Run integrity/smoke tests and verify residue.
7. Retire temporary recovery endpoints and record the final `TAKEOVER_READY` state.

Checkpoint 2 is not complete until those restore and verification steps pass.
