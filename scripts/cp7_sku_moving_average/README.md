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

The 639 exact rows cover 12 tables, 19 explicit/implicit indexes, 183 table
and index columns, 132 constraints, 202 triggers (including both ends of
47 foreign keys), 12 private functions, 24 row/array types, their 24
implementation rows, and 12 deny policies. The other catalogue groups remain exact except for one declared schema USAGE
lease to the existing private FG reader role. Every added row must be present with its exact metadata;
matching a name prefix is insufficient. Existing objects remain frozen
except for the already declared, exact function-body substitutions and that
one exact reader schema lease.

The pre-database controls reject each missing or altered expected row,
undeclared additions in every catalogue group, changes to existing authority,
and replacements of an all-22 group. The actual Native5 run, all used-state
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
do not replace the actual Native5/used-inverse/whole-package qualification.

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
