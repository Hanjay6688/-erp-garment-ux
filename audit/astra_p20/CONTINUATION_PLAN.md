# Independent continuation — 9 October 2026

Product remains `2e605bb7d9b6b7903919b8df2be1443f1740140b`. Writer documentation head is still `a7f37aec69abfd24226abb77b8ad2f24973525f4`; this continuation is **not** a retest of a revised product. Prior failures, findings and first attempts stay intact.

The following additional oracles are registered before execution. Input/master setup and RPC transport may reuse writer helpers; assertions, numerical examples, concurrency orchestration and verdicts below belong to the auditor. No writer case functions are called as independent cases. Partial parent coverage is an audit task, not a product finding. PR44 remains subject to conflict-free acceptance by another auditor.

| ID | Independent additional oracle |
|---|---|
| AS20C-22-NET | Native eight-piece WIP with selected yield5/8, daily need13 over10days: need130, projected5, gap125; capacity cannot subtract the same WIP twice. Late supply cannot erase an earlier shortage. |
| AS20C-23-SPILL | Two calendar windows37+83 minutes, unrelated work61+7 minutes and captured work11+13+17 minutes: 11minutes remain, or3 whole PCS at3minutes each. Excess beyond the calendar is UNKNOWN. |
| AS20C-24-199 | Five completed groups totaling199 cut pieces remain insufficient; a sixth piece reaching200 meets the sample threshold. Independent Wilson computation determines the yield. |
| AS20C-25-REOPEN | Reverse a real BS disposal after an exhaustion proof. The reopened group cannot contribute finished-history yield; old proof rows remain unchanged. Re-dispose alone cannot reactivate a stale proof; explicit new proof can. |
| AS20C-07-DISCOUNT | Valid laundry invoices near the 32-bit-cent boundary, with nonzero discounts, conserve payable/product cost and balance every journal. |
| AS20C-08-SIZE | Unequal sizes11+7 with common tariff1.37 and extra service2.03 on only3 pieces of the second size: first size15.07, second15.68, total30.75. Receipt and FG attribution must preserve this. |
| AS20C-04-ACTOR | Reusing a receipt UUID across a different actor or action must not return another actor/action's successful response or duplicate stock. |
| AS20C-50-LATE | One combined73receipt/41FG/13sale/4return chain, with final material invoices arriving afterwards: final material AP889.83, GRNI0, physical raw32/FG32, revenue269.19 and AR132.16; exact recost destinations independently reconciled. |
| AS20C-01-CONSUMERS | Current permission revocation applies to staged cache/page/AI, reports and reminders; cached successful UUID is not a permission bypass. |
| AS20C-37-FAILED | A genuinely failed staged job remains retained just before7days, expires just after, keeps failure evidence, and cannot be cleaned as DONE. RUNNING jobs do not expire. Cancellation is assessed against actual supported states, not invented. |
| AS20C-27-UTF8 | Unicode target identities and empty scope preserve exact UTF8/page/hash semantics without silently dropping targets. |
| AS20C-05-LOST | Commit a receipt but discard its response, reconnect and reuse its original UUID: one document/stock/AP effect. A changed body still refuses. |
| AS20C-15-RACE | Two actual physical completions compete for one finite source: aggregate committed GOOD+BS cannot exceed source; replay cannot add another effect. |
| AS20C-28-WORKERS | Two staged workers contend for one job; completed work is unique, retained pages hash exactly, repeated DONE calls perform no recompute. |
| AS20C-29-INFLIGHT | Source transaction remains uncommitted while capture completes, then commits: freshness reports the change while the original result stays byte-identical. |
| AS20C-34-PUBLISH | Competing report revisions with the same expected revision produce exactly one coherent next revision; no duplicate/mixed sections. |
| AS20C-19-CARRY | Two payrolls compete for4 opening carry pieces at2.50: total reserved quantity never exceeds4 and the corresponding expense is incurred once. |

All execution uses disposable loopback databases/CI. Application files, writer branches, hosted databases, deployment and production are unchanged. Each first failure is preserved and classified before any targeted correction of an auditor fixture. `production_go:false`.

Additional independent oracles registered before their execution:

* `AS20C-11-RETURN`: real13x7.31 receipt, five physical units returned, portable credit36.55 to a distinct11x7.31 receipt. AP58.48/80.41 becomes95.03/43.86 with no new cash or stock effect; allocation dependency blocks premature reversal; inverse restores source.
* `AS20C-18-ROSTER`: two workers named Rina with different codes and explicit rates23.17/31.29; full/half attendance yields38.815 before cents posting and38.82 accrued once. Distinct identity, attendance records, and existing work6000 stay separate.
* `AS20C-09-CLOSED`: sell13, return4, then correct sold quantity12 after closing the sale's economic day. Original journal dates remain unchanged, new GL posting stays after close, net AR102.25 and FG33. The approved ability to correct closed economic history is preserved; no invented blanket refusal.
* `AS20C-22-TIE`: independent17-piece graph and selected yield1. Needs tied except stable IDs A/B must allocate11 toA then6 toB regardless input order; an earlier real deadline outranks the stable-ID tie. Unknown timing is a review item, not silently feasible supply. Kernel scope is explicit.

First money attempt `37892630236` passed discount, size and whole-flow cases. `AS20C-04-ACTOR` stopped at an auditor typo (`erp.material_purchases`; actual table is `erp.material_purchase_headers`) before its cross-actor checks. Preserve the original trace and rerun only that unfinished case in the extra-edge suite; no product/oracle change and no rerun of the three passing cases.

First state attempt `37892863976` passed genuine FAILED retention and Unicode transport. Consumer-revocation setup stopped at the positive reminder control because the generic fixture creates a custom role code, while reminder access explicitly admits internal OWNER/ADMIN/STAFF role codes. Use an actual STAFF fixture with the four required view permissions before capture, then revoke the same WIP permission. Original first failure remains; only the unfinished revocation case is rerun.
