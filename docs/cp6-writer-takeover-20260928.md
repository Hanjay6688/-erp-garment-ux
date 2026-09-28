# Writer continuation — 28 September 2026

Owner mandate: finish the handover, then continue the laundry/vendor authority,
pending kontra bon, relevant PR30 findings, and same-supplier return credit family.
Stop writing and inform Hansen if another writer pushes. Unpushed work in another
chat cannot be observed. CP6 HOLD; audit_complete=false; production_go=false.

## Latest acceptance — PR32 and R10 scope, 29 September WIB

PR32 independently accepts CP6-FINAL-01 on the current BF package: five native
probes and 30 package installs PASS. The [acceptance and scope record](cp6-pr32-acceptance-and-r10-scope-20260929.md)
preserves those results and the recovered master clauses placing connected
Sales/payment/return/refund at CP7. R10 remains OPEN, and overall CP6 sign-off
is still HOLD. This update changes documentation only.

## Previous continuation — two independent auditor handoffs

The [conversion-history and CP7 handoff](cp6-conversion-history-writer-handoff-20260928.md)
records the subsequent conversion history guard, unchanged independent probes,
nonempty Grade B case, renewed package/rollback evidence, and CP7-DELTA-01 fix.
The CP7 shell is owner-authorized; operational integration remains closed.
The prior results below retain their original scope and source revisions.

## Previous continuation — combined flows and the BF release package

The work after the checkpoint below is recorded in the
[combined-flow and BF package handoff](cp6-combined-release-writer-handoff-20260928.md)
and its [per-case proof](cp6-combined-release-writer-proof-20260928.json).
It adds native running-PO/range/rework/return/import/partial-wash cases and the
30-file AC..BF package, including exact rollback and backup/restore qualification.
Read that handoff for the current run status and remaining acceptance boundary.
Final installed-package run 36452814728 on `add1704a` passed 90 native, 22
contention, 8 real Auth HTTP and 27 BF browser cases, plus 10 AU browser cases.
All three package jobs passed. Packaged rollback run 36450928491 passed 147 checks;
build and CodeQL passed. The follow-on writer scope is qualified; independent
CP6 acceptance and the explicitly documented UI/coverage boundaries remain.
The 133-case checkpoint below is historical, not a claim that all CP6 gates closed.

## Earlier checkpoint — vendor authority and portable credit qualified

Product commit **86f057c0308617fd92564ba586b8940ff0725bee** is qualified within the
scope below. [Run 36415977301](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36415977301)
completed with **76 native + 22 contention + 8 real Auth HTTP + 27 browser PASS**;
zero FAIL or INCOMPLETE. Desktop and mobile supplier split/inverse both PASS.
Both material families also PASS reuse after a fully released former target is
reversed. The original primary is unchanged and no test clone remains.

[Build UX 36415977122](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36415977122)
and [CodeQL 36415977218](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36415977218)
PASS on that same exact product commit. The later documentation commit only
records this proof; it does not introduce another product revision.

- BF SQL SHA-256: `554596386f32122019f145fa0f8aa75998b637afbca19c4152520433416653df`.
- Unchanged BE SQL SHA-256: `695475db3719617bd2c10d82c4dee2eaa567f4c10f322697a1714b17b60d29f6`.
- Per-case results and prior incomplete runs:
  [writer proof](cp6-vendor-credit-writer-proof-20260928.json).
- PR30 conversation update:
  https://github.com/Hanjay6688/-erp-garment-ux/pull/30#issuecomment-5868511894.
- This closes this writer task's tested scope. **CP6 HOLD;
  audit_complete=false; production_go=false** remains unchanged.

## Baseline

- Writer head: df2c09f6a9c5b5e6aaa2e500d46f9cfa8dd45f72.
- Tree: 928e2d74d2d422fad7ba0417c27d0402cc891b25.
- Full context: ERP_Kesiapan_Takeover_Writer_20260928.md, retained handover.
- Product source authority correction was documentation only at that head.
- Earlier BF 125 combined results do not establish vendor tariff authority: some
  laundry fixtures incorrectly configured monetary rates in the SKU master.

## Owner oracle

1. Vendor master owns process/package/component rates. A known combination and
   separately checked components are alternative selections for a delivery.
   SKU history suggests selections and past amounts only.
2. Details may be empty until kontra bon. Price stays unknown, rate NULL, with no
   invented component or FREE/WAIVED price. Physical receipt/QC may continue.
