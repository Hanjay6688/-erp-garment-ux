# CP6 AG: sale draft and reserved stock must stay together

Owner: “VENI. VIDI. VICI. ERP. — I CONQUERED ERP.” Reliable data is supreme;
finance and reports, stock, and HPP remain the priorities. CP6 only;
`production_go:false`. Single writer on `competition/cp6-j-closure-20260911`.
Main/PR24/25/hosted databases/merge/deploy/CP7 remain outside this work.

Original AF `f46699865501b03f9fba3a8b188f3fd01eedf404`, tree
`f4dad6a6bccfffa1ba01f542cac36ac1d100c63f`, failed independent run
[35058065869](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35058065869).
Five native ordinary-caller counterexamples share one root cause: a reserved
sale draft can change SKU, warehouse, customer, physical time, or parent while
its stock reservation stays unchanged; posting succeeds and reports say READY.
Twelve controls passed, including AF opening immutability and legal RPC edits.
Entire original data/catalog/grants restored; auth/app users and clone residue zero.
Artifact10431820947 SHA256
`088995fd091ec7d979202f62f8bfb78a2678ed4bae3e047d740cd2c2a534e5e6`.
Attempts35057609185 and35057822254 stopped before business tests due to missing
bootstrap identity and reserved GitHub environment propagation; neither is a bug verdict.

AG changes four functions through one new migration. Reserved structural edits
must use the existing atomic save/cancel RPC; the legacy and v2 posting path
checks dimensions and per-lot quantities before HPP or journal changes. The owner
report gains a critical lineage check. Installation refuses dirty predecessors;
no posted history is rewritten. Legal price/notes changes and official draft
rebuilds retain existing behavior. See `docs/evidence/cp6-ag-family-disposition.json`.

Writer acceptance is conditional on all reports from **CP6 AG Sale Reservation
Family** passing on the exact commit/tree; a green routing workflow does not
prove execution. The combined gate follows successful targeted checks. It covers
142 relevant old cases, eight actual two-session cases, twenty maintenance
schedules, eight rollback negative controls, and exact AF restore (533 functions,
221 tables, data/owners/ACLs). Runtime verification binds all533 functions plus
157 views/defaults, including unchanged inherited capsule contents. It does not
rerun the historical500-case matrix or declare all CP6 complete.

Review the unmodified original AF oracle, AG family cases, native failure history,
source/runtime pins, new SQL and rollback. Reuse AF Native10 only for its original
source and source-qualified unaffected behavior. Affected guard/report/sale
paths require the AG reports. Check branch before editing and pushing; stop if
another writer moved it. Successor independent audit is **PENDING**; writer
acceptance never grants independent PASS.

Limits: native tests temporarily grant schema USAGE to authenticated and restore
it. No new table privileges are granted. Signed HTTP, UI, real CSV and hosted
execution are **BELUM TERUJI**. SalesPages remains an explicitly local simulation.
F/H legacy cases retain their original postgres SQL identity; they do not prove
ordinary helper access. New ordinary posting controls use post_sale_v2; private
post_sale EXECUTE grants stay unchanged. Detector controls with privileged inconsistent data only prove detectors; original
business counterexamples are the five ordinary AF transactions above.

Next reviewer: pin latest branch and exact evidence, verify fixes and normal
transactions, then attack remaining stock/journal/HPP/date/late-invoice/partial/
return/retry/import/application/report behavior. Treat variants of one cause as
one family. Use targeted tests first; announce a concrete need before any large
matrix. Create a successor only for a proven material issue after writer ownership
is clear, and hand it back for independent checking.
