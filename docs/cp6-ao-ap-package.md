# CP6 AO/AP — permanent package and pre-use restoration

Status: writer package qualification PASS. CP6_HOLD; production_go=false;
hosted_migration_installed=false; independent_acceptance=false.

This package preserves the business implementation tested at
`eebfbfb045a268459f1cef20e306f86d78e3e720` and documented at
`4dcc950fb8cd2a102cc11c8f6545af2865cafa6c`. The original 54 proposal source
pins must still match. The earlier 184 AP, 12 AO and 142 frontend results belong
to those exact sources; they are not a claim that every historical suite has
been executed again against permanent migrations.

## Installation boundary

| Family | Predecessor | Replaced functions | New functions | New business tables |
| --- | --- | ---: | ---: | ---: |
| AO, invoice economic dates and accessory retail | AN | 10 | 1 | 1 |
| AP, connected import and material lifecycle | AO | 30 | 71 | 20 |

The AO predecessor count corrects the prior accessory checkpoint's statement
of 11 predecessor functions: AO defines 11 functions, of which 10 replace
predecessors and one is new. The AP function count is 101, including 30
replacements and 71 new functions. Each family also has one private rollback
capsule. AP introduces 28 triggers. Seven AP functions are public facades;
the other new functions remain private.

Both filenames were generated using Supabase CLI 2.116.0 `migration new`.
The exact CLI provenance, captured catalog and source hashes are recorded in
`docs/evidence/cp6-ao-ap-*`. The builder reproduces migration and rollback bytes.

The SQL accepts only closed, drained maintenance. The installer validates the
source and predecessor, opens its one target connection, closes database
admission through the separate maintenance authority, drains old sessions,
rechecks the full catalog, and applies DDL plus its platform migration row in
one transaction. The platform row contains the complete exact migration text.
Admission reopens only after the committed successor is verified. A failure
after closure leaves admission closed for explicit investigation.

The current controller deliberately admits only the existing disposable
loopback endpoints. This is a reviewable installation package and CI proof;
it does not provide or authorize a hosted rollout path.

## What is pinned and preserved

The catalog includes functions and owners/grants, tables, visible column order,
types and defaults, constraints, indexes, triggers, views, policies, row-level
security, sequence definitions, schemas, default grants and enum labels in
the ERP and public schemas. Column order is logical visible order: PostgreSQL
retains unused internal attribute slots after a column is dropped, and a
successful reinstall must not depend on those invisible slot numbers.

The captured AN/AO/AP catalogs contain 6,638 / 6,646 / 7,148 entries respectively,
excluding the new capsules. Capsule security, columns, constraints, indexes,
durability and original function definitions are checked separately. SQL pins
a canonical SHA256 of the length-delimited, sorted catalog entries; the runtime
checker also compares every individual entry with the captured map. Historical
capsule definitions remain source-bound.

Installation records all ERP table contents and both migration ledgers. It
proves that existing rows are preserved under the projection that removes only
the newly added nullable column, and that new business tables start empty.
The migration does not create fictional transactions or balances to satisfy
its checks.

## Restoration boundary

Restoration is available only before business use. Any difference in the
recorded post-install ERP data, or in prior migration history, rejects the
rollback. An append-only transaction and its linked business reversal still
leave history, so they do not qualify as an unused installation.

AP must be restored before AO. Restoration checks exact source bytes, the
installed catalog, original functions and ACLs, capsule security, successor
absence and recorded data. It removes new triggers, restores original
functions, drops new functions without CASCADE, restores prior constraints
and nullability, removes new columns/tables/capsules, and removes only its own
migration rows. The predecessor catalog and all recorded rows must then match
before commit.

The existing `cp6_preuse_rollback_maintenance.py` remains unchanged. The new
adapter registers the two exact families. The new rollback SQL repeats the
full catalog and data proof after the existing controller drains sessions.

## Qualification and remaining work

Tested source: `4bff4a65a7b93d7888fa77dbcb31bb1c937bbc57`, tree
`a09219329d2f09cf9f611f7c6f8b908b8b283a82`.
[Package run 35741707738](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35741707738),
job 106792886964, completed successfully. Its 48-entry artifact 10700715846 is
2,683,724 bytes, SHA256
`9417d13728cc61db292746b70cc20ed23b0ad6905ce9a67cd1d85c3e00efd6e2`.
CRC, SHA256, source head/tree, reports and every case result were verified.

