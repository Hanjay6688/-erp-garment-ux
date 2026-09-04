# CP5 v2.6.19c independent re-audit handoff

This handoff freezes the latest forward-only CP5 reliability closure after an
independent review found two new P1 issues and one P2 issue: claim reversal
could diverge from an active BS cash disposition, an ambiguous browser response
could be followed by a different mutation identity, and rollback trusted a
migration name/version without binding exact statement bytes. Those findings
are implemented in v2.6.19c and proved on the exact code head below.

This handoff is evidence, not authority. A reviewer must independently derive
the verdict from exact source, database behavior, and business conservation.
It does not authorize merge, production deployment, a real-user invitation, or
any mutation of the legacy ERP Garment project. `production_go` is `false`.

## Exact identity and commit shape

- Repository: `Hanjay6688/-erp-garment-ux`
- Pull request: `#23`, open, draft, unmerged
- Branch: `pre-cp5/cutting-persistence-pickup-wip-r1-20260903`
- Live `main`: `d5c48ce5c8daa7e6da92dc9d690d9b36879e74c1`
- Live-main tree: `70f7bf3c0265520eac5aafff747f448ed8be3e6b`
- CP5 source base: `8bfac13b91ea1be92111139e2fddcabccf9ae19a`
- CP5 source-base tree: `a9b193010266bb686c57709865a992769a835855`
- v2.6.19c runtime code head: `49647ded395d516983417e5f6315f6f0dc707f3d`
- v2.6.19c runtime code tree: `9c1b5ee3d6c225d0b7ef5b3d193e0e90ef30a2c5`
- Evidence/checker successor: resolve from PR immediately before review; its
  first parent must be the runtime code head above.

Reject branch drift, a concurrent writer, a non-direct evidence parent, or any
runtime/migration change after `49647ded395d516983417e5f6315f6f0dc707f3d`. The successor may change only
this handoff, v2.6.19c UAT evidence, access evidence/checker, and generated
ownership manifests. Recorded v2.6.18 through v2.6.19b bytes remain immutable;
v2.6.19c is the official forward migration.

## Owner business truth

The controlling rule is: **Reliability Data adalah Dewa. Keuangan, stok, dan
HPP adalah Raja.** Finance, stock/custody, HPP, claim capacity, payable
entitlement, and operational state must stay simultaneously correct. Relevant
mutations must be atomic, conserved, idempotent, concurrency-safe, reversible,
and auditable. A single inconsistent subsystem is a blocking failure.

### Rework defaults and accessory payment

- Default checked means the server-proven unpaid/unentitled baseline, not every
  BOM row. Already entitled, post-FG, ambiguous, or unprovable rows default off.
- A genuine additional replacement may be selected explicitly and is frozen as
  `MANUAL_REPLACEMENT`. Explicit `[]` never falls back to the full BOM.
- Component/labor defaults follow remaining new-work entitlement rather than
  invoice timing. Partial return is cumulative and cannot create premature FG,
  HPP, stock movement, journal, completion, or payable.
- Payment uses broad owner categories even when Mandor pickup is more detailed:

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

The last three categories must not silently produce a payable rate. UAT's
connected accessory master remains empty; no silent seed was inserted.

### Laundry physical and financial conservation

- Supported claims are exactly `MISSING`, `STUCK`, and `DAMAGE`; there is
  no unconserved `OTHER`.
- MISSING/STUCK share authoritative outstanding-delivery capacity. DAMAGE
  requires the matching POSTED receipt and its own receipt capacity.
- DRAFT/REVERSED/wrong-vendor sources and aggregate over-capacity are rejected.
  Delivery, receipt, return, claim, resolution, and reversal paths share a
  consistent receipt-to-delivery lock order.
- Chemical unavailable means a physical return. A later wash is a new
  delivery/service leg; two genuine legs may be paid separately. A full
  unwashed return is not a claim.
- An active `CASH_COMPENSATION` BS disposition must reference one active
  SETTLED claim. Claim reversal and creation of that cash disposition lock the
  same claim row. If cash wins, reversal fails; if reversal wins, cash fails.
  The database cannot end with reversed claim plus active dependent cash.

### Ambiguous browser response

