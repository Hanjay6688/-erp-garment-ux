# Native63 third attempt: source-derived platform owner

Run39545090852/job119041351478 at052d5b49 failed before any of63 cases:
`OW04_BOUNDED_TRIGGER_GUARD_UNKNOWN_INTERNAL_FUNCTION` for
`pg_catalog.RI_FKey_noaction_del()`. The unmodified runtime log, report and
package result are compressed here; RECEIPT.json pins their bytes. No case
was relabelled PASS. The package backup drill/advisor/primary checks do not
replace the missing OW04 runtime result.

The combined predicate did not print the rejected metadata, so that run does
not itself prove the actual owner. The source-derived diagnosis is precise:
Supabase postgres17.6.1.165 `Dockerfile-17` sets the bootstrap database user to
`supabase_admin`. PostgreSQL's bootstrap superuser has OID10; built-in RI
functions belong to that bootstrap user. ERP relation/ordinary-function
ownership remains governed by its separate source manifest.

The correction requires exactly `supabase_admin`/OID10 for internal RI
functions; it does not accept either of two owners, learn an allowed owner
from first capture, change any database ACL, or bypass the trigger/FK census.
Internal language, invoker, empty configuration, no arguments, trigger result,
exact internal entry point and all attachment semantics remain required.
Rejection now records the actual relevant metadata as well as the expected
owner, so a different cause can be distinguished on the next Native run.

`ri_owner_controls.py` reproduces the old rejection of the explicitly synthetic
Supabase bootstrap model and tests the corrected acceptance, wrong owners/OID,
changed metadata/entry point, missing FK/RI and ordinary ERP ownership.
All17 controls pass with zero database calls. This is not Native63 evidence.
The original synthetic catalogue is preserved with its provenance label.
The63 runtime cases, money/date/stock/HPP oracles and expected files are unchanged.

Source: PLATFORM_SOURCE.json records the exact upstream tag/path/blob and
relevant clause. Run the real disposable Native63 qualification next. OW04,
feature_complete, audit_complete and production_go remain false.
