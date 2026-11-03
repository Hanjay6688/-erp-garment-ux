# SKU moving average successor — Writer A

Status: source conversion/consumer core in progress. This directory is not an
actual Native qualification result and is not production acceptance.

The accepted SKU conversion keeps FIFO only for physical lot provenance. The
accounting amount is instead derived from the complete `product + location +
quality_grade` pool, including active sale reservations because reservation is
not a physical or value outflow.

For a conversion of `q` pieces from a pool `(Q,V)`, the authoritative transfer
amount is `round(q * V / Q, 2)`. The existing Native children still carry their
physical selected-lot value `C`. An append-only pair of value events records:

- source: quantity `-q`, effective value `-M`, legacy value `-C`, adjustment
  `C-M`;
- target: quantity `+q`, effective value `+M`, legacy value `+C`, adjustment
  `M-C`.

The adjustments sum to zero. A correction journal, when `M != C`, only
reclassifies FG inventory between the two products. It never creates cash,
receivable, payable, revenue, COGS, expense, or income.

The quote stores every contributing economic root, current HPP version,
high-precision component units, and cent-apportioned value. Native FIFO lots
remain the physical provenance. Append-only component corrections bridge the
two without changing pool quantity. This distinction is required for a later
root-HPP recost to follow the units that remain, were sold, or were returned.
Historical rows are immutable; reversal appends an exact inverse while recost
recomputes cumulative targets from the current root HPP.

## Required closure before qualification

The source now includes exact-derivation hooks for sale allocation component
snapshots, return restoration, mixed-scope reversal, recost scope expansion,
FG readers, and both PO and non-PO cumulative targets. A moving average can
mix PO and non-PO contributors; cents therefore follow economic roots even
when FIFO chooses different physical lots. Aggregate product-only balancing
is not accepted as a substitute.

The source bindings and pure arithmetic oracle pass locally, but no SQL in
this directory has been installed or executed against Native yet. Catalog
authority, real posting/reversal/recost cases, concurrency, and exact restore
remain mandatory. Until those actual gates pass, `production_go=false` and
`independent_acceptance=false`.

Canonical arithmetic:

1. A: `2@10 + 2@30 = 4/80`; B: `1@50`.
2. Forward one A to B transfers `20`: A `3/60`, B `2/70`.
3. A new manual B-to-A transfer uses B's then-current average `35`: A `4/95`,
   B `1/35`.
4. Total inventory value stays `130`; manual back is not an inverse. Exact
   cancellation remains the guarded group reversal.

Physical-time, economic-date, rights-after-waits, stale revision,
idempotency, two-tab serialization, and full restore obligations remain those
of the qualified parent and may only be tightened here.

## Exact catalogue preparation

`CATALOG_ADDITIONS.json` pins the expected additions from the unchanged
`valuation.sql` using the original all-22 catalogue queries. It was derived
on an isolated PostgreSQL 17.5 engine (`@electric-sql/pglite@0.3.14`) with
empty UUID-key dependency tables. No ERP fixture or financial function ran.
This is a DDL expectation, not Native qualification or acceptance.

The 639 exact rows cover 12 tables, 19 explicit/implicit indexes, 183 table
and index columns, 132 constraints, 202 triggers (including both ends of
47 foreign keys), 12 private functions, 24 row/array types, their 24
implementation rows, and 12 deny policies. The other 13 catalogue groups
must not change. Every added row must be present with its exact metadata;
matching a name prefix is insufficient. Existing objects remain frozen
except for the already declared, exact function-body substitutions.

The pre-database controls reject each missing or altered expected row,
undeclared additions in every catalogue group, changes to existing authority,
and replacements of an all-22 group. The actual Native5 run, all used-state
refusals, complete restoration, and the five package gates remain required.
