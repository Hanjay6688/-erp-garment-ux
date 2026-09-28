# Conversion history and CP7 auditor follow-up — 28 September 2026

Writer product change: `90f1ca11fe5d59d4776a812a2a6c8e51fc665ce6`.
Packaged product: `f8ddf7d0c42993b6e17dd2cc25b39131373a83b2`.
Rollback package: `434b18215f57dd7a361ca621341488d3c31e9703`.
CP6 remains HOLD for independent acceptance; audit_complete=false and
production_go=false. CP7's separate shell is authorized; operational integration
is still closed. No merge or deployment was performed.

**Writer scope qualified.** Final packaged runtime on
`0b78dbd6bfabdb13340f1d7b22298b963cc9239c` passes **97 native, 26 contention,
8 real Auth/HTTP, 27 BF browser and 10 AU browser cases**. Packaged rollback
passes **147 checks**. [Per-case evidence](cp6-conversion-history-writer-proof-20260928.json)
preserves the original counterexample, initial unsuccessful run, corrections
and final results. These are writer results, not independent sign-off.

## Why the two auditor reports are consistent

The first auditor's [run 36458272433](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36458272433)
proved that moving a range three seconds before a posted conversion could
change that document's historical target SKU and move its 1 PCS between
historical HPP groups. The exact physical lot and quantity stayed unchanged;
financial or journal corruption was not established. Ordinary FG and sales
controls were refused by the existing BOM commitment guard.

The second auditor's [handoff](https://github.com/Hanjay6688/-erp-garment-ux/blob/c2728c7e28ed674e680590b6f3db56478b1388b5/audits/independent_delta_20260929/reports/CP6_CP7_HANDOFF_WRITER_20260929.md)
passed its CP6 delta cases and raised CP7-DELTA-01. Those cases did not disprove
the first auditor's conversion counterexample. Previously passed vendor,
UNKNOWN/FREE/WAIVED, supplier-credit and combined range/rework cases remain
retained regressions, not reopened findings.

## CP6 implementation

The BF master rejects a proposed effective time at or before a posted
conversion involving an old or incoming member. It checks both source and
destination physical roots, including their physical versions and REVERSED
documents. A later effective time remains allowed. It does not rewrite lots,
conversion documents, HPP snapshots or journals.

The master takes the existing FG/HPP posting lock before the commercial master
lock and product rows. Native conversion posting already uses this lock, so a
master edit cannot read incomplete conversion history from a concurrent writer.
No additional public function, grant or business price rule was introduced.

The three original auditor probes are retained byte-for-byte in
`scripts/cp6_independent_final_probe.py` (SHA-256
`584de8be2246e2bba85b9f2e1c1bbd5619c7d18279de1f53bbb42e0d8ff3a736`).
New native cases check backdated/equal times, atomic refusal, legitimate later
moves, reversed documents, and unchanged balances and historical groupings.
Four schedules exercise conversion/master ordering with first commit/abort.
A real native sale return supplies nonempty Grade B after a range move, checking
original lot, quantity/value partition and reversal. This is a Grade B report
case, not blanket proof of every Grade B workflow.

## Package qualification

Only BF changed in the 30-file AC..BF install package. All 29 predecessor files
retain their previously qualified hashes. Fresh capture on the aligned
disposable baseline was used to rebuild BF; no production database was touched.

The first capture run correctly rejected the stale committed BF package. After
rebuilding, [run 36462124923](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36462124923)
reproduced all committed pins exactly and passed installation, backup/restore,
advisors and primary-unchanged gates. Rollback capture was renewed in
[run 36462124902](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36462124902).

On the packaged product, the unchanged independent probes pass 3/3; all four
new conversion/master schedules pass, and the real Grade B return case passes
with 18 Grade A + 1 Grade B = 19 PCS, Grade B value 42.00, and exact inverse.
The initial complete runtime run records 91 native PASS, 3 FAIL, 3 INCOMPLETE,
26 contention PASS and 8 HTTP PASS. It is not presented as a green run.

The three FAIL cases compared identical instants represented in Asia/Jakarta
and UTC as different strings. Every other document field was identical. The
writer test now compares those instants after timezone-aware normalization,
retaining timestamp precision and all fields. Three older non-PO recovery
fixtures placed next-day receipts at 09:00 on the current day, which was still
future just after midnight. Those complete prerequisite sequences now finish
yesterday. Refusal codes, values, original auditor probes and product code were
not weakened. Full retest on
`0b78dbd6bfabdb13340f1d7b22298b963cc9239c` now passes all **97 native,
26 contention and 8 HTTP** cases with no FAIL or INCOMPLETE. The three writer
history cases confirm exact document instants/fields, atomic refusal, unchanged
FG/COGS/WIP balances, preserved historical grouping and legal later moves.

Final [package run 36463334464](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36463334464)
passes all three jobs: identical pins, runtime/restore/advisors and browser.
Native/runtime job `109067126024` has all gates true. Auth users, public schema
and baseline state are restored; isolated HTTP/race databases are removed.
Build [36463334301](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36463334301)
and CodeQL [36463334448](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36463334448)
also pass. The triggered BE family probe independently exercises 16 retained
native cases on its own disposable stage and passes; it is auxiliary writer
evidence, not the independent auditor's acceptance.

The package browser job already passes 27 BF + 10 AU cases with zero console
errors and unchanged Auth/schema boundaries. Packaged rollback
[run 36462684960](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36462684960)
passes all 147 checks, including two complete rollback/reinstall cycles and
refusal after use, with the primary baseline unchanged. The subsequent fixture
corrections change neither installed product nor packaged rollback bytes.

## CP7-DELTA-01

Fixed separately in [PR #31](https://github.com/Hanjay6688/-erp-garment-ux/pull/31),
product `c9c228a087532cdabe53748568ab82b80e048790`, evidence
`fa0ed346c322b8f24924f19f3a39f4117e6a0068`. OPERATIONS now receives no metric
comparison payload; OWNER retains it, DENIED stays empty, and the source is
unchanged. Open metric IDs/units lack an access classification, so comparisons
use the same restriction as the existing metrics collection before formatting.

The exact seven independent probes reproduced 6 PASS / 1 FAIL before the fix
and pass after it. [CI 36460822362](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36460822362)
passed 619 tests, six desktop/mobile browser cases, security, build and both
CodeQL languages with zero findings. The financial projection fix is verified
for the synthetic shell. Backend authorization and combined CP6/CP7 integration
remain future gates; there is no demonstrated live-data exposure.
