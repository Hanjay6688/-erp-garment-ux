# ERP Reliability Invariants

Status: binding product and engineering rule.

## Supreme rule

> Reliability Data adalah Dewa. Keuangan, stok, dan HPP adalah Raja.
> Laporan keuangan termasuk di dalam wilayah Keuangan dan wajib membaca fakta
> authoritative yang sama.

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
| Physical time | Dispatch, receipt, and QC timestamps start blank and require explicit operator confirmation. The UI may not infer a physical event time from page load, browser clock, or server response time. |
| Evidence | Every migration ships with replay rejection, rollback refusal after use, accounting/stock/HPP assertions, serialized race tests, residue checks, and exact source identity. |
| Isolation | The legacy ERP project is read-only. CP5/CP6 objects, users, migrations, and test residue must remain zero there. |

## Product and production identity

- The human-facing product identity is ordered **Brand -> SKU number -> Model
  -> Color -> Size**. SKU numbers are brand-scoped: two different brands may
  legitimately use the same number, including for different models. Inside one
  brand, one SKU may span several sizes only when model and color stay the
  same. Stock, HPP, and transaction lineage remain bound to the exact
  `product_id`/size; two active roots may never overlap for the same Brand + SKU
  + Size.
- Product identity history is one linear effective-dated chain per exact-size
  root. Every non-root version has exactly one predecessor in that root, a
  predecessor has at most one successor, and both meet at the same timestamp.
  A missing root, detached version, fork, overlap, or retroactive boundary move
  fails closed; it is never repaired by rewriting stock/HPP history.
- After a product row is created, its Brand, SKU number, Model, Color, Size,
  root/predecessor links, and effective period are immutable. Display name,
  visibility, and active status may be maintained; a real identity change waits
  for a controlled successor-row workflow and never edits the old row.
- The current backend keeps one versioned product root per exact size. A master
  screen may present those rows as one human SKU, but a future connected master
  writer must fan out price/BOM changes atomically to every selected size root
  and fail the whole request on any stale version. It may not silently copy one
  size's stock, HPP, price, or history into another.
- SKU describes the sellable model; it does not store Pattern. Pattern remains
  an immutable cutting/production snapshot. Questions such as "which Pattern
  did this SKU use this year?" must be derived through authoritative lineage
  from FG/QC to Laundry receipt/batch and the cutting group, never copied into
  or guessed on the SKU master.
- Brand/SKU is never invented during PO, cutting, sewing, or Laundry dispatch.
  It is bound only at a terminal product-classification boundary: a Laundry-BS
  binds its Brand/SKU at the physical receipt, while Laundry Good binds its
  Brand/SKU at QC/Final-SKU allocation. Earlier facts retain model, size, and
  production lineage without guessing a brand.

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
- A physical Laundry receipt may snapshot the authoritative rate for HPP, but
  remains `ESTIMATED`/unbilled. It must not release the manufacturing accrual
  until a posted vendor invoice atomically finalizes the receipt cost, creates
  AP, and replaces the matching accrued liability. This keeps WIP, FG/HPP, AP,
  accrued liabilities, and financial reports reconciled while invoices arrive
  late or are later reversed/replaced.

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

## Delivery framework

| Checkpoint | Binding boundary |
| --- | --- |
| CP6 | Connect authoritative Laundry return, QC, and exact-size Final SKU/FG handoff. Simulation never substitutes for missing master or transactional data. |
| CP7 | Build stock calculation and reports only from real CP6 ledger facts. Draft invoices reduce physical availability by the approved business rule; reserved/ATP concepts may not be resurrected implicitly. |
| CP7.5 | Cleanup and rebaseline the accepted schema/evidence, archive exact source, bind digests, and prove restore before further expansion. |
| CP7C | Stress concurrency, automation, backup, and restore. A green happy path without race/recovery proof is insufficient. |
| CP8 | Independent exact-HEAD audit and owner-controlled cutover. Prior PASS is void if code, base, migration bytes, or environment identity moves. |

## Owner UX UAT and disposable data

- CP7 is the first checkpoint where the owner can exercise one complete dummy
  business transaction through authoritative stock, HPP, journals, and
  financial reports. The recommended formal owner UX verdict is after CP7.5,
  when exact schema/source identity and restore have been re-proven.
- End-to-end dummy transactions run only in an exact-schema disposable
  environment. During the session, posted corrections remain append-only as
  linked reversals so audit behavior is tested honestly.
- "Clean total" means tearing down or restoring the whole disposable
  environment to its recorded clean baseline, followed by zero-residue checks
  for auth/app users, business documents, stock movements, HPP, journals,
  report inputs, audit fixtures, idempotency envelopes, locks, and long-running
  sessions. It never means deleting selected posted history from a persistent
  ERP database.
- Production and the legacy ERP are never cleanup targets. Legacy remains
  read-only before, during, and after owner UAT.
