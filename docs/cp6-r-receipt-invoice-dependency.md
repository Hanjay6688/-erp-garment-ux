# CP6 R — Receipt/invoice dependency

Independent Q audit found one P2 backend defect, COMP-Q-R01. A posted
receipt can be reversed while a posted supplier invoice still references
its items. A receipt of 1 unit at 10,000 followed by its full invoice leaves
AP 10,000 and GRNI -10,000 after receipt reversal, with zero stock and
inventory. The report becomes BLOCKED. The invoice inverse then rejects
the source receipt because it is no longer POSTED. Partial invoices,
multi-receipt invoices, and one remaining active invoice reproduce the
same missing dependency guard.

The receipt reversal is an existing SECURITY DEFINER backend function
with owner/admin enforcement. These reproductions use owner claims in a
trusted SQL session. An authenticated HTTP or UI route to that function
has not been demonstrated; R does not add grants or a new public facade.

R changes three functions. Receipt reversal now refuses active supplier
invoices under its existing receipt row lock. Invoice posting already
takes that same lock and validates source state before committing. The
new guard reads invoice dependencies without taking invoice header locks,
preserving the invoice writer's lock order. A dedicated financial truth
check detects posted invoices referencing receipts outside POSTED, and
the main report includes that check.

The 13-case oracle covers four harmful document sequences, a privileged
detector replay, and eight controls: invoice-first reversal, reversed plus
draft invoices, stale draft posting, direct-final receipts, repeat reversal,
and existing payment/return/cost-correction dependency refusals. All checks
compare document, journal, stock, audit and posting-fact boundaries. The
upgrade refuses four unsafe histories without mutation; nine safe end
histories may upgrade. No posted business data is silently repaired.

Two native PostgreSQL schedules exercise invoice-post-first and
receipt-reverse-first using separate backend sessions. Each contender
must visibly block on the real writer's natural lock, then reject without
changing the winner's business boundary. There are no manual prelocks,
function replacements, trigger gates or retries in these race paths.

Q's published migration and rollback remain byte-for-byte intact. R pins
three exact predecessor/installed definitions, owner and ACL sets, and a
68-table pre-use boundary. The reviewed maintenance executor closes
admission and drains old sessions before an exact R-to-Q rollback. R uses
the canonical FG_HPP_SALES_V2620C advisory key; the historical Q rollback
contains an incidental spelling drift, without a demonstrated additional
admission bypass. That observation is not counted as a second finding.

All prior runtime evidence remains connected through Q-to-R successor
bindings. The maintenance matrix covers 13 generations × 5 backend paths
× 4 schedules = 260 schedules, with 65 backend body entries. Those are
rollback schedules, separately reported from the 13 R business cases and
two receipt/invoice race orders. CI requires exact SHA/source bindings,
all inherited suites, rollback, final reconciliation and physical cleanup.

Writer verification and independent acceptance remain separate verdicts.
`production_go:false`; DO NOT MERGE.

Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
