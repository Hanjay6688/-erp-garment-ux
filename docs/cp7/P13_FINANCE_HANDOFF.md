# P13 dated financial report and immutable archive reader

CP6 remains CLOSED_CONTRACT_SCOPE. P13/F03 OPEN; independent_acceptance=false; production_go=false. This is a bounded writer candidate, not a completed close/recost/finance packet. Native qualification is pending; local DOM checks do not substitute for ledger or browser proof.

## Accepted source and implemented boundary

The unchanged accepted `erp.get_owner_financial_snapshot_v2(from,to,as_of)` supplies position and performance from dated journal balances and signed sale/return lifecycle events. `accounting_close_preflight_v1` supplies readiness from the same native engine used by accounting close, including its own completeness window. The reader does not replace that window with the selected income-statement start date. Existing report functions, posting, HPP, recost, closing and reopening business functions are not changed.

The connected **Laporan & Tutup Buku** entry in DISPOSABLE_TEST exposes explicit dates, current-corrected amounts, readiness blockers and information, optional close preflight, and complete paged native close filings. Selecting a filing reads its original saved readiness and signed GL balances, alongside the current-corrected dated report. UTC serialization makes the original filing hash stable across caller timezones. Late corrections must retain the accepted BA `changed_since_filing` marker even after recost is processed and readiness returns to READY. The archive itself is never rewritten.

The UI expressly distinguishes current recorded knowledge from information known at a past date. Supplier exposure is explicitly **current operational state**, including when the financial date is historical. It does not pretend to reconstruct historical supplier aging. Missing percentage denominators remain unavailable; they are not turned into zero. All native financial JSON numbers are converted to exact decimal strings inside PostgreSQL before parsing by JavaScript. The UI only formats them; it does not calculate financial totals or HPP. Incomplete or incompatible responses retire prior money, while edited date filters remain.

Current report permission and the accepted native OWNER/ADMIN restriction are both required. Custom-role permission alone deliberately does not bypass the native report boundary. Close preflight appears only with `finance.period_close.manage`; this candidate exposes no close/reopen/recost/payment writer. The private no-login read role receives only enumerated SELECT and native read EXECUTE rights, no ERP DML or native financial write EXECUTE. The public wrapper checks live identity/access and returns a bounded complete response, never a truncated blocker list presented as READY.

## Predeclared12-case qualification

| Group | Cases | Required evidence |
|---|---:|---|
| Native source | 8 | Sale80 → return20 → cash30 gives AR30/cash30/FG−30/revenue60/COGS30/profit30; cash never repeats income/HPP; inverse restores all GL/report amounts. Exact `9007199254741009.99` native invoice; invalid queries/access/private writer refusal; unchanged and late-corrected actual native filings; complete filing pages. |
| Concurrent transactions | 1 | While native cash30 is uncommitted, the reader sees the complete old snapshot; after commit cash+30 and AR−30 appear together, with unchanged performance. |
| Auth/PostgREST | 1 | Real owner source/dates/exact strings; anonymous and deactivated identity refused. |
| Browser | 2 | Desktop and mobile real Auth read native sale/return/cash amounts, select an original filed report, retain READY+late-correction marker, match every original GL balance, distinguish source dates/current supplier state, retire money on failed refresh, and leave GL/stock/filing untouched. Native fixture controls are not claimed as browser financial writes. |

The two browser cases share one prepared committed native source/archive; each reads and checks it without changing it. No mocked product financial response. Native fixtures and lifecycle commands are confined to disposable database copies. Evidence must retain the exact source SHA/tree, installed bundle hash, actual counts, CP6 restoration, advisor, Auth/database cleanup and package backup/restore gates. Current screenshots require inspection before any visual-review claim. Failed or unrun cases stay recorded, not converted into acceptance by a green workflow.

## Remaining P13 and F03 obligations

This increment installs on the explicit P09/P11 development stack. It is not yet a combined P09–P13 installation and does not prove P12 guard compatibility. Existing HPP source views, recost commands, financial writers, real close/reopen UI, exports and their complete packet obligations remain separate. E05 partial settlement still requires its accepted contract to be recovered/confirmed; no cash-installment policy is invented here. R10/P11 has its own64-case source qualification. F03 cannot close from this12-case reader proof alone; full integration, installation/restoration and auditor acceptance remain open before F04 takeover.

Original frozen packet/source references: `framework-v2/work_packets.json`, P00 native catalogue, accepted CP6 AW/BA report/close semantics. No framework or CP6 acceptance hash is rewritten.
