# Preserved UI proposal, not an active feature

The two patch files and complete top-level proposal/test records are escrowed
losslessly in UI_PARENT_ESCROW.tar.gz so an interruption cannot lose the work. They are
unchanged copies of the earlier helper packet. No worktree, dependencies,
build output or unrelated repository snapshot is included.

ARCHIVE.json records the archive hashes and all53 regular-file members were
checked against ESCROW_MANIFEST.json after compression. Extract to a fresh
disposable directory before reading or applying either patch:

```sh
mkdir /tmp/ow04-ui-proposal
tar -xzf docs/cp7/d17-14/ow04/ui-parent-escrow/UI_PARENT_ESCROW.tar.gz \
  -C /tmp/ow04-ui-proposal
```

`ui-parent-prerequisites.patch` contains the four existing untracked parser,
component and test files. `ui-parent-integration.patch` then changes the four
existing parent/recovery/type files and adds the parent integration test.
The integrator verified the actual six base files still match BASE_MANIFEST
and `git apply --check` of the parent patch succeeds on the current root,
without applying it. The prerequisite patch must not be applied over the
root's existing four files; use a clean disposable checkout for both patches.

The historical local167-test and full TypeScript records use declared SDK
stand-ins. Initial failures are retained. These are not new runtime tests or
evidence of actual backend/browser integration. ESCROW_MANIFEST.json binds
the exact copied files, root prerequisites and preservation scope.

Atomic integration remains required: the same backend installation must
include the new quote/settle facades, source admission, native/financial
materialization and effective-settlement readers. The parent label must say
Pelunasan efektif invoice for E=P+U−I; raw payment history still shows P.
Installing this frontend by itself against the old default product package
would call missing APIs and misstate the old reader field, so it is not active.

Before adoption, verify complete real backend/browser journeys, original
recovery UUID/envelope persistence after a lost committed reply, permission
revocation while recovery is pending, fresh source/account quote invalidation,
and failed postcommit reload retaining writer locks. Corrected/multiple-cohort
reconciliation, credit APPLY/refund consumption/undo and default production
composition are separate open contracts. OW04 remains BELUM SELESAI.
