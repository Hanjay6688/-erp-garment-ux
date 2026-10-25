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

## Prepared schedule screen

`client/NativeFrozenSchedulePanel.tsx` and its separate physical-work form use
the actual existing Auth boundary and Supabase client but are not imported by
the application. Explicit DISPOSABLE_TEST only; four read permissions and
current manage permission. Actor storage uses auth UUID, not app profile ID.
Identity/query changes unmount pending work. Storage events and close retire
late replies without clearing retained commands. 401/403/42501 retire visible
work and retain recovery. Coexisting read and save recover independently.

The form preserves original microseconds when WIB input is unchanged, leaves
unknown assumptions blank, includes customer work without assigning company
stock, and keeps dirty input until explicit adoption after source/revision
change. Local 15 DOM journeys plus existing client/planning checks total153
PASS; dedicated TypeScript PASS. First failures are retained in the UI receipt.
Separate Browser4 renders desktop/mobile, submits the actual form, exercises
reload, actual cross-tab storage events and held replies on permission change.
Identity and RPC are controlled; it does not qualify real Auth or Native SAVE.
Screenshots require visual inspection after the complete original is returned.