A mutation envelope is persisted before sending: action, canonical payload,
client request UUID, expected row version, and target identity. Timeout,
network loss, reload, or a failed follow-up read leaves the envelope pending and
freezes every writer. Reconciliation resends exactly that envelope; it cannot
invent a new UUID/payload/version. A normal workspace refresh cannot silently
discard it. Only an authoritative exact reconciliation or a proven
non-ambiguous pre-send failure may release the writer.

## Delivered boundary

| Area | Current truth |
| --- | --- |
| Master Pola | Connected, immutable pattern identity |
| Potongan | Connected persistence and posting |
| Pickup / Bagi Potongan | Connected distribution and roll reconciliation |
| WIP | Connected continuity and server Pattern filter |
| Barang BS / Rework | Connected workspace, claims, recovery, reversal |
| Rework/Rewash accessories | Unpaid defaults plus explicit replacement |
| Laundry page | Pattern-filter simulation until CP6; CP5 claim actions live in BS Resolution |
| QC / Final page | Pattern-filter simulation until CP6 |

The public dispatcher still owns twelve canonical actions:
`CREATE_MANUAL_BS`, `CLASSIFY_BS`, `SAVE_REWORK`, `COMPLETE_REWORK`,
`DISPOSE_BS`, `HOLD_BS`, `RELEASE_HOLD`, `REVERSE_DISPOSITION`,
`REVERSE_REWORK_COMPLETION`, `SAVE_CLAIM`, `RESOLVE_CLAIM`, and
`REVERSE_CLAIM_RESOLUTION`.

## Exact code-head proof

Runtime code head `49647ded395d516983417e5f6315f6f0dc707f3d` passed all five required checks:

| Check | Run / job | Artifact ID / SHA-256 |
| --- | --- | --- |
| Build push | `33853233915` / `100960561572` | dist `9929320072` / `81b64664a34deb45f0e292f20c08c59524f5177dfa83c2959ef28bb3b46d8cee`; browser `9929318152` / `b87cabd0db4aefb6f6956c64fb5bd5b7840ff77422163da65868d358c32ee7f2` |
| Build PR | `33853238388` / `100960575862` | dist `9929260245` / `c1e5a812c06519c9ec0ecf27c70ca4a5a0e11d9e59fe49117e4c26b68b269002`; browser `9929258548` / `ec795b5e619b95bf8ee3b3ae9f24bf7d950f1c1f7f774458176f7bbc9586e95a` |
| CP5 full-schema | `33853233792` / `100960561707` | `9929435682` / `b88e9a26491e1b8b95003ec616b854595bb904bda4385b1e497d9b23f12aabc9` |
| Pre-CP5 full-schema | `33853238358` / `100960575646` | `9929253240` / `33a6441aac4e10028dd97662975b12d0e6d73078219c6a2868e4f2ea8738ef02` |
| Workers preview | check `100960709349` | build `41f41e9d-42f6-40c0-980d-2b8fc63bb475` |

Verified there:

- Unit: 25 files / 172 tests.
- Chromium: 2 CP4.5 + 2 pre-CP5 + 8 CP5.
- Ownership: 89 effective unique / 65 CP5 byte-bound / unowned 0.
- Five serialized CP5 race families include claim-reversal versus cash
  disposition in both commit orders; targeted residue is zero.
- Auth/JWT: 30 HTTP assertions, targeted residue zero.
- v19c post-use, wrong-name, and tampered-statement rollback rejection all
  pass; normal rollback restores v19b.
- Every v18-v19c rollback ledger is statement-digest-bound and the complete
  ladder restores CP4.5 with final residue zero.
- The previously leaked two synthetic DELETE audit rows are now identified by
  dynamic resolution ID and removed by the race fixture only. Production
  rollback guards were not weakened. Pre-rollback history is exactly zero.

## Recorded ERP Enteng UAT

