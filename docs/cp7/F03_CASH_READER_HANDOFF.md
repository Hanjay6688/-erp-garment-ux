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

## Completed retest recovered by the successor

The previously pending stdin retest completed successfully on **3c825db217d3a495ba263cf47d1d10d05b8a8392**, tree **f0ab6fcf1dbccf9bf2b4891f2247e3a73688a933**. [Run36691431985](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36691431985), job109809313667: **6 PASS,0 FAIL,0 INCOMPLETE,0 NOT_RUN** (native3,actual Auth/HTTP1,actual browsers2). Product source remains c618f840; the stdin correction changes test transport, not native money/date/Auth behavior. SQL bundle remains fbc874b151086dd38d5149062cb5b9a2d11d63714d1f199b43d67f989884dc61.

The successor downloaded artifact11085772495, checked its exact SHA256 de0dd3569e7d905211ae0417a61f9fe461ad8b445eec47e4e222fbb83d368afd, and checked complete case results and installation/restoration/advisor/current-access/cleanup gates. [Qualified receipt](evidence/f03-cash/QUALIFIED_RECEIPT.json) and [complete original JSON reports](evidence/f03-cash/QUALIFIED.json.gz) retain the source identity. Six actual source-bound desktop/mobile captures are retained losslessly with original/file/pixel hashes; their header, pagination and retired-data boundaries were visually inspected. This is recovery and verification of the inherited writer run, not a new or independent execution.

The fixed native33-source worksheet and complete25+8 HTTP/browser rows match exactly: debit1337.50,credit1200.00,net137.50,prior1000.00,after1137.50,reconciliation0.00. Native original/linked inverse dates are preserved. Desktop network failure and mobile actual permission403 remove every old amount and source row. No business writes from reads, no leaked sessions/Auth identities, primary unchanged and CP6 restored. The package writer gate is true for this six-case retest; this does not grant whole-family acceptance.

The separate [combined regression receipt](evidence/f03-combined/cash-route-regression/QUALIFIED_RECEIPT.json), run36691431972/job109809313834 on the same3c825db, retains **22/22 PASS**: native10,races2,HTTP4 and six browsers. It is an overlapping regression, not22 more cash cases. No fresh visual review of its captures is claimed.

The retest interruption is resolved. F03 remains OPEN: cash/misc-finance transaction writers, the explicit E05 partial-settlement contract, paid-return/refund continuation and remaining cross-flow/independent acceptance are recorded in [the contract ledger](F03_REMAINING_CONTRACT.md). No hosted deployment or production authorization.
