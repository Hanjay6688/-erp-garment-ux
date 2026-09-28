# Independent BE audit — locked business oracle, 28 September 2026 WIB

Product candidate: `e09b0207f08b7736fad79e82fd81f1bf5dc1a85d`, tree
`8b0f3fe4ca615458211715612db6ceaf5e24cb44`. This is the explicit BE release
checkpoint, separate from the earlier BD audit of 08065a3 and future BD fixes.
No production/UAT writes, product fixes, merge, or deployment are part of this
audit. Only our own audit branch and disposable databases are writable.

## Authority and independence

- Owner asked this session to continue with a complete independent BE audit.
- ERP_V3_2.md current Library version 15, and the recovered master
  ERP_V3_2_Master_Pulih_20260923.md: identity, quantity, immutable facts,
  idempotence, dates, source cost, accessories/conversion, and pocket rules.
- Owner-approved D01–D06 and C6 rev4, in candidate docs/contracts: conversion
  with accessories and redye BS into a new identity are included in CP6.
  Undecided production policy values remain pending. Synthetic fixture choices
  are explicit test choices and never become production settings.
- No BE writer tests, fixtures, expected results, evidence, or peer audit have
  been opened or adopted. Candidate/source filenames and commit metadata are
  visible. The owner master and C6 contain historical writer observations;
  incidental exposure is recorded and those numerical examples are not used
  as our expected values. Our already-authored BD environment/fixture adapters
  may be reused; their business findings remain separate from new BE findings.
- Business invariants and numbers below are fixed before reading BE product
  implementation. Reading source later establishes API shape and diagnoses
  adapter errors; it does not define the expected financial result.

## Core invariants

Draft/preview does not change authoritative quantity or journals. Posting is
atomic. A partial operation consumes only its explicit source quantity and
capacity. The same UUID/payload has one effect; changed payload is refused.
Two active, different actors competing for one capacity cannot both spend it.
Current authorization applies to normal calls and cached responses alike.

Posted input facts, identity, source, physical time and original amount remain
immutable. Correction/reversal has explicit lineage and respects downstream
dependencies. Backdating cannot borrow future quantity or change closed facts.
Unknown, configured zero and known positive are distinct. Default policy is
pending/refusal where the owner has not chosen a value.

Brand/SKU/model/color/size and identity root remain exact. Price lookup never
changes garment identity. Only a valid conversion/rework completion can create
the chosen target, linked to the actual source and QC. Stock, value, payroll,
reimbursement and vendor liabilities are separate quantities and reconcile.

## Independent numeric seeds and financial expectations

1. Conversion fixture: 13 PCS at an explicitly established source cost of
   1,234.57 per PCS (16,049.41). Convert 5 PCS: source portion 6,172.85;
   remaining 8 PCS 9,876.56. Five actually used new accessories at 23.17 cost
   115.85. An explicitly applicable service charge 143.29 gives target cost
   6,431.99. Source+target garment value 16,308.55 equals old garment value plus
   259.14 new cost. Accessory stock falls only once; no contractor sale or
   reimbursement is invented. No recovery credit/value is assumed unless its
   independently documented policy and real returned quantity support it.
2. Redye fixture: 9 BS PCS with established source value 1,432.19 each. Send
   7, leave 2 untouched. A completed result of 5 GOOD + 2 residual BS conserves
   all 9 PCS including the unsent 2. Partial progress never pretends the full
   7 are complete. If an explicit fixture charges all 7 serviced PCS at 197.31,
   the service total is 1,381.17, and total value after that service is
   14,270.88. Invoice actual 1,417.53 replaces that estimate: final total
   14,307.24, a delta of 36.36, with no second physical movement. Allocation to
   GOOD/residual must conserve the exact source charge with deterministic
   residuals and the approved cost/valuation policy.
3. Pocket fixture: 6.75 units consumed at 17.29 imply exact raw value 116.7075
   and monetary total 116.71 at two decimals. Stock-only operation recognizes
   period expense without garment HPP. If explicitly allocated to legitimate
   sewing output of 7 and 6 PCS, totals at cents are 62.84 and 53.87. Changing
   actual source price to 19.31 gives total 130.34 and parts 70.18 and 60.16.
   All source precision is retained; the audit checks native monetary rounding
   boundaries rather than inserting rounded values to force a match.