| App | Source ledger | Platform ledger | Stored bytes / SHA-256 |
| --- | --- | --- | --- |
| `v2.6.18` | `20260903022604` | `20260903060213` | 80,392 / `6a568a78ad0b9baa2ef5ee958ee967d7c997cc1f4dfb7f0e4ef5e6ff69e5038f` |
| `v2.6.18a` | `20260903070931` | `20260903105741` | 21,350 / `d024a9ef2c8b1d5d9c529669b0b46a7588575f3bdc6788252c1b90d0ab2aae6a` |
| `v2.6.19` | `20260903070932` | `20260903105814` | 67,744 / `79e7b51b82759f1f4579fc373d11e41a668f312a569425aad2fdc2c4d6d68aa6` |
| `v2.6.19a` | `20260903151034` | `20260903151034` | 55,354 / `204b9246f3c8c6464476da1a7f1574f5e0ae4c46f024c082704795b3eef5210f` |
| `v2.6.19b` | `20260904012525` | `20260904032110` | 42,020 / `89ed4535720e12722bc1cbedd1bbcb5b7920f9ee4b6b19754214d05ac82b0e8d` |
| `v2.6.19c` | `20260904061346` | `20260904083552` | 13,808 / `b11014081391f3d72e242813b09bb64c53e2aefe0f4eb42cc20e8089a57ef8ba` |

v19c was applied through the official Supabase migration connector and its
platform ledger contains the exact source bytes, including the final newline.
Six application rows and six platform rows exist exactly once. Capsule counts
are `17 / 8 / 30 / 6 / 7 / 1`.

Read-only verification found the v19c constraint validated, two guards enabled,
capsule checksum/runtime mismatch zero, reverse function MD5
`eb83b83b5c5b1a302f56f433f919e363`, owner `postgres`,
`SECURITY DEFINER`, empty search path, and no anon/authenticated direct execute.
The private capsule has RLS, no policy, and no client table grant.

All Auth/app-user/BS/rework/selection/claim/receipt/delivery/FG/entitlement/
idempotency/execution-context residue is zero. Waiting locks, active non-self
sessions, transactions over five minutes, and idle transactions are zero.
Pre-existing audit rows remain exactly 36.

Advisor scan has no ERROR and no performance WARN/ERROR. The two authenticated
SECURITY DEFINER warnings are the intentional public workspace and mutation
facades; internal permission checks, owner, empty search path, anonymous denial,
and private-table denial were verified. RLS-without-policy INFO for the
rollback capsule is intentional deny-by-default.

## Legacy isolation

Legacy `vlxdhpkjeevubjxexnfo` was checked read-only after UAT:
272 platform migrations, latest `20260829204756`; 38 application migrations,
latest `v2.6.9a`; zero CP5 ledger/relations/capsules/facade; zero users,
waiting locks, active sessions, long transactions, and idle transactions.
It lacks the v19c contract and was not mutated.

## Required independent re-audit

1. Resolve PR #23 identity, exact head/parent/tree/base, draft/open/unmerged
   state, and `production_go:false`. Treat this document as a claim.
2. Verify the final evidence commit is a direct child of `49647ded395d516983417e5f6315f6f0dc707f3d` and is
   evidence/checker-only. Recompute every Git blob and ownership hash.
3. Independently inspect the claim/cash invariant and lock order. Reproduce both
   commit orders and prove there is no reversed claim plus active dependent cash.
4. Reproduce browser timeout after server commit, reload, ordinary refetch,
   exact-envelope replay, conflict, and successful reconciliation. Prove request
   UUID, canonical payload, expected version, and target identity never change.
5. Tamper each rollback ledger name and statement bytes. Require refusal. Then
   prove normal v19c rollback restores exact v19b with zero relevant history.
6. Re-run unit, build, browser, access/security/ownership, CP5 full-schema, and
   pre-CP5 full-schema checks from exact source. Verify artifact digests.
7. Preserve the earlier closures: accessory defaults/replacement, explicit
   empty, partial rework, positive GOOD finance/HPP/stock, laundry source/caps,
   actor index, ownership, Auth/JWT, replay, reversal, and zero residue.
8. Recheck UAT and legacy read-only. Stop on any ledger/function drift, business
   residue, audit-count change, lock, long transaction, or legacy CP5 object.

## Authorization boundary

- ERP Enteng v2.6.18 through v2.6.19c: recorded.
- Exact v2.6.19c runtime code-head CI: 5/5 PASS.
- Legacy mutated: no.
- Canonical Worker promoted: no.
- PR merged: no.
- Production GO: no.
- Independent verdict: pending exact final evidence-head CI and fresh review.
- Merge authorization: pending independent PASS.
