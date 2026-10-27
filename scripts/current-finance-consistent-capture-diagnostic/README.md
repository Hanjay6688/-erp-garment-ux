# Prepared report and book consistency diagnostic — A

The accepted0bccf142 Native13 plus actual cron run passed. Its stored cron
report_snapshot was NULL. This proves absence of that snapshot on this path;
it does not yet prove an escaped inconsistent result. The unchanged child-XID
counterexample is running separately at05b62971 after two preserved HTTP503 failures before DB.
Preserve its first actual outcome.

This closed proposal computes the existing canonical book signature alongside
the official report in one STABLE query snapshot, then requires the collected
chunks to equal that signature before READY. It uses the unchanged book_chunk
row serialization, family ordering and current10000-row chunk policy. Counts
come from that same scan. A new private nullable column stores the expected
signature. The internal NOLOGIN finance reader receives schema USAGE so its
new definer helper can call the existing book_chunk; helper EXECUTE remains
revoked from public, anon, authenticated, service_role and cp7_capture.
No user-supplied token, persistent result reuse, added writer lock,
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

Prepared operations in cases.py retain the first child-XID oracle,13original
finance cases plus7original capture/Business Report cases, and the actual minute
cron case unchanged. The independent reference reads all four source tables
directly; chunk size1 exercises grouping without changing production10000.
An additional paired diagnostic measures SMALL, PRICE_PERCENT and1200x3 with
the original8s/30s diagnostic ceilings, requires full report equality except
captured_at, zero data writes and exactly one new book scan. It assumes no speedup.
The outer runner is prepared with a complete installed-baseline database dump
restored between all five operations, then the retained preinstallation restore.
The original parent's inverse is unchanged: candidate-schema cases must refuse
at its exact-catalog guard before DDL; the unchanged-parent overhead fixture
must refuse at its used-data guard. The rollback-only Native20 group is never
claimed as a committed-data test. No selected schema projection or cleanup is
allowed. The derived outer probe is bound to the unchanged first followup probe.

Admission requires the exact first diagnostic Original and full package bytes,
including its failed writer_runtime and all successful restoration proofs.
No actual counterexample has been admitted yet. The gate and workflow remain
closed until those first bytes prove the specific mixed-book escape. Six local
evidence checks and complete imports with connections refused are preparation
only; SQL has not yet been executed. Do not run a standalone operation.
