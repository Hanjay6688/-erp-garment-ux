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
