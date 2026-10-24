# Bounded history inputs — work in progress

This private, read-only adapter exposes the existing qualified SQL stock-summary
compiler for an explicitly selected closed-day query. It derives the Native
events, availability, history rows, current-stock reservation check and target
calculation from `cp7_reorder_inputs`, before the ROP default/manual/lead layer.

The original raw capture remains `INCOMPLETE` above 50,000 stock movements.
Every visible stock movement contributes through SQL aggregation; products,
sales, journals, returns, duplicate roots and ambiguous commercial identities
retain their existing refusal. The result records both the raw Native status
and the separate complete-input path. It does not alter source hashes, create a
job, fabricate DONE, calculate production capacity, or authorize checked SAVE.

There are two private functions, no public facade, no table and no old function
replacement. Installation takes an already authorized disposable cursor; no
default installer or connection/commit is provided. The pre-use inverse must
restore all 22 catalog groups and refuses external SQL callers before DDL.

Native3 qualified the component at candidate `cd8e37d6`, run40020162611:
exact complete-input parity; 2,000 synthetic products/202,000 movements plus
2 existing fixture products in three full reads (1413.602/1400.994/1416.235 ms,
each below the unchanged 8 s limit); real product-bound overflow refusal.
All36 source hashes,10 pre-use22 inverses, unchanged legacy9 oracle,
restore/advisor and all5 package gates matched. All ERP/platform/auth and
work-metadata rows stayed unchanged. Raw Native INCOMPLETE remained so.

The component does not yet provide a lossless raw-stock freshness digest,
create a versioned staged job, or qualify actual checked SAVE2000. Those
integration steps remain open; the parent OW13c completion count is unchanged.
See `docs/cp7/d17-14/ow13c/cd8e37d-inputs3-pass.json` for exact evidence.