4. Further positive fixtures can be added before their first execution, using
   independently calculated Decimal values and retaining the reason. API-shape
   or fixture changes never replace a failed economic oracle silently.

## Coverage register, initially NOT_RUN

Each item must finish with executed evidence, a reproduced product failure,
or a specific measured prerequisite gap. A parent failure must not suppress
unrelated cases. Setup failures are not labelled product bugs.

### CONV — conversion and accessories

01 legitimate source and exact target selection; 02 draft/preview unchanged;
03 partial 5 of 13 source; 04 no-accessory control; 05 real accessory use and
cost; 06 actually returned old accessories versus assumed BOM quantities;
07 recovery pending/valuation without double cost; 08 distinct-brand same SKU;
09 incompatible model/size/target; 10 excess and invalid quantities/money;
11 replay and UUID/payload mismatch; 12 stale draft/source;
13 reversal before use; 14 reversal after downstream use;
15 sale/return of converted goods and late source recost; 16 conversion chain.

### REDYE — BS, custody, QC and vendor cost

01 legacy same-product free rewash control; 02 explicit redye service/target;
03 SAVE/send without invented FG/payable; 04 partial/cumulative actual return;
05 GOOD+BS boundary and excess refusal; 06 exact target lineage;
07 wrong identity/size/location; 08 source overuse and duplicate completion;
09 known estimate; 10 unknown versus legitimate free policy;
11 late actual invoice and variance without quantity duplication;
12 partial invoice/payment/correction; 13 downstream sale/return/recost;
14 before-source/future/WIB dates; 15 open/closed-period financial behavior;
16 reversal dependencies; 17 rate snapshot stability; 18 pricing UI/router.

### NONPO — real unsourced/opening garments and rework

01 positive non-PO FG/BS lineage; 02 PO not fabricated;
03 genuine opening state continuation without historical sewing fiction;
04 source-capacity conservation; 05 supported rework target/mode variants;
06 completion cost and movement; 07 actual labor liability when applicable;
08 no fake regular payroll/reimbursement; 09 sale/return/descendant cost;
10 reversals/corrections and downstream dependency; 11 invalid target/input;
12 own import overlap/lock behavior and unrelated-operation control.

### POCKET — source movement, period basis and recost

01 stock-only control; 02 quantity versus remaining-roll entry;
03 preview unchanged; 04 valid allocation and exact cents;
05 legitimate sewing denominator including special contractor;
06 no fabricated denominator from opening WIP/non-PO opening FG;
07 mixed PO/conversion descendants; 08 WIP/FG/sold cost propagation;
09 late price increase/decrease; 10 period/date/as-of boundaries;
11 cancellation without second stock movement; 12 overlap/stale preview;
13 blocked source/denominator edits with active allocation;
14 invalid/empty period or quantity; 15 legitimate correction/reallocation.

### ACCESS/RACE — test each new public family

Active authorized owner controls; active regular operator read/write boundary;
money hiding; anonymous/inactive denial; revoke then same-token fresh and
replay calls; cross-actor requests; direct private helper/table denial;
source overuse by two distinct accounts; same request race; stale version
race; conversion/rework versus sale/import/pocket conflicts where applicable.
Denied calls must show no partial effects and the intended boundary, not merely
fail because the positive fixture is invalid.

### RELEASE/UI — delivered system and actual browser

Exact release install over its supported predecessor; separate source chain;
pre-use rollback equality; post-use rollback refusal without changes; official
build and existing security gates scoped to the pinned candidate.

Real Auth/HTTP and actual product UI: conversion, BS/rework/redye, pocket and
supporting selectors; independent inputs, confirmed payload, stored result,
reload and ledger; permissions; wrong/stale/rejected requests; lost response
and retry using the original UUID; source search/pagination with data beyond
the rendered cap. Desktop and Chromium mobile emulation with native touch;
do not claim physical-device or Safari coverage. Use viewport mobile captures
with before/after touch probes, as established by our BD tool corrections.

## Reporting

Keep new independent BE findings separate from inherited BD defects and any
later peer-informed cross-check. One combined writer handoff must give source
identity, input, expected/actual, relevant ledger/lineage, acceptance retest and
the limits of the evidence. No blanket PASS from a count or green workflow.
Production decision remains false until acceptance requirements are met.
