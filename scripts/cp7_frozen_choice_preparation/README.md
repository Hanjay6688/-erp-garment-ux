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

Preparation evidence: actual optional SQL/Native work DDL/cache/retention on
local PGlite, with controlled compiler/access/producer; actual compiler scale,
concurrency, public Auth, Python installer and composed restore are NOT claimed.
Focused React tests cover gating before candidates, replay after expired source,
close while pending, current access, source binding and same-work recovery.
