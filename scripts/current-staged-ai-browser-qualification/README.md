# Staged Tanya AI: prepared real-Auth desktop/mobile cases

Status: **PREPARED**. Local plan/oracle tests are executable, but this package
has not run Native SQL, Auth, PostgREST, a browser, CI, or hosted infrastructure.
It provides two additional internal writer qualification cases. It does not
give independent acceptance, release evidence, CP7 completion, or production go.

The input product fix is `4827530938a9cba85cbde8bff896acab6713c72e`:
`NativeStagedAiPanel` retires an outstanding handoff before painting a changed
selection or parent source hold. The retained DOM first failures and unchanged
regressions remain in `docs/cp7/d17-14/ow15/ai-fallback-local-20261029.*`.
No product component, shared App, installer, Auth host, runner, workflow, or
shared source registry is changed by this package.

## Existing runtime hooks

The integrator first supplies the complete current Native install and full
restore verification, with successful actual Native gates. Then call the
existing `scripts/cp6_auditor_modes.py::run_browser` with the absolute path to
this namespace's `cases.mjs`; use the existing
`scripts/cp6_auditor_browser_host.mjs` unchanged. Do not execute the case module
as a standalone server. Its `cases(ui, today)` export returns only these two
closures and performs no fixture/Auth operation during planning:

| Case ID | Host login and viewport |
| --- | --- |
| `A_STAGED_AI_BROWSER_DESKTOP_MANUAL_AND_RETIRED_RESPONSES` | OWNER, 1440×1000, Asia/Jakarta |
| `A_STAGED_AI_BROWSER_MOBILE_MANUAL_AND_RETIRED_RESPONSES` | OWNER, 390×844, touch/mobile, America/Los_Angeles |

The host supplies `ui.origin`, `ui.api`, `ui.login`, `ui.expect`, its business-day
checks, network allowlist, real Auth provisioning/login, ordinary public Native
RPCs and final cleanup. Keep `AUDITOR_UI_MODE=DISPOSABLE` and the normal full App
build: B's `build_3194.mjs` custom quantity/finance panel does not render Tanya
AI. No alternative Auth server, runner, fabricated token, custom UI build, or
private financial-step shortcut is added here.

`fixture.py` requires the host's `AUDITOR_BROWSER_DB_URL`, whose literal URL
must be the loopback `/cp6_auditor_browser` copy, and the integrator's explicit
`D17_18_SELECTED_BACKEND_ROOT`. That selected installed backend must contain:

* `scripts/current-frozen-public-native-qualification/public_finance_cases.py`
  and its retained imports;
* `scripts/cp7_ow04_restore_bundle.py` and its retained owning-install imports;
* the ordinary staged analysis, AI brief, pages and source-check Native functions.

Fixture operations are:

| Operation | Purpose and side effects |
| --- | --- |
| `plan` | JSON PREPARED plan, no environment, imports of Native modules or connection |
| `prepare` | Reuses B's small `native.setup`: `staged.analysis.setup` plus `finance.given`, ordinary retained Native fixture writers; temporarily required fixture-only ERP schema usage is restored exactly before commit |
| `state` | Entire unfiltered catalog `_data` census, all row count/hashes and all sequence states; full source-check rows for exact append verification; rolled back |
| `read` | Independent permitted public brief/page read under the browser actor on the copy, no invented HTTP identity; rolled back |

`prepare` creates business **fixtures**, including real fixture finance postings;
it does not create a screen, an analysis job or an expected financial result.
The actual logged-in browser opens the normal Barang Jadi → Data permintaan
ERP → Analisis ERP bersama path, selects the fixture query, starts its own
bounded staged run and chooses actual table targets. The finance checkbox
stays unchecked. A missing second visible target is a concrete runtime failure,
not a reason to fabricate a recommendation or silently skip a race.

## Observations required in each case

1. Read a real permitted staged brief, bound to the browser actor/run/selected
   keys. Compare the manual prompt's totals, top priority rows, selected rows,
   decimal strings, null unknowns, freshness and dates exactly to that actual
   answer and an independent Native/page readback. No whole-document reader
   or owner finance report is requested for the handoff.
