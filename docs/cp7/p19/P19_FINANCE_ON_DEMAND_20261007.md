# P19 finance on demand — 7 October 2026

Owner decision (7 Oct 2026, item 2): "Data keuangan: pilih dimuat saat diperlukan. Layar stok/perencanaan yang tidak membutuhkan angka keuangan jangan ikut menunggu seluruh buku besar. Perhitungan yang membutuhkan keuangan tetap wajib memakai sumber valid; data belum tersedia jangan dianggap nol."

## What changed

| Layer | Full path (unchanged behaviour) | Operational path (new default of the stock/planning panel) |
|---|---|---|
| Public capture | `erp_cp7_capture_analysis_v1` → `capture(q,id,'INCLUDED')` | `erp_cp7_capture_operational_analysis_v1` → `capture(q,id,'DEFERRED')` |
| Public job request | `erp_cp7_request_analysis_job_v1` → `request(q,id,'INCLUDED')` | `erp_cp7_request_operational_analysis_job_v1` → `request(q,id,'DEFERRED')` |
| Source | `source_for(q,'INCLUDED')` = the existing `source(q)` (owner report + all-book provenance scan for OWNER/ADMIN with `finance.reports.view`) | `source_for(q,'DEFERRED')` = `source()` plus `financial_source: null`, `financial_capture: 'DEFERRED'`; never calls `financial_source`, never reads `journal_lines`, `account_daily_balances`, `cash_accounts` |
| Later reads (`serve`, `manifest`) | compare with `source(q)` as before | `finance_mode(r.facts)` keeps the run on the same operational-only source, so a ledger change does not stale it and no ledger is read to check it |
| Result | unchanged; finance metrics, readiness and dependency as before | the existing no-finance shape: no IDR metric, `financial_readiness=BLOCKED`, `quality.financial=UNKNOWN`, warning `FINANCIAL_DOMAIN_NOT_CAPTURED` — exactly what an operations-only actor already receives |

One request UUID is one request: the same query **and** the same finance mode. A capture, job request or job run that meets a run or job of the other mode on the same UUID refuses with `CP7_ANALYSIS_REQUEST_CHANGED` (a job fails rather than adopt a mixed result). Only `INCLUDED` and `DEFERRED` exist at every private entry (`CP7_ANALYSIS_FINANCE_MODE`). The private three-argument functions are not executable by `anon`, `authenticated` or `service_role`; the two new public RPCs are `authenticated`-only, owned by `cp7_capture`, `SECURITY DEFINER`, `search_path=''`, like their siblings.

The demand-history source still reads the journal **headers** of sales and returns (their posting state is an operational fact). That is not the books: no journal line, balance or cash account is read on the operational path.

## Panel

- "Ambil analisis ERP terbaru" and "Hitung di latar belakang" use the operational path unless the owner ticks **"Sertakan angka keuangan (menunggu buku besar)"** (shown only with OWNER/ADMIN + `finance.reports.view`).
- A result without financial figures, for an actor who may see them, says: "Angka keuangan belum dimuat pada hasil ini, jadi stok dan produksi tidak menunggu buku besar. Keuangan dan HPP tidak dianggap nol." and offers **"Muat angka keuangan"**, which runs a new full capture (new UUID) through the unchanged full path.
- The stored request (ordinary and background) keeps the mode it was sent with, so a retry or a reload continues on the same path. A stored request from before this change has no mode and is retried on the full path it was sent on.
- An operational-only reply that carries financial figures is refused by the client.

## Proof added

| Where | What it proves |
|---|---|
| `P19T_FINANCE_DEFERRED_NO_BOOK_READ` (Native) | Operational capture, serve, job request/run, manifest and every segment add **zero** scans to `journal_lines`, `account_daily_balances`, `cash_accounts` (transaction counters); the full capture under the same counters adds scans to all three (positive control). Not loaded is UNKNOWN/BLOCKED, never zero. Operational rights alone still read the operational run; the full run still refuses without the report permission. Business tables unchanged. |
| `P19T_FINANCE_MODE_IDENTITY` (Native) | One UUID one mode across capture and job; same-mode UUID adopted; other-mode run fails the job; only two modes; no API path to the private functions. |
| `P19T_HTTP_FINANCE_ON_DEMAND` (real Auth/PostgREST) | Operational capture and job without finance, full capture still with the owner report, mode change refused, anonymous refused. |
| `P19T_BROWSER_FINANCE_ON_DEMAND` | Default click calls only the operational RPC, the panel states "belum dimuat" and shows no Rp; "Muat angka keuangan" calls the full RPC and shows the owner report; two runs; business unchanged. |
| DOM and unit tests | Default RPCs, finance checkbox, remount continuation of a background request with finance, legacy stored request on the full path, refusal of a finance-bearing operational reply, storage validation of the mode. |
| P19 scale | Third browser control `CAPTURE_WITH_FINANCE`; `finance_path_matches_control` check per click. CAPTURE/BACKGROUND now measure the operational default (runs through `a68abf1e` measured the full capture). |

Existing browser flows that assert the owner report through other readers (analysis, AI, attention, episode, history, payable, policy, receivable, E01 bridge) now tick the finance choice explicitly, so their oracles are unchanged. Flows without a financial assertion (material, plan, fabric physical/recipe, rule, P18 fabric rule, publication, obligation report, other obligations) now run on the operational default.

Local runs on PostgreSQL 16 (`LOCAL_PG16_DEV`) are development checks only; CI results are recorded in `SELF_CHECK_FORMULAS_20261006.md` §6.

## Not changed / still open

- The full path, its oracles and its all-book provenance hash are unchanged. Loading financial figures still waits for the books; that wait is now explicit and only when chosen.
- `production_go: false`. No owner latency target is claimed by this change.
