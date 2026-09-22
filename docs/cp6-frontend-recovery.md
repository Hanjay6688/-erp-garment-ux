# CP6 frontend recovery family — writer checkpoint

Owner mandate: execute ERP V3.2 Review R1. Parent checkpoint:
`aeda44756e5302568677514a52713e123145bf40`, tree
`86341797587d7adaf02e4c87b1fc34e9a149e0a8`.
One writer; competition branch only; `production_go:false`; CP7 not started.

## Scope and evidence boundary

This successor addresses AUD-A01–A05 and the existing connected production
surfaces of AUD-G15 together. SQL, installed functions, grants and admitted
migrations/rollbacks are unchanged. AL remains the backend generation.
This is a writer successor, not an independent acceptance or CP6 lock.

Original source, before repair, failed 19 of 33 directed DOM/parser checks:
six uncertain BS error responses discarded their envelope; thirteen malformed
WIP cases were accepted as usable facts. The 14 controls passed.
See `docs/evidence/cp6-frontend-original-counterexamples.json`. These observations
prove frontend behavior; they do not establish duplicated database effects.

| Path | Change and verification requirement |
| --- | --- |
| BS / rework / claim | Keep original UUID, action, payload and version on uncertain replies; validate the actual CP5 action/result receipt. Preserve corrupted or inaccessible storage without deleting it. Raw PCS cannot be rounded or clamped. |
| Cutting / Pickup, including DELETE and SAVE_DRAFT | Persist the request before sending. Validate the typed receipt, retire the old form on commit, and require a valid refresh before another write. Drafts remain editable by reopening their current server state. |
| Laundry / QC | Reuse the shared production coordinator while retaining the existing exact CP6 UUID/action/committed receipt and committed-form acknowledgement. Search facades and permissions stay unchanged. |
| WIP reads / flags | Validate required identity, timestamp, COUNT, version, flags and distribution totals. Malformed or stale responses display unknown totals and cannot enable a flag write. Flags use the same durable recovery path. |
| Cross-domain/tab | One Web Lock per project/app-user for the five writer domains. Existing CP5/CP6 keys remain readable. A persistent generation detects completed changes even if a tab missed both storage events. Every command rereads storage under the lock. No Web Locks means read-only. |
| Sessions / navigation | Invalidate readiness on identity/permission changes and unmount. Do not dispatch a command whose original screen/session retired while awaiting its lock. |

Initial database statement rejection and rejection during replay are different:
a later role denial can occur before the server reads the original idempotency
result. Any replay rejection therefore retains the uncertain original envelope.
HTTP status alone is not rollback proof. Unrecognized errors remain uncertain.

The UI barrier conservatively covers all five connected production writers
because these workspace responses do not expose a complete dependency graph.
Unrelated read surfaces remain available. Server capacity/version locks continue
to govern different users and devices; browser coordination does not replace them.
Evidence concerns tabs running this candidate and persisted legacy envelopes,
not every older deployed browser build. No hosted target was used.

COUNT input is a nonnegative integer within the supported range and source
capacity. Measured quantities accept decimal comma/dot with at most six decimal
places and reject representations that lose precision in the browser. Raw input
stays visible. Invalid input cannot become a different payload quantity.

## Verification at initial checkpoint

- 332 local unit/DOM tests passed, including actual mounted Cutting/Pickup forms,
  raw input, lost reply/reload, corrupt storage, rejected replay, missed generation,
  same-frame refetch, no Web Locks, cross-domain blocking and retired navigation.
- TypeScript, source/RPC ownership, the existing static gates, production build
  and client-artifact scan passed. No orphan runtime source or new RPC facade.
- Chromium download in the local runtime timed out. Local Chromium is not PASS.
- The combined CI now also runs existing CP5/CP6 desktop/mobile browser contracts
  and nine additional real Auth/UI/HTTP/database recovery cases. Those cases use
  actual candidate RPCs; transport faults occur only after a real commit or on
  read responses. Stock, WIP, journal row counts and pickup allocation are read
  directly from the disposable database as an independent arithmetic boundary.
- Native and browser evidence on this successor is **PENDING** until the exact
  candidate run and artifact are checked. The original full AL business230,
  import/value/concurrency/maintenance/restore/cleanup gates remain required.
  The 12 date-policy HOLD cases must not be relabelled PASS.

