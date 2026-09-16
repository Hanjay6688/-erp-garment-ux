# CP6 AH return family: writer qualification, independent review pending

Read `cp6-efficient-audit-rule.md` first. Keep CP6 and `production_go:false`.
Only `competition/cp6-j-closure-20260911` is writable. Check its live ref before
writing and pushing; stop if another writer moves it. Main, PR24/25, hosted
databases, merge, deployment and CP7 remain outside this work.

The predecessor is AG `119f8f133131eaf373f08cc45b7b3d6fc27a3d3e`, tree
`bd7dd026d40e64f08f03e122338d8a82ebfd292c`. The AH source delta starts at the
additional writer harness `961c592e22b6582ba7c5b07d612e32a9dbbae28b`.
Obtain the exact AH commit/tree and native/CodeQL status from its completed
run and final checkpoint. This document alone does not claim a successful run.

Additional checking of original AG proved 6 counterexamples, 15 passing
controls and 0 incomplete cases, run 35066611261, artifact 10434213550,
SHA256 `2b5e604bcf42fc6185f4de50ed8be5bb6a403ec93661028e6b4ef24df39e48c3`.
Three counterexamples are grade variants of one wrong warehouse comparison.
Other examples are excess returns against one allocation, a draft return
blocking its unposted source sale, and ordinary draft creation failing while
reading locations. The original artifact's summary label for ordinary draft
creation is stale; its explicit `RETURN_ORDINARY_DRAFT_CREATE` case records
the observed permission failure. Preserve both rather than rewriting evidence.
These were further writer checks, not independent acceptance of AG.

Two further reference-access counterexamples were proved on exact original AG
in run 35070228607: both allowed OWNER draft writes failed while reading a
restricted reference. The identical administrator control and complete business
flow passed with the report READY. Artifact 10436136832, SHA256
`0188e4602911fdf78f3b823e5173da38b912bf18cc0bf88633af5e3e6a985805`.
That workflow intentionally stopped after the two probes, before combined tests.
The previous probe's invoice fixture ID collision is preserved as INCOMPLETE;
it is not a business bug. Invoice posting remains a private backend dependency.

AH changes five functions:

* Return normalization requires an active posted source. Its private trigger
  reads its references as its owner with an empty search path and an explicit
  internal caller check. No table SELECT or trigger EXECUTE grants are widened.
  The same confined validation is applied to `validate_work_completion()` and
  `validate_vendor_invoice_item_lineage()` for the proven related draft paths.
* Posting derives eligibility and total returned quantity from the selected
  allocation ID; stock receipt uses the independently selected destination.
  Other allocations remain separately eligible. Existing locking, refunds,
  linked corrections, HPP synchronization and commercial journal rules remain.
* The main financial report checks posted return allocation/source/customer/
  date relationships, aggregate quantity, and matching active stock facts.

Posted history is never rewritten. Installation refuses existing invalid
active returns or draft dependencies on an unposted sale. The rollback capsule
contains five exact predecessor functions and a 220-relation data boundary;
pre-use rollback must restore all 533 functions and 222 tables of AG, including
data, ownership, privileges, markers and the original platform source ledger.

The native workflow is gated in this order: 2 exact-original AG reference
counterexamples; 9 admission controls; 82 focused
cases and 31 report controls; 142 combined business oracles; 8 actual two-session
races; 20 maintenance schedules; 8 atomic rollback refusals and exact AG restore.
Failed phases are preserved and prevent later gates. Synthetic corruption
controls prove detector behavior and are not new business bug discoveries.

Evidence reuse is dependency-aware: admitted SQL through AG and old business
oracles are byte-identical, pinned runtimes and original artifacts are verified.
The changed return/report and work/invoice draft paths invalidate prior coverage for those paths, so
the relevant combined cases run after focused checks pass. Four old workflows
route only the complete pinned AH delta and retain their original validation
bodies byte-for-byte after stripping routing. The three-function return wave
already passed Native 35069184362 at `916951c512977698d7d50fd85f626de954f55b9c`;
the two further proven reference paths require a consolidated qualification.
A green routing job is not the
AH native result and is not a rerun of the historical 500-case matrix.

For independent review: verify identity, source pins, actual artifact payloads,
negative controls and the disposition file. Attack return allocation boundaries
across grades/warehouses, concurrent post/reversal, late invoice recosting,
partial payment/refund corrections, backdate versus system time and report
lineage. Use normal business operations on the original candidate before
claiming a material bug. Finish all affected paths before one relevant combined
gate; do not rerun A-Z merely because the candidate letter changed.

Limits: native authenticated/OWNER calls use a temporary schema USAGE fixture.
Master data uses the fixture administrator. HTTP, UI, CSV and complete role
coverage remain BELUM TERUJI. SalesPages is a local prototype without a sale/
return backend call; no separate executable return import producer was found.
Source inspection of those surfaces is not end-to-end proof. Independent AH
review remains PENDING even if the writer workflow succeeds. This package does
not mean all CP6 is finished.
