# P03 — identity and production status

Status: WRITER_NATIVE_PASS for production policy and captured/current identity. Full F02 remains IN_PROGRESS; operator UI and canonical WIP source integration are not yet connected. Evidence: [verification receipt](evidence/p03-policy/VERIFICATION.json).

Tested backend `c56c3bb9b84a8d24e8dbe7a3b22bbd98b4d39111`: [run 36509688817](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36509688817), 10 native + 4 transaction races + 1 real Auth/HTTP case, plus fixture smoke. CP6 restored and advisor gate passed. App source-ownership fix `93fa65c2220da62e1b98a77e069b4b04af2816b6`: [app/build/browser/security/CodeQL run 36510654525](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36510654525) passed. This is writer evidence, not independent acceptance.

## Existing authorities and exact scope

- The accepted CP6 BF commercial master owns `erp.bf_skus_v1`, dated versions and membership. Physical root/size/version remains `erp.products`. CP7 does not edit these tables to set production status.
- Existing BF membership changes use advisory lock `BF:COMMERCIAL_SKUS` after the FG/HPP lock. A production-policy writer may take the commercial lock to validate a bulk reviewed membership, but must never subsequently acquire the FG/HPP lock and invert the existing order.
- Production state belongs to commercial SKU and the reviewed dated member set. It is separate from `products.is_active`, portal visibility, sale permission, existing WIP and physical stock.
- A policy records ACTIVE/PAUSED/STOPPED, reason, optional review time, actor, request identity, expected policy version and exact reviewed commercial version/member list. A passed review time does not change the state.
- No policy or changed membership is reported as unreviewed/unknown. It does not silently activate new members or create size overrides. Existing operational commands retain their accepted CP6 behavior.
- Read and write access are explicit and checked before replay. The initial permission mapping is read: `master.product.view` + `production.wip.view`; write additionally `master.product.manage`. The private policy writer is separate from the read/compute principal and can write only CP7 policy/command history.

## Predeclared native oracles

| Case | Expected |
|---|---|
| Singleton, alphanumeric and uneven member sets | IDs and exact size determine membership; no splitting labels or assumption of three sizes |
| Stop one SKU | Policy STOPPED; sibling unchanged; no `is_active`, stock, HPP, journal, sales or WIP mutation |
| Past PAUSED review date | Remains PAUSED; due review is information |
| Same request and payload | One committed outcome; replay with current authorization |
| Same request, different payload | Refused; no second policy row |
| Bulk two SKUs; second stale | Entire bulk refused; first SKU unchanged |
| Membership changed after preview | Entire bulk refused; no member activated by inference |
| Future membership becomes current | A previously reviewed set cannot silently govern new members; review required |
| Two conflicting revisions | Exactly one accepted; the loser must refresh |
| Role revoked while request waits / before replay | Refused; no partial policy history or cached disclosure |
| Read/compute principal invokes policy writer | Permission denied, including with a broad user JWT |

The P03/P04 canonical lineage graph and O15 conservation remain required work in family 2. P03 status proof alone cannot close O17's target/gap/start-new arithmetic, which must also be exercised through the planning engine. No production connection, independent acceptance or CP7 closure is claimed here.

## Additional executed controls

- Immutable source run preserves original SKU B and 6 PCS while the explicit current restatement reports SKU A. Other actors cannot read the run.
- Price-only version changes set `commercial_version_changed=true` and `group_changed=false`; policy remains applicable when its reviewed member set is unchanged.
- A real Auth session can read capture/current identity labels. Revoked/inactive users cannot replay the policy command.
- Transport decoder refuses unknown fields (including financial extras), missing/duplicate/overlapping members and a partial or wrong-request committed outcome. Exact revision strings survive values above JavaScript safe integer. Decoder currently lives in `contracts/cp7`, is typechecked/tested, and is not shipped through an unused browser import.
- Earlier setup-only failures and their corrections are recorded in the receipt; none was counted as a passing product test.
