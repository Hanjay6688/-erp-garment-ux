# P04 — conserved WIP, matching and remaining ETA

Status: WRITER_KERNEL_NATIVE_PASS_14_CASES; actual cutting source adapter implemented, native verification pending. F02 remains open. No operational
connection, production deployment, or independent acceptance.

## Authoritative implementation

Modular PostgreSQL kernels in `scripts/cp7-src/wip`, explicitly concatenated by
`cp7_wip_bundle.py`. No JavaScript quantity/planning engine.

- `reconcile`: one original input pool per exact size and ownership, positions
  of the same pool, ordered source transitions, exact prefix balances. Parent
  group totals are controls, not additional pools. Negative prefixes conflict;
  unaccounted input is UNKNOWN. Rework moves BS into WIP then back to FG/BS;
  rewash is a cycle of the same resource. A reversal references one prior exact
  transfer and must respect downstream consumption. Exits remain accounted.
- `match_target`: explicit confirmed destination and physical constraints are
  distinct from tariff/history hints. Known hard conflicts refuse; required
  unknowns need checking; optional empty metadata does not reject everything.
- `check_allocations`: all edges in one complete scope/scenario share remaining
  position and pool constraints. Filters are not accepted. Alternate scenarios
  are independent simulations, never reservations.
- `remaining_eta`: explicit remaining work only, versioned working intervals,
  no invented hours or leadtime. Insufficient calendar/unknown work gives no
  ETA/on-time boolean. History/assumption bases remain conditional. A calendar
  finish alone is not a capacity promise.

## Predeclared proof

14/14 native kernel cases passed on `33356d2dd9cd6cf10fb378bb0e93d7dfce357bee`, [run 36511438524](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36511438524), bundle SHA256 `4484de0c6b982067969532b3840e95ef198b5f9cb2da3cb6df39331fb31e5e76`. CP6 restored; advisor gate passed. Cases in `cp7_wip_cases.py` include owner O15 100 = 80 WIP + 15 FG + 5 BS,
rework 100 = 80 + 18 + 2, duplicate input, negative prefix, rewash/reversal,
size/ownership/partial captures, required versus optional matching, shared pools,
remaining-stage calendar and quantities above JavaScript safe integer. Isolated
accepted CP6 runner, explicit bundle, original ERP/public boundary restore.

## Required before F02 checkpoint

These tests use **normalized kernel fixtures**, not full ERP posting transactions.
The source adapter must next capture actual group/batch/size, laundry/QC and
rework facts in one MVCC snapshot, prove its normalization against the same
oracles, and expose only authorized immutable results. Existing sewing events
lack batch/size allocations: preserve quantity while marking the unproven
substage; do not divide by proportions. Ambiguous legacy links, missing/stuck,
opening stock, direct QC, failed wash/redispatch and rework need explicit
classifications. No sum of independent P02 runs can stand in for one capture.

P03 policy proof does not close O17 planning arithmetic. Global apply races and
connected sales/return R10 remain downstream obligations. `production_go=false`.

## Cutting source adapter under verification

Explicit selected groups (1–50), 16 nonfinancial source domains bounded at 2,000 rows each, one STABLE capture inside an immutable-run INSERT. Capture/serve/replay validate current Auth; real request lock precedes capture clock. Scope is selected cutting groups, not opening/non-PO sources or a whole planner snapshot. Results preserve current production disposition, not current FG on hand after later sales/conversions.

Shared pool is group + exact size. Batch references remain provenance; group sewing totals are not divided among sizes/children. Explicit size-line/header mismatches block the result; legacy missing size resolves only for a single-size source. Deferred invoice costs do not enter these projections. Draft/unposted input, unreconciled MISSING/STUCK custody and rewash/redispatch participants are currently held for further normalization. Public RPCs are authored for isolated tests and are not connected to the browser.

Additional declared source proof: ordinary cut/pickup/sewing/deferred laundry/receipt/partial QC produces 100=80+15+5; later ordinary QC changes the new run while preserving the old run; actor/revoke, malformed scope, inconsistent quantity, multiple groups, real HTTP and two snapshot/replay races. No source-case result is claimed until its run finishes.

### First adapter run and correction

Run `36512452133` on `7840397916676257621e5059e6126024932db4d7` passed the 14 kernels, but the first actual-source smoke failed with PostgreSQL `AmbiguousColumn` for `y` inside `normalize_cutting`. This is a new adapter implementation defect, not a CP6 posting failure; the ordinary posting fixture reached capture. Distinct SQL aliases replace the colliding PL/pgSQL names. Source-family/race/HTTP cases were NOT_RUN behind that smoke gate. CP6 boundary was restored and advisors passed.

The follow-up also checks ordinary partial rework: SAVE keeps the full rework resource in WIP; only a posted completion transfers actual GOOD to production disposition FG. A posted-completion flag is captured; no timestamp is invented for partial return. Claims join the source dependency hash, so a claim resolution/rejection cannot silently leave a run current. Claim custody normalization is held explicitly until its cases are qualified.

### Second adapter run

Run `36512824584` on `eb713ceb28312034aa40db8923bbab2b5b888582`: actual posting smoke PASS; 14 kernel PASS; source 6 PASS and 1 INCOMPLETE; 2 races and 1 real Auth/HTTP PASS. O15 physical totals and canonical authorization/concurrency passed. The incomplete case asserted `actual_cost IS NULL`, which is not the accepted CP6 unknown-price contract. `bd_delivery_line_price_unknown_v1` determines unknown price from incomplete tariff/invoice state; internal known-cost accumulation may be zero while the public valuation remains UNKNOWN. The follow-up tests that authoritative predicate and the P02 public valuation without accepting KNOWN(0). The original failed assertion remains recorded.

The next source run includes returned-unprocessed redispatch and repeated retry-at-vendor. Reversed original dispatches leave the original resource in the shared group-size pool; failed attempts are not GOOD/BS receipts. Active participant ranges must be within the exact source/successor batch-size, nonoverlapping, and backed by a full unprocessed return. Retry events retain the existing outstanding pool. Rewash substage/timing remains explicitly for review, rather than allocating overlapping attempt counts as extra physical stock.

### Third adapter run and bounded follow-up

Run `36513301637` on `c923e3faceb7be092d5e57a2344572a56f0ad1c6`: 14 kernel, one source smoke, seven source cases, two races and one Auth/HTTP case PASS. Ordinary deferred laundry passed both physical conservation and public UNKNOWN valuation. The new rewash fixture failed before capture: accepted `POST_FAILED_WASH` requires exactly one effective vendor/process rate. The follow-up declares vendor rate 5.00 through the existing master facade. This qualifies known-rate rewash only. **F03/P13 carries a review of failed-wash with unknown vendor pricing against the owner's price-later requirement.** No CP6 guard was changed; no SKU tariff was introduced.

The follow-up also tests actual MISSING/STUCK claims. Existing `validate_laundry_claim_lineage` requires a delivery header, excludes REJECTED claims from custody conservation, and counts SETTLED/WRITTEN_OFF claims. Normalization uses that contract: a uniquely proven delivery line and exact size moves unreturned input into withheld custody once. Multi-line or multi-size ambiguity yields UNKNOWN, never a guessed size split. Receipt-line MISSING/STUCK sources conflict with the accepted contract; legacy receipt custody counters remain explicitly UNKNOWN pending reconciliation. Rejection restores the outstanding classification, not received goods or FG. Claim state changes invalidate the current-source hash while leaving the old snapshot intact. These new cases remain pending until the native follow-up finishes.
