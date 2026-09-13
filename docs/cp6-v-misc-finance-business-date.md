# CP6 V — miscellaneous cash business dates

**DO NOT MERGE. `production_go:false`. Native V acceptance is required before writer PASS.**

“VENI. VIDI. VICI. ERP. — I CONQUERED ERP.”
“Reliable data adalah dewa.”
“Keuangan—termasuk laporan—stok, dan HPP adalah raja.”

## Reproducible predecessor failure

The admitted U corrective SQL is commit `61ae2c98ca1ddfc4957dfe34bbd6a4f201c701bc`, tree
`f59b421c5db60ef4570f214d223fd2411268bd5b`. Its historical native run #155 passed.
A subsequent adversarial audit found an uncovered P2 backend date defect.

On real PostgreSQL 17.6, with both `current_user` and `session_user` equal to
`authenticated` and application role OWNER, insert an ordinary DRAFT miscellaneous
income or expense for 0.03 with `physical_at='2026-09-03T00:30:00+07'`, then call
`erp.post_misc_finance(uuid)` in UTC or America/New_York. U posts the journal on
September 2. The September 2 owner report includes +0.03 income or -0.03 expense
and incorrectly reports READY. Expected: zero on September 2, the signed 0.03 on
September 3. Jakarta and Tokyo controls post correctly. The draft is inert, and
total debit and credit remain exactly 0.03; this is silent per-date cash/report
misposting, not evidence of total-money, stock or HPP loss.

