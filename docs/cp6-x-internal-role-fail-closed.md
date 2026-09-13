# CP6 X — explicit denial for a missing mapped internal role

At authoring: W failed native164; X writer and independent audit PENDING.
`production_go:false`. CP7 has not started. Single writer, no merge or deploy.

Native164 run34780374313/job103786174118 on W
`119e3c53ca0bb0de4ad8f99cbe9b133e0f8cc3c7`, tree
`f09efd64415c93199000a65bb51d80223defe44b`, admitted W successfully. Four paired
V-to-W upgrade probes passed. W then passed24 of25 lifecycle cases and failed
`NON_OWNER_POST_DENIED`: the unmapped authenticated subject's scrap posting
returned successfully instead of refusing. The refusal helper rolled that call
back; the complete case boundary, unseeded runtime and schema USAGE restored.
This is a failed acceptance run, never W writer PASS.

Original artifact10325097065,2,733,769 bytes,SHA256
`2a0781380132b2967a34017c4743727ed5ab24e332dba0051802f139ffa27606`.
Historical recovery artifact10325395651,4,263,766 bytes,SHA256
`118474c30a4722387d87ead72d4514626bd5e8944420029f9cdae6780491a4bb`.
Original ZIPs, log and per-case reports are retained. CodeQL39 on the same W
HEAD passed three languages with zero findings; it does not override native164.

## Cause and forward correction

The inherited `erp.require_internal()` ends with
`if v_app_role not in('OWNER','ADMIN','STAFF') then ...`.
`erp.current_app_role()` returns NULL for an unmapped, inactive or missing actor.
SQL NOT IN then evaluates to NULL and the PL/pgSQL IF does not enter its refusal.
The X migration changes only that expression to
`if coalesce(v_app_role,'') not in('OWNER','ADMIN','STAFF') then ...`.

OWNER, ADMIN and STAFF are the existing function's internal-role allowlist.
The baseline STAFF role is intentionally inactive; its real mapped role is NULL.
An active STAFF case below is only a conditional compatibility fixture, not a
claim that baseline STAFF has access. Existing administration, trusted service-role
and permission-scoped execution-context branches remain exact. Owner, ACL,
SECURITY DEFINER attributes and search_path remain exact; no grant is widened.
Posted history is never rewritten, and X does not claim to repair any historical
unauthorized postings. Such history would need a separate reviewed correction.

CLI-created additive migration:
`20260913202948_erp_v2_6_20x_cp6_internal_role_fail_closed.sql`.
All admitted migrations/rollbacks through W remain byte-identical. W's failed
162/163 attempts and parser correction remain in Git history.

One function, one private capsule original; rollback restores the exact W guard.
Original guard SHA256 `da4bc536f6a9b4f882c6985ee981bd4f1ea63cf3575390389d8798e3654fa91f`;
X guard SHA256 `5dffcd53c0a5de609ae41482ca246d2afc806b9d92241253d680cf5c7fe1612e`.
Owner postgres; EXECUTE only postgres/service_role on the private guard itself.
Admission verifies all U/V/W capsules, four authorization helper definitions/ACLs
and inherited T helper/fact security. Because this guard spans modules, locked
post-use snapshots cover all210 ERP business/control tables, including W capsule,
roles, permissions and execution contexts. Only X's own capsule and the separately
validated migration ledger are excluded. Added or missing tables refuse rollback.

## Required native evidence, not results claimed by this document

Ten paired cases use actual current_user=session_user=authenticated and explicit
auth.uid/current_app_role/JWT-role assertions. JWT context is a synthetic SQL
fixture; new-path HTTP/UI reachability is not yet proven.

- Six NULL-role cases: unmapped subject, missing subject, inactive user,
  inactive role, spoofed app-role claims and baseline inactive legacy STAFF. Before X each must reproduce the W
  acceptance with POSTED scrap, one journal and exact0.03 cash. After X all deny.
- Four controls: external mapped role refuses on both versions; OWNER and ADMIN
  post. STAFF posts only after an explicitly reported activation inside that
  disposable case, which is rolled back completely. After X: seven atomic
  denials, two baseline-role acceptances and one conditional STAFF acceptance.
- The inactive-user case uses active ADMIN to isolate user inactivity from role
  inactivity. Both role and user activity are recorded and asserted.
- Every case restores the entire catalog/table boundary, runtime and schema USAGE.
- W25, V29, U25, Auth95, all earlier business/permission/race/browser proofs remain
  mandatory on X. No W acceptance gate is deleted to accommodate native164.
- F–X380 closed-admission schedules,95 proven backend body entries; setup208.
- X direct rollback guards8, including a mutation outside W's80-table boundary,
  and inherited/authorization preflight guards11;
  coherent capsule forgery fails before admission mutation; full533-function
  X-to-W definitions/owners/ACLs restoration; complete older rollback ladder.
- Final X application/platform/capsule absence, zero clone databases, physical
  cleanup, lossless artifact inventory and all183 source pins remain required.

## Preserved failed X attempt165

Native165 run34782307500/job103791417598 on
`0a9f7568d9da80d64ea7de7268c1863d18890472` failed step68 before X admission.
Five W NULL-role posting paths reproduced with actual authenticated identities,
POSTED documents, balanced0.03 journals and exact cash effects; external, OWNER
and ADMIN controls passed. STAFF_CONTROL failed its actor oracle because the
baseline STAFF role is inactive in admitted v2.6.17. This was a fixture assumption
error. Every case, the unseeded runtime and schema USAGE restored exactly.
The forward fixture correction retains that baseline as a new NULL-role case and
labels active STAFF as a conditional disposable control. No SQL or deployed role
is changed. Original failed artifact10325860121,2,730,493 bytes,SHA256
`946ab47f4cacfcb5cef7230e7c1cfb41d1363f207732b2e70bb2ffc55a1f94a9`;
recovery artifact10325775162,4,263,766 bytes,SHA256
`ddd4abebd5f6abc6ca95878e88b07ac336a764bebcafc9b85594eedb7df3894c`.
CodeQL40 passed three languages with zero findings on the failed native HEAD.

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.
CP6 closure → CP7 rev3 WIP-first → CP7.5 → CP7C → CP8. CP9 obsolete.
