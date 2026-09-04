# CP5 v2.6.19b independent re-audit handoff

This handoff records the forward-only CP5 reliability correction requested by
the ERP owner after the prior independent audit returned two new P1 findings
and one P2 finding. Runtime code and migration bytes were frozen at the exact
code head below, all five required checks passed there, and v2.6.19b was then
installed and verified on ERP Enteng UAT. The successor commit is evidence and
checker only; it must pass the same five current-head checks before re-audit.

This is not authorization to merge, deploy to production, invite a real owner,
or mutate the legacy ERP Garment project. `production_go` remains `false`.

## Exact identity and commit shape

- Repository: `Hanjay6688/-erp-garment-ux`
- Pull request: `#23`, open, draft, unmerged
- Branch: `pre-cp5/cutting-persistence-pickup-wip-r1-20260903`
- Live `main`: `d5c48ce5c8daa7e6da92dc9d690d9b36879e74c1`
- Live-main tree: `70f7bf3c0265520eac5aafff747f448ed8be3e6b`
- CP5 source base: `8bfac13b91ea1be92111139e2fddcabccf9ae19a`
- CP5 source-base tree: `a9b193010266bb686c57709865a992769a835855`
- v2.6.19a historical code head: `2175bd8f199f6a5d860e7f517042e2efe35916e7`
- v2.6.19b runtime code head: `abd2e9e0dad09a2fe33d330ddc83872da3c54b53`
- v2.6.19b runtime code tree: `b8db214b145d4bac61bb62c21ac43210a42df57e`
- Evidence/checker successor: resolve from PR immediately before review; its
  first parent must be the v2.6.19b runtime code head above.

Reject branch drift, a concurrent writer, a non-direct evidence parent, or any
runtime/migration change after `abd2e9e0dad09a2fe33d330ddc83872da3c54b53`.
The evidence successor may change only this handoff, the v2.6.19b UAT evidence,
access/ownership evidence and validation checker, and generated ownership
manifests. Recorded v2.6.19 and v2.6.19a bytes remain immutable; v2.6.19b is a
new official forward migration.

## Owner business truth encoded by v2.6.19b

The controlling rule is: **Reliability data is supreme; finance, stock, and HPP
must remain simultaneously correct.** A mutation touching payment, stock, HPP,
physical custody, claim capacity, or entitlement must be atomic, conserved,
idempotent, concurrency-safe, and safely reversible. A successful mutation may
not be presented as authoritatively refreshed if the follow-up read failed.
See `docs/erp-reliability-invariants.md`.

### Rework defaults and accessory payment

- Default checked does not mean “all BOM.” The server decides the current
  unpaid/unentitled baseline. Only rows proven unpaid default on.
- Already entitled, post-FG, ambiguous, or unprovable rows default off.
- A real replacement outside the unpaid baseline is allowed only through an
  explicit operator selection recorded as `MANUAL_REPLACEMENT`.
- Rework component/labor defaults follow remaining work entitlement, not cash
  payment timing. The immutable selection records its basis.
- The backend rejects missing/duplicate/unknown selection metadata and never
  falls back from explicit `[]` to the full BOM.

### Laundry claims

- Supported claim types are exactly `MISSING`, `STUCK`, and `DAMAGE`; `OTHER`
  was removed from UI and database constraint.
- `MISSING` and `STUCK` consume one shared authoritative outstanding-delivery
  capacity. Multiple claims cannot exceed the physical outstanding quantity.
- A delivery source must be in an authoritative dispatched state. `DAMAGE`
  requires a matching `POSTED` receipt and is conserved against receipt lines.
- Delivery, receipt, return, claim, resolution, and reversal guards use a
  consistent receipt-to-delivery lock order and block source reversal after
  active dependent claim lineage.
- “Chemical unavailable” is not an `OTHER` claim. The vendor physically
  returns the PO quantity; a later wash is a new delivery/service leg. Two
  genuine legs may therefore be paid independently. A full unwashed return is
  recorded as a physical return, not an unconserved claim.

### Stale UI safety

After a mutation commits, a failed authoritative refetch closes the mutation
modal, shows an explicit stale-state warning, and freezes every writer. No
further write is possible until an authoritative workspace read succeeds.

## Owner accessory master reference

Payment uses the broad category even when Mandor pickup records are more
granular. The frontend reference master now matches the owner-provided sheet:

