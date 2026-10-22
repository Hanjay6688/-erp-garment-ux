# Closure scheduling proposal — no implementation or performance claim yet

The current actual browser counter window has10 deferred consumer-closure
trigger calls for one consumer20 command. Each reruns the complete historical
and current source proof. Current measured save latency is13–29seconds.
The isolated current-transaction timing job is still running; its results must
be retained before choosing or qualifying this optimization.

Proposed change: each insert/update on the same five private consumer tables
immediately enqueues its exact actor/request under the actual backend and
transaction. A postgres-owned private table coalesces only pending validation,
with one deferred constraint-trigger event per pending operation. At firing,
the event must find its exact unchanged pending row, resolve the actual
operation, run the original full assert_consumer_closed_v1, then delete only
that queue row. There is no stored successful-proof flag or cached truth.

If SET CONSTRAINTS has already fired, the row was deleted; a later mutation
must insert a fresh queue row and queue another complete check. A missing or
altered pending row must refuse, never skip validation. Multiple operations
in a transaction must each validate the final state. Every current permission,
immutable input, manifest, journal, Native/header, stock/HPP, dated capacity
and leak check stays in the existing full assertion. The queue grants no
command or posting authority and adds no typed Native internal capability.

Before accepting it, actually rerun all26 old Native cases plus six frozen
protocol cases: one/multiple operations, removed/changed queue row, requeue
after immediate closure, and a real late receipt mutation after enqueue.
The last mutation must roll the actual financial command back. Ordinary
roles must have no queue DML or helper execute. Full22 catalog, pre-use
removal, used-state restore, actual Auth/browser/concurrency and performance
still require evidence on any changed financial source.

This plan and EXPECTED.json are frozen before product implementation. A green
protocol test alone cannot establish product speed or completion of OW04.