Native #157, commit `db8bc4ece46859cad85ea8106415a3e93177c2a9`, run
`34761015794`, job `103733742216`, qualifies four failures plus four lawful
controls, zero oracle failures. All 209 ERP/platform tables and the entire
function boundary restore exactly; disposable cleanup passes. The audit step
fails intentionally and all subsequent native qualification is skipped.
[Native counterexample run #157](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/34761015794).

Preserve its artifact `cp6-r1-v2620u-full-schema-auth-browser-proof`, ID
`10318798691`, 2,148,441 bytes, ZIP SHA-256
`6775bc3e4ddb68d29ad26fdede810f97ccc2e04629a1e14e2774304425889484`.
The earlier #156 was a tester connection failure, not an ERP reproduction:
Supabase's local postgres role cannot SET SESSION AUTHORIZATION authenticated.
#157 uses the existing disposable bootstrap administrator solely to establish a
real authenticated session. No role attributes, passwords or function/table
privileges are changed. The frozen catalog's missing authenticated schema USAGE
is aligned transactionally from the existing, pinned platform source, as in U.
HTTP/UI reachability of this new path remains unproven.

## Forward-only V

U was admitted in native PostgreSQL, so its SQL is immutable. V is a new migration
created through the pinned Supabase CLI 2.116.0 at UTC timestamp `20260913135850`.
All historical migrations and rollbacks through U remain byte-identical. The two
diagnostic commits and failed runs #156/#157 remain in fast-forward history.

V replaces exactly three functions:

| Function | Change |
| --- | --- |
| `erp.post_misc_finance(uuid)` | Replace both session-dependent `t.physical_at::date` casts with the private canonical Jakarta business-date helper. |
| `erp.run_v267_financial_truth_checks()` | Add CRITICAL `V2620V_MISC_FINANCE_BUSINESS_DATE` for wrong original economic dates, including reversed originals. |
| `erp._v268_financial_report_checks_pre_scope()` | Propagate the new detector to the financial report. |

The detector compares **economic_date** to the canonical physical date. A closed
accounting period legitimately moves **transaction_date** to
`greatest(canonical_today, closed_through + 1)`; the accounting report follows that
posting date. V preserves this distinction and tests it explicitly. It does not
rewrite posted records or alter the existing period-close policy.

The private three-row rollback capsule stores independently pinned predecessor
and installed definitions, owners, ACLs and 77 table-content boundaries. Migration
admission authenticates all seven U capsule rows, the cash entry point, inherited
private helpers and fact security. Existing wrong-date history aborts atomically
with `V_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED`, without rewriting that history.
There are no new business tables, public helpers, grants or RPC contracts.

## Evidence gates

The paired native oracle first requires four known U failures and four controls.
Each wrong-history upgrade must refuse without any table/function/capsule residue;
each lawful-history upgrade must be accepted and rolled back exactly. AFTER_V must
pass the same eight cases, plus 21 additional cases: microsecond midnight edges,
real current time in ahead/behind zones, timezone changes between drafting,
posting and reporting, future refusal, immutable posted facts, duplicate posting,
linked reversal and replay for both cash directions, blank-reason refusal, draft
deletion, nonowner denial, posted/reversed detector faults, closed periods and ACLs.
All operate in actual authenticated SQL sessions where the operation requires it.
Controlled predecessor replay is a tester fault, not an operator privilege claim.

Three native document races additionally cover post→reverse, post→duplicate post,
and post-abort→post. The first real call holds its natural row lock; evidence must
show the contender blocked inside the actual business function, distinct backend
PIDs, zero manual prelocks and retries, exact cents, per-date cash and READY.

All broad CP3/4/4.5/5/6 and U's 25 date cases run on the final V runtime. Historical
runtime readers verify a pinned successor chain; maintenance admission continues
to require the exact installed generation and never uses that read-only translation.
The F–V maintenance matrix is 340 schedules with 85 demonstrated backend body
entries. V has seven direct and nine inherited helper/fact preflight rollback
faults, a coherent-checksum capsule attack, and exact three-function V→U restoration
plus the entire function catalog. Then U→T and all older rollback ladders still
run. Final no-residue, physical cleanup, Auth95, build/tests and all CodeQL languages
remain required on the exact remote SHA/tree. Lossless evidence transport retains
every payload and source pin.

Local PGlite replay is useful for SQL and oracle behavior but is not native
concurrency, Auth/JWT/HTTP or final acceptance evidence. Writer PASS still requires
successful full-schema native CI and independently verified complete artifacts;
it does not grant independent final PASS or production GO.

## Source identity

- Migration: `20260913135850_erp_v2_6_20v_cp6_misc_finance_business_date.sql`, 19,196 bytes,
  SHA-256 `3bd29c1280e09bd8d36e8303c4e5e4cfdd2be951c3f852c8ce38fe170ab3648d`.
- Rollback: matching `.rollback.sql`, 12,741 bytes,
  SHA-256 `4fb8f0ded3e452dca1d44214711bd79ffcf0f3b68d956283da9bbce5e4444f7b`.

Main, PR24/25 states, hosted UAT, legacy, production, deploy and merge are outside
this writer's mutation scope. CP7 is not started. The locked roadmap remains
CP7 rev3 WIP-first → CP7.5 cleanup/rebaseline/archive/fresh-restore equivalence →
CP7C stress/automation/backup → CP8 independent audit/cutover. CP9 is obsolete.

## Preserved first V run #158

V commit `9a7ce061c613e70fbd859771e3f20d56af248aa9` installed successfully in
native PostgreSQL. The paired 8-case U oracle, 29 V cases, U25, Auth95, physical
acceptance, 34 native CP6 races/three abort qualifications and broad regressions
through M passed. Step 80 then refused `M_RACE_UNSUPPORTED_SOURCE_GENERATION`:
the workflow supplied V, but M's separate startup allowlist still ended at U.
No M race case started. The remaining races, 340 matrix and rollback ladder were
skipped; cleanup passed. This candidate is FAIL, not writer PASS.

The corrective commit only adds V to that supported-generation allowlist and
pins it in the V source gate. M still verifies the exact source marker/capsules
before fixture writes and retains endpoint admission, actual locks, cents,
rejection and cleanup assertions. All V migration/rollback bytes stay unchanged.
Run #158 (`34763104719`, job `103739249075`) and its artifact are preserved:
`cp6-r1-v2620v-full-schema-auth-browser-proof`, ID `10318859445`, 5,463,874 bytes,
ZIP SHA-256 `30116f3975b0fd5a3bcc60391d3b556791675e6308eb20832fac7b93b0766d6a`.
Its three CodeQL artifacts passed; those do not waive the failed native gate.
