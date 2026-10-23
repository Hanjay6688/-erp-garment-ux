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

Not qualified yet: actual Native parity below the raw bound; complete 2,000
product/202,000 movement input under 8 seconds; malformed/other-incomplete
source refusal; inverse and composed source-authority checks. After those pass,
staged-job, source-freshness and final checked-SAVE integration still remain.
The parent OW13c completion count does not change for this adapter.
