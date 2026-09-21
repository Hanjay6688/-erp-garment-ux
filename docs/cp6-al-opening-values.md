# CP6 AL — opening values and typed import diagnostics

Checkpoint: 2026-09-21 UTC. **WRITER PASS — AL affected family, not independent acceptance.**
CP6 remains HOLD, `production_go:false`; CP7 has not started.

## Final tested candidate

- Product/code SHA: `3f5b782a45d3fdfd7cf0a838cb4bc3e918821a00`.
- Product tree: `ba48de054db630e0d7330354da54d331cd6dfd47`.
- [Native run 35638511554](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35638511554): SUCCESS,
  job `106461810392`, exact candidate above.
- [CodeQL run 35638511385](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35638511385): SUCCESS
  for JS/TS, Python, C/C++, and Actions.
- Final artifact `10657843119`, `cp6-al-r2-native.zip`: 60,747,995 bytes,
  327 entries, 494,087,448 uncompressed bytes, ZIP CRC verified;
  SHA-256 `1c1b323fb6ccef39f4f53632d4fc265c9bba1386b808209e036178f9e2d264d2`.
  JWT/private-key/GitHub-token/Supabase-secret/AWS-key-ID pattern scan: zero hits.
- The following documentation-only checkpoint adds this account of the results.
  It is not a different native-tested product SHA. Check branch HEAD separately;
  use the exact product SHA above for independent review.

| Fresh evidence on the final candidate | Result |
| --- | --- |
| Unchanged original AK 27-case probes before AL | 11 PASS, 12 BUG_PROVEN, 4 GAP_PROVEN, 0 INCOMPLETE |
| Opening value / typed-field family, including those 27 declarations | 65 PASS, 0 INCOMPLETE |
| Import references, staged dependencies, draft edits, recovered sales | 31 PASS, 0 INCOMPLETE |
| Full business ledger | 230 executed: 179 PASS, 39 CONTROL_PASS, 12 DATE_POLICY_REVIEW_REQUIRED, 0 INCOMPLETE |
| Staged draft edit/post schedules | 4 PASS, actual blocking observed |
| Direct MATERIAL/BS/WIP item edit/post schedules | 12 PASS, actual blocking and ledger/stock/BS outcomes checked |
| Original header/child/allocation/return schedules | 16 PASS |
| Work-source schedules | 12 CONTROL_PASS |
| Current AL maintenance edge | 20 PASS, zero remaining clone databases |
| Controlled midnight | 4 bounded native cases PASS; not an overnight soak |
| HTTP | Bounded PASS: 95 cases and 62 facade-role rows |
| UI | 43/43 WRITER_PASS; 58 additional gap cases, 96 permission rows, 32 positive money-permission rows |
| Pure money/parser checks | 34 cases PASS_REVIEWED_SCOPE |
| AL rollback refusals | 8 PASS with boundary restored |

The expected lost-reply UI test records one intentional `ERR_CONNECTION_RESET`
in `FAILED_WASH_LOST_REPLY`; it is not an unexplained browser failure. There
were no CORS errors or unfinished UI case IDs. This bounded coverage does not
claim every role/module combination or CSV transport.

Read-only advisors compared 83 predecessor findings with 84 successor findings.
The single addition is the reviewed private rollback capsule's no-policy
information; zero new unreviewed findings. Existing findings are retained,
not represented as an entirely clean baseline.

Exact restoration: AL→AK restored 533 functions/226 tables; AK→AJ 533/225;
AJ→AI 533/224; AI→AH 533/223. Each comparison includes definitions,
owners/ACLs and the recorded data boundary. Fixture schema grants were
restored, auth/app user counts were zero, and the disposable database,
auth clone, and temporary PostgREST container had zero residue.

The final gate explicitly records `global_status:CP6_HOLD`,
`global_cp6_acceptance:false`, `independent_acceptance:false`,
`production_go:false`. The historical 460 maintenance cases remain historical
evidence; they were not rerun or counted as fresh business cases.

## Context for a new chat

This is the owner's ERP Garment project, repository
`Hanjay6688/-erp-garment-ux`. Production flows through cutting, contractor
work, laundry, QC, finished goods, and sales. Stock quantities, valuation/HPP,
subledgers, journals, and dated reports must reconcile across those flows.
The owner wants related findings handled together, with fixes and evidence,
without repeatedly treating the historical 460-case maintenance matrix as a
universal business test.

AL is the current CP6 correction to opening-balance and import validation.
It follows AK's repair of stale prepared imports: changing draft qty 10→20
must ultimately post the current 20 after the required validation/preparation.
Prepare is still DRAFT and editable. A posted document is immutable; later
corrections need their proper linked business transaction.

