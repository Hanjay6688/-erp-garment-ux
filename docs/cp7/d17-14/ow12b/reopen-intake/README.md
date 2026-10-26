# B reopen correction — exact intake proposal for A

This is a proposal on B's branch. It has not changed A's branch, copied source,
runtime registration, financial routing or acceptance. A remains sole integrator.

The host at `0f818812a79013c926fcb54e949b0923bf1622ea` and its browser candidate
`1b095460e307160d9700d71c447852367984ee68` contain the same112host files, verified
with an exact Git tree comparison. Both still vendor B b96. That gate reads only
once after reopen. Eight new reopen regressions fail on that exact old copy.

`B_REOPEN_TO_A_HOST.patch` carries only these six host paths:

- Two B product modules, byte-exact from d6fad0d2: the preparation gate and monitor.
- One existing B test file plus the new eight-case reopen test, also byte-exact.
- B_SOURCE.json:91exact B files, with87existing files unchanged and3updated.
- The existing source guard: counts increase90→91,179→190 and16→17. No equality,
  source-hash, original-byte, compiled-graph, test-success or no-runtime guard is removed.

The patch keeps A's backend-parent field unchanged; that historical host field
does not qualify its backend. No public RPC, payload, SQL, SAVE condition,
financial formula, timeout or application default changes.

## Rehearsal result

In an isolated copy of the exact A host, `git apply --check` and application pass.
TypeScript and190tests/17files pass. All179original case IDs remain and pass;
11additional checks are the eight reopen cases and three monitor cases.
The existing A build function succeeds with the same79module paths. Only the
two B product-module hashes change. Its routing assertions still pass.
The updated source guard verifies91byte-exact B files and the whole test/build
evidence; stale B_SOURCE, BUILD_SOURCE or LOCAL_TESTS are each rejected.

The first sparse rehearsal omitted two A dependency roots and failed to import
three suites (173tests passed, no complete-suite credit). Materializing those
roots from the same A head resolves it. Product sources and test assertions were
not changed to address this setup failure. The first eight regressions, setup
failure and final raw reports are retained in the evidence supplement version2.
See REHEARSAL.json for exact file hashes and boundaries.

## Intake steps owned by A

1. Check every before_sha256 in REHEARSAL.json against the six target paths;
   the new test must be absent. If A has already changed any target, reconcile
   that source explicitly. Do not force the patch over another candidate.
2. On A's chosen candidate, apply with `git apply --check` followed by
   `git apply` using B_REOPEN_TO_A_HOST.patch. Ensure B d6fad0d2 is available
   to the original-byte checker. This is a host-only proposal, not an installer.
3. Run the host's TypeScript check and full configured Vitest suite. Regenerate
   LOCAL_TESTS.json using Vitest's JSON reporter; expect190/17, preserving179old IDs.
4. Run the existing buildCurrentProgressFinance from build.mjs in build-only
   mode, regenerate LOCAL_BUILD.json and BUILD_SOURCE.json from its actual
   returned source_paths, then run the host source_guard.py. The graph remains79.
   Do not reuse old build/test receipts with the new source.
5. Refresh A's current-progress-finance-ui-browser-qualification/HOST_SOURCE.json
   and its exact declarations/guards to the adopted host through A's normal
   source binding. This patch does not edit that qualification or bind an
   unqualified Native predecessor. Keep the old originals and source packages.
6. After the required exact Native5 and Native6 Originals pass and are intaken,
   qualify actual Auth/browser/K4/retention/two-session/after-use restore and
   full-factory official finance/HPP. B's standalone Browser6 PASS remains a
   separate controlled-RPC result, not transferable acceptance of A's host.

This rehearsal used controlled local RPC/Auth and a synthetic build-only key;
it made no database/network request and launched no server workflow. It earns
no actual browser/Auth/Native/cron/factory/finance parity or restore credit.
Formal5/16 remains unchanged; B scope is open; independent_acceptance=false;
production_go=false. The next action is A intake, followed by B checking the
adopted source and production behavior on that actual combined candidate.
