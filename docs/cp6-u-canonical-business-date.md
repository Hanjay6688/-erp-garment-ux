# CP6 U — canonical material, reversal and owner-report business dates

Audited predecessor: T `a333672509212467159104e5b7b52d573e13c9d1`.
Single writer; competition branch only. `production_go:false`. DO NOT MERGE.

## Independently reproduced T defects

The native disposable oracle fixes its business instant at
`2026-09-13 00:30:00+07` and changes only real PostgreSQL session timezones.
Run #149's pre-U gate proved four affected paths and one Jakarta control:

1. A material adjustment posted in UTC used `physical_at::date` and recorded
   September 12 although the canonical Jakarta business date was September 13.
2. Generic journal reversal used session `CURRENT_DATE`. A real UTC-12/UTC+14
   session either recorded the wrong day or hit the future-date guard.
3. Owner WIP cutoff cast `timestamptz::date`, so the same laundry movement was
   counted in different periods in UTC and Jakarta.
4. The owner's omitted `p_as_of` default used session `CURRENT_DATE`, producing
   a timezone-dependent balance-sheet date.

The `MATERIAL_ORIGINAL_JAKARTA` path remained a control. The oracle reaches the
material and report RPCs under the actual `authenticated` role. Its schema usage
is tied to the frozen UAT auth migration and aligned only inside the rollback-only
disposable transaction; this is not hosted-UAT evidence.

## Repair and financial truth

U replaces five definitions and creates no compatibility helper or business
table. Material posting derives both journal dates from
`_cp3_business_date(h.physical_at)`. Generic reversal derives its date from the
transaction's posting instant. The owner report canonicalizes material and WIP
cutoffs and its default `p_as_of` through the same Jakarta helper.

Two CRITICAL truth checks cover existing material-adjustment journals and generic
journal reversals. Both are connected to the owner financial report. Installation
refuses mismatched history atomically; it never rewrites an old journal or silently
repairs a report boundary.

## Upgrade and rollback boundary

The forward migration pins T's platform bytes, complete six-function capsule,
all five U inputs, inherited helper definitions, owners, ACLs and T's append-only
fact security. The new five-function capsule records exact predecessor and
installed hashes. The installed hashes were predicted from the independent T
oracle before U was authored and are checked again by PostgreSQL after install.

The pre-use boundary hashes 74 tables: T's 73-table boundary plus T's capsule,
excluding U's capsule. U rollback runs only behind the maintenance controller's
closed admission and drained sessions, refuses any table/history drift, restores
the exact T definitions and removes only U's marker, platform row and capsule.
The complete PostgreSQL function catalog is compared before U and after rollback.

## Required proof, not publication

Final U must pass all five AFTER_U cases, existing native Auth/browser suites,
all T and historical regressions, 34 established native races plus specialized
M/R/T races, 320 closed-admission schedules with 80 observed writer-body entries,
151 fixture-orchestration unit cases, direct and inherited rollback guards, the
entire rollback ladder, zero-residue cleanup, production build and exact-SHA
CodeQL. Static checks and mocked setup tests do not substitute for native proof.

No migration in this branch is applied to hosted UAT or production. Merge,
deployment and production GO remain owner-only decisions. CP7 rev3 stays next:
WIP-first, then CP7.5, CP7C and CP8.
