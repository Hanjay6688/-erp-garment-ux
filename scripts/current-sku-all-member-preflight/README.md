# SKU group inverse: check all members first

Actual run40928155690 on published bd2cd02c0b724f87f6f1d8628f8227dd30c513a4
passed all seven original core callbacks and one cost callback. Its other
cost callbacks stopped at an invalid BC timestamp and at an actual no-effect
failure: reversing the second member allocated audit/stock sequence values
before the first member refused an active cost source. Statement rollback
restored rows but could not restore those sequence values. Thirteen later
race/permission/browser callbacks were not reached. The complete outer backup
restore restored all original catalog, rows, sequences, roles, CP6 and advisors.
This result does not qualify a combined23 pass.

Only `cp7_sku_conversion.action_v1` changes here. Under the existing pocket and
global FG locks, it locks every member conversion in UUID order and rechecks
the caller's permissions after waiting. Before invoking any Native inverse,
it checks every member using the same existing BE and Native predicates:
BE source exists, no posted cost/recovery or receipt dependency, status is
POSTED/REVERSED, no active downstream for a posted destination, and a posted
conversion journal exists when the original allocated value requires it.
The journal threshold uses the Native numeric(24,6) assignment and 0.005 limit.
Existing BE/Native guards remain the authority during each actual inverse.
The six captured Native function definitions, Native cost/stock/financial
calculations, all original assertions and every other product function stay
unchanged. No sequence is reset or reseeded.

`local_check.mjs` executes the exact before/current coordinator and unchanged
BE inverse/dispatcher against explicitly declared local Auth, stock inverse,
idempotency and ledger doubles. It reproduces the old leak, then checks whole
local row/sequence/session equality for cost, receipt, downstream, missing BE
source, invalid status and missing Native journal refusals. Lawful released
dependencies still permit both member inverses in the original order; exact
UUID replay and direct member refusal retain the complete local census.
These ten checks provide no actual Native money, Auth, browser or full
installation evidence. `FIRST_LOCAL_CENSUS_SETUP_ERROR.log.gz` retains the
initial local census setup error (42809); the fixed census names both sequence
fields explicitly. Production guards and the oracle were not weakened.

Run with an explicitly selected local runtime:

```sh
F04_PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node scripts/current-sku-all-member-preflight/local_check.mjs
python3 -B scripts/current-sku-all-member-preflight/source_check.py
```

Fresh qualification must declare this one product transition, retain bd2's
original failure reports and rerun original Native7 plus cost3, races3,
permission waits6 and real-Auth browser4 with the full vendor engine and all
five package gates. A successful isolated case can allocate sequences even
when its enclosing savepoint later rolls back; complete per-run sequence
restoration is established only by the full outer backup/package check.
Known refused commands and exact replay still require unchanged all-sequence
snapshots. Group recovery, independent acceptance and production_go stay false.
