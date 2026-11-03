# Effective component ledger for recost-safe moving average

Currency-only adjustment rows are sufficient for the posting moment but not
for a later HPP correction. If one contributing lot is recosted, historical
moving-average transfers, sales, returns, FG, COGS, and PO/non-PO attribution
must all move by the same economic lineage.

The authoritative projection therefore needs append-only **component-unit**
events in addition to cent posting snapshots:

- A component is an economic root lot/HPP lineage, not necessarily the FIFO
  lot physically picked.
- A pool is exact `product + location + quality_grade` custody.
- Active reservations remain in the pool.
- Converting `q` from physical pool quantity `Q` transfers the fraction
  `q/Q` of every current economic component.
- FIFO movements keep physical provenance. Component events record only the
  difference between that physical carry-forward and the proportional
  economic transfer.
- A sale consumes the same proportional component mix and freezes a cent
  snapshot plus its component fractions. A return restores the recorded sale
  mix at the selected active destination.
- Repricing a root component changes the current effective value everywhere
  that its units remain. GL recost remains delta-based: new cumulative target
  minus the prior booked target.

For each event, exact high-precision units are stored separately from the
authoritative rounded currency amount. A deterministic cumulative apportioner
assigns cent children whose sum is exactly the group amount; the explicit
residual is evidence, never a hidden tolerance.

This model preserves two truths without conflating them:

1. physical lot/PO provenance answers which pieces moved;
2. economic component provenance answers whose HPP value moved.

Mixed PO/non-PO stock is therefore lawful: economic component cents retain
their PO or non-PO attribution even when FIFO picked another physical lot.

The SQL successor is not ready for actual installation until its pool quote,
conversion, sales, returns, readers, PO/non-PO targets, propagation, and
reversal all derive from this projection. `production_go=false`.

Return item currency snapshots are apportioned from the current FG target
change in each financial scope. The unrounded owned-root projection is shared
with both official target functions. Before an item is prepared, previously
prepared items of that same draft are included explicitly; other drafts remain
non-authoritative. PO scope spans products and warehouses, while non-PO scope
is one product across warehouses. Component units still restore the selected
sale allocation's original mix. Historical snapshots and inverse events stay
immutable; current journals continue to use the existing target/book deltas.
