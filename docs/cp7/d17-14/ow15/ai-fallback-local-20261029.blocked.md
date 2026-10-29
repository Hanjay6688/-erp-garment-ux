# Staged AI — parent blocking-read counterexample

First failure on product fix `51a6af7e9cb6c135d2ba0c2e7113454bce96fbe1`:
`NativeStagedAiPanel.tsx` SHA256
`3273b0f38425cf28b236a856335ba9061dfdee70bf738e95434b941aaee5773b`.
The focused synthetic DOM run executes one new case and fails; eleven other
fallback tests are deliberately unselected, not fresh PASS.

The actual parent passes `blocked=true` while staged-page loading or a source
check is in progress, without necessarily replacing/unmounting the staged AI
panel (`NativeAnalysisPanel.tsx` loadPage/checkStagedSource and its AI props).
Start a brief, rerender with the same run/selection but `blocked=true`, then
resolve the old valid brief. The button is disabled, yet the response still
creates manual text and issues a clipboard call. The expected oracle requires
no prompt/copy; after the parent clears its hold, a new trusted click and fresh
brief are required. Merely disabling the button does not retire in-flight work.

The `.blocked-first-result.json` file retains the exact failed report. This is
local internal evidence with RPC/clipboard doubles, not an actual Auth/browser
or Native result. Earlier first-failure and 16/16 local closure reports remain
unchanged. No database, workflow or remote action was performed.
