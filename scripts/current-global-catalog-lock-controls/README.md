# Isolated catalog barrier primitives — no ERP qualification

The retained nine relation-lock primitives remain valid and are not rerun.
They demonstrated that an ordinary relation barrier does not stop concurrent
function definition changes. These seven new controls examine a different
mechanism on the same exact PostgreSQL 17.6 image digest:

1. SHARE on pg_proc blocks CREATE OR REPLACE FUNCTION.
2. SHARE on pg_proc blocks changing a function's EXECUTE ACL.
3. SHARE on pg_authid blocks a role capability change.
4. SHARE on pg_auth_members blocks a new role membership.
5. An already active pg_proc writer makes the owning SHARE NOWAIT barrier refuse
   before the model sequence or effect row is consumed.
6. SHARE locks on every actual pg_catalog table allow an existing function call
   and ordinary model DML on another backend.
7. SET search_path to an empty identifier and set_config to an empty path retain
   their distinct actual settings. The historical missing error text is not
   reconstructed or declared proven.

Each blocked writer must have an observed distinct PID, actual held ShareLock,
pg_blocking_pids evidence and SQLSTATE 55P03. The identical statement must work
after holder commit, then roll back. Model rows/sequence/function definition and
ACL/role flags/membership must equal baseline. All opened sessions and new roles
and schema are removed. Every first failure is retained by an always-upload step.

This is a disposable model database, not the ERP schema or Native financial
flow. A successful primitive does not install a barrier, grant an app permission,
close external/runtime writers, or qualify an ERP lock profile. The full current
catalog and owning hooks still need final-parent admission and actual tests.
