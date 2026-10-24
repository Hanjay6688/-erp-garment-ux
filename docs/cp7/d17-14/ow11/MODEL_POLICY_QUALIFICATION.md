# OW11 — explicit prospective model policy

This opt-in stage records reviewed activation policy. It does not install a
forecast consumer or modify the default bundle, legacy result v1, existing
registry row, financial records, stock or HPP. A owns full-chain admission.

`cp7_model_policy_stage` adds the private admission gate (2 functions), policy
metadata (5 private functions, 2 public wrappers), 2 schemas and 2 immutable
RLS tables. There are zero old function replacements. No policy is seeded.
The read workspace exposes the fixed candidate definitions for review, without
copying technical proposal thresholds into an owner policy.

SET requires current access epoch, revision, template hash, reason, explicit
review and every policy field. OWNER/ADMIN and existing product-management
permission are required to write. SUSPEND appends a new version and retains the
prior configuration/template; reactivation requires a new explicit SET.
Each version atomically inserts a separate prospective registry row at its
actual recorded clock. Previous policy, command and registry rows are immutable.
There is no backdated effective timestamp or automatic forecast activation.

The writer takes the existing global FG/HPP/sales envelope, actor/request lock,
then policy lock. Access is checked after each wait and before committed replay.
An exact UUID/payload returns its original receipt; a changed payload fails.
CAS prevents two revisions being accepted from the same review. A failure at
the final command insert rolls back its registry and policy inserts as well.

The installer pins exact source/dependency functions and admits only its declared
delta across all 22 catalog groups. It checks owner, ACL, RLS and GUC settings.
Pre-use inverse uses RESTRICT and an internal savepoint, so a dependent view
cannot leave partial removal. Any policy/command use or registry-row change
requires composed backup restoration; the installer never deletes history.

## Evidence and remaining work

Actual SQL in the local controlled runtime passes 10 cases. Access stand-ins
are explicitly identified: this is not Native, Auth, concurrency or catalog22
qualification. The first report (9 PASS/1 FAIL) is retained: its immutable test
expected `CP7_IMMUTABLE_RUN`; the unchanged Native trigger returns
`CP7_RUN_IMMUTABLE`. Only the test's expected message was corrected.

Native6 is predeclared for isolated CI: catalog22/inverse/dependency, complete
public lifecycle, prospective microsecond clock/immutable rows, current Native
owner/admin access, 11 validation refusals, and atomic final-table failure.
The strict twelve-stage parent, 8-second request and 45-minute job budgets stay
unchanged. Native outcome is pending; no HTTP/browser/race credit is claimed.

Still required: actual HTTP/concurrent policy proof, reviewed UI, prospective
registry/dataset v2 adapter, cached immutable evaluation evidence, and dated
forecast integration through the single demand/target kernel. The private
admission prototype's synthetic backtest is not production model accuracy.
Formal acceptance stays 5/16, CP7C unaccepted, `production_go=false`.
