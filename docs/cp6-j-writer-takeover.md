# CP6 J writer takeover: rollback chain and payment conservation

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.

Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.

## Starting evidence

The starting commit is `90848bfa7b2853953f17cfab8782d81555604777`, tree
`bd6ae2426af98b7186bda7ea8850be0c7cb64b0e`, on draft PR #24. Independent
audit I at `a465e24067c1d17f3b07bcf72851f31271475525` remains FAIL: I-01
invoice allocation identity, I-02 reversal chronology, I-03 ambiguous conninfo,
and I-04 a permissive negative-test oracle. The J migration and its tests address
these findings, but writer evidence cannot confer independent acceptance.

[Full-schema run #120](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34512459436)
passed J business regressions, all 100 F/G/H/I/J schedules and the main J→I
restore, then failed the I trusted-capsule step with `UndefinedTable`. Subsequent
rollback levels, final no-residue verification and the final manifest did not run.
The two High CodeQL annotations on J guard JSON storage/logging also remained
open. The successful matrix does not make that run a complete proof.

## Root cause and repair

The shared matrix fixture helper unconditionally stripped J from every clone.
The I trusted-capsule guard invokes it after the main source has already been
restored to I, where the J capsule has correctly been removed. The helper now
requires an explicit I source for that caller and defaults to J for the full
matrix and J guards. Before any rollback or fixture write it verifies the clone's
latest platform ledger identity and all F–J markers/capsules. Unsupported source
generations, orphan successors, missing capsules and newer targets fail closed.
Every installed generation still passes through the existing admission/drain/
trusted-pin/restore executor; no migration or rollback SQL is rewritten.

The J restore summary emits counts and verified structural outcomes. Detailed
observed function hashes, owners and ACLs remain in the maintenance report. Raw
database-returned values are not copied through the summary serialization path.
CodeQL clearance requires a fresh scan of the successor commit.

## Evidence requirements

- 18 mocked orchestration checks exercise all nine supported J/I source-target
  plans, four invalid requests, four source-state faults and summary projection.
  Reintroducing the unconditional J strip or a permissive source verifier must
  fail the oracle. These checks are explicitly not native PostgreSQL proof.
- The 31 endpoint tests and permissive-validator negative control remain intact.
- Native payment proof retains I-01/I-02 and adds five invalid replacement paths:
  unreversed predecessor, different customer, same invoice, amount drift and
  original payment-clock drift. A valid correction plus repeated original
  reversal must leave one replacement, invoice allocations 0/40, unchanged net
  cash, receivable reduced exactly 40, and unchanged stock/FG valuation/COGS.
- Full CI must again prove 100 unique native schedules, 25 actual backend-body
  entries, J→I→H and all remaining predecessor restores, real Auth/role boundaries,
  browser behavior, frontend/security gates and physical cleanup. The final
  artifact must bind every payload and source to the exact successor SHA/tree.
- The I guard's setup artifacts must show I→target stripping and no second J
  strip. Keep the historical #120 failure in the handoff; never replace it with
  the successor result or reuse #119 as evidence for a newer SHA.

## Scope and owner rules

Payment allocation correction changes allocation, not inventory or production
cost. Posted corrections stay linked and append-only; retries cannot duplicate
cash, stock or entitlement. Existing regression gates retain physical-prefix
conservation, paid failed-wash cost/custody separation, partial FG/WIP HPP,
zero-fee rewash, source-bound stock, payroll/claim entitlement and readonly
legacy boundaries. A check of those gates is not a claim that CP7 is implemented.

CP7 rev3 remains the separate owner plan: WIP before SKU candidate, shared-source
capacity counted once, per-date ETA, Active/Pause/Stop, optional pattern metadata
with immutable production lineage, and honest unknown forecast data. Follow-on
gates remain CP7.5 cleanup/rebaseline, CP7C stress/automation and CP8 independent
cutover. This patch adds no CP7 scope and changes no hosted database.

The writer may prepare a re-audit candidate after complete exact-commit evidence.
Independent audit PASS, merging, UAT application and production release remain
separate decisions. PR #24 stays draft and unmerged; PR #25 remains separate.
