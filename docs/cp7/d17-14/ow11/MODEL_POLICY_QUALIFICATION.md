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

## First Native admission result and exact correction

Candidate e0284f6/run40097458641/job120882585502 produced six INCOMPLETE
cases, all stopped at the same installer catalog guard. The policies-to-registry
foreign key also creates two PostgreSQL internal triggers on the existing
registry. Those exact objects were missing from the admission declaration.
Original12561642820 SHA83e52f944a0d00b0b0b399f9d20a8e8c8b1507f64cdac70175f626c27b984b0c
and the full first log are retained. cp6/advisor restoration passed; writer
runtime was false. No policy behavior has Native PASS credit from that run.

The correction declares only policies_registry_id_fkey's RI_FKey_noaction_del
type9 and RI_FKey_noaction_upd type17 registry-side identities, pins them in the
manifest, verifies their exact set, and still rejects unrelated parent-table
or trigger deltas. The SQL, immutable FK, ACL and budgets are unchanged.
The controlled SQL harness independently checks those generated trigger keys.

## Reviewed client and actual browser candidate

The model evaluation panel opens a separate policy workspace only on explicit
selection. Seven numeric entries and seven allowed-method checkboxes start
empty. Stored fields can be copied by an explicit button. A reason and review
are mandatory; every edit clears review. Withdrawal keeps prior settings and
does not require inventing replacement thresholds. The UI clearly states that
saving policy does not yet activate forecasts on targets.

Closed parsers validate the fixed prospective model definitions, complete policy,
revision/registry/actor/request identity, exact decimal strings and microsecond
clock order. The typed local recovery record retains the whole UUID/payload
and prior policy before sending. Lost replies, contradictory receipts and
uncertain revoked replays stay pending; a definite first database rollback can
release the command. Browser locks, cross-tab invalidation and parent FG/HPP
retirement on access loss are covered locally.

69 client/DOM tests PASS, TypeScript PASS and CSS64 PASS. The fixture comes from
actual controlled SQL with the existing full eight-model registry template.
These are not actual browser/Auth results. Two new actual Auth mobile/desktop
journeys are predeclared: explicit SET, lost committed reply, reload exact UUID,
copied review, append SUSPEND, revoked read and parent facts retired. Browser2
and the corrected Native6 still require CI results.

The unchanged A-owned source checker now has exactly22 pending RPC pairs:
prior20 plus policy read/save in nativeModelPolicy.ts. A disposable proposal
containing only those22 passes373 reachable runtime files and317 owned RPC
boundaries with no orphan/direct table access. No shared checker/default/types
were edited. See MODEL_POLICY_REGISTRY_CHECK.json and the two-pair patch.
