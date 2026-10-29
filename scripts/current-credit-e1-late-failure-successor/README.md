# E1 private late-failure fixture successor

This is a local, closed test-fixture successor to public preparation
`f5b085a2bf3a34397616e9a9a3326af5119d19c4` (tree
`0f54938eea7893327456cbc8d850ae85ea9c6e58`). It changes only the nested
`late_failure` callback of `e_cases.py`. All 17 case IDs, the other 16 callback
bodies, the complete original `refusal` no-effect oracle, all nine E runtime
leaves, D1 runtime, retained fixture helpers and UI bytes remain unchanged.

The retained old callback added a `BEFORE INSERT` trigger to Native
`erp.journal_entries`. Source review found that this changes the exact Native
source-trigger census before the tested command reaches posting. The actual
failed D1 a994 run independently retained the same census refusal for its
own old journal-trigger fixture. No actual E execution is claimed for this
finding; its old source and the D1 raw case finding are retained in evidence.

The new trigger is test-only `AFTER INSERT` on E's own
`cp7_credit_note_carry_de.operations_v1`. It observes current transaction/actor
work in `MATERIALIZED`, real revision and final response with owning command
contexts cleared, a real posted replacement SALE journal and Native net550,
and exactly one carried80 assignment with the original APPLY event and journal
unchanged against the original basis, snapshots and hashes. It then calls the
unchanged Native source census, E historical guard and actual current profile
guard. Only after those return does it raise the original
`E_TEST_ACTUAL_NATIVE_POST_FAILURE` with raw observed IDs, amounts, hashes and
guard names in DETAIL. Incomplete setup uses a distinct
`E_TEST_LATE_POINT_SETUP_FAILED`; actual guard failures keep their own errors.

The honest failure point is `AFTER_NATIVE_POST_DURING_E_FINISH`. This does not
claim failure inside Native posting. The point precedes deletion of E's work
row, so the final `assert_closed_v1` is intentionally left to the unchanged
normal finisher rather than called prematurely in the trigger. Whole ERP
`pg_trigger` rows are compared before/after private test DDL and after the
refusal. The existing whole no-effect oracle still verifies the rolled-back
Native/note/consumer/E state without any narrower substitute.

Local results are structural doubles only: the exact trigger SQL literal is
extracted from the callback, compiled in local in-memory PGlite against clearly
declared minimal tables, fixed auth and helper/guard stand-ins. The latest
`LOCAL_TRIGGER_SECOND.json` has 14 PASS controls; FIRST has the retained earlier
12-control subset. These are not 26 independent cases and earn zero Native
credit. They check journal/phase/context/assignment/revision/response and old
APPLY integrity negatives, actual guard invocation negatives and local full
table/sequence equality after refusal. They cannot establish real ERP runtime,
source-catalog22, economic or Auth correctness.

Run the offline boundaries with:

```sh
python3 -B scripts/current-credit-e1-late-failure-successor/test_source_boundary.py
python3 -B scripts/current-credit-e1-late-failure-successor/source_check.py
```

The new `SOURCE.json` is an explicit local successor declaration. All files in
the frozen old E qualification namespace, its workflow and its CLOSED parent
manifest remain byte-identical. Those old manifests intentionally do not admit
this changed callback or dependency hash. Root alone must explicitly bind a
successful actual D1 source/run/artifact/full-restore/five-gate proof and update
the new E intake dependencies before any actual E17 run. D1 a994 remains failed
5/13 with all raw negatives retained; a later D1 cap run being in progress is
not qualification. Actual E/real Auth/browser/races are all zero here;
`production_go=false` and `independent_acceptance=false`.
