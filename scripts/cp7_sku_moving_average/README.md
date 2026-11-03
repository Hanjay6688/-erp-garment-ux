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

The Native attempts and first failures remain retained separately. Source
checks and isolated PostgreSQL preparation are not Native acceptance. Catalog
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

The 642 exact rows cover 12 tables, 19 explicit/implicit indexes, 183 table
and index columns, 132 constraints, 202 triggers (including both ends of
47 foreign keys), 15 private functions, 24 row/array types, their 24
implementation rows, and 12 deny policies. The other catalogue groups remain exact except for one declared schema USAGE
lease to the existing private FG reader role. Every added row must be present with its exact metadata;
matching a name prefix is insufficient. Existing objects remain frozen
except for the already declared, exact function-body substitutions and that
one exact reader schema lease.

The pre-database controls reject each missing or altered expected row,
undeclared additions in every catalogue group, changes to existing authority,
and replacements of an all-22 group. The actual Native6 run, all used-state
refusals, complete restoration, and the five package gates remain required.

## FG reader integration preparation

The current pool value is read through the existing ordinary FG public facades.
Only the existing private cp7_fg_read role receives schema USAGE and EXECUTE
on position_value_v2; private tables and all other new functions remain closed.
The callee checks the current actor's finance.hpp.view before observing data.
The unused inverse removes the exact schema lease and all22 must match again.

Only GRADE_A positions use the pool; other grades retain their original Native
lot reader. Unknown or depleted pools return UNKNOWN with null money, while
unrelated accounting and permission errors propagate. A pool has no single
HPP version. The client accepts the explicit pool basis/revision only on
GRADE_A, keeps the original lot contract closed, and labels the current card
unit cost as SKU HPP. No quantities or transaction commands are changed.

The isolated PostgreSQL17 reader capability controls use explicitly modeled
pool and actor-permission dependencies; they are not ERP or Auth acceptance.
The Native canonical forward/back case now also requires both actual existing
public FG readers to report source4/95 at23.75 and target1/35 at35. The private
ledger observations use the original administrative observer; business commands
and public reader checks retain the ordinary actor. The separate committed
fixture removes its temporary Native ERP-schema overlay and verifies the full
product catalog before committing. Actual Native and owning full restore remain
mandatory before this preparation can be integrated.
# Owning package inverse receipt

Run `41621518177` installed the moving-average delta and restored the exact
unused parent, then stopped before any Native case because the inverse receipt
omitted the owning package's required `used_guard_before_DDL` field. Complete
outer catalog/data/sequence/role/public/advisor restoration and the backup drill
were identical. The original failure is retained; it is not Native acceptance.

The inverse now emits that Boolean only after its existing locked whole-data
guard, exact restoration and parent verification finish. No guard or DDL was
changed. Five focused controls reproduce the old caller failure, run the exact
unchanged package assertion against the corrected receipt, and refuse used
state before DDL or inexact catalog/row/sequence restoration. These controls run
before database setup in the owning workflow. Collaborators are modeled; they
do not replace the actual Native6/used-inverse/whole-package qualification.

## PostgreSQL17 attribution planner correction

The fdabda actual Native5 attempt reached all five scenarios; each refused the
same unsupported FULL JOIN with a nullable PO identity predicate. Its complete
case boundary and outer data/catalogue/role restoration passed; financial
acceptance did not. The candidate now forms the complete distinct PO key set
(including NULL) and uses two nullable LEFT JOINs. It invents no UUID sentinel,
retains zero and one-sided scopes, and preserves exact source/target cents.

Before the long ERP installation, a pinned PostgreSQL17/WASM check executes the
exact candidate INSERT on synthetic rows. It reproduces the original planner
refusal and covers seven NULL/mixed/one-sided/duplicate/empty/zero cases. This
adds no Native acceptance. Only the one function's observed DDL definition and
valuation source pin change in the 639-row catalogue-addition profile.

## Component consumer closure after the retained 8168 attempt

The original `8168125136b79373693d3f186f02f9e23e6da8c5` run
`41633865632` passed the canonical forward/manual-back and exact inverse
cases. Root recost refused a source delta of 15 against the root basis change
of 20; both sale-dependent cases refused a PL/pgSQL record/SQL-alias collision.
All five results and complete successful restoration remain in the original
artifact `13231162946`; the attempt is incomplete and is not an accepted parent.

The successor binds eight existing Native consumer bodies. Opening correction
checks each affected product's complete target/book before changing the root
version, apportions the source journal across its economic component owners,
requires their exact sum to equal the opening basis delta, and checks every
affected target/book afterward. The physical-conversion correction refusal,
permissions, locks, immutable source history and minor-unit guard remain intact.

