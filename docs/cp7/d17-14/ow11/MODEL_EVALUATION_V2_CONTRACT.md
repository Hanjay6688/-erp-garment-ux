# Immutable model evaluation v2 candidate

The v2 capture records the prospective policy-bound dataset and assessment in a
new private immutable table. It reuses actual Native history extraction and the
same model/backtest engine. V1 functions, rows and request semantics are unchanged.
Seven private functions (the registry adapter's four plus three runtime functions),
two authenticated public facades, one schema/table; no existing replacement.
The policy stage is a separately checked prerequisite. Neither stage is in the
default installer and neither applies a forecast to a target.

- `erp_cp7_capture_model_evaluation_v2(p_query, p_request)` accepts only the same
  closed history/target/horizon query. It binds the exact raw JSON payload to the
  actor/UUID in its distinct v2 table and lock namespace. Canonicalization does
  not allow a changed raw payload to replace an existing request.
- Current access is checked before and after the global envelope and request
  locks, before replay, and before returning. New capture requires currently
  unchanged actor-owned history. Evaluation uses a server clock and current
  policy; client history, policy, parameters and forecast injection are refused.
- `erp_cp7_read_model_evaluation_v2(p_run)` returns the original assessment intact,
  plus a separately named `current_guard`. It does not rebuild a model or rewrite
  a saved evaluation. The guard rechecks Native history, engine, current policy,
  forecast origin/business day, clock and access. A stale or withdrawn result
  remains visible as historical evidence with baseline required for current use.
- `cp7.native-model-run.v2` contains run/actor/request/capture/query identifiers,
  immutable `assessment`, and refreshed `current_guard`. Only this named guard
  may change on exact replay. The immutable assessment and every stored field
  must remain identical. `forecast_applied=false` is explicit throughout.

The opt-in stage verifies exact bodies, owners, ACL/RLS/GUC, dependencies and all
22 catalog groups. Its declared delta includes precisely four internal parent
FK triggers, not blanket changes to Native history or registry tables. Pre-use
inverse uses RESTRICT and a savepoint so a dependent view cannot leave partial
DDL removal. Any v2 row requires composed backup/restore instead of pre-use
inverse. Full A composition and after-use restore are still unqualified.

Local tests execute actual v2 SQL against explicit synthetic capture/policy rows
with controlled access, history-freshness and SHA256 adapters. Eight cases cover
baseline/one-row replay, synthetic NAIVE100×7, withdrawal with unchanged history,
stale-source refusal, access/foreign isolation, guard clock/day/engine, raw
payload/immutability and last-row fault/ACL. All four FK identities are checked
against actual generated catalog values. The shared registry fixture retains
all13 previous cases. First8FAIL is retained: the local stub omitted the existing
snapshot parent's `extensions` USAGE grant; only the test bootstrap was corrected.

Native6 is separately predeclared: composed catalog/inverse, actual Native
baseline/v1/replay, real policy clocks with no posthoc historical approval,
actual posted sale/source retirement, current permissions/closed query, and
immutable/atomic/current-guard controls. No Native history or policy is backdated
to make a positive model win. Synthetic positive-vector proof remains explicitly
separate. The runtime limit stays8s, workflow45min, prior31/25/19 budgets unchanged.

Open: Native6 Original verification; actual Auth, races and browser; v2 client
recovery/UI; reviewed model activation and dated-vector consumption through the
single target engine; full A composition/after-use restore and independent audit.
Production and full OW11 acceptance remain false.

## Explicit client and immutable source header

The assessment includes a source header even when policy permits zero
challengers and evaluation is null. The UI can identify the Native snapshot,
actual knowledge time, product/size and exact policy registry clock without
manufacturing a model evaluation. This additive candidate changes the adapter
source hash and requires its own Native run; the 2263a57 Original predates it.

`nativeModelEvaluationV2.ts` validates the separate v2 wire contract, exact
actor/method/UUID/query, source/policy/model bindings, fixed parameter template,
paired fold and holdout evidence, decimal strings, microsecond clocks and
current guard. Reread compares the complete immutable response except the
current guard. No v1 parser or UUID namespace is repurposed. Recovery is durable
before capture and never exchanges uncertain work for a new request; stale tab
or selected history invalidates late responses. Initial database rollback may
release only a first request; uncertain retry remains held after access loss.

The explicit panel leaves horizon blank, displays archived daily forecast dates
and current policy/source/engine/date eligibility separately, and does not apply
forecast to targets. V1 and v2 pending captures block new evaluations across
both entry points. Existing production/browser locks and pending policy writes
are respected. Current access loss retires parent figures and preserves dirty
input. SQL fixture evidence is explicitly synthetic and is not Native/Auth or
production accuracy proof. Actual browser/transport qualification remains open.
