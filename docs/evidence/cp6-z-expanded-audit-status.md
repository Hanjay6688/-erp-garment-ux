# CP6 Z expanded independent audit checkpoint

`production_go:false`. The only writable branch is
`competition/cp6-j-closure-20260911`. Business candidate Z remains
`134774825dbe5ff6ffba5b82f629c1dac2a3ce8d`, tree
`3afeddbbca86f28285b1b24a002a572b34be54b7`.

The independent audit is **INCOMPLETE**, not a pass or a confirmed business
failure. All changes after Z so far are audit code, workflow wiring, and audit
documentation. No business migration or rollback has been changed.

## Executed attempts

| Native run | Audit checkout | Result | Fixture problem | Full audit transaction restored |
| --- | --- | --- | --- | --- |
| [180](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34849025778) | `a7ff35f7afa08300cc6478342d5a167223a2078f` | INCOMPLETE | Connection must originate as the disposable session administrator | No business case ran; disposable stack destroyed |
| [181](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34849936790) | `6cd307df122c6dea8560ce90654cde6fc845e2ae` | 8 INCOMPLETE | Two JSON text parameters needed explicit SQL types | Yes |
| [182](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34851276543) | `69e7ce4594d5e3423fe53a73c268585a7b61e2f9` | 8 INCOMPLETE | Manually seeded movements lacked a warehouse; location code exceeded 30 characters | Yes |

Each failed attempt preserved its diagnostic evidence. None establishes a
business bug. The earlier writer evidence remains historical evidence for Z;
it does not fill the new independent coverage ledger.

## Current harness correction

- Form checkpoint history through two ordinary owner V2 receipt postings.
  Qualify the resulting movement identities and exact chronological cost
  history before evaluating the checkpoint.
- Give every receipt a valid raw-material warehouse with a code within the
  schema limit. Read the private movement table as the disposable
  administrator; perform the business actions as the authenticated owner.
- Keep both receipt instants in the past regardless of runner start time.
- Capture the Python traceback for every incomplete case.
- Preserve all eight expected cases: four close-session zones and four
  correction-session zones. Correction cases close in Jakarta first to avoid
  cancellation between two separate date errors.

## Open work

The source review identified two hypotheses: session-dependent checkpoint
midnight and session-dependent recost checkpoint selection. Native business
reproduction remains required. Only a qualified material finding authorizes
the auditor-to-successor transition.

The broader independent ledger also remains open: long transactions across
Jakarta midnight; true late supplier invoices through WIP/FG/COGS; partial
allocations and cents; linked corrections and report confidence; role changes;
concurrent commands; admission, rollback, and orphan checks. See
`docs/cp6-competition-mode-audit-protocol.md`.

Workspace maintenance removed the older checkout during the audit. The
repository was recovered from the exact remote branch into the current
workspace, and the uncommitted fixture correction was reapplied. Git-backed
checkpoints and Actions artifacts are the recovery record.
