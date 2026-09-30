# F04 continuation: M07 dependency vectors and M08 plan outcomes

Scope remains P05–P07. These two additional pure, private SQL kernels and their
fixtures modify only the F04 owned paths. They neither read nor write F03, create
a plan draft, apply a plan, schedule work, or change the shared contracts.

## M07: `cp7_baseline.dependencies`

`cp7.dependency-check-input.v1` carries snapshot/scope IDs, captured/checked
instants, required domains, expected/current vectors and source references.
The vector entries use the frozen dependency shape: domain, revision,
completeness, fact_count and SHA-256 source_hash. Required domains must be
nonempty, unique and supplied by the authoritative snapshot orchestrator.

- Equal complete vectors are CURRENT even when the check happens later.
- Revision, hash, count or completeness changes are STALE. Calendar, lead-time,
  yield and capacity revisions are exercised separately. A backdate can change
  a hash without changing a count; a tombstone retains an authoritative revision.
- A missing current vector is UNKNOWN, not proof of deletion. An absent required
  domain or an unchanged partial/assumed/unknown vector cannot establish CURRENT.
- A known change plus missing evidence retains both: STALE and
  `evidence_complete=false`. Dependency order does not change the checks.
- The result includes old/new entries and precise reason codes. It preserves the
  captured inputs; it does not update the old plan or automatically recompute it.

CURRENT means only that the supplied vectors match. This function cannot prove
their authoritative origin, check live authorization, or close the X06 race at
serve/apply time. The integrator must derive the required-domain set, capture both
vectors and perform the current authorization/recheck in the proper transaction.
Do not derive a revision from `max(updated_at)` or remove tombstones from a vector.

## M08: `cp7_models.compare_plan`

`cp7.plan-comparison-input.v1` carries a frozen original plan, a separate actual
snapshot, assessment/capture/effective cutoffs, knowledge mode, capture flags and
immutable normalized actual effects. It supports **additive PCS outcomes only**;
it is not a universal revenue, cost, yield, or lead-time comparison formula.

The original plan retains its plan ID/version, original snapshot, scope, target,
physical size, metric ID, creation/information cutoffs, effective period and typed
planned value. KNOWN, ASSUMED and UNKNOWN remain distinct. Assumption IDs and
source references survive into the comparison. The emitted `comparison` uses
the existing frozen `plan_comparisons` item shape; no public schema is modified.

Each effect must name that exact plan/version/scope/target/size/metric. Partial
POSTs add quantity. A REVERSAL names its original POST and subtracts a partial or
full quantity. Exact duplicate events count once; conflicting identities, orphan
reversals in a complete capture, nested reversals and excess cumulative reversals
are rejected. No guessed attribution or automatic matching by SKU label occurs.

**Normalization rule:** a reversal here corrects the original metric outcome
and inherits its effective instant; its `known_at` is when the correction became
knowable. A correction cannot predate knowledge of its original. A return,
replacement delivery or physical movement in a later period is not automatically
this type of reversal. The source adapter must define the metric and normalize
the authorized source facts accordingly; no operational reader is invented here.

The plan period is `[period_start, period_end)`. Effects are included only through
`effective_through`, which cannot exceed `assessment_at`. The original plan must
exist by the assessment and cannot contain knowledge later than its creation.

| Mode | Knowledge used for actual outcomes | Meaning |
| --- | --- | --- |
| AS_KNOWN | Through `assessment_at` | Excludes later-known entries and corrections; historical reconstruction must be available. |
| RESTATED | Through the later `known_as_of` capture | Includes later-known corrections to the same effective period and counts those later-known events explicitly. |

Neither mode edits the original plan. Outcome differences never by themselves
prove the original decision wrong: `decision_verdict=NOT_INFERRED_FROM_OUTCOME`.
AS_KNOWN refers to the assessment cutoff; the distinct original decision cutoff
is retained in `original_plan.known_as_of`. They are not silently conflated.

Actual = unique selected POST quantities minus their selected linked corrections.
For a complete effective period, variance = actual − frozen planned PCS. During
an unfinished period, final variance is null; cumulative actual and remaining
quantity remain visible. A variance against an ASSUMED plan remains a comparison
against that labelled assumption, not an observed demand/forecast accuracy claim.

Missing capture, unavailable historical reconstruction or a selected unknown
quantity produces UNKNOWN actual and null variance. A separately labelled known
signed subtotal is diagnostic only, never a substitute for that unknown total.
A complete empty capture can establish zero. An incomplete empty capture cannot.

## Evidence and remaining work

The continuation adds 47 independent synthetic cases to the existing 91, using
the same SQL on the local development runtime and native CI. Receipts include
the new source files and the additional test-module digest. Both new functions
are invoker-only, owned by `cp7_capture` and denied to operational roles.

These cases qualify the named private boundaries only. Real plan persistence,
authoritative effect attribution, integrated calendar/ETA/capacity invalidation,
authorization/races, browser presentation and independent acceptance remain open.
The canonical M07 oracle is calendar/lead-time/yield/capacity validity; realistic
small/medium/large performance qualification is a **separate** ADR/P02/P07 gate.
Neither is closed by relabelling these synthetic cases.