3. Invoice establishes actual cost by its physical source; partial billing leaves
   remaining cost pending. Reversal reopens it. No quote changes after billing.
4. Credit settles other unpaid documents of the same legal counterparty without
   reducing aggregate AP twice. Laundry AP_VENDOR and supplier AP_SUPPLIER remain
   separate. Fabric and accessory supplier cases both need explicit evidence.
5. PR30 D01: withdraw the proposed size-tariff activation as an owner requirement.
   Preserve explicit BD policy handling; a wave binding cannot change authority.
6. PR30 D02: before first work snapshot, revalidate wave membership at the service
   time; refuse stale references and require explicit rebind. Preserve prior pins.
7. PR30 D03: group, membership and product reads all use the requested instant;
   optimistic-write revision remains the latest master revision.

## Source impact and verification

- BF laundry builder / rate helpers / SKU edit UI: remove monetary SKU authority,
  preserve old snapshots, use vendor versions and exact receiver quantities.
- BF work + workspace reader: first-use membership and historical projection.
- BD pricing/receipt/invoice/completeness functions extended by BF: no-charge
  pending delivery, invoice settlement, HPP/accrual/close/reversal consumers.
- Laundry send/unknown/invoice UI: real optional details and selection assistance.
- Supplier return allocation, payments, ledger checks and connected UI: inspect
  separately; current return code reduces source purchase AP and rejects an
  already-paid source. It is not proof of a reusable cross-document credit.
- Disposable native cases, real Auth, contention, browser and build evidence.
  Outcomes and exact pins will be appended as obtained; source inspection is not
  a native PASS. Old failures and invalid oracles remain in their original files.

Supabase changelog fetch timed out twice during preparation; database trigger
documentation was accessible. No platform/dependency upgrade is part of this work.

## Owner clarification, 16:53 WIB

Credit remains applicable to its original purchase as well as other bills of the
same supplier. It may be split over multiple eligible bills within its balance;
reallocation must preserve actual cash history and release the previous use.
Slogan: **Reliable data adalah dewa; Keuangan (termasuk laporan), stok, HPP adalah
raja.** Identity: **VENI. VIDI. VICI. ERP. — I CONQUERED ERP.**

## Native checkpoint 140e569 / run 36409431496

- 68 native transaction cases PASS; 3 INCOMPLETE because new fixture dates exceeded
  the existing five-minute master creation window. No failed numerical oracle.
- 20 contention cases, 7 real Auth HTTP cases and 25 desktop/mobile browser cases PASS.
- Empty-detail delivery -> partial/full kontra bon -> sold-stock HPP -> invoice
  reversal passed. Existing daily/opening laundry claim applications passed.
- PR30 historical workspace passed; stale-binding and legacy-SKU-authority fixture
  dates corrected in the next candidate. Product temporal admission is unchanged.
- Initial run 36406827364 remains INCOMPLETE: duplicate scenario IDs, pending-detail
  parser and SQL record alias defects. All three causes were corrected; evidence
  from the incomplete run is not aggregated into the later passing counts.
- Supplier credit implementation now reallocates original-purchase return relief
  with append-only inverse events and net-zero AP journals. Current cash history,
  return stock movement and economic cent facts are preserved. Native supplier
  qualification is queued; this is not yet a claim of working supplier coverage.
- CP6 HOLD; audit_complete=false; production_go=false.

## Continuation scope now implemented

- Vendor process/package/component versions are the only laundry price authority.
  SKU monetary laundry overrides are refused for new settings; historical settings
  and posted snapshots are retained. Work/sewing settings remain separate.
- Empty delivery details are admitted as PENDING with no synthetic component and
  no zero price. Partial kontra bon leaves cost pending; final kontra bon supplies
  actual source cost, including the correction to sold-stock HPP. Reversal reopens
  the cost gap. Price-detail edits after billing are refused.
- SKU wash history suggests service selections and displays the previous whole
  delivery's ESTIMATE / ACTUAL / UNKNOWN amount. It does not copy that amount as a
  new tariff. A process-only history can seed another pending delivery. Current
  vendor versions still determine newly selected prices and exact receivers.
- PR30 D01 restores the BD vendor resolver and policy checks without activating
  owner-inapplicable size tariffs. D02 revalidates unused bindings and retains valid
  old pins. D03 aligns historical group, member and product reads while retaining
  the latest revision for optimistic writes.
