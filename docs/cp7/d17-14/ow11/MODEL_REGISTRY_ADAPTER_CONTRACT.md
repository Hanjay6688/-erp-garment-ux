# Prospective model registry adapter v2 — private prototype

Four private functions, one private schema; no public facade, table, installer,
existing replacement, default activation policy or target consumer. All v1
dataset, build, capture/read and request semantics remain unchanged. This is
preparation for a separately versioned immutable capture and reviewed consumer.

`dataset(query, actor)` reuses the complete existing Native dataset extractor,
including actor-owned capture scope, actual immutable knowledge clocks,
corrected revisions, censored/unknown values, limits and fallback mean. It
selects the latest policy whose actual recorded clock is at or before that
history capture. It never attaches a later policy to older evidence. A policy
created today cannot borrow the older technical registry's registration clock.

`bind` verifies the existing dataset digest before extending it. The explicit
policy ID/revision/clock, registry ID and exact clock, promotion configuration,
actor/request and SHA256 of all fixed model definitions must agree. Only
explicitly allowed challengers enter the same existing evaluator; parameters
are unchanged from the reviewed registry. The baseline always remains the
comparison. Empty permission is supported as baseline-only without a fabricated
challenger or backtest. No factory threshold is supplied by the adapter.

The v2 digest includes the entire bound dataset, query/horizon, policy source,
the original dataset/engine hashes and the adapter/gate/policy/evaluator engine
hash. `assess` rejects any changed dataset digest, evaluates through the existing
model builder and recomputes admission through the existing gate. It retains
the daily vector and exact origin; it neither extrapolates a horizon nor flattens
the vector to a daily mean. A differing current policy source withdraws current
eligibility while preserving the earlier evaluation. Current source, engine,
identity, horizon and business-day checks remain required.

`cp7.native-model-assessment.v2` contains `evaluation` (the existing v1 evaluation
structure, or null for no permitted challenger), `evaluation_state`, `baseline`
(existing MEAN fallback, which may be unknown), `activation` and policy evidence.
`current_consumption_recheck_required=true`, `apply_allowed=false`,
`forecast_applied=false` and `production_go=false` are explicit. These private
functions do not accept arbitrary client datasets as a public API. The future
capture must supply Native-owned input and current server context itself; the
future consumer must recheck source, access, policy and date under the existing
global envelope before applying the vector once through the shared target kernel.

Local verification uses the actual existing dataset/build and all four adapter
functions. The 100 historical capture rows and historical policy are explicitly
synthetic, access and the `extensions.digest` SHA256 shim are controlled. These
are not Native history, Auth, catalog22, field accuracy or activation evidence.
Thirteen cases pass: unchanged v1, no policy, prospective allowed NAIVE100×7
with paired MAE4, actual-clock policy not backdating an older capture, one
microsecond cutoff, late registry, current suspension, empty permission in both
states, registry/source tampering, stale source/engine/day/horizon, actor/size
scope and query/engine digest/ACL/no-write boundaries.

First local run8PASS/4FAIL is retained. One actual adapter defect exposed the
legacy builder's null aggregate for zero challengers; the adapter now explicitly
reports baseline-only without calling that builder. Three negative-test groups
needed savepoints after expected PostgreSQL errors; the expected refusals and
SQL oracles were not relaxed. A separate active-empty case was then added.

Open: Native/catalog qualification, v2 immutable capture/read and current
access/exact replay, Auth/races/browser, reviewed activation and dated vector
consumption, full A composition/restore and independent acceptance.
