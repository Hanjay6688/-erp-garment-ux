# Frozen request v2 facade — prepared, unqualified, not adopted

One explicit new authenticated facade delegates exactly query and UUID to the
private frozen request. The server derives the actor/current access, compares
the full query and method on replay, and rechecks access after waits/capture.
Owner cp7_capture, empty search_path, no public CREATE grant, no anon/service/
alert execution and no table or old function changes. Pre-use removal requires
unchanged usage and refuses external functions or dependency views. This code
is not part of a default installer or public registry; A owns that adoption.

The separate prepared nativeFrozenAnalysis client uses a v2 storage namespace
bound to the current actor and scope. It rereads the durable exact request
before every network attempt; a lost reply never clears it or sends a new UUID.
Old v1 pointers remain untouched. Actor metadata is not accepted from the client
as server authority and is not sent in the request payload.

Actual Native catalog/install/remove, current Auth HTTP access, observed lock
races, browser flows and the underlying private-unit Native4 result remain
required. No public activation, runtime acceptance or production_go is implied.

Local evidence: 12 new recovery tests plus20 retained v1 tests pass; dedicated
TypeScript check passes. Four PGlite18.6 facade controls use a controlled private
request and do not qualify actual ERP policy or the Python catalog installer.
The source/access checkers report exactly the same existing registry drift on
e33 and this preparation. The first unreferenced src placement was rejected;
the module was moved out of the app graph, without a dummy import or exception.
Its original diagnostic log was not retained. Shared A registry was not changed.

Prepared provider: three Native cases, three observed blocking-session races
(same UUID, access changed during source capture, access changed during committed
replay), and two real Auth HTTP cases. It is not wired into F05/a workflow.
PGRST202 schema-cache readiness is bounded5s; business refusals are not retried.
No actual concurrency or browser credit follows from local storage tests. Atomic
cross-tab arbitration and the explicit v2 work parser remain adoption tasks.

Subsequent lock preparation: the same actor/scope namespace uses exclusive
browser locks for every create/clear/replace/send; a send holds the lock until
its reply/rejection. Missing lock support refuses before touching storage or
network. All mutation APIs are now asynchronous and require await.35local tests
(15new+20retained) and TypeScript pass with a controlled FIFO lock manager.
The actual two-tab browser qualification is still required. No active UI adopts
the package; prior32-test preparation evidence remains historical and retained.
