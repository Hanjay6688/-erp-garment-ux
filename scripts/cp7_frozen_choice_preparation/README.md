# Explicit frozen choice preparation — new owner timing policy

Prepared optional extension, not a default installation or qualified runtime.
The owner26October permits long total analysis but requires heavy reconstruction
to be separated from daily SAVE. The existing choice K3 failure is retained.

The measured K3 reader spends4557.743ms preparing the same sealed inputs before
two live source checks; cached confirmation was7220.494ms. This extension moves
that pure preparation to its own bounded unit. It reuses actual `prepare`,
`pack`, `unpack`, frozen capsule, producer identity and existing access/retention
guards. It never runs a new whole-factory analysis or recaptures current stock
at an old clock. Valid existing temporary inputs are reused; otherwise the same
compiler is run once. Original job/reference/pages and K3 tables stay unchanged.

One private work row per original job supplies durable deduplication and exact
source binding. `request` only enqueues; `step` performs one bounded unit;
`get` reads status. Concurrent steps use a nonwaiting advisory lock. A busy
worker is reported as RUNNING, an available queued row as QUEUED. READY means
only preparation finished, never that a choice was saved. Three real unit
timeouts fail the work; other errors fail immediately. No totals from a timer.

The optional replacements are exactly the private candidate reader and choice
`review_context` reference calls. Prepare before reading the first candidate:
otherwise a cold candidate read followed by preparation would duplicate the
same factory compilation. Both readers and SAVE consume the same inputs; absent inputs
raise PREPARATION_REQUIRED instead of compiling all targets during SAVE. Both
live source checks, the global FG envelope, request/target locks, current access,
exact receipt replay and final write ordering remain in their original bodies.
The public v2 candidate wrapper/signature and candidate arithmetic remain
unchanged. Its private reader now refuses missing preparation, without writes.
`client/PreparedFrozenAnalogPanel.tsx` supplies the explicit gated caller; it
keeps saved-choice receipt recovery available even when preparation fails or
the original source expires. `PreparedFrozenChoicePanel` is the narrower caller
for already-read candidates. Neither is imported by the default application.

Integration contract for A, before shared interface edits: three new B RPCs
`erp_cp7_request_frozen_choice_preparation_v1`,
`erp_cp7_get_frozen_choice_preparation_v1`,
`erp_cp7_step_frozen_choice_preparation_v1` use the **original source request**
and access epoch, with no newly invented analysis UUID. The existing K4 scheduler
can call the private `run_next` in a short8s transaction; this module does not
replace the shared scheduler or install a cron job. Until A composes that hook,
the prepared UI must not promise work continues with the page closed. Default
adoption, shared public registry, actual Native/Auth/scale/two-user/restore proofs
remain separate. No financial formula, balance, stock or HPP writer is changed.

Retention is checked on every use. `purge_expired` clears only expired private
payloads in bounded batches and retains the work identity as EXPIRED. READY
payloads and source binding cannot be rewritten; no FK obstructs the original
retention path. Used preparation requires full composed restore, never a
pre-use inverse. A must compose the cleanup hook, scheduler, public registry,
restore manifest and exact-source qualification route before adoption.

The worker observation follows the existing `cp7_analysis_jobs.worker_active`
pattern: read `pg_locks` without taking a lock. Enqueue and worker keys are
separate; another status read does not masquerade as a running worker.
PostgreSQL17 reference: https://www.postgresql.org/docs/17/view-pg-locks.html.
Single-unit8s is retained because the measured frozen preparation frame was
4557.743ms; it is not a universal total-analysis deadline. No retry raises it.
The client30s RPC wait and120s unchanged-unit monitor reuse the production
progress limits. A stopped monitor does not mark server work FAILED.

The optional private runner also counts cancellations during access/source
checks outside the compiler block. Its selected row remains the same work;
three such cancellations become FAILED and the caller's three claim settings
are restored after each handled attempt. Other access errors fail immediately.
PostgreSQL's `OTHERS` handler excludes query cancellation, so that condition
must be named explicitly (PostgreSQL17, PL/pgSQL Control Structures section41.6.8:
https://www.postgresql.org/docs/17/plpgsql-control-structures.html#PLPGSQL-ERROR-TRAPPING).
The local regression injects SQL57014 before the step; it does not claim a real
wall-clock timeout, backend termination, two-session or Native17 proof. Process
loss and combined K4 recovery still require A's separate qualification route.

Preparation evidence: actual optional SQL/Native work DDL/cache/retention on
local PGlite, with controlled compiler/access/producer; actual compiler scale,
concurrency, public Auth, Python installer and composed restore are NOT claimed.
Focused React tests cover gating before candidates, replay after expired source,
close while pending, current access, source binding and same-work recovery.

Reopening now observes QUEUED/RUNNING work with sequential status reads at the
existing two-second polling interval. It never enqueues or steps work merely
because the panel reopened. READY/FAILED/EXPIRED stop observation immediately;
lost replies and two minutes without persisted progress stop with the existing
recovery message. A real attempt/progress update resets that observation window;
alternating worker-lock observations do not. Explicit continuation retires the
older observer and keeps the same source request/access binding. Unmount or
identity changes retire late replies. Missing work is silently treated as not
started only on the first read, never after an existing work was observed.

This corrects a one-read-only reopen defect reproduced by six failing local DOM
cases. The repaired preparation and related choice clients pass97 tests in7
files, including42 preparation tests; these overlapping totals are not summed.
SQL and all RPC shapes/limits remain exact. A's prepared composition at613209db
has importedb96e2f74; it must explicitly intake this newer client correction.
Actual new preparation Native/Auth/runner/factory qualification remains open.
