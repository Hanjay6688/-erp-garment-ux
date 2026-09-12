# CP6 Q — Exact supplier invoice quantity

P admits an invoice one stored quantity step above its receipt capacity.
For a receipt of 1 unit at 10,000, an invoice for 1.000001 posts AP of
10,000.01 and an extra 0.01 variance; physical stock remains 1 and the report
stays READY. With 0.999999 invoiced instead, 0.01 remains in GRNI but P
reports MATCHED/FINAL. The same boundary survives split invoices,
return-adjusted capacity, and reversal of the final micro-unit invoice.

This is one P2 quantity-conservation finding with overbilling and premature
completion variants. The database stores these quantities as numeric(18,6).
Their addition and comparison are exact: an extra 0.000001 is a stored unit,
not floating-point noise. See [PostgreSQL numeric types](https://www.postgresql.org/docs/17/datatype-numeric.html).

Q changes four functions:

- The supplier invoice posting guard rejects any quantity above current
  capacity under the existing deterministic purchase/item locks.
- The match-state refresh keeps every positive unmatched remainder PARTIAL.
- The financial truth checks use the same exact capacity and state rules.
- The main report includes the invoice-over-receipt detector.

The shared 11-case SQL oracle runs before and after Q. Seven P counterexample
paths and four controls prove exact/split completion, one- and two-step
overflow, return-adjusted capacity, reversal, identical-request replay,
atomic refusal, money/stock conservation and detector/report agreement.
Two detector cases deliberately replay a preserved P function in a rolled
back tester subtransaction. They are privileged fault injection, not a claim
that an operator can replace a database function. V2 posting is exercised
with owner claims in a trusted SQL session; real Auth transport remains a
separate native gate.

All 11 end histories undergo upgrade qualification: five invalid histories
must be refused without business or runtime residue; six valid histories
may upgrade. Q does not rewrite pre-existing posted business data.

Q preserves the published P SQL and its evidence. Its capsule pins four
predecessor/installed definitions, owners and ACLs, with a 67-table pre-use
boundary. Rollback to P requires independently verified source pins,
closed database admission, drained old sessions and exact restoration.
The inherited maintenance matrix becomes 12 generations × 5 backend paths
× 4 schedules = 240 schedules, with 60 real backend body entries. Those
numbers describe rollback schedules, not 240 supplier business scenarios.

`production_go:false`; UAT and legacy remain untouched; DO NOT MERGE.

Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
