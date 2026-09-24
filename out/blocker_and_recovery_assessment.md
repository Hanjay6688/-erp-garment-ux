# CP6 blocker resolution and recovery assessment

Date: 2026-09-24. Candidate: `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc`. External audit report snapshot: `cf301a6f0c128ac8c221ab11e22c95db0ce1c896`. Review is post-lock and explicitly authorized by the owner's latest request. No product, writer-branch, hosted, legacy, production, or workflow mutation was made.

## Current capability and pending cases

The execution workspace responds again. At the first successful recovery check its uptime was about798seconds, the old cp6_audit folder was absent, and git/python/rg were available while gh/docker/psql were absent. This is consistent with a fresh/replaced workspace. The infrastructure cause of the earlier exec-server disconnect and409 environment_offline is not observable; there is no evidence that the ERP service went offline.

All three contract files and the original frozen phase1 findings were recovered with their original hashes. Exact original stock/import4 and money4 scenario bytes are now committed under audit/scenarios/. The later combined15-case payload has not been restored byte-for-byte or dispatched. Its count comprises4stock/import+4money+6advance+1selector, not15workflow runs. The older business checkpoint has a different hash; the selector's last revision remains missing. Their original status remains NOT_RUN with null run/job IDs.

Handoff:36–41 expressly authorizes the custom disposable dispatch. The available GitHub connector exposes GET and rerun-existing-job operations, but no arbitrary workflow-dispatch POST. Repeating an old run cannot insert a new scenario payload. This is a capability limit, not a new request for owner permission. No credentials should be requested. Several other CP6 families also lack completed test design/fixtures and review; the incomplete audit is not entirely attributable to this limit.

## 1. Two-session race: cause verified, runtime change required

Evidence: Actions run36051535647/job107808033765 (rev1) and36052066150/job107809808216 (rev2), read directly from logs. Three cases in each failed in setup, not during the intended race. Rev1 could not switch session authorization to supabase_admin. Rev2 fixed its admin connection but side connections could not see the main transaction's OWNER seed or schemaUSAGE grant.

The standard auditor runner invokes cases inside r1.group's uncommitted connection/savepoint. Side commits into the same clone breach that isolation; copying the clone as a PostgreSQL template also requires the source connection to have closed. Therefore a standalone retry of xaudit_3.py cannot safely close this gap.

Prepared integration contract: a race hook after r1.group closes, before normal clone disposal; one uniquely named disposable copy per schedule; committed fixture and actor preflight in that copy; both workers recorded and joined; exact product refusal and ledger oracle; deletion plus source/primary fingerprints. The grant added for a fixture must be disclosed as fixture-expanded ACL, not production ACL proof. Full specification and oracle corrections: [race_blocker_review.md](race_blocker_review.md).

The external script's count<=1 oracles are insufficient: zero workers/zero filings can satisfy them. For an already posted initial opening key, both later batches must remain unposted, not one extra winner. A READY close needs exactly one filing/success and one defined refusal; a BLOCKED control needs two defined refusals and no changes. Permission/setup/timeouts remain INCOMPLETE.

Status: verified harness blocker; no native product race verdict, no runtime repair claimed.

## 2. HTTP/JWT: rejected approach is not a complete Auth proof

xaudit_4.py reads the PostgREST container environment, extracts PGRST_JWT_SECRET, and signs its own bearer tokens. That explains a plausible Credential Materialization classification. The classifier event itself is reported by the external audit, not observable in this session. Moving the same operation to another dispatch interface is not a solution.

Even if permitted, those tokens do not prove real GoTrue login. The scenario omits inactive/view-only identities, guesses arguments, and lacks exact denial state-invariance oracles. Some endpoint errors could reflect malformed fixtures instead of authorization.

Prepared remedy: a distinct ten-facade matrix on the existing disposable T3 real Auth path, using actual password-grant sessions, valid pinned arguments, explicit roles/actions, same-bearer revocation, positive owner controls, complete ERP denial fingerprints, redacted artifacts, and Auth/clone cleanup. Existing T3 already proves a narrower10-case AU browser flow; that flow is not acceptance of the complete CP6 matrix. Full specification: [http_blocker_review.md](http_blocker_review.md).

Status: safe testing design available; new HTTP matrix not implemented/run. No classifier workaround or credential access attempted.

## 3. Native release rollback: missing qualification, not clone cleanup

Root checked the exact candidate's untruncated recursive tree and source files:
- No AW, AX, AY or AZ file exists under supabase/rollbacks/.
- .github/workflows/cp6-t3-release-package.yml:48–61 defines install/capture/browser. scripts/cp6_t3_package_run.py:79 accepts exactly those modes.
- supabase/release/cp6-t3/MANIFEST.json:1367 explicitly records rollbacks NOT_TESTED.
- AC rollback:15–16 accepts migration digests7b5690a2... or7a3613d8..., while the release manifest:14 pins AC at871fb32b.... This is an unresolved release-variant qualification mismatch. The guard's refusal protects data; do not weaken it or merely whitelist another hash without proving equivalence.
- package_run.py:135 runs backup/restore, :138–140 drops the test clone. Neither is an AC..AZ migration downgrade proof. Its final assertion:148 also does not assert restore/primary-cleanup flags; those must be read separately.

Contract oracle: Master3816,3826;5205–5209;5306;5354–5355 require preserved posted facts, matched migration/rollback source, exact restoration/refusal and cleanup. Master108–114 describes prior AQ qualification, not a new candidate run. Master2713–2719 belongs to CP7 BR and should not be the sole basis for a CP6 gate.

Concrete qualification required from the writer's approved runtime:
1. Derive source-pinned AW..AZ inverse/restore capsules in reverse dependency order, with exact before/after definitions, owner/ACL, triggers, constraints, migration ledger, and data fingerprints. Qualify the release AC variant, preserving refusal protections.
2. On a fresh unused disposable install: record baseline, install exact release24, close admission with documented maintenance authority, execute inverse chain, and compare the complete baseline. Repeat install/rollback twice; no silent snapshot reload may count as migration rollback.
3. Negative controls: wrong source/hash/catalog, admission still open, and business use followed by inverse must refuse without any state change where the contract requires pre-use-only rollback. Preserve the failed run/logs.
4. Capture candidate/tree/package/rollback hashes, expected cases versus actual, exact refusal text, before/after catalog and ledger fingerprints, Auth/clone residue and untouched primary. A green install job alone cannot accept this gate.

Status: source-confirmed release qualification gap; no actual failed downgrade was reproduced here. Fixing it requires new reviewed writer artifacts/runtime support; audit code must not invent a passing rollback for the frozen candidate.

## 4. Other-provider quota: does not block review here

The claimed22:20UTC quota reset and22:26trigger are external statements; this session has not verified either. It cannot reset another provider's account or promise a scheduled invocation will run. Two bounded adversarial agents here completed the race and HTTP reviews and saved incremental notes, which were committed before further review. Their completed source/log reviews do not replace missing native tests.

## Disposition and next action

Workspace access, contract recovery and independent review capacity are restored. Eight original scenario cases are preserved in the audit branch. Race/HTTP/rollback native evidence remains open for the concrete reasons above. CP6 is still HOLD/INCOMPLETE; production_go=false. Continue native-log cross-review of Claude's economic findings, then reconstruct missing test revisions with new hashes and submit only through an authorized dispatch-capable environment. Do not count design documents or recovered source as executed cases.
