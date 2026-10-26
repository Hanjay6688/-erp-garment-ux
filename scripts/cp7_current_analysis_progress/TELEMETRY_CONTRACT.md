# Optional A telemetry proposal for B — D17-18

The unchanged v1 status stays inside `status` in a new, opt-in envelope.
`erp_cp7_get_frozen_analysis_progress_v1(p_request)` is prepared only. It is
not installed, routed by B or adopted by the application yet. A owns this
public reader and its integration. B's current parsers remain byte exact.

The reader returns server `observed_at`, source-bound original job status,
operational creation/activity/finish times and, only with current finance
permission, finance creation/activity/finish times, retry count, recorded
official report milliseconds and an observation of its existing worker lock.
There is no scheduler, new table, write, wait, worker tick, report reread,
business formula, changed producer hash or changed timeout in this extension.
One caller/job and its existing one-to-one capture are read in one statement.

`last_activity_at` is intentionally not called last completed progress:
retries also update it. Completed counts remain the authoritative progress.
`LOCK_HELD` only observes a finance worker holding its existing advisory lock
at read time; `NO_LOCK_OBSERVED` means no such lock was observed. Neither is a
promise about future work. Operational work uses row locks; its worker state
remains `NOT_EXPOSED` pending B's contract. Queue position is not invented.

Current finance denial produces null finance telemetry; no capture id, counts,
timestamps or worker details leak. Foreign requests remain unavailable. The
current ACL is checked before and after the read. Source and result parsers
must remain in use, including UUID, scope, period, capture and microseconds.

Consumption should replace an existing status poll rather than add duplicate
reads. Elapsed active time uses server observation minus creation. Terminal
duration uses the stored finish timestamp, never the current clock. Stalled
work requires a measured policy and explicit current observations; no new
stall threshold or automatic retry is adopted by this source preparation.

Before integration: real SQL controlled-reader tests, actual full-composition
read/ACL/revocation/concurrency/clock/absence-of-write checks, complete catalog
and inverse, affected small-read timings and real browser/factory proof.
The controlled fixture suite cannot supply those full ERP acceptance claims.

PostgreSQL advisory-lock representation reference:
https://www.postgresql.org/docs/17/view-pg-locks.html . `bigint` keys use high
and low halves in classid/objid and objsubid1, scoped to the current database.
