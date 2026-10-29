# Parent blocking-read retirement — local closure

Writer result: **17/17 local tests PASS, zero skipped; full typecheck PASS**.
The first-failure test and raw report from commit
`04084a22210dbf05b0dba95df355d6f2b5b8c22e` remain unchanged.

The parent `blocked` prop is an eligibility context: the real parent sets it
during page/source reads and other workspace holds without necessarily
changing the run or selected target. The repair adds `outer` to the existing
layout retirement dependencies. On a hold, the request generation and old
prompt retire before paint; the button remains disabled. Clearing that hold
does not revive the old response. The new regression requires another trusted
click and fresh brief before a prompt may be shown or copied.

This changes one dependency in `NativeStagedAiPanel.tsx`, not the parser,
backend, permission model or payload. Source SHA256:
`2d9927ce77fea8f886da1106f0cb1629eeb4b60579bdd3d624765d9b9ca8ebde`.
The exact result is retained as `.blocked-fixed-result.json`. Earlier 10/1,
11/11, 16/16 and blocked-parent first-failure reports are historical and intact.

The command remains the three-file single-worker Vitest run in `.fixed.md`,
plus `node node_modules/typescript/bin/tsc -b --pretty false`. All original
sixteen tests and the newly failing parent-block oracle pass without loosening
an expected result. This is local synthetic DOM evidence, not actual Auth,
browser, Native, independent acceptance or production GO. No remote, workflow,
database or hosted action occurred.
