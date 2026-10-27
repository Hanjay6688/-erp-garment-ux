# Prepared report and book consistency diagnostic — A

The accepted0bccf142 Native13 plus actual cron run passed. Its stored cron
report_snapshot was NULL. This proves absence of that snapshot on this path;
it does not yet prove an escaped inconsistent result. The unchanged child-XID
counterexample is running separately at2bfb3cc7. Preserve that first outcome.

This closed proposal computes the existing canonical book signature alongside
the official report in one STABLE query snapshot, then requires the collected
chunks to equal that signature before READY. It uses the unchanged book_chunk
row serialization, family ordering and current10000-row chunk policy. Counts
come from that same scan. A new private nullable column stores the expected
signature; no user-supplied token, persistent result reuse, added writer lock,
long-running transaction, cron change or B source modification is involved.

Existing row-count and snapshot checks stay. The added comparison also works
when heartbeat or report-job writes have already assigned a transaction ID.
The public capture metadata reports ROW_COUNTS_AND_REPORT_BOOK_SIGNATURE;
the original result keys, book digest format and source fingerprint stay.
Installation refuses nonempty capture/chunk tables and requires the exact live
parent bodies, roles and chunk size before any DDL. Only localhost cp6_rollback
is permitted. This is a temporary diagnostic, not an upgrade for existing data.

Evidence still required: old first visibility result, independent signature
equality on empty/small/multichunk sources, no ERP writes, same report/24metrics,
late child commit, committed same-count edits, actual scheduler and Business
Report paths, successful fresh-UUID recovery, Native13, permissions, full
catalog/data/sequence/role restoration, and measured factory overhead. The extra
book scan has a real cost; no speedup, latency budget or product acceptance is
claimed. The single-check experiment remains independent until it is measured.

PostgreSQL17 describes STABLE commands as sharing the calling query snapshot:
https://www.postgresql.org/docs/17/xfunc-volatility.html
Its snapshot visibility primitive is not reliable for subtransaction IDs:
https://www.postgresql.org/docs/17/functions-info.html#FUNCTIONS-PG-SNAPSHOT
These explain the design; they do not replace actual ERP qualification.
