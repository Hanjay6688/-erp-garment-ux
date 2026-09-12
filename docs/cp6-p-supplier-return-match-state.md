# CP6 P — Supplier return match state and report scope

P is the competition successor to O. O's native proof was independently
verified, then expanded transaction-sequence auditing found two P2 integrity
gaps outside O's original findings.

## Proven O counterexamples

1. A purchase item invoiced for part of its quantity stays `PARTIAL`/
   `PARTIAL` after a posted supplier return removes all remaining uninvoiced
   quantity. AP and GRNI both reach zero and the effective invoice capacity
   equals posted invoice quantity, so the derived state must be `MATCHED`/
   `FINAL`. Calling the existing refresh helper manually produces that state,
   proving the posting path omitted the refresh.
2. N and O added critical checks to `run_v267_financial_truth_checks()`, but
   `_v268_financial_report_checks_pre_scope()` forwarded only the older M
   namespace. A controlled O allocation fault produced one O issue while the
   authoritative financial report still said `READY`.

The shared nine-case SQL oracle reproduces five affected paths before P and
keeps four lawful controls. It proves single- and two-document closure,
post/reverse symmetry, partial and direct-final controls, over-invoice atomic
refusal, the new match-state detector, and the previously disconnected O
detector.

Upgrade qualification covers all nine final fixture histories: three stale
histories must be refused and six consistent histories may upgrade. The
follow-up over-invoice refusal is a lawful control, but its preceding O return
still leaves stale match state; a refused later action does not repair it.

## Repair

- `post_material_supplier_return(uuid)` refreshes invoice match state after
  every posted return item, in the same transaction as cost and stock updates.
- `run_v267_financial_truth_checks()` exposes
  `V2620P_SUPPLIER_RETURN_MATCH_STATE`.
- `_v268_financial_report_checks_pre_scope()` forwards all N, O, and P checks
  to the authoritative report.
- The migration refuses pre-existing inconsistent derived states for manual
  review; it does not silently rewrite historical business data.

## Trust and rollback boundary

P snapshots exactly three replaced functions, including definition hashes,
installed hashes, owners, ACLs, and 66 table boundaries. The reviewed P→O
rollback runs only through the admission-closed maintenance executor, refuses
successors or post-install history, and restores the exact O definitions.

The full rollback qualification is 11 generations × 5 real backend paths × 4
schedules = 220 native schedules, including 55 proven writer entries into
backend function bodies. P remains a local disposable candidate:
`production_go:false`, UAT and legacy untouched, and no merge authorized.

Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah
raja.

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
