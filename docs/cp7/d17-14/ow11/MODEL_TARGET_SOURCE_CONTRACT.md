# Private current model source

Three private functions, no public RPC, table or caller replacement. The server
selects the latest immutable v2 evaluation owned by the current actor for each
physical root and size. A newer baseline-only result supersedes an older winner;
the source cannot cherry-pick a favorable evaluation. A historical cutoff that
omits a newer current evaluation is refused.

The original v2 current_guard checks the parent history, policy, model engine,
forecast origin and captured eligibility. Old stored inputs and assessments
remain unchanged. Only a currently eligible row exposes its selected model and
vector to the future consumer. The exact history query travels with the row so
that target calculation can refuse a different date window or grouping mode.

One global Native history source is read before all rows and once again after
them. Current access, latest evaluations, policy, both engines and the WIB date
are checked again before returning. Source identity includes the current access
epoch as well as actor, policy, model engine, consumer engine, live history hash
and selected rows. Wall-clock check timestamps do not invalidate identical state.
No owned evaluation means no unnecessary global history scan.

The source deliberately matches the existing model-v2 reader's 1,000-product
Native history limit. An incomplete source retires the vector; it is never
promoted to complete or interpreted as zero. A bounded factory model-history
adapter remains open and is not qualified by this prototype.

Local actual SQL passes 13 cases, including actual immutable v2 rows and the
original serve_history function. Historical observations and policy are explicit
synthetic fixtures; access and live source are controlled. This is not actual
Native capture, Auth, factory scale, target-caller or production qualification.
The first 12-case checkpoint and final access-epoch result are retained.

Next: bind these server-owned rows to the existing baseline inputs and exact
query, preserve manual/own/analog priority, use one dated projection for ROP and
production, and propagate identity into staged and checked-save freshness.
