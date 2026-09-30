# CP7 F03 continuation — auditor checkpoint, 30 September 2026

**F03 remains OPEN. CP6 remains CLOSED_CONTRACT_SCOPE. independent_acceptance=false; production_go=false.** This is source-bound writer evidence for Hansen to forward to an independent auditor. No hosted database, merge or deployment is part of this checkpoint.

**Keuangan (termasuk laporan), stok dan HPP adalah raja. Reliable data adalah dewa.**

## Source and outcomes

| Scope | Exact source | Native / race / HTTP / browser | Result and entry |
|---|---|---|---|
| E03 selected customer custody/service after company return | `18c508deffc42415249c9bb2875bcadcbfc71554` | 1 / 0 / 1 / 2 | **4 PASS**, [handoff](F03_E03_HANDOFF.md), [receipt](evidence/f03-e03/QUALIFIED_RECEIPT.json), run36656705461 |
| Complete supplier return from multiple receipts | `e118bebfaff5501ee821c63f4205498f99b908a4` | 6 / 3 / 1 / 2 | **12 PASS**, [handoff](P09_COMBINED_RETURN_HANDOFF.md), [receipt](evidence/p09-return-documents/QUALIFIED_RECEIPT.json), run36658193540 |
| E24 receipt/transfer→accessory note/inverse and service-return→late invoice | `06ba28b0c2dbed426e676d37989296a5f6b6af79` | 2 / 0 / 0 / 2 | **4 PASS**, [handoff](F03_E24_ISSUE_HANDOFF.md), [receipt](evidence/f03-e24-issue/QUALIFIED_RECEIPT.json), run36658126203 |
| E01 READY source plus E12 same-context second-tab recovery | `9ac03af38a59e97f3ca70f5b1fa3de0631f89083` | 1 / 0 / 1 / 2 | **4 PASS**, [handoff](F03_E01_HANDOFF.md), [receipt](evidence/f03-e01/E12_QUALIFIED_RECEIPT.json), run36660530418 |
| E06 selected year-end invoice and close contention | `ca38bfbd1e8cc630e7d93ed2b7d70f64715143c2` | 4 / 1 / 0 / 0 | **5 PASS**, [handoff](F03_E06_HANDOFF.md), [receipt](evidence/f03-e06/QUALIFIED_RECEIPT.json), run36660802859 |
| X04 selected vendor FREE/WAIVED, PO/rework/group-version and late-invoice return | `8f2d81c0198a1c451314811d074f7c88a9cf793a` | 6 / 0 / 1 / 0 | **7 PASS**, [handoff](F03_X04_HANDOFF.md), [receipt](evidence/f03-x04/QUALIFIED_RECEIPT.json), run36662520866 |
| Existing P09 regression | `a28ad225eff755cd63a2eb1e1f06de6ae0c14150` | Breakdown retained in receipt | **132 PASS plus3 separate smokes**, [receipt](evidence/p09-return-documents/P09_REGRESSION_RECEIPT.json), run36657403318 |
| Selected combined F03 regression | Same `a28ad225...` | 10 / 2 / 4 / 6 | **22 PASS**, [receipt](evidence/f03-combined/RETURN_UI_QUALIFIED_RECEIPT.json), run36657403229 |
| P13 report/period regression | Same `a28ad225...` | 16 / 3 / 2 / 4 | **25 PASS**, [receipt](evidence/p09-return-documents/PERIOD_REGRESSION_RECEIPT.json), run36657403499 |

Do not sum these overlapping suites into a single family count. All qualified rows retain0 FAIL/INCOMPLETE/NOT_RUN in their own scope. Each receipt binds source tree, SQL bundle, complete original artifact hash, original report hash, compressed JSON reports and restoration/cleanup gates. All rows pass CP6 restoration, advisor, installation/backup restoration, unchanged primary and Auth/database cleanup. Browser uses real Auth/public RPCs on disposable PostgreSQL17; these are not mocked API outcomes.

Product implementation is `a28ad225...`. A direct git comparison from that source through `8f2d81c0...` shows no changes in `src`, `scripts/cp7-src`, CP7 bundle builders or Supabase product paths; intervening commits add qualification, test-fixture corrections and evidence. The combined SQL bundle for new returns/E24 is `fbc874b151086dd38d5149062cb5b9a2d11d63714d1f199b43d67f989884dc61`. The earlier E03 qualification used its separately recorded predecessor bundle, so it is not relabeled a new source run.

## What changed and what to examine

