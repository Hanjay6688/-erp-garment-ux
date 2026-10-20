# First actual HTTP8 run: missing STAFF master fixture

Candidatef3437108, run39492199058/job118867983298, executed all eight slots:
7PASS/1INCOMPLETE. Actual CREDIT and REFUND commits, fresh-connection exact
money/journal/date/stock/HPP verification, committed replay and five negative
cases passed. CP6 restoration and advisor gate were true. The complete first
log and per-case results are retained in CI_F343_HTTP_FIRST_RUNTIME.log.gz
and CI_F343_HTTP_FIRST_FAILURE.json.

The non-owner case stopped with OW04_HTTP_STAFF_ROLE_REQUIRED while looking
up a STAFF row in the disposable ERP role master. It never reached STAFF
Auth creation, login or either refund refusal. That authority distinction
is not proved by this run. The frozen copied runtime seeds OWNER/ADMIN for
its old cases; assuming a third role was a new fixture setup error.

The corrected test explicitly creates a non-system, unprotected active STAFF
master only if absent, exclusively on its disposable HTTP copy. An existing
inactive STAFF remains a setup refusal. It then copies the actual OWNER fine
permission keys, checks all six required keys, creates a real Auth STAFF user
through the unchanged retained harness, and requires that same user's CREDIT
quote to succeed before both REFUND calls fail with the exact unchanged
Native400/P0001 owner/admin message. No Native permission/posting helper,
public facade, authority guard or product role is replaced or broadened.

The eight declared IDs and EXPECTED.json remain unchanged fromf3437108.
Both implementation bytes and the reused Native44 core identity remain
reported independently. A fresh actual HTTP run is required; the historical
seven passing cases are not reclassified as an eight-case PASS.

The following six SQL concurrency/recovery cases are separately predeclared
in RACE_EXPECTED.json. They exercise actual waiting, COMMIT/ROLLBACK and an
explicit known-backend termination on disposable copies. They are not real
Auth or browser tests and cannot inherit PASS from either previous group.
No Enteng/main/production changes; OW04 remains open, production_go:false.