No automatic global or independent PASS. AUD-S01–S06, B04, G07/G08 and the
separately staged accessories/laundry change requests retain their R1 scope and
unresolved policy decisions. Demo PR27 remains on main; this branch has not
deployed it or changed the demo. After this family gate, continue the remaining
CP6 families and obtain independent acceptance on the final candidate.

## First CI attempt retained

Candidate `cdb7738cae95504033a3dde37e5a0c8d9653ae40`, tree
`880606814c623cf294acaee512c832934daded42`, run `35648220930` stopped
before database setup. Unit/DOM, build and static gates passed. CP5 browser
contracts: 10 passed, 2 failed at the same desktop/mobile success-message
assertion, which still expected the old `HOLD BS tersimpan` copy. The request
count assertion had already passed. Update only that message assertion to the
shared coordinator's confirmed-refresh copy; retain exact action/payload/version,
same-frame request count and browser error checks. CP6 browser/native remain
INCOMPLETE on this attempt. Artifact `10660674012`, SHA-256
`0278c2c6f9d38f52653add708e243628581aff2e5346e692387c510eba50feab`.

Run `35648649954` on `a9dcdd17e3da60737b3d16380bb0e788829de856`
retained the same 10/12 result: the updated exact-copy assertion omitted the
final period. Correct that punctuation; no product or business oracle changes.

