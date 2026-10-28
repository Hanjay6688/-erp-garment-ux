# D17-18: progress projection owned by integrator A

This module validates the exact existing B job/finance parser and projects a
combined status. It performs no RPC, scheduling, source read, transaction,
calculation or retry. It changes no existing B files or qualified backend.

Operational completion and official finance readiness remain separate. A
completed capture with BLOCKED/LIMITED report readiness is incomplete. Unit
percentages use completed server units only; an unfinished operational plan or
unknown finance denominator has no percentage. There is no overall percentage:
heterogeneous production and finance units are not an overall work denominator.
Clock passage never advances progress or invents a failure.

Elapsed time is explicitly the client observation clock minus the original
capture time, including waiting. It is not measured SQL time, terminal runtime
or an ETA. A client clock preceding capture produces an unavailable duration.

Remaining D17-18 gaps: the current public v1 contract does not expose a finance
last-progress timestamp, active worker/queue observation, complete-job duration
or an explicit stall signal. This module returns unavailable values rather than
guessing. A separate source-bound read-only telemetry contract must be agreed
with B and qualified before those states can be shown. Existing server retry
and source-change failure behavior is preserved. No new timeout has been set.

Not yet mounted in the UI. Tests use controlled wire fixtures; they do not
provide real browser, Auth, factory, runtime or independent acceptance credit.
The existing UI63d and six live pre-D17-18 candidates remain unchanged. Current
timing evidence and first failures remain valid under their original policies.
