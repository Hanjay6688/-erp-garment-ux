# BB intake, writer head 72bf53f — probe tool stops after three cases

Writer head `72bf53f8d808e18fd3e2866491f28667c1b6193d` adds `supabase/dev/cp6_bb_t1_family.sql`, `src/initialImportCatalogBB.json`, builder/probe and workflow. Compare d1bc8ad..72bf53f is one commit; existing BA release package and 25 T3 files are unchanged. This is development T1, not release acceptance. The frozen ALL22 oracle and its ALL-S01 errata are in `out/r9_all_oracle.md` and `out/r9_all_oracle_errata.md`.

Writer Actions [run 36126427534](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36126427534): before job `108043489572` FAILURE, after job `108043489771` FAILURE. Both install baseline and run three cases, then stop with `AssertionError: dict() got multiple values for keyword argument 'case'`. At `scripts/cp6_bb_probe.py:325`, `direct_date_finding` prepares `evidence=dict(case=case, ...)`, then lines 327–330 call `dict(evidence,status=...)`; the case result wrapper already passes a case identifier into the reporting path. This is a tool/result-shape collision to diagnose precisely; no product regression can be concluded from stopped jobs. All 24 planned cases remain T1 **UNVERIFIED as a complete group**.

| Job | Three partial cases before stopping | Completion |
|---|---|---|
| before `108043489572` | P02/S01/W05 settlement cycle each `NO_ROUTE` | `INCOMPLETE` due tool exception; 21 cases unexecuted |
| after `108043489771` | P02/S01/W05 settlement cycle each `PASS` | `INCOMPLETE` due same tool exception; 21 cases unexecuted |

The first three tests check settlement/reversal arithmetic and bank, including S01 residual 70→45→70 and bank 100→125→100; they do **not** settle the journal direction of the 70 opening AR (ALL-S01 errata). Do not re-label 24/24 PASS. The writer's `cp6-bb-t1-probe.yml` must complete before claiming T1; keep a fixed source hash and compare exact case IDs/results on the next head. Once writer fixes the probe, rerun independently on a disposable clone and add explicit S01 opening journal direction check `Dr AR 70 / Cr OPENING_EQUITY 70` (contract M:934–938 and frozen oracle internal comparison A02).

Severity P3 **test tooling**; no product finding shown. Global CP6 HOLD, audit_complete=false, production_go=false.
