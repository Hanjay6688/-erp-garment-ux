# CP7 — six delivery and audit families

Owner direction, 29 September 2026: finish the first family and group the remaining work. There are **22 packets, P00–P21**. The numbering and dependencies in the original framework remain unchanged; this document groups them for delivery and review.

**Keuangan (termasuk laporan), stok dan HPP adalah raja. Reliable data adalah dewa.**

| Execution order | Family | Packets | Reviewable outcome |
|---|---|---|---|
| 1 | Data foundation | P00–P02 | Accepted CP6 receipt, contracts/oracles, authorized coherent immutable source capture |
| 2 | Identity and WIP | P03–P04 | Physical/commercial identity, lineage, remaining WIP, ETA and shared capacity |
| 3 | Connected operations | P09–P13 | Procurement/materials, FG, sale/return/payment, attendance/payroll/Nota, finance/HPP/close |
| 4 | Planning | P05–P08 | Demand/availability, targets, adaptive evaluation, scenario/draft/apply |
| 5 | Consumers and reporting | P14–P17 | Planner/panels, Business Report, manual reminder, Tanya AI |
| 6 | Final qualification | P18–P21 | Full lifecycle, scale/resilience, independent candidate audit, installed release/restore |

Operations precede planning delivery because P08 requires P10. P05–P07 may be prepared after P04, but no apply is accepted before its operational dependency is verified. This grouping does not authorize concurrent canonical writers.

## Test and audit cadence

1. Every packet has risk-relevant writer tests and a source-bound receipt. A label/CSS edit does not trigger an unrelated full database/package matrix; money, stock, HPP, temporal, permissions and races require the affected native family and negative controls.
2. At a family handoff, freeze a concrete source SHA, contract/oracle, fixtures, expected/actual results, failures, cleanup and remaining scope. Submit it for independent review. The reviewer uses their own oracle and execution; reading the writer report is not independent acceptance.
3. Confirmed material findings block work that depends on the defective contract. Independent unaffected preparation may continue. Writer fixes remain writer work and need the appropriate retest.
4. P18 proves the whole lifecycle; P19 proves scale and recovery; P20 audits the integrated candidate independently; P21 qualifies the installed package and restoration. Family review does not replace these gates.
5. Track IMPLEMENTED, WRITER_VERIFIED, INDEPENDENT_ACCEPTED, RELEASE_QUALIFIED and PRODUCTION_AUTHORIZED separately. No green T1 family authorizes hosted installation or production use.

## Family 1 delivery boundary

Entry: [P00](P00_HANDOFF.md), [P01](P01_CONTRACT_HANDOFF.md), [P02 actor facade](P02_FACADE_HANDOFF.md). Original framework files and their 48 hashes remain immutable.

The initial capture boundary is one physical root/exact size, five operational source domains plus separately authorized lot cost, current knowledge, and at most 500 facts per domain. It persists a complete immutable run or refuses. The six-domain boundary is explicit in the response; it is not a planner result or complete ERP source coverage.

Family 1 handoff must distinguish the implemented boundary from the full case charters. E09/E14/E15/E20/E22/X09 contain downstream report/apply/shared-capacity/browser requirements that this source family cannot close. Those obligations stay in the active coverage ledger and their owning packets. Arbitrary historical AS_KNOWN reconstruction is unavailable until source history proves it; no current facts may be relabeled historical. No family-wide independent acceptance is claimed from writer native results.

R10 remains P11's connected sale/return browser obligation. Mandor payroll and its Nota interaction remain P12's obligation, reviewed against the owner frontend rules. Existing business decisions about vendor tariffs, UNKNOWN costs and reusable same-counterparty credits remain binding.

Current exact status and next action: [CURRENT_STATE.json](CURRENT_STATE.json).

## Family 2 writer checkpoint

[F02 handoff](F02_AUDITOR_HANDOFF.md): bounded P03 policy/identity proof (15 cases) and P04 atomic-origin WIP proof (39 cases plus repeated smoke) are source-bound and ready for independent review. This is WRITER_VERIFIED within the stated boundary, not INDEPENDENT_ACCEPTED. Dated demand, planner integration, connected browser and scale obligations remain assigned to their owning packets.

Current writing proceeds to family 3, beginning with P09 procurement/materials. F01/F02 independent review may follow the frozen checkpoints without two writers sharing the canonical branch.
