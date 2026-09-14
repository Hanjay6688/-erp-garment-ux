# CP6 Z expanded independent audit checkpoint

`production_go:false`. The only writable branch is
`competition/cp6-j-closure-20260911`. Business candidate Z remains
`134774825dbe5ff6ffba5b82f629c1dac2a3ce8d`, tree
`3afeddbbca86f28285b1b24a002a572b34be54b7`.

The frozen Z candidate is **FAIL_NEW_COUNTEREXAMPLE** after Native 183 proved
two material business defects. Successor AA is **WRITER PASS** after Native 185
and CodeQL 60, with all 12,203 payloads and 213 source pins verified. Its first
native attempt, 184, stopped at an inherited source gate before AA installation.
Native 187 rejects AA with **FAIL_NEW_COUNTEREXAMPLE**: all 23 cases executed,
17 controls passed, six qualified P2 counterexamples, and zero incomplete cases.
The repaired clock fixture now qualifies both long-transaction date failures.
CodeQL 62 passed all four languages with verified SARIF payloads. Successor
**AB is in progress, not yet native-qualified**. Admitted SQL through AA remains
unchanged; AB adds one migration and its matching rollback.

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

The initial checkpoint and recost hypotheses were qualified by Native 183,
as recorded below. That finding authorized the successor-writer transition;
the additional independent scenarios still require their own evidence.

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

AA subsequently reached **WRITER PASS** in Native 185. The wider independent
ledger above remains open, including true late supplier invoices
through WIP/FG/COGS; the proven final-price correction must not be reported as
that broader invoice coverage. `production_go:false`; no merge or deployment
is authorized.

## Native 184: inherited source gate stopped before AA

Native [184](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34871809182),
checkout `27f165ac106d3b1ad97471ab3c5b7488dd75822a`, failed at step 71 with
`INDEPENDENT_REQUIRES_UNCHANGED_X_BUSINESS_SQL`. The inherited X oracle's
repository allowlist named Y and Z additions but omitted the two new AA files.
No AA admission, installation, business regression, or rollback case ran.
This attempt is **INCOMPLETE**, with no AA business verdict. CodeQL 59 passed
on the same checkout. Failure cleanup reported `stop_exit=0`,
`remaining_database_container=0`, and `status=PASS`.

The follow-up changes the X oracle to admit only the exact AA migration and
rollback paths outside the original `X_AUDIT` phase. It also checks that every
admitted Z SQL file remains unchanged, retaining the existing X and Y history
guards. AA migration and rollback bytes, business assertions, expected case
counts, and runtime checks remain unchanged. Native acceptance requires a new
complete run; source-gate repair is not a substitute for execution.

## Native 185: AA writer evidence verified

Native [185](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34873186373)
and [CodeQL 60](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34873186641)
completed successfully on `7d824f780fa06fc16385c347759a9b96d0138e9d`.
Independent download verification checked all 12,203 payloads, all 213 source
pins against that exact Git commit, ZIP digests and CRC, the nested XZ archive,
and all three CodeQL SARIF manifests and payloads.

AA has eight passing business controls, twenty inherited close controls,
thirteen admission cases, eight direct and thirteen extra rollback guards,
440 distinct successful schedules, and 110 actual writer-first backend
entries with zero compilation-only contexts. All 440 disposable clones were
removed. The exact AA rollback restored 533 ERP functions and 214 tables;
Auth95 and final stack cleanup passed. The evidence verification record is
`docs/evidence/cp6-aa185-writer-verification.json`.

This establishes writer AA's result. It does not execute any of the new
independent cases below or close the broader competition ledger.

## Prepared AA independent audit wave

The new audit modules pin business source
`7d824f780fa06fc16385c347759a9b96d0138e9d`, tree
`0bfda3d552a3a3c37b4563d895a9eb387f64acb4`. Native
[185](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34873186373)
was already running when this wave was prepared. These additional cases are
not part of run 185. Their native outcomes are recorded in runs 186 and 187 below.

