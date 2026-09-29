# P03 — identity and production status

Status: CONTRACT_PREPARED; implementation and native execution NOT_RUN. This starts family 2 while the first family's final evidence is being preserved. The policy command described here is a proposed CP7 command, not an already connected operator feature.

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