- 105 installed public-RPC cases passed, each with its boundary restored.
- 38 atomic refusals passed, covering open admission, install replay, function
  owner/grant/configuration drift, table RLS/column/constraint/trigger drift,
  schema grants, capsule source/boundary/column/durability/grant drift, platform
  source/successor drift, changed existing business data and use of a new table.
- After installation, two complete AP→AO→AN→AO→AP cycles passed. Final AP→AO→AN restoration
  matched the full seeded AN catalog, all ERP table contents and migration ledger.
  The baseline had 114 nonempty ERP tables.
- Six real report schedules passed: natural drain, forced termination and
  refused drain timeout for each family. New connections were rejected while
  admission was closed. Expected drain-timeout controller failures began no DDL
  and stayed closed; only the disposable fixture was explicitly recovered after
  proving its original catalog and data unchanged.
- Advisors captured 86 baseline findings, then 88 at AO and 109 at AP. The 2
  and 21 additions were reviewed private-table/capsule RLS-without-policy INFO
  findings. There were zero unreviewed additions; baseline findings were retained,
  not declared resolved.
- [CodeQL 35741707781](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35741707781)
  passed all four language jobs. [Full-Schema 35741707766](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35741707766)
  passed its audit-scope job but failed the unchanged global source gate with
  `AC_ONLY_EXACT_SUCCESSOR_REPAIR_ALLOWED` before database execution.

The first package run, 35740795248 on `f9867f01d489b3f70368f491120d8faf8e999540`,
stopped during fixture preparation with `PACKAGE_CATALOG_DRIFT:SCHEMA:erp`.
A fixture GRANT/REVOKE materialized the original NULL schema ACL. Foundation
loading now stays in its existing administrative session without changing that
ACL. The exact catalog assertion remains intact. Artifact 10699830246 preserves
the failed run, SHA256
`099006232fff710282979f819e5b66cbac43f855ba091630c2e2ba2b411021f5`.

Catalog input comes from successful capture 35739333806 at
`c26bf139da026e0669e047d4535b1dbf3fb45211`; its artifact 10698766947 has SHA256
`645ec616337a31335199bb521b6e378072d4e84b241d77cca3b2ed03e9947032`.
Earlier capture 35738021269 passed before the logical column-order refinement.
The initial capture failure 35737331580 exposed the ambiguous concatenation of
PostgreSQL's internal `char` type in the default-ACL inventory; an explicit text
cast fixed it. Those capture artifacts are preserved as well.

`cp6_ao_ap_qualify.py` uses a physical clone of the exact AN disposable runtime
with a committed nonempty business fixture. It exercises install, two complete
restore/reinstall cycles, atomic drift and post-use refusals, unchanged public
RPC case modules on the committed AP package, and a real financial report
blocked inside a journal read under natural-drain, termination and drain-timeout
schedules. Security advisor findings are compared at AN, AO and AP, with only
specifically identified private RLS-without-policy information reviewed as
intentional. Baseline findings are retained.

The global historical Full-Schema/Final-Boundary harness still has its prior
AC-only successor scope gate. That gate is unchanged. Focused writer package
results cannot substitute for global independent acceptance.

HTTP with real Auth JWTs, browser flows, business transaction concurrency,
legacy opening overlap protection and the independent global audit remain
separate CP6 work. CP7 and production GO still require owner acceptance.

## Continuity after the checkpoint

The code and this evidence document are committed on the writer branch. The
separate nine-file save of the new Indonesian checkpoint, the two master-file
replacements, five evidence ZIPs and their manifest timed out without a result.
Read-only reconciliation still observed `ERP_V3_2.md` and
`ERP_V3_2_Perubahan.md` at version 15 and found no new checkpoint/final ZIP.
Therefore version 16 is prepared locally but is **not confirmed saved**. The
pending files retain their submitted bytes; no duplicate write was issued.
The Library skill's prepared-upload rule prohibits retrying or changing the
write route while a timed-out finalization may still be processing. Resolve
that outcome before resubmitting any master replacement or archive creation.
