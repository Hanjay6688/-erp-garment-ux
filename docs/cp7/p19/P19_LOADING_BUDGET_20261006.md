# Owner loading budget:1s reads,2s ordinary saves,3s complex work

Owner instruction on6 October2026 WIB: ERP should feel light; ordinary figures should load in under1 second. The owner then supplied Claude's more precise1/2/3-second breakdown below and required named background exceptions. Treat this as an engineering acceptance target for P19, not a claim that the current ERP or every possible network already meets it. There is no general5-second allowance.

Measure from the operator's click/navigation/refresh until current authorized numbers are completely visible and usable. Include request scheduling, network, server/SQL, transfer, parsing, state updates and rendering. A spinner disappearing, stale cached numbers, partial body or skeleton does not end the measurement. When loading is triggered by a write, show confirmed success only after its actual commit and required readback; report command and read phases separately as well as their combined visible completion.

| Predeclared journey class | Target | Evidence needed |
|---|---|---|
| Routine fresh figures, filtering and opening a page | Every declared observed sample `<1000ms` | Actual Auth/browser, current facts/authority, request+render timing, raw response bytes and complete correctness readback. |
| Ordinary transaction save | Every declared observed sample `<=2000ms` | Click→actual committed result and required current readback; UUID, lock, authority, one-effect and full money/source checks remain exact. |
| Period report, year-back correction, recalculation or import of hundreds of rows | Every declared observed sample `<=3000ms`, with progress | Entire declared scope available, exact quantities/costs/money/dates, required completeness, no silently dropped rows. |
| Named background exceptions: shadow run, installation, full-year snapshot rebuild | May exceed3s only as a background job | Screen stays usable; actual status such as `Sedang dihitung sejak jam X`, exact job/request identity, honest progress, reload/recovery and final result. |

A process that measures5 seconds cannot pass by redefining the common ceiling. Investigate its slow phase and, if justified, implement a specifically named background job with visible state. Being asynchronous does not itself award latency or correctness acceptance. The year-back Note correction is a **candidate exception requiring investigation first**, not a newly approved background implementation; preserve its existing8s statement timeout while finding the cause.

For background jobs, first visible acknowledgement/status must fit the normal read/page responsiveness target. Preserve exact actor/UUID/payload/source identity across reload and retries, current authority at execution and delivery, one committed effect and immutable final Originals. `Queued`/`running` does not mean a financial write succeeded. Failed, revoked, stale and interrupted jobs keep explicit status and owning recovery; do not manufacture percentages or auto-retry an unknown write. An operator must never face an unexplained blocked screen beyond3 seconds. The listed installation category does not authorize a hosted deployment.

Declare journey classes and data/network/device conditions before qualification. Report cold first use, warm use, refresh and concurrent readers plus a real writer separately. Preserve every sample and maximum; p95/p99 are useful diagnostics and do not replace the owner's ceiling or erase a slow sample. CI fixture setup, package installation and audit-suite duration are not operator loading time. A fixed hard guarantee over an undeclared or interrupted internet connection cannot be inferred from a finite benchmark.

## Actual current baseline, not whole-ERP acceptance

Fresh source8f326d87 Native6 Originals have been read per case and retained at `../evidence/integration-8f/p19-native-load/`. Full public captures of actual0/1/4/12 factsets take439.431/541.201/634.575/939.893ms; complete analysis bodies are28,027/157,793/294,370/659,117 UTF8 bytes. Four concurrent actual Auth captures reach1354.327ms. These are complete backend/HTTP observations, **not click-to-render browser measurements**, and the12-factset fixture is not factory-wide capacity.

The isolated5000-target analysis kernel previously took about13.15 seconds and emitted30,970,077 UTF8 bytes. It uses explicitly declared stand-ins and does not prove a real installed5000-target user flow. The actual committed historical Note364 HTTP path also has a retained bounded observation above3 seconds (source07ddb3db,6211.86ms command/7108.019ms complete HTTP); that is an open performance gap, not a reason to weaken its exact historical oracles or raise its8s timeout.

Record the fresh baseline separately in `../evidence/integration-8f/p19-native-load/OWNER_LOADING_BASELINE.json`. These captures do not yet qualify the1s/2s/3s browser targets or a named background exception. Prior correctness qualification remains intact; new latency acceptance is **OPEN**.

## Implementation direction and unfinished work

First profile real routine read paths and complete heavy paths with phase timings. Optimize repeated SQL/work, indexes and server-side aggregates; send only the complete information required for that particular screen. Virtualized display or visual pagination cannot by itself fix an oversized mandatory complete-source transport.

For analysis/reminders retain `P19_COMPLETE_SOURCE_CAPACITY.md`: bounded complete assembly, actor/run/scenario identity, row/byte/hash totals and current authority for each segment. Missing/duplicate/mixed/stale segments refuse action. Never make a selected subset look like a complete factory decision. Separate immutable historical Originals from live refreshed balances. Cache only with explicit freshness/source/authority invalidation; zero-effect replay and lost-reply recovery remain exact.

Do not increase body limits/timeouts or remove stock/HPP/GL/debt/cash/UNKNOWN checks to obtain a fast number. User business policies and planning fallback values remain separate from this latency target. Full P19, factory capacity, browser latency, many-user loading, complete-source transport and production SLA remain unqualified.

## Recorded background exception — owner decision 7 October 2026

Owner (item 5): "Latensi: pekerjaan berat boleh berjalan di latar belakang sebagai pengecualian yang dicatat. Layar tetap responsif, status/progres nyata, aman ditinggal dan dibuka kembali. Jangan menandai target selesai 3 detik sebagai tercapai kalau memang belum."

| Field | Value |
|---|---|
| Exception id | `P19_PLANNING_ANALYSIS_BACKGROUND_20261007` (declared in `P19_SCALE.json` → `owner_latency_targets.background_exception`) |
| Journey | Analisis, laporan & pengingat seluruh produk → "Hitung di latar belakang" (`erp_cp7_request_operational_analysis_job_v1` / `erp_cp7_request_analysis_job_v1`, `erp_cp7_run_analysis_job_v1`, `erp_cp7_get_analysis_job_v1`, manifest + segments) |
| Screen responsive | First visible acknowledgement is measured against the 1 s routine target (`first_visible_acknowledgement`); the panel never blocks other views. |
| Real status | Server job state: requested/started time ("Sedang dihitung sejak jam … WIB"), WAITING/RUNNING/DONE/FAILED, attempt number, failure code; segment progress "bagian x dari y" comes from the server manifest. No manufactured percentage. |
| Safe to leave and reopen | Request UUID and finance mode persisted before sending; on reopen the panel reads the server job, waits on a held worker without starting a second one, and continues the same UUID. Proven by `P19T_BROWSER_DESKTOP_RELOAD_RECOVERY`, `P19T_RACE_*` and the DOM recovery tests. |
| Completeness | Complete Original or an explicit refusal (declared cap or the unchanged 8 s statement limit). Nothing is sampled, truncated or raised. |
| Not awarded | The 3 s heavy-complete target for this journey and owner latency acceptance. The scale suite keeps reporting `complete_or_refusal_rendered` against 3 000 ms as measured (e.g. run 8: 100 targets 7,2–9,0 s → not met), and `owner_latency_acceptance` stays `false`. |

Staged processing for 5 000 targets (owner item 3) runs under this same exception once implemented; its stage progress must also come from persisted server state.
