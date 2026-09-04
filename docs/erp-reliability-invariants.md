# ERP Reliability Invariants

Status: binding product and engineering rule.

## Supreme rule

> Reliability Data adalah Dewa. Keuangan, stok, dan HPP adalah Raja.

The system must preserve all four together. A transaction that changes money,
stock, or HPP is successful only when every dependent fact is committed and can
be read back from the authoritative backend. A partial success is a failure.

## Non-negotiable invariants

| Boundary | Required invariant |
| --- | --- |
| Atomicity | Financial posting, stock movement, HPP propagation, entitlement, physical custody, and their lineage commit in one database transaction or all roll back. |
| Conservation | Source quantity equals returned physical quantity plus authoritative outstanding quantity. Claims, receipts, BS, Good FG, and rework may not count the same piece twice. |
| Idempotency | Retrying the same request produces the same result. Reusing its key with different content fails closed. |
| Concurrency | Competing writers serialize on one canonical source row. The winner commits; the stale or over-cap writer is rejected without residue. |
| Entitlement vs cash | Eligibility is closed when an entitlement is created, not when a late invoice or payroll payment is settled. Delayed cash settlement must never reopen eligibility. |
| Correction | Posted history is corrected by linked reversal or successor documents. It is never overwritten or silently deleted. |
| Replacement invoice | A replacement or late invoice references the original physical/financial lineage and cannot create a second stock, HPP, or entitlement event. |
| Read-after-write | The UI may claim authoritative success only after the server state is fetched and validated. If refetch fails after commit, close the form, mark the workspace stale, and freeze all writers until refetch succeeds. |
| Evidence | Every migration ships with replay rejection, rollback refusal after use, accounting/stock/HPP assertions, serialized race tests, residue checks, and exact source identity. |
| Isolation | The legacy ERP project is read-only. CP5/CP6 objects, users, migrations, and test residue must remain zero there. |

## CP5 business interpretation

- Accessory reimbursement defaults on only when the server can prove the
  current pre-FG quantity has not yet become an entitlement. A previously paid
  or unprovable baseline defaults off. An operator may explicitly select a real
  replacement; the immutable selection records that it was manual.
- Rework labor defaults from the remaining newly-performed entitlement counter,
  never from payroll cash status.
- `STUCK` and `MISSING` consume the same authoritative outstanding Laundry
  capacity. `DAMAGE` consumes posted BS receipt capacity. `OTHER` is not a
  Laundry claim type.
- A Laundry delivery or receipt cannot be reversed while an active claim still
  depends on it. Posting a return and creating a stuck/missing claim are
  serialized against the same delivery row.
- An unprocessed return caused by a failed wash is a physical return workflow,
  not a free-form claim. Re-dispatch and a legitimate second Laundry charge are
  a CP6 workflow and must preserve both physical legs.

## Accessory category truth supplied by the owner

| Large category | Mandor issue price | Reimbursement | State |
| --- | ---: | ---: | --- |
| Kancing | Rp495/pcs | Rp500/pcs | Active |
| Centang | Rp200/pcs | Rp200/pcs | Active |
| Kulit | Rp1.000/pcs | Rp1.000/pcs | Active |
| Sleting | Rp29.900/lusin | Rp2.500/pcs | Active |
| Plat | Rp500/pcs | Rp500/pcs | Active |
| Hang Tag | Rp7.150/lusin | Rp600/pcs | Active |
| Lock Pin | Rp300/pcs | Rp300/pcs | Active |
| Kain Kantong | Not configured | Other expense until defined | Future |
| Label | Not configured | Other expense until defined | Future |
| Kain Keras | Not configured | Other expense until defined | Future |

Detailed pickup items may be more granular, but reimbursement and payment are
grouped by these large categories. Historical snapshots keep the exact rate and
UOM used at the time; changing the master creates a successor version.
