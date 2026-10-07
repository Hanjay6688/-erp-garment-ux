# F04 writer contribution: P05–P07 private kernels

This contribution implements the computation work that can proceed independently
of the active F03 writer. It does **not** declare F04 accepted or connect planning
to live ERP transactions. The base and ownership assignment are in ASSIGNMENT.md.

## Implemented

| Packet | Private functions | Result and limits |
| --- | --- | --- |
| P05 | `cp7_demand.history`, `availability`, `estimate` | Revision-aware sales lineage, draft reservation once, separate returns, observed-zero/stockout/unknown days, historical/restated grouping, explicit own/analog/manual demand assumptions. |
| P06 | `cp7_baseline.target`, `net`, `timeline` | DAYS or aggregate-horizon empirical quantile target; unique on-time supply; exact size; ordered BACKLOG/LOST_SALES simulations retaining earlier gaps. |
| P06 | `allocate`, `material`, `capacity`, `feasibility` | Global greedy allocation with P04 matching re-evaluated, shared source/yield/capacity limits, material consumption evidence, dated work-centre capacity, explicit batch rounding, STOP retains unmet need. |
| P07-A | `cp7_models.predict`, `score` | Eight deterministic NUMERIC kernels with independent numeric examples; MAE, signed bias, horizon total error, MASE/RMSSE with explicit undefined denominators. |
| P07-B | `window`, `promotion`, `evaluate` | Knowledge-aware rolling origins, fixed pre-registered configurations, complete paired folds, baseline/promotion guards, untouched outer holdout reported after selection. |
| P06/M07 | `cp7_baseline.dependencies` | Version/hash/completeness changes mark the captured result stale; missing evidence stays unknown; no live authorization claim. |
| P07/M08 | `cp7_models.compare_plan` | Frozen plan/version versus attributed additive PCS outcomes; partial/full correction, as-known/restated cutoffs and explicit unknowns. |

Twenty-two functions include five private validation helpers. All are invoker-only,
owned by `cp7_capture`; PUBLIC/anon/authenticated/service_role have no direct
schema/function access. No new tables, operational writes, public RPCs,
SECURITY DEFINER functions, dynamic SQL, migrations, credentials, scheduled jobs,
model registry writes, or client-side calculation engine are introduced.

Outputs retain the inputs/references and reason codes used by each kernel;
model results also expose kernel versions. Receipts bind all implementation and
dependency hashes. A missing essential input produces UNKNOWN/INELIGIBLE or a validation
error. Fixture parameters (including 3 folds, alpha 0.5, 12-PCS rounding and
example lead time) are **not operational defaults**.

## Private input boundary

The `cp7.*-input.v1` objects in these modules are **new private kernel inputs**,
not amendments to the frozen public DTOs or claims that CP6/F03 already exports
these shapes. Field-exact validators and `tests/cp7/families/f04/fixtures.mjs`
define executable examples. The integrator must construct them from one coherent,
authorized, complete server-side snapshot. A caller-provided `complete_scope`,
source reference or timestamp is not proof of authorization or capture integrity.

Rules needed by the source adapter:

- PCS are canonical integer strings; demand rates/material quantities are bounded
  decimal strings, never JS floating-point business calculations. Null means unknown.
- Times are explicit UTC ISO instants. Daily history uses Asia/Jakarta dates and
  excludes a partial last day. Source known time differs from effective business time.
- One lineage is one sales line through draft/post/cancel revisions. Its physical
  identity cannot change. Revisions are monotone source revisions. POSTED retains
  original `posted_at`; cumulative returned quantity is separate demand evidence.
- Availability history must establish full-day availability. Missing coverage is
  UNKNOWN. Stockout-day observed sales stay visible but do not become true-zero
  training observations. Estimated lost sales are never presented as observed fact.
- FG in availability is on-hand **after** posted sales; open drafts are reserved
  exactly once. Residual future demand must already exclude those committed drafts.
- The target is a physical size, never a displayed range label. RESTATED grouping
  uses membership from the same captured snapshot; AS_SOLD keeps historical membership.
- Incoming/direct WIP quantities in `net` must already be eligible and scoped;
  candidate quantities must come from the complete-scope allocation simulation.
  Netting is not a replacement for matching or allocation authorization.
- Reuse the pinned P04 dated-work ETA kernel and matching/position capture. The
  allocator's explicit ETA input must be server-derived, never a client ETA label.
- Capacity is a **single homogeneous work-centre scenario**, with selected unit
  minutes and existing load per dated non-overlapping window. Multiple routes,
  shared work centres and different SKU processing times require composed resource
  constraints. The greedy allocator is deterministic, not a global optimum claim.
- Empirical statistical target samples must be total demand over the exact
  `L + R` horizon. This kernel does not fit/calibrate a predictive distribution.

The additional M07/M08 input semantics, correction normalization and limits are
documented in `CONTINUATION.md`. The executable examples remain synthetic.

## Model behavior

Candidates: MEAN, NAIVE, MOVING_MEAN, SES, DAMPED_HOLT, SEASONAL_NAIVE, SBA, TSB.
Method parameters are explicit. This revision adapts model **states** from data
and compares configured candidates; it does not perform a hidden hyperparameter
search, learn holiday effects, or invent training data.

