# CAT-01: one catalog comparator defect, E06 and E05 symptoms

This is one writer/tool finding with two symptoms: PRE-07/E06 and E05 `public_schema_unchanged=false`. Both successors use the same `cp7_catalog_state.exact_public_catalog` and the same full-member restoration comparison. There is no second payroll-specific comparison policy.

The frozen `cp6_auditor_runner.PUBLIC_STATE` aggregates signature/definition-hash pairs with `jsonb_agg(... ORDER BY 1)`. Inside an aggregate, PostgreSQL treats that `1` as a constant expression, not the output-column ordinal or OID. It does not establish a meaningful pair order. PostgreSQL documents this distinction in [aggregate expressions](https://www.postgresql.org/docs/16/sql-expressions.html#SYNTAX-AGGREGATES); unspecified input ordering is discussed in [sorting rows](https://www.postgresql.org/docs/16/queries-order.html). A changed array position alone cannot prove that any function was dropped and recreated.

The CP7 adapter sorts the complete list of original pairs, retaining multiplicity, every hash, relation, public-row observation and other original field. No member is deduplicated, omitted or truncated. Eight observed-catalog sensitivity controls refuse changed signatures/hashes, missing or duplicated functions, changed relations and changed rows, and prove input is not mutated. The frozen reader/runner and original business oracles are unchanged.

## Source-bound qualification and preserved failures

| Evidence | Source | Native / races / Auth HTTP / browser | Catalog evidence |
|---|---|---|---|
| Original E05 failure, run37440579840 | `8f326d87034e817cdc6c53aff2b90f92ddb26f4f` |19 PASS +1 INCOMPLETE /3 PASS /1 PASS /2 PASS | Failed replay's individual raw catalogs and OIDs were not captured. Final restoration has69 complete matching pairs but different array order. Original failure remains INCOMPLETE. |
| New E05 qualification, run37443617960 | `d7a3f15a42aea60f91757223947ef2fc33cc8143` |20/3/1/2 PASS,26 total |42 complete retained raw snapshots,156 functions each. Every individual case and whole-group catalog matches, including raw pair order in this execution. |
| Fresh integration E06, run37440579630 | `8f326d87034e817cdc6c53aff2b90f92ddb26f4f` |4/1/0/0 PASS,5 total |10 complete retained raw snapshots,156 functions each; every member/hash/field matches. |

Every new E05 case ID and budget remains the original26. This is a new source-bound qualification after the tool correction, not a relabeling or retry-credit transformation of the failed run. Full root Originals, original full job logs, ZIP member hashes, Auth0→0, installation/backup/primary/advisor gates and complete restoration are retained at `evidence/e05-catalog/{first-8f,qualified-d7}/`. E06 Originals and a separate readonly forensic review are at `evidence/integration-8f/f03-e06/`. The original E06 failure remains at `evidence/e06-095-first/`; its missing individual-case witness is not reconstructed.

Run `scripts/cp7_catalog_retained_review.py <ORIGINAL_REPORTS.json.gz> <report-name> <output-json>` to independently recompute every retained full catalog and record the signatures/positions that move. The reviewer uses its own complete-list comparison and awards zero new Native case credit. This does not award independent P20 acceptance.

## Which functions moved, and where?

In both the new E05 and integration E06 **final installation/restoration** witness, the two moved signatures are:

- `erp_get_supplier_credit_v1(jsonb)` — definition MD5 `86b080c4b83e7c5df1558cae2faba1b3`.
- `erp_save_supplier_credit_v1(jsonb,uuid)` — definition MD5 `4412723b42ab9f62ab82078b0b50f20e`.

They swap adjacent positions; all69 final pairs, relations and public-row observations remain equal. The source-owned installation driver declares an EXECUTE grant to the existing public supplier-credit reader, installs the declared supplier-credit writer guard, restores saved original definitions, and drops the temporary roles/owned privileges. See `cp7_p09_procurement_probe.install`, `cp7_procurement_bundle`, and the E05/E06 `finally` restoration. These are qualification installation/restoration operations on the disposable clone, outside the replay transaction. The reader's ACL grant and the writer's declared definition replacement must not be described as evidence of `DROP FUNCTION` during a payroll write.

The **first E05 final restoration** witness has24 moved signature/hash pairs spanning access, patterns, attendance/HPP, reminders, cutting and laundry. `first-8f/CATALOG_FORENSIC_REVIEW.json` lists every signature, original MD5 and before/after position. These are final restoration positions, not the missing failed-replay positions. No actor that supposedly recreated those24 functions can be identified from an array permutation alone.

The actual `E05_REPLAY` provider invokes the ordinary payroll fixture, PAY, exact same-UUID replay, changed-intent refusal, REVERSE_PAYROLL and cached original replay. It contains no function DDL. The new execution records identical full catalogs across all20 savepoint cases. Its snapshots contain signatures/hashes, not OID/ctid/xmin; they therefore do not prove a historical drop/recreate never happened, nor can they reconstruct the first replay's exact delta.

**Classification:** the comparator defect is confirmed and the E05/E06 successor scopes are qualified. The exact cause of the historical individual-case raw mismatch remains **UNPROVED**. There is no demonstrated product payroll schema-mutation finding to close or silently waive. If an actual per-case OID/DDL witness is later supplied, investigate it separately against its exact source and owning fixture/product routine.

PRE-03 and PRE-04 remain separate writer work assigned in the prepared Claude handoff; their delivery is still outstanding. This checkpoint is not a complete CP7 audit freeze or production GO.
