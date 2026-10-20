# Thirteen committed per-kind transport cases

Proposal only. Active product files are untouched by this helper. Native,
pg_net, provider and browser execution of these new cases is still pending.
The existing 86-case result is a separate receipt and remains unchanged.

Root should copy only `cp7_wa_all_kinds_transport_cases.py` to `scripts/` after
the independent source counters are resolved. It imports accepted fixture
modules and receives the already initialized WA module as an argument; it
does not import `cp7_wa_forward_cases` at module scope.

In `scripts/cp7_wa_forward_cases.py` add
`import cp7_wa_all_kinds_transport_cases as all_kind_transport`, append
`list(all_kind_transport.RACE_IDS)` to the existing race IDs, set `DECLARED=99`,
and append `all_kind_transport.races(tools,today,sys.modules[__name__])` to the
existing `races()` result before its existing exact registration assertion.
Keep every existing 86 ID and closure in its current order. Native, HTTP and
browser groups remain 55, 5 and 9; races increase from 17 to 30.

Update `docs/cp7/wa/WA_FORWARD.json` to exactly 99 total / 55 native / 30 races /
5 HTTP / 9 browser, appending the 13 IDs in `EXPECTED.json` in that order.
The existing probe checks exact manifest/IDS/functions/schedules equality at
`cp7_f05_analysis_probe.py:271–273`, so a missing declaration cannot pass.

`cp6_auditor_modes.py:175–194` rebuilds and seeds `cp6_auditor_race` before
each registered closure. Registration itself makes no connection, so this
module deliberately returns 13 closures instead of a shared-copy loop. Each
case also refuses a non-disposable URL/database, previous dispatch, nonempty
queue, wrong transport or a worker already targeting the copy before its
queued transaction commits.

The active workflow checks out the candidate as `auditor` and invokes
`../auditor/scripts/${{ matrix.probe }}` (`claude-wa-forward.yml:196–200,359`).
The probe imports the WA module from candidate `scripts`; there is no named
`copy_harness` function or per-module copy allowlist in the inspected active
scripts/workflow. If the external execution wrapper uses a copy helper, its
copy list must include this new file; that external wrapper is not present in
this repository. Do not claim that unobserved wrapper was verified.

Each case commits fixture/policy/collector work, freezes full ERP/Auth/platform
boundary plus selected Native-source facts and analysis Original/page identity,
then queues one actual request. Between `send_tick` and its immediate COMMIT,
only read assertions run. The worker is still observed off the copy then. The
existing strict `_provider_worker` starts after that COMMIT; its `finally`
restores the default worker target. Receipt phone, key_ok, status and exact body
must match the stored dispatch, including the selected source's amount/unit or
UNKNOWN wording. Actual response reconciliation must yield accepted round0 /
attempt1; the next tick must create no new dispatch, queue or fake receipt.

The full business boundary covers every ERP table's full-row hashes, not only
stock totals. For the analysis kinds it is supplemented with the immutable
reassembled Original, page identity, zero local claims and zero recorded local
rechecks. The live recheck is read-only (`recorded=false`). Transient timestamp
clocks `as_of`/`checked_at` in ordinary alert details are excluded from source
equality; the obligation source's actual WIB date `as_of` is compared. Actual
dates, `data_as_of`, raw decimal strings, units, financial documents, revisions
and hashes remain compared. The accepted stock readers may refresh private
formula caches; the complete ERP business boundary must remain equal.

First source counters and fixes are retained in `FIRST_STATIC_COUNTER.json`.
`STATIC_RESULT.json` records source-only syntax/import/registration checks and
final file hashes; it must never be relabelled as a Native/provider receipt.

The fake server's intentional uppercase `FAIL` negative control stays intact.
The two opening receipts use categories `GOOD`/`FAILED_ATTEMPT`, but their
actual emitted labels come from document numbers `*-P16-KNOWN`/`*-P16-UNKNOWN`
and vendor name `BB laundry` (`other-obligation-source.sql:277–278`, accepted
`laundry_opening_fixture` and `cp6_bb_probe.masters`). Category is not rendered.
The case still rejects any actual body containing `FAIL` and requires a real
status200 receipt; no fixture source or fake-server control is rewritten.
