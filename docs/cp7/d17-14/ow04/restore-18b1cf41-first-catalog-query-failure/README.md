# First admin backup-catalog query failure retained

Candidate18b1cf41; run39609428266/job119254071511 is INCOMPLETE.
The product's CREDIT and REFUND operations committed and post-use rollback
was refused. The new backup manifest reader then stopped before taking the
used dump: pg_get_expr cannot deparse a trigger WHEN that references both
OLD and NEW. The original clone returned to exact CP6 state.

The correction uses pg_get_triggerdef for each complete ordinary attachment,
including its condition and named columns; internal RI attachments keep their
complete semantic identity. It preserves active column identity/order by name
and ordinal, since a dump omits old dropped-column slots. Changed conditions,
reordered live columns and changed function bodies still refuse. The exact
old query failure is reproduced locally;22 catalog groups execute on two
PGlite instances with distinct OIDs, a two-row trigger condition and a dropped
column on the source only. This is local metadata evidence, not Native restore.

Original artifact ZIP was downloaded and client SHA256 verified. All five
unchanged JSON reports are preserved as locally generated gzip with raw/gzip
hashes. No used-restore or continued-write PASS is claimed here. The financial
Native core, literal inverse assertions and exact backup-data equality remain.
