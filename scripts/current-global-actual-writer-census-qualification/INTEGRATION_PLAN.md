# Exact integration candidate for the next existing composite qualification

This is a source-reviewed, metadata-only successor candidate. It does not
launch a job, open global hooks, or qualify any business transaction. The
original helper commit `68ec0f57c5861164f3d37db0efcc1cce0237a126` remains intact
in history. `INTEGRATION_SOURCE.json` pins every reviewed parent source at
`bce07059f7a351372e40bb7c2e4453876320a2e8`; no canonical source is changed.

## Exact safe phase

The retained `current-vendor-receivable-qualification/probe.py` outer engine
has these source anchors, preserved by the parent D1/E/SKU engine derivation:

| Original outer-engine line | Boundary preserved |
| --- | --- |
| 89 | Full baseline dump before installation |
| 95–98 | First delta, exact preuse inverse, second delta |
| 103–108 | Top verification, authority/advisors, roles; `conn.commit();installed=True` |
| 111–112 | **New connection and cursor**, then `runner.exercise(...)` |
| 125–137 | Complete original dump restore, roles, portable all22, full rows/ALL sequences, original CP6 proof |
| 180 | `stream_data.bound(catalog)` still encloses the entire `run_inner()` |

The supplemental capture belongs at the new connection's `runner.exercise`
phase. It must not run in `stage.install_delta` or `rollback_delta_preuse`,
inside their savepoints, or before the install commit. The committed
`STATE['after']` and `STATE['preuse_data_and_sequences']` are already available.
`stage.verify` lines 38–51 delegates to the read-only `sku.verify`: catalogue
and privilege reads, not the locking/DDL install or inverse code paths.

`runner_patch.derive('runner')` performs three exact counted substitutions:

1. After the existing two module loads and before the first database SELECT,
   require an idle, non-autocommit loopback connection; set this transaction to
   `READ COMMITTED READ ONLY`, empty search path, and UTC. Verify the resulting
   database/role/settings. No commit/rollback of existing work is permitted.
2. Immediately after the **existing** complete `before` snapshot, validate its
   exact table/sequence membership and equality with the installed preuse
   state; call the supplemental SELECT-only capture; persist its separate
   Original and record the byte reference in the case.
3. After the **existing** complete `after` snapshot and original exact equality
   assertion, require the typed full no-effect proof and attach its hashes and
   counts. The original `report.update` and final `conn.rollback()` remain.

READ COMMITTED is intentional: later statements can observe later commits.
REPEATABLE READ could make a before/after comparison appear unchanged because
both table reads reuse an earlier snapshot. This remains a controlled disposable
read, not a concurrent-writer qualification or a claim that a metadata snapshot
can exclude every transient outside change.

The helper reuses the existing runtime-bound `_data`; it does not copy or
replace its SQL, alter the row hash algorithm, skip tables, or reset sequences.
`complete_snapshot` requires every `r/p/m` relation plus every sequence in the
actual provider catalogue, with both `last_value` and `is_called`. Applied to
the already pinned SKU7c720 before/after evidence, this confirms **685 tables
and 15 sequences** on both sides. That is retained evidence validation, not a
new ERP run. The future D1/E/SKU counts are discovered and must match its own
catalogue rather than being hardcoded to these counts.

## Separate Original and gate

The new full metadata Original is exactly:

`cp6-proof/t3/GLOBAL_ACTUAL_WRITER_SUPPLEMENT.json`

It is created exclusively so an earlier result cannot be overwritten. The
writer reads it back and requires byte-for-byte equality plus parsed-value
equality. The case embeds only `name`, exact byte count, raw SHA-256, full
catalogue digest, and supplement digest. The existing full `read_before`,
`read_after`, current55 and eight-hook rows stay unchanged. Progress stdout
contains only phase, status, row count and failure SQLSTATE; no supplemental
data or compressed/base64 Original is printed.

`runner_patch.derive('gate')` performs three reversible substitutions: accept
the Original directory in `checked`, validate the added separate Original and
no-effect proof, and pass the CLI's existing `--directory` through. Every
original outer restoration, all5, zero-business-credit, exact-head, and Auth
residue check remains present. Supplemental validation cannot mark outer
restoration complete: its proof explicitly keeps
`outer_restoration_verified=false` and requires the original parent gate.