| Category | Pickup/issue reference | Reimbursement reference |
| --- | ---: | ---: |
| Kancing | 495 / pcs | 500 / pcs |
| Centang | 200 / pcs | 200 / pcs |
| Kulit | 1,000 / pcs | 1,000 / pcs |
| Sleting | 29,900 / lusin | 2,500 / pcs |
| Plat | 500 / pcs | 500 / pcs |
| Hang Tag | 7,150 / lusin | 600 / pcs |
| Lock Pin | 300 / pcs | 300 / pcs |
| Kain Kantong | not configured | not configured |
| Label | not configured | not configured |
| Kain Keras | not configured | not configured |

The final three categories are future possibilities and must not silently
produce a payable rate. The connected database master is currently empty on
UAT, so this is a checked reference/readiness correction, not silent seed data.

## Delivered CP5 boundary

| Area | Current truth |
| --- | --- |
| Master Pola | Connected, immutable pattern identity |
| Potongan | Connected persistence and posting |
| Bagi Potongan / Pickup | Connected distribution and roll reconciliation |
| WIP | Connected continuity and server Pattern filter |
| Barang BS / Rework | Connected workspace, mutations, claims, recovery, reversal |
| Rework/Rewash accessories | Server-proven unpaid defaults plus explicit real replacement |
| Partial rework return | Cumulative save with no premature FG, HPP, journal, or payable |
| Laundry page | Pattern-filter simulation until CP6; CP5 claim actions live only inside BS Resolution |
| QC / Final page | Pattern-filter simulation until CP6 |

The existing public dispatcher still owns twelve canonical actions:
`CREATE_MANUAL_BS`, `CLASSIFY_BS`, `SAVE_REWORK`, `COMPLETE_REWORK`,
`DISPOSE_BS`, `HOLD_BS`, `RELEASE_HOLD`, `REVERSE_DISPOSITION`,
`REVERSE_REWORK_COMPLETION`, `SAVE_CLAIM`, `RESOLVE_CLAIM`, and
`REVERSE_CLAIM_RESOLUTION`.

## Recorded ERP Enteng UAT state

| Application | Source ledger | Platform ledger | Source SHA-256 |
| --- | --- | --- | --- |
| `v2.6.18` | `20260903022604` | `20260903060213` | `6a568a78ad0b9baa2ef5ee958ee967d7c997cc1f4dfb7f0e4ef5e6ff69e5038f` |
| `v2.6.18a` | `20260903070931` | `20260903105741` | `d024a9ef2c8b1d5d9c529669b0b46a7588575f3bdc6788252c1b90d0ab2aae6a` |
| `v2.6.19` | `20260903070932` | `20260903105814` | `79e7b51b82759f1f4579fc373d11e41a668f312a569425aad2fdc2c4d6d68aa6` |
| `v2.6.19a` | `20260903151034` | `20260903151034` | `204b9246f3c8c6464476da1a7f1574f5e0ae4c46f024c082704795b3eef5210f` |
| `v2.6.19b` | `20260904012525` | `20260904032110` | `b1bde1a6ccd1f60dd001d99b72d479ffa0a18a6ea46bf93cd80e406e2ef0ce1d` |

The official connector stored the v2.6.19b source without its final newline:
42,020 bytes and SHA-256
`89ed4535720e12722bc1cbedd1bbcb5b7920f9ee4b6b19754214d05ac82b0e8d`.
That is the only source/ledger byte difference and is bound by the rollback.

Post-install verification found the five application rows and five platform
rows exactly once, capsule counts `17 / 8 / 30 / 6 / 7`, zero source or
installed-function mismatch, the expected partial actor and unique GOOD-lot
indexes, owner `postgres`, empty function `search_path`, no anonymous facade
execution, and no browser access to private tables.

Both exact repository SQL acceptance suites passed against hosted UAT inside
rollback-only transactions. The reviewed v2.6.19b rollback restored the sealed
seven-function predecessor set inside an outer transaction that was itself
rolled back, leaving v2.6.19b installed. All Auth/app-user/BS/rework/selection/
claim/FG/entitlement/idempotency/execution-context/cutting residue remained
zero; locks, long transactions, active non-self sessions, and idle transactions
were zero. The 36 pre-existing audit rows remained exactly 36.

The seven installed MD5 values and complete residue record are in
`docs/evidence/cp5_v2619b_uat_acceptance.json`.

## Exact v2.6.19b code-head CI

Runtime code head `abd2e9e0dad09a2fe33d330ddc83872da3c54b53` passed
all five checks:

