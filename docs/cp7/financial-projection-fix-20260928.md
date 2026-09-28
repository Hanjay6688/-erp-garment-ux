# CP7-DELTA-01 — writer follow-up

Source under review: `6465825d0f8a865f28264626a4e0af818d66967e`, PR #31.
Independent handoff: [CP6_CP7_HANDOFF_WRITER_20260929.md](https://github.com/Hanjay6688/-erp-garment-ux/blob/c2728c7e28ed674e680590b6f3db56478b1388b5/audits/independent_delta_20260929/reports/CP6_CP7_HANDOFF_WRITER_20260929.md).

`projectShell` removed metrics for OPERATIONS but retained financial values,
references and interpretation text in `analysis.plan_comparisons`. The exact
independent probe reproduced this locally: 6 PASS / 1 FAIL before the fix.

The same restriction now removes the entire comparison collection before any
consumer receives the cloned analysis. The contract has open metric IDs and
units, with no per-metric permission classification. Neither a currency check
nor a list of known finance metric IDs is a reliable access boundary. The shell
therefore treats comparisons like its existing restricted metrics collection.
Operational recommendations, quantities, allocation edges and actions remain
available. OWNER retains the original analysis; DENIED receives empty output.

## Verification

- `tests/cp7/independent-delta.test.ts` is an exact copy of the auditor's seven
  probes; SHA-256 `6f0a42844c0a62d9ddf22245410f1397ae656843ec75018b3d885a3824a2e1ef`.
- Local focused tests: 44 PASS, comprising the existing 34, the unchanged seven
  independent probes and three new access-transition regressions.
- New cases cover KNOWN, ASSUMED and UNKNOWN comparisons, IDR/USD/ratio units,
  unclassified metric IDs, source references and interpretation text. They
  check OWNER → OPERATIONS → DENIED → OPERATIONS → OWNER, unchanged source,
  retained operational facts, and report/prompt/WhatsApp preview output.
- Build, typecheck and built-client scan: PASS locally.
- CI on product commit `c9c228a087532cdabe53748568ab82b80e048790`:
  [run 36460822362](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36460822362)
  passes 57 files / 619 tests, security checks, build and all six browser cases
  (desktop/mobile). CodeQL Actions and JavaScript/TypeScript both completed
  with zero findings; each result was checked in the original job log.
- Local browser launch lacked the pinned executable; no browser assertion ran
  locally. CI used its pinned browser successfully. The local security check
  initially lacked two historical Git objects; after fetching those objects,
  the unmodified security command passed. No guard was bypassed.

No schema or oracle was relaxed. Six consumers still derive from the shared
projection. This fixes the synthetic shell; the future connected reader must
enforce authorization server-side before returning data. There is no evidence
of exposure of live data. CP6 code, integration gates, deployment and production
permissions are unchanged. CP6 findings from the first auditor are tracked
separately; this CP7 result does not close those findings or reopen the second
auditor's passed CP6 cases.