2. Reject only `navigator.clipboard.writeText` with `NotAllowedError`. Its full
   attempted text must equal the read-only selectable manual textarea. The
   complete long hostile question, including closing tags, quotes, backslash,
   newline and final sentinel, remains one JSON string with escaped angle
   brackets. No injected element executes and no successful-copy status appears.
3. Verify exactly `https://chatgpt.com/`, `_blank`, `noopener noreferrer`; no
   query, fragment, payload or question in the href. A one-shot browser click
   veto models blocked external opening. The manual text remains complete,
   no new page opens, and no AI/provider request or automatic send occurs.
   This is deliberately a browser fault injection, **not** proof of a provider
   outage or actual provider availability.
4. Hold delivery of the actual successful brief for target A. Change selection
   through the real table from A to B, then deliver the unchanged response.
   It must neither publish manual text/link nor attempt clipboard. A new trusted
   click must load B and recover manual copy normally.
5. Hold another actual brief; click the real `Cek sumber` button and hold its
   actual answer. While the parent source check blocks the AI panel, deliver
   the unchanged old brief. No stale publish/copy is allowed during the hold
   or after releasing it. A new click must obtain a fresh checked manual prompt.

Holding responses changes only delivery order: `route.fetch()` reaches the
real permitted Native server; `route.fulfill({response})` forwards that same
response object. Status, body, headers, clocks, permission results, facts and
financial values are never mocked or replaced. Each discarded response's
original body hash and contents are retained in runtime evidence. These
deterministic delays and the navigation veto are declared separately from
the clipboard-denial fault.

## Exact change boundaries and quiet source

Take two identical complete catalog censuses **after** the logged-in browser's
run has completed and before AI actions. AI reads/copy/navigation/selection
must leave the entire unfiltered census exactly identical. It includes every
table and sequence returned by the owning catalog helper, including all CP7
business namespaces, not five monetary tables or only ERP/public. Built-in
catalog-helper scope still excludes system schemas and cron; this package
adds no ignored schema or key.

`Cek sumber` intentionally writes one audit row. In this second phase the only
permitted differences are `cp7_analysis_stage.source_checks` and
`sequence:cp7_analysis_stage.source_checks_id_seq`. Require the exact original
rows followed by one new row, the same browser actor/run, `UNCHANGED`, the
actual answer's checked timestamp/boundary, and exactly one identity allocation
including the initial `is_called=false` case. Every other row count/hash,
sequence and key must be identical. This is **not** absolute no-DML across all
schemas. A final identical census verifies the source remains quiet.

The owning disposable runtime must keep business writers/schedulers quiet
during these comparisons. Do not grant a test bypass, ignore an unexpected
Auth/business/metadata change, normalize it away, or retry until green. A
timeout, source change, signature mismatch, unexpected permission refusal,
console error, external request or census change stays a failure/incomplete
with originals. The integrator still owns complete install/Auth restore and
source binding; these cases do not substitute for that evidence.

Runtime outputs go through the existing host and `cp6-proof/t3/`:
`A_STAGED_AI_{DESKTOP,MOBILE}_EVIDENCE.json`, three screenshots per case and,
on failure, the original failure JSON/screenshot. Case return values report
PASS only if actually reached by that runtime; this checked-in plan remains
PREPARED until the integrator records the real run.

## Local checks, without Native/Auth/browser execution

```sh
node --test scripts/current-staged-ai-browser-qualification/plan.test.mjs
python scripts/current-staged-ai-browser-qualification/fixture_plan_test.py
python scripts/current-staged-ai-browser-qualification/fixture.py plan
```

These check planning, exact source hashes, forwarding unchanged response
objects, and adversarial oracle controls for lost text, changed facts,
unknown-to-zero, changed CP7 credit rows, missing tables, sequence leaks,
extra audit appends and wrong actors. They do not confer browser PASS.

First local plan run: 6 passed, 1 failed. The synthetic oracle control shared
one JavaScript object between priority and selected arrays, so mutating the
selected row correctly failed the priority assertion first. The fixture was
corrected to give those arrays separate objects, as actual JSON parsing does;
the exact selected-row negative assertion and product oracle were retained.
This was a local test-fixture defect, not an actual Native/browser failure.
