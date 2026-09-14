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

## Authoritative correction after Native 183

The earlier INCOMPLETE verdict describes runs 180–182. Native
[183](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34868697161),
checkout `bb0779ac26c038dbafd8ed29ab453f0acc8b9468`, now rejects Z with
**two qualified P1 business defects across four counterexamples**. Four controls
passed, zero cases were incomplete, all eight savepoints restored exactly,
the entire unseeded runtime restored, and the temporary schema grant restored.

1. Closing the same Jakarta business day as UTC or UTC−12 included the next
   day's receipt: quantity 20 at average 15 instead of quantity 10 at average
   10. UTC+14 excluded both receipts and saved a zero checkpoint.
2. Posting a final-price correction as UTC+14 changed the receipt input price
   and payable to 200, while material history and inventory remained at 100.
   The owner report still returned `READY`. The Jakarta, UTC, and UTC−12
   controls correctly recosted inventory to 200.

The qualified native JSON is preserved byte for byte in
`docs/evidence/cp6-z183-qualified-audit.json`. GitHub artifact `10357774610`
contains the report and diagnostics; its ZIP is 637112 bytes with SHA-256
`5538f22dd7b378b320e0c881c9881cd78f44f950b19e7698720109cf3d40e4e0`.
The downloaded ZIP matched this digest and passed its CRC check.

This material finding activates the owner's standing auditor-to-writer
instruction. Successor **AA**, still CP6, changes only the two proven date
expressions. The admitted SQL through Z remains immutable. AA adds a private
two-function rollback capsule, exact Z input/output pins, thirteen atomic
admission cases, before/after eight-case business regressions, twenty inherited
close cases under AA, and twenty additional rollback schedules (440 total,
110 expected writer-first backend body entries). Existing checkpoints require
explicit historical review before installation; AA must not silently bless an
already incorrect checkpoint.

AA is **WRITER IN PROGRESS**, with native acceptance still pending. The wider
independent ledger above remains open, including true late supplier invoices
through WIP/FG/COGS; the proven final-price correction must not be reported as
that broader invoice coverage. `production_go:false`; no merge or deployment
is authorized.
