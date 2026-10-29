# S05 installer successor above frozen200922 — local proof only

The frozen component e290 and qualifier200922 remain retained. The successor
keeps **report.sql byte-identical**, including all five query bodies, four
private `OWNER TO postgres` statements and the public wrapper owner transfer.
The ten Native callbacks/labels, UI, parent runtime, workflow and package engine
remain exact. No existing function changes, new RPCs, schema or role are added
beyond the original S05 declaration.

The installer/inverse now execute complete original DDL as the **already
current administrative superuser**, after checking actual current/session
identity and `rolsuper`. They never obtain superuser themselves. Current
non-superuser callers refuse before DDL. Both operations use the inherited
atomic savepoint. The installer records every actual new function ACL and
refuses an unexpected default grant, rolling back instead of normalizing it.
Original `verify`, `transition`, function-source checks and the no-membership
oracle remain unchanged. Each future real Native reader interval retains its
actual installer profile in the outer report.

No temporary public CREATE grant, membership, GUC change, catalog update,
projection or seal regeneration is used. Existing raw `public.nspacl` remains
byte-identical, including NULL. The new reader remains NOLOGIN/NOINHERIT and
has zero membership rows. Public execution remains authenticated only; no
private ERP/table/native-writer grants are added.

Source route: the frozen engine opens `package.boundary.ADMIN`; retained
`cp6_au_browser_fixture.py` binds local clone `supabase_admin`. Existing
`cp7_finance_capture.composition.handover` similarly requires a current
superuser when a Native installer handover is needed. This is **source
consistency, not an actual S05 Native role-profile observation**. The successor
records and validates that profile when root executes it. Non-superuser CP7C
and hosted installation remain unqualified.

Local controls use an already installed PGlite0.3.14 / embedded PostgreSQL17.5.
They execute original whole report DDL with **check_function_bodies=off only in
the local fixture** because no ERP source schema is installed; no report
function or ERP writer is called. Parent verification is explicitly an
orchestration stub. The exact22 source catalog queries/data comparator and
inherited atomic function are extracted without importing a product runtime.
This proves role/DDL/ACL/atomic behavior, **not Native SQL compilation or ERP
acceptance**. Native qualification keeps its original real body checks.

The final local8 controls cover original whole-DDL install/inverse/reinstall;
all22 equality against the original postgres-superuser route; explicit and
NULL public ACLs; named non-superuser refusal before DDL despite a superuser
session; pre-existing role and unexpected default-ACL refusal; SQL failure
after role creation/public owner transfer; validation error after DDL; and
inverse failure after DROP OWNED, with exact catalog/data/sequence restoration.

Retained first evidence is never overwritten. `FIRST_REPRO.json` records the
original non-superuser creator SET-role failure and NULL ACL materialization.
`ROLE_PROBE*` preserve followup experiments, including the PGlite template1
CREATE-grant limitation and absent grant-option fixture. V6 proves separate
SET/CREATE checks and the outer-superuser cleanup route, which was then
superseded by the simpler whole-DDL route. The unlaunched complex envelope is
retained under `retained/SUPERSEDED_UNLAUNCHED_*` and is **not imported or used**.

`OUTER_SU_FIRST` preserves PGlite's protected bootstrap-role attribute failure;
SECOND preserves session-role fixture isolation failure; THIRD preserves an
adapter duplicate-column-name loss and a non-superuser catalog-read fixture
failure; FOURTH/FIFTH preserve identity-reset fixture failures; SIXTH preserves
an explicit-role restoration mismatch in the comparison fixture. Their exact
source versions are retained. Only SEVENTH with array-row transport is the
complete PASS_LOCAL_ONLY receipt. Compressed receipts retain exact original
JSON bytes, with decompressed byte/hash identities in `LOCAL_ROLE_RECEIPTS.json`.

```bash
# Source/offline controls; no database, network or runtime imports:
PYTHONDONTWRITEBYTECODE=1 GIT_NO_LAZY_FETCH=1 python scripts/current-s05-native10-qualification/check.py
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s scripts/current-s05-native10-qualification -p 'test_*.py'

# Only the explicitly authorized local in-memory role/DDL fixture:
S05_PGLITE_MODULE=/path/to/already-installed/@electric-sql/pglite \
S05_LOCAL_ROLE_RECEIPT=/new/private/path/LOCAL_ROLE.json \
python scripts/current-s05-native10-qualification/owner_transfer/test_outer_superuser.py
```

Native10, actual parent/full22/full database+roles+CP6+advisors recovery, and all
five package gates remain mandatory for root's actual run. Real Auth/HTTP,
browser and independent acceptance are not supplied by these controls.
`Native_executions=0`, `ERP_function_calls=0`, `independent_acceptance=false`,
`production_go=false`. Afui/zero-reimbursement scope remains exactly as in the
qualifier README; no Native rule or case is changed for this installer repair.

Primary semantics: PostgreSQL17 [ALTER FUNCTION](https://www.postgresql.org/docs/17/sql-alterfunction.html),
[role attributes](https://www.postgresql.org/docs/17/role-attributes.html), and
[GRANT](https://www.postgresql.org/docs/17/sql-grant.html). The original
non-superuser path requires SET-role plus CREATE on the function schema;
non-superuser CREATE ROLE also creates a bootstrap ADMIN-only membership.
Current superuser DDL bypasses that owner-transfer check and creates no such
membership. The local actual controls retain those observations independently.
