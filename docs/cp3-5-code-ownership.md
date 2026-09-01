# CP3.5 code ownership

CP3.5 removes superseded runtime code while preserving byte-bound accounting
proof. A file is retained only when it belongs to one of these categories.

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

Recorded or independently reviewed migrations are not compacted, renamed, or
edited in place. Their timestamps and bytes are part of the migration ledger
and recovery contract, even when a later migration supersedes a function.

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

- CP3.5 source branch: writable
- ERP Enteng UAT: read-only
- ERP Garment legacy: read-only
- CP3 migrations: source-only, not applied
- CP4 Auth/RLS/grants: not started