Run `35648994561` on `0fce40bdff72fb6d726ceee423a2405e222dea6f`
passed 332 unit/DOM, CP5 browser12, CP6 browser26, and the original 43 real UI
cases. The AL business/value/import/concurrency/maintenance groups, exact rollback
chain and cleanup steps completed successfully. The new recovery cases did not
start: Supabase's ordinary fixture `postgres` session could not execute `SET
SESSION AUTHORIZATION authenticated`. This is a fixture setup refusal, not a
business counterexample. The successor creates the Cutting draft through the
already-established real Auth/HTTP RPC helper. No new grant or role privilege,
guard change, or product change is introduced. Native recovery remains INCOMPLETE
until that successor passes. Artifact `10661644950`, 61,223,917 bytes, SHA-256
`c37b9fa50a5a1b0f114951823f64a9b1c48451ff0be9da15a72872f8de097cd3`.

Run `35650814859` on `5603bfb7520d3fa522a5ce929192e69eeef95309`
passed the same existing groups and created the new draft through real Auth/HTTP.
The recovery runner then stopped at its warehouse selector: an exact wrapping-label
match omitted the select's option text. Use the actual combobox accessible-name
prefix; assertions, product, database and guards remain unchanged. Recovery9 is
still INCOMPLETE; CodeQL on this candidate passed. Exact rollback and cleanup
passed. Artifact `10662423099`, 61,218,140 bytes, SHA-256
`6830bc7f86d0abd70a672d28262b84a46f43b543f0e97b7ea3f91c6ac0088030`.

Run `35653575907` on `3b29a5335c19b32583653e9068120d8e66e433e6`
completed the first eight recovery cases. Cutting posted stock10→0/WIP0→100;
exact replay left those facts and two journal rows unchanged. Cross-tab QC reads
worked while writes stayed blocked. Pickup posted exactly ten pieces once and
survived read failure; strict WIP parsing accepted the original response. BS was
committed once behind a simulated gateway503 and its original envelope survived.

The ninth case exposed another UI path in this family: the still-open creation
dialog covered the page-level Reconcile button. The successor places the same
feedback and recovery control **inside either BS or claim dialog**, preserving
the form values and exact pending request. Desktop/mobile browser cases exercise
both dialogs, including edits that must not change the original replay payload.

That attempt also exposed a test-runner error: its response-wait promise rejected
before the obstructed click was awaited. Node terminated before the UI/Auth
cleanup `finally` block. AL→AK→AJ→AI restoration passed; the final AH structural
comparison passed but its zero-user assertion failed. Whole-clone and container
disposal completed, but Auth cleanup/exact final restoration are **not PASS** on
this attempt. The successor awaits each listener and browser action together so
failure enters the existing cleanup path; it marks the UI report PASS only after
all required groups complete. It does not bypass click actionability or alter the
rollback assertions. Artifact `10664395010`, 61,209,342 bytes, SHA-256
`37e00ffda55216c6762fd28dc5905b3e54e4b7816ff64d3930b533ef82b29b05`.

## Next original foundation qualification, not a product repair

### Verified checkpoint4e74 and subsequent AM trial

`4e74e25270c6a062d98e1adaa58cf50ea22e2e8c`, tree
`da287f7d1d0ef429e244fafef37e0bb4a1c42b94`: run35657686329 and
CodeQL35657686325 SUCCESS. The qualification collected6 controls,5 transfer
counterexamples,4 gaps and0 incomplete. The7PCS dozen/gross cases were refused
atomically at6.999996/6.999984; no fractional stock posting was established.
Frontend332, CP5 browser16, CP6 browser26, original UI43 plus gaps, HTTP95
assertions/62 role-facade cases, and native recovery9 passed in their stated
scope. Exact final restore533 functions/223 tables, Auth/app users0 and cleanup
passed. Artifact10665794614:5,904,079 bytes/62 entries, SHA-256
`db5cd526467db73b93549ea5d3b115f0c9ed1156414678b1567ca724eaed0223`.

Recovery also passed on the product-identical79587 before that fixture repair:
run35655818159, artifact10666313180,61,235,866 bytes/334 entries, SHA-256
`e611bc6a1e3fd0de77197b5bbbfcded73ff488edae4918d89ddd3fc997494ac9`.
The overall79587 run failed on the four old PCS fixture errors; recovery9,
existing AL business230/import31/values65/concurrency/maintenance, restore and
cleanup passed separately. None of these counts supplies independent acceptance.
The4e74 focused profile did not repeat those large unchanged AL groups.

The successor now adds **unaccepted AM trial source** for the complete transfer
family. Six existing functions change, preserving identities/owners/ACLs:
SAVE/POST/REVERSE transfer, the stock insertion guard, chronological cost replay
and its checkpoint helper. No new facade or table of business facts is added.
The CLI-created stamp is20260921214120, proved by artifact10665794614. Existing
admitted SQL remains byte-identical.

The proposed repair validates every locked line, prices each IN from its paired
historical OUT, keeps paired movements adjacent during cost replay, checks
effective location/roll prefixes, validates checkpoint recurrence, preserves
original snapshots and gives reversal legs the matching value. It removes
unused DRAFT children before their parent, preserving the parent guard. Original
native cases will qualify the additional reversal-value/DRAFT-delete paths
before the repaired definitions are installed in that test transaction.

Admission refuses existing incomplete/imbalanced transfers, mismatched reversal
values or negative effective location history for review. It does not choose a
date policy or rewrite old facts during installation. Full-price PCS and report
date decisions remain outside AM.

`[cp6-am-trial]` runs30 bounded SQL cases:8 original/admission cases and22
successor controls, then exact SQL restore and whole-transaction rollback.
Minimal synthetic masters and an ordinary authenticated OWNER are used; no
guard is disabled. The temporary schemaUSAGE and all fixtures must disappear.
The old AL UI/HTTP/recovery groups still run after restoration. **SQL trial is
PENDING and is not full AM Writer PASS**: full business/integration, actual
committed maintenance/admission and transfer concurrency remain mandatory after
the family stabilizes. The AL-only full profile is deliberately refused while
the AM full-gate integration is pending. This keeps CI from implying that an
uninstalled migration has passed the combined product gate.

First qualification: `806d12da9ec802ee5eebd18a7d73c576092f8d72`, run
`35654563637`, artifact `10666055541`, SHA-256
`9bc4682e54807fb70a323132355ce3d582aec1b00aa5f2700ae29769aec2b3c8`.
Fifteen cases were collected: 4 controls, 5 proven counterexamples in three
transfer paths, 2 selector gaps, and 4 **INCOMPLETE** PCS fixtures. The original
category trigger already seeds dozen/gross conversions; the fixture incorrectly
attempted duplicate effective ranges. The next fixture verifies the installed
standard conversions without inserting replacements or modifying the guard.
All fifteen case snapshots, the schema privilege and all 690 runtime objects
were restored exactly. The old BS dialog obstruction then interrupted recovery9
and Auth cleanup as in the preceding attempt; the overall run is not PASS.

The transfer observations require repairs before CP6 acceptance: backdated
transfer10/100 changed global value3000 to3050/3500 while global qty200 and
journal remained unchanged; a mixed/all-inactive draft became POSTED with2/0
movements instead of4/2; a backdated outbound created a historical location
prefix of−5. A valid PO201 and draft101 remained absent in default, exact-query
and offset responses even though original SAVE_DRAFT succeeded. These are
original installed AL API observations, not deliberately damaged functions.

Retries marked `[cp6-foundation-focused]` have a separate admission: product,
SQL, grants, runtime and all unrelated tests must remain byte-identical to
`79587cc225cc70391bf59beb146696229a77702b`; only this document, the qualifier,
workflow and its source-pin map may differ. This profile runs the native
qualification, frontend/browser/HTTP recovery, exact restoration and cleanup;
it does **not** rerun business230/import31/value65/concurrency/maintenance or
declare full AL acceptance. The full profile retains all existing assertions.
The next backend repair will require fresh affected business/integration gates.
The pinned CLI also generates an empty next-migration file in isolated runner
scratch; this is provenance only, not an installed or accepted repair.

The same disposable clone now collects 15 independent arithmetic/control
observations for S01–S05, with every case rolled back before the next. These are
writer qualification cases on the installed AL source, not independent acceptance.
They cover whole PCS versus factor12/144; chronological versus backdated transfer
value; active/mixed/all-inactive transfer lines; current versus historical location
stock; and eligible PO201/draft101 outside the original selector windows.

The inactive-material scenario must first prove nonzero-stock deactivation is
refused. It then uses the original receipt reversal to zero stock and the normal
versioned deactivation API. No guard is disabled, no product function is altered,
and no posted row is edited or deleted. Successful ordinary commands establish
all physical movements. Count conversion that is refused atomically is a feature
gap/control, not proof of damaged posted stock. Price policy remains unresolved.

Legacy native function calls use the existing authenticated OWNER EXECUTE grants;
the missing schema USAGE, if any, is temporarily granted in the uncommitted
qualification transaction and exactly restored. That grant is explicit evidence
scope and does not prove a private function is an exposed HTTP endpoint. Runtime
690 objects, function catalog and transactional table boundaries are compared;
the parent workflow owns real Auth cleanup and whole-clone disposal. All original
AL and frontend requirements remain. Findings are retained as CP6 blockers and
must be fixed/proven before final acceptance; a completed qualification is not PASS.


## AM integration checkpoint — 2026-09-21 (not accepted)

The first AM SQL trial at `4b085e70569e63cd4ecc15a4460574aef86368a2`
(tree `73a7c6d8a7fea6ece288f292213fac20e8073352`) failed overall.
Run `35661132208`, artifact `10667539172`, 5,905,261 bytes / 59 ZIP entries,
SHA-256 `c3df7182789b9011d055c34e4a60e0f49bc6cd02573a7f17f2b47a352be0ab75`.
Counts: 25 controls, 3 additional original bug proofs, 2 incomplete fixture cases.
The incomplete cases tried duplicate `(transfer, material, roll)` item rows;
the original unique constraint correctly refused them. They are replaced by valid
multi-material roundtrips, with the duplicate refusal retained as explicit controls.
The original reverse-transfer location-value residue (qty 10 and 100) and DRAFT
DELETE failure are now native-proven. AM passed both single-material reversals
and deletion/replay. All SQL/table/catalog/schema-USAGE restoration was exact.
AL HTTP/UI/recovery and full AH restoration/physical cleanup also passed.
CodeQL `35661132354` succeeded. The failed trial remains evidence, not acceptance.

The next candidate runs the unchanged AM SQL bytes in the committed disposable
runtime, then the hash-pinned 230-case business oracle, native import31/value65,
4 import + 12 direct + 16 original + 12 work + 12 new transfer schedules,
20 maintenance schedules, controlled midnight4, HTTP/UI/recovery, exact rollback
refusals and physical cleanup. The original business assertions are not edited.
SQL trial expands to 34 cases (26 successor controls), including dependent transfer
source reversal after stock returns to the intermediate location. Final acceptance
requires every required group and restoration gate. CP6 remains HOLD for the
known date/PCS/selector/CSV gaps and independent review; production_go:false.


Integration wiring attempt `b6a2132e197562899e44329ae63741c397a6572c`
(tree `989fa1dded4dc8bc41242fa5efa0553e89368945`) stopped before database setup
in run `35662899969`: the static maintenance pin still described AL. No AM
business case ran. The successor static contract now verifies the AM checksum
and removes only its explicit target bindings to recover the exact accepted AL
checksum; all prior AL/AK/AJ body checks remain. The controller endpoint and
admission/drain/reopen implementation are unchanged. Artifact `10667931508`,
SHA-256 `0941d1dca53bf0b38f4539263a8c6c67f88c5749608a159629b33383b561d28b`.

AM combined runtime at `bf05659d4f8e99d0332215772d658417e4233cc8`
(tree `e5ac4db612e5c9097daf0c6a446abeafffc29cd2`) completed successfully in
run `35663140263`; CodeQL `35663140196` also succeeded. The native final seal is
`WRITER_PASS_AFFECTED_AM_FAMILY`, not independent or global CP6 acceptance.
Fresh evidence: SQL trial34 (31 controls, 3 original additional bug proofs),
business230 (179 PASS, 39 controls, 12 date-policy HOLD), import31, values65,
4 import + 12 direct + 16 original + 12 work + 12 transfer two-session schedules,
20 maintenance schedules, midnight4, original HTTP/UI and recovery9. AM foundation15
is 11 controls, 4 previously known PCS/selector gaps, 0 bugs, 0 incomplete.
Exact AM-to-AL restore: 533 functions / 227 tables with eight refusal controls;
final AH restore: 533 functions / 223 tables, Auth/app users0 and cleanup PASS.
Artifact `10668124130`: 64,497,485 bytes, ZIP355 entries, SHA-256
`299684058ecb0e3f03c8ab18a374f4d944848268d4462348e89c89e8036fd4cc`.
Locally verified full hash, ZIP CRC/path safety and zero GitHub token/JWT/private-key
pattern matches. Durable copy: `cp6-am-combined.zip`.

The next bounded follow-up connects a real warehouse transfer to the existing
cutting, wages, FG, sale and two-stage late-invoice oracle in eight cases.
The original money/custody/report assertions remain byte-identical. Follow-up
admits reuse only after verifying the exact successful artifact above and proving
all product/frontend/SQL, original oracles and maintenance controller unchanged.
The large groups are explicitly `REUSED_EVIDENCE`; fresh34 transfer trial,
fresh8 actual crossflow, advisors and exact restore/cleanup are required.
A fresh follow-up failure remains a failure even when the preceding full gate passed.
CLI2.116.0 generated next AN stamp `20260921223438` in the successful artifact;
no AN migration or selector acceptance exists yet. CP6 HOLD; production_go:false.

Follow-up setup attempt `0014fd62c873825fd562c2bfc522b9dbfb916aab` / run
`35665232900` stopped before database creation because the evidence directory
was created only in the skipped frontend step. No new crossflow case ran.
Directory creation is now in the unconditional runtime-binding step. Failure
artifact `10668812374`, 288 bytes, SHA-256
`d33a46990a5df580ad60759fb5974de677823c1c04b3b42652ecc62de697af17`.

First native transfer/invoice attempt `1beefbb81b3c9e5294ed94e34a4bf9493c32b1ed`,
run `35665393541`, completed trial34 and all restore/cleanup controls, but all
eight new crossflow fixtures were INCOMPLETE: the generated warehouse code was
37 characters against the existing varchar(30) contract. No transfer/invoice
assertion ran and this is not an AM product bug. Synthetic identifiers are now
25 characters; no application SQL, guard or oracle changes. Artifact `10669071464`,
1,605,928 bytes, SHA-256 `59f62db7874818d0ae9f5b1095eebb411cdb1111712a6fad217866bbc3a417dc`.


AM transfer/invoice follow-up succeeded at `6b0aa79753b3dd5a0dd7cd77012094971e7fa8aa`
(tree `882986cd99b22fe1bb0192aa5841f0841ac7a23e`), run `35665864959`,
CodeQL `35665864905` SUCCESS. Eight genuine warehouse-transfer → cutting →
wages → FG/sale → staged invoices cases passed (two quantities, two session zones,
open/closed receipt date), 0 BUG_PROVEN, 0 INCOMPLETE. Transfer legs stayed neutral;
original snapshots stayed exact; consumed-roll reversal refused atomically.
Fresh34 trial and exact AM→AL→AH restore/cleanup passed. Full AM business/money/
concurrency/maintenance and HTTP/UI groups from `bf05659…` were verified and
explicitly reused, not rerun. Artifact `10669107236`, 1,613,668 bytes, ZIP45 entries,
SHA-256 `a909662a4c33099980f60bb2d6dc3bf0e26620d9c21c078679f1874fde07df7b`;
full hash, ZIP CRC/path and public token/JWT/private-key pattern checks passed.
Durable copy: `cp6-am-transfer-crossflow-qualified.zip`.

AN candidate now addresses S05 PO201/draft101. It adds a versioned private/public
read-only workspace, independent literal search/pages/totals, selected records
outside the current page, and draft model identity. The old v1 functions, all AM
mutations, grants and existing SQL remain immutable. The connected page keeps
unsaved quantities/PO/sizes across search and pagination; changed/missing/posted
selected drafts block commands until explicit reload/new. Read tickets bind the
current identity session so retired responses cannot apply; pending transactions
remain readable and retain the existing write barrier and exact recovery envelope.

AN uses authentic CLI stamp `20260921223438` from the verified full AM artifact.
Every inherited AM function and relation plus both new readers/owner/ACL is pinned.
Rollback removes only the new readers (no CASCADE), retains the exact legacy reader,
and restores the full AM public/ERP catalog and 228-table data boundary after the
unchanged closed-admission protocol. Static checks recover every prior AM controller
byte after removing only explicit AN target bindings.

Planned AN acceptance requires native28 selector controls, real HTTP/UI15 controls,
20 schedules on the new rollback edge, all original HTTP/UI/recovery cases, exact
11-refusal rollback and physical cleanup. Local 342 unit/DOM tests and the targeted
selector/session tests passed; native AN remains UNTESTED until the dedicated run.
AM230/import31/value65 and AM transfer/money/concurrency evidence may be reused only
through exact artifact hashing and unchanged SQL/oracle admission; the affected AN
reader, UI, permissions, recovery and rollback evidence must be fresh. The preserved
v1 reader will still show its original two pagination limitations; those old-reader
controls do not override new v2 native/UI proof and are not silently relabeled PASS.
CP6 remains HOLD for dates, PCS pricing, CSV/role scope and independent acceptance.
No main/demo/UAT/hosted/deployment change. production_go:false; CP7 not started.

First AN attempt `c3f8541d48c7adfc35faebbc4641fcca16471c76` / run `35668363525`
failed overall. Native28 and six real HTTP role cases passed, but the maintenance
runner used misspelled STAMP/NAME attributes before any of its twenty schedules.
The new UI found a real candidate layout defect: long PO labels enlarged the
automatic card grid track, and the adjacent size card intercepted the normal
search-button click. Seven of fifteen selector cases completed; remaining eight
were INCOMPLETE. Original UI43, recovery9 and exact AN→AM→AH restore/cleanup passed
separately. CodeQL35668363436 SUCCESS does not turn this run into acceptance.
Artifact10670407145:6,600,539 bytes /78 ZIP entries, SHA-256
`cd6d0eb859e73ab0acf0168eb6ed4c453b306c7979ba1e5b89ef6954ea710de7`;
full hash, CRC/path checks and selected token/JWT/private-key patterns verified.
The retry corrects only the runner attribute names and actual card/field grid
sizing. The original normal pointer search is also exercised at1440/980/390px;
no forced clicks, mocked successful responses, or weaker oracle. SQL unchanged.

Second AN attempt `c0b064e351ad7076a28451070fd186fb3be02135`, tree
`975b34a837f6bd47ceee941cfff891544c2d74dc`, run35669411173 failed only the
selector UI requirement:8/15 completed,7 INCOMPLETE. Native28, maintenance20,
original HTTP/UI43/recovery9, eleven refusal controls, exact AN→AM→AH restore
and cleanup passed separately. CodeQL35669411193 SUCCESS.
Artifact10669908582:53,541,445 bytes /319 entries; SHA-256
`028a31c8ec33b22e17e1d70468da28b37c7d6eabd88dadee30dc972691950513`;
full hash, CRC/path checks and selected token/JWT/private-key patterns passed.
Search clicks now passed at1440/980/390px, but the PO-next button overlapped the
select. The retained screenshot exposed the exact shared cause: the nested
CuttingPatternPicker carries `grid-column:span 2` for another two-column parent.
Inside this single-column identity card it created a second implicit grid track,
placing header/search and pagination/fields side by side. The earlier long-label
diagnosis was incomplete. A scoped `grid-column:1/-1` now confines this child to
the existing track; card content starts at the top. Other picker consumers and
all SQL remain unchanged. Normal pointer assertions are unchanged; failure
evidence additionally records computed child geometry.
