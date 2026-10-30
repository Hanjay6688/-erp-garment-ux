# PostgreSQL17 lock mechanics, isolated model

This self-contained qualification compares the retained SHARE ROW EXCLUSIVE
blueprint with an EXCLUSIVE NOWAIT option. It imports no ERP module, installs
no ERP object, connects only to localhost54329/cp7_lock_mechanics and requires
PostgreSQL17. The password is public disposable model configuration, not an
application credential. The original global inspector, source authority,
financial engine and closed integration entry remain unchanged.

The actual server must match24 independently recorded lock-conflict pairs,
two real foreign-key holder cases, one before-effect busy command with all
model rows/sequences unchanged, one ordinary SELECT and four observed
blocking insert schedules with actual pg_blocking_pids across distinct
backends and commit/rollback release. The model's rows and sequences must
return exactly to their baseline, and its schema and sessions must disappear.

The old SRE option permits ROW SHARE, including an actual FK parent lock.
EXCLUSIVE excludes ROW SHARE and writers while allowing plain reads. NOWAIT
must fail before any command sequence/row effect. These are lock mechanics,
not proof that a proposed ERP relation list is complete or that its owning
hooks take the barrier early enough. No ERP Native, Auth, browser, production
or independent acceptance is conferred by a successful model.

Sources checked30October2026:
- https://www.postgresql.org/docs/17/explicit-locking.html (Table13.2)
- https://www.postgresql.org/docs/17/sql-lock.html (NOWAIT, transaction scope,
  table order, and fresh READ COMMITTED versus frozen higher-isolation reads)

The workflow retains the actual server/image metadata and first result even
on failure. Source sealing occurs locally only; CI cannot rewrite its pins.
