# CP5 independent audit handoff

This handoff freezes CP5 for an independent read-only audit. It is not an
approval to merge, deploy to production, invite a real owner, or mutate the
legacy ERP Garment project.

## Exact target and commit shape

- Repository: `Hanjay6688/-erp-garment-ux`
- Pull request: `#23`
- Branch: `pre-cp5/cutting-persistence-pickup-wip-r1-20260903`
- Base `main`: `d5c48ce5c8daa7e6da92dc9d690d9b36879e74c1`
- CP5 source base: `8bfac13b91ea1be92111139e2fddcabccf9ae19a`
- CP5 source-base tree: `a9b193010266bb686c57709865a992769a835855`
- Closure code/evidence commit: `264d6aa3512884db8454fdfb8f9e6df37697628b`
- Closure code/evidence tree: `cd69ab82958817884e5a2e6a7f76f93369bc0877`
- Closure parent and hosted-runtime source: `e2745a2f3cf77735913967dfb57151069513bbf1`
- Hosted-runtime tree: `f0bbaefdc2a44d101f762342e4b82f96d3eddfdd`

Resolve branch HEAD immediately before review and reject drift or a concurrent
writer. The final handoff commit must have `264d6aa3512884db8454fdfb8f9e6df37697628b`
as its parent. Its diff must contain only this handoff, the hosted evidence,
the CP5 source-hash manifest, and backend ownership v3. The application, SQL,
tests, and release guard must remain byte-identical to the closure tree above.

## Delivered functional boundary

| Area | CP5 truth boundary |
| --- | --- |
| Auth and access catalog | Connected to ERP Enteng through canonical public facades |
| Master Pola | Connected; immutable pattern identity continues downstream |
| Potongan | Connected persistence and posting |
| Bagi Potongan / Pickup | Connected distribution, roll-size reconciliation, and server Pattern filter |
| WIP | Connected continuity and server Pattern filter |
| Barang BS / Rework | Connected workspace, server Pattern filter, mutations, claims, recovery, and reversals |
| Laundry | Pattern filter present in UX, explicitly `SIMULATION_ONLY` until CP6 |
| QC / Final | Pattern filter present in UX, explicitly `SIMULATION_ONLY` until CP6; a zero-result filter has no hidden-detail fallback |

The CP5 dispatcher owns twelve canonical actions:
`CREATE_MANUAL_BS`, `CLASSIFY_BS`, `SAVE_REWORK`, `COMPLETE_REWORK`,
`DISPOSE_BS`, `HOLD_BS`, `RELEASE_HOLD`, `REVERSE_DISPOSITION`,
`REVERSE_REWORK_COMPLETION`, `SAVE_CLAIM`, `RESOLVE_CLAIM`, and
`REVERSE_CLAIM_RESOLUTION`. It covers stuck, missing, damage, and other claims;
receipt/allocation lineage; damage-capacity serialization; holds; rewash and
rework; idempotent replay; row-version rejection; and audit-safe reversal.

## Recorded ERP Enteng state

| Application | Source ledger | Platform ledger | Source SHA-256 |
| --- | --- | --- | --- |
| `v2.6.18` | `20260903022604` | `20260903060213` | `6a568a78ad0b9baa2ef5ee958ee967d7c997cc1f4dfb7f0e4ef5e6ff69e5038f` |
| `v2.6.18a` | `20260903070931` | `20260903105741` | `d024a9ef2c8b1d5d9c529669b0b46a7588575f3bdc6788252c1b90d0ab2aae6a` |
| `v2.6.19` | `20260903070932` | `20260903105814` | `79e7b51b82759f1f4579fc373d11e41a668f312a569425aad2fdc2c4d6d68aa6` |

Both hosted transactional acceptance suites passed and rolled back their
fixtures. The final hosted Auth/JWT run passed 31/31 assertions across OWNER,
operator, view-only, unmapped, and anonymous boundaries. It proved real
password sessions, private-schema denial, idempotency/conflict handling,
server-side Pattern empty state, role-specific post/reverse behavior, stale
version rejection, authoritative refetch, global logout, and revoked refresh.