- Posted supplier returns already relieve their original purchase. Portable
  allocation moves that existing relief to one or more purchases from the same
  supplier, with an append-only inverse for each released use. Remaining credit
  stays on the original purchase; an empty allocation restores it there.
- Supplier allocation journals debit and credit AP_SUPPLIER by the same amount.
  They change document allocation, never aggregate AP, cash, physical stock or
  material cost movements. The amount comes from the exact posted cent fact.
- Real supplier payments constrain reallocations. Moving credit away from a paid
  target can reopen its debt; moving credit onto an already fully paid purchase is
  refused atomically. Current permissions are checked before request replay.
- Connected **Utang & kredit retur supplier** provides current purchase balances,
  original/other allocations, a before-save balance preview, reason, confirmation,
  and inverse history. Laundry claim settlement remains in its own workspace.

### Financial example exercised for fabric and accessories

Three purchases are 100.00 / 100.00 / 60.00, and a posted return credit is 20.00.

| Credit allocation | Original purchase AP | Second AP | Third AP | Total AP |
| --- | ---: | ---: | ---: | ---: |
| Original purchase | 80.00 | 100.00 | 60.00 | 240.00 |
| Split 12.00 / 8.00 elsewhere | 100.00 | 88.00 | 52.00 | 240.00 |
| Restore original purchase | 80.00 | 100.00 | 60.00 | 240.00 |

Stock remains 28 units and material cost movement IDs/values are unchanged during
allocation. Native cash checks also reconcile AP ledger/subledger, payment caps
and payment statuses. These supplier cases do not claim a new end-to-end test of
consuming that returned material into finished goods and later selling it.

## Checkpoint 51a3007 / run 36413244138

- Exact commit: 51a300717857bdc88646ce48731c03ca5eecbc7c.
- Native 76 PASS; contention 22 PASS; real Auth HTTP 8 PASS; browser 26 PASS,
  1 INCOMPLETE. Product scenario status remains INCOMPLETE at this checkpoint.
- All PR30, pending kontra bon / sold-stock HPP / invoice inverse, SKU actual-cost
  history, fabric/accessory credit, cash reallocation and exact-cent cases PASS.
- Remaining browser issue: a mobile allocation button was obscured. The next
  candidate constrains tables to horizontal scrolling, wraps long document labels,
  and keeps action controls within the mobile viewport; no force-click is used.
- A source review found that a former target with fully released credit could still
  block reuse after the purchase was reversed. The next candidate locks and admits
  only current targets plus targets with a nonzero active allocation. Both material
  families now exercise release -> former-target reversal -> reuse -> restore.
- Build UX 36413244153 and CodeQL 36413244136 PASS on the same exact commit.

### Follow-up fbc789c / run 36414739377

The released-target change introduced an ambiguous `amount` reference in PL/pgSQL.
This writer regression stopped all four supplier native cases, both contention
cases, the supplier HTTP save and both browser saves. Native 72 PASS / 4 INCOMPLETE;
contention 20 PASS / 2 INCOMPLETE; HTTP 7 PASS / 1 FAIL; browser 25 PASS /
2 INCOMPLETE. The mobile viewport check and ordinary control clicks now reached
the save; its transaction failed on the SQL error. Commit
86f057c0308617fd92564ba586b8940ff0725bee qualifies all movement columns with their
table alias and reruns the complete qualification. The failed run stays retained.

## Boundaries retained

- Supplier allocation currently operates on posted return credits and normal posted
  material purchases. Creation of a new return against an already-paid source and
  supplier opening-payable targets are not newly implemented by this patch.
- Laundry claims remain same-vendor; supplier returns remain same-supplier. No
  cross-counterparty or cross-AP-account offset is inferred from flexibility.
- No production/UAT/legacy mutation, release packaging, main merge or deployment.
  These are writer proofs in disposable databases, not independent acceptance.
- Broader range/rework, connected sales, candidate packaging and final CP6 gates
  retain the separately recorded status in cp6-range-followup-20260928.md.
- **Keuangan (termasuk laporan), stok dan HPP adalah raja. Reliable data adalah
  dewa.** Every financial claim above is bounded by its actual test evidence.
- The writer branch is checked before edits/pushes. An hourly **Pantau writer ERP**
  notification task checks later branch changes; advance its known baseline after
  an acknowledged continuation. It cannot observe unpushed work or stop another
  chat. An unexpected push is a reason to stop this writer and inform Hansen.