- SES uses the explicitly supplied initial level, or initializes from the first
  observation when it is null. Damped Holt additionally requires an initial trend.
- Alpha/beta must be in `(0,1]`, phi in `(0,1]`. Phi=1 is the undamped limit.
- SBA initializes positive size and interval at the first observed positive period;
  its correction uses the interval smoothing coefficient. TSB initializes occurrence
  probability from the first observed indicator, updates probability every observed
  period, and updates size only on positive demand. Initialization is versioned.
- Internal smoothing states and forecasts are rounded to 12 decimal places;
  forecasts are clipped at zero. Numeric oracle tolerance is `1e-9`.
- Null/censored periods make these dense-series candidates ineligible; they are
  neither compressed out nor interpreted as zero. Two complete cycles are a
  conservative technical eligibility rule for seasonal naive, not proof of seasonality.
- Configurations must predate the first validation target (registered by the end
  of the first origin's Jakarta day). A fold trains on days through its origin O;
  because a day is complete only after it closes, the forecast is issued on O+1 and
  admits only revisions known by the end of O+1 (Jakarta). Later backdated revisions
  cannot enter that training window. Actual scoring uses the declared evaluation cutoff.
- All requested folds must be complete and share the same horizon. Fold count is
  an explicit technical policy, not a statistical guarantee. Primary MAE must improve
  strictly beyond the configured margin; absolute bias and worst horizon-total error
  must pass their guards. Baseline wins ties; equal winning challengers prefer the
  fixed simpler-kernel order, then stable model ID, independent of input-array order.
- Holdout is evaluated only after selection; it is never used to re-tune or select.
  A holdout loss stays visible. `activation_status=REVIEW_REQUIRED`,
  `automatic_activation=false`; nothing is promoted into a live registry.

Primary method references checked 29 September 2026:

- [Hyndman & Athanasopoulos, damped trend equations](https://otexts.com/fpp3/holt.html).
- [Hyndman & Athanasopoulos, time-series cross-validation](https://otexts.com/fpp3/tscv.html).
- [Teunter, Syntetos & Babai (2011), original paper](https://pure.rug.nl/ws/portalfiles/portal/145394864/Intermittent_demand_Linking_forecasting_to_inventory_obsolescence.pdf).

These sources justify candidate methods, not parameters for this factory or a
claim that the most complex candidate will be more accurate.

## Reproduce the proof

With non-root local PostgreSQL installed under `/usr/lib/postgresql/<major>/bin`:

```sh
node tests/cp7/families/f04/run.mjs
npm test
python3 scripts/cp7_contract_receipt.py
npm run test:security
npm run build
```

The test runtime accepts no external DB URL. It creates a disposable cluster with
a private Unix socket, no TCP listener, no operational credentials, and destroys
that cluster on completion. Missing native prerequisites fail, never skip green.

For explicitly labelled **local development only**, install PGlite 0.5.8 outside
the project and point `F04_PGLITE_MODULE` at its absolute `dist/index.js` path.
The same SQL and fixtures run unchanged. CI rejects this override. No project
dependency or lockfile was changed. PGlite's PostgreSQL 18.3 WASM is not native
PostgreSQL or Supabase Auth evidence.

The existing CP7 Shell workflow runs `npm test` on this contribution branch;
the dedicated test starts the runner's native PostgreSQL, records its actual
version and writes `test-results/cp7-shell-proof/f04-private-kernels.json` into
the existing artifact upload. The workflow also runs existing regression/build/
shell-browser checks and CodeQL (JS/TS and Actions). Workflow bytes are unchanged.

## Handoff and remaining gates

Current 138-case native/source-bound evidence is indexed by
`CONTINUATION_VERIFICATION.json`; `HANDOFF.md` gives the review and integration
sequence. The unsuffixed receipt files are preserved historical 91-case evidence.

| Boundary | Status in this contribution |
| --- | --- |
| Isolated P05/P06/P07 fixture kernels | Writer implementation and local proof; native CI receipt tracked separately. |
| Original 48 framework files | Byte-preserved; contract receipt passes. |
| Authoritative CP6/F03 sales, stock, material, calendar capture | **OPEN**, integrator/source owners; no fabricated reader. |
| F01/F02 independent acceptance and X06 stale/Auth/race composition | **OPEN** at pinned base; kernel tests do not close them. |
| Real Supabase target-major/schema/Auth/browser integration | **OPEN**; disposable SQL tests do not substitute for it. |
| M07 integrated calendar/ETA/capacity invalidation | **OPEN**; private vector comparison does not qualify the composed runtime. |
| Resource composition, realistic full-volume performance | **OPEN**, separate ADR/P02/P07 gate; no factory throughput/SLA claim from tiny fixtures. |
| Background event/cron invalidation, persisted model registry and explanations UI | **OPEN**, canonical orchestration/shared wiring; no scheduler claimed. |
| P08 transaction apply and P10 prerequisites | **EXCLUDED / WAIT**. |
| Independent audit and production GO | **NOT GRANTED** by writer evidence. |

To integrate: refresh dependency hashes against the accepted F01/F02/P10/F03
revisions; map source capture and private inputs under the single integrator;
install the modules transactionally after the qualified P04 helpers; compose
authorization/stale checks; then replay full family and cross-family oracles.
Do not edit the frozen 48-file framework to make this contribution appear accepted.
