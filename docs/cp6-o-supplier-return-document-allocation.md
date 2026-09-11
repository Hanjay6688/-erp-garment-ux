# CP6 O — Supplier return document allocation

Incoming N is exact commit `3cf5850bf9f82c558d60c9b4844e9399df0ca58f`,
tree `b1fbd1f41fd0083c93747c88065fbf4915529dd9`. Status: **writer
candidate; native CI and independent audit required**. This successor does not
authorize merge or deployment (`production_go:false`).

## Failure closed from N

N allocated invoice-backed return quantity one line at a time.  Every line in
one draft return document queried only earlier `POSTED` return documents.  The
header stayed `DRAFT` until the loop finished, so a later line could not see AP
quantity already allocated by an earlier line in the same document.

For one estimated purchase item received as two rolls (`5 + 5`), invoiced only
for `5`, a full two-line return could therefore allocate AP quantity `5 + 5`.
At an ordinary credit price the resulting negative AP check rejected a lawful
return atomically.  At credit price `4`, the duplicate allocation stayed above
zero and N silently posted AP quantity `10`, GRNI quantity `0`, AP `10`, GRNI
`50`, inventory `0`, and purchase variance `60`.  A later invoice for the
remaining quantity could consume the untouched GRNI and make current totals
look internally consistent, while preserving the wrong historical allocation.

## O behavior

`erp.post_material_supplier_return(uuid)` now tracks AP quantity already
allocated for the current `purchase_item_id` inside the document loop.  Each
later line receives only the remaining invoice-backed capacity; all other
returned quantity relieves GRNI.

The installation guard and `V2620O_SUPPLIER_RETURN_ALLOCATION` report check
also replay immutable `supplier_cent_posting_facts.recorded_at` events.  Legacy
invoice capacity is the opening balance.  Posted invoice facts add capacity and
posted AP-return snapshots consume it.  Capacity may never be negative at a
return event, so an invoice posted later cannot conceal an earlier excess.
Ambiguous pre-existing history is refused with
`O_PREEXISTING_RETURN_ALLOCATION_REVIEW_REQUIRED`; no history is rewritten.

## Exact oracles

The committed native oracle covers 18 isolated cases:

- seven controls: no invoice, direct-final, full invoice, one return line, two
  return documents, a two-line return below invoice capacity, and an atomic
  high-credit refusal;
- eleven affected/adversarial cases: the original two-roll case, crossing the
  capacity within two or three lines, split invoices, repricing, prior relief,
  low credit, payment-constrained AP, late-invoice laundering, reversal, and
  fractional quantity.

On exact N the oracle requires seven controls to pass and eleven N failures to
reproduce.  On O all 18 must pass.  The low-credit case must end at AP `30`,
GRNI `0`, inventory `0`, variance `30`, with AP quantity `5` and GRNI quantity
`5`; the late invoice must then fail atomically.

The migration preserves the N helper/fact security boundary, snapshots exactly
two predecessor functions, validates owner/ACL and source hashes, and records a
65-table boundary.  Its reviewed pre-use rollback is admitted only by the
closed-admission maintenance executor and restores exact N function bytes.

Sequential PGlite replay reproduces all seven N controls and eleven N failures,
then passes all 18 O cases and restores exact N hashes through the reviewed
rollback. The native workflow expands the F–O rollback matrix to 200 schedules
with 50 observed writer-body entries. Native PostgreSQL CI remains the authority
for concurrency, Auth, maintenance admission, and final proof-manifest evidence.
