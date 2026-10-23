# Next implementation: bounded staged analysis (not yet qualified)

Native11 qualifies work metadata. Native3 qualifies full bounded history inputs
(2000 synthetic products,202000 movements,1414ms). Native4 qualifies every raw
stock row's digest (202001 visible rows,2207ms). These are components; actual
staged DONE/source freshness/checked SAVE2000 remain open. Parent5/16.

The raw Native capture must stay INCOMPLETE above its existing50000-row bound.
Do not overwrite status, fake a completed job, shrink the fixture, or raise8s.
Use an explicit new request/reference contract and real Native staged jobs.
A owns default installation/types/registry/global after-use census/full chain.

## Source factory

Derive read-only copies, keeping every other Native query/guard unchanged:

| Function/source | Required adaptation |
| --- | --- |
| `cp7_supply_native.source_parts_within(integer)` in frozen `planning/supply-source.sql` | Replace only `cp7_baseline_native.source_within` with qualified `cp7_reorder_inputs.capture_baseline`. Keep `wip_source_parts`, complete global graph and clocks. |
| `cp7_schedule_native.source_within(integer)` in `planning/schedule-scenario.sql` | Use those copied source parts; keep actual Native schedule source. |
| `cp7_netting_native.source_within(integer,integer)` in `planning/netting.sql` | Use copied schedule source; keep all matching-product bounds. |
| `cp7_analysis_native.source_within(integer,integer)` in `planning/analysis.sql` | Use copied netting source; retain material/fabric/engine source and operational finance DEFERRED. Bind new producer code. |

The capture path computes genuine `cp7_history_bounded` inputs and
`cp7_history_reference.stock_digest` at that same captured clock and MVCC
statement. The freshness path needs raw source/digest/code identity, not another
full history/target calculation. This matters for two full source checks inside
8s checked SAVE. Hash the digest's `rows_sha256`, not its changing captured_at.
Do not put the selected demand query into the work-calendar fingerprint: work
assumptions must remain usable across queries when the work source is identical.

A producer hash must bind new private function bodies and both helper versions.
New reference metadata must distinguish raw capture status from complete SQL
history coverage. The immutable query/job/reference must agree. No browser
supplies coverage, source hashes, eligibility or DONE.

## Counted existing-function adaptations

Use a new B module with exact original/new bodies/owners/ACLs, additive facade,
strict catalog delta and inverse. Never edit frozen `cp7-src` or A bundles.

| Existing function | Required behavior |
| --- | --- |
| `cp7_supply_native.fingerprint(jsonb)` | Its actual current body is `cp7_production_stage/sql/cp7_supply_native__fingerprint.sql` (target-unified-2), not the older frozen body. Only the new reference adds full stock digest/producer identity. Old reference input must return the exact old hash. The work hash excludes calendar/query; Native schedule/netting/analysis fingerprints inherit it. |
| `cp7_analysis_stage.run_scenario_unit(jobs,units,jsonb)` | Old references execute the exact old branch. New dense references use a private derived Native history preflight and full prepared history/current-stock slices for HIST_ROWS/HIST_STOCK. Preserve Native event validation, ordering, BASE_ROWS, WIP/schedule/netting/allocator/page kernels and all unit limits. |
| `cp7_analysis_stage.analysis_skeleton(...)` | Distinguish complete derived input coverage from raw status. Preserve genuine UNKNOWN, WIP conservation, financial deferral and existing warnings. Add a truthful raw-incomplete/full-SQL-input warning. Do not claim every forecast or material feasibility is known. |
| `cp7_analysis_stage.check_source(uuid)` | Select the same versioned raw-source factory as the immutable job. Keep DONE/actor/K2/current-access checks; old jobs retain their old factory. |
| `cp7_schedule_staged_review.workspace(uuid)` | Select the reference's factory. Old response remains v1. A new response may explicitly label complete bounded coverage while preserving raw INCOMPLETE; client must validate its version/real request/run/hash. |
| `cp7_schedule_staged_review.save(jsonb,uuid)` | Read the real job reference for pre/post source checks. Keep request/global locks, fresh access, CAS, immutable UUID replay, Native config validation and atomic metadata. Post-check must include full raw digest without rejecting its own calendar write. |

Derive the new public request from `cp7_analysis_stage.request(jsonb,uuid)`:
real `create_job`, one Native snapshot, same limits/access/idempotency/K2.
Do not silently turn an existing old UUID into a new-method job. Existing
step/status/pages/plan v2 readers should use those genuine Native rows.

The new stage must mask its exact declared changes in a savepoint before
running the unchanged11-stage oracle, then restore all22 catalog groups. Its
inverse must refuse any real new-method job/use before DDL and reject unknown
external callers. Do not replace the package's after-use restore with this
pre-use inverse.

## Client and qualification

Persist the new request method/version with the UUID before sending. Recover
legacy native source/capture/SAVE payloads through their original routes. The
Native v1 operational query has exactly from_date/group_mode/through_date;
finance_mode was a rejected extra field. Generic recovery's optional finance
mode includes other financial modes, so do not pass it to StagedRequest or
silently ignore it in work-source recovery.

Work review must use the same versioned source as the analysis. Save calendar
metadata first, then capture a fresh analysis containing that calendar. Do not
claim the pre-save analysis stayed current. Preserve dirty forms and explicit
source adoption. New quantity calculation should use the existing paged staged
analysis rather than the old1000-product whole-netting capture. Coordinate any
shared UI/finance caller with A; do not edit App/generated types/defaults.

The real browser has concurrent initial-auto calls on the same request endpoint
(`initial_auto: ENSURE`, null p_request). Observe the work form by its durable
UUID and complete selected query; do not catch the unrelated automatic response
or disable automatic analysis to make the test pass.

Required progression: source parity/full raw freshness/old-reference contracts;
real staged DONE without status overrides; K2/access/races; genuine checked
SAVE2000 three fresh UUIDs under8s including both source+feasibility checks;
replay/refusals/no physical or monetary effects; after-use restore; A full chain.
The synthetic volume dataset may need explicit synthetic Native policy/profile
fixtures for its extra products, so global allocation can be known. Label those
as performance fixtures, never owner defaults or proof of factory business data.
Do not fake reference, hash, feasibility, job state or receipt to bypass that.
