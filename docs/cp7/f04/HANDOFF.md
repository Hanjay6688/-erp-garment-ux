# F04 handoff to the single integrator

Contribution: [draft PR #36](https://github.com/Hanjay6688/-erp-garment-ux/pull/36)
on `cp7/f04-planning-20260929`, targeting `cp7/integration`.

Prior verified computation head: `b4d6fb134fce8b068a24b6c1996943d21a164431`.
Prior source tree: `888ded65e292c46f2c78d7b45716f69d83199620`.
Pinned integration base: `5da1fb6106c7c72058ebd73a782a5155f59c258d`.

The current continuation adds two functions and 47 M07/M08 cases (138 total).
See `CONTINUATION.md` for exact scope. Local WASM, all 716 Vitest tests, static
security, build and the 48-file contract lock passed for these additions.
Native continuation proof is pending the source push; the 91-case receipts below
remain historical evidence and do not qualify the new computation bytes.

## Writer delivery

P05/P06/P07 have private, executable SQL kernels and 138 synthetic assertions.
The work is independently reviewable without modifying F03, the shared DTOs,
CURRENT_STATE, source/migration manifests, UI, or workflows. All 48 frozen
framework files remain byte-identical.

`README.md` describes the input boundary, method initialization, explicit
assumptions, production exclusions, and reproduction commands. The SQL and
dedicated fixture runner are the actual implementation; there is no parallel
JavaScript implementation of the business mathematics.

The matching dependency is pinned P04, with these SHA-256 digests:

| File | SHA-256 |
| --- | --- |
| `scripts/cp7-src/wip/bootstrap.sql` | `f13d218d6ef6c38bea1968081368cdf253538c79d36b67a51e61d126927c2769` |
| `scripts/cp7-src/wip/matching.sql` | `b3fc0e9307f0d87ca80b7935412210b4eba7f38d9568c6d68dfa6355d97d8c4f` |
| `scripts/cp7-src/wip/timing.sql` | `cf61bae66086edd7a34e3456e5bad9d644cf42ced4cf2a2bedee4f89f1c9ebc9` |

## Prior checkpoint proof scope (91 cases)

Verified run: [36590548037](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36590548037),
all jobs successful on the source head above. Native PostgreSQL **16.15** passed
91 kernel/ACL cases; 716 Vitest tests, 6 existing shell-browser tests, static
security, build/client secret scan and the 48-file contract receipt passed.
Downloaded CodeQL SARIF for JS/TS and Actions has zero results and successful
invocations. SQL correctness is covered by native fixtures, not CodeQL.

`NATIVE_KERNEL_RECEIPT.json` is the unmodified file downloaded from the prior CI
artifact, SHA-bound to that checkpoint's SQL source/dependency and fixture. The
local `LOCAL_WASM_RECEIPT.json` is separately labelled. `CODEQL_RECEIPT.json`
records inspected SARIF/archive digests. `VERIFICATION.json` records source tree,
workflow/job/step outcomes, artifact identity and remaining gates.

This is cross-version kernel proof on PostgreSQL 16.15 and PGlite 18.3.
It does **not** qualify the target Supabase PostgreSQL 17 deployment or its Auth.

The receipt files bind source/dependency hashes, fixture/oracle hashes, runtime
version, expected/actual case values, errors rejected, and disposable cleanup.
They are **writer evidence**, not an independent auditor verdict.

The cases exercise the numeric boundaries associated with O01–O12, O16, O17,
O19, O20, E01, X02, X10–X15 and relevant M-series rules. Suffixes in case IDs
identify the exact tested subcase; they do not silently close an entire canonical
oracle. Example: allocation of 60 PCS proves its supplied global fixture scope,
not server-side prevention of a malicious user's filtered-scope submission.

Two faults found during writer verification were corrected and retained as
regressions: a JSON reference-binding expression in allocation, and ordering
calendar windows by actual instants when timestamp precision differs. The final
candidate also makes equal-score challenger selection prefer the simpler kernel,
then stable ID, independently of input-array order.

## Integration sequence

1. Revalidate the pinned helpers against independently accepted F01/F02/P04 and
   the current F03/P10 source readers. The active F03 writer remains owner of its files.
2. Have the integrator build these private inputs from complete authorized
   captures. No consumer or client may supply trusted allocation scope, matching
   facts, source eligibility, data completeness or ETA labels.
3. Add the modules to the canonical transaction/build/source/migration manifest
   under the integrator's ownership; this contribution does not create a release.
4. Compose snapshot/version invalidation and Auth/stale/race checks, then replay
   X06, target Supabase schema/roles, actual source lifecycle and conservation.
5. Compose multi-resource calendars/routes and qualify M07 invalidation. Separately
   run realistic-volume performance checks under the ADR/P02/P07 gate.
   Kernel fixture timing is not a factory-scale performance qualification.
6. Keep the model result as a reviewed recommendation. Every model activation is
   currently `REVIEW_REQUIRED`; there is no registry write or autonomous trigger.
7. P08 apply remains held until planning and P10 prerequisites pass. Preserve
   independent audit and production approval as separate gates.

Canonical family status remains **INTEGRATION / INDEPENDENT ACCEPTANCE OPEN**.
No receipt here declares F04 closed, production GO, or live data integration.
