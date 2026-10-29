# S05 public default ACL: locked local reproduction, product unchanged

Base: local `23c7a0a4c760ddd6b9671697caa4615e3a8a25e5`, tree
`3820c7348167fc750cc3f3f36645f14f76286e44`, identical to public failed
`b0e5ac05e2024d5673126b6fe7759591293b9b96` tree.
Branch: `feature/a-s05-public-default-acl-20261029`.

The actual b0 raw report is 805672 bytes, SHA256
`56408d4a2708c9fc66689ae660df6594c961774d101dc70f95801aaeb21bc728`.
It records one INCOMPLETE outer wrapper, **zero S05 Native business cases**,
an empty native result, and failure in `installer_function_grants` on the new
public report function. Full outer22/rows/sequences/public/roles/CP6/advisors
restoration is true; the writer gate is false. The report does not retain the
actual failing ACL or default ACL tuples, so no particular CI extra tuple is
proved by that artifact.

## Local mechanism, before any product change

The inherited role/DDL harness uses installed PGlite0.3.14 / PostgreSQL17.5.
It intentionally has no ERP schema and disables body compilation. Its parent
proof is a labelled orchestration stub; no ERP report function is executed.
The exact frozen whole report DDL and installer/checker are used unchanged.

The fixture adds only this source profile:

```sql
alter default privileges for role supabase_admin in schema public
grant execute on functions to postgres,anon,authenticated,service_role;
```

Both local controls pass by observing the expected frozen installation
refusal, not by qualifying S05:

1. Four private function ACLs match exactly. The public function has the
   required reader-owner and authenticated EXECUTE entries plus explicit
   `(cp7_accessory_standard_read, postgres, EXECUTE, false)`; the exact frozen
   checker raises the same public-function error as CI.
2. Adding `s05_external` to that fixture default adds one further public
   EXECUTE tuple and remains refused. Arbitrary default grants are not allowed.

Both failed installations restore all22 catalog groups, rows, all sequences,
raw public schema ACL, default ACL and caller identity exactly. Actual tuples,
all executed fixture SQL, runtime and source digests are retained before the
failure in `evidence/FROZEN_B0_LOCAL_DEFAULT_FIRST_REPRO.json` (494804 bytes,
SHA256 `632567a50a4fcb3ba22d7786a35fac2b2f6f4d893baded7932310bd76fb53e2d`).
This proves one faithful local mechanism. It does not identify the omitted
actual CI ACL tuple.

## Proposed bounded repair, awaiting integrator review

Only the final privilege declaration for the **new** public S05 function would
change. Add `postgres` to its existing REVOKE after the existing OWNER transfer.
The exact original line occurs once:

```sql
revoke all on function public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)from public,anon,service_role,cp7_capture;
```

Proposed replacement adds only `,postgres` before the semicolon. No default
privilege, schema ACL, existing function grant, role attribute or membership
changes. All five function bodies, the five final owners, search paths, original
verifier and Native10 callbacks stay byte-identical. The public function must
still have exactly two ACL tuples, owned by the reader role, without a grant
option: reader EXECUTE and authenticated EXECUTE. The four private ACL
requirements remain unchanged.

The failure diagnostic in the existing new installer checker should retain
actual failing ACL tuples and the relevant installer's GLOBAL/public function
default ACL rows before raising. It must remain bounded, with explicit total
counts/overflow flags, and must always refuse unknown grants. It must not
normalize or dynamically revoke arbitrary grantees. The next actual report
will therefore identify its exact source of failure instead of naming only a
function signature.

After explicit review, directed local controls should prove faithful-profile
install/preuse inverse/reinstall with exact two public tuples; unchanged
private tuples, raw schema/default ACL/identity during and after use; unknown
external default grant refusal with complete restoration; and fault rollback
around the new final privilege step. Existing original role/DDL controls remain
preserved. A new counted source transition must bind the single REVOKE change
and narrow diagnostic change; the old byte-identical-report transition and all
first failures remain retained, not silently repinned.

Only root may bind/publish/run the actual Native10 and complete package/full
database restoration qualification. Local reproduction: Native0,
Auth/HTTP/browser0, independent_acceptance=false, production_go=false.
