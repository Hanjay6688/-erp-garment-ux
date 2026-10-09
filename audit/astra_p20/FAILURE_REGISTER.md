# First failures — append only

## 37877038138, independent staged attempt1

- Product:2e605bb7; audit:ea858258.
- Error: `dict() got multiple values for keyword argument case`.
- Classification: AUDITOR_HARNESS, not a product finding.
- Cause: our result dict included `case`; the unchanged strict runner adds `case` when logging.
- First individual result was saved before the logger failed; remaining seven did not run.
- Source restoration: boundary/public/function hashes all true. Package30files, security and backup/restore gates passed.
- Fix: rename our metadata field to `audit_case_id`; no assertion/oracle/product changes.
- Preserve original run/artifacts11592801959(JSON),11593156018(raw), not overwritten.
- Corrected run must retain all first outcomes; no claim that first attempt passed.

## 37877343411, business attempt1

- Same AUDITOR_HARNESS result-key collision as37877038138.
- Independent full-flow case completed PASS; complete first verdict sha2567b6227b42193fbc6b752a6178d7096cff5facf356d64d01d668ebb07d17f4250 retained in evidence/projection-first-1.json.
- Three remaining cases were never reached; continuation executes only those three after metadata fix.
- Full composition restore boundary/public/functions true; package restore/security gates passed.

## 37877802981 and37877803025, retained-row comparison

- First hashes differ only in tables containing typed timestamptz (jobs/page_sets); immutable body/page hashes identical.
- Suspected AUDITOR_COMPARATOR: to_jsonb timestamptz text depends on session TimeZone. No field is excluded.
- Correct comparator setsUTC for serialization and restores callerTimeZone. Dedicated validation must prove time-zone invariance and preserve raw before/after differences.
- Original COUNTEREXAMPLE outputs preserved in evidence/log-verdicts-113650280731.json and113650279827.json. Not attributed to product until adjudicated.

## 37878142700, AS20-32 first setup

- `CP7_PLAN_ASSUMPTIONS_NOT_REVIEWED` at v1 SAVE before either racing action.
- AUDITOR_FIXTURE: payload reused v2 assumption IDs while v1 capture has its own IDs. Positive guard rejection, not product failure.
- Correct only reviewed_assumption_ids using the actually read v1 option list. Capacity inputs/oracle unchanged. Continue only the unreached race; preserve all five PASS cases.

## 37878640217, precise source amount and receipt actor

- AS20-07_LARGE_INVOICE PASS on all three actual amounts. No rerun required.
- AS20-04_08_PRECISION raw `material_purchase_final_ap_total` returned exact61.648683507697. Original expectation incorrectly imposed cents at an intermediate function. Framework02 says rate/amount scales differ and round only at a valid boundary. Classification pending runtime public payment check; do not assign this intermediate mismatch as a product bug.
- Followup preserves exact-operand equality, verifies public payable61.65 and actually pays61.65 to test zero residual. First output retained.
- AS20-01_RECEIPT_REPLAY setup refused `CP7_PROCUREMENT_VALUE_DENIED`: our actor could post but lacked `finance.ap.view` for the explicit price. Add value permission only to initial positive setup; still revoke posting before replay. No guard changed.

## 37878853771, unchanged candidate shell gate

- `scripts/cp7_probe_evidence_test.py` fails `NameError: p19_plan_v2 is not defined` at actual finalizer execution.
- WRITER_HARNESS_DEFECT, independently reproduced at exact candidate; not an application monetary defect.
- Remaining shell/build/browser steps were skipped. Run them separately unchanged, while keeping original shell gate FAILED. Never remove this failure from final assessment.
