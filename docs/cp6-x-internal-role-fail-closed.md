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

OWNER, ADMIN and STAFF are the existing internal-role allowlist. This is not an
owner-only posting rule. Existing database administration, trusted service-role
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

Nine paired cases use actual current_user=session_user=authenticated and explicit
auth.uid/current_app_role/JWT-role assertions. JWT context is a synthetic SQL
fixture; new-path HTTP/UI reachability is not yet proven.

- Five NULL-role cases: unmapped subject, missing subject, inactive user,
  inactive role and spoofed app-role claims. Before X each must reproduce the W
  acceptance with POSTED scrap, one journal and exact0.03 cash. After X all deny.
- Four controls: external mapped role refuses on both versions; OWNER, ADMIN and
  STAFF continue to post. After X: six atomic denials, three lawful acceptances.
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

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.
CP6 closure → CP7 rev3 WIP-first → CP7.5 → CP7C → CP8. CP9 obsolete.