| Group | Cases | Independent oracle |
| --- | --- | --- |
| True late invoice and partial production | 16 | Four caller zones, two final prices, estimated receipt alone or ten cut/sewn/sent pieces, eight received, five FG, two sold; raw stock, WIP, FG, COGS, AP, GRNI, exact cents, replay, current and prior-day GL reports |
| Authorization ordering | 3 | Active owner control, user deactivated after transaction start, and user deactivated while ordinary posting waits on an ordinary draft edit's row lock; real authenticated SQL sessions, committed ordering, exact denial boundary |
| Jakarta midnight | 4 | Fresh versus long transactions and prior-day versus current-day scrap source; controlled native wall clock on a separate physical copy, ordinary post and linked reversal, per-day cash and report confidence |

Each group persists individual case outcomes and cleanup evidence. The combined
step collects all three groups before deciding whether it passed. It preserves
the audit source bytes even when the later acceptance ladder does not run.
Date-related invoice or posting refusals need a passing corresponding control
before they can become a qualified counterexample. Other setup or execution
errors remain `INCOMPLETE` with diagnostics.

Local preparation verified Python/C compilation, workflow shell and embedded
Python syntax, all five CP6 check commands, six independent arithmetic examples,
and six one-cent error controls. These are local harness checks, not PostgreSQL
business passes. CodeQL gains a fourth C/C++ analysis job for the new test-only
clock library; the original three analyses remain required.

The copied clock experiment uses the same PostgreSQL image and executable,
requires an exact ERP table/function boundary before fixtures, changes no ERP
function, preserves monotonic time, and verifies original-server restoration
and clock continuity. It proves a controlled clock experiment only. HTTP/UI
reachability, an overnight soak, other permission paths, other source types,
and the remaining expanded ledger rows stay open.

## Native 186: qualified AA recost date defect and clock-fixture failure

Native [186](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34881571969)
ran on `9aa8c3992128e1ddb8b25938619b230e85e856ad`, with AA business SQL unchanged.
The downloaded qualification artifact `10363353256` is 5,530,716 bytes,
SHA-256 `8baf54b6e2eb3cb280d5eb40a9df049731d1daf9d5d9fc3f9224a9f05e1dda29`.
Its ZIP CRC and all seven audit-input source pins matched the exact checkout.

The invoice/partial group executed all sixteen cases: **twelve controls and
four qualified P2 counterexamples**, with no incomplete case and exact rollback
of every case and the whole fixture. In UTC and UTC−12, both final prices
produced correct current-day totals and exact cents, but material and HPP
revaluation events used September 14 instead of the current Jakarta business
day, September 15. Yesterday's report changed: for the integer-price case,
material inventory became −100, FG changed from 51 to 81, and COGS from 34 to
54. It still returned `READY`. Jakarta and UTC+14 partial controls, and all
eight receipt-only controls, passed. The native sixteen-case JSON is preserved
byte for byte in `docs/evidence/cp6-aa186-qualified-audit.json`.

All three authorization-order cases passed. Both deactivated-owner postings
were refused with `Internal ERP access required`, with no new movement,
idempotency row, or other business-table residue. The waiting case proved
committed deactivation while ordinary posting waited on an ordinary draft
edit's row lock. Each clone was removed and the source remained unchanged.
This is authenticated SQL evidence; it does not claim HTTP/UI coverage.

The midnight group executed **zero of four cases**. The host-built clock
library referenced `__isoc23_strtoll`, unavailable in the copied PostgreSQL
image. The source and copied executable hashes matched, but the library failed
before the copied server could start. The copy was removed, the source boundary
and real clock remained intact, and final stack cleanup passed. This is a
fixture failure, not a business verdict. The repair parses the bounded decimal
offset without the incompatible host-libc symbol and records an explicit
copied-executable load control before startup. Fourteen local clock/parser
controls passed; native execution is still required.

