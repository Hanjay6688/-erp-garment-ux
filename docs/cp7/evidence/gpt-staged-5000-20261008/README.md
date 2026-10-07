# Writer integration evidence: staged 5,000 targets

Checkpoint source: `7927b42cf80dc44dd8af19d7f9138e2469e1efc4`;
last qualified product base: `013ea062e69e3fb4a9d12431be8b74650bfc41c4`.
All WIP patches from the checkpoint were applied together in their documented
order. No hosted database, deployment, main or integration branch is changed.
`production_go=false`; `independent_acceptance=false`.

## Local validation (not Native/Auth/HTTP/browser proof)

Runtime: explicitly selected PGlite with pgcrypto, labelled
`PGLITE_WASM_LOCAL_NOT_NATIVE_AUTH_PROOF`. Native PostgreSQL is not available
in this workspace. Native and full application evidence must come from CI.

| Evidence | Result | Exact scope |
|---|---|---|
| `17-frontend.log` | 1,469 passed, 145 files | All `src` Vitest tests; includes ordinary and staged routes |
| `18-reopen-pause.log` | 11 passed | Staged panel DOM, same UUID pause/resume and completed reopening without recompute |
| `06-hash-contract.log` | 8 passed | Page identity including zero pages and malformed identity rejection |
| `08-parity-first.log` | 1 passed, 3 unselected | Selected 162-capture product analysis/Original parity corpus; remaining tests must run Native |
| `11-real-scenario.log` | 3 passed | Full real scenario chain parity, caps and deliberately incorrect units |
| `12-product-pages.log` | 2 passed | Product page reassembly under three byte budgets; page/access contract before extra security cases |
| `19-page-security.log` | 2 passed, 1 unselected | Current multibyte/hash/access/immutable/source checks and oversize-target refusal |
| `26-progress-api.log` | 3 passed | UUID cross-path refusal; six public boundaries; access revoke; immutable/purge; real progress contract at each unit; 5,001-target first-unit refusal |

Final typecheck, Python compilation, JS syntax and source/access/CSS catalogs
passed. Catalog: 277 runtime files, 216 RPC boundaries, 111 permissions and
48 routes. No frontend test claims browser performance.

## First failed attempts retained

Logs 01–16 retain fixture/contract/DOM setup failures and their diagnosis.
`15-reopen-pause.log.gz` is the exact losslessly compressed original DOM log
(large repeated render dumps); decompression restores it byte for byte.
Logs 20–21 show why using a limited API stand-in over a real scenario was an
invalid fixture (missing `remain_eta` privileges); the regression now calls
the real private kernel in the disposable runtime. Native/Auth uses the
closed full-bundle CI suite, not that stand-in.

`22-progress-old-failure.log` is the actual old-product regression: NET_PAIRS
reported 2 completed targets although it had processed position ranges.
The repaired status counts only target-range units. Logs 23–25 retain
subsequent test construction mistakes (zero-root generator, camelCase
parsed field, and a stand-in that bypasses real HIST_PREP bounds). The final
real-chain regression in log 26 passes without loosening the bound.

## Required CI evidence

- Product kernel suites plus independent Native sessions, lock/retry tests,
  benchmark vectors 1,000×30, 5,000×30 and 5,000×100, all target rows covered.
- Native/Auth/HTTP/browser `p19-staged12` and the full application scale
  ladder at 100/300/1,000/5,000; all generated pages actually read.
- Measured time from trusted next-page click to verified rendered page plus
  two paint frames; same measurement when reopening a completed result.
  Owner steering 8 Oct 02:09 WIB makes 3,000 ms a goal, not a mandatory gate;
  optimise as far as possible. Actual times and goal results remain visible.
- Background computation wall time, capture time and acknowledgement are
  separate measurements. None is substituted for usable result loading.
- The four previously path-filtered ERP workflows run on this head too;
  one-head qualification remains pending until their actual results exist.

P20/P21 packaging, integration merge and auditor acceptance remain pending.
Open owner policy values remain open; no invented yield/retention/driver or
downstream staged feature policy is included.
