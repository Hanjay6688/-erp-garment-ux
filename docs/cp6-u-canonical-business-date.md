# CP6 U corrective revision — canonical business dates

Baseline T: `a333672509212467159104e5b7b52d573e13c9d1` (native #149 PASS).
Single writer; competition branch only. `production_go:false`. DO NOT MERGE.

## Frozen installation failure and native diagnosis

Original remote U `ce6df43ee4115b83dd921eb06a726356c278bb09` failed native
#150, job 103694215610, at step 61. The five-case independent T oracle passed;
all proof after U installation was skipped. Cleanup succeeded. Original bytes:

- Migration: 20,907 bytes, SHA-256 `83878cf18de9fad9bbaf4a306ad1a6d2527dbd6f45ecd85cd388f53a476bba85`.
- Rollback: 13,658 bytes, SHA-256 `f7802f51292af6805397e8672bbb1c3a443f5312a4fb60fd0b739e3b30081f69`.
- Failed ZIP: artifact 10314192304, 2,114,812 bytes, SHA-256 `4c4dc9ab63823bee373ed4e28093eb51bd20137ce64670f716d80ad56c59e232`.

Diagnostic commit `67d7e4bf` / native #151 reproduced the original rejection,
then its instrumentation failed: alias `c` shadowed a PL/pgSQL record. This was a
tester defect. Commit `3591d62f` / native #152 corrected the alias and recorded
all predicates on PostgreSQL 17.6. The original migration was replayed both
byte-identically and with an added NOTICE; its original assertions were retained.
Both rejected transactions restored all 533 ERP function definitions/owners/ACLs
and all 208 ERP/platform tables exactly.

Only two predicates were false, both for the owner report:

| Operand | Expected | Observed |
| --- | --- | --- |
| Predecessor and capsule definition SHA-256 | `e51dbe224d112f523e51bddc609ee0f0036ecae2ef5d328b865326781aa8780c` | Exact match, including hash of capsule text |
| Installed and live definition SHA-256 | `78210a408d3cf6bf48e3e86200c3a429adacff19a339b11669598accceaaf9cb` | `9d0a6abf16a8632bbf877a20e763dd46f3041f8d157a5b52a3deed19ac11cdcd` |
| Owner before/after | `postgres` | Exact match |
| ACL before/after | postgres, authenticated, service_role EXECUTE | Exact match |

PostgreSQL normalized the default argument to
`p_as_of date DEFAULT erp._cp3_business_date(CURRENT_TIMESTAMP)`.
The rejected pin had been predicted from lowercase `current_timestamp` input
text instead of the installed deparser output. This is a bad pin prediction;
no owner/ACL regression or PostgreSQL version change was demonstrated.

## Versioning decision

U was never admitted and failed atomically. The owner explicitly authorized
correcting this unadmitted migration in a new fast-forward commit. This is **U
corrective revision**, retaining the U timestamp and runtime label, not a new
migration that requires failed U to exist. Original U, both diagnostic commits,
and all failed CI runs remain in history. Every migration/rollback F–T remains
byte-identical. Current U pins, byte counts, capsule counts and acceptance gates
are updated together. The frozen diagnostic still replays original U's five
functions; the corrected capsule contains seven.

## Reproduced business defects and repair

The unchanged five-case oracle proves four T defects and one Jakarta control:
material-adjustment journal day, generic reversal day, owner-report operational
cutoffs, and omitted `p_as_of`. The report's `h.physical_at` changes concern QC and
laundry movement cutoffs; financial account balances already use journal dates.

Independent follow-up also found:

1. **P2, atomic refusal:** original U's omitted report argument called a private
   helper before entering the SECURITY DEFINER body. Actual `authenticated`
   owners received SQLSTATE 42501; an explicit date succeeded. The corrected
   default uses the built-in Jakarta timestamp/date expression. The private
   helper remains private. Explicit NULL and invalid ranges remain rejected.
2. **P2, silent wrong report period, inherited from T:** receipt and GRNI posting
   cast `physical_at::date` in the session zone. A receipt at
   `2026-09-03T00:30:00+07`, two units at 0.015, posted 0.03 on September 2 under
   UTC/New York while Jakarta/Tokyo used September 3. The prior-day material and
   AP/GRNI report was wrong but READY; total money and quantity still conserved.
   Both receipt posting and its GRNI trigger now use canonical Jakarta dates.

Seven definitions change: generic reversal, material adjustment, material
receipt, receipt GRNI trigger, financial truth checks, report-check propagation,
and owner report. No compatibility helper or business table is added. Three
CRITICAL detectors cover adjustment, generic reversal, and receipt/GRNI dates.
Installation rejects mismatched posted history without rewriting it.

The pre-U hash oracle now executes each proposed CREATE OR REPLACE inside a
savepoint, reads `pg_get_functiondef()`, verifies unchanged owner/ACL, and restores
the exact predecessor. Text predictions remain diagnostic data, never installed
pins. The migration's installed-definition assertions remain mandatory.

## Independent expanded oracle and limits

Twenty added groups run both before and after U, alongside the original five:

- Estimated/final receipts in UTC, New York, Jakarta and Tokyo; exact Jakarta
  midnight boundary; per-day material, AP, GRNI and zero unrelated-account deltas.
- Actual authenticated SQL posting and request replay with inert second effects.
- Frozen original-default permission failure with explicit-date positive control;
  explicit NULL, invalid period, and five successive real session timezones.
- Adjustment replay, future-date atomic refusal and a linked monetary inverse.
- All three detectors and READY/BLOCKED propagation with rollback to READY.
- Fourteen upgrade probes: eight invalid histories rejected and six lawful
  histories accepted; full function/owner/ACL/table snapshots restored afterward.

The reversal detector test deliberately installs a private test-only function
that creates a wrong date, then restores the current definition before reading
the detector. It proves detector sensitivity, not ordinary-user permission to
replace code. Other detector probes replay pinned T definitions. All such fault
injection is confined to rollback-only disposable transactions. SQL fixture
CASE-parenthesis and varchar-length errors found locally were corrected before
publication; they are not ERP bugs.

The authenticated schema-usage alignment comes from the frozen source-owned auth
migration and exists only inside the disposable transaction. New-case HTTP/UI
reachability is not claimed; native Auth/JWT/HTTP tests are separate evidence.
PGlite verifies sequential local behavior, not native PostgreSQL races or Auth.
Remaining CURRENT_DATE/localtimestamp/date casts outside this bounded material
and report change are an explicit follow-up inventory, not a claim of universal
coverage. Writer PASS never substitutes for independent final PASS.

## Required exact-runtime proof and rollback boundary

The pre-use boundary remains 74 tables; U's private seven-function capsule is
excluded. Rollback requires closed maintenance admission and drained sessions,
refuses history drift, and restores seven exact T definitions with owner/ACL.
The complete function catalog is compared before U and after rollback. T's
append-only fact security and every historical rollback remain mandatory.

A corrective candidate may be called writer PASS only after its exact remote
SHA/tree proves full-schema SUCCESS, original five plus expanded twenty native
cases, fourteen upgrade guards, Auth 95, broad CP3–CP6 regression on final U,
34 established races and three abort qualifications plus specialized M/R/T races,
320 maintenance schedules with 80 observed writer-body entries, 151 setup units,
31 maintenance units, seven direct and nine extra-object rollback guards,
U→T exact restore, the old rollback ladder, no residue and physical cleanup.
Build, 208 frontend tests, security gates, artifact payload/source-pin verification
and all CodeQL languages must also pass. Local checks cannot waive a native gate.

No hosted migration, UAT/legacy/production mutation, merge, deployment or PR-state
change is authorized. CP7 has not started. The locked roadmap remains CP7 rev3
WIP-first → CP7.5 cleanup/rebaseline/archive/fresh-restore equivalence → CP7C
stress/automation/backup → CP8 final independent audit/cutover. CP9 is obsolete.

Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.
VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