Synthetic Auth, access, BS, resolution, rework, hold, idempotency, execution
context, and scoped audit residue all returned to exact zero. The temporary
HTTP extension and credentials were removed. The 36 pre-existing audit rows
were preserved. See `docs/evidence/cp5_hosted_uat_auth_e2e.json`.

## Closure CI bound to the code tree

Commit `264d6aa3512884db8454fdfb8f9e6df37697628b` has five successful checks:

- Build push run/job `33751681211` / `100636432796`; dist artifact
  `9891842446` with SHA-256
  `dfd34b1ac19ec36883f586c803578146f37015c504a2f09fe9f1c3902879a27b`;
  browser artifact `9891840562` with SHA-256
  `21a7c18ccfe3809ccc4ae65acb5c0cbc6096110641fd9869d6cd6b06e063eb83`.
- Build PR run/job `33751686144` / `100636448834`; dist artifact
  `9891848918` with SHA-256
  `e1c1ca186ffd8fef59c06b389a891d6c86d826e6811225c991ed6684ca23d4cf`;
  browser artifact `9891846664` with SHA-256
  `cb2a782c8d55478f8bdbbef4ddf0ca2d6e0b0c8552de62aa19facd573a222ffc`.
- CP5 full-schema run/job `33751681199` / `100636432739`; artifact
  `9891955134` with SHA-256
  `89bf947818e65fd90126eaf11f6426a12389c275f8faaa0f5fca217b7fe62347`.
- Pre-CP5 full-schema run/job `33751686266` / `100636448934`; artifact
  `9891913344` with SHA-256
  `8c64c3e90cbb8dc7688b4bc944b0dff154613e9c90d8850b42f3a6924f7599e2`.
- Workers build check `100636558235`, build
  `823c8b78-863f-4731-b0e7-f68050ac9d83`.

CI installed pinned Chromium and passed all eight desktop/mobile browser cases.
The CP5 full-schema job passed both real two-connection races, real local
Auth/JWT, affected accounting/HPP/stock regressions, wrong-ledger rejection,
and the rollback ladder `v2.6.19 -> v2.6.18a -> v2.6.18 -> CP4.5`, with final
disposable residue zero.

## Required independent checks

1. Re-resolve PR head, parent, tree, and base; stop on drift or concurrent
   writer. Confirm the evidence-only commit shape described above.
2. Run `npm ci`, `npm test`, `npm run test:security`, and `npm run build`.
   Require 25/25 test files and 165/165 tests, zero orphan/direct-table access,
   80 effective owned backend/proof files, and a clean client-secret scan.
3. Run or inspect `npm run check:cp5` and `npm run check:backend`. Verify all
   52 candidate source files against `docs/evidence/cp5_r1_source_hashes.json`.
4. Recompute the three migration hashes. Confirm the recorded migrations were
   not rewritten and each rollback binds the exact platform version, name, and
   source hash in match, conflict, and delete predicates.
5. Inspect the full-schema artifact and logs for all twelve actions, claim and
   damage-capacity cases, the two real races, Auth/JWT role matrix, rollback
   ladder, predecessor regressions, and zero final residue.
6. Inspect the hosted evidence independently. Do not relabel the manual hosted
   run as CI, and do not treat the immutable UAT preview as a production deploy.
7. Confirm Laundry and QC remain honestly labelled simulation. CP6, not CP5,
   owns their canonical backend connection.
8. Recheck ERP Enteng and legacy read-only before any post-audit writer action.
   Stop on a hash mismatch, new writer, waiting lock, long transaction, or
   unexplained business residue.

## Truth and authorization boundary

- ERP Enteng UAT migrations `v2.6.18`, `v2.6.18a`, `v2.6.19`: recorded
- Hosted CP5 Auth/JWT evidence: `MANUAL_HOSTED_UAT_VERIFIED`, 31/31 PASS
- Exact closure-tree CI: 5/5 PASS
- Legacy ERP Garment mutated: no
- Canonical Worker promoted: no
- Production deploy or production GO: no
- Independent audit verdict: pending
- Merge authorization: pending independent PASS