Sale preparation uses a distinct loop variable and gives every physical
allocation the proportional root mix. Consecutive root intervals must not
assign different economics to otherwise equivalent returned pieces. Pending
sale/return components remain non-authoritative until their header is posted;
posted reversals append their exact inverse. Both PO and non-PO targets retain
a disjoint fallback for pre-installation Native sale/return histories. Returning
an old allocation retains its original Native source scopes.

The early PostgreSQL17 controls execute the exact candidate preparation,
source-target and opening-correction SQL, plus the full `erp.post_sale` body
with explicit synthetic authority, book/journal and known-HPP providers. They
check the real reservation -> source/book -> status -> journal order, positive
and negative source controls, proportional partial return, reversal, preserved
legacy COGS and a one-lot sale. These are modeled SQL controls with zero Native,
Auth, HTTP or browser credit. They run before the long ERP installation. The
actual five business cases, used-state refusal, all-22/all-row/all-sequence
restore and owning package gates remain required.

## Fractional return scope cents (3 Nov 2026, successor pending qualification)

The first added model incorrectly treated item snapshots as the journal
authority. The exact Native return body already posts cumulative target/book
deltas: two returns posted 3.33 and 3.34 correctly. The demonstrated issue is
that immutable item snapshots both stored 3.33. That first report and the
corrected exact-body counterexample remain retained separately.

Return snapshots now use the same unrounded owned-root projection as the
official FG target, with current draft items added explicitly. Rounding occurs
within each financial scope (PO across products, or non-PO per product), before
root cents are apportioned. This preserves the cent after another allocation,
warehouse change, an earlier inverse, or a current root recost. Current prior
stock is valued at current HPP; historical item rows are never rewritten.

The new private read helper adds one exact catalogue row; the return function's
other 18 authority attributes and the other 638 catalogue rows are unchanged.
No table, column, permission grant, transaction oracle or restore gate changes.
The 25-table early model includes the exact sale/return allocation unique
indexes and exact Native sale, return, FG movement and chronology bodies,
with explicit authority/credit/book provider models. It earns zero actual
Native or Auth credit. A new sixth Native case exercises actual public sale
commands, mixed-cent return allocations, earlier-return reversal, root recost,
immutable snapshots, exact current books and final inverse. The five earlier
Native cases and all complete-package restoration obligations remain required.


## Credit HPP projection after the 7eed actual failure

Run `41644713451` closed the root-recost case in addition to the two earlier
conversion cases. Sale/return stopped at `CP7_CREDIT_HPP_CANONICAL_TARGET_MISMATCH`:
its retained pre-posting credit proof still calculated physical lot costs.
The fifth case restored quantity/value/average correctly but compared an old
revision against the legitimately changed immutable sale/inverse history.
All five case boundaries and the complete outer restoration passed. Actual
acceptance remains incomplete (three business cases passed, two incomplete).
The first original archive is retained, not replaced by a rerun.

`credit_delta.py` admits four byte-exact retained functions. The independent
canonical target now derives owned, sold, returned and conversion amounts from
raw economic components, with the disjoint physical fallback for older sales.
It never copies the official target into its own proof. A shared read-only
allocation plan is used before posting and by immutable return preparation;
it applies allocation capacity, known current root HPP, integer quantity and
12-decimal root-unit conservation checks before calculating scope cents.

The pre-posting sealer includes both physical and economic PO/non-PO scopes,
locks every contributing root and all HPP versions before period acquisition,
and re-reads the allocation plan and lock set after waits. Support hashes and
opening-state proofs include cross-product roots and component provenance.
The existing physical-lot profile remains exact for Native completion guards.
Every old refusal, actual target/book comparison, conserved journal vector,
account mapping and authority attribute is preserved. No registered-credit
source-mutation guard is relaxed. The new Native fixtures are unpaid sales
with empty recognition; their inverse route does not enter the separate bounded
cohort/incoming-credit reconciliation extension.

Two further private read helpers make 15 functions / 642 exact added rows.
The other 639 pre-existing added rows are unchanged, the altered return body
retains all 18 other attributes, and each of the four credit functions retains
all 18 authority attributes. Existing definitions restore before helper drops.
The revision check now requires a changed revision after real sale/inverse
history and exact equality of every other quote field; the untouched warehouse
comparison during conversion still requires whole-quote equality.

The 32-table PostgreSQL17 model additionally executes the exact retained and
candidate credit HPP proof, account/line semantics, and Native sale/return/
physical-inverse bodies. It reproduces the old canonical refusal, checks the
actual Native HPP journal against the customer-bound sealed plan, split and
multi-allocation cents, current-root recost, earlier inverse and replacement,
known-zero versus unknown, mixed PO/non-PO scopes, legacy allocations, unexplained
book cents and cross-product support. Monetary credit lifecycle, authority and
journal storage remain explicit model providers. The first model failures are
retained (alias collision, incomplete synthetic sale attributes and omitted
customer binding); correcting them adds no actual Native acceptance. Actual
Native6 and all five full-package gates are still required.
