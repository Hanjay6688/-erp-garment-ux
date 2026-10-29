# Staged Tanya AI — directed local DOM controls, 29 October 2026

Status: **10 PASS / 1 reproduced product defect; not accepted.** This is an
internal writer check on synthetic fixtures, not Native, Auth, actual browser,
independent acceptance or a production authorization. No workflow or database
was started. The component and its SQL/permissions remain unchanged.

Base: `93a238d230eefedb052553c0e804b1ef320a2dc1`.
`src/NativeStagedAiPanel.tsx` SHA256:
`583def2cfd04607a9af2daf319b4d44c0cbd579f8dfc32de61a1f22645cfe4e4`.
New tests: `src/NativeStagedAiPanel.fallback.dom.test.tsx`.

The first single-worker run executes six new controls and the five existing
panel/parser tests: **11 total, 10 PASS, 1 FAIL, zero skipped**. TypeScript
`tsc -b --pretty false` passes. The second complete run adds observable stale
selection details to the same failing assertion, preserving its expected
behavior; it has the same 10/1 result. Both raw JSON reports are retained
unchanged in the adjacent `.first-result.json` and `.expanded-result.json`.

| New control | Observed |
|---|---|
| Clipboard denial preserves the full reviewed manual prompt; no false copied state or automatic external request | PASS |
| Long hostile question round-trips as escaped JSON; static manual link has no ERP query/hash; prevented navigation retains manual text | PASS, synthetic blocked navigation |
| Verified stale snapshot keeps its original WIB time, explicit stale state and UNKNOWN values | PASS |
| Current 401, provider identity still AUTHORIZED, retires previous manual text/link and copies nothing new | PASS |
| Current 403/42501, provider identity still AUTHORIZED, retires previous manual text/link and copies nothing new | PASS |
| Selected target changes while its old brief request is pending | **FAIL: stale response is published and copied** |

Counterexample: request target SKU-1; before its response resolves, rerender
the parent selection as SKU-3; resolve the valid SKU-1 brief. The screen says
SKU-3, but the manual prompt's `selected_targets` still contains SKU-1 and the
clipboard has been called once. Expected: the superseded request produces no
manual prompt and no clipboard call. The focused diagnostic run preserves
this exact observed object in `.counterexample-result.json`; it runs only this
case and reports one failure/five deliberately unselected tests, not six fresh
executions.

Cause from source review: the dependency effect clears text/message when run,
selection, question or finance changes but does not retire the request
generation. `prepare()` therefore still accepts the old response. Any product
repair must retire that generation and release its busy state without removing
the strict server/run/selection validation or altering the test oracle.

The passing controls prove local component behavior only. Actual desktop and
390px Auth/browser journeys on the final transitive backend still need the
clipboard/navigation fault witnesses and complete business-table/sequence
no-DML comparator. Physical owner-device evidence is distinct from mobile
viewport emulation. Existing AI9 and full-Native E206 witnesses retain their
original scope and receive no new execution credit from these tests.

No changes to the frozen base SQL, financial/stock/HPP calculations, production
permissions, shared registers, Library records or existing evidence were made.
`production_go=false`; `independent_acceptance=false`.