Both source derivations return source strings and digests only. They refuse a
different parent byte sequence and prove reverse application restores the
exact original bytes. There is **no metadata launch command yet** and
`runtime_entry=null` continues to mean no global business command exists.

## Required successor admission and producer transitions before launch

These are required work for the integrator's next explicitly named successor;
they are not changes made to the running parent candidate.

1. **Wait for and pin the actual parent result.** Retain exact parent report,
   package/all5 and terminal run/head, including any first failure. Source bce
   alone does not certify the installed composite. Bind actual current55,
   all eight full19 hooks, and all three layer catalogues.
2. **Create a bounded successor source admission.** Pin bce's entire immutable
   source tree plus the exact helper revision and new successor files. Keep
   all old `SOURCE.json` files unchanged. New source/admission must list every
   additional namespace/workflow/loader explicitly and reject undeclared or
   dirty sources; invoking bce's original `preflight()` against a changed HEAD
   will correctly reject the new files.
3. **Bind the derived modules and complete engine.** Load the existing parent
   `derive.py` as a pure source transformer, retain its complete vendor-engine
   derivation, then use exact counted loader/admission substitutions for the
   new successor. The derived runner must have `__file__` set to the pinned
   original runner path so its existing `HERE`, context reader and stage paths
   retain their meaning. Preserve the gate's original `context_catalog` import
   resolution and verify that module's pinned parent path; a different module
   with the same generic name is not interchangeable. Seal original and derived runner/gate/engine hashes
   in the new successor manifest. Do not edit the parent runner or bypass its
   stage verifier, source manifest, result gate, or restoration engine.
4. **Derive the workflow explicitly.** Retain the current complete 71-step
   workflow's Original fetches, full pre-DB admission, package/clone/install,
   preuse inverse/reinstall, outer restore, all5, and failure retention. Route
   only the successor source checks, metadata-only launch and additional gate
   to the new admitted loader. Give the workflow/branch/concurrency/artifact a
   distinct metadata-only identity; do not dispatch this helper as a global
   Native transaction suite.
5. **Bind all output producers.** New successor profiles corresponding to
   `GENERATED_RECEIPTS.json`, `LATER_GENERATED_RECEIPTS.json`, and
   `SKU_GENERATED_RECEIPTS.json` must bind the new workflow producer bytes;
   the later package profile must use the exact new `package_workflow_name`.
   Preserve original downloaded bytes and existing producers unchanged.
   Declare the new Original's exact output path as data-only, not a blanket
   `.json` or `cp6-proof` allowance. Admission must validate the case reference,
   raw hash/length and typed supplement; output admission alone is not PASS.
   Keep an incomplete/corrupt Original as failure evidence and refuse it as
   qualifying input; never delete/rewrite it to get a clean source check.
6. **Retain and independently gate the Original.** The existing
   `auditor/cp6-proof/t3` artifact-directory upload already covers the new file.
   Keep it out of the old compressed stdout receipt enumeration. Require the
   new result gate to open it, validate exact bytes, and check the full typed
   bracket as well as all unchanged parent gates. No function/table count or
   green job substitutes for these checks.

`capture.validate` now rejects `False`, `0.0`, strings and absent values as
Native credit: only `type(value) is int and value == 0` is accepted.
`independent_acceptance`, `production_go`, and `transaction_writes` must be
literal false; both caller proof obligations must be literal true; runtime
entry must be explicitly present and null. The integration proof comparison
uses canonical JSON so nested `False == 0` Python equality cannot mask a
changed field. All global permission/writer closure flags remain UNKNOWN/false.

73 local controls pass. They include source preimage drift, original byte
corruption/overwrite, active installer and autocommit refusal, first-statement
ordering, wrong isolation, omitted table/sequence, changed sequence, and all
strict type/flag cases. Query SQL is unchanged from the earlier 19-query syntax
smoke. No new business, runtime, or independent acceptance credit is claimed.

Primary PostgreSQL 17 references checked for these transaction decisions:
[transaction isolation](https://www.postgresql.org/docs/17/transaction-iso.html)
and [SET TRANSACTION](https://www.postgresql.org/docs/17/sql-set-transaction.html),
plus [Psycopg transaction management](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
for the implicit BEGIN on the first operation of a non-autocommit connection.
