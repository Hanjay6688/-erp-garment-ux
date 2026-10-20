# First browser CI failure: fixture SKU lookup

Candidate dfc4a56b6691d1fde1754bccb443093f70ad3b8f, tree
32da7dad9d3230b12f44a62b25b6cb4431f5d37d,
run39502462818/job118903108563 produced4 INCOMPLETE,0 PASS.
All four slots stopped in prepare before Auth login or settlement. The UI
build/anonymous bootstrap reached CASES, but that is not four browser passes.
CI_DFC4_BROWSER_FIRST_FAILURE.json and the complete compressed runtime preserve
the actual first result. CP6 restoration/advisors passed; writer_runtime:false
correctly made the outer package fail although its install stage succeeded.

The writer used SELECT product_sku FROM erp.products. This is a schema
assumption error: scripts/cp7-src/sales/returns.sql:54 exposes p.sku AS
product_sku, while scripts/cp7_note_correction_cases.py:131–136 stock() already
returns the actual products.sku value. native.prepared retains that same f
dictionary. The repair reuses f['x']['f']['sku']; no new query, product change,
golden, case ID, money/date oracle or browser expected change is made.

COUNTER_STOCK_SKU_FIX.json independently checks that exact single-lookup diff
and its retained fixture provenance. It is source review, not a browser result.
The earlier three qualification-counter repairs remain unchanged.

The HTTP workflow now excludes only browser* and BROWSER_EXPECTED.json from
its broad qualifier path filter, while the browser workflow includes the
entire shared qualifier directory. Thus subsequent browser-only fixes run the
browser suite; changes to shared transport/fixture dependencies still run
both. Both workflows' jobs, actual commands, guards, pins and outer gates are
unchanged. Changing the HTTP workflow itself still triggers its suite once.
Prior Native44 and HTTP8/race6 evidence is never relabelled as a fresh run.
OW04 remains open; production_go:false.
