# P04 — conserved WIP, matching and remaining ETA

Status: IMPLEMENTED_KERNEL_NATIVE_NOT_RUN. F02 remains open. No operational
connection, production deployment, or independent acceptance.

## Authoritative implementation

Modular PostgreSQL kernels in `scripts/cp7-src/wip`, explicitly concatenated by
`cp7_wip_bundle.py`. No JavaScript quantity/planning engine.

- `reconcile`: one original input pool per exact size and ownership, positions
  of the same pool, ordered source transitions, exact prefix balances. Parent
  group totals are controls, not additional pools. Negative prefixes conflict;
  unaccounted input is UNKNOWN. Rework moves BS into WIP then back to FG/BS;
  rewash is a cycle of the same resource. A reversal references one prior exact
  transfer and must respect downstream consumption. Exits remain accounted.
- `match_target`: explicit confirmed destination and physical constraints are
  distinct from tariff/history hints. Known hard conflicts refuse; required
  unknowns need checking; optional empty metadata does not reject everything.
- `check_allocations`: all edges in one complete scope/scenario share remaining
  position and pool constraints. Filters are not accepted. Alternate scenarios
  are independent simulations, never reservations.
- `remaining_eta`: explicit remaining work only, versioned working intervals,
  no invented hours or leadtime. Insufficient calendar/unknown work gives no
  ETA/on-time boolean. History/assumption bases remain conditional. A calendar
  finish alone is not a capacity promise.

## Predeclared proof

14 native cases in `cp7_wip_cases.py` include owner O15 100 = 80 WIP + 15 FG + 5 BS,
rework 100 = 80 + 18 + 2, duplicate input, negative prefix, rewash/reversal,
size/ownership/partial captures, required versus optional matching, shared pools,
remaining-stage calendar and quantities above JavaScript safe integer. Isolated
accepted CP6 runner, explicit bundle, original ERP/public boundary restore.

## Required before F02 checkpoint

These tests use **normalized kernel fixtures**, not full ERP posting transactions.
The source adapter must next capture actual group/batch/size, laundry/QC and
rework facts in one MVCC snapshot, prove its normalization against the same
oracles, and expose only authorized immutable results. Existing sewing events
lack batch/size allocations: preserve quantity while marking the unproven
substage; do not divide by proportions. Ambiguous legacy links, missing/stuck,
opening stock, direct QC, failed wash/redispatch and rework need explicit
classifications. No sum of independent P02 runs can stand in for one capture.

P03 policy proof does not close O17 planning arithmetic. Global apply races and
connected sales/return R10 remain downstream obligations. `production_go=false`.