The new P09 picker loads POSTED receipts from the same supplier with complete server pagination and no money in its source headers. The editor preserves every selected receipt/item/roll, exact quantity/version transport and source warehouse. SAVE_DOCUMENT/POST_DOCUMENT/REVERSE_DOCUMENT require full native source membership; original single-source actions retain their bounded contract. Native writers still own stock, AP/GRNI, valuation, cent allocation and inverse. Current permission checks precede cached outcomes and follow real waits. No new ERP DML permission or replacement credit/stock ledger is introduced.

The supplier fixture returns2 from10×10 and3 from10×20: stock8/7, AP80/140. Credit20 can move to the second receipt (AP100/120) and return to its original allocation without another journal/stock effect. Reversal is refused while that credit is used away; once restored, inverse recovers both sources. Mixed fabric/accessory with estimated/final valuation also passes. Same-request, competing-capacity and actual lock-wait revocation tests pass. Desktop/mobile create/edit/review/post/inverse the full document; mobile loses a committed reply and reconciles the identical envelope.

E03 keeps one customer-owned garment separate from five company returns. Company FG45/value675, AR175, cash200 and HPP remain unchanged by service. Two company accessories cost4 as service expense; custody-out creates no company FG or customer cash right. Native inverse restores stock/accounts and report readiness is READY. No customer cash refund or full E03 acceptance is claimed.

E24 proves a CP7 receipt and transfer can feed the inherited accessory-note UI: issue7 at retail3.25 produces receivable22.75 with company cost kept separate, then inverse restores every account and source stock. Its separate native service/return/invoice chain leaves949 pieces and mandor collectible18; late price2.10 gives material value1992.90 and supplierAP2100/GRNI0 without another physical movement. Invoice inverse restores prior valuation while physical quantity and mandor collectible remain.

Local42 DOM/recovery tests, TypeScript and source/access ownership gates passed for the new UI. New-return and E24 desktop/mobile screenshots were inspected and retained as lossless pixel-identical WebP with both hashes. Fixed headers remain at the capture scroll offset in the full-page images; mobile note tables scroll inside their panels. This is not a claim to have reviewed every intermediate form/viewport. Existing regression screenshots are in their downloaded full artifacts; no new visual-review claim is made for those regressions.

## History retained, not hidden or reopened as new defects

- E03 FIRST:4 INCOMPLETE due to missing `rolls=[]` in fixture; SOURCE_CORRECTED:2 browser PASS/2 INCOMPLETE due to fixture timestamp format. Qualified source uses the native WIB contract without weakening it.
- New returns FIRST:9 PASS/1 INCOMPLETE; native correctly refused quantity11 against purchased10 during SAVE, earlier than the fixture expected. Follow-up also proves actual POST rollback after warehouse stock changes through a lawful transfer.
- BROWSER_TIME_FIXTURE and BROWSER_SOURCE_ORDER each preserve10 PASS/2 browser INCOMPLETE. The test corrections use the HTML control's declared time precision and compare quantity by native purchase-item identity, not row ordinal. The final12-case source passes unchanged stock/AP expectations.
- Combined source05c1e25:16 PASS/6 browser NOT_RUN because loopback54328 was occupied at host START. No browser case/user started. Original failure is retained; a28ad22 subsequently passes22/22. It is not reported as a product regression or rewritten green.

## Remaining handoff boundary

[The current F03 contract ledger](F03_REMAINING_CONTRACT.md) remains authoritative. These results close the scoped increments above, not whole P09–P13/family acceptance. Paid-source supplier-return carry, eligible customer refund/returned-BS continuation, the precise E05 partial-settlement business contract, remaining cross-flow coverage and independent family review remain open. Original full-net payroll proof is not installment proof. Source/FG evidence is not a claim that a future planner gap calculation has run.

Earlier [E01 READY source journey](F03_E01_HANDOFF.md), [selected O18/E04/E07 cost continuations](F03_COST_CONTINUATION_HANDOFF.md) and [P13 checkpoint](F03_P13_AUDITOR_CHECKPOINT.md) remain valid in their declared scopes. F02's independent HOLD is separate. F04 takeover remains after the agreed F03 completion boundary, not after merely green workflows.

E06 retains both initial fixture-oracle errors before the five-case qualification. E12 retains its too-early peer-read assertion before the four-case qualification; the corrected observer waits for actual committed HTTP200 before abort/read. Product source and monetary expectations did not change. [X04 selected native/HTTP source-version continuation](F03_X04_HANDOFF.md) now passes7 on `8f2d81c0`. Both prior5-PASS/2-INCOMPLETE results remain retained: diagnostics identify equivalent WIB/UTC timestamp spellings, and the qualified comparator preserves microseconds and all non-time fields. No new X04 redye/browser or visual review is claimed; those seams and independent review remain open.
