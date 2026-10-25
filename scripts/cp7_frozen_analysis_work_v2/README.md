# Explicit frozen work reader and schedule recovery preparation

The client is outside the application import graph. It reads existing
`erp_cp7_get_staged_production_schedule_v1` for the exact immutable v2 job,
and saves through existing `erp_cp7_save_staged_production_schedule_v1`.
The stored source run determines the backend dispatch. The client requires
explicit v2 workspace, request/reference and outcome contracts. It never
relabels the source as the previous bounded method.

History input coverage may be PENDING while captured physical work is usable.
DONE requires COMPLETE coverage; raw INCOMPLETE history is retained. UNKNOWN
physical work cannot be saved. Customer work is never allocated to company
stock by this adapter. Source identity includes exact microseconds.

Recovery retains actor, method, original source reference, exact payload and
UUID. A real browser Web Lock encloses every storage mutation and the complete
RPC attempt. A queued send rereads durable storage after obtaining that lock.
No missing lock/storage fallback, v1 migration, or automatic discard on an
ambiguous error. Clear requires the exact retained command. Server current
access/source/revision checks remain authoritative.

Local: 55 new client tests + 58 retained tests = 113 PASS; dedicated TypeScript
PASS. Controlled FIFO lock tests do not establish real browser concurrency.
The separate Browser3 workflow executes two Chromium tabs with actual Web
Locks/localStorage and controlled replies. No Native/Auth/UI acceptance is
assigned from that workflow. No SQL, shared default installer, generated
types, RPC registry, application UI, or qualified backend source changed.

Still required: actual frozen-source Native schedule SAVE/replay/current-access
and lock-wait qualification; production UI adoption and Auth/browser journeys.
Production remains disabled. See the preparation receipt and complete CI
Originals for exact source binding and first failures.
