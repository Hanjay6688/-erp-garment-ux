# F03 Native reservation and size planner contract

The frozen P11 O06 and P10 O07 exits are now literal oracles against actual Native stock/sales writers and the existing shared Native planner. Two separate executions are declared; their run is pending. The frozen registry remains byte unchanged.

O06: Native FG100, actual draft reservation24, explicit selected future demand20. Available76 must project56 before and after actual invoice POST; POST cannot subtract the reservation again. A separate actual draft CANCEL must restore available100/projected80. The old source-cut archive must remain immutable after POST and become stale.

O07: two distinct Native sizes in one actual commercial SKU, S25/L5, with explicit selected demand S10/L20. The shared planner must return S surplus15 and L gap15. Aggregate30 cannot replace per-size rows. Master setup is administrative; every FG value comes from an accepted FOUND_AT_OPNAME POST, never injected stock or HPP. Planner reads must leave business state unchanged and cannot enable apply.

Provider: scripts/cp7_f03_planner_seam_cases.py. Qualifier: scripts/cp7_f03_planner_seam_probe.py, reusing the verified full stack through scripts/cp7_f04_netting_probe.py. Its seam mode runs only these two Native arithmetic cases. The existing82 Native/race/Auth/browser netting suite remains separate. Original reports, source/tree/provider hashes, exact restoration, backup and primary evidence must accompany the repeat before PASS.

First actual repeat atae74c41/run36865609138: O06 PASS, O07 INCOMPLETE during administrative fixture setup. Native correctly refused changing the size of an already-created immutable product, before the size stock/planner oracle ran. Originals are retained in evidence/f03-planner-seams/first2-ae74c41. The fixture now creates both product roots with their correct distinct sizes at INSERT; no existing identity is updated, no trigger bypass or product change. Repeat both exact oracles on the corrected source.
