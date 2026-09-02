# CP3.5 full canonical cleanup handoff

Review the exact branch HEAD, then verify its parent is the code commit below.
The final commit is evidence-only.

## Exact target

- Repository: `Hanjay6688/-erp-garment-ux`
- Branch: `cp3.5/full-canonical-cleanup-r2-20260901`
- Code commit: `ab326226ade12758689e03496f3e5d68c7c7fbd1`
- Code tree: `6fad34e49f51821986f62fe67ccb26b9b16994a7`
- Code CI run/job: `33573764408` / `100073138874` — `SUCCESS`
- Artifact: `9825879216`
- Artifact SHA-256: `859efc546c651ab10916abb03e15bb70184a014e3e7b1232cf98e7f734e8ceb0`

## What changed across the full CP3.5 scope

- Cleaned the complete frontend runtime graph, not only CP3 UI: removed
  superseded imperative renderers, fake test-only guards, orphan modules, legacy
  CSS, and unowned selectors.
- Replaced movement-book DOM mutation with React state and tests; lazy-loaded
  heavy workspaces.
- Bound regular FG Nota payroll identity to the sewing source, preventing a
  repeated QC completion from recognizing the full gross amount twice.
- Inventoried all backend source/proof material: 36 files have explicit owners
  and fixed hashes; no backend artifact is unclassified.
- Corrected four stale local migration filenames to the exact ERP Enteng ledger
  versions. All four are 100% content-identical renames; no SQL changed.
- Preserved all 22 reviewed CP3 R5 backend/proof files and the exact four CP3
  migrations byte-for-byte.

## Required reviewer checks

1. Re-resolve branch HEAD and reject any drift or concurrent writer.
2. Verify the final commit changes only this handoff and its evidence manifest;
   verify its parent/tree against the exact code identity above.
3. Run `npm ci`, `npm test`, `npm run test:security`, and `npm run build`.
4. Run `npm run check:backend`; require 36 owned files, four ledger-aligned UAT
   sources, four exact CP3 migrations, and zero unowned backend artifacts.
5. Verify each migration rename is content-identical and matches the hosted UAT
   ledger version/MD5. Do not interpret a filename correction as a SQL rewrite.
6. Recheck the 200 sewn / 20 stuck example and repeated-completion payroll
   identity.
7. Perform the browser visual pass in an environment with Chromium; the writer
   environment cannot claim this item as PASS.

## Truth and mutation boundary

- Frontend cleanup: `PASS` locally and in CI
- Backend repository ownership: `PASS` locally and in CI
- CP3 backend business bytes changed: `NO`
- ERP Enteng UAT mutation: `NO`
- ERP Garment legacy mutation: `NO`
- Deploy: `NO`
- CP4 Auth/RLS/grants: `NOT STARTED`
- Independent reviewer verdict: `PENDING`

The existing Drive recovery set remains the pre-review fallback. After an
independent PASS, create and independently restore a fresh final CP3.5 backup
before starting CP4.
