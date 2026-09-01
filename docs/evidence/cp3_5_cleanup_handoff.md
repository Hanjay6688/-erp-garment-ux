# CP3.5 canonical cleanup handoff

Review the exact branch HEAD, then verify its parent is the code commit recorded
in `cp3_5_cleanup_manifest.json`. The final commit is evidence-only.

## What changed

- Removed superseded imperative renderers, fake test-only mutation guards, and
  orphan runtime modules.
- Replaced the movement-book DOM observer with native React state and tests.
- Removed legacy CSS files and unowned selector branches; CI now enforces both
  source-file and selector ownership.
- Lazy-loaded heavy workspaces and separated vendor code from the initial app
  chunk.
- Bound regular FG Nota payroll identity to the sewing source instead of each
  QC completion, preventing repeated full-gross recognition.
- Preserved all 22 reviewed CP3 backend/proof files byte-for-byte and preserved
  the exact four-migration planner.

## Required reviewer checks

1. Re-resolve branch HEAD and reject any drift.
2. Run `npm ci`, `npm test`, `npm run test:security`, and `npm run build`.
3. Verify `npm run check:cp3-backend` reports 22 files and four migrations.
4. Recheck the 200 sewn / 20 stuck example and repeated-completion identity.
5. Perform the browser visual pass in an environment with Chromium; the writer
   environment could not install or launch a browser, so this item is not PASS.

## Mutation boundary

- Git mutation: CP3.5 branch only
- ERP Enteng UAT mutation: NO
- ERP Garment legacy mutation: NO
- Deploy: NO
- CP4 Auth/RLS/grants: NOT STARTED
