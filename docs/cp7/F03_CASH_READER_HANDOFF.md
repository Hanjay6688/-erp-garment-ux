# F03 connected Kas & Bank — source-bound reader increment

CP6 CLOSED_CONTRACT_SCOPE; F03 OPEN; independent_acceptance=false; production_go=false. This extends the cash source UI in the disposable CP7 candidate. It is writer work, not independent acceptance or hosted deployment.

The Kas & Bank route previously rendered financeData simulation balances in the disposable candidate. It now reads the unchanged public `erp_cp7_get_finance_analysis_v1` source with the existing closed decimal/date/page contract. Saldo before/after, debit/credit/net, reconciliation and all paged journal sources come from the same native projection. No bank list is invented from fixtures, no page subtotal replaces a full-period amount, and a transfer is not labeled sales income. Original/reversed journals and their linked inverse follow their own accounting dates; economic dates and original document identities remain visible.

The existing server report boundary remains current `finance.reports.view` plus native OWNER/ADMIN. The route additionally needs `finance.cash.view` for navigation. It does not introduce a cash-only API or broaden custom-role access to the owner report. The existing financial reader retains no journal posting/ERP DML authority. No SQL bundle, native posting/costing rule, private role, source grant or historical filing changes in this increment.

All money remains exact strings. A fresh read clears the old snapshot first. Date edits and identity/permission changes retire pending responses. Failed page/network/403 reads remove every old amount and source row while keeping selected dates. Dates refer to recorded knowledge now, not reconstructed historical knowledge. This page provides recorded cash balances; it does not claim READY/full HPP or create a transfer/misc-finance transaction. Hosted/UAT activation and cash/misc-finance writers remain separate.

## Qualification declared before execution

Six native/HTTP/browser cases on the existing combined26-role stack, using the unchanged30-file accepted package. The fixed worksheet uses a native internal transfer1000 (net0), actual customer receipt300 and supplier payment200, then30 native capital journals1.25 each. Result: cash delta137.50, debit1337.50, credit1200.00,33 cash-source journals across25+8 rows. Both pages must preserve full totals and all33 source identities must match native rows exactly.

| Group | Case and proof |
|---|---|
| Native3 | Fixed O14 worksheet/full33-source pages and whole read-only boundary; original next-day linked payment/transfer inverse; current native report role/private reader/no-journal-write controls |
| Actual Auth/HTTP1 | Both pages exact under real OWNER session; anonymous and current deactivation403 refused; read does not change business facts |
| Actual browsers2 | Desktop OWNER/mobile ADMIN navigate actual Kas & Bank, select the source day, read25+8 rows/full amounts; desktop network failure and mobile real report-permission403 clear old money/rows; source facts unchanged |

Cash source journals are prepared through inherited native journal/payment primitives only in disposable fixture databases. Browser makes real Auth/public read calls. Desktop and mobile share one prepared source fixture, avoiding duplicated capital/sales sources. Source/guard/admission/ACL, CP6 restoration, advisor, unchanged primary, package installation/backup recovery, Auth/database cleanup and inspected actual screenshots are required before qualification. Read workflow logs/reports, not just green job color. Full E13/E14/E20/family or cash-writer acceptance is not claimed.

Local targeted cash7 + retained analysis8/report8 =23 PASS. Build, TypeScript, source/access/CSS ownership and client secret scan pass; the separate63 shared recovery cases also pass, giving86 local cases on this source. [Full local report/build and hash receipt](evidence/f03-cash/LOCAL_WRITER_RECEIPT.json). Counts are local UI/recovery checks, not native business executions. [First local setup assertion](evidence/f03-cash/LOCAL_SETUP_FAILURE.json) preserves22 PASS/1 FAIL: the fixture filled the unchanged default date, so its expected date-change event never occurred. The repair derives a genuinely different date and keeps the same no-old-money assertion. No product guard or money oracle was weakened. Native/HTTP/browser result is pending and must bind the actual source SHA/tree/artifact.

**Keuangan (termasuk laporan), stok dan HPP adalah raja. Reliable data adalah dewa.**

## First actual qualification, retained without rewriting

Source c618f8402e7a89a5aa25993225831cd57f68b663, tree6ef1e940f57999ce0f7e2099eb78feae50989b30; run36690460505/job109806177247:4 PASS/0 FAIL/2 INCOMPLETE/0 NOT_RUN. All three native cases and actual Auth/HTTP pass, including the exact33 sources,137.50/1337.50/1200.00 worksheet, next-day linked inverse and server authority. [Complete original reports and receipt](evidence/f03-cash/FIRST_RECEIPT.json).

Both browsers reach their25+8 source pages and fixed amounts, then the disposable full-page comparison helper stops at Linux E2BIG: a single argv payload is larger than its per-argument limit. Full response validation and failed-read/403 completion are not yet proved. The fixture adapter now passes the entire JSON through stdin, retaining the16MiB complete-result cap, every row/money/date comparison and both stale-data assertions. Product/native SQL and money/permission behavior are unchanged. Full six-case qualification remains pending.

CP6/advisor,30-file installation, backup restoration, unchanged primary and Auth/database cleanup pass; overall writer gate correctly remains false for this interrupted run. Same-source combined22 and Shell build/security/CodeQL jobs pass separately. Their counts are not added to the cash6; no new screenshot review is claimed from this interrupted run.