The public Cloudflare site is a separate simulation demo, released from main.
The owner authorized its dark-blue Pengguna & Hak Akses appearance update.
That permission does not authorize deploying the CP6 backend. AL work belongs
only on the competition branch and in synthetic disposable databases.
There is one active writer; another chat must independently judge the repaired
candidate. A successful writer run is not independent acceptance or CP6 lock.

The full owner specification remains `ERP_V3_2.md`. Its other AUD entries and
CP7 designs are not closed by AL. A chat without repository access and a way to
execute the required checks can review supplied evidence and propose work;
it must mark unexecuted checks BELUM TERUJI/INCOMPLETE and must not invent
commits, pushes, tests, or independent PASS.

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

The first complete AL run tested `99d38d8f68b7fccb7cf417ab197319c61d474317`,
tree `a48d4d927fc81049bc9c19e403cf6d348c77e36b`: native run `35636515022`
finished FAILURE because import had 30 PASS and one INCOMPLETE. The unchanged
`MASTER_REF:MATERIAL:unit_code` oracle found that an overlong unit code was
rejected with a generic width message that omitted the field name. No invalid
opening was accepted by that case. This is a diagnostic regression to repair,
not evidence of a new stock/journal discrepancy.

That first run completed all 230 business cases fresh: 179 PASS, 39 CONTROL_PASS,
12 DATE_POLICY_REVIEW_REQUIRED, zero INCOMPLETE. It also passed 65 value cases,
4 staged and 12 direct edit/post schedules, 16 original plus 12 work schedules,
20 AL maintenance schedules, bounded midnight/HTTP/UI checks (43 UI cases),
eight rollback refusal controls, exact AL→AK restore (533 functions/226 tables),
the subsequent predecessor restore chain, and cleanup. These results remain
scoped to the first candidate; the final candidate's fresh results are above.

Artifact `10657190936`: 60,751,509 bytes, 327 ZIP entries, CRC valid,
SHA-256 `639bc63bd04257e9094bf61e49201b0fbcefd8a34d87965c254d4196c933b54a`.
CodeQL run `35636514910` passed JS/TS, Python, C/C++, and Actions.

The correction keeps the successful whole-row cast and, only on a type/width
error, identifies the offending field while retaining the original SQLSTATE.
The posting definition is byte-identical to the first AL candidate. The
independent 27-case source and the 31 import-case assertions are unchanged;
extra typed-field cases now also require actionable field names. The unaccepted
AL candidate migration/rollback/pins are regenerated together; all admitted
pre-AL SQL remains unchanged. The full combined gate stays in force.
The final native run above completed that gate. The repaired case now reports
`Invalid row value: unit_code: value too long for type character varying(20)`.

The twelve date-policy observations remain HOLD. CSV transport and complete
role/domain coverage remain unproven; bounded inherited HTTP/UI cases cannot
close them. All other AUD entries remain open unless separately evidenced.
AL writer acceptance will require a different chat to independently review
the final exact SHA. No global CP6 lock, CP7, UAT mutation, legacy mutation,
hosted database work, or backend deployment is authorized by this checkpoint.

## Independent handoff

Attach this checkpoint, `ERP_V3_2.md`, and `cp6-al-r2-native.zip` for a new
chat. This checkpoint does not replace the full owner specification.

Review the exact product SHA/tree listed above, inspect the two changed
business functions and their consumers, and design independent checks for
valid/invalid openings, latest DRAFT edits, dependent import rows, roles,
stock/journal/HPP, date boundaries, and restoration. Treat writer evidence as
claims to verify. A rerun of the writer's tests alone is not independent proof.
If a material issue is found, preserve its original counterexample and agree
one active writer before editing. Keep other AUD items visible and report
CP6_LOCK_READY, CP6_HOLD, or INCOMPLETE according to the actual global gaps;
AL's Writer PASS alone cannot authorize CP6_LOCK_READY or CP7.

Before continuing, a new chat should be able to answer:

1. Which exact product SHA/tree was tested, and which later SHA is documentation only?
2. What differs between the live demo on main and the CP6 competition candidate?
3. Why does prepare remain editable, and what must happen after qty changes 10→20?
4. What did AK originally do wrong for BS/WIP and typed import values?
5. Which evidence is fresh, which is historical, and why are the 12 date cases still HOLD?
6. What do the 460 maintenance schedules actually cover?
7. Which HTTP/UI roles and CSV paths remain unproven?
8. How are exact restoration and zero residue demonstrated?
9. Which tools can this chat actually execute, and what must remain BELUM TERUJI if it cannot?
10. Why are independent acceptance and an owner instruction still required before CP7?

“VENI. VIDI. VICI. ERP. — I CONQUERED ERP.”
“Reliable data adalah dewa.”
“Keuangan—termasuk laporan—stok, dan HPP adalah raja.”
