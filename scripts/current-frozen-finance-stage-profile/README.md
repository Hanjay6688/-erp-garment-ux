# D17-18: focused diagnosis, not acceptance

The immutable 05d89067 factory trial failed at unit zero on both operational
jobs and official finance, each after three attempts. Original run40251928378,
artifact12622604952 remains INCOMPLETE. This diagnostic reuses its exact Native
fixture (1,200 current commercial SKUs, three sizes, historical sales unchanged)
and product composition. B source and every existing limit remain unchanged.

Only the first operational unit, official report unit, and small status read
are measured. Function self/total times come from the current transaction's
PostgreSQL counters. Inlined SQL functions may not appear, canceled functions
may not contribute complete timings, and instrumentation overhead is explicit.
These timings identify work to optimize; they do not qualify normal runtime.

The two large calls have a diagnostic ceiling of 30 seconds and a 2 second lock
limit in an isolated disposable database. Thirty seconds allows observing the
call tree beyond the already proven 8 second cancellation without an unbounded
probe. No automatic escalation or repeated attempt occurs. The small request
and status read keep 8 seconds. The scheduled runner and product SQL are exact.
Each measured call rolls back before any other measurement; full catalog, all
data/sequences, job units and attempts must remain exact. No cron is installed,
no job completes, no result is published. Complete preinstall restoration and
advisors still apply. PASS means diagnostic collection only.

Sources: PostgreSQL17 monitoring-stats.html (transaction-local function counters)
and runtime-config-statistics.html (tracking overhead and inlined SQL omission).
Official Native/Auth/browser/factory parity, efficient staged completion, safe
recovery, source consistency and combined-candidate acceptance remain open.

The first diagnostic, 69078311 / run40263535654, remains INCOMPLETE. Its
operational unit completed in 11120.770ms, then the official finance call failed
after 2593.979ms with SQLSTATE25006: official opening-stock HPP resolution uses
SELECT FOR UPDATE. This was a harness transaction-mode error, not a timeout.
The partial finance timing is not a completed report measurement. Small status
read completed in 48.276ms. FIRST_RUNTIME_FAILURE_690.json binds the original.

The successor uses READ WRITE for both measured calculation paths, retaining
the savepoint rollback, outer rollback, exact catalog/data/sequence checks and
unchanged 30s diagnostic/2s lock limits. Small status remains READ ONLY/8s.
No product source, calculation formula or acceptance ceiling changes.
See https://www.postgresql.org/docs/17/explicit-locking.html and
https://www.postgresql.org/docs/17/sql-set-transaction.html.
