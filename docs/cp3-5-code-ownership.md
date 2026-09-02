# CP3.5 full repository ownership

CP3.5 covers the complete frontend and backend repository. It removes
superseded runtime code, aligns recorded migration identities with ERP Enteng,
and preserves byte-bound accounting proof. A code file is retained only when it
has an explicit runtime, migration, regression, proof, or UAT-provenance owner.

## Runtime

Every non-test TypeScript, TSX, and CSS file must be reachable from
`src/main.tsx`. `scripts/check-source-ownership.mjs` fails the build when a
runtime file is orphaned. It also keeps the pre-CP4 browser boundary closed:

- no business RPC or private-schema call;
- the only Data API read is `public.v_erp_my_profile`;
- no imperative HTML injection API.

`scripts/check-css-ownership.mjs` rejects selector branches whose class names
have no owning production component. Status selectors remain valid when they
are scoped beneath a live component class; whole superseded stylesheets and
unowned legacy branches are removed.

Regular FG Nota identity is bound to the sewing source (`parentId + batchId`),
not a QC completion click. Repeated partial QC completions therefore cannot
recognize the same full sewn quantity twice. The 200 sewn / 20 stuck rule stays
`200 × full rate − 20 × uninstalled component rate`.

## Immutable migration history

Recorded or independently reviewed migrations are not compacted or edited in
place. Their timestamps and bytes are part of the migration ledger and recovery
contract, even when a later migration supersedes a function. CP3.5 corrected
four stale local filenames to their already-recorded UAT identities; their SQL
bytes did not change.

Four recorded source files previously carried local timestamps that differed
from the exact ERP Enteng platform ledger. CP3.5 changed filenames only so the
active migration path now uses the recorded versions:

| Release | ERP Enteng ledger version |
|---|---|
| v2.6.10 | `20260829185830` |
| v2.6.11 | `20260829204632` |
| v2.6.12 | `20260830140645` |
| v2.6.13 | `20260830190955` |

The SQL bytes and their UAT ledger MD5 values are unchanged. The full pre-v2.6.10
base remains the encrypted CP2 recovery set; this repository is not a standalone
empty-database installer and ordinary migration-folder replay is forbidden.

## Complete backend ownership

`scripts/check-backend-ownership.mjs` inventories every SQL migration,
rollback, regression, UAT evidence file, CP3 harness, renderer, and validation
workflow. The fixed map is `docs/evidence/backend_source_ownership.json`.

- 36 backend/proof files are owned;
- four recorded migration sources match ERP Enteng ledger bytes and names;
- all 22 R5 CP3 proof files remain byte-for-byte frozen;
- the only pending backend candidate is the exact four-migration CP3 set;
- no ordinary `supabase db push` may replace the reviewed ledger-complete CP3
  planner.

## Frozen CP3 candidate

The CP3 backend remains the exact reviewed four-migration candidate from R5.
`scripts/check-cp3-frozen-backend.mjs` verifies every migration, rollback,
seed, acceptance test, concurrency harness, renderer, workflow, and manifest
digest recorded by the successful R5 proof.

R3-named proof files are retained because the R4/R5 proof imports them as the
base business/accounting regression. They are active test dependencies, not a
second deployable implementation.

## Applied UAT evidence

`ops/supabase/uat/applied` and matching acceptance files document already
applied UAT boundaries. They are provenance records, not candidates for source
compaction.

## Current mutation boundary

- CP3.5 R1: frozen and superseded by the full-scope R2 candidate
- CP3.5 R2 source branch: writable until reviewer freeze
- ERP Enteng UAT: read-only
- ERP Garment legacy: read-only
- CP3 migrations: source-only, not applied
- CP4 Auth/RLS/grants: not started
