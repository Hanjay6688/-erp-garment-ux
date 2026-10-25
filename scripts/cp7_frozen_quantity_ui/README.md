# Prepared frozen quantity client and UI

Explicit disposable-only entry. The default application does not import it.
The durable record uses the existing v2 actor/scope namespace and Web Lock.
Every open/reopen replays the explicit v2 request; shared status alone cannot
prove method identity. The result reader reaffirms v2 before accepting DONE,
then checks request/run/query/actor/target count, original microseconds, all
page hashes, access epoch and identity. No cast of a v2 request to v1.

The driver holds the same lock for every request, get, step and page read.
Replacement waits for an in-flight unit; the following call rereads the exact
stored request. Raw storage changes outside the lock retire the answer.
Read failures retain the pointer. Failed replacement retains the old result.

The UI displays server progress and totals, 50 rows at a time, complete source
pages and all-label product search. UNKNOWN remains distinct from known zero.
Candidate links use only a verified v2 source and the prepared frozen analog
panel. Current permission loss and cross-tab replacement clear stale displays.
An unresolved request cannot be silently replaced by a fresh UUID/query.

No cutting SAVE is wired in this preparation. The existing checked-plan path
requires actual frozen-source compatibility and bounded Native/HTTP evidence
before that handoff is enabled. Official finance, default adoption, full OW12b,
independent acceptance and production_go remain unqualified.

Validation: 19 transport + 15 DOM cases; 146 including retained client suites;
dedicated TypeScript; source serving; unchanged F05/default app and 51 backend
source pins. Separate Browser4 declares real Chromium desktop/mobile, three
source pages, whole-label search, exact reload recovery, actual StorageEvent
and access-loss retirement. RPC/identity replies are controlled; actual Auth
and Native credit require their own complete Originals.