- Build push run/job `33831666623` / `100895779188`; dist artifact
  `9921939239`, digest
  `b7e62b080025f81d8685d3167f887b910c7005d2e9623b60f8b19b1ac03277a3`;
  browser artifact `9921938084`, digest
  `d0768112da1e0e097bcf0f4ec3b2080aee3c925bef6dea7bb98c81c795add7b0`.
- Build PR run/job `33831670004` / `100895789611`; dist artifact
  `9921972533`, digest
  `df8709c73cbab3d05ca6f49098766ae91e0843166595e552bb013acfdc4bfdc2`;
  browser artifact `9921971246`, digest
  `ff18ed90a58964e2e8d9279c9d54055fbae5d8319bd3ae0cbe2491554223c606`.
- CP5 full-schema run/job `33831666549` / `100895779110`; artifact
  `9922045831`, digest
  `8d82b8ee0c0d5c2d9a2ab420c20f8597fcc1a40d231d7affab6a36565349cbd3`.
- Pre-CP5 full-schema run/job `33831669979` / `100895789590`; artifact
  `9921962427`, digest
  `3bd228d7be7a6dd90a3c8586f34d6851c82049ee675364b703ab2c413a2b67be`.
- Workers build check `100897068917`, build
  `49fdf3a4-9a87-47b2-a65e-293c26f312f2`.

The two Build runs each passed 25 files / 172 tests and ten Chromium cases:
two CP4.5, two pre-CP5, and six CP5 desktop/mobile cases. Full-schema CI passed
v2.6.19b forward/replay/rollback checks, five serialized races, 30 disposable
Auth/JWT assertions, finance/HPP/stock/reversal cases, the full rollback ladder,
and zero final residue. The evidence/checker successor must independently rerun
these five checks; its run IDs must be resolved from that exact final head.

## Advisor and legacy observations

The post-DDL advisor scan had zero scoped security errors, zero unexpected
scoped security warnings, and zero performance warnings/errors. The only
security warning was the intentional authenticated `SECURITY DEFINER` public
workspace facade; ACL, empty `search_path`, internal permission check, and
anonymous denial were independently verified. RLS-without-policy INFO is the
intentional deny-by-default design. Foreign-key and unused-index INFO is
non-blocking on empty UAT; the audit-required actor index exists with its exact
partial predicate.

Legacy project `vlxdhpkjeevubjxexnfo` was checked read-only after UAT proof:
272 platform migrations, latest `20260829204756`; 38 application migrations,
latest `v2.6.9a`; zero CP5 ledger/capsule/relation/facade residue; zero users,
locks, and long transactions. Historical function MD5 values were unchanged.

## Required independent re-audit

1. Resolve PR #23 head, parent, tree, base, draft/open state, and
   `production_go:false`; reject drift before using any evidence.
2. Verify the successor is a direct child of the runtime code head and that its
   diff is evidence/checker-only. Recompute every Git blob and ownership hash.
3. Run `npm ci`, `npm test`, `npm run build`, `npm run test:security`,
   `npm run check:cp5`, and `npm run check:backend`. Require zero orphan,
   direct-table, secret, stale-manifest, and source-ownership failures.
4. Inspect exact-head Build, Chromium, pre-CP5 full-schema, CP5 full-schema,
   and Workers logs/artifacts. Verify artifact digests rather than trusting this
   handoff.
5. Reproduce accessory defaults: unpaid baseline on, prior entitlement off,
   unprovable data fail-closed, explicit replacement recorded separately, and
   explicit empty never falling back to the BOM.
6. Reproduce laundry negative cases: DRAFT/REVERSED source, wrong vendor,
   non-POSTED damage receipt, duplicate/concurrent MISSING+STUCK over-capacity,
   damage over-capacity, source reversal after lineage, and absence of `OTHER`.
7. Reproduce mutation-commit/refetch-failure behavior and prove all writers
   remain frozen until one authoritative read succeeds.
8. Recheck ERP Enteng and legacy read-only. Stop on any ledger/function hash
   mismatch, business residue, audit-row drift, waiting lock, long transaction,
   or unexplained active session.

## Authorization boundary

- ERP Enteng v2.6.18 through v2.6.19b: recorded
- Exact v2.6.19b runtime code-head CI: 5/5 PASS
- Hosted v2.6.19b transactional SQL and rollback dry-run: PASS
- Legacy mutated: no
- Canonical Worker promoted: no
- PR merged: no
- Production deploy or production GO: no
- Independent re-audit verdict: pending exact final evidence-head CI
- Merge authorization: pending independent PASS
