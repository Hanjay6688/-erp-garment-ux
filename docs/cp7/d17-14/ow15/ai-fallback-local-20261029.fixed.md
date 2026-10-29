# Staged Tanya AI — local selection-race closure

Current writer result: **16/16 local tests PASS, zero skipped; typecheck PASS**.
This is not Native, real Auth/browser, independent acceptance or production GO.

The first-failure commit `a348ed2bc2c20bd044d250de265e3d3ace2feb14` and its
three raw reports remain unchanged. The exact same eleven tests were first
rerun against the repair and all eleven passed, including the previously
failing oracle. Five further asynchronous-boundary controls also pass.

The narrow product change in `src/NativeStagedAiPanel.tsx` retires pending
request generations when the actor, run/source identity, query, selected
targets, question or finance context changes. A layout effect retires the old
context before the changed screen is painted, clears its text/messages/error,
and releases busy so the operator can request the newly selected context.
Every async continuation checks both its generation and mount state. An old
response cannot publish/copy data, replace the newer result, report its old
error or release a newer request's busy state. Unmount retires pending work.

The original strict run/identity/time/selected-target parser, server RPCs,
finance read/permissions, JSON quoting and static manual ChatGPT link are
unchanged. A clipboard operation that already started while its context was
valid cannot be undone; a late acknowledgement no longer restores obsolete
manual text or a success message, and no additional copy is issued.

Additional controls beyond the original eleven: overlapping old success;
overlapping old 403; displayed run replacement; disposal during the brief;
late clipboard acknowledgement after selection retirement. Their expected
behavior is in the DOM test, not derived from an implementation token.

Commands:

```text
node node_modules/vitest/vitest.mjs run src/NativeStagedAiPanel.fallback.dom.test.tsx src/NativeStagedAiPanel.dom.test.tsx src/nativeStagedAi.test.ts --maxWorkers=1 --reporter=json --outputFile=<local report>
node node_modules/typescript/bin/tsc -b --pretty false
```

The adjacent `.first-fix-result.json` preserves 11/11 and `.final-result.json`
preserves 16/16; `.fixed.json` binds exact source/report hashes. The earlier
`.md`, `.first-result.json`, `.expanded-result.json` and
`.counterexample-result.json` remain the historical failure evidence.

A explicitly delegated this component repair to the internal helper. No
shared App/package/types/registers, frozen SQL, money/stock/HPP calculations,
permissions, workflow, remote branch, database or hosted environment changed.
The integrator must declare the one changed product leaf in its successor
source binding; historical B and AI9 manifests remain unchanged. Actual
desktop/mobile browser fallback and complete business-table/sequence no-DML
qualification on the final backend remain separate.
