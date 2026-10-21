# First fresh-restore platform catalog drift retained

Candidate ce685200426dbdbd7c0b2e6b8e09456773b9ef5a, run39615248025,
job119274420453 committed actual CREDIT and REFUND, refused unsafe pre-use
rollback, and dumped/restored the used database. All641 non-system table hashes
were exact. Rebinding still refused: five realtime partition PK flags, default
privileges in excluded cron, and graphql/graphql_public schema authority differed.
The original raw OID guard refused as required. No continued-write PASS is claimed.
CP6 preinstallation data/catalog/roles were restored exactly at cleanup.

Six original JSON files, including the complete trusted source manifest, are
preserved as unchanged bytes in gzip. The downloaded ZIP digest was verified;
RECEIPT.json retains every raw/compressed hash. No original report is rewritten.

The correction captures the exact parent constraint, backing index and table.
Only an attached PRIMARY KEY's connoinherit representation is canonicalized,
after both table and index ancestry prove its exact parent; every other flag,
definition and attachment remains exact. A direct CREATE TABLE PARTITION OF
and pg_dump-style separate PK plus ATTACH INDEX reproduce false/true locally.
cron default privileges now follow the already-declared cron schema exclusion.
The qualification caller explicitly restores the two extension-created schema
owners/grants from its source backup profile, including grantor/grant option,
before the product API compares metadata. Schema ACLs are never normalized.
The product API still regenerates only its source-validated local OID guard.

Ten local platform controls include changed/detached table/index and PK refusals,
plus the exact restore function AST's generated SQL replay against PGlite. Exact
source graphql authority is restored and an extra rogue grant disappears.
PGlite18 NOT NULL constraint records are omitted only from that local PK
comparison because Native17 has no such records; production capture omits none.
The aligned ERP schema still executes all22 queries over2411 triggers without
identity collisions. These are local metadata controls, not Native business or
backup acceptance. One new actual used-restore execution remains required.
