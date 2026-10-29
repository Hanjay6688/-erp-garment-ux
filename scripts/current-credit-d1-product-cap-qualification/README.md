# D1 product aggregate refund cap — bounded quote successor

Only `cp7_credit_correction_de.quote_v1` in `owning.sql` changes. Its other13
function bodies and the other8 product leaves remain byte-identical to local
568e57d5bdd1452ed7d62392879f6d5b738dfadd / public d902 equivalent tree
6f931e639bd8996378ff65b8a7be2a1ed8590b45. There is no new UI shape, issue code,
Native writer/costing/trigger/rounding change, or frozen qualifier modification.
Root alone integrates, publishes and runs actual qualification.

The first reproduction is retained in `evidence/FIRST_QUOTE_READY_NATIVE_REFUSAL.json`
with its exact test source. A5/net1000 + B1/net1000, paid2000, current A2/refund200
and peer A3/refund600 permit a per-line proposal400.01 because the normalizer
allows400+.01. The old actual quote returned READY with no issues. Executing
unchanged whole `erp.post_sales_return` on the local replacement reached its
strict product cap and refused1000.01>1000, before a stock/journal writer ran.

This is an actual SQL quote/retained collector/kernel and exact Native predicate
execution against explicitly declared local structural, source, authority,
profile and HPP dependency doubles. It is **not a Native financial flow** or
proof of the installed current profile. Original Native sources are pinned:
post12167 bytes/SHA5f974ad9b9fff9ec9fef3018153683d35b79a9a5e8bd4c60e9a4a17b97622cdc;
normalizer2346 bytes/SHA1ca83d0e1728833c1fff2d3a285b142f8b1064e85afd3560573f885fedfd92bc.
Their complete source Original and retained setup derivation are in PROVENANCE.
No posted Native rows are changed by these tests: every inserted/updated row
belongs to the declared in-memory structural/source double.

The quote keeps the existing line cap, then uses the same single captured
authoritative snapshot to map every proposed allocation to its source sale item
and product. For each proposed product it sums all sale item net values, all
other POSTED return refunds for that product, and all proposed refunds. Each
sum uses the exact Native numeric(24,6) variable assignment and strict `>`
predicate without the line normalizer's one-cent tolerance. It excludes exactly
the old current return id: the real correction reverses that return before
posting the new replacement. It never excludes a whole family or a peer.

Incomplete, duplicate, foreign, unknown-status or malformed cap facts fail
closed using existing REFUND_CAP_SOURCE_UNAVAILABLE. An excess uses existing
REFUND_EXCEEDS_ORIGINAL_NET_SALES_CAP. The full source and the derived per-product
amounts/excluded-current id enter the existing review token. The unchanged
prepare path recalculates this quote after its existing lock graph and refuses
an invalid fresh quote or a stale token before effects. No new lock is added.

`directed.mjs` supplies34 local SQL controls: .01/equality/below bounds, peer
ordinal2, exact old exclusion, other-product capacity, all same-product sale
items, multiline allocation grouping, DRAFT/REVERSED peers, no-peer full value,
peer token retirement and21 malformed factual controls. Its Native probe runs
the unchanged whole function and stops immediately after the product guard via
an explicit exception in the stock-writer double. Each probe compares every
local table row and sequence before/after its rollback. It does not claim a
successful Native post, real stock/journal effects, or production restoration.

`reproduce.mjs` replays the historical failure by loading the exact retained
before-quote body. `fixture-prefix.mjs.txt` derives the retained local cap setup
with three counted setup-path/input substitutions; the cut point and hashes are
declared. `fixture-setup.mjs.txt` contains only new local source/dependency
doubles. `schema-double.sql` is the retained structural builder's output with
defaults/constraints removed; it is never an installer.

```bash
CP7_PGLITE_MODULE=/path/to/already-installed/pglite/dist/index.js node scripts/current-credit-d1-product-cap-qualification/reproduce.mjs
CP7_PGLITE_MODULE=/path/to/already-installed/pglite/dist/index.js node scripts/current-credit-d1-product-cap-qualification/directed.mjs
python -B -m unittest discover -s scripts/current-credit-d1-product-cap-qualification -p 'test_*.py'
python -B scripts/current-credit-d1-product-cap-qualification/source_check.py
```

The product has no static own SOURCE file: composition.sources() dynamically
hashes its9 business leaves. This new namespace SOURCE binds its own inputs and
changed owning digest; all old qualifier SOURCE/workflow bytes remain unchanged.
The old local_cap_check's partial source double lacks returns/return_items and
normalizer-owned product fields on its preseeded old return. Its existing .01
cases cover line admissibility without peer aggregate coverage. A new successor
must supply the complete declared factual double; do not edit its frozen bytes
or silently rebind its old result as aggregate coverage.

`source_check` is the quote-only writer checkpoint. Root's separately owned
materialize phase→support_phase repair will intentionally change one of its8
old leaf pins; root must declare that exact combined source transition in the
new successor qualifier, not regenerate historical pins to claim unchanged
product. Native13 augmentation is proposed separately in NATIVE_AUGMENTATION.md;
no actual case has been run or credited here. d9024PASS/9INCOMPLETE remains an
independent retained failure; it does not unlock continuation or E.

Native financial executions0; real Auth/browser0; hosted/remote/CI calls0;
independent_acceptance=false; production_go=false.
