# Date family (ERP-DEC01) — auditor scenarios, results on 9add57e (INDEPENDENT_NATIVE_RERUN)

Oracle: Master 1057-1062 (open period: correction follows the INVOICE date, consistent across inventory, journals, WIP, FG, COGS, dated reports, readiness), Master 1061 (closed period: existing controlled adjustment). Fixture generators are the writer's (estimated receipt 10 units @10 on d=today-3 23:30; ordinary cutting RPC; ordinary invoice RPC); every expected value is the auditor's.

## Runs
| scenario | sha256 | phase | run | job | result |
|---|---|---|---|---|---|
| date_family_1.py | 492908b5… | after | 36041422305 | 107774254372 | INCOMPLETE run: 4 cases INCOMPLETE (auditor fixture cut at d 08:00 before the d 23:30 receipt: the CUT was refused `AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY`), 2 PASS, 2 COUNTEREXAMPLE (ambiguous shapes) |
| date_family_1.py | 492908b5… | before | 36041435083 | 107774296346 | same shape; ambiguous cases show WIP negative on E without AZ |
| date_family_2.py | 44f09ad1… | after | 36042210333 | 107776876564 | RUN_COMPLETE: 6 PASS, 2 COUNTEREXAMPLE (both ambiguous shapes) |
| date_family_2.py | 44f09ad1… | before | 36042223829 | 107776920429 | RUN_COMPLETE: 6 PASS, 2 COUNTEREXAMPLE; ambiguous shapes show WIP before the cut (WIP -14 on E with 3 units cut; WIP +20 on E before any cut) |

## What passed the contract oracle (after phase = final candidate)
- OPEN, invoice on/after every cut (HIGHER 12, LOWER 8, two cuts): supplier-invoice journal on E; every MATERIAL_COST_REVALUATION journal economic=transaction=E; days before E unchanged; MATERIAL_INVENTORY move from E = x × units still in stock; WIP legs = x × units cut; conservation 10x; no GL_INVENTORY_NEGATIVE_ASOF blocker; WIP never negative.
- CLOSED (cut inside closed period, invoice dated inside closed period, HIGHER/LOWER): no journal posted inside the closed period; closed days' ledger unchanged; events keep economic date E; correction posted on the recognition day (today) and fully visible (10x); no negative blocker.
- GOODS on the goods/sale day (LOWER/HIGHER, run 36041422305/36041435083): WIP -10 / FG -6 / COGS -4 (=10x) all dated E; readiness READY; close accepted after the invoice.
- S04 probe: cutting 4 units at 08:00 from a roll received 23:30 the same day is refused at the cutting RPC (`AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY`), receipt 2026-09-22 23:30+07 vs cut 08:00+07. Historical per-location validation exists at cut time. Provisional finding F1-09 is REFUTED by this probe.

## The ambiguous shape (invoice dated BEFORE the physical cut / goods day)
Observed (after, AZ): material inventory carries the whole correction on E (all units still in stock on E), the WIP/FG/COGS legs are dated on the day the units physically moved (max(E, movement day)); WIP never negative; conservation holds. Observed (before, no AZ): the WIP leg is dated E, giving WIP -8 / -14 / +20 on E before any cut existed (per-date inconsistency, AUD-B04). The literal reading of ERP-DEC01 ("every leg on E") is what the frozen AS/calendar oracles encode and what the BEFORE phase does; it is physically inconsistent. The candidate's rule is the one the writer quotes as an owner decision of 24 Sep, which is not in the three contract files → UNVERIFIED_OWNER_DECISION. Status of these two cases is COUNTEREXAMPLE against the literal contract text, not a product defect; disposition belongs to the owner.
