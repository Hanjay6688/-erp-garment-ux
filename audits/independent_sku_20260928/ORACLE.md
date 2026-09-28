# Independent SKU/range oracle — frozen before reading new writer/peer verdicts

Candidate: 23e9c9830c32dce10604c43d17e4476d2707b55d.
Product tree: 51f48d165b494e2ac256bc8b8ad6a82e2a527983.
Owner contracts: current conversation and prior owner requirements recorded in
docs/cp6-sku-range-impact-20260928.md at e96db5a (business sections). Prior own
BD/BE fixtures and failures are known and will be independently re-executed.
No new writer/peer test scripts, assertions or verdict artifacts have been read.

## Required business properties

1. Commercial SKU membership is explicit and versioned; physical product IDs,
   size IDs, stock, lot lineage and posted history are preserved. Same code in
   another brand/color/model cannot silently join the wrong group.
2. One sale price, accessory recipe and relevant service/work setting per SKU
   reaches every valid member atomically. Ordinary range members do not require
   duplicate input. Singleton/special SKU is independently priced.
3. Membership and effective date changes preserve old document snapshots. A
   31/32/33 group extended to 34 must not duplicate stock/value or erase history.
   New transactions use applicable group/version; retired/conflicting membership
   cannot be silently selected from the first row or inferred from text.
4. Physical quantity is authoritative: 5/8/3 across sizes remains 5/8/3; one
   mixed wave may contain several commercial SKUs and exact member sizes.
   A price-reference SKU is a reference, not creation of FG or reassignment of
   final QC identity. Different SKU sources may share a model without cost bleed.
5. Charge only the pieces receiving a service: finish 3 pieces of middle size
   at 913.27 costs 2739.81 on those pieces; other sizes receive none. An all-size
   service has one agreed tariff version, with quantities from actual recipients.
6. Owner HPP summary is remaining inventory value / remaining pieces, with
   consistent location/date/grade scope and UNKNOWN propagation. Example 9 pieces
   at 43210.17 plus 4 at 67890.43: total660453.25 /13 =50804.096153846... .
   FIFO sales/returns use actual allocated lots rather than summary average.
7. One dozen across 3 eligible sizes yields4/4/4. Dynamic singleton and ranges
   of 2/4/5/6 sizes preserve exact integer PCS and total. Zero, negatives, invalid
   fractional physical PCS and overflow cannot silently become a different order.
   Explicit size input overrides distribution; inventory cannot change merely
   from rendering or grouping. Draft availability moves only once; posting and
   returns retain exact source size/allocation.
8. Imports distinguish commercial SKU and exact physical member. Missing or
   contradictory brand/model/color/size must not choose an arbitrary product.
   Legacy conflicting prices/BOM require visible resolution. Costs already
   included in opening WIP must not be added again; cutoff/backdate preserved.
9. Rework, recovery, redye, conversion and accessory reimbursements preserve
   source/target SKU, size, selected recipe items, quantities and exact costs.
   Work/payroll uses applicable SKU snapshots; membership edit alone never
   rewrites old payroll or financial history.
10. Repricing, late invoices, reversals and correction recost preserve total
    inventory+COGS/journal and do not multiply charges across sibling sizes.
    Existing legitimate FREE/WAIVED remains distinct from UNKNOWN.
11. Concurrent group edits, member moves, rate changes and stock-consuming
    operations serialize or reject stale state. UUID replay remains once-only
    and checks current permission before returning sensitive saved responses.
12. Native, HTTP and actual browser results are distinguished; wrong input or
    test adapter failures are not product bugs. Pre-use rollback restores exact
    predecessor; after-use rollback refuses atomically. Official CI and CodeQL
    run on audit commit containing unchanged frozen product bytes.

## Independent work sequence

Freeze this oracle; inspect interfaces and new product source; author fresh
fixtures and expected calculations; execute isolated tests; cross-check the new
writer/peer handoffs and expand any missed scenarios without replacing this
oracle. Mark old BE issue persistence, closure, or untested honestly. CP1–CP6
impact map does not claim all unrelated historical tests were re-executed.
No product edits, live/UAT writes, merge or deployment. Any gap remaining is
listed explicitly, not scored as pass or mislabeled as a confirmed defect.
