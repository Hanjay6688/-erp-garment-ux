# OW11 — prospective policy Auth and concurrency candidate

This separately declared10-case composition keeps the strict twelve-stage
parent and installs the policy stage only inside disposable test copies.
The catalog anchor repeats Native6 admission and earns no new case credit.

Six races use distinct PostgreSQL backends: same UUID/payload, competing
revision, deactivation while waiting on the global envelope, deactivation
before a committed request replay, deactivation while waiting on the policy
lock, and an actual owner-to-auditor role change during the envelope wait.
The harness observes pg_blocking_pids, then releases the holder. Refused writes
must leave no orphan policy, registry or command. Successful concurrent writes
must insert exactly one atomic triple; stock, HPP and financial tables remain
unchanged. Wait observation and request timeouts are bounded.

Three actual Auth/PostgREST cases cover SET/SUSPEND/read and exact replay after
withdrawal, revoked old-token reads and committed replay, anonymous calls,
auditor writes and a foreign actor's epoch. The final case also verifies that
another authorized owner can write the global policy using their own fresh
epoch; this shared policy is not artificially restricted to its first author.

The default installer, SQL, immutable source history, original metadata suites,
8-second requests and45-minute jobs are unchanged. Static Python/YAML,
declaration and strict group/negative-parent checks pass. Actual runtime is
pending. This is neither browser nor model forecast activation evidence.
Formal acceptance remains5/16 and `production_go=false`.