[CodeQL 61](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34881571955)
passed Actions, JavaScript/TypeScript, and Python. C/C++ completed its 95-rule
analysis and reported one `cpp/path-injection` finding at the test library's
file open call. The existing path equality guard is retained and the file
open now uses the constant path directly. The zero-findings gate remains
required on the next checkout. Its failed SARIF ZIP and payload were verified.

The verification record is `docs/evidence/cp6-aa186-audit-verification.json`.
The qualified recost date defect activates successor writer AB under the
standing instruction. First complete the missing midnight observations on
unchanged AA, then add the successor migration, rollback, and regressions for
the qualified findings. No admitted business SQL changes in this fixture
repair; `production_go:false` and the remaining ledger stays open.

## Native 187: all AA independent groups qualified

Native [187](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34883270346)
ran on `86351dbc11e5525e35c645178776c2f7dae955f6`, tree
`b3b949af964a76d2203d00ed41e0126211a2cc50`, with AA business SQL unchanged.
Artifact `10363996744` contains 51 members in 5,552,219 bytes, SHA-256
`f730708e147438297d8ad5053b2f6147b5d3d3e43213a99d16c94dcec2047ab3`.
The downloaded archive's digest, CRC, and all nine audit-input source pins
matched the exact checkout. The verification record is
`docs/evidence/cp6-aa187-audit-verification.json`.

| Group | Controls | Qualified counterexamples | Incomplete |
| --- | ---: | ---: | ---: |
| True late invoice and partial production | 12 | 4 | 0 |
| Authorization ordering | 3 | 0 | 0 |
| Jakarta midnight | 2 | 2 | 0 |

The four invoice failures reproduce the prior-day recost defect from 186.
The midnight experiment now also proves:

1. A transaction starts at Jakarta 23:59:50. After the clock advances to
   00:00:05, posting a source dated 00:00:01 is refused as future-dated. The
   same source succeeds in the fresh-transaction control.
2. Posting and reversing the prior-day source after midnight in a long
   transaction assigns the inverse to the prior day. Prior-day cash becomes
   zero instead of 0.03 while the report remains `READY`. The fresh-transaction
   control correctly dates the inverse on the new day.

Every case boundary restored. The copied PostgreSQL executable matched the
source binary; no ERP function changed for the experiment. The copy was
removed, the original boundary and real clock stayed intact, and stack cleanup
passed. The midnight JSON is preserved byte for byte in
`docs/evidence/cp6-aa187-midnight-audit.json`. This is controlled-clock native
evidence, not an overnight soak or complete HTTP/UI evidence.

[CodeQL 62](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34883270071)
passed Actions, C/C++, JavaScript/TypeScript, and Python. All four downloaded
SARIF packages were verified; 23, 95, 103, and 50 rules respectively reported
zero findings. The fixture repair resolved the previous C/C++ finding without
removing the rule or suppressing its result.

## AB successor under preparation

AB changes five functions to use the current statement's clock for operational
Jakarta dates: material revaluation, queued HPP processing, accounting date
validation, generic linked reversal, and journal `posting_at`. Posting dates,
inverse dates, and report detectors must agree when successive commands span
midnight inside one transaction. Document economic dates remain explicit.

The 23 original audit cases run both before and after AB. The predecessor
invoice gate derives the affected zones from recorded transaction clocks;
the successor requires all 23 controls to pass. Eight inherited material-day
and twenty accounting-close cases also rerun under AB. No missing or incomplete
case can count as a pass.

AB adds 26 atomic admission cases, a five-function private rollback capsule,
eight direct and 22 additional rollback guards, and twenty new maintenance
schedules: 460 total with 115 expected actual backend entries. Before-use
rollback must restore all 533 functions and the complete 215-table AA snapshot.
Existing material recost or generic reversal history requires review; AB does
not rewrite or certify it. A lawful AA checkpoint history must still install.
These are required gates, not results: AB has not yet passed a native run.

Remaining independent scope includes other linked payment, return, and opening
balance paths; other authorization and `search_path` paths; and complete
HTTP/UI, reservation, and orphan-code lifecycles. `production_go:false`.
