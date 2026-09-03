# CP5 independent audit handoff

This handoff records the CP5 v2.6.19a audit correction after its exact code
head passed all five required checks. The next commit is evidence-only and
must itself rerun the same current-head checks before independent re-audit.
This is not approval to merge, deploy to production, invite a real owner, or
mutate the legacy ERP Garment project.

## Exact target and commit shape

- Repository: `Hanjay6688/-erp-garment-ux`
- Pull request: `#23`
- Branch: `pre-cp5/cutting-persistence-pickup-wip-r1-20260903`
- Base `main`: `d5c48ce5c8daa7e6da92dc9d690d9b36879e74c1`
- CP5 source base: `8bfac13b91ea1be92111139e2fddcabccf9ae19a`
- CP5 source-base tree: `a9b193010266bb686c57709865a992769a835855`
- Pre-correction hosted-evidence head: `7ac07d0f3d60436e44601061bc9584709efc67bd`
- v2.6.19a correction parent: `7ac07d0f3d60436e44601061bc9584709efc67bd`
- v2.6.19a correction code head: `2175bd8f199f6a5d860e7f517042e2efe35916e7`
- v2.6.19a correction code tree: `d845b1ff613774a150b999dbfa2b41b772e416e9`
- Final evidence-only head/tree: resolve from the PR after the evidence push;
  its parent must be the correction code head above and its own five checks
  must pass before re-audit starts.

Resolve branch HEAD immediately before review and reject drift or a concurrent
writer. The final evidence-only commit must descend directly from
`2175bd8f199f6a5d860e7f517042e2efe35916e7`; its cumulative diff may update
only this handoff, generated ownership manifests, and their validation
checkers. The code head manifest owns every correction byte, including the
forward migration, reviewed rollback, SQL acceptance, frontend contract,
browser/DOM proof, workflow, and evidence. Recorded v2.6.19 bytes remain
unchanged; the correction is the official forward-only v2.6.19a migration.

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

## Exact correction code-head CI

Correction code head `2175bd8f199f6a5d860e7f517042e2efe35916e7`
has five successful checks:

- Build push run/job `33774390975` / `100712335950`; dist artifact
  `9901021365` with SHA-256
  `9729560d4f063e673603c685f4ff803613806105bcc89d3d8455c388ae71d7e4`;
  browser artifact `9901019172` with SHA-256
  `31914693f2cee7acdd42a8f8eb42680cbf351739e4e553748853f484b9ca9f23`.
- Build PR run/job `33774401928` / `100712374137`; dist artifact
  `9901045905` with SHA-256
  `4f90cca51a0ba9c2ec7799b6636ac4205e36b6dfdc598e4db282ee1216ba1c1b`;
  browser artifact `9901043335` with SHA-256
  `bd04387cb5912fff80fc001fa04d2931d890e2e1496386cf504ed830135399cd`.
- CP5 full-schema run/job `33774390811` / `100712335295`; artifact
  `9901122437` with SHA-256
  `979d3ac9e23bbe86dcafbd01bddd52eb77ec2bf478a391b1d4424bbae1205a87`.
- Pre-CP5 full-schema run/job `33774401624` / `100712374712`; artifact
  `9901057447` with SHA-256
  `e232cf72bff897c399763bb65d417e6a11f6c0aa94696adb4b91d55b98fe0c17`.
- Workers build check `100712911183`, build
  `f1ee6e8f-9308-4a48-82eb-f01ed7837a82`.

The two Build runs each passed 25 files / 168 tests and ten Chromium cases:
two CP4.5, two pre-CP5 Pattern, and six CP5 BS Resolution desktop/mobile
contracts. Full-schema CI applied v2.6.19a once, rejected replay, proved
selected-only positive accounting and cumulative partial returns, ran real
Auth/JWT and both two-connection races, rejected post-use and wrong-ledger
rollbacks, completed the ladder
`v2.6.19a -> v2.6.19 -> v2.6.18a -> v2.6.18 -> CP4.5`, and ended with zero
disposable residue. The evidence-only successor must rerun the same five
checks; its run identities are intentionally resolved after this file exists.

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
- Exact v2.6.19a correction code-head CI: 5/5 PASS
- Final evidence-only current-head CI: required before re-audit
- Legacy ERP Garment mutated: no
- Canonical Worker promoted: no
- Production deploy or production GO: no
- Independent re-audit verdict: pending final evidence-head CI
- Merge authorization: pending independent PASS
