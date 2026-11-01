# Readonly system and scheduler metadata preparation

This prepares 27 SELECT queries across all namespaces, including system
routines, role settings, rules/triggers, foreign servers, cron, logical
replication and live backend metadata. It does not install or invoke a
business/provider function, open a connection, select locks, or certify
writer/permission closure. No hosted operation is supplied.

The caller must already hold an administrative, read only, repeatable read
transaction on loopback port 54322 and set `SET LOCAL search_path=pg_catalog`.
`capture(cur)` requires `cp6_rollback`; `capture_scheduler(cur)` requires
`postgres`, because cron in the primary scheduler database can target the
candidate database. Their separate snapshots are explicitly not atomic
writer proof. Autocommit, other hosts/ports, untrusted search paths, changed
authority and changed snapshots are refused. The collector never commits.

Routine bodies, defaults, configurations, foreign connection options,
cron commands/hosts, subscription connections and backend query/client
details are withheld or hashed. Raw ACLs retain NULL distinctions. Foreign
user mappings are not collected.

The first 23 SQL queries passed in isolated PGlite PostgreSQL 17.5 and were
not rerun after adding four queries. The four added queries passed separately;
their actual embedded catalog results were empty. Two labelled synthetic SQL
projections checked backend and subscription redaction expressions. Those
projections do not establish redaction coverage on live ERP backends.
The first added-query control's incorrect nonempty-backend assumption and its
failure are retained, followed by the corrected control. The earlier 23-query
receipt identifies its own exact bundle; it does not cover the later four.

Six local cursor-model controls check administrative preconditions and
changed snapshots. All evidence here has zero ERP Native/browser case credit.
Current rights after waits, owning hooks, external writers, phantom protection
and two-session proof remain open on the final candidate.
