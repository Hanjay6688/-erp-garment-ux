# D3 factory progress observation — isolated qualification only

VENI. VIDI. VICI. ERP. Reliable data adalah dewa.
Keuangan termasuk laporan, stok, dan HPP adalah raja.

Actual D3 d36685a2 remains INCOMPLETE. Six groups passed, including Native20,
all three complete report pairs and the real PostgreSQL 307.2MB streaming
regression. All seven installed restorations and the complete initial database
restoration passed. The final factory group stopped at its 300-second observer
cutoff: finance was READY, both analysis jobs were still RUNNING, and final
read-only diagnostics observed 86/97 and 87/97 units with no job failure.
The three recorded real minute cron invocations succeeded. This exact first
outcome does not qualify the unfinished factory group.

D17-18 allows large analysis to take longer while making real progress. This
qualification keeps every D3 backend file and complete data fingerprint byte
for byte. Only the factory observer changes. It reads both stored job counters
and the finance capture through default_transaction_read_only enabled on its
connection. It records progress and the first observation after the old
300-second cutoff; rejects regressing counters, failed/missing jobs, a RUNNING
member without progress for150seconds, or a total wait of900seconds. Both jobs
must actually be DONE and finance READY before the existing report,24metrics,
UNKNOWN,signatures,1200x3coverage,UUID,units-once,all-data and catalog checks.
No completion predicate is replaced by progress.

All original36factory,9outer-probe and14restoration-runner assertions remain.
The failed terminal assertion is compactly named; complete stored diagnostics
remain in the raw report. No page/test ticks,new schedule,progress writes,
money/stock/HPP rules,ordinary statement limits,B files,default installer or
public RPC change. Exact D3 Original/package bytes and its recomputed complete
source are required before database use. All7groups run again on the same
backend. Separate6group credit cannot unlock Auth/browser. Independent and
production acceptance remain false.
