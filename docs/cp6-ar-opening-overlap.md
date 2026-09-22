# AR — opening overlap repair under qualification

Parent: `3ddf32fde459ab437afb07b762bc6246f97744d5`. This successor follows
the AQ probe that reproduced ten opening balance types posted twice through
the public import RPC followed by the canonical native legacy function.

The common `erp.post_opening_balance(uuid)` now refuses overlapping POSTED
openings when one header belongs to a migration batch and the other is legacy.
This is symmetric; dates, amounts and quantities are not deduplication keys.

| Type | Overlap identity |
| --- | --- |
| Receivables/payables | Same balance type and customer/supplier/vendor/contractor |
| Cash/bank | Same cash account |
| Material | Same material and location; the same roll or a roll-less aggregate |
| Finished goods | Same product, effective warehouse and grade; use the prior posted movement's warehouse/grade |
| WIP | Model, stage and contractor; an unspecified dimension includes its details |
| BS | Product/model and responsible contractor/vendor; unspecified dimensions include their details |

The inherited import registry still governs separate source documents and lots.
AR does not claim to detect duplicate legacy-only records or every duplicate
import source across batches. A different warehouse, roll, product/size, party,
or non-overlapping production position must remain admissible.

Native post already holds `FG_HPP_SALES_V2620C`. Import FINALIZE and native
prepare now acquire the same transaction lock before batch/header/source locks.
The check runs on locked, current opening lines before economic effects. Canonical
post requires READ COMMITTED so a stale repeatable-read snapshot cannot bypass
the post-wait check. Existing journal, HPP and stock posting logic is unchanged.

Three function bodies change, with original owner/ACL retained. SQL install and
pre-use rollback require the pinned AQ catalog, exact prior migration history,
closed/drained disposable database, full business-data preservation and a private
rollback capsule. Previous migrations and historical source gates are unchanged.

Qualification is defined in `.github/workflows/cp6-ar.yml`: ten sequential
import→legacy cases, ten legacy→import cases, ten valid non-overlap controls,
twenty real concurrent schedules with observed advisory-lock blocking, winner
abort recovery and same-header races. Exact subledger, journal, material/FG,
WIP and BS effects are checked. Inherited connected lifecycle cases run on AR.
Two nonempty pre-use install/rollback cycles and post-use rollback refusal are
required. Reports bind source SHA/tree, SQL hashes and the complete runtime catalog.

At initial implementation there is **no fix PASS claim**. Native legacy checks
use the actual canonical function with owner claims in an administrative
connection; this is not a claim that the private ERP schema is exposed over HTTP.
Public import uses the ordinary authenticated database role and public RPC.

CP6 remains HOLD. `production_go: false`, `hosted_migration_installed: false`,
`independent_acceptance: false`. Auth/browser and independent combined-family
acceptance remain separate gates; predecessor evidence is not relabeled as AR.
