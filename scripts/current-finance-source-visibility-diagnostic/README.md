# Prepared source-visibility counterexample — Writer A

Status: PREPARED, NOT EXECUTED. No product fix or runtime PASS is claimed.
The currently running parent is953b87c0/run40509260377/job122206515921; this
separate worktree does not change that frozen candidate.

The accepted bd3505f6 race commits a Native kasbon created after the financial
report snapshot. This case posts through the same Native writer inside an
explicit savepoint before the snapshot, holds the outer transaction open,
reads the old journal and lines, then commits before the book and cash chunks.
It reuses the seed contractor, bank and date so later-family counts remain
constant. It records actual parent/child transaction IDs and PostgreSQL
visibility answers. It requires rejection before sealing; an escaped READY
result records whether the signature matches neither the old nor current
whole book before raising. No expected amount or source hash is fabricated.

Why this additional case is necessary: PostgreSQL17 documents that
pg_visible_in_snapshot does not give correct answers for subtransaction IDs.
The present capture derives IDs from row xmin; that is a code-review risk,
not proof that this ERP case fails. First obtain actual evidence with the
unchanged parent. Preserve its outcome, even if it disproves the hypothesis.
https://www.postgresql.org/docs/17/functions-info.html#FUNCTIONS-PG-SNAPSHOT

Execution requires an accepted exact parent Original, fresh disposable
cp6_rollback on localhost:54322, and full preinstall backup/restore around
this committed fixture. No hosted database, public RPC, B-owned file, cron
schedule or timeout is changed. Source and role restoration must be checked
alongside the case. The case is not independently runnable as a deployment.

Related open review: the normal scheduler writes a heartbeat before dispatch;
Business Report v2 takes a report-job row lock and starts a capture before
report_unit. Both can assign a transaction ID and suppress report_snapshot.
The current parent cron records its actual snapshot. The staged-report path
needs a separate observation. A future repair must cover both paths and the
source-visibility case, not merely move one heartbeat.
