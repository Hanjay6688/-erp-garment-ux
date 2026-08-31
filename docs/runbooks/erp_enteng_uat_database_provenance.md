# ERP Enteng UAT database provenance

- Status: **RECORDED / NO REPLAY**
- Target: **ERP Enteng UAT** (`siimvrusnzxexizpyoib`)
- Forbidden target: **ERP-Garment canonical** (`vlxdhpkjeevubjxexnfo`)

This runbook records database changes that were already installed and verified
on ERP Enteng UAT. The SQL under `ops/supabase/uat/applied` is immutable
evidence, not a deployment queue. This patch does not execute SQL, create an
Auth user, send an invitation, expose the `erp` schema, or change either
database.

The older v2.6.11a pre-connect runbook remains the historical record of that
manual closure. Its platform-history count of 50 was correct at its recorded
checkpoint, but it is not the current UAT ledger count. Use the exact rows
below for the later Reminder ACL and Auth-facade provenance.

## Recorded platform ledger

The evidence query selected one statement for each row from
`supabase_migrations.schema_migrations`. No `applied_at` value was captured;
do not infer one from the version, filesystem timestamp, or conversation time.

| Version | Name | Statement bytes | Statement MD5 | Meaning |
|---|---|---:|---|---|
| `20260830190955` | `erp_v2_6_13_manual_reminders_v1` | 26,376 | `77c9b08bc303809257a0c8bc46dbbc83` | Reminder v1 baseline; identical to the separately reviewed local baseline source. |
| `20260831031520` | `manual_reminders_v1_acl_hardening` | 16,026 | `5e100cdddea2600d04e48b57f101f6eb` | Primary Reminder ACL hardening record. |
| `20260831032911` | `erp_v2_6_13a_manual_reminders_acl_hardening` | 16,008 | `25b92a27481cea76d3c7edc19a02ee63` | Duplicate history record of the same Reminder ACL source after outer transaction-wrapper normalization. |
| `20260831032949` | `erp_v2_6_13b_auth_profile_facade_tracking` | 15,812 | `cf96eb40ea281d44388283043fc652e6` | Auth self-profile facade tracking, stored without the outer transaction wrapper. |

The `20260831032911` row is not a second logical Reminder release. It traces to
the same 16,026-byte source as `20260831031520`, with only the outer `begin` /
`commit` wrapper removed. Keep both remote history rows immutable. Do not add a
third migration, replay either row, delete a row, or use `migration repair` to
hide the duplication.

Only the authoritative primary Reminder statement and the exact stored Auth
statement have applied-source files in this patch. A separate file for
`20260831032911` is intentionally omitted because it would make a duplicate
ledger row look like another deployable change.

## Immutable applied artifacts

| Artifact | Bytes | Ledger MD5 | SHA-256 |
|---|---:|---|---|
| `ops/supabase/uat/applied/20260831031520_manual_reminders_v1_acl_hardening.sql` | 16,026 | `5e100cdddea2600d04e48b57f101f6eb` | `ef232bc2556bbf5495dd48ce78ac534ea943719f57f9ab9a7f27bbf67b64f6a8` |
| `ops/supabase/uat/applied/20260831032949_erp_v2_6_13b_auth_profile_facade_tracking.sql` | 15,812 | `cf96eb40ea281d44388283043fc652e6` | `a590eb50f32c6e3c86b46ab6df554a93714b7227a56b7a7d7539e3628e996e60` |

The Reminder artifact is the exact full ledger statement, including its outer
transaction. The Auth artifact is the exact ledger statement after the already
performed wrapper normalization and intentionally has no final newline. Do not
run a formatter over either file.

For review, wrapper normalization is byte-exact: remove the opening byte
sequence `begin;\n\n`, then remove the terminal byte sequence
`\n\ncommit;\n`. The normalized statement therefore has no final newline; every
byte between those two wrapper sequences remains unchanged. The resulting
normalized Reminder statement is 16,008 bytes with MD5
`25b92a27481cea76d3c7edc19a02ee63`; the normalized Auth statement is the
15,812-byte artifact recorded above.

## Rollback acceptance fixtures

| Fixture | SHA-256 |
|---|---|
| `ops/supabase/uat/acceptance/20260831031520_manual_reminders_v1_acl_hardening_rollback.sql` | `bb3da0d415a3158c248fd641643bdd9bbe903473590dfed02d27feb27e5c6343` |
| `ops/supabase/uat/acceptance/20260831032949_erp_v2_6_13b_auth_profile_facade_tracking_rollback.sql` | `3029e004507f2bcf87a5f4d62da976be76fa2850a7817b57d9a2cc8246f17cd0` |

Both fixtures pin the exact UAT ledger statement count, byte length, and MD5
before creating synthetic test rows. Their test transactions end with
`ROLLBACK`, followed by residue checks. They are stored for a separately
authorized UAT acceptance run; preparing this provenance patch does not run
them.

Before any future acceptance execution:

1. Independently verify the external project ref is exactly
   `siimvrusnzxexizpyoib`; PostgreSQL lineage checks cannot prove a Supabase
   project ref.
2. Require an explicit UAT-only authorization and execute as `postgres` in one
   session. Never target `vlxdhpkjeevubjxexnfo`.
3. Send the fixture bytes without prepending, appending, or editing SQL.
4. Require the functional result to report `PASS` and the post-rollback residue
   count to be zero.
5. Stop on an error or ambiguous transport result. Do not retry until the first
   request has a terminal state and database quiescence is proven.

## Repository boundary

These files stay under `ops/supabase/uat`; they must not be copied into
`supabase/migrations` or deployed with `supabase db push`. The repository does
not have a reconciled portable baseline, and local timestamp IDs differ from
the UAT and canonical ledgers. This provenance patch also deliberately excludes
HPP SQL, user or invitation provisioning, secrets, and database mutations.
