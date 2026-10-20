# WA current-authority race proposal

Uninstalled source proposal. No Native, database, HTTP, provider or browser run
was performed while preparing it. `EXPECTED.json` was written before the cases.
The active repository was not edited by this helper.

Copy `cp7_wa_authority_race_cases.py` into the closed harness's `scripts/` only
after reviewing the source and the completed owning authority fix. It exposes
`RACE_IDS` and `races(tools, today, wa)`, matching the existing accessory transport
module's integration shape. Registration performs no database calls.

Append the eight IDs to the existing `IDS['races']` declaration in
`cp7_wa_forward_cases.py`. Append this module's eight closures after the existing
race closures, before the exact returned-ID assertion:

```python
import cp7_wa_authority_race_cases as authority_races

# In the existing races(tools, today), before its final ID assertion:
planned += authority_races.races(tools, today, sys.modules[__name__])
```

The writer must update the actual current manifest/declaration and derived
counts together, retaining every existing ID. This proposal does not overwrite
the shared counts, workflow, probe, source metadata or unrelated in-progress
integration changes. Each of the eight closures is required; no partial count
or skipped-case success is accepted.

The four operations each have one new-request and one exact committed-replay
case. SETTINGS/KEY block on `CP7:WA:SETTINGS`; TEST blocks on `CP7:WA:TEST`;
RESOLVE blocks on the actual target dispatch row. RESOLVE replay specifically
requires its existing `resolve_request` lookup to lock that same row before
returning a cached receipt. An immediate cached return fails the observed-wait
oracle instead of being presented as a successful race.

The worker uses the public RPC as an authenticated, initially active fixture
OWNER. A separate observer must see the holder in `pg_blocking_pids(worker)`.
Only then does a third transaction retire that fresh app_user, preserving every
preexisting OWNER row and at least one active seed owner. The holder rolls back;
the worker must refuse with exactly `42501 / CP7_WA_OWNER_ONLY`, return no receipt
and leave all durable WA receipts, settings, key events, encrypted Vault secret,
dispatch/outbox/link rows and pg_net rows unchanged. The fresh fixture owner
remains inactive.

RESOLVE targets are actual public TEST dispatches. A labelled
`TEST_CLOCK_OVERRIDE` ages only their queue timestamps by eleven minutes; the
real sender reconciliation then records UNKNOWN without a fabricated provider
answer. These cases do not prove provider delivery or source-reminder rendering.
The module starts no provider worker and refuses a leftover worker configuration
targeting its disposable copy. The existing fake CallMeBot address remains the
only configured transport.

The closed runner rebuilds its committed copy for each registered race
(`cp6_auditor_modes.py175-194`, `_run_races_once/run_one`). Preparation requires
an empty dispatch history. Root's initial three-TEST-per-hour counter assumed
all eight closures shared one copy; root withdrew that counter after checking
the actual per-case rebuild. No prior TEST rows are aged, no product limit is
changed, and the RESOLVE fixture still requires exactly one reconciliation
answer and independently checks its own actual target is UNKNOWN.

The existing end-to-end helpers restore their worker in `finally`: both the main
`worker_back()` and accessory `_provider_worker()` reset `pg_net.database_name`,
reload and restart the primary worker. This module does not reproduce or weaken
that global operation. It refuses execution if a leftover configuration still
points the worker at `cp6_auditor_race`.

Preserved source counter: owner checks preceding a blocking lock cannot
authorize writes or cached receipts after retirement commits during that wait.
The first authority-fix source counter found during this review was PL/pgSQL
`FOUND` clobbering: inserting `PERFORM require_owner()` between a lookup and
`IF FOUND` changes the branch result. Preserve the lookup result, or inspect the
typed selected row's `id`, after the fresh authority check. The full old and new
source behavior remains to be proved by the disposable Native harness.
