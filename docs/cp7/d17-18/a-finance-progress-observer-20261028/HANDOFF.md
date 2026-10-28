# A finance progress observer — prepared successor

VENI. VIDI. VICI. ERP — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.

The A-owned finance panel previously polled an unchanged RUNNING capture forever.
It now pauses automatic observation after 150 seconds without observed financial
progress and explains how to read the same request again. This does not cancel,
fail, restart or save a server job. No result is delayed and no progress value is
invented. Unknown totals remain unknown; unready or revoked figures stay hidden.

The local observation window uses monotonic time. Real completed units, the first
known total or the first report-read time renew it. Equivalent rerenders and
repeated responses do not renew it. Manual reload starts a fresh observation of
the same UUID. Existing freshness, binding, access and late-response checks remain.
The window covers two opportunities for the existing minute schedule, the bounded
16-second initial step and read margin. It is an observation bound, not a new
backend SLA or a change to its 8/16-second transaction limits. D17-18 permits this
technical choice; it does not change any business policy.

Only `src/NativeAnalysisFinancePanel.tsx` changes runtime behavior. The new
`src/NativeAnalysisFinancePanel.progress.dom.test.tsx` adds four controls. Exact
local Vitest results, typecheck and ownership receipts are retained beside this
handoff. These are unit/DOM fixture tests, with zero actual ERP/Auth/browser cases.

A remains owner of this panel and backend contracts. B owns its production driver
and the combined browser candidate. B's current driver also has no explicit
no-progress exit in `driveStagedJob`; B must cover D17-18's finite observation and
safe recovery when adding the prepared `55000` large-initial-step handling.
Do not confuse the qualification observer's 900/150-second limits with a production
client bound already implemented. A does not patch B's driver or run B's browser.

The old readonly qualification SOURCE pins the previous A panel. It remains intact.
This is an explicit frontend successor, not evidence that historical browser or
Native tests ran this new UI. B must bind the exact A panel successor in its new
host-source declaration and retain the backend qualification on its exact frozen
source. Main's scoped backend/tooling source bridge explains that separation.
No old manifest is rewritten and no old JS/UI bytes are silently substituted.
Backend11c is still awaiting its complete all7 result; no browser gate is opened.

Prepared only: no default/official adoption, production_go=false,
independent_acceptance=false, formal5/16, CP7C not started.
