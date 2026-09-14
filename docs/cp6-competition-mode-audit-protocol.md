# CP6 competition-mode audit protocol

This protocol is shared by every CP6 writer and independent auditor. It is an
acceptance contract, not a claim that a particular candidate has passed.

## Evidence levels

1. `STATIC_QUALIFIED` identifies a concrete source path and an executable
   oracle. It is never a runtime pass.
2. `LOCAL_QUALIFIED` reproduces an observation in an isolated local database.
   It is never the final candidate pass.
3. `NATIVE_QUALIFIED` establishes a bounded observation on the exact Git
   candidate and pinned disposable native runtime. A qualified counterexample
   can reject a candidate even when subsequent regression steps were skipped.
   It cannot establish complete candidate acceptance.
4. `NATIVE_ACCEPTED` requires the exact Git candidate, the pinned disposable
   Supabase/PostgreSQL runtime, the full inherited suite, and downloadable
   evidence bound to the commit and tree.

## Fail-closed result vocabulary

Every ledger row must end as exactly one of:

- `PASS`: the required evidence level was executed and the oracle matched.
- `FAIL`: a qualified counterexample was reproduced.
- `INCOMPLETE`: the fixture, oracle, or environment did not establish either
  result.
- `BLOCKED_BY_TOOLING`: execution could not be completed by the available
  tooling.

`INCOMPLETE`, `BLOCKED_BY_TOOLING`, missing rows, and skipped rows all block the
candidate. They must never be counted as `PASS`.

## Monotonic coverage

- A successor adds regression coverage; it does not remove, rename away, or
  weaken an inherited assertion.
- Static review cannot replace runtime, multi-session, permission, HTTP, or
  rollback evidence where those layers are part of the ledger row.
- Synthetic fixtures may be used, but expected and actual business rows,
  journals, reports, actor identity, timezone, and transaction boundary must be
  recorded.
- Every fixture runs inside a disposable database and must prove rollback or
  database disposal with zero relevant residue.
- No production, UAT, legacy, or hosted database is an audit target.

## Required CP6 ledger

| Area | Minimum executable evidence |
| --- | --- |
| Business-day boundary | Same source instant under independent session zones; long transaction spanning Jakarta midnight |
| Late cost correction | Material recomputation through WIP, FG, COGS, payable, journals, and per-date reports |
| Partial completion | Laundry and FG allocation with exact stock, HPP, WIP, and minor-unit conservation |
| Linked corrections | Payment, return, opening balance, and source-linked inverse rows; report confidence must agree |
| Permission changes | Null/inactive roles and mid-transaction revocation must fail closed with no committed business row |
| Concurrent commands | Double submit, stale version, reservation, and competing sessions must serialize or refuse atomically |
| Admission and rollback | Preflight refusal, exact predecessor restoration, concurrent-use refusal, and zero orphan objects |

## Acceptance rule

A candidate is accepted only when every required ledger row is `PASS` at its
required evidence level, the inherited suite remains green, the exact commit
and tree are pinned, rollback restores the predecessor exactly, and
`production_go` remains `false` until the owner separately authorizes release.
