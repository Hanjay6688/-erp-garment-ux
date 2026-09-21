# CP6 AL — opening values and typed import diagnostics

Checkpoint: 2026-09-21. **INCOMPLETE — native AL not yet executed.**
CP6 remains HOLD, `production_go:false`; CP7 has not started.

## Authority and recovered source

- Competition branch: `competition/cp6-j-closure-20260911`, one writer,
  fast-forward only. Incoming HEAD `8c1a22b8fba26c1ee820645cf5793f19353522b8`,
  tree `b2b0ffc8f848f550ce1a8f9e70796d4c9d38f1fe`.
- The owner explicitly resumed AL after the demo appearance release.
- All 13 files in the archived draft were recovered to a separate directory
  and verified individually before integration: ZIP 83,648 bytes,
  322,713 uncompressed bytes, SHA-256
  `00b73dc7c4662c1cbba5ee05268fe9304922eb54c68150559385ccf25b27835a`.
  Integrity verification alone is not product acceptance.
- Current owner handoff `ERP_V3_2.md` was read, including its CP6/AL boundaries.
  Its additional report, accessory, reminder, and CP7 requirements are preserved
  as separate work; AL does not claim to implement them.
- Main changed only for the separately authorized demo appearance release:
  PR #26, merge `bf17dd84c85d7b0ace7987de55cb3b27c4a5a0af`.
  Cloudflare version `8e06a853-c9e7-4b37-bafc-c1b95bd0e3a0` deployed successfully;
  the public demo's role/user foreground and role-editor readability were
  checked. Build UX, its three browser suites, and CodeQL passed. The unrelated
  Pre-CP5 PR native workflow failed before startup on its historical no-merge
  ancestry rule; it was not relabelled PASS or modified for this release.
  The owner then clarified that the card and editor backgrounds must also be
  dark blue. PR #27 corrects that omission: candidate
  `d9244b6fe2bf01f299d2580f848fb944d613b3d1`, tree
  `5416de35c09de7acf1b0c47a8caa81b43f52318d`, main merge
  `557005e6674058f1e5e966b350cba05501e06182`, Cloudflare version
  `5892967f-78ea-46ff-8428-255e1c0c7eb6`. Canonical live demo panels,
  fields, and role editor were checked after deployment. Build UX run
  `35635332384` attempt 2 passed, including 173 unit tests and 16 browser
  cases; attempt 1 failed only at proof-upload finalization. CodeQL passed.
  The inherited no-merge Pre-CP5 gate still fails and is not weakened.
  These demo changes are separate from the competition branch; preserve their
  final dark palette in any future integration. No CP6 backend changes went
  to main or hosted databases.

## Affected family and intended behavior

| Audit ID | Existing evidence | AL change |
| --- | --- | --- |
| AUD-B01 | AK admits BS qty 1.5, -2, zero, or missing without BS cases | Preview and locked posting require positive whole PCS within integer capacity |
| AUD-B02 | AK admits negative WIP amount or qty/cost without WIP journal | Require explicit amount or qty+cost; reject non-finite/negative values before any posting effects |
| AUD-B03 | Four invalid master types preview VALID then apply refuses | Validate consumed fields against actual column types/widths and supplier enum; retain per-row diagnostics and valid defaults |
| AUD-T01 | Historical ten-case reuse runner refuses dependency drift | AL changes product source, so that runner remains strict and is not used; execute all 230 cases fresh with exact AL qualification |
| AUD-T02 | AL was an unintegrated archive | Add source routing/pins, maintenance binding, workflow install/gates/artifacts, direct-item schedules, and exact restore chain |

Only two existing business functions change:
`erp._validate_migration_batch_base(uuid)` and `erp.post_opening_balance(uuid)`.
The migration adds a private rollback capsule. Existing admitted SQL remains
byte-identical. No new browser facade or alternative stock ledger is added.
Prepare stays DRAFT and editable. Posting locks and checks current rows;
invalid documents refuse atomically. Posted facts remain immutable.

The maintenance controller's AL target bindings must strip back to the exact
reviewed AK controller, then to AJ. Its drain/admission/refusal body is intact.
The original independent AK case source remains byte-identical to `8435f15c`.
Its unchanged case declarations run before and after AL; rerunning them as
the AL writer does not constitute independent acceptance.

## Required evidence before writer acceptance

- Original AK 27-case reproduction: 11 PASS, 12 BUG_PROVEN, 4 GAP_PROVEN,
  zero INCOMPLETE. These are two defect families and four diagnostic gaps.
- Fresh AL 65-case value family, including those original 27 declarations;
  31 import cases; four staging edit/post schedules; twelve direct-item
  schedules with observed blocking and exact stock/journal/BS outcomes.
- Fresh 230-case business ledger; sixteen original and twelve work schedules;
  twenty current AL maintenance schedules; controlled midnight, inherited
  HTTP and UI regression at the declared AL runtime.
- Read-only advisors before/after; eight rollback refusal controls;
  exact AL→AK→AJ→AI→AH restoration including definitions, owners, ACLs,
  table boundaries, temporary schema usage, and zero disposable residue.
- Native workflow and CodeQL results, downloaded evidence integrity checks,
  exact head/tree and all unfinished groups reported honestly.

The historical 460 maintenance matrix is not a 460-business-flow test. It is
not rerun for unchanged generations. AL's current twenty maintenance cases
exercise the new edge directly.

## Remaining global gate

The twelve date-policy observations remain HOLD. CSV transport and complete
role/domain coverage remain unproven; bounded inherited HTTP/UI cases cannot
close them. All other AUD entries remain open unless separately evidenced.
AL writer acceptance will require a different chat to independently review
the final exact SHA. No global CP6 lock, CP7, UAT mutation, legacy mutation,
hosted database work, or backend deployment is authorized by this checkpoint.

“VENI. VIDI. VICI. ERP. — I CONQUERED ERP.”
“Reliable data adalah dewa.”
“Keuangan—termasuk laporan—stok, dan HPP adalah raja.”
