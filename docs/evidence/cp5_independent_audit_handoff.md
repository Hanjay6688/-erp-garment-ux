# CP5 independent audit handoff

This handoff records the CP5 v2.6.19a audit correction while its current-head
CI is still pending. It is not yet the final independent-audit freeze and is
not approval to merge, deploy to production, invite a real owner, or mutate
the legacy ERP Garment project.

## Exact target and commit shape

- Repository: `Hanjay6688/-erp-garment-ux`
- Pull request: `#23`
- Branch: `pre-cp5/cutting-persistence-pickup-wip-r1-20260903`
- Base `main`: `d5c48ce5c8daa7e6da92dc9d690d9b36879e74c1`
- CP5 source base: `8bfac13b91ea1be92111139e2fddcabccf9ae19a`
- CP5 source-base tree: `a9b193010266bb686c57709865a992769a835855`
- Pre-correction hosted-evidence head: `7ac07d0f3d60436e44601061bc9584709efc67bd`
- v2.6.19a correction parent: `7ac07d0f3d60436e44601061bc9584709efc67bd`
- v2.6.19a correction head/tree: resolve from the PR after the writer push;
  current-head CI must bind to that exact SHA before audit starts.

Resolve branch HEAD immediately before review and reject drift or a concurrent
writer. The correction chain must descend from `7ac07d0f3d60436e44601061bc9584709efc67bd`.
Its source manifest must own every changed byte, including the forward
migration, reviewed rollback, SQL acceptance, frontend contract, browser/DOM
proof, workflow, and evidence. Recorded v2.6.19 bytes must remain unchanged;
the correction is the official forward-only v2.6.19a migration.

## Delivered functional boundary

| Area | CP5 truth boundary |
| --- | --- |
| Auth and access catalog | Connected to ERP Enteng through canonical public facades |
| Master Pola | Connected; immutable pattern identity continues downstream |
| Potongan | Connected persistence and posting |
| Bagi Potongan / Pickup | Connected distribution, roll-size reconciliation, and server Pattern filter |
| WIP | Connected continuity and server Pattern filter |
| Barang BS / Rework | Connected workspace, server Pattern filter, mutations, claims, recovery, and reversals |
| Rework/Rewash accessory reimbursement | Connected immutable BOM checkbox selection; only checked, actually installed accessories enter HPP and Mandor reimbursement |
| Partial rework return | Connected cumulative save without premature FG, HPP, journal, or payable posting |
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
| `v2.6.19a` | `20260903151034` | `20260903151034` | `204b9246f3c8c6464476da1a7f1574f5e0ae4c46f024c082704795b3eef5210f` |

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

The v2.6.19a source acceptance then passed against the installed hosted UAT
inside a rollback-only transaction. It proves mixed 3 GOOD/1 BS accounting,
selected Button-only HPP/reimbursement, explicit-empty no-fallback behavior,
REWASH Label-only reimbursement to the PO Mandor with zero vendor work fee,
cumulative partial saves, idempotency, immutable lineage, and reversal. Its
reviewed rollback also restored exact v2.6.19 function source/ACL/owner/comment
inside an outer transaction, which was rolled back to leave v2.6.19a active.
All scoped business rows, locks, and long transactions remained zero. See
`docs/evidence/cp5_v2619a_uat_acceptance.json`.

## Pre-correction CI baseline and required current-head rerun

The prior CP5 closure had five successful checks. These remain predecessor
regression evidence, but they do not count as current-head v2.6.19a CI:

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

Before independent audit, the updated head must rerun pinned Chromium,
desktop/mobile browser contracts, real local Auth/JWT, both two-connection
races, selected-accessory positive accounting, all predecessor regressions,
wrong-ledger rejection, and the rollback ladder
`v2.6.19a -> v2.6.19 -> v2.6.18a -> v2.6.18 -> CP4.5`, ending with zero
disposable residue.

## Required independent checks

1. Re-resolve PR head, parent, tree, and base; stop on drift or concurrent
   writer. Confirm the evidence-only commit shape described above.
2. Run `npm ci`, `npm test`, `npm run test:security`, and `npm run build`.
   Require every discovered test, zero orphan/direct-table access, zero stale
   ownership/hash entries, and a clean client-secret scan.
3. Run or inspect `npm run check:cp5` and `npm run check:backend`. Verify all
   57 candidate source files against `docs/evidence/cp5_r1_source_hashes.json`.
   The backend checker must independently report the same 57-file count.
4. Recompute the four migration hashes. Confirm the recorded migrations were
   not rewritten and each rollback binds the exact platform version, name, and
   source hash in match, conflict, and delete predicates.
5. Inspect the current-head full-schema artifact and logs for all twelve
   actions, selected-accessory/partial/positive-money cases, claim and
   damage-capacity cases, the two real races, Auth/JWT role matrix, full
   rollback ladder, predecessor regressions, and zero final residue.
6. Inspect the hosted evidence independently. Do not relabel the manual hosted
   run as CI, and do not treat the immutable UAT preview as a production deploy.
7. Confirm Laundry and QC remain honestly labelled simulation. CP6, not CP5,
   owns their canonical backend connection.
8. Recheck ERP Enteng and legacy read-only before any post-audit writer action.
   Stop on a hash mismatch, new writer, waiting lock, long transaction, or
   unexplained business residue.

## Truth and authorization boundary

- ERP Enteng UAT migrations `v2.6.18`, `v2.6.18a`, `v2.6.19`, `v2.6.19a`: recorded
- Hosted CP5 Auth/JWT evidence: `MANUAL_HOSTED_UAT_VERIFIED`, 31/31 PASS
- Hosted v2.6.19a transactional SQL and reviewed rollback proof: PASS
- Exact v2.6.19a current-head CI: pending writer push
- Legacy ERP Garment mutated: no
- Canonical Worker promoted: no
- Production deploy or production GO: no
- Independent re-audit verdict: pending current-head CI
- Merge authorization: pending independent PASS
