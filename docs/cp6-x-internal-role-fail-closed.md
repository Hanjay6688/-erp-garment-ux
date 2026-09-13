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
post-use snapshots cover all209 ERP business/control tables, including W capsule,
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

## Preserved failed X attempt166

Native166 run34783132979/job103793659074 on5f7f2de72492708312cf10512883de0a88fa961f
passed all10 before-X cases, then failed migration step69 at
X_FULL_ERP_BOUNDARY_CARDINALITY. The expected210 confused two schema scopes:
the frozen native pre-U snapshot has208 tables,207 ERP plus1 platform ledger.
U/V/W add3 ERP capsules, giving210 ERP tables before X; excluding ERP's separately
verified migration ledger leaves209 boundary tables. X's own capsule is excluded.
The forward unadmitted SQL correction keeps the exact same all-ERP selector,
fixes only the cardinality and emits actual count on failure. Function body,
owner and ACL pins remain unchanged. Native must also prove the exact209 names
against the frozen baseline plus U/V/W additions, then match the installed capsule.
No business table is removed from the snapshot. Failed artifact10325841490,
3,023,501 bytes,SHA25642e43e85b6a1c69040ad3d71c4f572d294ce952bedf58ec3ec75d3290be1809e;
recovery10324544485,4,263,766 bytes,SHA256752b4dce461e10151fdd08107c8ba8d6a168398724c620599cd84604bdd52ef4.
Original ZIPs/logs and all previous failures remain. CodeQL41 passed three languages
with zero findings on this failed native HEAD; it is not X writer acceptance.

## X admitted167; inherited UTC report-fixture failure

Native167 run34783920877/job103795821147 onabaa15a5c1c6f415045a1a04ed5754eb21a98ee5
admitted X (step69); exact209 table-name/capsule proof and X10,W25,V29,U25,Auth95
and core acceptance passed. All79 migration/rollback files through X are now
frozen. Step76 failed the old v20d reversal-only report fixture: it sets UTC,
then asks for current_date Sep13, expecting20 revenue, observing0. The inherited
native reversal calls _cp3_business_date(current_timestamp), whose Jakarta date
at21:35UTC is Sep14. This is a date-scope mismatch in the test oracle; the next
native run must substantiate actual journal dates and both period values.
The forward test-only correction keeps the UTC caller, independently derives
the expected Jakarta transaction date, and asserts inverse lineage/date plus
canonical20 and legacy-period0 when the dates differ. All previous amounts,
lifecycle assertions and residue checks remain; no business SQL changes.
Original artifact10325617682,6,064,661 bytes,SHA256
8d294c5798bcde1326266cfb3d4a7a23cfae44816d092ac203368b1ded02960d;
recovery10325628340,4,263,766 bytes,SHA256
7664d7e08607b0f837604a1b3134c8b9123c18a90e98d9f9b05576aa87a1a54e.
The race clone was physically removed, while its cleanup report correctly remains
FAIL because the step failed. CodeQL42 on the same SHA passed and was independently
verified in all three languages, zero findings. Native167 remains writer FAIL.

## Preserved failed168 and K period control

Native168 run34784660879/job103797825862 onf726c52c387a27a743cc7970f92f0c117eebc5bf
proved the corrected reversal oracle: UTC Sep13, Jakarta Sep14, actual inverse
journal economic/posting dates Sep14, canonical revenue20 and UTC-period0.
The complete34 races/three qualifications and E through J regressions passed.
Step85 K then passed5/6 cases, including all8 timezones, and failed CLOSED_PERIOD
with P0001. That old control also closes current_date UTC; after Jakarta advances,
the predecessor inverse's GL date is still open, so lawful replacement can succeed.
The test-only successor records both dates and the inverse fact, probes the old
period in a deliberately rolled-back subtransaction, then closes through the
actual inverse GL date and requires atomic refusal. It independently checks the
canonical date and greatest(business_today,closed_through+1) policy. No amount,
scope or prior assertion is dropped; all79 admitted SQL remain byte-identical.
Case failures now retain their primary error message as well as SQLSTATE.
Original artifact10326740326,6,107,436 bytes,SHA256
73bae8d72550bbf840b373d1ce25f86af4f9d0b4bee57b8bade5ead579c84fd7;
recovery10326635330,4,263,766 bytes,SHA256
781d64b932127c77b8435d2438c7b699759e439454d81e8cf13b304a5eb38d11.
CodeQL43 passed three languages and all original artifact bytes were verified
on the failed native HEAD. Native168 remains writer FAIL; new native proof required.

## Failed169 and evidence controls awaiting new native qualification

Native169 run34785408617/job103799867689 on4ff892364f70a4e11b90544e6deb3d17b36df40f
passed the business and race gates through step99, including K6 and eight
timezone subcases. Step100 then failed: all380 matrix cases report UndefinedColumn,
SQLSTATE42703. No matrix case or backend body entry is claimed as PASS. Later
X guards and the final binder were not reached. The job is FAIL.
Original artifact10327086710 is600,545,460 bytes,SHA256
89ff12a1063329bb500c0c3bf4854cd9824f90687d29061bb46cbe280a7c30a6;
it exceeds the connector's536,870,912-byte limit. The dedicated forensic workflow
verifies that original ZIP and preserves every payload through lossless transport.
It separately qualifies the suspected PL/pgSQL record/SQL-alias collision on
disposable native PostgreSQL17.6. This checkpoint does not claim a corrected
full-schema run; the exact matrix cause and its forward correction remain pending.
CodeQL44's three authentic zero-finding artifacts do not override native169 FAIL.

Read-only replay of native168's D report proves a final-binder type mismatch:
the new D fields are numeric JSON20.0/0.0, but cash_delta_equal accepts strings
only and was called with integer20/0. All four old predicates return false.
The correction parses this report as exact Decimal, requires finite numeric
types and compares exact20/0; it also matches the complete observation against
the original SQL NOTICE. The existing strict string comparator and all other
cash predicates are unchanged. Original evidence passes both corrected binder
implementations; ten negative controls each reject cent/subcent differences,
strings, booleans, non-finite numbers, log mismatch, dates and lineage changes.
This is an offline qualification, not a claim that native169 reached that gate.

Native168's frozen pre-U snapshot records zero sizes rows and111 app_permissions
rows. Updating the first sizes row is therefore a no-op on that baseline. The
corrected X direct-guard fixture records that old zero-row control explicitly,
then changes one existing app_permissions description. That table is outside W's
80-table capsule boundary, inside X's209, and has no DML triggers. The runner
requires exactly one affected row and exactly that table's hash to change across
all209 tables, an X_POST_USE_ROLLBACK_REFUSED: app_permissions refusal, and exact
restoration of every table. This guard still requires fresh native execution.
All DML guard mutations must affect rows before attempting rollback. Incremental
per-guard diagnostics preserve operands and error messages even if a later guard
fails. No migration, rollback or installed business function changes.

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.
CP6 closure → CP7 rev3 WIP-first → CP7.5 → CP7C → CP8. CP9 obsolete.
