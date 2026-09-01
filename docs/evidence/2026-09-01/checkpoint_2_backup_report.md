# ERP Garment — Checkpoint 2: Encrypted Backup & Restore Drill

**Status:** PASS · CHECKPOINT COMPLETE  
**Completed:** 2026-09-01 WIB  
**Source baseline:** `main` at `bf3ce8e2821f120d8abd8788daf07f6da7c15459`  
**UAT source:** ERP Enteng `siimvrusnzxexizpyoib`  
**Restore mode:** free local Supabase stack in ephemeral GitHub Actions  
**Forbidden restore target:** ERP-Garment legacy `vlxdhpkjeevubjxexnfo`

## Final verdict

The encrypted recovery package was restored end-to-end on a local Supabase/Postgres stack matching hosted Postgres `17.6.1.165`. Database schema, ERP data, migration ledgers, cron, Auth empty state, and the actual Storage object all passed verification. The local stack and decrypted material were destroyed after the test.

No paid Supabase branch was created. Additional Supabase cost for this restore drill was **USD 0**.

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
| Local Supabase/Postgres start | PASS |
| Database schema restore | PASS |
| ERP data restore | PASS — 104 rows |
| Platform migration ledger | PASS — 55 rows |
| Application migration ledger | PASS — 41 rows |
| Cron restore | PASS — 1 active definition |
| Object/count/data mismatch | NONE |
| Integrity findings/errors | NONE |
| Auth empty state | PASS — 0 users, 0 app users |
| Storage restore and download round-trip | PASS — 1,084,146 bytes |
| Local cleanup | PASS |
| Plaintext uploaded as artifact | NO |

## Exact restore comparison

Expected and actual values matched:

- tables: 142
- views: 48
- functions: 436
- triggers: 383
- indexes: 419
- constraints: 944
- policies: 190
- platform migrations: 55
- application migrations: 41
- ERP rows: 104
- cron jobs: 1

The verifier reported:

```text
object_mismatches = {}
count_mismatches  = {}
data_mismatches   = []
integrity_findings = []
integrity_errors   = []
platform_ledger_match = true
application_ledger_match = true
```

## Storage proof

The real Storage object was recreated through the local Storage API and downloaded again:

- bucket: `chatgpt-temp-erp-export`
- object: `ERP_GARMENT_V2_6_0_COMPACT_ONE_SHOT.sql`
- bytes: `1,084,146`
- SHA-256: `756a962d8dda43c71487afa7a3cdbbd80ef787487b1eafc771c94def53187aee`
- round-trip download: PASS

## Recovery files

- encrypted backup: `ERP_ENTENG_CP2_BACKUP_20260831T193529Z.zip.enc`
- encrypted SHA-256: `f4a7e060b3d9d60b9e04ed6bf2afd3f15e6b8af74f030fb4c11914d070ed75a1`
- recovery key: `ERP_ENTENG_CP2_RECOVERY_KEY_20260831T193529Z.txt`
- recovery-key SHA-256: `6ed0dd8cd8296cf6f6080ac3a0db3b12a70351789bff60b05730cb4c7f9526e3`
- decrypted raw archive SHA-256: `e176cac94d78915cb5fd73a065f58150184ee0b37801e6eb70fbc8fcfa29ef53`

The encrypted backup and recovery key are stored in separate private Google Drive folders. Restore proof is stored in a third private folder.

## Durable evidence

### GitHub

- backup/export workflow run: `33430989888`
- successful export job: `99617105226`
- free restore workflow run: `33457299164`
- successful restore job: `99699891972`
- restore harness commit: `41bda0f748ebef57155013ea1e2f3dc86602a85a`
- restore proof artifact: `9781927051`
- restore proof artifact digest: `sha256:3a7ead9522dc1d48bef4f04b7e97d0fb041d4953379534080f1604dc411249c5`
- machine-readable manifest: `checkpoint_2_backup_manifest.json`
- machine-readable restore result: `checkpoint_2_restore_proof.json`

### Google Drive

```text
My Drive
├── ERP Recovery
│   ├── Encrypted Backups
│   │   └── ERP_ENTENG_CP2_ENCRYPTED_BACKUP_PACKAGE_20260831T193529Z.zip
│   └── Restore Proofs
│       └── ERP_ENTENG_CP2_FREE_LOCAL_RESTORE_PROOF_20260901.zip
└── ERP Recovery Keys
    └── ERP_ENTENG_CP2_RECOVERY_KEY_PACKAGE_20260831T193529Z.zip
```

All three Drive files were verified private/not shared.

## Boundary of this proof

This restore drill proves that the captured database catalog, ERP data, migration ledgers, cron definition, and actual Storage object can be recovered on the matching local Supabase/Postgres stack.

It does not claim that hosted-only settings are restored automatically. In particular, dashboard-level Auth signup/email/provider settings, hosted networking, and provider secrets remain separate configuration gates. Auth had zero users and zero identities at capture time, so no password-hash migration was required or tested.

## Gate transition

```text
CHECKPOINT_1 = PASS
CHECKPOINT_2 = PASS
TAKEOVER_READY = YES
CHECKPOINT_3_ALLOWED = YES
PRODUCTION_GO = NO
```

The next framework step is Checkpoint 3: independent Ultra audit and closure of the HPP/attendance route blockers. No persistent HPP mutation should begin without rechecking the current source/UAT fingerprint against this completed recovery baseline.
